"""The client. It asks the question and prints the answer.

**This is the other side of ``D-IMPL-127``'s cut.** Production is
``produce.py`` + ``deployment.py``; access is here. Both halves run in one
process, and the boundary is still a file boundary — because remoteness is a
deployment fact rather than an architectural one. **HW-2 replaces this file and
nothing else**, which is how it will show that remoteness costs nothing and that
the client owns the question.

**The threshold is the caller's and this file supplies no default.** ``--min-
revenue`` is required. A default here would be the example quietly choosing the
caller's question, and it is exactly the shape that would let a reader mistake a
Context Product for a precalculated static object.

This module carries **no marker region**, so not one printed line is
published-snippet surface (``D-IMPL-125``). The governance transcript is behind
``--explain``; the default output is the question, the answer, and the four
things a plain ``SELECT`` does not return.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
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
        required=True,
        type=int,
        help="return companies whose revenue exceeds this (required, no default)",
    )
    parser.add_argument(
        "--as-of", help="the instant to ask as of, ISO-8601 with a zone"
    )
    parser.add_argument(
        "--explain", action="store_true", help="print the governance transcript"
    )
    args = parser.parse_args()

    with provision.provisioned():
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            outcome = produce.assemble_and_serve(
                manifest=deployment.MANIFEST,
                connection=deployment.connection(root=root),
                read=deployment.read,
                plan_class=deployment.plan_class(),
                request=deployment.request(
                    parameters={deployment.THRESHOLD_PARAMETER: args.min_revenue},
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
