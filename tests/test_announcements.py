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
