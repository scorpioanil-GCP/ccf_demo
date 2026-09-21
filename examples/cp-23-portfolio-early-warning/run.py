"""Run the example and show a reader what came back.

[ADAPT] freely — presentation only.

Usage::

    export CCF_CP_23_POSTGRES_DSN=...  CCF_CP_23_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_23_FLUREE_URL=...    CCF_CP_23_FLUREE_LEDGER=fibo-v2
    export CCF_CP_23_TOKEN_COVERAGE=... CCF_CP_23_TOKEN_CREDIT=... CCF_CP_23_TOKEN_PRODUCT=... CCF_CP_23_TOKEN_UNGRANTED=...
    make -s example-cp-23
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
    parser.add_argument("--signal-classes", default=None, help="comma-separated signal types")
    parser.add_argument("--severity-floor", default=None)
    parser.add_argument("--debt-tolerance", default=None)
    parser.add_argument("--door", action="store_true")
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        params: dict[str, Any] = {deployment.AS_OF: arguments.as_of or arguments.asked_at}
        if arguments.signal_classes:
            params[deployment.SIGNAL_CLASSES] = [p for p in arguments.signal_classes.split(",") if p]
        if arguments.severity_floor is not None:
            params[deployment.SEVERITY_FLOOR] = arguments.severity_floor
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

        util = [r for r in payload["utilization"] if r["has_facility"] == "true"]
        if util:
            top = sorted(util, key=lambda r: -float(r["utilization_pct"] or 0))[:3]
            print(f"\n  UTILIZATION {len(util)} members with facilities")
            for row in top:
                print(f"    {row['lei']}  {row['utilization_pct']}% of {row['commitment']}"
                      f"  headroom {row['headroom']}")

        warn = payload["early_warning"]
        tiers: dict[str, int] = {}
        for row in warn:
            tiers[row["tier_label"]] = tiers.get(row["tier_label"], 0) + 1
        print(f"\n  EARLY WARNING {len(warn)} signals · " + " · ".join(
            f"{k} {v}" for k, v in sorted(tiers.items())))

        print("\n  FRESHNESS per class (weakest first — never one book average)")
        for row in payload["signal_freshness_by_class"]:
            print(f"    {row['signal_class']:26s} newest {row['newest_observed_at'][:10]}"
                  f"  {row['age_days']:>3s}d  {row['observations']:>4s} obs"
                  f"  {row['members_covered']:>2s} members")

        debt = payload["population_debt"]
        print(f"\n  POPULATION DEBT  rule={debt['rule']} ({debt['rule_authority']})"
              f" over {debt['members']} members")
        print(f"    F={debt['freshness']}  C={debt['completeness']}  S={debt['semantic_consistency']}"
              f"  ->  D_c={debt['debt']}")
        same = debt["max_member_debt"] == debt["debt"]
        print(f"    max(member D_c) would have been {debt['max_member_debt']}"
              + ("  — identical HERE, because one member sits at the floor on both weak"
                 " factors; the two laws differ in general, not in this book"
                 if same else
                 "  — different, because no single member carries every weak factor"))
        for factor, lei in sorted(debt["weakest_by_factor"].items()):
            print(f"    weakest {factor:22s} {lei}")

        if "covenant_history" in payload:
            cov = payload["covenant_history"]
            print(f"\n  COVENANT   {cov['active_breaches']} active · {cov['historical_breaches']}"
                  f" historical · {cov['cured_breaches']} cured")
        if "concentration" in payload:
            con = payload["concentration"]
            print(f"\n  CONCENTRATION basis={con['basis']} threshold={con['single_name_threshold_pct']}%"
                  f" ({con['threshold_authority']})")
            for row in con["by_name"][:3]:
                print(f"    {row['lei']}  {row['share_pct']}%  over={row['over_threshold']}")

        print(f"\n  findings   {len(payload['findings'])}")
        for finding in payload["findings"]:
            print(f"    {finding['finding']}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
