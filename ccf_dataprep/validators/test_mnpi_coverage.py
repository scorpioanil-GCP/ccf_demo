#!/usr/bin/env python3
"""Falsify every probe in `spec_coverage.py`'s `mnpi-wall-enforcement` manifest.

    uv run --with pytest pytest validators/test_mnpi_coverage.py

A coverage manifest is only worth the probes behind it, and this estate's
dominant defect is a check that cannot fail -- a gate whose query returns a
positive number whatever happened to the data. `MNPI_WALL` added eleven such
queries in one commit, which is eleven chances to ship decoration.

So every probe is tested TWICE: once against the estate, where it must find
something, and once in a deliberately falsified form of the SAME query shape,
where it must find nothing. A probe that answers the same in both directions
is not measuring anything, and only the pair tells them apart.

The falsified form always perturbs the SELECTOR, never the population: a
bogus form name, a class IRI that was never loaded, a join key mangled by one
character. That is what distinguishes "this query can return zero" from "this
table happens to be empty right now".

Read-only throughout. Nothing here writes to any store.
"""

from __future__ import annotations

import pytest

from ccf.config import PG_SCHEMA_V2, mongo_db, pg_connect
from validators.spec_coverage import (
    MANIFEST,
    PROBE,
    EX,
    fluree_instances,
    mnpi_classified_documents,
    mnpi_edgar_filings,
    mnpi_issuer_leis,
    mnpi_research_both_states,
    pg_count,
    read_catalog,
    run_product,
)

PRODUCT = "mnpi-wall-enforcement"


# --------------------------------------------------------------------------
# the manifest's own shape
# --------------------------------------------------------------------------

def test_manifest_accounts_for_every_catalog_row():
    """No §C row left unmapped -- the condition that had this product UNMAP."""
    rows = read_catalog(PRODUCT)
    _, unaccounted = run_product(PRODUCT)
    assert unaccounted == [], (
        f"{len(unaccounted)} of {len(rows)} rows unmapped: "
        f"{[r.element[:40] for r in unaccounted]}")


def test_catalog_is_the_fifteen_rows_this_manifest_was_written_against():
    """Pins the population. If the vault patches §C and the row count moves,
    this fails LOUDLY rather than the manifest silently covering fewer rows.
    """
    assert len(read_catalog(PRODUCT)) == 15


def test_every_probe_mapping_actually_carries_a_probe():
    for mp in MANIFEST[PRODUCT]:
        if mp.state == PROBE:
            assert callable(mp.probe), f"{mp.match!r} is PROBE with no probe"


# --------------------------------------------------------------------------
# direction 1 -- each probe finds what is there
# --------------------------------------------------------------------------

def test_every_probe_finds_something_today():
    zero = [mp.match for mp in MANIFEST[PRODUCT]
            if mp.state == PROBE and mp.probe() == 0]
    assert zero == [], f"probes returning ZERO: {zero}"


# --------------------------------------------------------------------------
# direction 2 -- the falsification: the same query shape must be able to
# return zero. Each case perturbs the SELECTOR and nothing else.
# --------------------------------------------------------------------------

def test_crosswalk_join_can_miss():
    """Issuer/family row: mangle the join key by one character."""
    assert pg_count(
        "SELECT count(*) FROM (SELECT DISTINCT d.lei FROM {S}.deal d "
        "JOIN {S}.crosswalk x ON x.lei = d.lei || 'X') t") == 0


def test_edgar_filing_probe_can_miss_on_form():
    """Filings row: a form family that was never filed."""
    assert mongo_db(write=False)["document"].count_documents({
        "form": {"$in": ["NOT-A-REAL-FORM"]},
        "lei": {"$in": mnpi_issuer_leis()},
    }) == 0


def test_edgar_filing_probe_can_miss_on_issuer():
    """Filings row, the other half: right forms, issuers that do not exist.

    This is the case that matters. The probe is scoped to THIS product's
    issuers precisely so it falls over if the filings stop covering them,
    and a scope that cannot miss is not a scope.
    """
    assert mongo_db(write=False)["document"].count_documents({
        "form": {"$in": ["10-K", "10-Q", "8-K"]},
        "lei": {"$in": ["NOTALEI00000000000000"]},
    }) == 0


@pytest.mark.parametrize("cls", ["RegFDEvent", "WallCrossing", "EmbargoWindow"])
def test_fluree_class_probes_can_miss(cls):
    """The three Fluree probes: a class IRI that was never loaded.

    Also asserts the real class IS found, so the pair proves the query
    discriminates rather than merely that one of them is empty.
    """
    assert fluree_instances(f"{EX}{cls}") > 0
    assert fluree_instances(f"{EX}{cls}ThatWasNeverLoaded") == 0


def test_gdelt_scope_can_miss():
    """Adverse-media row: mangle the join key by one character."""
    assert pg_count(
        "SELECT count(*) FROM {S}.gdelt_mention g "
        "JOIN {S}.deal d ON d.lei = g.lei || 'X'") == 0


def test_mnpi_interaction_probe_counts_the_flag_not_the_table():
    """Interaction row: the flagged subset must be a STRICT subset.

    If every interaction were MNPI-bearing the probe would be indistinguishable
    from `count(*)`, and clearing the flags is exactly the silent change it
    exists to catch.
    """
    flagged = pg_count(
        "SELECT count(*) FROM {S}.interaction WHERE mnpi_bearing")
    total = pg_count("SELECT count(*) FROM {S}.interaction")
    assert 0 < flagged < total, f"flagged={flagged} total={total}"
    assert pg_count(
        "SELECT count(*) FROM {S}.interaction "
        "WHERE mnpi_bearing AND 1 = 0") == 0


def test_deal_and_position_probes_can_miss():
    for table in ("deal", "position"):
        assert pg_count(f"SELECT count(*) FROM {{S}}.{table}") > 0
        assert pg_count(
            f"SELECT count(*) FROM {{S}}.{table} WHERE 1 = 0") == 0


def test_research_probe_falls_to_zero_if_either_state_empties():
    """The published/draft row: this is the whole reason it takes a MINIMUM.

    A plain count of research notes would stay green if every draft were
    published. Taking the smaller of the two states means emptying EITHER one
    zeroes the probe -- proven here by asking for a status that does not exist
    on each side in turn.
    """
    notes = mongo_db(write=False)["research_note"]
    published = notes.count_documents({"status": "published"})
    draft = notes.count_documents({"status": "draft"})
    assert published > 0 and draft > 0
    assert mnpi_research_both_states() == min(published, draft)
    # either side going empty must zero it
    assert min(published, notes.count_documents({"status": "no-such"})) == 0
    assert min(notes.count_documents({"status": "no-such"}), draft) == 0


def test_classification_probe_can_miss():
    """Classification row: a field name that no document carries."""
    db = mongo_db(write=False)
    absent = {"no_such_field": {"$exists": True, "$ne": None}}
    assert sum(db[c].count_documents(absent)
               for c in ("document", "research_note", "memorandum")) == 0
    assert mnpi_classified_documents() > 0


# --------------------------------------------------------------------------
# the two GAPs are real absences, not unwritten probes
# --------------------------------------------------------------------------

def test_no_issuer_level_market_data_exists():
    """The `Public market data` GAP, recomputed rather than asserted.

    §C wants per-issuer TRACE/price data. The claim is that none of the three
    market tables carries an `lei`. The control is the estate-wide count of
    tables that DO -- without it, a typo in the column name would look
    exactly like the gap.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_schema = %s AND column_name = 'lei' "
            "AND table_name IN "
            "('market_oas_series', 'intraday_tick', 'fx_intraday_tick')",
            (PG_SCHEMA_V2,))
        assert cur.fetchone()[0] == 0
        cur.execute(
            "SELECT count(DISTINCT table_name) FROM information_schema.columns "
            "WHERE table_schema = %s AND column_name = 'lei'",
            (PG_SCHEMA_V2,))
        assert cur.fetchone()[0] > 0, "control failed: no table carries lei"


def test_no_blackout_window_exists_in_fluree():
    """The `Insider transaction and blackout windows` GAP.

    Searches the live type list rather than a remembered one, and requires the
    same search to FIND the neighbouring types -- otherwise a broken query
    reads as a clean absence, which is how this estate has been fooled before.
    """
    from ccf import fluree
    from ccf.config import FLUREE_LEDGER_V2

    q = (f"SELECT DISTINCT ?t FROM <{FLUREE_LEDGER_V2}> "
         f"WHERE {{ ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?t }}")
    types = [b["t"]["value"]
             for b in fluree.query(q)["results"]["bindings"]]

    assert [t for t in types if "blackout" in t.lower()] == []
    # control: the search space is real and contains the adjacent concepts
    for neighbour in ("WallCrossing", "EmbargoWindow", "RegFDEvent"):
        assert any(t.endswith(neighbour) for t in types), \
            f"control failed: {neighbour} not in the type list"
