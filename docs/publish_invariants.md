# JTF News Publish Invariants

**Status (2026-04-14):** All published files are written atomically. APP-021 (multi-file atomic publish) and APP-022 (tests) remain as deferred Phase 3.

Every file JTF News publishes to `jtfnews.org` passes through one of two
pipelines:

1. **Local write** — `main.py` writes the file to disk on the Intel Mac.
2. **Remote push** — `push_to_ghpages()` reads the local file and PUTs it
   to GitHub via the Contents API; GitHub Pages + Fastly serve it.

A Truth-preserving pipeline must guarantee that no consumer ever observes
an internally inconsistent state at either stage. This document records
which invariants are enforced today and which are still open.

## Enforced today (Phase 1 — APP-019)

### Invariant 1: Atomic local writes for published JSON + podcast.xml

Files that are written via `atomic_write_text(path, content)` cannot be
observed mid-write by another process. `atomic_write_text` writes a `.tmp`
sibling and calls `os.replace`, which is a single atomic `rename(2)`
syscall on POSIX. Readers see either the old content or the new content,
never a truncated or partial file.

**Protected call sites (8):**

| Line | File | Write site |
|---|---|---|
| ~3227 | `stories.json` | `stories_file` in `update_story_status` |
| ~4364 | `alexa.json` | `alexa_file` in Alexa feed builder |
| ~4567 | `corrections.json` | `CORRECTIONS_FILE` in `save_corrections` |
| ~6946 | `docs/podcast.xml` | `feed_path` after episode insert |
| ~7241 | `monitor.json` | `monitor_file` (active-cycle writer) |
| ~7312 | `monitor.json` | `monitor_file` (sleeping-heartbeat writer) |
| ~7599 | `archive/index.json` | `index_file` in `update_archive_index` |
| ~8404 | `journalists.json` | `leaderboard_file` in leaderboard updater |

Plus a bonus fix: `clean_duplicate_namespaces` uses `atomic_write_text`
for its post-processed XML content, so `feed.xml`'s namespace-cleanup
step is atomic on top of the now-atomic upstream write.

**Why this matters (Truth-first rationale):** `push_to_ghpages()` reads
each file to base64-encode it. Before APP-019, a reader (another cron
job, or even a shell tail) could race the writer and see a half-written
JSON. Worse, `push_to_ghpages` itself, if invoked concurrently from
another trigger, would upload a corrupt file to GitHub and consumers on
`jtfnews.org` would see a broken feed until the next publish cycle.

### Invariant 2: Atomic XML writes for feed.xml

`feed.xml` is written via `atomic_tree_write(path, tree)`, which
serializes the tree to a `BytesIO` buffer and then calls
`atomic_write_bytes(path, data)` — same rename(2) guarantee as
`atomic_write_text`.

**Protected call sites (6):** every `tree.write(f, ...)` targeting
`feed_file` has been converted. `atomic_tree_write` is the single
chokepoint; grep for `open(feed_file` should return zero matches.

The subsequent `clean_duplicate_namespaces` cleanup is also atomic
(Invariant 1), so both stages of the publish now observe the same
rename-or-no-rename semantics.

### Invariant 4 (APP-020): Publish gate — `<item>` implies audio-downloadable

An `<enclosure>` URL in `podcast.xml` is a promise to every podcast
client that the audio file resolves to a 200 response. Archive.org
takes minutes to propagate a fresh upload; if `update_podcast_feeds`
runs before propagation completes, the feed advertises a URL that
404s until the next publish cycle overwrites it.

**Enforcement:** `wait_for_archive_reachability(url, timeout=900)` is
called between `upload_to_archive_org` and `update_podcast_feeds` in
the daily-digest path. It HEAD-polls the audio URL every 15 seconds,
returns when it sees a 200, and raises `TimeoutError` after 15 minutes
so the caller can defer the publish and alert.

**Call site (1):** `main.py` daily digest pipeline, between the
`archive_result = upload_to_archive_org(...)` and
`update_podcast_feeds(...)` lines.

### Invariant 3: Atomic gzip writes for all published .gz files

`atomic_gzip_write(path, data)` compresses into a `BytesIO` buffer
with `gzip.GzipFile(fileobj=buf, mode='wb')` and then calls
`atomic_write_bytes` — same rename(2) guarantee as
`atomic_write_text`.

**Protected call sites (4):**

| Line | File | Write site |
|---|---|---|
| ~7582 | `docs/archive/YYYY/{date}.txt.gz` | `archive_daily_log` (midnight sweep) |
| ~7646 | `docs/archive/YYYY/{date}.txt.gz` | `archive_specific_date` (recovery helper) |
| ~7757 | `docs/archive/search-index.json.gz` | `update_search_index` |
| ~8999 | `docs/archive/YYYY/{date}.txt.gz` | corrections-propagation rewrite |

Every `gzip.open(path, 'w*')` write site in `main.py` has been
converted. Read sites (`gzip.open(path, 'rt')`) are unchanged — they
are not atomicity-relevant.

## Deferred (Phase 3)

| ID | Invariant | Fix | Why deferred |
|---|---|---|---|
| APP-021 | Multi-file publishes atomic to the consumer | Rewrite `push_to_ghpages` to use the Git Data API (single commit for all changed files) | The consumer-visible gap between sequential per-file PUTs is milliseconds — vastly smaller than the Fastly edge cache TTL (600s). Large rewrite for marginal benefit. |
| APP-022 | Tests for Invariants 1–4 + APP-020 | `tests/test_atomic_writes.py`, `tests/test_publish_gate.py` | JTF methodology is "run forever, verify via live operation"; no existing test infrastructure. Adding one isolated test file without a runner is worse than not having it. |

## Internal (unpublished) writes — deliberately NOT atomic

The following writes remain non-atomic by design. They are local state,
never published, and atomic semantics would add cost with no Truth
benefit:

- `_fact_extraction_cache`, `_headline_hashes`, `_seen_hashes` — internal
  dedup state
- Daily log files in `logs/` — append-only, read only after rotation
- TTS audio files — content-hashed filenames, never overwritten
- OAuth credential cache — written once, read many
- Queue files — guarded by separate locking

If you add a new published file, it MUST go through one of
`atomic_write_text`, `atomic_write_bytes`, `atomic_tree_write`, or
`atomic_gzip_write` and be documented here.

## Scope rule for future contributors

> A file is "published" iff it can be served from `jtfnews.org` via
> GitHub Pages + Fastly. Every published file, at every point in its
> write path, must be replaceable by an atomic rename.

That rule is load-bearing. The April-8-vs-April-13 Digest bug (see
`docs/server_patches/APP-001-podcast-xml-conflict-markers.md`) showed
what happens when it's violated: consumers of `podcast.xml` saw a file
containing literal `<<<<<<<` conflict markers, because the file was
committed and pushed non-atomically with no pre-commit validation.
Atomic writes alone don't prevent that specific failure (that's APP-021
and human review), but they close one of the three doors through which
corrupt content can reach consumers.

## Commit hygiene

All edits to the files that implement these invariants MUST be committed
via `./bu.sh "<message>"`. Never `git commit` directly. `bu.sh` enforces
the exclude list for runtime files (`docs/podcast.xml` etc.) that are
managed through the GitHub API path instead of git.
