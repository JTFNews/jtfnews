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


from unittest.mock import MagicMock


def test_anthropic_backend_calls_api_and_parses_json():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"subjects": ["Q47010"], "subjects_text": ["UN General Assembly"], "action": "voted", "objects": ["Somaliland"], "quantities": [{"value": 143, "context": "votes in favor"}], "location": "New York", "event_time": {"start": "2026-04-18T14:00:00Z", "end": "2026-04-18T15:00:00Z"}, "claim_type": "vote"}')]
    mock_client.messages.create.return_value = mock_response

    backend = extraction.AnthropicBackend(
        client=mock_client,
        model="claude-haiku-4-5-20251001",
    )
    result = backend.extract_fact(
        "The UN General Assembly voted 143 to 9.",
        {"name": "Reuters", "url": "https://reuters.com/x"},
    )
    assert isinstance(result, extraction.StructuredFact)
    assert result.action == "voted"
    assert result.subjects == ["Q47010"]
    mock_client.messages.create.assert_called_once()


def test_anthropic_backend_raises_on_non_json_response():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="this is not json")]
    mock_client.messages.create.return_value = mock_response

    backend = extraction.AnthropicBackend(
        client=mock_client,
        model="claude-haiku-4-5-20251001",
    )
    with pytest.raises(extraction.ExtractionError):
        backend.extract_fact("x", {"name": "y", "url": "z"})


def test_anthropic_backend_declares_identifiers():
    backend = extraction.AnthropicBackend(
        client=MagicMock(),
        model="claude-haiku-4-5-20251001",
    )
    assert backend.backend_id == extraction.BACKEND_ANTHROPIC
    assert backend.model == "anthropic:claude-haiku-4-5-20251001"
    assert backend.prompt_version == "jtf-extract-v3"


def test_openai_compatible_backend_calls_api_and_parses_json():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"subjects": [], "subjects_text": ["Example"], "action": "announced", "objects": ["Policy"], "quantities": [], "location": "Washington", "event_time": {"start": "2026-04-18T10:00:00Z", "end": "2026-04-18T10:00:00Z"}, "claim_type": "announcement"}'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    backend = extraction.OpenAICompatibleBackend(
        client=mock_client,
        model="qwen2.5:72b-instruct-q5_K_M",
        backend_id=extraction.BACKEND_OLLAMA,
    )
    result = backend.extract_fact(
        "The agency announced a new policy.",
        {"name": "Reuters", "url": "https://reuters.com/y"},
    )
    assert isinstance(result, extraction.StructuredFact)
    assert result.action == "announced"


def test_openai_compatible_backend_declares_backend_id():
    for bid in [extraction.BACKEND_OPENAI, extraction.BACKEND_OLLAMA, extraction.BACKEND_LMSTUDIO]:
        backend = extraction.OpenAICompatibleBackend(
            client=MagicMock(),
            model="m",
            backend_id=bid,
        )
        assert backend.backend_id == bid


def test_openai_compatible_backend_rejects_invalid_backend_id():
    with pytest.raises(ValueError):
        extraction.OpenAICompatibleBackend(
            client=MagicMock(),
            model="m",
            backend_id="not_a_valid_backend",
        )


def test_openai_compatible_backend_raises_on_non_json():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "not json at all"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    backend = extraction.OpenAICompatibleBackend(
        client=mock_client,
        model="m",
        backend_id=extraction.BACKEND_OLLAMA,
    )
    with pytest.raises(extraction.ExtractionError):
        backend.extract_fact("x", {"name": "y", "url": "z"})


def test_get_backend_returns_anthropic_when_configured():
    cfg = {
        "backend": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "api_key": "sk-ant-fake",
    }
    backend = extraction.get_backend(cfg)
    assert isinstance(backend, extraction.AnthropicBackend)
    assert backend.backend_id == "anthropic"


def test_get_backend_returns_ollama_when_configured():
    cfg = {
        "backend": "ollama",
        "model": "qwen2.5:72b-instruct-q5_K_M",
        "base_url": "http://localhost:11434/v1",
    }
    backend = extraction.get_backend(cfg)
    assert isinstance(backend, extraction.OpenAICompatibleBackend)
    assert backend.backend_id == "ollama"


def test_get_backend_returns_lmstudio_when_configured():
    cfg = {
        "backend": "lmstudio",
        "model": "qwen2.5-72b-instruct",
        "base_url": "http://localhost:1234/v1",
    }
    backend = extraction.get_backend(cfg)
    assert isinstance(backend, extraction.OpenAICompatibleBackend)
    assert backend.backend_id == "lmstudio"


def test_get_backend_rejects_unknown_backend():
    with pytest.raises(ValueError):
        extraction.get_backend({"backend": "nonsense", "model": "x"})
