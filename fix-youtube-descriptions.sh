#!/bin/bash
# fix-youtube-descriptions.sh — one-time backfill of YouTube digest descriptions.
#
# This is a user-facing wrapper around main.py's --backfill-youtube-descriptions
# CLI flags (added in PHASEC-10). Run this once after the Phase C sprint
# completes to patch the existing historical digest videos with the new
# per-fact description format.
#
# Usage:
#   ./fix-youtube-descriptions.sh --dry-run    # preview — writes data/backfill_dry_run/*.txt
#   ./fix-youtube-descriptions.sh --confirm    # live run — actually calls YouTube API
#
# Ordering: run --dry-run first, review the generated .txt files for voice
# correctness, then run --confirm to apply the changes via the YouTube API.
#
# After a successful live run, the marker file
# data/youtube_description_backfill.json tracks which videos have been
# updated, so re-running is idempotent — already-patched videos are skipped.

set -e

cd "$(dirname "$0")"

if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found in $(pwd)"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "ERROR: venv/ not found. Run ./start.sh once to set up the environment."
    exit 1
fi

source venv/bin/activate

case "$1" in
    --dry-run)
        echo "Running dry-run backfill. No API calls will be made."
        python main.py --backfill-youtube-descriptions-dry-run
        echo ""
        echo "Dry-run complete. Preview files written to data/backfill_dry_run/"
        echo "Review them and then re-run with --confirm to apply the changes."
        ;;
    --confirm)
        echo "Running LIVE backfill. This will modify YouTube video descriptions."
        echo "Press Ctrl+C within 5 seconds to cancel..."
        sleep 5
        python main.py --backfill-youtube-descriptions
        echo ""
        echo "Live backfill complete. Marker file: data/youtube_description_backfill.json"
        echo "Open YouTube and verify 2-3 video descriptions manually."
        ;;
    *)
        echo "Usage:"
        echo "  $0 --dry-run    (preview descriptions, no API calls)"
        echo "  $0 --confirm    (live run, actually modifies YouTube videos)"
        exit 1
        ;;
esac
