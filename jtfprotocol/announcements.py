"""JTF Protocol fact announcement envelope.

When a server publishes a new fact, it pushes a lightweight
announcement to its known peers. Peers use the announcement to decide
whether to fetch the full fact from the announcing server's feed.

The announcement is signed by the announcing server's private key over
the six-field payload; peers verify with the ``server_key_id`` looked up
in the sender's ``/.well-known/jtf.json``.

See documentation/Protocol Ver 1.0 CURRENT.md, section
"Fact Propagation".
"""
from __future__ import annotations

import base64
import copy

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from jtfprotocol import identity as _identity
from jtfprotocol.fact import canonical_json


ANNOUNCEMENT_TYPE = "fact_announcement"


def build_announcement(
    fact_id: str,
    occurred_at: str,
    channel: str,
    server_domain: str,
    server_key_id: str,
    priv: Ed25519PrivateKey,
) -> dict:
    """Build a signed fact-announcement envelope. Deterministic for a
    given input (the signature bytes are deterministic because Ed25519
    uses deterministic RFC 8032 signing)."""
    envelope = {
        "type": ANNOUNCEMENT_TYPE,
        "fact_id": fact_id,
        "occurred_at": occurred_at,
        "channel": channel,
        "server_domain": server_domain,
        "server_key_id": server_key_id,
        "signature": "",
    }
    to_sign = canonical_json(envelope).encode("utf-8")
    sig = _identity.sign(priv, to_sign)
    envelope["signature"] = base64.b64encode(sig).decode("ascii")
    return envelope


def verify_announcement(ann: dict, pub: Ed25519PublicKey) -> bool:
    """Verify a fact-announcement envelope's Ed25519 signature.

    Returns True if the envelope's ``type`` is ``fact_announcement`` and
    the signature is valid over the canonical JSON of the envelope with
    the signature field emptied. Returns False otherwise. Does not raise.
    """
    try:
        if ann.get("type") != ANNOUNCEMENT_TYPE:
            return False
        to_verify = copy.deepcopy(ann)
        sig_b64 = to_verify.get("signature", "")
        to_verify["signature"] = ""
        sig = base64.b64decode(sig_b64)
        payload = canonical_json(to_verify).encode("utf-8")
        return _identity.verify(pub, payload, sig)
    except Exception:
        return False
