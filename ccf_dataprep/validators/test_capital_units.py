"""The units regression. A ratio cannot see a 1,000x error; a magnitude can.

`bank_capital` and `member_call_report` come from FDIC BankFind, which reports
in THOUSANDS of dollars. `facility.commitment_amount` is plain dollars. The
capstone divides one by the other, so a lost unit is a 1,000x error in every
percentage the product exists to produce.

The existing CET1 check in `load_reporting_bank.py` passes either way: it
compares tier 1 / RWA against the filed ratio, and both operands carry the
same unit, so the unit cancels. These tests assert a MAGNITUDE, which does not
cancel.
"""
from __future__ import annotations

import pytest

from ccf.config import PG_SCHEMA_V2 as S, pg_connect

#: Every FDIC-insured row in the estate. Measured 2026-08-27: the 16 peers
#: span $159.8bn - $4,091.3bn in assets and the reporting bank is $4,091.3bn.
#: Under a 1,000x error they would read $0.16bn - $4.09bn. A $10bn floor
#: clears every true value by at least 16x and misses every wrong value by at
#: least 2.4x -- a ~39x gap between the populations.
ASSETS_FLOOR_USD = 10_000_000_000

#: The reporting bank alone. JPMorgan Chase Bank, N.A. is a $4tn institution.
REPORTING_BANK_RSSD = "852218"
REPORTING_BANK_BAND_USD = (1_000_000_000_000, 10_000_000_000_000)


def _rows(table: str) -> list[tuple]:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT rssd, total_assets, unit FROM "{S}".{table}')
        return cur.fetchall()


def _to_usd(amount, unit: str) -> float:
    assert unit == "USD_THOUSANDS", f"unexpected unit {unit!r}"
    return float(amount) * 1000


@pytest.mark.parametrize("table", ["bank_capital", "member_call_report"])
def test_unit_column_is_recorded(table: str) -> None:
    rows = _rows(table)
    assert rows, f"{table} is empty -- the test would pass vacuously"
    for rssd, _assets, unit in rows:
        assert unit == "USD_THOUSANDS", f"{table} {rssd} carries unit {unit!r}"


@pytest.mark.parametrize("table", ["bank_capital", "member_call_report"])
def test_assets_clear_the_magnitude_floor(table: str) -> None:
    """The control the ratio check never was."""
    rows = _rows(table)
    assert rows, f"{table} is empty -- the test would pass vacuously"
    for rssd, assets, unit in rows:
        usd = _to_usd(assets, unit)
        assert usd >= ASSETS_FLOOR_USD, (
            f"{table} {rssd}: total assets ${usd/1e9:.1f}bn is below the "
            f"${ASSETS_FLOOR_USD/1e9:.0f}bn floor -- this is what a lost "
            f"1,000x factor looks like")


def test_reporting_bank_sits_in_its_own_band() -> None:
    lo, hi = REPORTING_BANK_BAND_USD
    rows = [r for r in _rows("bank_capital") if r[0] == REPORTING_BANK_RSSD]
    assert rows, "no bank_capital rows for the reporting bank"
    for rssd, assets, unit in rows:
        usd = _to_usd(assets, unit)
        assert lo <= usd <= hi, (
            f"reporting bank {rssd}: ${usd/1e9:.1f}bn outside ${lo/1e12:.0f}tn"
            f"-${hi/1e12:.0f}tn")


def test_the_floor_actually_discriminates() -> None:
    """Negative control: the floor must REJECT a 1,000x-wrong value.

    Without this, a floor set too low would pass forever and prove nothing.
    The estate's smallest true value is asserted to clear the floor, and that
    same value divided by 1,000 is asserted to fail it.
    """
    rows = _rows("member_call_report")
    assert rows, "member_call_report is empty"
    smallest = min(_to_usd(a, u) for _r, a, u in rows)
    assert smallest >= ASSETS_FLOOR_USD, "smallest true value must pass"
    assert smallest / 1000 < ASSETS_FLOOR_USD, (
        "the floor does not discriminate: a 1,000x-wrong value would also "
        "pass it, so this check would never fail")


def test_ratio_check_is_unit_invariant_and_therefore_insufficient() -> None:
    """Documents WHY the magnitude check exists, executably.

    Scaling both operands by 1,000 leaves the ratio identical. If this ever
    fails, the reasoning in docs/wave19-design.md section 3 is wrong.
    """
    tier1, rwa = 295_758_000, 1_961_368_325
    assert (tier1 / rwa) == ((tier1 * 1000) / (rwa * 1000))


class _StubCursor:
    """Minimal cursor: returns canned rows, records nothing.

    Lets the real assertion run against a 1,000x-wrong population without any
    connection to the estate.
    """

    def __init__(self, rows):
        self._rows, self._last = rows, []

    def execute(self, sql, params=None):
        if "member_call_report" in sql:
            self._last = self._rows["member_call_report"]
        elif "WHERE rssd" in sql:
            self._last = [(r[1], r[2]) for r in self._rows["bank_capital"]]
        else:
            self._last = self._rows["bank_capital"]

    def fetchall(self):
        return self._last


def test_assertion_rejects_a_thousandfold_error() -> None:
    """The negative control, run against the real assertion, no DB writes."""
    from loaders.load_wave19_postgres import assert_capital_magnitudes

    wrong = {                      # true values divided by 1,000
        "bank_capital": [("852218", 4_091_315, "USD_THOUSANDS")],
        "member_call_report": [("233031", 159_787, "USD_THOUSANDS")],
    }
    with pytest.raises(AssertionError, match="below the"):
        assert_capital_magnitudes(_StubCursor(wrong))


def test_assertion_accepts_the_true_population() -> None:
    """The positive control. Without it, an assertion that rejects
    EVERYTHING would pass the test above and prove nothing."""
    from loaders.load_wave19_postgres import assert_capital_magnitudes

    right = {
        "bank_capital": [("852218", 4_091_315_000, "USD_THOUSANDS")],
        "member_call_report": [("233031", 159_787_000, "USD_THOUSANDS")],
    }
    assert_capital_magnitudes(_StubCursor(right))   # must not raise
