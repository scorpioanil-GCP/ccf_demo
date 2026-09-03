"""The client. It asks the question and prints the resulting JSON.

[ADAPT] all of it. [MECHANISM] nothing — this file makes no fabric call the
spine does not.

**The parameters are the CALLER's.** `intent` and `debt_tolerance` are declared
REQUIRED with no default (§B.4), and a request omitting either is refused as
data before the graph is touched. Omitted from the command line, this file asks
the demonstration question declared in `artifacts/question.yaml` — scenario
material — so the example runs with no arguments.

**`--basis` IS THE FLAG THIS RUNG EXISTS FOR.** `as-reported` returns each
figure as it was FILED for that period; `latest-restated` returns it as most
recently amended. **Both settings are correct**, which no parameter in the
catalog before this one could say — a covenant test asks what was reported at
the time, a trend analysis asks for the restated series, and the decision picks.
Run the same obligor both ways and the content addresses differ, because the
answers differ.

**`--asked-at` PINS THE TRANSCRIPT.** The demonstrated run assembles over the
instant named in `question.yaml`, so the printed output reproduces byte for
byte. The bar is SAME QUESTION → SAME ANSWER, not correspondence with the live
world: a reader whose numbers differ has re-derived, not replayed. No `load_*`
step appears anywhere on this path — the 321 restatements this product
demonstrates are already in the estate.

**`--principal` IS THE ENTITLEMENT FLAG, and it changes WHICH OBLIGORS EXIST**
rather than how they are shaped (§B.2). The four principals this estate
declares see 49, 47, 0 and 0 of its 50 obligors. A principal who may not see
this obligor gets the same refusal as one asking about an obligor that is not
there.
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
        description="Serve one obligor financial spread."
    )
    parser.add_argument(
        "--lei",
        help=(
            "an obligor LEI. Defaults to the demonstration anchor in"
            " artifacts/question.yaml. 36 other obligors in this estate carry"
            " a restatement to look at."
        ),
    )
    parser.add_argument(
        "--periods",
        type=int,
        help="how many periods of history to spread (§B.4). Defaults to the artifact's.",
    )
    parser.add_argument(
        "--basis",
        choices=(deployment.BASIS_AS_REPORTED, deployment.BASIS_LATEST_RESTATED),
        help=(
            "THE PARAMETER THIS RUNG EXISTS FOR. Both settings are correct and"
            " the decision picks; for a restated obligor they produce different"
            " content addresses."
        ),
    )
    parser.add_argument(
        "--no-peers",
        action="store_true",
        help="omit the peer cohort comparison (§B.4).",
    )
    parser.add_argument(
        "--peer-basis",
        help="how the peer cohort is drawn — sic or sic-and-size (§B.4).",
    )
    parser.add_argument(
        "--debt-tolerance",
        type=str,
        help="the caller's D_c ceiling (§B.4). Defaults to the artifact's.",
    )
    parser.add_argument(
        "--principal",
        help=(
            "ask as a different principal (§B.2). The four this estate declares"
            " are PRIN-RES-002 (49 of 50 obligors), PRIN-COV-001 (47),"
            " PRIN-KYC-004 (0) and PRIN-TRD-003 (0)."
        ),
    )
    parser.add_argument(
        "--asked-at",
        help=(
            "the instant to ask as of, ISO-8601. The demonstrated run uses the"
            " pin in artifacts/question.yaml so the transcript reproduces."
        ),
    )
    parser.add_argument(
        "--as-of",
        help=(
            "DECLARED BUT INERT at this tier (§B.5) — this must be refused with"
            " not_supported_at_tier, never silently succeed."
        ),
    )
    args = parser.parse_args(argv)

    declared = deployment.demonstration_parameters()
    anchor = args.lei or deployment.demonstration_anchor()

    # `Decimal`, NOT `float`, and it is a measured constraint rather than a
    # style choice. `src/ccf/products/payload.py::_matches` admits `int` and
    # `Decimal` for a declared `number` and REFUSES a `float` with
    # `type-mismatch`. The artifact stores the value QUOTED, so it arrives as
    # text and the conversion happens here, at the caller's boundary, where a
    # client sending JSON would do it too.
    parameters: dict[str, object] = {
        deployment.PARAM_INTENT: declared[deployment.PARAM_INTENT],
        deployment.PARAM_PERIODS: (
            args.periods
            if args.periods is not None
            else int(declared[deployment.PARAM_PERIODS])
        ),
        deployment.PARAM_BASIS: (
            args.basis
            if args.basis is not None
            else str(declared[deployment.PARAM_BASIS])
        ),
        deployment.PARAM_INCLUDE_PEERS: (
            False
            if args.no_peers
            else bool(declared[deployment.PARAM_INCLUDE_PEERS])
        ),
        deployment.PARAM_PEER_BASIS: (
            args.peer_basis
            if args.peer_basis is not None
            else str(declared[deployment.PARAM_PEER_BASIS])
        ),
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            args.debt_tolerance
            if args.debt_tolerance is not None
            else str(declared[deployment.PARAM_DEBT_TOLERANCE])
        ),
    }
    if args.as_of is not None:
        parameters[deployment.PARAM_AS_OF] = args.as_of

    asked_at = datetime.fromisoformat(args.asked_at) if args.asked_at else None
    asked = deployment.request(parameters=parameters, asked_at=asked_at)
    # The LEI is an address token, so a caller overriding it is asking about a
    # different obligor rather than passing a different parameter.
    if anchor != deployment.demonstration_anchor():
        asked = asked.model_copy(update={"subject": anchor})

    with tempfile.TemporaryDirectory(prefix="cp03-") as tmp:
        root = Path(tmp)
        # THE RUN GOES THROUGH THE ASSEMBLER SEAM, DELIBERATELY. Routing the
        # client through `src/ccf/agents/assembler.py::ContextAssemblerProtocol`
        # is what makes this example a pressure test of that seam rather than a
        # demonstration that reaches past it.
        captured: list[object] = []
        product = assembler.SpreadAssembler(
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
    periods = scenario.periods
    restated = sorted(
        {name for period in periods for name in period.restated_lines}
    )
    classes = sorted({period.signal_class for period in periods})
    print("\nWhat a plain SELECT would not have told you:")
    print(f"   asked as of        {asked_at.isoformat()}")
    print(f"   basis applied      {scenario.basis}"
          f"   (both settings are correct; the decision picks)")
    # BOTH NUMBERS, because they differ and the difference is the point. The
    # request asks for a number of PERIOD ENDS; the spread returns a number of
    # COLUMNS, and a non-December filer carries two columns at one period end —
    # an `FY` cell and a quarterly cell. Printing only the second would look
    # like the deployment ignored the parameter.
    print(f"   period ends asked  {scenario.request.parameters.get(deployment.PARAM_PERIODS)}"
          f"   -> {len({p.period_end for p in periods})} returned,"
          f" {len(periods)} columns")
    print(f"   decay rates        {classes}"
          f"   ...ONE product, {len(classes)} half-life class(es) — §E.1")
    print(f"   latest filing      {scenario.latest_filed_in_payload}"
          f"   (the TTL anchor, and it MOVES as the obligor files)")
    print(f"   expires at         {product.expires_at.isoformat()}"
          f"   (ttl_anchor {product.ttl_anchor})")
    print(f"   restated lines     {restated or 'none in this window'}")
    # THE ANNOTATION TRACKS THE VALUE. It used to read "an Item 4.02 exists"
    # unconditionally, which printed beside `False` for every obligor that had
    # not filed one — a label contradicting the value it labelled, in the line
    # whose whole subject is that the filing corroborates rather than detects.
    filed_402 = scenario.resolved.has_non_reliance_filing
    print(f"   formally restated  {filed_402}"
          f"   ({'an Item 4.02 exists' if filed_402 else 'no Item 4.02'}"
          f" — CORROBORATION, never the detector)")
    # DECOMPOSED, because one number hides which half is speaking. F falls as
    # the history window widens — an eight-period spread averages a current
    # quarter against filings two years old — so this product's debt reading is
    # driven by the parameter that makes it a spread at all.
    print(f"   context debt D_c   {debt.debt:.4f}  ->  {debt.signal}")
    print(f"   ...decomposed      F={debt.factors.freshness:.4f}"
          f"  C={debt.factors.completeness:.4f}"
          f"  S={debt.factors.semantic_consistency}"
          f"   (S cannot move: one store, §E.2)")
    print(f"   principal          {scenario.perspective.principal_id}"
          f"   {len(scenario.permitted_jurisdictions)} jurisdiction(s) granted")
    print(f"   operators invoked  {sorted(assembled.operators_invoked)}")
    print(f"   policy version     "
          f"{sorted(product.lineage.policy_bundle_versions)}")
    print(f"   content address    {content_hash(product)}")
    print(f"   replay record      {content_hash(assembled.record)}")
    # TRANSCRIPT evidence of which implementation ran (`D-IMPL-245` am.1).
    # Decision Replay does not carry assembler identity today; this line is
    # the example's evidence, not a replay claim.
    print(f"   assembled by       {outcome.assembler_id}@{outcome.assembler_version}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
