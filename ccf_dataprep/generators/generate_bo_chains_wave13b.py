#!/usr/bin/env python3
"""Wave 13b Task 8 — engineered beneficial-ownership chains and cycles.

Four §F conditions land here:

    §F1  ~50 anchor entities with ownership chains reaching natural persons
    §F3  >= 3 chains reaching depth 5 or beyond, so `max_depth` is consequential
    §F4  >= 2 engineered cycles, at least one spanning jurisdictions
    §F7  >= 2 entities with EU-resident persons

## Why every one of these is `synthetic — engineered`, honestly

Measured in Task 2 against the **full** GLEIF golden copy with no traversal
caps: the anchor-reachable component is 190 entities with a maximum depth of
**4** and **zero** chains at depth 5. Public corporate hierarchies for this
cast are genuinely shallow, and the public record for a US-listed obligor
terminates in the listed company itself, never in a natural person — a chain
that reaches a person cannot be fetched, only built.

That is a measurement, not the assumption the design started from, and it is
what makes the engineering budget defensible rather than convenient.

## Two findings about the cycle condition

**`validators/conditions.py` counts cycle MEMBERS, not cycles.** Its check
binds `?a` in `?a owns ?b . ?b owns ?c . ?c owns ?a` and counts distinct `?a`
— one 3-cycle yields three bindings, so the estate's single cycle has been
reporting **3 / 3 PASS** against a condition asking for two CYCLES. Fixed in
this wave; recorded in `known-issues.md` §14.7.

**The existing cycle cannot span jurisdictions, because it has none.** Its
three nodes (`Calder Industrial N.V.`, `Meridian Holdings S.A.`,
`Thornbury Capital Ltd`) carry a type, a label and a provenance mark and no
jurisdiction anywhere — not in Fluree, and not in Postgres, where they have no
row at all. The legal-form suffixes in their names *imply* three countries and
assert nothing. This wave gives them rows with jurisdictions, so the claim
becomes checkable rather than suggestive.

## Structure

Chains hang off the offshore vehicles from Task 4 — an SPV with a natural
beneficial owner behind one or more holding companies is the shape KYC
actually has to unwind:

    person --owns--> holdco_n ... --owns--> holdco_1 --owns--> vehicle

Per-hop stakes are drawn so the EFFECTIVE stake (the product of the hops) lands
either side of the 25% statutory threshold, because a chain set where every
beneficial owner clears the threshold makes `bo_threshold` decorative.

Output: sources/screening/wave13b_bo_chains.json

    uv run generators/generate_bo_chains_wave13b.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from random import Random

from ccf.config import REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"

#: §F1 — ~50 entities whose chains reach a natural person.
TARGET_CHAINS = 50

#: §F3 — depth is the number of `owns` hops from the person down to the
#: entity. `>= 3 chains at depth 5+` is the floor; 8 are built so the
#: condition survives one being disturbed.
DEEP_CHAINS = 8
DEEP_MIN_DEPTH = 5

#: Jurisdictions for engineered holding companies, chosen so chains cross
#: borders the way real structures do.
HOLDCO_JURISDICTIONS = [
    ("LU", "Luxembourg"), ("NL", "Netherlands"), ("IE", "Ireland"),
    ("CY", "Cyprus"), ("MT", "Malta"), ("VGB", "British Virgin Islands"),
    ("KY", "Cayman Islands"), ("SG", "Singapore"), ("CH", "Switzerland"),
    ("JE", "Jersey"), ("GB", "United Kingdom"), ("DE", "Germany"),
]

HOLDCO_FIRST = ("Ardent", "Beacon", "Crestline", "Dunmore", "Eastcliff",
                "Foxglove", "Granton", "Halcyon", "Inverness", "Jessamine",
                "Kingsmoor", "Lockhart", "Marchmont", "Netherby", "Oakhurst",
                "Ptarmigan", "Ravenswood", "Stanhope", "Tenby", "Ullswater")
HOLDCO_SECOND = ("Holdings", "Capital", "Nominees", "Investments", "Trust",
                 "Participations", "Partners", "Equity")
SUFFIX = {"LU": "S.a r.l.", "NL": "B.V.", "IE": "DAC", "CY": "Ltd",
          "MT": "Ltd", "VGB": "Ltd", "KY": "Ltd", "SG": "Pte Ltd",
          "CH": "AG", "JE": "Ltd", "GB": "Ltd", "DE": "GmbH"}

#: The existing cycle, which has never carried a jurisdiction. Assigned to
#: match the legal form already in each label, so the rows agree with the
#: names the ledger has held since Wave 3 rather than contradicting them.
EXISTING_CYCLE = [
    ("CycCalderIndustrialNv", "Calder Industrial N.V.", "NL", "Netherlands"),
    ("CycMeridianHoldingsSa", "Meridian Holdings S.A.", "LU", "Luxembourg"),
    ("CycThornburyCapitalLtd", "Thornbury Capital Ltd", "GB", "United Kingdom"),
]

#: The second cycle §F4 requires. Deliberately spans three more countries and
#: does NOT reuse the first cycle's members, so the two are independent.
SECOND_CYCLE = [
    ("CycHarborstoneKy", "Harborstone Trustees Ltd", "KY", "Cayman Islands"),
    ("CycLindenfeldGmbh", "Lindenfeld Beteiligungen GmbH", "DE", "Germany"),
    ("CycPahangPteLtd", "Pahang Nominees Pte Ltd", "SG", "Singapore"),
]


def main() -> int:
    rng = Random(20260822)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT vehicle_id, name, jurisdiction FROM offshore_vehicle "
                    "ORDER BY vehicle_id")
        vehicles = cur.fetchall()
        cur.execute(
            "SELECT p.person_key, p.display_name, pp.nationality, "
            "       pp.country_of_residence, pp.is_eu_national "
            "FROM psc_person pp JOIN person p USING (person_key) "
            "ORDER BY p.person_key"
        )
        persons = cur.fetchall()
        cur.execute("SELECT DISTINCT country_of_residence FROM psc_person "
                    "WHERE residence_engineered")
        eu_residences = {r[0] for r in cur.fetchall()}

    if len(vehicles) < TARGET_CHAINS:
        print(f"  FAIL: only {len(vehicles)} offshore vehicles available")
        return 1

    eu_persons = [p for p in persons if p[3] in eu_residences]
    print("Wave 13b Task 8 — beneficial-ownership chains and cycles\n")
    print(f"  vehicles available   {len(vehicles)}")
    print(f"  persons available    {len(persons)}  "
          f"({len(eu_persons)} EU-resident)")

    used_names: set[str] = set()

    def mint_holdco(index: int) -> dict:
        code, country = rng.choice(HOLDCO_JURISDICTIONS)
        for _ in range(300):
            name = (f"{rng.choice(HOLDCO_FIRST)} {rng.choice(HOLDCO_SECOND)} "
                    f"{SUFFIX[code]}")
            if name not in used_names:
                used_names.add(name)
                break
        else:
            raise RuntimeError("holdco name bank exhausted")
        return {"entity_id": f"HLD-{index:04d}", "name": name,
                "jurisdiction": code, "country": country,
                "kind": "holding_company",
                "provenance": "synthetic — engineered"}

    # --- chains -----------------------------------------------------------
    targets = rng.sample(vehicles, TARGET_CHAINS)
    deep_slots = set(rng.sample(range(TARGET_CHAINS), DEEP_CHAINS))
    # Guarantee EU-resident owners on more than the floor of 2, so the
    # condition does not sit on a single chain.
    eu_slots = set(rng.sample(range(TARGET_CHAINS), 6))

    holdcos: list[dict] = []
    chains: list[dict] = []
    hops: list[dict] = []
    holdco_index = 0

    for slot, (vehicle_id, vehicle_name, vehicle_juris) in enumerate(targets):
        depth = (rng.randrange(DEEP_MIN_DEPTH, DEEP_MIN_DEPTH + 2)
                 if slot in deep_slots else rng.randrange(2, 5))
        pool = eu_persons if (slot in eu_slots and eu_persons) else persons
        person_key, person_name, nationality, residence, is_eu = rng.choice(pool)

        # depth hops means depth-1 intermediate holdcos between person and
        # vehicle: person -> h[0] -> ... -> h[depth-2] -> vehicle
        intermediates = []
        for _ in range(depth - 1):
            holdco_index += 1
            h = mint_holdco(holdco_index)
            holdcos.append(h)
            intermediates.append(h)

        chain_nodes = [person_key] + [h["entity_id"] for h in intermediates] + [vehicle_id]
        # Stakes: the top hop varies widely, lower hops are usually
        # majority-held. The EFFECTIVE stake is the product, and it has to
        # land on both sides of 25% across the population or `bo_threshold`
        # would never discriminate.
        stakes = []
        for hop in range(depth):
            stakes.append(round(rng.uniform(30.0, 100.0)
                                if hop else rng.uniform(15.0, 100.0), 2))
        effective = 100.0
        for s in stakes:
            effective *= s / 100.0
        effective = round(effective, 4)

        juris_path = ([nationality]
                      + [h["jurisdiction"] for h in intermediates]
                      + [vehicle_juris])
        chain_id = f"BOC-{slot + 1:04d}"
        chains.append({
            "chain_id": chain_id,
            "entity_id": vehicle_id,
            "entity_kind": "offshore_vehicle",
            "entity_name": vehicle_name,
            "person_key": person_key,
            "person_name": person_name,
            "person_residence": residence,
            "person_is_eu_resident": residence in eu_residences,
            "depth": depth,
            "effective_pct": effective,
            "jurisdiction_path": juris_path,
            "crosses_jurisdictions": len({j for j in juris_path[1:]}) > 1,
            "provenance": "synthetic — engineered",
        })
        for hop in range(depth):
            hops.append({
                "chain_id": chain_id,
                "hop_index": hop,
                "owner_id": chain_nodes[hop],
                "owner_kind": "person" if hop == 0 else "holding_company",
                "owned_id": chain_nodes[hop + 1],
                "owned_kind": ("offshore_vehicle" if hop == depth - 1
                               else "holding_company"),
                "stake_pct": stakes[hop],
                "provenance": "synthetic — engineered",
            })

    # --- cycles -----------------------------------------------------------
    cycle_entities = []
    cycle_edges = []
    for group, members in (("CYCLE-1", EXISTING_CYCLE), ("CYCLE-2", SECOND_CYCLE)):
        for entity_id, name, code, country in members:
            cycle_entities.append({
                "entity_id": entity_id, "name": name, "jurisdiction": code,
                "country": country, "kind": "cycle_member",
                "cycle_group": group,
                "provenance": "synthetic — engineered",
            })
        # Only the SECOND cycle's edges are written by this wave. The first
        # cycle's `owns` edges already exist in Fluree from Wave 3 and are
        # left alone — re-asserting them would be harmless but would blur
        # which wave owns them.
        if group == "CYCLE-2":
            for i, (entity_id, *_rest) in enumerate(members):
                cycle_edges.append({
                    "cycle_group": group,
                    "owner_id": entity_id,
                    "owned_id": members[(i + 1) % len(members)][0],
                    "stake_pct": round(rng.uniform(26.0, 49.0), 2),
                    "provenance": "synthetic — engineered",
                })

    # --- report and gate --------------------------------------------------
    depths = Counter(c["depth"] for c in chains)
    deep = [c for c in chains if c["depth"] >= DEEP_MIN_DEPTH]
    eu_chains = [c for c in chains if c["person_is_eu_resident"]]
    above = [c for c in chains if c["effective_pct"] >= 25.0]
    below = [c for c in chains if c["effective_pct"] < 25.0]
    cross = [c for c in chains if c["crosses_jurisdictions"]]

    print(f"\n  chains               {len(chains)}   depths: "
          f"{dict(sorted(depths.items()))}")
    print(f"      depth >= {DEEP_MIN_DEPTH}         {len(deep)}   (§F3 floor 3)")
    print(f"      crossing borders {len(cross)}")
    print(f"      EU-resident BO   {len(eu_chains)}   (§F7 floor 2 entities)")
    print(f"      effective >= 25% {len(above)} · < 25% {len(below)}  "
          f"(both sides needed or bo_threshold discriminates nothing)")
    print(f"  holding companies    {len(holdcos)}")
    print(f"  hops                 {len(hops)}")
    print(f"  cycle entities       {len(cycle_entities)}  "
          f"({len({c['cycle_group'] for c in cycle_entities})} cycles, "
          f"{len(cycle_edges)} new edges)")
    for group in ("CYCLE-1", "CYCLE-2"):
        js = {c["jurisdiction"] for c in cycle_entities
              if c["cycle_group"] == group}
        print(f"      {group}  jurisdictions {sorted(js)}  "
              f"{'SPANS' if len(js) > 1 else 'single-jurisdiction'}")

    failures = []
    if len(deep) < 3:
        failures.append(f"§F3: {len(deep)} chains at depth >= {DEEP_MIN_DEPTH}, "
                        f"floor is 3")
    if len(eu_chains) < 2:
        failures.append(f"§F7: {len(eu_chains)} entities with an EU-resident "
                        f"beneficial owner, floor is 2")
    if not above or not below:
        failures.append("every chain falls on ONE side of the 25% threshold; "
                        "bo_threshold would discriminate nothing")
    spanning = [g for g in ("CYCLE-1", "CYCLE-2")
                if len({c["jurisdiction"] for c in cycle_entities
                        if c["cycle_group"] == g}) > 1]
    if len(spanning) < 1:
        failures.append("§F4: no cycle spans jurisdictions")
    if failures:
        print()
        for f in failures:
            print(f"  FAIL  {f}")
        return 1

    out = SCREEN / "wave13b_bo_chains.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — beneficial-ownership chains and "
                                 "cycles (§F1, §F3, §F4, §F7). All engineered; "
                                 "GLEIF's real maximum depth for this cast is 4 "
                                 "and its chains never reach a natural person.",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "provenance": "synthetic — engineered",
                "chain_count": len(chains),
                "deep_chain_count": len(deep),
                "eu_resident_chain_count": len(eu_chains),
                "holdco_count": len(holdcos),
                "holdcos": holdcos,
                "chains": chains,
                "hops": hops,
                "cycle_entities": cycle_entities,
                "cycle_edges": cycle_edges,
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
