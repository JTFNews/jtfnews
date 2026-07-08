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
