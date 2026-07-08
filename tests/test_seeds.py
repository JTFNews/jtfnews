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


def test_lookup_srv_seed_returns_url_from_target_and_port():
    resolver = FakeResolver({
        ("_jtf._tcp.example.com", "SRV"): [
            ("srv.example.com", 443, 10, 100),
        ],
    })
    result = seeds.lookup_srv_seed("example.com", resolver=resolver)
    assert result == "https://srv.example.com/.well-known/jtf.json"


def test_lookup_srv_seed_uses_http_scheme_for_port_80():
    resolver = FakeResolver({
        ("_jtf._tcp.example.com", "SRV"): [
            ("srv.example.com", 80, 10, 100),
        ],
    })
    assert seeds.lookup_srv_seed("example.com", resolver=resolver) == (
        "http://srv.example.com/.well-known/jtf.json"
    )


def test_lookup_srv_seed_uses_lowest_priority_first():
    resolver = FakeResolver({
        ("_jtf._tcp.example.com", "SRV"): [
            ("high.example.com", 443, 20, 100),
            ("low.example.com", 443, 10, 100),
        ],
    })
    assert seeds.lookup_srv_seed("example.com", resolver=resolver) == (
        "https://low.example.com/.well-known/jtf.json"
    )


def test_lookup_srv_seed_returns_none_when_no_record():
    resolver = FakeResolver()
    assert seeds.lookup_srv_seed("example.com", resolver=resolver) is None


def test_discover_seeds_returns_hardcoded_urls_when_no_dns_hints():
    resolver = FakeResolver()
    urls = seeds.discover_seeds(candidate_domains=("example.com",), resolver=resolver)
    assert "https://jtfnews.org/.well-known/jtf.json" in urls
    assert len(urls) == 1


def test_discover_seeds_includes_dns_txt_hint():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["https://example.com/.well-known/jtf.json"],
    })
    urls = seeds.discover_seeds(candidate_domains=("example.com",), resolver=resolver)
    assert "https://example.com/.well-known/jtf.json" in urls
    assert "https://jtfnews.org/.well-known/jtf.json" in urls


def test_discover_seeds_prefers_txt_over_srv_when_both_present():
    resolver = FakeResolver({
        ("_jtf.example.com", "TXT"): ["https://txt.example.com/.well-known/jtf.json"],
        ("_jtf._tcp.example.com", "SRV"): [("srv.example.com", 443, 10, 100)],
    })
    urls = seeds.discover_seeds(candidate_domains=("example.com",), resolver=resolver)
    assert "https://txt.example.com/.well-known/jtf.json" in urls
    assert "https://srv.example.com/.well-known/jtf.json" not in urls


def test_discover_seeds_deduplicates():
    resolver = FakeResolver({
        ("_jtf.jtfnews.org", "TXT"): ["https://jtfnews.org/.well-known/jtf.json"],
    })
    urls = seeds.discover_seeds(candidate_domains=("jtfnews.org",), resolver=resolver)
    assert urls.count("https://jtfnews.org/.well-known/jtf.json") == 1
