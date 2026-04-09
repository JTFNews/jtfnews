#!/bin/bash
# Regenerate and push the archived daily log for a specific date.
#
# Use this when the normal midnight archive rotation (main.py::archive_daily_log)
# did not run on schedule — typically because the machine lost power or was
# offline at 00:00 UTC, as happened for 2026-04-07 — but the raw daily log
# at data/YYYY-MM-DD.txt is still intact from an earlier scrape that same day.
#
# This script is a date-parameterized version of archive_daily_log().  The
# original is hardcoded to "yesterday" (main.py:6739-6741), which is why a
# retry a day or two after the outage archives the wrong date — it picks up
# whatever was "yesterday" at the moment of the retry, not the day that was
# actually missed.  This script fixes that by taking the date explicitly.
#
# What it does, in order:
#   1. Verifies data/YYYY-MM-DD.txt exists (the raw log)
#   2. Verifies docs/archive/<year>/YYYY-MM-DD.txt.gz does NOT already exist
#   3. Runs mark_corrected_stories_in_log() on the raw log
#   4. Gzips the raw log into docs/archive/<year>/YYYY-MM-DD.txt.gz
#   5. Pushes the new .txt.gz to GitHub Pages via push_to_ghpages()
#   6. Calls update_archive_index() which also refreshes search-index.json.gz
#      and pushes both to GitHub Pages
#   7. Only after every push succeeds, cleans up the local raw log files
#      (data/<date>.txt, shown_<date>.txt, processed_<date>.txt,
#      fact_cache_<date>.json) so the post-state matches a normal rotation.
#      If any step above fails, the raw files are left in place so you can
#      inspect and retry without losing data.
#
# Usage:
#   ./regenerate_archive.sh 2026-04-07
#
# Preconditions:
#   - data/YYYY-MM-DD.txt exists
#   - docs/archive/<year>/YYYY-MM-DD.txt.gz does not exist
#   - venv is set up
#   - .env credentials (GitHub token) are present — loaded automatically by main.py

set -e

DATE=$1

if [[ -z "$DATE" ]] || [[ ! "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Usage: ./regenerate_archive.sh YYYY-MM-DD"
    echo "Example: ./regenerate_archive.sh 2026-04-07"
    exit 1
fi

cd "$(dirname "$0")"

YEAR="${DATE:0:4}"
RAW_LOG="data/${DATE}.txt"
ARCHIVE_FILE="docs/archive/${YEAR}/${DATE}.txt.gz"

if [[ ! -f "$RAW_LOG" ]]; then
    echo "ERROR: $RAW_LOG does not exist."
    echo ""
    echo "       This script is only useful when the midnight rotation missed"
    echo "       a day whose raw log is still present on disk. If the raw log"
    echo "       is already gone, there is nothing to regenerate from — the"
    echo "       stories for $DATE can no longer be recovered from this"
    echo "       machine."
    exit 1
fi

if [[ -f "$ARCHIVE_FILE" ]]; then
    echo "ERROR: $ARCHIVE_FILE already exists."
    echo ""
    echo "       Refusing to overwrite an existing archive.  If you really"
    echo "       intend to regenerate from the raw log, delete the existing"
    echo "       archive file first:"
    echo ""
    echo "           rm '$ARCHIVE_FILE'"
    echo "           ./regenerate_archive.sh $DATE"
    exit 1
fi

echo "=== Regenerating archive for $DATE ==="
echo "    Raw log:     $RAW_LOG"
echo "    Archive to:  $ARCHIVE_FILE"
echo ""

source venv/bin/activate

python3 - "$DATE" <<'PYEOF'
import sys
import gzip
import shutil
from pathlib import Path

# Importing `main` triggers its module-level load_dotenv() and wires up
# BASE_DIR / DATA_DIR / log / push_to_ghpages so we can reuse the production
# rotation primitives verbatim rather than re-implementing them here.
from main import (
    BASE_DIR,
    DATA_DIR,
    mark_corrected_stories_in_log,
    push_to_ghpages,
    update_archive_index,
    log,
)

date_str = sys.argv[1]
year = date_str[:4]

log_file = DATA_DIR / f"{date_str}.txt"
hash_file = DATA_DIR / f"shown_{date_str}.txt"
processed_file = DATA_DIR / f"processed_{date_str}.txt"
fact_cache_file = DATA_DIR / f"fact_cache_{date_str}.json"

# Step 1: mark any corrected stories in the raw log (mirrors the normal
# rotation — if a correction was issued against a $date_str story between
# scrape time and now, it needs to be reflected in the archived copy).
mark_corrected_stories_in_log(log_file, date_str)

# Step 2: gzip the raw log into its final docs/archive location.
archive_dir = BASE_DIR / "docs" / "archive" / year
archive_dir.mkdir(parents=True, exist_ok=True)
archive_file = archive_dir / f"{date_str}.txt.gz"

with open(log_file, 'rb') as f_in:
    with gzip.open(archive_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

log.info(f"Archived: {archive_file}")
print(f"[1/3] Wrote {archive_file}")

# Step 3: push the archive file to GitHub Pages.  This is the same call the
# normal rotation makes at main.py:6785.
push_to_ghpages(
    [(archive_file, f"archive/{year}/{date_str}.txt.gz")],
    f"Backfill archive {date_str}"
)
print(f"[2/3] Pushed {archive_file.name} to GitHub Pages")

# Step 4: update the archive index (which also rebuilds and pushes the
# search index).  update_archive_index() scans the archive directory, so it
# will automatically pick up the new date and its ordering.
update_archive_index()
print(f"[3/3] Updated archive index + search index")

# Step 5: clean up local raw files — only reached if every preceding step
# succeeded, so a failure at any step above leaves the raw log intact for
# inspection and retry.
log_file.unlink(missing_ok=True)
hash_file.unlink(missing_ok=True)
processed_file.unlink(missing_ok=True)
fact_cache_file.unlink(missing_ok=True)
print(f"      Cleaned up local raw log files for {date_str}")
PYEOF

echo ""
echo "=== Done — $DATE is now in the archive ==="
echo ""
echo "Verify with:"
echo "    curl -s https://jtfnews.org/archive/index.json | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d[\"dates\"][:5])'"
