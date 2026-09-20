"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else. It carries no
marker region and is the ONLY module in this example that writes to a
terminal.

Usage::

    export CCF_CP_17_SQLITE_PATH=...     # ccf_dataprep/data/departmental.sqlite, opened read-only
    export CCF_CP_17_POSTGRES_DSN=...    CCF_CP_17_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_17_FLUREE_URL=...      CCF_CP_17_FLUREE_LEDGER=fibo-v2
    export CCF_CP_17_MONGO_URI=...       CCF_CP_17_MONGO_DB=fibo_v2
    export CCF_CP_17_TOKEN_COVERAGE=...  CCF_CP_17_TOKEN_RESEARCH=... CCF_CP_17_TOKEN_TRADER=... CCF_CP_17_TOKEN_KYC=...
    make -s example-cp-17
    .venv/bin/python examples/cp-17-mnpi-wall-enforcement/run.py --door

Every request parameter is optional. Omitted, the program asks the
demonstration question in ``artifacts/question.yaml``. In-process, the
caller states its own perspective with ``--principal`` (the role comes from
the estate's principal register); the door takes no such flag — it resolves
the perspective from the verified credential (`CP-SPEC-017` §D.3 step 0).
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

import acquisition  # noqa: E402
import deployment  # noqa: E402
import produce  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"


def question() -> dict[str, Any]:
    document = yaml.safe_load(QUESTION.read_text(encoding="utf-8"))
    asked: dict[str, Any] = dict(document["declaration"]["question"])
    return asked


def main(argv: list[str]) -> int:
    default = question()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default=default["subject"], help="the issuer's LEI")
    parser.add_argument("--asked-at", default=default["asked_at"], help="the as-of instant (the vault's `as_of`)")
    parser.add_argument("--intent", default=default["intent"])
    parser.add_argument("--known-as-of", default=None, help="the assertion-time clock; omit to let the class default resolve")
    parser.add_argument("--debt-tolerance", default=None, help="omit to let the class default resolve")
    parser.add_argument("--principal", default=default["principal"], help="the in-process caller's principal id")
    parser.add_argument("--door", action="store_true", help="serve the standard MCP door on a loopback port instead")
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        parameters: dict[str, Any] = {}
        if arguments.known_as_of is not None:
            parameters[deployment.KNOWN_AS_OF] = arguments.known_as_of
        if arguments.debt_tolerance is not None:
            parameters[deployment.DEBT_TOLERANCE] = arguments.debt_tolerance
        asked = opened.question(
            subject=arguments.subject,
            asked_at=datetime.fromisoformat(arguments.asked_at),
            intent=arguments.intent,
            freshness=default["freshness"],
            parameters=parameters,
        )
        roles = acquisition.principal_roles(relational_settings=opened.sources[deployment.SOURCE_RELATIONAL])
        perspective = Perspective(principal_id=arguments.principal, role=roles.get(arguments.principal, "unmapped"))
        print(f"asked        {asked.subject} · {asked.intent} · as of {arguments.asked_at} · as {perspective.principal_id} ({perspective.role})")
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
        print(f"  role       {payload['role']}  known_as_of={payload['known_as_of']}")
        issuer = payload.get("issuer")
        if issuer is None:
            print("  issuer     (no issuer row — served computed-empty)")
        else:
            print(f"  issuer     {issuer['legal_name']}  reg_fd_disclosure={issuer['reg_fd_disclosure']}")
        print(f"  edges      {payload['edge_types_served']}  entities={payload['entities_in_view']}")
        for member in ("deal_engagements", "interactions", "research", "positions", "family"):
            if member in payload:
                print(f"  {member:<10} {len(payload[member])}")
        if product.computed_empty is not None:
            print(f"  empty      {sorted(product.computed_empty.operators_returned_empty)} ({product.computed_empty.emptiness})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
