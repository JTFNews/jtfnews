#!/bin/bash
# Manual daily digest trigger - mimics midnight behavior
# Usage: ./digest.sh 2026-02-20

set -e

DATE=${1:-$(date -v-1d +%Y-%m-%d)}

if [[ ! $DATE =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Usage: ./digest.sh YYYY-MM-DD"
    echo "Example: ./digest.sh 2026-02-20"
    exit 1
fi

echo "=== Generating daily digest for $DATE ==="

cd "$(dirname "$0")"
source venv/bin/activate

python3 -c "
from main import generate_and_upload_daily_summary
generate_and_upload_daily_summary('$DATE')
"

echo "=== Done ==="
