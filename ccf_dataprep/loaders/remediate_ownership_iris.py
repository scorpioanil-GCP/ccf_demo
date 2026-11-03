#!/usr/bin/env python3
"""Wave 8 — retract the invalid ownership/control predicates from `fibo-v2`.

See docs/known-issues.md §0.1. Through Wave 7 the ownership graph was loaded
against two predicates that do not exist in FIBO:

    BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn
    BE/OwnershipAndControl/Control/hasControllingInterestIn

Neither property exists; neither module resolves. `load_fluree_wave3.py` now
emits the confirmed replacements (`FND/OwnershipAndControl/Ownership/owns` and
`FND/Relations/Relations/controls`), but it is **INSERT DATA only** -- re-running
it alone would leave the old edges in place and double the graph to 1,130 edges.

So this runs first and retracts:

    1. every edge asserted with either invalid predicate
    2. the T-Box declarations of those two properties (type, label)
    3. the invented `control subPropertyOf ownership` axiom
    4. every type assertion on the five invalid starter CLASS IRIs (§0.2), their
       T-Box declarations, and the invented single-line subclass chain

Item 4 is what makes the re-typing a correction rather than an addition. FIBO
moved its foundational vocabulary to OMG Commons, so `Agent`, `Party`,
`LegalEntity`, and `FormalOrganization` are not FIBO terms and `Corporation`
moved inside FIBO. Reloading without retracting would leave every entity
carrying both the old types and the new ones.

Fluree is append-only (§5.3): a retraction changes *current state* and both the
assertion and the retraction remain in history. That is the intended property --
the wrong write stays auditable, it just stops being current. It also means this
cannot be undone, hence --dry-run and an explicit confirmation.

Order:
    uv run loaders/remediate_ownership_iris.py --dry-run
    uv run loaders/remediate_ownership_iris.py
    uv run loaders/load_fluree_wave3.py
    uv run validators/partition.py && uv run validators/conditions.py

Idempotent: re-running after a successful pass finds nothing to retract.
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

#: The two predicates being retired. Confirmed absent from FIBO across all 295
#: Production modules and against the live endpoint.
OLD_OWNS = f"{FIBO}BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn"
OLD_CONTROLS = f"{FIBO}BE/OwnershipAndControl/Control/hasControllingInterestIn"

#: Wave 8 part 2 (§0.2). The five starter CLASS IRIs, none of which exist:
#: four relocated to OMG Commons, one moved inside FIBO. Retracting these is
#: what makes the re-typing a correction rather than an addition -- without it
#: the reload would leave every entity carrying both the old and new types.
OLD_CLASSES = [
    f"{FIBO}FND/AgentsAndPeople/Agents/Agent",
    f"{FIBO}FND/Parties/Parties/Party",
    f"{FIBO}BE/LegalEntities/LegalPersons/LegalEntity",
    f"{FIBO}BE/LegalEntities/FormalBusinessOrganizations/FormalOrganization",
    f"{FIBO}BE/Corporations/Corporations/Corporation",
]

#: The invented single-line chain. The real hierarchy is wider and inverts one
#: link, so these axioms are wrong in shape as well as in IRI.
OLD_CHAIN = [
    (f"{FIBO}FND/Parties/Parties/Party", f"{FIBO}FND/AgentsAndPeople/Agents/Agent"),
    (f"{FIBO}BE/LegalEntities/LegalPersons/LegalEntity", f"{FIBO}FND/Parties/Parties/Party"),
    (f"{FIBO}BE/LegalEntities/FormalBusinessOrganizations/FormalOrganization",
     f"{FIBO}BE/LegalEntities/LegalPersons/LegalEntity"),
    (f"{FIBO}BE/Corporations/Corporations/Corporation",
     f"{FIBO}BE/LegalEntities/FormalBusinessOrganizations/FormalOrganization"),
]

#: (old_predicate, new_predicate, why) -- both IRIs valid; the MEANING moved.
#: GLEIF's ultimate parent is the ultimate accounting consolidating parent, a
#: global concept, not "control". Retracted only where the old edge set is a
#: subset of the new one, so genuine control edges are never swept up.
RE_PREDICATED = [
    (f"{FIBO}FND/Relations/Relations/controls",
     f"{FIBO}BE/OwnershipAndControl/CorporateControl/hasGlobalUltimateParent",
     "GLEIF ultimate parent is not control"),
]

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_SUBPROP = "http://www.w3.org/2000/01/rdf-schema#subPropertyOf"
OWL_OBJPROP = "http://www.w3.org/2002/07/owl#ObjectProperty"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
RDFS_SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"

BATCH = 200


def edges_for(predicate: str) -> list[tuple[str, str]]:
    """Every (subject, object) pair currently asserted with `predicate`."""
    sparql = (
        f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{predicate}> ?o }}"
    )
    result = fluree.query(sparql)
    return [
        (b["s"]["value"], b["o"]["value"])
        for b in result.get("results", {}).get("bindings", [])
    ]


def typed_as(cls_iri: str) -> list[str]:
    """Every subject currently typed with `cls_iri`."""
    sparql = (f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> "
              f"WHERE {{ ?s <{RDF_TYPE}> <{cls_iri}> }}")
    result = fluree.query(sparql)
    return [b["s"]["value"] for b in result.get("results", {}).get("bindings", [])]


def tbox_triples_for(predicate: str) -> list[str]:
    """T-Box statements this loader wrote about the retired property."""
    local = predicate.rsplit("/", 1)[-1]
    return [
        f"<{predicate}> <{RDF_TYPE}> <{OWL_OBJPROP}> .",
        f'<{predicate}> <{RDFS_LABEL}> "{local}" .',
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"Wave 8 remediation — retract invalid predicates from {FLUREE_LEDGER_V2}\n")

    statements: list[str] = []
    total_edges = 0
    for label, predicate in (("ownership", OLD_OWNS), ("control", OLD_CONTROLS)):
        pairs = edges_for(predicate)
        total_edges += len(pairs)
        print(f"  {label:<10} {len(pairs):>5} edges on {predicate.rsplit('/', 2)[-2]}/"
              f"{predicate.rsplit('/', 1)[-1]}")
        statements += [f"<{s}> <{predicate}> <{o}> ." for s, o in pairs]
        statements += tbox_triples_for(predicate)

    # The invented axiom: control subPropertyOf ownership. FIBO makes the two
    # siblings under playsActiveRoleThatDirectlyAffects, never sub/super.
    statements.append(f"<{OLD_CONTROLS}> <{RDFS_SUBPROP}> <{OLD_OWNS}> .")

    # --- part 2: the five invalid starter CLASS IRIs (§0.2) ----------------
    total_types = 0
    for cls in OLD_CLASSES:
        subjects = typed_as(cls)
        total_types += len(subjects)
        short = cls.rsplit("/", 1)[-1]
        print(f"  {short:<20} {len(subjects):>5} type assertions")
        statements += [f"<{s}> <{RDF_TYPE}> <{cls}> ." for s in subjects]
        statements += [
            f"<{cls}> <{RDF_TYPE}> <{OWL_CLASS}> .",
            f'<{cls}> <{RDFS_LABEL}> "{short}" .',
        ]
    for sub, sup in OLD_CHAIN:
        statements.append(f"<{sub}> <{RDFS_SUBCLASS}> <{sup}> .")
    print(f"\n  {total_types} type assertions on invalid class IRIs")

    # --- part 3: edges whose PREDICATE IS VALID but whose usage changed -----
    # A trap the first two parts miss entirely. `controls` is a real IRI and
    # stays in the T-Box, but the 103 GLEIF ultimate-parent edges asserted with
    # it were re-predicated to hasGlobalUltimateParent. Retracting only invalid
    # IRIs leaves those edges standing, and the reload adds the re-predicated
    # copies beside them -- 103 duplicates wearing two different meanings.
    #
    # Observed for real on 2026-08-17: the reload produced 704 edges where the
    # loader reported 601. Detect by identity, not by assumption: only retract
    # where the old predicate's edge set is a SUBSET of the new one's.
    for old_p, new_p, note in RE_PREDICATED:
        old_pairs, new_pairs = set(edges_for(old_p)), set(edges_for(new_p))
        if not old_pairs:
            continue
        short_o, short_n = old_p.rsplit("/", 1)[-1], new_p.rsplit("/", 1)[-1]
        if old_pairs <= new_pairs:
            print(f"  {short_o:<20} {len(old_pairs):>5} edges re-predicated to "
                  f"{short_n} — retracting ({note})")
            statements += [f"<{s}> <{old_p}> <{o}> ." for s, o in sorted(old_pairs)]
        else:
            print(f"  {short_o:<20} {len(old_pairs - new_pairs):>5} edges NOT in "
                  f"{short_n} — left alone, these are genuine {short_o}")

    print(f"\n  {total_edges} edges + {len(statements) - total_edges} T-Box "
          f"statements = {len(statements)} triples to retract")


    if args.dry_run:
        print("\n  DRY RUN — nothing retracted.")
        print("  Sample:")
        for stmt in statements[:3]:
            print(f"    {stmt}")
        return 0

    print(f"\n  retracting in batches of {BATCH}...")
    for i in range(0, len(statements), BATCH):
        chunk = statements[i:i + BATCH]
        fluree.update("DELETE DATA {\n" + "\n".join(chunk) + "\n}")
        if (i // BATCH) % 5 == 0:
            print(f"    {min(i + BATCH, len(statements)):>6}/{len(statements)}")

    remaining = (sum(len(edges_for(p)) for p in (OLD_OWNS, OLD_CONTROLS))
                 + sum(len(typed_as(c)) for c in OLD_CLASSES))
    t = fluree.ledger_t()
    total = fluree.count_triples()
    print(f"\n  retracted. ledger t={t}, {total:,} triples in current state")
    print(f"  assertions remaining on invalid IRIs: {remaining}")
    if remaining:
        print("  WARNING — retraction incomplete.")
        return 1
    print("\n  Next: uv run loaders/load_fluree_wave3.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
