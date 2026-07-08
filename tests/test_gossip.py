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

    # Each peer gets a unique ASN so the ASN diversity gate is never the
    # binding constraint; the rate limit of 10 is what we are testing here.
    admitted = 0
    for i in range(15):
        if batch.add_or_update(
            _entry(f"peer{i}.example", f"sha256:peer{i}", trust=0.5),
            asn=64500 + i,
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
    assert {"sha256:peerA", "sha256:peerB"}.issubset(ids)
    # Remote server is also merged (it's a peer we've now heard from directly).
    remote_key_id = doc["server"]["public_key_id"]
    assert remote_key_id in ids


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
