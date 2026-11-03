#!/usr/bin/env python3
"""Close §0.4 — control WITHOUT ownership, the estate's last outstanding §F gap.

`corporate-family-tree` §F wants at least one edge where a party CONTROLS an
entity it does not OWN. The estate has had zero since Wave 8, when the 103
edges sitting on `controls` were found to be GLEIF ultimate-parent facts and
were moved to `hasGlobalUltimateParent` where they belonged. That correction
was right, and it left a real hole: the product exists partly to surface
control that ownership percentages cannot explain, and there was none.

**Why this must be engineered rather than fetched.** GLEIF Level 2 records
ownership and ultimate-parent relationships. It does not record golden shares,
dual-class voting trusts, or board-appointment rights granted under a credit
agreement — the mechanisms by which control routinely exists without an
economic stake. No public source this project can reach publishes them in
structured form, so the condition cannot arise naturally here. Built
deliberately, labelled `synthetic — engineered`, and recorded as such.

Three control parties, three mechanisms, three real anchor targets:

    Ardsley Golden Share Trust      golden share — veto rights, no economic stake
    Kestrel Founders Voting Trust   dual-class voting control
    Pellworth Facility Agent        board-appointment rights under a credit agreement

Each `controls` a real anchor entity resolved FROM THE LEDGER and owns none of
it. Resolve, never construct: a constructed URI cannot fail loudly, which is
how fifteen phantom borrowers survived four waves.

    uv run loaders/load_control_edges.py --dry-run
    uv run loaders/load_control_edges.py

Idempotent: INSERT DATA of stable triples. Re-running advances `t` and leaves
the triple count unchanged.
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import EX
from loaders.load_collateral_wave9 import entity_uri_by_lei
from loaders.load_fluree_wave3 import (P_CONTROLS, P_OWNS, edge_triples,
                                       entity_triples, local_name, triple, uri)

PROVENANCE = "synthetic — engineered"

#: (party name, control mechanism) — the mechanism is narrative, recorded in
#: the docstring and known-issues rather than as a graph attribute, because
#: Fluree nodes carry label + provenance + lei and nothing else.
CONTROL_PARTIES = [
    ("Ardsley Golden Share Trust", "golden share, veto rights, no economic stake"),
    ("Kestrel Founders Voting Trust", "dual-class voting control"),
    ("Pellworth Facility Agent", "board-appointment rights under a credit agreement"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    entity_uri = entity_uri_by_lei()
    if len(entity_uri) < len(CONTROL_PARTIES):
        print(f"  only {len(entity_uri)} entity nodes resolved — need at least "
              f"{len(CONTROL_PARTIES)}. Run Wave 3 first.")
        return 1

    # Deterministic target selection: first N anchors by LEI. Stable across runs.
    targets = [entity_uri[lei] for lei in sorted(entity_uri)[:len(CONTROL_PARTIES)]]

    triples: list[str] = []
    for (party_name, mechanism), target in zip(CONTROL_PARTIES, targets):
        local = local_name(party_name, prefix="Ctl")
        triples += entity_triples(local, party_name, None, PROVENANCE)
        triples += edge_triples(local, target.rsplit("/", 1)[-1],
                                predicate=P_CONTROLS, provenance=PROVENANCE)
        triples.append(triple(uri(local), f"{EX}edgeProvenance",
                              PROVENANCE, literal=True))
        print(f"  {party_name}  --controls-->  {target.rsplit('/', 1)[-1]}"
              f"   ({mechanism})")

    print(f"\n  {len(triples)} triples · {len(CONTROL_PARTIES)} control-only edges")
    print("  NO owns edge is written for any of these pairs — that is the point.")

    if args.dry_run:
        print("  [dry-run] nothing written to Fluree")
        return 0

    before = fluree.count_triples()
    fluree.update("INSERT DATA {\n" + "\n".join(triples) + "\n}")
    after = fluree.count_triples()
    print(f"  ledger t={fluree.ledger_t()} · triples {before:,} -> {after:,}")

    # Verify what was actually asserted, rather than assuming the write landed.
    rows = fluree.query(f"""
        SELECT (COUNT(*) AS ?n) FROM <{fluree.FLUREE_LEDGER_V2}> WHERE {{
          ?a <{P_CONTROLS}> ?b .
          FILTER NOT EXISTS {{ ?a <{P_OWNS}> ?b }}
        }}""").get("results", {}).get("bindings", [])
    n = int(rows[0]["n"]["value"]) if rows else 0
    print(f"  control-WITHOUT-ownership edges now in the ledger: {n}")
    return 0 if n >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
