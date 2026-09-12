"""The client. Asks one question and prints what came back.

    export CCF_CP_09_POSTGRES_DSN=...   CCF_CP_09_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_09_FLUREE_URL=...     CCF_CP_09_FLUREE_LEDGER=fibo-v2
    make -s example-cp-09

Every request parameter is optional. Omitted, the program asks the
demonstration question in `artifacts/question.yaml` — a build tool is not a
request channel, and a threshold, an anchor and an as-of date are request
parameters rather than deployment configuration.
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
from ccf.replay.serve import ServedProduct  # noqa: E402

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
    parser.add_argument("--currencies", default=None)
    parser.add_argument("--max-staleness", default=default["max_staleness"])
    arguments = parser.parse_args(argv)

    asked = deployment.request(
        anchor_lei=arguments.lei,
        asked_at=datetime.fromisoformat(arguments.as_of),
        intent=arguments.intent,
        currencies=(
            arguments.currencies.split(",") if arguments.currencies else None
        ),
        max_staleness={"intraday-rate": arguments.max_staleness},
    )
    print(f"asked        {asked.subject} · {asked.intent} · as of {asked.asked_at.isoformat()}")

    with tempfile.TemporaryDirectory() as scratch:
        outcome = produce.assemble_and_serve(asked=asked, root=Path(scratch))

        if not isinstance(outcome, produce.Assembled):
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
        client = payload["client"]
        liquidity = payload["liquidity"]
        concentration = payload["concentration"]

        print(f"\n{client['label']}  ·  mandate {client['mandate_id']}  ·  home {client['home_currency']}")

        print("\nLIQUIDITY")
        for row in liquidity["by_currency"]:
            converted = row["balance_in_home"] or "NOT EVALUABLE"
            print(
                f"  {row['currency']}  {row['account_count']:>2} accounts"
                f"  {row['balance']:>18}  ->  {converted:>18}"
            )
        print(f"  {'':>4}{'':>12}{'':>21}total  {liquidity['home_currency_total']:>18}")

        print("\nCONCENTRATION")
        for row in concentration["counterparties"]:
            limit = row["limit_pct"] or "—"
            print(
                f"  {row['verdict']:<14} {row['share_pct']:>6}%  of limit {limit:>6}"
                f"   {row['counterparty_label']}"
            )
        coverage = concentration["limit_coverage"]
        counts = concentration["verdict_counts"]
        print(
            f"  coverage: {coverage['covered']} of {coverage['counterparties']}"
            f" counterparties carry a limit"
            f"   ({counts['breach']} breach, {counts['within-limit']} within,"
            f" {counts['limit-unknown']} not evaluable)"
        )

        print("\nREGULATORY POSTURE IN FORCE")
        for row in payload["regulatory_posture"]:
            print(
                f"  {row['jurisdiction']:<6} {row['level']:<18}"
                f" effective {row['valid_from']}   {row['version_id']}"
            )

        print("\nSIGNAL REGISTER")
        for row in payload["signal_register"]:
            print(
                f"  {row['signal_class']:<14} {str(row['signal_id']):<16}"
                f" observed {row['observed_at']}  age {row['age_seconds']:>7}s"
                f"  [{row['source']}]"
            )
        for absent in payload["absent_signal_sources"]:
            print(f"  {'absent':<14} {absent:<16} holds no observation at this instant")

        filing = payload["filing_evidence"]
        if filing and filing["status"] == "reported":
            print(
                f"\nFILING EVIDENCE  reported cash {filing['reported_cash']}"
                f" as of period end {filing['period_end']}"
                f"  ({filing['days_since_period_end']} days ago,"
                f" {filing['temporal_class']})"
            )
        elif filing:
            print(
                f"\nFILING EVIDENCE  period end {filing['period_end']} closes"
                f" AFTER this decision instant — not yet knowable, and"
                f" withheld rather than served as look-ahead"
            )

        debt = outcome.product.debt
        print(f"\ncontext debt D_c {debt.debt}   signal {debt.signal}")
        print(f"expires_at       {outcome.product.expires_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
