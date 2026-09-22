"""Ask one syndicate question, with or without reaching across the boundary.

    .venv/bin/python examples/cp-20-syndicated-lending-co-lender/run.py
    .venv/bin/python examples/cp-20-syndicated-lending-co-lender/run.py --include-federated

The peer's door must already be serving, and `CCF_CP20_PEER_URL` /
`CCF_CP20_PEER_TOKEN` must name it — see the README. The peer's own connection
material lives in `~/.bashrc`, so the door is booted under `bash -ic`.

[ADAPT] the demonstration values. [MECHANISM] the `produce` calls.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import deployment  # noqa: E402
import produce  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

#: The three principals, one per rendering. `CLD-G18`/`CLD-G19`: one class,
#: one door, three structurally different products, strictly nested.
PRINCIPALS = {
    "prospective": "PRIN-SYN-PROSPECT-001",
    "participant": "PRIN-SYN-001",
    "agent": "PRIN-SYN-AGENT-001",
}

#: `Q2` (Dave, 2026-09-22) splits the facilities. This is the ADMITTED-PEER
#: path: an attested Bank of America declaration behind an envelope that
#: admits `own_position`.
DEMONSTRATION_FACILITY = "FAC-6F4065"
BANK_OF_AMERICA = "B4TYDEB6GKMZO031MB27"
#: Citibank — in the syndicate, and OUT of envelope for this class (`Q1`(b)).
CITIBANK = "E57ODZWZ7FF32TWEFA76"

INTENT = "amendment-consent"
FRESHNESS = "standard"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facility", default=DEMONSTRATION_FACILITY)
    parser.add_argument(
        "--include-federated", action="store_true",
        help="reach across the organizational boundary. ABSENT TAKES THE"
             " DECLARED DEFAULT, which is false — a federated ask has legal"
             " consequences and must never happen because a default made it",
    )
    parser.add_argument(
        "--counterparty", default=BANK_OF_AMERICA,
        help=f"whom to ask. {CITIBANK} (Citibank) is out of envelope for this"
             " class and is refused before any peer is called",
    )
    parser.add_argument("--perspective", default="participant",
                        choices=("prospective", "participant", "agent"))
    parsed = parser.parse_args(argv[1:])

    parameters: dict[str, object] = {deployment.FACILITY: parsed.facility}
    if parsed.include_federated:
        parameters[deployment.INCLUDE_FEDERATED] = True
        parameters[deployment.COUNTERPARTIES] = [parsed.counterparty]

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        asked = opened.question(
            subject=parsed.facility, asked_at=datetime.now(UTC),
            intent=INTENT, freshness=FRESHNESS, parameters=parameters,
        )
        outcome = opened.answer(
            asked,
            perspective=Perspective(
                principal_id=PRINCIPALS[parsed.perspective], role=parsed.perspective
            ),
        )
        print(f"facility        : {parsed.facility}")
        print(f"include_federated: {parsed.include_federated}")
        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED         : {outcome.reason}")
            print(f"detail          : {getattr(outcome, 'detail', None)}")
            print(f"replay          : {outcome.replay_reference}")
            return 1
        payload = outcome.product.payload
        consent = payload["consent"]
        print(f"role            : {payload['role']}")
        print(f"syndicate       : {payload['syndicate']['member_count']} filed members,"
              f" total {payload['syndicate']['filed_total_usd']}")
        print(f"consent standard: {consent['consent_standard']} at {consent['consent_percent']}%")
        print(f"known holders   : {consent['known_holders']}")
        print(f"known consent   : {consent['known_consent_usd']} of {consent['denominator_usd']}")
        print(f"coverage        : {consent['coverage_percent']}%  reachable={consent['reachable']}")
        federated = payload.get("federated_position")
        if federated:
            print()
            print(f"federated       : {federated['counterparty']} @ {federated['precision']}")
            print(f"  provenance    : {federated['provenance']} (tenant {federated['producer_tenant']})")
            print(f"  declared TTL  : {federated['declared_ttl_seconds']} s")
            print(f"  declared lat  : {federated['declared_latency_ms']} ms,"
                  f" within bound = {federated['within_declared_latency_bound']}")
            divergence = payload.get("divergence")
            if divergence:
                print(f"  vs filed      : {divergence['filed_commitment_usd']}"
                      f" -> agrees={divergence['agrees']}")
        print()
        print(f"findings        : {json.dumps(payload['findings'])}")
        print(f"context debt    : D_c = {outcome.product.debt.debt}")
        print(f"expires at      : {outcome.product.expires_at.isoformat()}")
        print(f"replay          : {outcome.replay_ref.content_address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
