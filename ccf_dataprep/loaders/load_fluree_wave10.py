#!/usr/bin/env python3
"""Wave 10 — the client-360 edges, in Fluree.

Three of the six relationships have a real FIBO property; three do not. Verified
against the Wave 8 binding contract, which bound all ten officer, director and
employment terms:

    employedBy     -> fibo-fnd-org-fm:isEmployedBy      REAL FIBO term
    officer of     -> fibo-be-oac-exec:isOfficerOf      REAL FIBO term
    director of    -> fibo-be-oac-exec:isDirectorOf     REAL FIBO term
    coversClient   -> ex:coversClient                   no FIBO equivalent
    participatedIn -> ex:participatedIn                 no FIBO equivalent
    relatedToDeal  -> ex:relatedToDeal                   no FIBO equivalent

THIRD consecutive wave where FIBO has no vocabulary for the bank's own
operational relations — Covenant in Wave 5, pledgedBy/setOffAgainst/nettedUnder
in Wave 9, coverage and interaction now. That goes to the vault as one pattern.

FIBO has `CorporateOfficer` as a class but NO `Director` class — directorship is
only an edge, and `BoardOfDirectors` is the board, not the person. `ex:Director`
is deliberately NOT minted to make the model look symmetric.

Fluree has no OWL inference, so every node is typed explicitly for every role it
is queried against.

    uv run loaders/load_fluree_wave10.py --dry-run
    uv run loaders/load_fluree_wave10.py

**When Postgres has CHANGED since the last load, use `--reconcile`.** Fluree is
append-only and this loader is INSERT DATA only, so a plain re-load appends the
corrected edges BESIDE the stale ones rather than replacing them. `--reconcile`
retracts every edge on the six predicates this loader owns, then rebuilds:

    uv run loaders/load_fluree_wave10.py --reconcile --dry-run
    uv run loaders/load_fluree_wave10.py --reconcile

This replaces the one-off `remediate_wave10_interaction_edges.py`, which did the
same retraction for two predicates and had to be run in a specific, undocumented
order relative to two reloads. Retract-and-rebuild belongs inside the loader that
owns the edges, not beside it.
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, pg_connect
from loaders.load_collateral_wave9 import entity_uri_by_lei, triple, uri

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

C_PERSON = f"{FIBO}FND/AgentsAndPeople/People/Person"
C_OFFICER = f"{FIBO}BE/OwnershipAndControl/Executives/CorporateOfficer"
P_EMPLOYED_BY = f"{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy"
P_OFFICER_OF = f"{FIBO}BE/OwnershipAndControl/Executives/isOfficerOf"
P_DIRECTOR_OF = f"{FIBO}BE/OwnershipAndControl/Executives/isDirectorOf"

C_BANKER = f"{EX}Banker"
C_INTERACTION = f"{EX}Interaction"
C_DEAL = f"{EX}Deal"
P_COVERS_CLIENT = f"{EX}coversClient"
P_PARTICIPATED_IN = f"{EX}participatedIn"
P_RELATED_TO_DEAL = f"{EX}relatedToDeal"

BATCH = 500

#: The six edge predicates this loader is the sole author of. `--reconcile`
#: retracts every edge on these before rebuilding, which is what makes a
#: RE-load correct rather than merely additive.
OWNED_PREDICATES = {
    "isEmployedBy": P_EMPLOYED_BY,
    "isOfficerOf": P_OFFICER_OF,
    "isDirectorOf": P_DIRECTOR_OF,
    "coversClient": P_COVERS_CLIENT,
    "participatedIn": P_PARTICIPATED_IN,
    "relatedToDeal": P_RELATED_TO_DEAL,
}


def _asserted_edges(predicate: str) -> list[tuple[str, str]]:
    q = f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{predicate}> ?o }}"
    return [(b["s"]["value"], b["o"]["value"])
            for b in fluree.query(q).get("results", {}).get("bindings", [])]


def reconcile(*, dry_run: bool) -> int:
    """Retract every edge on the predicates this loader owns.

    Fluree is append-only and this loader is INSERT DATA only, so a plain
    re-load against CHANGED Postgres state appends the corrected edges BESIDE
    the stale ones rather than replacing them. That is exactly what happened
    on 2026-08-18: `generate_coverage.py` draws from one seeded rng stream, so
    removing two mistyped people from the eligible pool shifted every draw
    downstream — including which interactions carry a `deal_id` — and Fluree
    kept both versions.

    Retracting all six predicates wholesale, rather than computing which
    subset drifted, is deliberate: this loader is their sole author, so
    "retract everything and rebuild" is provably complete, whereas a computed
    subset is only as good as the reasoning behind it. That reasoning is what
    was wrong the first time.

    NODES are deliberately out of scope. A node that should no longer exist —
    a person reclassified as an entity, say — is a rarer and more dangerous
    retraction, and `loaders/remediate_person_owner_kind.py` handled that case
    with explicit keys. Edge lifecycle and node lifecycle are different
    problems and this flag solves only the first.
    """
    total = 0
    statements: list[str] = []
    for name, pred in OWNED_PREDICATES.items():
        pairs = _asserted_edges(pred)
        print(f"    {name:<15} {len(pairs):>5} asserted")
        statements += [f"<{s}> <{pred}> <{o}> ." for s, o in pairs]
        total += len(pairs)

    if not statements:
        print("    nothing asserted — nothing to retract")
        return 0
    print(f"    {total} edges to retract")
    if dry_run:
        print("    [dry-run] nothing retracted")
        return 0

    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")

    remaining = sum(len(_asserted_edges(p)) for p in OWNED_PREDICATES.values())
    print(f"    retracted · edges remaining on these predicates: {remaining}")
    if remaining:
        print("    WARNING — retraction incomplete; not proceeding to the rebuild.")
    return remaining


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="retract every edge this loader owns before rebuilding. "
                         "Required when Postgres has CHANGED since the last load — "
                         "without it a re-load appends beside the stale edges "
                         "rather than replacing them, because Fluree is append-only.")
    args = ap.parse_args()

    if args.reconcile:
        print("  --reconcile: retracting this loader's edges before rebuild")
        if reconcile(dry_run=args.dry_run):
            return 1

    entity_uri = entity_uri_by_lei()
    print(f"  resolved {len(entity_uri)} entity nodes from the ledger")

    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT person_key, display_name FROM "{S}".person '
                    "WHERE owner_kind = 'natural'")
        people = cur.fetchall()
        cur.execute(f'SELECT person_key, lei, role FROM "{S}".person_role r '
                    f'WHERE EXISTS (SELECT 1 FROM "{S}".person p '
                    "WHERE p.person_key = r.person_key AND p.owner_kind = 'natural')")
        roles = cur.fetchall()
        cur.execute(f'SELECT banker_id, full_name FROM "{S}".banker')
        bankers = cur.fetchall()
        cur.execute(f'SELECT banker_id, lei FROM "{S}".coverage_assignment')
        assignments = cur.fetchall()
        cur.execute(f'SELECT interaction_id, deal_id FROM "{S}".interaction')
        interactions = cur.fetchall()
        cur.execute(f'SELECT deal_id FROM "{S}".deal')
        deals = [r[0] for r in cur.fetchall()]
        cur.execute(f'SELECT interaction_id, party_kind, party_key '
                    f'FROM "{S}".interaction_participant')
        participants = cur.fetchall()

    triples: list[str] = []

    for cls in (C_BANKER, C_INTERACTION, C_DEAL):
        triples.append(triple(cls, RDF_TYPE, "http://www.w3.org/2002/07/owl#Class"))
        triples.append(triple(cls, RDFS_LABEL, cls.rsplit("/", 1)[-1], literal=True))

    person_uri = {}
    for person_key, display_name in people:
        node = uri(f"person-{person_key}")
        person_uri[person_key] = node
        triples.append(triple(node, RDF_TYPE, C_PERSON))
        triples.append(triple(node, RDFS_LABEL, display_name, literal=True))

    officers = {k for k, _, role in roles if role == "officer"}
    for person_key in officers & person_uri.keys():
        triples.append(triple(person_uri[person_key], RDF_TYPE, C_OFFICER))

    banker_uri = {}
    for banker_id, full_name in bankers:
        node = uri(f"banker-{banker_id}")
        banker_uri[banker_id] = node
        triples.append(triple(node, RDF_TYPE, C_BANKER))
        triples.append(triple(node, RDFS_LABEL, full_name, literal=True))

    interaction_uri = {}
    for interaction_id, _ in interactions:
        node = uri(f"interaction-{interaction_id}")
        interaction_uri[interaction_id] = node
        triples.append(triple(node, RDF_TYPE, C_INTERACTION))
        triples.append(triple(node, RDFS_LABEL, interaction_id, literal=True))

    deal_uri = {}
    for deal_id in deals:
        node = uri(f"deal-{deal_id}")
        deal_uri[deal_id] = node
        triples.append(triple(node, RDF_TYPE, C_DEAL))
        triples.append(triple(node, RDFS_LABEL, deal_id, literal=True))

    # ---- edges. Every target is resolved, never constructed. -----------------
    dangling = 0
    for person_key, lei, role in roles:
        subject = person_uri.get(person_key)
        target = entity_uri.get(lei)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_EMPLOYED_BY, target))
        if role == "officer":
            triples.append(triple(subject, P_OFFICER_OF, target))
        elif role == "director":
            triples.append(triple(subject, P_DIRECTOR_OF, target))

    for banker_id, lei in assignments:
        subject, target = banker_uri.get(banker_id), entity_uri.get(lei)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_COVERS_CLIENT, target))

    for interaction_id, party_kind, party_key in participants:
        target = interaction_uri.get(interaction_id)
        subject = (person_uri if party_kind == "person" else banker_uri).get(party_key)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_PARTICIPATED_IN, target))

    for interaction_id, deal_id in interactions:
        if not deal_id:
            continue
        subject, target = interaction_uri.get(interaction_id), deal_uri.get(deal_id)
        if subject is None or target is None:
            dangling += 1
            continue
        triples.append(triple(subject, P_RELATED_TO_DEAL, target))

    print(f"  {len(triples)} triples · {dangling} skipped for an unresolved endpoint")
    if dangling:
        print("  NOTE: skipped rather than pointed at a constructed URI. "
              "A constructed URI cannot fail loudly — see Wave 9.")

    if args.dry_run:
        print("  [dry-run] nothing written to Fluree")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
