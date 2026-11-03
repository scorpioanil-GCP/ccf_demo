"""Tests for the Florida UCC-1 lien-filing layer.

Every check here recomputes from the stores. Nothing reads a stored count, a
cached score, or a boolean flag written by the loader -- a gate that reads the
loader's own claim can only ever agree with it.

The controls matter more than usual for this source. The Florida search API has
a mode (`searchCategory=Standard`) that returns twenty alphabetically-near
names for ANY input, so a fetch built on it reports a 100% hit rate and means
nothing. Several tests below therefore assert BOTH that a known-present thing
is found and that a known-absent thing is not -- a check that cannot return
"no" is not a check.
"""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pytest

from ccf import config as C
from ccf import fluree
from loaders.load_ucc_fl_wave21 import _norm, _party_key, build_triples

EX = "http://example.org/fibo/"
SOURCE = Path(__file__).resolve().parent.parent / "sources" / "ucc_fl" / "mastec.json"


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(SOURCE.read_text())


def _rows(where: str, sel: str = "?f") -> list:
    """Bindings for a WHERE clause. Counted CLIENT-SIDE, deliberately.

    Fluree's `COUNT(*)` is not trustworthy here. For the two-pattern clause
    `?f a ex:UccFiling ; ex:filedOn ?d .` it reports **17** where the query
    actually returns **65** rows; `COUNT(DISTINCT ?f)` returns 65. A single
    -pattern count happens to be right, which is what makes this dangerous --
    the aggregate is wrong only sometimes, so spot-checking it agrees.

    So no check in this file asks the store to count. They ask for the rows
    and count them here, where the arithmetic is ours and verifiable.
    See docs/known-issues.md §60.
    """
    res = fluree.query(
        "PREFIX ex: <http://example.org/fibo/> "
        f"SELECT {sel} FROM <{C.FLUREE_LEDGER_V2}> WHERE {{ {where} }}")
    return res["results"]["bindings"]


def _ask_count(where: str, sel: str = "?f") -> int:
    return len(_rows(where, sel))


# --------------------------------------------------------------------------
# the pure builder -- no stores needed
# --------------------------------------------------------------------------

def test_secured_party_key_preserves_trailing_space() -> None:
    """The register holds two spellings of one party. Keep them distinct.

    'BANC OF AMERICA LEASING & CAPITAL, LLC' appears both with and without a
    trailing space. Any key that strips whitespace merges them and destroys
    the only evidence the register carries about its own inconsistency -- and
    that evidence is what makes the debtor-name join genuinely imperfect
    rather than engineered.
    """
    a = "BANC OF AMERICA LEASING & CAPITAL, LLC"
    b = "BANC OF AMERICA LEASING & CAPITAL, LLC "
    assert _party_key(a) != _party_key(b), (
        "the two filed spellings collapsed to one key -- the trailing-space "
        "variant has been silently merged"
    )
    # ... and the same string must key stably, or the load is not idempotent.
    assert _party_key(a) == _party_key(a)


def test_lapses_on_is_omitted_not_defaulted(data: dict) -> None:
    """A filing with no stated expiry must have NO lapsesOn triple.

    Defaulting the date would make "the registry did not say" indistinguishable
    from "it lapses on this date", which is exactly the kind of invented
    certainty this product exists to refute.
    """
    triples = build_triples(data)
    lapses = [t for t in triples if f"{EX}lapsesOn" in t]
    filings = [t for t in triples if t.endswith(f"<{EX}UccFiling> .")]
    assert len(filings) == 65
    assert len(lapses) == 64, (
        f"expected 64 lapsesOn for 65 filings (one filing has no expiry); "
        f"got {len(lapses)} -- a default may have crept in"
    )


def test_norm_is_scoring_only_and_never_reaches_a_triple(data: dict) -> None:
    """Normalised names must not be stored. Only filed strings are.

    POSITIVE + NEGATIVE control in one: the filed string must appear, and its
    normalised form must not.
    """
    triples = "\n".join(build_triples(data))
    filed = "MASTEC, INC."
    assert filed in triples, "the filed debtor name is absent -- check the loader"
    normalised = _norm(filed)          # 'MASTEC'
    assert f'"{normalised}"' not in triples, (
        f"the normalised form {normalised!r} was stored; normalisation is for "
        f"scoring only"
    )


# --------------------------------------------------------------------------
# the loaded ledger
# --------------------------------------------------------------------------

def test_filings_are_in_fluree(data: dict) -> None:
    n = _ask_count("?f a ex:UccFiling .")
    assert n == data["filings_retrieved"] == 65, (
        f"ledger holds {n} UccFiling nodes, source has "
        f"{data['filings_retrieved']}"
    )


def test_every_filing_has_a_filing_date() -> None:
    """§C's DEFERRED row. The filing date is the whole reason for this layer."""
    filings = _ask_count("?f a ex:UccFiling .")
    dated = _ask_count("?f a ex:UccFiling ; ex:filedOn ?d .")
    assert filings > 0, "no filings loaded -- this check would pass vacuously"
    assert dated == filings, f"{filings - dated} filings carry no filedOn"


def test_every_filing_date_matches_the_source(data: dict) -> None:
    """Every stored date must equal the date the registry supplied.

    THIS IS THE CHECK THAT CAUGHT THE REAL BUG, and it is the one no count
    could have caught. `test_every_filing_has_a_filing_date` passed while all
    65 dates were WRONG: the triples existed, they simply did not hold the
    values written. Counting presence cannot see a value being altered.

    The cause was `^^xsd:date` typing -- this Fluree build corrupts a typed
    date arriving through SPARQL UPDATE, returning 1971-11-15 for a literal
    written as 2024-12-19, with 53 distinct deltas across 65 filings, so it
    is arbitrary rather than an offset. Dates are now written untyped, which
    round-trips exactly and is the estate's existing convention.
    See docs/known-issues.md §59.
    """
    src = {r["ucc_number"]: r["file_date"][:10] for r in data["debtors"]}
    res = fluree.query(
        "PREFIX ex: <http://example.org/fibo/> SELECT ?n ?d "
        f"FROM <{C.FLUREE_LEDGER_V2}> "
        "WHERE { ?f a ex:UccFiling ; ex:filingNumber ?n ; ex:filedOn ?d . }")
    got = {b["n"]["value"]: b["d"]["value"] for b in res["results"]["bindings"]}
    assert got, "no filing dates in the ledger -- this check would be vacuous"
    wrong = {k: (src.get(k), v) for k, v in got.items() if src.get(k) != v}
    assert not wrong, (
        f"{len(wrong)} of {len(got)} stored dates differ from the source. "
        f"First: {list(wrong.items())[:3]}")


def test_date_filter_discriminates() -> None:
    """A date range must actually filter -- positive AND negative control.

    Without this, "filings since 2020" could match everything or nothing and
    still look like it worked.
    """
    all_f = _ask_count("?f a ex:UccFiling ; ex:filedOn ?d .")
    within = _ask_count(
        '?f a ex:UccFiling ; ex:filedOn ?d . FILTER(?d >= "2005-01-01")')
    impossible = _ask_count(
        '?f a ex:UccFiling ; ex:filedOn ?d . FILTER(?d < "1990-01-01")')
    partial = _ask_count(
        '?f a ex:UccFiling ; ex:filedOn ?d . FILTER(?d >= "2020-01-01")')
    assert within == all_f > 0, (
        f"positive control: a range covering the whole register matched "
        f"{within} of {all_f}")
    assert impossible == 0, (
        f"negative control: a range predating the register matched "
        f"{impossible} filings -- the filter is not filtering")
    assert 0 < partial < all_f, (
        f"a mid-range cut matched {partial} of {all_f}; a filter returning "
        f"all or nothing is not discriminating")


def test_terminated_liens_are_identifiable() -> None:
    """The demonstrable claim: some liens the estate calls 'secured' are dead.

    This is what a first/second column cannot express, and it is why the
    filing date and the amendment chain had to be loaded together.
    """
    terminated = _ask_count(
        '?f a ex:UccFiling ; ex:amendedBy ?a . '
        '?a ex:amendmentAction "Termination" .')
    continued = _ask_count(
        '?f a ex:UccFiling ; ex:amendedBy ?a . '
        '?a ex:amendmentAction "Continuation" .')
    nonsense = _ask_count(
        '?f a ex:UccFiling ; ex:amendedBy ?a . '
        '?a ex:amendmentAction "ZzqqxxNotAnAction" .')
    assert terminated > 0, "no terminations found -- the contrast cannot be shown"
    assert continued > 0, "no continuations found"
    assert nonsense == 0, (
        "negative control: an invented action matched -- the action filter is "
        "not filtering")


def test_secured_party_variants_survive_the_load() -> None:
    """24 filed spellings, 23 parties. Both numbers must be recoverable."""
    nodes = _ask_count("?p a ex:SecuredParty .")
    assert nodes == 24, (
        f"expected 24 SecuredParty nodes (one per filed spelling); got {nodes}. "
        f"23 would mean the trailing-space variant was normalised away")


# --------------------------------------------------------------------------
# partition -- both directions
# --------------------------------------------------------------------------

def test_postgres_holds_the_crosswalk_and_no_filing_attribute() -> None:
    """Single-writer discipline, checked in both directions.

    Present-where-it-belongs AND absent-where-it-does-not. `partition.py`
    historically only ever checked the second, which is why a MISSING element
    could never be caught by it.
    """
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute(f"select count(*) from {C.PG_SCHEMA_V2}.ucc_debtor_crosswalk")
        rows = cur.fetchone()[0]
        assert rows == 16, f"expected 16 crosswalk rows, got {rows}"

        cur.execute("""select column_name from information_schema.columns
                       where table_schema=%s and table_name='ucc_debtor_crosswalk'""",
                    (C.PG_SCHEMA_V2,))
        cols = {r[0] for r in cur.fetchall()}

    # Fluree owns every filing fact. None of these may appear in Postgres.
    forbidden = {"file_date", "filed_on", "expiration_date", "lapses_on",
                 "secured_party", "filing_status", "document_type",
                 "amendment_action", "ucc_number", "filing_number"}
    leaked = cols & forbidden
    assert not leaked, f"filing attributes leaked into Postgres: {sorted(leaked)}"
    assert {"filed_debtor_name", "lei", "match_score"} <= cols


def test_unmatched_debtors_are_kept_not_dropped() -> None:
    """An unmatched debtor is a fact. Dropping it would inflate match rate."""
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute(f"""select count(*) filter (where lei is not null),
                               count(*) filter (where lei is null)
                        from {C.PG_SCHEMA_V2}.ucc_debtor_crosswalk""")
        matched, unmatched = cur.fetchone()
    assert matched >= 1, "no debtor matched an LEI -- the join is broken"
    assert unmatched >= 1, (
        "every filed name matched, which for 62 subsidiaries absent from "
        "legal_entity is not credible -- check the accept threshold")


def test_idempotent_reload_preserves_a_named_value() -> None:
    """Idempotency proved by a VALUE, not a count.

    A row count cannot see a field being reset to null on reload, which is the
    failure mode this names instead.
    """
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute(f"""select lei, match_score from
                        {C.PG_SCHEMA_V2}.ucc_debtor_crosswalk
                        where filed_debtor_name = 'MASTEC, INC.'""")
        row = cur.fetchone()
    assert row is not None, "the MasTec parent row is missing"
    lei, score = row
    assert lei == "549300TMDIT8WREDOF45", (
        f"MasTec's LEI is {lei!r} -- a reload has reset or re-derived it wrongly")
    assert score is not None and float(score) >= 0.90


def test_provenance_uses_the_estates_three_classes_only() -> None:
    """CLAUDE.md defines exactly three provenance classes. Not two, not four.

    This loader shipped `"derived"` on its first pass -- a plausible-sounding
    label that is not in the vocabulary, and which `validators/large_exposure.py`
    uses as its *example* of an unrecognised one. Nothing caught it, because no
    check compared a provenance value against the permitted set.
    """
    permitted = {"public", "synthetic — internal", "synthetic — engineered"}
    with psycopg.connect(**C.PG) as conn:
        cur = conn.cursor()
        cur.execute(f"""select distinct provenance
                        from {C.PG_SCHEMA_V2}.ucc_debtor_crosswalk""")
        found = {r[0] for r in cur.fetchall()}
    assert found, "no provenance values -- this check would pass vacuously"
    assert found <= permitted, (
        f"provenance outside the three permitted classes: {found - permitted}")
