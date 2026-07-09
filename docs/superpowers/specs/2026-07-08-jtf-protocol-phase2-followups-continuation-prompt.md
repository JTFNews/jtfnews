# JTF Protocol Phase 2 — Follow-Ups Continuation Prompt

Use this file when you're ready to address the four Important-tier follow-ups that surfaced during Phase 2 code review. Copy everything below the line into a fresh Claude Code session started inside `/Users/larryseyer/JTFNews/.worktrees/phase2`.

---

## Task

Address the four Important-tier follow-ups from Phase 2 code review of the JTF Protocol implementation. Each is a small, isolated fix with a clear scope and TDD plan. All four should land as separate atomic commits on the existing branch `feature/jtf-protocol-phase2`.

There is also a short list of Minor items at the end that you may address opportunistically if there's time; skip them if not.

## Live-site safety (read first)

The JTF News live site (iOS app, iOS widgets, `https://jtfnews.org/` served from `docs/`) is running from `/Users/larryseyer/JTFNews` on branch `feature/jtf-protocol`. **Nothing in this worktree touches `main.py` or the live branch.** All work stays in the `jtfprotocol/` package and `tests/`. Phase 5 is where integration into `main.py` happens; that is NOT this task.

A safety audit at the end of Phase 2 confirmed:
- `main.py` is byte-identical to Phase 1 HEAD.
- Zero `PHASE2-` commits leaked to `feature/jtf-protocol`.
- The live main.py process (PID 24959 at audit time) runs from `/Users/larryseyer/JTFNews`, not the worktree.
- No `docs/`, `web/`, `data/`, `config.json`, `start.sh`, `digest.sh`, `feedback.sh`, or `bu.sh` were modified.

If any of your fixes would risk violating any of the above, STOP and escalate to the user before proceeding.

## Worktree state at handoff

- **Branch:** `feature/jtf-protocol-phase2`
- **Working directory:** `/Users/larryseyer/JTFNews/.worktrees/phase2`
- **HEAD:** `40f122b19` — `PHASE2-01b: untrack venv symlink (hardcoded absolute path broke portability)`
- **Tip of Phase 2 tasks:** `be515ac1d` — `PHASE2-22: end-to-end smoke test - bootstrap, exchange, announce, pull`
- **Tests:** 128 passing, 0 failing (as of `40f122b19`)
- **venv:** symlink at `venv` → `/Users/larryseyer/JTFNews/venv` (working tree only, not tracked; recreate with `ln -s /Users/larryseyer/JTFNews/venv venv` if missing).

Verify state before starting:

```bash
cd /Users/larryseyer/JTFNews/.worktrees/phase2
git rev-parse --abbrev-ref HEAD                          # feature/jtf-protocol-phase2
git log -1 --format='%h %s'                              # 40f122b19 PHASE2-01b: untrack venv symlink ...
ls -l venv                                               # symlink to /Users/larryseyer/JTFNews/venv
venv/bin/pytest -q 2>&1 | tail -3                        # 128 passed
```

If any of those checks fails, STOP and surface the mismatch before doing any work.

## Repo conventions (memorize)

- **Commit tool: `./bu.sh "message"` — NEVER raw `git commit`.** `bu.sh` stages, commits, pushes to `origin/feature/jtf-protocol-phase2` (branch-aware), and writes a Downloads backup zip. Raw `git commit` bypasses the push and the backup.
- **No emoji anywhere** — code, tests, docstrings, commit messages. JTF methodology rejects editorializing; emoji is editorializing.
- **venv is at `venv/`** (symlink to the live venv). Use `venv/bin/pytest` and `venv/bin/pip`.
- **`from __future__ import annotations`** at top of every new `.py`. Parameterized annotations (`list[dict]`, `dict | None`, `set[str]`) work on Python 3.9 because of that import — do NOT downgrade them.
- **One follow-up per commit.** Commit messages prefixed `PHASE2-FOLLOWUP-NN:`. Atomic commits via `./bu.sh` only.
- **Strict TDD.** Write the failing test first, run it to see it fail, write the minimum implementation to pass, run to see it pass, commit.

## Authoritative sources (read as needed)

1. **Protocol spec (source of truth):** `documentation/Protocol Ver 1.0 CURRENT.md`. Sections most relevant to these follow-ups: "The Well-Known Endpoint" (lines 333–384), "Fallback Discovery" (lines 441–448), "Gossip" (lines 386–397), "Peer Validation" (lines 399–407), "Fact Propagation" (lines 409–427).

2. **Phase 2 plan (for design context):** `docs/superpowers/plans/2026-07-08-jtf-protocol-phase2-discovery-gossip.md`.

3. **Project rules:** `CLAUDE.md` at repo root. The Ralph agent section at the top is not applicable to this session (Ralph is a sprint-driver; you are executing a targeted follow-up sprint). The "Known Bug Patterns" section IS applicable — respect the noted gotchas about `except Exception` swallowing retries, unbounded network timeouts, and the atomic-write pattern.

4. **User auto-memory:** `/Users/larryseyer/.claude/projects/-Users-larryseyer-JTFNews/memory/MEMORY.md`. The user prefers autonomy over permission questions; minimize mid-task check-ins.

---

## Follow-Up 1 — Fix `exchange_peer_lists` self-confirmation bug

**Severity:** Important. This will bias trust scoring at Phase 3 wire-up if left in.

**File:** `jtfprotocol/gossip.py` — `exchange_peer_lists` function.

**Symptom:** When Alpha fetches Bravo's well-known and merges Bravo as a peer, Bravo is entered under `source_key_id = bravo_key_id`, meaning Bravo is treated as having vouched for itself. After one exchange, Bravo's local `confirmed_by` counter reads 1. Per the spec ("Peer Validation" lines 399–407), `confirmed_by` counts *distinct third parties*. A peer that only vouches for itself has `confirmed_by = 0`, not 1.

**Current code (`jtfprotocol/gossip.py`, roughly the `exchange_peer_lists` body):**

```python
source_key_id = doc.get("server", {}).get("public_key_id", "")
...
self_entry = {
    "domain": doc["server"]["domain"],
    "public_key_id": source_key_id,
    ...
}
batch = CycleBatch(store, source_key_id=source_key_id, clock=clock)
changed = batch.add_or_update(self_entry, asn=remote_asn_hint)
```

**Root cause:** `self_entry.public_key_id == source_key_id`, so when `PeerStore.add_or_update` records the confirmation, the peer's `_confirmations[pkid]` set gains its own key_id — a self-confirmation.

**Fix approach (recommended):** Use a sentinel `source_key_id` for the "we heard from them directly" case that is distinguishable from any real peer's `sha256:...` key_id. Suggested sentinel: `"local:direct-exchange"` (a fixed string that cannot collide with any real Ed25519 key fingerprint, which always starts with `"sha256:"`).

**Fix code:**

```python
DIRECT_EXCHANGE_SOURCE_ID = "local:direct-exchange"
"""Sentinel used as ``source_key_id`` when a server directly fetches
another server's well-known. Distinguished from any real peer key
fingerprint (which always starts with ``sha256:``). Prevents a remote
from appearing as a confirmation of itself and skewing ``confirmed_by``."""


def exchange_peer_lists(
    peer_domain: str,
    store: PeerStore,
    fetcher: Fetcher | None = None,
    clock: Clock | None = None,
    timeout: float = 10.0,
) -> bool:
    doc = fetch_and_verify_well_known(peer_domain, fetcher=fetcher, timeout=timeout)
    if doc is None:
        return False
    remote_key_id = doc.get("server", {}).get("public_key_id", "")
    if not remote_key_id:
        return False
    remote_asn_hint = int(doc.get("server", {}).get("asn", 0) or 0)
    self_entry = {
        "domain": doc["server"]["domain"],
        "public_key_id": remote_key_id,
        "channel": doc["server"].get("channel", "global"),
        "last_seen": (clock or _default_clock)().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trust_score": 0.0,
        "confirmed_by": 0,
    }
    # Direct exchange: we heard from the remote itself, not a third-party
    # confirmation. Use the sentinel so the remote does not appear to
    # confirm itself.
    self_batch = CycleBatch(store, source_key_id=DIRECT_EXCHANGE_SOURCE_ID, clock=clock)
    changed = self_batch.add_or_update(self_entry, asn=remote_asn_hint)
    # Third-party peers advertised by the remote get the remote's real
    # key_id as their source.
    peer_batch = CycleBatch(store, source_key_id=remote_key_id, clock=clock)
    for entry in doc.get("peers", []):
        try:
            if peer_batch.add_or_update(entry):
                changed = True
        except Exception:
            continue
    return changed
```

**Design note:** Two `CycleBatch` instances are used — one for the self-entry (sentinel source) and one for the third-party peers (remote's real key_id). This is intentional: the rate-limit and ASN-cap counters are per-batch, and the self-entry is a distinct concept from "peers advertised by the remote." An alternative would be a single batch with a per-call `source_key_id` override, but that requires changing the `CycleBatch` contract and is out of scope.

**Test plan (TDD):**

1. **Failing test 1 — direct exchange does not self-confirm.** Add to `tests/test_gossip.py`:

   ```python
   def test_exchange_peer_lists_does_not_self_confirm_remote(tmp_path):
       _priv, _pub, doc = _make_signed_wellknown(
           domain="remote.example",
           peers=[],
       )
       body = _json.dumps(doc).encode("utf-8")
       fetcher = FakeFetcher(get_map={
           "https://remote.example/.well-known/jtf.json": FakeResponse(200, body, {}),
       })
       clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
       store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
       gossip.exchange_peer_lists("remote.example", store=store, fetcher=fetcher, clock=clock)
       remote_key_id = doc["server"]["public_key_id"]
       remote_record = store.find(remote_key_id)
       assert remote_record is not None
       assert remote_record.confirmed_by == 0
   ```

2. **Failing test 2 — two independent direct exchanges still only bump confirmed_by via third parties.**

   ```python
   def test_direct_exchange_confirmed_by_only_grows_via_third_party_confirmations(tmp_path):
       # Alpha exchanges directly with Bravo -> Bravo.confirmed_by == 0.
       # A third server (Gamma) that lists Bravo in its peer list bumps it to 1.
       _bp, _bpub, bravo_wk = _make_signed_wellknown(domain="bravo.example", peers=[])
       bravo_key_id = bravo_wk["server"]["public_key_id"]
       _gp, _gpub, gamma_wk = _make_signed_wellknown(
           domain="gamma.example",
           peers=[{
               "domain": "bravo.example",
               "public_key_id": bravo_key_id,
               "channel": "global",
               "last_seen": "2026-07-01T00:00:00Z",
               "trust_score": 0.5,
               "confirmed_by": 0,
           }],
       )
       fetcher = FakeFetcher(get_map={
           "https://bravo.example/.well-known/jtf.json": FakeResponse(
               200, _json.dumps(bravo_wk).encode("utf-8"), {}
           ),
           "https://gamma.example/.well-known/jtf.json": FakeResponse(
               200, _json.dumps(gamma_wk).encode("utf-8"), {}
           ),
       })
       clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
       store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)

       gossip.exchange_peer_lists("bravo.example", store=store, fetcher=fetcher, clock=clock)
       assert store.find(bravo_key_id).confirmed_by == 0

       gossip.exchange_peer_lists("gamma.example", store=store, fetcher=fetcher, clock=clock)
       assert store.find(bravo_key_id).confirmed_by == 1
   ```

3. **Run and confirm fail** — should fail with `confirmed_by == 1` (test 1) and `confirmed_by == 2` (test 2, because both direct exchange and Gamma's confirmation currently increment).

4. **Apply the fix** (add `DIRECT_EXCHANGE_SOURCE_ID` constant and rework `exchange_peer_lists` as shown above).

5. **Confirm all previous tests still pass** — the Phase 2 smoke test in `tests/test_smoke_phase2.py` currently asserts `alpha_store.find(bravo_key_id) is not None` (just presence, not confirmed_by count), so it should still pass unchanged. Verify.

6. **Commit:** `./bu.sh "PHASE2-FOLLOWUP-01: exchange_peer_lists — sentinel source_key_id for direct exchange"`

---

## Follow-Up 2 — Add observability to DNS exception swallowing

**Severity:** Important. Silent `NoNameservers` in particular means the resolver itself is broken (not "no record present"), which an operator investigating a network partition would want to know about.

**File:** `jtfprotocol/seeds.py` — `DnspythonResolver.resolve_txt` and `resolve_srv`.

**Current code:**

```python
class DnspythonResolver:
    def resolve_txt(self, name: str) -> list[str]:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, "TXT")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        ...

    def resolve_srv(self, name: str) -> list[tuple[str, int, int, int]]:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, "SRV")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        ...
```

**Fix approach:** Log at `DEBUG` level (not INFO or WARNING — this is a normal outcome for `NXDOMAIN`/`NoAnswer`, and only an operator actively debugging should see it). Keep `[]` as the return value in all three exception cases so downstream behavior does not change.

**Fix code:**

```python
import logging

_log = logging.getLogger(__name__)

class DnspythonResolver:
    def resolve_txt(self, name: str) -> list[str]:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, "TXT")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer) as e:
            _log.debug("DNS TXT lookup for %s returned %s", name, type(e).__name__)
            return []
        except dns.resolver.NoNameservers as e:
            _log.debug("DNS TXT lookup for %s failed: NoNameservers (%s)", name, e)
            return []
        ...
```

(Same pattern for `resolve_srv`.)

**Rationale for splitting the except clauses:** `NoNameservers` is meaningfully different from `NXDOMAIN`/`NoAnswer` — the first means the resolver could not reach any nameserver, while the latter two mean the query completed and no record exists. Distinguishing them in the log message helps operators triage.

**Test plan (TDD):**

1. **Failing test — verify debug logging fires.** Add to `tests/test_seeds.py`:

   ```python
   import logging
   from unittest.mock import MagicMock, patch


   def test_dnspython_resolver_logs_nxdomain_at_debug():
       import dns.resolver
       resolver = seeds.DnspythonResolver()
       with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN):
           with patch.object(seeds._log, "debug") as mock_debug:
               result = resolver.resolve_txt("_jtf.nonexistent.example")
               assert result == []
               assert mock_debug.called
               assert "NXDOMAIN" in str(mock_debug.call_args)


   def test_dnspython_resolver_logs_nonameservers_distinctly():
       import dns.resolver
       resolver = seeds.DnspythonResolver()
       with patch("dns.resolver.resolve",
                  side_effect=dns.resolver.NoNameservers(request=MagicMock())):
           with patch.object(seeds._log, "debug") as mock_debug:
               result = resolver.resolve_srv("_jtf._tcp.example.com")
               assert result == []
               assert mock_debug.called
               assert "NoNameservers" in str(mock_debug.call_args)
   ```

   Notes:
   - `dns.resolver.NoNameservers` requires a `request=` kwarg for construction; supplying a `MagicMock()` avoids that dependency.
   - The `seeds._log` attribute is what the fix introduces. If you name your logger differently (e.g., `logger` instead of `_log`), update the tests to match.

2. **Run and confirm fail** — should fail with `AttributeError: module 'jtfprotocol.seeds' has no attribute '_log'`.

3. **Apply the fix.**

4. **Run and confirm pass** plus all previous tests still pass.

5. **Commit:** `./bu.sh "PHASE2-FOLLOWUP-02: DNS resolver logs NXDOMAIN and NoNameservers at debug level"`

---

## Follow-Up 3 — Tighten URL validation in `lookup_txt_seed`

**Severity:** Important. Current check is `startswith("http://") or startswith("https://")`, which accepts `"https:// evil"`, `"http://\n"`, `"https://"` (empty netloc), etc. The returned URL is passed to `RequestsFetcher.get` downstream, so a malformed value could produce unexpected connection behavior.

**File:** `jtfprotocol/seeds.py` — `lookup_txt_seed`.

**Current code:**

```python
def lookup_txt_seed(domain: str, resolver: Resolver | None = None) -> str | None:
    resolver = resolver or _default_resolver()
    records = resolver.resolve_txt(f"_jtf.{domain}")
    for value in records:
        if value.startswith("http://") or value.startswith("https://"):
            return value
    return None
```

**Fix approach:** Use `urllib.parse.urlparse` and require:
1. `scheme in {"http", "https"}`
2. `netloc` is non-empty
3. `netloc` contains no whitespace
4. The path (if present) must not contain whitespace

**Fix code:**

```python
from urllib.parse import urlparse


def _is_valid_wellknown_url(value: str) -> bool:
    """Return True if ``value`` is a syntactically plausible HTTP(S)
    URL suitable for fetching a well-known document. Does not fetch."""
    if not value or any(c in value for c in (" ", "\t", "\n", "\r")):
        return False
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
    )


def lookup_txt_seed(domain: str, resolver: Resolver | None = None) -> str | None:
    """Look up ``_jtf.{domain}`` TXT record. Return the first
    validly-formed HTTP(S) URL or None. Does not fetch the URL."""
    resolver = resolver or _default_resolver()
    records = resolver.resolve_txt(f"_jtf.{domain}")
    for value in records:
        if _is_valid_wellknown_url(value):
            return value
    return None
```

**Test plan (TDD):**

1. **Update existing tests** — the old `test_lookup_txt_seed_returns_none_when_record_is_not_a_url` uses `"not-a-url"` which still fails validation. But add coverage for the new cases:

   ```python
   def test_lookup_txt_seed_rejects_whitespace_in_url():
       resolver = FakeResolver({
           ("_jtf.example.com", "TXT"): ["https:// evil.example.com/.well-known/jtf.json"],
       })
       assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


   def test_lookup_txt_seed_rejects_url_with_newline():
       resolver = FakeResolver({
           ("_jtf.example.com", "TXT"): ["https://evil.example.com\n/.well-known/jtf.json"],
       })
       assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


   def test_lookup_txt_seed_rejects_empty_netloc():
       resolver = FakeResolver({
           ("_jtf.example.com", "TXT"): ["https:///.well-known/jtf.json"],
       })
       assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


   def test_lookup_txt_seed_rejects_non_http_scheme():
       resolver = FakeResolver({
           ("_jtf.example.com", "TXT"): ["file:///etc/passwd"],
       })
       assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


   def test_lookup_txt_seed_accepts_url_with_path_and_port():
       resolver = FakeResolver({
           ("_jtf.example.com", "TXT"): ["https://example.com:8443/.well-known/jtf.json"],
       })
       assert seeds.lookup_txt_seed("example.com", resolver=resolver) == (
           "https://example.com:8443/.well-known/jtf.json"
       )
   ```

2. **Run and confirm fail** — the first four fail because the current implementation accepts anything starting with `http://` or `https://`. The fifth may already pass. All should pass after the fix.

3. **Apply the fix.**

4. **Confirm all prior tests still pass** — the `discover_seeds` composite tests should be unaffected.

5. **Commit:** `./bu.sh "PHASE2-FOLLOWUP-03: tighten URL validation in lookup_txt_seed"`

---

## Follow-Up 4 — Broaden `_parse_iso8601_utc` to accept compliant peer timestamps

**Severity:** Important. Currently the parser only handles the `Z` suffix that JTF servers emit. A compliant peer using another implementation of the spec (`+00:00`, fractional seconds like `.000Z`, etc.) has its timestamps silently rejected, which cascades:

- In `peers_for_publication`: the peer is silently ineligible for publication forever.
- In `drop_dead_peers`: the parse-except branch keeps the peer forever (never expires).

Both outcomes hide non-compliance behind silent no-ops.

**File:** `jtfprotocol/gossip.py` — `_parse_iso8601_utc`.

**Current code:**

```python
def _parse_iso8601_utc(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
```

**Fix approach:** Accept the four common canonical forms:

1. `2026-07-01T00:00:00Z` (what we emit)
2. `2026-07-01T00:00:00+00:00` (equivalent explicit UTC offset)
3. `2026-07-01T00:00:00.000Z` (fractional seconds, Z-suffixed)
4. `2026-07-01T00:00:00.000+00:00` (fractional seconds, explicit offset)

Python 3.9's `datetime.fromisoformat` already handles cases 2 and 4 natively (`+00:00`). Cases 1 and 3 need the `Z` translation we already do. So the fix is trivial: keep the `Z` translation and let `fromisoformat` handle the rest.

The current code already does exactly this. Let me double-check:

```python
if s.endswith("Z"):
    s = s[:-1] + "+00:00"
return datetime.fromisoformat(s)
```

For `2026-07-01T00:00:00.000Z`: becomes `2026-07-01T00:00:00.000+00:00` — Python 3.9's `fromisoformat` accepts this.

For `2026-07-01T00:00:00.000+00:00`: passed through unchanged — Python 3.9's `fromisoformat` accepts.

So the parser IS actually correct for all four cases on Python 3.9? Let me verify empirically before writing tests:

```bash
venv/bin/python -c "
from datetime import datetime
for s in ('2026-07-01T00:00:00Z',
          '2026-07-01T00:00:00+00:00',
          '2026-07-01T00:00:00.000Z',
          '2026-07-01T00:00:00.000+00:00',
          '2026-07-01T00:00:00.123456+00:00'):
    x = s
    if x.endswith('Z'):
        x = x[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(x)
        print(f'{s!r:60} -> {parsed}')
    except Exception as e:
        print(f'{s!r:60} -> ERROR: {e}')
"
```

**Run this first.** If all four (or five) succeed, then the parser is fine and this follow-up is actually a **test hardening exercise** rather than a code fix. In that case:

1. Add tests that exercise each canonical form and prove `_parse_iso8601_utc` handles them.
2. Add tests that prove `peers_for_publication` and `drop_dead_peers` process peers with `.000Z` and `+00:00` timestamps correctly (do NOT silently drop them).
3. Update the `_parse_iso8601_utc` docstring to explicitly enumerate the accepted forms.
4. Commit as `PHASE2-FOLLOWUP-04: document and test _parse_iso8601_utc for all four canonical ISO-8601 UTC forms`.

If Python 3.9's `fromisoformat` in the venv REJECTS one of the forms (older Python 3.9 versions have limitations — Python 3.9 pre-3.11 does NOT support `+00:00` but Python 3.11+ does), then the fix is broader:

**Broader fix (only if `fromisoformat` rejects):**

```python
_ISO_FORMATS_TO_TRY = (
    "%Y-%m-%dT%H:%M:%S%z",           # 2026-07-01T00:00:00+0000
    "%Y-%m-%dT%H:%M:%S.%f%z",        # 2026-07-01T00:00:00.000+0000
)


def _parse_iso8601_utc(s: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp emitted by any compliant JTF
    peer. Accepts:

      - ``2026-07-01T00:00:00Z``
      - ``2026-07-01T00:00:00+00:00``
      - ``2026-07-01T00:00:00.000Z``
      - ``2026-07-01T00:00:00.000+00:00``

    All are normalized to a timezone-aware UTC ``datetime``.
    """
    # Normalize Z suffix and remove colon in offset for strptime.
    normalized = s
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    # Try fromisoformat first (Python 3.11+ handles everything).
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    # Fall back to strptime with a stripped colon in the offset.
    stripped = normalized.replace("+00:00", "+0000")
    for fmt in _ISO_FORMATS_TO_TRY:
        try:
            return datetime.strptime(stripped, fmt)
        except ValueError:
            continue
    raise ValueError(f"could not parse ISO-8601 timestamp: {s!r}")
```

**IMPORTANT: run the diagnostic snippet above BEFORE deciding which path to take.** Do not blindly rewrite a function that already works.

**Test plan (TDD, both paths):**

1. **Add positive-case tests:**

   ```python
   @pytest.mark.parametrize("s", [
       "2026-07-01T00:00:00Z",
       "2026-07-01T00:00:00+00:00",
       "2026-07-01T00:00:00.000Z",
       "2026-07-01T00:00:00.000+00:00",
       "2026-07-01T00:00:00.123456+00:00",
   ])
   def test_parse_iso8601_utc_accepts_all_canonical_utc_forms(s):
       parsed = gossip._parse_iso8601_utc(s)
       assert parsed.year == 2026
       assert parsed.month == 7
       assert parsed.day == 1
       assert parsed.utcoffset().total_seconds() == 0
   ```

2. **Add integration tests for `peers_for_publication` and `drop_dead_peers` with non-Z-suffixed timestamps:**

   ```python
   def test_peers_for_publication_accepts_plus_offset_timestamps(tmp_path):
       clock = FakeClock(datetime(2026, 7, 8, tzinfo=timezone.utc))
       store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
       # first_seen uses +00:00 form (a compliant peer's format) and is >48h old
       store._peers.append(gossip.PeerRecord(
           domain="ext.example",
           public_key_id="sha256:ext",
           channel="global",
           last_seen="2026-07-08T00:00:00+00:00",
           first_seen="2026-06-01T00:00:00+00:00",
           trust_score=0.5,
           confirmed_by=1,
           asn=64500,
       ))
       published = store.peers_for_publication()
       assert any(p["public_key_id"] == "sha256:ext" for p in published)


   def test_drop_dead_peers_drops_plus_offset_stale_peer(tmp_path):
       clock = FakeClock(datetime(2026, 7, 8, tzinfo=timezone.utc))
       store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
       store._peers.append(gossip.PeerRecord(
           domain="stale.example",
           public_key_id="sha256:stale",
           channel="global",
           last_seen="2026-06-30T00:00:00+00:00",  # 8 days ago
           first_seen="2026-04-01T00:00:00+00:00",
           trust_score=0.5,
           confirmed_by=1,
           asn=64500,
       ))
       dropped = store.drop_dead_peers()
       assert dropped == ["sha256:stale"]
   ```

3. **Run and confirm fail** if the parser needs broadening. If the parser already handles everything, skip to step 4 (tests just pass, documenting the invariant).

4. **Apply the fix** if needed. Update the docstring.

5. **Commit:** `./bu.sh "PHASE2-FOLLOWUP-04: broaden _parse_iso8601_utc for all canonical UTC forms"`

---

## Full-Suite Verification After Each Follow-Up

After each commit, run:

```bash
venv/bin/pytest -q 2>&1 | tail -3
```

Expected: `128 passed` at start, growing by 2–6 tests per follow-up. If any prior test fails after your change, you introduced a regression — do NOT commit; investigate and fix.

---

## Optional Minor Items (address only if time permits)

These are cosmetic or low-priority. Skip if unsure; the follow-ups above are the priority.

### Minor A — Move mid-file imports to top of `gossip.py`

`jtfprotocol/gossip.py` currently has module-level imports at two places: some at the top of the file, and others (e.g., `base64`, `json`, `os`, `dataclasses`, `datetime`, `Ed25519PublicKey`, `well_known as _well_known`) appended in the middle as tasks grew. PEP 8 wants all imports at the top. This is a pure refactor with zero behavior change; add a test-suite pass-through as verification and commit as `PHASE2-FOLLOWUP-05: consolidate gossip.py imports at top of file`.

### Minor B — Move test fakes to `tests/fakes.py`

`tests/test_announcements.py` imports `FakeFetcher`/`FakeResponse` from `tests.test_gossip`, which is fragile (renaming `test_gossip.py` would break the import). Extract the fakes to a shared `tests/fakes.py` module and update both consumers. Commit as `PHASE2-FOLLOWUP-06: extract test fakes to tests/fakes.py`.

### Minor C — Fix `__init__.py` docstring example

`jtfprotocol/__init__.py`'s docstring example uses `Path("data/peers.json")` without importing `Path` in the snippet. Either add `from pathlib import Path` to the example or change to a string literal. Trivial commit.

---

## When You Are Done

After committing all four Important follow-ups (and any Minor items you chose to address):

1. Run the full suite one final time: `venv/bin/pytest -q 2>&1 | tail -5`. Expected: all tests pass.

2. Enumerate the follow-up commits:
   ```bash
   git log --oneline 40f122b19..HEAD
   ```
   Expected: 4 commits (plus any minor items you did).

3. Report back to the user with:
   - Number of new tests added.
   - Total test count now.
   - List of commit SHAs and messages.
   - Any surprises or unresolved concerns.

4. Ask the user for next-step direction:
   - Merge Phase 2 to `feature/jtf-protocol`?
   - Move on to Phase 3 (Trust System)?
   - Hold for review?

**Do NOT merge to `feature/jtf-protocol` or `main` without explicit user approval.** Phase 5 is the integration phase and requires a designed rollout; Phase 2 stays inert until then.

---

## One-Line Recap

Address the four Important follow-ups from Phase 2 review — self-confirmation bug in `exchange_peer_lists`, DNS observability in `DnspythonResolver`, URL validation in `lookup_txt_seed`, ISO-8601 parser breadth. TDD, one commit each via `./bu.sh "PHASE2-FOLLOWUP-NN: ..."`, no `main.py` changes, live site untouched.
