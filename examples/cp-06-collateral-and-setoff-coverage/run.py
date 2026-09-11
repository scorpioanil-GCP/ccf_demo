"""Run the example and show a reader what came back.

[ADAPT] freely — this file is presentation and nothing else. It carries no
marker region, so nothing printed here is published-snippet surface, and it is
the ONLY module in this example that writes to a terminal.

Usage::

    make example-cp-06
    make example-cp-06 FACILITY=--facility=FAC-102496 SCOPE=--scope=549300TMDIT8WREDOF45
    make example-cp-06 HAIRCUTS=--no-haircuts
    make example-cp-06 BASIS=--jurisdiction-basis=contractual

Every flag is OMITTED unless you pass it, so the class default in
``ccf_config.yaml`` resolves — a different act from passing the default's value,
and the run prints which happened.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import deployment
import produce
from ccf.products.refusal import RefusalEnvelope

#: The facility this example demonstrates against, and the borrower scope its
#: caller is entitled to walk. Arguments, not constants in the fabric's path.
DEMONSTRATION_FACILITY = "FAC-044206"
DEMONSTRATION_SCOPE = "529900E95812SYWMCE44"


def _money(value: str) -> str:
    return f"{Decimal(value):>18,.0f}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Collateral & set-off coverage")
    parser.add_argument("--facility", default=DEMONSTRATION_FACILITY)
    parser.add_argument("--scope", default=DEMONSTRATION_SCOPE)
    parser.add_argument("--no-haircuts", dest="haircuts", action="store_false",
                        default=None, help="omit to let the class default resolve")
    parser.add_argument("--no-setoff", dest="setoff", action="store_false",
                        default=None)
    parser.add_argument("--jurisdiction-basis", choices=("contractual", "enforceable"),
                        default=None)
    parser.add_argument("--shared-collateral", choices=("priority", "pro-rata"),
                        default=None)
    parsed = parser.parse_args(argv[1:])

    asked = deployment.request(
        facility_id=parsed.facility, borrower_scope=[parsed.scope],
        asked_at=datetime.now(UTC), apply_haircuts=parsed.haircuts,
        include_setoff=parsed.setoff, jurisdiction_basis=parsed.jurisdiction_basis,
        shared_collateral=parsed.shared_collateral)

    with tempfile.TemporaryDirectory() as scratch:
        outcome = produce.assemble_and_serve(asked=asked, root=Path(scratch))

        print(f"facility    : {parsed.facility}")
        if isinstance(outcome, RefusalEnvelope):
            # A refusal is an ANSWER, not a crash: the question was governed and
            # the verdict was no. It carries the reason and the record that
            # authorized saying it.
            print(f"\nREFUSED     : {outcome.reason}")
            print(f"replay      : {outcome.replay_reference}")
            return 1

        payload = outcome.product.payload
        basis, cov, found = payload["basis"], payload["coverage"], payload["findings"]
        print(f"borrower    : {outcome.coverage.borrower_name}")
        print(f"commitment  : {_money(payload['commitment'])}")
        print("basis       : "
              + ", ".join(f"{k}={v}" for k, v in basis.items())
              + "   (a flag you did not pass took the class default)")
        print()
        print(f"collateral  : {_money(cov['collateral_value'])}")
        print(f"set-off     : {_money(cov['setoff_value'])}")
        print(f"total       : {_money(cov['total'])}")
        print(f"COVERAGE    : {Decimal(cov['coverage_ratio']):.4f}"
              f"   {'covered' if Decimal(cov['coverage_ratio']) >= 1 else 'UNDER-COVERED'}")
        if Decimal(cov["shortfall"]) > 0:
            print(f"shortfall   : {_money(cov['shortfall'])}")
        print()

        # THE THINGS A COLLATERAL COLUMN CANNOT TELL YOU.
        print("what a column could not have told you")
        print(f"   assets shared with another facility : {found['shared_assets']}")
        for asset in payload["assets"]:
            if asset["shared_with"]:
                print(f"       {asset['uri']} ({asset['lien_position']})"
                      f" also secures {', '.join(asset['shared_with'])}"
                      f" — allocated {asset['allocation_basis']}")
        print(f"   set-off excluded as unenforceable   : "
              f"{found['setoff_excluded_as_unenforceable']}")
        print(f"   pledges with no recorded priority   : "
              f"{found['unpositioned_pledges']}")
        print(f"   liens the register says are RELEASED: {found['terminated_liens']}")
        for filing in payload["ucc_filings"]:
            marker = "  <<<" if "Termination" in filing["amendment_actions"] else ""
            print(f"       UCC {filing['filing_number']} filed {filing['filed_on']}"
                  f" — {filing['state']}{marker}")

        # THE VALUATION SPREAD, per asset, never flattened.
        print("\nvaluation dates, per asset — the spread this product refuses to flatten")
        for asset in payload["assets"]:
            print(f"   {asset['uri']}  {asset['category']:22s}"
                  f" valued {asset['valuation_date']}"
                  f" ({asset['valuation_age_days']:>4} days old)")

        print()
        print(f"context debt: D_c = {outcome.product.debt.debt}")
        print(f"       signal: {outcome.product.debt.signal}")
        print(f"expires at  : {outcome.product.expires_at.isoformat()}")
        print(f"replay      : {outcome.served.replay_ref.content_address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
