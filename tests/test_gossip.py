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
    # Now admit 10 new -- should all fit.
    for i in range(10):
        batch.add_or_update(
            _entry(f"new{i}.example", f"sha256:new{i}", trust=0.5),
        )
    assert len(store.all()) == 15
