#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: bu.sh \"commit message\""
    exit 1
fi

# =============================================================================
# SYNC WEB FILES TO GH-PAGES (single source of truth)
# =============================================================================
# web/ is the source, gh-pages-dist/ gets synced copies
# This prevents web files from getting out of sync between branches

SHARED_FILES="lower-third.js lower-third.html lower-third.css screensaver.html background-slideshow.html monitor.html monitor.css monitor.js"

echo "=== Syncing web/ to gh-pages-dist/ ==="
for f in $SHARED_FILES; do
    if [ -f "web/$f" ]; then
        cp "web/$f" "gh-pages-dist/$f"
    fi
done

# Commit and push gh-pages if there are changes
cd gh-pages-dist
if [ -n "$(git status --porcelain)" ]; then
    git add .
    git commit -m "Sync web files: $1"
    git push origin gh-pages
    echo "gh-pages updated"
else
    echo "gh-pages already in sync"
fi
cd ..

# =============================================================================
# COMMIT MAIN BRANCH
# =============================================================================
git add .
git commit -m "$1"
git push origin main

# =============================================================================
# BACKUP TO DROPBOX
# =============================================================================
SOURCE="/Users/larryseyer/JTFNews"
DEST_DIR="/Users/larryseyer/Dropbox/Automagic Art/Source Backup/JTFNews Backups"
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M_%S")
# Take first line only, limit to 50 chars, replace spaces/special chars
MESSAGE=$(echo "$1" | head -1 | cut -c1-50 | sed 's/[^a-zA-Z0-9]/_/g' | sed 's/__*/_/g' | sed 's/_$//')
ZIP_FILE="$DEST_DIR/JTFNews_${TIMESTAMP}_${MESSAGE}.zip"
cd "$SOURCE" || exit 1
zip -r "$ZIP_FILE" . -x "media/*" "media/" "gh-pages-dist/*" "gh-pages-dist/" "audio/*" "audio/" "data/*" "data/" "venv/*" "venv/" "__pycache__/*" "__pycache__/" ".git/*" ".git/" ".env"

# =============================================================================
# DEPLOY TO PRODUCTION
# =============================================================================
echo ""
echo "=== Deploying to production ==="
./deploy.sh
