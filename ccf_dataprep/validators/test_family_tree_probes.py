#!/usr/bin/env python3
"""The family-tree probes must be able to FAIL.

`validators/spec_coverage.py` accounts for the two parent-relationship rows of
`corporate-family-tree` §C with a probe that compares each edge's DIRECTION
against the GLEIF record it was built from, rather than counting edges. The
reason is known-issues §19.3: all 139 ultimate-parent edges in the ledger
pointed the wrong way for twelve waves, and every registered condition passed
throughout, because each one counted edges, hops or cycles and a reversed
graph has exactly as many of all three.

A probe written to catch that is worthless unless it can be shown to go red on
the very data it claims to reject, so every arm here feeds `_oriented()` a
hand-built pair of sets whose right answer is known before running it.

The arm that matters is `test_one_flipped_edge_zeroes_the_probe`. The obvious
implementation -- count the edges that agree with GLEIF and pass if that count
is above zero -- survives every other arm in this file and fails only that
one. A single loader re-run over a subset is the realistic regression, and it
leaves most edges correct; a probe asking "are some still right?" answers yes
forever.

    uv run --with pytest pytest validators/test_family_tree_probes.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "spec_coverage", REPO / "validators" / "spec_coverage.py")
sc = importlib.util.module_from_spec(_spec)
# Registered before exec: spec_coverage defines dataclasses, and
# @dataclass resolves annotations through sys.modules[cls.__module__].
sys.modules["spec_coverage"] = sc
_spec.loader.exec_module(sc)

#: GLEIF states consolidation as (child, parent). Three unrelated families so
#: that a bug collapsing the sets cannot pass by coincidence.
GLEIF = {("CHILD_A", "PARENT_A"), ("CHILD_B", "PARENT_B"), ("CHILD_C", "PARENT_C")}


# --- has*UltimateParent: subject is the CHILD -----------------------------

def test_correctly_oriented_ultimate_parent_edges_count():
    edges = {("CHILD_A", "PARENT_A"), ("CHILD_B", "PARENT_B")}
    assert sc._oriented(edges, GLEIF, subject_is_child=True) == 2


def test_fully_inverted_ultimate_parent_edges_return_zero():
    """The §19.3 estate exactly: every edge asserted parent -> child."""
    edges = {("PARENT_A", "CHILD_A"), ("PARENT_B", "CHILD_B")}
    assert sc._oriented(edges, GLEIF, subject_is_child=True) == 0


def test_one_flipped_edge_zeroes_the_probe():
    """THE FALSIFIER. Two edges right, one wrong -- a count would say 2."""
    edges = {("CHILD_A", "PARENT_A"),
             ("CHILD_B", "PARENT_B"),
             ("PARENT_C", "CHILD_C")}
    assert sc._oriented(edges, GLEIF, subject_is_child=True) == 0


# --- owns: subject is the PARENT ------------------------------------------

def test_correctly_oriented_owns_edges_count():
    edges = {("PARENT_A", "CHILD_A"), ("PARENT_B", "CHILD_B")}
    assert sc._oriented(edges, GLEIF, subject_is_child=False) == 2


def test_inverted_owns_edges_return_zero():
    edges = {("CHILD_A", "PARENT_A"), ("PARENT_B", "CHILD_B")}
    assert sc._oriented(edges, GLEIF, subject_is_child=False) == 0


# --- the two directions must not be interchangeable -----------------------

def test_the_subject_is_child_flag_actually_changes_the_answer():
    """A probe reading the same for both flags would be checking nothing.

    Both parent rows in §C are mapped through this one function, and the only
    thing distinguishing them is this argument.
    """
    edges = {("CHILD_A", "PARENT_A"), ("CHILD_B", "PARENT_B")}
    assert sc._oriented(edges, GLEIF, subject_is_child=True) == 2
    assert sc._oriented(edges, GLEIF, subject_is_child=False) == 0


# --- edges GLEIF cannot adjudicate ----------------------------------------

def test_edges_absent_from_gleif_are_neither_matched_nor_contradictions():
    """Engineered cycle edges have no GLEIF record and must not zero the row.

    Five of the ledger's LEI-to-LEI `owns` edges are not GLEIF direct-parent
    records. Treating an unknown pair as a contradiction would fail the row
    for data the spec asks to be engineered.
    """
    edges = {("PARENT_A", "CHILD_A"), ("SYN_X", "SYN_Y")}
    assert sc._oriented(edges, GLEIF, subject_is_child=False) == 1


def test_empty_edge_set_does_not_pass():
    """An unloaded ledger must read as absent, not as 'no contradictions'."""
    assert sc._oriented(set(), GLEIF, subject_is_child=True) == 0


# --- attribute resolution: 0 unless EVERY graph LEI resolves ---------------

GRAPH = {"LEI_A", "LEI_B", "LEI_C"}


def test_all_resolving_passes():
    assert sc._all_resolve(GRAPH, {"LEI_A", "LEI_B", "LEI_C", "LEI_SPARE"}) == 1


def test_one_unresolved_lei_fails_the_row():
    """THE FALSIFIER.

    The natural probe here is "how many graph entities resolve?", and it would
    have returned 50 while 105 resolved to nothing -- passing this row for
    twelve waves on the strength of the ones that worked. The quantity that
    decides the row is the SHORTFALL, so two of three resolving is a failure,
    not a two-thirds pass.
    """
    assert sc._all_resolve(GRAPH, {"LEI_A", "LEI_B"}) == 0


def test_none_resolving_fails():
    assert sc._all_resolve(GRAPH, set()) == 0


def test_an_empty_graph_is_not_a_pass_by_accident():
    """An unloaded ledger has no unresolved LEIs, which is not the same thing.

    This arm documents the one input where the probe's answer is vacuous: it
    returns 1 for an empty graph.

    WHICH FLOOR COVERS THAT MOVED on 2026-08-28. It used to be `conditions.py`'s
    500-entity floor, which was the right guard while the population was every
    LEI-bearing entity in the ledger. The population is now the LEI-bearing
    ENDPOINTS OF FAMILY EDGES, so an estate keeping all its entities and losing
    all its ownership edges would empty this set and green the row while the
    entity floor stayed happy. The guard is therefore `conditions.py`'s
    "ownership graph edges (all predicates) >= 500" -- if THAT floor is ever
    removed, this probe stops meaning anything.
    """
    assert sc._all_resolve(set(), set()) == 1


# --- merged filers: two Exhibit 21 lists collapsing into one entity --------

_c_spec = importlib.util.spec_from_file_location(
    "conditions", REPO / "validators" / "conditions.py")
cond = importlib.util.module_from_spec(_c_spec)
sys.modules["conditions"] = cond
_c_spec.loader.exec_module(cond)

STUBS = {"stubA", "stubB", "stubC"}


def test_a_clean_graph_reports_no_merged_filers():
    edges = [("AnchorOne", "stubA"), ("AnchorTwo", "stubB")]
    assert cond.count_stubs_with_two_filers(STUBS, edges) == 0


def test_a_stub_owned_by_two_filers_is_caught():
    """The §19.6 shape: one node, two unrelated companies' Exhibit 21s."""
    edges = [("AnchorOne", "stubA"), ("AnchorTwo", "stubA")]
    assert cond.count_stubs_with_two_filers(STUBS, edges) == 1


def test_an_engineered_chain_member_is_NOT_flagged():
    """THE FALSE-POSITIVE CONTROL, and the reason for the exclusion.

    A stub in a depth chain genuinely has two parents — its anchor and the
    stub above it. Nine of them do. A gate that counted parents rather than
    non-stub parents would fire on all nine on its first run and be deleted
    as noise, taking the real check with it.
    """
    edges = [("AnchorOne", "stubA"), ("AnchorOne", "stubB"), ("stubA", "stubB")]
    assert cond.count_stubs_with_two_filers(STUBS, edges) == 0


def test_both_shapes_at_once_counts_only_the_merge():
    edges = [("AnchorOne", "stubA"), ("stubA", "stubB"), ("AnchorOne", "stubB"),
             ("AnchorOne", "stubC"), ("AnchorTwo", "stubC")]
    assert cond.count_stubs_with_two_filers(STUBS, edges) == 1


# --- dual typing: fibo ContractualDefinition alongside the ex: role --------

def test_dual_typed_separates_present_from_absent_on_the_live_ledger():
    """The known-present / known-absent pair, and the estate supplies both.

    The vault corrected two specs on 2026-08-24 after this validator reported
    that their §C claimed "no FIBO term exists" for `CovenantDefinition`. The
    correction requires BOTH types on every node, so the probe must go to zero
    when one is missing rather than counting the nodes that have both.

    `ex:Covenant` is the negative control and it is real data, not a fixture:
    182 nodes carry it and NONE carries `ContractualDefinition`, correctly —
    FIBO's class describes a definition, and a covenant is not one. A probe
    that returned a bare count would report 182 here and green a row the spec
    says must be dual-typed.
    """
    assert sc.dual_typed(("CovenantDefinition", "DefinedTerm")) == 207
    assert sc.dual_typed(("Covenant",)) == 0
    assert sc.dual_typed(("MeasurementPeriod",)) == 0


def test_dual_typed_does_not_pass_vacuously_on_an_absent_type():
    """Zero nodes is not "no violations"; it is nothing loaded."""
    assert sc.dual_typed(("NoSuchTypeExistsHere",)) == 0


# --- rule #1: every element carries a provenance class ---------------------

def _unlabelled(type_iri: str) -> int:
    """The check's shape, run against any type: typed MINUS labelled."""
    from ccf import fluree
    from ccf.config import FLUREE_LEDGER_V2 as LEDGER

    RT = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    EXN = "http://example.org/fibo/"

    def n(where):
        return len({b["s"]["value"] for b in fluree.query(
            f"SELECT ?s FROM <{LEDGER}> WHERE {{ {where} }} LIMIT 9000"
        )["results"]["bindings"]})

    return (n(f"?s <{RT}> <{type_iri}> ")
            - n(f"?s <{RT}> <{type_iri}> . ?s <{EXN}provenance> ?p"))


def test_the_provenance_gate_discriminates_on_live_data():
    """Known-clean and known-dirty, both real, and the answers must differ.

    The gate this mirrors exists because `entities in Fluree` counts
    `?s ex:provenance ?p` — so a node with NO class is absent from the count
    rather than failing it, and 192 sat unlabelled for twelve waves inside a
    check whose whole job was labelling. A gate whose population is defined by
    the property it polices cannot see that property missing.

    `owl:Class` is the dirty input and it is genuine: 46 T-Box class
    declarations, 9 labelled, because a schema node legitimately carries no
    provenance. A gate written the blind way returns 0 for both arms.
    """
    clean = _unlabelled("https://www.omg.org/spec/Commons/Organizations/LegalEntity")
    dirty = _unlabelled("http://www.w3.org/2002/07/owl#Class")
    assert clean == 0, f"{clean} LegalEntity nodes carry no provenance — rule #1"
    assert dirty > 0, "owl:Class arm proves nothing if it is also 0"
    assert clean != dirty


# --- attribute resolution: the POPULATION, not just the decision -----------
#
# `_all_resolve` above tests the decision once the two sets are in hand. These
# arms test the set that gets handed to it, which is where the row actually
# broke: the probe drew its population from EVERY `ex:lei` node in the ledger,
# so each later wave that loaded LEI-bearing entities of its own -- Wave 17's
# AML parties, Wave 18's syndicate members, the registry companies -- enlarged
# corporate-family-tree's denominator with entities that are not family-tree
# traversal results and resolve from their own single-writer tables. The row
# read a permanent red at 279 of 434 while the family tree itself was clean.
#
# These arms need the live estate, following the precedent of the dual-typed
# and provenance arms below.


def test_family_population_excludes_other_products_entities():
    """THE FALSIFIER.

    Reverting the population to a plain `?s ex:lei ?l` over the whole ledger
    passes every other arm in this section and fails only this one. The
    positive control is the first assertion: the AML parties really are in the
    ledger carrying `ex:lei`, so the second assertion is discriminating an
    absence rather than reporting an empty query.
    """
    everything = sc.all_graph_leis()
    family = sc.family_tree_leis()

    assert any(l.startswith("SYN-AML-") for l in everything), (
        "positive control failed: no SYN-AML LEI in the ledger at all, so "
        "the exclusion below would pass vacuously")
    assert not any(l.startswith("SYN-AML-") for l in family), (
        "AML parties are in corporate-family-tree's population; they are "
        "another product's entities and resolve from ccf_v2.aml_party")
    assert family, "family population is empty -- the probe cannot mean anything"


def test_the_family_population_is_smaller_than_the_ledger():
    """The narrowing has to actually narrow, or the arm above proves nothing.

    Stated as a strict inequality on purpose: if a future wave loads its
    entities ONTO family-tree edges the two sets converge, and that is a
    change worth being told about rather than absorbing silently.
    """
    assert len(sc.family_tree_leis()) < len(sc.all_graph_leis())


def test_every_family_tree_entity_resolves_on_the_live_estate():
    """The row's actual claim, measured against the stores.

    Distinct from the arm above: that one says the population is right, this
    one says the data behind it is. Both can fail independently.
    """
    assert sc.unresolved_graph_leis() == 1


# --- "entities carrying a real LEI": the adjective is the whole check ------
#
# conditions.py floors this product at 50 entities carrying a REAL LEI. The
# check measured `COUNT(?s) WHERE ?s ex:lei ?l` over the ledger, which counts
# every LEI-bearing node whether its identifier is a real GLEIF LEI or one of
# this estate's own `SYN-` synthetics -- the exact confusion the SYN- prefix
# was introduced on 2026-08-23 to make impossible. Measured 2026-08-28 it
# reported 449 where the real-LEI population is 233.
#
# It passes either way at a floor of 50, which is what makes it worth fixing
# now: nothing will ever reveal it, and the number is load-bearing the moment
# anyone reads it as evidence of public-anchor coverage.

REAL_LEI = "5493001L3UGXFYA41M70"
OTHER_REAL_LEI = "213800K7ROBLZGACZV98"


def test_a_real_gleif_lei_counts():
    assert cond.count_real_leis([REAL_LEI]) == 1


def test_a_synthetic_identifier_does_not_count_as_real():
    """THE FALSIFIER.

    The estate's synthetic identifiers are `SYN-` with hyphens precisely so
    they can never be mistaken for the 20-character GLEIF form. 201 of them
    were being counted here.
    """
    assert cond.count_real_leis([REAL_LEI, "SYN-AML-0176", "SYN-ABS-0001"]) == 1


def test_the_same_lei_twice_counts_as_one_entity():
    """The check says ENTITIES. The SPARQL counted bindings, and the live
    ledger returns 449 bindings for 434 distinct values -- some nodes carry
    more than one `ex:lei`. A duplicate is not a second entity."""
    assert cond.count_real_leis([REAL_LEI, REAL_LEI, OTHER_REAL_LEI]) == 2


def test_a_malformed_identifier_is_not_a_real_lei():
    """Wrong length, lowercase, and empty are all rejected: a real LEI is 20
    uppercase alphanumerics. Without this arm the function could pass the
    others by merely excluding the literal prefix `SYN-`."""
    assert cond.count_real_leis(
        ["5493001L3UGXFYA41M7", "5493001L3UGXFYA41M700",
         "5493001l3ugxfya41m70", "", "   "]) == 0


def test_the_live_ledger_separates_real_from_synthetic():
    """Both halves present on the live estate, so neither arm is vacuous."""
    leis = sc.all_graph_leis()
    real = cond.count_real_leis(leis)
    assert real > 0, "positive control: no real LEI in the ledger at all"
    assert real < len(leis), (
        "no synthetic identifiers in the ledger, so the exclusion above "
        "cannot be shown to discriminate on live data")
