"""The client. It asks the question and prints the resulting JSON.

[ADAPT] all of it. [MECHANISM] nothing — this file makes no fabric call the
spine does not.

**The parameters are the CALLER's.** `debt_tolerance` and `include_lapsed` are
what a client sends, not configuration: the class declares `debt_tolerance`
REQUIRED with no default (§B.4), and a request omitting it is refused as data
before the graph is touched. Omitted from the command line, this file asks the
demonstration question declared in `artifacts/question.yaml` — scenario
material — so the example runs with no arguments and a reader sees the fabric
work before they have to invent a value.

**`--anchor` is what makes the two identity authorities visible.** The default
is the LEI-registered demonstration entity; pass an internal client id and the
same code path resolves through the internal client master instead, with a
different freshness ceiling in the payload (§C.3). That asymmetry is the point
of the rung, and it is one flag away rather than a second example.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from ccf.contracts.canonical import content_hash  # noqa: E402

import deployment  # noqa: E402
import produce  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve one counterparty reference snapshot."
    )
    parser.add_argument(
        "--anchor",
        help=(
            "an LEI(20) or an internal client id. Defaults to the demonstration"
            " anchor in artifacts/question.yaml."
        ),
    )
    parser.add_argument(
        "--debt-tolerance",
        type=float,
        help="the caller's D_c ceiling (§B.4). Defaults to the artifact's.",
    )
    parser.add_argument(
        "--include-lapsed",
        action="store_true",
        help="return an entity whose registration has lapsed (§B.4).",
    )
    parser.add_argument(
        "--principal",
        help=(
            "ask as a different principal (§D.3). The four the estate declares"
            " are PRIN-COV-001, PRIN-RES-002, PRIN-KYC-004 and PRIN-TRD-003."
        ),
    )
    parser.add_argument(
        "--as-of",
        help=(
            "DECLARED BUT INERT at this tier (§B.4) — this must be refused"
            " with not_supported_at_tier, never silently succeed."
        ),
    )
    args = parser.parse_args(argv)

    anchor = args.anchor or deployment.demonstration_anchor()
    # `Decimal`, NOT `float`, and it is a measured constraint rather than a
    # style choice. `src/ccf/products/payload.py::_matches` admits `int` and
    # `Decimal` for a declared `number` and REFUSES a `float` with
    # `type-mismatch` — while `yaml.safe_load` hands back exactly a float for
    # `0.25`. So the conversion happens HERE, at the caller's boundary, where a
    # client sending JSON would do it too. Recorded at spec §F.4: a request
    # surface whose numeric type admits the two forms a YAML artifact does not
    # produce will be met by every adopter who declares a fractional parameter.
    parameters: dict[str, object] = {
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            str(
                args.debt_tolerance
                if args.debt_tolerance is not None
                else deployment.demonstration_debt_tolerance()
            )
        ),
        deployment.PARAM_INCLUDE_LAPSED: (
            args.include_lapsed or deployment.demonstration_include_lapsed()
        ),
    }
    if args.as_of is not None:
        parameters["as_of"] = args.as_of

    question = deployment._declaration(deployment.QUESTION)
    asked = deployment.request(parameters=parameters)
    # The anchor is an address token, so a caller overriding it is asking about
    # a different entity rather than passing a different parameter.
    if anchor != question["subject"]:
        asked = asked.model_copy(update={"subject": anchor})

    with tempfile.TemporaryDirectory(prefix="cp01-") as tmp:
        root = Path(tmp)
        outcome = produce.assemble_and_serve(
            config=deployment.CONFIG,
            connection=deployment.connection(root=root),
            read=(
                deployment.read
                if args.principal is None
                else lambda b, q: deployment.read(b, q, principal_id=args.principal)
            ),
            plan_class=deployment.plan_class(),
            request=asked,
            root=root,
        )

        # BRANCHED ON AS DATA. Both refusals are values, not exceptions —
        # a bad question and a missing entity are not broken deployments.
        if isinstance(outcome, produce.AnchorUnresolvable):
            print(f"{outcome.status} {outcome.reason}: {outcome.anchor}")
            return 1
        if not isinstance(outcome, produce.Assembled):
            print(f"refused: {outcome.reason} — {outcome.key}")
            return 1

        print(json.dumps(dict(outcome.product.payload), indent=2, sort_keys=True))
        _report(outcome, asked_at=asked.asked_at)
    return 0


def _report(assembled: produce.Assembled, *, asked_at: datetime) -> None:
    """What a plain SELECT would not have told you."""
    product = assembled.product
    debt = product.debt
    scenario = assembled.scenario
    print("\nWhat a plain SELECT would not have told you:")
    print(f"   asked as of        {asked_at.isoformat()}")
    print(f"   expires at         {product.expires_at.isoformat()}"
          f"   (ttl_anchor {product.ttl_anchor})")
    print(f"   context debt D_c   {debt.debt:.4f}  ->  {debt.signal}")
    print(f"   identity authority {scenario.resolved.authority}")
    print(f"   freshness ceiling  {scenario.resolved.freshness_ceiling_days} day(s)"
          f"   (signal class {scenario.resolved.signal_class})")
    print(f"   principal          {scenario.perspective.principal_id}"
          f"   sees {len(scenario.permitted_jurisdictions)} jurisdiction(s)")
    print(f"   operators invoked  {sorted(assembled.operators_invoked)}")
    print(f"   content address    {content_hash(product)}")
    print(f"   replay record      {content_hash(assembled.record)}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
