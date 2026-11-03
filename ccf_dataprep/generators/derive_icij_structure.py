#!/usr/bin/env python3
"""Wave 13b Task 4 — an offshore intermediary layer, shaped by ICIJ.

§C: *"Entity and intermediary relationships — ICIJ Offshore Leaks Database
(free, structured)"* -> **Fluree**, `R`.

## A recorded deviation from §C: structure is loaded, names are not

The Offshore Leaks database names real companies and real people. Asserting a
relationship between one of those named entities and anything in this
demonstration graph would **fabricate a claim about a real company** — the
graph would say Trident-or-whoever administers an entity it has never heard
of. ICIJ's own publication terms are explicit that there are legitimate uses
for offshore companies and that inclusion implies no wrongdoing; a synthetic
graph that borrows the names inherits neither the caveat nor the journalism.

So this script takes from ICIJ what teaches the lesson and leaves what creates
the liability:

    TAKEN     fan-out distribution (entities administered per intermediary),
              jurisdiction pairings, the officer-role vocabulary, entity
              status and company-type vocabularies, and the RESOLUTION EDGE
              vocabulary (`same_name_as`, `similar`, `same_as`,
              `probably_same_officer_as`) with its observed weights
    NOT TAKEN any entity name, officer name, address, or node identifier

The generated layer is therefore `synthetic — engineered`, with ICIJ recorded
as the provenance of its *shape*. **This is a punch-list item for the vault**,
not a silent swap: §C reads as though the records themselves are loaded.

## What ICIJ turns out to be unusually good for

`relationships.csv` carries 104,170 `same_name_as`, 46,761 `similar`, 4,272
`same_as` and 132 `probably_same_officer_as` edges. That is a **published
identity-resolution vocabulary with real relative frequencies** — journalists
recording how confident they were that two records are one person. §C asks for
`identifiedAs` / `sameAs` edges *with confidence*, and Task 5 draws its
confidence bands from these weights rather than inventing a scale.

## The name gate, again

Company names are generated from a closed bank below and checked against it,
the same control `generators/derive_psc_persons.py` uses. A real ICIJ name
reaching the output would carry tokens the bank does not contain.

The raw archive is fetched to scratch outside the repository and deleted.

Output: sources/screening/wave13b_offshore.json

    uv run generators/derive_icij_structure.py
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from random import Random

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch

SCREEN = REPO_ROOT / "sources" / "screening"
URL = "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"
SCRATCH = Path(
    os.getenv("CCF_SCRATCH", "/tmp/claude-1000/-home-parkave-ccf-dataprep/"
                             "a76f9e18-95c3-45b9-ae6a-6447d9e1b3dd/scratchpad")
) / "icij"

TARGET_INTERMEDIARIES = 40
TARGET_VEHICLES = 150

#: Closed vocabulary for invented company names. Deliberately bland and
#: generic — an offshore vehicle's name is not where the teaching is, and a
#: distinctive invented name risks colliding with a real one.
NAME_FIRST = (
    "Northgate", "Sundial", "Harbourline", "Kestrel", "Meridian", "Alderway",
    "Blackwater", "Cobalt", "Driftwood", "Evergreen", "Fairhaven", "Goldcrest",
    "Highmark", "Ironbridge", "Juniper", "Larkspur", "Millstone", "Northwind",
    "Orchard", "Pinnacle", "Quarry", "Redstone", "Silverbirch", "Thornhill",
    "Umbra", "Vantage", "Westbourne", "Yardley", "Zephyr", "Ashgrove",
)
NAME_SECOND = (
    "Holdings", "Capital", "Ventures", "Investments", "Partners", "Group",
    "Assets", "Trading", "Nominees", "Trustees", "Management", "Enterprises",
)
#: Suffixes chosen to match the jurisdictions the pairing distribution emits.
SUFFIX_BY_COUNTRY = {
    "VGB": "Ltd", "CYM": "Ltd", "BHS": "Ltd", "PAN": "S.A.", "SYC": "Ltd",
    "BLZ": "Ltd", "JEY": "Ltd", "GGY": "Ltd", "IMN": "Ltd", "MLT": "Ltd",
    "CYP": "Ltd", "LUX": "S.a r.l.", "NLD": "B.V.", "CHE": "AG",
    "HKG": "Limited", "SGP": "Pte Ltd", "ARE": "FZE", "LIE": "AG",
    "GBR": "Ltd", "USA": "LLC", "IRL": "DAC",
}
DEFAULT_SUFFIX = "Ltd"

#: The ICIJ relationship kinds this script reads. Everything else is ignored.
REL_INTERMEDIARY = "intermediary_of"
REL_OFFICER = "officer_of"
RESOLUTION_RELS = ("same_name_as", "similar", "same_as", "same_company_as",
                   "same_id_as", "probably_same_officer_as",
                   "similar_company_as")


def open_member(zf: zipfile.ZipFile, name: str):
    return csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8"))


def scan(zip_path: Path) -> dict:
    """Derive vocabularies and distributions. No name is read into memory."""
    zf = zipfile.ZipFile(zip_path)

    # --- entities: jurisdiction, type, status vocabularies ----------------
    jurisdictions: Counter = Counter()
    company_types: Counter = Counter()
    statuses: Counter = Counter()
    entity_country: dict[str, str] = {}
    for row in open_member(zf, "nodes-entities.csv"):
        code = (row.get("jurisdiction") or "").strip()
        if code:
            jurisdictions[code] += 1
        if (ct := (row.get("company_type") or "").strip()):
            company_types[ct] += 1
        if (st := (row.get("status") or "").strip()):
            statuses[st] += 1
        entity_country[row["node_id"]] = (row.get("country_codes") or "").split(";")[0]

    # --- intermediaries: country only -------------------------------------
    intermediary_country: dict[str, str] = {}
    intermediary_status: Counter = Counter()
    for row in open_member(zf, "nodes-intermediaries.csv"):
        intermediary_country[row["node_id"]] = (
            row.get("country_codes") or "").split(";")[0]
        if (st := (row.get("status") or "").strip()):
            intermediary_status[st] += 1

    # --- relationships ----------------------------------------------------
    fanout: Counter = Counter()          # intermediary node -> entity count
    pairs: Counter = Counter()           # (intermediary country, entity country)
    officer_links: Counter = Counter()
    resolution: Counter = Counter()
    rel_types: Counter = Counter()

    for row in open_member(zf, "relationships.csv"):
        rel = row["rel_type"]
        rel_types[rel] += 1
        if rel == REL_INTERMEDIARY:
            start = row["node_id_start"]
            fanout[start] += 1
            pairs[(intermediary_country.get(start, ""),
                   entity_country.get(row["node_id_end"], ""))] += 1
        elif rel == REL_OFFICER:
            link = (row.get("link") or "").strip().lower()
            if link:
                officer_links[link] += 1
        elif rel in RESOLUTION_RELS:
            resolution[rel] += 1

    return {
        "jurisdictions": jurisdictions,
        "company_types": company_types,
        "statuses": statuses,
        "intermediary_status": intermediary_status,
        "fanout_histogram": Counter(fanout.values()),
        "intermediary_count": len(fanout),
        "pairs": pairs,
        "officer_links": officer_links,
        "resolution": resolution,
        "rel_types": rel_types,
    }


def weighted(rng: Random, counter: Counter):
    items, weights = zip(*counter.items())
    return rng.choices(items, weights=weights, k=1)[0]


def name_vocabulary() -> set[str]:
    vocab = set(NAME_FIRST) | set(NAME_SECOND) | set(SUFFIX_BY_COUNTRY.values())
    vocab.add(DEFAULT_SUFFIX)
    return {t for name in vocab for t in name.split()}


def generate(stats: dict, rng: Random) -> dict:
    # Jurisdictions restricted to those the suffix table covers, so a vehicle's
    # name and its jurisdiction cannot disagree.
    juris = Counter({k: v for k, v in stats["jurisdictions"].items()
                     if k in SUFFIX_BY_COUNTRY})
    if not juris:
        raise RuntimeError("no ICIJ jurisdiction maps to a known suffix")

    pairs = Counter({(a, b): n for (a, b), n in stats["pairs"].items()
                     if a and b in SUFFIX_BY_COUNTRY})

    used_names: set[str] = set()

    def mint(country: str) -> str:
        for _ in range(200):
            name = (f"{rng.choice(NAME_FIRST)} {rng.choice(NAME_SECOND)} "
                    f"{SUFFIX_BY_COUNTRY.get(country, DEFAULT_SUFFIX)}")
            if name not in used_names:
                used_names.add(name)
                return name
        raise RuntimeError("name bank exhausted; widen NAME_FIRST/NAME_SECOND")

    intermediaries = []
    for i in range(TARGET_INTERMEDIARIES):
        country, _ = weighted(rng, pairs)
        intermediaries.append({
            "intermediary_id": f"ICJ-INT-{i + 1:03d}",
            "name": mint(country),
            "country_code": country,
            "status": weighted(rng, stats["intermediary_status"]),
            "provenance": "synthetic — engineered",
        })

    # Fan-out, compressed. ICIJ's real distribution is extreme — a handful of
    # agents administer tens of thousands of companies each — and reproducing
    # it proportionally over a 150-vehicle budget gave ONE intermediary 116
    # vehicles and left 21 of 40 with none. That is faithful to the ratio and
    # useless as a graph: a traversal that never reaches 21 of the nodes it
    # loaded teaches nothing about intermediaries.
    #
    # So the ORDERING and the presence of a dominant agent are preserved, and
    # the magnitude is compressed logarithmically. Every intermediary gets at
    # least one vehicle. This is a departure from the observed distribution
    # and is recorded in the artifact as `fanout_compression`.
    import math

    hist = stats["fanout_histogram"]
    draws = sorted((weighted(rng, hist) for _ in intermediaries), reverse=True)
    weights = [math.log1p(d) for d in draws]
    total_w = sum(weights) or 1.0
    scaled = [max(1, round(w / total_w * TARGET_VEHICLES)) for w in weights]

    # Trim or pad to exactly the budget, taking from the largest first so the
    # dominant agent stays dominant.
    while sum(scaled) > TARGET_VEHICLES:
        i = scaled.index(max(scaled))
        scaled[i] -= 1
    while sum(scaled) < TARGET_VEHICLES:
        i = scaled.index(max(scaled))
        scaled[i] += 1

    vehicles = []
    edges = []
    v = 0
    for intermediary, count in zip(intermediaries, scaled):
        for _ in range(count):
            if v >= TARGET_VEHICLES:
                break
            country_pair = [p for p in pairs if p[0] == intermediary["country_code"]]
            entity_country = (
                rng.choice(country_pair)[1] if country_pair
                else weighted(rng, juris)
            )
            v += 1
            vehicle = {
                "vehicle_id": f"ICJ-SPV-{v:03d}",
                "name": mint(entity_country),
                "jurisdiction": entity_country,
                "company_type": weighted(rng, stats["company_types"]),
                "status": weighted(rng, stats["statuses"]),
                "provenance": "synthetic — engineered",
            }
            vehicles.append(vehicle)
            edges.append({
                "intermediary_id": intermediary["intermediary_id"],
                "vehicle_id": vehicle["vehicle_id"],
                "relationship": REL_INTERMEDIARY,
                "provenance": "synthetic — engineered",
            })

    return {"intermediaries": intermediaries, "vehicles": vehicles,
            "edges": edges,
            "fanout_compression": {
                "observed_draws_sorted": draws,
                "allocated": scaled,
                "note": "Observed ICIJ fan-out compressed by log1p. The "
                        "ordering and the dominant agent are preserved; the "
                        "magnitudes are not. Proportional allocation over a "
                        "150-vehicle budget left 21 of 40 intermediaries with "
                        "no vehicle at all.",
            }}


def check_no_leak(layer: dict) -> list[str]:
    vocab = name_vocabulary()
    failures = []
    for kind in ("intermediaries", "vehicles"):
        for node in layer[kind]:
            unknown = [t for t in node["name"].split() if t not in vocab]
            if unknown:
                failures.append(f"{kind}: {node.get('intermediary_id') or node['vehicle_id']}"
                                f" carries token(s) outside the bank: {unknown}")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep-raw", action="store_true")
    args = ap.parse_args()

    manifest = SourceManifest(
        source="icij",
        description=(
            "ICIJ Offshore Leaks Database (full CSV). PROVENANCE ONLY — the "
            "archive is fetched outside the repository, reduced to structural "
            "distributions and vocabularies, and deleted. No entity name, "
            "officer name, address or node id is retained."
        ),
        licence="ICIJ publishes the Offshore Leaks database under ODbL. ICIJ "
                "states that inclusion implies no wrongdoing; this project "
                "therefore uses the STRUCTURE only and never attributes a real "
                "name to a synthetic relationship.",
    )

    print("Wave 13b Task 4 — offshore intermediary layer, shaped by ICIJ\n")
    raw = fetch(URL, manifest, "full-oldb.zip", dest_dir=SCRATCH, timeout=900)

    stats = scan(raw)
    print(f"  relationships read   {sum(stats['rel_types'].values()):,}")
    for rel, n in stats["rel_types"].most_common(6):
        print(f"      {rel:<28} {n:>9,}")
    print(f"  intermediaries seen  {stats['intermediary_count']:,}")
    print(f"  jurisdictions        {len(stats['jurisdictions']):,}")
    print(f"  officer-role links   {len(stats['officer_links']):,} distinct; "
          f"top: {[l for l, _ in stats['officer_links'].most_common(4)]}")
    print(f"  resolution edges     {dict(stats['resolution'].most_common())}")

    layer = generate(stats, Random(20260822))

    if args.keep_raw:
        print(f"\n  WARNING: --keep-raw left the archive at {raw}")
    else:
        raw.unlink(missing_ok=True)
        print(f"\n  deleted raw archive — provenance kept in "
              f"sources/icij/manifest.json, contents not")

    failures = check_no_leak(layer)
    print(f"\n  NAME GATE: every generated name token must come from the bank")
    if failures:
        for f in failures[:5]:
            print(f"      FAIL  {f}")
        return 1
    print(f"      ok    {len(layer['intermediaries'])} intermediaries + "
          f"{len(layer['vehicles'])} vehicles")

    fanout_actual = Counter(e["intermediary_id"] for e in layer["edges"])
    print(f"\n  generated  {len(layer['intermediaries'])} intermediaries, "
          f"{len(layer['vehicles'])} vehicles, {len(layer['edges'])} edges")
    print(f"      fan-out  max {max(fanout_actual.values())}, "
          f"min {min(fanout_actual.values())}, "
          f"{len(fanout_actual)} intermediaries with at least one vehicle")
    print(f"      jurisdictions used: "
          f"{len({v['jurisdiction'] for v in layer['vehicles']})}")

    out = SCREEN / "wave13b_offshore.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — offshore intermediary layer "
                                 "(kyc-refresh-beneficial-ownership §C, ICIJ "
                                 "STRUCTURE only; see the generator docstring "
                                 "for the recorded deviation)",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "provenance": "synthetic — engineered",
                "shape_source": {
                    "name": "ICIJ Offshore Leaks Database",
                    "url": URL,
                    "relationships_read": sum(stats["rel_types"].values()),
                    "intermediaries_observed": stats["intermediary_count"],
                    "names_taken": False,
                },
                # Carried forward for Task 5: real relative frequencies for
                # identity-resolution edges, so the confidence bands are drawn
                # from observed journalism rather than invented.
                "resolution_vocabulary": dict(stats["resolution"].most_common()),
                "officer_role_vocabulary": dict(stats["officer_links"].most_common(20)),
                "fanout_compression": layer.pop("fanout_compression"),
                "intermediary_count": len(layer["intermediaries"]),
                "vehicle_count": len(layer["vehicles"]),
                "edge_count": len(layer["edges"]),
                **layer,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)} "
          f"({out.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
