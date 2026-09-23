"""Ask for one packaged memo, or serve them from a door.

    .venv/bin/python examples/dr-02-package-a-context-product/run.py
    .venv/bin/python examples/dr-02-package-a-context-product/run.py --door

**This rung needs an upstream door running.** Its substrate is another
product, so start that product's door first and export the URL it announces:

    .venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
    export CCF_DR_02_UPSTREAM_URL=http://127.0.0.1:<port>/mcp

That dependency is the point rather than an inconvenience: Assembly Mode 2
packages an *already-governed* product, and a demonstration that read a store
directly would be demonstrating a different thing.
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

#: The upstream's own demonstration facility and borrower scope — passed
#: straight through, because this deployment resolves no subject of its own.
DEMONSTRATION_FACILITY = "FAC-5B8418"
DEMONSTRATION_SCOPE = "2549001IGRCG4F0RLD36"
DEMONSTRATION_INSTANT = "2026-09-07T12:00:00+00:00"
INTENT = "credit-memo-drafting"
FRESHNESS = "as-filed"

#: Every audience the shipped prompt declares. Narrow it to watch the Policy
#: operator refuse a section its materialization rather than filter it.
DEMONSTRATION_AUDIENCE = ("credit-officer",)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facility", default=DEMONSTRATION_FACILITY)
    parser.add_argument("--scope", default=DEMONSTRATION_SCOPE)
    parser.add_argument("--asked-at", default=DEMONSTRATION_INSTANT)
    parser.add_argument("--intent", default=INTENT)
    parser.add_argument(
        "--audience",
        action="append",
        help="an audience classification this rendering may include; repeatable."
        " Omit for the shipped set.",
    )
    parser.add_argument(
        "--door",
        action="store_true",
        help="instead of asking once: boot the MCP egress door on an ephemeral"
        " 127.0.0.1 port, print `READY {port}`, and serve until terminated",
    )
    parsed = parser.parse_args(argv[1:])

    if parsed.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    parameters: dict[str, Any] = {
        deployment.FACILITY: parsed.facility,
        deployment.BORROWER_SCOPE: [parsed.scope],
        deployment.AUDIENCE: list(parsed.audience or DEMONSTRATION_AUDIENCE),
    }

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        asked = opened.question(
            subject=parsed.facility,
            asked_at=datetime.fromisoformat(parsed.asked_at),
            intent=parsed.intent,
            freshness=FRESHNESS,
            parameters=parameters,
        )
        outcome = opened.answer(asked)

        print(f"facility    : {parsed.facility}")
        print(f"asked at    : {asked.asked_at.isoformat()}")
        print(f"audience    : {', '.join(parameters[deployment.AUDIENCE])}")

        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED     : {outcome.reason}")
            print(f"detail      : {outcome.detail}")
            print(f"replay      : {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        substrate = payload["packaged_from"]
        by = payload["packaged_by"]

        print()
        print("THE SUBSTRATE — the artifact-of-record this memo renders")
        print(f"   content address : {substrate['content_address']}")
        print(f"   its expiry      : {substrate['expires_at']}")
        print(f"   its debt        : {substrate['debt']}")
        print()
        print("THE PACKAGING — §7.10.4's four pinned rendering primitives")
        print(f"   model           : {by['model']}")
        print(f"   temperature     : {by['temperature']}")
        print(f"   prompt artifact : {by['prompt_artifact_uri']}")
        print(f"   prompt hash     : {by['prompt_artifact_hash']}")
        print()
        print("THE MEMO")
        for section in payload["sections"]:
            print(f"\n   {str(section['heading']).upper()}  [{section['audience']}]")
            print(f"   {section['prose']}")
            print(f"   figures cited: {', '.join(section['figures_cited']) or '(none)'}")

        debt = outcome.product.debt
        print()
        print(f"context debt: D_c = {debt.debt}  signal: {debt.signal}")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"assembly    : {outcome.product.contract.assembly_mode if hasattr(outcome.product, 'contract') else 'llm_packaged (declared)'}")
        print(f"replay      : {outcome.replay_ref.content_address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
