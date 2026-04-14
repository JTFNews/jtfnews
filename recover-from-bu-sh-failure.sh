#!/bin/bash
# =============================================================================
# Recovery script for the bu.sh "Just to be safe" incident on 2026-04-13.
#
# Symptom: repo is "ahead 2, behind 493" of origin/main with dirty runtime
# files. The two local commits (24cf2b5b, 8a701abf) are byte-identical to
# content already on origin/main — fully redundant.
#
# Action: stash the dirty runtime files for safety, then hard-reset main
# to origin/main.
#
# RUN THIS ON THE INTEL MAC ONLY (via Jump Desktop terminal).
# Do NOT run from the M4 SMB mount.
# =============================================================================

set -e

EXPECTED_DIR="/Users/larryseyer/JTFNews"
LOG_FILE="$EXPECTED_DIR/readthis.txt"

# -----------------------------------------------------------------------------
# Guard: must run from the Intel Mac, not from the SMB mount
# -----------------------------------------------------------------------------
REAL_PWD="$(pwd -P)"
if [[ "$REAL_PWD" == /Volumes/* ]]; then
    echo "ERROR: this script cannot run from the M4 SMB mount."
    echo "       Current path: $REAL_PWD"
    echo "       Open a Jump Desktop session to the Intel Mac and run it there."
    exit 1
fi

if [[ "$REAL_PWD" != "$EXPECTED_DIR" ]]; then
    echo "ERROR: must run from $EXPECTED_DIR"
    echo "       Current path: $REAL_PWD"
    echo "       cd $EXPECTED_DIR && ./recover-from-bu-sh-failure.sh"
    exit 1
fi

# -----------------------------------------------------------------------------
# Show current state
# -----------------------------------------------------------------------------
echo "================================================================"
echo "Current repository state"
echo "================================================================"
git fetch origin 2>&1 | tee "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "--- git status -sb ---" | tee -a "$LOG_FILE"
git status -sb 2>&1 | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "--- last 3 local commits ---" | tee -a "$LOG_FILE"
git log --oneline -3 2>&1 | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "--- last 3 remote commits ---" | tee -a "$LOG_FILE"
git log --oneline origin/main -3 2>&1 | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# -----------------------------------------------------------------------------
# Confirm destructive action
# -----------------------------------------------------------------------------
echo "================================================================"
echo "About to do the following:"
echo "  1. git stash push -u the 8 dirty runtime files (recoverable)"
echo "  2. git reset --hard origin/main  (DROPS local commits)"
echo "================================================================"
echo ""
read -r -p "Proceed? Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted. No changes made."
    exit 1
fi

# -----------------------------------------------------------------------------
# Step 1: Stash dirty runtime files
# -----------------------------------------------------------------------------
STASH_MSG="pre-reset-dirty-runtime-$(date +%Y%m%d-%H%M%S)"
echo "" | tee -a "$LOG_FILE"
echo "--- stashing dirty runtime files ---" | tee -a "$LOG_FILE"
if git diff --quiet && git diff --cached --quiet; then
    echo "Working tree already clean — nothing to stash." | tee -a "$LOG_FILE"
else
    git stash push -u -m "$STASH_MSG" -- \
        docs/alexa.json \
        docs/archive/index.json \
        docs/feed.xml \
        docs/journalists.json \
        docs/monitor.json \
        docs/podcast.xml \
        docs/stories.json \
        jtf.log 2>&1 | tee -a "$LOG_FILE"
    echo "Stash saved as: $STASH_MSG" | tee -a "$LOG_FILE"
    echo "Recover with: git stash list   # find it, then   git stash pop <ref>" | tee -a "$LOG_FILE"
fi

# -----------------------------------------------------------------------------
# Step 2: Hard reset to origin/main
# -----------------------------------------------------------------------------
echo "" | tee -a "$LOG_FILE"
echo "--- hard-resetting main to origin/main ---" | tee -a "$LOG_FILE"
git reset --hard origin/main 2>&1 | tee -a "$LOG_FILE"

# -----------------------------------------------------------------------------
# Step 3: Verify
# -----------------------------------------------------------------------------
echo "" | tee -a "$LOG_FILE"
echo "================================================================" | tee -a "$LOG_FILE"
echo "Post-recovery state" | tee -a "$LOG_FILE"
echo "================================================================" | tee -a "$LOG_FILE"
echo "--- git status -sb ---" | tee -a "$LOG_FILE"
git status -sb 2>&1 | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "--- last 3 commits ---" | tee -a "$LOG_FILE"
git log --oneline -3 2>&1 | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# -----------------------------------------------------------------------------
# Sanity check: ahead/behind should be zero
# -----------------------------------------------------------------------------
AHEAD_BEHIND=$(git rev-list --left-right --count main...origin/main)
AHEAD=$(echo "$AHEAD_BEHIND" | awk '{print $1}')
BEHIND=$(echo "$AHEAD_BEHIND" | awk '{print $2}')
echo "Ahead: $AHEAD    Behind: $BEHIND" | tee -a "$LOG_FILE"

if [[ "$AHEAD" == "0" && "$BEHIND" == "0" ]]; then
    echo "" | tee -a "$LOG_FILE"
    echo "SUCCESS: main is in sync with origin/main." | tee -a "$LOG_FILE"
    echo "Log written to: $LOG_FILE" | tee -a "$LOG_FILE"
    echo ""
    echo "Note: main.py may regenerate runtime files (docs/monitor.json etc.)"
    echo "      on its next cycle. That is expected and will be auto-pushed."
    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "WARNING: main is still ahead=$AHEAD / behind=$BEHIND after reset." | tee -a "$LOG_FILE"
    echo "         Investigate manually. Log: $LOG_FILE" | tee -a "$LOG_FILE"
    exit 2
fi
