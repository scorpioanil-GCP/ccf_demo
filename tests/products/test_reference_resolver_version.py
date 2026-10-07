"""The reference constraint resolver's version names its behavior, and cannot outlive it.

**SDK-defined, not whitepaper-derived (CLAUDE.md §11).**
:class:`~ccf.products.constraints.PolicyConstraintResolver` carries
``resolver_id`` and ``resolver_version`` because *the resolver in force must be
pinnable into replay* (``D-IMPL-253`` Q8): an effective request is only
reproducible alongside the resolution that produced it. A version is therefore
a claim about BEHAVIOR, and a label that survives a change in what it labels is
a false pin.

``SEC-019`` (``D-IMPL-356`` D11) changed the reference resolution. An absent
parameter that a bounding constraint reaches is now refused ``required-absent``,
where ``1.0.0`` skipped it, so the reference resolver reports ``1.1.0``.

What is pinned here, and how:

* **The label and its fingerprint, together.** :data:`BEHAVIOR_BY_VERSION`
  records, per version, the outcome of a fixed set of questions put to the
  shipped :class:`~ccf.products.constraints.ReferencePolicyConstraintResolver`
  over a real Control Plane. The set reaches every decision the resolution
  makes: the window and the axis that select a constraint, the serve instant
  effectivity is judged at, the folds, the conflict, the clamp, the technical
  ceiling, the override and its entitlement, presence, guidance, and the absent
  bounded parameter. The resolver's fingerprint must equal the entry for the
  version it reports. A behavior change that keeps the label is red, and a new
  label cannot ship without recording what it names.
* **The bump names a real change.** ``1.0.0`` and ``1.1.0`` differ in exactly
  the three absent-bounded questions and nowhere else.
* **The guard can fire.** A scratch COPY of ``constraints.py`` with the
  ``SEC-019`` refusal severed still reports ``1.1.0``. Its fingerprint is
  ``1.0.0``'s, and the pinned predicate goes red against it. The tree is never
  edited.

``1.0.0`` is recorded as the reference resolution stood at ``8fceec83``, the
commit before ``SEC-019``. The label was not bumped at earlier behavior changes
(``D-IMPL-358`` moved effectivity to the serve instant under it), which is the
defect this module stops from recurring; it does not reconstruct those earlier
states.

Every key, name, number and instant below is this module's own fixture
vocabulary (CINV-01 reaches ``tests/``); none lives in ``src/``.
"""

from __future__ import annotations

import pathlib
import types
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    POLICY_CONSTRAINT,
    ConstraintApplicability,
    PolicyConstraint,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products import constraints as constraints_module
from ccf.products.constraints import (
    CAPABILITY_TRAVERSAL_DEPTH,
    REFERENCE_CONSTRAINT_RESOLVER_ID,
    REFERENCE_CONSTRAINT_RESOLVER_VERSION,
    ReferencePolicyConstraintResolver,
    TechnicalCapability,
)
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.provenance import ProvenanceSource
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

from tests.composition import register_typed_at_composition
from tests.products.test_policy_constraints import _scratch_constraints

CONSTRAINTS_PATH = pathlib.Path(constraints_module.__file__)
CONSTRAINTS_SOURCE = CONSTRAINTS_PATH.read_bytes()

#: The version the reference resolver reports now, spelled out rather than read
#: off the constant: a pin read off the thing it pins pins nothing.
VERSION_IN_FORCE = "1.1.0"

# --- this module's own vocabulary ---------------------------------------------

TENANT = "tenant-version-fixture"
PRODUCT_CLASS = "fixture.version-product"
PRODUCT_VERSION = "1.0.0"
OTHER_CLASS = "fixture.another-product"
ROLE = "role-fixture"
PRINCIPAL = "principal-fixture"
PERSPECTIVE = Perspective(principal_id=PRINCIPAL, role=ROLE)
INTENT = "fixture-intent"

#: The question's instant, the serve's, and the windows set around them.
ASKED_AT = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
SERVED_AT = ASKED_AT + timedelta(minutes=5)
OPENED = ASKED_AT - timedelta(days=30)
BETWEEN = ASKED_AT + timedelta(minutes=1)
NOT_YET = SERVED_AT + timedelta(days=1)

TOLERANCE = DEBT_TOLERANCE_PARAMETER
DEPTH = "depth"
THRESHOLD = "threshold"
TIER = "tier"
THRESHOLD_DEFAULT = 1000
OVERRIDABLE_POLICY = "overridable-ceiling"

DECLARED_SOURCE = ProvenanceSource(
    kind="artifact", identity="fixture/request-contract", version="1"
)
CAPABILITY = TechnicalCapability(
    capability=CAPABILITY_TRAVERSAL_DEPTH, maximum=Decimal(100), identity="fixture-store"
)

#: A tolerance, a depth the technical capability bounds, a threshold the class
#: defaults, and a tier. Only the threshold has a default.
CONTRACT = ProductRequestContract(
    semver="1.0.0",
    schema_name=PRODUCT_CLASS,
    schema_version=PRODUCT_VERSION,
    arguments=SkillArgumentSchema(
        properties={
            TOLERANCE: SkillArgumentProperty(type="number", description="a fixture tolerance"),
            DEPTH: SkillArgumentProperty(type="integer", description="a fixture depth"),
            THRESHOLD: SkillArgumentProperty(type="number", description="a fixture threshold"),
            TIER: SkillArgumentProperty(type="string", description="a fixture tier"),
        },
        required=(),
    ),
    defaults={THRESHOLD: THRESHOLD_DEFAULT},
    capability_bindings={DEPTH: CAPABILITY_TRAVERSAL_DEPTH},
)


def _constraint(
    key: str,
    *,
    parameter: str,
    operator: str,
    value: Any,
    overridable: bool = False,
    applies_to: ConstraintApplicability | None = None,
    effective_from: datetime = OPENED,
) -> tuple[str, PolicyConstraint]:
    """One constraint and the Control Plane key it is registered under."""
    return (
        key,
        PolicyConstraint(
            semver="1.0.0",
            policy_id=key.rsplit("/", 1)[-1],
            applies_to=applies_to or ConstraintApplicability(),
            parameter=parameter,
            operator=operator,
            value=value,
            overridable=overridable,
            source_authority="fixture-authority",
            effective_from=effective_from,
            effective_until=None,
            reason="a fixture reason",
        ),
    )


@dataclass(frozen=True)
class _Question:
    """One fixed question: what is registered, what is asked, who may override."""

    constraints: tuple[tuple[str, PolicyConstraint], ...]
    parameters: Mapping[str, Any]
    overrides: tuple[str, ...] = ()
    entitled_to: frozenset[str] = frozenset()


#: The fixed set of questions. Each name says what it asks.
QUESTIONS: Mapping[str, _Question] = {
    "a-value-within-a-ceiling": _Question(
        constraints=(_constraint("fixture/policy/depth-ten", parameter=DEPTH, operator="maximum", value=Decimal(10)),),
        parameters={DEPTH: 8},
    ),
    "a-value-over-a-ceiling": _Question(
        constraints=(_constraint("fixture/policy/depth-five", parameter=DEPTH, operator="maximum", value=Decimal(5)),),
        parameters={DEPTH: 10},
    ),
    "a-value-over-the-technical-ceiling": _Question(constraints=(), parameters={DEPTH: 101}),
    "a-tolerance-over-a-policy-maximum-is-clamped": _Question(
        constraints=(_constraint("fixture/policy/tolerance-ceiling", parameter=TOLERANCE, operator="maximum", value=Decimal("0.20")),),
        parameters={TOLERANCE: Decimal("0.30")},
    ),
    "a-default-is-held-to-a-ceiling": _Question(
        constraints=(_constraint("fixture/policy/threshold-ceiling", parameter=THRESHOLD, operator="maximum", value=Decimal(2000)),),
        parameters={},
    ),
    "a-value-outside-an-allowed-set": _Question(
        constraints=(_constraint("fixture/policy/tier-set", parameter=TIER, operator="allowed_set", value=("tier-a",)),),
        parameters={TIER: "tier-b"},
    ),
    "a-ceiling-below-a-floor": _Question(
        constraints=(
            _constraint("fixture/policy/depth-ceiling", parameter=DEPTH, operator="maximum", value=Decimal(3)),
            _constraint("fixture/policy/depth-floor", parameter=DEPTH, operator="minimum", value=Decimal(9)),
        ),
        parameters={DEPTH: 4},
    ),
    "guidance-the-value-violates": _Question(
        constraints=(_constraint("fixture/policy/depth-guidance", parameter=DEPTH, operator="preferred", value=Decimal(4)),),
        parameters={DEPTH: 8},
    ),
    "a-required-parameter-absent": _Question(
        constraints=(_constraint("fixture/policy/tier-required", parameter=TIER, operator="required", value=None),),
        parameters={},
    ),
    "an-absent-parameter-a-maximum-bounds": _Question(
        constraints=(_constraint("fixture/policy/absent-ceiling", parameter=TOLERANCE, operator="maximum", value=Decimal("0.01")),),
        parameters={},
    ),
    "an-absent-parameter-a-minimum-bounds": _Question(
        constraints=(_constraint("fixture/policy/absent-floor", parameter=TOLERANCE, operator="minimum", value=Decimal("0.05")),),
        parameters={},
    ),
    "an-absent-parameter-an-allowed-set-bounds": _Question(
        constraints=(_constraint("fixture/policy/absent-set", parameter=TIER, operator="allowed_set", value=("tier-a",)),),
        parameters={},
    ),
    "an-absent-parameter-only-guidance-reaches": _Question(
        constraints=(_constraint("fixture/policy/absent-guidance", parameter=TOLERANCE, operator="preferred", value=Decimal("0.10")),),
        parameters={},
    ),
    "an-absent-parameter-only-a-capability-bounds": _Question(constraints=(), parameters={}),
    "an-entitled-override-is-honored": _Question(
        constraints=(_constraint(f"fixture/policy/{OVERRIDABLE_POLICY}", parameter=DEPTH, operator="maximum", value=Decimal(5), overridable=True),),
        parameters={DEPTH: 10},
        overrides=(OVERRIDABLE_POLICY,),
        entitled_to=frozenset({OVERRIDABLE_POLICY}),
    ),
    "a-name-only-override-is-not-honored": _Question(
        constraints=(_constraint(f"fixture/policy/{OVERRIDABLE_POLICY}", parameter=DEPTH, operator="maximum", value=Decimal(5), overridable=True),),
        parameters={DEPTH: 10},
        overrides=(OVERRIDABLE_POLICY,),
    ),
    "a-constraint-not-yet-in-force": _Question(
        constraints=(_constraint("fixture/policy/depth-later", parameter=DEPTH, operator="maximum", value=Decimal(5), effective_from=NOT_YET),),
        parameters={DEPTH: 10},
    ),
    "a-constraint-in-force-at-the-serve-but-not-the-question": _Question(
        constraints=(_constraint("fixture/policy/depth-between", parameter=DEPTH, operator="maximum", value=Decimal(5), effective_from=BETWEEN),),
        parameters={DEPTH: 10},
    ),
    "a-constraint-for-another-class": _Question(
        constraints=(
            _constraint(
                "fixture/policy/depth-elsewhere",
                parameter=DEPTH,
                operator="maximum",
                value=Decimal(5),
                applies_to=ConstraintApplicability(product_class=OTHER_CLASS),
            ),
        ),
        parameters={DEPTH: 10},
    ),
}

#: The defaulted threshold, as every completed resolution below carries it.
_THRESHOLD = (THRESHOLD, str(THRESHOLD_DEFAULT), "default", None, None)

#: What ``1.1.0`` names: the outcome of each question above.
#: A refusal is ``("refused", type, reason, key, bound operator, bound authority)``.
#: A completion is ``("completed", parameters, guidance operators, overrides)``,
#: each parameter as ``(name, value, authority, bound operator, bound authority)``.
_BEHAVIOR_1_1_0: Mapping[str, tuple[Any, ...]] = {
    "a-value-within-a-ceiling": ("completed", ((DEPTH, "8", "caller", "maximum", "policy"), _THRESHOLD), (), ()),
    "a-value-over-a-ceiling": ("refused", "ConstraintRefusal", "bound-exceeded", DEPTH, "maximum", "policy"),
    "a-value-over-the-technical-ceiling": ("refused", "ConstraintRefusal", "bound-exceeded", DEPTH, "maximum", "technical"),
    "a-tolerance-over-a-policy-maximum-is-clamped": ("completed", ((TOLERANCE, "0.20", "policy", "maximum", "policy"), _THRESHOLD), (), ()),
    "a-default-is-held-to-a-ceiling": ("completed", ((THRESHOLD, str(THRESHOLD_DEFAULT), "default", "maximum", "policy"),), (), ()),
    "a-value-outside-an-allowed-set": ("refused", "ConstraintRefusal", "not-in-allowed-set", TIER, "allowed_set", "policy"),
    "a-ceiling-below-a-floor": ("refused", "PolicyResolutionConflict", "policy-resolution-conflict", DEPTH, None, None),
    "guidance-the-value-violates": ("completed", ((DEPTH, "8", "caller", "maximum", "technical"), _THRESHOLD), ("preferred",), ()),
    "a-required-parameter-absent": ("refused", "ConstraintRefusal", "required-absent", TIER, "required", "policy"),
    "an-absent-parameter-a-maximum-bounds": ("refused", "ConstraintRefusal", "required-absent", TOLERANCE, "maximum", "policy"),
    "an-absent-parameter-a-minimum-bounds": ("refused", "ConstraintRefusal", "required-absent", TOLERANCE, "minimum", "policy"),
    "an-absent-parameter-an-allowed-set-bounds": ("refused", "ConstraintRefusal", "required-absent", TIER, "allowed_set", "policy"),
    "an-absent-parameter-only-guidance-reaches": ("completed", (_THRESHOLD,), ("preferred",), ()),
    "an-absent-parameter-only-a-capability-bounds": ("completed", (_THRESHOLD,), (), ()),
    "an-entitled-override-is-honored": (
        "completed",
        ((DEPTH, "10", "caller", "maximum", "technical"), _THRESHOLD),
        (),
        ((OVERRIDABLE_POLICY, True, True),),
    ),
    "a-name-only-override-is-not-honored": ("refused", "ConstraintRefusal", "bound-exceeded", DEPTH, "maximum", "policy"),
    "a-constraint-not-yet-in-force": ("completed", ((DEPTH, "10", "caller", "maximum", "technical"), _THRESHOLD), (), ()),
    "a-constraint-in-force-at-the-serve-but-not-the-question": ("refused", "ConstraintRefusal", "bound-exceeded", DEPTH, "maximum", "policy"),
    "a-constraint-for-another-class": ("completed", ((DEPTH, "10", "caller", "maximum", "technical"), _THRESHOLD), (), ()),
}

#: The three questions ``SEC-019`` changed the answer to.
SEC019_QUESTIONS = (
    "an-absent-parameter-a-maximum-bounds",
    "an-absent-parameter-a-minimum-bounds",
    "an-absent-parameter-an-allowed-set-bounds",
)

#: What each version the reference resolver has carried names. ``1.0.0`` is the
#: resolution at ``8fceec83``: the same answers, except that an absent bounded
#: parameter was skipped and the resolution completed without it.
BEHAVIOR_BY_VERSION: Mapping[str, Mapping[str, tuple[Any, ...]]] = {
    "1.0.0": {
        **_BEHAVIOR_1_1_0,
        **{name: ("completed", (_THRESHOLD,), (), ()) for name in SEC019_QUESTIONS},
    },
    "1.1.0": _BEHAVIOR_1_1_0,
}

#: The severing the guard's control applies to a scratch copy: the ``SEC-019``
#: refusal removed, the label left as it is.
SEC019_NEEDLE = "            if bounding:\n"
SEC019_SABOTAGE = "            if False:\n"


def _answer(module: types.ModuleType, question: _Question) -> tuple[Any, ...]:
    """Put one question to ``module``'s reference resolver over a fresh Control Plane."""
    registry = ControlPlaneRegistry()
    for key, constraint in question.constraints:
        register_typed_at_composition(registry, key, constraint, POLICY_CONSTRAINT)
    if question.entitled_to:
        register_typed_at_composition(
            registry,
            product_entitlement_key(tenant_id=TENANT),
            ProductEntitlementPolicy(
                tenant_id=TENANT,
                policy_version="1.0.0",
                principals={
                    PRINCIPAL: ProductEntitlementGrant(
                        permitted_schema_names=frozenset({PRODUCT_CLASS}),
                        permitted_roles=frozenset({ROLE}),
                        overridable_policies=question.entitled_to,
                    )
                },
            ),
            PRODUCT_ENTITLEMENT_POLICY,
        )
    resolver = module.ReferencePolicyConstraintResolver(
        control_plane=registry, entitlement_key=product_entitlement_key(tenant_id=TENANT)
    )
    outcome = resolver.resolve(
        product_class=PRODUCT_CLASS,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject="fixture:subject/one",
            intent=INTENT,
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters=dict(question.parameters),
            policy_overrides=question.overrides,
        ),
        declared=CONTRACT,
        declared_source=DECLARED_SOURCE,
        perspective=PERSPECTIVE,
        intent=INTENT,
        tenant=TENANT,
        capabilities=(CAPABILITY,),
        served_at=SERVED_AT,
    )
    refusal = outcome.refusal
    if refusal is not None:
        bound = getattr(refusal, "bound", None)
        return (
            "refused",
            type(refusal).__name__,
            refusal.reason,
            refusal.key,
            None if bound is None else bound.operator,
            None if bound is None else bound.authority,
        )
    evidence = outcome.evidence
    return (
        "completed",
        tuple(
            (
                parameter.name,
                str(parameter.value),
                parameter.authority,
                None if parameter.bound is None else parameter.bound.operator,
                None if parameter.bound is None else parameter.bound.authority,
            )
            for parameter in evidence.parameters
        ),
        tuple(sorted(bound.operator for bound in evidence.guidance)),
        tuple((record.policy_id, record.entitled, record.honored) for record in evidence.overrides),
    )


def _fingerprint(module: types.ModuleType) -> dict[str, tuple[Any, ...]]:
    """``module``'s answer to every question, by name."""
    return {name: _answer(module, question) for name, question in QUESTIONS.items()}


def _assert_the_label_names_the_behavior(module: types.ModuleType) -> None:
    """The predicate under control: the version reported is the behavior observed."""
    version = module.REFERENCE_CONSTRAINT_RESOLVER_VERSION
    assert version in BEHAVIOR_BY_VERSION, (
        f"the reference resolver reports {version!r}, which names no recorded"
        " behavior; record what it names in BEHAVIOR_BY_VERSION"
    )
    observed = _fingerprint(module)
    expected = BEHAVIOR_BY_VERSION[version]
    differing = sorted(name for name in expected if observed.get(name) != expected[name])
    assert observed == expected, (
        f"the reference resolver reports {version!r} but behaves differently on"
        f" {differing}: a behavior change must bump"
        " REFERENCE_CONSTRAINT_RESOLVER_VERSION and record what the new"
        " version names (D-IMPL-253 Q8)"
    )


# --- the pin -------------------------------------------------------------------


def test_the_reference_resolver_reports_the_version_in_force() -> None:
    """``1.1.0``, on the constant and on the resolver that reports it."""
    assert REFERENCE_CONSTRAINT_RESOLVER_VERSION == VERSION_IN_FORCE
    resolver = ReferencePolicyConstraintResolver(
        control_plane=ControlPlaneRegistry(), entitlement_key=None
    )
    assert resolver.resolver_version == VERSION_IN_FORCE
    assert resolver.resolver_id == REFERENCE_CONSTRAINT_RESOLVER_ID


def test_the_version_in_force_names_the_behavior_in_force() -> None:
    """The shipped resolver's answers are exactly what ``1.1.0`` names."""
    assert set(QUESTIONS) == set(_BEHAVIOR_1_1_0)
    _assert_the_label_names_the_behavior(constraints_module)


def test_1_1_0_differs_from_1_0_0_in_exactly_the_absent_bounded_questions() -> None:
    """The bump names a real change: ``SEC-019``'s three questions, and nothing else."""
    old, new = BEHAVIOR_BY_VERSION["1.0.0"], BEHAVIOR_BY_VERSION["1.1.0"]
    assert set(old) == set(new) == set(QUESTIONS)
    assert sorted(name for name in new if old[name] != new[name]) == sorted(SEC019_QUESTIONS)
    for name in SEC019_QUESTIONS:
        assert new[name][:3] == ("refused", "ConstraintRefusal", "required-absent"), name
        assert old[name][0] == "completed", name


# --- the guard can fire ----------------------------------------------------------


def test_a_behavior_change_that_keeps_the_label_is_red_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """Sever the ``SEC-019`` refusal on a copy and leave the label: the pin goes red.

    The copy still reports ``1.1.0``, and its answers are ``1.0.0``'s, which
    also measures that the recorded history is what it says.
    """
    scratch = _scratch_constraints(
        tmp_path,
        name="constraints_with_the_sec019_refusal_severed",
        needle=SEC019_NEEDLE,
        replacement=SEC019_SABOTAGE,
    )
    assert scratch.REFERENCE_CONSTRAINT_RESOLVER_VERSION == VERSION_IN_FORCE

    with pytest.raises(AssertionError, match="behaves differently on"):
        _assert_the_label_names_the_behavior(scratch)
    assert _fingerprint(scratch) == BEHAVIOR_BY_VERSION["1.0.0"]

    # And the real module still names its behavior.
    _assert_the_label_names_the_behavior(constraints_module)


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """The control mutates a copy under ``tmp_path``; ``constraints.py`` is unchanged."""
    assert CONSTRAINTS_PATH.read_bytes() == CONSTRAINTS_SOURCE
    assert CONSTRAINTS_SOURCE.decode("utf-8").count(SEC019_NEEDLE) == 1
