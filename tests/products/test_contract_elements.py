"""The §6.3 contract, enumerated as an executable assertion, not as prose.

Three of the nine committed specification elements went missing from the
shipped types while every gate in this repo stayed green, because every gate
here tests what the fabric *does* and none tested what the delivered product
*carries*. A module docstring cannot fail when someone removes a field; this
module can. That is the whole reason it exists — the same reason
``tests/peering/test_trust_policy.py`` enumerates fields rather than trusting
the sentence that describes them.

**Why the union.** The enumeration runs over the union of
``ContextProductContract.model_fields`` and
``RegisteredProductClass.model_fields`` rather than over the instance type
alone. ``assembly_mode`` is already borne by the registered class and not by
the instance, and the phase's open question ``Q8`` has not ruled whether
``freshness_sla`` lands on the instance or on the class. The union makes this
suite correct under either ruling, because it asserts that an element is
**borne**, not where it is borne.

**Why a pending element asserts an absence before it skips.** A ratchet that
only skips has one working direction, and the direction it fails to hold is
the one this phase is about to exercise: land ``freshness_sla`` on the
contract, leave its pending marker on, and a skip-only suite stays green while
the anti-recurrence requirement is silently unmet. So the pending branch
asserts the field is absent from the union *first*; the skip is unreachable
once the element has landed.

**Deferrals are emitted, not hidden.** Three elements and one false docstring
claim are carried as pytest skips naming the reason, the plan that closes them
and the requirement — the shipped idiom of
``tests/invariants/test_replay_by_construction.py``. This tree carries no
expected-failure marker anywhere and this module does not introduce the first
one; a deferral that announces itself in the run output is a deferral someone
reads.

**Chosen to be jointly falsifying, not individually reassuring** — the
standard ``tests/properties/test_lineage_union.py`` holds this repo's property
suites to. Each check below names the weaker implementation it, and only it,
rules out:

* the **presence** branch of
  :func:`test_every_element_is_borne_by_a_named_field` falsifies "an element
  the code silently stopped carrying" — a deleted or renamed field;
* the **absence** assertion on the pending branch falsifies "an element that
  landed while its marker stayed on", which a skip-only ratchet cannot see and
  which is the exact direction this phase is about to exercise;
* :func:`test_the_pending_set_is_exactly_the_three_this_phase_closes`
  falsifies "a *fourth* element quietly declared pending" — a contributor
  answering a red presence branch by adding a deferral instead of a field;
* :func:`test_no_element_is_borne_by_a_field_two_elements_share` falsifies
  "nine names all pointing at one field that happens to exist" — without it,
  every element could be keyed to ``schema_name`` and the suite would be
  green;
* :func:`test_the_whitepaper_anchor_of_every_element_resolves` falsifies "an
  enumeration that agrees with itself" — a declaration whose nine names have
  drifted from the specification they claim to enumerate. This is the
  ``T-15.5-04`` repudiation mitigation, and it follows the anchored-citation
  posture ``make lint``'s ``GQ-NN`` guard already applies to
  ``docs/GRAPH_QUERY_SEMANTICS.md``;
* :func:`test_the_present_set_and_the_pending_set_partition_the_nine`
  falsifies "an element that is neither asserted nor deferred" — a
  ``pending`` reason on an element whose field is also declared present, or an
  element dropped from both halves and therefore checked by nothing.

**Where the union mechanism is coarse, and this says so rather than hiding
it.** ``contract.py``'s own field-to-element table routes Policy Binding
through ``lineage.policy_bundle_versions`` — a *nested* field, which a
top-level ``model_fields`` union cannot reach. This enumeration therefore keys
Policy Binding to ``accepted_policy_binding_modes``, the class-level top-level
field that carries the element's contract surface. Keying it to ``lineage``
instead would have collapsed two distinct elements onto one field, which the
injectivity guard rejects for good reason. The residual is recorded, not
papered over: the union proves the element has a bearing field, it does not
prove the nested policy-bundle route still exists.

Requirement CPS-02.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pytest

from ccf.products import contract as contract_module
from ccf.products.contract import (
    ContextProductContract,
    RegisteredProductClass,
)

#: Repo root, from this module's own location — never a configured path, so a
#: move of the tests tree cannot leave the anchor guard reading a stale copy.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: The plan that lands the three absent elements and makes the ``contract.py``
#: module docstring true.
CLOSING_PLAN = "15.5-07"

#: The requirement every deferral in this module answers to.
REQUIREMENT = "CPS-02"


class Element(NamedTuple):
    """One §6.3 specification element and the shipped field that bears it.

    Attributes:
        name: The element's name, exactly as the §6.3 table spells it.
        whitepaper_anchor: ``path:line`` or ``path:start-end`` of the passage
            that specifies the element, so the declaration can be resolved
            against the specification it claims to enumerate rather than
            trusted.
        borne_by: Dotted name of the shipped type carrying the field.
            Recorded for the reader; the assertion itself runs over the union
            of both types, because *borne* is the claim and *where* is Q8's to
            rule.
        field_name: The top-level field name on that type.
        pending: ``None`` when the element is borne today. Otherwise the
            deferral reason, naming the closing plan and the requirement.
        absence_markers: Substrings that must not appear in any field name
            while the element is pending. Present elements declare none. This
            catches an element that lands under a name other than the one
            predicted here — a pending ``field_name`` is a prediction, and a
            ratchet keyed only to a prediction is one a rename walks past.
    """

    name: str
    whitepaper_anchor: str
    borne_by: str
    field_name: str
    pending: str | None = None
    absence_markers: tuple[str, ...] = ()


def _deferral(element_name: str) -> str:
    return (
        f"{element_name} is a 6.3 element with no field on either shipped "
        f"type yet; plan {CLOSING_PLAN} lands it ({REQUIREMENT})"
    )


_INSTANCE = "ccf.products.contract.ContextProductContract"
_CLASS = "ccf.products.contract.RegisteredProductClass"

#: The nine elements of the Context Product Contract.
#:
#: Nine, not eight. ``D-IMPL-30`` resolved the count as reading (a): the
#: contract has nine elements including Assembly Mode, and every "eight"
#: reference in this tree — CLAUDE.md 5's included — is editorial drift the
#: ruling authorizes treating as such.
#:
#: Keyed to the whitepaper's own nine-row table (the §6.3 element table) and
#: anchored per element at the paragraph that unpacks it.
NINE_ELEMENTS: tuple[Element, ...] = (
    Element(
        name="Schema",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1451",
        borne_by=_INSTANCE,
        field_name="schema_name",
    ),
    Element(
        name="Semantic Versioning",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1461",
        borne_by=_INSTANCE,
        field_name="schema_version",
    ),
    Element(
        name="TTL",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1455",
        borne_by=_INSTANCE,
        field_name="expires_at",
    ),
    Element(
        name="Policy Binding",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1457",
        borne_by=_CLASS,
        field_name="accepted_policy_binding_modes",
    ),
    Element(
        name="Lineage",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1459",
        borne_by=_INSTANCE,
        field_name="lineage",
    ),
    Element(
        name="Assembly Mode",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1467",
        borne_by=_CLASS,
        field_name="assembly_mode",
    ),
    Element(
        name="Freshness SLA",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1453",
        borne_by=_CLASS,
        field_name="freshness_sla",
        pending=_deferral("Freshness SLA"),
        absence_markers=("freshness",),
    ),
    Element(
        name="Discovery",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1463",
        borne_by=_CLASS,
        field_name="discovery",
        pending=_deferral("Discovery"),
        absence_markers=("discovery",),
    ),
    Element(
        name="Addressability",
        whitepaper_anchor="docs/CCF_Whitepaper_1-2.md:1465",
        borne_by=_CLASS,
        field_name="addressability",
        pending=_deferral("Addressability"),
        absence_markers=("address",),
    ),
)

#: The elements this phase closes, named rather than counted. A *fourth*
#: element quietly losing its field fails
#: :func:`test_the_pending_set_is_exactly_the_three_this_phase_closes`, and an
#: element landing without its marker removed fails the absence assertion in
#: :func:`test_every_element_is_borne_by_a_named_field`.
PENDING_ELEMENT_NAMES = frozenset(
    {"Freshness SLA", "Discovery", "Addressability"}
)


def borne_field_names() -> frozenset[str]:
    """Every field name the two shipped contract types bear between them.

    The union, per this module's docstring: an element is asserted to be
    *borne*, not to be borne in a particular place, because Q8 has not ruled
    where ``freshness_sla`` lands.
    """
    return frozenset(ContextProductContract.model_fields) | frozenset(
        RegisteredProductClass.model_fields
    )


def test_the_contract_has_nine_elements() -> None:
    """D-IMPL-30, reading (a): nine elements, Assembly Mode included.

    The "eight" references in this tree — CLAUDE.md 5's among them — are
    editorial drift, and the ruling doubles as authorization to treat them as
    such rather than as an override of the whitepaper's own table. Asserted
    here so a later reader who counts eight argues with a failing test rather
    than with a sentence.
    """
    assert len(NINE_ELEMENTS) == 9
    assert len({element.name for element in NINE_ELEMENTS}) == 9


@pytest.mark.parametrize(
    "element", NINE_ELEMENTS, ids=lambda element: element.name
)
def test_every_element_is_borne_by_a_named_field(element: Element) -> None:
    """An element unrepresented in code fails here instead of lying in prose.

    A present element asserts its field is in the union — a renamed or deleted
    field turns this red. A pending element asserts its field is **absent**
    from the union and only then emits its deferral, so an element that has
    landed can never reach the skip.
    """
    borne = borne_field_names()
    if element.pending is None:
        assert element.field_name in borne, (
            f"6.3 element {element.name!r} is declared present, borne by "
            f"{element.borne_by}.{element.field_name}, and no field of that "
            f"name exists on either shipped contract type. Either the field "
            f"was renamed or removed, or this declaration is wrong; the "
            f"element is committed and cannot simply be dropped (D-IMPL-30, "
            f"{REQUIREMENT})."
        )
        return

    assert element.field_name not in borne, (
        f"6.3 element {element.name!r} has landed — {element.field_name!r} "
        f"now exists on a shipped contract type — and its pending marker was "
        f"not removed from NINE_ELEMENTS. Delete the element's pending "
        f"reason and its absence markers, and drop it from "
        f"PENDING_ELEMENT_NAMES ({REQUIREMENT})."
    )
    landed_under_another_name = sorted(
        name
        for name in borne
        for marker in element.absence_markers
        if marker in name.lower()
    )
    assert landed_under_another_name == [], (
        f"6.3 element {element.name!r} appears to have landed under a name "
        f"this declaration did not predict: {landed_under_another_name}. "
        f"Correct the element's field name and remove its pending marker "
        f"({REQUIREMENT})."
    )
    pytest.skip(element.pending)


def test_the_pending_set_is_exactly_the_three_this_phase_closes() -> None:
    """The ratchet's second direction: the deferral list cannot go stale.

    Between this and the absence assertion in
    :func:`test_every_element_is_borne_by_a_named_field` the declaration is
    impossible to leave stale. Landing a field without removing its marker
    fails there; removing a marker without landing the field fails there too,
    on the presence branch; and a *fourth* element quietly losing its field
    fails here, because it would have to be declared pending to pass the
    presence branch.
    """
    declared_pending = {
        element.name
        for element in NINE_ELEMENTS
        if element.pending is not None
    }
    assert declared_pending == set(PENDING_ELEMENT_NAMES)
    for element in NINE_ELEMENTS:
        if element.pending is None:
            continue
        assert CLOSING_PLAN in element.pending, element.name
        assert REQUIREMENT in element.pending, element.name


# --- the guards that make the set jointly falsifying -----------------------
#
# Task 1's checks are individually satisfiable by a weaker declaration than
# criterion 2 asks for. These three close that, each against a named weaker
# implementation (see the module docstring).


def test_no_element_is_borne_by_a_field_two_elements_share() -> None:
    """The element-to-field mapping is injective.

    Without this, nine elements could all name ``schema_name`` — a field that
    exists — and every presence assertion would pass while eight elements were
    unrepresented. Injectivity is what makes "borne by a named field" mean one
    field per element rather than one field for all of them.
    """
    fields = [element.field_name for element in NINE_ELEMENTS]
    shared = sorted({name for name in fields if fields.count(name) > 1})
    assert shared == [], (
        f"6.3 elements share a bearing field: {shared}. Each element must be "
        f"borne by its own field; a shared field means at least one element "
        f"is unrepresented while the presence assertion still passes "
        f"({REQUIREMENT})."
    )


def _anchor_lines(anchor: str) -> tuple[Path, int, int]:
    """Split ``path:start`` or ``path:start-end`` into a path and a range."""
    path_part, _, line_part = anchor.rpartition(":")
    start_part, _, end_part = line_part.partition("-")
    start = int(start_part)
    return REPO_ROOT / path_part, start, int(end_part or start_part)


@pytest.mark.parametrize(
    "element", NINE_ELEMENTS, ids=lambda element: element.name
)
def test_the_whitepaper_anchor_of_every_element_resolves(
    element: Element,
) -> None:
    """Each element resolves against the specification it claims to enumerate.

    ``T-15.5-04``: a declaration that authors its own expectations is the suite
    agreeing with itself. The anchor must name a line range that exists in the
    whitepaper and whose text carries the element's name, so the nine cannot
    drift away from the nine the specification commits to.
    """
    source, start, end = _anchor_lines(element.whitepaper_anchor)
    assert source.is_file(), (
        f"6.3 element {element.name!r} anchors at "
        f"{element.whitepaper_anchor}, and that file does not exist "
        f"({REQUIREMENT})."
    )
    lines = source.read_text(encoding="utf-8").splitlines()
    assert 1 <= start <= end <= len(lines), (
        f"6.3 element {element.name!r} anchors at "
        f"{element.whitepaper_anchor}, and that range is outside the "
        f"{len(lines)} lines the file has ({REQUIREMENT})."
    )
    cited = "\n".join(lines[start - 1 : end]).lower()
    assert element.name.lower() in cited, (
        f"6.3 element {element.name!r} anchors at "
        f"{element.whitepaper_anchor}, and those lines do not name it. "
        f"Either the whitepaper moved and the anchor needs re-pointing, or "
        f"this element is not the one the anchor specifies ({REQUIREMENT})."
    )


def test_the_present_set_and_the_pending_set_partition_the_nine() -> None:
    """Every element is exactly one of present or pending — never neither.

    Task 1's parametrized test branches on ``pending``, so an element in
    neither half is unreachable by construction there. Stated as its own check
    because the property being relied on is a *partition*, and a property
    relied on but never asserted is how the last three elements went missing.
    """
    present = {
        element.name for element in NINE_ELEMENTS if element.pending is None
    }
    pending = {
        element.name
        for element in NINE_ELEMENTS
        if element.pending is not None
    }
    assert present & pending == set()
    assert present | pending == {element.name for element in NINE_ELEMENTS}
    assert len(present) + len(pending) == len(NINE_ELEMENTS) == 9
    assert pending == set(PENDING_ELEMENT_NAMES)


def _paragraphs_claiming_class_level_residence(
    docstring: str,
) -> list[str]:
    return [
        paragraph
        for paragraph in docstring.split("\n\n")
        if "RegisteredProductClass" in paragraph
    ]


def test_the_module_docstring_names_only_fields_that_exist() -> None:
    """The ``contract.py`` docstring is a thing the suite checks, not reads.

    ``contract.py`` states that four 6.3 elements "live" on
    :class:`RegisteredProductClass`. Only one of them does. This test reads
    the docstring, resolves each element it claims resides there to the field
    that claim implies, and asserts the field exists. It is **expected to skip
    today**: the three unlanded claims are the same three deferrals the
    enumeration carries, and plan ``15.5-07`` closes them by making the
    sentence true.
    """
    docstring = contract_module.__doc__ or ""
    claiming = _paragraphs_claiming_class_level_residence(docstring)
    assert claiming, (
        "no paragraph of the ccf.products.contract module docstring mentions "
        "RegisteredProductClass; this test can no longer find the claim it "
        "audits and must be re-pointed rather than left passing vacuously"
    )
    claimed = {
        element
        for element in NINE_ELEMENTS
        for paragraph in claiming
        if element.name.lower() in paragraph.lower()
    }
    assert claimed, (
        "the ccf.products.contract module docstring names no 6.3 element as "
        "living on RegisteredProductClass; if the claim was rewritten, "
        "re-point this test at the new wording"
    )
    absent = {
        element.name
        for element in claimed
        if element.field_name not in RegisteredProductClass.model_fields
    }
    if not absent:
        return
    assert absent == set(PENDING_ELEMENT_NAMES), (
        f"the ccf.products.contract module docstring claims {sorted(absent)} "
        f"live on RegisteredProductClass, and they do not. Only the three "
        f"known deferrals may be false here; anything else is a new false "
        f"claim ({REQUIREMENT})."
    )
    pytest.skip(
        f"the ccf.products.contract module docstring claims {sorted(absent)} "
        f"live on RegisteredProductClass, where they do not; plan "
        f"{CLOSING_PLAN} lands the fields and makes the sentence true "
        f"({REQUIREMENT})"
    )
