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
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
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


MAX_PEERS = 100
"""Spec: 'Each server maintains at most one hundred active peers.'"""


DEAD_PEER_SECONDS = 7 * 24 * 3600
"""Spec: 'Servers that have not responded in seven days are dropped from peer lists.'"""


MIN_UPTIME_FOR_PROPAGATION_SECONDS = 48 * 3600
"""Spec: 'A peer must have been observed responding for at least
forty-eight hours before a server includes it in peer lists shared with
others.'"""


def _parse_iso8601_utc(s: str) -> datetime:
    """Parse a subset of ISO-8601 covering the Z-suffixed UTC form we
    emit. Kept intentionally narrow — anything else is a caller bug."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


class PeerStore:
    """Local peer state, persisted to a single JSON file.

    This is the reference implementation. Phase 5 wires this into
    ``main.py``'s data directory. Until then, callers pass an explicit
    ``path``.

    Not thread-safe. main.py is single-threaded (see CLAUDE.md).
    """

    def __init__(self, path: Path, clock: Clock | None = None):
        self._path = Path(path)
        self._clock = clock or _default_clock
        self._peers: list[PeerRecord] = []
        self._load()

    def _load(self) -> None:
        self._confirmations = {}
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            return
        peers: list[PeerRecord] = []
        for entry in data.get("peers", []):
            try:
                peers.append(PeerRecord(**entry))
            except TypeError:
                continue
        self._peers = peers
        self._confirmations = {
            k: set(v) for k, v in data.get("confirmations", {}).items()
        }

    def save(self) -> None:
        payload = {
            "version": 1,
            "peers": [asdict(p) for p in self._peers],
            "confirmations": {k: sorted(v) for k, v in self._confirmations.items()},
        }
        # Atomic write (see main.py atomic_write_text pattern).
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    def add_or_update(
        self,
        entry: dict,
        source_key_id: str,
        asn: int = 0,
    ) -> bool:
        """Merge a peer-list entry received from ``source_key_id``.

        - New peer: appended with ``confirmed_by = 1``, marked confirmed
          by this source.
        - Existing peer, new source: ``confirmed_by`` increments; the
          record's ``last_seen``, ``trust_score``, ``channel`` fields
          adopt the newer entry's values.
        - Existing peer, same source that already confirmed: no change.

        Returns True if the peer set changed, False otherwise. Callers
        are responsible for calling ``save()`` when their batch is done.
        """
        pkid = entry["public_key_id"]
        existing = self.find(pkid)
        source_set = self._confirmations.setdefault(pkid, set())

        if existing is None:
            now = self._clock().strftime("%Y-%m-%dT%H:%M:%SZ")
            new = PeerRecord.from_wellknown_entry(entry, first_seen=now, asn=asn)
            new.confirmed_by = 1
            if len(self._peers) < MAX_PEERS:
                self._peers.append(new)
                source_set.add(source_key_id)
                return True
            # Cap reached: evict the lowest-trust existing peer if the
            # candidate outranks it. Ties resolve against the newer peer
            # so we do not thrash.
            weakest_index, weakest = min(
                enumerate(self._peers), key=lambda kv: kv[1].trust_score
            )
            if new.trust_score > weakest.trust_score:
                # Drop the evicted peer's confirmation record too.
                self._confirmations.pop(weakest.public_key_id, None)
                self._peers[weakest_index] = new
                source_set.add(source_key_id)
                return True
            # Not strong enough. Roll back the empty confirmation set we
            # created above so we don't leak state.
            if not source_set:
                self._confirmations.pop(pkid, None)
            return False

        if source_key_id in source_set:
            return False

        source_set.add(source_key_id)
        existing.confirmed_by = len(source_set)
        existing.last_seen = entry.get("last_seen", existing.last_seen)
        existing.trust_score = float(entry.get("trust_score", existing.trust_score))
        existing.channel = entry.get("channel", existing.channel)
        if asn:
            existing.asn = int(asn)
        return True

    def all(self) -> list[PeerRecord]:
        """Return a snapshot of all peer records."""
        return list(self._peers)

    def find(self, public_key_id: str) -> PeerRecord | None:
        for p in self._peers:
            if p.public_key_id == public_key_id:
                return p
        return None

    def peers_for_publication(self) -> list[dict]:
        """Return peer entries eligible to be published in this
        server's own ``/.well-known/jtf.json``. Filters out peers whose
        first-seen timestamp is less than ``MIN_UPTIME_FOR_PROPAGATION_SECONDS``
        old, per the spec's uptime gate."""
        now = self._clock()
        eligible: list[dict] = []
        for p in self._peers:
            try:
                first = _parse_iso8601_utc(p.first_seen)
            except Exception:
                continue
            age = (now - first).total_seconds()
            if age >= MIN_UPTIME_FOR_PROPAGATION_SECONDS:
                eligible.append(p.to_wellknown_entry())
        return eligible

    def drop_dead_peers(self) -> list[str]:
        """Remove peers whose ``last_seen`` is older than
        ``DEAD_PEER_SECONDS``. Returns the list of dropped
        ``public_key_id``s. Also clears their confirmation records so
        their eviction doesn't leak state."""
        now = self._clock()
        keep: list[PeerRecord] = []
        dropped: list[str] = []
        for p in self._peers:
            try:
                seen = _parse_iso8601_utc(p.last_seen)
            except Exception:
                keep.append(p)
                continue
            age = (now - seen).total_seconds()
            if age >= DEAD_PEER_SECONDS:
                dropped.append(p.public_key_id)
                self._confirmations.pop(p.public_key_id, None)
            else:
                keep.append(p)
        self._peers = keep
        return dropped


MAX_ASN_SHARE = 0.30
"""Spec: 'No more than thirty percent of a server's peers should share the same ASN.'"""


ASN_SHARE_FLOOR_PEERS = 3
"""Below this population the ASN cap is not enforced (three peers can
be from the same ASN early on)."""


MAX_NEW_PEERS_PER_CYCLE = 10
"""Spec: 'A server accepts at most ten new peers per gossip cycle.'"""


class CycleBatch:
    """Enforces per-cycle new-peer rate limit while delegating merge
    semantics to ``PeerStore``. One ``CycleBatch`` per gossip cycle.

    Rejecting a new peer because the rate limit is full is not an
    error; it is protocol design. The rejected peer will be reconsidered
    next cycle.
    """

    def __init__(
        self,
        store: PeerStore,
        source_key_id: str,
        clock: Clock | None = None,
        max_new: int = MAX_NEW_PEERS_PER_CYCLE,
    ):
        self._store = store
        self._source_key_id = source_key_id
        self._clock = clock or _default_clock
        self._max_new = max_new
        self._new_admissions = 0

    def add_or_update(self, entry: dict, asn: int = 0) -> bool:
        """Delegate to PeerStore, but decline to admit a *new* peer once
        the per-cycle new-peer quota is exhausted or the ASN diversity cap
        would be breached. Updates of already-tracked peers are unlimited."""
        pkid = entry["public_key_id"]
        is_new = self._store.find(pkid) is None
        if is_new and self._new_admissions >= self._max_new:
            return False
        if is_new and asn and not self._asn_would_stay_under_cap(asn):
            return False
        changed = self._store.add_or_update(
            entry,
            source_key_id=self._source_key_id,
            asn=asn,
        )
        if changed and is_new and self._store.find(pkid) is not None:
            self._new_admissions += 1
        return changed

    def _asn_would_stay_under_cap(self, candidate_asn: int) -> bool:
        current = self._store.all()
        total_after = len(current) + 1
        if total_after <= ASN_SHARE_FLOOR_PEERS:
            return True
        same_asn = sum(1 for p in current if p.asn == candidate_asn) + 1
        return (same_asn / total_after) <= MAX_ASN_SHARE


def fetch_fact_by_id(
    peer_domain: str,
    fact_id: str,
    feed_path: str,
    fetcher: Fetcher | None = None,
    timeout: float = 10.0,
) -> dict | None:
    """Fetch ``peer_domain``'s facts feed and return the fact with the
    given ``fact_id``. Returns None if the fetch fails, the feed is
    malformed, or the fact is not present. Never raises.

    Signature verification is intentionally NOT performed here; callers
    are responsible for verifying with the sender's public key looked up
    from the sender's ``/.well-known/jtf.json``. Keeping this function
    signature-agnostic lets it be re-used for archive lookups and other
    feeds that may carry the same fact under a different signing key.
    """
    fetcher = fetcher or RequestsFetcher()
    url = f"https://{peer_domain}{feed_path}"
    try:
        resp = fetcher.get(url, timeout=timeout)
        if resp.status_code != 200:
            return None
        feed = resp.json()
    except Exception:
        return None
    for entry in feed.get("facts", []):
        if entry.get("id") == fact_id:
            return entry
    return None


def exchange_peer_lists(
    peer_domain: str,
    store: PeerStore,
    fetcher: Fetcher | None = None,
    clock: Clock | None = None,
    timeout: float = 10.0,
) -> bool:
    """Fetch ``peer_domain``'s well-known document and merge its peer
    list into ``store`` using a single ``CycleBatch``.

    Returns True if the well-known was successfully fetched and at
    least one peer was merged or updated. Returns False on any fetch
    or verification failure. Never raises.

    The remote's ``server.public_key_id`` is used as the ``source_key_id``
    for confirmation counting.
    """
    doc = fetch_and_verify_well_known(peer_domain, fetcher=fetcher, timeout=timeout)
    if doc is None:
        return False
    source_key_id = doc.get("server", {}).get("public_key_id", "")
    if not source_key_id:
        return False
    remote_asn_hint = int(doc.get("server", {}).get("asn", 0) or 0)
    # The remote itself is a peer we've now heard from directly; enter it too.
    self_entry = {
        "domain": doc["server"]["domain"],
        "public_key_id": source_key_id,
        "channel": doc["server"].get("channel", "global"),
        "last_seen": (clock or _default_clock)().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trust_score": 0.0,
        "confirmed_by": 0,
    }
    batch = CycleBatch(store, source_key_id=source_key_id, clock=clock)
    changed = batch.add_or_update(self_entry, asn=remote_asn_hint)
    for entry in doc.get("peers", []):
        try:
            if batch.add_or_update(entry):
                changed = True
        except Exception:
            continue
    return changed
