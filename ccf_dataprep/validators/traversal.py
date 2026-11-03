#!/usr/bin/env python3
"""§F: >= 1 client whose depth-2 traversal exceeds `limit=200`.

This condition CANNOT be established by counting. §D step 3 requires the limit
be applied INSIDE the traversal, ordered by recency — "fetching 5,000 nodes and
truncating to 200 in memory satisfies the contract and defeats its purpose". So
the proof has to be an actual bounded traversal.

Depth 1 from the client entity reaches people (isEmployedBy, inverse) and
bankers (coversClient, inverse). Depth 2 reaches the interactions those parties
participated in. The node set is the union.

    uv run validators/traversal.py
"""

from __future__ import annotations

import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, pg_connect

LIMIT = 200
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"


def depth2_nodes(entity_uri: str) -> set[str]:
    """Every node reachable within two hops of one client entity."""
    sparql = f"""
    SELECT DISTINCT ?node FROM <{FLUREE_LEDGER_V2}> WHERE {{
      {{ ?node <{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy>
               <{entity_uri}> }}
      UNION
      {{ ?node <{EX}coversClient> <{entity_uri}> }}
      UNION
      {{ ?party <{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy>
                <{entity_uri}> .
         ?party <{EX}participatedIn> ?node }}
      UNION
      {{ ?party <{EX}coversClient> <{entity_uri}> .
         ?party <{EX}participatedIn> ?node }}
    }}
    """
    rows = fluree.query(sparql).get("results", {}).get("bindings", [])
    return {r["node"]["value"] for r in rows}


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, count(*) AS n FROM "{PG_SCHEMA_V2}".interaction '
                    "GROUP BY lei ORDER BY n DESC LIMIT 5")
        candidates = cur.fetchall()

    from loaders.load_collateral_wave9 import entity_uri_by_lei
    entity_uri = entity_uri_by_lei()

    print(f"\n  DEPTH-2 TRAVERSAL vs limit={LIMIT}\n")
    exceeded = []
    for lei, interaction_count in candidates:
        node = entity_uri.get(lei)
        if node is None:
            print(f"  [skip] {lei}: no entity node in the ledger")
            continue
        nodes = depth2_nodes(node)
        over = len(nodes) > LIMIT
        exceeded.append(lei) if over else None
        print(f"  [{'ok  ' if over else '    '}] {lei}: {len(nodes):>4} nodes at "
              f"depth 2  ({interaction_count} interactions)")

    ok = len(exceeded) >= 1
    print(f"\n  {len(exceeded)} client(s) exceed limit={LIMIT} — §F wants >= 1: "
          f"{'PASS' if ok else 'FAIL'}\n")
    if not ok:
        print("  Truncation disclosure is unexercised. Raise the dense anchor's "
              "share in generate_coverage.py; do NOT lower the limit.\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
