# Wave 16 — `ib-opportunity-synthesis` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load the data that backs `cib.opportunity-synthesis.v1` across all five
stores, such that the same signal set provably produces different rankings for
the M&A originator and the DCM banker.

**Architecture:** Four new public fetches (Schedule 13D, 8-K Item 2.01, merger
proxies/S-4, USASpending) join the inherited coverage, signal and spread layers.
Three perspectives each get a weight vector in Postgres, versioned twice.
`validators/ib_rank.py` recomputes orderings from the stores to prove the four §F
floors. No runtime operator is built.

**Tech Stack:** Python 3.12 · `uv` · Postgres (`psycopg`) · Fluree 4.1.4 (SPARQL)
· MongoDB (`pymongo`) · SQLite · `requests`

**Spec:** `docs/wave16-design.md` (design) · vault
`context-products/ib-opportunity-synthesis` (§C catalog, §F envelope)

---

## Global Constraints

Copied verbatim from CLAUDE.md and the design. Every task's requirements include
these.

- **`uv run pytest` is broken repo-wide.** Use `uv run --with pytest pytest`.
- **Tests live in `validators/test_*.py`**, not a `tests/` directory.
- **Artifacts** (generator JSON output) live in `sources/screening/`, read via
  `ccf.currency.verify_current()`, which refuses a stale artifact.
- **Fluree takes plain-string dates, never `xsd:date`** — Fluree 4.1.4 corrupts
  typed date literals silently (known-issues §19.4).
- **`AS_OF_IB = "2026-08-24"` is pinned.** Never `date.today()` anywhere in this
  wave's ranking path.
- **Read schema/ledger names from `ccf/config.py`** — `PG_SCHEMA_V2`,
  `FLUREE_LEDGER_V2`, `MONGO_DB_V2` — never string literals.
- **FIBO absence claims use `dev.fibo-quickstart.ttl`, never `prod`** (prod omits
  40 Provisional modules). An EDM Council URL returning HTTP 200 proves nothing —
  grep the ontology for `rdf:about`.
- **Loaders are idempotent**, and idempotency is proved by **naming a value that
  must survive a second run**, never by comparing row counts.
- **Every new table gets `provenance`**, one of `public`, `synthetic — internal`,
  `synthetic — engineered`.
- **Single-writer discipline** — no attribute duplicated into a store that does
  not own it per §C.
- **AML rule does not apply here**, but the engineered-labelling rule does: an
  engineered condition is labelled `synthetic — engineered`, never presented as
  emergent.
- Read the PASS count from `conditions.py`, never a "0 failed" line — SKIP hides
  a broken query.

---

## Decisions taken during planning

Recorded so an executor does not re-open them.

1. **`comparableTo` is derived from shared SIC plus a size band**, and the basis
   is recorded on the edge. There are no existing pairwise peer edges to reuse:
   `peer_cohort` is SIC-level statistics, `peer_entity` is a CIK+SIC membership
   list. Pure SIC is too coarse to carry the sector strategist's whole ranking.
2. **Boston Omaha Corp is the divergence prospect.** Real Schedule 13D activity
   (27 filings, freshest 2026-08-13, inside the 30-day λ_c) and an **engineered**
   long-dated debt profile so its low DCM score is measured rather than missing.
3. **Anywhere Real Estate Inc. is the DCM comparator**, not Charter. Charter and
   BGC are both on the restricted list, so they leave every candidate set.
4. **Five new Postgres tables, not four** (the design said four). `λ_c` is a
   property of the signal class per §E, so `ib_signal_class` holds it once rather
   than duplicating `half_life_days` across three perspectives, where it would
   drift.
5. **`prospect_note` is re-keyed to `banker_id`** before it is extended. See
   Task 3 — this is a live defect, not a nicety.

---

## File Structure

| File | Responsibility |
|---|---|
| `ccf/config.py` *(modify)* | `AS_OF_IB`, `IB_WINDOW_START`, `IB_WINDOW_END` |
| `ccf/ib_rank.py` *(create)* | pure scoring arithmetic — no I/O, importable by the validator only |
| `generators/fetch_schedule13d.py` *(create)* | Schedule 13D, both form-name eras |
| `generators/fetch_8k_items.py` *(modify)* | add Item `2.01` |
| `generators/fetch_merger_docs.py` *(create)* | DEFM14A / PREM14A / S-4 documents |
| `generators/fetch_usaspending.py` *(create)* | curated recipient allow-list |
| `generators/generate_ib_perspectives.py` *(create)* | 3 perspectives, 2 weight vector versions, signal classes |
| `generators/generate_ib_mandates.py` *(create)* | deal pipeline, appetite, mandate history |
| `generators/generate_boston_omaha_debt.py` *(create)* | the engineered long-dated ladder |
| `generators/generate_opportunity_signals.py` *(create)* | assemble signals from all sources |
| `loaders/repair_prospect_note_keys_wave16.py` *(create)* | re-key notes to `banker_id` |
| `loaders/load_postgres_wave16.py` *(create)* | 5 new tables + rows |
| `loaders/load_fluree_wave16.py` *(create)* | `ex:OpportunitySignal`, 3 edge predicates |
| `loaders/load_mongo_wave16.py` *(create)* | proxy/S-4 text + passages |
| `loaders/load_sqlite_wave16.py` *(create)* | notes to ~50, ≥5 rank-changing |
| `validators/ib_rank.py` *(create)* | the four §F floors, recomputed |
| `validators/test_ib_rank.py` *(create)* | tests the checker with present + absent fixtures |
| `validators/conditions.py` *(modify)* | register the product |
| `validators/spec_coverage.py` *(modify)* | map all 18 §C rows |
| `docs/ccf_dataprep_v2.md` *(modify)* | binding table + entity tables |

---

### Task 1: Pin the as-of date

**Files:**
- Modify: `ccf/config.py`
- Test: `validators/test_ib_rank.py`

**Interfaces:**
- Produces: `AS_OF_IB: str`, `IB_WINDOW_START: str`, `IB_WINDOW_END: str` in
  `ccf.config`.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_ib_rank.py
"""Wave 16 — the ranking instrument, and the pins it depends on."""
from __future__ import annotations

import datetime as _dt


def test_as_of_is_pinned_not_today():
    """The ranking is a function of the clock as much as of the weights.

    Every signal class decays. If the as-of instant floats to `date.today()`,
    the engineered divergence passes on the day it is built and silently dies
    weeks later as the catalysts age past the M&A weight floor -- and the
    weight-replay condition proves nothing, because a reorder cannot be
    attributed to the weights rather than the calendar.
    """
    from ccf.config import AS_OF_IB, IB_WINDOW_END, IB_WINDOW_START

    assert AS_OF_IB == "2026-08-24"
    assert IB_WINDOW_START == "2025-08-25"
    assert IB_WINDOW_END == "2026-08-24"
    # It must be a constant, not a formatted clock read.
    assert AS_OF_IB != _dt.date.today().isoformat() or _dt.date.today() == _dt.date(2026, 8, 24)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -v`
Expected: FAIL — `ImportError: cannot import name 'AS_OF_IB'`

- [ ] **Step 3: Add the pins**

Append to `ccf/config.py`:

```python
#: Wave 16 (`ib-opportunity-synthesis`) ranks at a PINNED instant.
#:
#: Spec §E gives a half-life per signal class -- 30d for 13D, 14d for 8-K, 7d
#: for GDELT -- so a ranking computed at `date.today()` reorders itself as the
#: calendar moves. Two things break if this floats:
#:
#:   * §F's divergent prospect passes on build day and rots afterwards, with
#:     no check able to see it happen;
#:   * §F's "replay under the prior weight version" becomes unattributable,
#:     since a reorder could be the weight change or the clock.
#:
#: So the ranking path reads this constant and never the system clock.
AS_OF_IB = "2026-08-24"

#: The 12-month window §F's ~600 signals span. SYNTHETIC signals are dated
#: into it. REAL filing dates are never shifted -- a filing date is a public
#: fact, and moving one to make a window look full is fabrication.
IB_WINDOW_START = "2025-08-25"
IB_WINDOW_END = "2026-08-24"
```

- [ ] **Step 4: Run it and watch it pass**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ccf/config.py validators/test_ib_rank.py
git commit -m "Pin the as-of instant, because a decaying ranking reads the clock"
```

---

### Task 2: Bind the three new terms

**Files:**
- Modify: `docs/ccf_dataprep_v2.md` (binding table)
- Test: `validators/test_ib_rank.py`

**Interfaces:**
- Produces: `ex:OpportunitySignal`, `ex:coveredBy`, `ex:comparableTo` bound at
  `http://example.org/fibo/{local}`.

- [ ] **Step 1: Establish the FIBO absence claim honestly**

Run, and paste the output into the binding-table rationale column:

```bash
grep -oE 'rdf:about="[^"]*(OpportunitySignal|coveredBy|comparableTo)[^"]*"' \
  ontology/dev.fibo-quickstart.ttl | sort -u
```

Expected: no output. If `ontology/dev.fibo-quickstart.ttl` is absent, fetch the
**dev** quickstart — never `prod`, which omits 40 Provisional modules including
nine terms this repo already binds (known-issues §19.8). A bare HTTP 200 from
`spec.edmcouncil.org` is **not** evidence: the site returns 200 for names that do
not exist.

- [ ] **Step 2: Write the failing test**

Append to `validators/test_ib_rank.py`:

```python
def test_wave16_terms_are_bound():
    """A term generated against but never bound validates here and cannot be
    consumed downstream. That failure is silent and expensive, so it is a test."""
    from pathlib import Path

    md = Path("docs/ccf_dataprep_v2.md").read_text()
    for local in ("OpportunitySignal", "coveredBy", "comparableTo"):
        assert f"http://example.org/fibo/{local}" in md, f"{local} unbound"
```

- [ ] **Step 3: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_wave16_terms_are_bound -v`
Expected: FAIL — `OpportunitySignal unbound`

- [ ] **Step 4: Add three rows to the binding table**

In `docs/ccf_dataprep_v2.md`, in the `ex:` application-term table:

```markdown
| `OpportunitySignal` | class | `http://example.org/fibo/OpportunitySignal` | no FIBO class for a origination-side opportunity observation. Distinct from Wave 10's `ex:WarningSignal`, which is credit-deterioration: the two carry opposite polarity and must not share a type, or a query for "what should I pitch" collects "what might default" |
| `coveredBy` | property | `http://example.org/fibo/coveredBy` | relates a prospect to the banker covering it. FIBO models employment and agency, not a bank's internal coverage assignment |
| `comparableTo` | property | `http://example.org/fibo/comparableTo` | peer comparability for the sector strategist's ranking. Derived from shared SIC plus size band; the basis is recorded on the edge via `ex:comparabilityBasis` so "comparable" is inspectable rather than implied |
```

- [ ] **Step 5: Run it and watch it pass**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add docs/ccf_dataprep_v2.md validators/test_ib_rank.py
git commit -m "Bind OpportunitySignal, coveredBy, comparableTo

Verified absent from dev.fibo-quickstart.ttl, not from an HTTP 200.
OpportunitySignal is deliberately NOT ex:WarningSignal: opposite polarity,
and sharing the type would make 'what should I pitch' collect 'what might
default'.

VAULT MIRROR NEEDS REFRESH -- 3 terms added."
```

---

### Task 3: Re-key the departmental notes to `banker_id`

This is a **live defect**, found while planning. `prospect_note.banker` holds a
display name: `"R. Bhattacharya"`, `"T. Nakamura"`, `"M. Lindqvist"`,
`"A. Okonkwo"`. Three of the four **do not exist** in Postgres `banker` at all,
and `M. Lindqvist` surname-matches **four** different bankers. The roster is 40
rows over 32 distinct `full_name` values, so name-matching is ambiguous *by
construction*.

CLAUDE.md rule 4: the crosswalk is mandatory or nothing joins. §D step 6 requires
resolving *this banker's* notes from the departmental store, and §F requires ≥5
notes that change **a** ranking — unprovable when you cannot say whose ranking.

Fix it before notes are extended to ~50, or the repair gets 50 rows harder.

**Files:**
- Create: `loaders/repair_prospect_note_keys_wave16.py`
- Test: `validators/test_ib_rank.py`

**Interfaces:**
- Produces: `prospect_note.banker_id TEXT` populated for every row, each value
  present in Postgres `banker.banker_id`.

- [ ] **Step 1: Write the failing test**

```python
def test_every_prospect_note_resolves_to_a_banker():
    """Rule 4. A note whose author is not in the roster cannot be enriched
    into that banker's product, and cannot be shown to have changed a ranking.

    Counting notes proves nothing here -- 50 notes that join to nobody is the
    exact failure this asserts against. Count the notes that RESOLVE.
    """
    import sqlite3

    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import REPO_ROOT, pg_connect

    sq = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    notes = sq.execute("SELECT note_id, banker_id FROM prospect_note").fetchall()
    assert notes, "no prospect notes at all"

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT banker_id FROM "{S}".banker')
        roster = {r[0] for r in cur.fetchall()}

    orphans = [n for n, b in notes if b not in roster]
    assert not orphans, f"{len(orphans)}/{len(notes)} notes have no banker: {orphans[:5]}"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_every_prospect_note_resolves_to_a_banker -v`
Expected: FAIL — `sqlite3.OperationalError: no such column: banker_id`

- [ ] **Step 3: Write the repair loader**

```python
#!/usr/bin/env python3
"""Wave 16 — give the departmental notes a key that joins.

`prospect_note.banker` was a display name. Three of its four values are absent
from the Postgres roster entirely and the fourth matches four bankers, because
the roster carries 40 rows over 32 distinct names. Name is not an identity.

The repair assigns a real `banker_id` and KEEPS the original string in
`banker_display`, so the mapping stays auditable rather than being overwritten
by the thing that replaced it.

Assignment is deterministic (sorted note_id, round-robin over the coverage
bankers who actually cover that note's LEI), so a rerun produces the same
mapping. Where no banker covers the LEI, the note falls back to the primary
coverage banker for that entity; where there is none, the note is left with a
NULL `banker_id` and REPORTED -- never silently assigned, because an invented
coverage relationship is worse than a visible gap.

    uv run loaders/repair_prospect_note_keys_wave16.py --dry-run
    uv run loaders/repair_prospect_note_keys_wave16.py
"""
from __future__ import annotations

import argparse
import sqlite3
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, assert_v2_schema, pg_connect

DB = REPO_ROOT / "data" / "departmental.sqlite"


def coverage_map() -> dict[str, list[str]]:
    """lei -> banker_ids covering it, primary first then stable by id."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT lei, banker_id, is_primary FROM "{S}".coverage_assignment '
            "ORDER BY lei, is_primary DESC, banker_id"
        )
        out: dict[str, list[str]] = {}
        for lei, banker_id, _primary in cur.fetchall():
            out.setdefault(lei, []).append(banker_id)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_v2_schema(S)
    cov = coverage_map()

    con = sqlite3.connect(DB)
    cols = {r[1] for r in con.execute("PRAGMA table_info(prospect_note)")}
    if "banker_id" not in cols:
        con.execute("ALTER TABLE prospect_note ADD COLUMN banker_id TEXT")
    if "banker_display" not in cols:
        con.execute("ALTER TABLE prospect_note ADD COLUMN banker_display TEXT")

    rows = con.execute(
        "SELECT note_id, lei, banker FROM prospect_note ORDER BY note_id"
    ).fetchall()

    assigned, unassigned = [], []
    for i, (note_id, lei, banker) in enumerate(rows):
        candidates = cov.get(lei or "", [])
        if candidates:
            assigned.append((candidates[i % len(candidates)], banker, note_id))
        else:
            unassigned.append(note_id)

    print(f"Wave 16 — re-key prospect_note to banker_id\n")
    print(f"  notes                {len(rows):>5}")
    print(f"  resolved to a banker {len(assigned):>5}")
    print(f"  NO coverage for LEI  {len(unassigned):>5}  {unassigned[:5]}")

    if unassigned:
        print("\n  Those notes keep a NULL banker_id. Assigning them a banker "
              "would invent a coverage relationship that does not exist.")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    con.executemany(
        "UPDATE prospect_note SET banker_id = ?, banker_display = ? "
        "WHERE note_id = ?",
        assigned,
    )
    con.commit()

    still = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE banker_id IS NULL"
    ).fetchone()[0]
    print(f"\n  written. notes still without a banker_id: {still}")
    return 1 if still == len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Dry-run, then run**

```bash
uv run loaders/repair_prospect_note_keys_wave16.py --dry-run
uv run loaders/repair_prospect_note_keys_wave16.py
```

Expected: `resolved to a banker` equals 18 (all current notes are on covered LEIs).

- [ ] **Step 5: Prove idempotency by naming a value, not a count**

```bash
sqlite3 data/departmental.sqlite \
  "SELECT note_id, banker_id, banker_display FROM prospect_note ORDER BY note_id LIMIT 3;"
uv run loaders/repair_prospect_note_keys_wave16.py
sqlite3 data/departmental.sqlite \
  "SELECT note_id, banker_id, banker_display FROM prospect_note ORDER BY note_id LIMIT 3;"
```

Expected: **byte-identical `banker_id` values** across the two reads. A row count
cannot see `banker_display` being reset to NULL on the second pass; a named value
can.

- [ ] **Step 6: Run the test and watch it pass**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add loaders/repair_prospect_note_keys_wave16.py validators/test_ib_rank.py
git commit -m "Give the departmental notes a key that joins

prospect_note.banker held a display name. Three of four were absent from the
Postgres roster; the fourth matched four bankers, because the roster is 40 rows
over 32 distinct names. Name is not an identity.

Rule 4, and it blocks two things at once: SD step 6 cannot resolve 'this
banker's notes', and SF's 'notes that change a ranking' cannot be attributed."
```

- [ ] **Step 8: Record it as a found defect**

Add a section to `docs/known-issues.md` describing the above, marked
**FIXED 2026-08-24 (Wave 16)**, and grep the estate for anything else joining
bankers by name:

```bash
grep -rnE "banker[^_a-z]" --include=*.py loaders/ generators/ validators/ | grep -v banker_id
```

---

### Task 4: Fetch Schedule 13D — both form-name eras

**Files:**
- Create: `generators/fetch_schedule13d.py`
- Output: `sources/schedule13d/manifest.json`, `sources/screening/wave16_13d.json`

**Interfaces:**
- Consumes: `crosswalk(lei, cik)` from Postgres.
- Produces: artifact `wave16_13d.json` with
  `{"filings": [{"lei", "cik", "form", "accession", "filing_date", "role"}], ...}`.

- [ ] **Step 1: Write the failing test**

```python
def test_schedule13d_matches_both_form_name_eras():
    """The SEC renamed the form under the structured-XML mandate in Dec 2024.

    Matching only `SC 13D` returns zero filings after 2024-12-06, which is
    indistinguishable from the source drying up. It had not. This test exists
    because that read cost a probe to catch, and the same shape will recur.
    """
    from generators.fetch_schedule13d import FORMS, matches

    assert matches("SC 13D")            # legacy
    assert matches("SCHEDULE 13D")      # modern
    assert matches("SCHEDULE 13D/A")    # modern amendment
    assert not matches("SC 13G")        # 13G is not a catalyst signal
    assert not matches("SCHEDULE 13E-3")
    assert "SCHEDULE 13D" in FORMS and "SC 13D" in FORMS
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_schedule13d_matches_both_form_name_eras -v`
Expected: FAIL — `ModuleNotFoundError: generators.fetch_schedule13d`

- [ ] **Step 3: Write the fetcher**

```python
#!/usr/bin/env python3
"""Wave 16 — Schedule 13D activist stakes against the anchor set.

## Two form names, one form

The SEC's structured-XML mandate renamed Schedule 13D in December 2024. Filings
before that are `SC 13D` / `SC 13D/A`; after, `SCHEDULE 13D` / `SCHEDULE 13D/A`.

Matching only the legacy string returns ZERO filings after 2024-12-06 -- which
reads exactly like a dead source and is not one. Both eras are matched, and a
count is printed per era so a future rename is visible as a cliff rather than a
silence.

## Direction

A Schedule 13D is filed BY an activist ABOUT a subject company, so it was an
open question whether it appears under the subject's CIK at all. Sampled 12
recent filings and read the submission header: the anchor is the SUBJECT in
12 of 12. `role` is recorded per filing from the header so the claim stays
checkable rather than remembered.

    uv run generators/fetch_schedule13d.py --dry-run
    uv run generators/fetch_schedule13d.py
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect
from ccf.fetch import SOURCES_ROOT, get, get_json

#: Both eras. Order is display order, not precedence.
FORMS: tuple[str, ...] = ("SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A")

_SUBJECT = re.compile(r"SUBJECT COMPANY:.*?CENTRAL INDEX KEY:\s*(\d+)", re.S)
_FILED_BY = re.compile(r"FILED BY:.*?CENTRAL INDEX KEY:\s*(\d+)", re.S)


def matches(form: str) -> bool:
    """Exact membership, never substring.

    Substring would make `SCHEDULE 13D` swallow `SCHEDULE 13D-X` if the SEC
    ever mints one, and would match `SC 13D` inside longer strings.
    """
    return form.strip().upper() in FORMS


def header_role(cik: int, accession: str) -> str:
    """SUBJECT, FILER, or UNKNOWN, read from the submission header.

    Resolved from the header rather than `index.json`, which has been observed
    to omit a real, fetchable exhibit.
    """
    nodash = accession.replace("-", "")
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/"
           f"{accession}-index-headers.html")
    try:
        text = get(url, is_sec=True).text
    except Exception:  # noqa: BLE001 — a missing header is not a missing filing
        return "UNKNOWN"
    subject = _SUBJECT.search(text)
    filed_by = _FILED_BY.search(text)
    if subject and int(subject.group(1)) == cik:
        return "SUBJECT"
    if filed_by and int(filed_by.group(1)) == cik:
        return "FILER"
    return "UNKNOWN"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-roles", type=int, default=12,
                    help="how many filings to header-check for direction")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{S}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    filings: list[dict] = []
    for lei, cik in anchors:
        sub = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        blocks = [sub["filings"]["recent"]]
        for shard in sub["filings"].get("files", []):
            blocks.append(get_json(
                f"https://data.sec.gov/submissions/{shard['name']}", is_sec=True))
        for block in blocks:
            for form, acc, date in zip(
                    block.get("form", []), block.get("accessionNumber", []),
                    block.get("filingDate", []), strict=True):
                if matches(form):
                    filings.append({
                        "lei": lei, "cik": int(cik), "form": form.strip().upper(),
                        "accession": acc, "filing_date": date,
                        "role": None, "provenance": "public",
                    })

    filings.sort(key=lambda f: (f["filing_date"], f["accession"]), reverse=True)

    # Direction check on the most recent N. Not all of them: the claim is
    # "the anchor is the subject", and a sample that has never once returned
    # FILER is the evidence. Recording `role` keeps it checkable.
    for f in filings[:args.verify_roles]:
        f["role"] = header_role(f["cik"], f["accession"])

    era = collections.Counter(
        "modern" if f["form"].startswith("SCHEDULE") else "legacy" for f in filings)
    roles = collections.Counter(f["role"] for f in filings if f["role"])

    print("Wave 16 — Schedule 13D\n")
    print(f"  anchors queried   {len(anchors):>5}")
    print(f"  filings           {len(filings):>5}  "
          f"across {len({f['lei'] for f in filings})} entities")
    print(f"    legacy `SC 13D*`      {era['legacy']:>5}")
    print(f"    modern `SCHEDULE 13D*`{era['modern']:>5}   "
          f"<- zero here means the form was renamed again")
    print(f"  direction sample  {dict(roles)}")
    if roles.get("FILER"):
        print("\n  WARNING: an anchor is the FILER, not the subject. The join "
              "the spec assumes does not hold for that row.")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    out = SOURCES_ROOT / "screening" / "wave16_13d.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "source": "SEC EDGAR submissions index, both Schedule 13D form-name eras",
        "forms": list(FORMS),
        "direction_sample": dict(roles),
        "filings": filings,
    }, indent=1))
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test, then the fetch**

```bash
uv run --with pytest pytest validators/test_ib_rank.py::test_schedule13d_matches_both_form_name_eras -v
uv run generators/fetch_schedule13d.py --dry-run
uv run generators/fetch_schedule13d.py
```

Expected: test PASS; ~899 filings across ~39 entities; `direction sample` shows
`{'SUBJECT': 12}` and no `FILER`.

- [ ] **Step 5: Commit**

```bash
git add generators/fetch_schedule13d.py validators/test_ib_rank.py sources/screening/wave16_13d.json
git commit -m "Fetch Schedule 13D across both form-name eras

Matching only SC 13D returns nothing after 2024-12-06 and reads as a dead
source. The SEC renamed the form under the structured-XML mandate. Both eras
matched, counted separately, so the next rename shows as a cliff not a silence.

Direction recorded per filing from the submission header rather than assumed:
the anchor is the SUBJECT in 12 of 12 sampled."
```

---

### Task 5: Add 8-K Item 2.01

**Files:**
- Modify: `generators/fetch_8k_items.py:36`

**Interfaces:**
- Produces: `2.01` events in the existing 8-K item artifact.

- [ ] **Step 1: Write the failing test**

```python
def test_8k_item_codes_include_completed_acquisitions():
    """Item 1.01 is entry into a material agreement; 2.01 is COMPLETION of an
    acquisition. The M&A originator's ranking needs both -- an announced deal
    and a closed one are different signals about the same prospect."""
    from generators.fetch_8k_items import ITEM_CODES

    assert "1.01" in ITEM_CODES
    assert "2.01" in ITEM_CODES
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_8k_item_codes_include_completed_acquisitions -v`
Expected: FAIL — `assert '2.01' in ('1.01', '2.03', '2.04', '4.01', '4.02', '5.02')`

- [ ] **Step 3: Add the code**

In `generators/fetch_8k_items.py`, change line 36 to:

```python
# 2.01 added 2026-08-24 (Wave 16). `ib-opportunity-synthesis` SC assigns
# "M&A and material-agreement events / EDGAR 8-K Items 1.01 / 2.01" to Fluree.
# 1.01 is entry into a material agreement; 2.01 is completion of an
# acquisition or disposition -- an announced deal and a closed one are
# different signals about the same prospect, and the M&A ranking needs both.
ITEM_CODES: tuple[str, ...] = ("1.01", "2.01", "2.03", "2.04", "4.01", "4.02", "5.02")
```

- [ ] **Step 4: Refetch and confirm 2.01 appears**

```bash
uv run --with pytest pytest validators/test_ib_rank.py::test_8k_item_codes_include_completed_acquisitions -v
uv run generators/fetch_8k_items.py --dry-run
uv run generators/fetch_8k_items.py
```

Expected: the per-obligor counts rise; `2.01` present in the output artifact.

- [ ] **Step 5: Commit**

```bash
git add generators/fetch_8k_items.py validators/test_ib_rank.py
git commit -m "Fetch 8-K Item 2.01 -- a closed deal is not the same signal as an announced one"
```

---

### Task 6: Fetch merger proxies and S-4 registrations

**Files:**
- Create: `generators/fetch_merger_docs.py`
- Output: `sources/merger_docs/`, `sources/screening/wave16_merger_docs.json`

**Interfaces:**
- Produces: artifact with `{"documents": [{"lei","cik","form","accession","filing_date","primary_document","path"}]}`.

- [ ] **Step 1: Write the failing test**

```python
def test_merger_doc_forms_exclude_s1():
    """S-1 is dropped, with evidence, not forgotten.

    Probed 2026-08-24: 43 S-1 filings lifetime across the anchor set, ZERO
    since 2023, because the cast are established issuers who do not file IPO
    registrations. S-4 covers the merger-registration half of the same SC row.
    """
    from generators.fetch_merger_docs import FORMS

    assert "DEFM14A" in FORMS and "PREM14A" in FORMS
    assert "S-4" in FORMS and "S-4/A" in FORMS
    assert "S-1" not in FORMS
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_merger_doc_forms_exclude_s1 -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the fetcher**

```python
#!/usr/bin/env python3
"""Wave 16 — merger proxies and merger-registration documents.

SC assigns two rows to MongoDB:

    Merger proxies and deal terms          EDGAR DEF 14A / DEFM14A
    IPO and merger registration pipeline   EDGAR S-1 / S-4

## S-1 is dropped, and this is the evidence

Probed 2026-08-24 across all 53 anchors carrying a CIK: 43 `S-1` filings
lifetime, and ZERO since 2023. That is a fact about the cast -- established
issuers do not file IPO registrations -- not a gap in the fetch. `S-4` covers
the merger-registration half of the same row, so the row is partially and
honestly accounted for, and `validators/spec_coverage.py` records it as a
NAMED GAP rather than a silent one.

`DEF 14A` is already on disk (49 files, `sources/def14a/`) from an earlier
wave. This fetcher adds the MERGER proxies specifically -- DEFM14A and PREM14A
-- which carry deal terms rather than routine annual-meeting business.

    uv run generators/fetch_merger_docs.py --dry-run
    uv run generators/fetch_merger_docs.py
"""
from __future__ import annotations

import argparse
import collections
import json
import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect
from ccf.fetch import SOURCES_ROOT, fetch, get_json

#: `S-1` is deliberately absent. See the module docstring.
FORMS: tuple[str, ...] = ("DEFM14A", "PREM14A", "S-4", "S-4/A")

WINDOW_START = "2024-08-19"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, cik FROM "{S}".crosswalk '
                    "WHERE cik IS NOT NULL ORDER BY lei")
        anchors = cur.fetchall()

    docs: list[dict] = []
    for n, (lei, cik) in enumerate(anchors, 1):
        # Progress with flush=True. This walk is minutes long, and a fetcher
        # that prints only on completion is indistinguishable from a hang --
        # which invites an operator to kill it and lose rate-limited work.
        print(f"  [{n}/{len(anchors)}] {lei}", flush=True)
        sub = get_json(
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", is_sec=True)
        blocks = [sub["filings"]["recent"]]
        for shard in sub["filings"].get("files", []):
            blocks.append(get_json(
                f"https://data.sec.gov/submissions/{shard['name']}", is_sec=True))
        for block in blocks:
            for form, acc, date, primary in zip(
                    block.get("form", []), block.get("accessionNumber", []),
                    block.get("filingDate", []),
                    block.get("primaryDocument", []), strict=True):
                if form.strip().upper() in FORMS and date >= WINDOW_START:
                    docs.append({
                        "lei": lei, "cik": int(cik), "form": form.strip().upper(),
                        "accession": acc, "filing_date": date,
                        "primary_document": primary, "provenance": "public",
                    })

    by_form = collections.Counter(d["form"] for d in docs)
    print("Wave 16 — merger proxies and S-4 registrations\n")
    print(f"  window from {WINDOW_START}")
    for f in FORMS:
        print(f"    {f:10s} {by_form[f]:>4}")
    print(f"  total {len(docs)} across {len({d['lei'] for d in docs})} entities")
    print("\n  S-1: NOT fetched. 43 lifetime, 0 since 2023 -- the cast are "
          "established issuers. Recorded as a named gap in spec_coverage.py.")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    dest = SOURCES_ROOT / "merger_docs"
    for d in docs:
        nodash = d["accession"].replace("-", "")
        url = (f"https://www.sec.gov/Archives/edgar/data/{d['cik']}/{nodash}/"
               f"{d['primary_document']}")
        target = dest / f"{d['cik']:010d}_{d['accession']}_{d['primary_document']}"
        try:
            fetch(url, target, is_sec=True)
            d["path"] = str(target.relative_to(SOURCES_ROOT))
        except Exception as exc:  # noqa: BLE001
            print(f"    MISS {d['accession']}: {exc}")
            d["path"] = None

    got = sum(1 for d in docs if d["path"])
    out = SOURCES_ROOT / "screening" / "wave16_merger_docs.json"
    out.write_text(json.dumps({
        "source": "SEC EDGAR submissions index + Archives",
        "forms": list(FORMS),
        "s1_excluded_because": "43 lifetime, 0 since 2023 across the anchor set",
        "documents": docs,
    }, indent=1))
    print(f"\n  downloaded {got}/{len(docs)}; wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test, dry-run, then fetch**

```bash
uv run --with pytest pytest validators/test_ib_rank.py::test_merger_doc_forms_exclude_s1 -v
uv run generators/fetch_merger_docs.py --dry-run
uv run generators/fetch_merger_docs.py
```

Expected: ~15 documents (5 DEFM14A, 4 PREM14A, 3 S-4, 3 S-4/A).

- [ ] **Step 5: Commit**

```bash
git add generators/fetch_merger_docs.py validators/test_ib_rank.py sources/screening/wave16_merger_docs.json sources/merger_docs/manifest.json
git commit -m "Fetch merger proxies and S-4; drop S-1 with its evidence

S-1: 43 filings lifetime across the anchor set, zero since 2023. Established
issuers do not file IPO registrations. That is a fact about the cast, not a
gap in the fetch, and spec_coverage.py records it as a named gap."
```

---

### Task 7: Fetch USASpending against a curated allow-list

**Files:**
- Create: `generators/fetch_usaspending.py`
- Create: `sources/usaspending/recipient_allowlist.json` (hand-verified)
- Output: `sources/screening/wave16_usaspending.json`

**Interfaces:**
- Produces: rows `{"lei", "recipient_name", "match_band", "fy", "obligated_usd"}`.

- [ ] **Step 1: Write the failing test**

```python
def test_usaspending_rows_carry_a_match_band():
    """USASpending joins on NAME. There is no LEI, no CIK, no shared key.

    Its `keywords` filter searches award DESCRIPTION text, which returned
    XPO -> Lockheed Martin and REGIS -> Humana Government Business. Switching
    to `recipient_search_text` narrows it but does not fix it: AMPHENOL ->
    MTS Systems.

    CLAUDE.md rule 5 wants joins that are imperfect ON PURPOSE. These are
    imperfect BY ACCIDENT, and a government-revenue-concentration measure
    built on them is simply wrong. So every row records how it was matched,
    and unverified candidates are dropped rather than guessed.
    """
    from generators.fetch_usaspending import MATCH_BANDS, classify

    assert set(MATCH_BANDS) == {"exact", "verified-subsidiary", "rejected"}
    assert classify("SP PLUS LLC", "SP Plus Corp") == "exact"
    assert classify("LOCKHEED MARTIN CORP", "XPO") == "rejected"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_usaspending_rows_carry_a_match_band -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Build the allow-list by inspection**

Run the candidate sweep and **read the output by hand**:

```bash
uv run generators/fetch_usaspending.py --propose > /tmp/usaspending_candidates.txt
cat /tmp/usaspending_candidates.txt
```

For each candidate, decide `exact` (the recipient IS the anchor),
`verified-subsidiary` (the recipient is a named subsidiary of the anchor —
confirm against `corporate_ownership_record` or Exhibit 21, do not assume from
the name), or `rejected`. Write the decisions to
`sources/usaspending/recipient_allowlist.json`:

```json
{
  "_note": "Hand-verified 2026-08-24. USASpending has no LEI or CIK, so every row here is a name judgement and is recorded as one. Unlisted candidates are rejected by omission.",
  "entries": [
    {"lei": "0IDE18EMH1CUKQCUYE69", "recipient_name": "SP PLUS LLC", "match_band": "exact", "verified_against": "identical trading name"},
    {"lei": "...", "recipient_name": "GRANITE CONSTRUCTION COMPANY", "match_band": "exact", "verified_against": "identical legal name"}
  ]
}
```

- [ ] **Step 4: Write the fetcher**

```python
#!/usr/bin/env python3
"""Wave 16 — federal contract concentration, joined on name and admitting it.

SC row: "Government-contract revenue concentration | USASpending.gov | public |
Postgres | E".

## The join is the problem

USASpending carries no LEI and no CIK. The only bridge to our anchors is a
company NAME, and its `keywords` filter searches award DESCRIPTION text, not
recipient identity -- it returned XPO -> Lockheed Martin and REGIS -> Humana
Government Business at $20.4bn. `recipient_search_text` narrows the search to
the recipient but still returns AMPHENOL -> MTS Systems.

CLAUDE.md rule 5 asks for joins that are imperfect ON PURPOSE, so that
resolution logic is testable. These are imperfect BY ACCIDENT, which is a
different thing: a concentration measure built on them would be wrong rather
than instructively fuzzy.

So the fetch runs against a HAND-VERIFIED allow-list, every row records its
`match_band`, and anything not on the list is dropped. `--propose` regenerates
the candidate sweep for a human to re-verify; it never writes the allow-list
itself.

    uv run generators/fetch_usaspending.py --propose
    uv run generators/fetch_usaspending.py --dry-run
    uv run generators/fetch_usaspending.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time

import requests

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect
from ccf.fetch import SOURCES_ROOT

URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
ALLOWLIST = SOURCES_ROOT / "usaspending" / "recipient_allowlist.json"

MATCH_BANDS = ("exact", "verified-subsidiary", "rejected")

_SUFFIX = re.compile(
    r"[,.]?\s*(INC|CORP|CORPORATION|COMPANY|CO|LTD|LLC|L\.L\.C|PLC|HOLDINGS|"
    r"GROUP|TRUST|LP|L\.P)\.?$", re.I)


def _core(name: str) -> str:
    """Strip legal-form suffixes and punctuation for comparison only."""
    n = re.sub(r"\s*/[A-Z]{2}/\s*$", "", name).upper()
    while True:
        stripped = _SUFFIX.sub("", n).strip(" ,.")
        if stripped == n:
            return re.sub(r"[^A-Z0-9 ]", "", n).strip()
        n = stripped


def classify(recipient_name: str, anchor_name: str) -> str:
    """`exact` when the cores agree, else `rejected`.

    `verified-subsidiary` is never returned by this function -- it is a HUMAN
    judgement recorded in the allow-list, because deciding that
    "GRIFFON AEROSPACE, INC." is Griffon Corp's subsidiary requires checking
    an ownership record, not comparing two strings.
    """
    return "exact" if _core(recipient_name) == _core(anchor_name) else "rejected"


def anchors() -> list[tuple[str, str]]:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT e.lei, e.legal_name FROM "{S}".legal_entity e '
            f'JOIN "{S}".crosswalk c ON c.lei = e.lei '
            "WHERE c.cik IS NOT NULL AND e.lei NOT LIKE 'SYN-%' "
            "ORDER BY e.legal_name")
        return cur.fetchall()


def query(name: str) -> list[dict]:
    body = {
        "filters": {
            "recipient_search_text": [name],
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{"start_date": "2023-01-01", "end_date": "2026-08-24"}],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
                   "Start Date"],
        "limit": 20, "page": 1, "sort": "Award Amount", "order": "desc",
    }
    resp = requests.post(URL, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json().get("results", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--propose", action="store_true",
                    help="print candidates for human verification; writes nothing")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.propose:
        print("# USASpending candidates — VERIFY EACH BY HAND\n")
        print("# auto_band is a string comparison only. `verified-subsidiary`")
        print("# is yours to decide against an ownership record.\n")
        for lei, name in anchors():
            core = _core(name)
            try:
                results = query(core)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERR  {name}: {exc}")
                continue
            for r in results[:3]:
                rn = r.get("Recipient Name") or ""
                print(f"  {lei}  anchor={name[:34]:34s} recipient={rn[:38]:38s} "
                      f"amount={r.get('Award Amount')}  auto_band={classify(rn, name)}")
            time.sleep(0.35)
        return 0

    if not ALLOWLIST.exists():
        print(f"No allow-list at {ALLOWLIST}.\n"
              f"Run with --propose, verify the candidates by hand, and write it.\n"
              f"This fetcher will not guess a join it cannot check.")
        return 1

    allow = json.loads(ALLOWLIST.read_text())["entries"]
    keep = {(e["lei"], e["recipient_name"].upper()): e for e in allow
            if e["match_band"] != "rejected"}
    print(f"Wave 16 — USASpending\n\n  allow-list entries kept {len(keep)}")

    by_lei: dict[str, list[str]] = {}
    for lei, _rn in keep:
        by_lei.setdefault(lei, [])

    rows: list[dict] = []
    name_of = dict(anchors())
    for lei in sorted(by_lei):
        for r in query(_core(name_of.get(lei, ""))):
            rn = (r.get("Recipient Name") or "").upper()
            entry = keep.get((lei, rn))
            if not entry:
                continue  # not on the list == rejected by omission
            rows.append({
                "lei": lei,
                "recipient_name": rn,
                "match_band": entry["match_band"],
                "verified_against": entry.get("verified_against", ""),
                "award_id": r.get("Award ID"),
                "awarding_agency": r.get("Awarding Agency"),
                "start_date": r.get("Start Date"),
                "obligated_usd": r.get("Award Amount"),
                "provenance": "public",
            })
        time.sleep(0.35)

    print(f"  awards kept             {len(rows)}")
    print(f"  entities with any award {len({r['lei'] for r in rows})}")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    out = SOURCES_ROOT / "screening" / "wave16_usaspending.json"
    out.write_text(json.dumps({
        "source": "USASpending.gov API v2 spending_by_award, recipient_search_text",
        "join": "company NAME against a hand-verified allow-list; no LEI or CIK exists",
        "awards": rows,
    }, indent=1))
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run test, propose, verify, fetch**

```bash
uv run --with pytest pytest validators/test_ib_rank.py::test_usaspending_rows_carry_a_match_band -v
uv run generators/fetch_usaspending.py --propose > /tmp/usaspending_candidates.txt
# ... verify by hand, write sources/usaspending/recipient_allowlist.json ...
uv run generators/fetch_usaspending.py --dry-run
uv run generators/fetch_usaspending.py
```

- [ ] **Step 6: Commit**

```bash
# `.gitignore` carries an explicit `!sources/usaspending/recipient_allowlist.json`
# exception. VERIFY the allow-list actually stages -- `sources/**` is ignored, so
# without that exception `git add` on it is a silent no-op and the hand
# verification is lost on the next fresh checkout:
git check-ignore -v sources/usaspending/recipient_allowlist.json && echo "STOP: still ignored" || echo "ok, will commit"
git add generators/fetch_usaspending.py sources/usaspending/recipient_allowlist.json sources/screening/wave16_usaspending.json validators/test_ib_rank.py
git commit -m "Fetch USASpending against a hand-verified allow-list

The API joins on name and its keyword filter searches award description text,
not recipient identity: XPO -> Lockheed Martin, REGIS -> Humana Government
Business at \$20.4bn. recipient_search_text narrows it and still gives
AMPHENOL -> MTS Systems.

Rule 5 wants joins imperfect on purpose. These are imperfect by accident, and
a concentration measure built on them is wrong rather than instructive. Every
row records its match band; anything unlisted is rejected by omission."
```

---

### Task 8: Perspectives, signal classes, and two weight vectors

**Files:**
- Create: `generators/generate_ib_perspectives.py`
- Output: `sources/screening/wave16_perspectives.json`

**Interfaces:**
- Produces: `{"perspectives": [...], "signal_classes": [...], "weights": [...]}`
  where a weight row is
  `{"perspective_id", "signal_type", "weight_version", "weight", "rationale"}`.
- Consumed by Task 11 (`load_postgres_wave16.py`) and Task 14 (`ccf/ib_rank.py`).

- [ ] **Step 1: Write the failing test**

```python
def test_weights_separate_ma_from_dcm():
    """SF's centrepiece is that identical signals produce different orderings.

    That is a property of the WEIGHT VECTORS, and it is checkable before any
    data loads: if M&A and DCM weight the same signal types the same way, no
    amount of signal data will make the two lists differ.
    """
    from generators.generate_ib_perspectives import WEIGHTS_V2

    ma = {w["signal_type"]: w["weight"] for w in WEIGHTS_V2 if w["perspective_id"] == "PSP-MA"}
    dcm = {w["signal_type"]: w["weight"] for w in WEIGHTS_V2 if w["perspective_id"] == "PSP-DCM"}

    assert ma["activist_stake_13d"] >= 0.9, "13D is the M&A originator's top signal"
    assert dcm["activist_stake_13d"] <= 0.15, "a 13D is near-noise to a DCM banker"
    assert dcm["maturity_wall"] >= 0.9, "the maturity wall is the DCM banker's top signal"
    assert ma["maturity_wall"] <= 0.15, "a maturity wall is near-noise to an M&A originator"


def test_two_weight_versions_exist_and_differ():
    """SF: two weight-vector versions, so a ranking can be replayed under the
    prior one. Two IDENTICAL versions would satisfy a count and prove nothing."""
    from generators.generate_ib_perspectives import WEIGHTS_V1, WEIGHTS_V2

    v1 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V1}
    v2 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V2}
    assert set(v1) == set(v2), "the two versions must cover the same cells"
    assert v1 != v2, "two identical weight vectors replay to the same order"


def test_half_life_lives_once():
    """Lambda_c is a property of the signal class per SE, not of a perspective.

    Storing it per (perspective, signal_type) would triple every value and let
    the three copies drift, so it lives on the signal class alone.
    """
    from generators.generate_ib_perspectives import SIGNAL_CLASSES, WEIGHTS_V2

    # Count the population FIRST. `all(...)` over an empty sequence is True,
    # so without these two lines both assertions below pass when the
    # generator produces nothing at all -- a gate blind to its own
    # denominator, which is this estate's second-most-repeated defect.
    assert len(SIGNAL_CLASSES) >= 10, f"only {len(SIGNAL_CLASSES)} signal classes"
    assert len(WEIGHTS_V2) >= 30, f"only {len(WEIGHTS_V2)} v2 weight rows"

    assert all("half_life_days" in c for c in SIGNAL_CLASSES)
    assert all("half_life_days" not in w for w in WEIGHTS_V2)
```

- [ ] **Step 2: Run and watch all three fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -k "weights or half_life" -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the generator**

```python
#!/usr/bin/env python3
"""Wave 16 — the three perspectives and the weight vectors that separate them.

SC assigns "Per-perspective ranking weights" and "ProjectionPlan per
perspective" to Postgres as `synthetic — internal`, dimension Pi / P. They are
OURS to produce; the SDK's Rank Operator consumes them.

## Why the weights are the mechanism

SB: "the same underlying signals produce three different rankings -- not three
sorts of one ranking." That difference lives entirely here. A maturity wall is
the DCM banker's top signal and near-noise to the M&A originator, so the two
weight vectors must genuinely diverge or no signal data will make the lists
differ.

## Two versions, and why they must differ

SF requires two weight-vector versions so a ranking can be replayed under the
prior one. Two identical versions would satisfy a count and demonstrate
nothing, so v1 and v2 differ on the cells that reorder the list -- v1 is the
"pre-2026 origination policy" that under-weighted activist stakes.

## Half-life lives once

SE gives lambda_c per signal CLASS, not per perspective. Storing it per
(perspective, signal_type) would write every value three times and let the
copies drift silently. It lives on `ib_signal_class` alone.

    uv run generators/generate_ib_perspectives.py --dry-run
    uv run generators/generate_ib_perspectives.py
"""
from __future__ import annotations

import argparse
import json
import sys

from ccf.fetch import SOURCES_ROOT

PERSPECTIVES = [
    {"perspective_id": "PSP-MA", "label": "M&A originator",
     "ranks_on": "strategic catalyst, sponsor activity, sector consolidation",
     "provenance": "synthetic — internal"},
    {"perspective_id": "PSP-DCM", "label": "DCM banker",
     "ranks_on": "maturity walls, refinancing windows, rate sensitivity",
     "provenance": "synthetic — internal"},
    {"perspective_id": "PSP-SECTOR", "label": "sector strategist",
     "ranks_on": "thematic movement across the sector",
     "provenance": "synthetic — internal"},
]

#: lambda_c per SE. Half-life in days: a signal contributes
#: `weight * 0.5 ** (age_days / half_life_days)`.
SIGNAL_CLASSES = [
    {"signal_type": "activist_stake_13d", "half_life_days": 30,
     "note": "SE: catalyst value decays as the market absorbs it"},
    {"signal_type": "ma_event_8k", "half_life_days": 14, "note": "SE"},
    {"signal_type": "merger_proxy", "half_life_days": 30, "note": "deal terms filed"},
    {"signal_type": "registration_s4", "half_life_days": 30, "note": "merger registration"},
    {"signal_type": "insider_activity_form4", "half_life_days": 14, "note": "insider transactions"},
    {"signal_type": "institutional_positioning_13f", "half_life_days": 90,
     "note": "quarterly filing cadence sets the floor"},
    {"signal_type": "maturity_wall", "half_life_days": 90, "note": "SE"},
    {"signal_type": "spread_trajectory", "half_life_days": 1, "note": "SE"},
    {"signal_type": "sector_news_gdelt", "half_life_days": 7, "note": "SE"},
    {"signal_type": "gov_revenue_concentration", "half_life_days": 180,
     "note": "contract awards move slowly"},
    {"signal_type": "banker_local_note", "half_life_days": 60,
     "note": "SD step 6: local knowledge the fabric must reach"},
]


def _w(perspective: str, weights: dict[str, float], version: str,
       rationale: str) -> list[dict]:
    return [{"perspective_id": perspective, "signal_type": st,
             "weight_version": version, "weight": w, "rationale": rationale,
             "provenance": "synthetic — internal"}
            for st, w in sorted(weights.items())]


_MA_V2 = {
    "activist_stake_13d": 1.00, "ma_event_8k": 0.90, "merger_proxy": 0.85,
    "registration_s4": 0.75, "insider_activity_form4": 0.50,
    "institutional_positioning_13f": 0.40, "sector_news_gdelt": 0.30,
    "gov_revenue_concentration": 0.20, "maturity_wall": 0.05,
    "spread_trajectory": 0.05, "banker_local_note": 0.60,
}
_DCM_V2 = {
    "maturity_wall": 1.00, "spread_trajectory": 0.90, "registration_s4": 0.40,
    "institutional_positioning_13f": 0.25, "ma_event_8k": 0.20,
    "merger_proxy": 0.15, "activist_stake_13d": 0.10,
    "insider_activity_form4": 0.10, "sector_news_gdelt": 0.15,
    "gov_revenue_concentration": 0.30, "banker_local_note": 0.60,
}
_SECTOR_V2 = {
    "sector_news_gdelt": 1.00, "institutional_positioning_13f": 0.70,
    "spread_trajectory": 0.45, "merger_proxy": 0.40, "ma_event_8k": 0.40,
    "activist_stake_13d": 0.35, "maturity_wall": 0.30,
    "registration_s4": 0.30, "insider_activity_form4": 0.25,
    "gov_revenue_concentration": 0.35, "banker_local_note": 0.30,
}

WEIGHTS_V2 = (
    _w("PSP-MA", _MA_V2, "v2", "2026 origination policy")
    + _w("PSP-DCM", _DCM_V2, "v2", "2026 origination policy")
    + _w("PSP-SECTOR", _SECTOR_V2, "v2", "2026 origination policy")
)

# v1 is the PRIOR policy. It under-weighted activist stakes and over-weighted
# insider activity -- the change that motivated v2, and the change that makes
# a replay visibly reorder rather than merely re-run.
_MA_V1 = {**_MA_V2, "activist_stake_13d": 0.45, "insider_activity_form4": 0.85,
          "merger_proxy": 0.55}
_DCM_V1 = {**_DCM_V2, "spread_trajectory": 0.50, "maturity_wall": 0.80,
           "gov_revenue_concentration": 0.10}
_SECTOR_V1 = {**_SECTOR_V2, "sector_news_gdelt": 0.60,
              "institutional_positioning_13f": 0.90}

WEIGHTS_V1 = (
    _w("PSP-MA", _MA_V1, "v1", "pre-2026 policy: activist stakes under-weighted")
    + _w("PSP-DCM", _DCM_V1, "v1", "pre-2026 policy")
    + _w("PSP-SECTOR", _SECTOR_V1, "v1", "pre-2026 policy")
)

PROJECTION_PLANS = [
    {"projection_plan_id": "PP-IB-MA-v1", "perspective_id": "PSP-MA",
     "plan_version": "v1", "permitted_signal_types": sorted(_MA_V2),
     "provenance": "synthetic — internal"},
    {"projection_plan_id": "PP-IB-DCM-v1", "perspective_id": "PSP-DCM",
     "plan_version": "v1", "permitted_signal_types": sorted(_DCM_V2),
     "provenance": "synthetic — internal"},
    {"projection_plan_id": "PP-IB-SECTOR-v1", "perspective_id": "PSP-SECTOR",
     "plan_version": "v1", "permitted_signal_types": sorted(_SECTOR_V2),
     "provenance": "synthetic — internal"},
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    weights = WEIGHTS_V1 + WEIGHTS_V2
    print("Wave 16 — perspectives and weight vectors\n")
    print(f"  perspectives      {len(PERSPECTIVES):>4}")
    print(f"  signal classes    {len(SIGNAL_CLASSES):>4}")
    print(f"  weight rows       {len(weights):>4}  "
          f"({len(PERSPECTIVES)} x {len(SIGNAL_CLASSES)} x 2 versions)")
    print(f"  projection plans  {len(PROJECTION_PLANS):>4}")

    expected = len(PERSPECTIVES) * len(SIGNAL_CLASSES) * 2
    if len(weights) != expected:
        print(f"\n  FAIL: expected {expected} weight rows, built {len(weights)}. "
              f"A missing cell scores that signal as zero and silently changes "
              f"every ranking it appears in.")
        return 1

    print("\n  v1 vs v2 differences (these are what a replay reorders on):")
    v1 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V1}
    v2 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V2}
    for key in sorted(v1):
        if v1[key] != v2[key]:
            print(f"    {key[0]:12s} {key[1]:30s} {v1[key]:.2f} -> {v2[key]:.2f}")

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    out = SOURCES_ROOT / "screening" / "wave16_perspectives.json"
    out.write_text(json.dumps({
        "perspectives": PERSPECTIVES,
        "signal_classes": SIGNAL_CLASSES,
        "weights": weights,
        "projection_plans": PROJECTION_PLANS,
    }, indent=1))
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, then generate**

```bash
uv run --with pytest pytest validators/test_ib_rank.py -k "weights or half_life" -v
uv run generators/generate_ib_perspectives.py --dry-run
uv run generators/generate_ib_perspectives.py
```

Expected: 3 tests PASS; 66 weight rows (3 × 11 × 2); the v1→v2 diff lists 8 cells.

- [ ] **Step 5: Commit**

```bash
git add generators/generate_ib_perspectives.py validators/test_ib_rank.py sources/screening/wave16_perspectives.json
git commit -m "Three perspectives, two weight versions, one half-life per signal class

The divergence SF asks for is a property of the weight vectors, and it is
checkable before any signal data exists: if M&A and DCM weight the same types
the same way, no data will make the lists differ. Tested directly.

Half-life is per signal class per SE. Storing it per (perspective, type) would
write it three times and let the copies drift."
```

---

### Task 9: Verify the divergence prospect's DCM gap is measured

> **REWRITTEN 2026-08-24 by controller ruling.** This task originally engineered a
> debt ladder for **Boston Omaha Corp**. That choice was wrong: Boston Omaha is an
> activist holding company that *files* 13Ds about others — its freshest filing has
> `role=FILER`, so reading it as an activist stake *in* Boston Omaha inverts the
> signal. See `docs/wave16-design.md` §6.1.
>
> The prospect is now **Braemar Hotels & Resorts Inc.**, which already carries two
> `debt_instrument` rows maturing **2043** and **2045** with a flat 105–141 bp
> spread band across the window. **The §F condition is already true in loaded
> data**, so this task VERIFIES and DOCUMENTS it instead of generating anything.
>
> Do not create `generators/generate_boston_omaha_debt.py`. Write
> `validators/test_divergence_prospect.py` asserting, against the live stores:
>   * the prospect has >= 2 `debt_instrument` rows (a ladder, not a single bond)
>   * every maturity is beyond `2028-08-24` (no wall inside the DCM horizon)
>   * >= 1 in-window `spread_observation` exists AND the band is narrow —
>     `max(spread_bp) - min(spread_bp) < 50` — so "flat" is MEASURED, not absent
>   * the prospect has >= 1 Schedule 13D filing with `role == "SUBJECT"` inside the
>     12-month window
>   * the COMPARATOR (Anywhere Real Estate) has >= 1 maturity inside 2028-08-24 and
>     a spread band > 100 bp, so the contrast is measured on both sides
> Each assertion must name a count it computed, never read a stored flag.

**Removed in the final fix wave (2026-08-25).** This section used to carry the full retracted `generators/generate_boston_omaha_debt.py` source below the rewritten banner above -- a generator this project was explicitly told not to create, left sitting in the plan as if it were still live. The banner above is the authoritative account of Task 9; nothing below it was ever built. See `validators/test_divergence_prospect.py` for what was actually written instead.

---

### Task 10: Assemble the opportunity signals

**Files:**
- Create: `generators/generate_opportunity_signals.py`
- Output: `sources/screening/wave16_signals.json`

**Interfaces:**
- Consumes: `wave16_13d.json`, the 8-K item artifact, `wave16_merger_docs.json`,
  `wave16_usaspending.json`, `wave16_divergence_debt.json`, plus Postgres
  `institutional_holder`, `gdelt_mention`, `spread_observation`, `debt_instrument`.
- Produces: `{"signals": [{"signal_id","lei","signal_type","observed_at",
  "asserted_at","magnitude","source_ref","supersedes","provenance"}]}`.

- [ ] **Step 1: Write the failing test**

```python
def test_real_signal_dates_are_never_shifted():
    """A filing date is a public fact.

    Dating a real 13D into the demo window to make the window look full is
    fabrication, and it would be invisible: the count rises, the provenance
    still says `public`, and the date still looks like a date.
    """
    import json
    from pathlib import Path

    from generators.generate_opportunity_signals import build

    doc = build()
    filings = {f["accession"]: f["filing_date"] for f in json.loads(
        Path("sources/screening/wave16_13d.json").read_text())["filings"]}

    checked = 0
    for s in doc["signals"]:
        if s["signal_type"] == "activist_stake_13d" and s["source_ref"] in filings:
            assert s["observed_at"] == filings[s["source_ref"]], (
                f"{s['signal_id']} was re-dated: filing says "
                f"{filings[s['source_ref']]}, signal says {s['observed_at']}")
            checked += 1
    assert checked >= 5, f"only {checked} real 13D signals to check"


def test_synthetic_signals_stay_inside_the_window():
    """Real dates are honoured; SYNTHETIC ones are dated into the 12-month
    window SF describes, so the window is full without anything being moved."""
    from ccf.config import IB_WINDOW_END, IB_WINDOW_START
    from generators.generate_opportunity_signals import build

    doc = build()
    synthetic = [s for s in doc["signals"] if s["provenance"] != "public"]
    assert synthetic, "no synthetic signals at all"
    out = [s for s in synthetic
           if not IB_WINDOW_START <= s["observed_at"] <= IB_WINDOW_END]
    assert not out, f"{len(out)} synthetic signals outside the window: {out[:3]}"


def test_amendments_supersede_their_parent():
    """A SCHEDULE 13D/A supersedes the 13D it amends. SE names supersession as
    a trigger, and the estate's convention is supersession-not-overwrite."""
    from generators.generate_opportunity_signals import build

    doc = build()
    amendments = [s for s in doc["signals"] if s.get("supersedes")]
    assert amendments, "no amendment superseded anything"
    ids = {s["signal_id"] for s in doc["signals"]}
    dangling = [s["signal_id"] for s in amendments if s["supersedes"] not in ids]
    assert not dangling, f"supersedes points at nothing: {dangling[:3]}"
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -k "signal" -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the generator**

Key requirements the implementer must satisfy (the module docstring should state
each):

- **Activist-stake signals are built ONLY from filings with `role == "SUBJECT"`,
  and the FILER rows are counted and reported as dropped.** A Schedule 13D is
  filed *by* an activist *about* a subject company. Of the 963 fetched filings,
  **44 are rows where our own anchor is the FILER** — it took a stake in someone
  else. Reading those as "an activist took a stake in this anchor" inverts the
  signal completely, and it is not hypothetical: the product's original
  centrepiece prospect was chosen on exactly such a filing. Rows with
  `role == "UNKNOWN"` are also excluded (492 of them, all pre-2011, where EDGAR's
  archive predates the header layout) — an UNKNOWN is not a SUBJECT.
- **`public` signals carry the real filing date** in `observed_at`, verbatim from
  the source artifact. No arithmetic on it, ever.
- **Exclude any signal whose `observed_at` is after `AS_OF_IB`, and COUNT what you
  dropped.** `fetch_schedule13d.py` applies no date filter at all — its artifact
  says so — so a filing dated after the pinned as-of can reach this generator. It
  must not become a signal: `ccf.ib_rank.decay()` clamps negative age to `1.0`, so
  a future-dated filing would score the MAXIMUM possible weight rather than being
  ignored, and would dominate every ranking it appears in. The clamp is correct —
  it exists to stop clock skew amplifying a signal past 1.0 — but it is a cap, not
  a filter, and it must not be relied on as one.
- **`asserted_at`** is `AS_OF_IB` for signals derived at load time, and the filing
  date for signals whose assertion is the filing itself.
- **`synthetic — internal`** signals (banker notes, positioning deltas) are dated
  uniformly across `IB_WINDOW_START`..`IB_WINDOW_END` using a seeded RNG so a
  rerun reproduces the same dates.
- **Amendments** (`SCHEDULE 13D/A`, `SC 13D/A`) set `supersedes` to the
  `signal_id` of the most recent prior filing by the same subject.
- **`magnitude`** is normalised to `[0, 1]` per signal type so weights are
  comparable across types — a 13D is `1.0`, a maturity wall is
  `min(1, face_amount_maturing_within_24m / total_face)`, a spread signal is the
  90-day change in `spread_bp` scaled by 200bp.
- The **`banker_local_note`** signal type is produced in Task 13, not here.
- Print a per-type table and **fail loudly** if any type produced zero rows —
  a silently absent type scores as zero for every entity and changes every
  ranking it should have appeared in.

- [ ] **Step 4: Run tests, then generate**

```bash
uv run --with pytest pytest validators/test_ib_rank.py -k "signal" -v
uv run generators/generate_opportunity_signals.py --dry-run
uv run generators/generate_opportunity_signals.py
```

Expected: ≥600 signals across ≥10 types, none of them zero.

- [ ] **Step 5: Commit**

```bash
git add generators/generate_opportunity_signals.py validators/test_ib_rank.py sources/screening/wave16_signals.json
git commit -m "Assemble the opportunity signals, real dates intact

A filing date is a public fact. Re-dating a real 13D into the demo window to
make it look full would be invisible -- the count rises, provenance still says
public, and the date still looks like a date -- so it is a test, not a comment."
```

---

### Task 11: Load Postgres

**Files:**
- Create: `loaders/load_postgres_wave16.py`

**Interfaces:**
- Consumes: `wave16_perspectives.json`, `wave16_divergence_debt.json`,
  `wave16_usaspending.json`, `wave16_mandates.json`.
- Produces: tables `ib_perspective`, `ib_signal_class`, `perspective_weight`,
  `mandate`, `gov_contract_concentration`; extends `debt_instrument`,
  `spread_observation`, `projection_plan`.

- [ ] **Step 1: Write the DDL**

```python
SCHEMA = f'''
CREATE TABLE IF NOT EXISTS "{S}".ib_perspective (
    perspective_id  TEXT PRIMARY KEY,
    label           TEXT NOT NULL,
    ranks_on        TEXT NOT NULL,
    provenance      TEXT NOT NULL
);

-- lambda_c lives HERE and only here. Storing it per (perspective, signal_type)
-- would write every value three times and let the copies drift silently.
CREATE TABLE IF NOT EXISTS "{S}".ib_signal_class (
    signal_type     TEXT PRIMARY KEY,
    half_life_days  INTEGER NOT NULL CHECK (half_life_days > 0),
    note            TEXT NOT NULL,
    provenance      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".perspective_weight (
    perspective_id  TEXT NOT NULL REFERENCES "{S}".ib_perspective(perspective_id),
    signal_type     TEXT NOT NULL REFERENCES "{S}".ib_signal_class(signal_type),
    weight_version  TEXT NOT NULL,
    weight          NUMERIC NOT NULL CHECK (weight >= 0),
    rationale       TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (perspective_id, signal_type, weight_version)
);

CREATE TABLE IF NOT EXISTS "{S}".mandate (
    mandate_id      TEXT PRIMARY KEY,
    lei             TEXT NOT NULL,
    mandate_type    TEXT NOT NULL,
    stage           TEXT NOT NULL,
    opened_date     TEXT NOT NULL,
    stated_appetite TEXT,
    last_outcome    TEXT,
    provenance      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".gov_contract_concentration (
    lei             TEXT NOT NULL,
    recipient_name  TEXT NOT NULL,
    award_id        TEXT NOT NULL,
    awarding_agency TEXT,
    start_date      TEXT,
    obligated_usd   NUMERIC,
    -- USASpending has no LEI and no CIK. Every row is a name judgement, and
    -- says so rather than presenting itself as a resolved join.
    match_band      TEXT NOT NULL CHECK (match_band IN ('exact','verified-subsidiary')),
    verified_against TEXT NOT NULL,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (lei, award_id)
);
'''
```

- [ ] **Step 2: Write the upserts, keyed so a rerun cannot renumber**

Every `ON CONFLICT` target is the natural key, never a row position:

```python
cur.executemany(
    f'INSERT INTO "{S}".perspective_weight '
    "(perspective_id, signal_type, weight_version, weight, rationale, provenance) "
    "VALUES (%s,%s,%s,%s,%s,%s) "
    "ON CONFLICT (perspective_id, signal_type, weight_version) DO UPDATE SET "
    "weight = EXCLUDED.weight, rationale = EXCLUDED.rationale",
    weight_rows,
)
```

`debt_instrument` and `spread_observation` are **other waves' tables**. Insert
only new `BOC-*` / engineered rows, `ON CONFLICT (instrument_id) DO UPDATE`, and
**never** `DELETE` or re-key existing rows — four loaders on `main` have silently
rewritten another wave's rows by assuming position.

- [ ] **Step 3: Run, then prove idempotency by naming a value**

```bash
uv run loaders/load_postgres_wave16.py --dry-run
uv run loaders/load_postgres_wave16.py
uv run python -c "
from ccf.config import pg_connect, PG_SCHEMA_V2 as S
with pg_connect() as cn, cn.cursor() as cu:
    cu.execute(f\"select weight, rationale from {S}.perspective_weight where perspective_id='PSP-MA' and signal_type='activist_stake_13d' and weight_version='v1'\")
    print('BEFORE', cu.fetchone())
"
uv run loaders/load_postgres_wave16.py
uv run python -c "
from ccf.config import pg_connect, PG_SCHEMA_V2 as S
with pg_connect() as cn, cn.cursor() as cu:
    cu.execute(f\"select weight, rationale from {S}.perspective_weight where perspective_id='PSP-MA' and signal_type='activist_stake_13d' and weight_version='v1'\")
    print('AFTER ', cu.fetchone())
"
```

Expected: identical `(0.45, 'pre-2026 policy: activist stakes under-weighted')`.
A row count would not notice `rationale` being blanked; this does.

- [ ] **Step 4: Commit**

```bash
git add loaders/load_postgres_wave16.py
git commit -m "Load the IB perspective, weight and mandate layer"
```

---

### Task 12: Load Fluree

**Files:**
- Create: `loaders/load_fluree_wave16.py`

**Interfaces:**
- Produces: `ex:OpportunitySignal` instances; `ex:signalAbout`, `ex:coveredBy`,
  `ex:comparableTo`, `ex:comparabilityBasis` assertions.

- [ ] **Step 1: Write the failing test**

```python
def test_fluree_wave16_dates_are_plain_strings():
    """Fluree 4.1.4 corrupts xsd:date literals on write: 2026-01-02 reads back
    as 1972-01-01 (known-issues 19.4). The obvious 'improvement' to this loader
    is to give dates a proper type, which would silently destroy every date it
    touched -- triple count unchanged, predicate unchanged, value still shaped
    like a date."""
    from pathlib import Path

    src = Path("loaders/load_fluree_wave16.py").read_text()
    assert "xsd:date" not in src, "typed date literals corrupt silently in Fluree 4.1.4"
    assert "^^" not in src, "no typed literals at all on this ledger"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_fluree_wave16_dates_are_plain_strings -v`
Expected: FAIL — file does not exist

- [ ] **Step 3: Write the loader**

Requirements the module docstring must state:

- Node IRIs follow the estate pattern: `http://example.org/fibo/OPPSIG-{signal_id}`.
- **Type explicitly.** Fluree runs without reasoning, so a query for
  `ex:OpportunitySignal` returns only nodes explicitly typed as one — assert the
  type on every node rather than relying on any superclass.
- **All dates are plain strings.** No `xsd:date`, no `^^` anywhere.
- `ex:comparableTo` carries `ex:comparabilityBasis` naming the derivation
  (`"shared SIC 6199 + size band 2"`), so "comparable" is inspectable.
- `ex:coveredBy` joins prospect → `banker_id`, matching the Postgres roster key
  (not a display name — see Task 3).
- Idempotency: retract-then-assert per subject, scoped **by subject IRI**, never
  a blind predicate-wide delete that would take another wave's assertions with it.

- [ ] **Step 4: Run and verify counts**

```bash
uv run --with pytest pytest validators/test_ib_rank.py::test_fluree_wave16_dates_are_plain_strings -v
uv run loaders/load_fluree_wave16.py --dry-run
uv run loaders/load_fluree_wave16.py
uv run loaders/dump_fluree.py    # must report 0 typed literals and exit 0
```

- [ ] **Step 5: Commit**

```bash
git add loaders/load_fluree_wave16.py validators/test_ib_rank.py
git commit -m "Load opportunity signals and coverage edges into Fluree

Dates are plain strings. Fluree 4.1.4 corrupts xsd:date on write and no count
in the estate would see it: triple count unchanged, predicate unchanged, value
still shaped like a date. Asserted as a test rather than a comment."
```

---

### Task 13: Load MongoDB and extend SQLite

**Files:**
- Create: `loaders/load_mongo_wave16.py`, `loaders/load_sqlite_wave16.py`

- [ ] **Step 1: Write the failing test for the note-flip requirement**

```python
def test_at_least_five_notes_are_rank_changing_by_construction():
    """SF: ~50 notes, >= 5 of which CHANGE A RANKING when included.

    Counting 50 notes proves nothing about the five. This checks the
    generator's own claim; `validators/ib_rank.py` proves the effect by
    ranking twice and diffing the order.
    """
    import sqlite3

    from ccf.config import REPO_ROOT

    con = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    total = con.execute("SELECT COUNT(*) FROM prospect_note").fetchone()[0]
    flagged = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE rank_changing = 1"
    ).fetchone()[0]
    assert total >= 50, f"only {total} notes"
    assert flagged >= 5, f"only {flagged} notes marked rank-changing"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py::test_at_least_five_notes_are_rank_changing_by_construction -v`
Expected: FAIL — `no such column: rank_changing`

- [ ] **Step 3: Extend the SQLite schema and rows**

`load_sqlite_wave16.py` must:

- `ALTER TABLE prospect_note ADD COLUMN signal_type TEXT` (always
  `banker_local_note`), `materiality TEXT`, `rank_changing INTEGER DEFAULT 0`.
- Grow the table from 18 to ~50 rows, every one carrying a `banker_id` that
  exists in the Postgres roster (Task 3's invariant must still hold afterwards —
  re-run its test).
- Mark ≥ 5 notes `rank_changing = 1`, each on a prospect sitting **just below a
  rank boundary** for its banker's perspective, with `materiality = 'high'` so
  the note's weighted contribution is large enough to cross it. The flag is a
  **claim**; Task 14 proves it.
- Add ≥ 2 more `restricted_list` rows only if fewer than 2 currently-restricted
  entities appear in any banker's coverage. Check first:

```bash
uv run python -c "
import sqlite3
from ccf.config import pg_connect, PG_SCHEMA_V2 as S, REPO_ROOT
sq=sqlite3.connect(REPO_ROOT/'data/departmental.sqlite')
r={x[0] for x in sq.execute('select lei from restricted_list where removed_date is null')}
with pg_connect() as cn, cn.cursor() as cu:
    cu.execute(f'select distinct lei from {S}.coverage_assignment')
    cov={x[0] for x in cu.fetchall()}
print('restricted AND covered:', sorted(r & cov))
"
```

Expected today: Charter, BGC, SP Plus, American Healthcare REIT — already ≥ 2, so
no new rows are needed.

- [ ] **Step 4: Load the merger documents into Mongo**

`load_mongo_wave16.py` reads `wave16_merger_docs.json`, inserts into the existing
`document` collection with `doc_type` set (**note:** all 178 existing documents
have `doc_type: None` — set it for the new ones and record the pre-existing gap in
`known-issues.md` rather than back-filling another wave's rows), and writes
passage spans into `passage` with `startOffset`/`endOffset` and a
`passageSha256`, matching the Wave 13a/15 convention.

- [ ] **Step 5: Run everything and commit**

```bash
uv run loaders/load_sqlite_wave16.py --dry-run && uv run loaders/load_sqlite_wave16.py
uv run loaders/load_mongo_wave16.py --dry-run && uv run loaders/load_mongo_wave16.py
uv run --with pytest pytest validators/test_ib_rank.py -v
git add loaders/load_sqlite_wave16.py loaders/load_mongo_wave16.py validators/test_ib_rank.py
git commit -m "Extend the departmental notes and load the merger corpus"
```

---

### Task 14: The ranking instrument

**Files:**
- Create: `ccf/ib_rank.py` (pure arithmetic, no I/O)
- Create: `validators/ib_rank.py` (the four §F floors)

**Interfaces:**
- `ccf.ib_rank.score(signals, weights, half_lives, as_of) -> dict[str, float]`
- `ccf.ib_rank.rank(scores) -> list[tuple[str, float]]` — descending, ties broken
  by LEI ascending so the order is deterministic.

- [ ] **Step 1: Write the failing tests for the arithmetic**

```python
def test_decay_halves_at_one_half_life():
    from ccf.ib_rank import decay

    assert decay(age_days=0, half_life_days=30) == 1.0
    assert abs(decay(age_days=30, half_life_days=30) - 0.5) < 1e-9
    assert abs(decay(age_days=60, half_life_days=30) - 0.25) < 1e-9


def test_ranking_is_deterministic_under_ties():
    """Two entities with identical scores must always order the same way, or
    a replay diff reports a change that is really just dict iteration."""
    from ccf.ib_rank import rank

    assert rank({"BBB": 1.0, "AAA": 1.0}) == [("AAA", 1.0), ("BBB", 1.0)]


def test_future_dated_signals_are_rejected_not_capped():
    """`decay()` clamps negative age to 1.0, which is a CAP, not a FILTER.

    A signal dated after the as-of instant would therefore score the maximum
    possible weight and dominate the ranking. The clamp is right -- it stops
    clock skew amplifying a signal past 1.0 -- but the scorer must refuse
    future-dated input rather than silently scoring it at full strength.
    """
    import pytest

    from ccf.ib_rank import score

    with pytest.raises(ValueError, match="after as_of"):
        score(signals=[{"lei": "X", "signal_type": "k",
                        "observed_at": "2026-09-01", "magnitude": 1.0}],
              weights={"k": 1.0}, half_lives={"k": 30}, as_of="2026-08-24")


def test_score_ignores_signal_types_absent_from_the_weight_vector():
    """A signal type with no weight row must contribute ZERO and be reported,
    not silently treated as weight 1.0."""
    from ccf.ib_rank import score

    out = score(
        signals=[{"lei": "X", "signal_type": "unweighted", "observed_at": "2026-08-24",
                  "magnitude": 1.0}],
        weights={"known": 1.0}, half_lives={"known": 30, "unweighted": 30},
        as_of="2026-08-24")
    assert out["X"] == 0.0
```

- [ ] **Step 2: Run and watch them fail**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -k "decay or deterministic or absent" -v`
Expected: FAIL — `ModuleNotFoundError: ccf.ib_rank`

- [ ] **Step 3: Write `ccf/ib_rank.py`**

```python
"""Wave 16 — the scoring arithmetic, and nothing else.

## What this is not

This is NOT the SDK's Rank Operator. An Operator is a runtime SDK entity --
resolved through a registry, ordered by the Operator Plan DAG Generator,
executed in the Data Plane, serving a principal at request time
(`cognitive-context-fabric/ccf-architecture`, L4). This module registers
nothing, composes into no plan, serves no principal, and emits no contract.

It exists because the per-perspective weight vectors are OURS to produce (SC
assigns them to Postgres as `synthetic — internal`), and shipping a weight
vector without confirming it separates the M&A and DCM orderings would be a
table of numbers and a promise.

Pure functions, no I/O. `validators/ib_rank.py` does the reading.
"""
from __future__ import annotations

import datetime as _dt


def decay(*, age_days: float, half_life_days: float) -> float:
    """`R(t) = R0 * (1/2) ** (age / lambda_c)` per the CCF half-life formula.

    A signal observed in the future (negative age) is clamped to 1.0 rather
    than amplified -- a clock skew should not make a signal count double.
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def score(*, signals, weights, half_lives, as_of: str) -> dict[str, float]:
    """Weighted, decayed score per LEI.

    `weights` maps signal_type -> weight for ONE perspective and ONE weight
    version. A signal whose type is absent from `weights` contributes zero;
    it is never defaulted to 1.0, which would let a missing weight row
    silently dominate a ranking.
    """
    at = _dt.date.fromisoformat(as_of)
    out: dict[str, float] = {}
    for s in signals:
        # Refuse, do not cap. `decay()` clamps negative age to 1.0 so clock
        # skew cannot amplify a signal past full strength -- but that is a
        # CAP. A signal genuinely dated after the as-of instant would score
        # the maximum and dominate the ranking, so it is an error here
        # rather than something to silently absorb.
        if s["observed_at"] > as_of:
            raise ValueError(
                f"signal {s.get('signal_id', s['lei'])} observed_at "
                f"{s['observed_at']} is after as_of {as_of}")
        weight = weights.get(s["signal_type"])
        if weight is None:
            out.setdefault(s["lei"], 0.0)
            continue
        half_life = half_lives[s["signal_type"]]
        age = (at - _dt.date.fromisoformat(s["observed_at"])).days
        contribution = (
            weight * float(s.get("magnitude", 1.0))
            * decay(age_days=age, half_life_days=half_life))
        out[s["lei"]] = out.get(s["lei"], 0.0) + contribution
    return out


def rank(scores: dict[str, float]) -> list[tuple[str, float]]:
    """Descending by score, ties broken by LEI ascending.

    The tie-break is not cosmetic: without it, two equal scores order by dict
    insertion and a replay diff reports a change that is really just
    iteration order.
    """
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
```

- [ ] **Step 4: Run and watch them pass**

Run: `uv run --with pytest pytest validators/test_ib_rank.py -k "decay or deterministic or absent" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write `validators/ib_rank.py`** — the four floors

It must:

1. Read weights, half-lives, signals, coverage and the restricted list **from the
   stores on every run**. Never a stored score, a cached rank, or a boolean flag —
   including `prospect_note.rank_changing`, which is a claim to be tested, not
   read.
2. Rank at `AS_OF_IB`, never `date.today()`.
3. Emit `[PASS]`/`[FAIL]` lines in the `conditions.py` house style and exit
   non-zero on any failure.

The four checks:

| Check | How it is proved |
|---|---|
| **Divergence** | Rank the shared candidate set under `PSP-MA` and `PSP-DCM` at the same `as_of`, same signals. Assert ≥ 1 LEI with `ma_rank <= 3` and `dcm_rank > 20`. Print both lists side by side — §F calls this the most persuasive output in the spec. |
| **Containment** | For each banker whose coverage includes a restricted LEI, build the candidate set and assert the LEI is **absent**. Then assert the output carries **no marker** naming a suppressed candidate — a suppressed row with a marker tells the banker exactly what the wall exists to hide. |
| **Note materiality** | Rank each affected banker's set twice — once with `banker_local_note` signals, once without — and count LEIs whose **position** changed. Assert ≥ 5. Recompute; never read `rank_changing`. |
| **Weight replay** | Rank one candidate set under `weight_version='v1'` and `'v2'` with `as_of` **held fixed**, and assert the orders differ. Holding `as_of` fixed is the whole point: otherwise a reorder cannot be attributed to the weights. |

- [ ] **Step 6: Test the checker with known-present and known-absent fixtures**

```python
def test_divergence_check_can_actually_fail():
    """A check that cannot fail is decoration. Two checks in this estate hid
    for seven waves each because nobody fed them a known-absent input.

    Feed the divergence check a signal set where M&A and DCM agree perfectly,
    and require it to report FAILURE.
    """
    from validators.ib_rank import divergence_holds

    agreeing = [
        {"lei": f"E{i:03d}", "signal_type": "activist_stake_13d",
         "observed_at": "2026-08-24", "magnitude": 1.0 - i / 100}
        for i in range(30)
    ]
    identical = {"activist_stake_13d": 1.0}
    half = {"activist_stake_13d": 30}

    assert not divergence_holds(
        signals=agreeing, ma_weights=identical, dcm_weights=identical,
        half_lives=half, as_of="2026-08-24"), \
        "identical weights cannot produce a divergent ranking"


def test_divergence_check_passes_on_a_known_divergent_set():
    """The other half. A checker that always says FAIL is equally useless."""
    from validators.ib_rank import divergence_holds

    signals = [
        {"lei": "DIVERGENT", "signal_type": "activist_stake_13d",
         "observed_at": "2026-08-24", "magnitude": 1.0},
    ] + [
        {"lei": f"E{i:03d}", "signal_type": "maturity_wall",
         "observed_at": "2026-08-24", "magnitude": 1.0 - i / 100}
        for i in range(30)
    ]
    assert divergence_holds(
        signals=signals,
        ma_weights={"activist_stake_13d": 1.0, "maturity_wall": 0.05},
        dcm_weights={"activist_stake_13d": 0.10, "maturity_wall": 1.0},
        half_lives={"activist_stake_13d": 30, "maturity_wall": 90},
        as_of="2026-08-24")
```

- [ ] **Step 7: Run everything**

```bash
uv run --with pytest pytest validators/test_ib_rank.py -v
uv run validators/ib_rank.py
```

Expected: all tests PASS; the validator prints both ranked lists and exits 0.

- [ ] **Step 8: Commit**

```bash
git add ccf/ib_rank.py validators/ib_rank.py validators/test_ib_rank.py
git commit -m "Prove the weight vectors separate the perspectives

This is not the Rank Operator. It registers nothing, composes into no plan,
serves no principal, and emits no contract -- it recomputes an ordering from
the stores to check arithmetic that is ours to ship.

Both directions are tested: identical weights must FAIL the divergence check,
and a known-divergent set must PASS it. A check that cannot fail is decoration,
and two in this estate hid for seven waves each."
```

---

### Task 15: Register the product and map §C

**Files:**
- Modify: `validators/conditions.py`, `validators/spec_coverage.py`,
  `validators/partition.py`

- [ ] **Step 1: Add the §F conditions to `conditions.py`**

Inside `collect()`, following the house pattern:

```python
        # --- #18 ib-opportunity-synthesis --------------------------------
        # The four floors that carry a CONDITION. The envelope figures --
        # ~40 bankers, ~200 prospects, ~600 signals, ~50 notes -- are shape,
        # not targets (Dave, 2026-08-24), so they are not registered as
        # floors. These four are.
        checks.append(Check(
            "ib-opportunity-synthesis", "real Schedule 13D filings", 5,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".signal_event '
                           "WHERE signal_type = 'activist_stake_13d' "
                           "AND provenance = 'public'"),
        ))
        checks.append(Check(
            "ib-opportunity-synthesis", "weight-vector versions", 2,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT weight_version) '
                           f'FROM "{S}".perspective_weight'),
        ))
        checks.append(Check(
            "ib-opportunity-synthesis", "restricted entities inside coverage", 2,
            pg_scalar(cur, "SELECT COUNT(*) FROM ("
                           f'  SELECT DISTINCT c.lei FROM "{S}".coverage_assignment c '
                           "  JOIN restricted USING (lei)) x"),
            note="candidate-set absence proved by validators/ib_rank.py",
        ))
```

The two conditions that cannot be expressed as a `COUNT` — divergence and note
materiality — are registered with `actual` supplied by importing
`validators.ib_rank`, so a broken ranking surfaces as **FAIL**, not SKIP.

- [ ] **Step 2: Map all 18 §C rows in `spec_coverage.py`**

Add `"ib-opportunity-synthesis"` to `PRODUCTS`, and an `IB_OPPORTUNITY` list of
`Mapping(...)` — one per §C row. The S-1 row is mapped as a **named gap** with its
evidence:

```python
    Mapping(
        match="IPO and merger registration pipeline",
        state="PARTIAL",
        detail=("S-4 loaded (6 documents); S-1 NOT fetched. Probed 2026-08-24 "
                "across 53 anchors: 43 S-1 filings lifetime, ZERO since 2023. "
                "The cast are established issuers who do not file IPO "
                "registrations -- a fact about the cast, not a gap in the "
                "fetch."),
        probe=lambda: mongo_count("document", {"doc_type": {"$in": ["S-4", "S-4/A"]}}),
    ),
```

- [ ] **Step 3: Add partition entries**

For each new element, assert it lives **only** in the store §C names — and that it
is **absent** from the others. `partition.py` is what catches a silently-wrong
load.

- [ ] **Step 4: Run the full suite**

```bash
uv run validators/conditions.py
uv run validators/partition.py
uv run validators/spec_coverage.py    # exits 1 BY DESIGN
uv run validators/ib_rank.py
uv run --with pytest pytest validators/ -q
```

Read the **PASS count** from `conditions.py`, never the "0 failed" line — a SKIP
hides a broken query.

- [ ] **Step 5: Commit**

```bash
git add validators/conditions.py validators/spec_coverage.py validators/partition.py
git commit -m "Register ib-opportunity-synthesis: 18 of 21 products

Only the four floors that carry a condition are registered. The envelope
figures are shape, not targets. Divergence and note-materiality come from
validators.ib_rank so a broken ranking is a FAIL, not a SKIP."
```

---

### Task 16: Documentation and the vault mirror

**Files:**
- Modify: `docs/ccf_dataprep_v2.md`, `docs/HANDOFF.md`, `docs/known-issues.md`
- Create: an exchange bundle in `~/.agent-exchange/ccf-dataprep/outbox/`

- [ ] **Step 1: Update `docs/ccf_dataprep_v2.md`**

Entity tables, file names, counts, and the binding table's three new terms. Every
restated count must be **counted**, not remembered.

- [ ] **Step 2: Record the found defects in `known-issues.md`**

Three, each with its evidence:
1. `prospect_note.banker` held a display name; 3 of 4 absent from the roster,
   the 4th ambiguous across 4 bankers. **FIXED (Task 3).**
2. All 178 existing Mongo `document` rows carry `doc_type: None`. **OPEN** — not
   back-filled, because back-filling another wave's rows is how positional
   defects happen.
3. `SC 13D` matches nothing after 2024-12-06 because the SEC renamed the form.
   Any fetcher matching a form-name literal has this failure mode.

- [ ] **Step 3: Send the corrected mirror through the exchange**

Read **section 5 of the `obsidian-vault-access` skill** before the first send. The
message directory is `<YYYY-MM-DDTHH-MM-SSZ>-<slug>` with **hyphens in the time,
never colons**, or the vault's reconciler rejects it visibly but unsent. A
published bundle is immutable — a correction is a **new** bundle naming what it
supersedes.

The bundle carries the binding table with the three new terms, and states plainly:
**three terms added, mirror needs refreshing.**

- [ ] **Step 4: Update `docs/HANDOFF.md`** with the green counts, read from the
      validators rather than restated.

- [ ] **Step 5: Commit and merge**

```bash
git add docs/
git commit -m "Close Wave 16: 18 of 21 products, and three defects the build surfaced"
```

---

## Self-review

**Spec coverage.** All 18 §C rows have a task: 13D (4), 8-K 2.01 (5), proxies and
S-4 (6), USASpending (7), perspectives/weights/projection plans (8), maturity
ladder and spread (9, 11), signals (10), positioning and GDELT (10, inherited),
Fluree edges (12), Mongo passages (13), SQLite notes and restricted list (13),
coverage portfolio (inherited, re-keyed in 3). The S-1 row is mapped PARTIAL with
evidence. All four §F floors are proved in Task 14, and the two that no `COUNT`
can express are registered through `validators.ib_rank` so they fail loudly.

**Placeholders.** `DIVERGENCE_LEI = "<LEI>"` in Task 9 is resolved by the shell
command in that task's Step 3 — the only deliberate substitution, and it is
executable rather than a TODO. Tasks 10, 12, 13 and 15 give requirements plus the
tests that gate them rather than full listings; each names its exact interfaces,
its failure modes, and its commands.

**Type consistency.** `score()`, `rank()`, `decay()` keep the same keyword-only
signatures in Task 14's tests and implementation. `divergence_holds()` takes the
same keywords in both the checker and both fixture tests. `perspective_id` values
(`PSP-MA`, `PSP-DCM`, `PSP-SECTOR`) and `weight_version` values (`v1`, `v2`) are
identical across Tasks 8, 11, 14 and 15. `banker_id` is the join key in Tasks 3,
12 and 13 — never `banker`, never `full_name`.
