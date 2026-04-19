"""End-to-end smoke test across every Phase 1 module.

Proves that the pieces compose: generate an identity, render the
well-known document, sign a fact that passes deterministic compliance,
and verify that fact.
"""
from unittest.mock import MagicMock

from jtfprotocol import compliance, extraction, fact, identity, well_known


def test_phase1_composition(sample_fact_dict, monkeypatch):
    # 1) Identity
    priv, pub = identity.generate_keypair()
    kid = identity.public_key_id(pub)
    assert kid.startswith("sha256:")

    # 2) Well-known endpoint for this server
    wk = well_known.generate_well_known(
        priv=priv,
        pub=pub,
        server_info={
            "domain": "jtfnews.org",
            "channel": "global",
            "name": "JTF News",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 0,
            "location_country": "US",
        },
        extraction_info={
            "backend": "ollama",
            "model": "ollama:qwen2.5:72b-instruct-q5_K_M",
            "prompt_version": "jtf-extract-v3",
        },
        feeds={"facts_rss": "/feed.xml"},
        peers=[],
    )
    assert well_known.verify_well_known(wk, pub) is True

    # 3) Sign and verify a canonical fact
    sample_fact_dict["server"]["public_key_id"] = kid
    signed = fact.sign_fact(sample_fact_dict, priv)
    assert fact.verify_fact(signed, pub) is True

    # 4) Deterministic compliance on the signed fact
    result = compliance.check_compliance(signed, node_type="full")
    assert result.passed is True, [c for c in result.checks if not c.passed]

    # 5) Backend factory produces a usable OpenAI-compatible backend
    mock_openai = MagicMock()
    import sys

    monkeypatch.setitem(sys.modules, "openai", mock_openai)
    backend = extraction.get_backend({
        "backend": "ollama",
        "model": "qwen2.5:72b-instruct-q5_K_M",
        "base_url": "http://localhost:11434/v1",
    })
    assert backend.backend_id == "ollama"
    assert backend.model == "ollama:qwen2.5:72b-instruct-q5_K_M"
