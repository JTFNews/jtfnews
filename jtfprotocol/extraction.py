"""Pluggable extraction backends.

Every JTF server extracts structured facts from raw source text. The
protocol is backend-agnostic: commercial APIs and local inference are
both first-class. This module defines the interface and ships two
concrete backends (Anthropic, and an OpenAI-compatible backend that
covers OpenAI / Ollama / LM Studio).

See documentation/Protocol Ver 1.0 CURRENT.md, section "Extraction Backends".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
