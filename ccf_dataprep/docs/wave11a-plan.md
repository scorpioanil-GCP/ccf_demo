# Wave 11a — `rating-and-spread-migration` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load a rating-and-spread migration dataset — ~60 engineered debt instruments over ~30 real obligors, with spreads composed from real public market data plus an engineered idiosyncratic component, and a grade history that is a genuine supersession chain in the ledger.

**Architecture:** Spread is composed, not fetched, because per-CUSIP TRACE history is licensed. Two public legs (Treasury par curve, FRED ICE BofA OAS by rating band) carry the market's real movement; one engineered leg carries the instrument-specific level and the deliberate divergence cases. Postgres owns observations and policy; Fluree owns instrument nodes, `issuedBy` edges, and the bitemporal grade assertions.

**Tech Stack:** Python 3.12, `uv`, `psycopg` 3, `requests`, stdlib `csv`/`datetime`. Fluree 4.1.4 over SPARQL. **No pytest.**

**Spec:** `docs/wave11a-design.md`

## Global Constraints

- **No pytest.** Tests are standalone executables: `#!/usr/bin/env python3`, a `main() -> int` printing `  [ok  ] label` / `  [FAIL] label`, a total line, `sys.exit(main())`. Pattern: `validators/test_binding_drift.py`, `validators/test_form4.py`.
- **Provenance per element**, exactly one of `public`, `synthetic — internal`, `synthetic — engineered`.
- **Single-writer discipline.** Fluree holds edges, node types and a display label. Every attribute resolves from Postgres.
- **Instance URIs are `ex:{LocalName}`.** Never construct a URI for a node that has not been loaded; resolve edge targets from loaded nodes.
- **Every script takes `--dry-run` and is idempotent.**
- **Fluree SPARQL requires an explicit `FROM <ledger>`.** Use `fluree.query()` / `fluree.update()`.
- **No OWL inference.** Type every node explicitly for every role queried against.
- Schema `ccf_v2`, ledger `fibo-v2`. **Never write to v1.**
- Instrument identifiers: **`syn-i-<6 hex>`**. Never CUSIP-shaped.
- `sources/**` payloads gitignored; `sources/**/manifest.json` and `sources/screening/*.json` tracked.
- No `__init__.py` anywhere — PEP 420 namespace packages.

## Facts verified against the live artifacts on 2026-08-19

Wave 10's post-mortem found **thirteen** defects in its plan's reference code, and every one was a fact about a live artifact the plan asserted without touching. These were touched. Treat them as reliable:

| Fact | Verified value |
|---|---|
| `SourceManifest` fields | `source`, `description`, `licence`, `fetches` — **there is no `name` field** |
| `fetch()` filename | must be **flat**; it only creates `manifest.directory`, so a `/` in the name raises |
| `Check` signature | `Check(product, condition, floor, actual, note="", errored=False)` |
| `CheckFailure` | exists; raise it when a check cannot execute, so it renders FAIL not SKIP |
| `Result` signature (partition) | `Result(check, store, passed, detail)` |
| Treasury CSV header | **VARIES BY YEAR.** 2024 has **14** columns and no `1.5 Month`; 2025 and 2026 have **15** and include it — Treasury added a 6-week bill benchmark in 2025. **Read the header per file; never hardcode it.** |
| Treasury date format | **`MM/DD/YYYY`** — e.g. `01/02/2025` |
| Treasury blanks | real, but `1.5 Month` is **not** a mostly-empty column — it is absent in 2024 and populated on essentially every row from 2025-02-18. Blanks still occur; the drop-not-zero rule stands |
| Treasury URL | **per calendar year**, so 24 months spans 2024, 2025, 2026 |
| FRED CSV header | `observation_date,<SERIES_ID>` |
| FRED date format | **ISO `YYYY-MM-DD`** |
| FRED series (verified, 794 rows each) | `BAMLC0A2CAA` AA · `BAMLC0A3CA` A · `BAMLC0A4CBBB` BBB · `BAMLH0A1HYBB` BB · `BAMLH0A2HYB` B |
| `financial_fact` columns | `lei, cik, taxonomy, tag, unit, period_start, period_end, fiscal_year, fiscal_period, form, filed_date, accession, value, provenance, source, retrieved_at` |
| Rating-action 8-Ks | **5 anchors, 14 filings** — paged FTS, see design §1.4 |

**⚠️ VERIFY FIRST — not yet touched, do not assume:**

- `issuedBy` — no FIBO binding exists in the contract. **Verify against the EDM Council source before generating**; mint `ex:issuedBy` only if FIBO genuinely lacks it.
- Whether FIBO carries classes for a credit grade or a market observation. Same rule.
- Any table column not listed above.

---

## File Structure

| File | Responsibility |
|---|---|
| `generators/curves.py` | **Pure.** Date parsing for both formats, tenor matching, blank handling |
| `generators/fetch_treasury.py` | Treasury par curve, three calendar years |
| `generators/fetch_market_oas.py` | The five FRED OAS series |
| `generators/fetch_rating_actions.py` | **Paged** EDGAR FTS sweep + fetch |
| `generators/generate_instruments.py` | ~60 instruments, laddered, `syn-i-` ids |
| `generators/generate_spreads.py` | Compose three legs; place divergence and sparsity |
| `generators/generate_grades.py` | Quarterly + off-cycle, as a supersession chain |
| `loaders/load_postgres_wave11a.py` | Six tables |
| `loaders/load_fluree_wave11a.py` | Nodes, `issuedBy`, grade assertions — **`--reconcile` from the start** |
| `validators/series.py` | The divergence, sparsity and market-dominance proofs |
| `validators/test_curves.py` | Pure tests for `curves.py` |

---

### Task 1: Curve pure functions — two date formats, tenor matching, real blanks

**Files:**
- Create: `generators/curves.py`
- Test: `validators/test_curves.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `parse_treasury_date(raw: str) -> date` — `MM/DD/YYYY`
  - `parse_fred_date(raw: str) -> date` — ISO
  - `TENORS: list[tuple[str, float]]` — column label → years
  - `tenor_years(label: str) -> float | None`
  - `interpolate_tenor(curve: dict[float, float], years: float) -> float | None` — linear between bracketing tenors
  - `parse_treasury_row(header: list[str], row: list[str]) -> tuple[date, dict[float, float]]`

- [ ] **Step 1: Write the failing test**

Create `validators/test_curves.py`:

```python
#!/usr/bin/env python3
"""Pure tests for curve parsing and tenor matching.

Two traps are pinned here, both of the shape that has cost this project most.

TWO DATE FORMATS. Treasury renders MM/DD/YYYY, FRED renders ISO YYYY-MM-DD, and
the two are joined on date. Wave 8's amendment resolution compared DD-MON-YYYY
as raw strings and sorted by day-of-month, then month NAME alphabetically — it
was correct only by coincidence of that archive's date distribution. Parse, do
not pattern-match.

TENOR MATCHING, NOT CALENDAR PROXIMITY. §D forbids matching a benchmark point by
whichever tenor is nearest in the file. An instrument with 4.2 years to maturity
is interpolated between the 3-year and 5-year points, never snapped to one.

    uv run validators/test_curves.py
"""

from __future__ import annotations

import sys
from datetime import date

from generators.curves import (interpolate_tenor, parse_fred_date,
                               parse_treasury_date, parse_treasury_row,
                               tenor_years)

HEADER = ["Date", "1 Mo", "1.5 Month", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr",
          "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]
ROW = ["01/02/2025", "4.45", "", "4.36", "4.36", "4.31", "4.25", "4.17",
       "4.25", "4.29", "4.38", "4.47", "4.57", "4.86", "4.79"]


def check_dates() -> list[tuple[str, bool]]:
    return [
        ("treasury MM/DD/YYYY parses",
         parse_treasury_date("01/02/2025") == date(2025, 1, 2)),
        ("treasury month and day are not transposed",
         parse_treasury_date("03/11/2025") == date(2025, 3, 11)),
        ("fred ISO parses", parse_fred_date("2026-08-18") == date(2026, 8, 18)),
        ("the two formats agree on the same day",
         parse_treasury_date("08/18/2026") == parse_fred_date("2026-08-18")),
        ("a treasury date is NOT accepted by the fred parser",
         _raises(parse_fred_date, "08/18/2026")),
        ("a fred date is NOT accepted by the treasury parser",
         _raises(parse_treasury_date, "2026-08-18")),
    ]


def _raises(fn, arg) -> bool:
    try:
        fn(arg)
    except Exception:
        return True
    return False


def check_tenors() -> list[tuple[str, bool]]:
    return [
        ("1 Mo is one twelfth of a year", abs(tenor_years("1 Mo") - 1 / 12) < 1e-9),
        ("1.5 Month parses as a month label", tenor_years("1.5 Month") is not None),
        ("10 Yr is ten years", tenor_years("10 Yr") == 10.0),
        ("an unknown label yields None", tenor_years("banana") is None),
    ]


def check_row() -> list[tuple[str, bool]]:
    d, curve = parse_treasury_row(HEADER, ROW)
    return [
        ("row date parses", d == date(2025, 1, 2)),
        ("the blank 1.5 Month cell is DROPPED, not zero",
         not any(abs(k - 0.125) < 1e-6 for k in curve)),
        ("a blank never becomes 0.0", 0.0 not in curve.values()),
        ("populated tenors survive", abs(curve[10.0] - 4.57) < 1e-9),
        ("all populated cells are present", len(curve) == 13),
    ]


def check_interpolation() -> list[tuple[str, bool]]:
    curve = {3.0: 4.29, 5.0: 4.38, 10.0: 4.57}
    mid = interpolate_tenor(curve, 4.0)
    off = interpolate_tenor(curve, 4.2)
    return [
        ("an exact tenor returns its own point",
         interpolate_tenor(curve, 5.0) == 4.38),
        ("a midpoint interpolates linearly", abs(mid - 4.335) < 1e-9),
        ("4.2y sits between the 3y and 5y points, not snapped to either",
         off is not None and 4.29 < off < 4.38 and off != 4.29 and off != 4.38),
        ("4.2y is NOT the nearest tenor's value — proximity is forbidden",
         abs(off - 4.38) > 1e-9),
        ("beyond the longest tenor yields None rather than extrapolating",
         interpolate_tenor(curve, 40.0) is None),
        ("below the shortest tenor yields None",
         interpolate_tenor(curve, 0.5) is None),
    ]


def main() -> int:
    cases = check_dates() + check_tenors() + check_row() + check_interpolation()
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_curves.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.curves'`

- [ ] **Step 3: Write minimal implementation**

Create `generators/curves.py`:

```python
#!/usr/bin/env python3
"""Pure curve helpers — date parsing, tenor labels, interpolation. No I/O.

Treasury and FRED publish the same kind of daily series in DIFFERENT date
formats, and this wave joins them on date. `MM/DD/YYYY` against ISO
`YYYY-MM-DD`. Both parsers are strict: handed the other's format they raise,
rather than silently producing a plausible wrong date.

Tenor matching is interpolation between bracketing points, never a snap to the
nearest column. §D forbids calendar proximity explicitly, and an instrument at
4.2 years matched to the 5-year point would produce a spread that is wrong by
the shape of the curve rather than by a visible error.
"""

from __future__ import annotations

from datetime import date, datetime

#: Treasury column label -> tenor in years. `1.5 Month` is published but almost
#: always blank; it is parsed anyway so a populated cell is not silently lost.
TENORS: list[tuple[str, float]] = [
    ("1 Mo", 1 / 12), ("1.5 Month", 1.5 / 12), ("2 Mo", 2 / 12),
    ("3 Mo", 3 / 12), ("4 Mo", 4 / 12), ("6 Mo", 6 / 12),
    ("1 Yr", 1.0), ("2 Yr", 2.0), ("3 Yr", 3.0), ("5 Yr", 5.0),
    ("7 Yr", 7.0), ("10 Yr", 10.0), ("20 Yr", 20.0), ("30 Yr", 30.0),
]
_BY_LABEL = dict(TENORS)


def parse_treasury_date(raw: str) -> date:
    """`MM/DD/YYYY`. Strict — an ISO date raises rather than being coerced."""
    return datetime.strptime(raw.strip(), "%m/%d/%Y").date()


def parse_fred_date(raw: str) -> date:
    """ISO `YYYY-MM-DD`. Strict — a Treasury date raises."""
    return datetime.strptime(raw.strip(), "%Y-%m-%d").date()


def tenor_years(label: str) -> float | None:
    return _BY_LABEL.get(label.strip())


def parse_treasury_row(header: list[str], row: list[str]) -> tuple[date, dict[float, float]]:
    """One Treasury row -> (date, {tenor_years: par_yield}).

    A blank cell is DROPPED, never defaulted to zero. A zero yield is a
    meaningful value and a missing one is not; conflating them would put a
    fictional 0% point on the curve and silently distort every spread
    interpolated across it.
    """
    d = parse_treasury_date(row[0])
    curve: dict[float, float] = {}
    # strict=True turns a header/row length mismatch into a loud ValueError.
    # Plain zip() truncates to the shorter sequence, which would file every
    # subsequent yield under the WRONG tenor with no error raised — the same
    # silent-and-plausible failure this module's date parsers refuse to make.
    for label, cell in zip(header[1:], row[1:], strict=True):
        years = tenor_years(label)
        text = (cell or "").strip()
        if years is None or not text:
            continue
        curve[years] = float(text)
    return d, curve


def interpolate_tenor(curve: dict[float, float], years: float) -> float | None:
    """Linear interpolation between the two bracketing tenors.

    Returns None outside the curve's range rather than extrapolating — an
    invented point beyond 30 years is not a benchmark, and a caller that gets
    None can record the gap instead of carrying a fabricated number forward.
    """
    if not curve:
        return None
    if years in curve:
        return curve[years]
    lower = [t for t in curve if t < years]
    upper = [t for t in curve if t > years]
    if not lower or not upper:
        return None
    lo, hi = max(lower), min(upper)
    span = hi - lo
    if span == 0:
        return curve[lo]
    weight = (years - lo) / span
    return curve[lo] + weight * (curve[hi] - curve[lo])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_curves.py`
Expected: PASS — `21/21 cases behave as specified`

- [ ] **Step 5: Commit**

```bash
git add generators/curves.py validators/test_curves.py
git commit -m "Wave 11a: curve helpers, with both date formats pinned by test"
```

---

### Task 2: Fetch the two public market series

**Files:**
- Create: `generators/fetch_treasury.py`
- Create: `generators/fetch_market_oas.py`
- Output: `sources/treasury/**`, `sources/fred/**` (payloads gitignored, manifests tracked), `sources/screening/wave11a_curve.json`, `sources/screening/wave11a_oas.json`

**Interfaces:**
- Consumes: `curves.parse_treasury_row`, `curves.parse_fred_date`, `ccf.fetch.fetch`, `ccf.fetch.SourceManifest`.
- Produces:
  - `wave11a_curve.json` — `{"generated_at", "source", "provenance": "public", "curve": [{"date": "YYYY-MM-DD", "tenors": {"0.0833": 4.45, ...}}]}`
  - `wave11a_oas.json` — `{"generated_at", "series": {"BBB": {"fred_id": "BAMLC0A4CBBB", "unit": "basis_points", "points": [{"date", "oas_bp"}]}}}`. **The field is `oas_bp`, not `oas_pct`** — FRED serves percent and the fetch converts once, so what lands on disk is already basis points and the `unit` key says so.

- [ ] **Step 1: Write `generators/fetch_treasury.py`**

```python
#!/usr/bin/env python3
"""Treasury par yield curve — the benchmark leg, and it is genuinely public.

The URL is PER CALENDAR YEAR, so 24 months of history spans three files.
Dates render MM/DD/YYYY, unlike FRED's ISO; `curves.py` parses both strictly
so neither can be silently coerced into the other.

Blank cells are real — `1.5 Month` is published and almost always empty — and
are dropped rather than defaulted, because a 0% benchmark point would distort
every spread interpolated across it.

    uv run generators/fetch_treasury.py --dry-run
    uv run generators/fetch_treasury.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch
from generators.curves import parse_treasury_row

SCREEN = REPO_ROOT / "sources" / "screening"
YEARS = [2024, 2025, 2026]
URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
       "daily-treasury-rates.csv/{year}/all"
       "?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = SourceManifest(
        source="treasury",
        description="US Treasury daily par yield curve — benchmark leg for spreads",
        licence="US Government work, public domain",
    )

    rows: list[dict] = []
    for year in YEARS:
        url = URL.format(year=year)
        if args.dry_run:
            print(f"  [plan] {url}")
            continue
        path = fetch(url, manifest, f"treasury-{year}.csv")
        text = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(text.splitlines())
        header = next(reader)
        n = 0
        for raw in reader:
            if not raw or not raw[0].strip():
                continue
            d, curve = parse_treasury_row(header, raw)
            rows.append({"date": d.isoformat(),
                         "tenors": {f"{k:.6f}": v for k, v in sorted(curve.items())}})
            n += 1
        print(f"  {year}: {n} curve dates")

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    rows.sort(key=lambda r: r["date"])
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "US Treasury daily par yield curve",
        "provenance": "public",
        "curve": rows,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11a_curve.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  {len(rows)} curve dates, {rows[0]['date']} -> {rows[-1]['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write `generators/fetch_market_oas.py`**

```python
#!/usr/bin/env python3
"""FRED ICE BofA OAS by rating band — the public market factor.

Five series, verified 2026-08-19 at 794 daily rows each. On 2026-08-18 they
read AA 0.60 < A 0.69 < BBB 1.00 < BB 1.63 < B 2.94 — a real credit curve,
monotonic by rating, which is the entire reason this leg is worth fetching
rather than inventing.

Values are PERCENT, not basis points: BBB reads 1.00 meaning 100bp. Converted
once, here, with the unit recorded in the payload so a later reader cannot
re-convert.

Dates are ISO, unlike Treasury's MM/DD/YYYY. `curves.py` parses both strictly.

    uv run generators/fetch_market_oas.py --dry-run
    uv run generators/fetch_market_oas.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch
from generators.curves import parse_fred_date

SCREEN = REPO_ROOT / "sources" / "screening"

#: AAA is deliberately absent — this cast is mid-market and leveraged, and no
#: anchor in it would price at AAA. BAMLC0A1CAAAEY exists and works but is the
#: effective-YIELD variant, not OAS; mixing the two is a units error.
SERIES = {
    "AA":  "BAMLC0A2CAA",
    "A":   "BAMLC0A3CA",
    "BBB": "BAMLC0A4CBBB",
    "BB":  "BAMLH0A1HYBB",
    "B":   "BAMLH0A2HYB",
}
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest = SourceManifest(
        source="fred",
        description="ICE BofA US corporate OAS by rating band — market factor",
        licence="FRED/St. Louis Fed redistribution terms; ICE BofA index data",
    )

    out: dict[str, dict] = {}
    for band, sid in SERIES.items():
        url = URL.format(sid=sid)
        if args.dry_run:
            print(f"  [plan] {band:<4} {url}")
            continue
        path = fetch(url, manifest, f"{sid}.csv")
        reader = csv.reader(path.read_text(encoding="utf-8").splitlines())
        header = next(reader)
        if header[1].strip() != sid:
            raise RuntimeError(
                f"{sid}: expected column {sid!r}, got {header[1]!r} — FRED "
                "changed the CSV shape; do not guess, look at the file")
        points = []
        for row in reader:
            if len(row) < 2 or not row[1].strip() or row[1].strip() == ".":
                continue          # FRED renders a missing observation as "."
            points.append({"date": parse_fred_date(row[0]).isoformat(),
                           "oas_bp": round(float(row[1]) * 100, 2)})
        out[band] = {"fred_id": sid, "unit": "basis_points", "points": points}
        print(f"  {band:<4} {sid:<14} {len(points):>4} points  "
              f"{points[0]['date']} -> {points[-1]['date']}")

    if args.dry_run:
        print("  [dry-run] nothing fetched or written")
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "FRED — ICE BofA US corporate index OAS",
        "provenance": "public",
        "series": out,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11a_oas.json").write_text(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Note the two defensive details, both earned. The header check raises rather than
guessing if FRED changes the CSV shape — Wave 10 shipped a wrong column name
masked by `dict.get()` that silently emptied a field on every row. And `"."` is
FRED's missing-observation marker, which `float()` would otherwise turn into a
crash mid-run.

**AAA is deliberately absent.** This cast is mid-market and leveraged; no anchor in it would price at AAA. `BAMLC0A1CAAAEY` exists and works but is the effective-**yield** variant, not OAS — mixing the two is a units error.

- [ ] **Step 3: Dry-run both, then run**

```bash
uv run generators/fetch_treasury.py --dry-run && uv run generators/fetch_treasury.py
uv run generators/fetch_market_oas.py --dry-run && uv run generators/fetch_market_oas.py
```

Expected: ~750 curve dates across three years; five series at ~794 rows each. **Report the actual date ranges** — if the curve does not cover the full 24-month window the spread series needs, say so now rather than discovering it in Task 6.

- [ ] **Step 4: Commit**

```bash
git add generators/fetch_treasury.py generators/fetch_market_oas.py \
        sources/treasury/manifest.json sources/fred/manifest.json \
        sources/screening/wave11a_curve.json sources/screening/wave11a_oas.json
git commit -m "Wave 11a: fetch the Treasury curve and the five FRED OAS series"
```

---

### Task 3: Paged rating-action sweep and Item 2.03 issuance events

**Files:**
- Create: `generators/fetch_rating_actions.py`
- Output: `sources/screening/wave11a_rating_actions.json`, `sources/screening/wave11a_issuance.json`

**Interfaces:**
- Consumes: `ccf.fetch.get_json`, `ccf_v2.crosswalk`, `ccf_v2.legal_entity`.
- Produces: `wave11a_rating_actions.json` — `[{"lei", "cik", "accession", "file_date", "matched_query", "provenance": "public"}]`; `wave11a_issuance.json` — Item 2.03 filings per anchor.

- [ ] **Step 1: The sweep MUST page — this is the task's whole lesson**

A first-page-only sweep of EDGAR full-text search found **1** anchor with a rating-action 8-K. The identical sweep **with paging** found **5, across 14 filings**. The difference was pagination, not data. A probe that stops at page one returns a confident wrong number.

Use `generators/screen_obligors.py::fts_pages` — it already exists, already pages, and already handles the `from` offset:

```python
from generators.screen_obligors import fts_pages

QUERIES = [
    '"Moody\'s Investors Service"',
    '"Standard & Poor\'s" "credit rating"',
    '"corporate credit rating"',
    '"S&P Global Ratings"',
    '"Fitch Ratings"',
]
```

Filter hits to `src["ciks"]` intersecting our 50. Record which query matched, so a later reader can see why a filing was selected.

**Expected: ≥ 5 anchors.** AVIS BUDGET GROUP (5 filings), INDEPENDENCE REALTY TRUST (5), Peakstone Realty Trust (2), Vertiv Holdings (1), GRIFFON CORP (1). If you find fewer than 5, the paging is wrong — investigate rather than accepting it.

**A hit is a candidate, not a confirmed rating action.** The query matches an
agency's *name* appearing in an 8-K; the filing might be disclosing a downgrade,
an affirmation, a new facility rated by that agency, or merely naming the agency
in a defined term. Confirming which requires reading prose.

So: fetch each matched filing and search it for action language near the agency
name. A candidate that **cannot** be confirmed is written to `ccf_v2.context_debt`
with `subject_kind='rating_action'` and the accession as `subject_key` — recorded
as a gap, never forced into the dataset as a confirmed action. Wave 10 widened
`context_debt` with `subject_kind` / `subject_key` for exactly this pattern, and
§F condition 6 needs only ≥ 1 confirmed, against 14 candidates.

Verified schema (2026-08-19): `context_debt` is `debt_id, accession, covenant_type, reason, recorded_at, subject_kind, subject_key`. `accession` is **nullable** (Wave 10 widened it) but **`reason` is NOT NULL** — supply one.

- [ ] **Step 2: Item 2.03 issuance is free — reuse the metadata trick**

The submissions index carries an `items` field per filing, so Item 2.03 selection needs no document parsing at all. `generators/fetch_8k502.py` from Wave 10 is the working pattern; the only change is `"2.03" in (items or "")`.

All 50 anchors have at least one. Record accession, filing date, and the items string.

- [ ] **Step 3: Run and report**

```bash
uv run generators/fetch_rating_actions.py --dry-run
uv run generators/fetch_rating_actions.py
```

Report anchors with a rating action, filings per anchor, and total Item 2.03 filings.

- [ ] **Step 4: Commit**

---

### Task 4: Generate the instrument set

**Files:**
- Create: `generators/generate_instruments.py`
- Output: `sources/screening/wave11a_instruments.json`

**Interfaces:**
- Consumes: `ccf_v2.financial_fact` (`LongTermDebt`), `ccf_v2.filing_profile`, `wave11a_issuance.json`, `wave11a_rating_actions.json`.
- Produces: `[{"instrument_id": "syn-i-a1b2c3", "lei", "coupon_pct", "maturity", "issue_date", "face_amount_usd", "rating_band", "seniority", "provenance": "synthetic — engineered"}]`

- [ ] **Step 1: Obligor selection is deterministic and public**

The **30 largest by most-recent reported `LongTermDebt`** in `financial_fact`, restricted to obligors with ≥ 1 Item 2.03 filing. Ties broken by LEI ascending.

**Force-include the 5 rating-action anchors regardless of rank.** §F condition 6 wants ≥ 1 obligor with a rating action in a real 8-K, and letting it depend on a debt ranking means a data refresh could silently drop the condition. Force-inclusion makes it structural.

- [ ] **Step 2: Instruments**

~60 across the 30 obligors — two each, laddered so maturities spread across the window rather than clustering. Issue dates anchored to a **real Item 2.03 filing date** for that obligor where one exists; that is what makes the issuance events public even though the instrument is engineered.

Identifiers are **`syn-i-<6 hex>`**, deterministic from `(lei, sequence)` so re-runs are stable. Never CUSIP-shaped.

Rating band per obligor from a deterministic rule over reported leverage — it selects which real FRED series drives that instrument's market factor, so it must be recorded, not implied.

- [ ] **Step 3: Seed determinism**

Fixed `SEED`, no wall-clock reads except the `generated_at` provenance field, and **`ORDER BY` on every `SELECT` whose row order reaches the RNG**. Wave 10 shipped an unordered `deal` query whose order fed `rng.choice`; the seed guaranteed the same *index*, not the same *deal*.

- [ ] **Step 4: Run, verify counts, commit**

---

### Task 5: Compose the spread series

**Files:**
- Create: `generators/generate_spreads.py`
- Test: extend `validators/test_curves.py` with the composition cases
- Output: `sources/screening/wave11a_spreads.json`

**Interfaces:**
- Consumes: `wave11a_curve.json`, `wave11a_oas.json`, `wave11a_instruments.json`, `curves.interpolate_tenor`.
- Produces: `[{"instrument_id", "obs_date", "benchmark_bp", "market_oas_bp", "idiosyncratic_bp", "spread_bp", "yield_bp"}]`

- [ ] **Step 1: The composition**

```
benchmark_bp     = interpolate_tenor(curve[d], years_to_maturity) * 100   [public]
market_oas_bp    = oas[in_force_band(d)][d]                              [public, already bp -- do NOT * 100; superseded by docs/wave11a-migration-transition-design.md, which also steps the band at asserted_at instead of pinning it]
idiosyncratic_bp = engineered per instrument, per date                   [engineered]
spread_bp        = market_oas_bp + idiosyncratic_bp
yield_bp         = benchmark_bp + spread_bp
```

**Tenor is computed per observation date**, because an instrument's years-to-maturity shrinks as the window advances. Matching against a fixed tenor would be the calendar-proximity error §D forbids, arriving by a different route.

Where `interpolate_tenor` returns `None` — outside the curve's range — **record no observation**. Do not carry the previous day forward and do not extrapolate.

- [ ] **Step 2: The two conditions counting cannot fake**

**≥ 3 divergence cases, ≥ 1 confirmed later.** A divergence is a window where `idiosyncratic_bp` widens materially while the obligor's grade does not move. The generator places them; `validators/series.py` must **recompute them from the loaded series** rather than reading a flag.

**≥ 2 thinly-traded instruments with observation gaps.** Genuine missing dates, not interpolated values. A validator counting observations would pass a fully interpolated series, so the check must assert dates are *absent*.

- [ ] **Step 3: Market dominance is measurable, not asserted**

Outside divergence windows, median `|idiosyncratic_bp|` must be **≤ 40% of median `market_oas_bp`**. Inside a window it may exceed that — widening it *is* how a divergence is made — so the check excludes those windows **by date** rather than being relaxed.

Report the actual ratio. If the engineered component dominates, the public index has become decoration and the product's central claim rests on invented data.

- [ ] **Step 4: Extend `validators/test_curves.py` with the composition cases**

These are pure — they take a hand-built series, not the loaded data:

```python
from generators.generate_spreads import compose_observation, dominance_ratio

def check_composition() -> list[tuple[str, bool]]:
    obs = compose_observation(benchmark_bp=430.0, market_oas_bp=163.0,
                              idiosyncratic_bp=45.0)
    return [
        ("spread is market plus idiosyncratic, not including benchmark",
         obs["spread_bp"] == 208.0),
        ("yield is benchmark plus spread", obs["yield_bp"] == 638.0),
        ("the two components stay separately addressable",
         obs["market_oas_bp"] == 163.0 and obs["idiosyncratic_bp"] == 45.0),
        ("a None benchmark yields no observation at all, never a zero",
         compose_observation(benchmark_bp=None, market_oas_bp=163.0,
                             idiosyncratic_bp=45.0) is None),
    ]

def check_dominance() -> list[tuple[str, bool]]:
    calm = [{"market_oas_bp": 160.0, "idiosyncratic_bp": 40.0}] * 10
    swamped = [{"market_oas_bp": 160.0, "idiosyncratic_bp": 200.0}] * 10
    return [
        ("a calm series passes the 40% dominance rule",
         dominance_ratio(calm) <= 0.40),
        ("a swamped series FAILS it — the check can go red",
         dominance_ratio(swamped) > 0.40),
        ("the ratio is median-based, so one outlier cannot flip it",
         dominance_ratio(calm + [{"market_oas_bp": 160.0,
                                  "idiosyncratic_bp": 900.0}]) <= 0.40),
    ]
```

The second dominance case matters more than the first: it is the one proving the
check **can fail**. A rule that only ever sees passing data is not a rule.

- [ ] **Step 5: Run, verify, commit**

Run: `uv run validators/test_curves.py`
Expected: PASS — `28/28 cases behave as specified` (21 from Task 1 + 7 here)

---

### Task 6: Generate the grade history as a supersession chain

**Files:**
- Create: `generators/generate_grades.py`
- Output: `sources/screening/wave11a_grades.json`

**Interfaces:**
- Consumes: `wave11a_instruments.json` (for the obligor set), `wave11a_spreads.json` (to place the confirming rerating).
- Produces: `[{"assertion_id", "lei", "grade", "notch", "valid_from", "valid_to", "asserted_at", "supersedes", "trigger", "provenance": "synthetic — internal"}]`

- [ ] **Step 1: The shape §D demands**

§D step 3: *"the migration IS the supersession chain, which is why this product needs a ledger rather than a current-state table."*

So a grade is never overwritten. Each rerating writes a **new assertion** carrying `supersedes` pointing at the one it replaces, and the superseded assertion keeps its `valid_to`. Reading the chain backwards reconstructs the migration.

Reuse Wave 5's vocabulary — it exists and is partly populated: `ex:validFrom` (223 assertions), `ex:assertedAt` (29), `ex:supersededBy` (**0 — declared, never populated**). This wave populates it, the same way Wave 10's follow-up populated `fibo-fnd-rel-rel:controls` after it had sat declared-and-empty since Wave 8.

- [ ] **Step 2: Cadence**

Quarterly per obligor across 24 months (8 regular points), plus **≥ 4 off-cycle reratings** so the series is not mechanically regular. Off-cycle assertions carry a `trigger` naming why.

**A grade is a step function.** Exact `valid_from` dates, no smoothing, no intermediate states. §D step 5's *"resample, do not interpolate across a rating action"* is an assembly rule, but it is only satisfiable if the data carries exact effective dates.

- [ ] **Step 3: The confirming rerating**

§F wants **≥ 1 divergence where the grade later moved to confirm the market** — the design calls it the product's most persuasive single output. So at least one off-cycle rerating must land *after* a divergence window opened, moving in the direction the spread already indicated. This requires reading `wave11a_spreads.json`, which is why this task runs after Task 5.

- [ ] **Step 4: Run, verify, commit**

Report: assertions per obligor, off-cycle count, supersession chain depth, and which obligor carries the confirming rerating.

---

### Task 7: Load Postgres

**Files:**
- Create: `loaders/load_postgres_wave11a.py`

**Interfaces:**
- Consumes: all five `wave11a_*.json` artifacts.
- Produces: six tables. Later tasks read `ccf_v2.debt_instrument`, `spread_observation`, `benchmark_curve`, `market_oas_series`, `rating_scale`, `divergence_threshold`.

- [ ] **Step 1: DDL**

Six tables per design §3.1. Every insert an upsert on a natural key. Note explicitly:

- `spread_observation` keeps `market_oas_bp` and `idiosyncratic_bp` in **separate columns**. That is the mechanism by which public and engineered stay separable by query — a consumer can always ask what was observed and what was built.
- `rating_scale` and `divergence_threshold` carry `policy_version`. §D step 2: a recalibration changes every notch-equivalent figure the product has ever produced, so lineage must record which mapping applied.
- `market_oas_series` records the **FRED series id** per row, not just the band. The band is our label; the series id is the provenance.

- [ ] **Step 2: Three trap shapes this project has hit repeatedly**

1. **A partial `ON CONFLICT ... DO UPDATE SET`** that refreshes some columns and leaves others stale. Wave 10 shipped one on `interaction`; it updated `need_to_know` and `channel` and left `deal_id` stale after a regeneration, and every count still reconciled. Either set every non-key column or delete-and-insert.
2. **A `NOT NULL` on an inherited table** that the new insert path violates. Wave 10 hit this on `context_debt.accession`.
3. **A column name that does not exist**, masked by `dict.get()` returning a default. The highest-risk shape in a loader — a wrong key silently writes NULL across every row.

- [ ] **Step 3: Dry-run, load, load again for idempotency**

Second run must change no row counts. Report both.

- [ ] **Step 4: Confirm nothing else moved**

```bash
uv run validators/artifact_reproduces_store.py
```

Extend it to the new artifacts in Task 9; for now confirm the Wave 10 checks still hold at 20/22.

- [ ] **Step 5: Commit**

---

### Task 8: Load Fluree

**Files:**
- Create: `loaders/load_fluree_wave11a.py`

**Interfaces:**
- Consumes: `ccf_v2.debt_instrument`, `ccf_v2` grade assertions; `loaders.load_collateral_wave9.entity_uri_by_lei`.
- Produces: instrument nodes, `issuedBy` edges, grade assertions with supersession, issuance and rating-action events.

- [ ] **Step 1: ⚠️ VERIFY THE BINDINGS FIRST — before writing any triple**

`issuedBy` has **no FIBO binding in the contract**. Neither does a credit-grade or market-observation class. Per CLAUDE.md, verify against the EDM Council source, add to `docs/ccf_dataprep_v2.md` **before** generating, and mint `ex:` only where FIBO genuinely lacks a term.

`generators/verify_fibo_terms.py` exists from Wave 8 and is the tool for this. Report which terms resolved to real FIBO IRIs and which became extensions.

**Already bound, no action needed:** `fibo-fbc-fi-fi:DebtInstrument`, `fibo-sec-dbt-bnd:Bond` / `CorporateBond` / `FloatingRateNote`, `fibo-sec-dbt-dbti:isSubordinated` / `isSubordinatedTo`.

- [ ] **Step 2: `--reconcile` from the start**

`load_fluree_wave10.py --reconcile` exists and is the pattern: retract every edge on the predicates this loader solely authors, then rebuild. Wave 10 needed a separate one-off remediation script because the loader was INSERT-only and the ledger is append-only, so a re-load against changed Postgres appended *beside* the stale edges. Build it in now rather than discovering it.

Nodes stay out of scope for `--reconcile`, as in Wave 10 — edge lifecycle and node lifecycle are different problems.

- [ ] **Step 3: Resolve, never construct**

Every edge target comes from `entity_uri_by_lei()` or a node created in this run. `dangling` must be **0**. Wave 9's fifteen phantom borrowers were syntactically valid triples pointing at nodes with zero content.

- [ ] **Step 4: Dry-run, load, re-run, run `partition.py`**

Report ledger `t` and triple count before and after, `dangling`, node counts by type, edge counts by predicate.

- [ ] **Step 5: Commit**

---

### Task 9: Validators

**Files:**
- Create: `validators/series.py`
- Modify: `validators/conditions.py`, `validators/partition.py`, `validators/artifact_reproduces_store.py`

- [ ] **Step 1: `validators/series.py` — the three proofs counting would fake**

Modelled on `validators/traversal.py`, which was split out in Wave 10 for exactly this reason.

1. **Divergence** — recompute from the loaded series: windows where the spread widened materially while the grade did not move. Assert ≥ 3, and ≥ 1 where a later rerating moved in the direction the spread indicated. **Do not read a generator flag.**
2. **Sparsity** — assert observation dates are genuinely *absent* for ≥ 2 instruments. A count-based check passes a fully interpolated series.
3. **Market dominance** — median `|idiosyncratic_bp|` ≤ 40% of median `market_oas_bp`, **excluding divergence windows by date**.

- [ ] **Step 2: `conditions.py` — seven §F checks**

Add a `rating-and-spread-migration` section. Delegate #5 and #7 to `series.py` rather than reimplementing. Raise `CheckFailure` when a check cannot execute — `Check.errored` renders FAIL, not SKIP, and Wave 10's fix pass added that distinction precisely so an outage cannot silently downgrade a flagship condition.

- [ ] **Step 3: For every check, state what would make it fail**

Before reporting, write the counterfactual for each: what data turns this red? A check with no answer is not a check. This plan's own predecessor shipped `"CEODana" not in text.replace(" ", "") or True` — an assertion that could not fail, added to silence a genuine failure.

- [ ] **Step 4: `partition.py` and `artifact_reproduces_store.py`**

Register any new `ex:` types. Add the new artifacts to the reproduce-store check — it found a real divergence on its first run in Wave 10, and every new artifact belongs in it.

- [ ] **Step 5: Full suite**

```bash
uv run validators/partition.py conditions.py series.py traversal.py \
       projection.py bitemporal.py cast_audit.py artifact_reproduces_store.py
```

**`conditions.py` reached 72 passed / 0 failed on 2026-08-19 — the estate's first fully green run.** A new red check now means a real regression. Do not let it go red and call it expected.

- [ ] **Step 6: Commit**

---

### Task 10: Docs, published claims, and the vault

**Files:**
- Modify: `docs/ccf_dataprep_v2.md`, `docs/known-issues.md`, `docs/HANDOFF.md`, `docs/data-acquisition-plan.md`, `sources/screening/published_claims.json`
- Create: an outbox message

- [ ] **Step 1: The TRACE finding is the headline**

`docs/known-issues.md` gets a numbered entry recording that §C names FINRA TRACE for per-instrument prices and yields, and that bond-level history is a licensed product. Include the evidence: every free-API group root 404s; the one endpoint returning data is equity ATS volume; and `companyfacts` flattens away the dimensional context that would let XBRL substitute.

Record the three-leg model as the sanctioned substitute, and be precise that the market factor is `public` while the instrument-specific level is `synthetic — engineered`.

- [ ] **Step 2: The pagination lesson**

Record it. A first-page EDGAR FTS sweep found 1 anchor with a rating-action 8-K; the same sweep paged found 5 across 14 filings. A probe that stops at page one returns a confident wrong number, and this one would have committed the spec to a zero-margin condition.

- [ ] **Step 3: The vault**

Read section 5 of `obsidian-vault-access` before the first send. Build `~/.agent-exchange/ccf-dataprep/outbox/<YYYY-MM-DDTHH-MM-SSZ>-wave11a-drift.tmp/`, then **rename to drop `.tmp`** — the rename publishes it.

Batch three things:
- the **TRACE spec finding** — §C already carries exactly the right reasoning for licensed data, applied to agency ratings; it needs the same treatment for TRACE;
- any new `ex:` terms minted in Task 8, and the debt-instrument terms moving to materialized;
- `ex:supersededBy` moving from declared-and-empty to populated.

State plainly that the submission **adds and removes nothing**.

- [ ] **Step 4: Commit**

---

## Appendix: facts an implementer will otherwise rediscover the hard way

1. **Treasury dates are `MM/DD/YYYY`; FRED dates are ISO.** They are joined on date. Parse both strictly.
2. **Treasury blanks are real.** `1.5 Month` is usually empty. Dropping is correct; defaulting to 0.0 puts a fictional point on the curve.
3. **The Treasury URL is per calendar year.** 24 months spans three files.
4. **FRED values are percent, not basis points.** BBB reads `1.00` for 100bp. Convert once, at load, and record the unit.
5. **`SourceManifest` has no `name` field** — `source`, `description`, `licence`.
6. **A `/` in a `fetch()` filename raises.** It only creates `manifest.directory`.
7. **EDGAR FTS must be paged.** One page found 1 anchor; paging found 5.
8. **Item 2.03 selection is free** via the submissions `items` field. Never parse a document to decide relevance.
9. **`companyfacts` drops dimensional context**, so debt-instrument facts cannot be attributed to instruments.
10. **Fluree needs an explicit `FROM <ledger>`** or returns HTTP 500.
11. **Fluree is append-only.** Build `--reconcile` into the loader from the start.
12. **`conditions.py` is at 72/0.** Green is now the baseline, not an aspiration.
