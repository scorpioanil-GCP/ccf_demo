"""ABS-EE parser tests. The absence cases are the point.

A parser that maps every missing element to zero produces a pool where
every loan is current and every loan has paid off -- simultaneously, and
silently. Both defects load cleanly.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ccf.absee import UnknownABSEEElement, coerce, delinquency_days, parse_assets

NS = "http://www.sec.gov/edgar/document/absee/autoloan/assetdata"


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "ex102.xml"
    p.write_text(f'<?xml version="1.0" encoding="utf-8"?>\n'
                 f'<assetData xmlns="{NS}">\n{textwrap.dedent(body)}\n</assetData>\n')
    return p


ACTIVE = """
  <assets>
    <assetTypeNumber>RANDOMID</assetTypeNumber>
    <assetNumber>471915860</assetNumber>
    <reportingPeriodBeginningDate>06-01-2026</reportingPeriodBeginningDate>
    <reportingPeriodEndingDate>06-30-2026</reportingPeriodEndingDate>
    <originalLoanAmount>62866.67000000</originalLoanAmount>
    <obligorCreditScore>726</obligorCreditScore>
    <obligorGeographicLocation>CA</obligorGeographicLocation>
    <reportingPeriodActualEndBalanceAmount>14211.05000000</reportingPeriodActualEndBalanceAmount>
    <currentDelinquencyStatus>61</currentDelinquencyStatus>
  </assets>
"""

PAID_OFF = """
  <assets>
    <assetTypeNumber>RANDOMID</assetTypeNumber>
    <assetNumber>471915861</assetNumber>
    <reportingPeriodBeginningDate>06-01-2026</reportingPeriodBeginningDate>
    <reportingPeriodEndingDate>06-30-2026</reportingPeriodEndingDate>
    <originalLoanAmount>30000.00000000</originalLoanAmount>
    <reportingPeriodActualEndBalanceAmount>0.00000000</reportingPeriodActualEndBalanceAmount>
    <zeroBalanceEffectiveDate>07/2024</zeroBalanceEffectiveDate>
    <zeroBalanceCode>4</zeroBalanceCode>
  </assets>
"""


COLLECTED = """
  <assets>
    <assetTypeNumber>RANDOMID</assetTypeNumber>
    <assetNumber>471915862</assetNumber>
    <reportingPeriodBeginningDate>06-01-2026</reportingPeriodBeginningDate>
    <reportingPeriodEndingDate>06-30-2026</reportingPeriodEndingDate>
    <originalLoanAmount>20000.00000000</originalLoanAmount>
    <reportingPeriodActualEndBalanceAmount>15000.00000000</reportingPeriodActualEndBalanceAmount>
    <actualInterestCollectedAmount>50.25000000</actualInterestCollectedAmount>
    <actualPrincipalCollectedAmount>400.75000000</actualPrincipalCollectedAmount>
    <actualOtherCollectedAmount>0.00000000</actualOtherCollectedAmount>
    <totalActualAmountPaid>451.00000000</totalActualAmountPaid>
  </assets>
"""


def test_streams_every_asset(tmp_path):
    path = _write(tmp_path, ACTIVE + PAID_OFF)
    assert len(list(parse_assets(path))) == 2


def test_absent_element_is_absent_not_none(tmp_path):
    """The raw parse must not invent keys. Coercion decides defaults."""
    path = _write(tmp_path, ACTIVE)
    rec = next(parse_assets(path))
    assert "zeroBalanceCode" not in rec
    assert rec["currentDelinquencyStatus"] == "61"


def test_absent_zero_balance_code_stays_null(tmp_path):
    """An active loan must not be coerced to zeroBalanceCode 0.

    Code 0 is not 'no code' -- ABS-EE uses it. Mapping absence onto it marks
    live loans as terminated and the pool balance would still foot, because
    balances are summed independently.
    """
    path = _write(tmp_path, ACTIVE)
    out = coerce(next(parse_assets(path)))
    assert out["zero_balance_code"] is None
    assert out["zero_balance_effective_date"] is None


def test_absent_amounts_coerce_to_zero(tmp_path):
    path = _write(tmp_path, ACTIVE)
    out = coerce(next(parse_assets(path)))
    assert out["chargedoff_principal_amount"] == 0
    assert out["recovered_amount"] == 0


def test_absent_delinquency_status_is_null_not_current(tmp_path):
    """Absent delinquency is unknown, not current.

    Coercing it to 0 makes every paid-off loan count as a performing loan in
    the denominator and never in the numerator, which biases the delinquency
    percentage downward -- the exact direction that makes a trigger look
    further away than it is.
    """
    path = _write(tmp_path, PAID_OFF)
    out = coerce(next(parse_assets(path)))
    assert out["current_delinquency_status"] is None
    assert delinquency_days(out) is None


def test_delinquency_days_reads_the_status(tmp_path):
    path = _write(tmp_path, ACTIVE)
    out = coerce(next(parse_assets(path)))
    assert delinquency_days(out) == 61


def test_dates_parse_both_layouts(tmp_path):
    """ABS-EE mixes MM-DD-YYYY and MM/YYYY in the same record."""
    path = _write(tmp_path, PAID_OFF)
    out = coerce(next(parse_assets(path)))
    assert out["reporting_period_ending_date"].isoformat() == "2026-06-30"
    assert out["zero_balance_effective_date"].isoformat() == "2024-07-01"


def test_numeric_precision_is_preserved(tmp_path):
    """Balances are Decimal, not float. Summing 1.3M floats drifts."""
    from decimal import Decimal
    path = _write(tmp_path, ACTIVE)
    out = coerce(next(parse_assets(path)))
    assert out["reporting_period_actual_end_balance_amount"] == Decimal("14211.05")
    assert isinstance(out["reporting_period_actual_end_balance_amount"], Decimal)


def test_actual_collected_amounts_present_and_absent(tmp_path):
    """actualInterestCollectedAmount et al. are monetary: present -> Decimal,
    absent -> Decimal(0), same as the other amount fields."""
    from decimal import Decimal

    path = _write(tmp_path, COLLECTED)
    out = coerce(next(parse_assets(path)))
    assert out["actual_interest_collected_amount"] == Decimal("50.25")
    assert out["actual_principal_collected_amount"] == Decimal("400.75")
    assert out["actual_other_collected_amount"] == Decimal("0.00")
    assert out["total_actual_amount_paid"] == Decimal("451.00")

    path = _write(tmp_path, ACTIVE)
    out = coerce(next(parse_assets(path)))
    assert out["actual_interest_collected_amount"] == Decimal(0)
    assert out["actual_principal_collected_amount"] == Decimal(0)
    assert out["actual_other_collected_amount"] == Decimal(0)
    assert out["total_actual_amount_paid"] == Decimal(0)


def test_coerce_raises_on_unrecognized_element(tmp_path):
    """An element ABS-EE adds that ABSEE_FIELDS doesn't know about must stop
    the load, not vanish. See ccf/absee.py's module docstring."""
    path = _write(tmp_path, ACTIVE.replace(
        "</assets>",
        "  <invented-future-field>x</invented-future-field>\n  </assets>",
    ))
    rec = next(parse_assets(path))
    assert "invented-future-field" in rec
    with pytest.raises(UnknownABSEEElement):
        coerce(rec)
