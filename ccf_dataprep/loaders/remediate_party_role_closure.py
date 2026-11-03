#!/usr/bin/env python3
"""Assert the missing Commons party-chain types on nodes that imply them.

See docs/known-issues.md §62. Measured 2026-10-09: 315 nodes typed
`cmns-org:LegalEntity` were not typed `cmns-pts:Party`, so a `Party` query,
the one a consumer asks for "everyone connected to X", silently skipped
them. Fluree runs no reasoner (rule 7), so an unasserted ancestor is an
absent one.

    ICJ-SPV-* (150), ICJ-INT-* (40), RSSD-* (3)   stopped at LegalEntity
    HLD-* (119), Cyc* cycle nodes (3)             stopped at LegalPerson

**Additive only.** Each triple written is an ancestor of a type the node already
carries, per the published FIBO/Commons hierarchy (`ccf/party_roles.py`). No
type is retracted, and no node gains a role its existing types do not already
entail. Callers' queries are unchanged; they simply stop missing rows.

The four source loaders now emit the full chain via
`ccf.party_roles.with_ancestors`, so a reload produces the same state this
leaves behind.

    uv run loaders/remediate_party_role_closure.py --dry-run
    uv run loaders/remediate_party_role_closure.py
    uv run validators/party_role_closure.py

Idempotent: a second run finds no gaps and writes nothing.
"""

from __future__ import annotations

import argparse
import collections
import sys

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2
from ccf.party_roles import chain_type_map, closure_gaps

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
BATCH = 400


def short(iri: str) -> str:
    return iri.rsplit("/", 1)[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="report the gaps without writing")
    args = parser.parse_args()

    gaps = closure_gaps(chain_type_map(fluree.query))
    triples = sorted(f"<{s}> <{RDF_TYPE}> <{t}> ."
                     for s, missing in gaps.items() for t in missing)

    by_class = collections.Counter(t for m in gaps.values() for t in m)
    print(f"ledger {FLUREE_LEDGER_V2}: {len(gaps)} nodes missing "
          f"{len(triples)} chain types")
    for cls, n in sorted(by_class.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>5}  + {short(cls)}")

    if not triples:
        print("nothing to do")
        return 0
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    remaining = closure_gaps(chain_type_map(fluree.query))
    if remaining:
        print(f"ERROR: {len(remaining)} nodes still have gaps after the write")
        return 1
    print(f"wrote {len(triples)} triples; 0 gaps remain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
