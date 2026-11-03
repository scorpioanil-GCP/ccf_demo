#!/usr/bin/env python3
"""Wave 7 — generate the MNPI wall dataset.

`mnpi-wall-enforcement` is the catalog's demonstration that entitlement is a
**formative constraint**: the edge is not filtered from the result, it never
materializes. Three principals request the same issuer at the same moment and
receive products that differ in *what exists*, not in what is shown.

Store split per §C, and the SQLite placement is the point rather than a detail:

    SQLite    control-room restricted list. In real institutions this lives in
              a small, locally-maintained system owned by compliance -- not the
              enterprise data platform. The fabric must reach a departmental
              store to enforce an enterprise-critical policy, and must do so
              BEFORE anything else runs. A demo where every signal sits in a
              well-governed enterprise store misrepresents integration.
    Fluree    wall-state assertions (bitemporal: valid + assertion time),
              research embargo windows, Reg FD disclosure events
    Postgres  deal pipeline, MNPI-bearing interactions, trading positions,
              ProjectionPlan definitions
    MongoDB   research notes, published and draft, with MNPI tags

**Wall state is `T` as much as `P`.** Who was over the wall *on a given date* is
what a surveillance review asks, so it needs the same bitemporal treatment as
covenant-in-force-as-of: valid time for when the wall applied, assertion time
for when the control room recorded it.

Note on entities: real issuers are correct here — §C inherits them from
`corporate-family-tree` as public. The synthetic-entities-only hard rule belongs
to `aml-typology-match`, a different spec, and is not in scope for this wave.
Every deal, interaction, position, research note and wall crossing below is
invented and labelled `synthetic — internal`.

Output: sources/screening/mnpi_layer.json

Run: uv run generators/generate_mnpi.py
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260817
ISSUER_COUNT = 10
RESTRICTED_COUNT = 4
DEAL_COUNT = 32
RESEARCH_COUNT = 42

#: Three principals, three ProjectionPlans. `perspective` is requestable but
#: NEVER self-asserted — a request for a perspective the credential does not
#: support is refused, not downgraded. Silent downgrade would let a caller
#: probe the wall by observing which requests degrade.
PRINCIPALS = [
    {
        "principal_id": "PRIN-COV-001",
        "name": "coverage banker",
        "side": "private",
        "perspective": "coverage-banker",
        "permitted_edge_types": [
            "owns", "controls",
            "hasDealEngagement", "hasInteraction", "hasMnpiEngagement",
        ],
        "permitted_classifications": [
            "public-filed", "internal-confidential", "internal-restricted",
        ],
        "permitted_document_types": ["filing", "memorandum", "research"],
        "sees_mnpi": True,
    },
    {
        "principal_id": "PRIN-RES-002",
        "name": "research analyst",
        "side": "public",
        "perspective": "research-analyst",
        "permitted_edge_types": [
            "owns", "controls",
            "hasPublishedResearch",
        ],
        "permitted_classifications": ["public-filed"],
        "permitted_document_types": ["filing", "research"],
        "sees_mnpi": False,
    },
    {
        "principal_id": "PRIN-TRD-003",
        "name": "trader",
        "side": "public-surveilled",
        "perspective": "trader",
        "permitted_edge_types": [
            "owns", "controls",
            "hasPosition",
        ],
        # A trader sees neither MNPI nor research pre-publication state. §A's
        # table gives them positions, market data, and public disclosure --
        # research is absent entirely, not merely filtered to published.
        "permitted_classifications": ["public-filed"],
        "permitted_document_types": ["filing"],
        "sees_mnpi": False,
    },
]

DEAL_TYPES = ["M&A sell-side", "M&A buy-side", "DCM issuance",
              "ECM follow-on", "refinancing", "LBO financing"]
DEAL_STAGES = ["pitched", "mandated", "diligence", "documentation", "signed"]
INTERACTION_TYPES = ["management meeting", "site visit", "earnings call",
                     "deal update", "non-deal roadshow"]


def iso(d: date) -> str:
    return d.isoformat()


def main() -> int:
    rng = random.Random(SEED)
    today = date.today()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT e.lei, e.legal_name, c.internal_client_id, c.ticker
            FROM "{PG_SCHEMA_V2}".legal_entity e
            JOIN "{PG_SCHEMA_V2}".crosswalk c USING (lei)
            WHERE e.is_anchor
            ORDER BY e.lei
            LIMIT %s
        """, (ISSUER_COUNT,))
        issuers = [
            {"lei": r[0], "legal_name": r[1], "internal_client_id": r[2],
             "ticker": r[3]}
            for r in cur.fetchall()
        ]

    print(f"Generating MNPI wall dataset over {len(issuers)} issuers\n")

    # --- restricted list (SQLite) ------------------------------------------
    restricted = []
    for issuer in issuers[:RESTRICTED_COUNT]:
        added = today - timedelta(days=rng.randint(20, 300))
        restricted.append({
            "lei": issuer["lei"],
            "legal_name": issuer["legal_name"],
            "ticker": issuer["ticker"],
            "restriction_type": rng.choice(
                ["deal-related", "research-restricted", "full-restriction"]),
            "added_date": iso(added),
            "removed_date": None,
            "added_by": "control-room",
            "reason_code": rng.choice(["RC-DEAL", "RC-MNPI", "RC-SURVEIL"]),
            "provenance": "synthetic — internal",
        })

    # --- wall crossings (Fluree, bitemporal) -------------------------------
    wall_crossings = []
    for i, issuer in enumerate(issuers[:RESTRICTED_COUNT]):
        # The banker crosses over the wall; a crossing is permanent history
        # and only its VALIDITY ends.
        effective = today - timedelta(days=rng.randint(30, 250))
        # Assertion time: the control room records it, sometimes a day or two
        # later. One crossing carries a deliberate lag so `as_of` on wall state
        # behaves like `as_of` on covenants.
        lag = 9 if i == 0 else rng.randint(0, 2)
        wall_crossings.append({
            "crossing_id": f"WALL-{i:03d}",
            "principal_id": "PRIN-COV-001",
            "lei": issuer["lei"],
            "valid_from": iso(effective),
            "valid_to": None,
            "asserted_at": iso(effective + timedelta(days=lag)),
            "recording_lag_days": lag,
            "basis": "deal engagement",
            "provenance": ("synthetic — engineered" if lag > 3
                           else "synthetic — internal"),
            "note": ("recording lag deliberately introduced so a surveillance "
                     "review at as_of sees a different wall state than one at "
                     "known_as_of" if lag > 3 else None),
        })

    # --- deals and interactions (Postgres) --------------------------------
    deals = []
    interactions = []
    for i in range(DEAL_COUNT):
        issuer = issuers[i % len(issuers)]
        is_mnpi = i % 3 == 0            # >= 10 MNPI-tagged
        opened = today - timedelta(days=rng.randint(20, 500))
        deals.append({
            "deal_id": f"DEAL-{i:04d}",
            "lei": issuer["lei"],
            "deal_type": rng.choice(DEAL_TYPES),
            "stage": rng.choice(DEAL_STAGES),
            "opened_date": iso(opened),
            "mnpi_bearing": is_mnpi,
            "estimated_fee_usd": rng.randrange(500_000, 25_000_000, 250_000),
            "provenance": "synthetic — internal",
        })
        for _ in range(rng.randint(1, 3)):
            when = opened + timedelta(days=rng.randint(1, 200))
            if when > today:
                continue
            interactions.append({
                "interaction_id": f"INT-{len(interactions):05d}",
                "lei": issuer["lei"],
                "deal_id": f"DEAL-{i:04d}",
                "interaction_type": rng.choice(INTERACTION_TYPES),
                "interaction_date": iso(when),
                "mnpi_bearing": is_mnpi,
                "provenance": "synthetic — internal",
            })

    # --- research notes (MongoDB) -----------------------------------------
    research = []
    for i in range(RESEARCH_COUNT):
        issuer = issuers[i % len(issuers)]
        # >= 8 in draft under embargo
        draft = i % 5 == 1
        authored = today - timedelta(days=rng.randint(5, 400))
        embargo_until = (authored + timedelta(days=rng.randint(3, 21))
                         if draft else None)
        research.append({
            "note_id": f"RES-{i:04d}",
            "lei": issuer["lei"],
            "title": f"{issuer['legal_name'][:38]} — "
                     f"{'initiation' if i % 4 == 0 else 'update'}",
            "body": (
                f"Rating {'initiated at' if i % 4 == 0 else 'maintained at'} "
                f"{rng.choice(['Buy', 'Hold', 'Sell'])}. Estimates reflect "
                f"reported results through the most recent filed period and "
                f"peer comparison at identical period ends. "
                + ("DRAFT — not for distribution; under embargo pending "
                   "supervisory review." if draft else
                   "Published and distributed to institutional clients.")
            ),
            "status": "draft" if draft else "published",
            "authored_date": iso(authored),
            "embargo_until": iso(embargo_until) if embargo_until else None,
            "classification": ("internal-restricted" if draft
                               else "public-filed"),
            "provenance": "synthetic — internal",
        })

    # --- positions (Postgres) ---------------------------------------------
    positions = []
    for i, issuer in enumerate(issuers):
        positions.append({
            "position_id": f"POS-{i:04d}",
            "lei": issuer["lei"],
            "quantity": rng.randrange(-500_000, 500_000, 1_000),
            "as_of": iso(today - timedelta(days=rng.randint(0, 2))),
            "book": rng.choice(["flow-credit", "flow-equity", "market-making"]),
            "provenance": "synthetic — internal",
        })

    # --- Reg FD event: private -> public, a WIDENING supersession ---------
    reg_fd = []
    target = issuers[0]
    disclosed = today - timedelta(days=45)
    reg_fd.append({
        "event_id": "REGFD-000",
        "lei": target["lei"],
        "disclosure_date": iso(disclosed),
        "item": "7.01",
        "description": "Material previously held on the private side was "
                       "publicly disclosed, converting it to public "
                       "information mid-series.",
        "widens_access": True,
        "provenance": "synthetic — internal",
        "note": "the only supersession trigger in the catalog that WIDENS "
                "rather than narrows access",
    })

    payload = {
        "generated_for": "Wave 7 — MNPI wall dataset",
        "seed": SEED,
        "issuers": issuers,
        "principals": PRINCIPALS,
        "restricted_list": restricted,
        "wall_crossings": wall_crossings,
        "deals": deals,
        "interactions": interactions,
        "research_notes": research,
        "positions": positions,
        "reg_fd_events": reg_fd,
    }
    (SCREEN / "mnpi_layer.json").write_text(json.dumps(payload, indent=2) + "\n")

    mnpi_deals = sum(1 for d in deals if d["mnpi_bearing"])
    drafts = sum(1 for r in research if r["status"] == "draft")
    lagged = [w for w in wall_crossings if w["recording_lag_days"] > 3]

    print(f"  issuers                {len(issuers):>4}   (§F asks ~10)")
    print(f"  on restricted list     {len(restricted):>4}   (§F floor 3)")
    print(f"  principals             {len(PRINCIPALS):>4}   (§F asks 3)")
    print(f"  deals                  {len(deals):>4}   (§F asks ~30)")
    print(f"    MNPI-tagged          {mnpi_deals:>4}   (§F floor 10)")
    print(f"  interactions           {len(interactions):>4}")
    print(f"  research notes         {len(research):>4}   (§F asks ~40)")
    print(f"    draft under embargo  {drafts:>4}   (§F floor 8)")
    print(f"  positions              {len(positions):>4}")
    print(f"  wall crossings         {len(wall_crossings):>4}   (§F floor 1)")
    print(f"    with recording lag   {len(lagged):>4}   engineered")
    print(f"  Reg FD events          {len(reg_fd):>4}   (§F floor 1, WIDENS)")
    print(f"\n  written: sources/screening/mnpi_layer.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
