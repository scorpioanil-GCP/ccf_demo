#!/usr/bin/env python3
"""The jurisdiction-entitlement gate must be able to FAIL.

`counterparty-reference-snapshot` §B binds the T1 policy as *"Entitlement
scope only -- JURISDICTION VISIBILITY per calling principal"*, and §D's
Validation gates line names **suppression silence** among six gates. Neither
is satisfied by a column whose values differ: the quantity that decides it is
whether the VISIBLE ENTITY SET differs, and a populated column sitting above
a Policy Operator that filters nothing is the "counted but not created"
failure in the one product every other product inherits its contract
machinery from.

So every arm here feeds the decision functions hand-built input whose right
answer is known before running it, and the arms that matter are the ones a
naive implementation passes everything else and fails only here:

  * `test_two_principals_with_different_scopes_but_identical_visibility` --
    scopes differ, visible sets do not, because no entity sits in the part of
    the scope that differs. A check reading the COLUMN says two; a check
    recomputing the SET says one. This is the whole point.
  * `test_a_principal_seeing_everything_is_not_suppression` -- an unrestricted
    principal makes the operator a no-op for that principal however many
    others are restricted.

    uv run --with pytest pytest validators/test_entitlement.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "entitlement", REPO / "validators" / "entitlement.py")
ent = importlib.util.module_from_spec(_spec)
sys.modules["entitlement"] = ent
_spec.loader.exec_module(ent)

#: (lei, legal_jurisdiction). Mixed country and ISO 3166-2 subdivision codes,
#: because the estate holds both -- US-DE alongside GB.
ENTITIES = [
    ("LEI_DE_A", "US-DE"), ("LEI_DE_B", "US-DE"), ("LEI_MD", "US-MD"),
    ("LEI_GB", "GB"), ("LEI_NL", "NL"), ("LEI_DEU", "DE"),
    ("LEI_CA", "CA"), ("LEI_CABC", "CA-BC"),
]


# --- scope matching: a country prefix covers its subdivisions --------------

def test_a_country_prefix_covers_its_subdivisions():
    assert ent.in_scope("US-DE", "US")


def test_a_country_prefix_covers_the_bare_country():
    assert ent.in_scope("CA", "CA")


def test_a_prefix_does_not_leak_across_countries():
    """`US` must not match `US-DE` by accident of string containment in one
    direction and `DE` the country in the other."""
    assert not ent.in_scope("DE", "US")
    assert not ent.in_scope("US-DE", "DE")


def test_a_subdivision_scope_does_not_widen_to_its_country():
    """Entitlement narrows; it never widens. `US-DE` must not admit `US-MD`."""
    assert not ent.in_scope("US-MD", "US-DE")


# --- visibility ------------------------------------------------------------

def test_visibility_is_the_union_of_the_scopes():
    assert ent.visible(ENTITIES, ["GB", "NL"]) == {"LEI_GB", "LEI_NL"}


def test_an_empty_scope_sees_nothing():
    assert ent.visible(ENTITIES, []) == set()


# --- the decisions the gate turns on ---------------------------------------

def test_three_genuinely_different_scopes_give_three_distinct_sets():
    sets = {"a": ent.visible(ENTITIES, ["US"]),
            "b": ent.visible(ENTITIES, ["GB"]),
            "c": ent.visible(ENTITIES, ["NL", "DE"])}
    assert ent.distinct_visible_sets(sets) == 3


def test_two_principals_with_different_scopes_but_identical_visibility():
    """THE FALSIFIER.

    `KR` and `JP` are both absent from this population, so two principals
    scoped to them differ in the COLUMN and see exactly the same thing --
    nothing. A gate that counted distinct scope values would report two
    differing principals here and be wrong. Only recomputing the set catches
    it, and this is precisely the shape a jurisdiction nobody loaded produces.
    """
    sets = {"a": ent.visible(ENTITIES, ["KR"]),
            "b": ent.visible(ENTITIES, ["JP"])}
    assert ent.distinct_visible_sets(sets) == 1


def test_an_entity_visible_to_one_and_not_another_is_detected():
    sets = {"a": ent.visible(ENTITIES, ["GB"]), "b": ent.visible(ENTITIES, ["NL"])}
    assert ent.asymmetric_pair(sets) == ("a", "b") or \
           ent.asymmetric_pair(sets) == ("b", "a")


def test_identical_visibility_has_no_asymmetric_pair():
    sets = {"a": ent.visible(ENTITIES, ["GB"]), "b": ent.visible(ENTITIES, ["GB"])}
    assert ent.asymmetric_pair(sets) is None


def test_a_principal_seeing_everything_is_not_suppression():
    """THE SECOND FALSIFIER.

    Distinctness alone is satisfiable while one principal is unrestricted, and
    for that principal the Policy Operator filters nothing -- the no-op the
    gate exists to prevent, surviving inside a passing check.
    """
    sets = {"all": ent.visible(ENTITIES, ["US", "GB", "NL", "DE", "CA"]),
            "gb": ent.visible(ENTITIES, ["GB"])}
    assert ent.distinct_visible_sets(sets) == 2
    assert not ent.every_principal_is_suppressed(sets, total=len(ENTITIES))


def test_every_principal_restricted_is_suppression():
    sets = {"a": ent.visible(ENTITIES, ["US"]), "b": ent.visible(ENTITIES, ["GB"])}
    assert ent.every_principal_is_suppressed(sets, total=len(ENTITIES))


def test_no_principals_at_all_is_not_a_pass():
    assert not ent.every_principal_is_suppressed({}, total=len(ENTITIES))
