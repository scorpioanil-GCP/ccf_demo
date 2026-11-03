"""Tests for the spec-coverage sweep and the shape fix it forced.

Every test here feeds the thing under test an input that must make it FAIL.
That is deliberate: this whole wave started from two checks whose output never
varied, so a test that only confirms the happy path would be the same defect in
test form.
"""

from __future__ import annotations

import pytest

from validators import binding_drift, spec_coverage


# --------------------------------------------------------------------------
# shape_of — the fix that made named individuals visible to the drift sweep
# --------------------------------------------------------------------------

@pytest.mark.parametrize(("kind", "expected"), [
    ("Class", "class"),
    ("ObjectProperty", "property"),
    ("DatatypeProperty", "property"),
    ("FunctionalProperty+ObjectProperty", "property"),
    # The case that was silently scoring 0 before Wave 15: FIBO writes an
    # enumeration value as its classifier type PLUS owl:NamedIndividual.
    ("LenderLienPosition+NamedIndividual", "individual"),
    ("NamedIndividual", "individual"),
    ("", "class"),
])
def test_shape_of(kind: str, expected: str) -> None:
    assert binding_drift.shape_of(kind) == expected


def test_shape_of_prefers_individual_over_property() -> None:
    """A compound kind carrying both must resolve to individual.

    Order matters and is not arbitrary: an individual is a VALUE, so counting
    it as a predicate asks `?a <iri> ?b` and returns a confident zero, which is
    indistinguishable from "not loaded".
    """
    assert binding_drift.shape_of("SomeProperty+NamedIndividual") == "individual"


# --------------------------------------------------------------------------
# the manifest guards
# --------------------------------------------------------------------------

def _rows(*elements: str) -> list[spec_coverage.CatalogRow]:
    return [
        spec_coverage.CatalogRow(
            product="p", element=e, provenance="", provenance_class="",
            store="Fluree", g="R",
        )
        for e in elements
    ]


def test_mapping_matching_no_row_is_an_error(monkeypatch) -> None:
    """A mapping whose element text has moved upstream must fail loudly.

    The vault patches §C prose in place. A mapping that quietly matched
    nothing would drop a catalog row out of the count while the run still
    looked clean — the exact shape of the defect this file exists to catch.
    """
    monkeypatch.setattr(spec_coverage, "read_catalog",
                        lambda product: _rows("Lien priority and filing date"))
    monkeypatch.setitem(
        spec_coverage.MANIFEST, "p",
        [spec_coverage.Mapping("a wording that no longer exists",
                               spec_coverage.WAIVED, "x")],
    )
    with pytest.raises(RuntimeError, match="matched 0 catalog rows"):
        spec_coverage.run_product("p")


def test_mapping_matching_two_rows_is_an_error(monkeypatch) -> None:
    """An ambiguous match must fail rather than silently claim the first row."""
    monkeypatch.setattr(spec_coverage, "read_catalog",
                        lambda product: _rows("Lien priority", "Lien priority and date"))
    monkeypatch.setitem(
        spec_coverage.MANIFEST, "p",
        [spec_coverage.Mapping("Lien priority", spec_coverage.WAIVED, "x")],
    )
    with pytest.raises(RuntimeError, match="matched 2 catalog rows"):
        spec_coverage.run_product("p")


def test_unmapped_rows_are_returned_not_ignored(monkeypatch) -> None:
    """A catalog row with no mapping must surface as unaccounted."""
    monkeypatch.setattr(spec_coverage, "read_catalog",
                        lambda product: _rows("Covered thing", "Forgotten thing"))
    monkeypatch.setitem(
        spec_coverage.MANIFEST, "p",
        [spec_coverage.Mapping("Covered thing", spec_coverage.WAIVED, "x")],
    )
    outcomes, unaccounted = spec_coverage.run_product("p")
    assert len(outcomes) == 1
    assert [r.element for r in unaccounted] == ["Forgotten thing"]


def test_deferred_row_fails(monkeypatch) -> None:
    """A named gap must not pass. A GAP that passed would be a waiver."""
    monkeypatch.setattr(spec_coverage, "read_catalog",
                        lambda product: _rows("Negative-pledge covenant presence"))
    monkeypatch.setitem(
        spec_coverage.MANIFEST, "p",
        [spec_coverage.Mapping("Negative-pledge", spec_coverage.DEFERRED, "absent")],
    )
    outcomes, _ = spec_coverage.run_product("p")
    assert outcomes[0].ok is False


def test_zero_probe_fails(monkeypatch) -> None:
    """The discriminating test: the same mapping passes on 1 and fails on 0."""
    monkeypatch.setattr(spec_coverage, "read_catalog",
                        lambda product: _rows("Lien priority and filing date"))
    for n, expected in ((1, True), (0, False)):
        monkeypatch.setitem(
            spec_coverage.MANIFEST, "p",
            [spec_coverage.Mapping("Lien priority", spec_coverage.PROBE, "x",
                                   probe=lambda n=n: n)],
        )
        outcomes, _ = spec_coverage.run_product("p")
        assert outcomes[0].ok is expected


# --------------------------------------------------------------------------
# the catalog reader
# --------------------------------------------------------------------------

def test_every_registered_product_has_a_readable_catalog() -> None:
    """§C must parse for all 17, with rows.

    An unreadable spec returning [] would make a product trivially and
    silently 100% covered.
    """
    for product in spec_coverage.PRODUCTS:
        rows = spec_coverage.read_catalog(product)
        assert rows, product
        assert all(r.store for r in rows), product


def test_missing_catalog_raises(tmp_path, monkeypatch) -> None:
    """A spec without a §C must raise, never return an empty catalog."""
    (tmp_path / "fake.md").write_text("# Fake\n\n## D · Assembly Recipe\n")
    monkeypatch.setattr(spec_coverage, "VAULT", tmp_path)
    with pytest.raises(RuntimeError, match="no §C Data Catalog"):
        spec_coverage.read_catalog("fake")


@pytest.mark.parametrize("heading", [
    "## C · Data Catalog",
    "## C · Data catalog",
])
def test_catalog_heading_case_is_tolerated(heading, tmp_path, monkeypatch) -> None:
    """The vault has edited one spec's heading to lowercase 'catalog'.

    Every other spec still capitalizes it. The parser must accept both —
    a case-sensitive match would silently render the catalog unreadable for
    whichever spec the vault touches next.
    """
    md = (
        f"# Fake\n\n{heading}\n\n"
        "| Element | Provenance | Class | Store | G |\n"
        "|---|---|---|---|---|\n"
        "| foo | bar | public | Postgres | 1 |\n\n"
        "## D · Assembly Recipe\n"
    )
    (tmp_path / "fake.md").write_text(md)
    monkeypatch.setattr(spec_coverage, "VAULT", tmp_path)
    rows = spec_coverage.read_catalog("fake")
    assert rows
    assert rows[0].element == "foo"


# --------------------------------------------------------------------------
# manifest-vs-spec drift — the failure mode this file exists to catch early
# --------------------------------------------------------------------------

def test_every_manifest_still_resolves_against_its_live_spec() -> None:
    """Each mapping must still match exactly one §C row, for every product.

    THE DRIFT THIS CATCHES IS SILENT AND ALPHABETICAL. The vault patches §C
    prose in place, so a mapping's substring can stop matching without anyone
    touching this repo. `run_product` raises on that -- correctly -- but the
    sweep runs products in alphabetical order and the raise aborts the whole
    run, so ONE stale mapping hides every product sorted after it. That is
    what happened to `counterparty-reference-snapshot`: the vault re-authored
    it to spec-standard-v0-3, collapsing §C from 10 rows to 4, and the crash
    masked every product from `covenant-` onward until each was run singly.

    This arm resolves the mappings WITHOUT probing the stores, so it fails on
    drift alone and does not go red merely because an estate is unloaded.
    """
    stale: list[str] = []
    for product, mappings in spec_coverage.MANIFEST.items():
        rows = spec_coverage.read_catalog(product)
        claimed: dict[int, str] = {}
        for mp in mappings:
            needle = mp.match.casefold()
            hits = [i for i, r in enumerate(rows)
                    if needle in r.element.casefold()]
            if len(hits) != 1:
                stale.append(
                    f"{product}: {mp.match!r} matched {len(hits)} rows")
            elif hits[0] in claimed:
                stale.append(
                    f"{product}: {mp.match!r} and {claimed[hits[0]]!r} both "
                    f"claim row {hits[0]}")
            else:
                claimed[hits[0]] = mp.match
        unmapped = [r.element for i, r in enumerate(rows) if i not in claimed]
        if unmapped:
            stale.append(f"{product}: {len(unmapped)} §C row(s) unmapped: "
                         + "; ".join(e[:60] for e in unmapped))
    assert not stale, "manifest has drifted from the vault:\n  " + "\n  ".join(stale)


# --------------------------------------------------------------------------
# addresses — present, LABELLED, and excluding exactly the entities GLEIF
# has no record of
# --------------------------------------------------------------------------
#
# §C names `addresses`, plural; §B names which two, "headquarters and legal
# address". Until Wave 20 this estate held one unlabelled triple. The defect
# was never a missing column so much as an ambiguous one: a missing address
# returns nothing and the consumer notices, while an unlabelled one returns
# Wilmington, Delaware for a company run from Whippany, New Jersey.

REAL = "5493001L3UGXFYA41M70"
SYN = "SYN-SDART-2022-6"


def test_a_real_lei_entity_with_both_addresses_passes() -> None:
    assert spec_coverage._addresses_labelled([(REAL, "US", "US")]) == 1


def test_a_real_lei_entity_missing_its_headquarters_fails() -> None:
    """THE FALSIFIER. This is the state the estate was in for every entity."""
    assert spec_coverage._addresses_labelled([(REAL, "US", None)]) == 0


def test_a_real_lei_entity_missing_its_legal_address_fails() -> None:
    assert spec_coverage._addresses_labelled([(REAL, None, "US")]) == 0


def test_a_synthetic_entity_without_a_headquarters_is_not_a_failure() -> None:
    """The three ABS deal trusts. GLEIF has no record of them and never will,
    so requiring a GLEIF-sourced address of them would make the row
    permanently and wrongly red."""
    assert spec_coverage._addresses_labelled([(REAL, "US", "US"),
                                              (SYN, None, None)]) == 1


def test_one_bad_row_among_many_good_ones_still_fails() -> None:
    """Deliberately brittle, for the reason the family-tree probe is: a count
    of entities with both addresses would sail past a partial regression."""
    rows = [(REAL, "US", "US")] * 50 + [("549300LFK257DF2RVN05", "GB", None)]
    assert spec_coverage._addresses_labelled(rows) == 0


def test_an_empty_estate_does_not_pass_by_accident() -> None:
    assert spec_coverage._addresses_labelled([]) == 0


def test_the_two_real_lei_definitions_agree() -> None:
    """`spec_coverage` and `conditions` each carry a real-LEI pattern.

    They are separate modules on purpose -- neither imports the other -- but
    two copies of one definition drift, and a drifted copy here would silently
    change which entities this row polices. So the copies are asserted equal
    rather than hoped equal.
    """
    import importlib.util
    import sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "conditions_for_lei_check", repo / "validators" / "conditions.py")
    cond = importlib.util.module_from_spec(spec)
    sys.modules["conditions_for_lei_check"] = cond
    spec.loader.exec_module(cond)
    assert spec_coverage._REAL_LEI.pattern == cond._REAL_LEI.pattern


# --- distinguishability: two addresses, or one address typed twice? --------
#
# 4 of the 69 rows that differ on a raw comparison differ ONLY BY CASE --
# AMPHENOL CORP /DE/ carries WILMINGTON against Wilmington, HNA ACQUISITION
# ULC carries EDMONTON against Edmonton. A raw `IS DISTINCT FROM` scores those
# as two addresses when they are one address typed twice.
#
# It does not dent the conclusion (65 of 153 still differ, 42%), but the
# question the assertion has to answer is "are these different PLACES", not
# "do these strings differ", and those are not the same question.

def test_the_same_place_typed_in_two_cases_is_one_place() -> None:
    """THE FALSIFIER, and it is a real row: AMPHENOL CORP /DE/."""
    assert spec_coverage._same_place(("US", "WILMINGTON", "US-DE"),
                                     ("US", "Wilmington", "US-DE"))


def test_surrounding_whitespace_does_not_make_a_second_place() -> None:
    assert spec_coverage._same_place(("US", "Wilmington ", "US-DE"),
                                     ("US", " Wilmington", "US-DE"))


def test_genuinely_different_cities_are_different_places() -> None:
    """The Delaware pattern this whole gap exists to expose."""
    assert not spec_coverage._same_place(("US", "Wilmington", "US-DE"),
                                         ("US", "Whippany", "US-NJ"))


def test_a_different_region_alone_is_a_different_place() -> None:
    assert not spec_coverage._same_place(("US", "Portland", "US-OR"),
                                         ("US", "Portland", "US-ME"))


def test_a_missing_component_is_not_quietly_equal_to_a_present_one() -> None:
    assert not spec_coverage._same_place(("US", None, "US-DE"),
                                         ("US", "Wilmington", "US-DE"))
