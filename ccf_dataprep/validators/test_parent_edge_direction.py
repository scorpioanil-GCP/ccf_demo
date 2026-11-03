#!/usr/bin/env python3
"""FIBO's parent and ownership predicates do not run the same way.

`load_fluree_wave3.py` emitted every GLEIF edge from one orientation --
subject = parent, object = child -- taken from a single `(p, c)` pair:

    p, c = e["parent_lei"], e["child_lei"]
    predicate = (P_GLOBAL_ULTIMATE if e["edge_type"] == "hasUltimateParent"
                 else P_OWNS)
    triples += edge_triples(locals_by_lei[p], locals_by_lei[c], ...)

That is correct for `owns` and inverted for `hasGlobalUltimateParent`:

    fibo-fnd-...:owns                      parent -> child
    fibo-be-oac-cctl:hasGlobalUltimateParent   child -> PARENT

Confirmed from FIBO's own published instance data in prod.fibo-quickstart.ttl,
where the SUBJECT is the subsidiary:

    Business Entity Data (BED) B.V. NL
        fibo-be-oac-cctl:hasGlobalUltimateParent  DepositoryTrustAndClearingCorporation

and from `rdfs:range GlobalUltimateParent` -- the object is the parent.

Measured against the 140 GLEIF `IS_ULTIMATELY_CONSOLIDATED_BY` records in
`ccf_v2.corporate_ownership_record`, read as (child, parent):

    as stored : 0 of 140      reversed : 103 of 140

Zero-and-103 is not partial overlap; it is the direction. 139 edges were
affected. Nothing caught it for seven waves because every check that touches
these predicates is a bare COUNT, and a count cannot see an arrow.

    uv run --with pytest pytest validators/test_parent_edge_direction.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "load_fluree_wave3", REPO / "loaders" / "load_fluree_wave3.py")
w3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w3)

PARENT, CHILD = "BigCo", "LittleCo"


def _subject_object(predicate: str) -> tuple[str, str]:
    """(subject, object) of the single triple emitted for a parent->child fact.

    Call sites all pass (parent, child) in that order; what varies is which
    end becomes the subject, and that is the thing under test.
    """
    out = w3.edge_triples(PARENT, CHILD, predicate=predicate,
                          provenance="public")
    assert len(out) == 1, f"expected one triple, got {out}"
    parts = out[0].split()
    return parts[0], parts[2]


def test_owns_points_parent_to_child():
    subj, obj = _subject_object(w3.P_OWNS)
    assert PARENT in subj, f"owns subject should be the parent: {subj}"
    assert CHILD in obj


def test_global_ultimate_parent_points_child_to_parent():
    subj, obj = _subject_object(w3.P_GLOBAL_ULTIMATE)
    assert CHILD in subj, (
        f"hasGlobalUltimateParent subject must be the CHILD: {subj}")
    assert PARENT in obj, (
        f"hasGlobalUltimateParent object must be the PARENT: {obj}")


def test_domestic_ultimate_parent_points_child_to_parent():
    subj, obj = _subject_object(w3.P_DOMESTIC_ULTIMATE)
    assert CHILD in subj, (
        f"hasDomesticUltimateParent subject must be the CHILD: {subj}")
    assert PARENT in obj


def test_controls_points_parent_to_child():
    """Negative control for the flip.

    Without it, inverting EVERY predicate passes both parent tests above.
    `controls`, like `owns`, runs parent -> child, so a blanket flip fails
    here.
    """
    subj, obj = _subject_object(w3.P_CONTROLS)
    assert PARENT in subj, f"controls subject should be the parent: {subj}"
    assert CHILD in obj


# -- the remediation must converge, not oscillate --------------------------

_rspec = importlib.util.spec_from_file_location(
    "remediate_parent_direction", REPO / "loaders" /
    "remediate_parent_direction_wave15.py")
rem = importlib.util.module_from_spec(_rspec)
_rspec.loader.exec_module(rem)

# BigCo -> MidCo -> LittleCo, as GLEIF states it (child: parent)
PARENT_MAP = {"LittleCo": "MidCo", "MidCo": "BigCo"}


def _decide(subject: str, obj: str) -> str:
    """What the remediation would do with edge (subject, pred, obj)."""
    if rem.is_ancestor(PARENT_MAP, obj, subject):
        return "keep"
    if rem.is_ancestor(PARENT_MAP, subject, obj):
        return "flip"
    return "unresolved"


def test_inverted_edge_is_flipped():
    assert _decide("BigCo", "LittleCo") == "flip"


def test_correct_edge_is_left_alone():
    """The convergence property.

    The first version of this remediation selected "every edge whose reverse
    is not already asserted", which corrects an inverted ledger once and then
    inverts it again on the next run. This arm is what makes that impossible:
    a correctly-oriented edge must be a no-op.
    """
    assert _decide("LittleCo", "BigCo") == "keep"


def test_indirect_ancestry_still_resolves():
    """LittleCo's GLOBAL ultimate parent is BigCo, two hops up."""
    assert _decide("LittleCo", "BigCo") == "keep"
    assert _decide("BigCo", "LittleCo") == "flip"


def test_unrelated_pair_is_never_guessed():
    """An edge with no ancestry either way must be reported, not flipped.

    Guessing here would silently reverse edges GLEIF says nothing about.
    """
    assert _decide("LittleCo", "Stranger") == "unresolved"
    assert _decide("Stranger", "LittleCo") == "unresolved"


def test_ancestry_walk_terminates_on_a_cycle():
    cyclic = {"A": "B", "B": "A"}
    assert rem.is_ancestor(cyclic, "B", "A") is True
    assert rem.is_ancestor(cyclic, "Z", "A") is False
