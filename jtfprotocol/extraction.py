"""Pluggable extraction backends.

Every JTF server extracts structured facts from raw source text. The
protocol is backend-agnostic: commercial APIs and local inference are
both first-class. This module defines the interface and ships two
concrete backends (Anthropic, and an OpenAI-compatible backend that
covers OpenAI / Ollama / LM Studio).

See documentation/Protocol Ver 1.0 CURRENT.md, section "Extraction Backends".
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from jtfprotocol import prompts


BACKEND_ANTHROPIC = "anthropic"
BACKEND_OPENAI = "openai"
BACKEND_OLLAMA = "ollama"
BACKEND_LMSTUDIO = "lmstudio"
BACKEND_CUSTOM = "custom"

SUPPORTED_BACKENDS = frozenset({
    BACKEND_ANTHROPIC,
    BACKEND_OPENAI,
    BACKEND_OLLAMA,
    BACKEND_LMSTUDIO,
    BACKEND_CUSTOM,
})


@dataclass(frozen=True)
class StructuredFact:
    """The extracted structured form of a fact.

    Matches the `structured_extraction` object in the canonical fact
    schema. Free of signature, sources, and identity fields -- those are
    added by the caller (Phase 5 integration) when assembling the
    canonical fact.
    """
    subjects: list[str]           # Wikidata QIDs where available
    subjects_text: list[str]      # Human-readable names
    action: str                   # From controlled vocabulary
    objects: list[str]
    quantities: list[dict]        # [{value, context}, ...]
    location: str
    event_time: dict              # {start, end} ISO-8601
    claim_type: str


class ExtractionBackend(ABC):
    """Interface every extraction backend implements."""

    backend_id: str = ""   # One of SUPPORTED_BACKENDS
    model: str = ""        # vendor:model:version
    prompt_version: str = ""

    @abstractmethod
    def extract_fact(
        self,
        source_text: str,
        source_metadata: dict,
    ) -> StructuredFact:
        """Extract a StructuredFact from raw source text.

        `source_text` is the article content. `source_metadata` carries
        the source name, URL, publication date, and any other hints the
        prompt may incorporate.

        Raises:
            ExtractionError: if the backend returns malformed output or
                a non-recoverable error.
        """


class ExtractionError(RuntimeError):
    """Raised when a backend fails to produce a valid StructuredFact."""


class AnthropicBackend(ExtractionBackend):
    """Fact extraction via the Anthropic Messages API."""

    backend_id = BACKEND_ANTHROPIC

    def __init__(self, client, model: str, max_tokens: int = 1024):
        """Construct an AnthropicBackend.

        Args:
            client: An initialized `anthropic.Anthropic` client. Passed
                in rather than constructed here so tests can inject a
                mock.
            model: The model identifier accepted by the Anthropic SDK
                (e.g. "claude-haiku-4-5-20251001"). Stored on the
                instance as `self.model` in canonical `vendor:model`
                form for protocol disclosure.
            max_tokens: Maximum tokens in the model response.
        """
        self._client = client
        self._model_raw = model
        self.model = f"anthropic:{model}"
        self.prompt_version = prompts.PROMPT_VERSION
        self._max_tokens = max_tokens

    def extract_fact(
        self,
        source_text: str,
        source_metadata: dict,
    ) -> StructuredFact:
        prompt = prompts.build_extraction_prompt(source_text, source_metadata)
        response = self._client.messages.create(
            model=self._model_raw,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            raw_text = response.content[0].text
            data = json.loads(raw_text)
            return StructuredFact(
                subjects=data["subjects"],
                subjects_text=data["subjects_text"],
                action=data["action"],
                objects=data["objects"],
                quantities=data["quantities"],
                location=data["location"],
                event_time=data["event_time"],
                claim_type=data["claim_type"],
            )
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError) as e:
            raise ExtractionError(
                f"Anthropic backend returned malformed output: {e}"
            ) from e


_OPENAI_COMPATIBLE_BACKEND_IDS = frozenset({
    BACKEND_OPENAI, BACKEND_OLLAMA, BACKEND_LMSTUDIO, BACKEND_CUSTOM,
})


class OpenAICompatibleBackend(ExtractionBackend):
    """Fact extraction via any OpenAI-compatible Chat Completions endpoint.

    Used for:
      - OpenAI official API (backend_id="openai")
      - Ollama's OpenAI-compatible endpoint (backend_id="ollama")
      - LM Studio (backend_id="lmstudio")
      - Any other self-hosted OpenAI-compatible server (backend_id="custom")

    The caller constructs an SDK client pointed at the correct base URL
    and passes it in. This class is transport-agnostic -- it only speaks
    the Chat Completions wire format.
    """

    def __init__(
        self,
        client,
        model: str,
        backend_id: str,
        max_tokens: int = 1024,
    ):
        if backend_id not in _OPENAI_COMPATIBLE_BACKEND_IDS:
            raise ValueError(
                f"backend_id must be one of {sorted(_OPENAI_COMPATIBLE_BACKEND_IDS)}, "
                f"got {backend_id!r}"
            )
        self._client = client
        self._model_raw = model
        self.backend_id = backend_id
        self.model = f"{backend_id}:{model}"
        self.prompt_version = prompts.PROMPT_VERSION
        self._max_tokens = max_tokens

    def extract_fact(
        self,
        source_text: str,
        source_metadata: dict,
    ) -> StructuredFact:
        prompt = prompts.build_extraction_prompt(source_text, source_metadata)
        response = self._client.chat.completions.create(
            model=self._model_raw,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            raw_text = response.choices[0].message.content
            data = json.loads(raw_text)
            return StructuredFact(
                subjects=data["subjects"],
                subjects_text=data["subjects_text"],
                action=data["action"],
                objects=data["objects"],
                quantities=data["quantities"],
                location=data["location"],
                event_time=data["event_time"],
                claim_type=data["claim_type"],
            )
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError) as e:
            raise ExtractionError(
                f"{self.backend_id} backend returned malformed output: {e}"
            ) from e
