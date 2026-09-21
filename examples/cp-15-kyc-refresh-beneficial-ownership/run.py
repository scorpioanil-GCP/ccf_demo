"""Run the example and show a reader what came back.

[ADAPT] freely — presentation only. This is the ONLY module in this example
that writes to a terminal, and the only one that calls BOTH the producer road
and the review queue: the product is served first and completely, then its
findings are referred (`CP-SPEC-015` §F.4.1).

Usage::

    export CCF_CP_15_POSTGRES_DSN=...    CCF_CP_15_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_15_FLUREE_URL=...      CCF_CP_15_FLUREE_LEDGER=fibo-v2
    export CCF_CP_15_MONGO_URI=...       CCF_CP_15_MONGO_DB=fibo_v2
    export CCF_CP_15_TOKEN_KYC=...       CCF_CP_15_TOKEN_COVERAGE=... CCF_CP_15_TOKEN_RESEARCH=... CCF_CP_15_TOKEN_UNGRANTED=...
    make -s example-cp-15
    .venv/bin/python examples/cp-15-kyc-refresh-beneficial-ownership/run.py --door
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import deployment  # noqa: E402
import produce  # noqa: E402
import review  # noqa: E402
from ccf.contracts.canonical import content_hash  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"


def declaration() -> dict[str, Any]:
    return yaml.safe_load(QUESTION.read_text(encoding="utf-8"))["declaration"]


def main(argv: list[str]) -> int:
    declared = declaration()
    asked_defaults = dict(declared["question"])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity", default=asked_defaults["subject"], help="the anchor entity")
    parser.add_argument("--asked-at", default=asked_defaults["asked_at"])
    parser.add_argument("--intent", default=asked_defaults["intent"],
                        help="one of " + ", ".join(declared["priced_intents"]))
    parser.add_argument("--principal", default=asked_defaults["principal"])
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--threshold", default=None, help="may be raised above the estate's floor, never lowered")
    parser.add_argument("--min-confidence", default=None, help="likewise floored")
    parser.add_argument("--max-depth", default=None)
    parser.add_argument("--debt-tolerance", default=None)
    parser.add_argument("--door", action="store_true", help="serve the standard MCP door on a loopback port")
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: arguments.as_of or arguments.asked_at}
        for flag, name in ((arguments.threshold, deployment.THRESHOLD),
                           (arguments.min_confidence, deployment.MIN_CONFIDENCE),
                           (arguments.max_depth, deployment.MAX_DEPTH),
                           (arguments.debt_tolerance, "debt_tolerance")):
            if flag is not None:
                parameters[name] = flag
        from server.serve import perspective_by_principal  # noqa: PLC0415

        mapping = perspective_by_principal(opened)
        perspective = Perspective(
            principal_id=arguments.principal,
            role=mapping.get(arguments.principal, "unmapped"),
        )
        asked = opened.question(
            subject=arguments.entity, asked_at=datetime.fromisoformat(arguments.asked_at),
            intent=arguments.intent, freshness=asked_defaults["freshness"], parameters=parameters,
        )
        print(f"asked        {asked.subject} · {asked.intent} · decided {arguments.asked_at}"
              f" · as {perspective.principal_id} ({perspective.role})")
        outcome = opened.answer(asked, perspective=perspective)

        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED      {outcome.kind} · {outcome.reason}")
            print(f"  {outcome.detail}")
            print(f"  replay     {outcome.replay_reference}")
            return 1

        product = outcome.product
        payload = product.payload
        print(f"\nSERVED       {product.schema_name}@{product.schema_version}")
        print(f"  address    {content_hash(product)}")
        print(f"  record     {outcome.replay_ref.content_address}")
        print(f"  debt       D_c={product.debt.debt if product.debt else 'n/a'}  signal={product.debt.signal if product.debt else 'n/a'}")
        entity = payload.get("entity")
        if entity is None:
            print("  entity     (no ownership chain — served computed-empty)")
        else:
            print(f"  entity     {entity['entity_id']} · {entity['entity_kind']} · chain {entity['chain_id']}"
                  f" · depth {entity['depth']} · {entity['jurisdiction_path']}")
        print(f"  threshold  {payload['applicable_threshold']}%  ({entity['threshold_basis'] if entity else '-'})")
        print(f"  confidence floor {payload['min_confidence']}")
        print(f"  residency  {payload.get('residency_entitlement', '(not a member of this perspective)')}")
        for member in ("ownership_chain", "reportable_owners", "sub_threshold_findings",
                       "resolution_findings", "sanctions_findings", "cycle_findings"):
            rows = payload.get(member) or []
            print(f"  {member:<24} {len(rows)}")
        print(f"  refresh    {payload['refresh_state']}")

        # THE CONSTRUCTION BOUNDARY. The product above is complete, governed,
        # assessed and immutable. Only now is anything referred.
        before = content_hash(product)
        queue = review.open_queue(clock=lambda: datetime.now(UTC))
        submitted = review.refer_findings(
            queue=queue, served=outcome, tenant_id=opened.tenant_id,
            at=datetime.fromisoformat(arguments.asked_at),
        )
        print(f"\nREFERRED     {len(submitted.referrals)} finding(s) to the review queue"
              f"; {len(submitted.not_referred)} not referred for want of evidence")
        for row in review.referral_summary(submitted):
            print(f"    {row['member']:<24} {row['reason']:<28} {row['person_key']}")
        print(f"  workflow_state_ref  {submitted.workflow_state_ref}")
        print(f"  output_ref          {submitted.output_ref}")
        print(f"  the product is unchanged by the referral: {content_hash(product) == before}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
