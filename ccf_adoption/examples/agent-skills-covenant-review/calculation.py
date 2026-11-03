# Copyright (c) 2026 David Castillo. All rights reserved.
"""Illustrative covenant definitions, deliberately outside the SDK library."""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext


def calculate(row: Mapping[str, str]) -> dict[str, str]:
    """Compare unrounded ratios; round only the displayed values to two places.

    All inputs are decimal strings. Positive EBITDA and interest expense are
    required for these illustrative formulas. Other cases need an agreed
    business treatment and are refused here, never labelled compliant.
    """
    numbers = {}
    for name in (
        "total_debt", "ebitda", "interest_expense",
        "maximum_leverage", "minimum_interest_coverage",
    ):
        value = row[name]
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a decimal string")
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f"{name} is not a decimal") from exc
        if not number.is_finite():
            raise ValueError(f"{name} must be finite")
        if number < 0 or (name != "total_debt" and number == 0):
            raise ValueError(f"{name} is outside this example's supported range")
        numbers[name] = number

    with localcontext() as context:
        context.prec = 50
        debt, ebitda, interest = (
            numbers["total_debt"], numbers["ebitda"], numbers["interest_expense"]
        )
        maximum = numbers["maximum_leverage"]
        minimum = numbers["minimum_interest_coverage"]
        leverage = debt / ebitda
        coverage = ebitda / interest
        # Compare before display rounding. Exact equality is compliant.
        leverage_breach = debt > maximum * ebitda
        coverage_breach = ebitda < minimum * interest

        def display(number: Decimal) -> str:
            return str(number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        return {
            "leverage": display(leverage),
            "maximum_leverage": display(maximum),
            "leverage_headroom": display(maximum - leverage),
            "interest_coverage": display(coverage),
            "minimum_interest_coverage": display(minimum),
            "coverage_headroom": display(coverage - minimum),
            "leverage_breach": str(leverage_breach).lower(),
            "coverage_breach": str(coverage_breach).lower(),
            "status": "review-required" if leverage_breach or coverage_breach else "within-limits",
        }


class CovenantCalculator:
    """Read a fixed synthetic portfolio; no network, writes, or model calls."""

    def __init__(self, financials: dict) -> None:
        self.financials = financials
        self.calls = 0

    def __call__(self, arguments: Mapping[str, str]) -> Mapping[str, str]:
        self.calls += 1
        counterparty_id = arguments["counterparty_id"]
        rows = self.financials["counterparties"]
        if counterparty_id not in rows:
            raise ValueError("Counterparty is outside the demonstration portfolio")
        return {
            "counterparty_id": counterparty_id,
            "as_of": self.financials["as_of"],
            "currency": self.financials["currency"],
            "monetary_unit": self.financials["monetary_unit"],
            "flow_period": self.financials["flow_period"],
            **calculate(rows[counterparty_id]),
        }
