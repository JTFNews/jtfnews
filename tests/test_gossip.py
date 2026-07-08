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
