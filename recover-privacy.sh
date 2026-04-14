#!/bin/bash
# recover-privacy.sh — one-shot recovery for the privacy.html deploy.
#
# Situation this fixes:
#   - Local commit ffeafbf5 ("privacy: add privacy.html and link from all page footers")
#     is on main but never reached origin/main.
#   - Two other local commits (d2e9a18d, f2d086a4) are redundant digest entries
#     already present on origin/main via main.py's GitHub-API push path.
#   - The straight bu.sh rebase conflicts on docs/feed.xml because of the redundancy,
#     and bu.sh's auto-resolution has a --no-edit bug that stalls non-interactively.
#
# Strategy: reset main to origin/main (drops the two redundant digests — still
# recoverable from reflog for ~90 days), cherry-pick ffeafbf5, push.
#
# Non-interactive. Safety gates:
#   - Redundancy guard (aborts if digest entries not already on origin/main)
#   - Cherry-pick aborts cleanly on conflict
#   - Reflog preserves ffeafbf5 for ~90 days regardless
#
# Usage: ./recover-privacy.sh > readthis.txt 2>&1

set -euo pipefail

PRIVACY_COMMIT="ffeafbf5"

echo "=== recover-privacy.sh — $(date) ==="
echo

# ---------------------------------------------------------------------------
# Precondition: must be in the JTFNews repo root
# ---------------------------------------------------------------------------
if [ ! -f "bu.sh" ] || [ ! -d "docs" ] || [ ! -d ".git" ]; then
    echo "ERROR: run from the JTFNews repo root (expected bu.sh, docs/, .git/ here)."
    exit 1
fi

# ---------------------------------------------------------------------------
# Abort any in-progress rebase so we start from a clean slate
# ---------------------------------------------------------------------------
if [ -d ".git/rebase-apply" ] || [ -d ".git/rebase-merge" ]; then
    echo "Detected in-progress rebase. Aborting it."
    git rebase --abort || true
    echo
fi

# Refuse to run with uncommitted changes to TRACKED files (untracked is fine).
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: working tree has uncommitted changes to tracked files."
    echo "Commit or stash them first, then re-run this script."
    git status --short
    exit 1
fi

# ---------------------------------------------------------------------------
# Fetch and sanity-check
# ---------------------------------------------------------------------------
echo "Fetching origin..."
git fetch origin
echo

echo "Current state:"
echo "  local main:   $(git rev-parse main)"
echo "  origin/main:  $(git rev-parse origin/main)"
echo "  target pick:  $(git rev-parse $PRIVACY_COMMIT 2>/dev/null || echo MISSING)"
echo

# Verify the privacy commit is still reachable.
if ! git cat-file -e "${PRIVACY_COMMIT}^{commit}" 2>/dev/null; then
    echo "ERROR: commit $PRIVACY_COMMIT is not reachable. Check 'git reflog' for its SHA."
    exit 1
fi

echo "Privacy commit summary:"
git log --oneline -1 "$PRIVACY_COMMIT"
echo
echo "Files in that commit:"
git show --stat --oneline "$PRIVACY_COMMIT" | tail -n +2
echo

# ---------------------------------------------------------------------------
# Redundancy guard: confirm the two digests being dropped are already on origin.
# If either is missing, we'd be deleting real work — abort.
# ---------------------------------------------------------------------------
echo "Verifying digest commits d2e9a18d (04-11) and f2d086a4 (04-12) are redundant..."
MISSING=""
for GUID in "digest-2026-04-11" "digest-2026-04-12"; do
    # Inline check: pipe git show directly into grep. Capturing 78KB into a bash
    # variable and re-echoing was flaky under `set -euo pipefail`.
    if git show origin/main:docs/feed.xml 2>/dev/null | grep -q "$GUID"; then
        echo "  found on origin/main: $GUID"
    else
        MISSING="$MISSING $GUID"
    fi
done
if [ -n "$MISSING" ]; then
    echo "ERROR: origin/main is missing:$MISSING"
    echo "Refusing to reset — those local digest commits would be lost."
    echo "Escalate to Claude for a different recovery path."
    exit 1
fi
echo "OK — both digest entries already on origin/main. Local digest commits are safe to drop."
echo

# ---------------------------------------------------------------------------
# Reset local main to origin/main. Drops redundant d2e9a18d and f2d086a4.
# ffeafbf5 remains reachable via reflog for ~90 days.
# ---------------------------------------------------------------------------
echo "Running: git checkout main && git reset --hard origin/main"
git checkout main
git reset --hard origin/main
echo

# ---------------------------------------------------------------------------
# Cherry-pick the privacy commit
# ---------------------------------------------------------------------------
echo "Cherry-picking $PRIVACY_COMMIT..."
if ! git cherry-pick "$PRIVACY_COMMIT"; then
    echo
    echo "ERROR: cherry-pick hit conflicts. Aborting it to leave main clean."
    git cherry-pick --abort || true
    echo "Conflicting files were:"
    git diff --name-only --diff-filter=U 2>/dev/null || true
    echo "Do not auto-resolve. Escalate to Claude."
    exit 1
fi
echo
echo "Cherry-pick succeeded. New log:"
git log --oneline -3
echo

# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------
echo "Running: git push origin main"
git push origin main
echo

# ---------------------------------------------------------------------------
# Verify live (may take up to ~60s for GitHub Pages rebuild)
# ---------------------------------------------------------------------------
echo "Waiting 15s for GitHub Pages to start rebuilding..."
sleep 15
echo
echo "Probing https://jtfnews.org/privacy.html ..."
STATUS="000"
for i in 1 2 3 4 5 6; do
    STATUS=$(curl -sI -o /dev/null -w "%{http_code}" https://jtfnews.org/privacy.html || echo "000")
    echo "  attempt $i: HTTP $STATUS"
    if [ "$STATUS" = "200" ]; then
        echo
        echo "SUCCESS — privacy.html is live."
        break
    fi
    sleep 10
done

if [ "$STATUS" != "200" ]; then
    echo
    echo "NOTE: still not 200 after ~75s. GitHub Pages may still be rebuilding."
    echo "Re-check manually in a minute: curl -sI https://jtfnews.org/privacy.html"
fi

echo
echo "=== Done. ==="
