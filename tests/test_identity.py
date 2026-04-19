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


def test_save_and_load_keypair_roundtrip(tmp_path):
    priv, pub = identity.generate_keypair()
    priv_path = tmp_path / "server.key"
    pub_path = tmp_path / "server.pub"

    identity.save_keypair(priv, pub, priv_path, pub_path)
    assert priv_path.exists()
    assert pub_path.exists()

    loaded_priv, loaded_pub = identity.load_keypair(priv_path, pub_path)
    assert loaded_priv.private_bytes_raw() == priv.private_bytes_raw()
    assert loaded_pub.public_bytes_raw() == pub.public_bytes_raw()


def test_save_keypair_sets_restrictive_permissions(tmp_path):
    import stat

    priv, pub = identity.generate_keypair()
    priv_path = tmp_path / "server.key"
    pub_path = tmp_path / "server.pub"
    identity.save_keypair(priv, pub, priv_path, pub_path)

    # Private key should be 0600 (owner read/write only).
    mode = stat.S_IMODE(priv_path.stat().st_mode)
    assert mode == 0o600


def test_sign_then_verify_succeeds():
    priv, pub = identity.generate_keypair()
    data = b"hello jtf"
    sig = identity.sign(priv, data)
    assert identity.verify(pub, data, sig) is True


def test_verify_rejects_tampered_data():
    priv, pub = identity.generate_keypair()
    sig = identity.sign(priv, b"hello jtf")
    assert identity.verify(pub, b"hello jtg", sig) is False


def test_verify_rejects_tampered_signature():
    priv, pub = identity.generate_keypair()
    sig = identity.sign(priv, b"hello jtf")
    tampered = bytes([sig[0] ^ 0x01]) + sig[1:]
    assert identity.verify(pub, b"hello jtf", tampered) is False


def test_verify_rejects_wrong_public_key():
    priv1, _ = identity.generate_keypair()
    _, pub2 = identity.generate_keypair()
    sig = identity.sign(priv1, b"hello jtf")
    assert identity.verify(pub2, b"hello jtf", sig) is False


def test_public_key_id_is_deterministic_and_well_formed():
    _, pub = identity.generate_keypair()
    kid1 = identity.public_key_id(pub)
    kid2 = identity.public_key_id(pub)
    assert kid1 == kid2
    assert kid1.startswith("sha256:")
    # 64 hex chars after the prefix.
    assert len(kid1) == len("sha256:") + 64


def test_public_key_id_differs_across_keys():
    _, pub1 = identity.generate_keypair()
    _, pub2 = identity.generate_keypair()
    assert identity.public_key_id(pub1) != identity.public_key_id(pub2)
