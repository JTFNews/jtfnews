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
