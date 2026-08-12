"""The door-side half of product entitlement: one definition, three doors.

Plan 15.5-03 shipped the *artifact* — who may receive which Context Product
class, and as whom. This file asserts the *door* half: the seam every exposed
product door holds, the reference source that resolves the artifact per call
and audits both outcomes, and the shared resolution order that decides a
:class:`~ccf.projection.plan.Perspective` from a verified grant rather than
from a caller's claim.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
T-15.5-19 (caller-asserted role)           a resolver could mint a role outside
                                           the grant and the door would serve
                                           the view conditioned on it
T-15.5-20 (per-class disclosure)           a principal entitled to one class
                                           would receive another
T-15.5-21 (inert-when-unbound)             a door would build with no
                                           entitlement source and answer
                                           everyone
T-15.5-23 (unaudited allow/deny)           a refusal — or an allow — would
                                           leave no ``authz_decision`` trace
T-15.5-24 (stale policy)                   a cached policy would decide against
                                           a version no longer in force
=========================================  ===================================

Tenant, principal, role and product-class names below are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    ProductEntitlementViolation,
    product_entitlement_key,
)
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    PerspectiveResolverProtocol,
    ProductEntitlementRefused,
    ProductEntitlementSourceProtocol,
    entitled_perspective,
)
from ccf_runtime.authz.refusals import ACTION_PRODUCT_RETRIEVE
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
    ERROR_PRODUCT_POLICY_ABSENT,
    ERROR_PRODUCT_ROLE_UNGRANTED,
    ERROR_SUBJECT_CONFLICT,
)
from ccf_runtime.mcp.auth import TokenGrant

#: Test deployment vocabulary. The SDK ships none of these values.
TENANT = "tenant-entitlement-door"
OTHER_TENANT = "tenant-entitlement-door-other"
PRINCIPAL = "caller-entitled"
STRANGER = "caller-unconfigured"
ROLE = "role-granted"
OTHER_ROLE = "role-ungranted"
PRODUCT_CLASS = "class-permitted"
OTHER_PRODUCT_CLASS = "class-not-permitted"
POLICY_VERSION = "1.0.0"

#: The instant every audit event carries. Injected, never read from a clock.
NOW = datetime(2026, 8, 11, tzinfo=UTC)


def _grant(client_id: str = PRINCIPAL) -> TokenGrant:
    return TokenGrant(client_id=client_id, scopes=())


def _policy(
    *,
    tenant: str = TENANT,
    schemas: frozenset[str] = frozenset({PRODUCT_CLASS}),
    roles: frozenset[str] = frozenset({ROLE}),
) -> ProductEntitlementPolicy:
    return ProductEntitlementPolicy(
        tenant_id=tenant,
        policy_version=POLICY_VERSION,
        principals={
            PRINCIPAL: ProductEntitlementGrant(
                permitted_schema_names=schemas, permitted_roles=roles
            )
        },
    )


def _registry_with(
    policy: ProductEntitlementPolicy, *, tenant: str = TENANT
) -> ControlPlaneRegistry:
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=tenant),
        policy,
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return registry


def _source(
    registry: ControlPlaneRegistry,
) -> ControlPlaneProductEntitlementSource:
    return ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: NOW
    )


def _authz_events(
    registry: ControlPlaneRegistry,
) -> list[AuthzDecisionAuditEvent]:
    return [
        event
        for event in registry.audit_log.events()
        if isinstance(event, AuthzDecisionAuditEvent)
        and event.authz_action_id == ACTION_PRODUCT_RETRIEVE
    ]


# --- the seams are Protocols the SDK does not own the shape of --------------


def test_both_door_seams_are_runtime_checkable_protocols() -> None:
    """A deployment substitutes by conforming, never by subclassing.

    What would fail here: either seam becoming a base class, at which point a
    deployment's own resolver would have to inherit the SDK's opinion about
    where a role comes from (CLAUDE.md §11).
    """

    class Resolver:
        def __call__(
            self, *, grant: TokenGrant, tenant: str, requested_role: str | None
        ) -> Perspective:  # pragma: no cover - structural conformance only
            return Perspective(principal_id=grant.client_id, role=ROLE)

    assert isinstance(Resolver(), PerspectiveResolverProtocol)
    assert isinstance(
        _source(_registry_with(_policy())), ProductEntitlementSourceProtocol
    )


# --- the reference source: resolve per call, decide, audit both outcomes ----


def test_an_entitled_principal_receives_its_grant_and_the_allow_is_audited() -> (
    None
):
    """The allow leg exists, and it leaves a trace (D-09/D-10).

    What would fail here: a source that audited only refusals, which is the
    half an examiner reading "who received this class?" needs most.
    """
    registry = _registry_with(_policy())
    in_force, _ = registry.resolve_latest(
        product_entitlement_key(tenant_id=TENANT)
    )

    entitled = _source(registry).authorize(
        grant=_grant(), tenant=TENANT, product_class=PRODUCT_CLASS, role=ROLE
    )

    assert entitled.permitted_schema_names == frozenset({PRODUCT_CLASS})
    events = _authz_events(registry)
    assert len(events) == 1
    assert events[0].resolved is True
    assert events[0].actor == PRINCIPAL
    assert events[0].key == TENANT
    # The *registry* version in force, not the artifact's own declared lane:
    # ``register_typed`` versions by content address, and what an examiner
    # needs on the record is the exact artifact that decided, which is the
    # address (D-04/D-07). A policy edited without a lane bump would still
    # move this string; the declared lane would not.
    assert events[0].version == in_force
    assert events[0].artifact_class == PRODUCT_ENTITLEMENT_POLICY.class_id


def test_an_unconfigured_principal_is_refused_and_the_deny_is_audited() -> None:
    """A caller the deployment never declared is a refusal, never a blank grant.

    What would fail here: ``grant_for`` softened to a permissive default —
    exactly the bypass plan 15.5-03 made unexpressible on the artifact.
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        _source(registry).authorize(
            grant=_grant(STRANGER),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            role=ROLE,
        )

    assert refused.value.error_code == ERROR_PRINCIPAL_NOT_ENTITLED
    events = _authz_events(registry)
    assert len(events) == 1
    assert events[0].resolved is False
    assert events[0].actor == STRANGER


def test_a_principal_entitled_to_another_class_is_refused_by_class() -> None:
    """Entitlement is per class, and the refusal names which one (T-15.5-20).

    What would fail here: a door that checked only that the principal exists,
    which is authentication wearing an entitlement's name.
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        _source(registry).authorize(
            grant=_grant(),
            tenant=TENANT,
            product_class=OTHER_PRODUCT_CLASS,
            role=ROLE,
        )

    assert refused.value.error_code == ERROR_PRODUCT_CLASS_UNENTITLED
    assert OTHER_PRODUCT_CLASS in str(refused.value)
    assert _authz_events(registry)[0].resolved is False


def test_a_role_outside_the_grant_is_refused_by_role() -> None:
    """A caller cannot be served a view conditioned on a role nobody granted.

    What would fail here: ``require_role`` never reached, which is the whole
    of T-15.5-19 on the door side.
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        _source(registry).authorize(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            role=OTHER_ROLE,
        )

    assert refused.value.error_code == ERROR_PRODUCT_ROLE_UNGRANTED
    assert _authz_events(registry)[0].resolved is False


def test_a_tenant_with_no_registered_policy_is_refused_not_served() -> None:
    """No policy is a deny, never an open door (T-15.5-21).

    What would fail here: a source that treated an absent artifact as "nothing
    to enforce", which is how a misconfigured deployment ships wide open.
    """
    registry = ControlPlaneRegistry()

    with pytest.raises(ProductEntitlementRefused) as refused:
        _source(registry).authorize(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            role=ROLE,
        )

    assert refused.value.error_code == ERROR_PRODUCT_POLICY_ABSENT
    events = _authz_events(registry)
    assert len(events) == 1
    assert events[0].resolved is False
    assert events[0].version == ""


def test_a_near_miss_artifact_is_audited_as_a_deny_before_it_raises() -> None:
    """WR-04, transplanted: a misregistered policy still leaves a trace.

    What would fail here: the wiring error raised first, so the exact
    misconfiguration window an examiner cares about is the one with no record.
    """
    registry = ControlPlaneRegistry()
    registry.register(product_entitlement_key(tenant_id=TENANT), {"not": "a policy"})

    with pytest.raises(TypeError):
        _source(registry).authorize(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            role=ROLE,
        )

    events = _authz_events(registry)
    assert len(events) == 1
    assert events[0].resolved is False


def test_a_policy_declaring_another_tenant_is_refused_under_this_tenants_key() -> None:
    """The key and the artifact's own ``tenant_id`` are compared, not assumed.

    ``ProductEntitlementPolicy`` documents itself as *"tenant-scoped by
    construction … not by convention"*, but the key
    (:func:`product_entitlement_key`) and the ``tenant_id`` field are supplied
    **independently** by whoever registers the policy, and nothing upstream
    binds them. Without the door's own comparison, a policy whose content says
    ``OTHER_TENANT`` — registered, whether by wiring error or by an attacker
    with Control Plane write — authorizes ``TENANT``'s door with
    ``OTHER_TENANT``'s grants, and every downstream refusal leg passes because
    the *principal* and the *schema* match.

    What would fail here: dropping the comparison at
    ``ControlPlaneProductEntitlementSource.authorize``. The near-miss posture
    is shared with the wrong-artifact-type leg above — audited as a deny first
    (WR-04), then raised rather than refused, because a misregistered policy is
    a deployment fact and not a statement about this caller.

    Found by the Phase 15.5 close-time cross-AI panel
    (`15.5-CLOSE-REVIEWS.md`, finding P1).
    """
    registry = _registry_with(_policy(tenant=OTHER_TENANT), tenant=TENANT)

    with pytest.raises(TypeError, match=OTHER_TENANT):
        _source(registry).authorize(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            role=ROLE,
        )

    events = _authz_events(registry)
    assert len(events) == 1
    assert events[0].resolved is False

    # The control: the identical policy under its *own* tenant's key is served.
    permitted = _registry_with(_policy(tenant=OTHER_TENANT), tenant=OTHER_TENANT)
    assert _source(permitted).authorize(
        grant=_grant(),
        tenant=OTHER_TENANT,
        product_class=PRODUCT_CLASS,
        role=ROLE,
    )


def test_the_policy_is_re_resolved_on_every_call_with_no_cache(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-07: a version change takes effect on the next call, not the next boot.

    What would fail here: a source that read the artifact once at construction.
    The second call would then decide against a policy the deployment has
    already replaced (T-15.5-24).
    """
    registry = _registry_with(_policy())
    source = _source(registry)

    assert source.authorize(
        grant=_grant(), tenant=TENANT, product_class=PRODUCT_CLASS, role=ROLE
    )

    registry.register_typed(
        product_entitlement_key(tenant_id=TENANT),
        _policy(schemas=frozenset({OTHER_PRODUCT_CLASS})),
        PRODUCT_ENTITLEMENT_POLICY,
    )

    with pytest.raises(ProductEntitlementRefused):
        source.authorize(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            role=ROLE,
        )


def test_one_tenants_entitlement_never_decides_for_another() -> None:
    """D-IMPL-05 at the door: the key derivation carries the tenant.

    What would fail here: a source that resolved one key for every tenant, at
    which point one tenant's grant would serve its principal under another.
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        _source(registry).authorize(
            grant=_grant(),
            tenant=OTHER_TENANT,
            product_class=PRODUCT_CLASS,
            role=ROLE,
        )

    assert refused.value.error_code == ERROR_PRODUCT_POLICY_ABSENT


def test_a_refusal_carries_the_one_refusal_body_shape() -> None:
    """The typed code is the contract; the prose is human context (D-08).

    What would fail here: a free-text refusal, which every consumer would then
    have to parse — the finding ``http_api/errors.py`` exists to close.
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        _source(registry).authorize(
            grant=_grant(),
            tenant=TENANT,
            product_class=OTHER_PRODUCT_CLASS,
            role=ROLE,
        )

    assert refused.value.error_code in str(refused.value)
    assert isinstance(refused.value, ProductEntitlementViolation)


# --- the shared resolution order every door runs ----------------------------


def _resolver(role: str, *, principal: str | None = None):
    def resolve(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(
            principal_id=principal if principal is not None else grant.client_id,
            role=requested_role if requested_role is not None else role,
        )

    return resolve


def test_the_door_returns_a_perspective_carrying_the_granted_role() -> None:
    """The happy path: verified identity in, conditioned view out.

    What would fail here: a door that returned the caller's claim untouched.
    """
    registry = _registry_with(_policy())

    perspective = entitled_perspective(
        grant=_grant(),
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        requested_role=None,
        entitlement_source=_source(registry),
        perspective_resolver=_resolver(ROLE),
    )

    assert perspective == Perspective(principal_id=PRINCIPAL, role=ROLE)


def test_a_resolver_that_mints_an_ungranted_role_is_refused() -> None:
    """The resolver may propose; the entitlement decides (T-15.5-19).

    What would fail here: checking only the *requested* role. A resolver that
    ignored its argument would then hand the engine a role nobody granted, and
    the whole perspective seam would be a suggestion box.
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        entitled_perspective(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            requested_role=None,
            entitlement_source=_source(registry),
            perspective_resolver=_resolver(OTHER_ROLE),
        )

    assert refused.value.error_code == ERROR_PRODUCT_ROLE_UNGRANTED


def test_a_resolver_that_substitutes_a_principal_is_refused() -> None:
    """The subject is the verified identity, never a resolver's choice.

    What would fail here: a perspective whose ``principal_id`` came from
    anywhere but the verified grant, which lands verbatim in replay dimension
    4 and would make the record name someone who never called (D-IMPL-67).
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        entitled_perspective(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            requested_role=None,
            entitlement_source=_source(registry),
            perspective_resolver=_resolver(ROLE, principal=STRANGER),
        )

    assert refused.value.error_code == ERROR_SUBJECT_CONFLICT


def test_a_requested_role_outside_the_grant_is_refused() -> None:
    """A caller may ask; asking is not receiving.

    What would fail here: the requested role threaded to the engine without
    ever meeting ``require_role``.
    """
    registry = _registry_with(_policy())

    with pytest.raises(ProductEntitlementRefused) as refused:
        entitled_perspective(
            grant=_grant(),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            requested_role=OTHER_ROLE,
            entitlement_source=_source(registry),
            perspective_resolver=_resolver(ROLE),
        )

    assert refused.value.error_code == ERROR_PRODUCT_ROLE_UNGRANTED


def test_the_door_refuses_before_it_would_have_served() -> None:
    """Refusal precedes resolution, so a refused caller moves no fabric.

    What would fail here: a door that assembled first and filtered after,
    which is the shape that leaks through timing and through logs even when
    the body never ships.
    """
    registry = _registry_with(_policy())
    reached: list[str] = []

    def recording_resolver(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        reached.append(grant.client_id)
        return Perspective(principal_id=grant.client_id, role=ROLE)

    with pytest.raises(ProductEntitlementRefused):
        entitled_perspective(
            grant=_grant(STRANGER),
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            requested_role=None,
            entitlement_source=_source(registry),
            perspective_resolver=recording_resolver,
        )

    # The resolver runs (it is a pure derivation over the verified grant and
    # touches no fabric); what must not have happened is a servable product.
    assert reached == [STRANGER]
    assert _authz_events(registry)[0].resolved is False


# --- the module holds no deployment vocabulary (CINV-01) --------------------


def test_the_door_module_source_holds_no_deployment_vocabulary() -> None:
    """No principal, role, tenant or product-class name lives in the module.

    What would fail here: a default role, a well-known principal, or an
    example tenant hardcoded into mechanism — the defect class CINV-01 exists
    to catch, asserted against the module's own source rather than trusted.
    """
    import inspect

    import ccf_runtime.authz.product_entitlement as module

    source = inspect.getsource(module)
    for forbidden in (TENANT, PRINCIPAL, ROLE, PRODUCT_CLASS, STRANGER):
        assert forbidden not in source
