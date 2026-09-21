"""Run the example and show a reader what came back.

[ADAPT] freely — presentation only.

Usage::

    export CCF_CP_24_POSTGRES_DSN=...  CCF_CP_24_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_24_FLUREE_URL=...    CCF_CP_24_FLUREE_LEDGER=fibo-v2
    export CCF_CP_24_TOKEN_COVERAGE=... CCF_CP_24_TOKEN_CREDIT=... CCF_CP_24_TOKEN_PRODUCT=... CCF_CP_24_TOKEN_UNGRANTED=...
    make -s example-cp-24
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
from ccf.contracts.canonical import content_hash  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"


def declaration() -> dict[str, Any]:
    return yaml.safe_load(QUESTION.read_text(encoding="utf-8"))["declaration"]


def main(argv: list[str]) -> int:
    declared = declaration()
    asked_defaults = dict(declared["question"])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=asked_defaults["subject"])
    parser.add_argument("--asked-at", default=asked_defaults["asked_at"])
    parser.add_argument("--intent", default=asked_defaults["intent"],
                        help="one of " + ", ".join(declared["priced_intents"]))
    parser.add_argument("--principal", default=asked_defaults["principal"])
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--members", default=None, help="comma-separated LEIs; canonicalized")
    parser.add_argument("--scenario", default=None,
                        help='JSON object, e.g. \'{"rate_shift_bp":150,"collateral_shift_bp":-1000}\'')
    parser.add_argument("--coverage-floor", default=None, help="in basis points")
    parser.add_argument("--debt-tolerance", default=None)
    parser.add_argument("--door", action="store_true")
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        params: dict[str, Any] = {deployment.AS_OF: arguments.as_of or arguments.asked_at}
        import json as _json  # noqa: PLC0415

        declared_scenario = dict(declared["scenario"])
        if arguments.scenario:
            declared_scenario = _json.loads(arguments.scenario)
        params[deployment.SCENARIO] = declared_scenario
        if arguments.coverage_floor is not None:
            params[deployment.COVERAGE_FLOOR] = int(arguments.coverage_floor)
        if arguments.debt_tolerance is not None:
            params["debt_tolerance"] = arguments.debt_tolerance

        from server.serve import perspective_by_principal  # noqa: PLC0415

        mapping = perspective_by_principal()
        perspective = Perspective(principal_id=arguments.principal,
                                  role=mapping.get(arguments.principal, "unmapped"))
        asked = produce.book_question(
            opened, book=arguments.book, asked_at=datetime.fromisoformat(arguments.asked_at),
            intent=arguments.intent, freshness=asked_defaults["freshness"],
            members=[m for m in (arguments.members or "").split(",") if m], **params,
        )
        print(f"asked        book {asked.subject} · {asked.intent} · decided {arguments.asked_at}"
              f" · as {perspective.principal_id} ({perspective.role})")
        outcome = opened.answer(asked, perspective=perspective)

        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED      {outcome.kind} · {outcome.reason}\n  {outcome.detail}")
            print(f"  replay     {outcome.replay_reference}")
            return 1

        product, payload = outcome.product, outcome.product.payload
        print(f"\nSERVED       {product.schema_name}@{product.schema_version}")
        print(f"  address    {content_hash(product)}")
        print(f"  debt       D_c={product.debt.debt if product.debt else 'n/a'}"
              f"  signal={product.debt.signal if product.debt else 'n/a'}")
        book = payload.get("book")
        if book is None:
            print("  book       (no such book — served computed-empty)")
            return 0
        print(f"  book       {book['banker_id']} · {book['banker_name']} · {book['banker_role']}"
              f" / {book['banker_desk']}")
        print(f"  population {payload['member_count']} members · digest {book['member_digest']}"
              f" · {book['facility_covered_count']} with a facility")

        sc, obs = payload["scenario"], payload["observed_state"]
        print(f"\n  ASSUMED    rate {sc['rate_shift_bp']}bp · collateral {sc['collateral_shift_bp']}bp"
              f" on {sc['collateral_class'] or '(none)'} · horizon {sc['horizon_months']}m"
              f"   [basis={sc['basis']}]")
        print(f"  OBSERVED   {obs['base_rate_series']} {obs['base_rate_pct']}%"
              f" at {obs['base_rate_observed_at']}   [basis={obs['basis']}]")
        print(f"             {obs['collateral_assets']} collateral observations,"
              f" ages {obs['collateral_age_days_min']}–{obs['collateral_age_days_max']} days")

        impact = payload["interest_impact"]
        if impact:
            top = sorted(impact, key=lambda r: -float(r["incremental_interest"] or 0))[:3]
            print(f"\n  INTEREST   {len(impact)} members with drawn balances")
            for row in top:
                print(f"    {row['lei']}  drawn {row['drawn_amount']}"
                      f"  {row['observed_rate_pct']}% -> {row['shifted_rate_pct']}%"
                      f"  +{row['incremental_interest']}  [{row['basis']}/{row['from_assumption']}]")

        if "collateral_impact" in payload:
            ci = payload["collateral_impact"]
            shifted = [r for r in ci if r["shift_applied"] == "true"]
            stale = sorted(ci, key=lambda r: -int(r["observed_age_days"] or 0))[:2]
            print(f"\n  COLLATERAL {len(ci)} assets · {len(shifted)} in the shifted class")
            for row in stale:
                print(f"    {row['asset_id']:10s} {row['category']:22s}"
                      f" observed {row['observed_valuation']} at {row['observed_at']}"
                      f" ({row['observed_age_days']}d old)")
                print(f"    {'':10s} {'stressed ->':22s} {row['stressed_valuation']}"
                      f"  — STILL {row['observed_age_days']}d old; arithmetic refreshes nothing")

        if "coverage_rollup" in payload:
            rr = payload["coverage_rollup"]
            print(f"\n  ROLL-UP    floor {rr['floor_bp']}bp · {rr['members_evaluated']} evaluated"
                  f" · {rr['members_below_floor']} below")
            for lei in rr["below_floor_leis"][:4]:
                print(f"    below: {lei}")

        debt = payload["population_debt"]
        print(f"\n  DEBT       rule={debt['rule']} over {debt['members']} members"
              f"  F={debt['freshness']} C={debt['completeness']} -> D_c={debt['debt']}")
        print(f"             observed evidence only; the scenario does not move it")

        print(f"\n  findings   {len(payload['findings'])}")
        for finding in payload["findings"]:
            print(f"    {finding['finding']}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
