# JTF Protocol Phase 2 — Continuation Prompt

Use this file when you're ready to start Phase 2 (Discovery & Gossip). Copy everything below the line into a fresh Claude Code session started inside `/Users/larryseyer/JTFNews`.

---

## Task

Execute **Phase 2** of the JTF Protocol: Discovery & Gossip.

## Context

JTF News is a live automated news service that publishes only verified facts. The JTF Protocol decentralizes it so that multiple independent servers can publish, cross-verify, and gossip facts without any central authority. This is the protocol's second implementation phase.

**Phase 1 is already complete and merged on branch `feature/jtf-protocol`** (if not yet merged to `main`). It delivered:

- `jtfprotocol/identity.py` — Ed25519 keypair generation, disk serialization (with consistency check and overwrite guard), sign/verify primitives, `public_key_id` fingerprint
- `jtfprotocol/fact.py` — `Fact` dataclass, `canonical_json`, `compute_fact_id`, `sign_fact`, `verify_fact`
- `jtfprotocol/compliance.py` — 5 deterministic methodology compliance checks + `check_compliance` orchestrator
- `jtfprotocol/prompts.py` — shared `build_extraction_prompt` for all backends
- `jtfprotocol/extraction.py` — `ExtractionBackend` ABC + `AnthropicBackend` + `OpenAICompatibleBackend` (covers OpenAI/Ollama/LM Studio) + `get_backend` factory
- `jtfprotocol/well_known.py` — signed `/.well-known/jtf.json` generation and verification
- 74 passing tests in `tests/`

**Phase 1 did NOT touch `main.py` or any part of the live site.** Phase 5 is the first phase that does; until then, the live site runs untouched and Phase 2 continues to build the standalone protocol package.

## Authoritative sources (read first)

1. **Spec:** `documentation/Protocol Ver 1.0 CURRENT.md` — the protocol specification. Sections most relevant to Phase 2: "Discovery", "The Well-Known Endpoint", "Gossip", "Peer Validation", "Fact Propagation", "Seed Domains", "Fallback Discovery".

2. **Plan file (has the Phase 2-6 roadmap):** `docs/superpowers/plans/2026-04-19-jtf-protocol-phase1-foundation.md` — see the "Next Phases (Roadmap)" section at the end. Phase 2's high-level scope is listed there.

3. **Project rules:** `CLAUDE.md` — the Ralph agent contract at the top, then the project spec. Key non-negotiables:
   - Always commit via `./bu.sh "message"`, never raw `git commit`
   - No emoji anywhere (code, docs, commits)
   - Two-source minimum, no editorializing (enforced at spec level)
   - Python venv at `venv/` — use `venv/bin/pytest` and `venv/bin/pip`
   - `from __future__ import annotations` is the pattern — parameterized type annotations (`list[dict]`, `dict | None`, `set[str]`) work on Python 3.9 because of this. Do NOT simplify them to unparameterized forms.

4. **Auto-memory:** The user has persistent memory at `/Users/larryseyer/.claude/projects/-Users-larryseyer-JTFNews/memory/` including a feedback memory about preferring autonomy over permission questions. Check `MEMORY.md` at session start.

## Phase 2 scope (from the roadmap)

New module `jtfprotocol/gossip.py` delivering:

- **Well-known bootstrap:** fetch and verify `/.well-known/jtf.json` from a peer
- **Seed domain configuration:** hard-coded seed domains in a config module, with DNS TXT/SRV fallback for discovery
- **Peer list exchange:** merge received peer lists into local state
- **Peer validation:** rate limits (10 new peers per gossip cycle), ASN diversity (max 30% same ASN), minimum uptime (48 hours) before propagation, multi-source confirmation (`confirmed_by` counter)
- **Maximum peer list size** (100 active peers), trust-weighted eviction
- **Fact announcement push:** send lightweight announcement (`fact_id`, `occurred_at`, `channel`, `server_domain`, `server_key_id`, `signature`) to known peers on publish
- **Fact pull:** fetch full fact body from announcing server's feeds when announcement is seen for the first time
- **Gossip cadence:** 30-minute refresh cycle aligned with the JTF update cadence
- **Drop dead peers:** 7 days without response → drop from peer list

**Phase 2 continues to NOT touch `main.py`.** Integration is Phase 5.

## How to proceed

1. **Verify state:**
   ```bash
   git rev-parse --abbrev-ref HEAD    # should be main OR feature/jtf-protocol
   git log --oneline -5
   venv/bin/pytest -v                  # should show 74 passing
   ```

2. **Branching decision:**
   - If `feature/jtf-protocol` is still active (not merged): continue Phase 2 on it.
   - If `feature/jtf-protocol` is already merged to `main`: create `feature/jtf-protocol-phase2` from `main` and work there.
   - Either way: never work directly on `main` for Phase 2. Use `./bu.sh` — it is branch-aware.

3. **Invoke the `superpowers:writing-plans` skill** to produce a detailed implementation plan for Phase 2. The plan should:
   - Live at `docs/superpowers/plans/YYYY-MM-DD-jtf-protocol-phase2-discovery-gossip.md`
   - Decompose Phase 2 into TDD-driven tasks (one commit per task via `./bu.sh`)
   - Reference the relevant sections of the Protocol spec per task
   - Reuse the Phase 1 primitives where appropriate (canonical_json, sign/verify, well_known.verify_well_known, etc.)
   - Keep `jtfprotocol/gossip.py` as the primary new file; add `jtfprotocol/seeds.py` only if the seed-domain list is substantial enough to warrant its own file

4. **Show the plan to the user for approval** before execution. They may redirect scope (e.g., "do just peer-list exchange tonight, defer fact propagation").

5. **Execute via `superpowers:subagent-driven-development`** (recommended; what Phase 1 used) or `superpowers:executing-plans` — user's call. Phase 1 used subagent-driven and it worked well.

6. **After Phase 2 is complete**, write a similar continuation prompt at `docs/superpowers/specs/YYYY-MM-DD-jtf-protocol-phase3-continuation-prompt.md` so the next session has the same handoff quality.

## Constraints (repeat for emphasis)

- **Live site safety:** If the live site is running on `main`, Phase 2 work stays on the feature branch. Do not merge to main until the user explicitly asks.
- **Commit discipline:** Via `./bu.sh` only. One task = one commit with `PHASE2-NN:` prefix.
- **TDD:** Write the failing test first, run it to see it fail, write the minimum code, run to see it pass, commit. Not optional.
- **No emoji anywhere.**
- **Spec is authoritative.** If Phase 2 work would conflict with the spec, STOP and ask. Do not silently change the spec.
- **Model autonomy:** The user runs multiple parallel Claude Code sessions. Minimize permission questions. Decide and proceed when the plan or spec gives direction. Only escalate for genuine architectural ambiguity or destructive actions.

## User facts worth knowing

- User's auto-memory at `/Users/larryseyer/.claude/projects/-Users-larryseyer-JTFNews/memory/MEMORY.md` — read at session start.
- Today's date: check `date` command.
- The user may be busy in other sessions — batch updates at milestones rather than per-task.

## One-line recap

Phase 1 is done on `feature/jtf-protocol` (74 tests passing, untouched live site). Phase 2 is Discovery & Gossip. Invoke `superpowers:writing-plans`, produce a plan, get approval, execute via subagent-driven development, then write the Phase 3 handoff.
