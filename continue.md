# Continue: Regional Filtering Implementation

**Last updated:** 2026-02-13
**Status:** Design complete, implementation plan ready

---

## What Was Done

1. **Brainstormed** regional filtering approaches with multiple options
2. **Chose architecture:** Single `stories.json` with location tags, client-side filtering via `?region=` URL parameter
3. **Wrote design doc:** `docs/plans/2026-02-13-regional-filtering-design.md`
4. **Wrote implementation plan:** `docs/plans/2026-02-13-regional-filtering-implementation.md`

---

## Key Design Decisions

- **Filter at display time, not write time** — No duplicate data directories
- **Claude extracts location** during fact processing (with keyword fallback)
- **Persistent audio files** — `audio/{id}.wav` instead of overwriting `current.wav`
- **Playback stays in JavaScript** — lower-third.js handles region filtering
- **Zero cost increase** — Same API calls, just additional fields

---

## Next Steps

Execute the implementation plan. There are 8 tasks:

1. Add location extraction to Claude prompt (`main.py`)
2. Add keyword fallback for location detection (`main.py`)
3. Update stories.json structure with location (`main.py`)
4. Pass location through publishing pipeline (`main.py`)
5. Add region filtering to lower-third.js (`web/lower-third.js`)
6. Add regions configuration to config.json
7. Update screensaver to support region filtering
8. Validation and testing

---

## How to Continue

Start a new Claude Code session and say:

```
Read docs/plans/2026-02-13-regional-filtering-implementation.md and execute the plan using the executing-plans skill.
```

Or for subagent-driven execution:

```
Read docs/plans/2026-02-13-regional-filtering-implementation.md and use subagent-driven-development to implement it.
```

---

## Files to Reference

| File | Purpose |
|------|---------|
| `docs/plans/2026-02-13-regional-filtering-design.md` | Full design rationale |
| `docs/plans/2026-02-13-regional-filtering-implementation.md` | Step-by-step implementation plan |
| `main.py:473-539` | Claude prompt to modify |
| `web/lower-third.js` | JS to add region filtering |
| `config.json` | Add regions section |

---

## Quick Context

JTF News is an automated fact-only news stream. This feature adds geographic tagging so you can run regional streams (JTF News US, JTF News California) by just changing a URL parameter in the OBS browser source.

Phase 1 (this plan): Tag existing global news by location, filter at display.
Phase 2 (future): Add local news sources, lower thresholds.
