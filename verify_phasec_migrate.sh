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

show_counts() {
    local label="$1"
    echo "=== feed.xml $label migration ==="
    printf "  digest entries:           %s\n" "$(grep -c 'digest-' docs/feed.xml)"
    printf "  <link> tags to youtube:   %s\n" "$(grep -c 'watch?v=' docs/feed.xml)"
    printf "  jtf:type attributes:      %s\n" "$(grep -c 'jtf:type' docs/feed.xml)"
    printf "  jtf:archive elements:     %s\n" "$(grep -c 'jtf:archive' docs/feed.xml)"
    echo ""
}

show_counts "BEFORE"

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

show_counts "AFTER"

echo "Expected after: 9 digest entries, 9+ <link> tags with watch?v=, 9 jtf:type, 9 jtf:archive"
