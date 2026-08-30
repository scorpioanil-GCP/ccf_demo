"""The census `cp-03` must re-derive, and the four wrong methods it must not use.

Phase 24.3 criteria 2-16 and 18. Schema from
`tests/examples/fixtures/cp_03_census_schema.sql` and rows from
`cp_03_census_rows.sql`, applied by the ``seeded`` fixture and by nothing else.

**WHY THIS MODULE IS WEIGHTED THE WAY IT IS.** The mechanism this product needs
is small — one operator, one lookup, a batch-select, a derivation. **Every
serious defect found while specifying it was a MEASUREMENT defect**: four wrong
counts before a line of code existed, each one a check whose population was not
its question. So the census is gated as heavily as the assembly, and the four
controls below exist because a wrong method here produces a **plausible number
and no error** — which is the failure that survives review.

**CRITERION 18, AND IT IS THE POINT OF THE CONTROLS.** Each control asserts
BOTH the specific number its method produces AND that the number differs from
the census. Asserting only *"this differs"* keeps passing after the method stops
producing a wrong answer; asserting only the number does not prove the control
still discriminates. A control that has stopped discriminating is worse than no
control, because it reports green.

**A RED HERE MUST NAME A METHOD.** Every control runs real SQL against the
seeded fixture and compares integers. If one of these fails, the message names
the grouping key or the join that produced the wrong number — not a
``NameError`` from the test having broken, which would be a red that proves
nothing about the product.

**Expectations live in `cp_03_census_expected.yaml`, not in this file.** A number
this module authored would be the module agreeing with itself about what the
estate holds.

Marked ``postgres``: every test requests the session-scoped ``postgres_dsn``.
Unset ``CCF_TEST_POSTGRES_DSN`` starts a container; ``CCF_REQUIRE_POSTGRES``
turns a skip into a failure.

**Criterion 17 is deliberately absent.** It asserts Fluree predicate counts
(178/198 against 171) and there is no Fluree in this fixture. It defers with the
rest of the Fluree unit — §C.1 element 11 and `OFS-G14` — rather than being
approximated against Postgres, which would be a different control wearing
criterion 17's name.
"""

from __future__ import annotations

import os
import pathlib
from typing import Any, Iterator

import psycopg
import pytest
import yaml

pytestmark = pytest.mark.postgres

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SCHEMA_SQL = FIXTURES / "cp_03_census_schema.sql"
ROWS_SQL = FIXTURES / "cp_03_census_rows.sql"
EXPECTED = yaml.safe_load((FIXTURES / "cp_03_census_expected.yaml").read_text("utf-8"))

CENSUS: dict[str, Any] = EXPECTED["census"]
WRONG: dict[str, Any] = EXPECTED["wrong_methods"]

SCHEMA = "ccf_v2"

#: The estate's own `PRIMARY KEY (cik, tag, unit, period_end, fiscal_period,
#: accession)` minus `accession` — the filing, which is exactly what a
#: restatement varies. `lei` substitutes for `cik`; the two are 1:1 across all
#: 50 obligors, and `test_the_correlation_key_is_one_to_one` proves it rather
#: than assuming it.
KEY = ", ".join(CENSUS["key"])

#: One restated fact-cell, with its first- and last-filed values. Grouping —
#: never `JOIN ... USING` — because `GROUP BY` treats NULL `period_start` as a
#: value and a join drops all 8,088 instant facts without raising.
CELLS = f"""
    SELECT {KEY},
           (period_start IS NULL) AS is_instant,
           (array_agg(value ORDER BY filed_date))[1]      AS first_v,
           (array_agg(value ORDER BY filed_date DESC))[1] AS last_v
      FROM {SCHEMA}.financial_fact
     GROUP BY 1, 2, 3, 4, 5, 6
    HAVING count(DISTINCT value) > 1
"""


@pytest.fixture(scope="module")
def seeded(postgres_dsn: str) -> Iterator[str]:
    """A container carrying the whole `financial_fact` population, not a sample."""
    with psycopg.connect(postgres_dsn, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        cursor.execute(ROWS_SQL.read_text(encoding="utf-8"))
    yield postgres_dsn


def scalar(dsn: str, sql: str) -> int:
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
        assert row is not None, f"query returned no row:\n{sql}"
        return int(row[0])


def rows(dsn: str, sql: str) -> list[tuple[Any, ...]]:
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_seeder_seeded(seeded: str) -> None:
    """Without this, every count below could be a true statement about nothing."""
    facts = scalar(seeded, f"SELECT count(*) FROM {SCHEMA}.financial_fact")
    assert facts == CENSUS["facts_total"], (
        f"the fixture holds {facts} facts, expected {CENSUS['facts_total']}."
        " Every census assertion below is measured against this population, so a"
        " short seed makes all of them true of the wrong thing."
    )


def test_the_correlation_key_is_one_to_one(seeded: str) -> None:
    """`lei` may substitute for the key's `cik` only while the two are 1:1."""
    leis, ciks, pairs = rows(
        seeded,
        f"""SELECT count(DISTINCT lei), count(DISTINCT cik), count(*)
              FROM (SELECT DISTINCT lei, cik FROM {SCHEMA}.financial_fact) s""",
    )[0]
    assert leis == ciks == pairs, (
        f"lei/cik is not 1:1 ({leis} leis, {ciks} ciks, {pairs} pairs), so the"
        " census key's substitution of `lei` for the estate's `cik` no longer"
        " holds and every restatement figure is keyed on the wrong column."
    )


# ---------------------------------------------------------------------------
# Criteria 2 to 12 — every figure re-derived from the store, not imported.
# ---------------------------------------------------------------------------


def test_the_restatement_census(seeded: str) -> None:
    """Criteria 2 and 3."""
    cells, obligors = rows(
        seeded, f"SELECT count(*), count(DISTINCT lei) FROM ({CELLS}) c"
    )[0]
    assert cells == CENSUS["restatement_cells"], (
        f"restatement census is {cells}, expected {CENSUS['restatement_cells']}"
        f" on key ({KEY}). A HIGHER number means the key was relaxed — see the"
        " wrong-method controls."
    )
    assert obligors == CENSUS["restatement_obligors"]


def test_the_accession_census_and_its_identity(seeded: str) -> None:
    """Criterion 9, and the identity that makes the three numbers one statement."""
    total, multi, restated, identical = rows(
        seeded,
        f"""SELECT count(*),
                   count(*) FILTER (WHERE n_acc > 1),
                   count(*) FILTER (WHERE n_val > 1),
                   count(*) FILTER (WHERE n_acc > 1 AND n_val = 1)
              FROM (SELECT {KEY},
                           count(DISTINCT accession) AS n_acc,
                           count(DISTINCT value)     AS n_val
                      FROM {SCHEMA}.financial_fact
                     GROUP BY 1, 2, 3, 4, 5) s""",
    )[0]
    assert total == CENSUS["total_fact_cells"]
    assert multi == CENSUS["cells_multi_accession"]
    assert restated == CENSUS["restatement_cells"]
    assert identical == CENSUS["cells_repeated_identically"]
    assert identical + restated == multi, (
        f"{identical} identical + {restated} restated != {multi} multi-accession."
        " These are not three independent counts: every multi-accession cell is"
        " either re-reported unchanged or genuinely restated, and a fixture where"
        " that fails has drifted inconsistently."
    )


def test_the_severity_bands(seeded: str) -> None:
    """Criteria 4, 5 and 6 — and the bands must partition the census."""
    threshold_sql = """
        CASE WHEN first_v = 0 OR first_v IS NULL THEN 'undefined'
             WHEN abs((last_v - first_v) / abs(first_v)) < 0.01 THEN 'precision'
             WHEN abs((last_v - first_v) / abs(first_v)) < 0.05 THEN 'middle'
             ELSE 'material' END
    """
    found = {
        band: (cells, obligors)
        for band, cells, obligors in rows(
            seeded,
            f"SELECT {threshold_sql}, count(*), count(DISTINCT lei)"
            f" FROM ({CELLS}) c GROUP BY 1",
        )
    }
    for band, expected in CENSUS["bands"].items():
        cells, obligors = found.get(band, (0, 0))
        assert cells == expected["cells"], (
            f"band {band!r} holds {cells} cells, expected {expected['cells']}"
        )
        assert obligors == expected["obligors"]
    assert sum(c for c, _ in found.values()) == CENSUS["restatement_cells"], (
        "the bands do not partition the census — a cell is counted twice or"
        " not at all, which no per-band assertion above would catch"
    )


def test_instant_and_duration_facts_are_both_present(seeded: str) -> None:
    """Criterion 7 — a duration-only census is a defect, not a simplification."""
    instant, duration = rows(
        seeded,
        f"""SELECT count(*) FILTER (WHERE period_start IS NULL),
                   count(*) FILTER (WHERE period_start IS NOT NULL)
              FROM {SCHEMA}.financial_fact""",
    )[0]
    assert instant == CENSUS["facts_instant"]
    assert duration == CENSUS["facts_duration"]
    assert instant + duration == CENSUS["facts_total"]
    assert instant > 0 and duration > 0, (
        "leverage needs debt (instant) over EBITDA (duration); a population"
        " missing either kind cannot compute a ratio at all"
    )


def test_item_402_coverage(seeded: str) -> None:
    """Criterion 8 — the native signal is corroboration and covers 9 of 37."""
    table = {
        bool(has): (restated, clean)
        for has, restated, clean in rows(
            seeded,
            f"""WITH changed AS (SELECT DISTINCT lei FROM ({CELLS}) c)
                SELECT (p.count_8k_item_4_02 > 0),
                       count(*) FILTER (WHERE ch.lei IS NOT NULL),
                       count(*) FILTER (WHERE ch.lei IS NULL)
                  FROM {SCHEMA}.filing_profile p
                  LEFT JOIN changed ch ON ch.lei = p.lei
                 GROUP BY 1""",
        )
    }
    expected = CENSUS["item_402"]
    assert table[True][0] == expected["restated_with_filing"]
    assert table[False][0] == expected["restated_without_filing"]
    assert table[True][1] == expected["unrestated_with_filing"]
    assert sum(sum(pair) for pair in table.values()) == expected["obligors_total"]
    assert table[False][0] > table[True][0], (
        "more restatements carry a 4.02 than not, which would make the filing a"
        " usable detector — the product's binding (corroboration only) assumes"
        " the opposite and would need revisiting"
    )


def test_crosswalk_coverage(seeded: str) -> None:
    """Criterion 10 — resolution goes through rung 01's crosswalk."""
    resolved, orphans = rows(
        seeded,
        f"""SELECT count(*) FILTER (WHERE c.lei IS NOT NULL),
                   count(*) FILTER (WHERE c.lei IS NULL)
              FROM (SELECT DISTINCT lei FROM {SCHEMA}.financial_fact) f
              LEFT JOIN {SCHEMA}.crosswalk c ON c.lei = f.lei""",
    )[0]
    assert resolved == CENSUS["crosswalk_obligors"]
    assert orphans == CENSUS["crosswalk_orphans"]


def test_non_december_fiscal_year_ends(seeded: str) -> None:
    """Criterion 11 — period alignment is a real operation, not a formality."""
    months = rows(
        seeded,
        f"""WITH latest AS (
                SELECT DISTINCT ON (lei) lei, period_end
                  FROM {SCHEMA}.financial_fact
                 WHERE fiscal_period = 'FY' AND form = '10-K'
                 ORDER BY lei, period_end DESC)
            SELECT EXTRACT(MONTH FROM period_end)::int, count(*)
              FROM latest GROUP BY 1""",
    )
    total = sum(count for _, count in months)
    non_december = sum(count for month, count in months if month != 12)
    assert total == CENSUS["fiscal_year_end_obligors_total"], (
        f"{total} obligors have a latest FY 10-K, expected"
        f" {CENSUS['fiscal_year_end_obligors_total']} — the distribution must"
        " cover the population or the non-December share is of the wrong base"
    )
    assert non_december == CENSUS["non_december_fiscal_year_ends"]


def test_the_obligor_with_no_revenue_tag(seeded: str) -> None:
    """Criterion 12 — served NOT_EVALUABLE, never 0."""
    missing = scalar(
        seeded,
        f"""SELECT count(*) FROM (
                SELECT DISTINCT lei FROM {SCHEMA}.financial_fact
                EXCEPT
                SELECT DISTINCT lei FROM {SCHEMA}.financial_fact
                 WHERE tag ILIKE '%%Revenue%%' OR tag = 'SalesRevenueNet') s""",
    )
    assert missing == CENSUS["obligors_without_any_revenue_tag"]


# ---------------------------------------------------------------------------
# Criteria 13 to 16 and 18 — the wrong methods, each proved still wrong.
#
# Every control asserts TWO things: the specific number its method produces,
# and that the number differs from the census. The pairing is criterion 18 and
# it is not decoration — a control asserting only "this differs" goes green
# forever once the method stops producing a wrong answer, and one asserting
# only the number never proves it still discriminates.
# ---------------------------------------------------------------------------


def _control(dsn: str, name: str, sql: str) -> None:
    """Run one wrong method and hold it to both halves of criterion 18."""
    expected = WRONG[name]
    produced = scalar(dsn, sql)
    census = CENSUS["restatement_cells"]

    assert produced == expected["yields"], (
        f"control {name!r} produced {produced}, expected {expected['yields']}."
        f" The method is: {expected['description']}."
        " Either the fixture changed or this control has stopped exercising the"
        " method it names — and a control that no longer produces its wrong"
        " number cannot prove the right one is right."
    )
    assert produced != census, (
        f"control {name!r} produced {produced}, which now EQUALS the census"
        f" ({census}). The control has stopped discriminating: it would pass"
        " whether or not the build used the wrong method, which is worse than"
        f" having no control. The method it should still expose: {expected['hides']}."
    )


def test_control_the_short_key_over_counts(seeded: str) -> None:
    """Criterion 13 — (lei, tag, period_end) counts currency and duration artifacts."""
    _control(
        seeded,
        "short_key",
        f"""SELECT count(*) FROM (
                SELECT lei, tag, period_end FROM {SCHEMA}.financial_fact
                 GROUP BY 1, 2, 3 HAVING count(DISTINCT value) > 1) s""",
    )


def test_control_the_invented_period_start_key_over_counts(seeded: str) -> None:
    """Criterion 14 — the key this specification itself invented, before reading the estate's."""
    _control(
        seeded,
        "invented_period_start_key",
        f"""SELECT count(*) FROM (
                SELECT lei, tag, unit, period_start, period_end
                  FROM {SCHEMA}.financial_fact
                 GROUP BY 1, 2, 3, 4, 5 HAVING count(DISTINCT value) > 1) s""",
    )


def test_control_accession_multiplicity_is_not_restatement(seeded: str) -> None:
    """Criterion 15 — counting filings instead of values."""
    _control(
        seeded,
        "accession_multiplicity",
        f"""SELECT count(*) FROM (
                SELECT {KEY} FROM {SCHEMA}.financial_fact
                 GROUP BY 1, 2, 3, 4, 5 HAVING count(DISTINCT accession) > 1) s""",
    )


def test_control_a_null_dropping_join_loses_every_instant_fact(seeded: str) -> None:
    """Criterion 16 — `JOIN ... USING (period_start)`, where NULL never equals NULL."""
    _control(
        seeded,
        "null_dropping_join",
        f"""SELECT count(*) FROM (
                SELECT f.lei, f.tag, f.unit, f.period_start, f.period_end
                  FROM {SCHEMA}.financial_fact f
                  JOIN (SELECT lei, tag, unit, period_start, period_end
                          FROM {SCHEMA}.financial_fact
                         GROUP BY 1, 2, 3, 4, 5
                        HAVING count(DISTINCT value) > 1) g
                    USING (lei, tag, unit, period_start, period_end)
                 GROUP BY 1, 2, 3, 4, 5) s""",
    )


def test_every_declared_control_has_a_test_and_a_distinct_number() -> None:
    """The controls are a roster, not a count — and two sharing a number is one control."""
    tested = {
        name
        for name, obj in globals().items()
        if name.startswith("test_control_") and callable(obj)
    }
    assert len(tested) == len(WRONG), (
        f"{len(WRONG)} wrong methods are declared and {len(tested)} have a test."
        " A declared method with no control is a wrong number nothing forbids."
    )
    numbers = [entry["yields"] for entry in WRONG.values()]
    assert len(set(numbers)) == len(numbers), (
        f"two wrong methods yield the same number ({numbers}); a control cannot"
        " then say which method produced it, and one of them is redundant"
    )
    assert CENSUS["restatement_cells"] not in numbers, (
        "a wrong method yields the census figure itself, so its control cannot"
        " discriminate at all"
    )


# ---------------------------------------------------------------------------
# The drift control — env-gated, and it FAILS rather than refreshing.
# ---------------------------------------------------------------------------


LIVE_DSN = "CCF_CP_03_LIVE_DSN"


@pytest.mark.skipif(
    not os.environ.get(LIVE_DSN),
    reason=f"{LIVE_DSN} unset — the live estate is on a LAN host CI cannot reach",
)
def test_the_fixture_still_matches_the_live_estate() -> None:
    """The fixture is a snapshot; this is what stops it becoming fiction.

    **IT FAILS LOUDLY AND REFRESHES NOTHING.** A drift check that regenerated the
    fixture would turn every census assertion above into a tautology about
    whatever the estate holds today. Refreshing is
    `tools/dump_cp03_fixture.py` plus a reviewed commit, deliberately — the same
    footing as changing an `expected_output.txt`.
    """
    dsn = os.environ[LIVE_DSN]
    live_facts = scalar(dsn, f"SELECT count(*) FROM {SCHEMA}.financial_fact")
    live_cells, live_obligors = rows(
        dsn, f"SELECT count(*), count(DISTINCT lei) FROM ({CELLS}) c"
    )[0]
    live_instant = scalar(
        dsn,
        f"SELECT count(*) FROM {SCHEMA}.financial_fact WHERE period_start IS NULL",
    )

    drift = [
        f"{label}: fixture {pinned}, live {actual}"
        for label, pinned, actual in (
            ("facts", CENSUS["facts_total"], live_facts),
            ("restatement cells", CENSUS["restatement_cells"], live_cells),
            ("restated obligors", CENSUS["restatement_obligors"], live_obligors),
            ("instant facts", CENSUS["facts_instant"], live_instant),
        )
        if pinned != actual
    ]
    assert not drift, (
        "the pinned fixture no longer represents the live estate:\n  "
        + "\n  ".join(drift)
        + "\n\nThis is NOT fixed by re-running the generator and moving on. Read"
        " what changed in `ccf_dataprep`, decide whether the census figures in"
        " `cp_03_census_expected.yaml` should move, and land the regenerated"
        " fixture and the revised figures in ONE reviewed commit."
    )
