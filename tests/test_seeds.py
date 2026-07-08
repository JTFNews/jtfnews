"""Tests for jtfprotocol.seeds."""
from __future__ import annotations

from jtfprotocol import seeds


def test_seed_domains_is_a_tuple_of_strings():
    assert isinstance(seeds.SEED_DOMAINS, tuple)
    assert all(isinstance(d, str) and d for d in seeds.SEED_DOMAINS)


def test_seed_domains_includes_jtfnews_org():
    assert "jtfnews.org" in seeds.SEED_DOMAINS
