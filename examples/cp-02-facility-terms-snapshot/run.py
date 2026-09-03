"""The client. It asks the question and prints the resulting JSON.

[ADAPT] all of it. [MECHANISM] nothing — this file makes no fabric call the
spine does not.

**The parameters are the CALLER's.** `debt_tolerance` and
`include_pricing_grid` are what a client sends, not configuration: the class
declares `debt_tolerance` REQUIRED with no default (§B.4), and a request
omitting it is refused as data before the graph is touched. Omitted from the
command line, this file asks the demonstration question declared in
`artifacts/question.yaml` — scenario material — so the example runs with no
arguments.

**`--facility` is what makes this product's findings visible.** The default is
the clean case. Three other facilities, named in `artifacts/expected.yaml` and
in the README, reach the three traps in one flag each: an inverted date pair
that serves with a NOT_EVALUABLE tenor, a facility with no maturity date, and
one REFUSED on `ttl-bounds` — which is 50 of the 60 facilities in this estate
and the finding this rung exists to surface.

**`--asked-at` is the one that proves the primitive.** Run the same facility at
two different instants and `expires_at` must not move. It is derived from the
credit agreement's own date, never from the question.
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

from ccf.agents.assembler import AssemblyOutcome  # noqa: E402
from ccf.agents.errors import AssemblyRefused  # noqa: E402
from ccf.contracts.canonical import content_hash  # noqa: E402
from ccf.products.request import ProductRequestViolation  # noqa: E402

import assembler  # noqa: E402
import deployment  # noqa: E402
import produce  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve one facility terms snapshot."
    )
    parser.add_argument(
        "--facility",
        help=(
            "a facility id. Defaults to the demonstration anchor in"
            " artifacts/question.yaml."
        ),
    )
    parser.add_argument(
        "--debt-tolerance",
        type=str,
        help="the caller's D_c ceiling (§B.4). Defaults to the artifact's.",
    )
    parser.add_argument(
        "--no-pricing-grid",
        action="store_true",
        help=(
            "omit the tiered pricing grid (§B.4). THE ONE PARAMETER THAT"
            " CHANGES THE PAYLOAD'S SHAPE, so it changes the content address."
        ),
    )
    parser.add_argument(
        "--principal",
        help=(
            "ask as a different principal (§D.3). The four the estate declares"
            " are PRIN-COV-001, PRIN-RES-002, PRIN-KYC-004 and PRIN-TRD-003."
            " Only PRIN-COV-001 carries facility-level need-to-know."
        ),
    )
    parser.add_argument(
        "--asked-at",
        help=(
            "the instant to ask as of, ISO-8601. `expires_at` MUST NOT MOVE"
            " when this does — that is the primitive this rung teaches."
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

    anchor = args.facility or deployment.demonstration_anchor()
    # `Decimal`, NOT `float`, and it is a measured constraint rather than a
    # style choice. `src/ccf/products/payload.py::_matches` admits `int` and
    # `Decimal` for a declared `number` and REFUSES a `float` with
    # `type-mismatch`. The artifact stores the value QUOTED, so it arrives as
    # text and the conversion happens here, at the caller's boundary, where a
    # client sending JSON would do it too.
    parameters: dict[str, object] = {
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            args.debt_tolerance
            if args.debt_tolerance is not None
            else deployment.demonstration_debt_tolerance()
        ),
        deployment.PARAM_INCLUDE_PRICING_GRID: (
            False
            if args.no_pricing_grid
            else deployment.demonstration_include_pricing_grid()
        ),
    }
    if args.as_of is not None:
        parameters["as_of"] = args.as_of

    question = deployment._declaration(deployment.QUESTION)
    asked_at = (
        datetime.fromisoformat(args.asked_at) if args.asked_at else None
    )
    asked = deployment.request(parameters=parameters, asked_at=asked_at)
    # The facility id is an address token, so a caller overriding it is asking
    # about a different instrument rather than passing a different parameter.
    if anchor != question["subject"]:
        asked = asked.model_copy(update={"subject": anchor})

    with tempfile.TemporaryDirectory(prefix="cp02-") as tmp:
        root = Path(tmp)
        # THE RUN GOES THROUGH THE ASSEMBLER SEAM, DELIBERATELY. Routing the
        # client through `src/ccf/agents/assembler.py::ContextAssemblerProtocol`
        # is what makes this example a pressure test of that seam rather than a
        # demonstration that reaches past it.
        captured: list[object] = []
        product = assembler.FacilityAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=(
                deployment.read
                if args.principal is None
                else lambda b, q: deployment.read(b, q, principal_id=args.principal)
            ),
            plan_class=deployment.plan_class(),
            observer=captured.append,
        )
        try:
            governed = product.assemble(
                request=asked,
                perspective=deployment.perspective(),
                tenant_id=deployment.tenant_id(),
            )
        except AssemblyRefused as refused:
            print(f"assembly refused: {refused}")
            return 1
        outcome = captured[0] if captured else governed
        if isinstance(governed, ProductRequestViolation):
            outcome = governed

        # BRANCHED ON AS DATA. Both refusals are values, not exceptions.
        if isinstance(outcome, produce.AnchorUnresolvable):
            print(f"{outcome.status} {outcome.reason}: {outcome.anchor}")
            return 1
        if not isinstance(outcome, produce.Assembled):
            print(f"refused: {outcome.reason} — {outcome.key}")
            if isinstance(outcome, ProductRequestViolation):
                print(f"   {outcome.detail}")
            return 1

        print(json.dumps(dict(outcome.product.payload), indent=2, sort_keys=True))
        _report(outcome, governed, asked_at=asked.asked_at)
    return 0


def _report(
    assembled: produce.Assembled, outcome: AssemblyOutcome, *, asked_at: datetime
) -> None:
    """What a plain SELECT would not have told you."""
    product = assembled.product
    debt = product.debt
    scenario = assembled.scenario
    print("\nWhat a plain SELECT would not have told you:")
    print(f"   asked as of        {asked_at.isoformat()}")
    print(f"   ttl basis          {scenario.ttl_basis_value}"
          f"   ({deployment.TTL_BASIS}, the agreement's own date)")
    print(f"   expires at         {product.expires_at.isoformat()}"
          f"   (ttl_anchor {product.ttl_anchor})")
    print("   ...which does NOT move when `asked as of` moves — that is the"
          " anchor")
    print(f"   context debt D_c   {debt.debt:.4f}  ->  {debt.signal}")
    print(f"   amendments         {scenario.resolved.attributes.get('amendment_count')}"
          f"   (a COUNT; this estate holds no amendment DATE)")
    print(f"   principal          {scenario.perspective.principal_id}"
          f"   need-to-know {scenario.sees_need_to_know},"
          f" {len(scenario.permitted_jurisdictions)} jurisdiction(s)")
    print(f"   operators invoked  {sorted(assembled.operators_invoked)}")
    print(f"   content address    {content_hash(product)}")
    print(f"   replay record      {content_hash(assembled.record)}")
    # TRANSCRIPT evidence of which implementation ran (`D-IMPL-245` am.1).
    # Decision Replay does not carry assembler identity today; this line is
    # the example's evidence, not a replay claim.
    print(f"   assembled by       {outcome.assembler_id}@{outcome.assembler_version}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
