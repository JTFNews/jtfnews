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


def lookup_srv_seed(domain: str, resolver: Resolver | None = None) -> str | None:
    """Look up ``_jtf._tcp.{domain}`` SRV record. Return a well-known
    URL derived from the lowest-priority target, or None.

    Scheme selection: port 80 -> http, anything else -> https. The
    protocol expects TLS for anything other than the well-known port.
    """
    resolver = resolver or _default_resolver()
    records = resolver.resolve_srv(f"_jtf._tcp.{domain}")
    if not records:
        return None
    records = sorted(records, key=lambda r: (r[2], -r[3]))
    target, port, _priority, _weight = records[0]
    scheme = "http" if port == 80 else "https"
    host = target if port in (80, 443) else f"{target}:{port}"
    return f"{scheme}://{host}/.well-known/jtf.json"


def lookup_txt_seed(domain: str, resolver: Resolver | None = None) -> str | None:
    """Look up ``_jtf.{domain}`` TXT record. Return the first URL-looking
    value or None. Does not fetch the URL."""
    resolver = resolver or _default_resolver()
    records = resolver.resolve_txt(f"_jtf.{domain}")
    for value in records:
        if value.startswith("http://") or value.startswith("https://"):
            return value
    return None


def discover_seeds(
    candidate_domains: tuple[str, ...] = (),
    resolver: Resolver | None = None,
) -> list[str]:
    """Return an ordered, de-duplicated list of well-known URLs to try.

    Ordering:
      1. Hard-coded ``SEED_DOMAINS`` (always first -- the lifeboat).
      2. For each ``candidate_domain``: TXT record hint, then SRV record
         hint. TXT wins over SRV when both are present for the same domain.

    ``candidate_domains`` is typically a list of domains a server has
    heard about via out-of-band means (last-known-good peer cache,
    operator configuration). Empty by default.
    """
    resolver = resolver or _default_resolver()
    urls: list[str] = []
    seen: set[str] = set()

    def _add(url: str | None) -> None:
        if url and url not in seen:
            urls.append(url)
            seen.add(url)

    for d in SEED_DOMAINS:
        _add(f"https://{d}/.well-known/jtf.json")

    for d in candidate_domains:
        txt = lookup_txt_seed(d, resolver=resolver)
        if txt:
            _add(txt)
            continue
        srv = lookup_srv_seed(d, resolver=resolver)
        _add(srv)

    return urls
