#!/usr/bin/env python3
"""Retract Wave 13b Task 5's first Fluree shape, which duplicated attributes.

    uv run loaders/remediate_resolution_shape_wave13b.py --dry-run
    uv run loaders/remediate_resolution_shape_wave13b.py

The first version of `load_resolution_wave13b.py` wrote the name string, its
source registry and its rendering onto Fluree `PersonName` nodes, and the
screening disposition and score onto `Person` nodes. All five are
`person_name_variant` / `sanctions_screening_result` columns, so the graph held
a second copy of attributes Postgres owns.

`validators/partition.py` caught it — "no client-360 attribute in the graph:
hasPersonName on 5+ nodes" — which is precisely the check working. The fix is
the estate's existing cross-store pattern: Fluree carries a **join key**
(`ex:variantId`, exactly as `ex:documentId` reaches a MongoDB passage) and the
edges, and resolves every attribute from Postgres.

**Fluree is append-only, so the old triples do not disappear when the loader
changes.** They stay in the ledger, indistinguishable from live data, and keep
the partition check red — the failure mode `validators/orphan_terms.py` exists
for. This script retracts them explicitly.

What is retracted:

    every triple whose subject is an `ex:PN-####` node   (the old name nodes)
    ex:nameSource, ex:nameRendering, ex:screeningDisposition  (everywhere)
    ex:resolutionConfidence on `ex:PSC-####` person nodes  (kept on RES- nodes)
    rdfs:label on `ex:OFAC-*` nodes                        (the listed name)
    rdfs:label on `ex:RES-####` nodes                      (the name-bearing
                                                            label, replaced by
                                                            a key-bearing one)

Read-then-delete: every statement is fetched from the ledger first, so nothing
is retracted that is not actually there.
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2

RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
BATCH = 500

DOOMED_PREDICATES = [f"{EX}nameSource", f"{EX}nameRendering",
                     f"{EX}screeningDisposition"]


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def stmt(s: str, p: str, o: str, is_literal: bool) -> str:
    obj = f'"{esc(o)}"' if is_literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def rows(sparql: str) -> list[dict]:
    return fluree.query(sparql)["results"]["bindings"]


def collect() -> list[str]:
    out: list[str] = []

    # 1 — everything asserted on, or pointing at, the old PN- name nodes.
    for b in rows(f"""SELECT ?s ?p ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{
            ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "{EX}PN-")) }}"""):
        out.append(stmt(b["s"]["value"], b["p"]["value"], b["o"]["value"],
                        b["o"]["type"] == "literal"))
    for b in rows(f"""SELECT ?s ?p ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{
            ?s ?p ?o . FILTER(STRSTARTS(STR(?o), "{EX}PN-")) }}"""):
        out.append(stmt(b["s"]["value"], b["p"]["value"], b["o"]["value"], False))

    # 2 — predicates that carried a duplicated attribute, wherever they sit.
    for pred in DOOMED_PREDICATES:
        for b in rows(f"""SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{
                ?s <{pred}> ?o }}"""):
            out.append(stmt(b["s"]["value"], pred, b["o"]["value"],
                            b["o"]["type"] == "literal"))

    # 3 — confidence on PERSON nodes. It belongs on the resolution node, which
    #     is a Fluree-owned concept with no Postgres row, not on the person.
    for b in rows(f"""SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{
            ?s <{EX}resolutionConfidence> ?o .
            FILTER(STRSTARTS(STR(?s), "{EX}PSC-")) }}"""):
        out.append(stmt(b["s"]["value"], f"{EX}resolutionConfidence",
                        b["o"]["value"], True))

    # 4 — labels that copied a name out of Postgres.
    for prefix in (f"{EX}OFAC-", f"{EX}RES-"):
        for b in rows(f"""SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{
                ?s <{RDFS_LABEL}> ?o . FILTER(STRSTARTS(STR(?s), "{prefix}")) }}"""):
            out.append(stmt(b["s"]["value"], RDFS_LABEL, b["o"]["value"], True))

    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    statements = collect()
    print(f"Wave 13b Task 5 — retract the duplicated-attribute shape\n")
    print(f"  statements found in the ledger: {len(statements)}")
    for s in statements[:5]:
        print(f"    {s[:118]}")
    if len(statements) > 5:
        print(f"    … {len(statements) - 5} more")

    if not statements:
        print("\n  nothing to retract — already clean")
        return 0

    if args.dry_run:
        print("\n  [dry-run] nothing retracted")
        return 0

    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")

    left = len(collect())
    print(f"\n  retracted {len(statements)}; {left} remaining")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
