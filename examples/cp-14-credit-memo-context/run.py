"""Ask the credit-memo composite its first real question and show what came back.

[ADAPT] freely — this file is presentation and nothing else. It carries no
marker region, so nothing printed here is published-snippet surface, and it is
the ONLY module in this example that writes to a terminal.

Usage::

    export CCF_CP_14_POSTGRES_DSN=...  CCF_CP_14_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP14_SPREAD_URL=http://127.0.0.1:<port>/mcp  CCF_CP14_SPREAD_TOKEN=...
    export CCF_CP14_FAMILY_URL=... CCF_CP14_FAMILY_TOKEN=...   # and EXPOSURE, COLLATERAL, COVENANT
    .venv/bin/python examples/cp-14-credit-memo-context/run.py
    .venv/bin/python examples/cp-14-credit-memo-context/run.py --debt-tolerance 1.0   # diagnostic only

The spread producer is `examples/cp-03-canonical-obligor-financial-spread/run.py
--door`, which prints `READY {port}`. The production question is asked at the
memo's governed tolerance — 0.25 under the v2 policy at the CP-14 instant — and
the honest expected result at that tolerance is a refusal: the spread child is
withheld by its own producer, the required slot is refused, the composite
refuses, and five child rows are retained (`D-IMPL-338`).

**What this prints comes from the PERSISTED record, reloaded from a fresh store
instance** — never from memory — so what is shown is what a later examiner
would find.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import deployment
import produce
from ccf.artifacts.file_store import FileArtifactStore
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

#: BGC Group, Inc. — the first real question's obligor (spec §C.1 roster; the
#: same obligor the cross-deployment proof asks the spread producer about).
DEMONSTRATION_ANCHOR = "2549001IGRCG4F0RLD36"

#: BGC's one facility on the estate (`ccf_v2.facility`, measured 2026-09-15):
#: the collateral child answers one facility per question (`CP14-F-20`).
DEMONSTRATION_FACILITY = "FAC-5B8418"

#: The CP-14 instant — held, not tuned (`CP14-F-19`): the children's instant.
DEMONSTRATION_INSTANT = "2026-09-07T12:00:00+00:00"

#: The memo's governed tolerance at that instant: the v2 policy's
#: `debtToleranceDefault` (spec §B.3), stated explicitly in this slice.
GOVERNED_TOLERANCE = "0.25"

INTENT = "annual-review"
FRESHNESS = "decision-scoped"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lei", default=DEMONSTRATION_ANCHOR)
    parser.add_argument("--facility-id", default=DEMONSTRATION_FACILITY)
    parser.add_argument("--asked-at", default=DEMONSTRATION_INSTANT, help="the children's instant")
    parser.add_argument("--as-of", default=None, help="the decision instant; defaults to --asked-at")
    parser.add_argument("--debt-tolerance", default=GOVERNED_TOLERANCE, help="0.25 is the governed value; 1.0 is a diagnostic")
    parser.add_argument("--memo-type", default=None, help="omit to let the class default resolve")
    parsed = parser.parse_args(argv[1:])

    asked_at = datetime.fromisoformat(parsed.asked_at)
    parameters: dict[str, object] = {
        deployment.AS_OF: parsed.as_of or parsed.asked_at,
        deployment.DEBT_TOLERANCE: Decimal(parsed.debt_tolerance),
        deployment.FACILITY_ID: parsed.facility_id,
    }
    if parsed.memo_type:
        parameters[deployment.MEMO_TYPE] = parsed.memo_type

    with tempfile.TemporaryDirectory(prefix="cp14-") as scratch, produce.product(Path(scratch)) as opened:
        asked = opened.question(subject=parsed.lei, asked_at=asked_at, intent=INTENT, freshness=FRESHNESS, parameters=parameters)
        outcome = opened.answer(asked)
        store_root = opened.scratch / opened.replay.store_dirname
        # The record, from a FRESH store instance: what an examiner finds.
        fresh = FileArtifactStore(root=store_root)
        if isinstance(outcome, ServedProduct):
            address = outcome.replay_ref.content_address
        else:
            address = fresh.resolve_uri(uri=outcome.replay_reference)
        record = DecisionReplayRecord.model_validate_json(fresh.get(content_address=address))

    print(f"question    : {parsed.lei} at {parsed.asked_at} (as_of {parameters[deployment.AS_OF]}), tolerance {parsed.debt_tolerance}")
    if isinstance(outcome, ServedProduct):
        print(f"outcome     : SERVED  content address {outcome.content_address}")
        print(json.dumps(outcome.product.payload, indent=2, default=str))
    else:
        assert isinstance(outcome, RefusalEnvelope)
        print(f"outcome     : REFUSED kind={outcome.kind} reason={outcome.reason}")
        print(f"disclosed   : {outcome.detail}")
        retained = record.content_generation_path.assembly_refusal
        if retained:
            print(f"retained    : {json.loads(retained).get('detail')}")
    print(f"record      : {address}")
    rows = record.content_generation_path.child_resolutions
    print(f"child rows  : {len(rows)}")
    for row in rows:
        print(
            f"  - {row.required_product_class:<40} {row.outcome_status:<24}"
            f" producer={row.producer_id or '-'} tenant={row.producer_tenant or '-'}"
            f" question={'yes' if row.child_question_address else 'no'}"
            f" child={row.child_content_address or '-'}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv))
