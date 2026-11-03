#!/usr/bin/env python3
"""Pure WARN-notice parsers — no network, no file I/O.

Mirrors `generators/curves.py` sitting beside `generators/fetch_treasury.py`:
the parsing logic lives here so it is unit-testable offline
(`validators/test_warn_match.py`), and the network/subprocess plumbing lives
in `generators/fetch_warn.py`.

Three sources, three shapes, one dataclass:

- **Texas** (Socrata JSON): dates arrive as `2022-01-06T00:00:00.000`.
  Truncated at the `T` — the value is already ISO-ordered (YYYY-MM-DD), so
  slicing off the time component does not reorder anything the way slicing a
  `MM/DD/YYYY` string would.
- **California XLSX** (`'Detailed WARN Report '` sheet, trailing space and
  all): the header row carries embedded newlines (`"Notice\nDate"`), so
  columns are located by a *normalised* header name, never literal text.
  Dates arrive as `"2026-06-26 00:00:00"`, truncated at the space — same
  ISO-ordering argument as Texas.
- **California PDF** (`pdftotext -layout` over the per-FY reports): dates
  render `MM/DD/YYYY`. THIS one is genuinely ambiguous against slicing, so it
  is the one parser in this module that goes through `datetime.strptime`
  rather than a string op — never treat `MM/DD/YYYY` and `YYYY-MM-DD` as
  interchangeable by position.

Employer strings are preserved EXACTLY as published — no normalisation, no
title-casing, no stripping of site suffixes ("Stearns Lending, LLC -
Corporate", "Avis Budget Car Rental-El Paso"). The next wave's obligor match
depends on these warts surviving intact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

#: The Socrata resource backing every TX row parsed here.
TX_SOURCE_REF = "data.texas.gov:8w53-c4f6"

#: A CA PDF data line starts with a date token; header/page-furniture lines
#: do not, and are how they're discarded.
_PDF_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
#: The employees+type field, e.g. "104 Layoff Permanent" or "16,132 Closure
#: Permanent" — matched by CONTENT (the trailing Layoff/Closure keyword),
#: not by a fixed column index. See the long comment in parse_ca_pdf_text.
_PDF_EMPLOYEES_RE = re.compile(r"^([\d,]+)\s+(?:Layoff|Closure)\b")


@dataclass
class WarnNotice:
    """One WARN layoff notice, from whichever state/format it was read.

    `employer` is preserved verbatim — see module docstring.
    """

    state: str
    employer: str
    notice_date: str  # ISO YYYY-MM-DD
    effective_date: str | None
    employees: int | None
    city: str | None
    county: str | None
    source_ref: str


def _truncate_iso_datetime(raw: str | None, sep: str) -> str | None:
    """Truncate an already-ISO-ordered `YYYY-MM-DD<sep>...` at `sep`.

    Not used for MM/DD/YYYY — that format is parsed with `strptime` in
    `parse_ca_pdf_text` because slicing it would risk transposing month and
    day. ISO-ordered strings have no such ambiguity: dropping everything
    from `sep` onward can't reorder components that are already
    year-month-day.
    """
    if not raw:
        return None
    return raw.split(sep, 1)[0] or None


def parse_tx_socrata(rows: list[dict]) -> list[WarnNotice]:
    """Parse rows from `data.texas.gov` resource `8w53-c4f6`."""
    notices: list[WarnNotice] = []
    for row in rows:
        notice_date = _truncate_iso_datetime(row.get("notice_date"), "T")
        if not notice_date:
            continue
        effective_date = _truncate_iso_datetime(row.get("layoff_date"), "T")
        raw_count = row.get("total_layoff_number")
        employees = int(raw_count) if raw_count not in (None, "") else None
        notices.append(WarnNotice(
            state="TX",
            employer=row.get("job_site_name", ""),
            notice_date=notice_date,
            effective_date=effective_date,
            employees=employees,
            city=row.get("city_name") or None,
            county=row.get("county_name") or None,
            source_ref=TX_SOURCE_REF,
        ))
    return notices


def _normalise_header(cell: object) -> str:
    """`"Notice\\nDate"` -> `"notice date"`. Collapses ANY whitespace run."""
    return " ".join(str(cell).split()).lower()


def parse_ca_xlsx(rows: list[list[str]]) -> list[WarnNotice]:
    """Parse rows from the `'Detailed WARN Report '` sheet of `warn_report1.xlsx`.

    `rows[0]` is the header row; the title banner (workbook row 0 in the
    real file) is the caller's problem to have already skipped by handing
    in the header as `rows[0]`.
    """
    if not rows:
        return []

    header = [_normalise_header(c) for c in rows[0]]

    def col(name: str) -> int | None:
        return header.index(name) if name in header else None

    idx_county = col("county/parish")
    idx_notice = col("notice date")
    idx_effective = col("effective date")
    idx_company = col("company")
    idx_employees = col("no. of employees")

    notices: list[WarnNotice] = []
    for i, row in enumerate(rows[1:], start=2):
        if idx_company is None or idx_notice is None:
            continue

        def cell(idx: int | None) -> str | None:
            if idx is None or idx >= len(row) or row[idx] is None:
                return None
            return str(row[idx])

        employer = cell(idx_company) or ""
        if not employer.strip():
            continue

        notice_date = _truncate_iso_datetime(cell(idx_notice), " ")
        if not notice_date:
            continue
        effective_date = _truncate_iso_datetime(cell(idx_effective), " ")

        raw_emp = cell(idx_employees)
        employees: int | None = None
        if raw_emp not in (None, ""):
            try:
                employees = int(float(raw_emp))
            except ValueError:
                employees = None

        notices.append(WarnNotice(
            state="CA",
            employer=employer,
            notice_date=notice_date,
            effective_date=effective_date,
            employees=employees,
            city=None,  # no dedicated city column; only a free-text address
            county=cell(idx_county),
            source_ref=f"ca-xlsx:row{i}",
        ))
    return notices


def parse_ca_pdf_text(text: str) -> list[WarnNotice]:
    """Parse `pdftotext -layout` output over a CA EDD per-FY WARN PDF report.

    Column order is Notice Date | Received Date | Effective Date | Company |
    County | Employees+Type | Address, separated by runs of 2+ spaces (the
    `-layout` column padding). A line whose first field is not `MM/DD/YYYY`
    is header or page furniture and is discarded.
    """
    notices: list[WarnNotice] = []
    # `str.splitlines()` treats the form-feed page breaks pdftotext inserts
    # between pages as line boundaries too, so its count diverges from what
    # `grep -n` / `sed -n` report on the same text (they split on `\n`
    # only) — verified against this file: 4306 vs 4251 lines on the
    # FY2024-25 report. Split on `\n` explicitly so `source_ref`'s line
    # number is the one a human would actually find with grep -n.
    for lineno, raw_line in enumerate(text.split("\n"), start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = re.split(r"\s{2,}", line)
        if not fields or not _PDF_DATE_RE.match(fields[0]):
            continue
        if len(fields) < 4:
            continue

        notice_date = datetime.strptime(fields[0], "%m/%d/%Y").date().isoformat()

        effective_date = None
        if len(fields) > 2 and _PDF_DATE_RE.match(fields[2]):
            effective_date = datetime.strptime(fields[2], "%m/%d/%Y").date().isoformat()

        # Locate the "<employees> Layoff/Closure ..." field by CONTENT, not a
        # fixed index. When the employer name is long, its rendered width
        # overruns the County column's start x-position and `pdftotext
        # -layout` glues the two together with a single space instead of the
        # column-gap's usual run of spaces — e.g. "...Solution, Riverside
        # County        104 Layoff Permanent" collapses "Solution," and
        # "Riverside" onto the SAME field with no 2+-space gap between them.
        # A fixed fields[4]/fields[5] assumption would then read the
        # employee count from the ADDRESS's leading house number instead —
        # silently wrong, and it corrupted 16 real rows in the FY2024-25
        # report before this scan replaced the fixed index.
        emp_idx = None
        for idx in range(4, len(fields)):
            if _PDF_EMPLOYEES_RE.match(fields[idx]):
                emp_idx = idx
                break

        # A separate County field exists only if something sits strictly
        # between the employer field and the employees field; when they are
        # adjacent (emp_idx == 4) the county text was swallowed into the
        # employer field above and there is nothing honest to recover here.
        county = fields[4] if emp_idx is not None and emp_idx > 4 else None

        employees = None
        if emp_idx is not None:
            m = _PDF_EMPLOYEES_RE.match(fields[emp_idx])
            employees = int(m.group(1).replace(",", ""))

        notices.append(WarnNotice(
            state="CA",
            employer=fields[3],
            notice_date=notice_date,
            effective_date=effective_date,
            employees=employees,
            city=None,  # city sits inside the free-text address field, if present
            county=county,
            source_ref=f"ca-pdf:line{lineno}",
        ))
    return notices
