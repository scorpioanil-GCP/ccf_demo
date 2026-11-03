# Wave 14 Implementation Plan — `abs-securitization-surveillance`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load three real auto-ABS deals — loan level, tranche structure,
trigger definitions and servicer reports — across twelve aligned monthly
periods, so that trigger proximity can be recomputed from ~1.32M loan records
and the fan-out cost of doing so can be measured rather than estimated.

**Architecture:** Postgres holds the loan-period fact table and the
materialized aggregates above it. Fluree holds the deal→tranche structure and
the trigger threshold assertions, dated so as-of evaluation is meaningful.
MongoDB holds prospectus and servicer text with span offsets, so every
threshold resolves to the sentence that defines it. One engineered
trigger-definition amendment supplies the only §F condition real filings
cannot.

**Tech Stack:** Python 3.12 · `uv` · psycopg 3 (`COPY`) · `xml.etree`
iterparse · pymongo · Fluree SPARQL over HTTP · existing `ccf.fetch`
harness.

**Spec:** `docs/wave14-design.md` — read it before Task 1. This plan argues
from it and does not restate its reasoning.

## Global Constraints

- **Schema:** all Postgres DDL/DML in `ccf_v2`, via `pg_connect()`; never
  hardcode the schema name, always `PG_SCHEMA_V2`.
- **Ledger:** all Fluree writes to `fibo:main` via `ccf.fluree.update`.
  Fluree is append-only — a wrong write cannot be undone.
- **Mongo:** database `fibo` via `mongo_db()`. The host also runs `rtdetect`
  with 5.5M documents — **never enumerate databases**.
- **Deals:** SDART 2022-6 (CIK 1943670), TAOT 2022-B (CIK 1914281),
  SDART 2024-1 (CIK 2004812).
- **Window:** reporting months `2025-07` through `2026-06` inclusive, keyed on
  EDGAR `reportDate`, never `filingDate`.
- **Delinquency Trigger:** `24.00%` — parsed from the prospectus at run time,
  never written as a constant in a validator.
- **Provenance:** every row carries one of `public`,
  `synthetic — internal`, `synthetic — engineered`. Three classes, not two.
- **Idempotency:** every loader re-runnable. The loan loader deletes by
  `(deal_id, period)` before insert — never upsert.
- **Fluree verification:** count writes with `ccf.fluree.stable_scalar`,
  not a bare query (`known-issues.md` §14.2).
- **SEC:** all fetches through `ccf.fetch.fetch(..., is_sec=True)` so the
  8 req/s limiter and `SEC_USER_AGENT` apply.

---

## File Structure

**Create:**

| File | Responsibility |
|---|---|
| `ccf/absee.py` | Pure ABS-EE XML streaming parser and field coercion. No I/O beyond a file handle. |
| `ccf/servicer_report.py` | Pure EX-99.1 servicer-report parser — numbered line items to a dict. |
| `generators/fetch_abs_deals.py` | Resolve the 3 deals' filings; fetch ABS-EE, 10-D, 424B5, ABS-15G. |
| `generators/extract_prospectus.py` | Prospectus text, tranche table, trigger definitions with span offsets. |
| `generators/generate_abs_overlay.py` | Holdings, materialization policy, privacy constraints, restricted principal. |
| `generators/generate_trigger_amendment.py` | The one engineered amendment. |
| `loaders/load_abs_prospectus_wave14.py` | Prospectus + servicer text and passages → MongoDB. |
| `loaders/load_abs_loans_wave14.py` | Loan-period facts → Postgres via `COPY`. |
| `loaders/load_abs_structure_wave14.py` | Deals, tranche state, servicer measures, repurchases → Postgres. |
| `loaders/load_abs_fluree_wave14.py` | Tranche structure, subordination, trigger assertions → Fluree. |
| `loaders/load_abs_aggregates_wave14.py` | Cohort performance and vintage benchmarks → Postgres. |
| `loaders/load_abs_overlay_wave14.py` | Internal overlay → Postgres + Fluree. |
| `validators/abs_surveillance.py` | The wave's gate — recomputes, never reads a flag. |
| `validators/abs_cost.py` | The granularity cost curve. |
| `validators/test_absee.py` | Parser unit tests, including the absence-is-meaningful cases. |
| `validators/test_servicer_report.py` | Servicer-report parser unit tests. |
| `validators/test_abs_amendment.py` | Mutation tests for the amendment gate. |

**Modify:**

| File | Change |
|---|---|
| `validators/conditions.py` | Nine `abs-securitization-surveillance` rows. |
| `validators/partition.py` | Wave 14 tables and predicates in the owned-slice lists. |
| `docs/ccf_dataprep_v2.md` | Wave 14 changelog, entity tables, `isSubordinateTo` binding. |
| `docs/HANDOFF.md` | §3 product table, §8 next step. |
| `docs/known-issues.md` | Any defect found during the wave. |

---

## Task 1: Verify and bind `isSubordinateTo`

The securitization vocabulary is already bound from Waves 8 and 11c. One term
the spec names is not: `fibo-fnd-agr-ctr:isSubordinateTo`. Generating against
an unverified IRI is the failure CLAUDE.md calls out by name — it validates
here and cannot be consumed downstream.

**Files:**
- Modify: `docs/ccf_dataprep_v2.md` (binding table)

**Interfaces:**
- Produces: the constant `P_IS_SUBORDINATE_TO` used by Task 9.

- [ ] **Step 1: Verify the IRI resolves against the EDM Council source**

```bash
curl -sI "https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/isSubordinateTo" \
  | head -1
# Then confirm it appears in the module's Turtle, which is authoritative:
curl -s "https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/" \
  | grep -o 'isSubordinateTo' | head -3
```

Expected: the term appears in `FND/Agreements/Contracts/`.

**If it does not appear**, do not guess another module. Wave 8's `Tranche`
episode is the precedent: a wrong module guess is indistinguishable from a
missing term. Record it on the do-not-bind list, use `ex:isSubordinateTo`,
and note the negative result in the binding table — a recorded absence is
worth as much as a recorded presence, because it stops the next person
re-deriving it.

- [ ] **Step 2: Add the row to the binding table**

Find the object-property table in `docs/ccf_dataprep_v2.md` (near line 717,
alongside `hasAttachmentPoint`) and add, in alphabetical position:

```markdown
| isSubordinateTo | `fibo-fnd-agr-ctr:isSubordinateTo` | `.../FND/Agreements/Contracts/isSubordinateTo` |
```

Also add the prefix row if `fibo-fnd-agr-ctr` is not already present:

```markdown
| `fibo-fnd-agr-ctr` | `https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/` |
```

- [ ] **Step 3: Confirm the drift validator sees it**

Run: `uv run validators/binding_drift.py`
Expected: **no change attributable to this term.** This validator compares
vault claims against Fluree state — it is not a binding-table term count, so
it cannot see a term that has only been documented and not yet loaded. Run it
to confirm you broke nothing (measured 2026-08-23: 10 agree · 41 disagree,
exit 0), then move on. The real verification is Steps 1-2.

- [ ] **Step 4: Commit**

```bash
git add docs/ccf_dataprep_v2.md
git commit -m "Bind isSubordinateTo, verified against the EDM Council source"
```

---

## Task 2: The ABS-EE parser — absence is meaningful

**Files:**
- Create: `ccf/absee.py`
- Test: `validators/test_absee.py`

**Interfaces:**
- Produces:
  - `ABSEE_FIELDS: tuple[str, ...]` — the 63 element names, load order.
  - `parse_assets(path: Path) -> Iterator[dict]` — streams one dict per
    `<assets>` element; absent elements are absent from the dict, not `None`.
  - `coerce(rec: dict) -> dict` — typed values, with the absence rules below.
  - `delinquency_days(rec: dict) -> int | None`.

The whole wave depends on this being right, and its defects would be
invisible: a parser that mis-handles one optional field produces 1.32M rows
that load cleanly and answer wrongly.

**The rule that matters.** ABS-EE **omits** optional elements rather than
emitting them empty. So absence carries meaning, and it is not always the
same meaning:

| Element | Absent means | Coerce to |
|---|---|---|
| `zeroBalanceCode` | the loan is still active | `NULL` — **never `0`**, which is a valid code |
| `zeroBalanceEffectiveDate` | still active | `NULL` |
| `chargedoffPrincipalAmount` | nothing charged off | `0` |
| `recoveredAmount` | nothing recovered | `0` |
| `currentDelinquencyStatus` | no delinquency measured this period (typically a zero-balance loan) | `NULL` — **never `0`**, which means current |
| `modificationTypeCode` | not modified | `NULL` |

Measured on 2026-06 files: `zeroBalanceCode` present on 13.8% of TAOT
records, `currentDelinquencyStatus` on 94% of TAOT and 100% of SDART,
`recoveredAmount` on ~6% of both.

- [ ] **Step 1: Write the failing tests**

```python
# validators/test_absee.py
"""ABS-EE parser tests. The absence cases are the point.

A parser that maps every missing element to zero produces a pool where
every loan is current and every loan has paid off -- simultaneously, and
silently. Both defects load cleanly.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ccf.absee import coerce, delinquency_days, parse_assets

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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest validators/test_absee.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ccf.absee'`

- [ ] **Step 3: Implement the parser**

```python
# ccf/absee.py
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
    """Type the raw record, applying the absence rules in the module docstring."""
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest validators/test_absee.py -v`
Expected: 8 passed.

- [ ] **Step 5: Verify against a real file, not just fixtures**

Fixtures test the rules; only a real file tests the schema. Download one and
check the record count matches the measured figure:

```bash
uv run python - <<'PY'
from pathlib import Path
from ccf.absee import parse_assets, coerce, delinquency_days
p = Path("sources/absee/sdart-2022-6/2026-06.xml")   # after Task 3
n = delinq = 0
from decimal import Decimal
bal = Decimal(0)
for rec in parse_assets(p):
    c = coerce(rec); n += 1
    bal += c["reporting_period_actual_end_balance_amount"]
    d = delinquency_days(c)
    if d is not None and d >= 60: delinq += 1
print(f"{n:,} assets, pool balance {bal:,.2f}, {delinq:,} at 60+ days")
PY
```

Expected: 35,814 assets for SDART 2022-6 at 2026-06. **If the count differs,
stop** — the parser is dropping or duplicating records and every downstream
number inherits it.

- [ ] **Step 6: Commit**

```bash
git add ccf/absee.py validators/test_absee.py
git commit -m "ABS-EE streaming parser: absence is meaningful, three ways"
```

---

## Task 3: Fetch the deal filings

**Files:**
- Create: `generators/fetch_abs_deals.py`

**Interfaces:**
- Consumes: `ccf.fetch.fetch`, `SourceManifest`.
- Produces:
  - `sources/absee/<deal-slug>/<YYYY-MM>.xml` — 36 loan files.
  - `sources/absee/<deal-slug>/servicer-<YYYY-MM>.htm` — 36 servicer reports.
  - `sources/absee/<deal-slug>/prospectus.htm` — 3.
  - `sources/absee/repurchase/<depositor>-<accession>.htm` — ABS-15G.
  - `sources/absee/deals.json` — the registry every later task reads.

**Two layout traps, both silent.**

1. **ABS-15G is filed by the depositor, not the trust.** A per-trust search
   returns zero filings and reads as "no repurchase activity". Santander's sit
   under CIK 1383094; Toyota's under CIK 1131131.
2. ~~**Santander co-files ABS-EE and 10-D in one accession**~~ — **WRONG, and
   corrected during Task 3.** Both issuers file ABS-EE and 10-D as separate
   accessions. The real trap is narrower: resolve the EX-102 by filename suffix
   within the accession rather than assuming a form-to-file mapping. Fixed in
   `generators/fetch_abs_deals.py` and `docs/wave14-design.md`; left here struck
   through rather than deleted so the plan still records what was believed.

- [ ] **Step 1: Write the deal registry and resolver**

```python
#!/usr/bin/env python3
"""Fetch the three ABS deals' filings for the Wave 14 window.

    uv run generators/fetch_abs_deals.py --dry-run   # resolve, fetch nothing
    uv run generators/fetch_abs_deals.py             # ~5.4 GB, be patient

Idempotent: `ccf.fetch` skips any URL already recorded whose payload still
exists, so an interrupted run resumes for free.

## Why the window is keyed on reportDate

EDGAR's `filingDate` and `reportDate` differ by 2-7 weeks and the lag varies
by filer. Selecting on filing date would silently mis-align the three deals
by up to two reporting months, and a vintage benchmark that compares one
deal's July with another's September is not a benchmark -- it is noise with
a table around it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date

import requests

from ccf.config import REPO_ROOT
from ccf.fetch import SEC_LIMITER, SourceManifest, fetch, sec_headers

SOURCE = "absee"
OUT = REPO_ROOT / "sources" / SOURCE
REGISTRY = OUT / "deals.json"

WINDOW = tuple(f"{y}-{m:02d}" for y, m in
               [(2025, m) for m in range(7, 13)] + [(2026, m) for m in range(1, 7)])

#: `prospectus_filed` is the 424B5 filing date, verified on EDGAR 2026-08-22.
#: It is the assertion date for every original trigger threshold -- the date
#: the market could first have known the number. Task 9 depends on it, and
#: using today's date there instead would make the bitemporal check in Task 13
#: pass vacuously (`known_as_of` would find no assertion at all and return
#: None, so `as_of != known_as_of` would hold for the wrong reason).
DEALS = [
    {"deal_id": "SDART-2022-6", "slug": "sdart-2022-6", "cik": "1943670",
     "legal_name": "Santander Drive Auto Receivables Trust 2022-6",
     "credit_tier": "subprime", "vintage": 2022, "servicer": "Santander Consumer USA Inc.",
     "depositor_cik": "1383094", "prospectus_filed": "2022-09-14",
     "prospectus": ("0001193125-22-244774", "d399127d424b5.htm")},
    {"deal_id": "TAOT-2022-B", "slug": "taot-2022-b", "cik": "1914281",
     "legal_name": "Toyota Auto Receivables 2022-B Owner Trust",
     "credit_tier": "prime", "vintage": 2022, "servicer": "Toyota Motor Credit Corporation",
     "depositor_cik": "1131131", "prospectus_filed": "2022-04-11",
     "prospectus": ("0000929638-22-000773", "a424b5.htm")},
    {"deal_id": "SDART-2024-1", "slug": "sdart-2024-1", "cik": "2004812",
     "legal_name": "Santander Drive Auto Receivables Trust 2024-1",
     "credit_tier": "subprime", "vintage": 2024, "servicer": "Santander Consumer USA Inc.",
     "depositor_cik": "1383094", "prospectus_filed": "2024-01-16",
     "prospectus": ("0001193125-24-008591", "d605182d424b5.htm")},
]


def submissions(cik: str) -> dict:
    SEC_LIMITER.wait()
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    r = requests.get(url, headers=sec_headers(), timeout=60)
    r.raise_for_status()
    return r.json()


#: `<TYPE>...<FILENAME>` triples in an EDGAR submission header.
_DOC = re.compile(r"<TYPE>([^\r\n<]+)[\r\n]+<SEQUENCE>(\d+)[\r\n]+"
                  r"<FILENAME>([^\r\n<]+)")


def accession_files(cik: str, accession: str) -> list[tuple[str, str]]:
    """Return [(document_type, filename)] from the SUBMISSION HEADER.

    NOT from `index.json`. Measured 2026-08-23 on Toyota accession
    0001193125-26-322407: `index.json` lists four entries and OMITS
    `d70261dex991.htm`, the EX-99.1 servicer certificate -- which fetches
    perfectly well (HTTP 200, 140 KB) and is listed in the submission header
    as SEQUENCE 2. The same call on the Santander accessions lists their
    EX-99.1 correctly.

    That asymmetry is the danger: resolving through `index.json` works for two
    of the three deals and silently reports "no servicer report" for the
    third, across all twelve of its periods. A guard that raises on the empty
    result then reads as a data problem rather than a resolution bug.

    The header is fetched with a Range request -- the full submission text is
    the concatenation of every document (72 MB for an ABS-EE accession), and
    the header sits in the first few kilobytes.
    """
    SEC_LIMITER.wait()
    acc = accession.replace("-", "")
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/"
           f"{accession}.txt")
    headers = {**sec_headers(), "Range": "bytes=0-32767"}
    r = requests.get(url, headers=headers, timeout=60)
    if r.status_code not in (200, 206):
        r.raise_for_status()
    docs = [(t.strip(), f.strip()) for t, _seq, f in _DOC.findall(r.text)]
    if not docs:
        raise RuntimeError(
            f"{accession}: no <TYPE>/<FILENAME> entries in the first 32 KB of "
            f"the submission header. Do not fall back to index.json -- it is "
            f"incomplete for at least one filer in this wave.")
    return docs


def archive(cik: str, accession: str, name: str) -> str:
    return (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{accession.replace('-', '')}/{name}")


def resolve(deal: dict) -> dict:
    """Map each window month to its ABS-EE and 10-D accession."""
    sub = submissions(deal["cik"])["filings"]["recent"]
    rows = list(zip(sub["form"], sub["accessionNumber"], sub["reportDate"]))

    periods: dict[str, dict] = {}
    for form, accession, report_date in rows:
        if not report_date:
            continue
        month = report_date[:7]
        if month not in WINDOW or form not in {"ABS-EE", "10-D"}:
            continue
        periods.setdefault(month, {})[form] = accession

    missing = [m for m in WINDOW if "ABS-EE" not in periods.get(m, {})]
    if missing:
        raise RuntimeError(
            f"{deal['deal_id']}: no ABS-EE for {missing}. The window is fixed "
            f"by docs/wave14-design.md §2.1 -- do not silently shorten it.")
    return periods
```

- [ ] **Step 2: Add the fetch loop**

```python
def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Wave 14 ABS deal filings")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve accessions and report sizes, fetch nothing")
    args = ap.parse_args()

    manifest = SourceManifest(
        source=SOURCE,
        description=("SEC Form ABS-EE loan-level XML, 424B5 prospectuses, "
                     "10-D servicer reports and ABS-15G repurchase filings "
                     "for three auto-ABS deals, 2025-07..2026-06."),
        licence="US public domain (SEC EDGAR)",
    ).load()

    registry = {"generated_at": date.today().isoformat(),
                "window": list(WINDOW), "deals": []}

    for deal in DEALS:
        print(f"\n{deal['deal_id']}  ({deal['legal_name']})")
        periods = resolve(deal)
        dest = OUT / deal["slug"]
        entry = {**deal, "periods": {}}

        # Prospectus -- one per deal, the anchor for every trigger threshold.
        acc, doc = deal["prospectus"]
        if not args.dry_run:
            fetch(archive(deal["cik"], acc, doc), manifest,
                  f"{deal['slug']}/prospectus.htm", is_sec=True)
        entry["prospectus_url"] = archive(deal["cik"], acc, doc)

        for month in WINDOW:
            found = periods[month]
            docs = accession_files(deal["cik"], found["ABS-EE"])
            names = [n for _t, n in docs]

            # Resolve by DECLARED TYPE first, falling back to the filename
            # suffix. The two issuers lay accessions out differently and
            # Santander co-files the servicer report beside the loan XML.
            ex102 = [n for t, n in docs if t.upper() == "EX-102"] or \
                    [n for n in names if n.endswith("ex102.xml")]
            if len(ex102) != 1:
                raise RuntimeError(
                    f"{deal['deal_id']} {month}: expected exactly one "
                    f"*ex102.xml in {found['ABS-EE']}, found {ex102}")

            rec = {"absee_accession": found["ABS-EE"], "absee_file": ex102[0]}

            # The servicer report: same accession for Santander, the 10-D
            # accession for Toyota.
            servicer_acc = found.get("10-D", found["ABS-EE"])
            servicer_docs = (docs if servicer_acc == found["ABS-EE"]
                             else accession_files(deal["cik"], servicer_acc))
            ex991 = [n for t, n in servicer_docs if t.upper() == "EX-99.1"] or \
                    [n for _t, n in servicer_docs if "ex991" in n.lower()]
            if not ex991:
                raise RuntimeError(
                    f"{deal['deal_id']} {month}: no EX-99.1 servicer report "
                    f"in {servicer_acc}. Do not fall back to the 10-D cover "
                    f"page -- it carries no distribution figures.")
            rec |= {"servicer_accession": servicer_acc, "servicer_file": ex991[0]}

            if not args.dry_run:
                fetch(archive(deal["cik"], found["ABS-EE"], ex102[0]), manifest,
                      f"{deal['slug']}/{month}.xml", is_sec=True, timeout=600)
                fetch(archive(deal["cik"], servicer_acc, ex991[0]), manifest,
                      f"{deal['slug']}/servicer-{month}.htm", is_sec=True)

            entry["periods"][month] = rec
            print(f"  {month}  {ex102[0]:<34} {ex991[0]}")

        registry["deals"].append(entry)

    # ABS-15G -- depositor level. A per-trust lookup returns nothing and
    # reads as "no repurchase activity", which is the wave's most plausible
    # silent-empty failure.
    seen = set()
    registry["repurchase"] = []
    for deal in DEALS:
        cik = deal["depositor_cik"]
        if cik in seen:
            continue
        seen.add(cik)
        sub = submissions(cik)["filings"]["recent"]
        filings = [(f, a, d) for f, a, d in
                   zip(sub["form"], sub["accessionNumber"], sub["filingDate"])
                   if f.startswith("ABS-15G")]
        if not filings:
            raise RuntimeError(
                f"depositor CIK {cik} has no ABS-15G. Check the CIK before "
                f"concluding there is no repurchase activity.")
        print(f"\nABS-15G depositor {cik}: {len(filings)} filings")
        for form, accession, filed in filings[:4]:
            doc = next((n for _t, n in accession_files(cik, accession)
                        if n.endswith((".htm", ".txt")) and "index" not in n),
                       None)
            if doc and not args.dry_run:
                fetch(archive(cik, accession, doc), manifest,
                      f"repurchase/{cik}-{accession}.htm", is_sec=True)
            registry["repurchase"].append(
                {"depositor_cik": cik, "form": form,
                 "accession": accession, "filed_date": filed, "file": doc})

    if args.dry_run:
        print("\n  DRY RUN -- nothing fetched.")
        return 0

    manifest.save()
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(registry, indent=2) + "\n")
    print(f"\n  registry -> {REGISTRY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Dry-run first**

Run: `uv run generators/fetch_abs_deals.py --dry-run`
Expected: 36 resolved period lines (12 per deal), each naming an `ex102.xml`
and an `ex991` file, plus the two depositors' ABS-15G counts. No downloads.

- [ ] **Step 4: Confirm the ignore rules split payloads from artifacts**

Already set up (`.gitignore` line 40, commit below) — verify, do not re-add:

```bash
git check-ignore -v sources/absee/deals.json            # want: the ! rule -> committable
mkdir -p sources/absee/x && touch sources/absee/x/a.xml
git check-ignore -v sources/absee/x/a.xml               # want: sources/** -> ignored
rm -rf sources/absee/x
```

`sources/**` ignores everything; `!sources/absee/*.json` un-ignores only the
four small artifacts this wave commits. Payloads live one directory deeper
(`sources/absee/<slug>/<month>.xml`), so the exemption cannot reach them.
**5.4 GB must not enter git history — it cannot be removed once committed.**

- [ ] **Step 5: Fetch**

Run: `uv run generators/fetch_abs_deals.py`
Expected: ~5.4 GB across 75 files. Verify:

```bash
du -sh sources/absee/*/ && ls sources/absee/*/ | wc -l
```

- [ ] **Step 6: Commit the manifest and registry, not the payloads**

```bash
git status --short          # confirm no .xml appears
git add generators/fetch_abs_deals.py sources/absee/manifest.json sources/absee/deals.json
git commit -m "Fetch three ABS deals across the twelve-month window"
```

---

## Task 4: The servicer-report parser — TWO formats, not one

**Files:**
- Create: `ccf/servicer_report.py`
- Test: `validators/test_servicer_report.py`

**Interfaces:**
- Produces:
  - `detect_format(text: str) -> str` — `"numbered"` or `"labelled"`.
  - `parse_servicer_report(html: str) -> dict` — dispatches on format, returns
    the SAME key set either way.
  - `UnparseableServicerReport(ValueError)` — raised, never defaulted.

**The plan originally assumed one format. It was wrong, and here is the
evidence.** Measured 2026-08-23 against both issuers' 2026-06 certificates:

| | Santander (SDART) | Toyota (TAOT) |
|---|---|---|
| Structure | numbered line items — `{79} Delinquency Percentage … 10.79 %` | pure label/value, **zero `{n}` markers** |
| Delinquency label | `Delinquency Percentage as of the End of the Collection Period` | `60-Day Delinquency Percentage` |
| Trigger label | `Delinquency Trigger` | `Delinquency Trigger Percentage` |
| Trigger value | **24.00%** | **4.65%** |
| Measured delinquency | 10.79% | 1.31% |
| Delinquency buckets | 31-60 / 61-90 / 91-120 / 121+ | **30-59 / 60-89 / 90-119 / 120+** |
| Pool balance label | `{64} End of period Principal Balance of the Receivables` | `Receivables Pool Balance` |
| OC target label | `{63} Targeted Overcollateralization` | `Overcollateralization Target Amount` |

**Two traps live in that table.**

1. **The bucket boundaries do not align.** Santander's first bucket starts at
   31 days, Toyota's at 30; Santander's 61-90 against Toyota's 60-89. Summing
   "the 61+ buckets" across issuers compares different populations. Task 11's
   vintage benchmark must therefore use the balance-weighted 60-day measure
   each servicer publishes — or recompute from loan level, where the
   day-count is per-loan and directly comparable — **never the buckets**.
2. **Toyota does not publish every field Santander does.** `oc_percent` and
   `sixty_day_delinquent_balance` have no Toyota equivalent. They must come
   back `None`, and `None` must be distinguishable from zero, exactly as in
   `ccf/absee.py`. Do not compute a substitute and present it as filed.

**Known-good values, for use as test oracles** — the 2026-06 period, read
from the files on disk and cross-checked against loan level:

| Field | SDART 2022-6 | TAOT 2022-B |
|---|---|---|
| `pool_balance` | 320202755.30 | 81727263.10 |
| `note_balance` | 216345645.95 | 0.00 |
| `delinquency_percent` | 11.18 | 1.31 |
| `delinquency_trigger` | 24.00 | 4.65 |
| `trigger_occurred` | False | False |
| `oc_target` | 103857109.35 | 14450000.06 |
| `oc_amount` | 103857109.35 | 80453472.38 |
| `oc_percent` | 32.43 | **None** |
| `sixty_day_delinquent_balance` | 35784723.53 | **None** |
| `cumulative_net_loss_percent` | 12.16 | 0.38001 |
| `receivable_count` | 23525 | 16779 |
| `source_format` | `numbered` | `labelled` |

**These replace an earlier table that was wrong, and the way it was wrong is
worth knowing.** The first version of this row set was measured from
accession `0001193125-26-352765` — whose reporting month is **2026-07**, one
month past the loaded window — and then labelled 2026-06. Every SDART figure
in it was real, filed, internally consistent, and from the wrong period. Only
`delinquency_trigger` survived, because it does not move.

The trap: `delinquency_percent` in that table read 10.79, and 10.79 *does*
appear in the window — at 2026-05. The series oscillates between 9.99 and
11.30 and hits the same value twice. So a reviewer spot-checking one number
against one file could have confirmed the table and moved on.

The implementer of this task found it, refused to force a match, and used the
on-disk values instead. That is the correct response to an oracle that
disagrees with the data: **read the document, do not adjust the parser.**

**Independently confirmed against loan level** — the strongest evidence in
this wave. Summing every loan's ending balance and every 60+ day balance
reproduces the filing exactly, at both ends of the window, for both issuers
and both report formats:

| Deal | Period | Loans | Pool: ours vs filed | Delinquency: ours vs filed |
|---|---|---|---|---|
| SDART 2022-6 | 2025-07 | 44,251 | 569,563,187.36 = 569,563,187.36 | 9.99% = 9.99% |
| SDART 2022-6 | 2026-06 | 35,814 | 320,202,755.30 = 320,202,755.30 | 11.18% = 11.18% |
| TAOT 2022-B | 2025-07 | 35,272 | 262,117,356.15 = 262,117,356.15 | 0.76% = 0.76% |
| TAOT 2022-B | 2026-06 | 19,430 | 81,727,263.10 = 81,727,263.10 | 1.31% = 1.31% |

Zero difference on every cell. Two documents, two preparers, two parsers, one
number. This is why Task 13's reconciliation tolerance is 0.02pp rather than
anything looser — the observed disagreement is 0.00.

**Why this parser exists at all**, given the loan file already carries the raw
data: it is the *independent* derivation. Task 13 compares what we compute
from loan level against what the servicer published, and two derivations that
must agree catch errors neither would catch alone.

**One more fact worth knowing before you start.** TAOT 2022-B is called
(optionally redeemed) in the final window period — its 2026-06 certificate
shows `Total Repurchased Amount $85,977,263.12` and `Total Note Balance $0.00`,
and it filed a Form 15-15D. 2026-06 is genuinely its last period. That is real
and in scope; do not treat the zero note balance as a parse failure.

- [ ] **Step 1: Write the failing tests**

Write `validators/test_servicer_report.py` covering BOTH formats. Structure it
as follows — the fixtures must be real excerpts, so take them from the files
Task 3 fetched (or fetch the two 2026-06 certificates directly):

- Santander: `https://www.sec.gov/Archives/edgar/data/1943670/000119312526352765/d140430dex991.htm`
- Toyota: `https://www.sec.gov/Archives/edgar/data/1914281/000119312526322407/d70261dex991.htm`

Required tests, at minimum:

```python
def test_detects_numbered_format():           # SDART -> "numbered"
def test_detects_labelled_format():           # TAOT  -> "labelled"
def test_numbered_reads_every_oracle_field(): # all 8 SDART values above
def test_labelled_reads_every_oracle_field(): # all 8 TAOT values above
def test_toyota_oc_percent_is_none_not_zero():
    """Toyota does not publish it. None means 'not published'; 0.00 would be
    a claim the filing does not make."""
def test_trigger_occurred_captured_as_evidence_only():
    """Captured because a disagreement with our own recomputation is a
    finding. Never read as the answer to 'did the trigger occur'."""
def test_bucket_boundaries_are_labelled_per_issuer():
    """Buckets come back keyed by the issuer's OWN boundaries, so a caller
    cannot accidentally add 61-90 to 60-89 and call it a total."""
def test_em_dash_is_zero():                   # servicer reports write nil as an em dash
def test_missing_field_raises_not_defaults():
    with pytest.raises(UnparseableServicerReport):
        parse_servicer_report("<html><body>nothing here</body></html>")
def test_unknown_format_raises():
    """A third issuer layout must fail loudly, not silently return zeros."""
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --with pytest pytest validators/test_servicer_report.py -v`
Expected: FAIL — no module `ccf.servicer_report`.

(`uv run pytest` without `--with pytest` is broken repo-wide in this project —
pytest is not a declared dependency. Pre-existing; do not fix it here.)

- [ ] **Step 3: Implement**

Write `ccf/servicer_report.py` with this shape:

```python
"""Parser for monthly servicer distribution reports (EX-99.1 to Form 10-D).

## Two formats, dispatched — never guessed

Santander numbers its line items (`{79} Delinquency Percentage ... 10.79 %`);
Toyota uses pure label/value with no numeric markers at all. `detect_format`
decides by counting `{n}` markers, and an unrecognized layout RAISES rather
than returning a dict of zeros. A third issuer's format must stop the load,
because a servicer report that silently parses to zeros would sail through
every downstream check while destroying the reconciliation it exists to
provide.

## This parser produces evidence, not answers

`trigger_occurred` is captured because the servicer publishes it, and because
a disagreement between it and our own loan-level recomputation is a finding
worth surfacing. It must NEVER be the basis for deciding whether a trigger
occurred -- `validators/abs_surveillance.py` recomputes from loan level and
uses this field only as a cross-check. Reading a stored flag that states the
answer is how three of Wave 13b's four defects survived in checks already
reporting PASS.

## None is not zero

Toyota publishes no overcollateralization PERCENTAGE and no 60-day delinquent
BALANCE. Those come back None. Substituting a computed value and returning it
beside genuinely-filed figures would present our arithmetic as the servicer's.

## Bucket boundaries differ by issuer

Santander reports 31-60 / 61-90 / 91-120 / 121+; Toyota reports
30-59 / 60-89 / 90-119 / 120+. Buckets are therefore returned keyed by the
issuer's own boundary labels, so a caller cannot add two non-comparable
buckets together and call the result a total. Cross-issuer comparison must use
the published 60-day percentage or a loan-level recomputation.
"""
```

Implement `detect_format`, a `_parse_numbered` (item-number keyed, as the
Santander layout allows) and a `_parse_labelled` (label keyed, for Toyota),
and a `parse_servicer_report` that dispatches and validates that every
required key is present. Both branches must return this key set:

```
pool_balance, note_balance, oc_amount, oc_percent, oc_target,
delinquency_percent, delinquency_trigger, trigger_occurred,
sixty_day_delinquent_balance, cumulative_net_loss_percent,
receivable_count, delinquency_buckets, source_format
```

Use `Decimal` throughout, never `float`. Servicer reports write nil as an em
dash, en dash or hyphen — all mean zero.

- [ ] **Step 4: Run to verify pass**

Run: `uv run --with pytest pytest validators/test_servicer_report.py -v`
Expected: all pass, including every oracle value in the table above.

- [ ] **Step 5: Run against all 36 real reports**

```bash
uv run python - <<'PY'
import json
from ccf.config import REPO_ROOT
from ccf.servicer_report import parse_servicer_report
reg = json.loads((REPO_ROOT/"sources/absee/deals.json").read_text())
bad = []
for deal in reg["deals"]:
    for month in reg["window"]:
        p = REPO_ROOT/f"sources/absee/{deal['slug']}/servicer-{month}.htm"
        try:
            out = parse_servicer_report(p.read_text(errors="replace"))
            print(f"{deal['deal_id']:14s} {month} [{out['source_format']:8s}]"
                  f" delinq={out['delinquency_percent']:>6}%"
                  f" trigger={out['delinquency_trigger']:>6}%"
                  f" pool={out['pool_balance']:>16,}")
        except Exception as exc:
            bad.append((deal["deal_id"], month, str(exc)[:90]))
for b in bad: print("  FAILED", b)
print(f"\n{len(bad)} of 36 failed")
PY
```

Expected: 0 failures, 24 reports detected `numbered` and 12 `labelled`. The
Santander delinquency series should rise across the window; Toyota's should
stay near 1% against its 4.65% trigger.

**If a period fails to parse, do not loosen a pattern until it matches** —
read that period's actual document. A pattern loosened to fit is how a number
from the wrong row gets bound as a threshold.

- [ ] **Step 6: Commit**

```bash
git add ccf/servicer_report.py validators/test_servicer_report.py
git commit -m "Servicer report parser: two issuer formats, dispatched not guessed"
```

---

## Task 5: Postgres schema and the loan loader

**Files:**
- Create: `loaders/load_abs_loans_wave14.py`

**Interfaces:**
- Consumes: `ccf.absee.parse_assets`, `coerce`, `ABSEE_FIELDS`.
- Produces: tables `abs_deal`, `abs_loan_period`; the `(deal_id, period)`
  delete-then-insert contract every re-run depends on.

**The defect this task must not have.** `known-issues.md` §14.10: upsert-only
loaders are not idempotent for variable-length children. The pool shrinks
every period — 44,251 assets in 2025-07 down to 35,814 in 2026-06 for
SDART 2022-6. An upsert leaves the 8,437 difference behind as ghost rows that
every query still happily reads.

- [ ] **Step 1: Write the DDL and the loader**

```python
#!/usr/bin/env python3
"""Load ABS-EE loan-level records into Postgres.

    uv run loaders/load_abs_loans_wave14.py --dry-run
    uv run loaders/load_abs_loans_wave14.py --deal SDART-2022-6 --period 2026-06
    uv run loaders/load_abs_loans_wave14.py            # all 36, ~1.32M rows

## Delete by period, never upsert

The pool shrinks: SDART 2022-6 carries 44,251 assets at 2025-07 and 35,814
at 2026-06. An upsert-only reload leaves the 8,437-row difference behind,
anchored to a period they are no longer part of. Every query still works and
every count is wrong -- `known-issues.md` §14.10, found in Wave 13b's Mongo
loader and not swept elsewhere until now.

So each (deal, period) is deleted before it is inserted, inside one
transaction, which also makes the loader resumable per period.

## COPY, not executemany

1.32M rows through `executemany` is roughly an hour. `COPY` is a few minutes.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf.absee import ABSEE_FIELDS, coerce, parse_assets, snake
from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)
REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"

COLUMNS = ("deal_id", "period") + tuple(snake(f) for f in ABSEE_FIELDS)

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_deal (
    deal_id       text PRIMARY KEY,
    legal_name    text NOT NULL,
    cik           text NOT NULL,
    depositor_cik text NOT NULL,
    credit_tier   text NOT NULL,        -- prime | subprime
    vintage       integer NOT NULL,
    servicer      text NOT NULL,
    provenance    text NOT NULL,
    source        text NOT NULL,
    retrieved_at  date NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_loan_period (
    deal_id text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    period  char(7) NOT NULL,                       -- YYYY-MM, the reportDate month
    asset_type_number text,
    asset_number      text NOT NULL,
    reporting_period_beginning_date date,
    reporting_period_ending_date    date,
    originator_name   text,
    origination_date  date,
    original_loan_amount numeric,
    original_loan_term   integer,
    original_interest_rate_percentage numeric,
    interest_calculation_type_code text,
    original_interest_rate_type_code text,
    original_first_payment_date date,
    underwriting_indicator boolean,
    grace_period_number integer,
    payment_type_code text,
    subvented text,
    vehicle_manufacturer_name text,
    vehicle_model_name text,
    vehicle_new_used_code text,
    vehicle_model_year integer,
    vehicle_type_code text,
    vehicle_value_amount numeric,
    vehicle_value_source_code text,
    obligor_credit_score_type text,
    obligor_credit_score integer,
    obligor_income_verification_level_code text,
    obligor_employment_verification_code text,
    co_obligor_indicator boolean,
    payment_to_income_percentage numeric,
    obligor_geographic_location text,          -- US state only; no address
    asset_added_indicator boolean,
    reporting_period_modification_indicator boolean,
    modification_type_code text,
    servicing_advance_method_code text,
    servicing_fee_percentage numeric,
    reporting_period_beginning_loan_balance_amount numeric,
    reporting_period_interest_rate_percentage numeric,
    next_interest_rate_percentage numeric,
    next_reporting_period_payment_amount_due numeric,
    reporting_period_scheduled_payment_amount numeric,
    scheduled_interest_amount numeric,
    scheduled_principal_amount numeric,
    other_principal_adjustment_amount numeric,
    -- Actual cash collected, as against the SCHEDULED amounts above. These
    -- four were missing from the first cut of ABSEE_FIELDS and would have
    -- been dropped silently from all 1.32M rows; both issuers emit them.
    actual_interest_collected_amount numeric,
    actual_principal_collected_amount numeric,
    actual_other_collected_amount numeric,
    total_actual_amount_paid numeric,
    reporting_period_actual_end_balance_amount numeric,
    remaining_term_to_maturity_number integer,
    loan_maturity_date date,
    interest_paid_through_date date,
    payment_extended_number integer,
    -- NULL means the loan is still active. 0 is a real ABS-EE code and does
    -- not mean 'no code' -- see ccf/absee.py.
    zero_balance_effective_date date,
    zero_balance_code text,
    -- NULL means not measured this period; 0 means CURRENT. Conflating them
    -- biases every delinquency ratio downward.
    current_delinquency_status integer,
    primary_loan_servicer_name text,
    most_recent_servicing_transfer_received_date date,
    asset_subject_demand_indicator boolean,
    other_assessed_uncollected_servicer_fee_amount numeric,
    chargedoff_principal_amount numeric,
    recovered_amount numeric,
    repossessed_indicator boolean,
    repossessed_proceeds_amount numeric,
    PRIMARY KEY (deal_id, period, asset_number)
);

CREATE INDEX IF NOT EXISTS abs_loan_period_deal_period_idx
    ON "{S}".abs_loan_period (deal_id, period);
CREATE INDEX IF NOT EXISTS abs_loan_period_delinquency_idx
    ON "{S}".abs_loan_period (deal_id, period, current_delinquency_status)
    WHERE current_delinquency_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS abs_loan_period_state_idx
    ON "{S}".abs_loan_period (deal_id, period, obligor_geographic_location);
"""


def load_period(conn, deal_id: str, period: str, path) -> int:
    """Replace one (deal, period) slice. Returns rows written."""
    with conn.cursor() as cur:
        # The delete is the idempotency contract. It must be inside the same
        # transaction as the insert, or an interrupted run leaves the period
        # empty rather than unchanged.
        cur.execute(f'DELETE FROM "{S}".abs_loan_period '
                    "WHERE deal_id = %s AND period = %s", (deal_id, period))

        collist = ", ".join(f'"{c}"' for c in COLUMNS)
        written = 0
        with cur.copy(f'COPY "{S}".abs_loan_period ({collist}) FROM STDIN') as cp:
            for raw in parse_assets(path):
                rec = coerce(raw)
                cp.write_row((deal_id, period,
                              *(rec[snake(f)] for f in ABSEE_FIELDS)))
                written += 1
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Load ABS-EE loans into Postgres")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--deal", help="load one deal only")
    ap.add_argument("--period", help="load one period only, e.g. 2026-06")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    today = date.today().isoformat()
    source = "SEC EDGAR Form ABS-EE EX-102"

    with pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            for deal in reg["deals"]:
                cur.execute(f"""
                    INSERT INTO "{S}".abs_deal (deal_id, legal_name, cik,
                        depositor_cik, credit_tier, vintage, servicer,
                        provenance, source, retrieved_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'public',%s,%s)
                    ON CONFLICT (deal_id) DO UPDATE SET
                        legal_name = EXCLUDED.legal_name,
                        retrieved_at = EXCLUDED.retrieved_at""",
                    (deal["deal_id"], deal["legal_name"], deal["cik"],
                     deal["depositor_cik"], deal["credit_tier"],
                     deal["vintage"], deal["servicer"], source, today))
        conn.commit()

        total = 0
        for deal in reg["deals"]:
            if args.deal and deal["deal_id"] != args.deal:
                continue
            for period in reg["window"]:
                if args.period and period != args.period:
                    continue
                path = REPO_ROOT / "sources" / "absee" / deal["slug"] / f"{period}.xml"
                if not path.exists():
                    raise RuntimeError(
                        f"missing {path}. Run generators/fetch_abs_deals.py. "
                        f"Do not skip the period -- a short window silently "
                        f"breaks the vintage benchmark.")
                if args.dry_run:
                    print(f"  would load {deal['deal_id']} {period}  {path.name}")
                    continue
                n = load_period(conn, deal["deal_id"], period, path)
                conn.commit()           # per period, so a crash costs one period
                total += n
                print(f"  {deal['deal_id']:14s} {period}  {n:>7,} rows")

    print(f"\n  {total:,} loan-period rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Load one period and check the count against the file**

```bash
uv run loaders/load_abs_loans_wave14.py --deal SDART-2022-6 --period 2026-06
```

Expected: `35,814 rows`. Cross-check against the raw file:

```bash
grep -c '<assets>' sources/absee/sdart-2022-6/2026-06.xml
```

The two numbers must be equal. A mismatch means the parser is dropping
records.

- [ ] **Step 3: Prove idempotency, including the shrinking-pool case**

This is the test that would have caught §14.10. Load a **large** period, then
reload a **smaller** one over the same key, and confirm no ghosts survive:

```bash
uv run python - <<'PY'
from ccf.config import PG_SCHEMA_V2 as S, pg_connect
with pg_connect() as c, c.cursor() as cur:
    cur.execute(f'SELECT period, COUNT(*) FROM "{S}".abs_loan_period '
                "WHERE deal_id='SDART-2022-6' GROUP BY period ORDER BY period")
    for r in cur.fetchall(): print(r)
PY
```

Then re-run the same period twice and confirm the count is identical, not
doubled:

```bash
uv run loaders/load_abs_loans_wave14.py --deal SDART-2022-6 --period 2026-06
uv run loaders/load_abs_loans_wave14.py --deal SDART-2022-6 --period 2026-06
```

Expected: `35,814 rows` both times, and the table total unchanged.

- [ ] **Step 4: Load everything**

Run: `uv run loaders/load_abs_loans_wave14.py`
Expected: 36 lines, total near 1,320,000. Record the **actual** total — the
design doc's figure is an extrapolation and must be corrected from this.

- [ ] **Step 5: Check the footprint**

```bash
uv run python - <<'PY'
from ccf.config import PG_SCHEMA_V2 as S, pg_connect
with pg_connect() as c, c.cursor() as cur:
    cur.execute(f"""SELECT pg_size_pretty(pg_total_relation_size('"{S}".abs_loan_period')),
                           pg_size_pretty(pg_database_size(current_database()))""")
    print("abs_loan_period / database:", cur.fetchone())
PY
```

- [ ] **Step 6: Commit**

```bash
git add loaders/load_abs_loans_wave14.py
git commit -m "Loan-period loader: delete by period, COPY, resumable"
```

---

## Task 6: Prospectus extraction — tranches and trigger definitions with offsets

**Files:**
- Create: `generators/extract_prospectus.py`

**Interfaces:**
- Produces `sources/absee/prospectus_extract.json`:
  ```
  {"deals": [{"deal_id": str, "text_sha256": str, "text_length": int,
              "tranches": [{"tranche_id","class_name","cusip","original_balance",
                            "interest_rate","subordinate_to"}],
              "triggers": [{"trigger_id","name","threshold_value","threshold_unit",
                            "definition_text","start_offset","end_offset"}]}]}
  ```

**Offsets are the deliverable, not the text.** §D's validation gates require
every trigger threshold to carry a prospectus passage anchor — "a threshold
asserted without a passage anchor is a number nobody can defend to a
committee". An offset that does not actually bracket the definition is worse
than no offset, because it looks defensible.

- [ ] **Step 1: Implement the extractor**

```python
#!/usr/bin/env python3
"""Extract tranche structure and trigger definitions from the 424B5 prospectuses.

    uv run generators/extract_prospectus.py

## Offsets must be taken against the SAME text that MongoDB stores

Wave 13a's narrative loader hit this: offsets computed against one
normalization and stored beside text under another point at the wrong
characters, and nothing downstream can tell. So this module writes the
normalized text's sha256 alongside the offsets, and the Mongo loader refuses
to store a document whose hash disagrees.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import re
import sys
from datetime import date
from decimal import Decimal

from ccf.config import REPO_ROOT

REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
OUT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"

_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"[\s\xa0]+")

#: Trigger definitions take TWO forms across these three prospectuses:
#:   Santander: `" Delinquency Trigger " means, for any payment date ..., 24.00%.`
#:   Toyota:    `The " Delinquency Trigger Percentage " will equal 4.65%.`
#: A pattern keyed on `means` finds nothing in the Toyota document.
_DEFINITION = re.compile(
    r"[\u201c\"]\s*(?P<name>[A-Z][A-Za-z ]{3,60}?)\s*[\u201d\"]\s*"
    r"(?:means|will equal)\b"
    r"(?P<body>[^\u201c\"]{0,600}?)\.\s",
    re.S)

#: The triggers this product needs, by the name the prospectus defines.
#: Toyota names the same concept `Delinquency Trigger Percentage`.
WANTED = {
    "delinquency trigger": ("delinquency", "percent_of_pool"),
    "delinquency trigger percentage": ("delinquency", "percent_of_pool"),
    "targeted overcollateralization": ("overcollateralization", "amount_or_percent"),
    "overcollateralization target amount": ("overcollateralization", "amount_or_percent"),
    "cumulative net loss": ("cumulative_net_loss", "percent_of_initial_pool"),
    "specified reserve account balance": ("reserve", "amount_or_percent"),
}

#: Verified by the controller directly against each prospectus, 2026-08-23.
#: The extractor asserts against these rather than trusting a pattern to have
#: matched the right sentence.
#:
#: THE TRAP THIS GUARD EXISTS FOR: `24.00%` appears in the TOYOTA prospectus
#: too -- as the upper bound of the receivable-eligibility APR range
#: ("APR 0.00% to 24.00%"). A pattern that hunts for a percentage near the
#: words "Delinquency Trigger" in that document can land on an underwriting
#: criterion and bind it as a performance trigger. The data would be real and
#: the account of it wrong, and every proximity figure downstream would be
#: measured against a number that means nothing of the sort.
EXPECTED_DELINQUENCY_TRIGGER = {
    "SDART-2022-6": Decimal("24.00"),
    "SDART-2024-1": Decimal("24.00"),
    "TAOT-2022-B": Decimal("4.65"),
}

_CLASS = re.compile(r"\bClass\s+(A-[0-9][ab]?|[B-E])\b")


def normalize(raw_html: str) -> str:
    """The one canonical text. Offsets mean nothing without it."""
    return _WS.sub(" ", _html.unescape(_TAGS.sub(" ", raw_html))).strip()


def find_triggers(text: str, deal_id: str) -> list[dict]:
    found: list[dict] = []
    for m in _DEFINITION.finditer(text):
        name = m.group("name").strip()
        key = name.lower()
        if key not in WANTED:
            continue
        kind, unit = WANTED[key]
        body = m.group("body")
        pct = re.search(r"([\d]+\.?\d*)\s*%", body)
        found.append({
            "trigger_id": f"{deal_id}-{kind}",
            "name": name,
            "kind": kind,
            "threshold_value": str(Decimal(pct.group(1))) if pct else None,
            "threshold_unit": unit,
            "definition_text": text[m.start():m.end()],
            "start_offset": m.start(),
            "end_offset": m.end(),
            "provenance": "public",
        })
    # Deduplicate on trigger_id, keeping the first (the defined-terms article
    # is where the number lives; later mentions are cross-references).
    seen, out = set(), []
    for t in found:
        if t["trigger_id"] in seen:
            continue
        seen.add(t["trigger_id"])
        out.append(t)
    return out


def find_tranches(text: str, deal_id: str) -> list[dict]:
    """Distinct note classes, in seniority order.

    Counted as DISTINCT CLASSES, not as mentions -- the §F floor is four
    tranches, and 'Class B' appearing 97 times is still one tranche.
    """
    order = ["A-1", "A-2", "A-2a", "A-2b", "A-3", "A-4", "B", "C", "D", "E"]
    present = {m.group(1) for m in _CLASS.finditer(text)}
    ranked = [c for c in order if c in present]
    tranches = []
    for i, cls in enumerate(ranked):
        tranches.append({
            "tranche_id": f"{deal_id}-{cls}",
            "class_name": cls,
            # Subordination runs down the stack: each class is subordinate to
            # the one above it. The prospectus states this in the priority of
            # payments; the ordering above encodes it.
            "subordinate_to": f"{deal_id}-{ranked[i - 1]}" if i else None,
            "seniority_rank": i,
            "provenance": "public",
        })
    return tranches


def main() -> int:
    reg = json.loads(REGISTRY.read_text())
    out = {"generated_at": date.today().isoformat(), "deals": []}

    for deal in reg["deals"]:
        path = REPO_ROOT / "sources" / "absee" / deal["slug"] / "prospectus.htm"
        text = normalize(path.read_text(errors="replace"))
        triggers = find_triggers(text, deal["deal_id"])
        tranches = find_tranches(text, deal["deal_id"])

        if len(tranches) < 4:
            raise RuntimeError(
                f"{deal['deal_id']}: found {len(tranches)} tranches, floor is 4. "
                f"Fix the extractor -- do not lower the floor.")
        if len(triggers) < 3:
            raise RuntimeError(
                f"{deal['deal_id']}: found {len(triggers)} trigger definitions "
                f"{[t['name'] for t in triggers]}, floor is 3.")

        # Assert the delinquency threshold is the one this deal actually
        # states. See EXPECTED_DELINQUENCY_TRIGGER for why a pattern match is
        # not sufficient evidence on its own.
        expected = EXPECTED_DELINQUENCY_TRIGGER[deal["deal_id"]]
        got = next((Decimal(t["threshold_value"]) for t in triggers
                    if t["kind"] == "delinquency"
                    and t["threshold_value"] is not None), None)
        if got != expected:
            raise RuntimeError(
                f"{deal['deal_id']}: delinquency trigger extracted as {got}, "
                f"expected {expected}. Do NOT relax the pattern to make this "
                f"pass -- read the prospectus sentence the extractor matched. "
                f"In the Toyota document 24.00% is an APR eligibility bound, "
                f"not a trigger.")

        # Every offset must actually bracket its own definition text.
        for t in triggers:
            if text[t["start_offset"]:t["end_offset"]] != t["definition_text"]:
                raise RuntimeError(
                    f"{deal['deal_id']} {t['name']}: offsets do not reproduce "
                    f"the definition. An anchor that points at the wrong "
                    f"characters is worse than none -- it looks defensible.")

        out["deals"].append({
            "deal_id": deal["deal_id"],
            "text_length": len(text),
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "tranches": tranches,
            "triggers": triggers,
        })
        print(f"  {deal['deal_id']:14s} {len(tranches)} tranches, "
              f"{len(triggers)} triggers, delinquency={got}%: "
              f"{[(t['name'], t['threshold_value']) for t in triggers]}")

    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `uv run generators/extract_prospectus.py`
Expected: three lines, each with ≥ 4 tranches and ≥ 3 triggers, and the
delinquency threshold reading **24.00 for both Santander deals and 4.65 for
Toyota** — the assertion enforces exactly that.

**If a deal yields fewer than 3 triggers**, widen `WANTED` with the names that
deal actually uses — read the prospectus, do not relax the regex until
something matches. Toyota is prime and defines its triggers differently, which
is a real structural difference and belongs in the extract, not hidden.

**If the delinquency assertion fires**, the pattern matched the wrong
sentence. Print the matched text and read it before changing anything. The
Toyota prospectus contains `24.00%` as an APR eligibility bound; a pattern
relaxed until "something matches" will find it and bind an underwriting
criterion as a performance trigger.

- [ ] **Step 3: Commit**

```bash
git add generators/extract_prospectus.py sources/absee/prospectus_extract.json
git commit -m "Extract tranche structure and trigger definitions with verified offsets"
```

---

## Task 7: Prospectus and servicer text into MongoDB

**Files:**
- Create: `loaders/load_abs_prospectus_wave14.py`

**Interfaces:**
- Consumes: `prospectus_extract.json`, `generators.segment_passages.segment`.
- Produces: `document` and `passage` documents with
  `document_id` values `abs-prospectus-<deal_id>` and
  `abs-servicer-<deal_id>-<period>`; every trigger has a resolvable passage.

- [ ] **Step 1: Implement**

```python
#!/usr/bin/env python3
"""Prospectus and servicer-report text into MongoDB, with passage spans.

    uv run loaders/load_abs_prospectus_wave14.py --dry-run
    uv run loaders/load_abs_prospectus_wave14.py

Reuses `generators.segment_passages.segment` rather than reimplementing
segmentation -- Wave 13a's rule, so passage semantics stay identical across
every corpus this project stores.

## Stale passages must be removed, not upserted over

`known-issues.md` §14.10 again: an upsert-only reload of a document whose
text shrank leaves passages anchored to offsets the text no longer has. The
loader deletes a document's passages before writing the new set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date

from pymongo import ASCENDING, UpdateOne

from ccf.config import REPO_ROOT, mongo_db
from ccf.servicer_report import parse_servicer_report
from generators.extract_prospectus import normalize
from generators.segment_passages import segment

REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
EXTRACT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"
CLASSIFICATION = "public"
BATCH = 500


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    ext = {d["deal_id"]: d for d in json.loads(EXTRACT.read_text())["deals"]}
    today = date.today().isoformat()

    documents, passages, trigger_anchors = [], [], []

    for deal in reg["deals"]:
        deal_id = deal["deal_id"]
        base = REPO_ROOT / "sources" / "absee" / deal["slug"]

        text = normalize((base / "prospectus.htm").read_text(errors="replace"))
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest != ext[deal_id]["text_sha256"]:
            raise RuntimeError(
                f"{deal_id}: prospectus text hash disagrees with the extract. "
                f"The offsets in prospectus_extract.json point at different "
                f"characters than the text about to be stored. Re-run "
                f"generators/extract_prospectus.py.")

        doc_id = f"abs-prospectus-{deal_id}"
        ps = segment(text, doc_id)
        documents.append({
            "document_id": doc_id, "deal_id": deal_id, "form": "424B5",
            "cik": deal["cik"], "sec_name": deal["legal_name"],
            "text": text, "text_length": len(text), "text_sha256": digest,
            "passage_count": len(ps), "classification": CLASSIFICATION,
            "residency": "US", "provenance": "public",
            "source": "SEC EDGAR Form 424B5", "retrieved_at": today,
        })
        passages.extend(ps)

        # Bind each trigger to the passage whose span contains its definition.
        for trig in ext[deal_id]["triggers"]:
            hit = next((p for p in ps
                        if p["start_offset"] <= trig["start_offset"]
                        and p["end_offset"] >= trig["end_offset"]), None)
            if hit is None:
                # The definition straddles a passage boundary. Take the
                # passage containing the START and record that it is partial,
                # rather than silently anchoring to nothing.
                hit = next((p for p in ps
                            if p["start_offset"] <= trig["start_offset"]
                            < p["end_offset"]), None)
            if hit is None:
                raise RuntimeError(
                    f"{deal_id} {trig['name']}: no passage contains offsets "
                    f"{trig['start_offset']}..{trig['end_offset']}. §D requires "
                    f"every threshold to resolve to prospectus text.")
            trigger_anchors.append({
                "_id": f"{trig['trigger_id']}-anchor",
                "trigger_id": trig["trigger_id"], "deal_id": deal_id,
                "document_id": doc_id, "passage_id": hit["passage_id"],
                "start_offset": trig["start_offset"],
                "end_offset": trig["end_offset"],
                "quoted_text": trig["definition_text"],
                "complete_span": (hit["start_offset"] <= trig["start_offset"]
                                  and hit["end_offset"] >= trig["end_offset"]),
                "provenance": "public",
            })

        for month in reg["window"]:
            raw = (base / f"servicer-{month}.htm").read_text(errors="replace")
            stext = normalize(raw)
            sdoc_id = f"abs-servicer-{deal_id}-{month}"
            sps = segment(stext, sdoc_id)
            measures = parse_servicer_report(raw)
            documents.append({
                "document_id": sdoc_id, "deal_id": deal_id, "period": month,
                "form": "10-D EX-99.1", "cik": deal["cik"],
                "sec_name": deal["legal_name"],
                "text": stext, "text_length": len(stext),
                "text_sha256": hashlib.sha256(stext.encode()).hexdigest(),
                "passage_count": len(sps),
                # Stored as evidence for the gate's cross-check. Never read as
                # the answer to "did the trigger occur".
                "published_measures": {k: str(v) for k, v in measures.items()
                                       if k != "delinquency_buckets"},
                "classification": CLASSIFICATION, "residency": "US",
                "provenance": "public",
                "source": "SEC EDGAR Form 10-D EX-99.1", "retrieved_at": today,
            })
            passages.extend(sps)

    print(f"  {len(documents)} documents, {len(passages):,} passages, "
          f"{len(trigger_anchors)} trigger anchors")
    partial = [a for a in trigger_anchors if not a["complete_span"]]
    if partial:
        print(f"  {len(partial)} anchors span a passage boundary (recorded, not hidden)")

    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    db = mongo_db()
    doc_ids = [d["document_id"] for d in documents]
    # Remove stale passages before writing, per the module docstring.
    db["passage"].delete_many({"document_id": {"$in": doc_ids}})

    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in documents], ordered=False)
    for i in range(0, len(passages), BATCH):
        db["passage"].bulk_write([
            UpdateOne({"_id": p["passage_id"]},
                      {"$set": {**p, "embedding": None,
                                "embedding_model": None,
                                "provenance": "public"}}, upsert=True)
            for p in passages[i:i + BATCH]], ordered=False)
    db["trigger_anchor"].bulk_write([
        UpdateOne({"_id": a["_id"]}, {"$set": a}, upsert=True)
        for a in trigger_anchors], ordered=False)
    db["passage"].create_index([("document_id", ASCENDING),
                                ("start_offset", ASCENDING)])
    db["trigger_anchor"].create_index([("deal_id", ASCENDING)])
    print("  written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry run, then load**

```bash
uv run loaders/load_abs_prospectus_wave14.py --dry-run
uv run loaders/load_abs_prospectus_wave14.py
```

Expected: 39 documents (3 prospectuses + 36 servicer reports), ≥ 9 trigger
anchors.

- [ ] **Step 3: Verify an anchor actually quotes the threshold**

```bash
uv run python - <<'PY'
from ccf.config import mongo_db
db = mongo_db()
for a in db["trigger_anchor"].find({"trigger_id": {"$regex": "delinquency"}}):
    print(a["trigger_id"], "|", a["quoted_text"][:150])
PY
```

Expected: each quoted span contains the words "Delinquency Trigger" and its
percentage. **If a quote does not contain the number, the anchor is
decorative** — fix the extractor.

- [ ] **Step 4: Embed the passages**

Run: `uv run loaders/embed_passages.py` (existing; picks up null embeddings)

- [ ] **Step 5: Commit**

```bash
git add loaders/load_abs_prospectus_wave14.py
git commit -m "Prospectus and servicer text into MongoDB with trigger anchors"
```

---

## Task 8: Tranche state, servicer measures and repurchases into Postgres

**Files:**
- Create: `loaders/load_abs_structure_wave14.py`

**Interfaces:**
- Produces: `abs_tranche`, `abs_tranche_state`, `abs_servicer_report`,
  `abs_repurchase`.

- [ ] **Step 1: Implement**

```python
#!/usr/bin/env python3
"""Tranche structure, monthly servicer measures and repurchase activity.

    uv run loaders/load_abs_structure_wave14.py --dry-run
    uv run loaders/load_abs_structure_wave14.py

The servicer's published figures land here as EVIDENCE. `abs_servicer_report`
is what `validators/abs_surveillance.py` compares its own loan-level
recomputation against; it is never the source of a trigger answer.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.servicer_report import parse_servicer_report

S = assert_v2_schema(PG_SCHEMA_V2)
REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
EXTRACT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_tranche (
    tranche_id     text PRIMARY KEY,
    deal_id        text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    class_name     text NOT NULL,
    seniority_rank integer NOT NULL,
    subordinate_to text REFERENCES "{S}".abs_tranche(tranche_id),
    cusip          text,
    provenance     text NOT NULL,
    source         text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_servicer_report (
    deal_id  text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    period   char(7) NOT NULL,
    pool_balance   numeric NOT NULL,
    note_balance   numeric NOT NULL,
    oc_amount      numeric,
    oc_percent     numeric,
    oc_target      numeric,
    -- The servicer's own published figures. Kept so the gate can compare its
    -- recomputation against them, NOT so anything can read the answer here.
    published_delinquency_percent numeric,
    published_delinquency_trigger numeric,
    published_trigger_occurred    boolean,
    -- Toyota publishes neither of these. NULL means NOT PUBLISHED; it is not
    -- zero, and it must not be back-filled with our own arithmetic and then
    -- sit beside genuinely-filed figures.
    sixty_day_delinquent_balance  numeric,
    cumulative_net_loss_percent   numeric,
    receivable_count integer,
    -- Buckets are JSONB keyed by the ISSUER'S OWN boundaries, not fixed
    -- columns. Santander reports 31-60 / 61-90 / 91-120 / 121+; Toyota
    -- reports 30-59 / 60-89 / 90-119 / 120+. Columns named for one issuer's
    -- boundaries would silently relabel the other's -- a 30-59 figure sitting
    -- in a column called bucket_31_60 is a different population wearing the
    -- wrong name, and nothing downstream could tell.
    delinquency_buckets jsonb NOT NULL,
    source_format text NOT NULL,          -- numbered | labelled
    provenance text NOT NULL,
    source     text NOT NULL,
    PRIMARY KEY (deal_id, period)
);

CREATE TABLE IF NOT EXISTS "{S}".abs_repurchase (
    repurchase_id text PRIMARY KEY,
    depositor_cik text NOT NULL,
    deal_id       text REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    form          text NOT NULL,
    accession     text NOT NULL,
    filed_date    date NOT NULL,
    asset_count   integer,
    note          text,
    provenance    text NOT NULL,
    source        text NOT NULL
);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    ext = {d["deal_id"]: d for d in json.loads(EXTRACT.read_text())["deals"]}

    tranche_rows, report_rows, repo_rows = [], [], []
    for deal in reg["deals"]:
        deal_id, base = deal["deal_id"], REPO_ROOT / "sources" / "absee" / deal["slug"]
        for t in ext[deal_id]["tranches"]:
            tranche_rows.append((t["tranche_id"], deal_id, t["class_name"],
                                 t["seniority_rank"], t["subordinate_to"], None,
                                 "public", "SEC EDGAR Form 424B5"))
        for month in reg["window"]:
            m = parse_servicer_report(
                (base / f"servicer-{month}.htm").read_text(errors="replace"))
            report_rows.append((
                deal_id, month, m["pool_balance"], m["note_balance"],
                m["oc_amount"], m["oc_percent"], m["oc_target"],
                m["delinquency_percent"], m["delinquency_trigger"],
                m["trigger_occurred"], m["sixty_day_delinquent_balance"],
                m["cumulative_net_loss_percent"], m["receivable_count"],
                # Decimal is not JSON-serialisable; stringify rather than
                # float() -- these are balances.
                json.dumps({k: str(v) for k, v
                            in m["delinquency_buckets"].items()}),
                m["source_format"], "public",
                "SEC EDGAR Form 10-D EX-99.1"))

    for r in reg["repurchase"]:
        repo_rows.append((f"{r['depositor_cik']}-{r['accession']}",
                          r["depositor_cik"], None, r["form"], r["accession"],
                          r["filed_date"], None,
                          "depositor-level filing; covers the shelf, not one trust",
                          "public", "SEC EDGAR Form ABS-15G"))

    print(f"  {len(tranche_rows)} tranches, {len(report_rows)} servicer reports, "
          f"{len(repo_rows)} ABS-15G filings")
    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        # Insert seniors before juniors so the self-reference resolves.
        for row in sorted(tranche_rows, key=lambda r: r[3]):
            cur.execute(f"""
                INSERT INTO "{S}".abs_tranche VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (tranche_id) DO UPDATE SET
                  seniority_rank = EXCLUDED.seniority_rank,
                  subordinate_to = EXCLUDED.subordinate_to""", row)
        cur.executemany(f"""
            INSERT INTO "{S}".abs_servicer_report VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (deal_id, period) DO UPDATE SET
              pool_balance = EXCLUDED.pool_balance,
              published_delinquency_percent = EXCLUDED.published_delinquency_percent,
              published_trigger_occurred = EXCLUDED.published_trigger_occurred,
              delinquency_buckets = EXCLUDED.delinquency_buckets,
              source_format = EXCLUDED.source_format
            """, report_rows)
        cur.executemany(f"""
            INSERT INTO "{S}".abs_repurchase VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (repurchase_id) DO NOTHING""", repo_rows)
        conn.commit()
    print("  written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Load and sanity-check the delinquency series**

```bash
uv run loaders/load_abs_structure_wave14.py
uv run python - <<'PY'
from ccf.config import PG_SCHEMA_V2 as S, pg_connect
with pg_connect() as c, c.cursor() as cur:
    cur.execute(f"""SELECT deal_id, period, published_delinquency_percent,
                           published_delinquency_trigger, oc_percent
                    FROM "{S}".abs_servicer_report ORDER BY deal_id, period""")
    for r in cur.fetchall(): print("  %-14s %s  delinq %6s  trig %6s  oc %6s" % r)
PY
```

Expected: 36 rows, the SDART delinquency series rising across the window.

- [ ] **Step 3: Commit**

```bash
git add loaders/load_abs_structure_wave14.py
git commit -m "Tranche structure, servicer measures and repurchase filings"
```

---

## Task 9: Fluree — structure and dated trigger assertions

**Files:**
- Create: `loaders/load_abs_fluree_wave14.py`

**Interfaces:**
- Consumes: `P_IS_SUBORDINATE_TO` from Task 1.
- Produces: deal, tranche and trigger nodes; `collateralizes`,
  `isSubordinateTo`, `specifiesTrigger` edges; threshold assertions carrying
  `ex:validFrom` and `ex:assertedAt`.

**Single-writer discipline.** Fluree nodes carry identity, type and structure.
Every threshold *value* also lives here — because the threshold is a
*temporal* fact and `T` is Fluree's slice — but no performance measure does.
Pool balances, delinquency percentages and cohort aggregates resolve from
Postgres only.

**No OWL inference.** Type every node explicitly for each role it must be
queried under. A query for `Tranche` returns only nodes explicitly typed
`Tranche`.

- [ ] **Step 1: Implement**

```python
#!/usr/bin/env python3
"""Deal structure and dated trigger assertions into Fluree.

    uv run loaders/load_abs_fluree_wave14.py --dry-run
    uv run loaders/load_abs_fluree_wave14.py

## Why the thresholds live here and the measures do not

A threshold is a temporal fact: it holds from an effective date, and it can be
superseded. That is Fluree's slice (`T`). A delinquency percentage is a
measure computed from the pool, which is Postgres's slice (`E`). Putting the
measure here too would duplicate an attribute across stores -- the one thing
CLAUDE.md forbids outright -- and would let the two disagree silently.

## Explicit typing, because Fluree does not reason

Every tranche is typed BOTH `fibo-sec-dbt-pbs:Tranche` and, where it is the
senior-most class, nothing else -- there is no inference to add supertypes.
A node that must answer a `PoolBackedSecurity` query carries that type
explicitly.
"""
from __future__ import annotations

import argparse
import json
import sys
from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT

REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
EXTRACT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

C_TRANCHE = f"{FIBO}SEC/Debt/PoolBackedSecurities/Tranche"
C_ABS = f"{FIBO}SEC/Debt/PoolBackedSecurities/AssetBackedSecurity"
C_POOL_BACKED = f"{FIBO}SEC/Debt/PoolBackedSecurities/PoolBackedSecurity"
C_TRIGGER_EVENT = f"{FIBO}SEC/Debt/CollateralizedDebtObligations/TriggerEvent"
C_LOAN = f"{FIBO}LOAN/LoansGeneral/Loans/Loan"
C_SERVICER = f"{FIBO}LOAN/LoansGeneral/Loans/Servicer"

P_SPECIFIES_TRIGGER = f"{FIBO}SEC/Debt/CollateralizedDebtObligations/specifiesTrigger"
P_IS_SUBORDINATE_TO = f"{FIBO}FND/Agreements/Contracts/isSubordinateTo"
P_IS_COLLATERALIZATION_OF = f"{FIBO}FBC/DebtAndEquities/Debt/isCollateralizationOf"

# No FIBO term exists for these -- recorded on the do-not-bind list in
# docs/ccf_dataprep_v2.md, so they are `ex:` deliberately, not by omission.
P_SERVICED_BY = f"{EX}servicedBy"
P_THRESHOLD_VALUE = f"{EX}thresholdValue"
P_THRESHOLD_UNIT = f"{EX}thresholdUnit"
P_VALID_FROM = f"{EX}validFrom"
P_ASSERTED_AT = f"{EX}assertedAt"
P_PROVENANCE = f"{EX}provenance"
P_ANCHOR = f"{EX}passageAnchor"


def esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def uri(local: str) -> str:
    return f"{EX}{local}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    ext = {d["deal_id"]: d for d in json.loads(EXTRACT.read_text())["deals"]}

    triples: list[str] = []
    for deal in reg["deals"]:
        deal_id = deal["deal_id"]
        d_uri = uri(f"abs-deal-{deal_id}")
        # Explicitly typed for every role it is queried under -- there is no
        # inference to derive PoolBackedSecurity from AssetBackedSecurity.
        for cls in (C_ABS, C_POOL_BACKED):
            triples.append(triple(d_uri, RDF_TYPE, cls))
        triples.append(triple(d_uri, RDFS_LABEL, deal["legal_name"], literal=True))
        triples.append(triple(d_uri, P_PROVENANCE, "public", literal=True))

        s_uri = uri("abs-servicer-" + deal["servicer"].lower()
                    .replace(" ", "-").replace(".", "").replace(",", ""))
        triples.append(triple(s_uri, RDF_TYPE, C_SERVICER))
        triples.append(triple(s_uri, RDFS_LABEL, deal["servicer"], literal=True))
        triples.append(triple(d_uri, P_SERVICED_BY, s_uri))

        for t in ext[deal_id]["tranches"]:
            t_uri = uri(f"abs-tranche-{t['tranche_id']}")
            triples.append(triple(t_uri, RDF_TYPE, C_TRANCHE))
            triples.append(triple(t_uri, RDFS_LABEL,
                                  f"{deal_id} Class {t['class_name']}", literal=True))
            # The pool collateralizes the tranche.
            triples.append(triple(t_uri, P_IS_COLLATERALIZATION_OF, d_uri))
            if t["subordinate_to"]:
                triples.append(triple(t_uri, P_IS_SUBORDINATE_TO,
                                      uri(f"abs-tranche-{t['subordinate_to']}")))

        for trig in ext[deal_id]["triggers"]:
            g_uri = uri(f"abs-trigger-{trig['trigger_id']}")
            triples.append(triple(g_uri, RDF_TYPE, C_TRIGGER_EVENT))
            triples.append(triple(g_uri, RDFS_LABEL, trig["name"], literal=True))
            triples.append(triple(d_uri, P_SPECIFIES_TRIGGER, g_uri))
            if trig["threshold_value"] is not None:
                triples.append(triple(g_uri, P_THRESHOLD_VALUE,
                                      trig["threshold_value"], literal=True))
            triples.append(triple(g_uri, P_THRESHOLD_UNIT,
                                  trig["threshold_unit"], literal=True))
            # Effective and assertion dates follow the block below -- they are
            # the 424B5 filing date, NOT today. The amendment in Task 10
            # supersedes this assertion.
            triples.append(triple(g_uri, P_PROVENANCE, "public", literal=True))
            triples.append(triple(g_uri, P_ANCHOR,
                                  f"{trig['trigger_id']}-anchor", literal=True))
```

**The two dates are the whole bitemporal mechanism — do not use `now`.**
An original threshold was *in force* from the day the deal priced and was
*knowable* from the day the prospectus was filed. For these deals both are the
424B5 filing date, which `deals.json` carries as `prospectus_filed`.

Stamping `assertedAt` with today's date instead breaks Task 13 silently:
today is later than the amendment's own assertion date, so
`threshold_known_as_of` would find no assertion at or before the gap day and
return `None`. The divergence check would then pass because `13.50 != None` —
green, while measuring nothing. Replace the two lines above with:

```python
            # In force from pricing, knowable from filing. Both are the 424B5
            # filing date for these deals. NEVER today's date -- see above.
            filed = deal["prospectus_filed"]
            triples.append(triple(g_uri, P_VALID_FROM, filed, literal=True))
            triples.append(triple(g_uri, P_ASSERTED_AT, filed, literal=True))

    print(f"  {len(triples)} triples")
    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    BATCH = 500
    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA { " + " ".join(triples[i:i + BATCH]) + " }")

    # stable_scalar, not a bare query: a read immediately after INSERT DATA
    # can return 0 while the index catches up (known-issues.md §14.2). A bare
    # count here would produce a false FAIL as easily as a false PASS.
    n = fluree.stable_scalar(f"""
        SELECT (COUNT(?t) AS ?n) WHERE {{ ?t a <{C_TRANCHE}> }}""")
    print(f"  tranches in ledger: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry run, then load**

```bash
uv run loaders/load_abs_fluree_wave14.py --dry-run
uv run loaders/load_abs_fluree_wave14.py
```

Expected: tranche count 19 (6 + 7 + 6).

- [ ] **Step 3: Verify the subordination chain walks**

```bash
uv run python - <<'PY'
from ccf import fluree
FIBO="https://spec.edmcouncil.org/fibo/ontology/"
q = f"""SELECT ?t ?sub WHERE {{
  ?t <{FIBO}FND/Agreements/Contracts/isSubordinateTo> ?sub }}"""
for b in fluree.query(q)["results"]["bindings"]:
    print(b["t"]["value"].split("/")[-1], "->", b["sub"]["value"].split("/")[-1])
PY
```

Expected: 16 edges (each deal's classes below the senior-most). **If Task 1
found the term absent**, substitute `ex:isSubordinateTo` here and in the query.

- [ ] **Step 4: Commit**

```bash
git add loaders/load_abs_fluree_wave14.py
git commit -m "Deal structure and dated trigger assertions into Fluree"
```

---

## Task 10: The engineered trigger amendment

**Files:**
- Create: `generators/generate_trigger_amendment.py`
- Test: `validators/test_abs_amendment.py`

**Interfaces:**
- Produces: `sources/absee/trigger_amendment.json` and the Fluree assertion
  superseding SDART 2022-6's Delinquency Trigger.

This is the wave's only engineered condition. Everything about it must say so.

**What it must demonstrate.** Three questions, three answers, one ledger:

| Question | Expected |
|---|---|
| threshold now | the amended value |
| threshold `as_of` a date before the effective date | 24.00 |
| threshold `known_as_of` a date after effective but before assertion | 24.00 |

- [ ] **Step 1: Write the failing mutation tests**

```python
# validators/test_abs_amendment.py
"""Mutation tests for the trigger-amendment gate.

Each test breaks the data in one specific way and asserts the gate NOTICES.
A gate that passes all of these while passing on correct data is measuring
something; a gate that passes them is decoration.
"""
from __future__ import annotations

from datetime import date

import pytest

from generators.generate_trigger_amendment import (
    AMENDMENT, threshold_as_of, threshold_known_as_of,
)


def _chain():
    """The assertion chain as the generator builds it."""
    return [
        {"value": "24.00", "effective_from": date(2022, 9, 14),
         "asserted_at": date(2022, 9, 14), "provenance": "public"},
        {"value": AMENDMENT["new_threshold"],
         "effective_from": AMENDMENT["effective_from"],
         "asserted_at": AMENDMENT["asserted_at"],
         "provenance": "synthetic — engineered"},
    ]


def test_effective_precedes_assertion():
    """No lag, no demonstration. This is the whole mechanism."""
    assert AMENDMENT["effective_from"] < AMENDMENT["asserted_at"]


def test_as_of_before_effective_returns_the_original():
    assert threshold_as_of(_chain(), date(2025, 8, 1)) == "24.00"


def test_as_of_after_effective_returns_the_amendment():
    assert threshold_as_of(_chain(), date(2026, 5, 1)) == AMENDMENT["new_threshold"]


def test_known_as_of_inside_the_gap_returns_the_original():
    """The one a mirroring pipeline loses.

    Between the effective date and the assertion date the amendment was in
    force but not yet known. Asking what we KNEW must return 24.00.
    """
    gap = AMENDMENT["effective_from"] + (AMENDMENT["asserted_at"]
                                         - AMENDMENT["effective_from"]) / 2
    assert threshold_known_as_of(_chain(), gap) == "24.00"


def test_known_as_of_after_assertion_returns_the_amendment():
    assert threshold_known_as_of(
        _chain(), AMENDMENT["asserted_at"]) == AMENDMENT["new_threshold"]


def test_as_of_and_known_as_of_actually_diverge():
    """If they agree everywhere, the bitemporal claim is unfalsifiable."""
    gap = AMENDMENT["effective_from"] + (AMENDMENT["asserted_at"]
                                         - AMENDMENT["effective_from"]) / 2
    assert threshold_as_of(_chain(), gap) != threshold_known_as_of(_chain(), gap)


def test_amendment_is_labelled_engineered():
    assert AMENDMENT["provenance"] == "synthetic — engineered"


def test_amendment_carries_no_passage_anchor():
    """No prospectus sentence says this. Claiming an anchor would be a lie
    that the trigger-anchoring gate would happily accept."""
    assert AMENDMENT.get("passage_anchor") is None


def test_mutation_removing_the_lag_breaks_divergence():
    """Collapse the lag and the mechanism must stop working."""
    chain = _chain()
    chain[1]["asserted_at"] = chain[1]["effective_from"]
    gap = chain[1]["effective_from"]
    assert threshold_as_of(chain, gap) == threshold_known_as_of(chain, gap)


def test_new_threshold_is_close_to_the_real_series():
    """A threshold far from the observed series changes proximity by a
    constant and demonstrates nothing. It must actually bite."""
    assert 10 < float(AMENDMENT["new_threshold"]) < 16
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest validators/test_abs_amendment.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python3
"""The one engineered condition: a trigger-definition amendment.

    uv run generators/generate_trigger_amendment.py
    uv run generators/generate_trigger_amendment.py --load

## Why this is invented, and why that is disclosed everywhere it appears

Auto ABS trigger definitions are fixed at issuance. Across 135 ABS-EE periods
and three prospectuses there is no amendment to find and there will not be
one. §F requires one so that as-of evaluation is not a decoration, so it is
built -- and labelled `synthetic — engineered` in Postgres, given a distinct
assertion provenance in Fluree, and deliberately given NO passage anchor,
because no filed sentence says it.

Presenting it as filed would be the misrepresentation CLAUDE.md's provenance
rule exists to prevent.

## Choosing the new threshold

It must land close to the REAL, unmodified delinquency series. A threshold far
above it changes every proximity by a constant and proves nothing; one below
it would trip the trigger in every period and remove the trajectory. So it is
chosen from the loaded series: just above the window's observed maximum, so
proximity narrows toward it without breaching.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal

from ccf import fluree
from ccf.config import EX, PG_SCHEMA_V2, REPO_ROOT, pg_connect

S = PG_SCHEMA_V2
OUT = REPO_ROOT / "sources" / "absee" / "trigger_amendment.json"

TARGET_DEAL = "SDART-2022-6"
TARGET_TRIGGER = f"{TARGET_DEAL}-delinquency"

#: Effective inside the window; asserted 71 days later. The lag is the point.
AMENDMENT = {
    "deal_id": TARGET_DEAL,
    "trigger_id": TARGET_TRIGGER,
    "effective_from": date(2025, 11, 1),
    "asserted_at": date(2026, 1, 11),
    "new_threshold": "13.50",
    "provenance": "synthetic — engineered",
    "passage_anchor": None,
    "rationale": (
        "Engineered so as-of and known-as-of evaluation diverge. Auto ABS "
        "triggers are fixed at issuance; no real amendment exists to load. "
        "The threshold sits just above the deal's observed delinquency "
        "maximum in the window, so proximity narrows without breaching."),
}


def threshold_as_of(chain: list[dict], when: date) -> str | None:
    """What the threshold WAS on `when`, by effective time."""
    live = [a for a in chain if a["effective_from"] <= when]
    return max(live, key=lambda a: a["effective_from"])["value"] if live else None


def threshold_known_as_of(chain: list[dict], when: date) -> str | None:
    """What we KNEW the threshold to be on `when`, by assertion time.

    The difference from `threshold_as_of` is the whole bitemporal claim: an
    amendment effective in November but booked in January was in force, and
    unknown, for 71 days.
    """
    known = [a for a in chain if a["asserted_at"] <= when]
    return max(known, key=lambda a: a["effective_from"])["value"] if known else None


def observed_maximum() -> Decimal:
    """The deal's highest delinquency percentage across the window."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT MAX(published_delinquency_percent)
                        FROM "{S}".abs_servicer_report WHERE deal_id = %s""",
                    (TARGET_DEAL,))
        return cur.fetchone()[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true", help="write to Fluree and Postgres")
    args = ap.parse_args()

    peak = observed_maximum()
    if peak is None:
        raise RuntimeError("no servicer reports loaded; run Task 8 first.")
    if not (peak < Decimal(AMENDMENT["new_threshold"]) < peak + Decimal("4")):
        raise RuntimeError(
            f"observed delinquency peak is {peak}%; the engineered threshold "
            f"{AMENDMENT['new_threshold']}% must sit just above it so proximity "
            f"narrows without breaching. Adjust AMENDMENT and say so in the "
            f"design doc -- do not widen this guard.")

    payload = {**AMENDMENT,
               "effective_from": AMENDMENT["effective_from"].isoformat(),
               "asserted_at": AMENDMENT["asserted_at"].isoformat(),
               "observed_peak_percent": str(peak),
               "lag_days": (AMENDMENT["asserted_at"] - AMENDMENT["effective_from"]).days}
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"  engineered amendment: {TARGET_TRIGGER}  24.00% -> "
          f"{AMENDMENT['new_threshold']}%  effective "
          f"{payload['effective_from']}, asserted {payload['asserted_at']} "
          f"({payload['lag_days']}d lag); observed peak {peak}%")

    if not args.load:
        print("\n  Not loaded. Re-run with --load.")
        return 0

    g_uri = f"{EX}abs-trigger-{TARGET_TRIGGER}-amendment"
    orig = f"{EX}abs-trigger-{TARGET_TRIGGER}"
    FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
    triples = [
        f'<{g_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
        f'<{FIBO}SEC/Debt/CollateralizedDebtObligations/TriggerEvent> .',
        # Estate convention is the FORWARD edge, old -> new. The binding
        # table says in bold: do NOT mint ex:supersedes.
        f'<{orig}> <{EX}supersededBy> <{g_uri}> .',
        f'<{g_uri}> <{EX}thresholdValue> "{AMENDMENT["new_threshold"]}" .',
        f'<{g_uri}> <{EX}thresholdUnit> "percent_of_pool" .',
        f'<{g_uri}> <{EX}validFrom> "{payload["effective_from"]}" .',
        f'<{g_uri}> <{EX}assertedAt> "{payload["asserted_at"]}" .',
        f'<{g_uri}> <{EX}provenance> "synthetic — engineered" .',
    ]
    fluree.update("INSERT DATA { " + " ".join(triples) + " }")
    n = fluree.stable_scalar(
        f'SELECT (COUNT(?s) AS ?n) WHERE {{ <{orig}> <{EX}supersededBy> ?s }}')
    print(f"  supersession edges in ledger: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest validators/test_abs_amendment.py -v`
Expected: 10 passed.

- [ ] **Step 5: Generate and load**

```bash
uv run generators/generate_trigger_amendment.py
uv run generators/generate_trigger_amendment.py --load
```

Expected: the guard reports the observed peak and confirms 13.50 sits just
above it. **If the guard raises**, the observed peak differs from the
2026-08 reading of 10.79% — adjust `new_threshold` to sit 1–3 points above
the actual peak and record the change in the design doc.

- [ ] **Step 6: Commit**

```bash
git add generators/generate_trigger_amendment.py validators/test_abs_amendment.py \
        sources/absee/trigger_amendment.json
git commit -m "Engineered trigger amendment: effective November, booked January"
```

---

## Task 11: Cohort and vintage aggregates

**Files:**
- Create: `loaders/load_abs_aggregates_wave14.py`

**Interfaces:**
- Produces: `abs_cohort_performance`, `abs_vintage_benchmark`. These are the
  pre-aggregated state the `deal`, `tranche` and `cohort` granularities read,
  and they are what makes those granularities cheap.

**Materialized tables, not views.** §E's posture is "tranche and cohort
aggregates materialized on the monthly cycle; loan level derived on demand" —
the split *is* the cost strategy. A view would recompute over 1.32M rows on
every read and the measured curve would show no benefit from materialization,
which is the finding the product exists to teach.

**Do not use `CREATE OR REPLACE VIEW`.** Wave 13b found an early loader whose
`CREATE OR REPLACE VIEW` would have silently rebuilt a view *without* a later
wave's source, and every query would still have worked.

- [ ] **Step 1: Implement**

```python
#!/usr/bin/env python3
"""Cohort performance and vintage benchmarks -- the materialized layer.

    uv run loaders/load_abs_aggregates_wave14.py

Cohorts are (deal, period, credit band, state region, vintage-of-origination)
-- the dimensions §D's cohort granularity filters on.

## Why tables and not views

§E puts everything above loan level in the materialized band. A view would
rescan 1.32M rows per read and `validators/abs_cost.py` would then measure no
difference between granularities, which is precisely the behaviour the
product is meant to expose.
"""
from __future__ import annotations

import argparse
import sys

from ccf.config import PG_SCHEMA_V2, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_cohort_performance (
    deal_id text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    period  char(7) NOT NULL,
    credit_band text NOT NULL,       -- <600 | 600-659 | 660-719 | 720+ | unscored
    loan_count integer NOT NULL,
    pool_balance numeric NOT NULL,
    delinquent_60_plus_balance numeric NOT NULL,
    delinquency_percent numeric NOT NULL,
    chargedoff_amount numeric NOT NULL,
    recovered_amount numeric NOT NULL,
    weighted_average_coupon numeric,
    provenance text NOT NULL,
    PRIMARY KEY (deal_id, period, credit_band)
);

CREATE TABLE IF NOT EXISTS "{S}".abs_vintage_benchmark (
    asset_class text NOT NULL,       -- auto-loan
    vintage integer NOT NULL,
    credit_tier text NOT NULL,       -- prime | subprime
    period char(7) NOT NULL,
    deal_count integer NOT NULL,
    pool_balance numeric NOT NULL,
    delinquency_percent numeric NOT NULL,
    cumulative_chargeoff_percent numeric NOT NULL,
    provenance text NOT NULL,
    PRIMARY KEY (asset_class, vintage, credit_tier, period)
);
"""

#: Delinquency is measured at >= 60 days, NOT >= 61.
#:
#: Measured 2026-08-23 against SDART 2022-6's 2026-07 file, 35,171 records:
#:
#:   pool balance      301,051,961.82  == servicer item 64, to the penny
#:   60+ balance        32,480,926.13  == servicer item 78, to the penny
#:   delinquency at >=60      10.7891% -> 10.79%, the published figure
#:   delinquency at >=61      10.1139%   0.68pp low, matches nothing filed
#:
#: The servicer's line is "Aggregate Principal Balance of 60 Day Delinquent
#: Receivables", and 60 means 60. An earlier draft of this plan used >= 61 and
#: paired it with a 2.0pp reconciliation tolerance, which would have absorbed
#: the 0.68pp bias silently on every deal-period forever -- a gate wide enough
#: to swallow its own systematic error.
#:
#: Weighting is by BALANCE, never by row count. ABS-EE keeps reporting
#: charged-off loans with a frozen delinquency status and a zero balance:
#: 35,171 records carry only 22,734 nonzero balances, so a count-based ratio
#: reads about 36% against a true 10.79%.
COHORTS = f"""
INSERT INTO "{S}".abs_cohort_performance
SELECT deal_id, period,
       CASE WHEN obligor_credit_score IS NULL THEN 'unscored'
            WHEN obligor_credit_score < 600 THEN '<600'
            WHEN obligor_credit_score < 660 THEN '600-659'
            WHEN obligor_credit_score < 720 THEN '660-719'
            ELSE '720+' END                                   AS credit_band,
       COUNT(*)                                               AS loan_count,
       SUM(reporting_period_actual_end_balance_amount)        AS pool_balance,
       SUM(CASE WHEN current_delinquency_status >= 60
                THEN reporting_period_actual_end_balance_amount
                ELSE 0 END)                                   AS delinquent_60_plus_balance,
       CASE WHEN SUM(reporting_period_actual_end_balance_amount) > 0
            THEN ROUND(100 * SUM(CASE WHEN current_delinquency_status >= 60
                                      THEN reporting_period_actual_end_balance_amount
                                      ELSE 0 END)
                       / SUM(reporting_period_actual_end_balance_amount), 4)
            ELSE 0 END                                        AS delinquency_percent,
       SUM(chargedoff_principal_amount)                       AS chargedoff_amount,
       SUM(recovered_amount)                                  AS recovered_amount,
       CASE WHEN SUM(reporting_period_actual_end_balance_amount) > 0
            THEN ROUND(SUM(reporting_period_interest_rate_percentage
                           * reporting_period_actual_end_balance_amount)
                       / SUM(reporting_period_actual_end_balance_amount), 6)
            END                                               AS weighted_average_coupon,
       'public'
FROM "{S}".abs_loan_period
GROUP BY deal_id, period, 3;
"""

BENCHMARKS = f"""
INSERT INTO "{S}".abs_vintage_benchmark
SELECT 'auto-loan', d.vintage, d.credit_tier, c.period,
       COUNT(DISTINCT c.deal_id),
       SUM(c.pool_balance),
       CASE WHEN SUM(c.pool_balance) > 0
            THEN ROUND(100 * SUM(c.delinquent_60_plus_balance) / SUM(c.pool_balance), 4)
            ELSE 0 END,
       CASE WHEN SUM(c.pool_balance) > 0
            THEN ROUND(100 * SUM(c.chargedoff_amount) / SUM(c.pool_balance), 4)
            ELSE 0 END,
       'public'
FROM "{S}".abs_cohort_performance c
JOIN "{S}".abs_deal d USING (deal_id)
GROUP BY d.vintage, d.credit_tier, c.period;
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        if args.dry_run:
            print("  DDL only; aggregates not rebuilt.")
            conn.commit()
            return 0
        # Full rebuild, not upsert: a cohort that disappears (a credit band
        # with no remaining loans) must disappear from the table too.
        cur.execute(f'TRUNCATE "{S}".abs_cohort_performance, "{S}".abs_vintage_benchmark')
        cur.execute(COHORTS)
        cohorts = cur.rowcount
        cur.execute(BENCHMARKS)
        benchmarks = cur.rowcount
        conn.commit()
        cur.execute(f"""SELECT deal_id, period, delinquency_percent
                        FROM "{S}".abs_cohort_performance
                        WHERE credit_band = '<600' ORDER BY deal_id, period LIMIT 6""")
        sample = cur.fetchall()

    print(f"  {cohorts} cohort rows, {benchmarks} vintage benchmark rows")
    for r in sample:
        print("    %-14s %s  <600 band delinquency %s%%" % r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Build and inspect**

Run: `uv run loaders/load_abs_aggregates_wave14.py`
Expected: ~180 cohort rows (3 deals × 12 periods × up to 5 bands) and 24
benchmark rows (2 vintages × tiers × 12 periods).

- [ ] **Step 3: Verify the aggregate reconciles to the servicer's pool balance**

```bash
uv run python - <<'PY'
from ccf.config import PG_SCHEMA_V2 as S, pg_connect
with pg_connect() as c, c.cursor() as cur:
    cur.execute(f"""
      SELECT c.deal_id, c.period,
             SUM(c.pool_balance) AS ours, r.pool_balance AS theirs,
             ROUND(100*(SUM(c.pool_balance)-r.pool_balance)/r.pool_balance,3) AS pct
      FROM "{S}".abs_cohort_performance c
      JOIN "{S}".abs_servicer_report r USING (deal_id, period)
      GROUP BY c.deal_id, c.period, r.pool_balance
      ORDER BY ABS(SUM(c.pool_balance)-r.pool_balance) DESC LIMIT 8""")
    for r in cur.fetchall(): print("  %-14s %s  ours %s  theirs %s  %s%%" % r)
PY
```

Expected: small differences. ABS-EE and the servicer report are struck at
slightly different points, so **exact equality is not expected and a zero
difference everywhere would itself be suspicious**. Record the observed
spread; a deal-period beyond a few percent is a finding.

- [ ] **Step 4: Commit**

```bash
git add loaders/load_abs_aggregates_wave14.py
git commit -m "Materialized cohort and vintage aggregates"
```

---

## Task 12: The internal overlay

**Files:**
- Create: `generators/generate_abs_overlay.py`, `loaders/load_abs_overlay_wave14.py`

**Interfaces:**
- Produces: `abs_holding`, `abs_materialization_policy`,
  `abs_granularity_entitlement`; Fluree privacy-constraint nodes; three
  crosswalk rows.

**§F's restricted principal must actually bind.** A policy row granting a
ceiling nobody hits is a label, not a constraint — Wave 13b's exact defect.
The gate in Task 13 issues a `loan`-granularity request as the restricted
principal and proves the effective granularity comes back lower.

**Crosswalk care.** `positional-identity-is-a-defect-class`: four loaders on
`main` assign identity by row position and silently rewrite other waves' rows
when a table grows. Check before inserting the three trusts.

- [ ] **Step 1: Check the crosswalk loaders for positional identity**

```bash
grep -rn 'ROW_NUMBER\|enumerate(\|idx + 1\|i + 1' loaders/*.py | grep -i 'crosswalk\|internal_client'
```

Expected: nothing. **If a loader derives `internal_client_id` from position**,
adding three rows renumbers existing clients. Fix that loader first and note
it in `known-issues.md` — do not work around it here.

- [ ] **Step 2: Implement the generator**

```python
#!/usr/bin/env python3
"""The bank-internal overlay for the ABS deals.

    uv run generators/generate_abs_overlay.py

Everything here is invented, because it is bank-internal by nature: what the
bank holds, how it materializes, and who may see loan-level detail. All rows
carry `synthetic — internal`.

## The restricted principal has to actually bind

§F asks for a principal restricted to aggregate-only granularity. A policy row
that grants a ceiling nobody ever reaches is a label. So the restricted
principal is one that a realistic request WOULD otherwise take to loan level,
and `validators/abs_surveillance.py` proves the ceiling lowers a real request
rather than merely existing.
"""
from __future__ import annotations

import json
import sys
from datetime import date

from ccf.config import REPO_ROOT

OUT = REPO_ROOT / "sources" / "absee" / "overlay.json"

HOLDINGS = [
    # (deal_id, class, position type, notional, retention)
    ("SDART-2022-6", "A-3", "investment", "25000000", False),
    ("SDART-2022-6", "B",   "investment", "10000000", False),
    ("TAOT-2022-B",  "A-4", "investment", "40000000", False),
    ("TAOT-2022-B",  "B",   "risk-retention", "12500000", True),
    ("SDART-2024-1", "A-3", "investment", "30000000", False),
    ("SDART-2024-1", "C",   "risk-retention", "8000000", True),
]

MATERIALIZATION = [
    ("deal",    "materialized", 30, "read pre-aggregated deal state; one query"),
    ("tranche", "materialized", 30, "read pre-aggregated tranche state; one query"),
    ("cohort",  "materialized", 30, "cohort aggregates, batched per requested cohort"),
    ("loan",    "on-demand",     0, "stream loan rows; never materialize the pool"),
]

ENTITLEMENTS = [
    # (principal, max granularity, why)
    ("structured-finance-desk", "loan",
     "arranges and holds these deals; needs loan-level detail"),
    ("credit-risk", "cohort",
     "monitors trigger proximity; cohort detail is sufficient"),
    # The restricted principal. §F requires one, and it must BITE.
    ("client-reporting", "deal",
     "external-facing; loan-level borrower attributes are not disclosable"),
]

#: Fields a below-loan principal must never receive, even in aggregate form
#: with a small denominator. These are the quasi-identifiers in ABS-EE.
PRIVACY_RESTRICTED_FIELDS = [
    "obligor_credit_score", "obligor_geographic_location",
    "payment_to_income_percentage", "obligor_income_verification_level_code",
]


def main() -> int:
    payload = {
        "generated_at": date.today().isoformat(),
        "provenance": "synthetic — internal",
        "holdings": [
            {"deal_id": d, "class_name": c, "position_type": p,
             "notional": n, "is_risk_retention": r,
             "tranche_id": f"{d}-{c}"}
            for d, c, p, n, r in HOLDINGS],
        "materialization": [
            {"granularity": g, "posture": p, "refresh_days": r, "note": n}
            for g, p, r, n in MATERIALIZATION],
        "entitlements": [
            {"principal": p, "max_granularity": g, "rationale": r}
            for p, g, r in ENTITLEMENTS],
        "privacy_restricted_fields": PRIVACY_RESTRICTED_FIELDS,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"  {len(HOLDINGS)} holdings, {len(ENTITLEMENTS)} entitlements "
          f"(restricted: client-reporting -> deal)")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Implement the loader**

```python
#!/usr/bin/env python3
"""Load the internal overlay into Postgres and Fluree.

    uv run loaders/load_abs_overlay_wave14.py --dry-run
    uv run loaders/load_abs_overlay_wave14.py

Postgres owns the holdings, the materialization policy and the entitlement
grants (`E` and `P` reference). Fluree owns the loan-level privacy
constraints, which §C files under `P` on the Fluree row.
"""
from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import EX, PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)
OVERLAY = REPO_ROOT / "sources" / "absee" / "overlay.json"
PROV = "synthetic — internal"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_holding (
    holding_id text PRIMARY KEY,
    deal_id    text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    tranche_id text NOT NULL REFERENCES "{S}".abs_tranche(tranche_id),
    position_type text NOT NULL,
    notional numeric NOT NULL,
    is_risk_retention boolean NOT NULL,
    provenance text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_materialization_policy (
    granularity text PRIMARY KEY,
    posture     text NOT NULL,          -- materialized | on-demand
    refresh_days integer NOT NULL,
    note        text NOT NULL,
    provenance  text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_granularity_entitlement (
    principal text PRIMARY KEY,
    max_granularity text NOT NULL,      -- deal | tranche | cohort | loan
    rationale text NOT NULL,
    provenance text NOT NULL
);
"""

#: Granularity ordering, coarse to fine. The ceiling is a MIN over this.
ORDER = {"deal": 0, "tranche": 1, "cohort": 2, "loan": 3}


def effective_granularity(requested: str, principal_max: str) -> str:
    """The lower of what was asked for and what the principal may have."""
    return requested if ORDER[requested] <= ORDER[principal_max] else principal_max


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ov = json.loads(OVERLAY.read_text())
    holdings = [(f"{h['deal_id']}-{h['class_name']}-{h['position_type']}",
                 h["deal_id"], h["tranche_id"], h["position_type"],
                 h["notional"], h["is_risk_retention"], PROV)
                for h in ov["holdings"]]

    print(f"  {len(holdings)} holdings, {len(ov['materialization'])} policy rows, "
          f"{len(ov['entitlements'])} entitlements")
    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(f"""
            INSERT INTO "{S}".abs_holding VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (holding_id) DO UPDATE SET notional = EXCLUDED.notional""",
            holdings)
        cur.executemany(f"""
            INSERT INTO "{S}".abs_materialization_policy VALUES (%s,%s,%s,%s,'{PROV}')
            ON CONFLICT (granularity) DO UPDATE SET posture = EXCLUDED.posture""",
            [(m["granularity"], m["posture"], m["refresh_days"], m["note"])
             for m in ov["materialization"]])
        cur.executemany(f"""
            INSERT INTO "{S}".abs_granularity_entitlement VALUES (%s,%s,%s,'{PROV}')
            ON CONFLICT (principal) DO UPDATE SET
              max_granularity = EXCLUDED.max_granularity""",
            [(e["principal"], e["max_granularity"], e["rationale"])
             for e in ov["entitlements"]])
        conn.commit()

    # Fluree: the loan-level privacy constraints (§C files these under P here).
    triples = []
    for field in ov["privacy_restricted_fields"]:
        c_uri = f"{EX}abs-privacy-constraint-{field.replace('_', '-')}"
        triples += [
            f'<{c_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            f'<{EX}LoanLevelPrivacyConstraint> .',
            f'<{c_uri}> <{EX}restrictsField> "{field}" .',
            f'<{c_uri}> <{EX}minimumGranularity> "cohort" .',
            f'<{c_uri}> <{EX}provenance> "{PROV}" .',
        ]
    fluree.update("INSERT DATA { " + " ".join(triples) + " }")
    n = fluree.stable_scalar(
        f'SELECT (COUNT(?c) AS ?n) WHERE {{ ?c a <{EX}LoanLevelPrivacyConstraint> }}')
    print(f"  privacy constraints in ledger: {n}")

    # The three trusts join the crosswalk so internal holdings resolve.
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT column_name FROM information_schema.columns '
                    f"WHERE table_schema='{S}' AND table_name='crosswalk'")
        print("  crosswalk columns:", [r[0] for r in cur.fetchall()])
    print("  NOTE: add the three trusts to the crosswalk using that table's own "
          "id convention -- never a positional id.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Generate, load, and add the crosswalk rows**

```bash
uv run generators/generate_abs_overlay.py
uv run loaders/load_abs_overlay_wave14.py --dry-run
uv run loaders/load_abs_overlay_wave14.py
```

Read the printed crosswalk columns and add the three trusts with an
`internal_client_id` following that table's existing convention. Then confirm
the orphan gate still passes:

```bash
uv run validators/conditions.py --product counterparty-reference-snapshot
```

Expected: the crosswalk orphan check still reports 0 orphans.

- [ ] **Step 5: Commit**

```bash
git add generators/generate_abs_overlay.py loaders/load_abs_overlay_wave14.py \
        sources/absee/overlay.json
git commit -m "Internal overlay: holdings, materialization policy, privacy ceiling"
```

---

## Task 13: `validators/abs_surveillance.py` — the gate

**Files:**
- Create: `validators/abs_surveillance.py`

**Interfaces:**
- Consumes: `effective_granularity` from `loaders.load_abs_overlay_wave14`;
  `threshold_as_of`/`threshold_known_as_of` from
  `generators.generate_trigger_amendment`.
- Produces: exit 0 when all six checks pass.

Seven checks. Every one recomputes; none reads a stored answer.

- [ ] **Step 1: Implement**

```python
#!/usr/bin/env python3
"""The Wave 14 gate. Seven checks, all recomputed.

    uv run validators/abs_surveillance.py

## What this file refuses to do

`abs_servicer_report.published_trigger_occurred` states, per period, whether
the delinquency trigger fired. `abs_servicer_report.published_delinquency_percent`
states the ratio. `bo_chain.depth` and `person_crosswalk.match_band` were the
Wave 13b equivalents, and reading them is how three of that wave's four
defects survived in conditions already reporting PASS.

So check 1 recomputes the delinquency percentage from `abs_loan_period` and
uses the published figure only to CROSS-CHECK. A disagreement is reported,
never smoothed.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ccf import fluree
from ccf.config import EX, PG_SCHEMA_V2, mongo_db, pg_connect

S = PG_SCHEMA_V2
#: They agree EXACTLY. Measured 2026-08-23 on SDART 2022-6 2026-07: the
#: loan-level pool balance and 60-day delinquent balance each reproduce the
#: servicer's published figure to the penny, and the ratio lands on the
#: published 10.79%.
#:
#: So the tolerance is tight on purpose. A wide one here would be decoration:
#: an earlier draft used 2.0pp, which is three times the 0.68pp bias that a
#: >= 61 day threshold introduces -- the gate would have passed forever while
#: measuring the wrong population.
RECONCILE_TOLERANCE_PP = Decimal("0.02")


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


def check_delinquency_recomputes(cur) -> list[Result]:
    """Recompute delinquency from loan level; cross-check against the filing."""
    cur.execute(f"""
        SELECT l.deal_id, l.period,
               ROUND(100 * SUM(CASE WHEN l.current_delinquency_status >= 60
                        THEN l.reporting_period_actual_end_balance_amount ELSE 0 END)
                     / NULLIF(SUM(l.reporting_period_actual_end_balance_amount), 0), 4)
                   AS recomputed,
               r.published_delinquency_percent AS published
        FROM "{S}".abs_loan_period l
        JOIN "{S}".abs_servicer_report r USING (deal_id, period)
        GROUP BY l.deal_id, l.period, r.published_delinquency_percent
        ORDER BY l.deal_id, l.period""")
    rows = cur.fetchall()
    if not rows:
        return [Result("delinquency recomputed from loan level", False,
                       "no loan rows joined to servicer reports")]
    breaks = [(d, p, rc, pb) for d, p, rc, pb in rows
              if rc is None or abs(rc - pb) > RECONCILE_TOLERANCE_PP]
    detail = (f"{len(rows)} deal-periods recomputed; "
              f"{len(breaks)} beyond {RECONCILE_TOLERANCE_PP}pp")
    if breaks:
        detail += " -- " + "; ".join(f"{d} {p}: ours {rc} vs filed {pb}"
                                     for d, p, rc, pb in breaks[:4])
    return [Result("delinquency recomputed from loan level", not breaks, detail)]


def check_pool_balance_reconciles(cur) -> list[Result]:
    """The strongest check in the wave: the loan file must foot to the filing.

    Summing every loan's ending balance must equal the pool balance the
    servicer published, to the cent -- two documents, two preparers, one
    number. This is what proves the load is complete and correctly typed:
    a single dropped record, a truncated period, or a float somewhere would
    all move it.
    """
    cur.execute(f"""
        SELECT l.deal_id, l.period,
               SUM(l.reporting_period_actual_end_balance_amount) AS ours,
               r.pool_balance AS filed
        FROM "{S}".abs_loan_period l
        JOIN "{S}".abs_servicer_report r USING (deal_id, period)
        GROUP BY l.deal_id, l.period, r.pool_balance
        ORDER BY l.deal_id, l.period""")
    rows = cur.fetchall()
    if not rows:
        return [Result("pool balance reconciles to the filing", False,
                       "no loan rows joined to servicer reports")]
    breaks = [(d, p, ours, filed) for d, p, ours, filed in rows
              if ours is None or abs(ours - filed) > Decimal("0.01")]
    detail = f"{len(rows)} deal-periods; {len(breaks)} off by more than a cent"
    if breaks:
        detail += " -- " + "; ".join(f"{d} {p}: ours {ours} vs filed {filed}"
                                     for d, p, ours, filed in breaks[:4])
    return [Result("pool balance reconciles to the filing", not breaks, detail)]


def check_trajectory(cur) -> list[Result]:
    """A trajectory, not a static distance.

    Counts PERIODS in which proximity narrowed -- the unit the condition
    names. Counting deals, or trigger definitions, would pass forever.
    """
    cur.execute(f"""
        SELECT deal_id, period, published_delinquency_trigger
                                - published_delinquency_percent AS distance
        FROM "{S}".abs_servicer_report ORDER BY deal_id, period""")
    series: dict[str, list] = {}
    for deal_id, period, distance in cur.fetchall():
        series.setdefault(deal_id, []).append((period, distance))

    results = []
    narrowing_deals = 0
    for deal_id, points in series.items():
        narrowed = sum(1 for i in range(1, len(points))
                       if points[i][1] < points[i - 1][1])
        total_move = points[0][1] - points[-1][1]
        if narrowed >= len(points) // 2 and total_move > 0:
            narrowing_deals += 1
        results.append(Result(
            f"  {deal_id} proximity", True,
            f"{narrowed}/{len(points) - 1} periods narrowed, "
            f"net {total_move:+.2f}pp toward the trigger"))
    results.insert(0, Result(
        "at least one trigger approaching across the series",
        narrowing_deals >= 1,
        f"{narrowing_deals} of {len(series)} deals narrow across the window"))
    return results


def check_amendment_diverges() -> list[Result]:
    """as_of and known_as_of must return DIFFERENT answers in the gap.

    If they agree everywhere the bitemporal claim is unfalsifiable, which is
    the same shape as a decomposition that is algebraically zero.
    """
    rows = fluree.query(f"""
        SELECT ?t ?v ?eff ?asserted WHERE {{
          ?t <{EX}thresholdValue> ?v .
          ?t <{EX}validFrom> ?eff .
          ?t <{EX}assertedAt> ?asserted .
        }}""")["results"]["bindings"]
    chain = [{"value": b["v"]["value"],
              "effective_from": date.fromisoformat(b["eff"]["value"]),
              "asserted_at": date.fromisoformat(b["asserted"]["value"])}
             for b in rows if "delinquency" in b["t"]["value"]
             and "SDART-2022-6" in b["t"]["value"]]
    if len(chain) < 2:
        return [Result("trigger amendment supersession", False,
                       f"expected 2 assertions in the chain, found {len(chain)}")]

    from generators.generate_trigger_amendment import (
        threshold_as_of, threshold_known_as_of)
    amended = max(chain, key=lambda a: a["effective_from"])
    gap_day = amended["effective_from"] + (
        amended["asserted_at"] - amended["effective_from"]) / 2

    as_of = threshold_as_of(chain, gap_day)
    known = threshold_known_as_of(chain, gap_day)
    return [Result(
        "as_of and known_as_of diverge inside the booking gap",
        as_of != known,
        f"on {gap_day}: in force {as_of}, known {known} "
        f"({(amended['asserted_at'] - amended['effective_from']).days}d lag)")]


def check_every_threshold_is_anchored() -> list[Result]:
    """Every filed threshold resolves to prospectus text.

    The engineered amendment is the ONE exception, by name, because no filed
    sentence says it. Exempting it silently would let any unanchored
    threshold through.
    """
    db = mongo_db(write=False)
    anchors = {a["trigger_id"] for a in db["trigger_anchor"].find({}, {"trigger_id": 1})}
    rows = fluree.query(f"""
        SELECT ?t ?p WHERE {{ ?t <{EX}thresholdValue> ?v .
                              ?t <{EX}provenance> ?p . }}""")["results"]["bindings"]
    unanchored = []
    for b in rows:
        trigger_uri = b["t"]["value"]
        trigger_id = trigger_uri.rsplit("abs-trigger-", 1)[-1]
        if b["p"]["value"] == "synthetic — engineered":
            continue                      # named exception, see docstring
        if trigger_id not in anchors:
            unanchored.append(trigger_id)
    return [Result("every filed threshold carries a passage anchor",
                   not unanchored,
                   f"{len(anchors)} anchors; unanchored: {unanchored or 'none'}")]


def check_restricted_principal_binds(cur) -> list[Result]:
    """The ceiling must LOWER a real request, not merely exist."""
    from loaders.load_abs_overlay_wave14 import effective_granularity
    cur.execute(f'SELECT principal, max_granularity '
                f'FROM "{S}".abs_granularity_entitlement')
    grants = dict(cur.fetchall())
    if not grants:
        return [Result("restricted principal binds", False, "no entitlements loaded")]

    lowered = {p: effective_granularity("loan", g)
               for p, g in grants.items()
               if effective_granularity("loan", g) != "loan"}
    shown = (", ".join(f"{p} -> {g}" for p, g in sorted(lowered.items()))
             if lowered else "none lowered")
    return [Result(
        "at least one principal is restricted below the request",
        len(lowered) >= 1,
        f"requesting granularity=loan: {shown}")]


def check_tranche_structure(cur) -> list[Result]:
    """Count DISTINCT tranches per deal, not mentions."""
    cur.execute(f"""SELECT deal_id, COUNT(*) FROM "{S}".abs_tranche
                    GROUP BY deal_id ORDER BY deal_id""")
    rows = cur.fetchall()
    short = [(d, n) for d, n in rows if n < 4]
    return [Result("every deal carries >= 4 distinct tranches", not short,
                   ", ".join(f"{d}: {n}" for d, n in rows))]


def main() -> int:
    results: list[Result] = []
    with pg_connect() as conn, conn.cursor() as cur:
        results += check_pool_balance_reconciles(cur)
        results += check_delinquency_recomputes(cur)
        results += check_trajectory(cur)
        results += check_tranche_structure(cur)
        results += check_restricted_principal_binds(cur)
    results += check_amendment_diverges()
    results += check_every_threshold_is_anchored()

    print("ABS securitization surveillance — Wave 14 gate\n")
    failed = 0
    for r in results:
        if r.name.startswith("  "):
            print(f"      {r.detail}")
            continue
        state = "PASS" if r.ok else "FAIL"
        failed += not r.ok
        print(f"  [{state}] {r.name}\n         {r.detail}")
    print(f"\n  {len(results) - failed} pass, {failed} fail")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `uv run validators/abs_surveillance.py`
Expected: 7 PASS.

- [ ] **Step 3: Prove each check can fail — the step Wave 12 skipped**

A check nobody has seen fail is a check nobody has verified. Break each input
in a transaction and roll back:

```bash
uv run python - <<'PY'
from ccf.config import PG_SCHEMA_V2 as S, pg_connect
import subprocess
MUTATIONS = [
  ("delinquency", f'UPDATE "{S}".abs_loan_period SET current_delinquency_status = 0 '
                  "WHERE current_delinquency_status >= 60"),
  ("trajectory",  f'UPDATE "{S}".abs_servicer_report '
                  "SET published_delinquency_percent = 5.0"),
  ("tranches",    f'DELETE FROM "{S}".abs_tranche WHERE class_name NOT IN (%s,%s)'),
  ("entitlement", f"UPDATE \"{S}\".abs_granularity_entitlement SET max_granularity='loan'"),
]
for name, sql in MUTATIONS:
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(sql, ("A-1","A-2")) if "%s" in sql else cur.execute(sql)
        r = subprocess.run(["uv","run","validators/abs_surveillance.py"],
                           capture_output=True, text=True)
        print(f"{name:12s} -> exit {r.returncode}  (want non-zero)")
        c.rollback()
PY
```

Expected: **every mutation produces a non-zero exit.** Any that still passes
is a decorative check — fix it before continuing. Note that the `delinquency`
mutation must trip check 1 *because* the recomputation moves while the
published figure does not; if it passes, the check is reading the published
column.

- [ ] **Step 4: Commit**

```bash
git add validators/abs_surveillance.py
git commit -m "Wave 14 gate: six checks, all recomputed, all proven to fail"
```

---

## Task 14: `validators/abs_cost.py` — the measured curve

**Files:**
- Create: `validators/abs_cost.py`

**Interfaces:**
- Produces: table `abs_cost_measurement`; a printed curve.

The spec calls this the product's most valuable output. It measures *our
data's* fan-out — rows, bytes, latency — and nothing about assembly.

- [ ] **Step 1: Implement**

```python
#!/usr/bin/env python3
"""Measure the fan-out cost at each granularity.

    uv run validators/abs_cost.py
    uv run validators/abs_cost.py --repeat 5

§F: "Measured cost figures at each granularity, captured during assembly and
published alongside the spec -- this product's most valuable output for the
SDK."

## What is measured, and what is not

Measured: rows returned, bytes read from the heap, and wall-clock latency for
the canonical query at each granularity, against the loaded stores. That is a
property of the DATA and squarely this project's job.

NOT measured or built here: operators, projection, contracts, TTL. Those are
downstream and out of scope per CLAUDE.md.

## The curve is recomputed, never stored as a constant

A hard-coded cost table is the same defect class as a hard-coded threshold:
it reports the same answer after the data changes underneath it.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time

from ccf.config import PG_SCHEMA_V2, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_cost_measurement (
    measured_at timestamptz NOT NULL DEFAULT now(),
    granularity text NOT NULL,
    deal_id     text NOT NULL,
    period      char(7) NOT NULL,
    rows_returned bigint NOT NULL,
    heap_blocks_read bigint,
    median_ms numeric NOT NULL,
    repeats integer NOT NULL,
    row_basis bigint NOT NULL,      -- table size the measurement was taken against
    provenance text NOT NULL DEFAULT 'derived — measured',
    PRIMARY KEY (measured_at, granularity, deal_id, period)
);
"""

QUERIES = {
    "deal": f"""
        SELECT deal_id, SUM(pool_balance), SUM(delinquent_60_plus_balance)
        FROM "{S}".abs_cohort_performance
        WHERE deal_id = %(deal)s AND period = %(period)s GROUP BY deal_id""",
    "tranche": f"""
        SELECT t.tranche_id, t.seniority_rank, c.pool_balance
        FROM "{S}".abs_tranche t
        JOIN "{S}".abs_cohort_performance c ON c.deal_id = t.deal_id
        WHERE t.deal_id = %(deal)s AND c.period = %(period)s""",
    "cohort": f"""
        SELECT credit_band, loan_count, pool_balance, delinquency_percent
        FROM "{S}".abs_cohort_performance
        WHERE deal_id = %(deal)s AND period = %(period)s""",
    "loan": f"""
        SELECT asset_number, reporting_period_actual_end_balance_amount,
               current_delinquency_status, obligor_credit_score
        FROM "{S}".abs_loan_period
        WHERE deal_id = %(deal)s AND period = %(period)s""",
}


def measure(cur, granularity: str, deal: str, period: str, repeats: int) -> dict:
    sql = QUERIES[granularity]
    params = {"deal": deal, "period": period}

    # Explicit warm-up so the first timing does not carry cold-cache noise
    # into a curve that is meant to compare granularities, not cache states.
    cur.execute(sql, params)
    cur.fetchall()

    timings, rows = [], 0
    for _ in range(repeats):
        start = time.perf_counter()
        cur.execute(sql, params)
        fetched = cur.fetchall()
        timings.append((time.perf_counter() - start) * 1000)
        rows = len(fetched)

    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}", params)
    plan = cur.fetchone()[0][0]["Plan"]
    blocks = plan.get("Shared Hit Blocks", 0) + plan.get("Shared Read Blocks", 0)

    return {"granularity": granularity, "deal_id": deal, "period": period,
            "rows_returned": rows, "heap_blocks_read": blocks,
            "median_ms": round(statistics.median(timings), 3), "repeats": repeats}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--deal", default="SDART-2022-6")
    ap.add_argument("--period", default="2026-06")
    ap.add_argument("--no-store", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        conn.commit()
        cur.execute(f'SELECT COUNT(*) FROM "{S}".abs_loan_period')
        basis = cur.fetchone()[0]

        print(f"Cost curve — {args.deal} {args.period}, "
              f"measured against {basis:,} loan rows\n")
        print(f"  {'granularity':<12}{'rows':>10}{'blocks':>10}{'median ms':>12}"
              f"{'x deal':>9}")
        results, baseline = [], None
        for g in ("deal", "tranche", "cohort", "loan"):
            m = measure(cur, g, args.deal, args.period, args.repeat)
            baseline = baseline or m["median_ms"]
            ratio = m["median_ms"] / baseline if baseline else 0
            results.append(m)
            print(f"  {g:<12}{m['rows_returned']:>10,}{m['heap_blocks_read']:>10,}"
                  f"{m['median_ms']:>12.3f}{ratio:>8.1f}x")

        if not args.no_store:
            for m in results:
                cur.execute(f"""
                    INSERT INTO "{S}".abs_cost_measurement
                      (granularity, deal_id, period, rows_returned,
                       heap_blocks_read, median_ms, repeats, row_basis)
                    VALUES (%(granularity)s,%(deal_id)s,%(period)s,
                            %(rows_returned)s,%(heap_blocks_read)s,
                            %(median_ms)s,%(repeats)s,%(basis)s)""",
                    {**m, "basis": basis})
            conn.commit()

    # A curve that does not RISE has measured nothing -- most likely the
    # aggregates were built as views, so every granularity rescans the pool.
    loan = next(r for r in results if r["granularity"] == "loan")
    deal = next(r for r in results if r["granularity"] == "deal")
    if loan["rows_returned"] <= deal["rows_returned"]:
        print("\n  FAIL: loan granularity returned no more rows than deal. "
              "The fan-out this product exists to measure is not present.")
        return 1
    print(f"\n  fan-out {loan['rows_returned'] / max(deal['rows_returned'], 1):,.0f}x "
          f"in rows, {loan['median_ms'] / max(deal['median_ms'], 0.001):,.1f}x in time")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Measure**

Run: `uv run validators/abs_cost.py --repeat 5`
Expected: a rising curve — `deal` ~1 row, `loan` ~35,814 rows, with latency
rising by a large multiple. **If `loan` is not markedly more expensive, the
aggregates are not doing their job** — check Task 11 built tables, not views.

- [ ] **Step 3: Record the curve in the design doc**

Add the measured figures to `docs/wave14-design.md` §7 as a table, with the
row basis and the date. This is the deliverable the spec names.

- [ ] **Step 4: Commit**

```bash
git add validators/abs_cost.py docs/wave14-design.md
git commit -m "Measured cost curve at each granularity"
```

---

## Task 15: Register, partition, document, and send the punch list

**Files:**
- Modify: `validators/conditions.py`, `validators/partition.py`,
  `docs/ccf_dataprep_v2.md`, `docs/HANDOFF.md`

**Unregistered is invisible.** `facility-terms-snapshot` sat complete for
eleven waves because it had no rows here. A product is done when a gate would
notice if its data stopped existing.

- [ ] **Step 1: Add the nine conditions**

In `validators/conditions.py`, inside `collect()`, after the last product
block and using the surrounding style:

```python
        # --- #17 abs-securitization-surveillance --------------------------
        checks.append(Check(
            "abs-securitization-surveillance", "deals loaded", 2,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".abs_deal'),
            "spec says 2-3; depth not breadth",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "deals with all 12 periods", 3,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT deal_id FROM "{S}".abs_loan_period
                    GROUP BY deal_id HAVING COUNT(DISTINCT period) >= 12) t"""),
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "minimum loans in any deal-period", 15000,
            pg_scalar(cur, f"""
                SELECT MIN(n) FROM (
                    SELECT COUNT(*) AS n FROM "{S}".abs_loan_period
                    GROUP BY deal_id, period) t"""),
            "the MINIMUM, not the mean -- a mean hides a thin period",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "deals with >= 4 distinct tranches", 3,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT deal_id FROM "{S}".abs_tranche
                    GROUP BY deal_id HAVING COUNT(*) >= 4) t"""),
            "distinct tranches, never prospectus mentions",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "trigger definitions with a threshold", 9,
            fl_scalar(f"""
                SELECT (COUNT(DISTINCT ?t) AS ?n) WHERE {{
                  ?t <{EX}thresholdValue> ?v }}"""),
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "thresholds anchored to prospectus text", 9,
            mongo_count("trigger_anchor", {}),
            "an unanchored threshold is a number nobody can defend",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "engineered trigger amendments", 1,
            fl_scalar(f"""
                SELECT (COUNT(?s) AS ?n) WHERE {{
                  ?o <{EX}supersededBy> ?s .
                  ?s <{EX}provenance> "synthetic — engineered" }}"""),
            "labelled engineered; no real auto ABS amends a trigger",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "principals restricted below loan level", 1,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM "{S}".abs_granularity_entitlement
                WHERE max_granularity <> 'loan'"""),
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "granularities with a measured cost", 4,
            pg_scalar(cur, f"""
                SELECT COUNT(DISTINCT granularity) FROM "{S}".abs_cost_measurement"""),
        ))
```

`pg_scalar`, `fl_scalar` and `mongo_count` all already exist in this validator
(lines 71, 80, 88) — use them, do not add new helpers. `mongo_count`'s second
argument is optional, so `mongo_count("trigger_anchor")` is equivalent to the
call above.

- [ ] **Step 2: Run the register**

Run: `uv run validators/conditions.py --product abs-securitization-surveillance`
Expected: 9 PASS. Then the whole register:

Run: `uv run validators/conditions.py`
Expected: 146 pass, 0 fail (137 + 9). **A drop in the prior 137 means this
wave broke something** — find it before continuing.

- [ ] **Step 3: Extend the partition check**

Add the Wave 14 tables to `POSTGRES_OWNED_ATTRS` and the Fluree predicates to
the permitted lists in `validators/partition.py`, following the existing
entries. The check must assert:

- Postgres holds `abs_loan_period`, `abs_cohort_performance`,
  `abs_servicer_report` and **no threshold values**;
- Fluree holds trigger thresholds and structure and **no pool balances or
  delinquency percentages**;
- Mongo holds text and anchors and **no numeric measures outside
  `published_measures`**, which is stored evidence and is documented as such.

Run: `uv run validators/partition.py`
Expected: all checks pass, count rises from 27.

- [ ] **Step 4: Update the documentation**

`docs/ccf_dataprep_v2.md`: add a 2026-08 Wave 14 changelog with the actual
loaded counts (not the plan's estimates), the new tables, the `isSubordinateTo`
binding, and the ABS trust entities.

`docs/HANDOFF.md`: move `abs-securitization-surveillance` into the §3 table as
product 17, remove it from "the five that remain", rewrite §8 to name the next
product, and record any defect found.

- [ ] **Step 5: Send the vault punch list**

Read section 5 of the `obsidian-vault-access` skill before the first send.
The message directory is `<YYYY-MM-DDTHH-MM-SSZ>-<slug>` with **hyphens in
the time, never colons**.

The punch list should carry: the `isSubordinateTo` binding (or its recorded
absence), any §C source deviation found — in particular that ABS-15G is
depositor-level rather than per-trust, which the spec does not say — and the
measured cost curve, since §F asks for it to be published alongside the spec.

Then **say in your response** that the mirror needs refreshing and that the
punch list has been sent.

- [ ] **Step 6: Final verification and commit**

```bash
uv run validators/conditions.py
uv run validators/partition.py
uv run validators/abs_surveillance.py
uv run validators/abs_cost.py
uv run pytest validators/ -q
git add -A
git commit -m "Register Wave 14: nine conditions, partition slice, docs"
```

Expected: conditions 146/0, partition all pass, gate 7/7, all suites green.
`artifact_reproduces_store` still exits 1 by design.

**`binding_drift.py` exits 1, not 0** — this note originally said the
opposite. Measured 2026-08-23 after the fix round: **9 agree · 47 disagree**,
split 31 `CAVEAT_STALE` + 16 `CLAIM_MISSING`, not the 10/41 claimed here nor
the 11/32 the pre-rewrite handoff claimed. The line references (75, 89, 111,
206) were correct against the 919-line handoff that existed when this plan was
written; that file has since been rewritten to ~75 lines. It
compares vault claims against Fluree state, so it is not a binding-table
count and will not mention `isSubordinateTo` at all. Correct those four
handoff lines as part of this step; the growth from 32 to 41 disagreements is
the uncollected Wave 13b punch list, and the mirror drifts in both
directions.

---

## Self-review notes

**Spec coverage.** Every §C element maps to a task: loan data (5), prospectus
and structural terms (6, 7), tranche/waterfall/trigger definitions (6, 7, 9),
ABS-15G (3, 8), servicer reports (3, 7, 8), passage spans (7), the three edge
types (9), dated threshold assertions (9, 10), FIBO classes (1, 9), benchmarks
(11), internal holdings (12), materialization policy (12), privacy constraints
(12). All nine §F conditions are registered in Task 15.

**Deliberate omissions.** No embeddings task — `loaders/embed_passages.py`
already exists and Task 7 step 4 invokes it. No SQLite or Neo4j work: §C
assigns them nothing.

**Where this plan is most likely to be wrong.** The servicer-report item
numbers are verified against one Santander report only. If Toyota numbers its
line items differently, Task 4 step 5 will surface it across all 36 files at
once, and the fix is an issuer-keyed map rather than a looser regex. That is
called out in the task.

**The cost figures in `docs/wave14-design.md` are extrapolations** from two
measured endpoints per deal. Task 5 step 4 produces the true count and the
design doc must be corrected from it — the plan says so explicitly rather than
letting an estimate harden into a recorded fact.
