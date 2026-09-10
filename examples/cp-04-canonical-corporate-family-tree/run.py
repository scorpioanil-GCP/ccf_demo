"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else.

**It carries no marker region**, so nothing printed here is published-snippet
surface: an adopter copies ``produce.py``'s three regions, not this. It is also
the ONLY module in this example that writes to a terminal, which is what keeps
a printed line out of the spine.

Usage::

    export CCF_CP_04C_FLUREE_URL=...      CCF_CP_04C_FLUREE_LEDGER=...
    export CCF_CP_04C_POSTGRES_DSN=...    CCF_CP_04C_POSTGRES_SCHEMA=...
    make example-cp-04-canonical
    make example-cp-04-canonical LEI=--lei=<lei> MAX_DEPTH=--max-depth=2

``--max-depth`` omitted asks the question WITHOUT the parameter, so the class
default resolves — which is a different thing from passing the default's value,
and the run prints which happened.

**Named flags rather than positional arguments**, so a depth supplied without an
anchor cannot silently land in the anchor's slot and be read as an LEI.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import deployment
import produce
from ccf.products.refusal import RefusalEnvelope

#: The family this example demonstrates against. An argument, not a constant in
#: the fabric's path — pass your own anchor to ask about another family.
DEMONSTRATION_ANCHOR = "549300FHJQTDPPN41627"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lei", default=DEMONSTRATION_ANCHOR)
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="omit entirely to let the class default resolve",
    )
    parsed = parser.parse_args(argv[1:])
    anchor = parsed.lei
    asked_depth = parsed.max_depth

    asked = deployment.request(
        anchor_lei=anchor,
        # Ordinarily the anchor's own family. A caller entitled to two families
        # can name both without a second code path.
        families=[anchor],
        asked_at=datetime.now(UTC),
        max_depth=asked_depth,
    )

    with tempfile.TemporaryDirectory() as scratch:
        outcome = produce.assemble_and_serve(asked=asked, root=Path(scratch))

        print(f"anchor      : {anchor}")
        print(
            "max_depth   : "
            + (
                f"{asked_depth} (as asked)"
                if asked_depth is not None
                else "absent — the class default resolves"
            )
        )

        if isinstance(outcome, RefusalEnvelope):
            # A refusal is an ANSWER, not a crash: the question was governed and
            # the verdict was no. It carries the reason and the decision record
            # that authorized saying it.
            print(f"\nREFUSED     : {outcome.reason}")
            print(f"replay      : {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        findings = payload["findings"]
        print(f"depth served: {payload['depth_served']}")
        print()
        print(f"family      : {payload['node_count']} entities")
        print(f"relations   : {payload['relationship_count']} typed family edges")
        print(
            f"resolved    : {payload['resolved_count']} of {payload['node_count']}"
            " carry attributes from the second store"
        )
        print(
            f"cycles      : {findings['cycles_found']} ownership circuits,"
            f" enumerated to length {findings['max_length_enumerated']}"
        )
        print()
        # The two things a SELECT could not have told you.
        print(f"context debt: D_c = {outcome.product.debt.debt}")
        print(f"       signal: {outcome.product.debt.signal}")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"replay      : {outcome.served.replay_ref.content_address}")

        if findings["cycles"]:
            first = findings["cycles"][0]
            print()
            print("first circuit, as a finding rather than an error:")
            for member in first["members"]:
                print(f"    {member}")
            print(
                f"    closes: {first['closing_edge']['subject']}"
                f" -> {first['closing_edge']['object']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
