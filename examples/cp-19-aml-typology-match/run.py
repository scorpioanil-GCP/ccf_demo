"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else. It carries no
marker region and is the ONLY module in this example that writes to a
terminal.

Usage::

    export CCF_CP_19_SQLITE_PATH=...     # ccf_dataprep/data/departmental.sqlite, opened read-only
    export CCF_CP_19_POSTGRES_DSN=...    CCF_CP_19_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_19_FLUREE_URL=...      CCF_CP_19_FLUREE_LEDGER=fibo-v2
    export CCF_CP_19_MONGO_URI=...       CCF_CP_19_MONGO_DB=fibo_v2
    export CCF_CP_19_TOKEN_L1=...        CCF_CP_19_TOKEN_L2=... CCF_CP_19_TOKEN_EXAMINER=... CCF_CP_19_TOKEN_UNGRANTED=...
    make -s example-cp-19
    .venv/bin/python examples/cp-19-aml-typology-match/run.py --door

Every request parameter is optional. Omitted, the program asks the
demonstration question in ``artifacts/question.yaml``. In-process the caller
states its own principal with ``--principal``; the perspective that principal
asks under is this DEPLOYMENT's declared mapping, because the estate holds no
AML principal (`CP-SPEC-019` §F.2 `TBC-1`). The door takes no such flag — it
resolves the perspective from the verified credential.
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
    parser.add_argument("--subject", default=asked_defaults["subject"], help="the alert id")
    parser.add_argument("--asked-at", default=asked_defaults["asked_at"], help="the decision instant")
    parser.add_argument("--intent", default=asked_defaults["intent"])
    parser.add_argument("--as-of", default=None, help="the instant whose filing posture governs; omit to let the class default resolve")
    parser.add_argument("--network-depth", default=None, help="hops from the subject party the acquisition walk follows")
    parser.add_argument("--debt-tolerance", default=None, help="omit to let the class default resolve")
    parser.add_argument("--principal", default=asked_defaults["principal"], help="the in-process caller's principal id")
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
        if arguments.network_depth is not None:
            parameters[deployment.NETWORK_DEPTH] = arguments.network_depth
        if arguments.debt_tolerance is not None:
            parameters["debt_tolerance"] = arguments.debt_tolerance
        asked = opened.question(
            subject=arguments.subject,
            asked_at=datetime.fromisoformat(arguments.asked_at),
            intent=arguments.intent,
            freshness=asked_defaults["freshness"],
            parameters=parameters,
        )
        perspective = Perspective(
            principal_id=arguments.principal,
            role=PERSPECTIVE_BY_PRINCIPAL.get(arguments.principal, "unmapped"),
        )
        print(
            f"asked        {asked.subject} · {asked.intent} · decided {arguments.asked_at}"
            f" · posture as of {arguments.as_of or '(class default: the decision instant)'}"
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
        posture = payload.get("posture")
        print(f"  posture    {'(none in force at this instant)' if posture is None else posture['posture_id'] + ' effective ' + posture['effective_from']}")
        print(f"  permitted  {payload['permitted_dispositions']}")
        alert = payload.get("alert")
        if alert is None:
            print("  alert      (no alert row — served computed-empty)")
        else:
            print(f"  alert      {alert['alert_id']}  subject={alert['subject_party']}  trigger={alert['trigger']}")
        print(f"  edges      {payload['edge_types_served']}  entities={payload['entities_in_view']}")
        # Only the members THIS perspective's shape carries are printed, and a
        # member another perspective would carry is silently absent — which is
        # the product's own claim, not this program's formatting choice.
        for member, value in sorted(payload.items()):
            if isinstance(value, list) and member not in ("edge_types_served", "permitted_dispositions"):
                print(f"  {member:<26} {len(value)}")
        if product.computed_empty is not None:
            print(f"  empty      {sorted(product.computed_empty.operators_returned_empty)} ({product.computed_empty.emptiness})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
