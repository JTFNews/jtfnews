"""End-to-end Phase 2 smoke test.

Simulates two JTF servers (Alpha and Bravo) using only in-memory fakes:

  1. Alpha bootstraps from a seed pointing at Bravo.
  2. Alpha fetches Bravo's well-known and merges Bravo into its peer store.
  3. Alpha publishes a fact; sends a signed announcement to Bravo.
  4. Bravo verifies the announcement and pulls the full fact from
     Alpha's simulated stories.json feed.
  5. The pulled fact's Ed25519 signature verifies under Alpha's public
     key.

No real network, no real DNS, no wall clock.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from jtfprotocol import announcements, fact, gossip, identity, well_known


@dataclass
class FakeResponse:
    status_code: int
    body: bytes

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class FakeFetcher:
    def __init__(self, get_map=None, post_map=None):
        self.get_map = get_map or {}
        self.post_map = post_map or {}
        self.posts: list[tuple[str, bytes]] = []

    def get(self, url, timeout=10.0):
        entry = self.get_map.get(url)
        return entry if entry is not None else FakeResponse(404, b"")

    def post(self, url, body, timeout=10.0):
        self.posts.append((url, body))
        entry = self.post_map.get(url)
        return entry if entry is not None else FakeResponse(404, b"")


class FakeClock:
    def __init__(self, now):
        self._now = now

    def __call__(self):
        return self._now


def _make_wellknown(domain: str, priv, pub, peers=None):
    return well_known.generate_well_known(
        priv=priv, pub=pub,
        server_info={
            "domain": domain,
            "channel": "global",
            "name": f"{domain}",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 64500,
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


def test_phase2_two_server_end_to_end(tmp_path):
    alpha_priv, alpha_pub = identity.generate_keypair()
    bravo_priv, bravo_pub = identity.generate_keypair()

    alpha_key_id = identity.public_key_id(alpha_pub)
    bravo_key_id = identity.public_key_id(bravo_pub)

    # Alpha's fact.
    alpha_fact = {
        "jtf_version": 1,
        "id": "",
        "fact": "The Federal Reserve announced a rate change of twenty-five basis points.",
        "occurred_at": "2026-07-08T14:30:00Z",
        "published_at": "2026-07-08T14:35:00Z",
        "verification_method": {"backend": "ollama", "prompt_version": "jtf-extract-v3"},
        "structured_extraction": {"actor": "Federal Reserve", "action": "announced"},
        "sources": [
            {"url": "https://a.example/1", "publisher": "A News"},
            {"url": "https://b.example/1", "publisher": "B News"},
        ],
        "channel": "global",
        "server": {"domain": "alpha.example", "public_key_id": alpha_key_id},
        "algorithm": "Ed25519",
        "signature": "",
    }
    alpha_fact_signed = fact.sign_fact(alpha_fact, alpha_priv)

    # Alpha's well-known lists no peers yet (it just came online).
    alpha_wellknown = _make_wellknown("alpha.example", alpha_priv, alpha_pub, peers=[])
    # Bravo's well-known (Alpha will bootstrap from it via seed).
    bravo_wellknown = _make_wellknown("bravo.example", bravo_priv, bravo_pub, peers=[])

    # Wire the fetcher: Alpha and Bravo each expose their well-known;
    # Alpha exposes its facts feed; Bravo exposes an announcements POST.
    fetcher = FakeFetcher(
        get_map={
            "https://bravo.example/.well-known/jtf.json": FakeResponse(
                200, json.dumps(bravo_wellknown).encode("utf-8"),
            ),
            "https://alpha.example/.well-known/jtf.json": FakeResponse(
                200, json.dumps(alpha_wellknown).encode("utf-8"),
            ),
            "https://alpha.example/stories.json": FakeResponse(
                200, json.dumps({"facts": [alpha_fact_signed]}).encode("utf-8"),
            ),
        },
        post_map={
            "https://bravo.example/announcements": FakeResponse(202, b""),
        },
    )
    clock = FakeClock(datetime(2026, 7, 8, tzinfo=timezone.utc))

    # 1. Alpha bootstraps from a seed pointing at Bravo. Since Bravo is
    # not in the hard-coded SEED_DOMAINS, we pass it in as a candidate
    # via the store bootstrap path.
    alpha_store = gossip.PeerStore(path=tmp_path / "alpha_peers.json", clock=clock)
    stats = gossip.run_gossip_cycle(
        seed_domains=("bravo.example",),
        store=alpha_store,
        fetcher=fetcher,
        clock=clock,
    )
    # Alpha should have contacted Bravo and merged Bravo as a peer.
    assert stats["reachable"] == 1
    assert alpha_store.find(bravo_key_id) is not None

    # 2. Alpha publishes: sign a fact-announcement and send it to Bravo.
    ann = announcements.build_announcement(
        fact_id=alpha_fact_signed["id"],
        occurred_at=alpha_fact_signed["occurred_at"],
        channel=alpha_fact_signed["channel"],
        server_domain="alpha.example",
        server_key_id=alpha_key_id,
        priv=alpha_priv,
    )
    ok = announcements.send_announcement(
        peer_domain="bravo.example",
        announcement=ann,
        fetcher=fetcher,
    )
    assert ok is True

    # 3. Bravo receives (simulated by grabbing the last POST body) and
    # verifies the announcement signature by looking up Alpha's key.
    posted_url, posted_body = fetcher.posts[-1]
    received_ann = json.loads(posted_body.decode("utf-8"))
    alpha_pub_from_wire = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(alpha_wellknown["server"]["public_key"])
    )
    assert announcements.verify_announcement(received_ann, alpha_pub_from_wire) is True

    # 4. Bravo pulls the full fact from Alpha's feed.
    pulled = gossip.fetch_fact_by_id(
        peer_domain="alpha.example",
        fact_id=received_ann["fact_id"],
        feed_path="/stories.json",
        fetcher=fetcher,
    )
    assert pulled is not None
    assert pulled["fact"].startswith("The Federal Reserve")

    # 5. Bravo verifies the fact signature under Alpha's public key.
    assert fact.verify_fact(pulled, alpha_pub_from_wire) is True
