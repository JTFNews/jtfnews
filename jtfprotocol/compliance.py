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
