"""The client. It asks the question and prints the answer.

**This is the other side of ``D-IMPL-127``'s cut.** Production is
``produce.py`` + ``deployment.py``; access is here. Both halves run in one
process, and the boundary is still a file boundary — because remoteness is a
deployment fact rather than an architectural one. **HW-2 replaces this file and
nothing else**, which is how it will show that remoteness costs nothing and that
the client owns the question.

**The threshold is the caller's, and it is a REQUEST parameter — not
configuration.** The product is assembled against the number at the moment it is
asked; two thresholds are two products with two content addresses
(``tests/examples/test_s1_00_output.py::test_two_thresholds_are_two_products``).
Nothing here is precomputed and waiting to be handed over.

``--min-revenue`` is therefore what a *client* sends. Omitted, this file asks the
demonstration question declared in ``scenario/question.yaml`` — scenario
material, the same category as the rows ``provision.py`` fabricates — so
``make example-s1-00`` runs with no arguments and a reader sees the fabric work
before they have to invent a number.

**That default lives here, not in the contract.** ``revenue_threshold`` stays
required: a request without one is refused at the door with
``missing-required-parameter`` before anything is assembled, asserted below this
CLI against the request layer by
``tests/examples/test_s1_00_output.py::test_a_missing_threshold_is_refused_not_defaulted``.
A CLI convenience and a contract obligation are different things, and this file
previously conflated them — it required the flag and made the first command a
newcomer types fail with an ``argparse`` error.

This module carries **no marker region**, so not one printed line is
published-snippet surface (``D-IMPL-125``). The governance transcript is behind
``--explain``; the default output is the question, the answer, and the four
things a plain ``SELECT`` does not return.
"""

from __future__ import annotations

import argparse
import sys
import tempfile

import yaml
from datetime import datetime
from pathlib import Path

# This example is a directory of modules rather than a package, so the two
# module trees it draws on go on the path before they are imported.
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scenario"))

import deployment  # noqa: E402
import produce  # noqa: E402
import provision  # noqa: E402

from ccf.contracts.canonical import content_hash  # noqa: E402
from ccf.products.request import ProductRequestViolation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Companies over a revenue you choose.")
    parser.add_argument(
        "--min-revenue",
        type=int,
        default=None,
        help=(
            "return companies whose revenue exceeds this. Omitted, the"
            " demonstration question in scenario/question.yaml is asked instead"
        ),
    )
    parser.add_argument(
        "--as-of", help="the instant to ask as of, ISO-8601 with a zone"
    )
    parser.add_argument(
        "--explain", action="store_true", help="print the governance transcript"
    )
    args = parser.parse_args()

    # The caller's number, or the demonstration's if this run supplied none.
    # Read from scenario material rather than defaulted in code or in the
    # Makefile: a request parameter is not deployment configuration, and a
    # build tool is not a request channel. The CONTRACT still requires it —
    # `refuse_request` returns `missing-required-parameter` for a request
    # without one, which is asserted below this CLI against the request layer.
    min_revenue = args.min_revenue
    if min_revenue is None:
        question = yaml.safe_load(
            (HERE / "scenario" / "question.yaml").read_text(encoding="utf-8")
        )
        min_revenue = int(question["demonstration"]["revenue_threshold"])

    with provision.provisioned():
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            outcome = produce.assemble_and_serve(
                manifest=deployment.MANIFEST,
                connection=deployment.connection(root=root),
                read=deployment.read,
                plan_class=deployment.plan_class(),
                request=deployment.request(
                    parameters={deployment.THRESHOLD_PARAMETER: min_revenue},
                    asked_at=(
                        datetime.fromisoformat(args.as_of) if args.as_of else None
                    ),
                ),
                root=root,
            )
            if isinstance(outcome, ProductRequestViolation):
                print(f"refused: {outcome.reason} — {outcome.key}")
                return 1
            report(outcome, explain=args.explain)
    return 0


def report(result: object, *, explain: bool) -> None:
    """Print the answer, then what the fabric added to it."""
    product = result.product  # type: ignore[attr-defined]
    payload = product.payload
    debt = product.debt

    print(f"\nQ: which companies have revenue over {payload['threshold']}?")
    print(f"   asked as of {product.temporal_boundary.isoformat()}\n")
    for entry in payload["companies"]:
        print(
            f"   {entry['name']:<24} {entry['revenue']:>13}"
            f"   updated {entry['last_updated'][:10]}"
        )
    print(f"\n   {payload['count']} of {payload['assembled']} companies\n")

    print("What a SELECT would not have told you:")
    print(
        f"   context debt D_c   {debt.debt:.4f}  ->  {debt.signal.value}"
        f"   (F={debt.factors.freshness:.4f} from last_updated on"
        f" {payload['assembled']} rows against the declared half-life)"
    )
    print(
        "   policy version     "
        + ", ".join(sorted(product.lineage.policy_bundle_versions))
    )
    print(f"   content address    {content_hash(product)}")
    print(
        f"   replay record      {result.served.replay_ref.content_address}"  # type: ignore[attr-defined]
    )

    if explain:
        print("\n--- governance transcript")
        print(f"   operators invoked  {sorted(product.lineage.operators_invoked)}")
        print(f"   assembly mode      {product.ttl_anchor}")
        print(f"   graph snapshot at  {product.lineage.graph_snapshot_at.isoformat()}")
        print(f"   expires at         {product.expires_at.isoformat()}")
        print(f"   completeness C     {debt.factors.completeness}")
        print(f"   semantic consist.  {debt.factors.semantic_consistency}")


if __name__ == "__main__":
    raise SystemExit(main())
