#!/bin/bash
# Ralph Suite Launcher — starts the JTF News Ralph loop, monitor, and watchdog.
# Usage: ./run_ralph.sh [max_iterations]
#
# Opens a new Terminal tab for the status monitor, starts the watchdog in the
# background, and runs the main Ralph loop in the foreground. Ctrl+C stops
# everything cleanly.
#
# IMPORTANT: This script is designed to be run BY THE USER in an interactive
# Terminal. Do not attempt to run it from a remote agent or background process
# — the monitor launch uses osascript to open a new Terminal tab, which
# requires an active GUI session.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_ARGS="$@"

cleanup() {
    echo ""
    echo "Stopping Ralph suite..."
    kill $WATCHDOG_PID 2>/dev/null
    wait 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

cd "$SCRIPT_DIR"

# Sanity check — the three sibling scripts must exist
for script in bash/ralph.sh bash/ralph_monitor.sh bash/ralph_watchdog.sh; do
    if [ ! -f "$script" ]; then
        echo "ERROR: $script not found. Ralph infrastructure is incomplete."
        exit 1
    fi
    chmod +x "$script" 2>/dev/null || true
done

if [ ! -f "prd.json" ]; then
    echo "ERROR: prd.json not found. Nothing for Ralph to do."
    exit 1
fi

if [ ! -f "progress.txt" ]; then
    echo "WARNING: progress.txt not found. Will be created by the loop."
fi

# Start watchdog in background (logs to bash/ralph_watchdog.log)
bash/ralph_watchdog.sh &
WATCHDOG_PID=$!
echo "Started watchdog (PID: $WATCHDOG_PID)"

# Launch monitor in a new Terminal tab (macOS only)
osascript -e 'tell app "Terminal" to do script "cd '"$SCRIPT_DIR"' && bash/ralph_monitor.sh"' >/dev/null 2>&1
echo "Started monitor in new Terminal tab"

echo ""
echo "Ralph suite running. Ctrl+C to stop everything."
echo "Main loop:"
echo ""

# Run ralph loop in foreground — blocks until done or max iterations
bash/ralph.sh $RALPH_ARGS

cleanup
