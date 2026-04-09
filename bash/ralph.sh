#!/bin/bash
# Ralph Wiggum — long-running autonomous coding loop for JTF News
# Usage: ./bash/ralph.sh [max_iterations]
#
# Each iteration spawns a fresh Claude session that reads CLAUDE.md (for the
# Ralph Agent Instructions contract), prd.json (sprint stories), and
# progress.txt (codebase patterns + learnings log), implements the next
# story, and commits atomically via ./bu.sh.
#
# JTF News customizations vs. OTTO's ralph.sh:
#   - Claude-only (no amp fallback — JTF News doesn't use amp)
#   - Prompt includes the hard NO-PYTHON constraint
#   - Verification phase tells Claude to emit COMPLETE immediately (no test
#     suite exists; manual verification is user-only)
#   - Uses flat .stories[] structure in prd.json

set -e

MAX_ITERATIONS="${1:-100}"
if ! [[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
    MAX_ITERATIONS=100
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
PRD_FILE="$PROJECT_ROOT/prd.json"
PROGRESS_FILE="$PROJECT_ROOT/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

# Archive previous sprint if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
    CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
    LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")

    if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
        DATE=$(date +%Y-%m-%d)
        FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
        ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"

        echo "Archiving previous sprint: $LAST_BRANCH"
        mkdir -p "$ARCHIVE_FOLDER"
        [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
        [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
        echo "  Archived to: $ARCHIVE_FOLDER"

        # Reset progress for new sprint (but preserve Codebase Patterns header)
        if grep -q '^## Codebase Patterns' "$PROGRESS_FILE" 2>/dev/null; then
            awk '/^## \[/ {exit} {print}' "$PROGRESS_FILE" > "${PROGRESS_FILE}.tmp"
            mv "${PROGRESS_FILE}.tmp" "$PROGRESS_FILE"
        else
            echo "## Codebase Patterns" > "$PROGRESS_FILE"
            echo "" >> "$PROGRESS_FILE"
            echo "(Sprint in progress — patterns will be appended as stories complete)" >> "$PROGRESS_FILE"
            echo "" >> "$PROGRESS_FILE"
            echo "---" >> "$PROGRESS_FILE"
        fi
    fi
fi

# Track current branch
if [ -f "$PRD_FILE" ]; then
    CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
    if [ -n "$CURRENT_BRANCH" ]; then
        echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
    fi
fi

# Initialize progress file if missing
if [ ! -f "$PROGRESS_FILE" ]; then
    cat > "$PROGRESS_FILE" <<'EOF'
## Codebase Patterns

(Sprint in progress — patterns will be appended as stories complete.)

---
EOF
fi

echo "Starting Ralph for JTF News — max iterations: $MAX_ITERATIONS"

# The prompt that drives every iteration. Reads CLAUDE.md for the full Ralph
# Agent Instructions contract; the prompt below is the per-iteration kick.
ITERATION_PROMPT=$(cat <<'PROMPT'
Follow the Ralph Agent Instructions at the top of CLAUDE.md. Read prd.json and
progress.txt. Pick the highest-priority story where passes:false, implement it,
then atomically commit code + prd.json (passes:true) + progress.txt + any
CLAUDE.md updates via ./bu.sh.

HARD CONSTRAINT: You cannot run Python. Not python, not pip, not main.py, not
./start.sh, not ./digest.sh, not python -c, not python -m py_compile. Python
execution is user-only on this project. Verify acceptance criteria using
static checks only: grep, file existence, git log, function signatures,
bash -n for shell scripts, jq for JSON. If a story's acceptance criterion
appears to require Python execution, rewrite it as a static check or mark the
story blocked in progress.txt and move to the next story.

IMPORTANT: Do NOT run builds or tests during this phase. Focus on code edits
and git commits via ./bu.sh.
PROMPT
)

VERIFY_PROMPT=$(cat <<'PROMPT'
All stories in prd.json are now marked passes:true. JTF News has no automated
test suite (the methodology is "run forever, verify via live operation") and
you cannot run Python anyway. Manual verification is user-only, documented in
progress.txt's "Post-sprint manual verification" section. Emit the exact
completion signal and nothing else:

<promise>COMPLETE</promise>
PROMPT
)

for i in $(seq 1 $MAX_ITERATIONS); do
    echo ""
    echo "==============================================================="
    echo "  Ralph Iteration $i of $MAX_ITERATIONS (JTF News)"
    echo "==============================================================="

    OUTPUT=$(cd "$PROJECT_ROOT" && claude --dangerously-skip-permissions --print "$ITERATION_PROMPT" 2>&1 | tee /dev/stderr) || true

    # Completion signal from the iteration itself
    if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
        echo ""
        echo "Ralph completed all tasks at iteration $i of $MAX_ITERATIONS"
        exit 0
    fi

    # Check if all stories pass — if so, run the verification iteration
    COMPLETED=$(jq '[.stories[] | select(.passes == true)] | length' "$PRD_FILE" 2>/dev/null || echo "0")
    TOTAL=$(jq '[.stories[]] | length' "$PRD_FILE" 2>/dev/null || echo "0")

    if [[ "$COMPLETED" == "$TOTAL" ]] && [[ "$TOTAL" -gt 0 ]]; then
        echo ""
        echo "==============================================================="
        echo "  All $TOTAL stories passed. Running verification iteration..."
        echo "==============================================================="

        VERIFY_OUTPUT=$(cd "$PROJECT_ROOT" && claude --dangerously-skip-permissions --print "$VERIFY_PROMPT" 2>&1 | tee /dev/stderr) || true

        if echo "$VERIFY_OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
            echo ""
            echo "Ralph completed sprint at iteration $i of $MAX_ITERATIONS"
            echo "User: run ./start.sh and ./fix-youtube-descriptions.sh via Jump Desktop."
            exit 0
        fi

        echo "Verification did not emit COMPLETE. Continuing..."
    fi

    echo "Iteration $i complete. Continuing..."
    sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing the sprint."
echo "Check $PROGRESS_FILE for status."
exit 1
