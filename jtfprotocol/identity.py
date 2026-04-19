"""Ed25519 identity primitives for the JTF Protocol.

Each JTF server generates one Ed25519 keypair on first startup. The private
key never leaves the server. The public key identifies the server to the
network. Every published fact is signed by the private key.
"""
from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Generate a fresh Ed25519 keypair.

    Uses the platform's cryptographically secure RNG via the cryptography
    library. Callers should persist the private key to encrypted storage;
    see `save_keypair` in the next task.
    """
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    return priv, pub
