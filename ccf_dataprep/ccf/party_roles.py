"""The Commons party chain, and its closure — the one place loaders get it from.

Fluree applies no inference (CLAUDE.md rule 7), so a node typed only
`cmns-org:LegalEntity` is NOT returned by a query for `cmns-pts:Party`, even
though the ontology says every LegalEntity is one. Every role a query will ask
for has to be asserted on the node itself.

Until this module existed, each loader kept its own hand-written tuple of
role types, and three of five stopped short of the top of the chain. 315
entities (offshore vehicles, intermediaries, holdcos, two RSSD banks) were
unreachable by `Party` and `Agent` — measured 2026-10-09, known-issues §62.
A loader that calls `with_ancestors()` cannot drift that way: it names the
most specific class it means, and the chain supplies the rest.

The chain is verified against `sources/fibo/dev.fibo-quickstart.ttl`:

    SpecialPurposeVehicle ⊑ LegalEntity        (FIBO BE/LegalEntities/LegalPersons)
    Corporation           ⊑ LegalEntity        (FIBO BE/LegalEntities/CorporateBodies)
    LegalEntity           ⊑ FormalOrganization, LegalPerson
    FormalOrganization    ⊑ Organization
    Organization          ⊑ Party
    LegalPerson           ⊑ Party
    Party                 ⊑ Agent

Only these named superclasses are closed over. Restrictions (`owl:Restriction`)
and role classes such as `cmns-org:ServiceProvider` (an `AgentRole`, not an
organization type) are deliberately outside it.
"""

from __future__ import annotations

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
CMNS = "https://www.omg.org/spec/Commons/"

C_AGENT = f"{CMNS}PartiesAndSituations/Agent"
C_PARTY = f"{CMNS}PartiesAndSituations/Party"
C_ORGANIZATION = f"{CMNS}Organizations/Organization"
C_FORMAL_ORG = f"{CMNS}Organizations/FormalOrganization"
C_LEGAL_PERSON = f"{CMNS}Organizations/LegalPerson"
C_LEGAL_ENTITY = f"{CMNS}Organizations/LegalEntity"
C_CORPORATION = f"{FIBO}BE/LegalEntities/CorporateBodies/Corporation"
C_SPV = f"{FIBO}BE/LegalEntities/LegalPersons/SpecialPurposeVehicle"

#: (subclass, superclass), exactly as published. LegalEntity has TWO parents.
SUPERCLASSES: dict[str, tuple[str, ...]] = {
    C_SPV: (C_LEGAL_ENTITY,),
    C_CORPORATION: (C_LEGAL_ENTITY,),
    C_LEGAL_ENTITY: (C_FORMAL_ORG, C_LEGAL_PERSON),
    C_FORMAL_ORG: (C_ORGANIZATION,),
    C_ORGANIZATION: (C_PARTY,),
    C_LEGAL_PERSON: (C_PARTY,),
    C_PARTY: (C_AGENT,),
    C_AGENT: (),
}

#: Every class the closure knows about. A node typed with any of these must
#: carry all of that class's ancestors.
CHAIN_CLASSES = frozenset(SUPERCLASSES)


def ancestors(cls: str) -> frozenset[str]:
    """Every superclass of `cls` in the chain, transitively, excluding itself.

    A class outside the chain has no ancestors here — it is not this module's
    to close over.
    """
    seen: set[str] = set()
    stack = list(SUPERCLASSES.get(cls, ()))
    while stack:
        sup = stack.pop()
        if sup not in seen:
            seen.add(sup)
            stack.extend(SUPERCLASSES.get(sup, ()))
    return frozenset(seen)


def with_ancestors(*classes: str) -> tuple[str, ...]:
    """`classes` plus every chain ancestor, de-duplicated, in a stable order.

    Order: the classes as given, then ancestors most-specific first, so the
    emitted triples read the same on every run.
    """
    out: list[str] = []
    for c in classes:
        if c not in out:
            out.append(c)
    order = list(SUPERCLASSES)
    extra = set().union(*(ancestors(c) for c in classes)) - set(out)
    out += sorted(extra, key=order.index)
    return tuple(out)


def missing_ancestors(types: set[str]) -> frozenset[str]:
    """The chain ancestors a node with rdf:types `types` is missing."""
    implied = set().union(*(ancestors(t) for t in types if t in CHAIN_CLASSES))
    return frozenset(implied - types)


def chain_type_map(query) -> dict[str, set[str]]:
    """{subject: its chain rdf:types} for every node typed with a chain class.

    `query` is `ccf.fluree.query` (or a test double). One DISTINCT query per
    class rather than a GROUP BY, which invents rows on this Fluree version
    (known-issues §56).
    """
    from ccf.config import FLUREE_LEDGER_V2

    out: dict[str, set[str]] = {}
    for cls in SUPERCLASSES:
        rows = query(
            f"SELECT DISTINCT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s a <{cls}> }}"
        )["results"]["bindings"]
        for b in rows:
            out.setdefault(b["s"]["value"], set()).add(cls)
    return out


def closure_gaps(type_map: dict[str, set[str]]) -> dict[str, frozenset[str]]:
    """{subject: missing ancestors} — empty when every node is closed."""
    gaps = {s: missing_ancestors(ts) for s, ts in type_map.items()}
    return {s: m for s, m in gaps.items() if m}
