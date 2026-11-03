#!/usr/bin/env python3
"""Wave 10 fix — retract the two mistyped Person nodes from `fibo-v2`.

`generators/form4.py::owner_kind` classified on the trailing token of the
filed name only. Two legal entities sailed past it because their real entity
marker was not the last token:

    CHARTER COMMUNICATIONS, INC. /MO/   trailing token: "/MO/" (EDGAR's
                                         state-of-incorporation suffix)
    ESS Holdings Business Trust I       trailing token: "I"

Both loaded as `fibo-fnd-aap-ppl:Person` nodes in `load_fluree_wave10.py`'s
first run. `owner_kind` now scans every token (and strips the `/XX/` marker
first), so a corrected `load_postgres_wave10.py` / `load_fluree_wave10.py`
run no longer produces these two nodes at all -- but Fluree is append-only, so
the WRONG nodes already committed do not go away on their own. A plain
reload only adds the corrected graph beside them.

So this runs first and retracts, for each of the two person_key URIs:

    1. its rdf:type Person assertion
    2. its rdfs:label
    3. every outgoing edge (isEmployedBy / isOfficerOf / isDirectorOf /
       participatedIn) -- whichever the node actually carries
    4. (defensive) any edge that points AT the node, in case a future wave
       adds a predicate where a person is an object rather than a subject

Confirmed by direct query before writing this script: neither node is ever
an object today, and Charter carries one isEmployedBy + one participatedIn,
ESS carries neither -- 2 type + 2 label + 1 isEmployedBy + 1 participatedIn
= 6 triples in current state.

Order:
    uv run loaders/remediate_person_owner_kind.py --dry-run
    uv run loaders/remediate_person_owner_kind.py
    uv run loaders/load_fluree_wave10.py

Idempotent: re-running after a successful pass finds nothing to retract.
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

#: The two reporting-owner CIKs that `owner_kind` mistyped as natural persons.
#: See generators/form4.py and validators/test_form4.py for the fix and its
#: pinned regression cases.
WRONG_PERSON_KEYS = ["0001091667", "0001859988"]

BATCH = 50


def node_uri(person_key: str) -> str:
    return f"{EX}person-{person_key}"


def triples_where_subject(node: str) -> list[str]:
    q = f"SELECT ?p ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ <{node}> ?p ?o }}"
    result = fluree.query(q)
    out = []
    for b in result.get("results", {}).get("bindings", []):
        p, o = b["p"]["value"], b["o"]["value"]
        obj = f'"{o}"' if b["o"]["type"] == "literal" else f"<{o}>"
        out.append(f"<{node}> <{p}> {obj} .")
    return out


def triples_where_object(node: str) -> list[str]:
    q = f"SELECT ?s ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s ?p <{node}> }}"
    result = fluree.query(q)
    return [f'<{b["s"]["value"]}> <{b["p"]["value"]}> <{node}> .'
            for b in result.get("results", {}).get("bindings", [])]


def any_triples(node: str) -> bool:
    """True if `node` is still referenced as subject, object, or type."""
    q = (f"SELECT (COUNT(*) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
         f"WHERE {{ {{ <{node}> ?p1 ?o1 }} UNION {{ ?s1 ?p2 <{node}> }} }}")
    result = fluree.query(q)
    rows = result.get("results", {}).get("bindings", [])
    return bool(rows) and int(rows[0]["n"]["value"]) > 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"Wave 10 fix — retract mistyped Person nodes from {FLUREE_LEDGER_V2}\n")

    statements: list[str] = []
    for key in WRONG_PERSON_KEYS:
        node = node_uri(key)
        out_triples = triples_where_subject(node)
        in_triples = triples_where_object(node)
        print(f"  {node}")
        for t in out_triples:
            print(f"    - {t}")
        for t in in_triples:
            print(f"    - {t}  (incoming)")
        if not out_triples and not in_triples:
            print("    (nothing found -- already retracted)")
        statements += out_triples + in_triples

    print(f"\n  {len(statements)} triples to retract")

    if args.dry_run:
        print("\n  DRY RUN — nothing retracted.")
        return 0

    if not statements:
        print("\n  nothing to do.")
        return 0

    print(f"\n  retracting in batches of {BATCH}...")
    for i in range(0, len(statements), BATCH):
        chunk = statements[i:i + BATCH]
        fluree.update("DELETE DATA {\n" + "\n".join(chunk) + "\n}")

    remaining = sum(any_triples(node_uri(k)) for k in WRONG_PERSON_KEYS)
    t = fluree.ledger_t()
    total = fluree.count_triples()
    print(f"\n  retracted. ledger t={t}, {total:,} triples in current state")
    print(f"  nodes still referenced: {remaining}")
    if remaining:
        print("  WARNING — retraction incomplete.")
        return 1
    print("\n  Next: uv run loaders/load_fluree_wave10.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
