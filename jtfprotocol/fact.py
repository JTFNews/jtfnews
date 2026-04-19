"""JTF Protocol canonical fact format.

The Fact is the atomic unit of the protocol. This module defines the
dataclass, round-trip serialization to/from dict, the canonical JSON
encoding used for hashing and signing, and the sign/verify helpers.

See documentation/Protocol Ver 1.0 CURRENT.md, section "The Fact".
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any


JTF_VERSION = 1


@dataclass(frozen=True)
class Fact:
    """A canonical JTF fact.

    Fields mirror the protocol spec exactly. Internal structure uses
    plain dicts for nested objects (verification_method, structured_extraction,
    sources, primary_source, server) because they are schema-stable but
    extensible. Stronger typing is a Phase 2 refactor if it earns its cost.
    """

    jtf_version: int
    id: str
    fact: str
    occurred_at: str
    published_at: str
    verification_method: dict
    structured_extraction: dict
    sources: list[dict]
    primary_source: dict | None
    channel: str
    server: dict
    algorithm: str
    signature: str

    @classmethod
    def from_dict(cls, data: dict) -> Fact:
        """Construct a Fact from a dict parsed from JSON.

        Performs version and presence validation. Does NOT verify the
        signature -- use `verify_fact` for that.
        """
        if data.get("jtf_version") != JTF_VERSION:
            raise ValueError(
                f"unsupported jtf_version: {data.get('jtf_version')} (expected {JTF_VERSION})"
            )
        required = [
            "id", "fact", "occurred_at", "published_at",
            "verification_method", "structured_extraction", "sources",
            "channel", "server", "algorithm", "signature",
        ]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"fact missing required fields: {missing}")
        return cls(
            jtf_version=data["jtf_version"],
            id=data["id"],
            fact=data["fact"],
            occurred_at=data["occurred_at"],
            published_at=data["published_at"],
            verification_method=copy.deepcopy(data["verification_method"]),
            structured_extraction=copy.deepcopy(data["structured_extraction"]),
            sources=copy.deepcopy(data["sources"]),
            primary_source=copy.deepcopy(data.get("primary_source")),
            channel=data["channel"],
            server=copy.deepcopy(data["server"]),
            algorithm=data["algorithm"],
            signature=data["signature"],
        )

    def to_dict(self) -> dict:
        """Return the fact as a plain dict suitable for JSON encoding."""
        out: dict[str, Any] = {
            "jtf_version": self.jtf_version,
            "id": self.id,
            "fact": self.fact,
            "occurred_at": self.occurred_at,
            "published_at": self.published_at,
            "verification_method": copy.deepcopy(self.verification_method),
            "structured_extraction": copy.deepcopy(self.structured_extraction),
            "sources": copy.deepcopy(self.sources),
        }
        if self.primary_source is not None:
            out["primary_source"] = copy.deepcopy(self.primary_source)
        out["channel"] = self.channel
        out["server"] = copy.deepcopy(self.server)
        out["algorithm"] = self.algorithm
        out["signature"] = self.signature
        return out


def canonical_json(data: dict) -> str:
    """Return a deterministic JSON encoding of `data`.

    - Keys are sorted lexicographically at every level.
    - No whitespace between tokens.
    - Unicode is preserved (not escaped).
    - Trailing newlines are not added.

    This is the single canonical encoding used for fact ID hashing,
    signing, and signature verification. Any two callers that hash or
    sign the same conceptual fact must produce identical bytes.
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
