# Design: Remove Live Stream from JTF News

**Date:** 2026-03-16
**Status:** Approved

## Context

Due to lack of funding and public interest, JTF News is terminating the live YouTube stream. The Daily Digest, screensaver, podcast, submission system, and all other services continue. OBS remains running for Daily Digest recording only. Live streaming may return when funding allows.

## Scope

Remove all active live stream references from documentation and the public website. No code changes needed in main.py or shell scripts. Preserve streaming configuration in SPECIFICATION.md (marked as suspended) for potential future reactivation.

## Changes

### Public Website (docs/)

**docs/index.html**
- Line 18, 25, 36: Change "24/7 automated news reporting" to "Automated news reporting" in meta descriptions
- Line 91: Change "24/7 verified news from 22 independent sources." to "Verified news from 22 independent sources."
- Lines 130-132: Change "Watch Live" card to "Daily Digest" card pointing to YouTube channel, remove "24/7 on YouTube."

**docs/how-it-works.html**
- Line 476: Change "Streamed — 24/7 live on YouTube" to "Published — Daily digest on YouTube"
- Line 508: Change "Watch Live" button to "Watch Daily Digest" (keep link to @JTFNewsLive)

**docs/support.html**
- Line 18: Change "a 24/7 fact-only news service" to "a fact-only news service" in meta description
- Lines 25, 36: "See our live costs" is about financial transparency (live costs dashboard), not live streaming — keep as-is
- Lines 304-309: Stream health JS — keep as-is (Option A decision)

**docs/screensaver-setup.html**
- Line 382: Change "YouTube Live" link text to "YouTube" (keep URL to @JTFNewsLive)

### Documentation

**CLAUDE.md** — specific lines to update:
- Line 4: "Automated 24/7 news stream" → "Automated daily news service"
- Line 238: "OBS Does Heavy Lifting — Let OBS handle media/streaming" → clarify OBS is for recording
- Lines 285, 289: "Development, OBS streaming, and production" → "Development, OBS recording, and production"
- Line 333: "OBS for streaming to YouTube" → "OBS for recording Daily Digest video"

**documentation/SPECIFICATION.md**
- Line 43: "Streams 24/7 via OBS to YouTube" → update to reflect Daily Digest model
- Line 71: "Streaming to YouTube → Built-in RTMP" → mark as suspended
- Section 13 (lines 1264-1337): Add "[SUSPENDED]" header note; keep content intact for future reactivation
- Lines 1420, 1473, 1481: Stream offline alerts — keep as-is (heartbeat monitors main.py, not OBS stream)
- Lines 1616, 1627: Pre-launch checklist "Start Streaming" — mark as suspended alongside Section 13

**documentation/WhitePaper Ver 1.3 CURRENT.md**
- Line 29: "Streams 24/7 to YouTube with calm visuals and TTS" → "Publishes daily digest to YouTube with calm visuals and TTS"
- Line 208: "Title: JTF News – Live." → "Title: JTF News – Daily Digest."
- Lines 19, 57, 221: "global stream" refers to the news feed concept, not YouTube live stream — keep as-is

### Code — No Changes

- `main.py` — OBS WebSocket calls are already recording-only (StartRecording/StopRecording for Daily Digest). No streaming start/stop calls exist. Heartbeat monitoring stays as-is. Podcast description template has no live stream references.
- Shell scripts — No streaming commands to remove.
- `web/lower-third.html` — Keep as-is for potential future use.
- `web/monitor.html`, `docs/monitor.html`, monitor.js — Keep stream health display as-is.

### What Does NOT Change

- Daily Digest pipeline (OBS recording, YouTube upload, Archive.org, podcast)
- OBS remains running for Daily Digest recording
- Heartbeat/stream health monitoring
- Lower-third overlay
- Screensaver, RSS feed, journalist submissions, public feedback
- Rumble upload — deferred to a separate future task

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Heartbeat monitoring | Keep as-is (Option A) | Still monitors main.py health; streaming may return |
| Lower-third overlay | Keep (Option B) | May be needed for Daily Digest or future streaming |
| Live stream mentions on website | Remove silently (Option A) | Site should reflect current offerings |
| SPEC Section 13 (Stream Settings) | Mark suspended (Option B) | Easy to reactivate without digging through git |
| Rumble uploads | Defer (Option B) | Separate task, keep this change focused |
| "24/7" language | Remove from all public pages | No longer accurate; replace with current offering |

## Verification

After implementation, grep `docs/` for `Watch Live`, `24/7`, `live stream`, `livestream` and confirm only intentionally preserved references remain (e.g., stream_health in monitor, "live costs" in support page).
