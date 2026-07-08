"""Tests for jtfprotocol.seeds."""
from __future__ import annotations

from jtfprotocol import seeds


def test_seed_domains_is_a_tuple_of_strings():
    assert isinstance(seeds.SEED_DOMAINS, tuple)
    assert all(isinstance(d, str) and d for d in seeds.SEED_DOMAINS)


def test_seed_domains_includes_jtfnews_org():
    assert "jtfnews.org" in seeds.SEED_DOMAINS


class FakeResolver:
    """Fake DNS resolver for tests. Maps (name, rdtype) -> list of str."""

    def __init__(self, answers: dict[tuple[str, str], list[str]] | None = None):
        self._answers = answers or {}

    def resolve_txt(self, name: str) -> list[str]:
        return list(self._answers.get((name, "TXT"), []))

    def resolve_srv(self, name: str) -> list[tuple[str, int, int, int]]:
        # (target, port, priority, weight)
        raw = self._answers.get((name, "SRV"), [])
        return list(raw)


def test_lookup_txt_seed_returns_url_when_txt_record_present():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["https://example.com/.well-known/jtf.json"],
    })
    result = seeds.lookup_txt_seed("example.com", resolver=resolver)
    assert result == "https://example.com/.well-known/jtf.json"


def test_lookup_txt_seed_returns_none_when_no_record():
    resolver = FakeResolver()
    assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


def test_lookup_txt_seed_returns_none_when_record_is_not_a_url():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["not-a-url"],
    })
    assert seeds.lookup_txt_seed("example.com", resolver=resolver) is None


def test_lookup_txt_seed_takes_first_url_when_multiple_records():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): [
            "https://a.example.com/.well-known/jtf.json",
            "https://b.example.com/.well-known/jtf.json",
        ],
    })
    result = seeds.lookup_txt_seed("example.com", resolver=resolver)
    assert result == "https://a.example.com/.well-known/jtf.json"
