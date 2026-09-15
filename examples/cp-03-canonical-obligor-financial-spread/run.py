"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else.

**It carries no marker region**, so nothing printed here is published-snippet
surface: an adopter copies ``produce.py``'s two regions, not this. It is also
the ONLY module in this example that writes to a terminal, which is what keeps
a printed line out of the spine.

Usage::

    export CCF_CP_03C_POSTGRES_DSN=...   CCF_CP_03C_POSTGRES_SCHEMA=ccf_v2
    make example-cp-03-canonical
    make example-cp-03-canonical LEI=--lei=<lei> ASKED_AT=--asked-at=2026-09-07T12:00:00+00:00
    make example-cp-03-canonical BASIS=--basis=latest-restated PRINCIPAL=--principal=PRIN-RES-002
    .venv/bin/python examples/cp-03-canonical-obligor-financial-spread/run.py --door

Every spread parameter omitted asks the question WITHOUT it, so the class
default resolves — which is a different thing from passing the default's value,
and the run prints which happened. ``--asked-at`` omitted asks now.

**Named flags rather than positional arguments**, so a basis supplied without
an anchor cannot silently land in the anchor's slot and be read as an LEI.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import deployment
import produce
from ccf.products.refusal import RefusalEnvelope
from ccf.projection.plan import Perspective

#: The obligor this example demonstrates against. An argument, not a constant
#: in the fabric's path — pass your own anchor to ask about another obligor.
#: BGC Group, Inc.: on `CP-SPEC-014`'s roster, and one of the three obligors
#: whose latest filing (2026-08-10) lies inside the declared 30-day window at
#: the instant CP-14 asks (`2026-09-07T12:00:00+00:00`, `CP14-F-19`).
DEMONSTRATION_ANCHOR = "2549001IGRCG4F0RLD36"

#: The instant CP-14 asks its children at — held, not tuned (`CP14-F-19`).
DEMONSTRATION_INSTANT = "2026-09-07T12:00:00+00:00"

#: Digital Turbine, Inc. — the frozen specimen's own demonstration obligor,
#: whose latest filing (2026-08-05) lies OUTSIDE the declared window at the
#: CP-14 instant. Asked then, it is refused by the product's own gate; asked at
#: the specimen's pinned instant (2026-08-29T12:00:00+00:00) it serves.
STALE_AT_THE_INSTANT = "549300D0WZR1VI2QGB24"

#: Two principals the estate's `principal_jurisdiction` table grants
#: differently: the EU KYC analyst's grant (EU prefixes) reaches no obligor the
#: demonstration asks about, and the research analyst's grant is wider than the default coverage
#: banker's (it adds `CA` and `GB`). Which principal asks changes WHICH
#: OBLIGORS EXIST, never how a spread is shaped.
PRINCIPAL_WITH_NO_GRANT = "PRIN-KYC-004"
PRINCIPAL_WITH_A_WIDER_GRANT = "PRIN-RES-002"

#: The intent and freshness this class serves — the discovery set declares the
#: first; the second is the request's own vocabulary (`CP-SPEC-003C` §B).
INTENT = "annual-review"
FRESHNESS = "filing-cadence"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lei", default=DEMONSTRATION_ANCHOR)
    parser.add_argument(
        "--asked-at", default=None,
        help=f"ISO instant with offset; omit to ask now (CP-14 asks at {DEMONSTRATION_INSTANT})",
    )
    parser.add_argument("--debt-tolerance", default="0.25", help="the caller's D_c ceiling (required by the contract)")
    parser.add_argument("--intent", default=INTENT)
    parser.add_argument("--periods", type=int, default=None, help="omit to let the class default resolve")
    parser.add_argument("--basis", default=None, help="as-reported | latest-restated; omit for the class default")
    parser.add_argument("--no-peers", action="store_true", help="ask with include_peers=false")
    parser.add_argument("--principal", default=None, help="ask as another principal; its grant is stated on the request")
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

    parameters: dict[str, Any] = {deployment.DEBT_TOLERANCE: Decimal(parsed.debt_tolerance)}
    for name, value in (
        (deployment.PERIODS, parsed.periods),
        (deployment.BASIS, parsed.basis),
        (deployment.INCLUDE_PEERS, False if parsed.no_peers else None),
    ):
        if value is not None:
            parameters[name] = value

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        perspective: Perspective | None = None
        if parsed.principal and parsed.principal != opened.default_perspective.principal_id:
            # Ask as somebody else: that principal's grant is STATED on the
            # request, where the effective request records it.
            parameters.update(
                deployment.grant_parameters(parsed.principal, settings=opened.sources[deployment.SOURCE])
            )
            perspective = Perspective(principal_id=parsed.principal, role=opened.default_perspective.role)
        asked = opened.question(
            subject=parsed.lei,
            asked_at=datetime.fromisoformat(parsed.asked_at) if parsed.asked_at else datetime.now(UTC),
            intent=parsed.intent,
            freshness=FRESHNESS,
            parameters=parameters,
        )
        outcome = opened.answer(asked, perspective=perspective)

        print(f"obligor     : {parsed.lei}")
        print(f"asked at    : {asked.asked_at.isoformat()}")
        print(f"intent      : {asked.intent}")
        for name in (deployment.PERIODS, deployment.BASIS, deployment.INCLUDE_PEERS):
            value = asked.parameters.get(name)
            print(f"{name:<12}: " + (f"{value} (as asked)" if value is not None else "absent — the class default resolves"))
        print(f"tolerance   : {asked.parameters[deployment.DEBT_TOLERANCE]}")
        if parsed.principal:
            print(f"principal   : {parsed.principal} — grant stated as {len(asked.parameters.get(deployment.JURISDICTIONS, ()))} jurisdictions")

        if isinstance(outcome, RefusalEnvelope):
            # A refusal is an ANSWER, not a crash: the question was governed and
            # the verdict was no. It carries the reason and the decision record
            # that authorized saying it.
            print(f"\nREFUSED     : {outcome.reason}")
            print(f"replay      : {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        obligor = payload["obligor"]
        print()
        print(f"name        : {obligor['obligor_legal_name']} ({obligor['obligor_jurisdiction']})")
        print(f"basis       : {payload['basis_applied']}")
        print(f"periods     : {len(payload['periods'])} columns, newest {payload['periods'][0]['period_end']} {payload['periods'][0]['fiscal_period']}")
        print(f"anchor      : {payload[deployment.ANCHOR_MEMBER]} (freshest filing in the payload)")
        restated = sum(
            1 for period in payload["periods"] for line in period["lines"].values() if line.get("restated")
        )
        not_evaluable = sum(
            1 for period in payload["periods"] for line in period["lines"].values() if line["value"] == "NOT_EVALUABLE"
        )
        print(f"restated    : {restated} lines changed across filings; {not_evaluable} lines NOT_EVALUABLE")
        peers = payload["peer_comparison"]
        print("peers       : " + ("NOT_EVALUABLE — a cohort of nobody" if peers == "NOT_EVALUABLE" else f"{peers['cohort_size']} peers in SIC {peers['sic']}"))
        newest = payload["periods"][0]["lines"]
        for name in ("revenue", "ebitda", "total_debt", "leverage", "interest_coverage"):
            if name in newest:
                print(f"    {name:<18}: {newest[name]['value']}")
        print()
        # The things a SELECT could not have told you.
        debt = outcome.product.debt
        print(f"context debt: D_c = {debt.debt}  (F={debt.factors.freshness} C={debt.factors.completeness} S={debt.factors.semantic_consistency})")
        print(f"       signal: {debt.signal}")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"replay      : {outcome.replay_ref.content_address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
