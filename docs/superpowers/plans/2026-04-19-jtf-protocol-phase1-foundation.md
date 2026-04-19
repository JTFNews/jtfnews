# JTF Protocol Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the cryptographic identity, canonical fact format, deterministic methodology compliance checks, and pluggable extraction backends required to publish a JTF-Protocol-compliant fact. No peer discovery, no trust scoring, no corrections — those are Phases 2-4. Phase 1 produces a standalone Python package that the existing `main.py` will adopt in Phase 5.

**Architecture:** A new Python package `jtfprotocol/` with narrow modules, one responsibility each. Ed25519 via the standard `cryptography` library. Dual-backend extraction: commercial via `AnthropicBackend`, local via `OpenAICompatibleBackend` (which handles OpenAI, Ollama, and LM Studio with different base URLs). Every published fact carries a signature, a content hash, a supporting quote, and a context window — the protocol's verifiability primitives. Integration with `main.py` is explicitly deferred to Phase 5 to keep the live system untouched.

**Tech Stack:** Python 3.9+, `cryptography` (Ed25519), `pytest` (test runner, dev-only), `anthropic` SDK (already a dep), `openai` SDK (already a dep, used for OpenAI-compatible local backends), `requests` (already a dep).

**Reference:** `documentation/Protocol Ver 1.0 CURRENT.md` is the authoritative spec. Every task references the section it implements.

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `jtfprotocol/__init__.py` | Package marker and public exports |
| `jtfprotocol/identity.py` | Ed25519 keypair generation, disk serialization, sign/verify primitives, public key fingerprint |
| `jtfprotocol/fact.py` | `Fact` dataclass, canonical JSON serialization, fact ID hashing, `sign_fact` / `verify_fact` |
| `jtfprotocol/compliance.py` | Deterministic methodology compliance checks (rule-based, reproducible, no AI) |
| `jtfprotocol/prompts.py` | Shared fact-extraction prompt template (same text across all backends) |
| `jtfprotocol/extraction.py` | `ExtractionBackend` ABC, `StructuredFact` dataclass, `AnthropicBackend`, `OpenAICompatibleBackend`, `get_backend` factory |
| `jtfprotocol/well_known.py` | `generate_well_known` and `verify_well_known` for `/.well-known/jtf.json` |
| `tests/__init__.py` | Test package marker |
| `tests/conftest.py` | Pytest fixtures (temp keypair, sample fact dict) |
| `tests/test_identity.py` | Identity module tests |
| `tests/test_fact.py` | Fact format and signing tests |
| `tests/test_compliance.py` | Compliance check tests |
| `tests/test_prompts.py` | Prompt template tests |
| `tests/test_extraction.py` | Extraction backend tests (with mocked HTTP) |
| `tests/test_well_known.py` | Well-known endpoint tests |
| `tests/test_smoke_phase1.py` | End-to-end smoke test crossing all modules |
| `tests/fixtures/sample_fact.json` | A canonical valid fact used across tests |
| `tests/fixtures/extraction_golden.jsonl` | Golden-set schema examples (not used for LLM-quality tests — operators run those) |
| `requirements-dev.txt` | Dev-only deps: `pytest` |

### Modified files

| Path | Change |
|---|---|
| `requirements.txt` | Add `cryptography>=42.0.0` |
| `.gitignore` | Add `data/protocol_keys/` (runtime keypair storage path reserved for Phase 5) |

### Out of scope for Phase 1 (deferred)

- `main.py` — no changes; integration happens in Phase 5
- Any files under `docs/` other than the plan itself
- Any runtime data files

---

## Conventions

- **Python style:** Type hints on every public function. `dataclasses.dataclass(frozen=True)` for immutable data structures.
- **Naming:** Module names lowercase, no underscores unless needed. Functions `snake_case`. Classes `PascalCase`.
- **Commits:** After every task via `./bu.sh "PHASE1-NN: short title"`. Atomic; one commit per task. Per CLAUDE.md, never raw `git commit`.
- **Tests first:** Write the failing test, run it to see it fail, implement the minimal code, run it to see it pass, commit. This is not optional; the skill is TDD.
- **No emoji** anywhere — code, docstrings, commits, this plan.

---

## Task 1: Package skeleton and pytest configuration

**Spec reference:** Supports the entire Phase 1. Sets up the test harness.

**Files:**
- Create: `jtfprotocol/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Create the package marker**

Create `jtfprotocol/__init__.py` with this content:

```python
"""JTF Protocol reference implementation.

Ed25519 identity, canonical fact format, deterministic methodology
compliance checks, and pluggable extraction backends.

See documentation/Protocol Ver 1.0 CURRENT.md for the authoritative spec.
"""

__version__ = "0.1.0"
```

- [ ] **Step 2: Create the test package marker**

Create `tests/__init__.py` with a single line:

```python
"""Tests for jtfprotocol."""
```

- [ ] **Step 3: Add pytest to requirements-dev.txt**

Create `requirements-dev.txt`:

```
# JTF Protocol development dependencies
# Install: pip install -r requirements-dev.txt
pytest>=8.0.0
```

- [ ] **Step 4: Add cryptography to requirements.txt**

Append to `requirements.txt`:

```
# JTF Protocol - Ed25519 signatures and key management
cryptography>=42.0.0
```

- [ ] **Step 5: Create pytest.ini**

Create `pytest.ini` at repo root:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

- [ ] **Step 6: Add protocol keys path to .gitignore**

Append to `.gitignore`:

```

# JTF Protocol runtime keypair storage (Phase 5 will populate this)
data/protocol_keys/
```

- [ ] **Step 7: Install deps and run pytest to see the empty-collection message**

Run:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Expected output: `no tests ran` (or `collected 0 items`) — confirms pytest is installed and finds the `tests/` directory.

- [ ] **Step 8: Commit**

```bash
./bu.sh "PHASE1-01: package skeleton and pytest setup"
```

---

## Task 2: Ed25519 keypair generation

**Spec reference:** Identity → Key Pairs. "Each server generates an Ed25519 key pair on first startup."

**Files:**
- Create: `jtfprotocol/identity.py`
- Create: `tests/test_identity.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_identity.py`:

```python
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
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
pytest tests/test_identity.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.identity'` (or equivalent collection error).

- [ ] **Step 3: Write the minimal implementation**

Create `jtfprotocol/identity.py`:

```python
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
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
pytest tests/test_identity.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-02: Ed25519 keypair generation"
```

---

## Task 3: Keypair serialization to and from disk

**Spec reference:** Identity → Key Pairs. "The private key stays on the server. It is never transmitted."

**Files:**
- Modify: `jtfprotocol/identity.py`
- Modify: `tests/test_identity.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_identity.py`:

```python
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
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_identity.py -v
```

Expected: `AttributeError: module 'jtfprotocol.identity' has no attribute 'save_keypair'`.

- [ ] **Step 3: Implement save_keypair and load_keypair**

Append to `jtfprotocol/identity.py`:

```python
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization


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
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_identity.py -v
```

Expected: four tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-03: keypair disk serialization"
```

---

## Task 4: Sign and verify primitives

**Spec reference:** Identity → Signing. "Every fact published by a server is signed with its private key. ... Anyone with the public key can verify three things: This fact came from the claimed server. The fact has not been altered since publication. The server cannot deny publishing it."

**Files:**
- Modify: `jtfprotocol/identity.py`
- Modify: `tests/test_identity.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_identity.py`:

```python
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
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_identity.py -v
```

Expected: `AttributeError: module 'jtfprotocol.identity' has no attribute 'sign'`.

- [ ] **Step 3: Implement sign and verify**

Append to `jtfprotocol/identity.py`:

```python
from cryptography.exceptions import InvalidSignature


def sign(priv: Ed25519PrivateKey, data: bytes) -> bytes:
    """Sign `data` with the Ed25519 private key.

    Returns a 64-byte signature.
    """
    return priv.sign(data)


def verify(pub: Ed25519PublicKey, data: bytes, signature: bytes) -> bool:
    """Verify an Ed25519 signature.

    Returns True if the signature is valid for the given data and public
    key. Returns False on any verification failure. Does not raise.
    """
    try:
        pub.verify(signature, data)
        return True
    except InvalidSignature:
        return False
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_identity.py -v
```

Expected: eight tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-04: sign and verify primitives"
```

---

## Task 5: Public key fingerprint (`public_key_id`)

**Spec reference:** Identity → Signing. Every fact carries `"server": { "public_key_id": "sha256:..." }`. The fingerprint is the stable identifier for a server's key across gossip, revocations, and rotations.

**Files:**
- Modify: `jtfprotocol/identity.py`
- Modify: `tests/test_identity.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_identity.py`:

```python
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
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
pytest tests/test_identity.py -v
```

Expected: `AttributeError: module 'jtfprotocol.identity' has no attribute 'public_key_id'`.

- [ ] **Step 3: Implement public_key_id**

Append to `jtfprotocol/identity.py`:

```python
import hashlib


def public_key_id(pub: Ed25519PublicKey) -> str:
    """Return the canonical public key identifier.

    Format: "sha256:{hex}" where hex is the SHA-256 of the raw 32-byte
    public key. This is the stable identifier used throughout the
    protocol (fact.server.public_key_id, peer lists, revocations).
    """
    raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    digest = hashlib.sha256(raw).hexdigest()
    return f"sha256:{digest}"
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_identity.py -v
```

Expected: ten tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-05: public key fingerprint (public_key_id)"
```

---

## Task 6: `Fact` dataclass and dict round-trip

**Spec reference:** The Fact → Canonical Format. The JSON schema on lines ~153-242 of the spec.

**Files:**
- Create: `jtfprotocol/fact.py`
- Create: `tests/fixtures/sample_fact.json`
- Create: `tests/conftest.py`
- Create: `tests/test_fact.py`

- [ ] **Step 1: Write the sample fact fixture**

Create `tests/fixtures/sample_fact.json` with a valid two-source fact (simplified but schema-complete):

```json
{
  "jtf_version": 1,
  "id": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "fact": "The United Nations General Assembly voted 143 to 9 to admit the Republic of Somaliland as its 194th member state.",
  "occurred_at": "2026-04-18T14:30:00Z",
  "published_at": "2026-04-18T15:02:00Z",
  "verification_method": {
    "backend": "anthropic",
    "model": "anthropic:claude-haiku:4-5-20251001",
    "prompt_version": "jtf-extract-v3",
    "methodology_checks": "rule-based-v1"
  },
  "structured_extraction": {
    "subjects": ["Q47010"],
    "subjects_text": ["United Nations General Assembly"],
    "action": "voted",
    "objects": ["Republic of Somaliland", "194th member state"],
    "quantities": [
      {"value": 143, "context": "votes in favor"},
      {"value": 9, "context": "votes against"}
    ],
    "location": "United Nations Headquarters, New York",
    "event_time": {"start": "2026-04-18T14:00:00Z", "end": "2026-04-18T15:00:00Z"},
    "claim_type": "vote",
    "required_fields_met": true
  },
  "sources": [
    {
      "name": "Reuters",
      "url": "https://reuters.com/world/example",
      "content_hash": "sha256:7d793037a0760186574b0282f2f435e7",
      "snapshot_url": "https://web.archive.org/web/20260418150000/https://reuters.com/world/example",
      "supporting_quote": "The General Assembly approved Somaliland's membership application by a vote of 143 in favor to 9 against.",
      "context_window": {
        "before": "After three hours of debate on Friday afternoon,",
        "after": "with 12 abstentions. The vote followed months of diplomatic negotiations.",
        "context_hash": "sha256:8a3c91aaaaaaaaaaaaaaaaaaaaaaaaaa"
      },
      "fetched_at": "2026-04-18T15:00:12Z",
      "derived_from": null,
      "ownership": [{"entity": "Thomson Reuters Corporation", "percentage": 100.0}],
      "scores": {"accuracy": 9.6, "bias": 9.2, "speed": 9.0, "consensus": 9.1}
    },
    {
      "name": "Associated Press",
      "url": "https://apnews.com/article/example",
      "content_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015",
      "snapshot_url": "https://web.archive.org/web/20260418150200/https://apnews.com/article/example",
      "supporting_quote": "In a 143-9 vote, the U.N. General Assembly voted Friday to admit Somaliland.",
      "context_window": {
        "before": "NEW YORK (AP) --",
        "after": "The decision caps a years-long campaign by the Horn of Africa nation.",
        "context_hash": "sha256:2b4f7ebbbbbbbbbbbbbbbbbbbbbbbbbb"
      },
      "fetched_at": "2026-04-18T15:01:05Z",
      "derived_from": null,
      "ownership": [{"entity": "Associated Press (nonprofit cooperative)", "percentage": 100.0}],
      "scores": {"accuracy": 9.5, "bias": 9.3, "speed": 8.8, "consensus": 9.0}
    }
  ],
  "primary_source": {
    "url": "https://press.un.org/en/2026/ga12345.doc.htm",
    "description": "UN General Assembly official press release"
  },
  "channel": "global",
  "server": {
    "domain": "jtfnews.org",
    "public_key_id": "sha256:a1b2c3aaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "algorithm": "Ed25519",
  "signature": "base64-placeholder"
}
```

- [ ] **Step 2: Write the conftest fixture**

Create `tests/conftest.py`:

```python
"""Shared pytest fixtures for jtfprotocol tests."""
import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_fact_dict() -> dict:
    """A valid two-source fact matching the Phase 1 schema."""
    return json.loads((FIXTURES / "sample_fact.json").read_text())
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_fact.py`:

```python
"""Tests for jtfprotocol.fact."""
from jtfprotocol import fact as fact_module


def test_fact_from_dict_roundtrip(sample_fact_dict):
    f = fact_module.Fact.from_dict(sample_fact_dict)
    assert f.to_dict() == sample_fact_dict


def test_fact_rejects_wrong_jtf_version(sample_fact_dict):
    sample_fact_dict["jtf_version"] = 999
    import pytest

    with pytest.raises(ValueError, match="jtf_version"):
        fact_module.Fact.from_dict(sample_fact_dict)
```

- [ ] **Step 4: Run the test to confirm it fails**

```bash
pytest tests/test_fact.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.fact'`.

- [ ] **Step 5: Implement the Fact dataclass**

Create `jtfprotocol/fact.py`:

```python
"""JTF Protocol canonical fact format.

The Fact is the atomic unit of the protocol. This module defines the
dataclass, round-trip serialization to/from dict, the canonical JSON
encoding used for hashing and signing, and the sign/verify helpers.

See documentation/Protocol Ver 1.0 CURRENT.md, section "The Fact".
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


JTF_VERSION = 1


@dataclass(frozen=True)
class Fact:
    """A canonical JTF fact.

    Fields mirror the protocol spec exactly. Internal structure uses
    plain dicts for nested objects (verification_method, structured_extraction,
    sources, primary_source, server) because they are schema-stable but
    extensible. Stronger typing is a Phase 2 refactor if it earns its cost.
    """

    jtf_version: int
    id: str
    fact: str
    occurred_at: str
    published_at: str
    verification_method: dict
    structured_extraction: dict
    sources: list[dict]
    primary_source: dict | None
    channel: str
    server: dict
    algorithm: str
    signature: str

    @classmethod
    def from_dict(cls, data: dict) -> Fact:
        """Construct a Fact from a dict parsed from JSON.

        Performs version and presence validation. Does NOT verify the
        signature — use `verify_fact` for that.
        """
        if data.get("jtf_version") != JTF_VERSION:
            raise ValueError(
                f"unsupported jtf_version: {data.get('jtf_version')} (expected {JTF_VERSION})"
            )
        required = [
            "id", "fact", "occurred_at", "published_at",
            "verification_method", "structured_extraction", "sources",
            "channel", "server", "algorithm", "signature",
        ]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"fact missing required fields: {missing}")
        return cls(
            jtf_version=data["jtf_version"],
            id=data["id"],
            fact=data["fact"],
            occurred_at=data["occurred_at"],
            published_at=data["published_at"],
            verification_method=copy.deepcopy(data["verification_method"]),
            structured_extraction=copy.deepcopy(data["structured_extraction"]),
            sources=copy.deepcopy(data["sources"]),
            primary_source=copy.deepcopy(data.get("primary_source")),
            channel=data["channel"],
            server=copy.deepcopy(data["server"]),
            algorithm=data["algorithm"],
            signature=data["signature"],
        )

    def to_dict(self) -> dict:
        """Return the fact as a plain dict suitable for JSON encoding."""
        out: dict[str, Any] = {
            "jtf_version": self.jtf_version,
            "id": self.id,
            "fact": self.fact,
            "occurred_at": self.occurred_at,
            "published_at": self.published_at,
            "verification_method": copy.deepcopy(self.verification_method),
            "structured_extraction": copy.deepcopy(self.structured_extraction),
            "sources": copy.deepcopy(self.sources),
        }
        if self.primary_source is not None:
            out["primary_source"] = copy.deepcopy(self.primary_source)
        out["channel"] = self.channel
        out["server"] = copy.deepcopy(self.server)
        out["algorithm"] = self.algorithm
        out["signature"] = self.signature
        return out
```

- [ ] **Step 6: Run the tests to confirm they pass**

```bash
pytest tests/test_fact.py -v
```

Expected: two tests pass.

- [ ] **Step 7: Commit**

```bash
./bu.sh "PHASE1-06: Fact dataclass and dict round-trip"
```

---

## Task 7: Canonical JSON serialization

**Spec reference:** The Fact → Fact Identity. "A fact's `id` is a SHA-256 hash of the canonical content." Canonical means byte-for-byte reproducible regardless of dict key order or whitespace.

**Files:**
- Modify: `jtfprotocol/fact.py`
- Modify: `tests/test_fact.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fact.py`:

```python
def test_canonical_json_is_deterministic(sample_fact_dict):
    shuffled = dict(reversed(list(sample_fact_dict.items())))
    assert (
        fact_module.canonical_json(sample_fact_dict)
        == fact_module.canonical_json(shuffled)
    )


def test_canonical_json_has_no_whitespace_padding(sample_fact_dict):
    s = fact_module.canonical_json(sample_fact_dict)
    # Separators are ("," ":") with no spaces.
    assert ", " not in s
    assert ": " not in s


def test_canonical_json_handles_nested_dicts(sample_fact_dict):
    # Reorder a nested dict and confirm canonical output is unchanged.
    reordered = copy_deep(sample_fact_dict)
    reordered["server"] = dict(reversed(list(sample_fact_dict["server"].items())))
    assert fact_module.canonical_json(sample_fact_dict) == fact_module.canonical_json(reordered)


def copy_deep(d):
    import copy
    return copy.deepcopy(d)
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_fact.py -v
```

Expected: `AttributeError: module 'jtfprotocol.fact' has no attribute 'canonical_json'`.

- [ ] **Step 3: Implement canonical_json**

Append to `jtfprotocol/fact.py`:

```python
import json


def canonical_json(data: dict) -> str:
    """Return a deterministic JSON encoding of `data`.

    - Keys are sorted lexicographically at every level.
    - No whitespace between tokens.
    - Unicode is preserved (not escaped).
    - Trailing newlines are not added.

    This is the single canonical encoding used for fact ID hashing,
    signing, and signature verification. Any two callers that hash or
    sign the same conceptual fact must produce identical bytes.
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_fact.py -v
```

Expected: five tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-07: canonical JSON serialization"
```

---

## Task 8: Fact ID computation

**Spec reference:** The Fact → Fact Identity. "A fact's `id` is a SHA-256 hash of the canonical content: the fact text, source URLs, and `occurred_at` timestamp. The full 256-bit hash is used."

Note: The spec names three fields but the canonical content must be fully deterministic and cover every field that a peer treats as load-bearing. To eliminate ambiguity, Phase 1 defines fact ID as SHA-256 of the canonical JSON of a specific identity-bearing subset: `fact`, `occurred_at`, `sources[*].url`, and `server.public_key_id`. This matches the spec's intent (different servers produce different IDs for the same event) while being deterministic.

**Files:**
- Modify: `jtfprotocol/fact.py`
- Modify: `tests/test_fact.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fact.py`:

```python
def test_compute_fact_id_is_deterministic(sample_fact_dict):
    id1 = fact_module.compute_fact_id(sample_fact_dict)
    id2 = fact_module.compute_fact_id(sample_fact_dict)
    assert id1 == id2
    assert id1.startswith("sha256:")
    assert len(id1) == len("sha256:") + 64


def test_compute_fact_id_changes_when_fact_text_changes(sample_fact_dict):
    original = fact_module.compute_fact_id(sample_fact_dict)
    sample_fact_dict["fact"] = "The vote was 141 to 9."
    changed = fact_module.compute_fact_id(sample_fact_dict)
    assert original != changed


def test_compute_fact_id_ignores_signature_field(sample_fact_dict):
    original = fact_module.compute_fact_id(sample_fact_dict)
    sample_fact_dict["signature"] = "different-signature"
    assert fact_module.compute_fact_id(sample_fact_dict) == original
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_fact.py -v
```

Expected: `AttributeError: module 'jtfprotocol.fact' has no attribute 'compute_fact_id'`.

- [ ] **Step 3: Implement compute_fact_id**

Append to `jtfprotocol/fact.py`:

```python
import hashlib


def compute_fact_id(fact_dict: dict) -> str:
    """Compute the canonical fact ID.

    The ID is the SHA-256 of the canonical JSON of the identity-bearing
    subset: the fact text, the occurred_at timestamp, the source URLs,
    and the server's public_key_id. This is deterministic, excludes the
    signature and the id itself, and guarantees that two servers
    independently verifying the same event produce different IDs because
    their server.public_key_id differs.
    """
    identity_subset = {
        "fact": fact_dict["fact"],
        "occurred_at": fact_dict["occurred_at"],
        "source_urls": [s["url"] for s in fact_dict["sources"]],
        "server_public_key_id": fact_dict["server"]["public_key_id"],
    }
    canonical = canonical_json(identity_subset)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_fact.py -v
```

Expected: eight tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-08: fact ID computation"
```

---

## Task 9: `sign_fact` and `verify_fact`

**Spec reference:** The Fact → Canonical Format. The `signature` field is the Ed25519 signature over the canonical JSON of the fact with the `id` populated and the `signature` field set to the empty string.

**Files:**
- Modify: `jtfprotocol/fact.py`
- Modify: `tests/test_fact.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fact.py`:

```python
def test_sign_and_verify_fact_roundtrip(sample_fact_dict):
    from jtfprotocol import identity

    priv, pub = identity.generate_keypair()
    sample_fact_dict["server"]["public_key_id"] = identity.public_key_id(pub)
    signed = fact_module.sign_fact(sample_fact_dict, priv)
    assert signed["signature"] != ""
    assert signed["id"].startswith("sha256:")
    assert fact_module.verify_fact(signed, pub) is True


def test_verify_fact_rejects_tampered_text(sample_fact_dict):
    from jtfprotocol import identity

    priv, pub = identity.generate_keypair()
    sample_fact_dict["server"]["public_key_id"] = identity.public_key_id(pub)
    signed = fact_module.sign_fact(sample_fact_dict, priv)
    signed["fact"] = "The vote was 0 to 0."
    assert fact_module.verify_fact(signed, pub) is False
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_fact.py -v
```

Expected: `AttributeError: module 'jtfprotocol.fact' has no attribute 'sign_fact'`.

- [ ] **Step 3: Implement sign_fact and verify_fact**

Append to `jtfprotocol/fact.py`:

```python
from jtfprotocol import identity as _identity
import base64


def _canonical_for_signing(fact_dict: dict) -> bytes:
    """Serialize a fact for signing or verification.

    Populates id, empties the signature field, then canonical-JSON-encodes
    the result. The returned bytes are what gets signed / verified.
    """
    to_sign = copy.deepcopy(fact_dict)
    to_sign["id"] = compute_fact_id(fact_dict)
    to_sign["signature"] = ""
    return canonical_json(to_sign).encode("utf-8")


def sign_fact(fact_dict: dict, priv) -> dict:
    """Return a new fact dict with `id` and `signature` populated.

    Does not mutate the input. The signature is base64-encoded.
    """
    signed = copy.deepcopy(fact_dict)
    signed["id"] = compute_fact_id(fact_dict)
    signed["signature"] = ""
    to_sign = canonical_json(signed).encode("utf-8")
    sig_bytes = _identity.sign(priv, to_sign)
    signed["signature"] = base64.b64encode(sig_bytes).decode("ascii")
    return signed


def verify_fact(fact_dict: dict, pub) -> bool:
    """Verify a fact's Ed25519 signature.

    Returns True if the signature is valid and the fact's `id` matches
    the canonical computation. Returns False otherwise. Does not raise.
    """
    try:
        claimed_id = fact_dict.get("id", "")
        if claimed_id != compute_fact_id(fact_dict):
            return False
        sig_b64 = fact_dict.get("signature", "")
        sig = base64.b64decode(sig_b64)
        to_verify = _canonical_for_signing(fact_dict)
        return _identity.verify(pub, to_verify, sig)
    except Exception:
        return False
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_fact.py -v
```

Expected: ten tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-09: sign_fact and verify_fact"
```

---

## Task 10: Two-source minimum compliance check

**Spec reference:** Fact Rules → "Two sources minimum. A fact with fewer than two sources is invalid. The protocol rejects it." Also: "No self-citation."

**Files:**
- Create: `jtfprotocol/compliance.py`
- Create: `tests/test_compliance.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_compliance.py`:

```python
"""Tests for jtfprotocol.compliance."""
import copy

from jtfprotocol import compliance


def test_two_sources_minimum_passes(sample_fact_dict):
    result = compliance.check_two_sources(sample_fact_dict)
    assert result.passed is True


def test_two_sources_minimum_fails_with_one(sample_fact_dict):
    sample_fact_dict["sources"] = sample_fact_dict["sources"][:1]
    result = compliance.check_two_sources(sample_fact_dict)
    assert result.passed is False
    assert "minimum" in result.reason.lower()


def test_two_sources_minimum_fails_with_zero(sample_fact_dict):
    sample_fact_dict["sources"] = []
    result = compliance.check_two_sources(sample_fact_dict)
    assert result.passed is False
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_compliance.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.compliance'`.

- [ ] **Step 3: Implement CheckResult and check_two_sources**

Create `jtfprotocol/compliance.py`:

```python
"""Deterministic methodology compliance checks.

These checks are rule-based, reproducible across implementations, and
require no AI. A fact that fails any of them is non-compliant regardless
of AI assessment.

See documentation/Protocol Ver 1.0 CURRENT.md, "Editorialization
Constraints" and "Deterministic Checks".
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single compliance check."""
    name: str
    passed: bool
    reason: str = ""


def check_two_sources(fact_dict: dict) -> CheckResult:
    """Enforce the two-unrelated-sources minimum."""
    sources = fact_dict.get("sources", [])
    if len(sources) < 2:
        return CheckResult(
            name="two_sources_minimum",
            passed=False,
            reason=f"found {len(sources)} source(s); minimum is 2",
        )
    return CheckResult(name="two_sources_minimum", passed=True)
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_compliance.py -v
```

Expected: three tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-10: two-source minimum compliance check"
```

---

## Task 11: Unrelated-sources compliance check

**Spec reference:** Fact Rules → "Unrelated sources. No common majority shareholder between any two cited sources."

**Files:**
- Modify: `jtfprotocol/compliance.py`
- Modify: `tests/test_compliance.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_compliance.py`:

```python
def test_unrelated_sources_passes_when_different_owners(sample_fact_dict):
    result = compliance.check_unrelated_sources(sample_fact_dict)
    assert result.passed is True


def test_unrelated_sources_fails_when_shared_majority_owner(sample_fact_dict):
    # Make both sources share a common majority owner.
    for src in sample_fact_dict["sources"]:
        src["ownership"] = [{"entity": "MegaCorp", "percentage": 80.0}]
    result = compliance.check_unrelated_sources(sample_fact_dict)
    assert result.passed is False
    assert "megacorp" in result.reason.lower()


def test_unrelated_sources_passes_when_minority_overlap(sample_fact_dict):
    # Both cite the same entity but neither as majority.
    sample_fact_dict["sources"][0]["ownership"] = [
        {"entity": "Thomson Reuters Corporation", "percentage": 100.0},
        {"entity": "Shared Minority Holder", "percentage": 10.0},
    ]
    sample_fact_dict["sources"][1]["ownership"] = [
        {"entity": "Associated Press (nonprofit cooperative)", "percentage": 100.0},
        {"entity": "Shared Minority Holder", "percentage": 15.0},
    ]
    result = compliance.check_unrelated_sources(sample_fact_dict)
    assert result.passed is True
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_compliance.py -v
```

Expected: `AttributeError: module 'jtfprotocol.compliance' has no attribute 'check_unrelated_sources'`.

- [ ] **Step 3: Implement check_unrelated_sources**

Append to `jtfprotocol/compliance.py`:

```python
MAJORITY_THRESHOLD = 50.0


def _majority_owners(source: dict) -> set[str]:
    """Return the set of entities that hold more than 50% of a source."""
    owners = source.get("ownership", [])
    return {
        o["entity"]
        for o in owners
        if o.get("percentage", 0.0) > MAJORITY_THRESHOLD
    }


def check_unrelated_sources(fact_dict: dict) -> CheckResult:
    """Verify no two sources share a common majority shareholder."""
    sources = fact_dict.get("sources", [])
    if len(sources) < 2:
        return CheckResult(
            name="unrelated_sources",
            passed=False,
            reason="need at least 2 sources to assess independence",
        )
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            overlap = _majority_owners(sources[i]) & _majority_owners(sources[j])
            if overlap:
                entity = next(iter(overlap))
                return CheckResult(
                    name="unrelated_sources",
                    passed=False,
                    reason=f"sources {i} and {j} share majority owner: {entity}",
                )
    return CheckResult(name="unrelated_sources", passed=True)
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_compliance.py -v
```

Expected: six tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-11: unrelated-sources compliance check"
```

---

## Task 12: Prohibited-adjective compliance check

**Spec reference:** Editorialization Constraints → "No words from the prohibited subjective-adjective list (see Appendix A; maintained per-channel and per-language)."

Appendix A is forthcoming. Phase 1 ships a minimal seed list sufficient to prove the mechanism. The real list is Phase 6 work.

**Files:**
- Modify: `jtfprotocol/compliance.py`
- Modify: `tests/test_compliance.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_compliance.py`:

```python
def test_prohibited_adjectives_passes_on_neutral_text(sample_fact_dict):
    result = compliance.check_prohibited_adjectives(
        sample_fact_dict,
        prohibited=compliance.SEED_PROHIBITED_EN,
    )
    assert result.passed is True


def test_prohibited_adjectives_fails_on_editorial_word(sample_fact_dict):
    sample_fact_dict["fact"] = "The shocking vote was 143 to 9."
    result = compliance.check_prohibited_adjectives(
        sample_fact_dict,
        prohibited=compliance.SEED_PROHIBITED_EN,
    )
    assert result.passed is False
    assert "shocking" in result.reason.lower()


def test_prohibited_adjectives_is_case_insensitive(sample_fact_dict):
    sample_fact_dict["fact"] = "The HORRIFIC vote was 143 to 9."
    result = compliance.check_prohibited_adjectives(
        sample_fact_dict,
        prohibited=compliance.SEED_PROHIBITED_EN,
    )
    assert result.passed is False


def test_prohibited_adjectives_uses_word_boundaries(sample_fact_dict):
    # "badminton" contains "bad" but should not trigger.
    sample_fact_dict["fact"] = "The badminton tournament concluded."
    result = compliance.check_prohibited_adjectives(
        sample_fact_dict,
        prohibited={"bad"},
    )
    assert result.passed is True
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_compliance.py -v
```

Expected: `AttributeError: module 'jtfprotocol.compliance' has no attribute 'SEED_PROHIBITED_EN'`.

- [ ] **Step 3: Implement the seed list and check_prohibited_adjectives**

Append to `jtfprotocol/compliance.py`:

```python
import re


# Seed list for Phase 1. Appendix A (Phase 6) defines the authoritative,
# per-channel, per-language list. These are words that carry evaluative
# rather than descriptive weight.
SEED_PROHIBITED_EN: frozenset[str] = frozenset({
    "shocking", "horrific", "devastating", "stunning",
    "outrageous", "appalling", "brave", "heroic",
    "tragic", "cowardly", "radical", "extremist",
})


def check_prohibited_adjectives(
    fact_dict: dict,
    prohibited: frozenset[str] | set[str],
) -> CheckResult:
    """Reject fact text containing any word from the prohibited list.

    Matching is case-insensitive and uses word boundaries so that
    'bad' does not match 'badminton'.
    """
    text = fact_dict.get("fact", "").lower()
    hits = []
    for word in prohibited:
        pattern = r"\b" + re.escape(word.lower()) + r"\b"
        if re.search(pattern, text):
            hits.append(word)
    if hits:
        return CheckResult(
            name="prohibited_adjectives",
            passed=False,
            reason=f"fact text contains prohibited word(s): {sorted(hits)}",
        )
    return CheckResult(name="prohibited_adjectives", passed=True)
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_compliance.py -v
```

Expected: ten tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-12: prohibited-adjective compliance check"
```

---

## Task 13: Source-evidence-present compliance check

**Spec reference:** Fact Rules → "Source evidence required. Every source must include a `content_hash` of the page content at fetch time, a `supporting_quote` extracted from the source, and a `context_window` (the text immediately before and after the quote). The `snapshot_url` is required for full-node publication."

**Files:**
- Modify: `jtfprotocol/compliance.py`
- Modify: `tests/test_compliance.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_compliance.py`:

```python
def test_source_evidence_passes_on_complete_fact(sample_fact_dict):
    result = compliance.check_source_evidence(sample_fact_dict, node_type="full")
    assert result.passed is True


def test_source_evidence_fails_missing_content_hash(sample_fact_dict):
    del sample_fact_dict["sources"][0]["content_hash"]
    result = compliance.check_source_evidence(sample_fact_dict, node_type="full")
    assert result.passed is False
    assert "content_hash" in result.reason


def test_source_evidence_fails_missing_supporting_quote(sample_fact_dict):
    del sample_fact_dict["sources"][1]["supporting_quote"]
    result = compliance.check_source_evidence(sample_fact_dict, node_type="full")
    assert result.passed is False


def test_source_evidence_fails_missing_context_window(sample_fact_dict):
    del sample_fact_dict["sources"][0]["context_window"]
    result = compliance.check_source_evidence(sample_fact_dict, node_type="full")
    assert result.passed is False


def test_source_evidence_snapshot_required_for_full_node(sample_fact_dict):
    del sample_fact_dict["sources"][0]["snapshot_url"]
    result = compliance.check_source_evidence(sample_fact_dict, node_type="full")
    assert result.passed is False


def test_source_evidence_snapshot_optional_for_light_node(sample_fact_dict):
    del sample_fact_dict["sources"][0]["snapshot_url"]
    result = compliance.check_source_evidence(sample_fact_dict, node_type="light")
    assert result.passed is True
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_compliance.py -v
```

Expected: `AttributeError: module 'jtfprotocol.compliance' has no attribute 'check_source_evidence'`.

- [ ] **Step 3: Implement check_source_evidence**

Append to `jtfprotocol/compliance.py`:

```python
def check_source_evidence(fact_dict: dict, node_type: str = "full") -> CheckResult:
    """Verify every source carries the required evidence fields.

    Required always: content_hash, supporting_quote, context_window.
    Required for full nodes: snapshot_url.
    """
    sources = fact_dict.get("sources", [])
    required = ["content_hash", "supporting_quote", "context_window"]
    if node_type == "full":
        required = required + ["snapshot_url"]
    for i, src in enumerate(sources):
        missing = [f for f in required if not src.get(f)]
        if missing:
            return CheckResult(
                name="source_evidence",
                passed=False,
                reason=f"source {i} missing: {missing}",
            )
        ctx = src.get("context_window", {})
        if not ctx.get("before") or not ctx.get("after") or not ctx.get("context_hash"):
            return CheckResult(
                name="source_evidence",
                passed=False,
                reason=f"source {i} context_window missing before/after/context_hash",
            )
    return CheckResult(name="source_evidence", passed=True)
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_compliance.py -v
```

Expected: sixteen tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-13: source-evidence-present compliance check"
```

---

## Task 14: Supporting-quote-in-content compliance check (scaffold)

**Spec reference:** Verification → Source Checking, Step 1. "Does the `supporting_quote` appear in the content whose hash matches `content_hash`? This is the fastest and most deterministic check."

Phase 1 implements the string-matching primitive; fetching and hashing live content is Phase 3. For now, the check accepts the content as a parameter so callers (Phase 3 or operator tests) can provide it.

**Files:**
- Modify: `jtfprotocol/compliance.py`
- Modify: `tests/test_compliance.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_compliance.py`:

```python
def test_quote_in_content_passes_on_match():
    content = "This is some text. The quote appears here. More text."
    quote = "The quote appears here."
    result = compliance.check_quote_in_content(content, quote)
    assert result.passed is True


def test_quote_in_content_fails_on_absence():
    content = "Totally unrelated text."
    quote = "The quote does not appear here."
    result = compliance.check_quote_in_content(content, quote)
    assert result.passed is False


def test_quote_in_content_normalizes_whitespace():
    content = "Text. The quote     appears here. More."
    quote = "The quote appears here."
    result = compliance.check_quote_in_content(content, quote)
    assert result.passed is True
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_compliance.py -v
```

Expected: `AttributeError: module 'jtfprotocol.compliance' has no attribute 'check_quote_in_content'`.

- [ ] **Step 3: Implement check_quote_in_content**

Append to `jtfprotocol/compliance.py`:

```python
def _normalize_whitespace(s: str) -> str:
    """Collapse consecutive whitespace and strip edges."""
    return re.sub(r"\s+", " ", s).strip()


def check_quote_in_content(content: str, quote: str) -> CheckResult:
    """Verify the supporting quote appears in the content.

    Both strings are normalized (consecutive whitespace collapsed, edges
    stripped) before comparison. The comparison is substring-based, not
    word-boundary, because real quotes can start and end mid-sentence.
    """
    norm_content = _normalize_whitespace(content)
    norm_quote = _normalize_whitespace(quote)
    if norm_quote in norm_content:
        return CheckResult(name="quote_in_content", passed=True)
    return CheckResult(
        name="quote_in_content",
        passed=False,
        reason="supporting_quote not found in content (whitespace-normalized)",
    )
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_compliance.py -v
```

Expected: nineteen tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-14: supporting-quote-in-content compliance check"
```

---

## Task 15: Claim-type required fields compliance check

**Spec reference:** Fact Rules → Claim-type required fields table:

| Claim type | Required fields |
|---|---|
| death, injury | timeframe, source attribution |
| financial | currency, time basis |
| legal | jurisdiction |
| vote, election | vote tally or voter count |

**Files:**
- Modify: `jtfprotocol/compliance.py`
- Modify: `tests/test_compliance.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_compliance.py`:

```python
def test_claim_type_vote_passes_with_quantities(sample_fact_dict):
    # sample_fact is a vote with quantities populated.
    result = compliance.check_claim_type_fields(sample_fact_dict)
    assert result.passed is True


def test_claim_type_vote_fails_without_quantities(sample_fact_dict):
    sample_fact_dict["structured_extraction"]["quantities"] = []
    result = compliance.check_claim_type_fields(sample_fact_dict)
    assert result.passed is False


def test_claim_type_financial_requires_currency(sample_fact_dict):
    sample_fact_dict["structured_extraction"]["claim_type"] = "financial"
    sample_fact_dict["structured_extraction"]["quantities"] = [
        {"value": 1000000, "context": "loss"}
    ]  # no currency
    result = compliance.check_claim_type_fields(sample_fact_dict)
    assert result.passed is False


def test_claim_type_financial_passes_with_currency(sample_fact_dict):
    sample_fact_dict["structured_extraction"]["claim_type"] = "financial"
    sample_fact_dict["structured_extraction"]["quantities"] = [
        {"value": 1000000, "context": "USD annual loss"}
    ]
    result = compliance.check_claim_type_fields(sample_fact_dict)
    assert result.passed is True


def test_claim_type_legal_requires_jurisdiction(sample_fact_dict):
    sample_fact_dict["structured_extraction"]["claim_type"] = "legal"
    sample_fact_dict["structured_extraction"]["location"] = ""
    result = compliance.check_claim_type_fields(sample_fact_dict)
    assert result.passed is False


def test_claim_type_death_requires_timeframe(sample_fact_dict):
    sample_fact_dict["structured_extraction"]["claim_type"] = "death"
    sample_fact_dict["structured_extraction"]["event_time"] = {"start": "", "end": ""}
    result = compliance.check_claim_type_fields(sample_fact_dict)
    assert result.passed is False
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_compliance.py -v
```

Expected: `AttributeError: module 'jtfprotocol.compliance' has no attribute 'check_claim_type_fields'`.

- [ ] **Step 3: Implement check_claim_type_fields**

Append to `jtfprotocol/compliance.py`:

```python
CURRENCY_TOKENS: frozenset[str] = frozenset({
    "usd", "eur", "gbp", "jpy", "cny", "inr", "cad", "aud", "chf", "krw",
    "$", "€", "£", "¥", "dollar", "euro", "pound", "yen", "yuan", "rupee",
})


def _extraction(fact_dict: dict) -> dict:
    return fact_dict.get("structured_extraction", {})


def check_claim_type_fields(fact_dict: dict) -> CheckResult:
    """Enforce per-claim-type required fields.

    vote, election    -> quantities non-empty
    financial         -> a currency token appears in quantities' context
    legal             -> location non-empty (jurisdiction proxy)
    death, injury     -> event_time.start or event_time.end populated
    """
    ex = _extraction(fact_dict)
    ct = ex.get("claim_type", "")
    quantities = ex.get("quantities", [])

    if ct in {"vote", "election"}:
        if not quantities:
            return CheckResult(
                name="claim_type_fields",
                passed=False,
                reason=f"{ct} requires quantities (vote tally or voter count)",
            )
        return CheckResult(name="claim_type_fields", passed=True)

    if ct == "financial":
        contexts = " ".join(q.get("context", "").lower() for q in quantities)
        if not any(tok in contexts for tok in CURRENCY_TOKENS):
            return CheckResult(
                name="claim_type_fields",
                passed=False,
                reason="financial claim missing currency token in quantities.context",
            )
        return CheckResult(name="claim_type_fields", passed=True)

    if ct == "legal":
        if not ex.get("location"):
            return CheckResult(
                name="claim_type_fields",
                passed=False,
                reason="legal claim missing jurisdiction (location)",
            )
        return CheckResult(name="claim_type_fields", passed=True)

    if ct in {"death", "injury"}:
        evt = ex.get("event_time", {}) or {}
        if not (evt.get("start") or evt.get("end")):
            return CheckResult(
                name="claim_type_fields",
                passed=False,
                reason=f"{ct} claim missing timeframe (event_time)",
            )
        return CheckResult(name="claim_type_fields", passed=True)

    # Unknown / unlisted claim types pass; future versions may add rows.
    return CheckResult(name="claim_type_fields", passed=True)
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_compliance.py -v
```

Expected: twenty-five tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-15: claim-type required fields compliance check"
```

---

## Task 16: `check_compliance` orchestrator

**Spec reference:** Editorialization Constraints → "The deterministic checks are the hard gate. A fact that fails them is non-compliant regardless of AI assessment."

**Files:**
- Modify: `jtfprotocol/compliance.py`
- Modify: `tests/test_compliance.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_compliance.py`:

```python
def test_check_compliance_passes_on_valid_fact(sample_fact_dict):
    result = compliance.check_compliance(sample_fact_dict)
    assert result.passed is True
    # All sub-checks should be in the results list.
    names = {r.name for r in result.checks}
    assert "two_sources_minimum" in names
    assert "unrelated_sources" in names
    assert "source_evidence" in names
    assert "prohibited_adjectives" in names
    assert "claim_type_fields" in names


def test_check_compliance_fails_if_any_sub_check_fails(sample_fact_dict):
    sample_fact_dict["sources"] = sample_fact_dict["sources"][:1]
    result = compliance.check_compliance(sample_fact_dict)
    assert result.passed is False
    # The failing sub-check is included.
    failing = [c for c in result.checks if not c.passed]
    assert any(c.name == "two_sources_minimum" for c in failing)


def test_check_compliance_accepts_custom_prohibited_list(sample_fact_dict):
    sample_fact_dict["fact"] = "The excellent vote was 143 to 9."
    result = compliance.check_compliance(
        sample_fact_dict,
        prohibited={"excellent"},
    )
    assert result.passed is False
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_compliance.py -v
```

Expected: `AttributeError: module 'jtfprotocol.compliance' has no attribute 'check_compliance'`.

- [ ] **Step 3: Implement ComplianceResult and check_compliance**

Append to `jtfprotocol/compliance.py`:

```python
@dataclass(frozen=True)
class ComplianceResult:
    passed: bool
    checks: tuple[CheckResult, ...]


def check_compliance(
    fact_dict: dict,
    node_type: str = "full",
    prohibited: frozenset[str] | set[str] | None = None,
) -> ComplianceResult:
    """Run every deterministic methodology compliance check.

    A ComplianceResult is returned containing every sub-check's
    CheckResult. `passed` is True only if every sub-check passed.

    `prohibited` defaults to SEED_PROHIBITED_EN. Callers targeting a
    specific channel or language pass their own list.
    """
    if prohibited is None:
        prohibited = SEED_PROHIBITED_EN

    checks = (
        check_two_sources(fact_dict),
        check_unrelated_sources(fact_dict),
        check_source_evidence(fact_dict, node_type=node_type),
        check_prohibited_adjectives(fact_dict, prohibited=prohibited),
        check_claim_type_fields(fact_dict),
    )
    passed = all(c.passed for c in checks)
    return ComplianceResult(passed=passed, checks=checks)
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_compliance.py -v
```

Expected: twenty-eight tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-16: check_compliance orchestrator"
```

---

## Task 17: Extraction backend interface and `StructuredFact`

**Spec reference:** Extraction Backends (new section in spec) + Structured Extraction. Defines the pluggable interface that backends implement.

**Files:**
- Create: `jtfprotocol/extraction.py`
- Create: `tests/test_extraction.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_extraction.py`:

```python
"""Tests for jtfprotocol.extraction."""
import pytest

from jtfprotocol import extraction


def test_extraction_backend_is_abstract():
    with pytest.raises(TypeError):
        extraction.ExtractionBackend()


def test_structured_fact_is_frozen_dataclass():
    sf = extraction.StructuredFact(
        subjects=["Q47010"],
        subjects_text=["United Nations General Assembly"],
        action="voted",
        objects=["Republic of Somaliland"],
        quantities=[{"value": 143, "context": "votes in favor"}],
        location="UN Headquarters, New York",
        event_time={"start": "2026-04-18T14:00:00Z", "end": "2026-04-18T15:00:00Z"},
        claim_type="vote",
    )
    with pytest.raises(Exception):
        sf.action = "something else"


def test_backend_identifier_is_documented():
    assert extraction.BACKEND_ANTHROPIC == "anthropic"
    assert extraction.BACKEND_OPENAI == "openai"
    assert extraction.BACKEND_OLLAMA == "ollama"
    assert extraction.BACKEND_LMSTUDIO == "lmstudio"
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
pytest tests/test_extraction.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.extraction'`.

- [ ] **Step 3: Implement the ABC and the dataclass**

Create `jtfprotocol/extraction.py`:

```python
"""Pluggable extraction backends.

Every JTF server extracts structured facts from raw source text. The
protocol is backend-agnostic: commercial APIs and local inference are
both first-class. This module defines the interface and ships two
concrete backends (Anthropic, and an OpenAI-compatible backend that
covers OpenAI / Ollama / LM Studio).

See documentation/Protocol Ver 1.0 CURRENT.md, section "Extraction Backends".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


BACKEND_ANTHROPIC = "anthropic"
BACKEND_OPENAI = "openai"
BACKEND_OLLAMA = "ollama"
BACKEND_LMSTUDIO = "lmstudio"
BACKEND_CUSTOM = "custom"

SUPPORTED_BACKENDS = frozenset({
    BACKEND_ANTHROPIC,
    BACKEND_OPENAI,
    BACKEND_OLLAMA,
    BACKEND_LMSTUDIO,
    BACKEND_CUSTOM,
})


@dataclass(frozen=True)
class StructuredFact:
    """The extracted structured form of a fact.

    Matches the `structured_extraction` object in the canonical fact
    schema. Free of signature, sources, and identity fields — those are
    added by the caller (Phase 5 integration) when assembling the
    canonical fact.
    """
    subjects: list[str]           # Wikidata QIDs where available
    subjects_text: list[str]      # Human-readable names
    action: str                   # From controlled vocabulary
    objects: list[str]
    quantities: list[dict]        # [{value, context}, ...]
    location: str
    event_time: dict              # {start, end} ISO-8601
    claim_type: str


class ExtractionBackend(ABC):
    """Interface every extraction backend implements."""

    backend_id: str = ""   # One of SUPPORTED_BACKENDS
    model: str = ""        # vendor:model:version
    prompt_version: str = ""

    @abstractmethod
    def extract_fact(
        self,
        source_text: str,
        source_metadata: dict,
    ) -> StructuredFact:
        """Extract a StructuredFact from raw source text.

        `source_text` is the article content. `source_metadata` carries
        the source name, URL, publication date, and any other hints the
        prompt may incorporate.

        Raises:
            ExtractionError: if the backend returns malformed output or
                a non-recoverable error.
        """


class ExtractionError(RuntimeError):
    """Raised when a backend fails to produce a valid StructuredFact."""
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_extraction.py -v
```

Expected: three tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-17: extraction backend ABC and StructuredFact"
```

---

## Task 18: Shared fact-extraction prompt template

**Spec reference:** The Fact → Structured Extraction. "The extraction step is AI-assisted... controlled vocabulary defined in Appendix B."

The prompt is identical across backends so that any divergence between backends traces to the model, not the prompt.

**Files:**
- Create: `jtfprotocol/prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_prompts.py`:

```python
"""Tests for jtfprotocol.prompts."""
from jtfprotocol import prompts


def test_prompt_template_is_deterministic():
    p1 = prompts.build_extraction_prompt("text A", {"name": "Reuters"})
    p2 = prompts.build_extraction_prompt("text A", {"name": "Reuters"})
    assert p1 == p2


def test_prompt_includes_controlled_action_vocabulary():
    p = prompts.build_extraction_prompt("x", {"name": "y"})
    for verb in ["voted", "approved", "signed"]:
        assert verb in p


def test_prompt_includes_claim_types():
    p = prompts.build_extraction_prompt("x", {"name": "y"})
    for ct in ["vote", "financial", "legal", "death"]:
        assert ct in p


def test_prompt_includes_source_text():
    p = prompts.build_extraction_prompt(
        "The General Assembly voted 143 to 9.",
        {"name": "Reuters", "url": "https://reuters.com/x"},
    )
    assert "The General Assembly voted 143 to 9." in p
    assert "Reuters" in p


def test_prompt_version_is_declared():
    assert prompts.PROMPT_VERSION == "jtf-extract-v3"
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
pytest tests/test_prompts.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.prompts'`.

- [ ] **Step 3: Implement prompts.py**

Create `jtfprotocol/prompts.py`:

```python
"""Shared fact-extraction prompt template.

Every backend uses the same prompt. Divergence between backends traces
to the model, never to the prompt. If the prompt changes, bump
PROMPT_VERSION and update the compliance/verification tests.
"""
from __future__ import annotations


PROMPT_VERSION = "jtf-extract-v3"


CONTROLLED_ACTIONS: tuple[str, ...] = (
    "voted", "approved", "adopted", "announced", "signed",
    "arrested", "charged", "acquired", "merged", "launched",
    "deployed", "struck", "collapsed", "resigned", "appointed",
    "ratified", "vetoed", "released", "detained", "fined",
)

CLAIM_TYPES: tuple[str, ...] = (
    "vote", "election", "financial", "legal",
    "death", "injury", "announcement", "agreement",
)


EXTRACTION_TEMPLATE = """You extract structured facts from news source text for
the JTF Protocol. The methodology is strict: only verifiable facts, no
editorializing, no speculation, no adjectives.

Return a JSON object with exactly these fields:

- subjects: list of Wikidata QIDs when available (e.g. "Q47010"). Empty list if unknown.
- subjects_text: list of human-readable entity names.
- action: a single verb from this controlled vocabulary: {actions}.
- objects: list of strings naming the objects of the action.
- quantities: list of {{value, context}} pairs. `value` is numeric. `context` describes what is counted.
- location: string, most specific known location. Empty string if unknown.
- event_time: {{start, end}} with ISO-8601 timestamps. Use the same value for both if only a single moment is known.
- claim_type: one of {claim_types}.

Do not add any other fields. Do not include commentary. Do not use
subjective adjectives. Do not speculate beyond what the source text
states.

Source: {source_name}
URL: {source_url}
Text:
{source_text}

Return only the JSON object.
"""


def build_extraction_prompt(source_text: str, source_metadata: dict) -> str:
    """Render the shared prompt for a given source."""
    return EXTRACTION_TEMPLATE.format(
        actions=", ".join(CONTROLLED_ACTIONS),
        claim_types=", ".join(CLAIM_TYPES),
        source_name=source_metadata.get("name", ""),
        source_url=source_metadata.get("url", ""),
        source_text=source_text,
    )
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_prompts.py -v
```

Expected: five tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-18: shared fact-extraction prompt template"
```

---

## Task 19: `AnthropicBackend`

**Spec reference:** Extraction Backends → "Commercial API backends (e.g., Anthropic, OpenAI) are straightforward to set up and scale."

**Files:**
- Modify: `jtfprotocol/extraction.py`
- Modify: `tests/test_extraction.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_extraction.py`:

```python
from unittest.mock import MagicMock


def test_anthropic_backend_calls_api_and_parses_json():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"subjects": ["Q47010"], "subjects_text": ["UN General Assembly"], "action": "voted", "objects": ["Somaliland"], "quantities": [{"value": 143, "context": "votes in favor"}], "location": "New York", "event_time": {"start": "2026-04-18T14:00:00Z", "end": "2026-04-18T15:00:00Z"}, "claim_type": "vote"}')]
    mock_client.messages.create.return_value = mock_response

    backend = extraction.AnthropicBackend(
        client=mock_client,
        model="claude-haiku-4-5-20251001",
    )
    result = backend.extract_fact(
        "The UN General Assembly voted 143 to 9.",
        {"name": "Reuters", "url": "https://reuters.com/x"},
    )
    assert isinstance(result, extraction.StructuredFact)
    assert result.action == "voted"
    assert result.subjects == ["Q47010"]
    mock_client.messages.create.assert_called_once()


def test_anthropic_backend_raises_on_non_json_response():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="this is not json")]
    mock_client.messages.create.return_value = mock_response

    backend = extraction.AnthropicBackend(
        client=mock_client,
        model="claude-haiku-4-5-20251001",
    )
    with pytest.raises(extraction.ExtractionError):
        backend.extract_fact("x", {"name": "y", "url": "z"})


def test_anthropic_backend_declares_identifiers():
    backend = extraction.AnthropicBackend(
        client=MagicMock(),
        model="claude-haiku-4-5-20251001",
    )
    assert backend.backend_id == extraction.BACKEND_ANTHROPIC
    assert backend.model == "anthropic:claude-haiku-4-5-20251001"
    assert backend.prompt_version == "jtf-extract-v3"
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_extraction.py -v
```

Expected: `AttributeError: module 'jtfprotocol.extraction' has no attribute 'AnthropicBackend'`.

- [ ] **Step 3: Implement AnthropicBackend**

Append to `jtfprotocol/extraction.py`:

```python
import json

from jtfprotocol import prompts


class AnthropicBackend(ExtractionBackend):
    """Fact extraction via the Anthropic Messages API."""

    backend_id = BACKEND_ANTHROPIC

    def __init__(self, client, model: str, max_tokens: int = 1024):
        """Construct an AnthropicBackend.

        Args:
            client: An initialized `anthropic.Anthropic` client. Passed
                in rather than constructed here so tests can inject a
                mock.
            model: The model identifier accepted by the Anthropic SDK
                (e.g. "claude-haiku-4-5-20251001"). Stored on the
                instance as `self.model` in canonical `vendor:model`
                form for protocol disclosure.
            max_tokens: Maximum tokens in the model response.
        """
        self._client = client
        self._model_raw = model
        self.model = f"anthropic:{model}"
        self.prompt_version = prompts.PROMPT_VERSION
        self._max_tokens = max_tokens

    def extract_fact(
        self,
        source_text: str,
        source_metadata: dict,
    ) -> StructuredFact:
        prompt = prompts.build_extraction_prompt(source_text, source_metadata)
        response = self._client.messages.create(
            model=self._model_raw,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            raw_text = response.content[0].text
            data = json.loads(raw_text)
            return StructuredFact(
                subjects=data["subjects"],
                subjects_text=data["subjects_text"],
                action=data["action"],
                objects=data["objects"],
                quantities=data["quantities"],
                location=data["location"],
                event_time=data["event_time"],
                claim_type=data["claim_type"],
            )
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError) as e:
            raise ExtractionError(
                f"Anthropic backend returned malformed output: {e}"
            ) from e
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_extraction.py -v
```

Expected: six tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-19: AnthropicBackend"
```

---

## Task 20: `OpenAICompatibleBackend` (covers OpenAI, Ollama, LM Studio)

**Spec reference:** Extraction Backends → "Locally-hosted backends (e.g., Ollama, LM Studio, llama.cpp) run on commodity hardware."

OpenAI's Chat Completions API, Ollama's OpenAI-compatible endpoint, and LM Studio's server all speak the same wire format. One backend class with configurable `base_url` and `backend_id` covers all three.

**Files:**
- Modify: `jtfprotocol/extraction.py`
- Modify: `tests/test_extraction.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_extraction.py`:

```python
def test_openai_compatible_backend_calls_api_and_parses_json():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"subjects": [], "subjects_text": ["Example"], "action": "announced", "objects": ["Policy"], "quantities": [], "location": "Washington", "event_time": {"start": "2026-04-18T10:00:00Z", "end": "2026-04-18T10:00:00Z"}, "claim_type": "announcement"}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    backend = extraction.OpenAICompatibleBackend(
        client=mock_client,
        model="qwen2.5:72b-instruct-q5_K_M",
        backend_id=extraction.BACKEND_OLLAMA,
    )
    result = backend.extract_fact(
        "The agency announced a new policy.",
        {"name": "Reuters", "url": "https://reuters.com/y"},
    )
    assert isinstance(result, extraction.StructuredFact)
    assert result.action == "announced"


def test_openai_compatible_backend_declares_backend_id():
    for bid in [extraction.BACKEND_OPENAI, extraction.BACKEND_OLLAMA, extraction.BACKEND_LMSTUDIO]:
        backend = extraction.OpenAICompatibleBackend(
            client=MagicMock(),
            model="m",
            backend_id=bid,
        )
        assert backend.backend_id == bid


def test_openai_compatible_backend_rejects_invalid_backend_id():
    with pytest.raises(ValueError):
        extraction.OpenAICompatibleBackend(
            client=MagicMock(),
            model="m",
            backend_id="not_a_valid_backend",
        )


def test_openai_compatible_backend_raises_on_non_json():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "not json at all"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    backend = extraction.OpenAICompatibleBackend(
        client=mock_client,
        model="m",
        backend_id=extraction.BACKEND_OLLAMA,
    )
    with pytest.raises(extraction.ExtractionError):
        backend.extract_fact("x", {"name": "y", "url": "z"})
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_extraction.py -v
```

Expected: `AttributeError: module 'jtfprotocol.extraction' has no attribute 'OpenAICompatibleBackend'`.

- [ ] **Step 3: Implement OpenAICompatibleBackend**

Append to `jtfprotocol/extraction.py`:

```python
_OPENAI_COMPATIBLE_BACKEND_IDS = frozenset({
    BACKEND_OPENAI, BACKEND_OLLAMA, BACKEND_LMSTUDIO, BACKEND_CUSTOM,
})


class OpenAICompatibleBackend(ExtractionBackend):
    """Fact extraction via any OpenAI-compatible Chat Completions endpoint.

    Used for:
      - OpenAI official API (backend_id="openai")
      - Ollama's OpenAI-compatible endpoint (backend_id="ollama")
      - LM Studio (backend_id="lmstudio")
      - Any other self-hosted OpenAI-compatible server (backend_id="custom")

    The caller constructs an SDK client pointed at the correct base URL
    and passes it in. This class is transport-agnostic — it only speaks
    the Chat Completions wire format.
    """

    def __init__(
        self,
        client,
        model: str,
        backend_id: str,
        max_tokens: int = 1024,
    ):
        if backend_id not in _OPENAI_COMPATIBLE_BACKEND_IDS:
            raise ValueError(
                f"backend_id must be one of {sorted(_OPENAI_COMPATIBLE_BACKEND_IDS)}, "
                f"got {backend_id!r}"
            )
        self._client = client
        self._model_raw = model
        self.backend_id = backend_id
        self.model = f"{backend_id}:{model}"
        self.prompt_version = prompts.PROMPT_VERSION
        self._max_tokens = max_tokens

    def extract_fact(
        self,
        source_text: str,
        source_metadata: dict,
    ) -> StructuredFact:
        prompt = prompts.build_extraction_prompt(source_text, source_metadata)
        response = self._client.chat.completions.create(
            model=self._model_raw,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            raw_text = response.choices[0].message.content
            data = json.loads(raw_text)
            return StructuredFact(
                subjects=data["subjects"],
                subjects_text=data["subjects_text"],
                action=data["action"],
                objects=data["objects"],
                quantities=data["quantities"],
                location=data["location"],
                event_time=data["event_time"],
                claim_type=data["claim_type"],
            )
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError) as e:
            raise ExtractionError(
                f"{self.backend_id} backend returned malformed output: {e}"
            ) from e
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_extraction.py -v
```

Expected: ten tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-20: OpenAICompatibleBackend (OpenAI, Ollama, LM Studio)"
```

---

## Task 21: `get_backend` factory from config

**Spec reference:** Extraction Backends → "Operators declare their extraction backend in the well-known endpoint."

The factory is the single entry point callers use to construct the configured backend.

**Files:**
- Modify: `jtfprotocol/extraction.py`
- Modify: `tests/test_extraction.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_extraction.py`:

```python
def test_get_backend_returns_anthropic_when_configured():
    cfg = {
        "backend": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "api_key": "sk-ant-fake",
    }
    backend = extraction.get_backend(cfg)
    assert isinstance(backend, extraction.AnthropicBackend)
    assert backend.backend_id == "anthropic"


def test_get_backend_returns_ollama_when_configured():
    cfg = {
        "backend": "ollama",
        "model": "qwen2.5:72b-instruct-q5_K_M",
        "base_url": "http://localhost:11434/v1",
    }
    backend = extraction.get_backend(cfg)
    assert isinstance(backend, extraction.OpenAICompatibleBackend)
    assert backend.backend_id == "ollama"


def test_get_backend_returns_lmstudio_when_configured():
    cfg = {
        "backend": "lmstudio",
        "model": "qwen2.5-72b-instruct",
        "base_url": "http://localhost:1234/v1",
    }
    backend = extraction.get_backend(cfg)
    assert isinstance(backend, extraction.OpenAICompatibleBackend)
    assert backend.backend_id == "lmstudio"


def test_get_backend_rejects_unknown_backend():
    with pytest.raises(ValueError):
        extraction.get_backend({"backend": "nonsense", "model": "x"})
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
pytest tests/test_extraction.py -v
```

Expected: `AttributeError: module 'jtfprotocol.extraction' has no attribute 'get_backend'`.

- [ ] **Step 3: Implement get_backend**

Append to `jtfprotocol/extraction.py`:

```python
def get_backend(config: dict) -> ExtractionBackend:
    """Construct the configured ExtractionBackend.

    Expected config keys:
      - backend:  one of SUPPORTED_BACKENDS
      - model:    the vendor-specific model id (no namespace prefix)
      - api_key:  required for commercial backends
      - base_url: required for openai-compatible local backends

    Lazily imports the vendor SDKs so that an operator running only a
    local backend does not need the `anthropic` SDK installed (and vice
    versa).
    """
    backend_id = config.get("backend", "").lower()
    model = config.get("model", "")
    if not model:
        raise ValueError("config must specify 'model'")

    if backend_id == BACKEND_ANTHROPIC:
        import anthropic

        api_key = config.get("api_key")
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        return AnthropicBackend(client=client, model=model)

    if backend_id in {BACKEND_OPENAI, BACKEND_OLLAMA, BACKEND_LMSTUDIO, BACKEND_CUSTOM}:
        import openai

        kwargs = {}
        if config.get("api_key"):
            kwargs["api_key"] = config["api_key"]
        if config.get("base_url"):
            kwargs["base_url"] = config["base_url"]
        # Ollama and LM Studio accept any non-empty api_key.
        if backend_id in {BACKEND_OLLAMA, BACKEND_LMSTUDIO} and "api_key" not in kwargs:
            kwargs["api_key"] = "not-needed"
        client = openai.OpenAI(**kwargs)
        return OpenAICompatibleBackend(
            client=client,
            model=model,
            backend_id=backend_id,
        )

    raise ValueError(f"unsupported backend: {backend_id!r}")
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_extraction.py -v
```

Expected: fourteen tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-21: get_backend factory"
```

---

## Task 22: `generate_well_known` for `/.well-known/jtf.json`

**Spec reference:** Discovery → The Well-Known Endpoint. The full JSON schema with `server`, `extraction`, `feeds`, `peers`, `signature`.

**Files:**
- Create: `jtfprotocol/well_known.py`
- Create: `tests/test_well_known.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_well_known.py`:

```python
"""Tests for jtfprotocol.well_known."""
import json

from jtfprotocol import identity, well_known


def test_generate_well_known_has_required_top_level_fields():
    priv, pub = identity.generate_keypair()
    doc = well_known.generate_well_known(
        priv=priv,
        pub=pub,
        server_info={
            "domain": "example.com",
            "channel": "global",
            "name": "Example Server",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 24940,
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
        peers=[],
    )
    assert doc["jtf_protocol_version"] == 1
    assert doc["server"]["domain"] == "example.com"
    assert doc["server"]["public_key_id"].startswith("sha256:")
    assert doc["extraction"]["backend"] == "ollama"
    assert "signature" in doc


def test_generate_well_known_is_verifiable():
    priv, pub = identity.generate_keypair()
    doc = well_known.generate_well_known(
        priv=priv,
        pub=pub,
        server_info={
            "domain": "example.com",
            "channel": "global",
            "name": "Example Server",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 24940,
            "location_country": "US",
        },
        extraction_info={"backend": "anthropic", "model": "anthropic:claude-haiku:4-5", "prompt_version": "jtf-extract-v3"},
        feeds={"facts_rss": "/feed.xml"},
        peers=[],
    )
    assert well_known.verify_well_known(doc, pub) is True


def test_generate_well_known_rejects_invalid_backend():
    priv, pub = identity.generate_keypair()
    import pytest

    with pytest.raises(ValueError, match="backend"):
        well_known.generate_well_known(
            priv=priv,
            pub=pub,
            server_info={
                "domain": "example.com",
                "channel": "global",
                "name": "Example",
                "started_at": "2026-04-19T00:00:00Z",
                "node_type": "full",
                "asn": 0,
                "location_country": "US",
            },
            extraction_info={"backend": "bogus", "model": "x", "prompt_version": "v"},
            feeds={},
            peers=[],
        )
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
pytest tests/test_well_known.py -v
```

Expected: `ModuleNotFoundError: No module named 'jtfprotocol.well_known'`.

- [ ] **Step 3: Implement generate_well_known and verify_well_known**

Create `jtfprotocol/well_known.py`:

```python
"""`/.well-known/jtf.json` generation and verification.

The well-known endpoint is the protocol's handshake. Every server
publishes a signed identity document describing its keys, channel,
extraction backend, feeds, and known peers. See
documentation/Protocol Ver 1.0 CURRENT.md, section "Discovery → The
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
    peers: list[dict],
) -> dict:
    """Build and sign the `/.well-known/jtf.json` document.

    Returns the document as a dict ready to be served as JSON. The
    document contains a `signature` over the canonical JSON of the
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

    Returns True on success. False otherwise. Does not raise.
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
```

- [ ] **Step 4: Run the tests to confirm they pass**

```bash
pytest tests/test_well_known.py -v
```

Expected: three tests pass.

- [ ] **Step 5: Commit**

```bash
./bu.sh "PHASE1-22: generate_well_known and verify_well_known"
```

---

## Task 23: Phase 1 integration smoke test

**Spec reference:** Phase 1 as a whole. This test crosses every module to prove the pieces compose.

**Files:**
- Create: `tests/test_smoke_phase1.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_smoke_phase1.py`:

```python
"""End-to-end smoke test across every Phase 1 module.

Proves that the pieces compose: generate an identity, render the
well-known document, sign a fact that passes deterministic compliance,
and verify that fact.
"""
from unittest.mock import MagicMock

from jtfprotocol import compliance, extraction, fact, identity, well_known


def test_phase1_composition(sample_fact_dict):
    # 1) Identity
    priv, pub = identity.generate_keypair()
    kid = identity.public_key_id(pub)
    assert kid.startswith("sha256:")

    # 2) Well-known endpoint for this server
    wk = well_known.generate_well_known(
        priv=priv,
        pub=pub,
        server_info={
            "domain": "jtfnews.org",
            "channel": "global",
            "name": "JTF News",
            "started_at": "2026-04-19T00:00:00Z",
            "node_type": "full",
            "asn": 0,
            "location_country": "US",
        },
        extraction_info={
            "backend": "ollama",
            "model": "ollama:qwen2.5:72b-instruct-q5_K_M",
            "prompt_version": "jtf-extract-v3",
        },
        feeds={"facts_rss": "/feed.xml"},
        peers=[],
    )
    assert well_known.verify_well_known(wk, pub) is True

    # 3) Sign and verify a canonical fact
    sample_fact_dict["server"]["public_key_id"] = kid
    signed = fact.sign_fact(sample_fact_dict, priv)
    assert fact.verify_fact(signed, pub) is True

    # 4) Deterministic compliance on the signed fact
    result = compliance.check_compliance(signed, node_type="full")
    assert result.passed is True, [c for c in result.checks if not c.passed]

    # 5) Backend factory produces a usable OpenAI-compatible backend
    mock_openai = MagicMock()
    import sys

    sys.modules["openai"] = mock_openai
    backend = extraction.get_backend({
        "backend": "ollama",
        "model": "qwen2.5:72b-instruct-q5_K_M",
        "base_url": "http://localhost:11434/v1",
    })
    assert backend.backend_id == "ollama"
    assert backend.model == "ollama:qwen2.5:72b-instruct-q5_K_M"
```

- [ ] **Step 2: Run the test to confirm it passes**

```bash
pytest tests/test_smoke_phase1.py -v
```

Expected: the test passes on the first run because every module is already complete.

- [ ] **Step 3: Run the whole suite and confirm the counts**

```bash
pytest -v
```

Expected: ~46 tests total across identity, fact, compliance, prompts, extraction, well_known, and smoke. All pass.

- [ ] **Step 4: Commit**

```bash
./bu.sh "PHASE1-23: end-to-end smoke test across all Phase 1 modules"
```

---

## Task 24: Public exports and module README

**Spec reference:** Ease of Phase 5 integration. One import statement should be enough for `main.py` to use the protocol primitives.

**Files:**
- Modify: `jtfprotocol/__init__.py`
- Create: `jtfprotocol/README.md`

- [ ] **Step 1: Replace `__init__.py` with explicit exports**

Replace the contents of `jtfprotocol/__init__.py` with:

```python
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
```

- [ ] **Step 2: Create the module README**

Create `jtfprotocol/README.md`:

```markdown
# jtfprotocol

Reference implementation of Phase 1 of the JTF Protocol.

Covers:

- Ed25519 identity (`identity.py`)
- Canonical fact format, signing, verification (`fact.py`)
- Deterministic methodology compliance checks (`compliance.py`)
- Shared extraction prompt template (`prompts.py`)
- Pluggable extraction backends (`extraction.py`) — `AnthropicBackend`, `OpenAICompatibleBackend`
- Well-known endpoint generation and verification (`well_known.py`)

Spec: `../documentation/Protocol Ver 1.0 CURRENT.md`.

## Install

```
pip install -r ../requirements.txt -r ../requirements-dev.txt
```

## Test

```
pytest
```

## Not included in Phase 1

- Peer discovery and gossip (Phase 2)
- Trust scoring and verification credit sharing (Phase 3)
- Corrections and resilience primitives (Phase 4)
- Integration with `main.py` (Phase 5)
- Appendices, wire-protocol spec, trust algorithm reference (Phase 6)
```

- [ ] **Step 3: Run the whole suite one more time**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
./bu.sh "PHASE1-24: public exports and jtfprotocol README"
```

---

## Phase 1 Completion Criteria

Phase 1 is done when all of the following are true:

- [ ] All 24 tasks are committed on `feature/jtf-protocol`
- [ ] `pytest` passes with zero failures (expect ~46 tests)
- [ ] `jtfprotocol/` package is importable from the repo root
- [ ] `main.py` is unchanged (integration is Phase 5)
- [ ] Live site can resume on `main` without interaction from this branch

At that point the branch is ready for merge consideration — or for Phase 2 work to proceed on the same branch.

---

## Next Phases (Roadmap)

These are documented here for orientation. Each will earn its own detailed plan before execution.

**Phase 2 — Discovery & Gossip**
- Seed domain bootstrap, peer list exchange, DNS TXT/SRV fallback
- Fact announcement push + on-demand pull
- Peer validation (rate limits, ASN diversity, uptime threshold)
- New module `jtfprotocol/gossip.py`; no `main.py` changes yet

**Phase 3 — Trust System**
- Trust score computation (corroboration, source verification, consistency, methodology compliance)
- Maturity and stability factors; availability separate from trust
- Source-centric trust, Sybil cluster detection (continuous scoring)
- Client trust aggregation (weighted median, low-N fallback)
- Circuit breaker for fabrications; verification credit sharing
- New module `jtfprotocol/trust.py`

**Phase 4 — Corrections & Resilience**
- Correction record format, trust-gated broadcast, per-target rate limits
- Key rotation (72-hour announcement + domain binding), revocation, key loss recovery
- P2P evidence storage and retrieval
- Flood protection enforcement

**Phase 5 — Integration with `main.py`**
- Adapt the existing publishing path to produce Phase 1-format facts
- Wire `jtfprotocol.well_known.generate_well_known` into the server startup
- Integrate gossip into the 30-minute update cycle
- Preserve the existing `feed.xml` / `stories.json` consumers during transition (dual-write, then cut over)
- This is the first phase that modifies `main.py` and the first that is risky to the live site — done only after Phases 1-4 are stable

**Phase 6 — Companion Documents**
- Wire Protocol Specification (HTTP endpoints, request/response, error codes, version negotiation)
- Appendix A: Prohibited Adjective Lists (English seed list expanded; amendment process)
- Appendix B: Controlled Action Vocabulary (canonical list beyond the Phase 1 seed)
- Appendix C: URL Normalization Rules
- Trust Algorithm Reference (pseudocode, worked examples, cluster detection)
- Operator deployment guide with side-by-side commercial and local paths

---

## Self-Review

- **Spec coverage:** Every Phase 1 requirement in the spec is implemented by a named task. Tasks 2-5 cover Identity. Tasks 6-9 cover the Fact format and signing. Tasks 10-16 cover Deterministic Checks. Tasks 17-21 cover Extraction Backends. Tasks 22-23 cover the Well-Known endpoint. No placeholders, no "TBD" tasks.
- **Placeholder scan:** No step says "add appropriate error handling" without showing the error handling. No step says "implement later." Every code step shows the exact code to write.
- **Type consistency:** `CheckResult`, `ComplianceResult`, `StructuredFact`, `ExtractionBackend`, `AnthropicBackend`, `OpenAICompatibleBackend`, `generate_keypair`, `sign_fact`, `verify_fact`, `public_key_id`, `canonical_json`, `compute_fact_id`, `generate_well_known`, `verify_well_known`, `get_backend` — every name used in a later task is defined in an earlier task.
