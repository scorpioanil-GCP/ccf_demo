"""Ask one Context Product one question. This file is the whole example.

`docs/superpowers/specs/2026-08-15-ccf-client-design.md` §7. It knows the
product's identity and the question's parameters, and nothing else: no
manifest, no Control Plane key, no deployment type. Where the product lives is
`CCF_BINDING`'s business, and how it was assembled is `deployment/`'s.

What a `SELECT` would not have told you is everything printed after the
answer — the measured Context Debt, the address the answer hashes to, and the
replay record that authorized it. See README.md for the one documented command.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from ccf.client import ProductClient

# `D-05`: a scheme reaches the registry by its adapter module being imported.
# No plugin lookup, no discovery chain. TWO transports are imported and neither
# is chosen here — which one answers is `CCF_BINDING`'s business (see README).
import ccf.client.adapters.inprocess  # noqa: E402,F401
import ccf.client.adapters.mcp_stdio  # noqa: E402,F401


def parse_args() -> argparse.Namespace:
    """The three flags this example takes."""
    parser = argparse.ArgumentParser(description="Ask hw1.companies-over-revenue.")
    parser.add_argument(
        # `int`, not `float`: `WireRequest` refuses a float because canonical
        # JSON renders it as text, so the decoded echo differs from what was
        # sent — and that cross-check is live, so it fails a healthy wire.
        "--min-revenue", type=int, required=True, help="The revenue threshold."
    )
    parser.add_argument("--as-of", help="ISO 8601 boundary; UTC offset required.")
    parser.add_argument("--explain", action="store_true", help="Governance detail.")
    return parser.parse_args()


def main() -> int:
    """Ask, branch on the governed refusal, print the answer and its warrant."""
    args = parse_args()
    client = ProductClient.for_product("hw1.companies-over-revenue")
    result = client.ask(
        parameters={"revenue_threshold": args.min_revenue},
        as_of=datetime.fromisoformat(args.as_of) if args.as_of else None,
    )

    if result.refused:  # a refusal names a key only when it names one; a gate refusal names none
        print(f"refused: {result.refusal.reason}" + (f" — {result.refusal.key}" if result.refusal.key is not None else ""))
        return 1

    print(f"\nQ: which companies have revenue over {result.payload['threshold']}?")
    for company in result.payload["companies"]:
        print(f"   {company['name']:<30} {company['revenue']}")
    print(f"\n   {result.payload['count']} of {result.payload['assembled']} assembled")

    print("\nand what a SELECT would not have told you:")
    if result.debt is None:
        print("   context debt D_c   not assessed by this deployment")
    else:
        print(f"   context debt D_c   {result.debt.debt:.4f}  →  {result.debt.signal}")
    print(f"   content address    {result.content_address}")
    print(f"   replay record      {result.replay_ref}")
    print(f"   answer expires     {result.expires_at}")

    if args.explain:
        print("\ngovernance detail:")
        print(f"   perspective        {result.payload['role']}")
        print(f"   temporal boundary  {result.temporal_boundary}")
        print(f"   lineage            {result.lineage}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
