# Fix Contradiction Correction System

**Date:** 2026-03-01
**Status:** Approved

## Problem

`detect_correction_needed()` formats story IDs as `[ID]` for Claude's prompt. Claude returns the ID with brackets. `issue_correction()` compares the bracketed ID against the raw ID in stories.json. They never match, so corrections are logged but never applied to stories.

Evidence: corrections.json shows 4 corrections detected, but stories.json still has those stories as "published".

## Changes

### 1. Normalize story_id in `issue_correction()` and `issue_retraction()`
Strip `[` and `]` from `story_id` before matching: `story_id = story_id.strip("[]")`

### 2. Add verification logging
Log WARNING if story_id not found in stories.json after correction attempt.

### 3. Add post-correction verification in `process_cycle()`
After calling `issue_correction()`, verify the story status actually changed.

### 4. Clean story_id before storing in corrections.json
Strip brackets before writing to corrections log.

### 5. Manual fix for story 001
Update stories.json to mark 2026-03-01-001 as corrected.
