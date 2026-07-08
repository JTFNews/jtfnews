"""JTF Protocol seed domain list and DNS discovery fallback.

Servers use this module on first startup to find at least one other
server. Once a server has exchanged peer lists with two others, it no
longer needs seeds. The seed list is a lifeboat, not a chain of command.

See documentation/Protocol Ver 1.0 CURRENT.md, sections "Seed Domains"
and "Fallback Discovery".
"""
from __future__ import annotations


SEED_DOMAINS: tuple[str, ...] = (
    "jtfnews.org",
)
"""Hard-coded seed domains. Additional entries are added by editing this
tuple and cutting a new release. The protocol requires a minimum of three
seed domains in different jurisdictions before the network is considered
production-ready."""
