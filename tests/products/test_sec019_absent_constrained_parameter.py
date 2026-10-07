"""SEC-019: an absent constrained parameter is REFUSED, never skipped (``D-IMPL-356`` D11).

**The row, as worded** (security review of 2026-09-23, MEDIUM table): *"A
policy ``maximum`` on ``debt_tolerance`` is skipped when the caller omits the
parameter and no default exists, served at any debt."* Two sites skipped it.
The constraint layer,
:func:`ccf.products.constraints.resolve_effective_request`, passed over a
bounded parameter with no value (``if key not in effective: continue``), and
the tolerance step, :func:`ccf.products.gates.refuse_over_tolerance`, served an
absent tolerance at any Debt (``if tolerance is None: return None``).

**The remedy is ruled and locked**: ``D-IMPL-356``, sub-ruling D11, the
``SEC-019`` rider of the accepted v1.0.2 design. *"A bounding constraint
(``maximum``/``minimum``/``allowed_set``) on a parameter with no value and no
declared default is a ``required-absent`` refusal; ``required`` stays the
explicit form; ``preferred`` stays non-refusing."* It amends the realization of
``D-IMPL-253`` Q5, under which only ``required`` refused absence. The same rule
holds at the tolerance step: it cannot serve an absent tolerance that a policy
bounds.

What each test pins:

* **The worded case, through the shipped**
  :class:`~ccf.products.resolver.GovernedResolver`: a class declaring no
  default tolerance, a registered ``ccf.policy-constraint`` ``maximum`` of
  0.01 on ``debt_tolerance``, an observed ``D_c`` of 0.99, and a caller who
  omits the parameter. The request is REFUSED: ``constraint-refusal``,
  ``required-absent``, and a bound carrying authority ``policy`` and the
  constraint's own pin, read back from the replay record the refusal wrote.
  Before the repair the product was SERVED at 0.99.
* **Its two controls on the same deployment.** A STATED tolerance is clamped by
  the same maximum and withheld, so the policy is live and the worded test is
  not passing on a deployment that refuses everything. With NO constraint
  registered the omitted tolerance is still served: a parameter with no
  registered constraint keeps today's behavior.
* **The constraint layer, per bounding operator** (``maximum``, ``minimum``,
  ``allowed_set``): each refuses ``required-absent`` with its own bound, its
  own pin and authority ``policy``, and the evidence still names it.
* **The controls that keep it from over-refusing.** ``preferred`` alone stays
  guidance. A declared default is held to the bound, not refused as absent. A
  parameter that only a TECHNICAL capability bounds keeps today's behavior:
  the ruling covers registered policy constraints, and the capability step's
  own skip of an absent parameter is deliberately unchanged. A parameter
  nothing bounds completes.
* **The tolerance step.** An absent tolerance that a policy bounds cannot be
  served there either (``required-absent``, the policy's bound). An absent
  tolerance that nothing bounds still is.

Every number, key and role is this module's own or is imported from the
fixture module that owns it (CINV-01 reaches ``tests/``); none lives in
``src/``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products import constraints as constraints_module
from ccf.products.constraints import (
    CAPABILITY_TRAVERSAL_DEPTH,
    ConstraintRefusal,
    PinnedConstraint,
    ResolutionOutcome,
)
from ccf.products.contract import NO_SERVE_OBLIGATIONS
from ccf.products.gates import (
    DEBT_TOLERANCE_PARAMETER,
    ServableProduct,
    refuse_over_tolerance,
)
from ccf.products.provenance import ParameterBound, ProvenanceSource
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.serve import ServedProduct

from tests.products.test_policy_constraints import (
    CAPABILITY,
    DECLARED_SOURCE,
    DEPTH,
    PERSPECTIVE,
    TENANT,
    TIER,
    TOLERANCE,
    _contract,
    _pinned,
    _request,
    _resolve,
)
from tests.products.test_resolver_seam import _ask, _internal
from tests.products.test_structural_gates import (
    PAYLOAD_WITH_MEMBER,
    POLICY_ARTIFACT_KEY,
    POLICY_ARTIFACT_VERSION,
    _candidate,
    _class,
    _serve,
)
from tests.products.test_tolerance_exceeded import (  # noqa: F401  (fixture import)
    ANY_DEBT,
    CALLER_LOOSE,
    POLICY_ID,
    POLICY_KEY,
    POLICY_MAXIMUM,
    _Booted,
    _governed,
    _question,
    _register_maximum,
    booted_without_default,
)

# --- this module's own vocabulary --------------------------------------------

#: The fixture request surface with NO declared defaults: omission of any
#: parameter means nothing, so an absent parameter has no value to govern.
UNDEFAULTED = _contract(defaults={})

#: The bounding operators the ruling names, each on an absent parameter, with a
#: value of the shape the operator takes. Fixture figures only.
BOUNDING = (
    pytest.param(TOLERANCE, "maximum", Decimal("0.20"), id="maximum"),
    pytest.param(TOLERANCE, "minimum", Decimal("0.05"), id="minimum"),
    pytest.param(TIER, "allowed_set", ("tier-a", "tier-b"), id="allowed_set"),
)

#: The policy bound the tolerance step is handed in the step-level case: a
#: ``maximum`` on the tolerance, authority ``policy``, with an artifact pin.
STEP_POLICY_BOUND = ParameterBound(
    operator="maximum",
    value=Decimal("0.01"),
    authority="policy",
    source=ProvenanceSource(
        kind="artifact", identity=POLICY_ARTIFACT_KEY, version=POLICY_ARTIFACT_VERSION
    ),
    policy_id="fixture-tolerance-policy",
    reason="a fixture reason",
)

#: The Debt the step-level product carries: far over any tolerance, so a step
#: that served it would have served at any Debt.
STEP_OBSERVED_DEBT = Decimal("0.99")


def _resolve_undefaulted(
    request: ProductRequest,
    *,
    constraints: tuple[PinnedConstraint, ...] = (),
    capability_bindings: dict[str, str] | None = None,
) -> ResolutionOutcome:
    """Resolve against :data:`UNDEFAULTED` through the shipped module."""
    return constraints_module.resolve_effective_request(
        request=request,
        declared=UNDEFAULTED,
        declared_source=DECLARED_SOURCE,
        constraints=constraints,
        capabilities=(CAPABILITY,),
        capability_bindings={} if capability_bindings is None else capability_bindings,
        verified_overrides=(),
        perspective=PERSPECTIVE,
        tenant=TENANT,
        served_at=request.asked_at,
    )


def _admitted(debt: Decimal) -> ServableProduct:
    """A product the gates ADMITTED, carrying a ``D_c`` of exactly ``debt``."""
    registry = ControlPlaneRegistry()
    product_class = _class(registry, serve_obligations=NO_SERVE_OBLIGATIONS)
    gated = _serve(
        _candidate(debt=debt, payload=PAYLOAD_WITH_MEMBER),
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct), gated
    return gated


# --- (a) the worded case, through the shipped GovernedResolver -----------------


def test_the_worded_case_a_policy_maximum_on_an_omitted_tolerance_is_refused_not_served(
    booted_without_default: _Booted,
) -> None:
    """SEC-019 as worded: no default, a policy maximum, the caller omits it, D_c 0.99.

    The request is refused before anything is read, by the constraint that
    bounds the parameter: ``constraint-refusal`` / ``required-absent``, the
    bound carrying authority ``policy`` and the constraint's ``(key,
    version)``. ``_internal`` reads the determination back from the replay
    record it wrote, so "refused" here also means "recorded".
    """
    version = _register_maximum(booted_without_default, POLICY_MAXIMUM)

    outcome = _ask(_governed(booted_without_default, debt=ANY_DEBT), _question())

    served_debt = (
        outcome.product.debt.debt
        if isinstance(outcome, ServedProduct) and outcome.product.debt is not None
        else None
    )
    assert not isinstance(outcome, ServedProduct), (
        f"SEC-019 HOLE PRESENT: policy maximum {POLICY_MAXIMUM} on"
        f" {DEBT_TOLERANCE_PARAMETER} was skipped for an omitted parameter with"
        f" no default; the product was SERVED at debt {served_debt}"
    )
    assert isinstance(outcome, RefusalEnvelope), type(outcome).__name__
    assert outcome.kind == REFUSAL_KINDS[ConstraintRefusal] == "constraint-refusal"
    assert outcome.reason == "required-absent", outcome.reason
    assert outcome.key == DEBT_TOLERANCE_PARAMETER, outcome.key

    internal = _internal(booted_without_default, outcome)
    assert internal.kind == "constraint-refusal"
    assert internal.reason == "required-absent"
    assert internal.key == DEBT_TOLERANCE_PARAMETER
    bound = ParameterBound.model_validate_json(internal.fields["bound"])
    assert bound.authority == "policy", bound
    assert bound.operator == "maximum", bound
    assert Decimal(str(bound.value)) == POLICY_MAXIMUM, bound
    assert bound.source == ProvenanceSource(
        kind="artifact", identity=POLICY_KEY, version=version
    ), bound.source
    assert bound.policy_id == POLICY_ID
    # Nothing was presented, stated positively rather than as a zero.
    assert internal.fields["requested"] == "null", internal.fields


def test_control_a_stated_tolerance_on_the_same_deployment_is_clamped_and_withheld(
    booted_without_default: _Booted,
) -> None:
    """The control that keeps the worded test non-vacuous: the maximum is LIVE.

    The same deployment and the same registered maximum. A caller who STATES
    0.30 is clamped to the policy's 0.01 (worked case 3) and withheld at 0.99
    as ``tolerance-exceeded`` with authority ``policy``. So the refusal above is
    not a deployment that refuses whatever it is asked.
    """
    _register_maximum(booted_without_default, POLICY_MAXIMUM)

    outcome = _ask(
        _governed(booted_without_default, debt=ANY_DEBT),
        _question(**{DEBT_TOLERANCE_PARAMETER: CALLER_LOOSE}),
    )

    assert isinstance(outcome, RefusalEnvelope), type(outcome).__name__
    assert outcome.kind == "tolerance-exceeded", outcome.kind
    assert outcome.fields["authority"] == '"policy"', outcome.fields


def test_control_with_no_registered_constraint_an_omitted_tolerance_is_still_served(
    booted_without_default: _Booted,
) -> None:
    """A parameter with NO registered constraint keeps today's behavior.

    No default, no caller value, no constraint: nothing declared a tolerance,
    so none applies, and the product is served at 0.99. This is what keeps the
    worded test from passing on a resolver that refused every absent parameter.
    """
    outcome = _ask(_governed(booted_without_default, debt=ANY_DEBT), _question())

    assert isinstance(outcome, ServedProduct), outcome
    assert outcome.product.debt is not None
    assert outcome.product.debt.debt == ANY_DEBT


# --- (b) the constraint layer: every bounding operator -------------------------


@pytest.mark.parametrize(("parameter", "operator", "value"), BOUNDING)
def test_an_absent_parameter_a_bounding_constraint_reaches_is_refused_required_absent(
    parameter: str, operator: str, value: Any
) -> None:
    """``maximum``, ``minimum`` and ``allowed_set`` each refuse an absent parameter.

    The class declares no default and the caller states nothing, so there is no
    value to hold to the bound. The bound is reported with the authority and
    the pin it was resolved by, and the evidence accumulated so far still names
    the constraint (``D-IMPL-264`` D-07).
    """
    pinned = _pinned(
        parameter=parameter, operator=operator, value=value, key=f"constraint/{operator}"
    )

    outcome = _resolve_undefaulted(_request(), constraints=(pinned,))

    assert isinstance(outcome.refusal, ConstraintRefusal), (
        f"SEC-019: the {operator} constraint on the absent {parameter!r} was"
        " skipped and the resolution completed with"
        f" {dict(outcome.evidence.values())}"
    )
    refusal = outcome.refusal
    assert refusal.reason == "required-absent"
    assert refusal.key == parameter
    assert refusal.requested is None
    assert refusal.bound.operator == operator
    assert refusal.bound.authority == "policy"
    assert refusal.bound.source == ProvenanceSource(
        kind="artifact", identity=pinned.key, version=pinned.version
    )
    assert refusal.bound.policy_id == pinned.constraint.policy_id
    assert refusal.bound.source in outcome.evidence.applied
    assert outcome.evidence.parameter(parameter) is None


def test_control_preferred_alone_on_an_absent_parameter_stays_guidance() -> None:
    """``preferred`` stays non-refusing (``D-IMPL-253`` Q5), present or absent."""
    pinned = _pinned(parameter=TOLERANCE, operator="preferred", value=Decimal("0.10"))

    outcome = _resolve_undefaulted(_request(), constraints=(pinned,))

    assert outcome.refusal is None, outcome.refusal
    assert outcome.evidence.parameter(TOLERANCE) is None
    assert [bound.operator for bound in outcome.evidence.guidance] == ["preferred"]


def test_control_a_declared_default_is_held_to_the_bound_not_refused_as_absent() -> None:
    """Omission means the default: a defaulted value is governed, not refused.

    The fixture contract declares a default depth of 6. A policy maximum of 10
    holds it. The value keeps authority ``default`` and carries the policy's
    bound.
    """
    pinned = _pinned(parameter=DEPTH, operator="maximum", value=Decimal(10))

    outcome = _resolve(_request(), constraints=(pinned,))

    assert outcome.refusal is None, outcome.refusal
    depth = outcome.evidence.parameter(DEPTH)
    assert depth is not None
    assert depth.authority == "default"
    assert depth.value == 6
    assert depth.bound is not None
    assert depth.bound.operator == "maximum"
    assert depth.bound.authority == "policy"


def test_control_a_parameter_only_a_technical_capability_bounds_keeps_todays_behavior() -> None:
    """The capability step's skip of an absent parameter is deliberately unchanged.

    The ruling covers a REGISTERED POLICY constraint. A backend's technical
    limit is not one, and a parameter with no registered constraint keeps
    today's behavior: the depth is absent, nothing refuses, and the capability
    is still recorded as consulted.
    """
    outcome = _resolve_undefaulted(
        _request(), capability_bindings={DEPTH: CAPABILITY_TRAVERSAL_DEPTH}
    )

    assert outcome.refusal is None, outcome.refusal
    assert outcome.evidence.parameter(DEPTH) is None
    assert (
        ProvenanceSource(kind="capability", identity=CAPABILITY.identity, version=None)
        in outcome.evidence.applied
    )


def test_control_a_parameter_nothing_bounds_completes_when_absent() -> None:
    """No constraint, no default, no value: the resolution completes, as before."""
    outcome = _resolve_undefaulted(_request())

    assert outcome.refusal is None, outcome.refusal
    assert dict(outcome.evidence.values()) == {}


# --- (c) the tolerance step ----------------------------------------------------


def test_the_tolerance_step_cannot_serve_an_absent_tolerance_a_policy_bounds() -> None:
    """The same rule at the delivery step: absent but policy-bounded is refused.

    The step is handed no tolerance and the policy's bound on it. It refuses
    with the Authority layer's own determination (``required-absent``, the
    policy's bound) instead of serving a product whose ``D_c`` is 0.99.
    """
    gated = _admitted(STEP_OBSERVED_DEBT)

    withheld = refuse_over_tolerance(
        gated, tolerance=None, policy_bound=STEP_POLICY_BOUND
    )

    assert withheld is not None, (
        "SEC-019 at the tolerance step: an absent tolerance a policy bounds was"
        f" served at debt {STEP_OBSERVED_DEBT}"
    )
    assert isinstance(withheld, ConstraintRefusal), type(withheld).__name__
    assert withheld.reason == "required-absent"
    assert withheld.key == DEBT_TOLERANCE_PARAMETER
    assert withheld.bound == STEP_POLICY_BOUND
    assert withheld.bound.authority == "policy"
    assert withheld.requested is None


def test_control_the_tolerance_step_still_serves_an_absent_tolerance_nothing_bounds() -> None:
    """No tolerance and no policy bound: nothing to enforce, so it is served."""
    gated = _admitted(STEP_OBSERVED_DEBT)

    assert refuse_over_tolerance(gated, tolerance=None, policy_bound=None) is None
