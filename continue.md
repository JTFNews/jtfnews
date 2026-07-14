# continue.md — session handoff for JTFNews reliability work

**Last updated:** 2026-05-19 ~02:25 CDT
**User:** Larry Seyer (larryseyer@gmail.com)
**Branch:** `feature/jtf-protocol` (NOT main — bu.sh pushes to current branch)
**Status:** JTFNews running cleanly after three reliability fixes shipped today.

## Why this file exists

User asked me to leave a handoff in case my session crashes. They keep the terminal open in case JTFNews crashes again and they need to call on me. The work below is the context any successor session needs.

## The original problem

JTFNews backend has chronic uptime issues — `data/uptime_stats.json` showed **24.2% availability for May 2026** before today's fixes. User had to quit-and-restart the terminal at least once a day. ACIM-daily-minute runs in a separate terminal from `/Users/larryseyer/acim-daily-minute` and is NOT affected — do NOT touch ACIM processes.

## DO NOT confuse the two processes

Both projects use `./start.sh` and run `main.py`. Always verify cwd before any destructive action:

```bash
lsof -p <PID> | grep cwd
```

- cwd `/Users/larryseyer/JTFNews` → JTFNews (this project)
- cwd `/Users/larryseyer/acim-daily-minute` → ACIM (leave alone)

I made this mistake once early in the session and the user corrected me. Don't repeat it.

## What we shipped today (all on feature/jtf-protocol, all via ./bu.sh)

In chronological order:

1. **`c30803da3`** — `fix: bound Claude API timeout to 60s and restore broken retry for extract_fact`
   - Added `get_anthropic_client()` helper that returns `anthropic.Anthropic(timeout=60.0)`. Replaced all 11 `anthropic.Anthropic()` constructions. SDK default was 600s (10 min) — way too long for a long-running service.
   - Refactored `extract_fact` into `_call_claude_extract_fact` (decorated, retryable) + `extract_fact` (catches final failure, degrades to SKIP). Before: an inner `except Exception` swallowed `APITimeoutError` before `@retry_with_backoff` could see it — retries were dead code for ~14 months.

2. **`d6192d76d`** — `fix: SIGALRM watchdog around per-source fetch to prevent multi-hour hangs (CBC incident 2026-05-18)`
   - Added per-source SIGALRM watchdog (30s). Triggered by an actual incident where CBC RSS via Akamai hung the process for 9+ hours. `requests.get(..., timeout=15)` doesn't always work on macOS — SSL_read can stall in a way the Python timer cannot reach.

3. **`8a9df0e3f`** — `fix: retry transient Anthropic errors during startup validation (529 Overloaded should not block start)`
   - `validate_services()` was treating a 529 Overloaded as fatal and exiting. Now retries 5 times with backoff (5s/10s/20s/40s/60s — worst case ~2.3 min). Auth errors still fail fast.

4. **`487bc2e11`** — `fix: nestable SIGALRM watchdog wraps process_cycle (10-min ceiling, BaseException-rooted to escape inner except blocks)`
   - Added a `watchdog(seconds, label)` context manager (nestable) and a `CYCLE_WATCHDOG_SECONDS = 600` ceiling around `process_cycle()`. Refactored the per-source watchdog to use the same context manager. `WatchdogTimeout` inherits from `BaseException` (not `Exception`) so it propagates past every `except Exception` block in the cycle — this is critical. `OuterWatchdogTimeout` is a subclass for the case where a nested inner sees the outer's deadline fire first.

All four commits include corresponding `## Known Bug Patterns` entries in CLAUDE.md.

## Current process state

As of last check, JTFNews is running. PIDs change frequently — always re-verify with:

```bash
ps -ef | grep main.py | grep -v grep
```

Then `lsof -p <pid> | grep cwd` to confirm it's the JTFNews one. ACIM has been running continuously since 2026-05-17 6:25PM as PID 5874 — don't touch it.

## Tiered reliability plan (user-approved)

Today completed tier 1 (cycle-level watchdog). User asked me to plan #2 next; then changed mind: "Let's not do that yet."

- **#1 (done):** Cycle watchdog + per-source watchdog + Claude timeout + startup retry
- **#2 (DEFERRED at user's request):** launchd supervisor. Would replace the terminal-based `./start.sh` invocation with `~/Library/LaunchAgents/org.jtfnews.plist` running with `KeepAlive=true`. Process crash → automatic restart. Tradeoff: user loses live terminal output, has to `tail -f jtf.log`.
- **#3 (DEFERRED):** External heartbeat watcher. Separate script + launchd job that polls `data/heartbeat.txt` every 2 min and `kill -9` + restart if stale beyond 10 min. Catches "alive but useless" — the one failure mode in-process watchdogs cannot detect.

If user re-engages on #2, design the plist first and confirm with them before writing files. Don't surprise them with a behavior change.

## Key files / call sites a successor will want

- `main.py` — single ~9400-line file, the whole backend
- `main.py:153` — `retry_with_backoff` decorator definition
- `main.py:191` — `get_anthropic_client()` helper (timeout=60s)
- `main.py:~870-920` — `extract_fact` / `_call_claude_extract_fact` (post-refactor)
- `main.py:~1280` — `watchdog` context manager, `WatchdogTimeout`, `OuterWatchdogTimeout`, `fetch_headlines_with_watchdog`, `scrape_all_sources`, `CYCLE_WATCHDOG_SECONDS = 600`, `SOURCE_FETCH_WATCHDOG_SECONDS = 30`
- `main.py:~440-475` — `validate_services` with the 5-attempt startup retry
- `main.py:~8700` — main loop (`while True`) with `with watchdog(CYCLE_WATCHDOG_SECONDS, "cycle"): process_cycle()` and the `except WatchdogTimeout` handler
- `CLAUDE.md` lines 74–146 — the four `## Known Bug Patterns` entries we added today
- `bu.sh` — commit/push/backup wrapper. ALWAYS use this. Never raw `git commit`. Pushes to current branch (not hardcoded main).
- `data/uptime_stats.json` — track availability trend post-fixes
- `~/.claude/projects/-Users-larryseyer-JTFNews/memory/MEMORY.md` — auto-memory index, includes `feedback_autonomy.md` (user prefers autonomy, minimize check-ins) and runtime-files-not-staged note.

## Known gotchas (already in CLAUDE.md but worth surfacing)

1. **runtime files are managed by main.py via GitHub API.** Never `git add` `feed.xml`, `stories.json`, `monitor.json`, `podcast.xml`, `archive/index.json`, `corrections.json`, `journalists.json`, `alexa.json`, `data/`, `jtf.log`. `bu.sh` handles this.
2. **WatchdogTimeout : BaseException.** Do NOT change this base class. Many `except Exception` blocks would otherwise swallow it and defeat the cycle watchdog.
3. **Nested watchdogs:** any new per-operation watchdog must `except OuterWatchdogTimeout: raise` before `except WatchdogTimeout: <degrade locally>`.
4. **All Claude calls must go through `get_anthropic_client()`** — never construct `anthropic.Anthropic()` directly. Future call sites must inherit the bounded timeout.
5. **bu.sh enforces single-commit-per-iteration.** Don't split into multiple commits.
6. **No emoji anywhere** — code, commits, docs. JTF methodology rejects editorialization.

## What was being discussed when this file was written

User explicitly deferred #2 and #3. They are keeping the JTFNews terminal open as live observation. If it crashes again, the question is whether the four shipped fixes were sufficient or whether a previously-unknown hang path remains. Investigate before adding more layers.

If user reports a NEW hang:
1. `ps -ef | grep main.py | grep -v grep` — get PID
2. `lsof -p <PID> | grep cwd` — confirm it's JTFNews
3. `tail -100 jtf.log` — see last successful operation
4. `lsof -p <PID> | grep -vE "REG|DIR|CHR"` — open sockets/network state
5. `sample <PID> 2 -mayDie` — C-level stack (Python-level not available — py-spy is not installed)
6. `cat data/uptime_stats.json` — current availability trend
7. Don't kill until you've gathered evidence and the user confirms.
