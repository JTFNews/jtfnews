#!/bin/bash

# Ralph Watchdog — monitors Ralph's progress and detects stalls.
# Runs independently in the background, logs progress, alerts on stalls.
#
# Adapted from OTTO's ralph_watchdog.sh, with a bug fix: OTTO's version queries
# .epics[].stories[] but prd.json uses a flat .stories[] array (matching the
# monitor). JTFNews uses the same flat .stories[] structure.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
PRD_FILE="$PROJECT_ROOT/prd.json"
LOG_FILE="$SCRIPT_DIR/ralph_watchdog.log"
CHECK_INTERVAL=600   # 10 minutes between checks
STALL_THRESHOLD=1800 # 30 minutes without a commit = stalled

LAST_COMMIT=""
LAST_COMMIT_TIME=0
STALL_ALERTED=false

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_total_count() {
    jq '[.stories[]] | length' "$PRD_FILE" 2>/dev/null || echo "0"
}

get_completed_count() {
    jq '[.stories[] | select(.passes == true)] | length' "$PRD_FILE" 2>/dev/null || echo "0"
}

get_next_story() {
    jq -r '[.stories[] | select(.passes == false)][0] | "\(.id): \(.title)"' "$PRD_FILE" 2>/dev/null || echo "unknown"
}

get_latest_commit() {
    cd "$PROJECT_ROOT" && git log --oneline -1 --format="%h" 2>/dev/null || echo ""
}

get_latest_commit_time() {
    cd "$PROJECT_ROOT" && git log -1 --format="%ct" 2>/dev/null || echo "0"
}

is_ralph_running() {
    pgrep -f "ralph.sh" > /dev/null 2>&1
}

is_claude_running() {
    pgrep -f "claude" > /dev/null 2>&1
}

check_progress() {
    local current_commit=$(get_latest_commit)
    local current_time=$(date +%s)
    local total=$(get_total_count)
    local completed=$(get_completed_count)
    local next=$(get_next_story)

    # All stories done — exit cleanly
    if [[ "$completed" == "$total" ]] && [[ "$total" -gt 0 ]]; then
        log "ALL STORIES COMPLETE! ($completed/$total)"
        log "Ralph has finished the sprint successfully."
        exit 0
    fi

    # New commit since last check
    if [[ "$current_commit" != "$LAST_COMMIT" ]]; then
        LAST_COMMIT="$current_commit"
        LAST_COMMIT_TIME=$(get_latest_commit_time)
        STALL_ALERTED=false
        log "Progress: $completed/$total complete | Next: $next | Commit: $current_commit"
        return
    fi

    # No new commit — check for stall
    local time_since_commit=$((current_time - LAST_COMMIT_TIME))

    if [[ $time_since_commit -gt $STALL_THRESHOLD ]] && [[ "$STALL_ALERTED" == "false" ]]; then
        STALL_ALERTED=true
        log "STALL DETECTED: No commits for $((time_since_commit / 60)) minutes"
        log "    Last story: $next"
        log "    Claude running: $(is_claude_running && echo 'yes' || echo 'NO')"
        log "    Ralph running: $(is_ralph_running && echo 'yes' || echo 'NO')"
    elif [[ $time_since_commit -le $STALL_THRESHOLD ]]; then
        log "Waiting: $completed/$total | Working on: $next | ${time_since_commit}s since last commit"
    fi
}

main() {
    log "=========================================="
    log "Ralph Watchdog Started"
    log "Check interval: ${CHECK_INTERVAL}s ($(($CHECK_INTERVAL / 60)) min)"
    log "Stall threshold: ${STALL_THRESHOLD}s ($(($STALL_THRESHOLD / 60)) min)"
    log "=========================================="

    LAST_COMMIT=$(get_latest_commit)
    LAST_COMMIT_TIME=$(get_latest_commit_time)

    local total=$(get_total_count)
    local completed=$(get_completed_count)
    log "Starting state: $completed/$total stories complete"

    while true; do
        check_progress
        sleep "$CHECK_INTERVAL"
    done
}

trap 'log "Watchdog stopped by user"; exit 0' SIGINT SIGTERM

main
