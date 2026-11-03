#!/usr/bin/env python3
"""Wave 13b Task 2 — GLEIF Level 2 relationship records, widened draw.

§C asks for *"corporate ownership records across jurisdictions"* in
**Postgres**. Its named source, OpenCorporates, now returns 401 and is no
longer free; the user approved **GLEIF Level 2** as the substitute, and it is
an improvement rather than a concession — GLEIF is keyed on LEI, already this
estate's correlation key, so it joins to everything without a new crosswalk.
That deviation is a documented punch-list item for the vault, not a silent swap.

## Why the bulk golden copy, not the Wave 3 API crawl

`generators/fetch_gleif_relationships.py` (Wave 3) walks the relationship API
per LEI under two caps — `MAX_FRONTIER = 400`, `MAX_CHILDREN_PER_NODE = 25` —
and reported **zero** anchors at depth >= 4. Wave 11a's lesson applies exactly:
*instability or emptiness from a capped sweep is evidence of incompleteness,
not a fact about the source.* The daily golden copy is one file holding every
published relationship, so the hierarchy can be traversed with no cap at all
and the depth census is a measurement rather than an artifact of the caps.

## The two relationship kinds must not be mixed

    IS_DIRECTLY_CONSOLIDATED_BY     child -> its immediate parent
    IS_ULTIMATELY_CONSOLIDATED_BY   child -> the top of its group, skipping
                                    every intermediate

Traversing both as one edge set does two wrong things at once: it **collapses**
real depth (a 5-hop chain also carries a 1-hop ultimate edge) and it
**manufactures cycles** (A -> B -> C directly, C -> A ultimately). A depth
figure measured that way would describe the edge mixture, not the group. Only
DIRECT edges build the chain here; ULTIMATE edges are kept as records and used
to cross-check the top, never to walk.

Relationship STATUS matters the same way: only `ACTIVE` relationships describe
the group as it stands. Inactive ones are loaded — they are genuine registry
records with an end date, and supersession is part of what this estate teaches
— but they never enter the depth traversal.

Output: sources/screening/wave13b_gleif_l2.json

    uv run generators/fetch_gleif_level2.py
    uv run generators/fetch_gleif_level2.py --force
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from collections import defaultdict, deque
from datetime import datetime, timezone

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT, pg_connect
from ccf.fetch import DEFAULT_LIMITER, SourceManifest, fetch, get_json

SCREEN = REPO_ROOT / "sources" / "screening"
GOLDEN_LATEST = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/rr/latest"
LEI_API = "https://api.gleif.org/api/v1/lei-records"

DIRECT = "IS_DIRECTLY_CONSOLIDATED_BY"
ULTIMATE = "IS_ULTIMATELY_CONSOLIDATED_BY"

#: GLEIF allows a comma-separated LEI filter; 200 is the API's page ceiling.
LEI_BATCH = 100


def anchor_leis(cur) -> list[str]:
    cur.execute('SELECT lei FROM legal_entity WHERE is_anchor ORDER BY lei')
    return [r[0] for r in cur.fetchall()]


def fluree_graph_leis() -> list[str]:
    """Every LEI already asserted in the Fluree graph.

    Wave 3's capped crawl put 153 real LEIs into the ledger. They are part of
    this estate's graph, so their families belong in the draw — seeding from
    the anchors alone would re-derive a narrower slice than the estate already
    holds and call it a widening.
    """
    q = (f"PREFIX ex: <{EX}>\n"
         f"SELECT ?lei FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s ex:lei ?lei . }}")
    res = fluree.query(q)
    bindings = res["results"]["bindings"]
    return sorted({b["lei"]["value"] for b in bindings})


def download_rr(manifest: SourceManifest, force: bool) -> tuple[dict, "zipfile.ZipFile"]:
    meta = get_json(GOLDEN_LATEST)
    full = meta["data"]["full_file"]["csv"]
    publish = meta["data"]["publish_date"]
    print(f"  golden copy    {publish}  ({full['record_count']:,} records, "
          f"{full['size_human_readable']})")

    # The URL carries the publish date and file id, so it is stable and
    # re-fetchable — unlike OFAC's signed redirect. Recording it as given.
    path = fetch(full["url"], manifest, "rr-golden-copy.csv.zip", force=force)
    zf = zipfile.ZipFile(path)
    return {"publish_date": publish,
            "record_count": full["record_count"],
            "url": full["url"],
            "cdf_version": full["cdf_version"]}, zf


def parse_rr(zf: zipfile.ZipFile) -> list[dict]:
    name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
    with zf.open(name) as fh:
        reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
        cols = reader.fieldnames or []

        def col(*candidates: str) -> str:
            for c in candidates:
                if c in cols:
                    return c
            raise RuntimeError(
                f"RR CSV is missing all of {candidates}. Header changed; "
                f"columns present: {cols[:12]}"
            )

        c_start = col("Relationship.StartNode.NodeID")
        c_end = col("Relationship.EndNode.NodeID")
        c_type = col("Relationship.RelationshipType")
        c_status = col("Relationship.RelationshipStatus")
        c_reg_status = col("Registration.RegistrationStatus")
        c_reg_init = col("Registration.InitialRegistrationDate")
        c_reg_upd = col("Registration.LastUpdateDate")

        # Relationship periods are repeated groups; the RELATIONSHIP-typed one
        # carries the validity window. Column names are positional in the CSV
        # flattening, so they are discovered rather than assumed.
        period_cols = [c for c in cols if "RelationshipPeriods" in c]

        rows = []
        for r in reader:
            rows.append(
                {
                    # RR-CDF: StartNode is the CHILD, EndNode is the PARENT.
                    "child_lei": (r[c_start] or "").strip(),
                    "parent_lei": (r[c_end] or "").strip(),
                    "relationship_type": (r[c_type] or "").strip(),
                    "relationship_status": (r[c_status] or "").strip(),
                    "registration_status": (r[c_reg_status] or "").strip(),
                    "initial_registration": (r[c_reg_init] or "").strip()[:10] or None,
                    "last_update": (r[c_reg_upd] or "").strip()[:10] or None,
                    "period_start": next(
                        (r[c][:10] for c in period_cols
                         if "StartDate" in c and (r[c] or "").strip()), None),
                    "period_end": next(
                        (r[c][:10] for c in period_cols
                         if "EndDate" in c and (r[c] or "").strip()), None),
                }
            )
        return rows


def reachable(edges: list[dict], seeds: set[str]) -> tuple[set[str], list[dict]]:
    """Every entity connected to a seed through ACTIVE DIRECT edges.

    Undirected on purpose: a sibling subsidiary is reached by going up to the
    shared parent and back down, and the cross-jurisdiction structure §C wants
    lives in exactly those siblings.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        if e["relationship_type"] != DIRECT or e["relationship_status"] != "ACTIVE":
            continue
        adj[e["child_lei"]].add(e["parent_lei"])
        adj[e["parent_lei"]].add(e["child_lei"])

    seen = set(seeds)
    queue = deque(seeds)
    while queue:
        node = queue.popleft()
        for nxt in adj[node]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)

    kept = [e for e in edges
            if e["child_lei"] in seen and e["parent_lei"] in seen]
    return seen, kept


def depth_census(edges: list[dict], population: set[str]) -> dict:
    """Longest ACTIVE DIRECT parent chain above each entity.

    Walks upward only, so the number means "hops to the top of the group",
    which is what §F3's `max_depth` parameter actually ranges over.
    """
    parent: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e["relationship_type"] == DIRECT and e["relationship_status"] == "ACTIVE":
            parent[e["child_lei"]].append(e["parent_lei"])

    memo: dict[str, int] = {}

    def height(node: str, stack: frozenset) -> int:
        if node in memo:
            return memo[node]
        if node in stack:          # a genuine registry cycle; do not recurse
            return 0
        best = 0
        for p in parent.get(node, []):
            best = max(best, 1 + height(p, stack | {node}))
        memo[node] = best
        return best

    depths = {lei: height(lei, frozenset()) for lei in population}
    hist: dict[int, int] = defaultdict(int)
    for d in depths.values():
        hist[d] += 1
    return {"depths": depths, "histogram": dict(sorted(hist.items()))}


def fetch_lei_records(leis: list[str]) -> dict[str, dict]:
    """LEI-level attributes for the subgraph, batched through the public API.

    The LEI-CDF bulk file is GB-scale; the subgraph is a few hundred entities,
    so batching the API is both smaller and current.
    """
    out: dict[str, dict] = {}
    for i in range(0, len(leis), LEI_BATCH):
        batch = leis[i:i + LEI_BATCH]
        DEFAULT_LIMITER.wait()
        payload = get_json(
            f"{LEI_API}?filter%5Blei%5D={','.join(batch)}"
            f"&page%5Bsize%5D={LEI_BATCH}"
        )
        for rec in payload.get("data", []):
            a = rec["attributes"]
            ent = a["entity"]
            legal_addr = ent.get("legalAddress") or {}
            hq_addr = ent.get("headquartersAddress") or {}
            reg = a.get("registration") or {}
            out[a["lei"]] = {
                "lei": a["lei"],
                "legal_name": (ent.get("legalName") or {}).get("name"),
                "legal_jurisdiction": ent.get("jurisdiction"),
                "legal_form": ((ent.get("legalForm") or {}).get("id")),
                "entity_category": ent.get("category"),
                "entity_status": ent.get("status"),
                "legal_country": legal_addr.get("country"),
                "hq_country": hq_addr.get("country"),
                "registration_status": reg.get("status"),
                "initial_registration": (reg.get("initialRegistrationDate") or "")[:10] or None,
                "last_update": (reg.get("lastUpdateDate") or "")[:10] or None,
                # Kept because §F5 needs transliteration structure and GLEIF is
                # one of the few sources that publishes it explicitly.
                "transliterated_names": [
                    n.get("name") for n in (ent.get("transliteratedOtherNames") or [])
                    if n.get("name")
                ],
                "other_names": [
                    n.get("name") for n in (ent.get("otherNames") or []) if n.get("name")
                ],
            }
        print(f"    LEI records {len(out):>5} / {len(leis)}", end="\r")
    print()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    manifest = SourceManifest(
        source="gleif_l2",
        description="GLEIF Level 2 (RR-CDF) relationship golden copy — the "
                    "daily full file of every published entity relationship.",
        licence="GLEIF publishes LEI and relationship data under CC0 1.0.",
    )

    print("Wave 13b Task 2 — GLEIF Level 2 widened draw\n")
    publish, zf = download_rr(manifest, args.force)

    edges = parse_rr(zf)
    print(f"  parsed         {len(edges):,} relationship records")
    if len(edges) != publish["record_count"]:
        print(f"  FAIL: parsed {len(edges):,} but the publisher declares "
              f"{publish['record_count']:,}")
        return 1

    by_type: dict[str, int] = defaultdict(int)
    for e in edges:
        by_type[e["relationship_type"]] += 1
    for t, n in sorted(by_type.items(), key=lambda kv: -kv[1])[:6]:
        print(f"      {t:<34} {n:>8,}")

    with pg_connect() as conn, conn.cursor() as cur:
        anchors = anchor_leis(cur)
    graph_leis = fluree_graph_leis()
    seeds = set(anchors) | set(graph_leis)
    print(f"\n  seeds          {len(seeds)} LEIs  "
          f"({len(anchors)} Postgres anchors + {len(graph_leis)} already in "
          f"Fluree, {len(set(anchors) & set(graph_leis))} in both)")

    population, kept = reachable(edges, seeds)
    print(f"  reachable      {len(population):,} entities via ACTIVE DIRECT edges")
    print(f"  edges in scope {len(kept):,} records among them")

    census = depth_census(kept, population)
    print(f"\n  DEPTH CENSUS (§F3 wants >= 3 chains at depth 5+)")
    for d, n in census["histogram"].items():
        print(f"      depth {d}: {n:>5} entities")
    deep = [lei for lei, d in census["depths"].items() if d >= 5]
    anchors_deep = [lei for lei in anchors if census["depths"].get(lei, 0) >= 5]
    print(f"      entities at depth >= 5 : {len(deep)}")
    print(f"      ANCHORS at depth >= 5  : {len(anchors_deep)}")

    lei_records = fetch_lei_records(sorted(population))
    missing = sorted(population - set(lei_records))
    print(f"  LEI records    {len(lei_records):,} fetched, {len(missing)} missing")

    juris = defaultdict(int)
    for r in lei_records.values():
        juris[(r["legal_jurisdiction"] or "?").split("-")[0]] += 1
    print(f"  jurisdictions  {len(juris)} distinct: "
          f"{dict(sorted(juris.items(), key=lambda kv: -kv[1])[:10])}")

    cross = 0
    for e in kept:
        pj = (lei_records.get(e["parent_lei"], {}).get("legal_jurisdiction") or "")
        cj = (lei_records.get(e["child_lei"], {}).get("legal_jurisdiction") or "")
        if pj and cj and pj.split("-")[0] != cj.split("-")[0]:
            cross += 1
    print(f"  cross-border   {cross:,} of {len(kept):,} records span countries")

    out = SCREEN / "wave13b_gleif_l2.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — GLEIF Level 2 relationship records "
                                 "(kyc-refresh-beneficial-ownership §C, substituting "
                                 "for OpenCorporates; provenance: public)",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "publication": publish,
                "seed_count": len(seeds),
                "entity_count": len(lei_records),
                "record_count": len(kept),
                "cross_border_records": cross,
                "depth_histogram": census["histogram"],
                "depths": census["depths"],
                "entities": lei_records,
                "records": kept,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)} "
          f"({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
