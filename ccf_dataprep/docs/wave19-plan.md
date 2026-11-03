# Wave 19 — `large-exposure-rwa-concentration` implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the source data for `large-exposure-rwa-concentration`, the
twenty-first and final Context Product, across all five datastores.

**Architecture:** Regime rule text is fetched from three public sources and
lands in MongoDB as passages with span offsets and embeddings. Group-forming
edges land in Fluree; **no connected group is ever stored anywhere**. Capital
and exposure stay in Postgres, where a units defect is repaired first. The
departmental workbook lands in SQLite. `validators/large_exposure.py`
recomputes every group and every utilisation from the stores on each run.

**Tech Stack:** Python 3.12 · `uv` · psycopg 3 · Fluree SPARQL over HTTP ·
pymongo · sqlite3 · `pypdf` · `ccf.fetch` for all public retrieval.

**Spec:** `docs/wave19-design.md` — read it before Task 1. Sections 3, 5 and 6
carry the measurements every task below depends on. The vault spec itself is
`get_article("context-products", "large-exposure-rwa-concentration")`.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Never build an Operator.** No request-time assembly, no plan resolution,
  no contract emission, no TTL enforcement. §D and §E of the vault spec are
  read for understanding only. `validators/large_exposure.py` is a build-time
  validator and must not grow into a shadow §D.
- **Store ownership is fixed by §C.** Fluree owns `R`/`T`/policy binding;
  Postgres owns `E` and policy reference; MongoDB owns passage-level `L`;
  SQLite owns departmental. Never duplicate an attribute into a store that
  does not own it.
- **Three provenance classes, labelled per element:** `public`,
  `synthetic — internal`, `synthetic — engineered`. Use the em dash; the
  estate's existing rows do.
- **Fluree SPARQL requires an explicit `FROM <fibo-v2>`** or the server
  returns HTTP 500. Read the ledger name from `ccf.config.FLUREE_LEDGER_V2`,
  never as a literal.
- **`?s <p> ?s` does not enforce equality** on this Fluree build. Use
  `FILTER(?s = ?o)`. `FILTER NOT EXISTS` is unaffected. known-issues §27.
- **Loaders must be idempotent.** `CREATE TABLE IF NOT EXISTS` plus
  `ON CONFLICT ... DO UPDATE`. You will reload many times.
- **Positional identity is a defect class.** Four loaders on `main` rewrite
  other waves' rows when a table grows. Before adding rows to any pre-existing
  table, check whether anything keys off row position or `ORDER BY` offset.
- **Money units:** `USD_THOUSANDS` for anything sourced from FDIC BankFind;
  plain dollars everywhere else. After Task 1 the `unit` column says which.
- **Testing:** `uv run pytest` is broken repo-wide. Use
  `uv run --with pytest pytest`. Read the PASS count from `conditions.py`
  itself, never the "0 failed" line.
- **Do not fetch `spec.edmcouncil.org` to prove a FIBO term exists.** It
  returns HTTP 200 for names that were never declared. Grep
  `sources/fibo/dev.fibo-quickstart.ttl` in subject position.
- **Embeddings are mandatory** for every passage this wave writes. known-issues
  §38 and §42 record 84 passages that carry none; do not grow that population.

---

## File structure

**Created:**

| Path | Responsibility |
|---|---|
| `generators/fetch_regime_text.py` | Fetch Reg O, CRR and PRA rule text with manifests |
| `generators/verify_fibo_wave19.py` | Subject-position FIBO check for this wave's terms |
| `generators/extract_regime_passages.py` | Segment rule text into passages with offsets |
| `generators/generate_dependency_edges.py` | The ≥4 engineered `economicallyDependentOn` edges |
| `generators/generate_insider_cases.py` | Invented Reg O insiders and their related interests |
| `generators/generate_limit_envelope.py` | Internal limit envelope and regime version history |
| `generators/generate_proposals.py` | The engineered proposal cases |
| `loaders/load_regime_mongo.py` | Regime text and methodology → MongoDB |
| `loaders/load_nic_hierarchy.py` | FFIEC NIC RSSD hierarchy → Fluree |
| `loaders/load_group_edges.py` | `connectedTo` + `economicallyDependentOn` → Fluree |
| `loaders/load_policy_fluree.py` | Limit envelope, regime versions, insider designations → Fluree |
| `loaders/load_wave19_postgres.py` | `unit` columns, proposals, ProjectionPlans |
| `loaders/load_limit_workbook.py` | Risk-department workbook → SQLite |
| `validators/large_exposure.py` | The recomputed floors |
| `validators/test_large_exposure.py` | Unit tests for the floors |
| `validators/test_capital_units.py` | Regression test for the units defect |

**Modified:** `validators/conditions.py`, `validators/partition.py`,
`validators/spec_coverage.py`, `loaders/load_reporting_bank.py`,
`docs/ccf_dataprep_v2.md`, `docs/spec-digest.md`, `docs/known-issues.md`,
`docs/HANDOFF.md`.

---

## Task 1 — Repair the capital units defect

`bank_capital.tier1_capital` and `member_call_report.*` are in **thousands of
dollars**; `facility.commitment_amount` is in dollars; nothing records either.
The existing CET1 ratio check cannot see this, because a ratio is
unit-invariant. Nothing downstream is safe until this is fixed.

**Files:**
- Modify: `loaders/load_reporting_bank.py`
- Create: `loaders/load_wave19_postgres.py`
- Create: `validators/test_capital_units.py`

**Interfaces:**
- Produces: `ccf_v2.bank_capital.unit` and `ccf_v2.member_call_report.unit`,
  both `text NOT NULL` valued `'USD_THOUSANDS'`; and
  `loaders/load_wave19_postgres.py::assert_capital_magnitudes(cur) -> None`,
  which raises `AssertionError` on a unit regression.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_capital_units.py
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pytest pytest validators/test_capital_units.py -q`
Expected: FAIL — `column "unit" does not exist`.

- [ ] **Step 3: Add the `unit` columns and the assertion helper**

Add to `loaders/load_reporting_bank.py`'s DDL string, inside both
`bank_capital` and (in `loaders/load_postgres_wave18.py`)
`member_call_report`. Because both tables already exist on `main`, the DDL
alone will not add the column — include the `ALTER`:

```python
# loaders/load_wave19_postgres.py
#!/usr/bin/env python3
"""Wave 19 Postgres — the units repair, proposals, and ProjectionPlans.

The units repair comes first and everything else in the wave depends on it.
`bank_capital` and `member_call_report` are sourced from FDIC BankFind, which
publishes in THOUSANDS of dollars. `facility.commitment_amount` is in dollars.
`large-exposure-rwa-concentration` divides one by the other on every figure it
produces, so an unrecorded unit is a 1,000x error in the whole product.

The check already on `bank_capital` verifies tier 1 / RWA against the filed
CET1 ratio. It passes with or without the defect, because a ratio is
unit-invariant -- both operands carry the same unit and it cancels. The
magnitude assertion below does not cancel, and that is the whole point of it.

    uv run loaders/load_wave19_postgres.py
"""
from __future__ import annotations

import sys

from ccf.config import PG_SCHEMA_V2 as S, pg_connect

UNIT_DDL = f"""
ALTER TABLE "{S}".bank_capital
    ADD COLUMN IF NOT EXISTS unit text NOT NULL DEFAULT 'USD_THOUSANDS';
COMMENT ON COLUMN "{S}".bank_capital.unit IS
    'Unit of every money column in this row. FDIC BankFind reports in '
    'thousands of dollars; ccf_v2.facility is in dollars. Recorded because '
    'the ratio checks on this table cannot observe the difference.';

ALTER TABLE "{S}".member_call_report
    ADD COLUMN IF NOT EXISTS unit text NOT NULL DEFAULT 'USD_THOUSANDS';
COMMENT ON COLUMN "{S}".member_call_report.unit IS
    'Unit of every money column in this row. See bank_capital.unit.';
"""

#: See docs/wave19-design.md section 3 for how this figure was chosen. It is
#: measured against the estate's own population, not guessed.
ASSETS_FLOOR_USD = 10_000_000_000
REPORTING_BANK_RSSD = "852218"
REPORTING_BANK_BAND_USD = (1_000_000_000_000, 10_000_000_000_000)


def assert_capital_magnitudes(cur) -> None:
    """Raise if any FDIC-sourced row's assets imply a lost 1,000x factor.

    Two tiers deliberately. A single JPM-class band would be a FALSE RED on
    the 16 peer banks, which span $159.8bn to $4.09tn; a single floor low
    enough for them would still catch every 1,000x error, because the wrong
    values top out at $4.09bn.
    """
    for table in ("bank_capital", "member_call_report"):
        cur.execute(f'SELECT rssd, total_assets, unit FROM "{S}".{table}')
        rows = cur.fetchall()
        if not rows:
            raise AssertionError(
                f"{table} is empty -- this assertion would pass vacuously")
        for rssd, assets, unit in rows:
            if unit != "USD_THOUSANDS":
                raise AssertionError(f"{table} {rssd}: unit {unit!r}")
            usd = float(assets) * 1000
            if usd < ASSETS_FLOOR_USD:
                raise AssertionError(
                    f"{table} {rssd}: assets ${usd/1e9:.1f}bn below the "
                    f"${ASSETS_FLOOR_USD/1e9:.0f}bn floor -- lost 1,000x?")

    lo, hi = REPORTING_BANK_BAND_USD
    cur.execute(f'SELECT total_assets, unit FROM "{S}".bank_capital '
                "WHERE rssd = %s", (REPORTING_BANK_RSSD,))
    bank_rows = cur.fetchall()
    if not bank_rows:
        raise AssertionError("no bank_capital rows for the reporting bank")
    for assets, unit in bank_rows:
        usd = float(assets) * 1000
        if not lo <= usd <= hi:
            raise AssertionError(
                f"reporting bank: ${usd/1e9:.1f}bn outside its band")


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(UNIT_DDL)
        conn.commit()
        assert_capital_magnitudes(cur)
    cur.execute(f'SELECT COUNT(*) FROM "{S}".bank_capital')
    rows = cur.fetchone()[0]
    cur.execute(f'SELECT COUNT(*) FROM "{S}".member_call_report')
    rows += cur.fetchone()[0]
    cur.execute(f'SELECT COUNT(DISTINCT rssd) FROM ('
                f'SELECT rssd FROM "{S}".bank_capital '
                f'UNION SELECT rssd FROM "{S}".member_call_report) u')
    institutions = cur.fetchone()[0]
    print(f"  units recorded and magnitudes asserted on {rows} rows "
          f"across {institutions} institutions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the loader, then the test**

Run: `uv run loaders/load_wave19_postgres.py`
Expected: `units recorded and magnitudes asserted on 28 rows across 16 institutions`

**Both figures are COUNTED by the code, never written into the string.** The
two tables **overlap** — RSSD 852218 is in `bank_capital` (12 quarters) *and*
is one of `member_call_report`'s 16 banks — so `1 + 16 = 17` is wrong, and any
hard-coded total is a claim nobody re-checks. Count the rows the assertion
actually looped over, and count `DISTINCT rssd` across the union.

Run: `uv run --with pytest pytest validators/test_capital_units.py -q`
Expected: **7 passed** (two of the five tests are parametrised over both tables). Step 5 adds two more, for 9.

- [ ] **Step 5: Prove the assertion can fail — without touching the data**

A floor you have never seen reject anything is a floor you have no evidence
about. But do **not** prove it with an `UPDATE` on the live estate, even inside
a transaction you mean to roll back: these are shared servers, one missing
`rollback()` divides real capital by 1,000, and the proof is available without
the risk.

`assert_capital_magnitudes` takes a cursor, so hand it a fake one:

```python
# append to validators/test_capital_units.py
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
```

Run: `uv run --with pytest pytest validators/test_capital_units.py -q`
Expected: **9 passed** — the seven above plus these two controls.

Both controls are required. A test that only proves rejection would pass for
an assertion that rejects every input, which is a broken floor, not a strict
one.

- [ ] **Step 6: Commit**

```bash
git add loaders/load_wave19_postgres.py validators/test_capital_units.py loaders/load_reporting_bank.py
git commit -m "Wave 19 Task 1: record capital units and assert a magnitude the ratio check cannot see"
```

---

## Task 2 — Fetch the regime text

Three sources, all probed live on 2026-08-27. **EUR-Lex is blocked** (HTTP 202
with a zero-byte body on every request including its homepage); CRR comes from
legislation.gov.uk instead.

**Files:**
- Create: `generators/fetch_regime_text.py`
- Creates on disk: `sources/regimes/manifest.json` and the payloads

**Interfaces:**
- Produces: `sources/regimes/` containing `reg-o-12cfr215.xml`,
  `crr-art-{392..403}-{2020-12-31,2021-12-31}.html`,
  `crr-art-395-2022-01-01.html` (the omission notice, kept as version-history
  evidence), `pra-large-exposures-{01-01-2020,01-01-2022,01-01-2026}.html`,
  `pra-ss16-13.html`, `pra-ss03-25.html`, each recorded in the manifest.

- [ ] **Step 1: Write the fetch script**

```python
# generators/fetch_regime_text.py
#!/usr/bin/env python3
"""Wave 19 Task 2 — the three large-exposure regimes, as citable text.

§C names EUR-Lex for CRR. **EUR-Lex does not work from here.** Measured
2026-08-27: every request returns HTTP 202 with a zero-byte body, including
`eur-lex.europa.eu/homepage.html`, with three user agents and with a cookie
jar; `publications.europa.eu` cellar content negotiation returns HTTP 400.
Recorded the way Wave 17 recorded FATF's 403 -- a measured fact with a date.

legislation.gov.uk carries CRR as assimilated UK law with full point-in-time
history, and it is BETTER than EUR-Lex for this product, because it records
the moment the regime changed hands: Articles 392-403 were omitted on
2022-01-01 by SI 2021/1078, when large exposures moved into the PRA Rulebook.
That is a REAL regime version boundary with a REAL effective date, which is
what §F's ">= 2 regime versions with distinct effective dates" asks for.

**The dates below are not interchangeable.** A fetch of the live CRR URL
returns an omission notice, not rule text. Measured, same day:

    2020-12-31   69,369 B   operative text present
    2021-12-31   69,337 B   operative text present
    2022-01-01   43,449 B   operative text ABSENT
    2023-01-01   43,410 B   operative text ABSENT

And the string "omitted" appears on ALL FOUR, because the textual-amendment
annotation rides along on the in-force versions too. A guard written as
`if "omitted" in html` flags every date and discriminates nothing. This script
asserts on the OPERATIVE SENTENCE and carries both controls.

    uv run generators/fetch_regime_text.py
"""
from __future__ import annotations

import re
import sys

from ccf.fetch import SourceManifest, fetch

#: The sentence that is present only while Article 395 is in force. Chosen
#: because it is the operative prohibition, not an annotation about it.
CRR_OPERATIVE = "shall not incur an exposure"

#: Positive and negative controls for the CRR fetch. If the in-force date
#: lacks the sentence, or the omitted date carries it, the source has changed
#: shape and every downstream citation is suspect.
CRR_CONTROL_IN_FORCE = "2021-12-31"
CRR_CONTROL_OMITTED = "2022-01-01"

CRR_IN_FORCE_DATES = ("2020-12-31", "2021-12-31")
CRR_ARTICLES = tuple(range(392, 404))
CRR_URL = "https://www.legislation.gov.uk/eur/2013/575/article/{art}/{date}"

ECFR_URL = ("https://www.ecfr.gov/api/versioner/v1/full/2026-01-01/"
            "title-12.xml?part=215")

PRA_ROOT = "https://www.prarulebook.co.uk"
PRA_VERSIONS = ("01-01-2020", "01-01-2022", "01-01-2026")
PRA_GUIDANCE = {
    "pra-ss16-13.html":
        f"{PRA_ROOT}/guidance/supervisory-statements/ss16-13---large-exposures",
    "pra-ss03-25.html":
        f"{PRA_ROOT}/guidance/supervisory-statements/"
        "ss03-25---identification-of-groups-of-connected-clients-for-large-"
        "exposures-purposes",
}


def text_of(path) -> str:
    """Tags stripped, whitespace collapsed. Enough to assert on a sentence."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", raw))


def main() -> int:
    manifest = SourceManifest(
        source="regimes",
        description=("Large-exposure regime text: Regulation O (eCFR), CRR "
                     "as assimilated UK law (legislation.gov.uk, EUR-Lex "
                     "blocked), and the PRA Rulebook Large Exposures Part"),
        licence="US government work; UK Open Government Licence v3.0",
    ).load()

    failures: list[str] = []

    print("Regulation O -- 12 CFR 215, eCFR versioner API")
    rego = fetch(ECFR_URL, manifest, "reg-o-12cfr215.xml")
    body = text_of(rego)
    for needle in ("$500,000", "unimpaired capital and unimpaired surplus"):
        if needle not in body:
            failures.append(f"Reg O text lacks {needle!r}")
    print(f"  {rego.name}  {rego.stat().st_size:,} B")

    print("\nCRR Articles 392-403 -- legislation.gov.uk, point-in-time")
    for date in CRR_IN_FORCE_DATES:
        for art in CRR_ARTICLES:
            fetch(CRR_URL.format(art=art, date=date), manifest,
                  f"crr-art-{art}-{date}.html")
        print(f"  {date}  {len(CRR_ARTICLES)} articles")

    # The omission notice, kept as evidence of the version boundary -- it is
    # version history, NOT rule text, and nothing may cite it as a provision.
    fetch(CRR_URL.format(art=395, date=CRR_CONTROL_OMITTED), manifest,
          f"crr-art-395-{CRR_CONTROL_OMITTED}.html")

    print("\n  controls:")
    in_force = text_of(manifest.directory /
                       f"crr-art-395-{CRR_CONTROL_IN_FORCE}.html")
    omitted = text_of(manifest.directory /
                      f"crr-art-395-{CRR_CONTROL_OMITTED}.html")
    if CRR_OPERATIVE not in in_force:
        failures.append(f"positive control: {CRR_CONTROL_IN_FORCE} lacks the "
                        f"operative sentence")
    if CRR_OPERATIVE in omitted:
        failures.append(f"negative control: {CRR_CONTROL_OMITTED} carries the "
                        f"operative sentence though the article was omitted")
    # The trap, asserted so nobody re-introduces the naive guard.
    if "omitted" not in in_force:
        failures.append("the 'omitted' annotation is absent from the in-force "
                        "version -- the source changed shape; re-read before "
                        "trusting any guard written against it")
    print(f"    in force {CRR_CONTROL_IN_FORCE}: operative sentence present")
    print(f"    omitted  {CRR_CONTROL_OMITTED}: operative sentence absent")
    print(f"    'omitted' appears on BOTH -- never guard on that string")

    print("\nPRA Rulebook -- Large Exposures, point-in-time in the URL")
    for version in PRA_VERSIONS:
        p = fetch(f"{PRA_ROOT}/pra-rules/large-exposures/{version}", manifest,
                  f"pra-large-exposures-{version}.html")
        if "25%" not in text_of(p):
            failures.append(f"PRA {version} lacks a 25% limit")
        print(f"  {version}  {p.stat().st_size:,} B")
    for filename, url in PRA_GUIDANCE.items():
        p = fetch(url, manifest, filename)
        print(f"  {filename}  {p.stat().st_size:,} B")

    manifest.save()

    if failures:
        print("\nFAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK -- three regimes fetched, controls hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `uv run generators/fetch_regime_text.py`
Expected: `OK -- three regimes fetched, controls hold`, and
`sources/regimes/manifest.json` recording every URL with a retrieval date and
sha256.

- [ ] **Step 3: Verify idempotency**

Run it again. Expected: every line reads `[cached]`, exit 0, and
`manifest.json` is unchanged (`git diff --stat sources/regimes/manifest.json`
shows nothing).

- [ ] **Step 4: Commit**

```bash
git add generators/fetch_regime_text.py sources/regimes/
git commit -m "Wave 19 Task 2: fetch Reg O, CRR and PRA regime text with in-force/omitted controls"
```

---

## Task 3 — FIBO verification and semantic binding

**Files:**
- Create: `generators/verify_fibo_wave19.py`
- Modify: `docs/ccf_dataprep_v2.md` (the binding table)

**Interfaces:**
- Produces: the `ex:` locals later tasks use — `ex:ConnectedGroup`,
  `ex:economicallyDependentOn`, `ex:connectedTo`, `ex:governedByRegime`,
  `ex:RegimeVersion`, `ex:LimitEnvelope`, `ex:InsiderDesignation`,
  `ex:assertedBy`, `ex:assertedOn` — plus whichever FIBO terms the run
  confirms, which MUST be used in preference to minting.

- [ ] **Step 1: Copy the established method, do not invent one**

`generators/verify_fibo_wave18.py` is the reference. Copy its structure
exactly: subject-position matching (`prefix:Local` **alone on a line**), a
`POSITIVE_CONTROL` that must be found or the file is not being read correctly,
and `rdfs:domain`/`rdfs:range` printed for every object property so a name
that reads right and means something else is visible.

**A trap recorded from the design session.** The first absence check written
during design returned "0 hits" for *every* candidate, including `Exposure`
and `Capital`, which FIBO plainly declares. The regex was wrong, not FIBO — it
required a trailing space, and declarations put the qname alone on the line.
So this script asserts a **known-present** term as well as the absences:

```python
#: Terms FIBO DOES declare, confirmed 2026-08-27. If any of these comes back
#: absent, the matcher is broken and no absence result in this run means
#: anything. This is the control the first attempt lacked.
KNOWN_PRESENT = (
    "fibo-fbc-pas-fpas:Exposure",
    "fibo-fbc-pas-fpas:ExposureBearer",
    "fibo-fbc-pas-fpas:hasExposureTo",
    "fibo-be-oac-cpty:ContractualControl",
    "fibo-be-oac-cpty:MajorityControllingParty",
    # Task 5 needs a bank type. All five below are declared, verified
    # 2026-08-27 (pre-flight ruling P5).
    "fibo-fbc-fct-fse:Bank",
    "fibo-fbc-fct-fse:BankHoldingCompany",
    "fibo-fbc-fct-usfse:NationalBank",
)
```

- [ ] **Step 2: Run it**

Run: `uv run generators/verify_fibo_wave19.py`
Expected: every `KNOWN_PRESENT` term found in subject position; each candidate
`ex:` local reported as absent from FIBO; exit 0.

**If any `KNOWN_PRESENT` term reports absent, stop.** The matcher is broken
and every absence claim in the run is worthless.

- [ ] **Step 3: Prefer FIBO where it fits**

`fibo-fbc-pas-fpas:Exposure` / `ExposureBearer` / `hasExposureTo` cover the
exposure relation, and `fibo-be-oac-cpty:` covers control. Use them. Mint
under `ex:` only what the run proves absent. Record the domain and range the
script printed against each — a term whose range is wrong is worse than a
minted one.

- [ ] **Step 4: Update the binding table**

Add every term to the Canonical FIBO IRI binding section of
`docs/ccf_dataprep_v2.md`, with its full IRI, and for `ex:` terms a one-line
note on why FIBO did not supply it.

- [ ] **Step 5: Commit**

```bash
git add generators/verify_fibo_wave19.py docs/ccf_dataprep_v2.md
git commit -m "Wave 19 Task 3: verify FIBO coverage and bind the large-exposure vocabulary"
```

- [ ] **Step 6: Say it in your response**

Per CLAUDE.md, name the terms added and state that the vault mirror needs
refreshing. The mirror is already stale by four uncollected Wave 18 bundles;
this makes five. The bundle itself is sent in Task 17.

---

## Task 4 — Regime text into MongoDB as passages

**Files:**
- Create: `generators/extract_regime_passages.py`
- Create: `loaders/load_regime_mongo.py`

**Interfaces:**
- Consumes: `sources/regimes/` from Task 2.
- Produces: MongoDB `fibo_v2.document` rows with
  `doc_type='regime_text'` and `fibo_v2.passage` rows carrying
  `passage_id`, `doc_id`, `char_start`, `char_end`, `text`, `embedding`,
  `regime` (`reg-o` | `crr` | `pra`), `provision` (e.g. `215.4(b)`,
  `Article 395(1)`, `LE 2.1`), `effective_date`.

- [ ] **Step 1: Segment with real offsets**

Follow `generators/segment_passages.py`. Offsets must be **into the stored
document text**, so a consumer can resolve a citation back to the byte range.
Do not store a passage whose `text` is not literally
`document.text[char_start:char_end]` — Task 15 asserts exactly that.

- [ ] **Step 2: Embed every passage**

Use the same embedding path as the existing corpus. known-issues §38 and §42
record 84 passages estate-wide with no embedding; **this wave adds none**. The
loader refuses to write a passage whose `embedding` is absent or empty.

- [ ] **Step 3: Load, then verify by resolving a citation**

Run: `uv run loaders/load_regime_mongo.py`

Then prove a citation resolves, rather than trusting a count:

```bash
uv run python -c "
from ccf.config import mongo_db
db = mongo_db()
p = db.passage.find_one({'regime': 'reg-o', 'provision': {'\$regex': '215.4'}})
d = db.document.find_one({'doc_id': p['doc_id']})
slice_ = d['text'][p['char_start']:p['char_end']]
assert slice_ == p['text'], 'offsets do not resolve to the stored text'
assert p.get('embedding'), 'passage carries no embedding'
print('resolved:', p['provision'], '->', p['text'][:90])
"
```

- [ ] **Step 4: Commit**

```bash
git add generators/extract_regime_passages.py loaders/load_regime_mongo.py
git commit -m "Wave 19 Task 4: regime text into MongoDB with resolvable spans and embeddings"
```

---

## Task 5 — FFIEC NIC RSSD hierarchy into Fluree

§C assigns "Bank holding structure — FFIEC NIC RSSD hierarchy" to Fluree as
`R`. The estate already holds the two ends (`reporting_bank`, 2 rows); this
task puts the hierarchy in the graph so the reporting entity can be
established by traversal, per §D step 4.

**Files:**
- Create: `loaders/load_nic_hierarchy.py`

**Interfaces:**
- Produces: Fluree nodes `ex:bank/{rssd}` with `ex:rssd`, `ex:lei` and
  `rdfs:label`, and `ex:subsidiaryOf` edges child → parent. Types, per
  pre-flight ruling P5 (all verified declared in FIBO on 2026-08-27):
  **`fibo-fbc-fct-usfse:NationalBank`** for RSSD 852218 — "National
  Association" is exactly what that term models — and
  **`fibo-fbc-fct-fse:BankHoldingCompany`** for RSSD 1039502. Type explicitly
  for every role you query against; Fluree runs without OWL inference, so a
  query for `Bank` will NOT return a `NationalBank`.

- [ ] **Step 1: Source the hierarchy from FDIC, which is already in use**

`RSSDHCR` on the FDIC institutions endpoint gives the holding-company parent
for every insured bank, and Task 2's fetch pattern applies. Only two entities
under RSSD 1039502 are still active — JPMorgan Chase Bank N.A. (852218) and
JPMorgan Chase Bank, Dearborn (651448) — so this is a small graph, and that
is the honest shape of it.

- [ ] **Step 2: Nodes carry identity only**

Single-writer discipline: Fluree bank nodes carry `rssd`, `lei` and a label.
Capital resolves from Postgres. **Never** put `tier1_capital` on a Fluree node.

- [ ] **Step 3: Load and verify idempotency by value, not by count**

Run: `uv run loaders/load_nic_hierarchy.py` twice. Assert the triple count is
identical **and** that a named value survived — a count cannot see a field
being reset:

```bash
uv run python -c "
from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L, EX
q = f'SELECT ?l FROM <{L}> WHERE {{ <{EX}bank/852218> <http://www.w3.org/2000/01/rdf-schema#label> ?l }}'
b = fluree.query(q)['results']['bindings']
print('label:', [r['l']['value'] for r in b])
assert b, 'the reporting bank node lost its label on reload'
"
```

- [ ] **Step 4: Commit**

```bash
git add loaders/load_nic_hierarchy.py
git commit -m "Wave 19 Task 5: FFIEC NIC RSSD hierarchy into Fluree"
```

---

## Task 6 — `connectedTo` edges from the real control graph

**Files:**
- Create: `loaders/load_group_edges.py`

**Interfaces:**
- Consumes: `ccf_v2.corporate_ownership_record` (280 ACTIVE GLEIF edges).
- Produces: Fluree `ex:connectedTo` edges, `public` provenance.

- [ ] **Step 1: Derive, do not invent**

Every `connectedTo` edge is derived from an ACTIVE `IS_DIRECTLY_CONSOLIDATED_BY`
or `IS_ULTIMATELY_CONSOLIDATED_BY` record. Carry the GLEIF relationship type
onto the edge so the basis is visible, and mark provenance `public`.

- [ ] **Step 2: Do not create a group node**

This is the task most likely to drift. Per `docs/wave19-design.md` §4, **no
`ConnectedGroup` node, table, or row is created anywhere.** The edges are the
data; groups are recomputed by the validator. If you find yourself wanting a
group id to hang something off, the design is being reinterpreted — stop.

- [ ] **Step 3: Verify the graph reproduces the measured shape**

```bash
uv run python -c "
from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L, EX
import collections
q = f'SELECT ?a ?b FROM <{L}> WHERE {{ ?a <{EX}connectedTo> ?b }}'
b = fluree.query(q)['results']['bindings']
par={}
def f(x):
    par.setdefault(x,x)
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
for r in b:
    a,c=f(r['a']['value']),f(r['b']['value'])
    if a!=c: par[a]=c
comp=collections.Counter(f(x) for x in list(par))
print('edges', len(b), 'components', len(comp))
assert len(comp) == 26, f'expected 26 components, got {len(comp)}'
"
```

Expected: `components 26`. If it differs, either the load dropped edges or the
underlying GLEIF data moved — find out which before proceeding.

- [ ] **Step 4: Commit**

```bash
git add loaders/load_group_edges.py
git commit -m "Wave 19 Task 6: connectedTo edges from the real GLEIF control graph"
```

---

## Task 7 — The engineered `economicallyDependentOn` edges

§C: *"the one relationship the public estate cannot supply"* — a judgment edge
that lives in an analyst's head. Placing it in the graph **with an assertion
date and an author** is much of what the fabric offers here.

**Files:**
- Create: `generators/generate_dependency_edges.py`
- Modify: `loaders/load_group_edges.py`

**Interfaces:**
- Produces: ≥ 4 Fluree `ex:economicallyDependentOn` edges, each carrying
  `ex:assertedBy` (an analyst identifier), `ex:assertedOn` (a date),
  `ex:dependencyBasis` (free text — supplier concentration, single-tenant
  lease, shared funding), provenance `synthetic — engineered`.

- [ ] **Step 1: Choose the edges to do three jobs at once**

Each edge must be defensible as a judgment, and between them they must:

1. produce **≥ 1 group that control-based grouping alone would miss** — §F;
2. produce **≥ 1 edge that changes the binding limit** — §F, and this is a
   claim about *which* limit binds, so it is recomputed in Task 15, never
   flagged;
3. close as much of the per-group jurisdiction gap as they honestly can —
   `docs/wave19-design.md` §9's reading note. Nine groups span ≥ 3
   jurisdictions on their own; prefer merges whose combined footprint crosses
   a third country.

- [ ] **Step 2: Label honestly**

These are `synthetic — engineered`: invented deliberately to create a condition
public data will not supply. Presenting them as emergent misrepresents what
the data proves.

- [ ] **Step 3: Verify the merge actually happens**

Recompute components with `connection_basis='both'` and assert the count is
**lower** than the 26 from Task 6 — a merge that does not merge is the failure
this check exists to catch:

```bash
uv run python -c "
from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L, EX
import collections
def components(predicates):
    par={}
    def f(x):
        par.setdefault(x,x)
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for p in predicates:
        q = f'SELECT ?a ?b FROM <{L}> WHERE {{ ?a <{EX}{p}> ?b }}'
        for r in fluree.query(q)['results']['bindings']:
            a,c=f(r['a']['value']),f(r['b']['value'])
            if a!=c: par[a]=c
    return len(collections.Counter(f(x) for x in list(par)))
control = components(['connectedTo'])
both = components(['connectedTo','economicallyDependentOn'])
print('control basis:', control, ' both:', both)
assert both < control, 'the dependency edges merged nothing -- connection_basis is not consequential'
"
```

- [ ] **Step 4: Commit**

```bash
git add generators/generate_dependency_edges.py loaders/load_group_edges.py
git commit -m "Wave 19 Task 7: engineered economicallyDependentOn edges with author and assertion date"
```

---

## Task 8 — Insider designations, with invented people

**Decision (Dave, 2026-08-27): real rule text, invented insiders.** No real
person is named as a borrower on an engineered breach.

**Files:**
- Create: `generators/generate_insider_cases.py`
- **Create: `loaders/load_policy_fluree.py`** — this task creates it; Task 9
  extends the same file. (Pre-flight ruling P1: the plan originally had Task 8
  modifying a file Task 9 created. 8-before-9 is the right order, because
  Task 9 depends on Task 4's passage ids and Task 8 does not.)

**Interfaces:**
- Produces: Fluree `ex:InsiderDesignation` nodes linking an invented person to
  the reporting bank and to a related interest among the existing obligors,
  provenance `synthetic — engineered`; synthetic identifiers in the `SYN-`
  format the estate already uses.

- [ ] **Step 1: Invent the people, ingest the rule**

The Reg O rule text (Task 2) and JPMorgan's real DEF 14A related-party
disclosure are the citable sources. The director, the executive officer and
the related interest that actually trip the limit are **invented**, carry
`SYN-` identifiers, and appear in `ccf_v2.person` alongside the estate's other
synthetic people.

- [ ] **Step 2: Assert no real person is designated**

A hard guard, run at generation time and again in Task 15:

The designations themselves live in **Fluree**, per §C — so the guard reads
the person ids off the graph and checks them against Postgres, which owns
person provenance. It does not query a Postgres designation table, because
there is no such table and creating one would duplicate `R` into `E`:

```python
def assert_no_real_person_designated() -> None:
    """No insider designation may name a person sourced from a real registry.

    Designations are Fluree nodes (§C assigns them to `R`); person provenance
    lives in Postgres (§C assigns it to `E`). So this reads ids from the graph
    and resolves provenance from the table -- crossing the stores to ask the
    question, rather than duplicating either side to make it local.

    The estate's real-person populations are `psc_person` (pseudonymised UK
    PSC data) and any `ccf_v2.person` row whose provenance is `public`. An
    insider designation touching either is a legal problem, not a style one.
    """
    q = (f"SELECT ?person FROM <{L}> WHERE {{ "
         f"?d a <{EX}InsiderDesignation> ; <{EX}designatedPerson> ?person }}")
    keys = [local_name(r["person"]["value"])
            for r in fluree.query(q)["results"]["bindings"]]
    if not keys:
        raise AssertionError(
            "no insider designations found -- this guard would pass vacuously")

    # Both tables key on `person_key`, NOT `person_id`. Verified live
    # 2026-08-27; `person.provenance` takes only 'public' and
    # 'synthetic — engineered', so 'public' is the right discriminator.
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT person_key FROM "{S}".person '
                    "WHERE person_key = ANY(%s) AND provenance = 'public'",
                    (keys,))
        offenders = [r[0] for r in cur.fetchall()]
        cur.execute(f'SELECT person_key FROM "{S}".psc_person '
                    "WHERE person_key = ANY(%s)", (keys,))
        offenders += [r[0] for r in cur.fetchall()]

    if offenders:
        raise AssertionError(
            f"insider designations name real people: {sorted(set(offenders))}")
```

Note the vacuity guard. Without it, a run in which the designations failed to
load reports "no real people designated" and passes — an absence that is
wrong forever.

- [ ] **Step 3: Commit**

```bash
git add generators/generate_insider_cases.py
git commit -m "Wave 19 Task 8: Reg O insider designations on invented people"
```

---

## Task 9 — Limit envelope and regime version history into Fluree

**Files:**
- Create: `generators/generate_limit_envelope.py`
- **Modify: `loaders/load_policy_fluree.py`** — created by Task 8; extend it

**Interfaces:**
- Produces: Fluree `ex:LimitEnvelope` nodes (internal appetite and sub-limits,
  `synthetic — internal`) and `ex:RegimeVersion` nodes (`public`) carrying
  `ex:effectiveFrom`, `ex:effectiveTo`, `ex:limitPctOfCapital`,
  `ex:citesProvision` → a MongoDB `passage_id` from Task 4.

- [ ] **Step 1: Regime versions are real; internal versions are invented**

Three `RegimeVersion` nodes at minimum, and the boundary between them is
factual:

| Regime | Effective from | Effective to | Limit | Cites |
|---|---|---|---|---|
| CRR (assimilated) | 2014-01-01 | **2021-12-31** | 25% of eligible capital | CRR Art 395(1) passage |
| PRA Large Exposures | **2022-01-01** | — | 25% | PRA Part passage |
| Regulation O | (eCFR date) | — | **$500,000 absolute** | 12 CFR 215.4(b) passage |

The 2021-12-31 / 2022-01-01 boundary is SI 2021/1078. It is real, and it is
what makes an `as_of` reconstruction differ from the live answer.

- [ ] **Step 2: The internal appetite sits below 5.4%**

So the largest real group (5.4% of tier 1) breaches house policy while
remaining compliant under CRR and PRA. Provenance `synthetic — internal`.

- [ ] **Step 3: Every limit cites a provision**

§D's validation gates name **regime anchoring** — every limit must cite a
provision. A `RegimeVersion` with no `ex:citesProvision` is a load failure,
not a warning.

- [ ] **Step 4: Commit**

```bash
git add generators/generate_limit_envelope.py loaders/load_policy_fluree.py
git commit -m "Wave 19 Task 9: limit envelope and real regime version history into Fluree"
```

---

## Task 10 — Methodology documentation into MongoDB

**Files:**
- Modify: `loaders/load_regime_mongo.py`

**Interfaces:**
- Produces: `fibo_v2.document` rows with `doc_type='methodology'`, passages
  embedded, provenance `synthetic — internal`.

- [ ] **Step 1: Write the Reg O narrowing into the methodology itself**

12 CFR 215.4 is a **stack**, not a flat $500,000 test: a percentage-of-capital
threshold requiring prior board approval (the higher of $25,000 or 5% of
unimpaired capital and surplus, §215.4(b)), the $500,000 absolute cap above
which approval is required regardless, the single-borrower lending limit of
15% via 12 U.S.C. 84 (§215.2(i)), and an aggregate ceiling across all
insiders.

**This wave exercises the $500,000 cap only**, because it is the one that binds
at this estate's magnitudes — 5% of $295.8bn is $14.8bn and nothing approaches
it. A methodology document implying Reg O *is* a flat $500k test would be
inaccurate about real regulation, so the narrowing is one explicit sentence in
the document, and again as a `divergence` string in Task 16.

- [ ] **Step 2: The examiner rendering carries the replay attribution**

§F asks for three ProjectionPlans "with the examiner rendering carrying full
methodology and replay attribution". The methodology documents are what the
examiner plan points at. Write them so that is true of the data — do not
implement the pointing.

- [ ] **Step 3: Commit**

```bash
git add loaders/load_regime_mongo.py
git commit -m "Wave 19 Task 10: methodology documentation, with the Reg O narrowing written down"
```

---

## Task 11 — The risk-department limit workbook into SQLite

**Files:**
- Create: `loaders/load_limit_workbook.py`

**Interfaces:**
- Produces: `data/departmental.sqlite` table `risk_limit_workbook` —
  `line_id`, `group_label`, `limit_intent`, `limit_pct`, `note` (free text),
  `owner`, `reviewed_on`, `provenance`.

- [ ] **Step 1: This is the leak path — write it carefully**

The workbook is free-text working notes about a **real named bank**. It is the
one store whose contents read as prose, so it is where an engineered breach
most easily becomes a sentence that looks like a fact. Every `note` must be
phrased about the **synthetic envelope**, never as an assertion about the real
institution's regulatory standing. Task 15 asserts this by enumeration.

- [ ] **Step 2: Check before adding rows**

`data/departmental.sqlite` already has 5 tables from earlier waves. Confirm no
loader keys off row position or `ORDER BY` offset before adding a sixth —
positional identity has silently rewritten other waves' rows four times on
`main`.

- [ ] **Step 3: Commit**

```bash
git add loaders/load_limit_workbook.py
git commit -m "Wave 19 Task 11: risk-department limit workbook into SQLite"
```

---

## Task 12 — Three ProjectionPlans into Postgres

**Files:**
- Modify: `loaders/load_wave19_postgres.py`

**Interfaces:**
- Produces: `ccf_v2.large_exposure_projection_plan` — `plan_id`,
  `perspective` (`credit-officer` | `committee` | `examiner`),
  `elements_included` (text[]), `carries_methodology` bool,
  `carries_replay_attribution` bool, `provenance`.

- [ ] **Step 1: Name the collision in three places**

`ProjectionPlan` is an SDK Protocol entity. These rows are **catalog data
describing what each perspective would receive** — nothing more. The loader
docstring, the table comment, and the `conditions.py` registration each state:
*does not resolve, does not assemble, does not run at request time.*

```python
COMMENT ON TABLE "{S}".large_exposure_projection_plan IS
    'Catalog data describing what each perspective would receive. NOT an SDK '
    'ProjectionPlan: does not resolve, does not assemble, does not run at '
    'request time. §C assigns the element to Postgres; this table holds it.';
```

- [ ] **Step 2: The three must genuinely differ**

The examiner plan carries methodology and replay attribution the committee
plan never requests. Task 15 asserts the three `elements_included` sets are
pairwise distinct — three identical plans would satisfy a count of three and
demonstrate nothing.

- [ ] **Step 3: Commit**

```bash
git add loaders/load_wave19_postgres.py
git commit -m "Wave 19 Task 12: three ProjectionPlan rows, pairwise distinct"
```

---

## Task 13 — The engineered proposal cases

**Files:**
- Create: `generators/generate_proposals.py`
- Modify: `loaders/load_wave19_postgres.py`

**Interfaces:**
- Produces: `ccf_v2.exposure_proposal` — `proposal_id`, `subject_lei`,
  `facility_type`, `commitment_amount`, `currency`, `is_hypothetical` (bool,
  `NOT NULL`, always true), `expected_outcome` (`breaches` |
  `fits_after_mitigation` | `fits`), `provenance`.

- [ ] **Step 1: Proposals never touch `facility`**

This is the correction that matters most in this task. §6 of the design
rejected inventing $74bn of booked exposure; writing a proposal into
`ccf_v2.facility` re-creates exactly that, and every portfolio total in the
estate moves silently. Proposals live in their own table, always flagged
hypothetical, always `synthetic — engineered`.

- [ ] **Step 2: Size them against the measured numbers**

- **Breaches:** a proposal that takes its group above **$73.9bn** (25% of
  $295.8bn tier 1). The largest group is $16.0bn, so the proposal is roughly
  $58bn — clearly hypothetical, and never booked.
- **Fits only after mitigation:** sized to sit just over the line until the
  existing `haircut_schedule` and `collateral_pledge` values are applied, and
  under it afterwards. Recomputed in Task 15 — the outcome is not read from
  `expected_outcome`, which exists only to document intent.

- [ ] **Step 3: Assert the booked total did not move**

A row count cannot see an amount being altered. Assert the magnitude:

```python
def assert_booked_total_unchanged(cur) -> None:
    """Wave 19 must not change the estate's booked commitment.

    Measured 2026-08-27, before this wave: $55,718,... across 60 facilities.
    A proposal written into `facility` by mistake would move this, and a row
    count would not notice an amount changing.
    """
    cur.execute(f'SELECT COALESCE(SUM(commitment_amount), 0), COUNT(*) '
                f'FROM "{S}".facility')
    total, count = cur.fetchone()
    if float(total) != float(BOOKED_COMMITMENT_AT_WAVE19_START):
        raise AssertionError(
            f"booked commitment moved from "
            f"${BOOKED_COMMITMENT_AT_WAVE19_START/1e9:.3f}bn to "
            f"${float(total)/1e9:.3f}bn -- did a proposal land in `facility`?")
    if count != FACILITY_COUNT_AT_WAVE19_START:
        raise AssertionError(
            f"facility count moved from {FACILITY_COUNT_AT_WAVE19_START} "
            f"to {count}")
```

Both constants are **measured, not guessed** — taken from the live estate on
2026-08-27, before this wave wrote anything:

```python
#: ccf_v2.facility, measured 2026-08-27 before Wave 19. Exact integers, so the
#: comparison is exact: a proposal landing here moves the sum by billions, and
#: a tolerance would only ever hide a smaller mistake.
BOOKED_COMMITMENT_AT_WAVE19_START = 55_719_058_576
FACILITY_COUNT_AT_WAVE19_START = 60
```

The count is asserted **as well as** the sum, because they fail differently: a
proposal inserted as a facility moves both, but a proposal that *replaces* an
existing row's amount moves only the sum. Neither alone sees both.

- [ ] **Step 4: Commit**

```bash
git add generators/generate_proposals.py loaders/load_wave19_postgres.py
git commit -m "Wave 19 Task 13: hypothetical proposals in their own table, booked total asserted unchanged"
```

---

## Task 14 — Wire the debt-tolerance case

**Files:**
- Modify: `generators/generate_proposals.py`

**Interfaces:**
- Consumes: **`ccf_v2.memo_context_debt.aggregate_debt`, keyed by `lei`** — and
  `validators/memo_debt.py::policy_tolerance(cur)` for the bound.
- Produces: at least one connected group whose members' aggregate debt exceeds
  the tolerance.

**Pre-flight ruling P3 — read the right table.** `ccf_v2.context_debt` is a
**record** table (`debt_id`, `reason`, `subject_kind`, `subject_key`) with no
numeric score, and 133 of its 304 rows are keyed to a *person* rather than an
entity. The float lives in **`ccf_v2.memo_context_debt.aggregate_debt`**, keyed
by `lei`, and `validators/memo_debt.py` already exposes `policy_tolerance(cur)`
as the tolerance source with a discrimination check around it. Aggregating
`context_debt` would fail loudly on a column that does not exist.

- [ ] **Step 1: MEASURE before engineering anything**

At least one obligor already sits at `aggregate_debt` **0.4875** against a 0.2
bound, so a group containing it may already breach and this condition may need
**verification, not invention**. Measure first:

```bash
uv run python -c "
from ccf.config import pg_connect, PG_SCHEMA_V2 as S
with pg_connect() as c:
    rows = c.execute(f'select lei, aggregate_debt from {S}.memo_context_debt order by aggregate_debt desc limit 10').fetchall()
    for lei, d in rows: print(f'  {lei}  {float(d):.4f}')
"
```

Then form the groups from Task 6/7's edges and check whether any group's
members already aggregate above tolerance. **If one does, engineer nothing** —
record that the condition is satisfied by existing data and say so in the
task report. Only if none does may this task add a debt record, and it must
be labelled `synthetic — engineered`.

- [ ] **Step 2: Aggregate across the group, not the obligor**

§D step 6 describes collecting each prerequisite product's Context Debt "now
across a group rather than an obligor". Recompute it in Task 15; do not store
an aggregated figure, which would be a derived value duplicated out of its
owning store.

- [ ] **Step 2: Commit**

```bash
git add generators/generate_proposals.py
git commit -m "Wave 19 Task 14: a connected group that breaches debt tolerance"
```

---

## Task 15 — `validators/large_exposure.py`

The floors §F itself says cannot be established by counting. This file is the
wave's regression suite and the reason the whole design is safe.

**Files:**
- Create: `validators/large_exposure.py`
- Create: `validators/test_large_exposure.py`

**Interfaces:**
- Produces: `load_context(as_of: str | None = None) -> Context` and eight floor
  functions, each `(ctx: Context | None = None) -> tuple[bool, str]`, plus
  `FLOORS: list[tuple[str, Callable]]` — the same shape as
  `validators/syndicate.py`, which `conditions.py` already knows how to
  delegate to.
- `Context` fields, named here because Task 16's delegates and the tests below
  both refer to them:

```python
@dataclass
class Context:
    #: entity IRI -> entity IRI, one entry per ex:connectedTo edge
    control_edges: list[tuple[str, str]]
    #: same shape, one per ex:economicallyDependentOn edge
    dependency_edges: list[tuple[str, str]]
    #: lei -> ISO 3166-1 alpha-2 country, from ccf_v2.v_entity_jurisdiction
    jurisdiction: dict[str, str]
    #: lei -> booked commitment in DOLLARS, from ccf_v2.facility
    exposure: dict[str, float]
    #: report_date -> tier 1 in DOLLARS. Converted on load from
    #: USD_THOUSANDS; the `unit` column from Task 1 is read, never assumed.
    capital: dict[str, float]
    #: one per ex:RegimeVersion node: regime, effective_from, effective_to,
    #: limit_pct_of_capital, limit_absolute_usd, cites_passage_id
    regimes: list[dict]
    #: ccf_v2.exposure_proposal rows
    proposals: list[dict]
    #: lei -> aggregate_debt, from ccf_v2.memo_context_debt (NOT
    #: ccf_v2.context_debt, which is a record table with no score --
    #: pre-flight ruling P3)
    debt: dict[str, float]
    #: every free-text surface the provenance floor enumerates
    narrative: list[dict]
```

- [ ] **Step 1: Copy `validators/syndicate.py`'s shape**

One `Context` built by `load_context()`, shared across floors because building
it is expensive. **The floors read only** — if one ever mutates the context,
the sharing becomes a defect, exactly as recorded for Wave 18.

- [ ] **Step 2: The eight floors**

| Floor | Asserts | Why a count cannot |
|---|---|---|
| `groups_recompute` | 26 components from `connectedTo`; ≥ 9 spanning ≥ 3 countries individually, reported separately from the collective figure | reads edges, forms groups fresh; no stored group exists to read |
| `dependency_changes_binding_limit` | ≥ 1 `economicallyDependentOn` edge whose removal changes **which** limit binds | a claim about ordering between limits |
| `regime_divergence` | ≥ 1 group compliant under CRR/PRA and in breach under Reg O, both recomputed from the stored limits and the live exposure | a claim about two answers differing |
| `proposal_breaches` | ≥ 1 proposal that takes its group above the 25% limit, recomputed — never read from `expected_outcome` | the stored column is intent, not outcome |
| `mitigation_is_load_bearing` | ≥ 1 proposal over the limit before haircuts and under it after | a claim about a flip |
| `debt_tolerance_breached` | ≥ 1 group whose members' `memo_context_debt.aggregate_debt` aggregates above `memo_debt.policy_tolerance(cur)` | aggregation across a group, against a tolerance read from policy rather than hard-coded |
| `projection_plans_differ` | the three `elements_included` sets are pairwise distinct | three identical rows pass a count of three |
| `no_public_row_in_a_breach` | the provenance floor, by enumeration | see Step 3 |

- [ ] **Step 3: The provenance floor is not a flag check**

It covers four surfaces by enumeration — utilisation rows, **every SQLite
workbook line including free text**, every MongoDB methodology or narrative
passage naming the reporting bank, and every breach and proposal record — and
makes **two separate** assertions:

1. every such row is labelled `synthetic — internal` or
   `synthetic — engineered`, and no `public` row participates in a breach;
2. no free-text field asserts a regulatory breach by the real institution.

The second is not implied by the first. A correctly labelled row can still
carry a sentence that reads as fact once quoted out of its table, and SQLite
is where that happens.

- [ ] **Step 4: Test the checker, not just the data**

Every floor gets a test with a **known-present** and a **known-absent** input,
and they must give different answers. A checker that always returns the same
verdict has hidden defects for seven waves at a time in this estate.

```python
def test_regime_divergence_rejects_a_world_with_one_regime(monkeypatch):
    """The negative control. Strip Reg O from the context and the floor must
    fail -- if it still passes, it is not reading the regimes at all."""
    ctx = large_exposure.load_context()
    ctx.regimes = [r for r in ctx.regimes if r["regime"] != "reg-o"]
    ok, detail = large_exposure.regime_divergence(ctx)
    assert not ok, f"floor passed with no second regime: {detail}"
```

- [ ] **Step 5: Run both**

Run: `uv run validators/large_exposure.py`
Expected: `8 passed · 0 failed`

Run: `uv run --with pytest pytest validators/test_large_exposure.py -q`
Expected: all pass, including every negative control.

- [ ] **Step 6: Commit**

```bash
git add validators/large_exposure.py validators/test_large_exposure.py
git commit -m "Wave 19 Task 15: eight recomputed floors, each with a negative control"
```

---

## Task 16 — Registration

**Files:**
- Modify: `validators/conditions.py`, `validators/partition.py`,
  `validators/spec_coverage.py`

- [ ] **Step 1: Measure the PASS count before you touch anything**

```bash
uv run validators/conditions.py 2>&1 | tail -3
uv run validators/partition.py 2>&1 | tail -3
```

Record both. The delta after registration is the number of checks actually
added — the only honest way to report it. Wave 18 closed at **184 passed** in
`conditions.py` and **56/56** in `partition.py`.

- [ ] **Step 2: Register in `conditions.py`**

Add a `# --- #21 large-exposure-rwa-concentration (Wave 19) ---` block, in the
established shape: direct counts registered as counts, and the eight floors
delegated to `validators/large_exposure.py` through a `_run_large_exposure_floor`
helper modelled on `_run_syndicate_floor`. Build **one** `Context` per
`collect()` run and share it, as the Wave 18 block does.

- [ ] **Step 3: Register in `partition.py`**

A `check_wave19()` returning `list[Result]`, asserting each store holds its
slice **and nothing it does not own**. At minimum: no capital figure on a
Fluree node; no group table anywhere in Postgres; no regime rule text outside
MongoDB; no proposal row in `facility`. State on each check what would make it
fail, as `check_wave18` does.

- [ ] **Step 4: Register in `spec_coverage.py`**

Add a `LARGE_EXPOSURE` manifest and its `MANIFEST` entry. Two rows carry a
`divergence` string:

- the **Reg O narrowing** — the $500,000 cap only, of a four-limit stack;
- **FFIEC 101** — absent, because the loaded capital is bank-level FDIC rather
  than holding-company FR Y-9C. A recorded divergence, not a silent invention.

- [ ] **Step 5: Assert this product's lines by name**

**Do not assert "the file is green."** Full `spec_coverage.py` runs already
exit non-zero for two inherited reasons — the
`counterparty-reference-snapshot` mapping matches zero catalog rows, and
DEFERRED rows make a non-zero exit by design — so a permanently red suite is
somewhere new rows hide indefinitely.

```bash
uv run validators/conditions.py --product large-exposure-rwa-concentration
uv run validators/spec_coverage.py --product large-exposure-rwa-concentration
```

Assert each expected PASS line **by its own name and verdict**, and report the
before/after PASS-count delta from Step 1.

- [ ] **Step 6: Commit**

```bash
git add validators/conditions.py validators/partition.py validators/spec_coverage.py
git commit -m "Wave 19 Task 16: register the capstone, asserting its lines by name"
```

---

## Task 17 — Documentation, handoff, and the vault bundle

**Files:**
- Modify: `docs/ccf_dataprep_v2.md`, `docs/spec-digest.md`,
  `docs/known-issues.md`, `docs/HANDOFF.md`
- Creates: an outbox bundle under `~/.agent-exchange/ccf-dataprep/outbox/`

- [ ] **Step 1: Correct `docs/spec-digest.md`**

Its jurisdiction finding is stale. It records "3 countries present (US, NZ,
CA) but only 3 non-US entities total" and calls the connected group
unbuildable without engineering. Wave 15's GLEIF subsidiary fetch closed that:
**30+ countries across 421 entities, 26 groups, 9 spanning ≥ 3 jurisdictions.**
Correct it in place and date the correction.

Also correct its claim that regime version history is **engineered** — it is
real, sourced from SI 2021/1078 and the PRA Rulebook's point-in-time versions.

- [ ] **Step 2: Record the new known issues**

At minimum: EUR-Lex blocked with the measured date and the substitute; the
"omitted" string trap on legislation.gov.uk; the capital units defect, why the
ratio check could never see it, and the magnitude floor that replaces it.

- [ ] **Step 3: Send the vault bundle**

Read **section 5 of the `obsidian-vault-access` skill** before the first send.
The message directory is `<YYYY-MM-DDTHH-MM-SSZ>-<slug>` with **hyphens in the
time, never colons**, or the reconciler rejects it silently-but-visibly.

The mirror is already stale by four uncollected Wave 18 bundles; this is the
fifth. Bundles are immutable — a correction is a **new** bundle naming what it
supersedes, never an edit.

- [ ] **Step 4: Update `docs/HANDOFF.md`**

State the merge position honestly, including anything left open. Write out the
deferred findings **as findings, not as a count** — "8 minors deferred" is
bookkeeping that records nothing.

- [ ] **Step 5: Full green run, read from the register itself**

```bash
uv run validators/conditions.py            # read the PASS count, not "0 failed"
uv run validators/partition.py
uv run validators/large_exposure.py
uv run validators/test_fabric_isolation.py # NOT a pytest file — run it directly
uv run --with pytest pytest validators/ -q
```

- [ ] **Step 6: Commit**

```bash
git add docs/
git commit -m "Wave 19 Task 17: register the capstone in the docs and correct two stale findings"
```

---

## Self-review notes

**Spec coverage.** Every §C row and every §F condition in
`docs/wave19-design.md` §9 maps to a task: regime text → 2, 4, 10; NIC → 5;
control edges → 6; dependency edges → 7; insider designations → 8; limit
envelope and regime versions → 9; workbook → 11; ProjectionPlans → 12;
proposals and mitigation → 13; debt tolerance → 14; capital → 1 (repair; the
data itself is already loaded).

**Known gap, deliberate.** FFIEC 101 advanced-approaches detail is not
fetched — the loaded capital is bank-level FDIC, not holding-company FR Y-9C.
Recorded as a divergence in Task 16 Step 4 rather than invented.

**Ambiguity resolved.** §F's "~15 connected groups spanning ≥ 3 jurisdictions"
is built to the **per-group** reading (9 satisfied from real edges, Task 7
closes what it honestly can, shortfall recorded as a divergence), not the
looser collective reading. See `docs/wave19-design.md` §9.
