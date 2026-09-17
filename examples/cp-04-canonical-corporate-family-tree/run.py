"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else.

**It carries no marker region**, so nothing printed here is published-snippet
surface: an adopter copies ``produce.py``'s two regions, not this. It is also
the ONLY module in this example that writes to a terminal, which is what keeps
a printed line out of the spine.

Usage::

    export CCF_CP_04C_FLUREE_URL=...      CCF_CP_04C_FLUREE_LEDGER=...
    export CCF_CP_04C_POSTGRES_DSN=...    CCF_CP_04C_POSTGRES_SCHEMA=...
    make example-cp-04-canonical
    make example-cp-04-canonical LEI=--lei=<lei> MAX_DEPTH=--max-depth=2
    .venv/bin/python examples/cp-04-canonical-corporate-family-tree/run.py --door

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
from typing import Any

import deployment
import produce
from ccf.products.refusal import RefusalEnvelope

#: The family this example demonstrates against. An argument, not a constant in
#: the fabric's path — pass your own anchor to ask about another family.
DEMONSTRATION_ANCHOR = "549300FHJQTDPPN41627"

#: The intent and freshness this class serves — the request's own vocabulary.
INTENT = "credit-concentration"
FRESHNESS = "standard"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lei", default=DEMONSTRATION_ANCHOR)
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="omit entirely to let the class default resolve",
    )
    parser.add_argument(
        "--door", action="store_true",
        help="instead of asking once: boot the MCP egress door on an ephemeral 127.0.0.1"
             " port, print `READY {port}`, and serve questions from other processes until terminated",
    )
    parsed = parser.parse_args(argv[1:])

    if parsed.door:
        # The door is a fabric-facing module that writes to no terminal; the
        # readiness line a harness reads is this module's to print.
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    anchor = parsed.lei
    asked_depth = parsed.max_depth
    parameters: dict[str, Any] = {deployment.ANCHOR: anchor, deployment.FAMILIES: [anchor]}
    if asked_depth is not None:
        parameters[deployment.MAX_DEPTH] = asked_depth

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        asked = opened.question(
            subject=anchor, asked_at=datetime.now(UTC), intent=INTENT, freshness=FRESHNESS,
            parameters=parameters,
        )
        outcome = opened.answer(asked)
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
        print(f"context debt: D_c = {outcome.product.debt.debt}")
        print(f"       signal: {outcome.product.debt.signal}")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"replay      : {outcome.replay_ref.content_address}")
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
