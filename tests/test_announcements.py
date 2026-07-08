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
