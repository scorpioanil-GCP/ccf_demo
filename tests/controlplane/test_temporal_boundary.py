"""`TemporalBoundaryPolicy`: declared, validated, tenant-resolved and PINNED.

`D-IMPL-358`, Wave 2 step 3. What this suite establishes is exactly the step's
claim and no more: the artifact can be declared, versioned, resolved by tenant
and pinned exactly. It establishes nothing about enforcement — no clock is read,
no request is bounded, and no served or refusal record is touched anywhere in
this module or in the code it exercises.

**Real registry throughout, with one narrow and measured exception.** Every test
below uses `ccf.controlplane.registry.ControlPlaneRegistry` and the same
composition-minted registration door the rest of the suite uses. The exception is
the pin control, and the reason is a measurement rather than a preference: the
real registry derives a version as ``content_hash(artifact)``, so an
implementation that DISCARDED the registry's version and recomputed it from the
policy would produce a byte-identical string. A pin control on the real registry
therefore **cannot** falsify the defect it exists to catch.
`test_a_pin_control_on_the_real_registry_is_blind_to_a_recomputed_version`
measures that blindness directly, and the pin control itself uses a stand-in
whose version is not derivable from content.

**The defect this whole suite guards against** is in the sibling artifact:
`ccf/peering/eligibility.py::_evidence_too_old` resolves as ``_version, policy =
registry.resolve_latest(key)`` and discards the version, so no replay can name
which version of the bound authorized an admission.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.controlplane.registry import (
    AuditLog,
    ControlPlaneMissing,
    ControlPlaneRegistry,
    content_hash,
)
from ccf.controlplane.temporal_boundary import (
    TEMPORAL_BOUNDARY_POLICY,
    PinnedTemporalBoundary,
    TemporalBoundaryMisdeclared,
    TemporalBoundaryPolicy,
    TemporalBoundaryUndeclared,
    resolve_temporal_boundary,
    temporal_boundary_policy_key,
)
from ccf.peering.eligibility import (
    ELIGIBILITY_EVIDENCE_POLICY,
    EligibilityEvidencePolicy,
)
from ccf.replay.record import PolicyBinding
from tests.composition import register_typed_at_composition

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"


@pytest.fixture()
def registry() -> ControlPlaneRegistry:
    """A REAL in-process Control Plane, as the rest of this suite constructs one."""
    return ControlPlaneRegistry()


def declare(
    registry: ControlPlaneRegistry,
    *,
    tenant_id: str,
    max_past: int = 86_400,
    skew: int = 60,
) -> str:
    """Register a boundary for `tenant_id` and return the version the registry gave."""
    return register_typed_at_composition(
        registry,
        temporal_boundary_policy_key(tenant_id=tenant_id),
        TemporalBoundaryPolicy(
            max_past_seconds=max_past, permitted_clock_skew_seconds=skew
        ),
        TEMPORAL_BOUNDARY_POLICY,
    )


# ==========================================================================
# Shape and validation. The SDK supplies no number.
# ==========================================================================


def test_a_negative_max_past_is_refused() -> None:
    """A negative window names an interval that ends before it begins."""
    with pytest.raises(ValueError, match="cannot be negative"):
        TemporalBoundaryPolicy(max_past_seconds=-1, permitted_clock_skew_seconds=0)


def test_a_negative_permitted_clock_skew_is_refused() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        TemporalBoundaryPolicy(max_past_seconds=0, permitted_clock_skew_seconds=-1)


def test_zero_is_a_legal_value_and_is_the_strictest_bound() -> None:
    """The accepted duration semantics, read off the sibling artifact's comparison.

    `ccf/peering/eligibility.py::_evidence_too_old` compares ``age >
    max_evidence_age_seconds``, so a declared ``0`` admits only an age of zero or
    less. Zero is therefore a legal declaration meaning the strictest bound, NOT
    "unbounded" — and this test asserts only that it is accepted, because the
    comparison itself is out of scope at this step.
    """
    policy = TemporalBoundaryPolicy(max_past_seconds=0, permitted_clock_skew_seconds=0)
    assert policy.max_past_seconds == 0
    assert policy.permitted_clock_skew_seconds == 0


def test_neither_field_has_an_sdk_default() -> None:
    """`D-IMPL-38`, no-silent-default. A field with a default would be the SDK
    holding a deployment value, and a deployment that forgot to declare one would
    silently inherit the SDK's opinion about how much history it answers for."""
    with pytest.raises(ValueError):
        TemporalBoundaryPolicy()  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        TemporalBoundaryPolicy(max_past_seconds=1)  # type: ignore[call-arg]
    for name, field in TemporalBoundaryPolicy.model_fields.items():
        assert field.is_required(), f"{name} acquired a default"


def test_the_artifact_class_id_follows_the_repository_convention() -> None:
    assert TEMPORAL_BOUNDARY_POLICY.class_id == "ccf.temporal-boundary-policy"
    assert TEMPORAL_BOUNDARY_POLICY.contract is TemporalBoundaryPolicy


# ==========================================================================
# Tenant scope. Two tenants cannot collide on one key.
# ==========================================================================


def test_the_canonical_tenant_key_is_deterministic() -> None:
    first = temporal_boundary_policy_key(tenant_id=TENANT_A)
    assert first == temporal_boundary_policy_key(tenant_id=TENANT_A)
    assert first == f"{TENANT_A}/ccf.temporal-boundary-policy"


def test_two_tenants_derive_different_keys_and_the_tenant_comes_first() -> None:
    """Tenant-first (``{tenant}/{class}``) because the registry's one tenant
    comparison reads the segment before the first ``/`` (`D-IMPL-353` §1.3)."""
    key_a = temporal_boundary_policy_key(tenant_id=TENANT_A)
    key_b = temporal_boundary_policy_key(tenant_id=TENANT_B)
    assert key_a != key_b
    assert key_a.split("/", 1)[0] == TENANT_A
    assert key_b.split("/", 1)[0] == TENANT_B


def test_two_tenants_resolve_independently_and_cannot_collide_on_one_key(
    registry: ControlPlaneRegistry,
) -> None:
    """The isolation property severing T2 falsifies.

    Each tenant declares a DIFFERENT window, so a collision would be visible in
    the resolved value and not only in the key string.
    """
    version_a = declare(registry, tenant_id=TENANT_A, max_past=3_600)
    version_b = declare(registry, tenant_id=TENANT_B, max_past=604_800)

    pinned_a = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)
    pinned_b = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_B)
    assert isinstance(pinned_a, PinnedTemporalBoundary)
    assert isinstance(pinned_b, PinnedTemporalBoundary)

    assert pinned_a.policy.max_past_seconds == 3_600
    assert pinned_b.policy.max_past_seconds == 604_800
    assert pinned_a.key != pinned_b.key
    assert pinned_a.version == version_a
    assert pinned_b.version == version_b
    assert pinned_a.version != pinned_b.version


def test_one_tenants_declaration_does_not_make_another_tenant_declared(
    registry: ControlPlaneRegistry,
) -> None:
    """Tenant B declaring nothing must remain undeclared however much A declared."""
    declare(registry, tenant_id=TENANT_A)
    undeclared = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_B)
    assert isinstance(undeclared, TemporalBoundaryUndeclared)
    assert undeclared.key == temporal_boundary_policy_key(tenant_id=TENANT_B)


# ==========================================================================
# Resolution: the typed result, and the version that survives it.
# ==========================================================================


def test_a_registered_policy_resolves_as_the_correct_type(
    registry: ControlPlaneRegistry,
) -> None:
    declare(registry, tenant_id=TENANT_A, max_past=86_400, skew=60)
    pinned = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)
    assert isinstance(pinned, PinnedTemporalBoundary)
    assert isinstance(pinned.policy, TemporalBoundaryPolicy)
    assert pinned.policy.max_past_seconds == 86_400
    assert pinned.policy.permitted_clock_skew_seconds == 60


def test_the_exact_registered_version_survives_resolution(
    registry: ControlPlaneRegistry,
) -> None:
    version = declare(registry, tenant_id=TENANT_A)
    pinned = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)
    assert isinstance(pinned, PinnedTemporalBoundary)
    assert pinned.version == version


def test_registering_a_second_version_changes_the_resulting_pin(
    registry: ControlPlaneRegistry,
) -> None:
    """A pin names the version that authorized a decision, so it must move when the
    registered policy does — and must name the LATEST, not the first."""
    first = declare(registry, tenant_id=TENANT_A, max_past=3_600)
    pinned_first = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)
    assert isinstance(pinned_first, PinnedTemporalBoundary)
    assert pinned_first.version == first

    second = declare(registry, tenant_id=TENANT_A, max_past=7_200)
    assert second != first
    pinned_second = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)
    assert isinstance(pinned_second, PinnedTemporalBoundary)
    assert pinned_second.version == second
    assert pinned_second.binding != pinned_first.binding


# ==========================================================================
# THE PIN CONTROL, and the measured reason it cannot use the real registry.
# ==========================================================================


class _OpaqueVersionPlane:
    """A stand-in Control Plane whose version is NOT derivable from the artifact.

    Narrow and deliberate. The real registry's version is ``content_hash(artifact)``,
    so it cannot distinguish a carried version from a recomputed one; this plane
    can, because nothing about ``OPAQUE_VERSION`` follows from the policy. It
    implements only what `resolve_temporal_boundary` calls.
    """

    OPAQUE_VERSION = "registry-issued-2026-09-28T01:00:00Z-seq-0007"

    def __init__(self, artifact: object) -> None:
        self._artifact = artifact
        self.resolved_keys: list[str] = []

    def resolve_latest(self, key: str) -> tuple[str, object]:
        self.resolved_keys.append(key)
        return self.OPAQUE_VERSION, self._artifact


def test_a_pin_control_on_the_real_registry_is_blind_to_a_recomputed_version(
    registry: ControlPlaneRegistry,
) -> None:
    """THE CONTROL FOR THE CONTROL. Measured, not argued.

    If the real registry's version equals ``content_hash(policy)``, then asserting
    ``pinned.version == registered_version`` passes for an implementation that
    never read the registry's version at all. This test exists so that fact is
    recorded in the suite rather than discovered later, and so the stand-in below
    is visibly necessary rather than a convenience.
    """
    policy = TemporalBoundaryPolicy(max_past_seconds=86_400, permitted_clock_skew_seconds=60)
    version = register_typed_at_composition(
        registry,
        temporal_boundary_policy_key(tenant_id=TENANT_A),
        policy,
        TEMPORAL_BOUNDARY_POLICY,
    )
    assert version == content_hash(policy), (
        "the registry no longer derives its version from content — if this fails,"
        " the real registry CAN falsify a recomputing implementation and the"
        " stand-in below is no longer required"
    )


def test_resolving_produces_the_exact_policy_binding_replay_will_carry() -> None:
    """THE PIN CONTROL (`D-IMPL-358` step 3).

    Subject: *resolving a temporal policy produces the exact
    ``PolicyBinding(key, version)`` later replay will carry.*

    Uses `_OpaqueVersionPlane` so the assertion FAILS if the implementation
    discards the registry's version and reconstructs or hard-codes one — which the
    real registry cannot detect, as the test above measures. Severing T1 falsifies
    this control.

    **Nothing is appended to a ReplayRecord here.** The binding is established as
    a value; threading it into records is a later step.
    """
    policy = TemporalBoundaryPolicy(max_past_seconds=86_400, permitted_clock_skew_seconds=60)
    plane = _OpaqueVersionPlane(policy)
    expected_key = temporal_boundary_policy_key(tenant_id=TENANT_A)

    pinned = resolve_temporal_boundary(registry=plane, tenant_id=TENANT_A)  # type: ignore[arg-type]

    assert isinstance(pinned, PinnedTemporalBoundary)
    assert plane.resolved_keys == [expected_key], "the canonical key was not the one consulted"
    assert pinned.key == expected_key
    assert pinned.version == _OpaqueVersionPlane.OPAQUE_VERSION
    assert pinned.version != content_hash(policy), (
        "the version is derivable from the policy, so this control proves nothing"
    )
    assert pinned.binding == PolicyBinding(
        key=expected_key, version=_OpaqueVersionPlane.OPAQUE_VERSION
    )


def test_the_pin_carries_all_three_facts_together() -> None:
    """Key, version and typed policy in one frozen value, so there is no way to
    construct a pin that lost one of them."""
    policy = TemporalBoundaryPolicy(max_past_seconds=1, permitted_clock_skew_seconds=2)
    pinned = PinnedTemporalBoundary(key="t/x", version="v-1", policy=policy)
    assert (pinned.key, pinned.version, pinned.policy) == ("t/x", "v-1", policy)
    with pytest.raises(TypeError):
        PinnedTemporalBoundary(key="t/x", version="v-1")  # type: ignore[call-arg]


# ==========================================================================
# Absent, wrong, and unavailable are three different facts.
# ==========================================================================


def test_a_missing_policy_produces_the_explicit_absence_and_invents_nothing(
    registry: ControlPlaneRegistry,
) -> None:
    """`D-IMPL-358` ruling 11: on absence the fabric records the key or class that
    was required and the absence reason, and never fabricates a version."""
    undeclared = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)
    assert isinstance(undeclared, TemporalBoundaryUndeclared)
    assert undeclared.key == temporal_boundary_policy_key(tenant_id=TENANT_A)
    assert undeclared.required_class_id == "ccf.temporal-boundary-policy"
    assert undeclared.reason == "temporal-boundary-undeclared"
    assert not hasattr(undeclared, "version"), "absence must not carry a version"
    assert not hasattr(undeclared, "policy"), "absence must not carry a policy"


def test_a_wrong_artifact_at_the_key_is_not_treated_as_absence(
    registry: ControlPlaneRegistry,
) -> None:
    """The sibling artifact folds both into ``eligibility-bound-undeclared``. A
    deployment that declared the WRONG thing and one that declared NOTHING need
    different things done about them."""
    register_typed_at_composition(
        registry,
        temporal_boundary_policy_key(tenant_id=TENANT_A),
        EligibilityEvidencePolicy(max_evidence_age_seconds=1, permitted_clock_skew_seconds=1),
        ELIGIBILITY_EVIDENCE_POLICY,
    )
    with pytest.raises(TemporalBoundaryMisdeclared, match="NOT an undeclared boundary"):
        resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)


def test_the_misdeclared_error_is_a_type_error_so_existing_handlers_still_catch_it() -> None:
    assert issubclass(TemporalBoundaryMisdeclared, TypeError)


class _FailingPlane:
    """A Control Plane that is unwell. Its failure is not an absence."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def resolve_latest(self, key: str) -> tuple[str, object]:
        raise self._error


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("the control plane is unreachable"),
        PermissionError("this capability may not read that key"),
        TimeoutError("the control plane did not answer"),
        ValueError("the stored artifact could not be decoded"),
    ],
    ids=["unreachable", "unauthorized", "timeout", "undecodable"],
)
def test_a_registry_failure_is_not_treated_as_absence(error: Exception) -> None:
    """Only `ControlPlaneMissing` means absence. A broad ``except`` would report an
    outage as an undeclared bound and silently disable the boundary on exactly the
    day the control plane was unwell. Severing T4 falsifies this."""
    with pytest.raises(type(error)):
        resolve_temporal_boundary(registry=_FailingPlane(error), tenant_id=TENANT_A)  # type: ignore[arg-type]


def test_control_plane_missing_is_the_one_exception_that_means_absence() -> None:
    """Named explicitly, so a future edit that widens the catch has to change this
    test and say why."""
    undeclared = resolve_temporal_boundary(
        registry=_FailingPlane(ControlPlaneMissing("nothing there")),  # type: ignore[arg-type]
        tenant_id=TENANT_A,
    )
    assert isinstance(undeclared, TemporalBoundaryUndeclared)
    assert issubclass(ControlPlaneMissing, LookupError)


# ==========================================================================
# The step boundary: this module enforces nothing.
# ==========================================================================


def test_nothing_in_this_module_reads_a_clock() -> None:
    """The Wave 2 step 3 boundary, and `D-IMPL-159`: this is a declaration and
    resolution surface, not an enforcement one. A clock read here would be the
    first half of an enforcement nobody ruled yet."""
    import pathlib

    import ccf.controlplane.temporal_boundary as module

    source = pathlib.Path(module.__file__).read_text()
    executable = "\n".join(
        line
        for line in source.splitlines()
        if not line.lstrip().startswith(("#", '"', "'"))
    )
    for forbidden in ("datetime.now", "time.time", "utcnow", "admission_clock", "monotonic"):
        assert forbidden not in executable, f"this module reads a clock: {forbidden}"
