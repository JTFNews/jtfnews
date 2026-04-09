# YouTube Description: Full Fact List with Corrections Propagation

**Date:** 2026-04-09
**Phase:** B — Implementation Design
**Depends on:** White paper v1.4 (committed as `d60b2a56`)
**Next phase:** C — Implementation via `superpowers:writing-plans`

---

## Context

Today's YouTube Daily Digest uploads ship with a generic boilerplate description (`main.py:5136-5139`). The podcast RSS feed (`main.py:6170-6174`) already publishes the full fact list in its `content:encoded` field. Two sibling publishing destinations treat the same content asymmetrically. This spec closes the gap.

YouTube descriptions will contain the verified facts from each day's digest, formatted to visually match the video's lower-third overlay, with every fact carrying inline source attribution and compact accuracy|bias scores. Corrections will propagate into historical YouTube descriptions via the existing corrections pipeline, making the description a **living, truth-tracking surface** rather than frozen metadata.

This satisfies white paper v1.4's YouTube section: *"The verified facts rendered in the day's digest, listed with their verifying sources. No commentary. No opinion. When a fact is later corrected or retracted, the description of the affected video is updated to match the correction. A video cannot change after upload. A description can. When the facts change, the description changes too."*

Scope of backfill: <100 historical videos (well under YouTube API daily quota).

---

## The Description Format

### Structure

```
JTF News for {MONTH} {DAY}, {YEAR}.

{source1_name} {acc1}|{bias1} · {source2_name} {acc2}|{bias2}
{fact_1}

{source1_name} {acc1}|{bias1} · {source2_name} {acc2}|{bias2}
{fact_2}

... (N facts)

{optional truncation line}

CC-BY-SA.

JTF News: Two sources. No adjectives. Just facts.
```

### Real example (2026-04-08 digest)

```
JTF News for April 8, 2026.

France 24 4.3|8.5 · BBC News 5.1|7.2
At least 182 deaths reported across Lebanon following Israeli strikes.

PBS NewsHour 5.3|7.8 · CBC News 3.2|6.9
A woman received a 15-year prison sentence for selling ketamine that resulted in the death of actor Matthew Perry.

PBS NewsHour 5.3|7.8 · NPR 4.7|7.3
Oil prices fell below $95 per barrel and the Dow Jones Industrial Average increased approximately 1,100 points following an Iran ceasefire agreement.

CC-BY-SA.

JTF News: Two sources. No adjectives. Just facts.
```

### Per-fact shape (matches lower-third overlay in the video)

Each fact is **two lines**, separated from neighbors by **one blank line**:

1. **Source line**: `{source1} {acc}|{bias} · {source2} {acc}|{bias}` — followed by `(+N more)` if more than 2 sources verified the fact. Format mirrors `format_source_attribution()` at `main.py:3061` and `get_compact_scores()` at `main.py:2559`. The `·` separator is a middle dot (U+00B7). The `|` between accuracy and bias is a pipe.
2. **Fact line**: the plain fact text, no bullet marker.

**Do not include the `· {timeAgo}` part** that `web/lower-third.js:376-380` appends for the video — timeAgo is meaningless in a static description. The compact scores alone are enough to match the lower-third visually.

### Corrections — inline sub-bullet

When a fact is corrected (per white paper v1.4 YouTube section), the correction appears **immediately beneath the original fact** as a three-line indented sub-bullet:

```
{source1} {acc}|{bias} · {source2} {acc}|{bias}
{original_fact}
  CORRECTION {YYYY-MM-DD}
  {corrector_source1} {acc}|{bias} · {corrector_source2} {acc}|{bias}
  {corrected_fact}
```

- Indentation: two spaces on each correction line.
- Header: `CORRECTION {date}` where date is the correction issuance date (not the original fact date).
- Source line: the sources that verified the correction (may differ from sources that verified the original).
- Fact line: the corrected fact text (or a retraction notice if retracted — retractions use the existing `main.py:3423-3449` retraction text pattern).
- The original fact is **never silently deleted** — it stays visible above the correction, per white paper "never silently deleted" commitment.

### Footer

Exactly two lines, nothing else:

```
CC-BY-SA.

JTF News: Two sources. No adjectives. Just facts.
```

- No methodology link.
- No source ownership link.
- No corrections log link (corrections are inline, so a log link would be redundant).
- No `jtfnews.org` URL (the tagline implicitly points to JTF News; viewers who want more find it themselves).

### Truncation — 4,800-character safeguard

YouTube caps descriptions at 5,000 characters. If the built description exceeds **4,800 characters** (safety margin), truncate the fact list at a fact boundary (never mid-fact) and insert this line where the remaining facts would have been:

```
Complete stories to this date can be found at https://jtfnews.org/archive/{YYYY-MM-DD}.html
```

The truncation line goes **before** the `CC-BY-SA.` footer. The archive page at `jtfnews.org/archive/{date}.html` already exists (built by the archive pipeline) and contains the full day's record — which satisfies the methodology requirement that nothing is silently dropped.

### Header

The first line of every description:

```
JTF News for {MONTH} {DAY}, {YEAR}.
```

Where month is the full English name (January, February, ..., December), day is the numeric day without leading zero, year is the 4-digit year. Example: `JTF News for April 8, 2026.`

The same date-formatting function used by the podcast feed builder (`main.py:6158-6159`) can be reused: `datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")`.

---

## Architecture

One formatter function serves three callers: the live digest upload path, the first-run backfill, and the corrections propagation hook. When the white paper voice evolves, we change one function.

```
                   ┌────────────────────────────┐
                   │  build_youtube_description │
                   │  (date, facts_with_sources)│
                   └──────────────┬─────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
      upload_to_youtube()   backfill_youtube_    correction
      (live path,           descriptions()        propagation
      main.py:5112)         (one-shot CLI)        hook
```

### Components to build

All new code lives in `main.py` unless otherwise noted. No new files, no new dependencies — everything uses existing libraries (`googleapiclient`, `gzip`, stdlib).

| # | Component | Purpose |
|---|---|---|
| 1 | `build_youtube_description(date, facts)` | Assembles the final description string per the format above. Single source of truth for YouTube description voice. |
| 2 | `parse_daily_archive(date)` | Reads `docs/archive/YYYY/YYYY-MM-DD.txt.gz` and returns a list of `(fact, sources_with_scores)` tuples. |
| 3 | `get_compact_scores_for_source_name(name)` | Helper that resolves `source_name → source_id → get_compact_scores()` via `CONFIG["sources"]`. Handles the archive/config mismatch (archive stores names, config keys by id). |
| 4 | `load_digest_video_ids_from_feed()` | Parses `docs/feed.xml` for `<item jtf:type="digest">` entries and returns `{date: video_id}`. |
| 5 | `update_youtube_description(video_id, description)` | Wraps `youtube.videos().update()`. Handles 404/403/401 failure modes. |
| 6 | `backfill_youtube_descriptions()` | One-shot orchestrator, CLI-invoked. Idempotent via marker file. |
| 7 | Corrections propagation hook | Integrated into the existing correction code path around `main.py:3423-3449`. |
| 8 | Live path modification | `upload_to_youtube()` at `main.py:5112` calls `build_youtube_description()` instead of the hardcoded literal at lines 5136-5139. |

---

## Component Specifications

### 1. `build_youtube_description(date, facts)`

**Signature:**
```python
def build_youtube_description(date: str, facts: list[dict]) -> str:
    """Build the YouTube description for a daily digest.

    Args:
        date: YYYY-MM-DD string for the digest date.
        facts: List of dicts, each shaped as:
            {
                "fact": str,                    # plain fact text
                "sources": [                    # 2+ verifying sources
                    {"name": "France 24", "acc": "4.3", "bias": "8.5"},
                    {"name": "BBC News",  "acc": "5.1", "bias": "7.2"},
                ],
                "extra_source_count": int,      # 0 if exactly 2 sources
                "correction": {                 # optional; None or missing if uncorrected
                    "correction_date": "2026-04-12",
                    "corrected_fact": str,
                    "sources": [...],           # same shape as top-level sources
                    "extra_source_count": int,
                } | None,
            }

    Returns:
        Full description string, ready to send to YouTube API.
        Guaranteed <= 5000 chars (truncates to ~4800 if over, with pointer line).
    """
```

**Algorithm:**
1. Format date to display form: `datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")`.
2. Build header: `f"JTF News for {display_date}."`
3. Build each fact block as two lines (source line + fact line), plus optional 3-line correction sub-bullet.
4. Accumulate blocks, separated by `\n\n`.
5. Build footer: `"CC-BY-SA.\n\nJTF News: Two sources. No adjectives. Just facts."`
6. Assemble: `header + "\n\n" + facts_blob + "\n\n" + footer`
7. If total length > 4800:
   - Rebuild with facts truncated at the largest N such that `header + truncated_facts + truncation_line + footer <= 4800`.
   - Insert truncation line before footer: `f"Complete stories to this date can be found at https://jtfnews.org/archive/{date}.html"`.
8. Return the final string.

**Edge cases:**
- If `facts` is empty: return a minimal description `"JTF News for {display_date}.\n\nNo verified facts for this date.\n\nCC-BY-SA.\n\nJTF News: Two sources. No adjectives. Just facts."`
- If a fact has fewer than 2 sources listed (shouldn't happen, but defensive): render with whatever sources are present; log a warning.
- If `extra_source_count > 0`: append `(+{N} more)` to the source line.

### 2. `parse_daily_archive(date)`

**Signature:**
```python
def parse_daily_archive(date: str) -> list[dict]:
    """Parse the daily archive gz file for a given date.

    Args:
        date: YYYY-MM-DD string.

    Returns:
        List of fact dicts in the shape expected by build_youtube_description().
        Empty list if archive file does not exist.
    """
```

**Implementation notes:**
- Path: `BASE_DIR / "docs" / "archive" / date[:4] / f"{date}.txt.gz"`
- Format (per `append_daily_log()` at `main.py:3097`): each line is `timestamp|source_names|source_scores|source_urls|audio_name|fact`, where:
  - `source_names` is comma-separated like `"France 24,BBC News"` or `"France 24,BBC News (+2 more)"`
  - `source_scores` is comma-separated display ratings like `"4.3 (209/489),5.1 (181/355)"` — the accuracy numbers with evidence counts in parens
  - `source_urls` is comma-separated URLs
- The parser must:
  - Read the gzipped file
  - Skip header lines beginning with `#`
  - Split each non-header line on `|` (exactly 6 fields)
  - Extract the fact text (field 6)
  - Extract source names (split on `,`, handle `(+N more)` suffix to recover `extra_source_count`)
  - Extract accuracy scores from `source_scores` (split on `,`, parse the first whitespace-delimited token per score to strip `(209/489)` evidence counts → yields `"4.3"`)
  - Look up bias scores via `get_compact_scores_for_source_name()`
  - Assemble the dict shape documented in `build_youtube_description()` docstring
- Return the full ordered list (chronological, earliest fact first, matching the archive file order).

**Why we need this helper at all:** The live path has `sources` dicts already in memory. The backfill and corrections-propagation paths have to reconstruct fact/source pairs from the archive file. This function is the bridge.

### 3. `get_compact_scores_for_source_name(name)`

**Signature:**
```python
def get_compact_scores_for_source_name(source_name: str) -> tuple[str, str]:
    """Resolve a source name to (accuracy, bias) compact scores.

    Strips trailing " (+N more)" noise if present.
    Looks up source_id by matching name against CONFIG["sources"][*]["name"].
    Falls back to ("?", "?") if not found (logs warning).

    Returns:
        (accuracy_str, bias_str) — e.g., ("4.3", "8.5") or ("9.8*", "9.5")
    """
```

**Why needed:** The archive file stores `source_names` but not `source_ids`. The compact-score computation (`get_compact_scores()` at `main.py:2559`) takes a `source_id`. This helper bridges that gap via a name lookup in `CONFIG["sources"]`.

**Edge cases:**
- Journalist source IDs (prefix `journalist:`) — delegate to the same lookup as institutional sources; their data lives in `journalists.json` but the lookup pattern is uniform per `CLAUDE.md` journalist system section.
- Unknown source names (renamed sources, typos, sources removed from config) — log warning, return `("?", "?")`. The description will show `France 24 ?|?` which is ugly but honest. Backfill for old dates may hit this if a source was renamed — the user can manually clean up after running the backfill.

### 4. `load_digest_video_ids_from_feed()`

**Signature:**
```python
def load_digest_video_ids_from_feed() -> dict[str, str]:
    """Parse docs/feed.xml for digest items and return {date: video_id}.

    Returns:
        Dict mapping YYYY-MM-DD → YouTube video ID, one entry per digest item.
        Empty dict if feed.xml missing or has no digest items.
    """
```

**Implementation notes:**
- Parse `docs/feed.xml` with `xml.etree.ElementTree`.
- Find all `<item>` elements whose `jtf:type` attribute equals `"digest"` (namespace: `https://jtfnews.com/rss`).
- For each: extract `<guid>digest-{date}</guid>` → `date`; extract `<link>https://youtube.com/watch?v={video_id}</link>` → `video_id`.
- Reuse the XML navigation pattern from `add_digest_to_feed()` at `main.py:3804` — same namespace, same element shapes.

**Why feed.xml and not `digest_status.json`:** `digest_status.json` only holds the latest run's state (per `load_digest_status()` at `main.py:6233`). The feed.xml has a full historical list, one entry per successfully-uploaded digest.

### 5. `update_youtube_description(video_id, description)`

**Signature:**
```python
@retry_with_backoff(max_retries=3, base_delay=30.0)
def update_youtube_description(video_id: str, description: str) -> bool:
    """Update the description of a YouTube video.

    Args:
        video_id: YouTube video ID.
        description: New description string (must be <= 5000 chars).

    Returns:
        True on success, False on handled failure (404 skip, 403 quota, etc).

    Raises:
        On auth failure (401), re-raises so backfill orchestrator can stop.
    """
```

**Implementation notes:**
- Reuse the `get_authenticated_youtube_service()` helper at `main.py:5076` (approx).
- Call `youtube.videos().update(part="snippet", body={"id": video_id, "snippet": {"description": description, ...preserve title/tags/categoryId from the existing video}}).execute()`.
- **Critical:** `videos.update` REPLACES the entire snippet, so the call must first fetch the existing snippet (`videos.list(id=video_id, part="snippet")`), modify only the `description` field, and send the full snippet back. Otherwise title and tags are wiped.
- Failure handling:
  - 404 → video was deleted; log, return False, skip marker-file update.
  - 403 quota exceeded → re-raise, backfill orchestrator handles with sleep or abort.
  - 401 unauthorized → re-raise, needs auth refresh (not per-video failure).
  - Transient network errors → let `@retry_with_backoff` handle (3 tries, 30s base delay).

**Decorator:** `@retry_with_backoff` is already used by `upload_to_youtube()` at `main.py:5111` — reuse the same pattern.

### 6. `backfill_youtube_descriptions()`

**Signature:**
```python
def backfill_youtube_descriptions(dry_run: bool = False) -> dict:
    """Update YouTube descriptions for all historical digest videos.

    Args:
        dry_run: If True, build descriptions and log them but don't call the API.

    Returns:
        Summary dict: {"updated": N, "skipped": N, "failed": N, "dry_run": bool}
    """
```

**Implementation:**
1. Load idempotency marker: `DATA_DIR / "youtube_description_backfill.json"` — shape `{video_id: {"updated_at": iso_timestamp, "date": "YYYY-MM-DD"}}`. Default empty dict if file missing.
2. Call `load_digest_video_ids_from_feed()` → full `{date: video_id}` map.
3. For each `(date, video_id)`:
   - If `video_id` already in marker file: log "already updated", increment `skipped` counter, continue.
   - Call `parse_daily_archive(date)` → `facts`. If empty, log warning, increment `skipped`, continue.
   - Call `build_youtube_description(date, facts)` → `description`.
   - If `dry_run`: write `description` to `DATA_DIR / "backfill_dry_run" / f"{date}.txt"` for inspection, increment `updated`, continue (no API call, no marker update).
   - Else: call `update_youtube_description(video_id, description)`.
     - On success: append to marker file with current ISO timestamp, save marker file (flush after each update — resumable mid-run), increment `updated`.
     - On handled failure (404): log, increment `failed`, continue. Do NOT add to marker file (allows retry later if video is restored).
     - On unhandled exception (401, quota): log summary so far, re-raise, exit orchestrator.
4. Log final summary.
5. Return summary dict.

**CLI wiring:** Add a new `--backfill-youtube-descriptions` flag to `main.py`'s argparse setup. Parallel flag `--backfill-youtube-descriptions-dry-run` for dry-run mode. Invoke `backfill_youtube_descriptions(dry_run=...)` and exit after completion.

**Quota math:** Each `videos.update` costs ~50 quota units; each `videos.list` costs ~1. Default daily quota is 10,000. ~100 videos × 51 units ≈ 5,100 units — half the daily quota, plenty of headroom.

**Idempotency:** If the run is interrupted (power, quota, auth), re-running is safe — the marker file tracks what's already been done, and the loop resumes where it left off.

### 7. Corrections Propagation Hook

**Location:** Extend the existing correction code path around `main.py:3423-3449` (where `description` is built for correction entries in `add_correction_to_feed()` or equivalent).

**Trigger:** When a correction is applied to a past fact, after the existing code updates `feed.xml`, `stories.json`, and the archive.

**Action:**
1. Determine the affected `date` — the correction already knows the original fact's publication date (required by the existing pipeline).
2. Call `parse_daily_archive(date)` → post-correction facts (the archive should already be updated by the correction pipeline before this hook fires; if not, this hook needs to run AFTER that update).
3. Call `build_youtube_description(date, facts)` → new description.
4. Call `load_digest_video_ids_from_feed()` → resolve `date` to `video_id`. If the date predates any digest upload, log and skip (no video to update).
5. Call `update_youtube_description(video_id, description)`.
6. Log the update into the existing corrections log file.

**Why this hook matters:** This is the **integrity payoff** — the commitment in white paper v1.4 that "the description is part of the record, and the record stays truthful." Without this hook, corrections live on the archive and RSS feed but not on the YouTube video that viewers actually see.

### 8. Live Path Modification — `upload_to_youtube()`

**Location:** `main.py:5112`.

**Change:**
- Modify signature to accept a `facts: list[dict]` argument (callers will pass the same list that `update_podcast_feeds()` at `main.py:6137` already receives).
- At line 5136-5139, replace the hardcoded description literal with:
  ```python
  description = build_youtube_description(date, facts)
  ```
- Update the single call site (around `main.py:6010` in the digest finalization code) to pass the facts list.

---

## Data Flow — Live Digest Upload

```
daily_digest()
  └─> collect_facts_for_date(date)  [existing]
        └─> returns facts list (dicts with fact + sources)
  └─> build_youtube_description(date, facts)  [NEW]
        └─> returns description string
  └─> upload_to_youtube(video_path, date, facts)  [MODIFIED]
        └─> uses description from above
        └─> returns video_id
  └─> update_podcast_feeds(...)  [existing, unchanged]
```

## Data Flow — Backfill (one-shot)

```
main.py --backfill-youtube-descriptions
  └─> backfill_youtube_descriptions()  [NEW]
        └─> load_digest_video_ids_from_feed()  [NEW]
              └─> returns {date: video_id}
        └─> for each (date, video_id):
              └─> parse_daily_archive(date)  [NEW]
                    └─> returns facts list
              └─> build_youtube_description(date, facts)  [NEW, shared with live]
              └─> update_youtube_description(video_id, description)  [NEW]
        └─> writes data/youtube_description_backfill.json (marker)
```

## Data Flow — Corrections Propagation

```
correction_issued(original_story_id, corrected_fact, ...)  [existing entry point]
  └─> existing: update stories.json, feed.xml, archive
  └─> NEW HOOK:
        └─> determine date from original_story_id
        └─> parse_daily_archive(date)
        └─> build_youtube_description(date, facts)
        └─> load_digest_video_ids_from_feed()
        └─> update_youtube_description(video_id, description)
        └─> log to corrections log
```

---

## Failure Modes

| Failure | Detection | Handling |
|---|---|---|
| Archive file missing for a date | `parse_daily_archive()` returns empty | Log warning, skip this date in backfill/corrections |
| Video deleted on YouTube | `videos.list` returns 404 | Log, mark as skipped in backfill (do NOT add to marker — allows retry if restored) |
| Video made private | `videos.list` returns 403 on specific video | Same as deleted — log, skip |
| Fact list empty (no stories that day) | `len(facts) == 0` | Use fallback minimal description (see Edge Cases in §1) |
| Source name not in CONFIG | `get_compact_scores_for_source_name()` returns `("?", "?")` | Render with `?` markers, log warning. Safe degradation. |
| Description exceeds 5000 chars | Length check in `build_youtube_description()` | Truncate to ~4800 at fact boundary, insert archive link pointer |
| Quota exhausted mid-backfill | `update_youtube_description()` raises on 403 quota | Backfill orchestrator logs progress so far, re-raises, exits. User re-runs the next day — marker file makes it resumable. |
| Auth token expired | `update_youtube_description()` raises on 401 | Re-raise, let existing token-refresh logic kick in on next run |
| feed.xml malformed | `load_digest_video_ids_from_feed()` raises XML parse error | Log, return empty dict, backfill aborts cleanly |
| Correction fires but no matching video_id | `load_digest_video_ids_from_feed()` dict lookup misses | Log, skip YouTube update (not a blocker for the correction itself; the archive and RSS corrections still happen) |

---

## Verification Plan

**Critical note:** Per memory file `feedback_split_dev_environment.md`, Python cannot be executed from the M4 side. All verification steps that involve running Python must be handed to the user to run on their Jump Desktop session to the Intel Mac.

### Step 1 — Archive parser unit check

Build `parse_daily_archive()` first. Verify against a known archive file before writing anything else.

**Command to hand user:**
```
cd /Users/larryseyer/JTFNews
python -c "from main import parse_daily_archive; import json; print(json.dumps(parse_daily_archive('2026-04-08'), indent=2))"
```

**Expected:** Three fact dicts matching the 2026-04-08 archive content shown in the example above. Each dict has `fact`, `sources` (list of 2), `extra_source_count` (int, probably 0 for 2026-04-08), and no `correction` key (or `correction: None`).

### Step 2 — Formatter unit check

Build `build_youtube_description()`. Test against parsed archive data.

**Command to hand user:**
```
cd /Users/larryseyer/JTFNews
python -c "from main import build_youtube_description, parse_daily_archive; print(build_youtube_description('2026-04-08', parse_daily_archive('2026-04-08')))"
```

**Expected:** The full description string matching the example in §1 above. Character count should be well under 5000.

### Step 3 — Video ID loader unit check

Build `load_digest_video_ids_from_feed()`. Verify against current `feed.xml`.

**Command to hand user:**
```
cd /Users/larryseyer/JTFNews
python -c "from main import load_digest_video_ids_from_feed; import json; print(json.dumps(load_digest_video_ids_from_feed(), indent=2))"
```

**Expected:** A dict with ~9 entries (matching the 9 `digest-{date}` entries currently in feed.xml, 2026-03-31 through 2026-04-08 per Phase A investigation). Each value should be an 11-char YouTube video ID.

### Step 4 — Backfill dry run

Run the backfill in dry-run mode. Inspect generated descriptions without calling the API.

**Command to hand user:**
```
cd /Users/larryseyer/JTFNews
python main.py --backfill-youtube-descriptions-dry-run
ls -la data/backfill_dry_run/
cat "data/backfill_dry_run/2026-04-08.txt"
```

**Expected:** Output directory contains one `.txt` file per digest date. Spot-check 3-5 files for correctness. No API calls made. No marker file written.

### Step 5 — Backfill live run

Once dry run looks correct, run the real backfill.

**Command to hand user:**
```
cd /Users/larryseyer/JTFNews
python main.py --backfill-youtube-descriptions
cat data/youtube_description_backfill.json
```

**Expected:** Summary log shows "updated: N, skipped: 0, failed: 0" (or documented failures). Marker file contains one entry per updated video.

**Manual verification:** Open 2-3 YouTube videos in a browser, confirm descriptions are the new format.

### Step 6 — Live path test

On the next daily digest cycle, run `./digest.sh` and verify the new upload has the full fact description.

**Command to hand user:**
```
cd /Users/larryseyer/JTFNews
./digest.sh
# Wait for completion, then check YouTube manually
```

**Expected:** Newly uploaded video has the full per-fact format. Marker file has a new entry for the new video_id.

### Step 7 — Corrections propagation test

Simulate a correction to a past fact using the existing correction tooling. Verify the YouTube description of the affected video is updated.

**Command to hand user:**
```
cd /Users/larryseyer/JTFNews
# Use existing correction issuance path — exact command depends on existing correction pipeline interface
# After correction: check YouTube video description for the affected date
```

**Expected:** The YouTube description for the affected date shows the correction as an inline sub-bullet beneath the original fact.

---

## Critical Files

| Path | Role | Lines |
|---|---|---|
| `main.py` | All new functions + modifications | New: ~250 lines; modified: ~10 lines |
| `main.py:5112` (`upload_to_youtube`) | Modify signature, replace hardcoded description | — |
| `main.py:5136-5139` | Current hardcoded description — to replace | — |
| `main.py:3061` (`format_source_attribution`) | Podcast feed precedent — read for pattern | — |
| `main.py:2559` (`get_compact_scores`) | Existing scorer — reuse via wrapper | — |
| `main.py:3097` (`append_daily_log`) | Archive write format — parser mirrors this | — |
| `main.py:3423-3449` (correction pipeline) | Hook location for corrections propagation | — |
| `main.py:3804` (`add_digest_to_feed`) | XML parsing pattern for feed.xml | — |
| `main.py:6137` (`update_podcast_feeds`) | Similar caller pattern — live path reference | — |
| `main.py:6170-6174` (podcast content_encoded) | Sibling formatter precedent | — |
| `docs/archive/YYYY/*.txt.gz` | Per-date facts source (READ) | — |
| `docs/feed.xml` | Historical date→video_id lookup (READ) | — |
| `data/youtube_description_backfill.json` | Idempotency marker file (NEW) | — |
| `web/lower-third.js:376-381` | Lower-third format reference — for voice consistency | — |
| `CONFIG["sources"]` (loaded from `config.json`) | Bias score lookup | — |
| `documentation/WhitePaper Ver 1.4 CURRENT.md` | Authoritative methodology text for the YouTube section | — |

---

## Reuse Notes

- **`format_source_attribution()` at `main.py:3061`** is the nearest sibling — same `name {acc}|{bias}` shape. But it uses `" · "` as the separator and is designed for the lower-third. Reuse its `get_compact_scores()` dependency, but build a new wrapper for YouTube since the description context is subtly different (no `timeAgo`, may differ on truncation logic).
- **`@retry_with_backoff`** decorator — already wraps `upload_to_youtube()` at `main.py:5111`. Apply identically to `update_youtube_description()`.
- **`get_authenticated_youtube_service()`** — reuse the existing auth helper, no new auth logic.
- **XML namespace registration** pattern from `add_digest_to_feed()` at `main.py:3815-3817` — `JTF_NS = "https://jtfnews.com/rss"`. Reuse this in `load_digest_video_ids_from_feed()`.
- **Date formatting** — reuse the `main.py:6158-6159` pattern: `datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")`.
- **Journalist source IDs** (prefix `journalist:`) — the compact-score lookup should route to journalist data per the same pattern used by `are_sources_unrelated()` and similar functions (CLAUDE.md journalist section).

---

## Explicit Non-Goals

- **Not fixing bu.sh's rebase-conflict handling.** That script has a known bug where empty rebase commits cause it to exit without popping stash. The Phase A work exposed this. Out of scope for this spec; worth a separate fix later.
- **Not extending podcast descriptions to include compact scores.** The podcast currently shows facts without per-fact sources. After this spec ships, YouTube descriptions will be more detailed than podcast descriptions. That asymmetry is worth addressing eventually but is a separate design.
- **Not adding structured data to descriptions** (schema.org, Open Graph, etc.). Plain text only, matching the white paper's "plain text with their verifying sources" language.
- **Not filtering which facts appear in the description.** If a fact is in the daily digest, it appears in the description. No curation, no editorial selection.
- **Not adding interactive elements** (timestamps linking to video chapters, clickable source links). YouTube doesn't render those reliably, and they add editorial layer beyond "state what happened."

---

## Ready for Phase C

This spec is complete and ready to feed into `superpowers:writing-plans` for the implementation plan. The plan should:

1. Build the components in the order listed (§1 formatter → §2 archive parser → §3 score lookup → §4 video ID loader → §5 API wrapper → §6 backfill orchestrator → §7 corrections hook → §8 live path mod).
2. Hand verification commands to the user per §Verification Plan (Python execution is Intel-Mac-only).
3. Land each component as a separate commit via `./bu.sh` on the Intel Mac so each step is independently verifiable and revertable.
4. Only enable the live path modification (§8) AFTER the backfill dry run has been validated by the user.
