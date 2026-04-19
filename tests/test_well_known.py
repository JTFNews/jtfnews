"""Tests for jtfprotocol.well_known."""
import json

from jtfprotocol import identity, well_known


def test_generate_well_known_has_required_top_level_fields():
    priv, pub = identity.generate_keypair()
    doc = well_known.generate_well_known(
        priv=priv,
        pub=pub,
        server_info={
            "domain": "example.com",
            "channel": "global",
            "name": "Example Server",
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
        peers=[],
    )
    assert doc["jtf_protocol_version"] == 1
    assert doc["server"]["domain"] == "example.com"
    assert doc["server"]["public_key_id"].startswith("sha256:")
    assert doc["extraction"]["backend"] == "ollama"
    assert "signature" in doc


def test_generate_well_known_is_verifiable():
    priv, pub = identity.generate_keypair()
    doc = well_known.generate_well_known(
        priv=priv,
        pub=pub,
        server_info={
            "domain": "example.com",
            "channel": "global",
            "name": "Example Server",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 24940,
            "location_country": "US",
        },
        extraction_info={"backend": "anthropic", "model": "anthropic:claude-haiku:4-5", "prompt_version": "jtf-extract-v3"},
        feeds={"facts_rss": "/feed.xml"},
        peers=[],
    )
    assert well_known.verify_well_known(doc, pub) is True


def test_generate_well_known_rejects_invalid_backend():
    priv, pub = identity.generate_keypair()
    import pytest

    with pytest.raises(ValueError, match="backend"):
        well_known.generate_well_known(
            priv=priv,
            pub=pub,
            server_info={
                "domain": "example.com",
                "channel": "global",
                "name": "Example",
                "started_at": "2026-04-19T00:00:00Z",
                "node_type": "full",
                "asn": 0,
                "location_country": "US",
            },
            extraction_info={"backend": "bogus", "model": "x", "prompt_version": "v"},
            feeds={},
            peers=[],
        )
