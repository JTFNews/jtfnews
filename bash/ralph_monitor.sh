#!/bin/bash

# Ralph Status Monitor — live terminal dashboard for the Ralph loop.
# Reads prd.json and progress.txt, displays current sprint progress and the
# next story queued for execution. Launched in a new Terminal tab by
# run_ralph.sh.
#
# Adapted from OTTO's ralph_monitor.sh — uses .stories[] flat structure.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
PRD_FILE="$PROJECT_ROOT/prd.json"
PROGRESS_FILE="$PROJECT_ROOT/progress.txt"
REFRESH_INTERVAL=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

clear_screen() {
    clear
    printf '\033[?25l'  # Hide cursor
}

show_cursor() {
    printf '\033[?25h'
}

cleanup() {
    show_cursor
    echo
    echo "Monitor stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

display_status() {
    clear_screen

    echo -e "${WHITE}==========================================================================${NC}"
    echo -e "${WHITE}                           RALPH MONITOR                                  ${NC}"
    echo -e "${WHITE}                    JTF News Live Sprint Dashboard                        ${NC}"
    echo -e "${WHITE}==========================================================================${NC}"
    echo

    # PRD status
    if [[ -f "$PRD_FILE" ]]; then
        local project=$(jq -r '.projectName // "unknown"' "$PRD_FILE" 2>/dev/null)
        local branch=$(jq -r '.branchName // "unknown"' "$PRD_FILE" 2>/dev/null)
        local total=$(jq '[.stories[]] | length' "$PRD_FILE" 2>/dev/null)
        local completed=$(jq '[.stories[] | select(.passes == true)] | length' "$PRD_FILE" 2>/dev/null)

        total=${total:-0}
        completed=${completed:-0}
        local percent=0
        if [[ "$total" -gt 0 ]]; then
            percent=$((completed * 100 / total))
        fi

        echo -e "${CYAN}--- Sprint Status ---${NC}"
        echo -e "${CYAN}  Project:${NC}  ${WHITE}$project${NC}"
        echo -e "${CYAN}  Branch:${NC}   ${WHITE}$branch${NC}"
        echo -e "${CYAN}  Progress:${NC} ${GREEN}$completed${NC}/${WHITE}$total${NC} stories (${percent}%)"

        # Progress bar
        local bar_width=50
        local filled=0
        if [[ "$total" -gt 0 ]]; then
            filled=$((completed * bar_width / total))
        fi
        local empty=$((bar_width - filled))
        printf "${CYAN}  [${NC}"
        printf "${GREEN}%${filled}s" | tr ' ' '#'
        printf "${NC}%${empty}s" | tr ' ' '.'
        printf "${CYAN}]${NC}\n"
        echo

        # Next story
        local next_id=$(jq -r '[.stories[] | select(.passes == false)] | sort_by(.priority) | .[0].id // "COMPLETE"' "$PRD_FILE" 2>/dev/null)
        local next_title=$(jq -r '[.stories[] | select(.passes == false)] | sort_by(.priority) | .[0].title // "All done!"' "$PRD_FILE" 2>/dev/null)

        if [[ "$next_id" != "COMPLETE" ]]; then
            echo -e "${YELLOW}--- Next Story ---${NC}"
            echo -e "${YELLOW}  ${WHITE}$next_id${NC}: $next_title"
        else
            echo -e "${GREEN}--- STATUS ---${NC}"
            echo -e "${GREEN}  ALL STORIES COMPLETE!${NC}"
            echo -e "${GREEN}  User: run ./start.sh and ./fix-youtube-descriptions.sh via Jump Desktop.${NC}"
        fi
        echo
    else
        echo -e "${RED}--- Error ---${NC}"
        echo -e "${RED}  PRD file not found: $PRD_FILE${NC}"
        echo
    fi

    # Recent progress entries
    echo -e "${BLUE}--- Recent Progress ---${NC}"
    if [[ -f "$PROGRESS_FILE" ]]; then
        grep -v '^---$' "$PROGRESS_FILE" | grep -v '^$' | tail -n 10 | while IFS= read -r line; do
            if [[ ${#line} -gt 72 ]]; then
                line="${line:0:69}..."
            fi
            echo -e "${BLUE}  $line${NC}"
        done
    else
        echo -e "${BLUE}  No progress file found${NC}"
    fi
    echo

    # Footer
    echo -e "${YELLOW}Refreshes every ${REFRESH_INTERVAL}s | $(date '+%Y-%m-%d %H:%M:%S') | Ctrl+C to exit${NC}"
}

main() {
    echo "Starting Ralph Monitor..."
    sleep 1
    while true; do
        display_status
        sleep "$REFRESH_INTERVAL"
    done
}

main
