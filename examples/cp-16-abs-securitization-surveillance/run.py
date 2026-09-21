"""Run the example and show a reader what came back.

[ADAPT] freely — presentation only. This is the ONLY module in this example
that writes to a terminal.

Usage::

    export CCF_CP_16_POSTGRES_DSN=...    CCF_CP_16_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_16_FLUREE_URL=...      CCF_CP_16_FLUREE_LEDGER=fibo-v2
    export CCF_CP_16_MONGO_URI=...       CCF_CP_16_MONGO_DB=fibo_v2
    export CCF_CP_16_TOKEN_DESK=...      CCF_CP_16_TOKEN_RISK=... CCF_CP_16_TOKEN_REPORTING=... CCF_CP_16_TOKEN_UNGRANTED=...
    make -s example-cp-16
    .venv/bin/python examples/cp-16-abs-securitization-surveillance/run.py --door
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
    parser.add_argument("--deal", default=asked_defaults["subject"], help="the anchor deal")
    parser.add_argument("--asked-at", default=asked_defaults["asked_at"])
    parser.add_argument("--intent", default=asked_defaults["intent"],
                        help="one of " + ", ".join(declared["priced_intents"]))
    parser.add_argument("--principal", default=asked_defaults["principal"])
    parser.add_argument("--as-of", default=None, help="the reporting period AND the decision instant")
    parser.add_argument("--granularity", default=None, help="deal | tranche | cohort | loan")
    parser.add_argument("--cohorts", default=None, help="comma-separated credit bands; passed as a LIST")
    parser.add_argument("--loan-sample", default=None, help="rows MATERIALIZED at loan granularity")
    parser.add_argument("--debt-tolerance", default=None)
    parser.add_argument("--door", action="store_true", help="serve the standard MCP door on a loopback port")
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: arguments.as_of or arguments.asked_at}
        if arguments.granularity is not None:
            parameters[deployment.GRANULARITY] = arguments.granularity
        if arguments.cohorts is not None:
            # DECLARED AS AN ARRAY, so it is passed as a LIST. A comma string
            # is refused by the SDK as a type mismatch, which is correct.
            parameters[deployment.COHORTS] = [part for part in arguments.cohorts.split(",") if part]
        if arguments.loan_sample is not None:
            parameters[deployment.LOAN_SAMPLE] = arguments.loan_sample
        if arguments.debt_tolerance is not None:
            parameters["debt_tolerance"] = arguments.debt_tolerance

        from server.serve import perspective_by_principal  # noqa: PLC0415

        mapping = perspective_by_principal()
        perspective = Perspective(
            principal_id=arguments.principal,
            role=mapping.get(arguments.principal, "unmapped"),
        )
        asked = opened.question(
            subject=arguments.deal, asked_at=datetime.fromisoformat(arguments.asked_at),
            intent=arguments.intent, freshness=asked_defaults["freshness"], parameters=parameters,
        )
        print(f"asked        {asked.subject} · {asked.intent} · decided {arguments.asked_at}"
              f" · as {perspective.principal_id} ({perspective.role})")
        outcome = opened.answer(asked, perspective=perspective)

        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED      {outcome.kind} · {outcome.reason}")
            print(f"  {outcome.detail}")
            print(f"  replay     {outcome.replay_reference}")
            return 1

        product = outcome.product
        payload = product.payload
        print(f"\nSERVED       {product.schema_name}@{product.schema_version}")
        print(f"  address    {content_hash(product)}")
        print(f"  record     {outcome.replay_ref.content_address}")
        print(f"  debt       D_c={product.debt.debt if product.debt else 'n/a'}"
              f"  signal={product.debt.signal if product.debt else 'n/a'}")
        deal = payload.get("deal")
        if deal is None:
            print("  deal       (no reporting period at this instant — served computed-empty)")
            return 0
        print(f"  deal       {deal['deal_id']} · {deal['legal_name']}")
        print(f"             {deal['credit_tier']} · vintage {deal['vintage']} · period {deal['period']}")
        print(f"  granularity requested={payload['requested_granularity']}"
              f" effective={payload['effective_granularity']} ceiling={payload['granularity_ceiling']}")

        pool = payload["pool_performance"]
        print(f"\n  pool       balance {pool['pool_balance']} · delinquency {pool['delinquency_percent']}%"
              f" · {pool['receivable_count']} receivables")
        print(f"             the FILED servicer report publishes trigger {pool['published_delinquency_trigger']}%"
              f" (occurred={pool['published_trigger_occurred']})")

        print(f"\n  triggers   {len(payload['triggers'])} in force at {payload['as_of']}")
        for trigger in payload["triggers"]:
            mark = "anchored" if trigger["anchored"] == "true" else "UNANCHORED"
            supersedes = f" supersedes {trigger['supersedes']}" if trigger["supersedes"] else ""
            print(f"    {trigger['trigger_id']:<52} {trigger['threshold_value'] or '(formula)':>10}"
                  f" {trigger['threshold_unit']:<18} {mark}{supersedes}")
        for row in payload["trigger_proximity"]:
            if row.get("distance") is not None:
                print(f"    proximity  {row['trigger_id']:<50} {row['distance']} points"
                      f" (breached={row.get('breached')})")
            else:
                print(f"    proximity  {row['trigger_id']:<50} uncomputable")

        if payload["unanchored_thresholds"]:
            print(f"\n  UNANCHORED {len(payload['unanchored_thresholds'])} threshold(s) served with no filed passage:")
            for row in payload["unanchored_thresholds"]:
                print(f"    {row['trigger_id']} · classified {row['source_classification']}")

        for member in ("tranches", "cohort_performance", "loan_sample_detail", "repurchase_activity"):
            if member in payload:
                print(f"  {member:<24} {len(payload[member])}")
        print(f"  benchmark  {payload['benchmark_comparison'].get('delinquency_vs_vintage', 'n/a')}"
              f" points vs vintage")

        cost = payload["assembly_cost"]
        print(f"\n  COST       {cost['records_materialized']} records materialized"
              f" · {cost['records_scanned']} scanned · {cost['blocks_scanned']} blocks"
              f" · band {cost['cost_band']}")
        print(f"             next: {cost['next_level_down']['granularity'] or '(none)'}"
              f" — {cost['next_level_down']['consequence']}")

        print(f"\n  findings   {len(payload['findings'])}")
        for finding in payload["findings"]:
            print(f"    {finding['finding']:<40} {finding['subject']}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
