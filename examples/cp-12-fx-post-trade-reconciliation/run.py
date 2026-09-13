"""The client. Asks one question and prints what came back.

    export CCF_CP_12_POSTGRES_DSN=...   CCF_CP_12_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_12_FLUREE_URL=...     CCF_CP_12_FLUREE_LEDGER=fibo-v2
    make -s example-cp-12

Every request parameter is optional. Omitted, the program asks the
demonstration question in `artifacts/question.yaml` — the trades, the
comparison instant, the alignment and a debt tolerance are **request**
parameters, and a build tool is not a request channel.
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
    parser.add_argument("--trades", nargs="+", default=default["trades"])
    parser.add_argument("--scope", default=default["scope"])
    parser.add_argument("--as-of", default=default["as_of"])
    parser.add_argument("--intent", default=default["intent"])
    parser.add_argument("--compare-at", default=default["compare_at"],
                        choices=["amendment-0", "latest"])
    parser.add_argument("--no-align-clocks", action="store_true")
    parser.add_argument("--materiality-pips", default=default.get("materiality_pips"))
    parser.add_argument("--debt-tolerance", default=default.get("debt_tolerance"))
    arguments = parser.parse_args(argv)

    asked = deployment.request(
        trades=arguments.trades,
        scope=arguments.scope,
        asked_at=datetime.fromisoformat(arguments.as_of),
        intent=arguments.intent,
        compare_at=arguments.compare_at,
        align_clocks=not arguments.no_align_clocks,
        materiality_pips=arguments.materiality_pips,
        debt_tolerance=arguments.debt_tolerance,
    )
    print(
        f"asked        {asked.subject} · {asked.intent}"
        f" · as of {asked.asked_at.isoformat()}"
    )
    print(
        f"             compare_at={asked.parameters['compare_at']}"
        f"  align_clocks={asked.parameters['align_clocks']}"
        f"  {len(asked.parameters['trades'])} trades"
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
        comparison = payload["comparison"]
        print(
            f"\nmateriality  {comparison['materiality_pips']} pips"
            f"   ({comparison['intent']}, from the estate's own table)"
            f"\ntick series  resolves to {comparison['tick_spacing_seconds']} s"
            "  — below that, nothing is decomposable"
        )

        counts = payload["verdict_counts"]
        print(
            f"\nVERDICTS over {payload['observations']} trades"
            "   — ONE per trade, and the count of this list IS the count of"
            " observations"
        )
        for name, count in counts.items():
            print(f"  {name:<16} {count:>4}")

        print("\nPER TRADE")
        for row in payload["reconciliations"]:
            d = row["decomposition"]
            named = row["divergent_system"] or "—"
            print(
                f"\n  {row['trade_id']}  {row['pair']:<8} {row['verdict']:<14}"
                f" divergent={named:<11} (estate designated"
                f" {row['estate_designated_class'] or '—'})"
            )
            print(f"     notional band {row['notional_band']}"
                  f"   groups {row['agreement_groups']}")
            for system in row["systems"]:
                print(
                    f"     {system['system']:<11} amd {system['amendment_seq']}"
                    f"  rate {system['value_rate']:<10}"
                    f" recorded {system['recorded_at'][11:19]}"
                    f"  offset {system['clock_offset_seconds']:>5}s"
                    f"  corrected {(system['corrected_at'] or '-')[11:19]}"
                )
            if d["state"] == "evaluated":
                print(
                    f"     total {d['total_pips']} pips ="
                    f" timing {d['timing_attributable_pips']}"
                    f" + residual {d['residual_pips']}"
                    f"   (closes={d['closes']}, gap"
                    f" {float(d["compared_gap_seconds"]):.0f}s)"
                )
                if d.get("note"):
                    print(f"       {d['note']}")
            elif d["state"] == "not-evaluable":
                print(f"     total {d['total_pips']} pips, DECOMPOSITION REFUSED"
                      f" — {d['reason']}")
                print(f"       {d['note']}")
                print("       timing and residual are NULL, not zero. A zero"
                      " would be a claim rather than a measurement.")

        print("\nABSENT LEGS — absent, not empty and not zero (CP12-F-01)")
        for leg, state in payload["absent_legs"].items():
            print(f"  {leg:<32} {state}")

        debt = outcome.product.debt
        print(f"\ncontext debt D_c {debt.debt}   signal {debt.signal}")
        print(
            f"  F {debt.factors.freshness}"
            f"  C {debt.factors.completeness}"
            f"  S {debt.factors.semantic_consistency}"
        )
        print(
            "  NOTE: F ages each system's leading edge against the instant that"
            "\n  system RECORDED — never the corrected instant. The correction"
            "\n  is this product's alignment model and reaches no fabric"
            "\n  temporal field (FXR-G24)."
        )
        # THE PRODUCT'S OWN ADDRESS, read off the replay record rather than
        # recomputed here. A client that hashed the payload itself would be
        # asserting the address rather than reading the one the fabric bound
        # its decision to.
        print(
            "content address  "
            f"{outcome.record.content_generation_path.product_content_address}"
        )
        print(f"replay record    {outcome.served.replay_ref.content_address}")
        print(f"expires_at       {outcome.product.expires_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
