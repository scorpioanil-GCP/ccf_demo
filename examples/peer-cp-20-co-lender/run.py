"""Ask the co-lender for one position, or boot its door for another process.

    .venv/bin/python examples/cp-20-syndicated-lending-co-lender/peer/run.py
    .venv/bin/python examples/cp-20-syndicated-lending-co-lender/peer/run.py --door

The peer's connection material lives in `~/.bashrc`, which returns early for
non-interactive shells, so **this script is run under `bash -ic`** (spec §C.1).

[ADAPT] the two demonstration values below. [MECHANISM] the `produce` calls.
This module carries no marker region: what a run prints is nobody's contract.
"""

from __future__ import annotations

import argparse
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

#: The attested facility (`PDEC-4BEB7CE1F8`, 21600 s, 650 ms, signed) and Bank
#: of America's LEI. `Q2` (Dave, 2026-09-22) splits the facilities: this is the
#: ADMITTED-PEER path. `FAC-A4A5EE` is the unattested one and stays refused.
DEMONSTRATION_FACILITY = "FAC-6F4065"
DEMONSTRATION_COUNTERPARTY = "B4TYDEB6GKMZO031MB27"

INTENT = "co-lender-position"
FRESHNESS = "standard"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facility", default=DEMONSTRATION_FACILITY)
    parser.add_argument("--counterparty", default=DEMONSTRATION_COUNTERPARTY)
    parser.add_argument(
        "--door", action="store_true",
        help="instead of asking once: boot the MCP egress door on an ephemeral"
             " 127.0.0.1 port, print `READY {port}`, and serve questions from"
             " other processes until terminated",
    )
    parsed = parser.parse_args(argv[1:])

    if parsed.door:
        from server import serve as door  # noqa: PLC0415

        door.loopback(announce=lambda port: print(f"READY {port}", flush=True))
        return 0

    with tempfile.TemporaryDirectory() as scratch, produce.product(Path(scratch)) as opened:
        asked = opened.question(
            subject=parsed.facility,
            asked_at=datetime.now(UTC),
            intent=INTENT,
            freshness=FRESHNESS,
            parameters={
                deployment.FACILITY: parsed.facility,
                deployment.COUNTERPARTY: parsed.counterparty,
            },
        )
        outcome = opened.answer(asked)
        print(f"facility    : {parsed.facility}")
        print(f"counterparty: {parsed.counterparty}")
        if isinstance(outcome, RefusalEnvelope):
            print(f"\nREFUSED     : {outcome.reason}")
            print(f"replay      : {outcome.replay_reference}")
            print(
                "\nA position with no attestation record behind it is not served"
                " with a caveat: the peer will not assert a claim it cannot"
                " stand behind, so the answer is a governed refusal carrying"
                " `unattested-position`. It is NOT Context Debt (`Q3.2`)."
            )
            return 1
        payload = outcome.product.payload
        if not payload["positions"]:
            # The policy operator emptied the view — the structural backstop
            # behind the attestation refusal. A computed-empty answer is
            # SERVED, not refused, which is why the refusal above exists.
            print("\npositions   : none survived the policy envelope")
            print(f"replay      : {outcome.replay_ref.content_address}")
            return 1
        position = payload["positions"][0]
        print(f"precision   : {position['precision']}")
        if position["precision"] == "band":
            print(f"band        : {position['band_low']} .. {position['band_high']}")
            print("share_usd   : ABSENT — a band never becomes a point estimate")
        else:
            print(f"share_usd   : {position['share_usd']}")
        print(f"declared TTL: {position['declared_ttl_seconds']} s")
        print(f"declared lat: {position['declared_latency_ms']} ms")
        print()
        print(f"context debt: D_c = {outcome.product.debt.debt}")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"replay      : {outcome.replay_ref.content_address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
