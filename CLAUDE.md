# Ralph Agent Instructions

You are an autonomous professional coding agent working on JTF News — an automated daily news service that reports only verified facts from two or more unrelated sources. This section is the Ralph contract: the per-iteration loop reads it before every story. The rest of this CLAUDE.md (starting at "# CLAUDE.md - JTF News" below) is the project spec and provides context.

## HARD CONSTRAINT: NO PYTHON EXECUTION

**You cannot run Python. Ever. No exceptions.**

This includes every form of Python invocation:
- `python main.py`, `python3 main.py`
- `./start.sh`, `./digest.sh` (both activate venv and run main.py)
- `python -c "..."`, `python3 -c "..."`
- `python -m py_compile`, `python -m anything`
- `pip install`, `pip list`, `pip anything`
- `pytest`, any test runner
- Any script that activates `venv/bin/activate` and then runs Python

**Why:** JTF News's Python scripts have real-world side effects that must stay supervised — Claude API calls (costs money per run), YouTube uploads (public, irreversible), archive.org uploads (public, permanent), SMS alerts via Twilio, ElevenLabs TTS generation (costs money, writes files), GitHub Pages pushes. Running these unsupervised in a Ralph loop is unacceptable. Only the user runs Python, via a supervised Jump Desktop session after the sprint completes.

**Your acceptance-criteria verification is STATIC only:**
- `grep -n 'def function_name' main.py` — function existence
- `grep -c 'pattern' file` — occurrence counts
- `test -f path` — file existence
- `bash -n script.sh` — shell syntax check (safe, no execution)
- `jq '.stories | length' prd.json` — JSON structure checks
- `git log --oneline -1 main.py` — commit history
- `git diff --stat HEAD~1 HEAD` — change summary
- Reading file content and reasoning about it

**Forbidden verification:**
- `python -c "from main import ..."` — NO
- `python main.py --any-flag` — NO
- `./start.sh`, `./digest.sh` — NO
- `python -m py_compile main.py` — NO

If a story's acceptance criterion appears to require Python execution, rewrite the criterion as a static check and note the change in `progress.txt`. Never silently skip verification; never "just try" running Python to see if it works.

## Your Task Loop

1. **Read `prd.json`.** Verify you're on the correct branch (`branchName` field — expect `main` for JTF News).
2. **Read `progress.txt`.** Start with the `## Codebase Patterns` section at the top — it contains persistent architectural facts about `main.py`, the archive format, feed.xml structure, and the existing function layout. Then scan recent per-story entries below the first `---` separator for cross-story context.
3. **Pick the highest-priority story** where `passes: false` (lowest numeric `priority`). If all stories have `passes: true`, you're in the verification phase — emit `<promise>COMPLETE</promise>` and stop.
4. **Implement that single story** by editing only the files listed in `filesToModify`. If you need to touch a file not in the list, STOP and add a blocking note to `progress.txt` explaining why, then move to the next story.
5. **Verify the acceptance criteria statically.** Run the grep/file/git commands specified by the criteria. Do not proceed until every criterion passes.
6. **Update `prd.json`**: set the story's `passes` to `true`.
7. **Append a per-story entry to `progress.txt`** below the most recent separator:
    ```
    ## [YYYY-MM-DD] - STORY-ID
    - What was done (bullets)
    - **Learnings for future iterations:**
      - Any non-obvious fact or gotcha
    ```
8. **If the story revealed a reusable gotcha, API quirk, or non-obvious pattern, update this CLAUDE.md's `## Known Bug Patterns` section** (create the section below the Ralph Agent Instructions if it doesn't exist). Include a `**Symptom:**` line and concrete WRONG/CORRECT examples. **Err strongly on the side of adding rather than skipping** — progress.txt learnings are per-iteration scratch, Bug Patterns here are cross-sprint memory that actually prevents the next sprint from repeating the same mistake.
9. **Commit ALL tracked changes atomically in ONE commit via `./bu.sh`**:
    ```
    ./bu.sh "PHASEC-NN: story title"
    ```
    `./bu.sh` handles `git add -A`, `git commit`, `git push origin main`, and the Downloads backup zip. Do NOT use raw `git commit` — it bypasses the backup and push. The commit captures the source edits and any CLAUDE.md updates.

    **About prd.json and progress.txt:** both files are listed in `.gitignore` under "Ralph runtime files" — they are working-tree state, not git-tracked content. The `git add -A` inside `./bu.sh` skips them automatically. That is by design: prd.json tracks the sprint's pass-flag state in-place, and progress.txt is a living log that gets archived to `bash/archive/DATE-branch/` by `bash/ralph.sh` at sprint end. The per-story commit message prefix (`PHASEC-NN:`) is the link between a git commit and the story — not a tracked file. You still MUST update prd.json and progress.txt in the working tree every iteration (steps 6 and 7), because the next iteration reads their current working-tree state to find the next story. Don't skip steps 6/7 just because they're not committed.

**Why the commit is step 9, not earlier:** every TRACKED output of the iteration (code + CLAUDE.md Bug Patterns) must land in one atomic commit so the git log has exactly one commit per story. The untracked state transitions (prd.json pass flag, progress.txt entry) happen concurrently but live only in the working tree. If you commit the code at step 4 and then edit CLAUDE.md at step 8, the Bug Pattern is post-commit working-tree drift that the next iteration inherits but never captures in that story's commit. Step 9 is the atomic commit fence for tracked content only.

## Verification Phase

When the Ralph loop detects that all stories have `passes: true`, it will launch a verification iteration with a special prompt. Your response in that phase is a single line:

```
<promise>COMPLETE</promise>
```

Nothing else. JTF News has no automated test suite by design (the methodology is "run forever, verify via live operation") and you cannot run Python anyway. Manual verification is documented in `progress.txt` under "Post-sprint manual verification (user only)" and is the user's responsibility to execute via Jump Desktop after you've finished.

Do NOT attempt to run `./scripts/test-all.sh`, `./start.sh`, or any Python script during verification. The test-all.sh script is a no-op placeholder that just echoes a message and exits 0.

## Commit Tool: `./bu.sh` — NEVER raw `git commit`

JTF News uses `./bu.sh "message"` for every commit. It:
1. Stages all changes (`git add -A`)
2. Commits with the message
3. Pushes to `origin/main`
4. Creates a timestamped backup zip in the user's Downloads folder

Raw `git commit` bypasses the backup and the push, leaving the next iteration with inconsistent state. Always use `./bu.sh "message"` — for every commit, no exceptions.

## JTF News Project Rules You Must Respect

When implementing stories, honor the project's non-negotiable constraints (full detail in the project spec below):

- **Two-source minimum** for any factual claim in generated content.
- **No editorializing** — no adjectives, no opinions, no interpretation, no emoji in code, docs, or commit messages.
- **Hash-based audio naming** — do not change the TTS file naming scheme.
- **Runtime files are pushed by `main.py` via the GitHub API**, not by hand. If your story touches code that writes `feed.xml`, `stories.json`, etc., understand that `push_to_ghpages()` is the push mechanism.
- **Do not change specs without asking.** If a story's requirements conflict with the JTF methodology or the project spec, STOP, add a blocking note to `progress.txt`, and move on. Never silently change a spec.

## Rules — Memorize

1. **No Python execution.** (See HARD CONSTRAINT above.)
2. **One story per commit.** Atomic commits via `./bu.sh` only.
3. **Static verification only.** No runtime checks.
4. **Update progress.txt AND CLAUDE.md Bug Patterns with every story.** See step 8 above.
5. **Only edit files in the story's filesToModify list.** Out-of-scope edits are blocking notes, not silent changes.
6. **No emoji** in commits, code, docs, or anywhere else. JTF methodology rejects editorializing; emoji is editorializing.
7. **No dead code** for code you're adding in this sprint. If you add a helper function, it must be called. If you change a signature, update every call site. Do NOT remove existing "legacy" code that wasn't in your story's scope — that's an unrelated cleanup.

---

# CLAUDE.md - JTF News

## Project Overview
JTF News (Just the Facts News) - Automated daily news service that reports only verified facts. No opinions, no adjectives, no interpretation.

---

# THE JTF METHODOLOGY

## Philosophy

**Two sources. Different owners. Strip the adjectives. State the facts. Stop.**

This is not journalism. It is data. The methodology belongs to no one. It serves everyone.

**Facts without opinion. Wherever they are needed.**

We do not interpret events.
We do not speculate.
We do not persuade.

We record.

---

## Core Principle

We do not editorialise. We state what happened, where, when, and—when known—how many. Nothing more.

Each item states:
- What occurred
- Where it occurred
- When it occurred
- Who was formally involved
- Quantifiable outcomes when available

---

## What Qualifies as News

A verifiable event, within the last 24 hours, that meets at least one criteria:
- Affects 500+ people
- Costs/invests $1M+ USD
- Changes a law or regulation
- Redraws a border
- Involves death or violent crime
- Major scientific/technological achievement
- Humanitarian milestone
- Official statement by head of state/government
- Major economic indicator (GDP, unemployment, inflation)
- International agreement or diplomatic action
- Major natural disaster, pandemic, or public health emergency

Nothing less. Nothing more.

These thresholds define the global stream. Other communities define relevance for themselves.

---

## Verification Standard

Two unrelated sources minimum. Unrelated means different owners, different investors. Where cross-ownership makes full independence difficult to confirm, no common majority shareholder is the minimum threshold.

Where ownership independence cannot be reasonably confirmed, publication is deferred.

---

## Content Rules

### Data Processing
AI rewrites. Strips adjectives. Keeps facts. If it can't be proven, it vanishes.

The system:
- Removes descriptive and evaluative language
- Removes speculation and predictions
- Standardizes titles and naming conventions
- Extracts quantifiable facts
- Excludes unsupported claims

**The system does not add facts not present in source material.**

### Official Titles
People are addressed by their official titles and names. President [surname]. Senator [surname]. Representative [surname]. Judge [surname] of the [district or circuit]. Never bare last names. Titles are facts. Omitting them is editorial. For judges, the court is also a fact.

**Media-invented nicknames are editorialization, not titles.** A journalistic shorthand like "border czar" is not an official government position—it carries implicit judgment. We use official titles only. The title a person holds is a fact. The nickname a reporter invents is opinion.

### Data Sourcing
Public headlines and metadata from open websites. No login walls. No paid content. No APIs. No copyrighted imagery.

---

## AI Transparency & Bias Mitigation

The AI rewriting step is not neutral by default. Language models carry inherited biases from training data. We mitigate this through:

- Public pseudocode and processing logic on GitHub
- Periodic human audits of output against source material
- Community reporting of detected bias or distortion
- Logging of all editorial decisions the algorithm makes (what was stripped, what was kept)

**No algorithm is perfect. Ours is visible.**

---

## Source Ownership Disclosure

For each story, the top three owners of each cited source are listed. Percentages. No spin. This lets the audience see who funds the information they are receiving.

Live source scores: accuracy, bias, speed, consensus. Numbers only. No labels.

### Ownership Data Maintenance
Ownership structures change. Acquisitions happen. Shareholders shift. We review and verify all source ownership data quarterly. Updates are logged publicly on GitHub.

**Stale data is dishonest data. We do not let it drift.**

---

## Voice & Visuals

Calm female voice, northern English. Slow, neutral background images—clouds, fields, water. **Never the event. Never the news.**

Images rotate every 50 seconds. Never match the story. **They breathe.**

Voice only. No music. No breath. When it stops, quiet.

---

## Updates & Corrections

### Update Cadence
Every 30 minutes. Breaking news within 5, but no urgency.

### Corrections & Retractions
When a fact passes the two-source test but is later proven false:

- A correction is issued within the next update cycle
- The original item is marked as corrected in the archive, **never silently deleted**
- If the error is fundamental, a full retraction is issued with explanation
- Corrections are given the same prominence as the original item
- A running corrections log is maintained publicly on GitHub

**We do not bury mistakes. We name them.**

---

## Social Media Policy

We post once per platform. We do not reply. No engagement. No likes. **Corrections are the sole exception**—corrections are posted with the same reach as the original.

---

## Ethics & Data Retention

We do not store raw data longer than 7 days.
Daily summaries are archived on GitHub.
**Nothing hidden. Nothing sold. Just the record.**

No paywalls. No bots. Respect robots.txt. No logs.

---

## Transparency & Governance

- Independent nonprofit oversight
- **No dividends. We own nothing.**
- Public documentation of methodology
- **Pseudocode on GitHub. Anyone can read. No one can change.**
- Version-controlled changes
- Public corrections log
- No advertising or sale of user data

---

## Limits of the Model

JTF News does not provide:
- Opinion
- Analysis
- Forecasts
- Policy advocacy

Disagreements between sources are reported as disagreements of record. The system mitigates bias through **transparency and defined rules, not claims of perfect neutrality.**

---

## Mission

**To provide a structured factual reference layer beneath public discourse.**

When narrative is removed, the record remains.

Because the world needs a place where facts stand alone.

---

## The Loop

24 hours. Midnight GMT. Each story once. Then back.

---

## Community Channels

The global stream is our first application, not our only one.

Communities deserve fact-based reporting:
- Local news, free from partisan spin
- Sports scores, free from hot takes
- School boards, free from drama

Each channel serves a community. Each follows the methodology. Each stands alone.

**If a community needs facts, the methodology is theirs.**

---

## Universal Principles

Across all channels, always:
- Two or more unrelated sources minimum
- AI strips all editorialization
- No engagement. No replies. No likes.
- Calm voice. Neutral visuals.
- No ads. No tracking. No profit.
- Public archives. Open methodology.

**We serve. We do not sell.**

---

# IMPLEMENTATION

## Current State
**Live and running** - Implementation complete with main.py (~2000 lines). SPECIFICATION.md is the design reference.

## Key Architecture Principles (from spec)
- **Simplicity = Stability** - Always choose the simplest solution; code must run forever
- **OBS Does Heavy Lifting** - Let OBS handle media/recording; we write minimal code (~500 lines total)
- **Silence is Default** - Don't speak unless facts are verified by 2+ unrelated sources
- **No Drama** - No emotional language, no "BREAKING" labels, just calm facts

## Key Files
- `docs/SPECIFICATION.md` - Complete technical spec (read this first for implementation)
- `documentation/WhitePaper Ver 1.4 CURRENT.md` - Project philosophy and methodology whitepaper
- `docs/ResilienceSystem.md` - 24/7 uptime resilience design (retry logic, alerts, degradation)
- `docs/implementation Ver 0.1.md` - Implementation notes
- `docs/mediasetup.md` - Media/OBS setup instructions

## Commands

### Running the Service
- `./start.sh` - Start the JTF News service (normal operation)
- `./start.sh --rebuild` - Recover stories.json from daily log (use if stories were accidentally cleared)
- `./start.sh --fresh` - Clear stories and start fresh (requires confirmation; use only when file format changes)
- `./digest.sh` - Manually run the daily digest (record, upload to YouTube, publish podcast)

**When to use each start.sh flag:**
| Situation | Command |
|-----------|---------|
| Normal startup | `./start.sh` |
| Accidentally ran --fresh | `./start.sh --rebuild` |
| Quarterly ownership audit | `python main.py --audit` |
| Apply pending audit (non-interactive) | `python main.py --apply-audit` |
| Regenerate audio for a date | `python main.py --regenerate-audio YYYY-MM-DD` |

### Quarterly Ownership Audit
On startup, main.py checks if the current quarter's ownership audit has been completed. If not:
1. Blocks startup
2. Uses Claude to research current ownership for all 22 sources
3. Presents any changes found
4. Requires confirmation before applying changes
5. Logs the audit to `data/ownership_audit.json`

The audit happens automatically on normal startup if needed, or can be run manually with `--audit`.

### IMPORTANT: Always Use bu.sh for Commits
Do NOT use raw `git commit` commands. Always use `./bu.sh "message"` which:
1. Stages all changes
2. Commits with your message
3. Pushes to origin (main branch)
4. Creates a timestamped backup zip in Downloads

## Single-Machine Architecture

**Everything runs on one machine.** Development, OBS recording, and production all happen at `/Users/larryseyer/JTFNews`. There is no separate deploy machine.

| Path | Purpose |
|------|---------|
| `/Users/larryseyer/JTFNews` | Everything: development, OBS recording, production |

## Git Workflow
- Single branch: `main`
- Website served from `/docs` folder on main branch
- Public site: https://jtfnews.org/
- GitHub org: JTFNews/jtfnews

### Automatic GitHub Updates
Runtime files (feed.xml, podcast.xml, stories.json, monitor.json, etc.) are pushed automatically by main.py via GitHub API. No manual git operations needed for website updates.

### Syncing Overlay Files (web/ → docs/)
When modifying overlay files that exist in BOTH locations, you MUST update BOTH:

| web/ (OBS local) | docs/ (public site) |
|------------------|---------------------|
| `web/screensaver.html` | `docs/screensaver.html` |
| `web/monitor.html` | `docs/monitor.html` |
| `web/lower-third.html` | (not on public site) |

**Path differences to fix when syncing:**
- `../media` → `./images`
- `../data/stories.json` → `./stories.json`
- `../data/monitor.json` → `./monitor.json`

**Files that exist ONLY in docs/:** index.html, how-it-works.html, whitepaper.html, screensaver-setup.html, feed.xml, podcast.xml

## Folder Structure
- `main.py` - Main application (~6500 lines with resilience system, daily digest, YouTube upload)
- `web/` - OBS browser source overlays (lower-third.html, background-slideshow.html, screensaver.html, monitor.html)
- `docs/` - Public website (GitHub Pages) - index.html, how-it-works, whitepaper, feed.xml, podcast.xml, stories.json
- `documentation/` - Project documentation (SPECIFICATION.md, WhitePaper Ver 1.4 CURRENT.md, plans/)
- `media/` - Background images organized by season (fall/, spring/, summer/, winter/)
- `data/` - Runtime data (stories.json, queue.json, api_usage, monitor.json) - NOT committed

## Tech Stack
- Python main script with resilience system (retry logic, alert throttling, graceful degradation)
- HTML/CSS/JS overlays for OBS browser source
- Claude AI (Haiku) for fact extraction/rewriting
- ElevenLabs TTS for audio generation (hash-based audio naming for sync integrity)
- ffmpeg/ffprobe for video silence trimming and validation
- YouTube Data API for daily digest uploads
- Archive.org (internetarchive library) for permanent podcast/video hosting
- Twilio for SMS alerts
- OBS for recording Daily Digest video (OBS WebSocket v4 for recording control)
- GitHub Pages for public website (how-it-works, whitepaper, operations dashboard)

## Journalist Submission System

Independent journalists can submit original reporting via `jtfnews.org/submit`. Submissions enter the same verification pipeline as automated sources.

### Key Principle
A journalist is a source. Sources follow the methodology. The methodology does not bend.

### How It Works
1. Journalist registers at `jtfnews.org/register` (GitHub OAuth, real name, financial disclosures)
2. Submits original reporting via web form at `jtfnews.org/submit`
3. Submission processed by same AI (extract_fact) — identical treatment
4. Enters queue awaiting independent corroboration (24-hour timeout)
5. Two-source rule: journalist + unrelated source = published
6. Financial independence check: no common majority funder between journalist and corroborating source

### Journalist Source IDs
Journalist source IDs use the prefix `journalist:` (e.g., `journalist:janedoe`). Functions that handle source IDs (are_sources_unrelated, get_learned_rating, record_verification_success, etc.) check for this prefix and route to journalist data.

### Data Files
| File | Purpose |
|------|---------|
| `data/journalists.json` | Journalist profiles, disclosures, scores |
| `data/submissions/` | Pending submission JSON files |
| `data/submissions/processed/` | Processed submissions (7-day retention) |
| `docs/journalists.json` | Public leaderboard data (pushed to GitHub Pages) |

### Quarterly Audit
Journalist financial disclosures are audited on the same quarterly schedule as institutional source ownership. Stale disclosures → journalist suspended until updated.

### Web Pages
| Page | Purpose |
|------|---------|
| `docs/register.html` | Journalist registration (GitHub OAuth) |
| `docs/submit.html` | Submission form for authenticated journalists |
| `docs/journalists.html` | Top 10 contributor leaderboard |

### OAuth Setup
GitHub OAuth proxy deployed as a Cloudflare Worker. See `documentation/oauth-setup.md` for deployment instructions. OAuth config placeholders in register.html and submit.html need real values:
- `GITHUB_CLIENT_ID` — from GitHub OAuth app
- `OAUTH_PROXY_URL` — Cloudflare Worker URL

## Feedback System

The public can anonymously report factual errors, bias concerns, and suggestions via `jtfnews.org/feedback.html`. No personal data collected. No email. No login.

### How It Works
1. User submits feedback via form (no account required)
2. Cloudflare Worker validates spam prevention (honeypot, time gate, rate limit, proof-of-work)
3. Worker pushes feedback JSON to `data/feedback/` via GitHub API
4. main.py fetches pending feedback each cycle
5. Claude AI triages: spam (discard), suggestion (log), bias (flag for audit), factual error (verify)
6. Factual errors verified by 2+ independent sources trigger auto-correction via existing pipeline

### Data Files
| File | Purpose |
|------|---------|
| `data/feedback/JTF-*.json` | Pending feedback (fetched from GitHub) |
| `data/feedback/processed/` | Processed feedback (7-day retention) |
| `data/feedback/suggestions.json` | Suggestions log (90-day retention) |
| `data/feedback/bias_reports.json` | Bias reports (until quarterly audit) |
| `data/feedback/stats.json` | Aggregate counts (30-day rolling) |

### Key Files
| File | Purpose |
|------|---------|
| `docs/feedback.html` | Public feedback form |
| `docs/feedback-worker.js` | Cloudflare Worker source |
| `documentation/feedback-worker-setup.md` | Worker deployment instructions |

## Constraints
- No APIs, no paywalls, respect robots.txt
- No ads, no tracking, no long-term raw data storage
- CC-BY-SA license on output
- **YouTube: Creative Commons license** (not Standard YouTube) - aligns with "methodology belongs to no one" philosophy
- **Archive.org: CC BY-SA 4.0** - permanent hosting for podcast audio and video
- Non-profit spirit
