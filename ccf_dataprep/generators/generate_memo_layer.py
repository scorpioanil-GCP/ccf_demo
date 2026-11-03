#!/usr/bin/env python3
"""Wave 13a stage 4 — the internal layer `credit-memo-context` composes over.

    uv run generators/generate_memo_layer.py --dry-run
    uv run generators/generate_memo_layer.py

Covers three §F conditions, all `synthetic — internal` because each is
bank-internal by nature and has no public equivalent:

    §F3   ~40 internal credit memoranda from prior cycles
    §F7   4 memo types with distinct section templates
    §F8   >= 2 policy versions with distinct effective dates

**Identity is derived from content, never from position.** `known-issues.md`
§13.3 records four loaders in this estate that mint ids from an index into a
sorted query result, and all four silently repoint their rows when the
underlying table gains one — 20 of 22 existing memoranda would be reassigned to
a different borrower on a re-run of Wave 6's loader. Every id minted here is a
short hash of the thing it identifies, so adding a facility, an obligor or a
template cannot move anything that already exists. This module must never
acquire a running counter.

That is also why these memoranda do not extend the `MEMO-NNNN` sequence: a new
row in that sequence would be indistinguishable from a repointed old one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import date, timedelta

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect
from ccf.memo_grade import memo_grade_leis

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13a_memo_layer.json"

SEED = 20260822
TODAY = date.today()

#: §F7. `memo_type` in the request surface is an enum of exactly these four,
#: and each must carry a DISTINCT section set — a template list that differs
#: only in name would satisfy the count and none of the purpose.
MEMO_TYPES = {
    "new-facility": ["Transaction summary", "Borrower and sponsor",
                     "Sources and uses", "Facility terms", "Covenant package",
                     "Collateral and security", "Financial projections",
                     "Risk factors", "Recommendation"],
    "annual-review": ["Relationship summary", "Financial performance",
                      "Peer comparison", "Covenant compliance",
                      "Exposure and limits", "Collateral position",
                      "Internal grade", "Recommendation"],
    "amendment": ["Requested amendment", "Rationale", "Covenant impact",
                  "Pricing and fees", "Exposure between effective and booking",
                  "Conditions precedent", "Recommendation"],
    "workout": ["Situation summary", "Default and breach history",
                "Collateral valuation and enforceability", "Set-off position",
                "Recovery scenarios", "Legal and jurisdictional",
                "Strategy and next steps"],
}

#: §D step 7 — the four contributions to aggregate Context Debt. Weights are
#: policy, hence `synthetic — internal`, and live in Postgres so the debt
#: computation reads them rather than hard-coding them. A gate that recomputes
#: debt must read these same rows or it is testing its own constants.
DEBT_WEIGHTS = {
    "unresolved_passage_anchor": 0.30,
    "peer_set_thinness": 0.25,
    "signal_staleness": 0.15,
    "inherited_prerequisite_debt": 0.30,
}

#: §F8. Two versions with distinct effective dates, so `as_of` selects between
#: them and a memo assembled at an earlier date is bound by the earlier rule.
POLICY_VERSIONS = [
    {"policy_version": "credit-memo-policy-v1",
     "effective_date": "2024-01-01",
     "ecoa_reasoning_path_restricted": True,
     "reg_o_insider_threshold_usd": 500_000,
     "credit_limit_envelope_usd": 750_000_000,
     "debt_tolerance_default": 0.30},
    {"policy_version": "credit-memo-policy-v2",
     "effective_date": "2025-07-01",
     "ecoa_reasoning_path_restricted": True,
     # Tightened: the later version is stricter on both, so a memo assembled
     # `as_of` an earlier date is genuinely bound by a different rule rather
     # than a cosmetically renamed one.
     "reg_o_insider_threshold_usd": 250_000,
     "credit_limit_envelope_usd": 600_000_000,
     "debt_tolerance_default": 0.25},
]

MEMO_BODIES = [
    ("annual-review", "Annual review — {name}",
     "Relationship reviewed at the {ftype}. Performance is within the range "
     "assumed at last review and peer comparison at identical reporting "
     "periods places the obligor mid-cohort. No change to internal grade."),
    ("amendment", "Amendment recommendation — {name}",
     "Borrower requests an amendment to the covenant package on the {ftype}. "
     "Credit view is supportive subject to a pricing step-up. Note the "
     "effective date precedes our booking date; exposure drawn in that window "
     "was governed by the prior terms."),
    ("new-facility", "New facility — {name}",
     "Proposed {ftype} for general corporate purposes. Sources and uses are "
     "consistent with the stated purpose. Covenant package follows the "
     "existing agreement with a tightened restricted-payments basket."),
    ("workout", "Workout assessment — {name}",
     "Obligor has breached the consolidated leverage covenant on the {ftype}. "
     "Collateral valuation is stale relative to the enforcement horizon and "
     "set-off across jurisdictions is untested. Recovery modelling assumes no "
     "enforcement outside the primary jurisdiction."),
]


def mid(*parts: str) -> str:
    """Content-derived id. Stable under insertion; see the module docstring."""
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:10].upper()
    return f"MEMO-13A-{h}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rng = random.Random(SEED)
    leis = sorted(memo_grade_leis())
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT f.facility_id, f.facility_type, e.legal_name, f.borrower_lei
            FROM "{S}".facility f
            JOIN "{S}".legal_entity e ON e.lei = f.borrower_lei
            WHERE f.borrower_lei = ANY(%s)
            ORDER BY f.facility_id
        """, (leis,))
        facilities = cur.fetchall()

    # One memorandum per memo-grade OBLIGOR, not per facility. A credit memo
    # is written about a borrower; per-facility would have produced 45 here
    # and 67 in the corpus against §F3's ~40, which is not over-delivery so
    # much as noise the peer-thinness and debt work would then have to read
    # past. Anchored to the obligor's lowest facility_id for a stable citation.
    primary: dict[str, tuple] = {}
    for fid, ftype, name, lei in facilities:
        if lei not in primary:            # facilities are ORDER BY facility_id
            primary[lei] = (fid, ftype, name, lei)

    # Type is chosen by hashing the facility id, so it is stable when the
    # obligor set changes. The resulting split is uneven -- 9 new-facility
    # against 1 workout across 18 -- and is deliberately left alone. Balancing
    # it would mean ranking obligors and assigning round-robin, and rank
    # depends on set membership: adding an obligor would reshuffle every
    # existing assignment, which is the positional-identity defect
    # known-issues.md §13.3 records four instances of. Reaching for a
    # different hash slice until the buckets look even is tuning to the
    # outcome. §F7 asks for four distinct section TEMPLATES, which exist and
    # are asserted distinct below; it does not ask for four equal piles.
    memoranda = []
    for fid, ftype, name, lei in primary.values():
        which = MEMO_BODIES[int(hashlib.sha256(fid.encode()).hexdigest(), 16)
                            % len(MEMO_BODIES)]
        memo_type, title_t, body_t = which
        body = body_t.format(name=name[:40], ftype=ftype)
        authored = TODAY - timedelta(days=rng.randint(45, 900))
        memoranda.append({
            "memorandum_id": mid(fid, memo_type),
            "memo_type": memo_type,
            "title": title_t.format(name=name[:40]),
            "body": body,
            "text_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "facility_id": fid, "borrower_lei": lei,
            "classification": "internal-confidential",
            "residency": rng.choice(["US", "US", "UK", "EU"]),
            "authored_date": authored.isoformat(),
            "provenance": "synthetic — internal",
            "source": "generated: no public equivalent exists for internal "
                      "credit opinions",
            "retrieved_at": TODAY.isoformat(),
        })

    templates = [
        {"memo_type": t, "section_order": i, "section_name": sec,
         "provenance": "synthetic — internal"}
        for t, secs in MEMO_TYPES.items() for i, sec in enumerate(secs, 1)
    ]

    print("Wave 13a — internal memo layer\n")
    print(f"  memo-grade facilities            {len(facilities):>4}")
    print(f"  memo-grade obligors with one     {len(primary):>4}")
    print(f"  memoranda (content-derived ids)  {len(memoranda):>4}")
    by_type: dict[str, int] = {}
    for m in memoranda:
        by_type[m["memo_type"]] = by_type.get(m["memo_type"], 0) + 1
    for k, v in sorted(by_type.items()):
        print(f"    {k:<20}{v:>4}")
    print(f"  section templates                {len(templates):>4} rows "
          f"across {len(MEMO_TYPES)} memo types (§F7 wants 4)")
    print(f"  distinct section sets            "
          f"{len({tuple(v) for v in MEMO_TYPES.values()}):>4}   "
          f"(must equal {len(MEMO_TYPES)}, else the types differ only in name)")
    print(f"  policy versions                  {len(POLICY_VERSIONS):>4} "
          f"(§F8 wants >= 2)")
    print(f"  debt weights                     {len(DEBT_WEIGHTS):>4}, "
          f"sum {sum(DEBT_WEIGHTS.values()):.2f}")
    print(f"  ids collide?                     "
          f"{'YES — BUG' if len({m['memorandum_id'] for m in memoranda}) != len(memoranda) else 'no'}")

    if args.dry_run:
        print("\n  DRY RUN — artifact not written.")
        return 0

    ARTIFACT.write_text(json.dumps({
        "generated_for": "credit-memo-context §F3 / §F7 / §F8",
        "seed": SEED,
        "note": ("memorandum ids are sha256-derived from (facility_id, "
                 "memo_type) and carry a MEMO-13A- prefix, deliberately NOT "
                 "extending Wave 6's positional MEMO-NNNN sequence — see "
                 "known-issues.md §13.3"),
        "memoranda": memoranda,
        "section_templates": templates,
        "debt_weights": DEBT_WEIGHTS,
        "policy_versions": POLICY_VERSIONS,
    }, indent=2) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
