# JTF Protocol — Implementation Planning Prompt

Use this prompt to start a new Claude Code session that picks up where the design brainstorm left off. Copy everything below the line into the new session.

---

## Context

We have completed the design phase for the JTF Protocol — a peer-to-peer network specification that decentralizes JTF News so that no single operator, server, or point of failure can kill the factual record.

The canonical protocol specification is at:
```
documentation/Protocol Ver 1.0 CURRENT.md
```

**Read that file first.** It is the canonical specification — lives alongside `documentation/WhitePaper Ver 1.4 CURRENT.md` and is referenced from the WhitePaper's "Protocol" section. Everything below summarizes it, but the spec is the source of truth.

The original design artifact (byte-identical at the time of promotion) is preserved at `docs/superpowers/specs/2026-04-18-jtf-protocol-design.md` for historical reference.

## What the JTF Protocol Is

JTF News (Just the Facts News) is a live, running automated news service that publishes only verified facts — no opinions, no adjectives, no interpretation. It currently runs as a single Python script (`main.py`, ~6500 lines) on one machine, publishing to GitHub Pages via the GitHub API. The iOS app and all other consumers pull static files (feed.xml, stories.json, podcast.xml, etc.) from `jtfnews.org`.

The JTF Protocol decentralizes this so that:

1. **Multiple independent servers** can run the JTF methodology, each publishing verified facts
2. **The iOS app (and any client)** can consume facts from multiple servers and cross-reference them
3. **Trust is algorithmic** — no human approves servers, no human curates content, no human is a dependency
4. **The system outlives its creator** — if every original operator disappears, the protocol continues
5. **Anyone can build a client** — the protocol is the product, not any particular app

## Architecture Summary

- **Peer-to-peer network** — no master, no hierarchy, no center
- **Ed25519 cryptographic identity** — each server generates its own key pair, signs every fact
- **Gossip-based discovery** — servers find each other by exchanging peer lists, seeded from well-known domains
- **Two node types** — Full nodes (AI verification, trust computation) and Light nodes (signature verification, relay)
- **Structured extraction for corroboration** — facts carry `{subjects, action, objects, quantities, location, time}` using controlled vocabulary + Wikidata QIDs; comparison is deterministic
- **Source evidence baked into facts** — content hash, supporting quote, context window (before/after text), snapshot URL, source lineage (`derived_from`)
- **Algorithmic trust scoring** — four components (corroboration 0.40, source verification 0.35, consistency 0.15, methodology compliance 0.10) multiplied by maturity factor and behavioral stability factor
- **Trust separated from availability** — dormant servers keep trust, availability recovers on return
- **Circuit breaker** — proven fabrication (quote not in content hash) drops trust to 0.10 first offense, permanent blacklist second
- **Source diversity weighting** — same-source corroboration = 0.5x, different-source = 1.0x
- **Model diversity bonus** — corroboration from different AI model families = 1.25x credit
- **Source-centric trust** — scores sources across the network, not just servers
- **Bootstrap mirroring detection** — temporal independence weighting prevents feed-copying from earning corroboration
- **72-hour key rotation announcement + domain binding** — prevents identity takeover
- **Key loss recovery** — peer quorum (5+ high-trust nodes + domain proof) shortens 180-day penalty to 90
- **Trust-weighted corrections** — 0.50 effective trust threshold for broadcast, per-target limits, independent verification required
- **Peer diversity constraint** — max 30% same ASN, diversity across geography and domain age
- **P2P evidence storage** — decentralized proof archive served via gossip
- **Verification credit sharing** — full nodes share signed spot-check results for 48-hour reuse
- **Client trust aggregation** — weighted median of peer assessments, low-N fallback to unweighted median
- **Continuous Sybil cluster detection** — standard-deviation-based, no hard thresholds
- **Flood protection** — 100 facts/day, 10/30min burst, 5 corrections/day, 3 per target per 30 days
- **NTP required** — clock-ahead rejection at 5 minutes, peer-observed days_active
- **Graceful aging** — 48-hour verification protection window for source URLs

## What the White Paper Says

The white paper is at `documentation/WhitePaper Ver 1.4 CURRENT.md`. Key principles the protocol must honor:

- Two unrelated sources minimum (different majority owners)
- No editorializing — no adjectives, no opinions, no speculation
- Source ownership disclosed with every story
- Corrections named, never buried or deleted
- No ads, no tracking, donations only
- CC-BY-SA licensing
- "The methodology belongs to no one. It serves everyone."
- Community channels (local news, sports, school boards) each follow the methodology

## Current Codebase State

- `main.py` (~6500 lines) — the running JTF News server, handles scraping, AI fact extraction, verification, TTS, publishing to GitHub Pages, daily digest, YouTube upload, podcast, corrections, archive
- `docs/` — GitHub Pages public site (feed.xml, stories.json, podcast.xml, corrections.json, monitor.json, archive/, etc.)
- `web/` — OBS browser source overlays
- Single branch: `main`
- Commits via `./bu.sh "message"` only (handles staging, committing, pushing, and backup)
- Runtime files (feed.xml, stories.json, etc.) are pushed by `main.py` via GitHub API, not by git

## Review Process

The protocol spec went through **eight independent AI reviews across two rounds**. All reviewers converged on the architecture being sound and ready for implementation. The spec incorporates feedback on:

- Source URL rot (solved by content hashes + snapshots + P2P evidence storage)
- Semantic similarity exploitability (solved by structured extraction with controlled vocabulary)
- AI centralization (solved by model disclosure + model diversity bonus + deterministic rule-based checks)
- State actor threats (solved by circuit breaker + behavioral stability + source diversity + honest threat model)
- Bootstrap fragility (solved by multiple seeds + DNS fallback + last-known-good peer lists)
- Key compromise/takeover (solved by 72-hour announcement window + domain binding + key loss recovery)
- Correction weaponization (solved by trust threshold + per-target limits + independent verification)
- Trust decay punishing quality (solved by separating trust from availability)
- Mirroring disguised as corroboration (solved by temporal independence + source diversity weighting)

## Your Task

**Invoke the `superpowers:writing-plans` skill** to create a detailed implementation plan for the JTF Protocol.

The implementation will need to cover:

### Phase 1: Protocol Foundation
- Well-known endpoint (`/.well-known/jtf.json`) generation and serving
- Ed25519 key pair generation and management
- Fact signing and signature verification
- Canonical fact format with all required fields (structured extraction, source evidence, context windows, content hashes)
- Deterministic rule-based methodology compliance checks

### Phase 2: Discovery & Gossip
- Seed domain bootstrap
- Peer list exchange and merging
- Peer validation (rate limits, diversity constraints, uptime requirements)
- DNS fallback discovery (TXT/SRV records)
- Fact announcement push + on-demand pull

### Phase 3: Trust System
- Trust score computation (four components + maturity + stability)
- Availability tracking (separate from trust)
- Source verification (content hash checking, spot-check sampling, verification credit sharing)
- Structured corroboration (fact equivalence, source diversity weighting, model diversity bonus, bootstrap mirroring detection)
- Behavioral stability monitoring
- Source-centric trust scoring
- Sybil cluster detection (continuous scoring)
- Client trust aggregation algorithm
- Circuit breaker for fabrications

### Phase 4: Corrections & Resilience
- Correction publishing, propagation, and verification
- Trust-weighted correction acceptance
- Correction abuse prevention (rate limits, per-target limits)
- Correction-of-correction and retraction semantics
- Reverse pointers for archived facts
- Key rotation (72-hour announcement + domain binding)
- Key revocation and key loss recovery
- P2P evidence storage and retrieval
- Flood protection enforcement

### Phase 5: Integration with Existing System
- Adapt `main.py` to publish facts in the new canonical format
- Generate and serve the well-known endpoint
- Integrate gossip into the existing 30-minute update cycle
- Maintain backward compatibility with existing feed.xml/stories.json consumers during transition
- Ensure the iOS app can consume both legacy and protocol-format data

### Phase 6: Companion Documents
- Wire protocol specification (HTTP endpoints, methods, error handling)
- Appendix A: Prohibited adjective list (English, with amendment process)
- Appendix B: Controlled action vocabulary
- Appendix C: URL normalization rules
- Trust algorithm reference with pseudocode and worked examples

### Important Constraints
- **Do not break the running system.** JTF News is live 24/7. Changes must be incremental and backward-compatible.
- **Always use `./bu.sh "message"` for commits.** Never raw `git commit`.
- **No emoji** in code, docs, or commits.
- **Read CLAUDE.md** for full project rules and constraints.
- **The protocol spec is the approved design.** Do not redesign during implementation. If something in the spec is unclear or seems wrong, flag it — do not silently change it.

## Deliverable

A phased implementation plan with clear stories, acceptance criteria, and file-level scope for each phase. The plan should identify which changes can be made to `main.py` incrementally vs. which require new files/modules.
