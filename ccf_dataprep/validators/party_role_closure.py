#!/usr/bin/env python3
"""Every node typed with a party-chain class carries all of its ancestors.

Fluree runs no reasoner, so a node typed `LegalEntity` but not `Party` is
invisible to a `Party` query — a silent short answer, not an error. This
recomputes the closure from the ledger on every run (reading no stored flag)
and fails on any gap. See known-issues §62.

    uv run validators/party_role_closure.py
"""

from __future__ import annotations

import collections
import sys

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2
from ccf.party_roles import C_PARTY, chain_type_map, closure_gaps


def main() -> int:
    type_map = chain_type_map(fluree.query)
    gaps = closure_gaps(type_map)
    parties = sum(1 for ts in type_map.values() if C_PARTY in ts)
    print(f"ledger {FLUREE_LEDGER_V2}: {len(type_map)} chain-typed nodes, "
          f"{parties} typed Party")
    if not gaps:
        print("PASS  every chain-typed node carries all of its ancestors")
        return 0
    by_prefix = collections.Counter(
        s.rsplit("/", 1)[-1].split("-")[0] for s in gaps)
    print(f"FAIL  {len(gaps)} nodes are missing chain ancestors: "
          f"{dict(by_prefix.most_common(8))}")
    for s, m in sorted(gaps.items())[:10]:
        print(f"      {s}  missing {sorted(t.rsplit('/', 1)[-1] for t in m)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
