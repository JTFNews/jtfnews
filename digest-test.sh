#!/bin/bash
# Local-only digest test - records via OBS, saves final video to ~/Downloads,
# skips YouTube upload and podcast pipeline.
# Usage: ./digest-test.sh [YYYY-MM-DD]

set -e

DATE=${1:-$(date -v-1d +%Y-%m-%d)}

if [[ ! $DATE =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Usage: ./digest-test.sh YYYY-MM-DD"
    echo "Example: ./digest-test.sh 2026-07-02"
    exit 1
fi

echo "=== Generating TEST daily digest for $DATE (local only, no upload) ==="

cd "$(dirname "$0")"
source venv/bin/activate

python3 -c "
from main import generate_and_upload_daily_summary
generate_and_upload_daily_summary('$DATE', test_local=True)
"

echo "=== Done. Look for JTFNews-Digest-$DATE-TEST.mp4 in ~/Downloads ==="
