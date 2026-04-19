# jtfprotocol

Reference implementation of Phase 1 of the JTF Protocol.

Covers:

- Ed25519 identity (`identity.py`)
- Canonical fact format, signing, verification (`fact.py`)
- Deterministic methodology compliance checks (`compliance.py`)
- Shared extraction prompt template (`prompts.py`)
- Pluggable extraction backends (`extraction.py`) -- `AnthropicBackend`, `OpenAICompatibleBackend`
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
