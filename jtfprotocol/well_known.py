"""``/.well-known/jtf.json`` generation and verification.

The well-known endpoint is the protocol's handshake. Every server
publishes a signed identity document describing its keys, channel,
extraction backend, feeds, and known peers. See
documentation/Protocol Ver 1.0 CURRENT.md, section "Discovery -> The
Well-Known Endpoint".
"""
from __future__ import annotations

import base64
import copy

from cryptography.hazmat.primitives import serialization

from jtfprotocol import identity as _identity
from jtfprotocol.extraction import SUPPORTED_BACKENDS
from jtfprotocol.fact import canonical_json


PROTOCOL_VERSION = 1


def generate_well_known(
    priv,
    pub,
    server_info: dict,
    extraction_info: dict,
    feeds: dict,
    peers: list,
) -> dict:
    """Build and sign the ``/.well-known/jtf.json`` document.

    Returns the document as a dict ready to be served as JSON. The
    document contains a ``signature`` over the canonical JSON of the
    document with the signature field emptied.
    """
    if extraction_info.get("backend") not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"extraction.backend must be one of {sorted(SUPPORTED_BACKENDS)}, "
            f"got {extraction_info.get('backend')!r}"
        )

    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    server = dict(server_info)
    server["public_key"] = base64.b64encode(pub_bytes).decode("ascii")
    server["public_key_id"] = _identity.public_key_id(pub)
    server["algorithm"] = "Ed25519"

    doc = {
        "jtf_protocol_version": PROTOCOL_VERSION,
        "server": server,
        "extraction": dict(extraction_info),
        "feeds": dict(feeds),
        "peers": [dict(p) for p in peers],
        "signature": "",
    }
    to_sign = canonical_json(doc).encode("utf-8")
    sig = _identity.sign(priv, to_sign)
    doc["signature"] = base64.b64encode(sig).decode("ascii")
    return doc


def verify_well_known(doc: dict, pub) -> bool:
    """Verify a well-known document's signature.

    Returns True on success, False otherwise. Does not raise.
    """
    try:
        to_verify = copy.deepcopy(doc)
        sig_b64 = to_verify.get("signature", "")
        to_verify["signature"] = ""
        sig = base64.b64decode(sig_b64)
        payload = canonical_json(to_verify).encode("utf-8")
        return _identity.verify(pub, payload, sig)
    except Exception:
        return False
