# JTF Protocol Phase 2 — Discovery & Gossip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add discovery and gossip primitives to the `jtfprotocol` package so JTF servers can find each other, exchange peer lists, and propagate fact announcements across the network — without touching `main.py` or the live site.

**Architecture:** Three new modules under `jtfprotocol/`. `seeds.py` owns the hard-coded seed list and the DNS TXT/SRV fallback lookups. `gossip.py` owns the HTTP fetch layer, the `PeerRecord` / `PeerStore` state, the peer validation rules, and the 30-minute cycle orchestrator. `announcements.py` owns the tiny signed-envelope format for `fact_announcement` messages. All network I/O is done through an injected `Fetcher` protocol (default: `requests`) and all time reads go through an injected `Clock` (default: `datetime.now(timezone.utc)`), so tests never touch the network or the wall clock.

**Tech Stack:** Python 3.9, `cryptography` (Ed25519 — already present), `requests` (already present), `dnspython` (new dep, pure-Python), `pytest` (dev). No `responses` / `httpx-mock` / `freezegun` needed — dependency injection carries the isolation.

---

## Preflight

Before starting task 1, run:

```bash
cd /Users/larryseyer/JTFNews/.worktrees/phase2
git log -1 --format='%h %s'                  # expect Phase 1 HEAD: 598a35c01 or later
git branch                                   # expect * feature/jtf-protocol-phase2
venv/bin/pytest -q                           # expect 74 passed
```

If any of those fails, STOP and surface the mismatch. Do not proceed.

**Commit tool:** Every task ends with `./bu.sh "PHASE2-NN: <title>"`. Never raw `git commit`. `bu.sh` in this worktree pushes to `origin feature/jtf-protocol-phase2` (branch-aware) and writes a Downloads backup zip.

**No emoji anywhere** — code, docstrings, tests, commit messages. JTF methodology rejects editorializing; emoji is editorializing.

**Type annotations:** `from __future__ import annotations` is at the top of every new `.py`. Parameterized annotations (`list[dict]`, `dict | None`, `set[str]`) work on Python 3.9 because of that import — do NOT downgrade them to `List[dict]` / `Optional[dict]`.

---

## File Structure

| File | Responsibility |
|---|---|
| `jtfprotocol/seeds.py` | Hard-coded seed domain list; DNS TXT (`_jtf.<domain>`) and SRV (`_jtf._tcp.<domain>`) resolution; `discover_seeds` composite that unions the hard-coded list with DNS-derived seeds. Pure functions plus one thin `Resolver` protocol wrapping `dns.resolver` for injection in tests. |
| `jtfprotocol/gossip.py` | `Fetcher` protocol + default `requests`-based implementation; `fetch_and_verify_well_known` (fetches `/.well-known/jtf.json`, verifies signature, returns doc); `PeerRecord` dataclass; `PeerStore` (in-memory state with JSON load/save; max-100 trust-weighted eviction; new-peer rate limit; ASN diversity gate; 48h uptime gate for propagation; 7-day dead-peer drop; `confirmed_by` counter); `exchange_peer_lists` (fetch remote well-known and merge peers); `fetch_fact_by_id` (pull full fact from a peer's `facts_json` feed); `run_gossip_cycle` orchestrator. |
| `jtfprotocol/announcements.py` | `build_announcement` (populate + canonical-JSON sign the 6-field envelope); `verify_announcement` (canonical-JSON verify); `send_announcement` (POST to peer's `/announcements` via injected fetcher). Small, focused, pure-crypto surface — same shape as `well_known.py`. |
| `tests/test_seeds.py` | Unit tests for the seed constants, TXT parser, SRV parser, `discover_seeds` composite. Uses a fake `Resolver`. |
| `tests/test_gossip.py` | Unit tests for `Fetcher`, `fetch_and_verify_well_known`, `PeerRecord`, `PeerStore` (persistence + each validation rule in isolation), `exchange_peer_lists`, `fetch_fact_by_id`, and `run_gossip_cycle`. Uses a fake `Fetcher` and a fake `Clock`. |
| `tests/test_announcements.py` | Unit tests for `build_announcement`, `verify_announcement`, `send_announcement`. |
| `tests/test_smoke_phase2.py` | One end-to-end scenario: two servers bootstrap from a seed, exchange peers, and successfully propagate a signed fact announcement + full fact pull. Uses fakes only. |
| `requirements.txt` | Add `dnspython>=2.4.0`. |
| `jtfprotocol/__init__.py` | Export the new modules alongside the Phase 1 ones. |
| `jtfprotocol/README.md` | Update the "Not included" section to mark Phase 2 done. |

---

## Task 1: Add `dnspython` dep and seed domain constants

**Spec reference:** "Seed Domains" (lines 429–439), "Fallback Discovery" (lines 441–448).

**Files:**
- Modify: `requirements.txt`
- Create: `jtfprotocol/seeds.py`
- Create: `tests/test_seeds.py`

- [ ] **Step 1: Add the dependency**

Edit `requirements.txt` — add one line at the end:

```
dnspython>=2.4.0
```

- [ ] **Step 2: Install the dep in the worktree venv**

```bash
./venv/bin/pip install "dnspython>=2.4.0"
./venv/bin/python -c "import dns.resolver; print(dns.resolver.__file__)"
```

Expected: prints a path inside `venv/lib/`. No errors.

- [ ] **Step 3: Write the failing test**

Create `tests/test_seeds.py`:

```python
"""Tests for jtfprotocol.seeds."""
from __future__ import annotations

from jtfprotocol import seeds


def test_seed_domains_is_a_tuple_of_strings():
    assert isinstance(seeds.SEED_DOMAINS, tuple)
    assert all(isinstance(d, str) and d for d in seeds.SEED_DOMAINS)


def test_seed_domains_includes_jtfnews_org():
    assert "jtfnews.org" in seeds.SEED_DOMAINS
```

- [ ] **Step 4: Run and confirm failure**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.seeds'`.

- [ ] **Step 5: Create the module with the seed constants**

Create `jtfprotocol/seeds.py`:

```python
"""JTF Protocol seed domain list and DNS discovery fallback.

Servers use this module on first startup to find at least one other
server. Once a server has exchanged peer lists with two others, it no
longer needs seeds. The seed list is a lifeboat, not a chain of command.

See documentation/Protocol Ver 1.0 CURRENT.md, sections "Seed Domains"
and "Fallback Discovery".
"""
from __future__ import annotations


SEED_DOMAINS: tuple[str, ...] = (
    "jtfnews.org",
)
"""Hard-coded seed domains. Additional entries are added by editing this
tuple and cutting a new release. The protocol requires a minimum of three
seed domains in different jurisdictions before the network is considered
production-ready."""
```

- [ ] **Step 6: Run and confirm pass**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
./bu.sh "PHASE2-01: seed domain constants and dnspython dep"
```

---

## Task 2: DNS TXT record discovery

**Spec reference:** "Fallback Discovery" (lines 441–448) — "DNS TXT record: A domain may publish a TXT record at `_jtf.{domain}` containing the URL of its well-known endpoint."

**Files:**
- Modify: `jtfprotocol/seeds.py`
- Modify: `tests/test_seeds.py`

- [ ] **Step 1: Extend the test file with TXT tests**

Append to `tests/test_seeds.py`:

```python
class FakeResolver:
    """Fake DNS resolver for tests. Maps (name, rdtype) -> list of str."""

    def __init__(self, answers: dict[tuple[str, str], list[str]] | None = None):
        self._answers = answers or {}

    def resolve_txt(self, name: str) -> list[str]:
        return list(self._answers.get((name, "TXT"), []))

    def resolve_srv(self, name: str) -> list[tuple[str, int, int, int]]:
        # (target, port, priority, weight)
        raw = self._answers.get((name, "SRV"), [])
        return list(raw)


def test_lookup_txt_seed_returns_url_when_txt_record_present():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["https://example.com/.well-known/jtf.json"],
    })
    result = seeds.lookup_txt_seed("example.com", resolver=resolver)
    assert result == "https://example.com/.well-known/jtf.json"


def test_lookup_txt_seed_returns_none_when_no_record():
    resolver = FakeResolver()
    assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


def test_lookup_txt_seed_returns_none_when_record_is_not_a_url():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["not-a-url"],
    })
    assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


def test_lookup_txt_seed_takes_first_url_when_multiple_records():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): [
            "https://a.example.com/.well-known/jtf.json",
            "https://b.example.com/.well-known/jtf.json",
        ],
    })
    result = seeds.lookup_txt_seed("example.com", resolver=resolver)
    assert result == "https://a.example.com/.well-known/jtf.json"
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: 4 new tests fail with `AttributeError: module 'jtfprotocol.seeds' has no attribute 'lookup_txt_seed'`.

- [ ] **Step 3: Add the Resolver protocol and TXT lookup**

Append to `jtfprotocol/seeds.py`:

```python
from typing import Protocol


class Resolver(Protocol):
    """Injectable DNS resolver. Tests supply a fake; production uses
    `DnspythonResolver` which wraps the ``dnspython`` package."""

    def resolve_txt(self, name: str) -> list[str]:
        ...

    def resolve_srv(self, name: str) -> list[tuple[str, int, int, int]]:
        ...


class DnspythonResolver:
    """Default resolver backed by ``dnspython``. Silent on NXDOMAIN /
    NoAnswer — those are expected outcomes, not errors."""

    def resolve_txt(self, name: str) -> list[str]:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, "TXT")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        out: list[str] = []
        for rdata in answers:
            # Each TXT rdata is a sequence of byte strings; join and decode.
            joined = b"".join(rdata.strings).decode("utf-8", errors="replace")
            out.append(joined)
        return out

    def resolve_srv(self, name: str) -> list[tuple[str, int, int, int]]:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, "SRV")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        out: list[tuple[str, int, int, int]] = []
        for rdata in answers:
            target = str(rdata.target).rstrip(".")
            out.append((target, int(rdata.port), int(rdata.priority), int(rdata.weight)))
        return out


def _default_resolver() -> Resolver:
    return DnspythonResolver()


def lookup_txt_seed(domain: str, resolver: Resolver | None = None) -> str | None:
    """Look up ``_jtf.{domain}`` TXT record. Return the first URL-looking
    value or None. Does not fetch the URL."""
    resolver = resolver or _default_resolver()
    records = resolver.resolve_txt(f"_jtf.{domain}")
    for value in records:
        if value.startswith("http://") or value.startswith("https://"):
            return value
    return None
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-02: DNS TXT record discovery for _jtf.<domain>"
```

---

## Task 3: DNS SRV record discovery

**Spec reference:** "Fallback Discovery" — "DNS SRV record: A domain may publish an SRV record at `_jtf._tcp.{domain}` pointing to its server's host and port."

**Files:**
- Modify: `jtfprotocol/seeds.py`
- Modify: `tests/test_seeds.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_seeds.py`:

```python
def test_lookup_srv_seed_returns_url_from_target_and_port():
    resolver = FakeResolver({
        ("_jtf._tcp.example.com", "SRV"): [
            ("srv.example.com", 443, 10, 100),
        ],
    })
    result = seeds.lookup_srv_seed("example.com", resolver=resolver)
    assert result == "https://srv.example.com/.well-known/jtf.json"


def test_lookup_srv_seed_uses_http_scheme_for_port_80():
    resolver = FakeResolver({
        ("_jtf._tcp.example.com", "SRV"): [
            ("srv.example.com", 80, 10, 100),
        ],
    })
    assert seeds.lookup_srv_seed("example.com", resolver=resolver) == (
        "http://srv.example.com/.well-known/jtf.json"
    )


def test_lookup_srv_seed_uses_lowest_priority_first():
    resolver = FakeResolver({
        ("_jtf._tcp.example.com", "SRV"): [
            ("high.example.com", 443, 20, 100),
            ("low.example.com", 443, 10, 100),
        ],
    })
    assert seeds.lookup_srv_seed("example.com", resolver=resolver) == (
        "https://low.example.com/.well-known/jtf.json"
    )


def test_lookup_srv_seed_returns_none_when_no_record():
    resolver = FakeResolver()
    assert seeds.lookup_srv_seed("example.com", resolver=resolver) is None
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: 4 new tests fail with `AttributeError: ... 'lookup_srv_seed'`.

- [ ] **Step 3: Implement the SRV lookup**

Append to `jtfprotocol/seeds.py`:

```python
def lookup_srv_seed(domain: str, resolver: Resolver | None = None) -> str | None:
    """Look up ``_jtf._tcp.{domain}`` SRV record. Return a well-known
    URL derived from the lowest-priority target, or None.

    Scheme selection: port 80 -> http, anything else -> https. The
    protocol expects TLS for anything other than the well-known port.
    """
    resolver = resolver or _default_resolver()
    records = resolver.resolve_srv(f"_jtf._tcp.{domain}")
    if not records:
        return None
    records = sorted(records, key=lambda r: (r[2], -r[3]))
    target, port, _priority, _weight = records[0]
    scheme = "http" if port == 80 else "https"
    host = target if port in (80, 443) else f"{target}:{port}"
    return f"{scheme}://{host}/.well-known/jtf.json"
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-03: DNS SRV record discovery for _jtf._tcp.<domain>"
```

---

## Task 4: `discover_seeds` composite

**Spec reference:** "Seed Domains" + "Fallback Discovery" — seeds are the primary entry, DNS is fallback.

**Files:**
- Modify: `jtfprotocol/seeds.py`
- Modify: `tests/test_seeds.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_seeds.py`:

```python
def test_discover_seeds_returns_hardcoded_urls_when_no_dns_hints():
    resolver = FakeResolver()
    urls = seeds.discover_seeds(candidate_domains=("example.com",), resolver=resolver)
    assert "https://jtfnews.org/.well-known/jtf.json" in urls
    assert len(urls) == 1


def test_discover_seeds_includes_dns_txt_hint():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["https://example.com/.well-known/jtf.json"],
    })
    urls = seeds.discover_seeds(candidate_domains=("example.com",), resolver=resolver)
    assert "https://example.com/.well-known/jtf.json" in urls
    assert "https://jtfnews.org/.well-known/jtf.json" in urls


def test_discover_seeds_prefers_txt_over_srv_when_both_present():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["https://txt.example.com/.well-known/jtf.json"],
        ("_jtf._tcp.example.com", "SRV"): [("srv.example.com", 443, 10, 100)],
    })
    urls = seeds.discover_seeds(candidate_domains=("example.com",), resolver=resolver)
    assert "https://txt.example.com/.well-known/jtf.json" in urls
    assert "https://srv.example.com/.well-known/jtf.json" not in urls


def test_discover_seeds_deduplicates():
    resolver = FakeResolver({
        ("_jtf.jtfnews.org", "TXT"): ["https://jtfnews.org/.well-known/jtf.json"],
    })
    urls = seeds.discover_seeds(candidate_domains=("jtfnews.org",), resolver=resolver)
    assert urls.count("https://jtfnews.org/.well-known/jtf.json") == 1
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: 4 new tests fail with `AttributeError: ... 'discover_seeds'`.

- [ ] **Step 3: Implement the composite**

Append to `jtfprotocol/seeds.py`:

```python
def discover_seeds(
    candidate_domains: tuple[str, ...] = (),
    resolver: Resolver | None = None,
) -> list[str]:
    """Return an ordered, de-duplicated list of well-known URLs to try.

    Ordering:
      1. Hard-coded ``SEED_DOMAINS`` (always first — the lifeboat).
      2. For each ``candidate_domain``: TXT record hint, then SRV record
         hint. TXT wins over SRV when both are present for the same domain.

    ``candidate_domains`` is typically a list of domains a server has
    heard about via out-of-band means (last-known-good peer cache,
    operator configuration). Empty by default.
    """
    resolver = resolver or _default_resolver()
    urls: list[str] = []
    seen: set[str] = set()

    def _add(url: str | None) -> None:
        if url and url not in seen:
            urls.append(url)
            seen.add(url)

    for d in SEED_DOMAINS:
        _add(f"https://{d}/.well-known/jtf.json")

    for d in candidate_domains:
        txt = lookup_txt_seed(d, resolver=resolver)
        if txt:
            _add(txt)
            continue
        srv = lookup_srv_seed(d, resolver=resolver)
        _add(srv)

    return urls
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_seeds.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-04: discover_seeds composite (hard-coded plus DNS fallback)"
```

---

## Task 5: `Fetcher` protocol and default `requests`-based implementation

**Spec reference:** "The Well-Known Endpoint" (lines 333–384) — endpoint is public HTTP GET, short-TTL cache, tolerate stale up to 24h. "Fact Propagation" (lines 409–427) — announcements are pushed via POST.

**Files:**
- Create: `jtfprotocol/gossip.py`
- Create: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_gossip.py`:

```python
"""Tests for jtfprotocol.gossip."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from jtfprotocol import gossip


@dataclass
class FakeResponse:
    status_code: int
    body: bytes
    headers: dict[str, str]

    def json(self):
        import json
        return json.loads(self.body.decode("utf-8"))


class FakeFetcher:
    """In-memory fetcher for tests.

    ``get_map`` and ``post_map`` are dicts keyed by URL. The value is
    either a ``FakeResponse`` or a callable ``(url, body) -> FakeResponse``.
    """

    def __init__(
        self,
        get_map: dict | None = None,
        post_map: dict | None = None,
    ):
        self.get_map = get_map or {}
        self.post_map = post_map or {}
        self.get_calls: list[str] = []
        self.post_calls: list[tuple[str, bytes]] = []

    def get(self, url: str, timeout: float = 10.0) -> FakeResponse:
        self.get_calls.append(url)
        entry = self.get_map.get(url)
        if entry is None:
            return FakeResponse(status_code=404, body=b"", headers={})
        return entry if isinstance(entry, FakeResponse) else entry(url)

    def post(self, url: str, body: bytes, timeout: float = 10.0) -> FakeResponse:
        self.post_calls.append((url, body))
        entry = self.post_map.get(url)
        if entry is None:
            return FakeResponse(status_code=404, body=b"", headers={})
        return entry if isinstance(entry, FakeResponse) else entry(url, body)


def test_default_fetcher_get_uses_requests(monkeypatch):
    captured = {}

    class DummyRequestsResponse:
        status_code = 200
        content = b'{"ok": true}'
        headers = {"Content-Type": "application/json"}

        def json(self):
            return {"ok": True}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return DummyRequestsResponse()

    import requests
    monkeypatch.setattr(requests, "get", fake_get)

    fetcher = gossip.RequestsFetcher()
    resp = fetcher.get("https://example.com/x", timeout=7.5)
    assert captured == {"url": "https://example.com/x", "timeout": 7.5}
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_default_fetcher_post_uses_requests(monkeypatch):
    captured = {}

    class DummyRequestsResponse:
        status_code = 202
        content = b""
        headers = {}

        def json(self):
            return {}

    def fake_post(url, data, timeout, headers):
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        captured["headers"] = headers
        return DummyRequestsResponse()

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    fetcher = gossip.RequestsFetcher()
    resp = fetcher.post("https://example.com/announcements", body=b"{}", timeout=3.0)
    assert captured["url"] == "https://example.com/announcements"
    assert captured["data"] == b"{}"
    assert captured["timeout"] == 3.0
    assert captured["headers"] == {"Content-Type": "application/json"}
    assert resp.status_code == 202
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.gossip'`.

- [ ] **Step 3: Create the module scaffold with the Fetcher**

Create `jtfprotocol/gossip.py`:

```python
"""JTF Protocol discovery, peer state, and gossip cycle.

Provides the client-side network primitives every JTF server needs to
find peers, exchange peer lists, and propagate fact announcements. All
network I/O flows through a ``Fetcher`` protocol so tests can inject a
fake and never hit the network. All time reads flow through a ``Clock``
callable so tests can inject a fake and never sleep.

Nothing in this module mutates ``main.py`` state, writes to
``feed.xml``, or touches the live site. Phase 5 wires it in.

See documentation/Protocol Ver 1.0 CURRENT.md, sections "Discovery",
"Gossip", "Peer Validation", and "Fact Propagation".
"""
from __future__ import annotations

from typing import Protocol


class Response(Protocol):
    """Minimal HTTP response contract used by ``Fetcher``."""

    status_code: int

    def json(self) -> dict:
        ...


class Fetcher(Protocol):
    """Injectable HTTP client. Default implementation is
    ``RequestsFetcher``; tests supply fakes."""

    def get(self, url: str, timeout: float = 10.0) -> Response:
        ...

    def post(self, url: str, body: bytes, timeout: float = 10.0) -> Response:
        ...


class RequestsFetcher:
    """Default fetcher backed by the ``requests`` library.

    Bounded timeout at every call site — the live-site incident record
    (see main.py CLAUDE.md "Bug Patterns") shows that unbounded HTTP
    clients hang for hours on macOS. Callers may pass a smaller
    ``timeout`` per call; the default is deliberately short.
    """

    def get(self, url: str, timeout: float = 10.0):
        import requests
        return requests.get(url, timeout=timeout)

    def post(self, url: str, body: bytes, timeout: float = 10.0):
        import requests
        return requests.post(
            url,
            data=body,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-05: Fetcher protocol and RequestsFetcher default"
```

---

## Task 6: `fetch_and_verify_well_known`

**Spec reference:** "The Well-Known Endpoint" — endpoint is signed by the server's private key; consumers verify the signature before trusting anything in it. Uses the Phase 1 `verify_well_known` primitive.

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
import base64
import json as _json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jtfprotocol import identity, well_known


def _make_signed_wellknown(domain: str = "example.com", peers=None):
    priv, pub = identity.generate_keypair()
    doc = well_known.generate_well_known(
        priv=priv,
        pub=pub,
        server_info={
            "domain": domain,
            "channel": "global",
            "name": f"{domain} server",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 24940,
            "location_country": "US",
        },
        extraction_info={
            "backend": "ollama",
            "model": "ollama:qwen2.5:72b-instruct-q5_K_M",
            "prompt_version": "jtf-extract-v3",
        },
        feeds={
            "facts_rss": "/feed.xml",
            "facts_json": "/stories.json",
            "corrections": "/corrections.json",
            "archive": "/archive/index.json",
            "announcements": "/announcements",
        },
        peers=peers or [],
    )
    return priv, pub, doc


def test_fetch_and_verify_well_known_returns_doc_on_success():
    _priv, _pub, doc = _make_signed_wellknown()
    body = _json.dumps(doc).encode("utf-8")
    fetcher = FakeFetcher(get_map={
        "https://example.com/.well-known/jtf.json": FakeResponse(200, body, {}),
    })

    result = gossip.fetch_and_verify_well_known("example.com", fetcher=fetcher)
    assert result is not None
    assert result["server"]["domain"] == "example.com"


def test_fetch_and_verify_well_known_returns_none_on_http_error():
    fetcher = FakeFetcher(get_map={
        "https://example.com/.well-known/jtf.json": FakeResponse(500, b"", {}),
    })
    assert gossip.fetch_and_verify_well_known("example.com", fetcher=fetcher) is None


def test_fetch_and_verify_well_known_returns_none_on_bad_signature():
    _priv, _pub, doc = _make_signed_wellknown()
    doc["signature"] = base64.b64encode(b"\x00" * 64).decode("ascii")
    body = _json.dumps(doc).encode("utf-8")
    fetcher = FakeFetcher(get_map={
        "https://example.com/.well-known/jtf.json": FakeResponse(200, body, {}),
    })
    assert gossip.fetch_and_verify_well_known("example.com", fetcher=fetcher) is None


def test_fetch_and_verify_well_known_returns_none_on_missing_public_key():
    _priv, _pub, doc = _make_signed_wellknown()
    del doc["server"]["public_key"]
    body = _json.dumps(doc).encode("utf-8")
    fetcher = FakeFetcher(get_map={
        "https://example.com/.well-known/jtf.json": FakeResponse(200, body, {}),
    })
    assert gossip.fetch_and_verify_well_known("example.com", fetcher=fetcher) is None
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 4 new tests fail with `AttributeError: ... 'fetch_and_verify_well_known'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/gossip.py`:

```python
import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jtfprotocol import well_known as _well_known


WELL_KNOWN_PATH = "/.well-known/jtf.json"


def fetch_and_verify_well_known(
    domain: str,
    fetcher: Fetcher | None = None,
    timeout: float = 10.0,
) -> dict | None:
    """Fetch ``https://{domain}/.well-known/jtf.json`` and verify its
    signature against the public key it advertises.

    Returns the parsed doc on success. Returns None on any failure
    (HTTP error, malformed JSON, missing public key, bad signature).
    Never raises.
    """
    fetcher = fetcher or RequestsFetcher()
    url = f"https://{domain}{WELL_KNOWN_PATH}"
    try:
        resp = fetcher.get(url, timeout=timeout)
        if resp.status_code != 200:
            return None
        doc = resp.json()
        pub_b64 = doc.get("server", {}).get("public_key")
        if not pub_b64:
            return None
        pub_bytes = base64.b64decode(pub_b64)
        pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
        if not _well_known.verify_well_known(doc, pub):
            return None
        return doc
    except Exception:
        return None
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-06: fetch_and_verify_well_known"
```

---

## Task 7: `PeerRecord` dataclass and `Clock` protocol

**Spec reference:** "Peer Validation" (lines 399–407) — peers carry trust, ASN, uptime, `confirmed_by` count, last-seen timestamp.

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_peer_record_from_wellknown_peer_entry():
    entry = {
        "domain": "example.com",
        "public_key_id": "sha256:abc",
        "channel": "global",
        "last_seen": "2026-07-01T00:00:00Z",
        "trust_score": 0.94,
        "confirmed_by": 3,
    }
    p = gossip.PeerRecord.from_wellknown_entry(entry, first_seen="2026-04-01T00:00:00Z", asn=64500)
    assert p.domain == "example.com"
    assert p.public_key_id == "sha256:abc"
    assert p.channel == "global"
    assert p.trust_score == 0.94
    assert p.confirmed_by == 3
    assert p.asn == 64500
    assert p.first_seen == "2026-04-01T00:00:00Z"


def test_peer_record_to_wellknown_entry_round_trip():
    p = gossip.PeerRecord(
        domain="example.com",
        public_key_id="sha256:abc",
        channel="global",
        last_seen="2026-07-01T00:00:00Z",
        trust_score=0.5,
        confirmed_by=1,
        first_seen="2026-04-01T00:00:00Z",
        asn=64500,
    )
    entry = p.to_wellknown_entry()
    assert entry == {
        "domain": "example.com",
        "public_key_id": "sha256:abc",
        "channel": "global",
        "last_seen": "2026-07-01T00:00:00Z",
        "trust_score": 0.5,
        "confirmed_by": 1,
    }
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 2 new tests fail with `AttributeError: ... 'PeerRecord'`.

- [ ] **Step 3: Add the dataclass and Clock protocol**

Append to `jtfprotocol/gossip.py`:

```python
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable


Clock = Callable[[], datetime]
"""Zero-arg callable returning the current UTC datetime. Tests inject a
fake so gossip logic can be time-tested without ``time.sleep`` or
freezegun."""


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PeerRecord:
    """Local record of a peer server.

    Fields with a ``last_seen`` / ``first_seen`` timestamp use ISO-8601
    UTC strings (``2026-07-01T00:00:00Z``) so JSON persistence stays
    lossless. All numeric fields default to zero, indicating "not yet
    observed"."""

    domain: str
    public_key_id: str
    channel: str
    last_seen: str
    first_seen: str
    trust_score: float = 0.0
    confirmed_by: int = 0
    asn: int = 0

    @classmethod
    def from_wellknown_entry(
        cls,
        entry: dict,
        first_seen: str,
        asn: int = 0,
    ) -> PeerRecord:
        return cls(
            domain=entry["domain"],
            public_key_id=entry["public_key_id"],
            channel=entry.get("channel", "global"),
            last_seen=entry.get("last_seen", first_seen),
            first_seen=first_seen,
            trust_score=float(entry.get("trust_score", 0.0)),
            confirmed_by=int(entry.get("confirmed_by", 0)),
            asn=int(asn),
        )

    def to_wellknown_entry(self) -> dict:
        """Return the six-field subset published in
        ``/.well-known/jtf.json`` under ``peers``. ``first_seen`` and
        ``asn`` are local bookkeeping and are NOT published."""
        return {
            "domain": self.domain,
            "public_key_id": self.public_key_id,
            "channel": self.channel,
            "last_seen": self.last_seen,
            "trust_score": self.trust_score,
            "confirmed_by": self.confirmed_by,
        }
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-07: PeerRecord dataclass and Clock protocol"
```

---

## Task 8: `PeerStore` persistence

**Spec reference:** "Peer Validation" — peer state is persistent across restarts; each server maintains at most 100 active peers.

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_peer_store_empty_load_when_file_missing(tmp_path):
    store = gossip.PeerStore(path=tmp_path / "peers.json")
    assert store.all() == []


def test_peer_store_save_and_reload_round_trip(tmp_path):
    path = tmp_path / "peers.json"
    store = gossip.PeerStore(path=path)
    store._peers.append(gossip.PeerRecord(
        domain="a.example",
        public_key_id="sha256:aaa",
        channel="global",
        last_seen="2026-07-01T00:00:00Z",
        first_seen="2026-04-01T00:00:00Z",
        trust_score=0.5,
        confirmed_by=2,
        asn=64500,
    ))
    store.save()

    reloaded = gossip.PeerStore(path=path)
    assert len(reloaded.all()) == 1
    p = reloaded.all()[0]
    assert p.domain == "a.example"
    assert p.confirmed_by == 2
    assert p.asn == 64500
    assert p.first_seen == "2026-04-01T00:00:00Z"


def test_peer_store_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "peers.json"
    path.write_text("not valid json {")
    store = gossip.PeerStore(path=path)
    assert store.all() == []
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 3 new tests fail with `AttributeError: ... 'PeerStore'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/gossip.py`:

```python
import os
from pathlib import Path


MAX_PEERS = 100
"""Spec: 'Each server maintains at most one hundred active peers.'"""


class PeerStore:
    """Local peer state, persisted to a single JSON file.

    This is the reference implementation. Phase 5 wires this into
    ``main.py``'s data directory. Until then, callers pass an explicit
    ``path``.

    Not thread-safe. main.py is single-threaded (see CLAUDE.md).
    """

    def __init__(self, path: Path, clock: Clock | None = None):
        self._path = Path(path)
        self._clock = clock or _default_clock
        self._peers: list[PeerRecord] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            return
        peers: list[PeerRecord] = []
        for entry in data.get("peers", []):
            try:
                peers.append(PeerRecord(**entry))
            except TypeError:
                continue
        self._peers = peers

    def save(self) -> None:
        payload = {
            "version": 1,
            "peers": [asdict(p) for p in self._peers],
        }
        # Atomic write (see main.py atomic_write_text pattern).
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    def all(self) -> list[PeerRecord]:
        """Return a snapshot of all peer records."""
        return list(self._peers)

    def find(self, public_key_id: str) -> PeerRecord | None:
        for p in self._peers:
            if p.public_key_id == public_key_id:
                return p
        return None
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-08: PeerStore JSON persistence with atomic write"
```

---

## Task 9: `PeerStore.add_or_update` — single-peer merge and `confirmed_by` counter

**Spec reference:** "Peer Validation" — "A peer that appears in the peer lists of three or more independent servers has stronger standing than one reported by a single source. The `confirmed_by` field tracks this count." "Multi-source confirmation."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
class FakeClock:
    def __init__(self, now: datetime):
        self._now = now

    def __call__(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        from datetime import timedelta
        self._now = self._now + timedelta(seconds=seconds)


from datetime import datetime, timezone


def test_add_or_update_inserts_new_peer(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    entry = {
        "domain": "a.example",
        "public_key_id": "sha256:aaa",
        "channel": "global",
        "last_seen": "2026-07-01T00:00:00Z",
        "trust_score": 0.5,
        "confirmed_by": 0,
    }
    added = store.add_or_update(entry, source_key_id="sha256:src1", asn=64500)
    assert added is True
    assert len(store.all()) == 1
    p = store.find("sha256:aaa")
    assert p.confirmed_by == 1
    assert p.asn == 64500


def test_add_or_update_second_source_increments_confirmed_by(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    entry = {
        "domain": "a.example",
        "public_key_id": "sha256:aaa",
        "channel": "global",
        "last_seen": "2026-07-01T00:00:00Z",
        "trust_score": 0.5,
        "confirmed_by": 0,
    }
    store.add_or_update(entry, source_key_id="sha256:src1", asn=64500)
    store.add_or_update(entry, source_key_id="sha256:src2", asn=64500)
    p = store.find("sha256:aaa")
    assert p.confirmed_by == 2


def test_add_or_update_same_source_twice_does_not_double_count(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    entry = {
        "domain": "a.example",
        "public_key_id": "sha256:aaa",
        "channel": "global",
        "last_seen": "2026-07-01T00:00:00Z",
        "trust_score": 0.5,
        "confirmed_by": 0,
    }
    store.add_or_update(entry, source_key_id="sha256:src1", asn=64500)
    store.add_or_update(entry, source_key_id="sha256:src1", asn=64500)
    p = store.find("sha256:aaa")
    assert p.confirmed_by == 1
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 3 new tests fail with `AttributeError: 'PeerStore' object has no attribute 'add_or_update'`.

- [ ] **Step 3: Implement**

Extend `PeerStore` in `jtfprotocol/gossip.py`:

```python
    # Instance state: which (peer_public_key_id, source_public_key_id)
    # confirmations have already been counted. Persisted in the same
    # JSON payload so the counter is stable across restarts.
    _confirmations: dict[str, set[str]]

    def _load(self) -> None:  # replace prior body
        self._confirmations = {}
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            return
        peers: list[PeerRecord] = []
        for entry in data.get("peers", []):
            try:
                peers.append(PeerRecord(**entry))
            except TypeError:
                continue
        self._peers = peers
        self._confirmations = {
            k: set(v) for k, v in data.get("confirmations", {}).items()
        }

    def save(self) -> None:  # replace prior body
        payload = {
            "version": 1,
            "peers": [asdict(p) for p in self._peers],
            "confirmations": {k: sorted(v) for k, v in self._confirmations.items()},
        }
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    def add_or_update(
        self,
        entry: dict,
        source_key_id: str,
        asn: int = 0,
    ) -> bool:
        """Merge a peer-list entry received from ``source_key_id``.

        - New peer: appended with ``confirmed_by = 1``, marked confirmed
          by this source.
        - Existing peer, new source: ``confirmed_by`` increments; the
          record's ``last_seen``, ``trust_score``, ``channel`` fields
          adopt the newer entry's values.
        - Existing peer, same source that already confirmed: no change.

        Returns True if the peer set changed, False otherwise. Callers
        are responsible for calling ``save()`` when their batch is done.
        """
        pkid = entry["public_key_id"]
        existing = self.find(pkid)
        source_set = self._confirmations.setdefault(pkid, set())

        if existing is None:
            now = self._clock().strftime("%Y-%m-%dT%H:%M:%SZ")
            new = PeerRecord.from_wellknown_entry(entry, first_seen=now, asn=asn)
            new.confirmed_by = 1
            self._peers.append(new)
            source_set.add(source_key_id)
            return True

        if source_key_id in source_set:
            return False

        source_set.add(source_key_id)
        existing.confirmed_by = len(source_set)
        existing.last_seen = entry.get("last_seen", existing.last_seen)
        existing.trust_score = float(entry.get("trust_score", existing.trust_score))
        existing.channel = entry.get("channel", existing.channel)
        if asn:
            existing.asn = int(asn)
        return True
```

Also update the class body definition to declare `_confirmations` (add near `_peers`):

```python
class PeerStore:
    ...
    _peers: list[PeerRecord]
    _confirmations: dict[str, set[str]]
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-09: PeerStore.add_or_update with confirmed_by counter"
```

---

## Task 10: `MAX_PEERS` cap with trust-weighted eviction

**Spec reference:** "Peer Validation" — "When the limit is reached, new peers replace the lowest-trust existing peers. Random selection from qualified candidates prevents geographic or infrastructure clustering."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def _entry(domain: str, pkid: str, trust: float = 0.5) -> dict:
    return {
        "domain": domain,
        "public_key_id": pkid,
        "channel": "global",
        "last_seen": "2026-07-01T00:00:00Z",
        "trust_score": trust,
        "confirmed_by": 0,
    }


def test_add_or_update_respects_max_peers_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(gossip, "MAX_PEERS", 3)
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    for i, trust in enumerate([0.9, 0.8, 0.7]):
        store.add_or_update(
            _entry(f"peer{i}.example", f"sha256:peer{i}", trust=trust),
            source_key_id="sha256:src",
        )
    assert len(store.all()) == 3

    store.add_or_update(
        _entry("newer.example", "sha256:newer", trust=0.95),
        source_key_id="sha256:src",
    )
    assert len(store.all()) == 3
    remaining_ids = {p.public_key_id for p in store.all()}
    assert "sha256:newer" in remaining_ids
    assert "sha256:peer2" not in remaining_ids  # lowest trust was evicted


def test_add_or_update_rejects_new_peer_when_it_would_not_win_eviction(tmp_path, monkeypatch):
    monkeypatch.setattr(gossip, "MAX_PEERS", 3)
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    for i, trust in enumerate([0.9, 0.8, 0.7]):
        store.add_or_update(
            _entry(f"peer{i}.example", f"sha256:peer{i}", trust=trust),
            source_key_id="sha256:src",
        )

    added = store.add_or_update(
        _entry("weaker.example", "sha256:weaker", trust=0.1),
        source_key_id="sha256:src",
    )
    assert added is False
    assert store.find("sha256:weaker") is None
    assert len(store.all()) == 3
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 2 new tests fail — the new peer is unconditionally appended past the cap.

- [ ] **Step 3: Implement the eviction**

Modify `add_or_update` in `jtfprotocol/gossip.py`. Replace the "new peer" branch (`if existing is None:`) with:

```python
        if existing is None:
            now = self._clock().strftime("%Y-%m-%dT%H:%M:%SZ")
            new = PeerRecord.from_wellknown_entry(entry, first_seen=now, asn=asn)
            new.confirmed_by = 1
            if len(self._peers) < MAX_PEERS:
                self._peers.append(new)
                source_set.add(source_key_id)
                return True
            # Cap reached: evict the lowest-trust existing peer if the
            # candidate outranks it. Ties resolve against the newer peer
            # so we do not thrash.
            weakest_index, weakest = min(
                enumerate(self._peers), key=lambda kv: kv[1].trust_score
            )
            if new.trust_score > weakest.trust_score:
                # Drop the evicted peer's confirmation record too.
                self._confirmations.pop(weakest.public_key_id, None)
                self._peers[weakest_index] = new
                source_set.add(source_key_id)
                return True
            # Not strong enough. Roll back the empty confirmation set we
            # created above so we don't leak state.
            if not source_set:
                self._confirmations.pop(pkid, None)
            return False
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-10: trust-weighted eviction at MAX_PEERS cap"
```

---

## Task 11: New-peer rate limit per gossip cycle

**Spec reference:** "Peer Validation" — "A server accepts at most ten new peers per gossip cycle."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_gossip_cycle_batch_admits_at_most_ten_new_peers(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    batch = gossip.CycleBatch(store, source_key_id="sha256:src", clock=clock)

    admitted = 0
    for i in range(15):
        if batch.add_or_update(
            _entry(f"peer{i}.example", f"sha256:peer{i}", trust=0.5),
            asn=64500,
        ):
            admitted += 1
    assert admitted == 10
    assert len(store.all()) == 10


def test_gossip_cycle_batch_updates_existing_peers_dont_count_against_limit(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    # Pre-seed 5 peers with source A so their confirmation sets exist.
    for i in range(5):
        store.add_or_update(
            _entry(f"existing{i}.example", f"sha256:existing{i}", trust=0.5),
            source_key_id="sha256:srcA",
        )
    batch = gossip.CycleBatch(store, source_key_id="sha256:srcB", clock=clock)
    # Re-confirming the 5 existing peers is not "new peer" admissions.
    for i in range(5):
        batch.add_or_update(
            _entry(f"existing{i}.example", f"sha256:existing{i}", trust=0.5),
        )
    # Now admit 10 new — should all fit.
    for i in range(10):
        batch.add_or_update(
            _entry(f"new{i}.example", f"sha256:new{i}", trust=0.5),
        )
    assert len(store.all()) == 15
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 2 new tests fail with `AttributeError: ... 'CycleBatch'`.

- [ ] **Step 3: Implement `CycleBatch`**

Append to `jtfprotocol/gossip.py`:

```python
MAX_NEW_PEERS_PER_CYCLE = 10
"""Spec: 'A server accepts at most ten new peers per gossip cycle.'"""


class CycleBatch:
    """Enforces per-cycle new-peer rate limit while delegating merge
    semantics to ``PeerStore``. One ``CycleBatch`` per gossip cycle.

    Rejecting a new peer because the rate limit is full is not an
    error; it is protocol design. The rejected peer will be reconsidered
    next cycle.
    """

    def __init__(
        self,
        store: PeerStore,
        source_key_id: str,
        clock: Clock | None = None,
        max_new: int = MAX_NEW_PEERS_PER_CYCLE,
    ):
        self._store = store
        self._source_key_id = source_key_id
        self._clock = clock or _default_clock
        self._max_new = max_new
        self._new_admissions = 0

    def add_or_update(self, entry: dict, asn: int = 0) -> bool:
        """Delegate to PeerStore, but decline to admit a *new* peer once
        the per-cycle new-peer quota is exhausted. Updates of already-
        tracked peers are unlimited."""
        pkid = entry["public_key_id"]
        is_new = self._store.find(pkid) is None
        if is_new and self._new_admissions >= self._max_new:
            return False
        changed = self._store.add_or_update(
            entry,
            source_key_id=self._source_key_id,
            asn=asn,
        )
        if changed and is_new and self._store.find(pkid) is not None:
            self._new_admissions += 1
        return changed
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-11: CycleBatch enforces MAX_NEW_PEERS_PER_CYCLE"
```

---

## Task 12: ASN diversity gate

**Spec reference:** "Peer Validation" — "No more than thirty percent of a server's peers should share the same ASN. This prevents a patient attacker from dominating a server's peer graph through infrastructure concentration."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_cycle_batch_rejects_new_peer_when_asn_share_would_exceed_thirty_percent(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    # Pre-seed 9 peers, 3 in ASN 64500, 3 in 64501, 3 in 64502.
    for asn in (64500, 64501, 64502):
        for i in range(3):
            store.add_or_update(
                _entry(f"asn{asn}-{i}.example", f"sha256:asn{asn}-{i}", trust=0.5),
                source_key_id="sha256:srcA",
                asn=asn,
            )
    batch = gossip.CycleBatch(store, source_key_id="sha256:srcB", clock=clock)
    # Adding a 10th peer in ASN 64500 would make it 4/10 = 40%. Reject.
    admitted = batch.add_or_update(
        _entry("dense.example", "sha256:dense", trust=0.5),
        asn=64500,
    )
    assert admitted is False
    assert store.find("sha256:dense") is None


def test_cycle_batch_allows_new_peer_when_asn_share_stays_under_thirty_percent(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    for asn in (64500, 64501, 64502):
        for i in range(3):
            store.add_or_update(
                _entry(f"asn{asn}-{i}.example", f"sha256:asn{asn}-{i}", trust=0.5),
                source_key_id="sha256:srcA",
                asn=asn,
            )
    batch = gossip.CycleBatch(store, source_key_id="sha256:srcB", clock=clock)
    admitted = batch.add_or_update(
        _entry("fresh.example", "sha256:fresh", trust=0.5),
        asn=64503,
    )
    assert admitted is True


def test_asn_diversity_gate_only_applies_to_new_admissions(tmp_path):
    """Refreshing an existing peer never trips the ASN cap."""
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    # 9 peers, 4 in ASN 64500 (would already be 44%). Insert directly.
    for i in range(9):
        asn = 64500 if i < 4 else 64500 + i
        store.add_or_update(
            _entry(f"peer{i}.example", f"sha256:peer{i}", trust=0.5),
            source_key_id="sha256:srcA",
            asn=asn,
        )
    batch = gossip.CycleBatch(store, source_key_id="sha256:srcB", clock=clock)
    # Confirming an existing peer2 (already ASN 64500) does NOT trip.
    ok = batch.add_or_update(
        _entry("peer2.example", "sha256:peer2", trust=0.5),
        asn=64500,
    )
    assert ok is True
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 3 new tests fail — dense peer is admitted, blowing the cap.

- [ ] **Step 3: Implement the ASN gate in `CycleBatch`**

Append two constants and modify `CycleBatch.add_or_update` in `jtfprotocol/gossip.py`:

```python
MAX_ASN_SHARE = 0.30
"""Spec: 'No more than thirty percent of a server's peers should share the same ASN.'"""


ASN_SHARE_FLOOR_PEERS = 3
"""Below this population the ASN cap is not enforced (three peers can
be from the same ASN early on)."""
```

Replace `CycleBatch.add_or_update` body with:

```python
    def add_or_update(self, entry: dict, asn: int = 0) -> bool:
        pkid = entry["public_key_id"]
        is_new = self._store.find(pkid) is None
        if is_new and self._new_admissions >= self._max_new:
            return False
        if is_new and asn and not self._asn_would_stay_under_cap(asn):
            return False
        changed = self._store.add_or_update(
            entry,
            source_key_id=self._source_key_id,
            asn=asn,
        )
        if changed and is_new and self._store.find(pkid) is not None:
            self._new_admissions += 1
        return changed

    def _asn_would_stay_under_cap(self, candidate_asn: int) -> bool:
        current = self._store.all()
        total_after = len(current) + 1
        if total_after <= ASN_SHARE_FLOOR_PEERS:
            return True
        same_asn = sum(1 for p in current if p.asn == candidate_asn) + 1
        return (same_asn / total_after) <= MAX_ASN_SHARE
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-12: ASN diversity gate on new peer admissions"
```

---

## Task 13: 48-hour uptime gate for propagation

**Spec reference:** "Peer Validation" — "A peer must have been observed responding for at least forty-eight hours before a server includes it in peer lists shared with others."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_peers_for_publication_excludes_peers_seen_less_than_forty_eight_hours(tmp_path):
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    # Peer A first seen 40h ago -> not eligible.
    store._peers.append(gossip.PeerRecord(
        domain="young.example",
        public_key_id="sha256:young",
        channel="global",
        last_seen="2026-06-29T08:00:00Z",
        first_seen="2026-06-29T08:00:00Z",
        trust_score=0.5,
        confirmed_by=1,
        asn=64500,
    ))
    # Peer B first seen 60h ago -> eligible.
    store._peers.append(gossip.PeerRecord(
        domain="mature.example",
        public_key_id="sha256:mature",
        channel="global",
        last_seen="2026-06-28T12:00:00Z",
        first_seen="2026-06-28T12:00:00Z",
        trust_score=0.5,
        confirmed_by=1,
        asn=64500,
    ))
    published = store.peers_for_publication()
    ids = {p["public_key_id"] for p in published}
    assert "sha256:mature" in ids
    assert "sha256:young" not in ids
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 1 new test fails with `AttributeError: ... 'peers_for_publication'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/gossip.py`:

```python
MIN_UPTIME_FOR_PROPAGATION_SECONDS = 48 * 3600
"""Spec: 'A peer must have been observed responding for at least
forty-eight hours before a server includes it in peer lists shared with
others.'"""
```

Add to `PeerStore`:

```python
    def peers_for_publication(self) -> list[dict]:
        """Return peer entries eligible to be published in this
        server's own ``/.well-known/jtf.json``. Filters out peers whose
        first-seen timestamp is less than ``MIN_UPTIME_FOR_PROPAGATION_SECONDS``
        old, per the spec's uptime gate."""
        now = self._clock()
        eligible: list[dict] = []
        for p in self._peers:
            try:
                first = _parse_iso8601_utc(p.first_seen)
            except Exception:
                continue
            age = (now - first).total_seconds()
            if age >= MIN_UPTIME_FOR_PROPAGATION_SECONDS:
                eligible.append(p.to_wellknown_entry())
        return eligible


def _parse_iso8601_utc(s: str) -> datetime:
    """Parse a subset of ISO-8601 covering the Z-suffixed UTC form we
    emit. Kept intentionally narrow — anything else is a caller bug."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 22 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-13: 48-hour uptime gate on peers_for_publication"
```

---

## Task 14: Drop dead peers after 7 days

**Spec reference:** "Gossip" — "Servers that have not responded in seven days are dropped from peer lists." "Peer Validation" — supports pruning at gossip cycle time.

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_drop_dead_peers_removes_records_older_than_seven_days(tmp_path):
    clock = FakeClock(datetime(2026, 7, 8, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    store._peers.append(gossip.PeerRecord(
        domain="dead.example",
        public_key_id="sha256:dead",
        channel="global",
        last_seen="2026-06-30T00:00:00Z",  # 8 days ago
        first_seen="2026-04-01T00:00:00Z",
        trust_score=0.5,
        confirmed_by=1,
        asn=64500,
    ))
    store._peers.append(gossip.PeerRecord(
        domain="alive.example",
        public_key_id="sha256:alive",
        channel="global",
        last_seen="2026-07-06T00:00:00Z",  # 2 days ago
        first_seen="2026-04-01T00:00:00Z",
        trust_score=0.5,
        confirmed_by=1,
        asn=64500,
    ))
    dropped = store.drop_dead_peers()
    assert dropped == ["sha256:dead"]
    ids = {p.public_key_id for p in store.all()}
    assert "sha256:alive" in ids
    assert "sha256:dead" not in ids
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 1 new test fails with `AttributeError: ... 'drop_dead_peers'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/gossip.py`:

```python
DEAD_PEER_SECONDS = 7 * 24 * 3600
"""Spec: 'Servers that have not responded in seven days are dropped from peer lists.'"""
```

Add to `PeerStore`:

```python
    def drop_dead_peers(self) -> list[str]:
        """Remove peers whose ``last_seen`` is older than
        ``DEAD_PEER_SECONDS``. Returns the list of dropped
        ``public_key_id``s. Also clears their confirmation records so
        their eviction doesn't leak state."""
        now = self._clock()
        keep: list[PeerRecord] = []
        dropped: list[str] = []
        for p in self._peers:
            try:
                seen = _parse_iso8601_utc(p.last_seen)
            except Exception:
                keep.append(p)
                continue
            age = (now - seen).total_seconds()
            if age >= DEAD_PEER_SECONDS:
                dropped.append(p.public_key_id)
                self._confirmations.pop(p.public_key_id, None)
            else:
                keep.append(p)
        self._peers = keep
        return dropped
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 23 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-14: drop_dead_peers pruning at seven-day threshold"
```

---

## Task 15: `exchange_peer_lists` — fetch a remote well-known and merge peers

**Spec reference:** "Gossip" — "It contacts those peers, fetches their peer lists, and merges them with its own."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_exchange_peer_lists_merges_remote_peers_into_local_store(tmp_path):
    _priv, _pub, doc = _make_signed_wellknown(
        domain="remote.example",
        peers=[
            {"domain": "peerA.example", "public_key_id": "sha256:peerA",
             "channel": "global", "last_seen": "2026-07-01T00:00:00Z",
             "trust_score": 0.7, "confirmed_by": 1},
            {"domain": "peerB.example", "public_key_id": "sha256:peerB",
             "channel": "global", "last_seen": "2026-07-01T00:00:00Z",
             "trust_score": 0.6, "confirmed_by": 1},
        ],
    )
    body = _json.dumps(doc).encode("utf-8")
    fetcher = FakeFetcher(get_map={
        "https://remote.example/.well-known/jtf.json": FakeResponse(200, body, {}),
    })
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)

    result = gossip.exchange_peer_lists(
        peer_domain="remote.example",
        store=store,
        fetcher=fetcher,
        clock=clock,
    )
    assert result is True
    ids = {p.public_key_id for p in store.all()}
    assert ids == {"sha256:peerA", "sha256:peerB"}


def test_exchange_peer_lists_returns_false_when_remote_unreachable(tmp_path):
    fetcher = FakeFetcher()  # no route -> 404
    clock = FakeClock(datetime(2026, 7, 1, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    result = gossip.exchange_peer_lists(
        peer_domain="unreachable.example",
        store=store,
        fetcher=fetcher,
        clock=clock,
    )
    assert result is False
    assert store.all() == []
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 2 new tests fail with `AttributeError: ... 'exchange_peer_lists'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/gossip.py`:

```python
def exchange_peer_lists(
    peer_domain: str,
    store: PeerStore,
    fetcher: Fetcher | None = None,
    clock: Clock | None = None,
    timeout: float = 10.0,
) -> bool:
    """Fetch ``peer_domain``'s well-known document and merge its peer
    list into ``store`` using a single ``CycleBatch``.

    Returns True if the well-known was successfully fetched and at
    least one peer was merged or updated. Returns False on any fetch
    or verification failure. Never raises.

    The remote's ``server.public_key_id`` is used as the ``source_key_id``
    for confirmation counting.
    """
    doc = fetch_and_verify_well_known(peer_domain, fetcher=fetcher, timeout=timeout)
    if doc is None:
        return False
    source_key_id = doc.get("server", {}).get("public_key_id", "")
    if not source_key_id:
        return False
    remote_asn_hint = int(doc.get("server", {}).get("asn", 0) or 0)
    # The remote itself is a peer we've now heard from directly; enter it too.
    self_entry = {
        "domain": doc["server"]["domain"],
        "public_key_id": source_key_id,
        "channel": doc["server"].get("channel", "global"),
        "last_seen": (clock or _default_clock)().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trust_score": 0.0,
        "confirmed_by": 0,
    }
    batch = CycleBatch(store, source_key_id=source_key_id, clock=clock)
    changed = batch.add_or_update(self_entry, asn=remote_asn_hint)
    for entry in doc.get("peers", []):
        try:
            if batch.add_or_update(entry):
                changed = True
        except Exception:
            continue
    return changed
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 25 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-15: exchange_peer_lists — fetch remote well-known and merge peers"
```

---

## Task 16: `build_announcement` — canonical-JSON signed envelope

**Spec reference:** "Fact Propagation" (lines 409–427) — announcement is the 6-field envelope + signature.

**Files:**
- Create: `jtfprotocol/announcements.py`
- Create: `tests/test_announcements.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_announcements.py`:

```python
"""Tests for jtfprotocol.announcements."""
from __future__ import annotations

import base64
import json

from jtfprotocol import announcements, identity


def test_build_announcement_populates_all_fields():
    priv, pub = identity.generate_keypair()
    server_key_id = identity.public_key_id(pub)
    ann = announcements.build_announcement(
        fact_id="sha256:e3b0c44",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=server_key_id,
        priv=priv,
    )
    assert ann["type"] == "fact_announcement"
    assert ann["fact_id"] == "sha256:e3b0c44"
    assert ann["occurred_at"] == "2026-04-18T14:30:00Z"
    assert ann["channel"] == "global"
    assert ann["server_domain"] == "jtfnews.org"
    assert ann["server_key_id"] == server_key_id
    assert isinstance(ann["signature"], str)
    assert len(base64.b64decode(ann["signature"])) == 64


def test_build_announcement_is_deterministic_for_same_input():
    priv, pub = identity.generate_keypair()
    server_key_id = identity.public_key_id(pub)
    args = dict(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=server_key_id,
        priv=priv,
    )
    a = announcements.build_announcement(**args)
    b = announcements.build_announcement(**args)
    assert a == b
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_announcements.py -v
```

Expected: 2 new tests fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `jtfprotocol/announcements.py`:

```python
"""JTF Protocol fact announcement envelope.

When a server publishes a new fact, it pushes a lightweight
announcement to its known peers. Peers use the announcement to decide
whether to fetch the full fact from the announcing server's feed.

The announcement is signed by the announcing server's private key over
the six-field payload; peers verify with the ``server_key_id`` looked up
in the sender's ``/.well-known/jtf.json``.

See documentation/Protocol Ver 1.0 CURRENT.md, section
"Fact Propagation".
"""
from __future__ import annotations

import base64
import copy

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from jtfprotocol import identity as _identity
from jtfprotocol.fact import canonical_json


ANNOUNCEMENT_TYPE = "fact_announcement"


def build_announcement(
    fact_id: str,
    occurred_at: str,
    channel: str,
    server_domain: str,
    server_key_id: str,
    priv: Ed25519PrivateKey,
) -> dict:
    """Build a signed fact-announcement envelope. Deterministic for a
    given input (the signature bytes are deterministic because Ed25519
    uses deterministic RFC 8032 signing)."""
    envelope = {
        "type": ANNOUNCEMENT_TYPE,
        "fact_id": fact_id,
        "occurred_at": occurred_at,
        "channel": channel,
        "server_domain": server_domain,
        "server_key_id": server_key_id,
        "signature": "",
    }
    to_sign = canonical_json(envelope).encode("utf-8")
    sig = _identity.sign(priv, to_sign)
    envelope["signature"] = base64.b64encode(sig).decode("ascii")
    return envelope
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_announcements.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-16: build_announcement signed envelope"
```

---

## Task 17: `verify_announcement`

**Spec reference:** "Fact Propagation" — peers reject unsigned or wrongly-signed announcements before doing any I/O.

**Files:**
- Modify: `jtfprotocol/announcements.py`
- Modify: `tests/test_announcements.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_announcements.py`:

```python
def test_verify_announcement_accepts_valid_signature():
    priv, pub = identity.generate_keypair()
    ann = announcements.build_announcement(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=identity.public_key_id(pub),
        priv=priv,
    )
    assert announcements.verify_announcement(ann, pub) is True


def test_verify_announcement_rejects_tampered_fact_id():
    priv, pub = identity.generate_keypair()
    ann = announcements.build_announcement(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=identity.public_key_id(pub),
        priv=priv,
    )
    ann["fact_id"] = "sha256:evil"
    assert announcements.verify_announcement(ann, pub) is False


def test_verify_announcement_rejects_wrong_public_key():
    priv, _pub = identity.generate_keypair()
    _priv2, pub2 = identity.generate_keypair()
    ann = announcements.build_announcement(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=identity.public_key_id(_pub),
        priv=priv,
    )
    assert announcements.verify_announcement(ann, pub2) is False


def test_verify_announcement_rejects_missing_type_field():
    priv, pub = identity.generate_keypair()
    ann = announcements.build_announcement(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=identity.public_key_id(pub),
        priv=priv,
    )
    del ann["type"]
    assert announcements.verify_announcement(ann, pub) is False
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_announcements.py -v
```

Expected: 4 new tests fail with `AttributeError: ... 'verify_announcement'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/announcements.py`:

```python
def verify_announcement(ann: dict, pub: Ed25519PublicKey) -> bool:
    """Verify a fact-announcement envelope's Ed25519 signature.

    Returns True if the envelope's ``type`` is ``fact_announcement`` and
    the signature is valid over the canonical JSON of the envelope with
    the signature field emptied. Returns False otherwise. Does not raise.
    """
    try:
        if ann.get("type") != ANNOUNCEMENT_TYPE:
            return False
        to_verify = copy.deepcopy(ann)
        sig_b64 = to_verify.get("signature", "")
        to_verify["signature"] = ""
        sig = base64.b64decode(sig_b64)
        payload = canonical_json(to_verify).encode("utf-8")
        return _identity.verify(pub, payload, sig)
    except Exception:
        return False
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_announcements.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-17: verify_announcement"
```

---

## Task 18: `send_announcement` — POST to peer's `/announcements`

**Spec reference:** "Fact Propagation" + "The Well-Known Endpoint" `feeds.announcements` — the endpoint where peers accept announcement POSTs.

**Files:**
- Modify: `jtfprotocol/announcements.py`
- Modify: `tests/test_announcements.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_announcements.py`:

```python
from jtfprotocol import gossip


def test_send_announcement_posts_to_peer_announcements_endpoint():
    priv, pub = identity.generate_keypair()
    ann = announcements.build_announcement(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=identity.public_key_id(pub),
        priv=priv,
    )

    # Use the FakeFetcher pattern from test_gossip.
    from tests.test_gossip import FakeFetcher, FakeResponse

    fetcher = FakeFetcher(post_map={
        "https://peer.example/announcements": FakeResponse(202, b"", {}),
    })
    ok = announcements.send_announcement(
        peer_domain="peer.example",
        announcement=ann,
        fetcher=fetcher,
    )
    assert ok is True
    assert fetcher.post_calls
    posted_url, posted_body = fetcher.post_calls[0]
    assert posted_url == "https://peer.example/announcements"
    assert json.loads(posted_body.decode("utf-8"))["fact_id"] == "sha256:x"


def test_send_announcement_uses_custom_endpoint_path():
    priv, pub = identity.generate_keypair()
    ann = announcements.build_announcement(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=identity.public_key_id(pub),
        priv=priv,
    )
    from tests.test_gossip import FakeFetcher, FakeResponse

    fetcher = FakeFetcher(post_map={
        "https://peer.example/custom-announcements": FakeResponse(200, b"", {}),
    })
    ok = announcements.send_announcement(
        peer_domain="peer.example",
        announcement=ann,
        fetcher=fetcher,
        endpoint_path="/custom-announcements",
    )
    assert ok is True


def test_send_announcement_returns_false_on_http_error():
    priv, pub = identity.generate_keypair()
    ann = announcements.build_announcement(
        fact_id="sha256:x",
        occurred_at="2026-04-18T14:30:00Z",
        channel="global",
        server_domain="jtfnews.org",
        server_key_id=identity.public_key_id(pub),
        priv=priv,
    )
    from tests.test_gossip import FakeFetcher, FakeResponse

    fetcher = FakeFetcher(post_map={
        "https://peer.example/announcements": FakeResponse(500, b"boom", {}),
    })
    ok = announcements.send_announcement(
        peer_domain="peer.example",
        announcement=ann,
        fetcher=fetcher,
    )
    assert ok is False
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_announcements.py -v
```

Expected: 3 new tests fail with `AttributeError: ... 'send_announcement'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/announcements.py`:

```python
import json

from jtfprotocol.gossip import Fetcher, RequestsFetcher


DEFAULT_ANNOUNCEMENTS_PATH = "/announcements"


def send_announcement(
    peer_domain: str,
    announcement: dict,
    fetcher: Fetcher | None = None,
    endpoint_path: str = DEFAULT_ANNOUNCEMENTS_PATH,
    timeout: float = 10.0,
) -> bool:
    """POST a signed announcement to ``https://{peer_domain}{endpoint_path}``.

    Returns True on any 2xx response. Returns False on any HTTP or
    transport error. Never raises. Callers may look up the actual path
    from the peer's own ``/.well-known/jtf.json`` ``feeds.announcements``
    and pass it as ``endpoint_path``.
    """
    fetcher = fetcher or RequestsFetcher()
    url = f"https://{peer_domain}{endpoint_path}"
    try:
        body = json.dumps(announcement).encode("utf-8")
        resp = fetcher.post(url, body=body, timeout=timeout)
        return 200 <= resp.status_code < 300
    except Exception:
        return False
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_announcements.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-18: send_announcement over injected Fetcher"
```

---

## Task 19: `fetch_fact_by_id` — pull a full fact from a peer's feed

**Spec reference:** "Fact Propagation" — "Peers that have not already seen this fact ID fetch the full fact from the announcing server's JSON feed."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
from jtfprotocol import fact as _fact


def test_fetch_fact_by_id_returns_matching_fact_from_feed():
    # Build a valid signed fact.
    priv, pub = identity.generate_keypair()
    fact_dict = {
        "jtf_version": 1,
        "id": "",
        "fact": "President Smith signed the trade agreement.",
        "occurred_at": "2026-07-01T14:30:00Z",
        "published_at": "2026-07-01T15:00:00Z",
        "verification_method": {"backend": "ollama"},
        "structured_extraction": {"actor": "President Smith", "action": "signed"},
        "sources": [
            {"url": "https://a.example/1", "publisher": "A"},
            {"url": "https://b.example/1", "publisher": "B"},
        ],
        "channel": "global",
        "server": {
            "domain": "remote.example",
            "public_key_id": identity.public_key_id(pub),
        },
        "algorithm": "Ed25519",
        "signature": "",
    }
    signed = _fact.sign_fact(fact_dict, priv)
    feed = {"facts": [signed]}
    fetcher = FakeFetcher(get_map={
        "https://remote.example/stories.json": FakeResponse(
            200, _json.dumps(feed).encode("utf-8"), {},
        ),
    })

    result = gossip.fetch_fact_by_id(
        peer_domain="remote.example",
        fact_id=signed["id"],
        feed_path="/stories.json",
        fetcher=fetcher,
    )
    assert result is not None
    assert result["fact"] == signed["fact"]


def test_fetch_fact_by_id_returns_none_when_id_not_in_feed():
    feed = {"facts": []}
    fetcher = FakeFetcher(get_map={
        "https://remote.example/stories.json": FakeResponse(
            200, _json.dumps(feed).encode("utf-8"), {},
        ),
    })
    result = gossip.fetch_fact_by_id(
        peer_domain="remote.example",
        fact_id="sha256:notpresent",
        feed_path="/stories.json",
        fetcher=fetcher,
    )
    assert result is None


def test_fetch_fact_by_id_returns_none_on_http_error():
    fetcher = FakeFetcher()  # 404 by default
    assert gossip.fetch_fact_by_id(
        peer_domain="remote.example",
        fact_id="sha256:x",
        feed_path="/stories.json",
        fetcher=fetcher,
    ) is None
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 3 new tests fail with `AttributeError: ... 'fetch_fact_by_id'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/gossip.py`:

```python
def fetch_fact_by_id(
    peer_domain: str,
    fact_id: str,
    feed_path: str,
    fetcher: Fetcher | None = None,
    timeout: float = 10.0,
) -> dict | None:
    """Fetch ``peer_domain``'s facts feed and return the fact with the
    given ``fact_id``. Returns None if the fetch fails, the feed is
    malformed, or the fact is not present. Never raises.

    Signature verification is intentionally NOT performed here; callers
    are responsible for verifying with the sender's public key looked up
    from the sender's ``/.well-known/jtf.json``. Keeping this function
    signature-agnostic lets it be re-used for archive lookups and other
    feeds that may carry the same fact under a different signing key.
    """
    fetcher = fetcher or RequestsFetcher()
    url = f"https://{peer_domain}{feed_path}"
    try:
        resp = fetcher.get(url, timeout=timeout)
        if resp.status_code != 200:
            return None
        feed = resp.json()
    except Exception:
        return None
    for entry in feed.get("facts", []):
        if entry.get("id") == fact_id:
            return entry
    return None
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 28 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-19: fetch_fact_by_id — pull full fact from a peer feed"
```

---

## Task 20: `run_gossip_cycle` orchestrator

**Spec reference:** "Gossip" — "Every thirty minutes, aligned with the JTF update cadence, it refreshes known peers."

**Files:**
- Modify: `jtfprotocol/gossip.py`
- Modify: `tests/test_gossip.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gossip.py`:

```python
def test_run_gossip_cycle_drops_dead_and_refreshes_and_returns_stats(tmp_path):
    _priv, _pub, doc = _make_signed_wellknown(
        domain="remote.example",
        peers=[
            {"domain": "peerA.example", "public_key_id": "sha256:peerA",
             "channel": "global", "last_seen": "2026-07-08T00:00:00Z",
             "trust_score": 0.7, "confirmed_by": 1},
        ],
    )
    body = _json.dumps(doc).encode("utf-8")
    fetcher = FakeFetcher(get_map={
        "https://remote.example/.well-known/jtf.json": FakeResponse(200, body, {}),
    })
    clock = FakeClock(datetime(2026, 7, 8, tzinfo=timezone.utc))
    store = gossip.PeerStore(path=tmp_path / "peers.json", clock=clock)
    # Pre-seed one dead peer (last_seen 8 days ago).
    store._peers.append(gossip.PeerRecord(
        domain="dead.example",
        public_key_id="sha256:dead",
        channel="global",
        last_seen="2026-06-30T00:00:00Z",
        first_seen="2026-04-01T00:00:00Z",
        trust_score=0.5,
        confirmed_by=1,
        asn=64500,
    ))

    stats = gossip.run_gossip_cycle(
        seed_domains=("remote.example",),
        store=store,
        fetcher=fetcher,
        clock=clock,
    )
    assert stats["dropped"] == 1
    assert stats["contacted"] == 1
    assert stats["merged_peers"] >= 1
    assert store.find("sha256:dead") is None
    assert store.find("sha256:peerA") is not None


def test_run_gossip_cycle_persists_the_store(tmp_path):
    _priv, _pub, doc = _make_signed_wellknown(
        domain="remote.example",
        peers=[],
    )
    body = _json.dumps(doc).encode("utf-8")
    fetcher = FakeFetcher(get_map={
        "https://remote.example/.well-known/jtf.json": FakeResponse(200, body, {}),
    })
    clock = FakeClock(datetime(2026, 7, 8, tzinfo=timezone.utc))
    path = tmp_path / "peers.json"
    store = gossip.PeerStore(path=path, clock=clock)
    gossip.run_gossip_cycle(
        seed_domains=("remote.example",),
        store=store,
        fetcher=fetcher,
        clock=clock,
    )
    assert path.exists()
    reloaded = gossip.PeerStore(path=path, clock=clock)
    assert reloaded.find(doc["server"]["public_key_id"]) is not None
```

- [ ] **Step 2: Run and confirm failure**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 2 new tests fail with `AttributeError: ... 'run_gossip_cycle'`.

- [ ] **Step 3: Implement**

Append to `jtfprotocol/gossip.py`:

```python
GOSSIP_CYCLE_SECONDS = 30 * 60
"""Spec: 'Every thirty minutes, aligned with the JTF update cadence,
it refreshes known peers.' Phase 2 exposes the value; Phase 5 wires it
into the main loop."""


def run_gossip_cycle(
    seed_domains: tuple[str, ...],
    store: PeerStore,
    fetcher: Fetcher | None = None,
    clock: Clock | None = None,
    timeout: float = 10.0,
) -> dict:
    """Run one 30-minute gossip cycle:

      1. Drop dead peers (>= 7 days without response).
      2. Contact each seed domain and each surviving peer's domain,
         fetching their well-known and merging peer lists.
      3. Persist the store.

    Returns a stats dict::

        {"dropped": N, "contacted": N, "reachable": N, "merged_peers": N}

    Callers schedule this every ``GOSSIP_CYCLE_SECONDS``. Phase 5 wires
    the scheduling into ``main.py``'s existing 30-minute loop.
    """
    fetcher = fetcher or RequestsFetcher()
    clock = clock or _default_clock

    dropped = store.drop_dead_peers()

    to_contact: list[str] = []
    seen: set[str] = set()
    for d in seed_domains:
        if d not in seen:
            to_contact.append(d)
            seen.add(d)
    for p in store.all():
        if p.domain not in seen:
            to_contact.append(p.domain)
            seen.add(p.domain)

    contacted = 0
    reachable = 0
    peers_before = {p.public_key_id for p in store.all()}
    for domain in to_contact:
        contacted += 1
        if exchange_peer_lists(
            peer_domain=domain,
            store=store,
            fetcher=fetcher,
            clock=clock,
            timeout=timeout,
        ):
            reachable += 1
    peers_after = {p.public_key_id for p in store.all()}
    merged_peers = len(peers_after - peers_before)

    store.save()
    return {
        "dropped": len(dropped),
        "contacted": contacted,
        "reachable": reachable,
        "merged_peers": merged_peers,
    }
```

- [ ] **Step 4: Run and confirm pass**

```bash
venv/bin/pytest tests/test_gossip.py -v
```

Expected: 30 passed.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE2-20: run_gossip_cycle orchestrator with drop+refresh+persist"
```

---

## Task 21: Public exports and README update

**Spec reference:** Ease of Phase 5 integration — `from jtfprotocol import gossip, seeds, announcements` should just work.

**Files:**
- Modify: `jtfprotocol/__init__.py`
- Modify: `jtfprotocol/README.md`

- [ ] **Step 1: Update `__init__.py`**

Replace `jtfprotocol/__init__.py` with:

```python
"""JTF Protocol reference implementation.

Ed25519 identity, canonical fact format, deterministic methodology
compliance checks, pluggable extraction backends, well-known endpoint,
seed and DNS discovery, peer store and gossip cycle, and fact
announcement envelope.

See documentation/Protocol Ver 1.0 CURRENT.md for the authoritative
spec.

Typical use (Phase 5 integration):

    from jtfprotocol import (
        identity, fact, compliance, extraction, well_known,
        seeds, gossip, announcements,
    )

    priv, pub = identity.generate_keypair()
    store = gossip.PeerStore(path=Path("data/peers.json"))
    gossip.run_gossip_cycle(seeds.SEED_DOMAINS, store)
"""

__version__ = "0.2.0"

from jtfprotocol import (
    announcements,
    compliance,
    extraction,
    fact,
    gossip,
    identity,
    prompts,
    seeds,
    well_known,
)

__all__ = [
    "__version__",
    "announcements",
    "compliance",
    "extraction",
    "fact",
    "gossip",
    "identity",
    "prompts",
    "seeds",
    "well_known",
]
```

- [ ] **Step 2: Update the README**

Edit `jtfprotocol/README.md`. Replace the "Not included in Phase 1" block with:

```markdown
## Included as of Phase 2

- Seed domain list and DNS TXT/SRV fallback discovery (`seeds.py`)
- HTTP `Fetcher` protocol and `RequestsFetcher` default (`gossip.py`)
- `fetch_and_verify_well_known` (`gossip.py`)
- `PeerRecord`, `PeerStore` with JSON persistence, trust-weighted
  eviction, new-peer rate limit, ASN diversity gate, 48-hour uptime
  gate for publication, seven-day dead-peer drop (`gossip.py`)
- `exchange_peer_lists`, `fetch_fact_by_id`, `run_gossip_cycle`
  (`gossip.py`)
- `build_announcement`, `verify_announcement`, `send_announcement`
  (`announcements.py`)

## Not included as of Phase 2

- Trust score computation and cluster detection (Phase 3)
- Corrections, key rotation, revocation, key loss recovery (Phase 4)
- Integration with `main.py` (Phase 5)
- Wire-protocol appendix, trust algorithm reference (Phase 6)
```

- [ ] **Step 3: Run the whole suite**

```bash
venv/bin/pytest -v
```

Expected: 74 (Phase 1) + Phase 2 tests all pass. Total should be around 74 + 30 (gossip) + 9 (announcements) + 14 (seeds) = 127 passing.

- [ ] **Step 4: Commit**

```bash
./bu.sh "PHASE2-21: public exports for seeds, gossip, announcements; README update"
```

---

## Task 22: End-to-end smoke test — two servers, bootstrap, exchange, announce, pull

**Spec reference:** Whole discovery + gossip loop end-to-end. This is the acceptance test for Phase 2.

**Files:**
- Create: `tests/test_smoke_phase2.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_smoke_phase2.py`:

```python
"""End-to-end Phase 2 smoke test.

Simulates two JTF servers (Alpha and Bravo) using only in-memory fakes:

  1. Alpha bootstraps from a seed pointing at Bravo.
  2. Alpha fetches Bravo's well-known and merges Bravo into its peer store.
  3. Alpha publishes a fact; sends a signed announcement to Bravo.
  4. Bravo verifies the announcement and pulls the full fact from
     Alpha's simulated stories.json feed.
  5. The pulled fact's Ed25519 signature verifies under Alpha's public
     key.

No real network, no real DNS, no wall clock.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jtfprotocol import announcements, fact, gossip, identity, well_known


@dataclass
class FakeResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class FakeFetcher:
    def __init__(self, get_map=None, post_map=None):
        self.get_map = get_map or {}
        self.post_map = post_map or {}
        self.posts: list[tuple[str, bytes]] = []

    def get(self, url, timeout=10.0):
        entry = self.get_map.get(url)
        return entry if entry is not None else FakeResponse(404, b"")

    def post(self, url, body, timeout=10.0):
        self.posts.append((url, body))
        entry = self.post_map.get(url)
        return entry if entry is not None else FakeResponse(404, b"")


class FakeClock:
    def __init__(self, now):
        self._now = now

    def __call__(self):
        return self._now


def _make_wellknown(domain: str, priv, pub, peers=None):
    return well_known.generate_well_known(
        priv=priv, pub=pub,
        server_info={
            "domain": domain,
            "channel": "global",
            "name": f"{domain}",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 64500,
            "location_country": "US",
        },
        extraction_info={
            "backend": "ollama",
            "model": "ollama:qwen2.5:72b-instruct-q5_K_M",
            "prompt_version": "jtf-extract-v3",
        },
        feeds={
            "facts_rss": "/feed.xml",
            "facts_json": "/stories.json",
            "corrections": "/corrections.json",
            "archive": "/archive/index.json",
            "announcements": "/announcements",
        },
        peers=peers or [],
    )


def test_phase2_two_server_end_to_end(tmp_path):
    alpha_priv, alpha_pub = identity.generate_keypair()
    bravo_priv, bravo_pub = identity.generate_keypair()

    alpha_key_id = identity.public_key_id(alpha_pub)
    bravo_key_id = identity.public_key_id(bravo_pub)

    # Alpha's fact.
    alpha_fact = {
        "jtf_version": 1,
        "id": "",
        "fact": "The Federal Reserve announced a rate change of twenty-five basis points.",
        "occurred_at": "2026-07-08T14:30:00Z",
        "published_at": "2026-07-08T14:35:00Z",
        "verification_method": {"backend": "ollama", "prompt_version": "jtf-extract-v3"},
        "structured_extraction": {"actor": "Federal Reserve", "action": "announced"},
        "sources": [
            {"url": "https://a.example/1", "publisher": "A News"},
            {"url": "https://b.example/1", "publisher": "B News"},
        ],
        "channel": "global",
        "server": {"domain": "alpha.example", "public_key_id": alpha_key_id},
        "algorithm": "Ed25519",
        "signature": "",
    }
    alpha_fact_signed = fact.sign_fact(alpha_fact, alpha_priv)

    # Alpha's well-known lists no peers yet (it just came online).
    alpha_wellknown = _make_wellknown("alpha.example", alpha_priv, alpha_pub, peers=[])
    # Bravo's well-known (Alpha will bootstrap from it via seed).
    bravo_wellknown = _make_wellknown("bravo.example", bravo_priv, bravo_pub, peers=[])

    # Wire the fetcher: Alpha and Bravo each expose their well-known;
    # Alpha exposes its facts feed; Bravo exposes an announcements POST.
    fetcher = FakeFetcher(
        get_map={
            "https://bravo.example/.well-known/jtf.json": FakeResponse(
                200, json.dumps(bravo_wellknown).encode("utf-8"),
            ),
            "https://alpha.example/.well-known/jtf.json": FakeResponse(
                200, json.dumps(alpha_wellknown).encode("utf-8"),
            ),
            "https://alpha.example/stories.json": FakeResponse(
                200, json.dumps({"facts": [alpha_fact_signed]}).encode("utf-8"),
            ),
        },
        post_map={
            "https://bravo.example/announcements": FakeResponse(202, b""),
        },
    )
    clock = FakeClock(datetime(2026, 7, 8, tzinfo=timezone.utc))

    # 1. Alpha bootstraps from a seed pointing at Bravo. Since Bravo is
    # not in the hard-coded SEED_DOMAINS, we pass it in as a candidate
    # via the store bootstrap path.
    alpha_store = gossip.PeerStore(path=tmp_path / "alpha_peers.json", clock=clock)
    stats = gossip.run_gossip_cycle(
        seed_domains=("bravo.example",),
        store=alpha_store,
        fetcher=fetcher,
        clock=clock,
    )
    # Alpha should have contacted Bravo and merged Bravo as a peer.
    assert stats["reachable"] == 1
    assert alpha_store.find(bravo_key_id) is not None

    # 2. Alpha publishes: sign a fact-announcement and send it to Bravo.
    ann = announcements.build_announcement(
        fact_id=alpha_fact_signed["id"],
        occurred_at=alpha_fact_signed["occurred_at"],
        channel=alpha_fact_signed["channel"],
        server_domain="alpha.example",
        server_key_id=alpha_key_id,
        priv=alpha_priv,
    )
    ok = announcements.send_announcement(
        peer_domain="bravo.example",
        announcement=ann,
        fetcher=fetcher,
    )
    assert ok is True

    # 3. Bravo receives (simulated by grabbing the last POST body) and
    # verifies the announcement signature by looking up Alpha's key.
    posted_url, posted_body = fetcher.posts[-1]
    received_ann = json.loads(posted_body.decode("utf-8"))
    alpha_pub_from_wire = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(alpha_wellknown["server"]["public_key"])
    )
    assert announcements.verify_announcement(received_ann, alpha_pub_from_wire) is True

    # 4. Bravo pulls the full fact from Alpha's feed.
    pulled = gossip.fetch_fact_by_id(
        peer_domain="alpha.example",
        fact_id=received_ann["fact_id"],
        feed_path="/stories.json",
        fetcher=fetcher,
    )
    assert pulled is not None
    assert pulled["fact"].startswith("The Federal Reserve")

    # 5. Bravo verifies the fact signature under Alpha's public key.
    assert fact.verify_fact(pulled, alpha_pub_from_wire) is True
```

- [ ] **Step 2: Run and confirm pass**

```bash
venv/bin/pytest tests/test_smoke_phase2.py -v
```

Expected: 1 passed on the first run because every module is already complete.

- [ ] **Step 3: Run the whole suite**

```bash
venv/bin/pytest -v
```

Expected: 74 (Phase 1) + Phase 2 tests. Every one passes.

- [ ] **Step 4: Commit**

```bash
./bu.sh "PHASE2-22: end-to-end smoke test — bootstrap, exchange, announce, pull"
```

---

## Phase 2 Completion Criteria

Phase 2 is done when all of the following are true:

- [ ] All 22 tasks are committed on `feature/jtf-protocol-phase2`.
- [ ] `venv/bin/pytest -v` passes with zero failures.
- [ ] `jtfprotocol/` package still imports from the repo root; the new `seeds`, `gossip`, `announcements` submodules are exported.
- [ ] `main.py` is unchanged. Live site can resume on `feature/jtf-protocol` without any interaction from this branch.
- [ ] `documentation/Protocol Ver 1.0 CURRENT.md` is unchanged. No silent spec drift.

At that point the branch is ready for merge consideration back to `feature/jtf-protocol` — or for Phase 3 work to proceed on a new branch off Phase 2's HEAD.

---

## Next Phases (Roadmap)

**Phase 3 — Trust System.** Trust score computation (corroboration, source verification, consistency, methodology compliance); maturity and stability factors; availability separate from trust; source-centric trust; continuous-score Sybil cluster detection; client trust aggregation (weighted median, low-N fallback); circuit breaker for fabrications; verification credit sharing. New module `jtfprotocol/trust.py`.

**Phase 4 — Corrections & Resilience.** Correction record format, trust-gated broadcast, per-target rate limits; key rotation (72-hour announcement + domain binding), revocation, key loss recovery; P2P evidence storage and retrieval; flood protection enforcement.

**Phase 5 — Integration with `main.py`.** Adapt the existing publishing path to produce Phase 1-format facts. Wire `well_known.generate_well_known` into server startup. Integrate `run_gossip_cycle` into the 30-minute update loop. Preserve existing `feed.xml` / `stories.json` consumers during transition (dual-write, then cut over).

**Phase 6 — Companion Documents.** Wire Protocol Specification (HTTP endpoints, request/response, error codes, version negotiation); Appendix A (Prohibited Adjective Lists); Appendix B (Controlled Action Vocabulary); Appendix C (URL Normalization Rules); Trust Algorithm Reference (pseudocode, worked examples, cluster detection); Operator deployment guide.

---

## Self-Review

**Spec coverage.** Every Phase 2 requirement is implemented by a named task:

- "Seed Domains" (lines 429–439): Task 1 (constants), Task 4 (composite).
- "Fallback Discovery" — TXT (line 445): Task 2. SRV (line 446): Task 3.
- "The Well-Known Endpoint" (lines 333–384) — fetch + signature verify: Task 6.
- "Gossip" (lines 386–397) — refresh cycle, drop dead peers: Task 14, Task 20.
- "Peer Validation" (lines 399–407) — max 100 (Task 10), rate limit 10/cycle (Task 11), ASN 30% (Task 12), 48h uptime (Task 13), `confirmed_by` (Task 9).
- "Fact Propagation" (lines 409–427) — announcement envelope (Task 16, 17), push (Task 18), pull (Task 19).
- End-to-end integration test (Task 22).

**Placeholder scan.** No step says "add appropriate error handling" without showing it. No step says "implement later." Every code step contains the actual code to write.

**Type consistency.** `Fetcher`, `Response`, `Clock`, `RequestsFetcher`, `Resolver`, `DnspythonResolver`, `PeerRecord`, `PeerStore`, `CycleBatch`, `SEED_DOMAINS`, `discover_seeds`, `lookup_txt_seed`, `lookup_srv_seed`, `fetch_and_verify_well_known`, `exchange_peer_lists`, `fetch_fact_by_id`, `run_gossip_cycle`, `build_announcement`, `verify_announcement`, `send_announcement`, `ANNOUNCEMENT_TYPE`, `MAX_PEERS`, `MAX_NEW_PEERS_PER_CYCLE`, `MAX_ASN_SHARE`, `MIN_UPTIME_FOR_PROPAGATION_SECONDS`, `DEAD_PEER_SECONDS`, `GOSSIP_CYCLE_SECONDS`, `WELL_KNOWN_PATH`, `DEFAULT_ANNOUNCEMENTS_PATH` — every name used in a later task is defined in an earlier task.

**Live-site safety.** No task modifies `main.py`, `feed.xml`, `stories.json`, `docs/`, or any live-site file. Every commit lands on `feature/jtf-protocol-phase2`, isolated in the worktree. Merge back to `feature/jtf-protocol` (or `main`) is a decision at the end of Phase 2, not during it.
