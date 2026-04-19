"""Tests for jtfprotocol.prompts."""
from jtfprotocol import prompts


def test_prompt_template_is_deterministic():
    p1 = prompts.build_extraction_prompt("text A", {"name": "Reuters"})
    p2 = prompts.build_extraction_prompt("text A", {"name": "Reuters"})
    assert p1 == p2


def test_prompt_includes_controlled_action_vocabulary():
    p = prompts.build_extraction_prompt("x", {"name": "y"})
    for verb in ["voted", "approved", "signed"]:
        assert verb in p


def test_prompt_includes_claim_types():
    p = prompts.build_extraction_prompt("x", {"name": "y"})
    for ct in ["vote", "financial", "legal", "death"]:
        assert ct in p


def test_prompt_includes_source_text():
    p = prompts.build_extraction_prompt(
        "The General Assembly voted 143 to 9.",
        {"name": "Reuters", "url": "https://reuters.com/x"},
    )
    assert "The General Assembly voted 143 to 9." in p
    assert "Reuters" in p


def test_prompt_version_is_declared():
    assert prompts.PROMPT_VERSION == "jtf-extract-v3"
