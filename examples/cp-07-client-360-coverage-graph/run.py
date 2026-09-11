"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else. It carries no
marker region, so nothing printed here is published-snippet surface, and it is
the ONLY module in this example that writes to a terminal.

Usage::

    make example-cp-07
    make example-cp-07 LEI=--lei=529900L7KB2N9KXCDI76      # the untruncated control
    make example-cp-07 LEI=--lei=549300FA4CTCW903Y781      # the STALE client — D_c crosses forced_llm
    make example-cp-07 LIMIT=--limit=50                    # force the boundary lower
    make example-cp-07 NTK=--need-to-know                  # a different graph, not a redacted one

Every flag is OMITTED unless you pass it, so the class default in
``ccf_config.yaml`` resolves — a different act from passing the default's value.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import deployment
import produce
from ccf.products.refusal import RefusalEnvelope

#: The client this example demonstrates against, and the scope its caller is
#: entitled to walk. Arguments, not constants in the fabric's path.
DEMONSTRATION_LEI = "JJAX4X60DE65EYFOTY73"

#: The negative control: fewer interactions than the bound, so nothing is cut.
#: Named here so a reader can run both without reading the tests.
CONTROL_LEI = "529900L7KB2N9KXCDI76"

#: The FRESHNESS control — the stalest relationship in the estate that still
#: has a graph. Nobody at the bank has spoken to anyone here since 2026-07-22,
#: and at the declared λ_c that is enough to push `D_c` past the `forced_llm`
#: threshold while the other two anchors stay `ok`. It is what makes the
#: freshness term visibly a measurement rather than a constant.
FRESHNESS_CONTROL_LEI = "549300FA4CTCW903Y781"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Client 360 / coverage graph")
    parser.add_argument("--lei", default=DEMONSTRATION_LEI)
    parser.add_argument("--scope", default=None,
                        help="defaults to the client's own LEI")
    parser.add_argument("--since", default=None,
                        help="omit to let the class default resolve")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-family", dest="family", action="store_false",
                        default=None)
    parser.add_argument("--need-to-know", dest="need_to_know", action="store_true",
                        default=None)
    parsed = parser.parse_args(argv[1:])

    asked = deployment.request(
        lei=parsed.lei, principal_scope=[parsed.scope or parsed.lei],
        asked_at=datetime.now(UTC), since=parsed.since, limit=parsed.limit,
        include_family=parsed.family, include_need_to_know=parsed.need_to_know)

    with tempfile.TemporaryDirectory() as scratch:
        outcome = produce.assemble_and_serve(asked=asked, root=Path(scratch))

        print(f"client      : {parsed.lei}")
        if isinstance(outcome, RefusalEnvelope):
            # A refusal is an ANSWER, not a crash: the question was governed and
            # the verdict was no. It carries the reason and the record that
            # authorized saying it.
            print(f"\nREFUSED     : {outcome.reason}")
            print(f"replay      : {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        boundary, found = payload["evidence_boundary"], payload["findings"]
        print(f"name        : {payload['client']['name']}")
        print(f"window      : since {payload['window']['since']},"
              f" limit {payload['window']['limit']}")
        print()

        # THE ACQUISITION BOUNDARY, said out loud. This is rung 7's whole point:
        # a graph can be populated and still be incomplete.
        print("evidence boundary")
        print(f"   interactions admitted   : {boundary['interactions_admitted']}")
        print(f"   interactions available  : {boundary['interactions_available']}")
        print(f"   withheld (need-to-know) : {boundary['withheld_need_to_know']}")
        print(f"   TRUNCATED               : {boundary['truncated']}")
        if boundary["truncated"]:
            print(f"   {boundary['note']}")
        print()

        print("relationship strength — who actually knows this client")
        for banker in payload["bankers"][:8]:
            covers = " (assigned)" if banker["covers_client"] else ""
            print(f"   {banker['relationship_strength']:>8}  {banker['banker']:12s}"
                  f" {(banker['name'] or '?'):24s} {banker['interactions']:>4} met"
                  f"  last {banker['most_recent'] or '—'}{covers}")

        # THE THING A CRM FIELD CANNOT CONTAIN. "Who covers this client?" is a
        # field. "Whom has nobody met?" is a path.
        print("\nwhat a CRM field could not have told you")
        print(f"   client-side officers seen  : {len(payload['people'])}")
        print(f"   coverage gaps              : {found['coverage_gaps']}")
        print(f"   of those, MATERIAL roles   : {found['material_coverage_gaps']}")
        print(f"   never met by anyone        : {found['never_met']}")
        print(f"   bankers formally assigned  : {found['bankers_covering']}")
        print(f"   edge types in the graph    : {', '.join(found['edge_types_present'])}")
        for gap in found["gaps"][:8]:
            flag = "  <<< MATERIAL" if gap["material"] else ""
            print(f"       {gap['gap_kind']:9s} {(gap['name'] or gap['person']):26s}"
                  f" {(gap['role'] or '?'):28s}"
                  f" strength {gap['best_relationship_strength']}{flag}")

        print()
        debt = outcome.product.debt
        print(f"context debt: D_c = {debt.debt}")
        print(f"       signal: {debt.signal}")
        print(f"     freshness: {debt.factors.freshness}"
              "   (how recently each party was last in contact)")
        print(f"  completeness: {debt.factors.completeness}"
              "   (every walked party was admitted and named)")
        print("       (the acquisition bound is disclosed above and is NEVER"
              " scored as debt)")
        print("       (half-lives are ILLUSTRATIVE for this point-in-time"
              " estate — see README.md)")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"replay      : {outcome.served.replay_ref.content_address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
