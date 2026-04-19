"""Shared fact-extraction prompt template.

Every backend uses the same prompt. Divergence between backends traces
to the model, never to the prompt. If the prompt changes, bump
PROMPT_VERSION and update the compliance/verification tests.
"""
from __future__ import annotations


PROMPT_VERSION = "jtf-extract-v3"


CONTROLLED_ACTIONS: tuple[str, ...] = (
    "voted", "approved", "adopted", "announced", "signed",
    "arrested", "charged", "acquired", "merged", "launched",
    "deployed", "struck", "collapsed", "resigned", "appointed",
    "ratified", "vetoed", "released", "detained", "fined",
)

CLAIM_TYPES: tuple[str, ...] = (
    "vote", "election", "financial", "legal",
    "death", "injury", "announcement", "agreement",
)


EXTRACTION_TEMPLATE = """You extract structured facts from news source text for
the JTF Protocol. The methodology is strict: only verifiable facts, no
editorializing, no speculation, no adjectives.

Return a JSON object with exactly these fields:

- subjects: list of Wikidata QIDs when available (e.g. "Q47010"). Empty list if unknown.
- subjects_text: list of human-readable entity names.
- action: a single verb from this controlled vocabulary: {actions}.
- objects: list of strings naming the objects of the action.
- quantities: list of {{value, context}} pairs. `value` is numeric. `context` describes what is counted.
- location: string, most specific known location. Empty string if unknown.
- event_time: {{start, end}} with ISO-8601 timestamps. Use the same value for both if only a single moment is known.
- claim_type: one of {claim_types}.

Do not add any other fields. Do not include commentary. Do not use
subjective adjectives. Do not speculate beyond what the source text
states.

Source: {source_name}
URL: {source_url}
Text:
{source_text}

Return only the JSON object.
"""


def build_extraction_prompt(source_text: str, source_metadata: dict) -> str:
    """Render the shared prompt for a given source."""
    return EXTRACTION_TEMPLATE.format(
        actions=", ".join(CONTROLLED_ACTIONS),
        claim_types=", ".join(CLAIM_TYPES),
        source_name=source_metadata.get("name", ""),
        source_url=source_metadata.get("url", ""),
        source_text=source_text,
    )
