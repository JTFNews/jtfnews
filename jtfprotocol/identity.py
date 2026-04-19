"""Ed25519 identity primitives for the JTF Protocol.

Each JTF server generates one Ed25519 keypair on first startup. The private
key never leaves the server. The public key identifies the server to the
network. Every published fact is signed by the private key.
"""
from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
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


def save_keypair(
    priv: Ed25519PrivateKey,
    pub: Ed25519PublicKey,
    priv_path: Path,
    pub_path: Path,
) -> None:
    """Persist a keypair to disk.

    The private key is written in PEM/PKCS8 format with restrictive file
    permissions (0600). The public key is written in raw 32-byte form.
    Callers are responsible for choosing a secure directory; this function
    does not create parent directories.
    """
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    Path(priv_path).write_bytes(priv_bytes)
    os.chmod(priv_path, 0o600)
    Path(pub_path).write_bytes(pub_bytes)
    os.chmod(pub_path, 0o644)


def load_keypair(
    priv_path: Path,
    pub_path: Path,
) -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Load a keypair previously written by save_keypair."""
    priv_bytes = Path(priv_path).read_bytes()
    pub_bytes = Path(pub_path).read_bytes()

    priv = serialization.load_pem_private_key(priv_bytes, password=None)
    if not isinstance(priv, Ed25519PrivateKey):
        raise ValueError(f"expected Ed25519 private key, got {type(priv).__name__}")

    pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
    return priv, pub
