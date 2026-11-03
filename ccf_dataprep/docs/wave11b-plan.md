# Wave 11b Implementation Plan — `credit-surveillance-early-warning`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load the `credit-risk.early-warning.v1` data product across Postgres and Fluree so that every §F condition — including the scripted cascade and the composite case — is satisfiable by a real query against loaded data.

**Architecture:** Three public fetchers (8-K items, state WARN notices, GDELT adverse media) plus two derivations from already-loaded data (XBRL trend deltas, Wave 11a spread signals) feed a single unified `signal_event` ledger in Postgres. Fluree holds the event assertions, the `signalAbout`/`triggeredBy` edges, and one prior observation ledger point per obligor. Two conditions that public data cannot supply — the scripted cascade and the composite case — are manufactured in a dedicated narrative module and labelled `synthetic — engineered`.

**Tech Stack:** Python 3.12 · `uv` · psycopg 3 · Fluree 4.1.4 (SPARQL, explicit `FROM <ledger>`) · `requests` · `openpyxl` (new) · `pdftotext` from poppler-utils (system binary, new)

**Spec:** `docs/wave11b-design.md` — read it before Task 1. The plan argues from the spec; the spec carries the measured feasibility numbers and the four recorded user decisions.

## Global Constraints

Copied verbatim from CLAUDE.md and `docs/wave11b-design.md`. Every task's requirements implicitly include this section.

- **Window is 24 months**, ending at the census end date `2026-08-19`, starting `2024-08-19`. Not §F's 18 months. Decision D1.
- **Load everything** — no sub-selection to §F's ~400 signal events. Decision D3. The distribution condition is *measured* in Task 12, never assumed.
- **Three provenance classes, labelled per element**: `public`, `synthetic — internal`, `synthetic — engineered`. Never two.
- **Single-writer discipline.** One store is authoritative per element. Never duplicate an attribute across stores "for convenience."
- **Do not assume OWL inference.** Fluree runs without reasoning. Type entities explicitly for every role you query against.
- **Fluree 4.1.4 SPARQL requires an explicit `FROM <ledger>`** — omitting it returns HTTP 500, not 400. `ccf/fluree.py` guards this.
- **Fluree is append-only.** A correction is a retraction plus a new assertion; both stay in history.
- **Instance URIs stay under `http://example.org/fibo/`** (`EX` in `ccf/config.py`). Real LEIs live in the `lei` attribute, never in the URI.
- **Every loader is `--dry-run` capable and idempotent.** You will reload many times.
- **Every `ON CONFLICT ... DO UPDATE SET` sets EVERY non-key column**, or the table is delete-then-insert. No column is left to go stale silently.
- **Baseline that must not regress:** `partition.py` 13/13 · `conditions.py` 82 passed / 0 failed · `series.py` PASS · 9 test files / 169 cases green. There is no standing exception; any red is a regression.
- **`sources/` is gitignored** except `sources/screening/*.json`. Generator artifacts go to `sources/screening/`.
- **Never enumerate MongoDB databases.** The Mongo host also carries `rtdetect` (~5.5M docs). This wave touches no Mongo, but the rule stands.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/ccf_dataprep_v2.md` | **modify** — binding table gains the Wave 11b `ex:` extension register |
| `sources/screening/published_claims.json` | **modify** — new terms appended so the next punch list generates itself |
| `generators/fetch_8k_items.py` | Fetch 6 8-K item types from the EDGAR submissions index, sharded history |
| `generators/warn_sources.py` | Pure parsers: TX Socrata JSON, CA XLSX, CA PDF text. No I/O |
| `generators/fetch_warn.py` | I/O driver for the WARN sources; writes one artifact |
| `generators/warn_match.py` | Pure name-matching logic: normalise, score, classify. No I/O |
| `generators/fetch_gdelt.py` | Throttled, resumable GDELT DOC API sweep |
| `generators/generate_trend_deltas.py` | XBRL period-over-period deltas from loaded `financial_fact` |
| `generators/generate_signals.py` | Unify all sources into one signal ledger; weights; thresholds |
| `generators/narrative_wave11b.py` | The two engineered conditions. Shared by generator and validator |
| `loaders/load_postgres_wave11b.py` | 7 new Postgres tables |
| `loaders/load_fluree_wave11b.py` | Event assertions, edges, prior observation points |
| `validators/conditions.py` | **modify** — append Wave 11b §F row checks |
| `validators/surveillance.py` | New gate: claims counting cannot establish |
| `validators/partition.py` | **modify** — new tables/assertions live only where they should |
| `validators/test_warn_match.py` | Pure tests for the lossy join, incl. the address collisions |
| `validators/test_signals.py` | Pure tests for window, item parsing, decay constants, composite |

**Why `warn_sources.py` and `warn_match.py` are separate from `fetch_warn.py`:** the parsing and matching logic must be unit-testable without network access. This mirrors `generators/curves.py` (pure) sitting beside `generators/fetch_treasury.py` (I/O), which is what let `test_curves.py` pin the two-date-format trap.

---

## Task 1: Bind the vocabulary before generating anything

Generating against invented local names is this project's named expensive failure: it validates cleanly here and cannot be consumed downstream. Nothing else in this plan may run first.

**Files:**
- Modify: `docs/ccf_dataprep_v2.md` (append a Wave 11b section to the `ex:` extension register)
- Modify: `sources/screening/published_claims.json`
- Test: `validators/test_binding_drift.py` (existing, must stay 9/9)

**Interfaces:**
- Consumes: nothing
- Produces: the IRI strings every later task writes. Exact values fixed by this task:
  - `ex:WarningSignal`, `ex:SignalSource`, `ex:signalAbout`, `ex:triggeredBy` — **pending verification**, see Step 1
  - reused: `ex:supersededBy`, `ex:IssuanceEvent`, `ex:filedBy`, `fibo-fnd-agr-ctr:BreachOfCovenant`

- [ ] **Step 1: Verify each candidate against the EDM Council source**

For each of `WarningSignal`, `SignalSource`, `signalAbout`, `triggeredBy`, search the FIBO ontology for a genuine equivalent before concluding it needs an `ex:` extension. Module membership does not pin an IRI.

```bash
# The estate already has a verifier for this exact question.
uv run generators/verify_fibo_terms.py --help
```

Search `https://spec.edmcouncil.org/fibo/` for each candidate. Record the result — **found** (bind the real IRI) or **absent** (create the `ex:` extension) — for all four. Do not skip a candidate because an `ex:` extension "seems obvious": `known-issues.md` §0.1–0.2 records that all ten inherited v1 bindings were wrong, and §0.2 was found only because a full read was forced.

Expected outcome, to be confirmed not assumed: all four absent from FIBO, matching the Covenant precedent at `docs/ccf_dataprep_v2.md:247`.

- [ ] **Step 2: Extend the binding table**

Append to `docs/ccf_dataprep_v2.md`, following the Wave 9 + Wave 10 `ex:` extension register at line 668. For each term record: local name, full IRI under `http://example.org/fibo/`, what it means, which wave introduced it, and **why it is not a FIBO term** (the outcome of Step 1).

Reuse rows — state these explicitly so a reader does not create duplicates:

| Need | Bind to | Status |
|---|---|---|
| `supersedes` | `ex:supersededBy` | already declared; 215 assertions since Wave 11a |
| Item 2.03 debt-issuance signal | `ex:IssuanceEvent` / `ex:filedBy` | bound in Wave 11a |
| covenant breach as a signal | `fibo-fnd-agr-ctr:BreachOfCovenant` | real FIBO term |

- [ ] **Step 3: Append the new terms to `published_claims.json`**

So the next punch list generates itself rather than being hand-assembled.

- [ ] **Step 4: Run the drift tests**

```bash
uv run validators/test_binding_drift.py     # expect 9/9 cases
uv run validators/binding_drift.py          # expect 23 + the new terms
```

Expected: `test_binding_drift.py` stays 9/9. `binding_drift.py` **rises above 23** — that is correct, not a regression: the new terms are materialised here and unpublished at the vault. The rise is the next punch list's content.

- [ ] **Step 5: Commit**

```bash
git add docs/ccf_dataprep_v2.md sources/screening/published_claims.json
git commit -m "Wave 11b Task 1: bind the surveillance vocabulary before generating"
```

---

## Task 2: Fetch the 8-K item events

**Files:**
- Create: `generators/fetch_8k_items.py`
- Create: `validators/test_signals.py`
- Artifact: `sources/screening/wave11b_8k_events.json`

**Interfaces:**
- Consumes: Task 1's IRIs; `ccf.fetch.get_json`, `ccf.fetch.SourceManifest`, `ccf.fetch.fetch`; `ccf.config.pg_connect`, `PG_SCHEMA_V2`
- Produces:
  - `WINDOW_START = "2024-08-19"`, `WINDOW_END = "2026-08-19"` (module constants)
  - `ITEM_CODES: tuple[str, ...] = ("1.01", "2.03", "2.04", "4.01", "4.02", "5.02")`
  - `def in_window(filing_date: str) -> bool`
  - `def matching_items(items_field: str | None) -> list[str]` — returns which of `ITEM_CODES` a filing carries
  - artifact schema: `{"generated_at", "window": {...}, "events": [{"lei","cik","item","accession","filing_date","primary_document"}]}`

- [ ] **Step 1: Write the failing tests**

Create `validators/test_signals.py`. Two traps are pinned here, both measured in `docs/wave11b-design.md` §1.

```python
#!/usr/bin/env python3
"""Pure tests for Wave 11b signal selection.

Two traps pinned here:

PREFIX MATCHING, NOT SUBSTRING. EDGAR renders the items field as a
comma-separated list like "5.02,9.01" or "Item 2.04". A substring test for
"2.04" also matches "12.04" if EDGAR ever renders one, and a test for "4.01"
matches "14.01". Match on the code as a token, anchored.

WINDOW BOUNDARIES ARE INCLUSIVE AND MEASURED. The 24-month window is a
recorded decision (D1), not a rolling `today - 730 days`. A rolling window
makes the loaded dataset depend on the day the loader ran, which is exactly
the instability Wave 11a diagnosed wrongly as "index movement".

    uv run validators/test_signals.py
"""

from __future__ import annotations

import sys

from generators.fetch_8k_items import (ITEM_CODES, WINDOW_END, WINDOW_START,
                                       in_window, matching_items)


def check_items() -> list[tuple[str, bool]]:
    return [
        ("a bare code matches", matching_items("2.04") == ["2.04"]),
        ("a comma list matches each code",
         sorted(matching_items("5.02,9.01")) == ["5.02"]),
        ("two wanted codes both match",
         sorted(matching_items("1.01,2.03")) == ["1.01", "2.03"]),
        ("whitespace is tolerated", matching_items(" 2.04 , 9.01 ") == ["2.04"]),
        ("an unwanted code yields nothing", matching_items("9.01") == []),
        ("None yields nothing", matching_items(None) == []),
        ("empty yields nothing", matching_items("") == []),
        # The trap: substring matching would return 2.04 here.
        ("12.04 does NOT match 2.04", matching_items("12.04") == []),
        ("14.01 does NOT match 4.01", matching_items("14.01") == []),
        ("all six codes are wanted", len(ITEM_CODES) == 6),
    ]


def check_window() -> list[tuple[str, bool]]:
    return [
        ("window start is the recorded constant", WINDOW_START == "2024-08-19"),
        ("window end is the recorded constant", WINDOW_END == "2026-08-19"),
        ("start boundary is inclusive", in_window("2024-08-19") is True),
        ("end boundary is inclusive", in_window("2026-08-19") is True),
        ("a day before start is out", in_window("2024-08-18") is False),
        ("a day after end is out", in_window("2026-08-20") is False),
        ("a mid-window date is in", in_window("2025-06-01") is True),
        # Tupperware, Container Store and Murphy Oil are the three real
        # in-window Item 2.04 obligors (design §1.2). If any falls out of the
        # window, §F's ">= 2 obligors" fails and the wave fails with it.
        ("Tupperware 2.04 is in window", in_window("2024-09-18") is True),
        ("Murphy Oil 2.04 (2024) is in window", in_window("2024-12-06") is True),
        ("Container Store 2.04 is in window", in_window("2024-12-23") is True),
        ("Murphy Oil 2.04 (2026) is in window", in_window("2026-01-08") is True),
    ]


def main() -> int:
    results = check_items() + check_window()
    failed = [(n, ok) for n, ok in results if not ok]
    for name, ok in results:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    print(f"\n  {len(results) - len(failed)}/{len(results)} cases behave as specified\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run validators/test_signals.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'generators.fetch_8k_items'`

- [ ] **Step 3: Implement the fetcher**

```python
#!/usr/bin/env python3
"""Wave 11b — 8-K item events for the anchor cast.

Selection costs nothing: the EDGAR submissions index carries an `items` field
per filing, so all six item types are a string match on METADATA. No
full-text search, and therefore none of the paging traps that cost Wave 11a a
wrong diagnosis.

READS THE SHARDS. `filings.recent` caps at ~1000 filings per issuer and
shards the remainder into `filings.files[]`. `known-issues.md` §9.11 records
that 40 of 50 anchors have unread shards, making every prior sweep a FLOOR.
Item 2.04 is rare enough (58 filings across the whole cast, all history) that
a floor can hide it entirely, so this sweep reads the shards too.

    uv run generators/fetch_8k_items.py --dry-run
    uv run generators/fetch_8k_items.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import get_json

SCREEN = REPO_ROOT / "sources" / "screening"

# Decision D1, docs/wave11b-design.md §0. Fixed constants, never a rolling
# window: a rolling window makes the dataset depend on the day it was built.
WINDOW_START = "2024-08-19"
WINDOW_END = "2026-08-19"

ITEM_CODES: tuple[str, ...] = ("1.01", "2.03", "2.04", "4.01", "4.02", "5.02")


def in_window(filing_date: str) -> bool:
    """ISO dates compare correctly as strings; both bounds inclusive."""
    return WINDOW_START <= filing_date <= WINDOW_END


def matching_items(items_field: str | None) -> list[str]:
    """Which wanted codes this filing carries.

    Token match, not substring: EDGAR renders "5.02,9.01", and a substring
    test for "4.01" would also fire on "14.01".
    """
    if not items_field:
        return []
    tokens = {t.strip() for t in items_field.split(",") if t.strip()}
    return [code for code in ITEM_CODES if code in tokens]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{PG_SCHEMA_V2}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    events: list[dict] = []
    shard_reads = 0
    for lei, cik in anchors:
        sub = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        blocks = [sub["filings"]["recent"]]
        for shard in sub["filings"].get("files", []):
            blocks.append(get_json(
                f"https://data.sec.gov/submissions/{shard['name']}", is_sec=True))
            shard_reads += 1

        found = 0
        for block in blocks:
            forms = block.get("form", [])
            items = block.get("items", [""] * len(forms))
            for form, acc, date, primary, it in zip(
                    forms, block.get("accessionNumber", []),
                    block.get("filingDate", []),
                    block.get("primaryDocument", []), items):
                if form != "8-K" or not in_window(date):
                    continue
                for code in matching_items(it):
                    events.append({
                        "lei": lei, "cik": cik, "item": code,
                        "accession": acc, "filing_date": date,
                        "primary_document": primary,
                        "provenance": "public",
                    })
                    found += 1
        print(f"  {lei}: {found} in-window item events", flush=True)

    print(f"\n  shard files read: {shard_reads}")
    print(f"  {len(events)} events across "
          f"{len({e['lei'] for e in events})} obligors")

    if args.dry_run:
        print("  [dry-run] nothing written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11b_8k_events.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR submissions index, `items` field, recent + shards",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "events": events,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run validators/test_signals.py
```

Expected: PASS, 21/21 cases.

- [ ] **Step 5: Run the fetcher and check it against the measured census**

```bash
uv run generators/fetch_8k_items.py
```

Expected, from `docs/wave11b-design.md` §1.2 — **these are measured numbers, treat a mismatch as a defect to investigate, not a number to accept:**
- ~534 in-window events
- Item 2.04: exactly **4 events across 3 obligors** (Tupperware, Murphy Oil ×2, Container Store)
- Item 4.02: exactly **0** — expected, see design §7.5
- ~41 shard files read

- [ ] **Step 6: Commit**

```bash
git add generators/fetch_8k_items.py validators/test_signals.py
git commit -m "Wave 11b Task 2: 8-K item events, sharded history, 24-month window"
```

---

## Task 3: Parse the WARN sources

Pure parsers first, I/O second, so the parsing is testable without network.

**Files:**
- Create: `generators/warn_sources.py` (pure)
- Create: `generators/fetch_warn.py` (I/O)
- Modify: `pyproject.toml` (add `openpyxl`)
- Test: `validators/test_warn_match.py` (created here, extended in Task 4)
- Artifact: `sources/screening/wave11b_warn.json`

**Interfaces:**
- Consumes: `ccf.fetch.fetch`, `ccf.fetch.SourceManifest`
- Produces:
  - `WarnNotice` dataclass: `state: str`, `employer: str`, `notice_date: str` (ISO), `effective_date: str | None`, `employees: int | None`, `city: str | None`, `county: str | None`, `source_ref: str`
  - `def parse_tx_socrata(rows: list[dict]) -> list[WarnNotice]`
  - `def parse_ca_xlsx(rows: list[list[str]]) -> list[WarnNotice]`
  - `def parse_ca_pdf_text(text: str) -> list[WarnNotice]`

- [ ] **Step 1: Add the dependency**

```bash
uv add openpyxl
```

`pdftotext` is a system binary from poppler-utils. Verify it exists; the CA PDF path depends on it:

```bash
which pdftotext || echo "MISSING — install poppler-utils"
```

- [ ] **Step 2: Write the failing tests**

Append to `validators/test_warn_match.py`. The fixtures below are **real rows** copied from the probes in `docs/wave11b-design.md` §1.3 — not invented shapes.

```python
#!/usr/bin/env python3
"""Pure tests for WARN parsing and the lossy obligor name join.

The join is SUPPOSED to be imperfect (CLAUDE.md rule 5). These tests pin both
directions: the true positives must resolve, and the known false positives
must NOT silently resolve. A match table containing only true positives
passes a row count and destroys the demonstration.

    uv run validators/test_warn_match.py
"""

from __future__ import annotations

import sys

from generators.warn_sources import (WarnNotice, parse_ca_pdf_text,
                                     parse_ca_xlsx, parse_tx_socrata)

# A real row from data.texas.gov resource 8w53-c4f6.
TX_ROW = {
    "notice_date": "2022-01-06T00:00:00.000",
    "job_site_name": "Stearns Lending, LLC - Corporate",
    "county_name": "Denton",
    "total_layoff_number": "348",
    "layoff_date": "2022-03-13T00:00:00.000",
    "city_name": "Lewisville",
}

# A real row from CA EDD warn_report1.xlsx, 'Detailed WARN Report' sheet.
CA_XLSX_HEADER = ["County/Parish", "Notice\nDate", "Processed\nDate",
                  "Effective \nDate", "Company", "Layoff/\nClosure",
                  "No. Of\nEmployees", "Address", "Related Industry"]
CA_XLSX_ROW = ["San Mateo County", "2026-06-26 00:00:00", "2026-07-01 00:00:00",
               "2026-07-29 00:00:00", "Genentech, Inc.", "Layoff Permanent",
               "103", "1 DNA Way  South San Francisco", "Biotech"]


def check_tx() -> list[tuple[str, bool]]:
    got = parse_tx_socrata([TX_ROW])
    n = got[0] if got else None
    return [
        ("one TX row yields one notice", len(got) == 1),
        ("TX state is stamped", n is not None and n.state == "TX"),
        ("TX employer comes from job_site_name",
         n is not None and n.employer == "Stearns Lending, LLC - Corporate"),
        ("TX notice_date is truncated to an ISO date",
         n is not None and n.notice_date == "2022-01-06"),
        ("TX employee count parses as int",
         n is not None and n.employees == 348),
        ("TX city is carried", n is not None and n.city == "Lewisville"),
    ]


def check_ca_xlsx() -> list[tuple[str, bool]]:
    got = parse_ca_xlsx([CA_XLSX_HEADER, CA_XLSX_ROW])
    n = got[0] if got else None
    return [
        ("one CA row yields one notice", len(got) == 1),
        ("CA state is stamped", n is not None and n.state == "CA"),
        ("CA employer comes from the Company column",
         n is not None and n.employer == "Genentech, Inc."),
        ("CA notice_date is an ISO date",
         n is not None and n.notice_date == "2026-06-26"),
        ("CA employee count parses", n is not None and n.employees == 103),
        # The trap: the header carries embedded newlines ("Notice\nDate").
        # Matching the header on its literal text fails; it must be normalised.
        ("the newline-bearing header is located by normalised name",
         n is not None and n.effective_date == "2026-07-29"),
    ]


def check_ca_pdf() -> list[tuple[str, bool]]:
    # Real layout from `pdftotext -layout` over the FY2024-25 report.
    text = ("Notice        Received      Effective\n"
            "Date          Date          Date\n"
            "07/01/2024    07/01/2024    06/30/2024    Lockheed Martin"
            "    Los Angeles County    57 Layoff Permanent"
            "    1011 Lockheed Way Palmdale CA 93599\n")
    got = parse_ca_pdf_text(text)
    n = got[0] if got else None
    return [
        ("a PDF data line yields one notice", len(got) == 1),
        ("PDF employer parses", n is not None and n.employer == "Lockheed Martin"),
        # The trap: the PDF renders MM/DD/YYYY while the XLSX renders ISO, and
        # both land in one table. Wave 11a's `test_curves.py` pinned exactly
        # this shape for Treasury vs FRED. Parse, do not pattern-match.
        ("PDF MM/DD/YYYY is converted to ISO",
         n is not None and n.notice_date == "2024-07-01"),
        ("PDF month and day are NOT transposed",
         parse_ca_pdf_text(
             "03/11/2025    03/11/2025    05/01/2025    Acme Co"
             "    Kern County    10 Layoff Permanent    1 Main St\n"
         )[0].notice_date == "2025-03-11"),
        ("a header line yields nothing",
         parse_ca_pdf_text("Notice        Received      Effective\n") == []),
    ]


def main() -> int:
    results = check_tx() + check_ca_xlsx() + check_ca_pdf()
    failed = [(n, ok) for n, ok in results if not ok]
    for name, ok in results:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    print(f"\n  {len(results) - len(failed)}/{len(results)} cases behave as specified\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run to verify it fails**

```bash
uv run validators/test_warn_match.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'generators.warn_sources'`

- [ ] **Step 4: Implement the pure parsers**

Create `generators/warn_sources.py`. Requirements the tests pin:
- `WarnNotice` is a `@dataclass`, fields exactly as in **Interfaces** above.
- `parse_tx_socrata` truncates Socrata's `2022-01-06T00:00:00.000` at the `T`, stamps `state="TX"`, reads the employer from `job_site_name`, and coerces `total_layoff_number` to `int | None` (the field is a string and can be absent).
- `parse_ca_xlsx` takes rows as lists, locates the header row by **normalised** column name (`" ".join(str(c).split()).lower()`) so `"Notice\nDate"` → `"notice date"`, then reads by index. Stamps `state="CA"`. Dates arrive as `"2026-06-26 00:00:00"`; truncate at the space.
- `parse_ca_pdf_text` processes line by line. A data line begins with `MM/DD/YYYY`; anything else is skipped, which is how header and page-furniture lines are discarded. Convert with `datetime.strptime(tok, "%m/%d/%Y").date().isoformat()` — never string slicing, which is what transposes month and day.
- Every parser sets `source_ref` to something that identifies the row's origin (the Socrata resource id, the XLSX filename, the PDF filename plus line number).

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run validators/test_warn_match.py
```

Expected: PASS, 17/17 cases.

- [ ] **Step 6: Implement the I/O driver**

Create `generators/fetch_warn.py`, with `--dry-run`. It must:
1. Fetch TX via `https://data.texas.gov/resource/8w53-c4f6.json?$limit=50000` through `ccf.fetch.fetch` so provenance is recorded.
2. Fetch CA `https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report1.xlsx` and the two per-FY PDFs covering the window: `warn-report-for-7-1-2024-to-06-30-2025.pdf` and `warn-report-for-7-1-25-to-6-30-26.pdf`.
3. Convert each PDF via `subprocess.run(["pdftotext", "-layout", path, "-"])`. **If `pdftotext` is absent, raise with a message naming poppler-utils** — do not silently produce zero CA PDF rows.
4. Filter every notice to the window with `fetch_8k_items.in_window`.
5. Write `sources/screening/wave11b_warn.json`.

- [ ] **Step 7: Verify the extraction against the source bytes, not the row count**

This is design §7.2 and it is not optional. Wave 10's Form 4 trap was 120 filings returning HTTP 200 with the wrong content, failing silently and identically.

```bash
uv run generators/fetch_warn.py
# Pick three parsed CA PDF rows at random and read them in the source:
pdftotext -layout sources/warn/warn-report-for-7-1-2024-to-06-30-2025.pdf - | grep -n "<employer name>"
```

Confirm employer, date and employee count match the bytes for all three. Record what you checked in the commit message.

- [ ] **Step 8: Commit**

```bash
git add generators/warn_sources.py generators/fetch_warn.py \
        validators/test_warn_match.py pyproject.toml uv.lock
git commit -m "Wave 11b Task 3: WARN sources — TX Socrata, CA XLSX + PDF"
```

---

## Task 4: The lossy obligor ↔ WARN name join

The join is **supposed** to be imperfect. A match table containing only true positives passes a count and destroys the demonstration.

**Files:**
- Create: `generators/warn_match.py` (pure)
- Modify: `validators/test_warn_match.py` (extend)
- Modify: `generators/fetch_warn.py` (call the matcher; write `matches` into the artifact)

**Interfaces:**
- Consumes: `WarnNotice` from Task 3
- Produces:
  - `def normalise(name: str) -> str` — lowercase, strip `/XX/` state suffixes and punctuation, drop corporate-form stopwords
  - `def score(anchor_name: str, employer: str) -> float` — 0.0–1.0
  - `def classify(score: float) -> str` — one of `"resolved"`, `"ambiguous"`, `"rejected"`
  - `RESOLVE_AT = 0.85`, `AMBIGUOUS_AT = 0.70`
  - `def match_all(anchors, notices) -> list[dict]` — rows `{"lei","anchor_name","employer","state","score","verdict","notice_ref"}`

- [ ] **Step 1: Write the failing tests**

Append to `validators/test_warn_match.py`. **Every pair below was measured** in design §1.3 — they are what the live data actually contains.

```python
from generators.warn_match import (AMBIGUOUS_AT, RESOLVE_AT, classify,
                                   normalise, score)

# Measured true positives — design §1.3. These MUST resolve.
TRUE_PAIRS = [
    ("CHARTER COMMUNICATIONS, INC. /MO/", "Charter Communications (Austin)"),
    ("CHARTER COMMUNICATIONS, INC. /MO/", "Charter Communications"),
    ("AVIS BUDGET GROUP, INC.", "Avis Budget Car Rental"),
    ("Quanex Building Products CORP", "Quanex Homeshield LLC"),
]

# Measured false positives — design §1.3. These MUST NOT resolve.
# The last two matched STREET ADDRESSES, not company names.
FALSE_PAIRS = [
    ("Caesars Entertainment, Inc.", "CEC Entertainment, Inc."),
    ("REGIS CORP", "St. Regis Houston"),
    ("BOSTON OMAHA Corp", "Boston Scientific Corporation"),
    ("Container Store Group, Inc.", "Dart Container Corporation"),
    ("GRANITE CONSTRUCTION INC", "Granite Peak Fabrication"),
    ("SMITH & WESSON BRANDS, INC.", "Hill & Smith, Inc."),
    ("GRANITE CONSTRUCTION INC", "182 Granite Street Corona CA 92879"),
    ("MURPHY OIL CORP", "1001 Murphy Ranch Road Milpitas CA 95035"),
]


def check_normalise() -> list[tuple[str, bool]]:
    return [
        ("state suffix is stripped",
         normalise("CHARTER COMMUNICATIONS, INC. /MO/") == "charter communications"),
        ("corporate form words are dropped",
         normalise("Quanex Building Products CORP") == "quanex building products"),
        ("case is folded", normalise("AVIS BUDGET GROUP, INC.") == "avis budget"),
        ("punctuation is dropped",
         "&" not in normalise("SMITH & WESSON BRANDS, INC.")),
    ]


def check_true_positives() -> list[tuple[str, bool]]:
    out = []
    for anchor, employer in TRUE_PAIRS:
        s = score(anchor, employer)
        out.append((f"RESOLVES: {anchor[:28]} -> {employer[:30]} ({s:.2f})",
                    classify(s) == "resolved"))
    return out


def check_false_positives() -> list[tuple[str, bool]]:
    out = []
    for anchor, employer in FALSE_PAIRS:
        s = score(anchor, employer)
        out.append((f"does NOT resolve: {anchor[:26]} -> {employer[:28]} ({s:.2f})",
                    classify(s) != "resolved"))
    return out


def check_ambiguity_survives() -> list[tuple[str, bool]]:
    # CLAUDE.md rule 5 and §F both want the ambiguity VISIBLE, not merely
    # rejected. At least one measured false pair must land in "ambiguous" so
    # the unresolved case is recorded rather than silently dropped.
    verdicts = [classify(score(a, e)) for a, e in FALSE_PAIRS]
    return [
        ("thresholds are ordered", AMBIGUOUS_AT < RESOLVE_AT),
        (">= 1 measured false pair is AMBIGUOUS, not silently rejected",
         verdicts.count("ambiguous") >= 1),
        ("no measured false pair resolves", verdicts.count("resolved") == 0),
    ]
```

Add these four groups to `main()`'s `results` list.

- [ ] **Step 2: Run to verify it fails**

```bash
uv run validators/test_warn_match.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'generators.warn_match'`

- [ ] **Step 3: Implement the matcher**

Create `generators/warn_match.py`. Requirements:
- `normalise` strips `/XX/` suffixes, removes non-alphanumerics, and drops this stopword set: `inc corp corporation co company llc lp plc holdings holding group ltd the and of`.
- `score` uses `difflib.SequenceMatcher(None, a, b).ratio()` over normalised strings, **plus** a token-containment bonus when every token of the shorter normalised name appears in the longer one — that is what lifts `"Charter Communications"` vs `"Charter Communications (Austin)"` above the threshold while leaving `"Regis"` vs `"St. Regis Houston"` below it.
- `classify` returns `"resolved"` at `>= RESOLVE_AT`, `"ambiguous"` at `>= AMBIGUOUS_AT`, else `"rejected"`.
- `match_all` returns **every** pair scoring `>= AMBIGUOUS_AT`, resolved and ambiguous alike. Rejected pairs below that are not emitted, or the table is 50 × 2,279 rows.

**Tune the thresholds against the measured pairs, not against intuition.** If a true pair fails to resolve, the scorer is wrong; if a false pair resolves, the scorer is wrong. Do not adjust the fixtures — they are what the live data contains.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run validators/test_warn_match.py
```

Expected: PASS, all cases. **≥3 distinct obligors must resolve** — Charter Communications, Quanex Building Products, Bausch Health — which is §F's floor.

> **CORRECTED 2026-08-21 (Task 13).** This line previously named the three as
> **"Charter, Avis Budget, Quanex"**. Avis Budget is wrong, for the same reason
> `wave11b-design.md` §1.3 and §1.5 were wrong and corrected there: every Avis
> WARN notice in Texas is from 2020, and the loaded window opens 2024-08-19, so
> **Avis has no in-window WARN notices at all**. The third obligor that actually
> resolves is **Bausch Health**, which was not in the original probe — Task 4's
> scorer found it by running the full 50 × 3,514 join instead of by inspection.
>
> This is the wave's signature failure one more time, and this instance is a
> *substantive claim* rather than a test fixture: a reader running this step and
> looking for Avis in the output would conclude the matcher had regressed. The
> four surviving Avis references elsewhere in the estate are fixtures and
> illustrative strings, correct in their own contexts and deliberately left
> alone; this one is not. See `docs/known-issues.md` §10.4.

- [ ] **Step 5: Wire the matcher into the fetcher and confirm the real yield**

```bash
uv run generators/fetch_warn.py
python3 -c "
import json; d=json.load(open('sources/screening/wave11b_warn.json'))
r=[m for m in d['matches'] if m['verdict']=='resolved']
print('resolved obligors:', sorted({m['anchor_name'] for m in r}))
print('ambiguous pairs:', sum(1 for m in d['matches'] if m['verdict']=='ambiguous'))
"
```

Expected: ≥3 resolved obligors, ≥1 ambiguous pair. **If resolved < 3, stop** — §F fails and the third state (Task 3 follow-on / design §7.4) must be added before proceeding.

- [ ] **Step 6: Commit**

```bash
git add generators/warn_match.py generators/fetch_warn.py validators/test_warn_match.py
git commit -m "Wave 11b Task 4: lossy WARN name join, true and false positives pinned"
```

---

## Task 5: Fetch GDELT adverse media

**Files:**
- Create: `generators/fetch_gdelt.py`
- Artifact: `sources/screening/wave11b_gdelt.json`

**Interfaces:**
- Consumes: `ccf.fetch.fetch`, `ccf.config.pg_connect`
- Produces: artifact `{"generated_at","source","substitution_note","mentions":[{"lei","employer_query","seendate","domain","title","url","tone","provenance"}]}`

- [ ] **Step 1: Implement the throttled, resumable sweep**

Requirements, each measured or mandated:
- Endpoint `https://api.gdeltproject.org/api/v2/doc/doc`, `mode=artlist`, `format=json`, with `startdatetime`/`enddatetime` covering the 24-month window.
- **Throttle to one request per 5 seconds.** Measured: an unthrottled request returned HTTP 429 with that exact instruction. Use `ccf.fetch`'s limiter or an explicit sleep.
- **Resumable.** Write the artifact incrementally, keyed by LEI, and skip LEIs already present unless `--force`. The embedding pass is the precedent (`loaders/embed_passages.py`).
- **A 429 must not be swallowed into an empty result.** Retry with backoff; if it persists, raise. Wave 11a's lesson 2: instability across runs is evidence of incompleteness, not of a changing source.
- Apply GDELT's tone filter so mentions are genuinely **adverse** — `tone<-5` in the query — per design §2.3.
- Record `substitution_note` in the artifact naming the DOC API as the substitute for §C's raw event/mention stream, so the provenance travels with the data.

- [ ] **Step 2: Run it and check the distribution**

```bash
uv run generators/fetch_gdelt.py
python3 -c "
import json,collections; d=json.load(open('sources/screening/wave11b_gdelt.json'))
c=collections.Counter(m['lei'] for m in d['mentions'])
print('mentions:',len(d['mentions']),'obligors:',len(c))
print('top 5:',c.most_common(5))
"
```

Expected: ~200+ mentions, **weighted toward a handful of names** per §F — a heavily skewed top-5 is the condition being satisfied, not a defect.

- [ ] **Step 3: Verify resumability by interrupting it**

Resumability has no pure unit test — it is a property of the I/O path, so it is verified by exercising it. Delete the artifact, start the sweep, interrupt it part-way, then restart:

```bash
rm -f sources/screening/wave11b_gdelt.json
uv run generators/fetch_gdelt.py     # interrupt after a few obligors (Ctrl-C)
uv run generators/fetch_gdelt.py     # must resume, not restart
```

Expected: the second run skips the LEIs already written and completes the rest. A run that re-fetches everything is not resumable, however it is labelled.

- [ ] **Step 4: Commit**

```bash
git add generators/fetch_gdelt.py
git commit -m "Wave 11b Task 5: GDELT adverse media via DOC API, throttled and resumable"
```

---

## Task 6: Derive XBRL trend deltas

No fetch — `financial_fact` already holds 15,055 rows.

**Files:**
- Create: `generators/generate_trend_deltas.py`
- Artifact: `sources/screening/wave11b_trend_deltas.json`

**Interfaces:**
- Produces:
  - `def pct_change(value: float, prior: float | None) -> float | None`
  - `{"deltas": [{"lei","tag","period_end","prior_period_end","value","prior_value","pct_change","provenance"}]}` with `provenance = "public"`

- [ ] **Step 1: Write the failing test**

Append to `validators/test_signals.py`. The zero-prior case is the one that matters: a division guard written as `if not prior: continue` **drops the row entirely**, which is a silent failure — the delta disappears from the dataset and nothing reports it. Emitting `None` keeps the row and makes the absence visible.

```python
from generators.generate_trend_deltas import pct_change


def _returns_without_raising(fn, *args) -> bool:
    try:
        fn(*args)
        return True
    except Exception:
        return False


def check_pct_change() -> list[tuple[str, bool]]:
    return [
        ("a normal rise computes", pct_change(110.0, 100.0) == 10.0),
        ("a normal fall computes", pct_change(90.0, 100.0) == -10.0),
        ("no change is zero", pct_change(100.0, 100.0) == 0.0),
        # The trap: `if not prior: continue` would drop these rows silently.
        ("a zero prior yields None, not an exception",
         pct_change(50.0, 0.0) is None),
        ("a missing prior yields None", pct_change(50.0, None) is None),
        ("a zero prior does NOT raise",
         _returns_without_raising(pct_change, 50.0, 0.0)),
        # A negative prior is real in XBRL: accumulated deficit, net loss.
        # Dividing by abs(prior) keeps the SIGN OF THE MOVE, not the sign of
        # the base: -100 -> -50 is a loss halving, which is +50%, not -50%.
        # Divide by `prior` itself and every negative-base series silently
        # reports its improvements as deteriorations.
        ("a negative prior still computes",
         pct_change(-50.0, -100.0) == 50.0),
        ("a negative base that worsens is negative",
         pct_change(-150.0, -100.0) == -50.0),
    ]
```

Add `check_pct_change()` to `main()`'s `results` list.

- [ ] **Step 2: Run to verify it fails**

```bash
uv run validators/test_signals.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'generators.generate_trend_deltas'`

- [ ] **Step 3: Implement**

Read `financial_fact` for the anchor cast. For each `(lei, tag, unit)`, order by `period_end` and emit period-over-period deltas whose later `period_end` falls in the window.

```python
def pct_change(value: float, prior: float | None) -> float | None:
    # Period-over-period change, or None where it is undefined.
    #
    # Returns None rather than skipping the row: a guard written as
    # `if not prior: continue` drops the observation entirely, and a delta
    # that vanishes from the dataset is a silent failure. None keeps the
    # row and makes the undefined case visible downstream.
    if prior is None or prior == 0:
        return None
    return (value - prior) / abs(prior) * 100.0
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run validators/test_signals.py
```

Expected: PASS, all cases.

- [ ] **Step 5: Run and sanity-check**

```bash
uv run generators/generate_trend_deltas.py
```

Expected: deltas across most of the 50 anchors. Break the count down by obligor before accepting it — this estate's recurring lesson is that an aggregate hides the decision.

- [ ] **Step 6: Commit**

```bash
git add generators/generate_trend_deltas.py validators/test_signals.py
git commit -m "Wave 11b Task 6: XBRL period-over-period trend deltas"
```

---

## Task 7: Unify into one signal ledger, with weights and thresholds

**Files:**
- Create: `generators/generate_signals.py`
- Modify: `validators/test_signals.py` (extend)
- Artifact: `sources/screening/wave11b_signals.json`

**Interfaces:**
- Consumes: all four artifacts from Tasks 2, 4, 5, 6, plus `spread_observation` from Postgres
- Produces:
  - `SIGNAL_TYPES = ("8k_event", "warn_notice", "adverse_media", "spread_widening", "trend_delta")`
  - `DECAY_DAYS: dict[str, float | None]` — §E's λ_c: `adverse_media` 7, `spread_widening` 1, `warn_notice` 180, `8k_event` **None** (no decay), `trend_delta` 90
  - `def signal_rows() -> list[dict]` — the unified ledger
  - artifact carries `signals`, `weights`, `thresholds`

- [ ] **Step 1: Write the failing tests**

Append to `validators/test_signals.py`:

```python
from generators.generate_signals import DECAY_DAYS, SIGNAL_TYPES


def check_decay() -> list[tuple[str, bool]]:
    # Spec §E. An 8-K never decays: it is a filed fact, and its relevance is
    # bounded by supersession rather than by time. That None is load-bearing,
    # not a missing value — §7.7 of the whitepaper separates half-life from
    # supersession precisely for this case.
    return [
        ("every signal type has a decay entry",
         set(DECAY_DAYS) == set(SIGNAL_TYPES)),
        ("adverse media decays in ~7 days", DECAY_DAYS["adverse_media"] == 7),
        ("spread widening decays in ~1 day", DECAY_DAYS["spread_widening"] == 1),
        ("WARN decays in ~180 days", DECAY_DAYS["warn_notice"] == 180),
        ("trend deltas decay in ~90 days", DECAY_DAYS["trend_delta"] == 90),
        ("an 8-K event does NOT decay", DECAY_DAYS["8k_event"] is None),
        ("five signal types", len(SIGNAL_TYPES) == 5),
    ]
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run validators/test_signals.py
```

Expected: FAIL — `ImportError: cannot import name 'DECAY_DAYS'`

- [ ] **Step 3: Implement**

Create `generators/generate_signals.py`:
- Load the four artifacts; derive spread-widening signals from `spread_observation` against `divergence_threshold`.
- **The spread signal must distinguish anticipation from confirmation** (design §7.6). Wave 11a's series is exactly invertible — `α = 1 − jump/gap` from two adjacent rows — so a naive detector recovers the generator's parameter instead of detecting anything. Read `docs/wave11a-migration-transition-design.md` before writing this part.
- Emit one row per signal with `signal_id`, `lei`, `signal_type`, `observed_at`, `severity`, `source_ref`, `provenance`.
- Emit `weights` (one per signal type × sector) and `thresholds` (per `intent`), both `synthetic — internal`. State in the module docstring that these are **ORIGINATED here**, following the precedent set in `loaders/load_postgres_wave11a.py`'s treatment of `divergence_threshold`.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run validators/test_signals.py
```

Expected: PASS, all cases.

- [ ] **Step 5: Run and report the composition**

```bash
uv run generators/generate_signals.py
```

Print a per-signal-type breakdown. Expected ~1,000+ total under decision D3. **Break it down** — do not report only the total.

- [ ] **Step 6: Commit**

```bash
git add generators/generate_signals.py validators/test_signals.py
git commit -m "Wave 11b Task 7: unified signal ledger, decay constants, weights, thresholds"
```

---

## Task 8: The two engineered conditions

**Files:**
- Create: `generators/narrative_wave11b.py`
- Modify: `validators/test_signals.py` (extend)
- Artifact: `sources/screening/wave11b_narrative.json`

**Interfaces:**
- Consumes: `signal_rows` from Task 7; Postgres `facility`, `collateral_pledge`, `drawdown`, `covenant_breach`
- Produces:
  - `CASCADE_LEI` — Avis Budget's LEI, resolved by query, not hardcoded by name
  - `def cascade_event() -> dict` — the engineered Item 2.04 and its `signalAbout` targets
  - `def composite_case() -> dict` — three individually-subthreshold signals on a **different** obligor
  - `def is_subthreshold(signal, thresholds) -> bool` — shared by generator and validator

**Why this module is shared with the validator:** Wave 11a's `narrative_wave11a.py` exists for exactly this reason — the validator must recompute the claim, not read a flag the generator set. If the generator and validator each implement `is_subthreshold`, they can drift and agree with each other while both being wrong. `conditions.py:32` records that this has already happened once in this estate.

- [ ] **Step 1: Write the failing tests**

```python
from generators.narrative_wave11b import composite_case, is_subthreshold


def check_composite() -> list[tuple[str, bool]]:
    case = composite_case()
    sigs = case["signals"]
    thr = case["threshold"]
    return [
        ("the composite case has exactly three signals", len(sigs) == 3),
        ("all three are individually subthreshold",
         all(is_subthreshold(s, thr) for s in sigs)),
        ("the three are of distinct signal types",
         len({s["signal_type"] for s in sigs}) == 3),
        ("their combined score breaches the threshold",
         sum(s["weighted_score"] for s in sigs) > thr),
        # The condition, not the count: a composite that breaches because one
        # signal was already over the line proves nothing.
        ("no single signal breaches on its own",
         all(s["weighted_score"] <= thr for s in sigs)),
    ]
```

- [ ] **Step 2: Run to verify it fails**

Expected: FAIL — `ModuleNotFoundError: No module named 'generators.narrative_wave11b'`

- [ ] **Step 3: Implement**

- **Cascade** (design §3.1): resolve Avis Budget's LEI by querying `legal_entity` for the anchor holding a facility **and** a collateral pledge **and** a drawdown **and** a `covenant_breach` row. Assert that exactly one anchor matches; if more than one does, pick deterministically and say which in the artifact. Emit an Item 2.04 event labelled `synthetic — engineered` with `signalAbout` edges to the facility, the pledge and the drawdown.
- **Composite** (design §3.3): select an obligor **other than** `CASCADE_LEI` holding all three of a GDELT cluster, a WARN notice and a spread widening. Scale the three so each is individually below the escalation threshold and their sum is above it.
- Label every row `synthetic — engineered`. Never `public`.

- [ ] **Step 4: Run the tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add generators/narrative_wave11b.py validators/test_signals.py
git commit -m "Wave 11b Task 8: engineered cascade and composite case"
```

---

## Task 9: Load Postgres

**Files:**
- Create: `loaders/load_postgres_wave11b.py`

**Interfaces:**
- Produces tables `warn_notice`, `warn_match`, `gdelt_mention`, `signal_event`, `signal_weight`, `escalation_threshold`, `trend_delta` in schema `ccf_v2`

- [ ] **Step 1: Implement, following `loaders/load_postgres_wave11a.py`**

- `--dry-run`; `CREATE TABLE IF NOT EXISTS`; idempotent upserts.
- **Every `ON CONFLICT ... DO UPDATE SET` sets every non-key column.** A partial update is the first trap named in the Wave 11a loader's docstring.
- `warn_match` stores **resolved and ambiguous** verdicts. Dropping ambiguous rows destroys the demonstration.
- Module docstring states, per table, whether it is DERIVED from an artifact or ORIGINATED here, and its provenance class.

- [ ] **Step 2: Dry-run, then load**

```bash
uv run loaders/load_postgres_wave11b.py --dry-run
uv run loaders/load_postgres_wave11b.py
uv run loaders/load_postgres_wave11b.py   # twice — idempotency is a requirement
```

Expected: the second run changes no row counts.

- [ ] **Step 3: Commit**

```bash
git add loaders/load_postgres_wave11b.py
git commit -m "Wave 11b Task 9: load seven surveillance tables into Postgres"
```

---

## Task 10: Load Fluree

**Files:**
- Create: `loaders/load_fluree_wave11b.py`

- [ ] **Step 1: Implement, following `loaders/load_fluree_wave11a.py`**

- 8-K event assertions, `signalAbout` and `triggeredBy` edges, one prior observation ledger point per obligor, supersession assertions reusing `ex:supersededBy`.
- **Every SPARQL query carries an explicit `FROM <ledger>`** — omitting it returns HTTP 500.
- **Type every entity explicitly for every role it is queried against.** No inference. A signal that is also an `ex:IssuanceEvent` carries both types.
- Instance URIs under `EX` (`http://example.org/fibo/`); the LEI is an attribute.
- `--dry-run`, idempotent. Remember Fluree is append-only: re-running must not duplicate assertions, so reconcile against what is already asserted (the `reconcile` function in the Wave 11a loader is the pattern).

- [ ] **Step 2: Dry-run, then load, then re-run**

```bash
uv run loaders/load_fluree_wave11b.py --dry-run
uv run loaders/load_fluree_wave11b.py
uv run loaders/load_fluree_wave11b.py   # must add no triples
```

- [ ] **Step 3: Verify every obligor got a prior observation point**

§D names delta anchoring explicitly: without a recorded prior, the next sweep double-reports.

```bash
uv run python -c "
from ccf.fluree import query, FLUREE_LEDGER_V2
r = query('''PREFIX ex: <http://example.org/fibo/>
SELECT (COUNT(DISTINCT ?o) AS ?n) FROM <'''+FLUREE_LEDGER_V2+'''>
WHERE { ?p a ex:PriorObservation ; ex:signalAbout ?o }''')
print(r)"
```

Expected: 50.

- [ ] **Step 4: Commit**

```bash
git add loaders/load_fluree_wave11b.py
git commit -m "Wave 11b Task 10: Fluree event assertions, edges, prior observation points"
```

---

## Task 11: Extend `conditions.py`

**Files:**
- Modify: `validators/conditions.py`

- [ ] **Step 1: Append the Wave 11b §F checks**

Following the existing `Check` dataclass (`validators/conditions.py:44`). One check per §F line:

| Condition | Floor |
|---|---|
| anchors under surveillance | 50 |
| signal events in window | 400 |
| obligors with a real in-window Item 2.04 | 2 |
| obligors with resolved WARN matches | 3 |
| ambiguous WARN matches retained | 1 |
| GDELT mentions | 200 |
| composite cases | 1 (delegates to `surveillance.py`) |
| scripted cascades | 1 (delegates to `surveillance.py`) |
| obligors with a prior observation point | 50 |

Two of these **delegate** — mark them so in the `note`, as conditions 5 and 7 already do for `series.py`. A count cannot establish them.

- [ ] **Step 2: Run the full validator**

```bash
uv run validators/conditions.py
```

Expected: **82 + 9 = 91 passed · 0 failed.** Any failure in the original 82 is a regression, not an expected cost of this wave.

- [ ] **Step 3: Commit**

```bash
git add validators/conditions.py
git commit -m "Wave 11b Task 11: nine §F condition checks"
```

---

## Task 12: `validators/surveillance.py` — the gate

**Files:**
- Create: `validators/surveillance.py`

This is the wave's regression suite for claims counting cannot establish, in the lineage of `series.py` and `traversal.py`.

- [ ] **Step 1: Implement the five recomputations**

Each must read from the **loaded stores**, never from a generator artifact or a flag the generator set.

1. **Cascade completeness** — walk `signalAbout` from the engineered Item 2.04 in Fluree and confirm it reaches the facility, the collateral pledge **and** the drawdown in Postgres. Assert all three; a count of edges is not proof they terminate correctly.
2. **Composite case** — recompute each of the three signals' weighted score from `signal_weight` and `escalation_threshold` as loaded. Assert each is **individually ≤ threshold** and the sum is **> threshold**. Import `is_subthreshold` from `generators.narrative_wave11b` so generator and validator cannot drift into agreeing while both are wrong.
3. **Score distribution** — compute the composite score for all 50 obligors and report the spread: min, median, max, and the count in each quartile. **§F wants scores to vary rather than cluster.** Decision D3 removed the mechanism that was going to design this, so it is measured here. Report the distribution **whichever way it comes out**; if scores cluster, fail the check and say so. Do not let the event count stand in for the condition.
4. **Delta anchoring** — every obligor has exactly one prior observation ledger point.
5. **WARN resolution quality** — ≥3 obligors resolved **and** ≥1 ambiguous pair retained unresolved. Both directions, in one check: a table of only true positives must fail.

- [ ] **Step 2: Run it**

```bash
uv run validators/surveillance.py
```

Expected: PASS on 1, 2, 4, 5. **Check 3 is the genuine unknown** — see design §7.1. If it fails, that is the wave's most likely real finding; surface it rather than adjusting the threshold to make it pass.

- [ ] **Step 3: Commit**

```bash
git add validators/surveillance.py
git commit -m "Wave 11b Task 12: surveillance gate — cascade, composite, distribution, anchoring"
```

---

## Task 13: Partition, docs, and the punch list

**Files:**
- Modify: `validators/partition.py`
- Modify: `docs/ccf_dataprep_v2.md`, `docs/known-issues.md`, `docs/HANDOFF.md`

- [ ] **Step 1: Extend the partition validator**

New Postgres tables exist **only** in Postgres; new Fluree assertions **only** in Fluree. The validator asserts each store holds the slice it owns and nothing it does not — it does not assert the stores agree.

```bash
uv run validators/partition.py
```

Expected: 13 + new checks, all passing.

- [ ] **Step 2: Run the whole suite**

```bash
uv run validators/partition.py      # 13+/13+
uv run validators/conditions.py     # 91/0
uv run validators/surveillance.py   # PASS
uv run validators/series.py         # PASS — must not regress
uv run validators/traversal.py
uv run validators/bitemporal.py
uv run validators/projection.py
for t in form4 persons renderings resolve coverage_shape curves instruments \
         migration binding_drift signals warn_match; do
  uv run validators/test_$t.py || echo "FAILED: $t"
done
```

Expected: everything green. 11 test files now, up from 9.

- [ ] **Step 3: Record the wave**

- `docs/ccf_dataprep_v2.md` — a `2026-08-xx — Wave 11b complete` section with the entity tables, file names, counts, and the new binding rows.
- `docs/known-issues.md` — a §10 for this wave, recording at minimum: the GDELT DOC API substitution (§2.3), Item 4.02's zero instances in-window (§7.5), the third WARN state's actual cost, and the score-distribution result from Task 12 check 3 whichever way it came out.
- `docs/HANDOFF.md` — new baseline numbers in §1, Wave 11b added to §3, next step in §8.

- [ ] **Step 4: Send the punch list to the vault**

Read **section 5 of the `obsidian-vault-access` skill** before the first send. The message directory is `<YYYY-MM-DDTHH-MM-SSZ>-<slug>` with **hyphens in the time, never colons**, or the reconciler rejects it visibly but unsent.

```bash
ls ~/.agent-exchange/ccf-dataprep/inbox/     # check for a reply first
uv run validators/binding_drift.py           # what needs publishing
```

Write to `~/.agent-exchange/ccf-dataprep/outbox/`. **Do not re-send the Wave 10 or Wave 11a punch lists** — both are delivered and awaiting application. This wave's list covers only Task 1's new terms.

- [ ] **Step 5: Commit**

```bash
git add validators/partition.py docs/
git commit -m "Wave 11b Task 13: partition checks, wave documentation, punch list"
```

---

## Self-review notes

Checked against `docs/wave11b-design.md`:

- §0 D1 (24 months) → Task 2 constants, pinned by test
- §0 D2 (TX+CA+1) → Task 3; the third state is Task 3's open item, gated by Task 4 Step 5
- §0 D3 (load everything) → Global Constraints; the risk it creates is Task 12 check 3
- §0 D4 (GDELT DOC API) → Task 5
- §0 D5 (Item 4.02 zero) → Task 2 Step 5, recorded in Task 13
- §0 D6 (Avis cascade) → Task 8
- §2.1 provenance classes → Tasks 7, 8, 9 labelling
- §2.2 inherit, don't re-fetch → Task 7 reads `spread_observation`; no market fetcher in the file list
- §3.4 prior observation points → Task 10 Step 3, Task 12 check 4
- §4.1 store partition → Tasks 9, 10, 13
- §4.2 bind before generating → Task 1, first and blocking
- §4.3 explicit typing → Task 10
- §5 pipeline order → task order; Task 7 after all fetchers
- §6.1–6.4 validation → Tasks 11, 12, 13, and the two test files
- §7.1–7.6 risks → 7.1→T12c3, 7.2→T3s7, 7.3→T5s1, 7.4→T3/T4s5, 7.5→T2s5, 7.6→T7s3

**Known gap, deliberate:** §7.4's third WARN state has no task of its own because it is unscoped by design. Task 4 Step 5 is the gate that forces it — if fewer than 3 obligors resolve, work stops there until it is added.
