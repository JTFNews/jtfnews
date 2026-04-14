#!/bin/bash

# Refuse to run from the M4 SMB mount. bu.sh is designed to run on the
# Intel Mac directly; the backup step hardcodes /Users/larryseyer/JTFNews
# and fails from the mount (incident 2026-04-13).
REAL_PWD="$(pwd -P)"
if [[ "$REAL_PWD" == /Volumes/* ]]; then
    echo "ERROR: bu.sh cannot run from the M4 SMB mount."
    echo "       Current path: $REAL_PWD"
    echo "       Run this from the Intel Mac (Jump Desktop terminal)."
    exit 1
fi

if [ -z "$1" ]; then
    echo "Usage: bu.sh \"commit message\""
    exit 1
fi

# =============================================================================
# RUNTIME FILES — main.py pushes these via GitHub API, never stage them
# =============================================================================
RUNTIME_FILES=(
    "docs/feed.xml"
    "docs/stories.json"
    "docs/monitor.json"
    "docs/podcast.xml"
    "docs/archive/index.json"
    "docs/corrections.json"
    "docs/journalists.json"
    "docs/alexa.json"
    "data/"
    "jtf.log"
)

# =============================================================================
# PULL FIRST — remote is always ahead from main.py API pushes
# Stash first because main.py may have modified runtime files locally
# =============================================================================
echo "Pulling latest from remote..."
git stash --quiet 2>/dev/null
STASHED=$?
git pull --rebase origin main
PULL_STATUS=$?
if [ $STASHED -eq 0 ]; then
    git stash pop --quiet 2>/dev/null
fi

# If rebase conflicts occur on runtime files, keep local (this IS the live server)
if [ $PULL_STATUS -ne 0 ]; then
    # If no rebase is actually in progress, the pull failed BEFORE the rebase
    # started (e.g., an untracked file in the working tree conflicts with an
    # incoming commit). Do NOT fall through to staging/committing — that
    # commits on a stale base (incident 2026-04-13, commit 24cf2b5bb).
    if [ ! -d .git/rebase-merge ] && [ ! -d .git/rebase-apply ]; then
        echo ""
        echo "ERROR: git pull --rebase failed before the rebase started."
        echo "       Usually means an untracked file in the working tree"
        echo "       conflicts with an incoming commit. Run 'git status'"
        echo "       and resolve manually. Aborting bu.sh."
        exit 1
    fi

    echo ""
    echo "Rebase conflict detected. Checking for runtime file conflicts..."
    CONFLICT_FILES=$(git diff --name-only --diff-filter=U)
    ALL_RUNTIME=true
    for file in $CONFLICT_FILES; do
        IS_RUNTIME=false
        for rf in "${RUNTIME_FILES[@]}"; do
            if [[ "$file" == "$rf" || "$file" == "$rf"* ]]; then
                IS_RUNTIME=true
                break
            fi
        done
        if [ "$IS_RUNTIME" = true ]; then
            echo "  Resolving runtime file (keeping local): $file"
            git checkout --ours "$file"
            git add "$file"
        else
            ALL_RUNTIME=false
            echo "  NON-RUNTIME CONFLICT: $file — resolve manually"
        fi
    done
    if [ "$ALL_RUNTIME" = false ]; then
        echo ""
        echo "Non-runtime conflicts need manual resolution. Run 'git rebase --continue' after fixing."
        exit 1
    fi
    # GIT_EDITOR=true uses the no-op `true` command as editor so rebase --continue
    # accepts the existing commit message without opening an interactive editor.
    # (`git rebase --continue --no-edit` is NOT valid — that flag doesn't exist
    # on `rebase --continue` and its use silently stalls the rebase.)
    GIT_EDITOR=true git rebase --continue
fi

# =============================================================================
# STAGE EVERYTHING EXCEPT RUNTIME FILES
# =============================================================================
git add .

# Unstage runtime files
for rf in "${RUNTIME_FILES[@]}"; do
    git reset HEAD -- "$rf" 2>/dev/null
done

# Check if anything is staged
if git diff --cached --quiet; then
    echo "Nothing to commit (only runtime files changed)."
    exit 0
fi

echo ""
echo "Staged changes:"
git diff --cached --stat

# =============================================================================
# COMMIT AND PUSH
# =============================================================================
git commit -m "$1"
git push origin main

# =============================================================================
# BACKUP TO DOWNLOADS
# =============================================================================
SOURCE="/Users/larryseyer/JTFNews"
DEST_DIR="/Users/larryseyer/Downloads/JTFNews Backups"
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M_%S")
# Take first line only, limit to 50 chars, replace spaces/special chars
MESSAGE=$(echo "$1" | head -1 | cut -c1-50 | sed 's/[^a-zA-Z0-9]/_/g' | sed 's/__*/_/g' | sed 's/_$//')
ZIP_FILE="$DEST_DIR/JTFNews_${TIMESTAMP}_${MESSAGE}.zip"
cd "$SOURCE" || exit 1
zip -r "$ZIP_FILE" . -x "media/*" "media/" "video/*" "video/" "audio/*" "audio/" "data/*" "data/" "venv/*" "venv/" "__pycache__/*" "__pycache__/" ".git/*" ".git/" ".env"

echo ""
echo "Done!"
