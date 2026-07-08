"""JTF Protocol reference implementation.

Ed25519 identity, canonical fact format, deterministic methodology
compliance checks, pluggable extraction backends, well-known endpoint,
seed and DNS discovery, peer store and gossip cycle, and fact
announcement envelope.

See documentation/Protocol Ver 1.0 CURRENT.md for the authoritative
spec.

Typical use (Phase 5 integration):

    from jtfprotocol import (
        identity, fact, compliance, extraction, well_known,
        seeds, gossip, announcements,
    )

    priv, pub = identity.generate_keypair()
    store = gossip.PeerStore(path=Path("data/peers.json"))
    gossip.run_gossip_cycle(seeds.SEED_DOMAINS, store)
"""

__version__ = "0.2.0"

from jtfprotocol import (
    announcements,
    compliance,
    extraction,
    fact,
    gossip,
    identity,
    prompts,
    seeds,
    well_known,
)

__all__ = [
    "__version__",
    "announcements",
    "compliance",
    "extraction",
    "fact",
    "gossip",
    "identity",
    "prompts",
    "seeds",
    "well_known",
]
