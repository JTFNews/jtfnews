"""Tests for jtfprotocol.extraction."""
import pytest

from jtfprotocol import extraction


def test_extraction_backend_is_abstract():
    with pytest.raises(TypeError):
        extraction.ExtractionBackend()


def test_structured_fact_is_frozen_dataclass():
    sf = extraction.StructuredFact(
        subjects=["Q47010"],
        subjects_text=["United Nations General Assembly"],
        action="voted",
        objects=["Republic of Somaliland"],
        quantities=[{"value": 143, "context": "votes in favor"}],
        location="UN Headquarters, New York",
        event_time={"start": "2026-04-18T14:00:00Z", "end": "2026-04-18T15:00:00Z"},
        claim_type="vote",
    )
    with pytest.raises(Exception):
        sf.action = "something else"


def test_backend_identifier_is_documented():
    assert extraction.BACKEND_ANTHROPIC == "anthropic"
    assert extraction.BACKEND_OPENAI == "openai"
    assert extraction.BACKEND_OLLAMA == "ollama"
    assert extraction.BACKEND_LMSTUDIO == "lmstudio"
