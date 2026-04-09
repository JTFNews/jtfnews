#!/bin/bash
# Phase C post-sprint verification — Step 2 (formatter + parser smoke test).
#
# Reads the given date's daily archive via parse_daily_archive (PHASEC-04),
# then formats the resulting fact list via build_youtube_description
# (PHASEC-02). Prints the output to stdout — no side effects, no API calls,
# no file writes.
#
# Usage:
#   ./verify_phasec_smoke.sh             # uses default 2026-04-08
#   ./verify_phasec_smoke.sh 2026-04-06  # test a different date
#
# Throwaway: delete after Phase C post-sprint verification is complete.

set -e
cd "$(dirname "$0")"

DATE="${1:-2026-04-08}"

if [ ! -d venv ]; then
    echo "ERROR: venv not found. Run ./start.sh once to set up the environment."
    exit 1
fi

if [ ! -f main.py ]; then
    echo "ERROR: main.py not found in $(pwd)"
    exit 1
fi

source venv/bin/activate

# Quoted 'PYEOF' so no variable substitution — the date is passed via argv.
python3 - "$DATE" <<'PYEOF'
import sys
from main import build_youtube_description, parse_daily_archive

date = sys.argv[1]
facts = parse_daily_archive(date)
print(f"parsed {len(facts)} facts for {date}")
print("---")
desc = build_youtube_description(date, facts)
print(desc)
print("---")
print(f"description length: {len(desc)} chars")

# Sanity assertions — will raise AssertionError and print a stack trace if any
# of the hard invariants from PHASEC-02 are violated.
assert len(desc) <= 5000, f"description exceeds YouTube 5000-char limit: {len(desc)}"
assert desc.startswith(f"JTF News for "), f"header does not start with 'JTF News for': {desc[:60]!r}"
assert desc.rstrip().endswith("JTF News: Two sources. No adjectives. Just facts."), "footer tagline missing or malformed"
assert "CC-BY-SA." in desc, "CC-BY-SA footer missing"
print("invariants: length<=5000, header, footer, CC-BY-SA — all pass")
PYEOF
