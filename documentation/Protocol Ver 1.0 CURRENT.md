# The JTF Protocol

## An Open Network for Verified Facts

*"The methodology belongs to no one. Now neither does the infrastructure."*

------------------------------------------------------------------------

## Purpose

JTF News began as one server, one operator, one machine. The methodology was always designed to travel. The infrastructure was not.

This protocol changes that.

The JTF Protocol defines how independent servers discover each other, share verified facts, and build trust without any central authority, without any human gatekeeper, and without any single point of failure.

If one server goes dark, the network continues. If the original operator disappears, the facts remain. The protocol outlives its creators. That is its only purpose.

------------------------------------------------------------------------

## Design Principles

Every technical decision in this protocol traces to the white paper. Where the methodology leads, the infrastructure follows.

| Principle | Source | Protocol Consequence |
|---|---|---|
| The methodology belongs to no one | White paper, opening | No server is special. All peers are equal. No anchor nodes. No hierarchy. |
| Two unrelated sources minimum | Verification Standard | Facts carry their proof: source URLs, content snapshots, context windows, and ownership data travel with every fact. |
| No algorithm is perfect. Ours is visible. | AI Transparency | The trust algorithm is published in this specification. AI models are disclosed per fact. Anyone can audit both. |
| We do not bury mistakes. We name them. | Corrections | Corrections propagate across the network. Original facts are marked, never deleted. |
| Stale data is dishonest data | Ownership Maintenance | Dead servers lose availability. Trust scores decline with verified failures. Source snapshots prevent stale verification. |
| If a community needs facts, the methodology is theirs | Community Channels | Any server can serve any community. The protocol supports global, local, and topical channels. |
| No ads. No tracking. Donations only. | Funding | The protocol has no monetization layer. Servers bear their own costs. Recognition is their reward. |
| CC-BY-SA | Licensing | This specification is CC-BY-SA. Anyone can implement it. Anyone can improve it. |

------------------------------------------------------------------------

## How It Works

The JTF Protocol is a peer-to-peer network of independent servers, each running its own implementation of the JTF methodology. There is no master. There is no hierarchy. There is no center.

Each server:

1. Generates its own cryptographic identity
2. Publishes verified facts, signed with its private key, with source evidence baked in
3. Discovers other servers through gossip
4. Builds trust through observed behavior over time
5. Verifies other servers' facts by checking their cited sources against captured evidence

The network supports two node types:

- **Full nodes** perform source verification, compute trust scores, and participate in cross-corroboration. They require access to an AI model — either a commercial API (Anthropic, OpenAI, others) or a locally-hosted model (Ollama, LM Studio, llama.cpp, or equivalent). Both paths are first-class. The protocol records which is in use and treats them symmetrically for trust. Operators choose the path that fits their budget, hardware, and data-sovereignty requirements.
- **Light nodes** verify cryptographic signatures, relay facts and trust scores, serve clients, and perform deterministic rule-based checks (supporting quote present in content hash, adjective list, source count). They do not perform AI-assisted source verification. They contribute to network resilience and distribution without requiring large compute budgets.

A Raspberry Pi can run a light node. A cloud server with API keys can run a full node. Both are valid participants. The protocol does not privilege one over the other. Peers detect claimed-full-but-not-verifying behavior as a methodology compliance penalty.

Clients connect to one or more servers, aggregate facts, and use the protocol's trust aggregation algorithm to assess reliability. The JTF News iOS app is one client. A web browser reading an RSS feed is another. Anyone can build a client. The protocol serves them all equally.

------------------------------------------------------------------------

## Identity

### Key Pairs

Each server generates an Ed25519 key pair on first startup.

- The **private key** stays on the server. It is never transmitted. It is never shared.
- The **public key** is published openly. It identifies the server to the network.

There is no certificate authority. No server signs another server's key. No server approves another server's existence. Identity is self-asserted. Trust is earned through behavior, not granted by authority.

### Signing

Every fact published by a server is signed with its private key. The signature covers the canonical fact content: the text, the sources, the source evidence, the structured extraction, the timestamps, the ownership data. Anyone with the public key can verify three things:

- This fact came from the claimed server.
- The fact has not been altered since publication.
- The server cannot deny publishing it.

### Key Rotation

Keys can be rotated. The process requires two safeguards to prevent identity takeover:

**Announcement window:** A key rotation is announced seventy-two hours before it takes effect. The announcement is signed by the old key and contains the new public key. During the window, the old key can cancel the rotation by publishing a signed cancellation. This gives the legitimate operator time to react if an attacker who has stolen the old key attempts to rotate to a key they control.

**Domain binding:** The new key must appear at the server's `/.well-known/jtf.json` endpoint before peers accept the rotation. Possession of the private key alone is not sufficient to take over an identity. The attacker also needs control of the domain and server. This separates "stole a key file" from "took over the entire server."

A key rotation that completes both safeguards preserves the server's trust history. The maturity ramp continues from where it was.

### Key Revocation

When a private key is compromised, the server publishes a **revocation record** through gossip:

```json
{
  "type": "key_revocation",
  "revoked_key_id": "sha256:a1b2c3...",
  "revoked_after": "2026-04-18T12:00:00Z",
  "new_key": "base64-encoded-new-public-key",
  "new_key_id": "sha256:d4e5f6...",
  "reason": "key_compromise",
  "announcement_expires": "2026-04-21T12:00:00Z",
  "signatures": {
    "by_revoked_key": "...",
    "by_new_key": "..."
  }
}
```

If the old key is still available, the revocation is signed by both old and new keys and follows the seventy-two-hour announcement window. During the window, the old key can cancel.

If the old key is lost entirely, the server restarts its trust history from zero with the extended maturity ramp of one hundred eighty days.

Peers that accept a revocation record reject any facts signed by the revoked key after the `revoked_after` timestamp. Facts signed before that timestamp remain valid.

### Key Loss Recovery

Losing a private key without compromise (hardware failure, accidental deletion) imposes the full one-hundred-eighty-day maturity ramp. This is harsh for honest operators. The protocol provides one recovery path:

A **key loss recovery** allows an operator who can prove domain ownership to recover with a shortened ramp:

1. The operator generates a new key and publishes it at their `/.well-known/jtf.json` endpoint.
2. The operator proves domain control via a DNS TXT challenge or a signed `.well-known/jtf-recovery.json` file served over TLS.
3. Five or more independent servers with trust scores above 0.70 co-sign a recovery endorsement within forty-eight hours.
4. If the endorsement reaches quorum, the new key receives a ninety-day maturity ramp instead of one hundred eighty.

This introduces a minimal social layer without central authority. The quorum is decentralized, temporary, and voluntary. No single server can grant or deny recovery.

### Identity Continuity

A new key with signed lineage from the old key (via completed rotation) inherits the server's trust history. The standard maturity ramp applies: ninety days to full maturity.

A new key **without** signed lineage begins at zero trust with the extended one-hundred-eighty-day maturity ramp, unless key loss recovery shortens it to ninety. This prevents trust laundering: a bad actor cannot burn a low-trust identity and restart at the normal pace. The cost of a fresh identity is time.

### Algorithm Agility

The protocol currently specifies Ed25519 for signing. Future versions may support additional algorithms.

- Every signature includes an `algorithm` field declaring the signing algorithm used.
- Version 1 requires support for Ed25519. Additional algorithms may be added in minor versions.
- When a new algorithm is introduced, servers must support both old and new for the duration of the deprecation period.

Hard-coded cryptography is a future migration problem. This field prevents it.

------------------------------------------------------------------------

## The Fact

A fact is the atomic unit of the JTF Protocol. It is a single verified claim about a real-world event, structured for machine processing and human reading.

### Canonical Format

```json
{
  "jtf_version": 1,
  "id": "sha256:e3b0c44298fc1c149afbf4c8996fb924...",
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
    "event_time": {
      "start": "2026-04-18T14:00:00Z",
      "end": "2026-04-18T15:00:00Z"
    },
    "claim_type": "vote",
    "required_fields_met": true
  },
  "sources": [
    {
      "name": "Reuters",
      "url": "https://reuters.com/world/example",
      "content_hash": "sha256:7d793037a076...",
      "snapshot_url": "https://web.archive.org/web/20260418150000*/https://reuters.com/world/example",
      "supporting_quote": "The General Assembly approved Somaliland's membership application by a vote of 143 in favor to 9 against.",
      "context_window": {
        "before": "After three hours of debate on Friday afternoon,",
        "after": "with 12 abstentions. The vote followed months of diplomatic negotiations.",
        "context_hash": "sha256:8a3c91..."
      },
      "fetched_at": "2026-04-18T15:00:12Z",
      "derived_from": null,
      "ownership": [
        {"entity": "Thomson Reuters Corporation", "percentage": 100.0}
      ],
      "scores": {
        "accuracy": 9.6,
        "bias": 9.2,
        "speed": 9.0,
        "consensus": 9.1
      }
    },
    {
      "name": "Associated Press",
      "url": "https://apnews.com/article/example",
      "content_hash": "sha256:9f86d081884c...",
      "snapshot_url": "https://web.archive.org/web/20260418150200*/https://apnews.com/article/example",
      "supporting_quote": "In a 143-9 vote, the U.N. General Assembly voted Friday to admit Somaliland.",
      "context_window": {
        "before": "NEW YORK (AP) --",
        "after": "The decision caps a years-long campaign by the Horn of Africa nation.",
        "context_hash": "sha256:2b4f7e..."
      },
      "fetched_at": "2026-04-18T15:01:05Z",
      "derived_from": null,
      "ownership": [
        {"entity": "Associated Press (nonprofit cooperative)", "percentage": 100.0}
      ],
      "scores": {
        "accuracy": 9.5,
        "bias": 9.3,
        "speed": 8.8,
        "consensus": 9.0
      }
    }
  ],
  "primary_source": {
    "url": "https://press.un.org/en/2026/ga12345.doc.htm",
    "description": "UN General Assembly official press release"
  },
  "channel": "global",
  "server": {
    "domain": "jtfnews.org",
    "public_key_id": "sha256:a1b2c3..."
  },
  "algorithm": "Ed25519",
  "signature": "base64-encoded-Ed25519-signature"
}
```

### Fact Rules

These are the methodology, expressed as data constraints:

- **Two sources minimum.** A fact with fewer than two sources is invalid. The protocol rejects it.
- **Unrelated sources.** No common majority shareholder between any two cited sources. The ownership data is in the fact. Anyone can verify independence.
- **No self-citation.** A server may not use its own previously published facts as one of the two required unrelated sources. Facts are verified from external sources, not from the network itself.
- **Source evidence required.** Every source must include a `content_hash` of the page content at fetch time, a `supporting_quote` extracted from the source, and a `context_window` (the text immediately before and after the quote). The `snapshot_url` is required for full-node publication. Light nodes relaying facts from full nodes are exempt from the snapshot requirement.
- **Context integrity.** The `context_window` must not negate the supporting quote. If the surrounding text contradicts or qualifies the quoted claim (e.g., "officials denied that..." preceding the quoted figure), the fact fails verification. This is checkable without AI: the context window is part of the signed evidence.
- **Source lineage.** When a source is derived from an upstream wire report, press release, or primary document, the `derived_from` field must contain the upstream URL. Two sources that share a common `derived_from` URL receive reduced independence credit (see Trust section).
- **Primary source encouraged.** When media outlets cite the same original record (a court filing, a UN transcript, a government press release), the fact should include a `primary_source` field linking to that original. Two outlets reprinting the same wire report is weaker evidence than two outlets plus the original record.
- **Official titles.** People are addressed by their official title and surname. Titles are facts. Omitting them is editorial. Media-invented nicknames are editorialization, not titles.
- **Claim-type required fields.** Certain claim types require additional data to prevent misleading omission:

| Claim type | Required fields |
|---|---|
| death, injury | timeframe, source attribution |
| financial | currency, time basis |
| legal | jurisdiction |
| vote, election | vote tally or voter count |

A fact that omits required fields for its claim type fails deterministic methodology compliance. This makes omission a mechanical failure, not an AI judgment call.

- **Immutable once signed.** A published, signed fact cannot be altered. Corrections are separate records that reference the original. We do not rewrite history. We annotate it.

### Editorialization Constraints

The JTF methodology requires the removal of editorialization from fact text. The protocol enforces this through two layers:

**Deterministic rule-based checks** (automated, reproducible, no AI required):

- No words from the prohibited subjective-adjective list (see Appendix A; maintained per-channel and per-language)
- Numeric specificity required where quantities are available
- Named entities must use official titles
- No speculative language ("might," "could," "is expected to," "sources say")
- Two sources minimum with disclosed ownership
- Claim-type required fields present
- Content hash, supporting quote, and context window present for all sources

**AI-assisted checks** (used for deeper analysis, model disclosed per fact):

- Framing bias detection (neutral presentation of information)
- Omission analysis (significant facts from sources not excluded without reason)

The deterministic checks are the hard gate. A fact that fails them is non-compliant regardless of AI assessment. The AI-assisted checks are advisory signals that feed into the methodology compliance score.

The protocol does not claim that automated analysis can detect all forms of bias or editorial framing. It claims that rule-based constraints minimize editorialization, and AI-assisted analysis provides an additional, transparent, imperfect layer. The distinction matters. No algorithm is perfect. Ours is visible.

### Fact Identity

A fact's `id` is a SHA-256 hash of the canonical content: the fact text, source URLs, and `occurred_at` timestamp. The full 256-bit hash is used, making collision attacks computationally infeasible.

Two servers independently verifying the same event will produce facts with different IDs because their AI rewrites will differ in wording. The protocol does not rely on ID matching for corroboration. It uses structured extraction matching, described in the Trust section.

### Structured Extraction

Each fact includes a `structured_extraction` object containing machine-comparable fields extracted from the fact text. The extraction step is AI-assisted and will vary across models. The comparison step is deterministic.

To minimize cross-model divergence:

- **Action verbs** use a controlled vocabulary defined in Appendix B: `voted`, `approved`, `adopted`, `announced`, `signed`, `arrested`, `charged`, `acquired`, `merged`, `launched`, `deployed`, `struck`, `collapsed`, `resigned`, `appointed`, and others. The vocabulary is versioned and extensible.
- **Subject entities** use Wikidata QIDs where available (e.g., `Q47010` for the UN General Assembly). The free-text `subjects_text` field is retained for human readability. Equivalence checks use QIDs when present, falling back to normalized string comparison.
- **Quantities** are numeric values with a required `context` string. Quantity comparison is exact by default; a tolerance applies only when the sources themselves report different figures, in which case both are preserved and the disagreement is noted.

The structured extraction is not perfectly deterministic. Different AI models will sometimes produce different action verbs or miss entities. The protocol is honest about this: structured extraction is more deterministic than semantic similarity, not perfectly deterministic. The controlled vocabulary and Wikidata QIDs reduce divergence. They do not eliminate it.

### Fact Equivalence

Two facts from different servers describe the same real-world event when:

1. **At least one subject matches** (by Wikidata QID or normalized entity name)
2. **The action verb matches** (from the controlled vocabulary)
3. **Quantities agree** (exact match on core numbers, or both report the same disagreement between sources)
4. **Event time windows overlap**
5. **At least one source URL matches** (after normalization), OR conditions 1 through 4 all hold independently

Source URL overlap is the strongest signal. When two servers cite the same source URL, they are verifiably reporting on the same event. When they cite different sources but their structured extractions match on subject, action, quantities, and time, they have independently corroborated the same event from different evidence. Both count. The second is stronger.

**URL normalization:** Source URLs are canonicalized before comparison: strip tracking parameters (`utm_*`, `ref`, `fbclid`), unify `www` and non-`www`, canonicalize percent-encoding, remove fragments. The normalization rules are defined in Appendix C.

### Verification Method Identifiers

The `verification_method.model` field uses the format `vendor:model:version` (e.g., `anthropic:claude-haiku:4-5-20251001`, `openai:gpt-4o:2026-04-01`, `meta:llama:3.2-70b`). Consistent formatting enables cross-server model-diversity analysis.

------------------------------------------------------------------------

## Discovery

### The Well-Known Endpoint

Every JTF server publishes a machine-readable identity file at:

```
https://{domain}/.well-known/jtf.json
```

This file is signed by the server's private key.

```json
{
  "jtf_protocol_version": 1,
  "server": {
    "domain": "example.com",
    "public_key": "base64-encoded-Ed25519-public-key",
    "public_key_id": "sha256:a1b2c3...",
    "algorithm": "Ed25519",
    "channel": "global",
    "name": "JTF News Frankfurt",
    "started_at": "2026-06-01T00:00:00Z",
    "node_type": "full",
    "asn": 24940,
    "location_country": "DE"
  },
  "extraction": {
    "backend": "ollama",
    "model": "qwen:2.5-72b-instruct-q5_K_M",
    "prompt_version": "jtf-extract-v3"
  },
  "feeds": {
    "facts_rss": "/feed.xml",
    "facts_json": "/stories.json",
    "corrections": "/corrections.json",
    "archive": "/archive/index.json",
    "announcements": "/announcements"
  },
  "peers": [
    {
      "domain": "jtfnews.org",
      "public_key_id": "sha256:d4e5f6...",
      "channel": "global",
      "last_seen": "2026-04-18T12:00:00Z",
      "trust_score": 0.94,
      "confirmed_by": 3
    }
  ],
  "signature": "base64-encoded-signature-of-this-document"
}
```

This endpoint requires no authentication. It is public. It is the protocol's handshake. Servers should serve it behind a cache with a short TTL (five minutes) to resist denial-of-service attacks on the handshake itself. Peers should tolerate stale well-known data up to twenty-four hours.

### Gossip

Servers discover each other through gossip. No directory. No registry. No gatekeeper.

1. On first startup, a server contacts one or more **seed domains** from this specification or from DNS discovery.
2. It fetches their `/.well-known/jtf.json` and learns their peer lists.
3. It contacts those peers, fetches their peer lists, and merges them with its own.
4. Every thirty minutes, aligned with the JTF update cadence, it refreshes known peers.
5. New servers propagate through the network within hours.
6. Servers that have not responded in seven days are dropped from peer lists.

No human approves a new server. No human removes a dead one. The protocol handles both.

### Peer Validation

Not every claimed peer should be trusted at face value. When merging peer lists received from other servers:

- **Maximum peer list size:** Each server maintains at most one hundred active peers. When the limit is reached, new peers replace the lowest-trust existing peers. Random selection from qualified candidates prevents geographic or infrastructure clustering.
- **Peer diversity:** When selecting peers, servers enforce diversity across autonomous system numbers (ASN), geographic regions, and domain age. No more than thirty percent of a server's peers should share the same ASN. This prevents a patient attacker from dominating a server's peer graph through infrastructure concentration.
- **New peer rate limit:** A server accepts at most ten new peers per gossip cycle.
- **Minimum uptime for propagation:** A peer must have been observed responding for at least forty-eight hours before a server includes it in peer lists shared with others.
- **Multi-source confirmation:** A peer that appears in the peer lists of three or more independent servers has stronger standing than one reported by a single source. The `confirmed_by` field tracks this count.

### Fact Propagation

When a server publishes a new fact, it pushes a **lightweight announcement** to its known peers:

```json
{
  "type": "fact_announcement",
  "fact_id": "sha256:e3b0c44...",
  "occurred_at": "2026-04-18T14:30:00Z",
  "channel": "global",
  "server_domain": "jtfnews.org",
  "server_key_id": "sha256:a1b2c3...",
  "signature": "..."
}
```

Peers that have not already seen this fact ID fetch the full fact from the announcing server's JSON feed. Peers that already have it ignore the announcement.

Corrections are announced with higher priority. When a server publishes a correction record, it pushes the announcement immediately rather than waiting for the next cycle.

### Seed Domains

The following domains serve as initial entry points to the JTF Network. They hold no special authority after first contact. They are simply the first known addresses.

```
jtfnews.org
```

**The protocol requires a minimum of three seed domains in different jurisdictions, operated by different individuals, before the network is considered production-ready.** Additional seed domains will be added to this specification as independent operators establish stable servers. This section will be updated accordingly.

Any server can serve as a seed for any other server. Once a server has exchanged peer lists with two others, it no longer needs seeds. The seed list is a lifeboat, not a chain of command.

### Fallback Discovery

If all known seeds are unreachable, servers can discover peers through DNS:

- **DNS TXT record:** A domain participating in the JTF Network may publish a TXT record at `_jtf.{domain}` containing the URL of its well-known endpoint.
- **DNS SRV record:** A domain may publish an SRV record at `_jtf._tcp.{domain}` pointing to its server's host and port.

Reference implementations should ship with a **last-known-good peer list**: a snapshot of high-trust peers at the time of the software release. This list is not authoritative. It is a lifeboat.

------------------------------------------------------------------------

## Trust

### The Principle

Trust is earned by behavior. It is never granted by authority. It is never permanent. It is never binary.

Every server in the network has a **trust score** and an **availability score**: two numbers between 0.0 and 1.0, computed from observable, verifiable metrics. The trust score reflects the quality and integrity of a server's output. The availability score reflects how recently and consistently it has been active.

```
effective_trust = trust_score x availability
```

A dormant but historically reliable server is not untrustworthy. It is unavailable. The distinction matters: a volunteer-run server covering a small community that goes offline for two weeks should not return to near-zero trust. It should return to full trust with reduced availability, which recovers as soon as it resumes publishing.

The algorithm is published here. It is not hidden. It is not proprietary. No algorithm is perfect. Ours is visible.

### The Components

A server's trust score is computed from four components:

**Corroboration Rate (weight: 0.40)** -- What fraction of this server's facts are independently corroborated by at least one other server in the network?

Corroboration is determined by the Fact Equivalence rules. A new server can build initial corroboration credit by confirming facts already published by established servers. If a new server independently arrives at the same facts from the same sources, that demonstrates methodology compliance before the network has had time to spot-check it.

**Bootstrap mirroring detection:** Corroboration credit is weighted by temporal independence. A fact published within fifteen minutes of the same fact on another server receives 0.25x corroboration credit. A fact published one to six hours later receives 0.75x. A fact published independently (no matching prior publication within six hours) receives full 1.0x credit. This distinguishes independent verification from feed mirroring.

**Source diversity weighting:** Corroboration from a server that cites the same source URLs as the original server receives 0.5x credit. Corroboration from a server that cites *different* source URLs receives full 1.0x credit. This pushes the network toward independent verification, not repetition.

**Source lineage weighting:** When two sources in a fact share a common `derived_from` URL (both cite the same wire report or press release), they receive 0.6x independence credit instead of full credit. Two outlets reprinting the same AP dispatch is weaker evidence than two outlets with independent reporting.

**Model diversity bonus:** Corroboration from a server using a different AI model family (as reported in `verification_method.model`) receives 1.25x credit. This incentivizes model diversity across the network without mandating it. If ninety percent of servers use the same model and that model has a systematic blind spot, the network is corroborating the model's bias, not reality. Model diversity is a defense.

**Source Verification Rate (weight: 0.35)** -- When source evidence is checked, what fraction supports the claimed fact?

Every fact carries a content hash, supporting quote, and context window. Verification checks:

1. Does the supporting quote appear in the content matching the content hash?
2. Does the context window contradict or negate the supporting quote?
3. Does the snapshot URL (when fetched) contain the claimed content?

Source verification uses temporal weighting:

```
source_verification = (
    recent_30_days_rate x 0.60 +
    older_rate x 0.40
)
```

**Circuit breaker:** A proven fabrication, defined as a supporting quote that does not appear anywhere in the content matching its own content hash, triggers an immediate trust penalty. First proven fabrication: trust drops to 0.10, with a ninety-day recovery ramp. Second proven fabrication from the same server: trust drops to 0.0 and the key is blacklisted. This is not a gradual decline. Fabrication is not a mistake. It is a disqualifying event.

**Consistency (weight: 0.15)** -- Does the server publish regularly and predictably?

A server that publishes facts every thirty minutes for six months is dependable. A server that publishes fifty facts in one day and then goes silent for a week is unreliable, even if its facts were accurate during the burst.

**Methodology Compliance (weight: 0.10)** -- Do the server's facts pass the deterministic rule-based checks?

Two sources minimum. Official titles. No prohibited subjective adjectives. No speculative language. Claim-type required fields present. Content hash, supporting quote, and context window present. Source lineage disclosed where applicable.

This is a format check, not a content judgment. It is deterministic and reproducible.

### The Formula

```
base_score = (
    corroboration_rate     x 0.40 +
    source_verification    x 0.35 +
    consistency            x 0.15 +
    methodology_compliance x 0.10
)

trust_score = base_score x maturity_factor x stability_factor

effective_trust = trust_score x availability
```

Where:

- All component rates are between 0.0 and 1.0.
- `maturity_factor = min(1.0, days_active / 90)` for keys with signed lineage.
- `maturity_factor = min(1.0, days_active / 180)` for keys without signed lineage.
- `stability_factor` measures behavioral consistency (see below).
- `availability = min(1.0, hours_online_last_7_days / 168)`.

The maturity ramp is continuous. Day forty-five is halfway (for signed lineage). Day ninety is full. The ramp has a ceiling, not a switch.

Peers compute `days_active` from their own first observation of the server, not the server's self-asserted `started_at`. Self-asserted identity age is a trivial forgery. Observed identity age is not.

### Behavioral Stability

The stability factor detects sudden changes in a server's behavior patterns. It measures three signals over a rolling thirty-day window compared to the prior ninety-day baseline:

- **Source mix shift:** Is the server suddenly citing sources it has never used before, or abandoning sources it relied on?
- **Publication rate deviation:** Has the server's output volume changed dramatically?
- **Topic distribution shift:** Is the server suddenly publishing facts in categories or regions it has never covered?

**Trust gating for new sources:** If a server with established behavior suddenly cites a source it has never used before, and that source is the sole provider of the core claim, the fact is flagged as "unverified" until a second established server corroborates it. High-trust servers are not exempt from scrutiny when their behavior changes.

Stable behavior produces a stability factor of 1.0. A sudden, discontinuous shift in multiple signals simultaneously produces a stability factor well below 1.0.

### Structured Corroboration

Corroboration is determined by structured extraction comparison as defined in Fact Equivalence. Two facts corroborate each other when their structured extractions agree on the core claim: who (QID or normalized name), what (controlled vocabulary action verb), how many (quantities), where (location), and when (overlapping time windows). Source URL overlap provides additional confirmation.

This is more deterministic than semantic similarity. It is not perfectly deterministic because the extraction step is AI-assisted. The controlled vocabulary and Wikidata QIDs reduce cross-model divergence. The comparison step is fully deterministic given the extractions. The protocol is honest about this boundary.

### Source-Centric Trust

In addition to server trust scores, the protocol tracks **source reliability** across the network. If a narrow set of sources is cited exclusively by a cluster of servers and rarely by the broader network, corroboration credit from that cluster is capped regardless of server count. This prevents Sybil clusters from manufacturing credibility through a captive source pool.

Source reliability is computed from: how many independent servers cite the source, how often the source's content matches its content hash over time, and how frequently facts citing the source are corroborated by facts citing different sources.

### Trust Decay and Availability

Trust and availability decay differently:

- **Availability** decays with inactivity. A server that goes offline loses availability at a rate that reaches zero after seven days of complete inactivity. Availability recovers immediately when the server resumes publishing.
- **Trust** does not decay from inactivity alone. Trust decays only from verified failures: facts that fail source verification, fabrication circuit breakers, methodology compliance failures, or cluster suspicion penalties. A server that was reliable for a year and goes offline for a month returns with the same trust score and zero availability. Its effective trust recovers as availability recovers.

This separates quality from currency. A dormant but historically reliable server is not the same as an untrustworthy one.

### Client Trust Aggregation

Trust scores are observer-relative. Each server computes trust for its peers based on its own observations. The protocol defines a standard aggregation algorithm for clients:

```
aggregated_trust(server_X) = weighted_median(
    [trust_from_S1, trust_from_S2, ... trust_from_Sn],
    weights = [S1_effective_trust, S2_effective_trust, ... Sn_effective_trust]
)
```

The aggregated trust of a server is the weighted median of all assessments, where each assessment is weighted by the assessing server's own effective trust. High-trust servers' assessments count more.

**Low-N regime:** When fewer than five independent assessments are available, the weighted median is unreliable. Below this threshold, clients use the unweighted median and display an "insufficient assessments" indicator. This prevents the early network from ossifying around whichever server has the longest history.

Clients must use this algorithm. Ad-hoc trust computation undermines the protocol's consistency guarantees.

### Sybil Cluster Detection

The protocol uses continuous statistical analysis to detect coordinated server groups:

```
cluster_suspicion(A, B) = (
    pairwise_corroboration(A, B) - network_mean
) / network_std_deviation
```

When the cluster suspicion score exceeds 2.0 standard deviations, both servers receive a trust penalty proportional to the excess. There is no hard threshold to game.

Additional detection signals:

- **Source concentration:** Servers that consistently cite the same narrow set of sources, even if they publish at different times, are flagged. Independent servers naturally cite diverse source pools.
- **Infrastructure correlation:** Peers in the same ASN, with similar TLS fingerprints, or with correlated clock drift are noted. This is not proof of coordination, but it elevates suspicion when combined with other signals.

Full pseudocode and worked examples for the cluster detection algorithm are provided in the Trust Algorithm Reference appendix.

### Publication of Trust

Each server publishes its computed trust and availability scores for all known peers in its `/.well-known/jtf.json` endpoint, signed to prevent tampering. The network dashboard is itself a gossiped data structure: each server publishes its view, and clients aggregate them. No single server controls the dashboard.

Numbers only. No labels. Just like source scores.

------------------------------------------------------------------------

## Verification

### Source Checking

Verification uses the source evidence in this order of preference:

1. **Supporting quote in content hash:** Does the `supporting_quote` appear in the content whose hash matches `content_hash`? This is the fastest and most deterministic check.
2. **Context window integrity:** Does the `context_window` contradict or negate the supporting quote?
3. **Snapshot verification:** Fetch the `snapshot_url` and confirm the supporting quote appears in the archived page.
4. **Live URL check:** Fetch the current live `url` and check for the supporting quote. This is the weakest check because live URLs change.

The content hash is the primary proof. The snapshot URL is the secondary proof. The live URL is the tertiary check. Archive.org is a useful archiving service, but it is a centralized entity that can be blocked by national firewalls or served with removal requests. The protocol does not depend on any single archiving service.

### Peer-to-Peer Evidence Storage

Each server stores the supporting quote and context window for every fact it publishes or verifies. This evidence is served via the gossip protocol on request. When a peer needs to verify a fact's source evidence but the snapshot URL is unavailable, it can request the evidence from any server that has previously verified the fact.

This creates a decentralized proof archive that does not depend on the Wayback Machine or any other single service. The evidence is small (the quote plus a few hundred characters of context) and carries its own content hash for integrity.

### Graceful Aging

Source URLs change. Articles are edited, paywalled, moved, or deleted. This should not penalize honest servers retroactively.

If a source URL was verified as supporting the fact within forty-eight hours of publication (confirmed by the content hash and supporting quote captured at fetch time), the trust score is protected from future URL changes. Spot-checks of older facts prioritize the content hash and snapshot over the live URL. A fact whose supporting quote matches its content hash is verified, even if the live URL now returns a 404.

### Spot-Check Frequency

Full nodes are expected to verify source evidence at defined rates:

- **Every new fact received:** Verify the supporting quote appears in the content matching the content hash. This is deterministic and fast (no AI required).
- **Random sampling of older facts:** Ten percent of facts older than thirty days, weighted toward lower-trust servers and higher-impact claims (death, legal, financial).
- **Verification credit sharing:** When a full node spot-checks a fact and publishes its signed verification result, other full nodes can reuse that result for forty-eight hours. This distributes verification cost across the network. The checking node receives a small corroboration boost for contributing verification work.

This keeps verification honest and distributed without making the AI cost prohibitive for modest operators.

### AI Transparency

Every fact includes a `verification_method` field declaring the AI model and version used for fact extraction and editorialization removal, the prompt version, and whether methodology compliance was checked by rule-based analysis, AI-assisted analysis, or both.

The protocol does not mandate a specific AI model. It mandates transparency. Model diversity across the network is a feature, not a bug. A network where every server uses the same model corroborates the model's biases, not reality.

### Extraction Backends

The protocol is backend-agnostic. Two reference backend families are supported, and both are first-class:

- **Commercial API backends** (e.g., Anthropic, OpenAI) are straightforward to set up and scale. They incur per-request cost.
- **Locally-hosted backends** (e.g., Ollama, LM Studio, llama.cpp) run on commodity hardware (consumer GPU, Apple Silicon workstation). They incur one-time hardware cost and marginal electricity cost.

Neither path is privileged. A fact extracted by a self-hosted Qwen 2.5 72B model with correct source evidence receives the same trust as a fact extracted by a commercial model with the same evidence. The model diversity bonus rewards diversity regardless of how the model is accessed — a network with a healthy mix of commercial and local extractions is stronger than a network dominated by either.

Operators declare their extraction backend in the well-known endpoint and per-fact in `verification_method`. Clients and peers can inspect both.

**Allowed backend values (v1):** `anthropic`, `openai`, `ollama`, `lmstudio`, `custom`. The `custom` value is a placeholder for operators running other inference stacks; it must be accompanied by a `model` string that follows the `vendor:model:version` format so peers can still perform model-diversity analysis.

**Quality floor.** Operators running local models should run the reference extraction test suite (see Companion Documents) before publishing. A locally-hosted model that fails the deterministic methodology compliance checks is subject to the same penalties as any other server. The circuit breaker for fabrication (supporting quote not in content hash) applies equally, regardless of backend.

### Deterministic Checks

The following methodology compliance checks are rule-based, reproducible, and require no AI:

- Minimum two sources with ownership data
- No words from the prohibited subjective-adjective list (per-channel, per-language)
- Named entities include official titles
- No speculative language patterns
- Numeric specificity present where quantities are available
- Source ownership data within the current quarter
- Content hash, supporting quote, and context window present for all sources
- Context window does not negate the supporting quote
- Claim-type required fields present
- Source lineage disclosed where applicable
- No self-citation

These checks produce identical results regardless of implementation.

### Ownership Independence

Source ownership data is part of every fact. The protocol defines "unrelated" as: no common majority shareholder. Majority means more than fifty percent.

**Known limitation:** The fifty-percent threshold does not capture all forms of editorial influence. Board overlap, shared parent foundations, funding dependencies, minority stakes exercising disproportionate control, and editorial cooperation agreements can create effective coordination between sources that are technically independent by ownership percentage.

The protocol acknowledges this gap. The bright line is chosen for automation: it is verifiable from public financial disclosures without subjective judgment. Individual channels may define stricter thresholds for their own use (e.g., a channel that uses a twenty-percent threshold). More nuanced editorial-control analysis remains a domain for human auditors and is encouraged as part of the quarterly ownership review.

Ownership data is verified quarterly, per the methodology. Servers flag ownership data as `stale` if it is more than ninety days old. Facts published with stale ownership data are penalized in methodology compliance checks.

------------------------------------------------------------------------

## Resilience

### Threat Model

The JTF Protocol operates in an adversarial environment. The protocol is honest about what it can and cannot defend against.

**Financial attackers** seek to manipulate markets or damage competitors through false facts. The protocol's lack of monetization provides no financial reward. Source-level verification catches fabricated claims. The circuit breaker penalizes proven fabrication catastrophically.

**Ideological attackers** seek to promote a political narrative. Source-level verification catches fabricated claims. Behavioral stability monitoring catches shifts in source mix or topic distribution. Source diversity weighting means biased facts need to come from genuinely independent evidence, not just multiple servers citing the same captive sources.

**State actors** have budgets and institutional patience that dwarf individual attackers. The protocol makes state-actor attacks expensive, visible, and traceable, but it cannot prevent them absolutely:

- Source ownership transparency exposes state-controlled media connections.
- Behavioral stability monitoring detects the moment a sleeper network activates.
- The circuit breaker makes fabrication a disqualifying event with no recovery path after a second offense.
- Source lineage tracking exposes when "independent" outlets are reprinting the same state-controlled wire report.
- Primary source encouragement pushes verification toward original records.
- Model diversity bonus means a state actor must compromise multiple AI vendors, not just one.

No decentralized protocol can fully prevent a sufficiently funded, sufficiently patient state actor from influencing the network. The protocol's defense is that the attack is traceable and expensive. This is the same limitation faced by every information system, including traditional journalism.

**Disruption attackers** seek to damage the network through denial of service, peer-list poisoning, fact flooding, or correction spam. The protocol addresses these through rate limiting, peer validation, trust-weighted propagation, peer diversity constraints, and the mechanical controls described throughout this specification.

### Sybil Resistance

Defenses at three layers:

**Layer 1: Source-level verification.** Every fact carries a content hash, supporting quote, and context window. If the sources do not support the claims, spot-checking catches it. The circuit breaker makes fabrication catastrophic.

**Layer 2: Continuous cluster detection.** Statistical analysis, source concentration analysis, and infrastructure correlation signals detect coordinated groups. No hard thresholds to game.

**Layer 3: Temporal and economic cost.** No money in the network. Ninety to one-hundred-eighty-day maturity ramp per server. Bootstrap mirroring detection prevents rapid trust accumulation through feed copying. Source diversity weighting prevents corroboration laundering through shared source pools.

### Flood Protection

- **Maximum publication rate:** One hundred facts per twenty-four-hour period per channel.
- **Burst limit:** Ten facts in any thirty-minute window.
- **Announcement rate limit:** Two hundred announcements per hour to any single peer.
- **Correction rate limit:** Five corrections per twenty-four-hour period per server. Three corrections per target server per thirty-day period.

### Network Partition

If the network splits, each partition continues operating independently. When connectivity resumes, peer lists merge through normal gossip. Trust scores computed during partition are discarded and recomputed from the merged peer graph. Facts corroborated only within one partition will initially appear under-corroborated from the other partition's perspective; this resolves as merged trust scores stabilize.

### Total Failure

If every server in the network goes offline except one, that one server continues publishing facts. When others return, gossip resumes and the network reconstitutes. The protocol recovers from any failure short of total extinction.

------------------------------------------------------------------------

## Corrections

When a published fact is later proven false, the white paper is clear: "We do not bury mistakes. We name them."

### The Process

1. A server identifies an error in a previously published fact.
2. It publishes a **correction record**, signed, referencing the original fact's ID.
3. The correction includes: original text, corrected text, sources with full evidence (content hash, supporting quote, context window, snapshot URL), and correction type.
4. The correction is announced immediately to all peers.
5. Each receiving server independently verifies the correction using the same two-source standard.
6. **Trust gate:** Corrections from servers with effective trust below 0.50 are stored locally but not broadcast to the network until independently verified by a server above the threshold. This prevents low-trust servers from using corrections as a spam or denial-of-service vector.
7. Once verified and accepted, the original fact is marked as corrected in the archive. It is never deleted.

### Correction Format

```json
{
  "jtf_version": 1,
  "type": "correction",
  "original_fact_id": "sha256:e3b0c44...",
  "correction_type": "correction",
  "original_text": "The vote was 143 to 9.",
  "corrected_text": "The vote was 141 to 9.",
  "sources": [
    {
      "name": "United Nations Official Record",
      "url": "https://press.un.org/en/2026/ga12345.doc.htm",
      "content_hash": "sha256:3c363836cf4e...",
      "snapshot_url": "https://web.archive.org/web/...",
      "supporting_quote": "The resolution was adopted by a recorded vote of 141 in favour to 9 against.",
      "context_window": {
        "before": "The President announced the results:",
        "after": "with 12 abstentions.",
        "context_hash": "sha256:..."
      },
      "fetched_at": "2026-04-18T17:45:00Z",
      "ownership": [
        {"entity": "United Nations", "percentage": 100.0}
      ]
    }
  ],
  "published_at": "2026-04-18T18:00:00Z",
  "server": {
    "domain": "jtfnews.org",
    "public_key_id": "sha256:a1b2c3..."
  },
  "algorithm": "Ed25519",
  "signature": "base64-encoded-Ed25519-signature"
}
```

### Correction Types

- **Correction**: A factual detail was wrong. Both versions remain in the record.
- **Retraction**: The entire fact was false or unverifiable. It is withdrawn but remains in the archive, marked as retracted.

### Correction of Correction

A correction can be superseded by a newer correction referencing the same original fact. The latest verified correction takes precedence. The chain of corrections is preserved in the archive.

A retraction is final. Once a fact is retracted, it cannot be un-retracted. The original fact, the retraction, and the reasons remain in the permanent record. This is by design: if new evidence later supports the retracted claim, it is published as a new fact with new sources. We do not resurrect withdrawn claims. We publish new evidence.

### Correction Abuse Prevention

- **Trust gate:** Corrections below 0.50 effective trust are not broadcast.
- **Independent verification required:** A correction is not applied until at least one other server independently verifies it.
- **Per-sender rate limit:** Five corrections per twenty-four-hour period.
- **Per-target rate limit:** Three corrections against any single server per thirty-day period. This prevents targeted harassment campaigns.
- **Correction honesty tracking:** Servers that issue corrections consistently not verified by the network receive methodology compliance penalties.

### Reverse Pointers

When a correction is accepted, the network gossips a correction pointer linking the original fact ID to the correction. Clients fetching a fact from an archive can query for correction pointers matching that fact ID.

------------------------------------------------------------------------

## Channels

The global news stream is the first application. It is not the only one.

The protocol supports **channels**: independent fact streams serving different communities.

### Channel Types

- `global` -- Thresholds as defined in the white paper.
- `local:{region}` -- Local news. The community defines its own thresholds.
- `sports` -- Scores and outcomes. No hot takes.
- `school-board:{district}` -- Public education governance. Facts only.
- Any other community-defined channel identifier.

### Channel Namespace

Channel identifiers are case-insensitive strings. For namespaced channels, the region or district identifier should use established standards where they exist (ISO 3166 for countries, postal codes for localities) to prevent ambiguity.

There is no central namespace authority. If two servers use the same channel identifier, clients distinguish them by domain, not by channel ID alone. Channel identifiers are discovery aids, not exclusive claims.

### Channel Rules

Every channel follows the same methodology. The thresholds change. The methodology does not.

### Channel-Specific Configuration

Channels may customize certain protocol parameters for their community:

- The prohibited subjective-adjective list (per language, maintained by the channel operator)
- Relevance thresholds (what qualifies as news for this community)
- Ownership independence thresholds (a channel may use a stricter twenty-percent threshold if it chooses)

The core rules are non-negotiable: two sources, source evidence, corrections never deletions, no ads, no tracking.

### Cross-Channel Corroboration

A fact corroborated across different channels receives 1.5x corroboration credit. Servers operating independently with different scopes and source pools provide stronger evidence when they agree.

------------------------------------------------------------------------

## Clients

A client is any software that reads facts from one or more JTF servers. The JTF News iOS app is one client. A web browser, a command-line tool, an Alexa skill, a classroom display.

Anyone can build a client. The protocol serves them all equally. No client is privileged. The data is public. The format is documented. The methodology is open.

There is nothing preventing anyone from building their own app that reads the JTF Network. That is not a vulnerability. It is the point.

Clients must implement the trust aggregation algorithm defined in this specification.

------------------------------------------------------------------------

## Security

### Transport Security

All server-to-server and server-to-client communication must use TLS 1.3 or later. Unencrypted HTTP is not permitted for any protocol endpoint.

### Clock Synchronization

Timestamps are load-bearing throughout this protocol: maturity ramps, trust decay, verification windows, correction propagation, and staleness thresholds all depend on wall-clock time.

- NTP synchronization is required for all servers.
- Facts with `published_at` more than five minutes ahead of the receiving peer's clock are rejected.
- Peers compute `days_active` from their own first observation of the server, not the server's self-asserted `started_at`. Self-asserted identity age is a trivial forgery. Observed identity age is not.

### Signed Messages

The following protocol messages must be signed: the well-known endpoint, every published fact, every correction record, every key revocation or rotation announcement, and every fact announcement. Peers must verify signatures before accepting any of these messages. Messages with invalid signatures are silently dropped.

### Implementation Security Considerations

This specification defines wire formats and protocol mechanics. Implementations must also address:

- **Key storage:** Private keys should be stored encrypted at rest. Hardware security modules (HSMs) are recommended for high-value servers.
- **Random number generation:** Key generation must use a cryptographically secure random number generator.
- **Timing attacks:** Signature verification should use constant-time comparison to prevent timing side channels.
- **Dependency management:** Reference implementations should pin cryptographic library versions and audit them regularly.

These are implementation details, not protocol requirements. They are the difference between a protocol that is secure on paper and secure in deployment.

------------------------------------------------------------------------

## Recognition

There is no money in the JTF Network. No advertising. No subscriptions. No tokens. No dividends. We own nothing.

Operators run servers because the mission matters to them. The protocol honors that commitment through transparent recognition:

- Every server is listed with its domain, channel, uptime, trust score, availability, and contribution metrics.
- Contribution metrics include: total facts published, corroboration rate, days active, corrections issued, verification credits contributed, node type.
- Numbers only. No labels. No rankings. Data, not editorializing.
- The network dashboard is a gossiped data structure. No single server controls it.

Operators may include voluntary donation links or organizational information in their well-known endpoint metadata. The protocol does not prohibit this. It does not facilitate it either.

Recognition is the primary incentive. It is sufficient for the kind of person who runs a JTF server.

------------------------------------------------------------------------

## Data Retention

Aligned with the white paper:

- **Raw source material:** Seven days maximum, then deleted. Content hashes, supporting quotes, and context windows extracted at fetch time are permanent.
- **Published facts:** Archived permanently in daily compressed logs.
- **Peer-to-peer evidence:** Supporting quotes and context windows stored locally and served via gossip. Permanent.
- **Peer discovery data:** Peers not seen in seven days are dropped.
- **Trust scores:** Recomputed daily. Historical scores archived for audit.
- **Verification results:** Spot-check results retained for ninety days.
- **Correction records:** Permanent.
- **Signatures:** Permanent.

Servers may optionally publish a daily **Merkle root** of their archive, allowing light nodes and clients to verify archive integrity without downloading every fact.

Nothing hidden. Nothing sold. Just the record.

------------------------------------------------------------------------

## Protocol Evolution

The protocol will change. When it does, changes are versioned, public, and gradual.

- The `jtf_protocol_version` field declares the supported version.
- Minor versions add non-breaking extensions.
- Major versions introduce breaking changes.
- Backward compatibility is required within a major version.
- **Deprecation timeline:** When a major version is released, the prior major version remains supported for six months.

Changes are tracked publicly on GitHub, version-controlled, and licensed under CC-BY-SA. The protocol belongs to everyone. It changes in the open.

------------------------------------------------------------------------

## Known Limitations

The protocol is honest about what it cannot do:

- **AI bias is mitigated, not eliminated.** Rule-based checks minimize editorialization. AI-assisted analysis provides an additional layer. Neither is perfect.
- **Structured extraction is more deterministic than semantic similarity, not perfectly deterministic.** The extraction step is AI-dependent. The comparison step is deterministic. Controlled vocabularies and Wikidata QIDs reduce divergence. They do not eliminate it.
- **Ownership data is approximate.** The fifty-percent threshold automates independence checking but does not capture all forms of editorial influence.
- **State actors can influence the network.** The protocol makes such attacks expensive, visible, and traceable, but it cannot prevent them absolutely.
- **The protocol guarantees factual integrity, not narrative completeness.** All published facts may be individually correct while the selection of facts is biased or strategic omissions shape a narrative. The protocol verifies what is published. It cannot verify what is not published. This is a fundamental boundary of any fact-verification system.
- **The incentive model may not scale globally.** Recognition serves mission-driven operators. It may not attract sufficient geographic diversity for comprehensive coverage.
- **Trust scores are estimates, not measurements.** They are useful approximations computed from partial observations by imperfect algorithms.
- **Legal conflicts with permanent archives.** Facts contain names of individuals. The archive is permanent. Servers in jurisdictions with right-to-erasure laws (GDPR Article 17 and equivalents) may face legal pressure that conflicts with the protocol's "corrections, never deletions" principle. This is a policy tension, not a technical one. The protocol's architecture forecloses certain compliance strategies. Operators must understand this before joining the network.
- **The prohibited-adjective list is a governance artifact.** Maintained per-channel and per-language, it requires a defined amendment process. The global channel's English list is maintained in the protocol appendix. Other channels maintain their own. The amendment process is documented in Appendix A.

These are not failures. They are boundaries. The protocol operates within them honestly rather than claiming capabilities it does not have.

------------------------------------------------------------------------

## Companion Documents

This specification defines the architecture, trust model, and data formats. The following companion documents provide additional detail:

- **Wire Protocol Specification** (forthcoming): HTTP endpoints, request/response formats, authentication headers, error codes, version negotiation mechanics.
- **Reference Implementation Guide** (forthcoming): How to set up a JTF server, generate keys, configure gossip, and join the network.
- **Appendix A: Prohibited Adjective Lists** (forthcoming): Per-language lists with amendment process.
- **Appendix B: Controlled Action Vocabulary** (forthcoming): The canonical action verb list for structured extraction.
- **Appendix C: URL Normalization Rules** (forthcoming): Canonicalization rules for source URL comparison.
- **Trust Algorithm Reference** (forthcoming): Full pseudocode, worked examples, cluster detection algorithm, and edge cases.

------------------------------------------------------------------------

## Reference Implementation

The reference implementation of the JTF Protocol is the JTF News server at `jtfnews.org`, adapted from the existing open-source codebase. It is available on GitHub under CC-BY-SA. The reference implementation ships with a pluggable extraction backend layer supporting both commercial APIs (Anthropic, OpenAI) and local inference (Ollama, LM Studio). Operators select their backend at deployment; the protocol is indifferent.

Any implementation that follows this specification is a valid participant. A server written in Go, Rust, JavaScript, or any other language is equally valid. The standard is this document, not any particular software.

------------------------------------------------------------------------

## What Stays the Same

The white paper defines what JTF News is. This protocol defines how it survives.

Nothing in this protocol changes the methodology. Everything in this protocol serves it.

Across all servers, all channels, all implementations, all clients:

- Two or more unrelated sources minimum
- Editorialization minimized through rule-based constraints and transparent AI-assisted analysis
- Source ownership disclosed with every fact
- Source evidence preserves the proof
- No ads. No tracking. No profit.
- Public archives. Open methodology. Visible algorithms.
- Corrections named, never buried
- We serve. We do not sell.

------------------------------------------------------------------------

## Mission

To make the factual record unkillable.

When one server goes dark, another speaks. When one operator leaves, the network remains. When the last original contributor is gone, the protocol continues.

The methodology belongs to no one. Now neither does the infrastructure.

------------------------------------------------------------------------

## Why

Because a fact network that depends on one person is not a fact network. It is a single point of failure with good intentions.

The world does not need good intentions. It needs facts that survive.

------------------------------------------------------------------------

## Launch

When two servers speak. When the gossip begins. The network starts. No fanfare.
