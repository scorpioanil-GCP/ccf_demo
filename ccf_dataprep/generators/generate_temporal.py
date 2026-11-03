#!/usr/bin/env python3
"""Wave 5 — generate the bitemporal covenant layer for the flagship.

`covenant-in-force-as-of` turns on one distinction:

    as_of        VALID time      — when was this covenant in force?
    known_as_of  ASSERTION time  — when did the bank know it?

Assertion time cannot be sourced publicly. When a bank *booked* an amendment is
internal, and Q019 §5 calls the resulting engineered element "the single most
important engineered element in the catalog": at least one amendment must carry
a deliberate gap between effective date and booking date, **with a drawdown
falling inside that gap**. Without it both parameters return identical answers
for every query and the bitemporal model reads as redundant machinery.

Three lag cases are generated, at 4-8 weeks, so the pattern reads as a real
operational characteristic rather than a single planted trick.

Provenance, per element:

    public                 facility effective dates (EX-10 "dated as of");
                           covenant thresholds and their offsets, extracted
                           from filed text; amendment COUNTS (filing profile)
    synthetic — internal   amendment effective DATES -- derived by stepping
                           forward from the facility date, not read from the
                           8-K Item 1.01 filing
                           booking dates, drawdowns, breach thresholds,
                           policy version history, covenant types engineered
                           to reach the >= 4 per facility §F requires
    synthetic — engineered THE LAG CASES and the drawdowns inside their gaps;
                           the past-breach-now-compliant covenant

Output: sources/screening/temporal_layer.json

Run: uv run generators/generate_temporal.py
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, datetime, timedelta

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260817
LAG_CASES = 3
LAG_WEEKS = (4, 8)

#: §F: >= 4 covenant types per facility. Extraction yields ~1.7, so the
#: remainder is engineered from this conventional set and labelled.
COVENANT_TEMPLATES = [
    ("leverage", "max", 3.50, "ratio"),
    ("interest_coverage", "min", 3.00, "ratio"),
    ("fixed_charge_coverage", "min", 1.25, "ratio"),
    ("minimum_liquidity", "min", 50_000_000, "USD"),
    ("secured_leverage", "max", 2.75, "ratio"),
]


def iso(d: date) -> str:
    return d.isoformat()


def parse(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def main() -> int:
    rng = random.Random(SEED)
    today = date.today()

    covenant_docs = json.loads(
        (SCREEN / "covenants_extracted.json").read_text()
    )["documents"]
    extracted_by_accn: dict[str, list[dict]] = {}
    refs_by_accn: dict[str, list[dict]] = {}
    for doc in covenant_docs:
        if doc["covenants"]:
            extracted_by_accn[doc["accession"]] = doc["covenants"]
        if doc["definition_references"]:
            refs_by_accn[doc["accession"]] = doc["definition_references"]

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT facility_id, borrower_lei, facility_type, commitment_amount,
                   effective_date, maturity_date, amendment_count,
                   is_amended_restated, source_accession, outstanding_balance
            FROM "{PG_SCHEMA_V2}".facility
            ORDER BY facility_id
        """)
        facilities = [
            {
                "facility_id": r[0], "borrower_lei": r[1], "facility_type": r[2],
                "commitment": float(r[3]) if r[3] else None,
                "effective_date": r[4], "maturity_date": r[5],
                "amendment_count": r[6], "is_amended_restated": r[7],
                "accession": r[8],
                "outstanding": float(r[9]) if r[9] else None,
            }
            for r in cur.fetchall()
        ]

    print(f"Generating temporal layer for {len(facilities)} facilities\n")

    covenants: list[dict] = []
    amendments: list[dict] = []
    drawdowns: list[dict] = []
    engineered: list[str] = []

    # Facilities eligible to carry an engineered lag: they must have an
    # amendment and a known effective date to anchor the gap against.
    lag_pool = [
        f for f in facilities
        if (f["amendment_count"] > 0 or f["is_amended_restated"])
        and f["effective_date"]
    ]
    rng.shuffle(lag_pool)
    # Oversample: a facility can fail to accommodate a lag (no room between
    # its last amendment and today), so take more candidates than needed and
    # stop once LAG_CASES have actually been created.
    lag_facilities = {f["facility_id"] for f in lag_pool[: LAG_CASES * 4]}
    lag_created = 0

    for fac in facilities:
        eff = fac["effective_date"]
        if not eff:
            continue
        fid = fac["facility_id"]

        # --- covenants: extracted first, engineered to reach 4 types -------
        got: set[str] = set()
        for c in extracted_by_accn.get(fac["accession"], []):
            covenants.append({
                "facility_id": fid, "covenant_type": c["covenant_type"],
                "direction": c["direction"], "threshold": c["threshold"],
                "unit": c["unit"], "test_frequency": c["test_frequency"],
                "effective_from": iso(eff),
                "provenance": "public",
                "source_accession": fac["accession"],
                "source_offset": c["offset"],
            })
            got.add(c["covenant_type"])

        for ctype, direction, base, unit in COVENANT_TEMPLATES:
            if len(got) >= 4:
                break
            if ctype in got:
                continue
            jitter = rng.uniform(0.85, 1.2)
            threshold = (round(base * jitter, 2) if unit == "ratio"
                         else int(base * jitter / 1e6) * 1_000_000)
            covenants.append({
                "facility_id": fid, "covenant_type": ctype,
                "direction": direction, "threshold": threshold, "unit": unit,
                "test_frequency": "fiscal quarter",
                "effective_from": iso(eff),
                "provenance": "synthetic — internal",
                "note": "engineered to reach §F's >= 4 covenant types per "
                        "facility; EX-10 extraction yielded fewer",
            })
            got.add(ctype)

        # --- amendments: BOTH dates are derived, and labelled as such ------
        # An earlier version labelled amendment effective dates "public". They
        # are not. Only the FACILITY effective date is public (extracted from
        # the EX-10 "dated as of" clause). Amendment effective dates here are
        # stepped forward from it synthetically, because mapping each 8-K Item
        # 1.01 filing to the specific facility it amends was not done. The
        # count of amendments per facility IS public (from the filing profile);
        # the dates are not.
        n_amend = min(max(fac["amendment_count"], 1 if fac["is_amended_restated"] else 0), 3)
        if fid in lag_facilities:
            n_amend = max(n_amend, 2)

        prior = eff
        for i in range(n_amend):
            is_lag_case = (
                fid in lag_facilities
                and i == n_amend - 1
                and lag_created < LAG_CASES
            )

            if is_lag_case:
                # Place the lag case working BACKWARD from today, so both the
                # effective date and the later booking date land in the past.
                # Stepping forward could push the booking date into the future,
                # which is meaningless for an assertion time — a bank cannot
                # have booked something it has not booked yet.
                gap_days = rng.randint(LAG_WEEKS[0] * 7, LAG_WEEKS[1] * 7)
                latest_effective = today - timedelta(days=gap_days + 15)
                if latest_effective <= prior:
                    # No room between the last amendment and today; skip the
                    # lag here rather than fabricate an out-of-order history.
                    break
                span = (latest_effective - prior).days
                effective = prior + timedelta(days=rng.randint(1, max(1, span)))
                provenance = "synthetic — engineered"
            else:
                effective = prior + timedelta(days=rng.randint(120, 400))
                if effective >= today:
                    break
                gap_days = rng.randint(0, 4)
                provenance = "synthetic — internal"
            booked = effective + timedelta(days=gap_days)
            if booked >= today:
                break

            amendment = {
                "facility_id": fid,
                "amendment_number": i + 1,
                "effective_date": iso(effective),
                "booked_date": iso(booked),
                "booking_lag_days": gap_days,
                "effective_date_provenance": "synthetic — internal",
                "effective_date_note": (
                    "derived by stepping forward from the facility's public "
                    "effective date; NOT the 8-K Item 1.01 filing date. "
                    "Amendment COUNT is public; amendment DATES are not."
                ),
                "booking_date_provenance": provenance,
                "is_engineered_lag": is_lag_case,
            }
            amendments.append(amendment)

            if is_lag_case:
                # THE condition: a drawdown inside the gap. On the drawdown
                # date the bank was operating in good faith against the OLD
                # terms, having not yet booked the new ones.
                mid = effective + timedelta(days=max(1, gap_days // 2))
                drawdowns.append({
                    "facility_id": fid,
                    "drawdown_date": iso(mid),
                    "amount": round((fac["commitment"] or 50_000_000) * 0.18),
                    "falls_in_booking_gap": True,
                    "amendment_number": i + 1,
                    "provenance": "synthetic — engineered",
                    "note": f"inside the {gap_days}-day gap between amendment "
                            f"{i + 1} effective {iso(effective)} and booked "
                            f"{iso(booked)} — as_of and known_as_of diverge here",
                })
                lag_created += 1
                engineered.append(
                    f"{fid} amendment {i + 1}: effective {iso(effective)}, "
                    f"booked {iso(booked)} ({gap_days}d = "
                    f"{gap_days / 7:.1f} weeks), drawdown {iso(mid)} in gap"
                )
            prior = effective

        # --- ordinary drawdowns, spread across amendment boundaries -------
        for _ in range(rng.randint(2, 5)):
            span = (today - eff).days
            if span <= 30:
                continue
            when = eff + timedelta(days=rng.randint(15, max(16, span - 5)))
            drawdowns.append({
                "facility_id": fid,
                "drawdown_date": iso(when),
                "amount": round((fac["commitment"] or 50_000_000)
                                * rng.uniform(0.03, 0.25)),
                "falls_in_booking_gap": False,
                "provenance": "synthetic — internal",
            })

    # --- policy versions: >= 2 with distinct effective dates --------------
    policy_versions = [
        {
            "policy_version": "credit-policy-v1.0",
            "effective_from": iso(today - timedelta(days=1100)),
            "effective_to": iso(today - timedelta(days=420)),
            "leverage_breach_buffer": 0.00,
            "cure_period_days": 30,
            "provenance": "synthetic — internal",
        },
        {
            "policy_version": "credit-policy-v1.1",
            "effective_from": iso(today - timedelta(days=419)),
            "effective_to": None,
            "leverage_breach_buffer": 0.25,
            "cure_period_days": 45,
            "provenance": "synthetic — internal",
            "note": "buffer widened; evaluating a pre-2025 covenant against "
                    "this version produces an anachronism that reads as a "
                    "finding — which is why step 2 loads policy AS AT as_of",
        },
    ]

    # --- ENGINEERED: a covenant breached in the past, compliant today -----
    breach_targets = [c for c in covenants
                      if c["covenant_type"] == "leverage"][:2]
    breach_events = []
    for c in breach_targets:
        breach_date = today - timedelta(days=rng.randint(400, 800))
        breach_events.append({
            "facility_id": c["facility_id"],
            "covenant_type": c["covenant_type"],
            "breach_date": iso(breach_date),
            "observed_value": round(c["threshold"] * 1.18, 2),
            "threshold_at_breach": c["threshold"],
            "cured_date": iso(breach_date + timedelta(days=52)),
            "compliant_today": True,
            "provenance": "synthetic — engineered",
            "note": "breached at a past date, compliant now — so a forensic "
                    "query and a live query genuinely disagree",
        })
        engineered.append(
            f"{c['facility_id']} leverage breached {iso(breach_date)}, "
            f"cured, compliant today"
        )

    payload = {
        "generated_for": "Wave 5 — bitemporal covenant layer",
        "seed": SEED,
        "counts": {
            "covenants": len(covenants),
            "amendments": len(amendments),
            "drawdowns": len(drawdowns),
            "policy_versions": len(policy_versions),
            "breach_events": len(breach_events),
        },
        "engineered_elements": engineered,
        "covenants": covenants,
        "amendments": amendments,
        "drawdowns": drawdowns,
        "policy_versions": policy_versions,
        "breach_events": breach_events,
    }
    (SCREEN / "temporal_layer.json").write_text(json.dumps(payload, indent=2) + "\n")

    # --- report ------------------------------------------------------------
    by_facility: dict[str, set[str]] = {}
    for c in covenants:
        by_facility.setdefault(c["facility_id"], set()).add(c["covenant_type"])
    four_plus = sum(1 for v in by_facility.values() if len(v) >= 4)

    seq = {}
    for a in amendments:
        seq[a["facility_id"]] = seq.get(a["facility_id"], 0) + 1
    two_plus = sum(1 for v in seq.values() if v >= 2)

    lag = [a for a in amendments if a["is_engineered_lag"]]
    gap_draws = [d for d in drawdowns if d["falls_in_booking_gap"]]
    pub = sum(1 for c in covenants if c["provenance"] == "public")

    print(f"  covenants        {len(covenants):>5}  ({pub} public, "
          f"{len(covenants) - pub} engineered to reach 4/facility)")
    print(f"  amendments       {len(amendments):>5}")
    print(f"  drawdowns        {len(drawdowns):>5}")
    print(f"  policy versions  {len(policy_versions):>5}")
    print(f"  breach events    {len(breach_events):>5}")
    print(f"\n  §F CONDITIONS")
    print(f"    facilities with >= 4 covenant types   {four_plus:>3} / 40")
    print(f"    facilities with 2+ sequential amend   {two_plus:>3} / 3")
    print(f"    engineered booking-lag amendments     {len(lag):>3} / 1")
    print(f"    drawdowns inside a booking gap        {len(gap_draws):>3} / 1")
    print(f"    policy versions, distinct dates       "
          f"{len(policy_versions):>3} / 2")
    print(f"    past-breach-now-compliant covenants   {len(breach_events):>3} / 1")

    print(f"\n  ENGINEERED ELEMENTS (labelled in the data):")
    for note in engineered:
        print(f"    {note}")

    print(f"\n  written: sources/screening/temporal_layer.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
