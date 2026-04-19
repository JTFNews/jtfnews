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
