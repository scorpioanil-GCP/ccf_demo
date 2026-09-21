"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else. It carries no
marker region and is the ONLY module in this example that writes to a
terminal.

Usage::

    export CCF_CP_18_SQLITE_PATH=...     # ccf_dataprep/data/departmental.sqlite, read-only
    export CCF_CP_18_POSTGRES_DSN=...    CCF_CP_18_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_18_FLUREE_URL=...      CCF_CP_18_FLUREE_LEDGER=fibo-v2
    export CCF_CP_18_MONGO_URI=...       CCF_CP_18_MONGO_DB=fibo_v2
    export CCF_CP_18_TOKEN_MA=...        CCF_CP_18_TOKEN_DCM=... CCF_CP_18_TOKEN_SECTOR=... CCF_CP_18_TOKEN_UNGRANTED=...
    make -s example-cp-18
    .venv/bin/python examples/cp-18-ib-opportunity-synthesis/run.py --door

Every request parameter is optional. Omitted, the program asks the
demonstration question in ``artifacts/question.yaml``. In-process the caller
states its own banker with ``--banker``; the perspective that banker asks
under is this DEPLOYMENT's declared mapping, because the estate holds no
banker-to-perspective row. The door takes no such flag — it resolves the
perspective from the verified credential.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import deployment  # noqa: E402
import produce  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"


def declaration() -> dict[str, Any]:
    return yaml.safe_load(QUESTION.read_text(encoding="utf-8"))["declaration"]


def main(argv: list[str]) -> int:
    declared = declaration()
    asked_defaults = dict(declared["question"])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--banker", default=asked_defaults["subject"], help="the banker whose book is ranked")
    parser.add_argument("--asked-at", default=asked_defaults["asked_at"], help="the decision instant")
    parser.add_argument("--intent", default=asked_defaults["intent"])
    parser.add_argument("--as-of", default=None, help="the instant whose weight vector governs; omit to let the class default resolve")
    parser.add_argument("--since", default=declared["instants"]["SINCE"], help="the signal window's lower bound")
    parser.add_argument("--limit", default=None, help="how many ranked rows to serve")
    parser.add_argument("--signal-types", default=None, help="comma-separated, narrowing within the perspective's plan")
    parser.add_argument("--debt-tolerance", default=None, help="omit to let the class default resolve")
    parser.add_argument("--door", action="store_true", help="serve the standard MCP door on a loopback port instead")
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    from server.serve import PERSPECTIVE_BY_PRINCIPAL  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        parameters: dict[str, Any] = {}
        if arguments.as_of is not None:
            parameters[deployment.AS_OF] = arguments.as_of
        if arguments.since is not None:
            parameters[deployment.SINCE] = arguments.since
        if arguments.limit is not None:
            parameters[deployment.LIMIT] = arguments.limit
        if arguments.signal_types is not None:
            parameters[deployment.SIGNAL_TYPES] = [
                part.strip() for part in arguments.signal_types.split(",") if part.strip()
            ]
        if arguments.debt_tolerance is not None:
            parameters["debt_tolerance"] = arguments.debt_tolerance
        asked = opened.question(
            subject=arguments.banker,
            asked_at=datetime.fromisoformat(arguments.asked_at),
            intent=arguments.intent,
            freshness=asked_defaults["freshness"],
            parameters=parameters,
        )
        perspective = Perspective(
            principal_id=arguments.banker,
            role=PERSPECTIVE_BY_PRINCIPAL.get(arguments.banker, "unmapped"),
        )
        print(
            f"asked        {asked.subject} · {asked.intent} · decided {arguments.asked_at}"
            f" · weights as of {arguments.as_of or '(class default: the decision instant)'}"
            f" · as {perspective.principal_id} ({perspective.role})"
        )
        outcome = opened.answer(asked, perspective=perspective)

        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED      {outcome.kind} · {outcome.reason}")
            print(f"  {outcome.detail}")
            print(f"  replay     {outcome.replay_reference}")
            return 1

        product = outcome.product
        payload = product.payload
        print(f"\nSERVED       {product.schema_name}@{product.schema_version}")
        print(f"  address    {outcome.replay_ref.content_address}")
        print(f"  expires    {product.expires_at.isoformat()}")
        print(f"  debt       D_c={product.debt.debt if product.debt else 'n/a'}  signal={product.debt.signal if product.debt else 'n/a'}")
        banker = payload.get("banker")
        if banker is None:
            print("  banker     (no banker row — served computed-empty)")
        else:
            print(f"  banker     {banker['banker_id']} {banker['full_name']} · {banker['desk']} · {banker['perspective_id']}")
        print(f"  weights    version {payload['weight_version']}  over {len(payload['signal_types_admitted'])} admitted signal types")
        print(f"  portfolio  {payload['portfolio_size']} covered · {payload['candidates_considered']} candidates considered")
        optional = payload["optional_context"]
        print(f"  optional   MNPI wall child {optional.get('mnpi_wall_child')} ({optional.get('child_count')}) — {optional.get('reason')}")
        print(f"  edges      {payload['edge_types_served']}  entities={payload['entities_in_view']}")
        print("\n  rank  score      prospect                                  restriction  top signal")
        for row in payload["ranked_opportunities"][:10]:
            top = row["contributing_signals"][0]["signal_type"] if row["contributing_signals"] else "-"
            print(f"  {row['rank']:>4}  {row['score']:<10} {row['legal_name'][:40]:<40}  {row['restriction_type'] or '-':<11}  {top}")
        if product.computed_empty is not None:
            print(f"\n  empty      {sorted(product.computed_empty.operators_returned_empty)} ({product.computed_empty.emptiness})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
