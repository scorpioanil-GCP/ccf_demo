"""The client. Asks one question and prints what came back.

    export CCF_CP_11_POSTGRES_DSN=...   CCF_CP_11_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_11_FLUREE_URL=...     CCF_CP_11_FLUREE_LEDGER=fibo-v2
    make -s example-cp-11

Every request parameter is optional. Omitted, the program asks the
demonstration question in `artifacts/question.yaml` — an anchor, a delta bound
and a debt tolerance are **request** parameters, and a build tool is not a
request channel.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date, datetime
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
    parser.add_argument("--since", default=default.get("since"))
    parser.add_argument("--window-days", type=int, default=default["window_days"])
    parser.add_argument("--debt-tolerance", default=default.get("debt_tolerance"))
    arguments = parser.parse_args(argv)

    asked = deployment.request(
        anchor_lei=arguments.lei,
        asked_at=datetime.fromisoformat(arguments.as_of),
        intent=arguments.intent,
        since=date.fromisoformat(arguments.since) if arguments.since else None,
        window_days=arguments.window_days,
        debt_tolerance=arguments.debt_tolerance,
    )
    print(
        f"asked        {asked.subject} · {asked.intent}"
        f" · as of {asked.asked_at.isoformat()}"
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
        print(f"  SIC {obligor['sic']} -> sector {obligor['sector']}")

        delta = payload["delta"]
        print(
            f"\nDELTA  {delta['from']} -> {delta['to']}"
            f"  ({delta['anchor']}, basis {delta['basis']})"
            f"   {delta['signals_in_delta']} signals"
        )

        composite = payload["composite"]
        print(f"\nCOMPOSITE WARNING SCORE   {composite['score']}")
        for band in composite["bands"]:
            mark = "REACHED" if band["reached"] else "       "
            estate = composite["estate_declared"].get(band["intent"], "—")
            print(
                f"  {mark}  {band['intent']:<26} floor {band['floor']:>8}"
                f"   (estate declares {estate})"
            )
        print(f"  band in force: {composite['band'] or 'none — no escalation'}")

        states = payload["chain_states"]
        print("\nSUPERSESSION — one state per signal, and they partition")
        for name, count in states["states"].items():
            print(f"  {name:<20} {count:>4}")
        print(f"  {'total':<20} {states['total']:>4}"
              f"   (participating classes: {', '.join(states['participating_classes'])})")

        print("\nCLASS COVERAGE — an absent class is ABSENT, never a zero")
        for row in payload["class_coverage"]:
            note = "" if row["state"] == "present" else "   <- no evidence at all"
            print(f"  {row['signal_class']:<18} {row['state']:<8} {row['observations']:>4}{note}")

        contributing = payload["contributing"]
        print(f"\nCONTRIBUTING — {len(contributing)} signals, newest first")
        for row in sorted(contributing, key=lambda r: r["observed_at"], reverse=True)[:6]:
            item = f" item {row['item']}" if row["item"] else ""
            decay = "no decay" if row["decay_days"] is None else f"{row['decay_days']}d"
            print(
                f"  {row['observed_at']}  {row['signal_type']:<15}{item:<10}"
                f" w={row['weight']} x sev={row['severity']} x ret={row['retained']}"
                f" ({decay}, {row['age_days']}d old)  = {row['contribution']}"
            )
        if len(contributing) > 6:
            print(f"  … and {len(contributing) - 6} more")

        excluded = payload["excluded"]
        print(f"\nEXCLUDED — {len(excluded)}, and WHY (this is how 'why did it not escalate' is answered)")
        for row in excluded[:5]:
            print(f"  {row['observed_at']}  {row['signal_type']:<15} {row['reason']}")
            print(f"       {row['note']}")
        if len(excluded) > 5:
            print(f"  … and {len(excluded) - 5} more, all {excluded[0]['reason']}")

        withheld = payload["withheld"]
        if withheld["ambiguous_warn_matches"]:
            print(
                f"\nWITHHELD  {withheld['ambiguous_warn_matches']} ambiguous WARN"
                f" name matches\n  {withheld['reason']}"
            )

        debt = outcome.product.debt
        print(f"\ncontext debt D_c {debt.debt}   signal {debt.signal}")
        print(
            f"  F {debt.factors.freshness}"
            f"  C {debt.factors.completeness}"
            f"  S {debt.factors.semantic_consistency}"
        )
        print(
            "  NOTE: D_c measures how old and how complete the EVIDENCE is."
            "\n  The composite above measures what the evidence SAYS. They are"
            "\n  separate models and move independently (EWS-G29)."
        )
        print(f"expires_at       {outcome.product.expires_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
