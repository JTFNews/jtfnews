"""Tests for jtfprotocol.identity."""
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from jtfprotocol import identity


def test_generate_keypair_returns_ed25519_types():
    priv, pub = identity.generate_keypair()
    assert isinstance(priv, Ed25519PrivateKey)
    assert isinstance(pub, Ed25519PublicKey)


def test_generate_keypair_returns_fresh_keys():
    priv1, _ = identity.generate_keypair()
    priv2, _ = identity.generate_keypair()
    priv1_bytes = priv1.private_bytes_raw()
    priv2_bytes = priv2.private_bytes_raw()
    assert priv1_bytes != priv2_bytes
