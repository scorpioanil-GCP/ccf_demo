"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else. It carries no
marker region, so nothing printed here is published-snippet surface: an adopter
copies ``produce.py``'s three regions, not this. It is also the only module in
this example that writes to a terminal, which keeps a printed line out of the
spine.

Usage::

    export CCF_CP_08_FLUREE_URL=...      CCF_CP_08_FLUREE_LEDGER=fibo-v2
    export CCF_CP_08_POSTGRES_DSN=...    CCF_CP_08_POSTGRES_SCHEMA=ccf_v2

    make example-cp-08
    make example-cp-08 KNOWN_AS_OF=--known-as-of=2026-09-11

**The default run asks the dispute question** — both instants at the drawdown
date — because that is the one a single-timeline store cannot answer. Vary
`--known-as-of` alone and the admitted amendment set changes while `as_of` is
held; that pair is the product's proof.

Omitting an instant asks the question WITHOUT the parameter, so the class's
declared default resolves — the request's own instant. That is a different act
from passing today's date, and the run prints which happened.

**Named flags rather than positional arguments**, so a date supplied without a
facility cannot land in the facility's slot.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import deployment  # noqa: E402
import produce  # noqa: E402

from ccf.products.refusal import RefusalEnvelope  # noqa: E402

#: The facility whose amendment 2 carries a 52-day booking lag with a drawdown
#: inside it. Read by the tests through this module so the demonstration anchor
#: is named once.
DEMONSTRATION_FACILITY = "FAC-01BB3F"

#: The drawdown date, and the instant the dispute question is asked at.
DEMONSTRATION_DRAWDOWN = "2025-09-09"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Covenant-in-force as-of.")
    parser.add_argument("--facility", default=DEMONSTRATION_FACILITY)
    parser.add_argument("--as-of", default=DEMONSTRATION_DRAWDOWN)
    parser.add_argument(
        "--known-as-of", default=None,
        help="omit to ask both axes at --as-of (the dispute question)",
    )
    args = parser.parse_args(argv)
    known_as_of = args.known_as_of or args.as_of

    asked = deployment.request(
        facility_id=args.facility,
        principal_scope=[args.facility],
        asked_at=datetime.now(UTC),
        as_of=args.as_of,
        known_as_of=known_as_of,
    )

    with tempfile.TemporaryDirectory(prefix="cp-08-") as scratch:
        outcome = produce.assemble_and_serve(asked=asked, root=Path(scratch))

        if isinstance(outcome, RefusalEnvelope):
            print(f"REFUSED  {outcome.reason}")
            print(f"         {outcome.detail or ''}")
            return 1

        payload = outcome.product.payload
        window = payload["window"]
        admitted = payload["amendments_in_force_and_known"]
        excluded = payload["amendments_excluded"]

        print(f"facility {args.facility}")
        print(f"  as_of        {window['as_of']}   — was it in force?")
        print(f"  known_as_of  {window['known_as_of']}   — had we booked it?")
        if args.known_as_of is None:
            print("               (both axes at the drawdown date — the dispute question)")
        print()

        print(f"  IN FORCE AND KNOWN  ({len(admitted)})")
        for entry in admitted:
            lag = entry["booking_lag_days"]
            print(f"    {entry['amendment_id']:18s} effective {entry['valid_from']}"
                  f"  booked {entry['asserted_at']}"
                  f"{'  (' + lag + '-day lag)' if lag else ''}")

        print(f"\n  EXCLUDED  ({len(excluded)})")
        for entry in excluded:
            print(f"    {entry['amendment_id']:18s} {entry['excluded_by']}")
            print(f"    {'':18s} {entry['because']}")
        if not excluded:
            print("    —")

        covenants = payload["covenants"]
        print(f"\n  COVENANTS CARRIED  ({len(covenants)}) — terms as they stand TODAY")
        for covenant in covenants:
            print(f"    {str(covenant['covenant_type']):24s} threshold {covenant['threshold']}")
        print(f"\n  {payload['covenant_terms_note'].strip()}")

        print(f"\n  D_c {outcome.product.debt.debt}  signal {outcome.product.debt.signal}"
              "   — the platform's reference assessment; this product declares none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
