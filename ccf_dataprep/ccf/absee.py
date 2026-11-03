"""Streaming parser for SEC Form ABS-EE loan-level XML (auto-loan schema).

One EX-102 file is 70-180 MB and carries 19,000-49,000 asset records, so
nothing here materializes the document. `iterparse` with an explicit
`elem.clear()` keeps resident memory flat regardless of file size.

## Absence is meaningful, and the meanings differ

ABS-EE omits optional elements rather than emitting them empty. `coerce`
therefore distinguishes three cases, and getting them wrong is silent:

  * a missing AMOUNT means zero -- nothing was charged off, nothing recovered;
  * a missing CODE means unknown -- and `0` is a real code, so mapping
    absence onto it marks live loans as terminated;
  * a missing STATUS means not measured -- and `0` means CURRENT, so mapping
    absence onto it moves paid-off loans into the performing population and
    biases every delinquency ratio downward.

The third is the dangerous one, because it moves a trigger measure in the
reassuring direction.

## Decimal, not float

Pool balances are summed across ~1.3M rows. `float` accumulates visible
drift at that count, and the resulting pool balance is the denominator of
every ratio in the product.

## Unknown elements fail loud, not silent

`ABSEE_FIELDS` is meant to be exhaustive. If `coerce` silently ignored any
element not in that tuple, a schema revision that adds a new field would
quietly drop a column across 1.32M rows -- the exact failure mode this
module exists to prevent, just moved one level up. So `coerce` raises
`UnknownABSEEElement` naming every unrecognized element it finds, rather
than dropping them. A future ABS-EE revision should stop the load loudly
and force `ABSEE_FIELDS` to be extended, not lose data quietly.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "http://www.sec.gov/edgar/document/absee/autoloan/assetdata"
_ASSETS = f"{{{NS}}}assets"
_TAG = re.compile(r"\{.*\}")


class UnknownABSEEElement(ValueError):
    """`coerce` received an element not present in `ABSEE_FIELDS`.

    Raised rather than silently dropped -- see the module docstring.
    """


#: Every element observed across both issuers, 2026-06 files. Load order.
ABSEE_FIELDS: tuple[str, ...] = (
    "assetTypeNumber", "assetNumber",
    "reportingPeriodBeginningDate", "reportingPeriodEndingDate",
    "originatorName", "originationDate",
    "originalLoanAmount", "originalLoanTerm",
    "originalInterestRatePercentage", "interestCalculationTypeCode",
    "originalInterestRateTypeCode", "originalFirstPaymentDate",
    "underwritingIndicator", "gracePeriodNumber", "paymentTypeCode",
    "subvented", "vehicleManufacturerName", "vehicleModelName",
    "vehicleNewUsedCode", "vehicleModelYear", "vehicleTypeCode",
    "vehicleValueAmount", "vehicleValueSourceCode",
    "obligorCreditScoreType", "obligorCreditScore",
    "obligorIncomeVerificationLevelCode", "obligorEmploymentVerificationCode",
    "coObligorIndicator", "paymentToIncomePercentage",
    "obligorGeographicLocation", "assetAddedIndicator",
    "reportingPeriodModificationIndicator", "modificationTypeCode",
    "servicingAdvanceMethodCode", "servicingFeePercentage",
    "reportingPeriodBeginningLoanBalanceAmount",
    "reportingPeriodInterestRatePercentage",
    "nextInterestRatePercentage", "nextReportingPeriodPaymentAmountDue",
    "reportingPeriodScheduledPaymentAmount",
    "scheduledInterestAmount", "scheduledPrincipalAmount",
    "otherPrincipalAdjustmentAmount",
    "actualInterestCollectedAmount", "actualPrincipalCollectedAmount",
    "actualOtherCollectedAmount", "totalActualAmountPaid",
    "reportingPeriodActualEndBalanceAmount",
    "remainingTermToMaturityNumber", "loanMaturityDate",
    "interestPaidThroughDate", "paymentExtendedNumber",
    "zeroBalanceEffectiveDate", "zeroBalanceCode",
    "currentDelinquencyStatus",
    "primaryLoanServicerName", "mostRecentServicingTransferReceivedDate",
    "assetSubjectDemandIndicator",
    "otherAssessedUncollectedServicerFeeAmount",
    "chargedoffPrincipalAmount", "recoveredAmount",
    "repossessedIndicator", "repossessedProceedsAmount",
)

#: Absent -> 0. Nothing happened, and zero states that faithfully.
_AMOUNT_DEFAULT_ZERO = frozenset({
    "chargedoffPrincipalAmount", "recoveredAmount",
    "repossessedProceedsAmount", "otherPrincipalAdjustmentAmount",
    "otherAssessedUncollectedServicerFeeAmount",
    "actualInterestCollectedAmount", "actualPrincipalCollectedAmount",
    "actualOtherCollectedAmount", "totalActualAmountPaid",
})

_DECIMAL_FIELDS = frozenset({
    "originalLoanAmount", "vehicleValueAmount",
    "reportingPeriodBeginningLoanBalanceAmount",
    "reportingPeriodActualEndBalanceAmount",
    "scheduledInterestAmount", "scheduledPrincipalAmount",
    "nextReportingPeriodPaymentAmountDue",
    "reportingPeriodScheduledPaymentAmount",
    "originalInterestRatePercentage", "reportingPeriodInterestRatePercentage",
    "nextInterestRatePercentage", "paymentToIncomePercentage",
    "servicingFeePercentage",
} | _AMOUNT_DEFAULT_ZERO)

_INT_FIELDS = frozenset({
    "originalLoanTerm", "gracePeriodNumber", "obligorCreditScore",
    "vehicleModelYear", "remainingTermToMaturityNumber",
    "paymentExtendedNumber", "currentDelinquencyStatus",
})

_BOOL_FIELDS = frozenset({
    "underwritingIndicator", "coObligorIndicator", "assetAddedIndicator",
    "reportingPeriodModificationIndicator", "assetSubjectDemandIndicator",
    "repossessedIndicator",
})

_DATE_FIELDS = frozenset({
    "reportingPeriodBeginningDate", "reportingPeriodEndingDate",
    "originationDate", "originalFirstPaymentDate", "loanMaturityDate",
    "interestPaidThroughDate", "zeroBalanceEffectiveDate",
    "mostRecentServicingTransferReceivedDate",
})


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def parse_assets(path: Path) -> Iterator[dict[str, str]]:
    """Stream `<assets>` records as raw string dicts.

    Absent elements are ABSENT from the dict. This function never invents a
    key, so `coerce` remains the single place absence is interpreted.
    """
    for _event, elem in ET.iterparse(str(path), events=("end",)):
        if elem.tag != _ASSETS:
            continue
        rec = {}
        for child in elem:
            text = (child.text or "").strip()
            if text:
                rec[_TAG.sub("", child.tag)] = text
        yield rec
        elem.clear()


def _parse_date(raw: str) -> date | None:
    """ABS-EE mixes `MM-DD-YYYY` and `MM/YYYY` inside one record."""
    raw = raw.strip()
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", raw):
        m, d, y = raw.split("-")
        return date(int(y), int(m), int(d))
    if re.fullmatch(r"\d{2}/\d{4}", raw):
        m, y = raw.split("/")
        return date(int(y), int(m), 1)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return date.fromisoformat(raw)
    return None


def coerce(rec: dict[str, str]) -> dict[str, object]:
    """Type the raw record, applying the absence rules in the module docstring.

    Raises `UnknownABSEEElement` if `rec` contains a key not in
    `ABSEE_FIELDS`, naming every such key. Absence is meaningful and handled
    explicitly above; an unrecognized *presence* must not be handled by
    silently ignoring it -- that is the same failure mode with the columns
    reversed.
    """
    unknown = rec.keys() - set(ABSEE_FIELDS)
    if unknown:
        raise UnknownABSEEElement(
            f"unrecognized ABS-EE element(s) not in ABSEE_FIELDS: {sorted(unknown)}"
        )
    out: dict[str, object] = {}
    for field in ABSEE_FIELDS:
        key = snake(field)
        raw = rec.get(field)

        if raw is None:
            # The three absence meanings. Amounts default to zero; everything
            # else stays NULL, because for codes and statuses a zero is a real
            # value with a different meaning.
            out[key] = Decimal(0) if field in _AMOUNT_DEFAULT_ZERO else None
            continue

        if field in _DECIMAL_FIELDS:
            out[key] = Decimal(raw)
        elif field in _INT_FIELDS:
            out[key] = int(Decimal(raw))
        elif field in _BOOL_FIELDS:
            out[key] = raw.strip().lower() in {"true", "1", "y", "yes"}
        elif field in _DATE_FIELDS:
            out[key] = _parse_date(raw)
        else:
            # Servicer names are space-padded to fixed width in the source.
            out[key] = raw.strip()
    return out


def delinquency_days(rec: dict[str, object]) -> int | None:
    """Days delinquent, or None where the period did not measure it.

    None is NOT zero. Zero means current; None means the loan carried no
    delinquency measurement this period, which is typical of zero-balance
    assets that ABS-EE keeps reporting after payoff.
    """
    value = rec.get("current_delinquency_status")
    return None if value is None else int(value)
