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

## Deterministic compliance checks: what Phase 1 includes

Phase 1 implements 5 of the 11 deterministic checks listed in the spec
(Protocol Ver 1.0, "Deterministic Checks"):

**Implemented:**
- Two-source minimum
- Unrelated-sources (no common majority shareholder)
- Source-evidence presence (content_hash, supporting_quote, context_window, snapshot_url for full nodes)
- Supporting quote in content (scaffold -- real content fetching is Phase 3)
- Claim-type required fields (vote/election/financial/legal/death/injury)

**Deferred to later phases:**
- Prohibited adjective list (seed list only; full list is Appendix A, Phase 6)
- Official-titles enforcement
- Speculative-language detection
- Numeric specificity
- Context window non-negation (Phase 3 -- needs NLP)
- Stale ownership data flagging (Phase 3 -- needs clock integration)
- Source lineage disclosure (Phase 3)
- No-self-citation (Phase 2 -- needs peer graph)

## Included as of Phase 2

- Seed domain list and DNS TXT/SRV fallback discovery (`seeds.py`)
- HTTP `Fetcher` protocol and `RequestsFetcher` default (`gossip.py`)
- `fetch_and_verify_well_known` (`gossip.py`)
- `PeerRecord`, `PeerStore` with JSON persistence, trust-weighted
  eviction, new-peer rate limit, ASN diversity gate, 48-hour uptime
  gate for publication, seven-day dead-peer drop (`gossip.py`)
- `exchange_peer_lists`, `fetch_fact_by_id`, `run_gossip_cycle`
  (`gossip.py`)
- `build_announcement`, `verify_announcement`, `send_announcement`
  (`announcements.py`)

## Not included as of Phase 2

- Trust score computation and cluster detection (Phase 3)
- Corrections, key rotation, revocation, key loss recovery (Phase 4)
- Integration with `main.py` (Phase 5)
- Wire-protocol appendix, trust algorithm reference (Phase 6)
