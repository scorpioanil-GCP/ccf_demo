"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else.

**It carries no marker region**, so nothing printed here is published-snippet
surface: an adopter copies ``produce.py``'s two regions, not this. It is also
the ONLY module in this example that writes to a terminal.

Usage::

    export CCF_CP_06C_FLUREE_URL=...     CCF_CP_06C_FLUREE_LEDGER=fibo-v2
    export CCF_CP_06C_POSTGRES_DSN=...   CCF_CP_06C_POSTGRES_SCHEMA=ccf_v2
    make example-cp-06-canonical
    make example-cp-06-canonical FACILITY=--facility=FAC-044206 SCOPE=--scope=<lei>
    make example-cp-06-canonical ASKED_AT=--asked-at=2026-09-07T12:00:00+00:00
    .venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door

Every basis flag omitted asks the question WITHOUT it, so the class default
resolves — which is a different thing from passing the default's value, and
the run prints which happened. ``--asked-at`` omitted asks now; `CP-SPEC-014`
asks at the demonstration instant.

**Named flags rather than positional arguments**, so a scope supplied without
a facility cannot silently land in the facility's slot.
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

#: The facility `CP-SPEC-014` names for its demonstration obligor, and that
#: obligor's LEI as the borrower scope. Arguments, not constants in the fabric's
#: path — pass your own.
DEMONSTRATION_FACILITY = "FAC-5B8418"
DEMONSTRATION_SCOPE = "2549001IGRCG4F0RLD36"
DEMONSTRATION_INSTANT = "2026-09-07T12:00:00+00:00"
INTENT = "lgd-assessment"
FRESHNESS = "as-filed"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facility", default=DEMONSTRATION_FACILITY)
    parser.add_argument("--scope", default=DEMONSTRATION_SCOPE, help="the borrower LEI the caller is entitled to walk")
    parser.add_argument(
        "--asked-at", default=None,
        help=f"ISO instant with offset; omit to ask now (CP-14 asks at {DEMONSTRATION_INSTANT})",
    )
    parser.add_argument("--intent", default=INTENT)
    parser.add_argument("--no-haircuts", dest="haircuts", action="store_false", default=None,
                        help="omit to let the class default resolve")
    parser.add_argument("--no-setoff", dest="setoff", action="store_false", default=None)
    parser.add_argument("--jurisdiction-basis", choices=("contractual", "enforceable"), default=None)
    parser.add_argument("--shared-collateral", choices=("priority", "pro-rata"), default=None)
    parser.add_argument(
        "--door", action="store_true",
        help="instead of asking once: boot the MCP egress door on an ephemeral 127.0.0.1"
             " port, print `READY {port}`, and serve questions from other processes until terminated",
    )
    parsed = parser.parse_args(argv[1:])

    if parsed.door:
        from server import serve as door  # noqa: PLC0415
        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    parameters: dict[str, Any] = {
        deployment.FACILITY: parsed.facility,
        deployment.BORROWER_SCOPE: [parsed.scope],
    }
    for name, value in (
        (deployment.APPLY_HAIRCUTS, parsed.haircuts),
        (deployment.INCLUDE_SETOFF, parsed.setoff),
        (deployment.JURISDICTION_BASIS, parsed.jurisdiction_basis),
        (deployment.SHARED_COLLATERAL, parsed.shared_collateral),
    ):
        if value is not None:
            parameters[name] = value

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        asked = opened.question(
            subject=parsed.facility,
            asked_at=datetime.fromisoformat(parsed.asked_at) if parsed.asked_at else datetime.now(UTC),
            intent=parsed.intent,
            freshness=FRESHNESS,
            parameters=parameters,
        )
        outcome = opened.answer(asked)

        print(f"facility    : {parsed.facility}")
        print(f"scope       : {parsed.scope}")
        print(f"asked at    : {asked.asked_at.isoformat()}")
        for name in (deployment.APPLY_HAIRCUTS, deployment.INCLUDE_SETOFF,
                     deployment.JURISDICTION_BASIS, deployment.SHARED_COLLATERAL):
            value = asked.parameters.get(name)
            print(f"{name:<20}: " + (f"{value} (as asked)" if value is not None else "absent — the class default resolves"))

        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED     : {outcome.reason}")
            print(f"detail      : {outcome.detail}")
            print(f"replay      : {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        coverage = payload["coverage"]
        print()
        print(f"commitment  : {payload['commitment']}")
        print(f"basis       : {payload['basis']['apply_haircuts']=} {payload['basis']['shared_collateral']=} {payload['basis']['jurisdiction_basis']=}")
        print(f"collateral  : {coverage['collateral_value']}")
        print(f"set-off     : {coverage['setoff_value']}")
        print(f"total       : {coverage['total']}")
        print(f"COVERAGE    : {coverage['coverage_ratio']}   {'covered' if coverage['shortfall'] == '0' else 'UNDER-COVERED'}")
        findings = payload["findings"]
        print()
        print("what a column could not have told you")
        print(f"   assets shared with another facility : {findings['shared_assets']}")
        print(f"   set-off excluded as unenforceable   : {findings['setoff_excluded_as_unenforceable']}")
        print(f"   pledges with no recorded priority   : {findings['unpositioned_pledges']}")
        print(f"   liens the register says are RELEASED: {findings['terminated_liens']}")
        print()
        print("valuation dates, per asset — the spread this product refuses to flatten")
        for asset in payload["assets"]:
            print(f"   {asset['uri']:<10} {asset['category'] or '?':<22} valued {asset['valuation_date']} ({asset['valuation_age_days']:>4} days old)")
        print()
        debt = outcome.product.debt
        print(f"context debt: D_c = {debt.debt}  (F={debt.factors.freshness} C={debt.factors.completeness} S={debt.factors.semantic_consistency})")
        print(f"       signal: {debt.signal}")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"replay      : {outcome.replay_ref.content_address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
