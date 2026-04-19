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
