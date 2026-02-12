#!/bin/bash
# deploy.sh - Copy only newer/changed files from development to deployment
#
# Development: /Users/larryseyer/JTFNews
# Deployment:  /Volumes/MacLive/Users/larryseyer/JTFNews

DEV_DIR="/Users/larryseyer/JTFNews"
DEPLOY_DIR="/Volumes/MacLive/Users/larryseyer/JTFNews"

# Check if deployment volume is mounted
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deployment folder not accessible: $DEPLOY_DIR"
    echo "Is the MacLive volume mounted?"
    exit 1
fi

echo "Deploying newer files from $DEV_DIR to $DEPLOY_DIR"
echo "==================================================="

# Use rsync to copy only newer files
# -a = archive mode (preserves permissions, timestamps, etc.)
# -v = verbose
# -u = skip files that are newer on the receiver
# --include/--exclude = control what gets copied

rsync -avu \
    --include='main.py' \
    --include='config.json' \
    --include='requirements.txt' \
    --include='web/***' \
    --include='media/***' \
    --exclude='data/' \
    --exclude='audio/' \
    --exclude='archive/' \
    --exclude='gh-pages-dist/' \
    --exclude='.git/' \
    --exclude='*.pyc' \
    --exclude='__pycache__/' \
    --exclude='.env' \
    --exclude='*.log' \
    --exclude='SPECIFICATION.md' \
    --exclude='README.md' \
    --exclude='CLAUDE.md' \
    --exclude='PromptStart.md' \
    --exclude='docs/' \
    --exclude='bu.sh' \
    --exclude='deploy.sh' \
    --exclude='*.zip' \
    "$DEV_DIR/" "$DEPLOY_DIR/"

echo ""
echo "Deployment complete. Only newer files were copied."
