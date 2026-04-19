"""JTF Protocol reference implementation.

Ed25519 identity, canonical fact format, deterministic methodology
compliance checks, and pluggable extraction backends.

See documentation/Protocol Ver 1.0 CURRENT.md for the authoritative spec.

Typical use (Phase 5 integration):

    from jtfprotocol import identity, fact, compliance, extraction, well_known

    priv, pub = identity.generate_keypair()
    backend = extraction.get_backend(config)
    structured = backend.extract_fact(source_text, source_metadata)
    # ...assemble fact_dict with structured, sources, etc...
    signed = fact.sign_fact(fact_dict, priv)
    result = compliance.check_compliance(signed)
"""

__version__ = "0.1.0"

from jtfprotocol import compliance, extraction, fact, identity, prompts, well_known

__all__ = [
    "__version__",
    "compliance",
    "extraction",
    "fact",
    "identity",
    "prompts",
    "well_known",
]
