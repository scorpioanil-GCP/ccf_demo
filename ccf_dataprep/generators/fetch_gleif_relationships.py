#!/usr/bin/env python3
"""Wave 3 — fetch GLEIF Level 2 relationship records for the anchor cast.

`corporate-family-tree` needs ownership edges deep enough that the `depth`
parameter changes the answer: §F asks for ~800 edges, families of 4-15
entities, and **>= 2 families reaching 4 hops or more**.

GLEIF RR-CDF Level 2 is the public source. It is a clean hierarchy, which is
also its limitation — genuine cross-shareholding cycles are effectively absent
at this scale, which is why §C marks the cycle as `synthetic — engineered`.

This fetch is discovery, not loading: it reports the natural depth available
so the engineering budget is known before anything enters Fluree.

Output: sources/screening/gleif_relationships.json

Run: uv run generators/fetch_gleif_relationships.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict, deque

import requests

from ccf.config import REPO_ROOT
from ccf.fetch import DEFAULT_LIMITER

SCREEN = REPO_ROOT / "sources" / "screening"
BASE = "https://api.gleif.org/api/v1/lei-records"

#: Relationship directions GLEIF exposes per LEI.
DIRECTIONS = {
    "direct-parent": "hasDirectParent",
    "ultimate-parent": "hasUltimateParent",
    "direct-children": "hasDirectChild",
}

#: Bound the crawl. Families are walked outward from each anchor; without a
#: cap a single large group could pull thousands of unrelated LEIs.
MAX_FRONTIER = 400
MAX_CHILDREN_PER_NODE = 25


def gleif_get(url: str, params: dict | None = None) -> dict | None:
    DEFAULT_LIMITER.wait()
    try:
        resp = requests.get(url, params=params or {}, timeout=25)
        if resp.status_code == 404:
            return None          # no such relationship — normal, not an error
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:  # noqa: BLE001
        return None


def record_attrs(payload: dict) -> list[dict]:
    data = payload.get("data")
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def main() -> int:
    anchors = json.loads((SCREEN / "anchors_final.json").read_text())["anchors"]
    anchor_leis = [a["lei"] for a in anchors]
    lei_name = {a["lei"]: a.get("gleif_legal_name") or a["sec_name"]
                for a in anchors}

    print(f"Crawling GLEIF Level 2 relationships from {len(anchor_leis)} anchors\n")

    edges: list[dict] = []
    seen_edges: set[tuple] = set()
    discovered: dict[str, str] = dict(lei_name)   # lei -> best-known name
    visited: set[str] = set()
    frontier = deque(anchor_leis)

    while frontier and len(visited) < MAX_FRONTIER:
        lei = frontier.popleft()
        if lei in visited:
            continue
        visited.add(lei)

        for endpoint, edge_type in DIRECTIONS.items():
            payload = gleif_get(f"{BASE}/{lei}/{endpoint}")
            if not payload:
                continue
            records = record_attrs(payload)
            if endpoint == "direct-children":
                records = records[:MAX_CHILDREN_PER_NODE]
            for rec in records:
                attrs = rec.get("attributes", {})
                other = attrs.get("lei")
                if not other:
                    continue
                entity = attrs.get("entity", {}) or {}
                name = (entity.get("legalName") or {}).get("name", "")
                if name:
                    discovered.setdefault(other, name)

                src, dst = (other, lei) if endpoint != "direct-children" else (lei, other)
                key = (src, dst, edge_type)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges.append({
                    "parent_lei": src,
                    "child_lei": dst,
                    "edge_type": edge_type,
                    "jurisdiction": entity.get("jurisdiction", ""),
                    "provenance": "public",
                    "source": "GLEIF RR-CDF Level 2 relationship API",
                })
                if other not in visited and len(visited) + len(frontier) < MAX_FRONTIER:
                    frontier.append(other)

        if len(visited) % 25 == 0:
            print(f"  visited {len(visited)}  edges {len(edges)}  "
                  f"queue {len(frontier)}")

    print(f"\n  {len(edges)} edges across {len(discovered)} entities "
          f"({len(visited)} crawled)")

    # Depth census — the condition that actually matters for `depth`.
    parents: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        parents[e["child_lei"]].append(e["parent_lei"])

    def depth_from(lei: str) -> int:
        best, seen, stack = 0, {lei}, [(lei, 0)]
        while stack:
            node, d = stack.pop()
            best = max(best, d)
            for p in parents.get(node, []):
                if p not in seen and d < 10:
                    seen.add(p)
                    stack.append((p, d + 1))
        return best

    depths = {lei: depth_from(lei) for lei in anchor_leis}
    deep = {k: v for k, v in depths.items() if v >= 4}
    three = {k: v for k, v in depths.items() if v == 3}

    print(f"\n  DEPTH CENSUS (§F wants >= 2 families reaching 4+ hops)")
    print(f"    anchors with depth >= 4 : {len(deep)}")
    print(f"    anchors with depth == 3 : {len(three)}")
    print(f"    anchors with depth <= 2 : {sum(1 for v in depths.values() if v <= 2)}")
    for lei, d in sorted(depths.items(), key=lambda kv: -kv[1])[:8]:
        print(f"      {d} hops  {discovered.get(lei, lei)[:44]}")

    (SCREEN / "gleif_relationships.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 3 — GLEIF Level 2 ownership edges",
                "source": "https://api.gleif.org/api/v1/lei-records/{lei}/{relationship}",
                "edge_count": len(edges),
                "entity_count": len(discovered),
                "anchors_depth_ge_4": len(deep),
                "depths": depths,
                "entities": discovered,
                "edges": edges,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: sources/screening/gleif_relationships.json")

    if len(deep) < 2:
        print(f"\n  NOTE: natural depth is short of §F's '>= 2 families at 4+ "
              f"hops'.\n  Wave 3 must engineer the shortfall and label it "
              f"`synthetic — engineered`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
