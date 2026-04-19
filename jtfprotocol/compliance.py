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
