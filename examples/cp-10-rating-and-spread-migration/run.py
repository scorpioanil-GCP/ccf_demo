"""The client. Asks one question and prints what came back.

    export CCF_CP_10_POSTGRES_DSN=...   CCF_CP_10_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_10_FLUREE_URL=...     CCF_CP_10_FLUREE_LEDGER=fibo-v2
    make -s example-cp-10

Every request parameter is optional. Omitted, the program asks the
demonstration question in `artifacts/question.yaml` — a build tool is not a
request channel, and an anchor, a window and a divergence threshold are
request parameters rather than deployment configuration.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import deployment  # noqa: E402
import produce  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"


def question() -> dict[str, Any]:
    """The demonstration question, from the artifact rather than from code."""
    document = yaml.safe_load(QUESTION.read_text(encoding="utf-8"))
    asked: dict[str, Any] = dict(document["declaration"]["question"])
    return asked


def main(argv: list[str]) -> int:
    default = question()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lei", default=default["lei"])
    parser.add_argument("--as-of", default=default["as_of"])
    parser.add_argument("--intent", default=default["intent"])
    parser.add_argument("--window-days", type=int, default=default["window_days"])
    parser.add_argument("--granularity", default=default["granularity"])
    parser.add_argument("--divergence-multiple", default=default["divergence_multiple"])
    parser.add_argument("--debt-tolerance", default=default["debt_tolerance"])
    arguments = parser.parse_args(argv)

    asked = deployment.request(
        anchor_lei=arguments.lei,
        asked_at=datetime.fromisoformat(arguments.as_of),
        intent=arguments.intent,
        window_days=arguments.window_days,
        granularity=arguments.granularity,
        divergence_multiple=arguments.divergence_multiple,
        debt_tolerance=arguments.debt_tolerance,
    )
    print(
        f"asked        {asked.subject} · {asked.intent}"
        f" · as of {asked.asked_at.isoformat()}"
        f" · {arguments.window_days}d window"
    )

    with tempfile.TemporaryDirectory() as scratch:
        outcome = produce.assemble_and_serve(asked=asked, root=Path(scratch))

        # BRANCH ON THE SDK's OWN TYPE. A governed *no* is an answer, and it
        # arrives as data rather than as an exception precisely so a client
        # cannot swallow it — so the client tests for it positively.
        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED      {outcome.kind}")
            print(f"  reason     {outcome.reason}")
            print(f"  detail     {outcome.detail}")
            print(
                "\n  The determination is preserved in the replay record; the"
                "\n  consumer envelope discloses less than the fabric recorded."
            )
            print(f"  replay     {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        obligor = payload["obligor"]
        print(f"\n{obligor['label']}  ·  {obligor['lei']}")
        print(f"benchmark basis  {payload['benchmark_basis']}")

        # THREE COMPONENTS, NEVER SUMMED. The headline number a naive product
        # would report is `benchmark + market_oas + idiosyncratic`, and §A.1 is
        # the record of what reporting it costs.
        print("\nSPREAD SERIES — per BOND, because a bond is what trades")
        for series in payload["spread_series"]:
            last = series["points"][-1] if series["points"] else {}
            print(
                f"  {series['instrument_id']:<14} {series['issue_band']:<4}"
                f" {str(series['tenor_years']):>4}y"
                f"  median {series['median_idiosyncratic_bp']:>8} bp"
                f"  ·  {series['observations']:>4} obs"
                f" {series['native_cadence']}→{series['resampled_cadence']}"
            )
            if last:
                print(
                    f"  {'':<14} latest {last['obs_date']}"
                    f"   benchmark {last['benchmark_bp']:>8}"
                    f" + market {last['market_oas_bp']:>8}"
                    f" + issuer {last['idiosyncratic_bp']:>8}  (never summed)"
                )

        summary = payload["obligor_spread_summary"]
        if summary:
            print("\nOBLIGOR-LEVEL SUMMARY — derived, and never travels alone")
            print(
                f"  blended median {summary['blended_median_idiosyncratic_bp']} bp"
                f"  over {summary['instrument_count']} instruments"
            )
            print(f"  per-bond medians {summary['dispersion']['per_bond_median_bp']}")
            print(f"  per-bond peaks   {summary['dispersion']['per_bond_peak_bp']}")
            print(f"  {summary['caution']}")

        print("\nDIVERGENCE EPISODES — per bond, against THAT bond's own median")
        if not payload["episodes"]:
            print("  none — no bond exceeded its own median by the requested multiple")
        for episode in payload["episodes"]:
            print(
                f"  {episode['instrument_id']:<14}"
                f" peak {episode['peak_idiosyncratic_bp']:>8} bp"
                f" on {episode['peak_date']}"
                f"  = {episode['multiple_of_own_median']}x its own"
                f" {episode['own_median_bp']} bp median"
            )
            grade = episode["grade_in_force_at_peak"]
            print(
                f"  {'':<14} grade in force at the peak:"
                f" {grade if episode['grade_evaluable'] else 'NOT EVALUABLE'}"
            )
            confirmation = episode["confirmation"]
            if confirmation["outcome"] != "changed":
                print(
                    f"  {'':<14} NOT CONFIRMED ({confirmation['outcome']})"
                    f" — {confirmation['why']}"
                )
                if confirmation["outcome"] == "unchanged":
                    print(
                        f"  {'':<14}   grade {confirmation['grade_in_force_throughout']}"
                        f" through {confirmation['reviews_after_peak']} later reviews"
                    )
                continue
            # ALL THREE TESTS PRINTED SEPARATELY (`RSM-G11`). Temporal
            # proximity alone is not confirmation: quarterly reviews land
            # every ~90 days, so SOME review is near any date.
            print(
                f"  {'':<14} next change {confirmation['from_grade']}"
                f" → {confirmation['to_grade']} on {confirmation['effective']}"
                f", {confirmation['lag_days']} days later"
            )
            print(
                f"  {'':<14}   later: {confirmation['is_later']}"
                f" · downgrade: {confirmation['is_downgrade']}"
                f" · off-cycle: {confirmation['is_off_cycle']}"
                f"  ->  CONFIRMS: {confirmation['confirms']}"
            )
            print(f"  {'':<14}   trigger: {confirmation['trigger']}")

        print("\nGRADE SERIES — two clocks, both served")
        for grade in payload["grade_series"]:
            print(
                f"  {str(grade['grade']):<5} from {grade['valid_from']}"
                f"  booked {grade['asserted_at']}"
                f" (+{grade['booking_lag_days']}d)"
                f"  {'off-cycle' if grade['off_cycle'] else 'on-cycle ':<9}"
                f"  {str(grade['scale_version'])}"
            )

        migration = payload["band_migration"]
        print("\nBAND MIGRATION — reported, never corrected")
        print(
            f"  issue bands {migration['issue_bands']}"
            f"  ·  grade band now {migration['current_grade_band']}"
            f"  ·  migrated: {migration['has_migrated_out_of_issue_band']}"
        )
        print(f"  {migration['effect_on_residual']}")

        print("\nSERIES REGISTER — each series carries its OWN cadence")
        for row in payload["series_register"]:
            print(
                f"  {row['series']:<38} {row['unit']:<10}"
                f" {row['window_from']} → {row['window_to']}"
                f"  {row['observations']:>4} obs"
            )

        debt = outcome.product.debt
        print(f"\ncontext debt D_c {debt.debt}   signal {debt.signal}")
        print(
            f"  F {debt.factors.freshness}"
            f"  C {debt.factors.completeness}"
            f"  S {debt.factors.semantic_consistency}"
        )
        print(f"expires_at       {outcome.product.expires_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
