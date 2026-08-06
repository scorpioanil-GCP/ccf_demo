"""The operator-set binder, watched to refuse an artifact edit and to admit agreement.

Design E2's element (3) — ``docs/DECISIONS.md`` D-IMPL-86 and its correction of
2026-08-05. ROADMAP criterion 4 asks that the divergence be reachable **by
editing an artifact**, not only by writing a bug, so every case here reaches
:func:`~ccf.deployment.binder.refuse_operator_set_divergence` through **authored
artifact documents parsed by** :func:`~ccf.controlplane.artifacts.load_artifact`.
Constructing the models directly would prove the comparison works on two objects
and say nothing about whether an author could ever make them disagree.

**The first two cases are a mandatory pair**, in the shape
``tests/products/test_gate_independence.py::test_perturbing_engine_resolved_is_refused_and_the_declared_set_is_not``
established: "a gate that always refuses passes the first, a gate that always
admits passes the second, and only the pair says the comparison is live." A
binder that always refused would pass case 2 and fail case 1; a binder that
always admitted would do the reverse. Neither half is redundant.

Every value below is fixture vocabulary — test-side names, never SDK values
(CINV-01).
"""

from __future__ import annotations

import difflib
from collections.abc import Mapping, Sequence
from datetime import datetime

import pytest

from ccf.controlplane.artifacts import (
    PRODUCT_CLASS,
    PROJECTION_REQUIREMENTS,
    ProductClassDeclaration,
    ProjectionRequirements,
    load_artifact,
)
from ccf.deployment.binder import refuse_operator_set_divergence
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan

# --- fixture vocabulary -------------------------------------------------------

PLAN_ID = "fixture.binder-plan"
TRAVERSAL = "traversal.typed-neighborhood"
POLICY = "policy.principal-subgraph"
TEMPORAL = "temporal.as-of"

#: What both documents declare when they agree. The two documents state them in
#: **different orders**, because order is not significant on either side — the
#: engine imposes the dependency order (INV-CH7-28) and neither author picks it.
AGREEING_CLAIM: tuple[str, ...] = (TRAVERSAL, POLICY)
AGREEING_REQUIREMENTS: tuple[str, ...] = (POLICY, TRAVERSAL)


# --- authored documents, as text ----------------------------------------------


def _product_class_text(operator_keys: Sequence[str]) -> str:
    """A ``ccf.product-class`` document with one operator key per line.

    One key per line on purpose: it is what makes "edit one key" a genuine
    single-line edit to an authored document rather than a restructuring of it.
    """
    body = "".join(f"- {key}\n" for key in operator_keys)
    return (
        "semver: 1.0.0\n"
        "schema_name: fixture.binder-product\n"
        "schema_version: 1.0.0\n"
        "ttl_anchor: from_decision\n"
        "assembly_mode: algorithmic\n"
        "max_ttl_key: fixture/binder/max-ttl\n"
        "required_operator_keys:\n"
    ) + body


def _requirements_text(operator_keys: Sequence[str], *, plan_id: str = PLAN_ID) -> str:
    """A ``ccf.projection-requirements`` document, same one-key-per-line shape."""
    body = "".join(f"- {key}\n" for key in operator_keys)
    return ("semver: 1.0.0\n" f"plan_id: {plan_id}\n" "required_operator_keys:\n") + body


def _declared(operator_keys: Sequence[str]) -> ProductClassDeclaration:
    """Parse a product-class document through the one supported seam."""
    parsed = load_artifact(_product_class_text(operator_keys), PRODUCT_CLASS)
    assert isinstance(parsed, ProductClassDeclaration)
    return parsed


def _requirements(operator_keys: Sequence[str]) -> ProjectionRequirements:
    """Parse a projection-requirements document through the same seam."""
    parsed = load_artifact(_requirements_text(operator_keys), PROJECTION_REQUIREMENTS)
    assert isinstance(parsed, ProjectionRequirements)
    return parsed


# --- the two plan shapes ------------------------------------------------------


class _ArtifactPlan:
    """A plan that reads its operator set from its requirements artifact (E2)."""

    def __init__(self, requirements: ProjectionRequirements) -> None:
        self._requirements = requirements

    @property
    def plan_id(self) -> str:
        return self._requirements.plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._requirements.required_operator_keys

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        """Never called: the binder runs before the engine, by construction."""
        raise AssertionError("the binder must refuse before a projection runs")


class _DetachedPlan(_ArtifactPlan):
    """A plan that has a requirements artifact and declares something else.

    The shape the ruling names ``plan.required_operators()`` for. See case 4.
    """

    def __init__(
        self, requirements: ProjectionRequirements, *, declares: Sequence[str]
    ) -> None:
        super().__init__(requirements)
        self._declares = tuple(declares)

    def required_operators(self) -> tuple[str, ...]:
        return self._declares


# --- (1) agreement admits -----------------------------------------------------


def test_two_agreeing_documents_are_admitted() -> None:
    """The admit half of the mandatory pair — and order is not significant.

    The two documents declare the same operator keys in **different orders**
    (INV-CH7-28), so this also pins that the binder compares sets rather than
    sequences. A binder that always refused fails here.
    """
    declared = _declared(AGREEING_CLAIM)
    plan: ProjectionPlan = _ArtifactPlan(_requirements(AGREEING_REQUIREMENTS))
    assert declared.required_operator_keys != tuple(plan.required_operators())

    assert refuse_operator_set_divergence(declared=declared, plan=plan) is None


# --- (2) one edited key refuses ----------------------------------------------


def test_one_edited_operator_key_in_one_document_is_refused() -> None:
    """The refuse half of the pair, reached by a one-line edit to one document.

    The two product-class documents below are byte-identical apart from a single
    line — the third operator key line — and that edit is the entire content of
    this case: under design E2 the operator set a deployment declares and the set
    its projection executes are two separately authored documents, so an author
    can now make them disagree. Before E2 they traced to one artifact through
    five pure transforms and nothing a deployment could author made them diverge.

    A binder that always admitted fails here. `test_two_agreeing_documents…`
    above is the half that a binder which always refused would fail.
    """
    agreeing_text = _product_class_text(AGREEING_CLAIM)
    edited_text = _product_class_text((TRAVERSAL, TEMPORAL))

    # The edit is one line, asserted rather than asserted-by-eyeball.
    changed = [
        line
        for line in difflib.ndiff(
            agreeing_text.splitlines(), edited_text.splitlines()
        )
        if line.startswith(("+", "-"))
    ]
    assert len(changed) == 2, changed  # one line removed, one added: a substitution

    declared = _declared((TRAVERSAL, TEMPORAL))
    plan: ProjectionPlan = _ArtifactPlan(_requirements(AGREEING_REQUIREMENTS))

    with pytest.raises(ValueError) as refusal:
        refuse_operator_set_divergence(declared=declared, plan=plan)

    message = str(refusal.value)
    assert TEMPORAL in message  # the key the edit introduced
    assert POLICY in message  # the key the edit displaced
    assert PLAN_ID in message
    assert "D-IMPL-86" in message


# --- (3) a superset and a subset are both refused -----------------------------


@pytest.mark.parametrize(
    ("claim", "requirements", "extra_side"),
    [
        pytest.param(
            (TRAVERSAL, POLICY, TEMPORAL),
            (POLICY, TRAVERSAL),
            "product class",
            id="extra-key-in-the-product-class",
        ),
        pytest.param(
            (TRAVERSAL, POLICY),
            (POLICY, TRAVERSAL, TEMPORAL),
            "projection requirements",
            id="extra-key-in-the-requirements",
        ),
    ],
)
def test_a_superset_and_a_subset_are_both_refused(
    claim: Sequence[str], requirements: Sequence[str], extra_side: str
) -> None:
    """Both directions, because they are different authoring mistakes.

    An operator key the product class claims and the projection does not require
    is a claim the product cannot honour; a key the projection requires and the
    product class does not claim is governance the lineage record will not carry.
    A binder that compared only one direction — a subset test rather than an
    equality — would admit one of these two.
    """
    declared = _declared(claim)
    plan: ProjectionPlan = _ArtifactPlan(_requirements(requirements))

    with pytest.raises(ValueError) as refusal:
        refuse_operator_set_divergence(declared=declared, plan=plan)

    message = str(refusal.value)
    assert TEMPORAL in message, extra_side
    assert "D-IMPL-86" in message


# --- (4) a plan that ignores its own requirements artifact --------------------


def test_a_plan_that_ignores_its_requirements_artifact_is_refused() -> None:
    """Why the ruling names ``plan.required_operators()``, not the second artifact.

    Here the two *documents* agree perfectly: the product class claims exactly
    what the projection-requirements artifact declares. A binder that compared
    the two artifacts to each other would admit this deployment. What it would
    admit is a plan that never read its artifact — it returns a different set,
    and that set is what the engine plans from and what the product is assembled
    by, so the deployment would serve a product assembled from operators no
    document names.

    Comparing against the constructed plan closes that, and it is the reason
    D-IMPL-86 element (3) names ``plan.required_operators()`` rather than the
    requirements document. It is also the case that keeps this a *binder* rather
    than a document diff.
    """
    declared = _declared(AGREEING_CLAIM)
    requirements = _requirements(AGREEING_REQUIREMENTS)
    assert frozenset(declared.required_operator_keys) == frozenset(
        requirements.required_operator_keys
    )

    plan: ProjectionPlan = _DetachedPlan(requirements, declares=(TEMPORAL,))

    with pytest.raises(ValueError) as refusal:
        refuse_operator_set_divergence(declared=declared, plan=plan)

    message = str(refusal.value)
    assert TEMPORAL in message
    assert "D-IMPL-86" in message
