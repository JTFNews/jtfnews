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


import base64
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jtfprotocol import well_known as _well_known


Clock = Callable[[], datetime]
"""Zero-arg callable returning the current UTC datetime. Tests inject a
fake so gossip logic can be time-tested without ``time.sleep`` or
freezegun."""


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


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
