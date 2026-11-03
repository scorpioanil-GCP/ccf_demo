#!/usr/bin/env python3
"""Create and verify the v2 Fluree ledger.

`fibo-v2` is a **separate ledger**, not a branch of v1's `fibo`. Fluree
aliases are `name:branch`, so the originally-planned "fibo:v2" would have
created a *branch of the v1 ledger* rather than an isolated store. A distinct
name removes the possibility entirely.

This is deliberately conservative about writes: Fluree is append-only, so a
transaction against the wrong ledger cannot be undone — only superseded by a
retraction that stays in history forever.

Idempotent: creating an existing ledger is a no-op.

    uv run loaders/init_fluree.py            # create if absent, then verify
    uv run loaders/init_fluree.py --verify   # verify only, no writes
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V1, FLUREE_LEDGER_V2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true",
                        help="report state without creating anything")
    args = parser.parse_args()

    print(f"Fluree at {fluree.FLUREE_URL}")
    ledgers = fluree.list_ledgers()
    print(f"  ledgers present: {[l['name'] for l in ledgers]}")

    v1_name = FLUREE_LEDGER_V1.split(":")[0]
    v1 = next((l for l in ledgers if l["name"] == v1_name), None)
    if v1:
        print(f"  v1 '{v1['name']}:{v1['branch']}' at t={v1['t']}  (read-only)")

    exists = any(l["name"] == FLUREE_LEDGER_V2 for l in ledgers)

    if not exists:
        if args.verify:
            print(f"\n  v2 ledger '{FLUREE_LEDGER_V2}' does NOT exist")
            return 1
        print(f"\n  creating '{FLUREE_LEDGER_V2}'...")
        result = fluree.create_ledger(FLUREE_LEDGER_V2)
        print(f"    created: {result.get('ledger_id')} at t={result.get('t')}")
    else:
        print(f"\n  v2 ledger '{FLUREE_LEDGER_V2}' already exists")

    t = fluree.ledger_t()
    triples = fluree.count_triples()
    print(f"  v2 state: t={t}, {triples} triples in current state")

    types = fluree.types_present()
    if types:
        print("  types present:")
        for iri, n in types[:10]:
            print(f"    {n:>5}  {iri}")
    else:
        print("  no typed subjects yet — ontology loads in Wave 3")

    # Re-assert isolation after every run: v1 must be untouched.
    if v1:
        after = next(
            (l for l in fluree.list_ledgers() if l["name"] == v1_name), None
        )
        if after and after["t"] != v1["t"]:
            print(f"\n  ERROR: v1 ledger t changed {v1['t']} -> {after['t']}")
            return 1
        print(f"  v1 unchanged at t={v1['t']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
