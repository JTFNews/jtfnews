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
