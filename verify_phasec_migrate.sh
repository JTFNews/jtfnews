#!/bin/bash
# Phase C post-sprint verification — Step 3 (one-time feed.xml heal migration).
#
# Runs migrate_feed_xml_digest_entries() which:
#   1. Queries the YouTube channel's uploads playlist for {date: video_id}
#   2. Walks feed.xml's 9 historical digest entries
#   3. For each: calls add_digest_to_feed with the healed update branch,
#      which adds the missing <link>, jtf:type, and jtf:archive elements
#
# Side effects: up to 9 separate GitHub Pages commits, one per healed entry,
# named "Heal digest feed entry for YYYY-MM-DD".
#
# Idempotent: safe to re-run. Already-healed entries are logged as
# "already complete" and the function returns without mutation.
#
# Usage:
#   ./verify_phasec_migrate.sh
#
# Throwaway: delete after Phase C post-sprint verification is complete.

set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "ERROR: venv not found. Run ./start.sh once to set up the environment."
    exit 1
fi

if [ ! -f main.py ]; then
    echo "ERROR: main.py not found in $(pwd)"
    exit 1
fi

source venv/bin/activate

echo "=== feed.xml BEFORE migration ==="
echo -n "  digest entries:           "
grep -c 'digest-' docs/feed.xmlecho -n "  <link> tags to youtube:   "
grep -c 'watch?v=' docs/feed.xmlecho -n "  jtf:type attributes:      "
grep -c 'jtf:type' docs/feed.xmlecho -n "  jtf:archive elements:     "
grep -c 'jtf:archive' docs/feed.xmlecho ""

echo "=== Running migrate_feed_xml_digest_entries() ==="
python3 - <<'PYEOF'
import json
from main import migrate_feed_xml_digest_entries

summary = migrate_feed_xml_digest_entries()
print("")
print("=== Migration summary ===")
print(json.dumps(summary, indent=2))
PYEOF
echo ""

echo "=== feed.xml AFTER migration ==="
echo -n "  digest entries:           "
grep -c 'digest-' docs/feed.xmlecho -n "  <link> tags to youtube:   "
grep -c 'watch?v=' docs/feed.xmlecho -n "  jtf:type attributes:      "
grep -c 'jtf:type' docs/feed.xmlecho -n "  jtf:archive elements:     "
grep -c 'jtf:archive' docs/feed.xmlecho ""
echo "Expected after: 9 digest entries, 9+ <link> tags with watch?v=, 9 jtf:type, 9 jtf:archive"
