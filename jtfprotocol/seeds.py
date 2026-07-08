"""JTF Protocol seed domain list and DNS discovery fallback.

Servers use this module on first startup to find at least one other
server. Once a server has exchanged peer lists with two others, it no
longer needs seeds. The seed list is a lifeboat, not a chain of command.

See documentation/Protocol Ver 1.0 CURRENT.md, sections "Seed Domains"
and "Fallback Discovery".
"""
from __future__ import annotations

from typing import Protocol


SEED_DOMAINS: tuple[str, ...] = (
    "jtfnews.org",
)
"""Hard-coded seed domains. Additional entries are added by editing this
tuple and cutting a new release. The protocol requires a minimum of three
seed domains in different jurisdictions before the network is considered
production-ready."""


class Resolver(Protocol):
    """Injectable DNS resolver. Tests supply a fake; production uses
    `DnspythonResolver` which wraps the ``dnspython`` package."""

    def resolve_txt(self, name: str) -> list[str]:
        ...

    def resolve_srv(self, name: str) -> list[tuple[str, int, int, int]]:
        ...


class DnspythonResolver:
    """Default resolver backed by ``dnspython``. Silent on NXDOMAIN /
    NoAnswer -- those are expected outcomes, not errors."""

    def resolve_txt(self, name: str) -> list[str]:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, "TXT")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        out: list[str] = []
        for rdata in answers:
            # Each TXT rdata is a sequence of byte strings; join and decode.
            joined = b"".join(rdata.strings).decode("utf-8", errors="replace")
            out.append(joined)
        return out

    def resolve_srv(self, name: str) -> list[tuple[str, int, int, int]]:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(name, "SRV")
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        out: list[tuple[str, int, int, int]] = []
        for rdata in answers:
            target = str(rdata.target).rstrip(".")
            out.append((target, int(rdata.port), int(rdata.priority), int(rdata.weight)))
        return out


def _default_resolver() -> Resolver:
    return DnspythonResolver()


def lookup_txt_seed(domain: str, resolver: Resolver | None = None) -> str | None:
    """Look up ``_jtf.{domain}`` TXT record. Return the first URL-looking
    value or None. Does not fetch the URL."""
    resolver = resolver or _default_resolver()
    records = resolver.resolve_txt(f"_jtf.{domain}")
    for value in records:
        if value.startswith("http://") or value.startswith("https://"):
            return value
    return None
