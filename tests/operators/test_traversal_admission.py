"""Node-class admission on the traversal walk — criterion 8, ledger row `24.5-L-05`.

`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201 (semantics version 1.1.0) says a
hop lands only on an entity whose ``entity_class`` is a member of
``admitted_entity_classes``, that walk starts (`GQ-11` at
docs/GRAPH_QUERY_SEMANTICS.md:221) are never filtered by admission, and that
``None`` admits every class — the 1.0.x behavior. This module proves each
sentence in process, network-free, on ONE two-class view, so the exclusion
and its control are read off the same state:

* an unadmitted neighbor is EXCLUDED, and so is everything behind it — the
  path to it ran through the excluded node (`GQ-13`);
* the all-admitted control on the same view reaches every neighbor, and the
  ``None`` sentinel reaches the same set (additive over breaking, D-10);
* ``src/ccf/graph/fallback.py::_walk`` — the differential oracle every
  pushed answer is held byte-identical to — agrees with
  ``src/ccf/operators/categories.py::TraversalNeighborhood.apply`` in every
  configuration;
* a start of an unadmitted class stays in the answer and still expands.

**The sabotage control.** ``src/ccf/operators/categories.py`` is copied to a
scratch module with the admission predicate removed and imported under a
scratch name; the exclusion assertion must FAIL on the copy, naming
``admitted_entity_classes``. The real tree is never edited, and the last test
asserts exactly that through ``git`` rather than trusting it — the
``tests/products/test_refusal_envelope.py::test_no_control_edits_the_real_source_tree``
voice.

Fixture discipline inherited from ``tests/properties/strategies.py``: the
three classes and the edge type are read from the ontology fixture and named
here by their ROLE in the view — no entity class and no relationship type is
written in this file (CLAUDE.md §6.4).
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
from types import ModuleType

import pytest

from ccf.graph.fallback import _walk
from ccf.graph.protocols import EntityRecord, GraphView, RelationshipRecord
from ccf.operators.categories import TraversalNeighborhood
from ccf.operators.params import TraversalNeighborhoodParameters

from tests.properties.strategies import (
    BOUNDARY,
    ENTITY_CLASSES,
    ENTITY_POOL,
    GENERATION,
    INSTANTS,
    RELATIONSHIP_RULES,
    TENANT,
    _entity_record,
    _relationship_record,
    _view,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CATEGORIES_SOURCE = REPO_ROOT / "src" / "ccf" / "operators" / "categories.py"

#: The three roles, in ontology vocabulary. The seed class starts the walk;
#: the admitted class is where a hop may land; the excluded class is the
#: boundary the walk must stop at.
SEED_CLASS, ADMITTED_CLASS, EXCLUDED_CLASS = ENTITY_CLASSES[:3]
#: One typed edge from the ontology. The operator walks EDGES by type and
#: reads the reached node's class only through admission, so one type is
#: enough to build every shape this module needs.
EDGE_TYPE: str = RELATIONSHIP_RULES[0][0]

#: The four nodes: S (seed) - A (admitted) ; S - B (excluded) - C (admitted).
S_URI = ENTITY_POOL[SEED_CLASS][0]
A_URI = ENTITY_POOL[ADMITTED_CLASS][0]
B_URI = ENTITY_POOL[EXCLUDED_CLASS][0]
C_URI = ENTITY_POOL[ADMITTED_CLASS][1]

EARLY = INSTANTS[0]
BUNDLE: str = GENERATION["permitted_policy_bundle_version"]
CLASSIFICATION: str = GENERATION["classifications"][0]
SYSTEM: str = GENERATION["source_systems"][0]

#: The exact predicate the sabotage removes. Asserted PRESENT in the real
#: source before the copy is mutated, so the control cannot pass vacuously
#: against a file that never carried it.
ADMISSION_PREDICATE = (
    "and (admitted is None or class_of.get(neighbour) in admitted)"
)


def _entity(uri: str, entity_class: str) -> EntityRecord:
    return _entity_record(
        entity_uri=uri,
        entity_class=entity_class,
        classification=CLASSIFICATION,
        policy_bundle_version=BUNDLE,
        observed_at=EARLY,
        valid_from=EARLY,
        valid_to=None,
        superseded_at=None,
        system_id=SYSTEM,
    )


def _edge(subject_uri: str, object_uri: str) -> RelationshipRecord:
    return _relationship_record(
        relationship_type=EDGE_TYPE,
        subject_uri=subject_uri,
        object_uri=object_uri,
        policy_bundle_version=BUNDLE,
        observed_at=EARLY,
        valid_from=EARLY,
        valid_to=None,
        superseded_at=None,
        system_id=SYSTEM,
    )


def two_class_view() -> GraphView:
    """S (seed) one hop from A (admitted) and B (excluded); C (admitted) one hop beyond B."""
    entities = (
        _entity(S_URI, SEED_CLASS),
        _entity(A_URI, ADMITTED_CLASS),
        _entity(B_URI, EXCLUDED_CLASS),
        _entity(C_URI, ADMITTED_CLASS),
    )
    relationships = (
        _edge(S_URI, A_URI),
        _edge(S_URI, B_URI),
        _edge(B_URI, C_URI),
    )
    return _view(entities, relationships)


VIEW = two_class_view()


def traversal(
    *,
    seed_classes: frozenset[str] = frozenset({SEED_CLASS}),
    admitted: frozenset[str] | None,
    depth: int = 2,
    operator_class: type = TraversalNeighborhood,
) -> TraversalNeighborhood:
    """One traversal operator over the view, admission as given."""
    operator: TraversalNeighborhood = operator_class(
        parameters=TraversalNeighborhoodParameters(
            seed_entity_classes=seed_classes,
            relationship_types=frozenset({EDGE_TYPE}),
            depth_limit=depth,
            admitted_entity_classes=admitted,
        )
    )
    return operator


def reached_by(operator: TraversalNeighborhood, view: GraphView = VIEW) -> set[str]:
    output = operator.apply(
        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
    )
    return {record.claim.entity_uri for record in output.view.entities}


def reached_by_fallback(operator: TraversalNeighborhood, view: GraphView = VIEW) -> set[str]:
    """The oracle's answer to the operator's own mirrored ``TraversalSpec``."""
    fragment = operator.read_intent()
    assert fragment.traverse is not None
    entities, _edges = _walk(
        view.entities, view.relationships, traverse=fragment.traverse, seeds=None
    )
    return {record.claim.entity_uri for record in entities}


# --- the exclusion and its controls ------------------------------------------


def test_the_view_has_the_shape_the_module_claims() -> None:
    """Three distinct classes, four nodes, the S-A / S-B-C chain — asserted, not assumed."""
    assert len({SEED_CLASS, ADMITTED_CLASS, EXCLUDED_CLASS}) == 3
    assert len({S_URI, A_URI, B_URI, C_URI}) == 4
    by_uri = {r.claim.entity_uri: r.claim.entity_class for r in VIEW.entities}
    assert by_uri == {
        S_URI: SEED_CLASS,
        A_URI: ADMITTED_CLASS,
        B_URI: EXCLUDED_CLASS,
        C_URI: ADMITTED_CLASS,
    }
    assert {(e.claim.subject_uri, e.claim.object_uri) for e in VIEW.relationships} == {
        (S_URI, A_URI),
        (S_URI, B_URI),
        (B_URI, C_URI),
    }


def test_a_neighbor_of_an_unadmitted_class_is_excluded() -> None:
    """`GQ-10` (1.1.0): B is one hop from S and of an unadmitted class — excluded.

    C is of an admitted class and two hops from S, but its only path runs
    through B: a path through an unadmitted node does not exist (`GQ-13`),
    so C is excluded too. A, admitted and one hop away, is reached.
    """
    reached = reached_by(traversal(admitted=frozenset({ADMITTED_CLASS})))
    assert reached == {S_URI, A_URI}, (
        "admitted_entity_classes did not exclude the unadmitted neighbor:"
        f" reached {sorted(reached)}"
    )
    assert B_URI not in reached
    assert C_URI not in reached


def test_the_all_admitted_control_reaches_every_neighbor() -> None:
    """The same view, every class admitted: S, A, B and C are all reached.

    And the ``None`` sentinel reaches the identical set — the 1.0.x question,
    so an artifact written before the field existed asks what it always asked.
    """
    every_class = frozenset({SEED_CLASS, ADMITTED_CLASS, EXCLUDED_CLASS})
    all_admitted = reached_by(traversal(admitted=every_class))
    assert all_admitted == {S_URI, A_URI, B_URI, C_URI}
    assert reached_by(traversal(admitted=None)) == all_admitted


def test_the_empty_set_admits_no_hop_and_answers_the_starts() -> None:
    """``frozenset()`` and ``None`` are different facts: no hop is admitted."""
    assert reached_by(traversal(admitted=frozenset())) == {S_URI}


def test_starts_are_never_filtered_by_admission() -> None:
    """`GQ-11` selects starts; admission filters hops. A start of an unadmitted class stays.

    Seeding from the EXCLUDED class with only the ADMITTED class admissible:
    B is a start, so it is in the answer and still expands — C (admitted) is
    reached through it — while S (the seed class, not admitted here) is not.
    """
    reached = reached_by(
        traversal(
            seed_classes=frozenset({EXCLUDED_CLASS}),
            admitted=frozenset({ADMITTED_CLASS}),
        )
    )
    assert B_URI in reached, "a walk start was filtered by admission"
    assert reached == {B_URI, C_URI}


@pytest.mark.parametrize(
    ("seed_classes", "admitted"),
    [
        (frozenset({SEED_CLASS}), frozenset({ADMITTED_CLASS})),
        (frozenset({SEED_CLASS}), frozenset({SEED_CLASS, ADMITTED_CLASS, EXCLUDED_CLASS})),
        (frozenset({SEED_CLASS}), None),
        (frozenset({SEED_CLASS}), frozenset()),
        (frozenset({EXCLUDED_CLASS}), frozenset({ADMITTED_CLASS})),
    ],
    ids=["one-class", "all-admitted", "none-sentinel", "empty-set", "start-unfiltered"],
)
def test_the_fallback_walk_agrees_with_the_operator(
    seed_classes: frozenset[str], admitted: frozenset[str] | None
) -> None:
    """The oracle answers the mirrored spec with the operator's own entity set (D-04)."""
    operator = traversal(seed_classes=seed_classes, admitted=admitted)
    fragment = operator.read_intent()
    assert fragment.traverse is not None
    assert fragment.traverse.admitted_entity_classes == admitted
    assert reached_by_fallback(operator) == reached_by(operator)


def test_read_intent_mirrors_admission_field_for_field() -> None:
    """The pushed spec carries exactly the operator's admission — nothing translated."""
    admitted = frozenset({ADMITTED_CLASS})
    fragment = traversal(admitted=admitted).read_intent()
    assert fragment.traverse is not None
    # Equality, not identity: the frozen contract copies the set on validation.
    assert fragment.traverse.admitted_entity_classes == admitted
    sentinel = traversal(admitted=None).read_intent().traverse
    assert sentinel is not None
    assert sentinel.admitted_entity_classes is None


# --- the sabotage control -----------------------------------------------------


def _import_sabotaged_categories(tmp_path: pathlib.Path) -> ModuleType:
    """A copy of ``categories.py`` with the admission predicate removed, under a scratch name."""
    source = CATEGORIES_SOURCE.read_text(encoding="utf-8")
    assert source.count(ADMISSION_PREDICATE) == 1, (
        "the admission predicate is not where this control expects it;"
        " re-read src/ccf/operators/categories.py::TraversalNeighborhood.apply"
    )
    sabotaged = source.replace(ADMISSION_PREDICATE, "")
    assert ADMISSION_PREDICATE not in sabotaged
    scratch = tmp_path / "sabotaged_categories_no_admission.py"
    scratch.write_text(sabotaged, encoding="utf-8")
    name = "tests_operators_sabotaged_categories_no_admission"
    spec = importlib.util.spec_from_file_location(name, scratch)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def test_control_1_the_exclusion_fails_on_a_copy_without_the_predicate(
    tmp_path: pathlib.Path,
) -> None:
    """Remove the admission predicate from a COPY; the exclusion assertion goes RED.

    The copy's operator, asked the one-class question, reaches B and C as if
    ``admitted_entity_classes`` were absent — which is exactly what the real
    test above would report, naming the field, if the predicate were lost.
    """
    sabotaged = _import_sabotaged_categories(tmp_path)
    operator = traversal(
        admitted=frozenset({ADMITTED_CLASS}),
        operator_class=sabotaged.TraversalNeighborhood,
    )
    reached = reached_by(operator)
    with pytest.raises(AssertionError, match="admitted_entity_classes"):
        assert reached == {S_URI, A_URI}, (
            "admitted_entity_classes did not exclude the unadmitted neighbor:"
            f" reached {sorted(reached)}"
        )
    # The positive statement of the same fact: the sabotaged walk crossed
    # the class boundary, so the control is discriminating, not merely red.
    assert reached == {S_URI, A_URI, B_URI, C_URI}
    # And the real operator on the same view still excludes — the two
    # answers differ on exactly the nodes admission governs.
    assert reached - reached_by(traversal(admitted=frozenset({ADMITTED_CLASS}))) == {
        B_URI,
        C_URI,
    }


def test_no_control_edits_the_real_source_tree() -> None:
    """The control copies; it never edits and reverts. Asserted through ``git``.

    An edit-and-revert control that crashed halfway would leave the tree
    modified and this suite green, so the real file's cleanliness is read
    from ``git status --short`` (staged or unstaged) and, second leg, from
    the unstaged diff — scoped to the one file the control copies, so an
    unrelated edit elsewhere under ``src/`` cannot make this go red.
    """
    relative = CATEGORIES_SOURCE.relative_to(REPO_ROOT).as_posix()
    status = subprocess.run(
        ["git", "status", "--short", "--", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert status.strip() == "", f"a control touched the real tree: {status!r}"
    diff = subprocess.run(
        ["git", "diff", "--", relative],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert diff == ""
    assert ADMISSION_PREDICATE in CATEGORIES_SOURCE.read_text(encoding="utf-8")
