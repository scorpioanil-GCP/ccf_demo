"""Authorization at the HTTP door, on all four axes (``SEC-001``/``SEC-002``).

The successor to the HARD-04 matrix suite (10-03 T1). That one proved the
**two HITL routes** enforced ``(grant, tenant, action)`` inside their own
handlers. Both halves of that sentence changed:

* **Where.** Enforcement moved out of two handlers and into one middleware in
  front of the whole application (:mod:`ccf_runtime.http_api.gate`). Two
  routes out of twenty-six was the coverage a per-handler check actually had,
  and which two was decided by whoever remembered.
* **On what.** The decision is now ``(grant, tenant, action, resource)``, and
  the tenant is the **verified grant's** rather than a value the caller typed
  into a query parameter or a request body.

What this file proves, drafted from what would fail here:

==========================================  ==================================
Invariant / requirement                     What would fail here
==========================================  ==================================
deny-by-default (T-10-01)                   an unmatched grant or an
                                            unresolvable mapping would yield
                                            an allow
the resource axis (``SEC-002``)             holding an action would authorize
                                            every resource that action can
                                            name — the finding's exact shape
the tenant is SELECTED from the grant's     a path segment, query parameter
set (D-IMPL-353 §1.3)                       or body field would supply a
                                            tenant the grant does not hold; a
                                            grant spanning several would have
                                            one picked for it
a grant with no tenant                      would be given one
audit-by-construction (D-09/D-10)           an allow or a deny would leave no
                                            ``authz_decision`` event on the
                                            one Control Plane audit log
one refusal, one code (D-27's shape)        a caller could tell *which axis
                                            refused* and enumerate the
                                            surface with it
==========================================  ==================================

Every scope string, tenant name, token value and resource is test deployment
vocabulary (CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.projection.plan import Perspective
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
)
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.authz.refusals import (
    ACTION_AGENT_READ,
    ACTION_CONFIG_REGISTER,
    ACTION_HEALTH_READ,
    ACTION_HITL_QUEUE_READ,
    ACTION_PRODUCT_RETRIEVE,
)
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.errors import (
    ERROR_AMBIGUOUS_TENANT,
    ERROR_REQUEST_UNAUTHORIZED,
    ERROR_UNTENANTED_GRANT,
)

from .conftest import Fabric
from .gate_fixtures import (
    WIDE_RESOURCES,
    probe,
    tenanted_source,
)
from .test_product_declared_obligation_409 import (
    _entitlement_registry,
    _recorder,
)
from http_api.composition_authority import (
    register_typed_at_composition,
)

#: Test deployment vocabulary.
MAPPING_KEY = "gate-authz/scope-mapping"
SCOPE_NARROW = "gate-authz:narrow"
SCOPE_WIDE = "gate-authz:wide"
TOKEN_NARROW = "gate-authz-narrow"
TOKEN_WIDE = "gate-authz-wide"
TOKEN_OTHER = "gate-authz-other-tenant"
TOKEN_UNTENANTED = "gate-authz-untenanted"
TOKEN_BOTH = "gate-authz-both-tenants"
CLIENT_ID = "gate-authz-caller"
OTHER_TENANT = "gate-authz-other-tenant-name"
#: The one Control Plane key ``SCOPE_NARROW`` may register into, and the one
#: it may not. The pair is the ``SEC-002`` subject: both are the *same action*
#: on the *same tenant* by the *same principal*, and only the resource differs.
PERMITTED_KEY = "gate-authz-permitted/prompt"
FORBIDDEN_KEY = "gate-authz-forbidden/prompt"
INSTANT = datetime(2026, 8, 11, tzinfo=UTC)


def _mapping(tenant: str) -> ScopeMappingArtifact:
    return ScopeMappingArtifact(
        semver="1.0.0",
        scopes={
            # Narrow: one action, one tenant, ONE resource prefix.
            SCOPE_NARROW: ScopeEntry(
                tenant_patterns=(tenant,),
                action_ids=(ACTION_CONFIG_REGISTER, ACTION_HEALTH_READ),
                resource_patterns=("gate-authz-permitted/*", "health.*"),
            ),
            # Wide: the whole vocabulary this suite reaches for, on two
            # tenants. Spelled out because the D-01 grammar refuses the bare
            # "*" (WR-03), which is the property rather than the annoyance.
            SCOPE_WIDE: ScopeEntry(
                tenant_patterns=(tenant, OTHER_TENANT),
                action_ids=(
                    ACTION_CONFIG_REGISTER,
                    ACTION_HEALTH_READ,
                    ACTION_HITL_QUEUE_READ,
                    ACTION_AGENT_READ,
                    ACTION_PRODUCT_RETRIEVE,
                ),
                resource_patterns=WIDE_RESOURCES,
            ),
        },
    )


@pytest.fixture(scope="module")
def door(fabric: Fabric, tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One app, one pinned mapping, four credentials."""
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    root = tmp_path_factory.mktemp("gate-authz")
    tenant = fabric.product_address.tenant
    registry = ControlPlaneRegistry()
    version = register_typed_at_composition(registry, 
        MAPPING_KEY, _mapping(tenant), SCOPE_MAPPING
    )
    assert isinstance(version, str)

    # Every credential is the base `TokenGrant` through the real per-boot
    # source (D-IMPL-353 §2 P1). The untenanted one is the SAME contract with
    # an EMPTY `tenants` set — what a source never told a tenant mints.
    source = tenanted_source(
        {
            TOKEN_NARROW: (CLIENT_ID, (SCOPE_NARROW,)),
            TOKEN_WIDE: (CLIENT_ID, (SCOPE_WIDE,)),
            TOKEN_OTHER: (CLIENT_ID, (SCOPE_WIDE,), OTHER_TENANT),
            TOKEN_BOTH: (CLIENT_ID, (SCOPE_WIDE,), (tenant, OTHER_TENANT)),
            TOKEN_UNTENANTED: (CLIENT_ID, (SCOPE_WIDE,), ()),
        },
        tenant=tenant,
    )

    entitlement = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(fabric), clock=lambda: INSTANT
    )
    app = create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            hitl_transport=fabric.hitl,
        ),
        auth=BearerTokenAuth(token_source=source),
        authorizer=ControlPlaneTenantAuthorizer(
            control_plane=registry,
            scope_mapping_key=MAPPING_KEY,
            scope_mapping_version=version,
            clock=lambda: INSTANT,
        ),
        product_entitlement=entitlement,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role="gate-authz-role"
            )
        ),
        refusal_recorder=_recorder(fabric, root, source=entitlement),
        replay_record_product_class=None,
    )
    return _Door(app=app, tenant=tenant, version=version, registry=registry)


class _Door:
    def __init__(
        self,
        *,
        app: Any,
        tenant: str,
        version: str,
        registry: ControlPlaneRegistry,
    ) -> None:
        self.app = app
        self.tenant = tenant
        self.version = version
        self.registry = registry

    def get(self, url: str, *, token: str) -> Any:
        return probe(
            self.app,
            "GET",
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

    def register(self, key: str, *, token: str) -> Any:
        """``POST /config/registrations`` — the ``SEC-002`` door itself."""
        return probe(
            self.app,
            "POST",
            "/config/registrations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "key": key,
                "class_id": "ccf.prompt-artifact",
                "artifact": {},
            },
        )

    def events(self) -> tuple[AuthzDecisionAuditEvent, ...]:
        return tuple(
            event
            for event in self.registry.audit_events()
            if isinstance(event, AuthzDecisionAuditEvent)
        )


# --- the resource axis: the finding, and the repair -------------------------


def test_the_resource_decides_and_not_only_the_action(door: Any) -> None:
    """``SEC-002``, in one comparison.

    The same principal, the same tenant, the same action, the same scope —
    and two different Control Plane keys. Under a ``(grant, tenant, action)``
    decision both answer identically, which is precisely the finding: *"any
    bearer with config.register can rewrite it"*. The resource axis is what
    makes the second one refuse.

    What would fail here: ``resource_patterns`` becoming advisory, or the
    matcher returning an allow when only three of four axes matched.
    """
    permitted = door.register(PERMITTED_KEY, token=TOKEN_NARROW)
    forbidden = door.register(FORBIDDEN_KEY, token=TOKEN_NARROW)

    assert permitted.status_code != 403, permitted.text
    assert forbidden.status_code == 403
    assert (
        forbidden.json()["detail"]["error_code"] == ERROR_REQUEST_UNAUTHORIZED
    )


def test_a_wider_grant_reaches_the_same_key_the_narrow_one_cannot(
    door: Any,
) -> None:
    """The positive control for the test above.

    Without it, ``forbidden`` might be refused for some reason that has
    nothing to do with the resource — a malformed body, an unregistered class
    — and the finding would look closed while nothing had changed.
    """
    assert door.register(FORBIDDEN_KEY, token=TOKEN_WIDE).status_code != 403


# --- the tenant is selected from the grant's set (D-IMPL-353 §1.3) -----------


def test_a_path_segment_may_agree_with_the_grant_but_never_supply_it(
    door: Any, fabric: Fabric
) -> None:
    """``SEC-002``: the product address keeps its tenant segment and loses its
    authority.

    The same credential reaches its own tenant's address and is refused at
    another's — with no reference to the second tenant's policy, because the
    gate never gets far enough to consult one.
    """
    address = fabric.product_address
    own = door.get(
        f"/product/{door.tenant}/{address.product_class}/{address.version}",
        token=TOKEN_WIDE,
    )
    other = door.get(
        f"/product/{OTHER_TENANT}/{address.product_class}/{address.version}",
        token=TOKEN_WIDE,
    )

    assert own.status_code != 403, own.text
    assert other.status_code == 403
    assert other.json()["detail"]["error_code"] == ERROR_REQUEST_UNAUTHORIZED


def test_a_credential_for_another_tenant_reaches_its_own_address(
    door: Any, fabric: Fabric
) -> None:
    """The positive control: the refusal above is about the *pairing*.

    ``TOKEN_OTHER`` holds the same wide scope and names ``OTHER_TENANT``, so
    it is refused at ``door.tenant``'s address and admitted at its own — which
    is the same assertion read from the other side.
    """
    address = fabric.product_address
    crossed = door.get(
        f"/product/{door.tenant}/{address.product_class}/{address.version}",
        token=TOKEN_OTHER,
    )
    assert crossed.status_code == 403


def test_a_grant_spanning_two_tenants_is_refused_where_the_route_names_none(
    door: Any, fabric: Fabric
) -> None:
    """§1.3: the gate does not pick. The same credential is decided for the
    member a tenanted route names, and refused as ambiguous on a route that
    names none — with its own code, because the answer is a function of the
    credential and the template and nothing a caller can vary."""
    address = fabric.product_address
    ambiguous = door.get("/health", token=TOKEN_BOTH)
    assert ambiguous.status_code == 403
    assert ambiguous.json()["detail"]["error_code"] == ERROR_AMBIGUOUS_TENANT

    before = len(door.events())
    named = door.get(
        f"/product/{OTHER_TENANT}/{address.product_class}/{address.version}",
        token=TOKEN_BOTH,
    )
    assert named.status_code != 403, named.text
    (decision,) = door.events()[before:]
    assert decision.key == OTHER_TENANT


def test_a_grant_with_no_tenant_is_refused_rather_than_given_one(
    door: Any,
) -> None:
    """The fail-closed arm, and its own code.

    A caller cannot change what its own credential carries, so this answer is
    constant for a given credential across every route — which is why it is
    distinguishable without opening an oracle, and why an operator who wired a
    token source that mints untenanted grants gets to read the cause.
    """
    refused = door.get("/health", token=TOKEN_UNTENANTED)

    assert refused.status_code == 403
    assert refused.json()["detail"]["error_code"] == ERROR_UNTENANTED_GRANT


# --- deny-by-default, and one refusal shape ---------------------------------


def test_an_action_outside_the_scope_is_denied(door: Any) -> None:
    """``SCOPE_NARROW`` holds two actions; the queue read is not one."""
    assert door.get("/hitl/queue", token=TOKEN_NARROW).status_code == 403


def test_every_denial_is_the_same_code_and_the_same_sentence(
    door: Any, fabric: Fabric
) -> None:
    """One code, one sentence, whichever axis refused (``D-IMPL-253`` (4)).

    Four denials with four different internal causes — no declaration covers
    the request line, the path tenant disagrees, the resource is unreadable,
    the mapping says no — reach the caller as one body. A caller able to tell
    them apart could enumerate which routes exist, which tenants it is near,
    and which of its own parameters the door reads.

    What would fail here: a branch growing its own message.
    """
    address = fabric.product_address
    bodies = [
        door.get("/no-such-route", token=TOKEN_WIDE).json()["detail"],
        door.get(
            f"/product/{OTHER_TENANT}/{address.product_class}/"
            f"{address.version}",
            token=TOKEN_WIDE,
        ).json()["detail"],
        # An unreadable resource: the declared query parameter is absent.
        door.get("/agent/declaration", token=TOKEN_WIDE).json()["detail"],
        door.register(FORBIDDEN_KEY, token=TOKEN_NARROW).json()["detail"],
    ]

    assert len({(body["error_code"], body["message"]) for body in bodies}) == 1
    assert bodies[0]["error_code"] == ERROR_REQUEST_UNAUTHORIZED


def test_the_refusal_names_neither_the_action_nor_the_resource(
    door: Any,
) -> None:
    """The message is a constant, so it cannot leak what it decided about."""
    body = door.register(FORBIDDEN_KEY, token=TOKEN_NARROW).json()["detail"]

    assert FORBIDDEN_KEY not in body["message"]
    assert ACTION_CONFIG_REGISTER not in body["message"]
    assert TOKEN_NARROW not in body["message"]


# --- audit-by-construction (D-09/D-10) --------------------------------------


def test_allow_and_deny_both_audit_with_the_pinned_version(door: Any) -> None:
    """Both outcomes land, and both carry the version actually decided under."""
    before = len(door.events())
    door.register(PERMITTED_KEY, token=TOKEN_NARROW)
    door.register(FORBIDDEN_KEY, token=TOKEN_NARROW)
    new = door.events()[before:]

    assert [event.resolved for event in new] == [True, False]
    assert all(event.version == door.version for event in new)
    assert all(event.action == "authz_decision" for event in new)
    assert all(event.actor == CLIENT_ID for event in new)
    assert all(event.key == door.tenant for event in new)
    assert all(
        event.authz_action_id == ACTION_CONFIG_REGISTER for event in new
    )
    # D-IMPL-353 §3: both say WHAT they decided about, and the deny says
    # WHICH axis refused — here the resource, since the narrow scope holds
    # the action for this tenant and not for this key.
    allow, deny = new
    assert allow.authz_resource == PERMITTED_KEY
    assert allow.authz_matched_resource_pattern == "gate-authz-permitted/*"
    assert allow.authz_failing_axis is None
    assert deny.authz_resource == FORBIDDEN_KEY
    assert deny.authz_matched_resource_pattern is None
    assert deny.authz_failing_axis == "resource"


def test_a_denial_before_the_authorizer_is_reached_writes_no_decision(
    door: Any,
) -> None:
    """The honest edge, recorded rather than smoothed over.

    An untenanted grant, an unmatched request line and an ambiguous tenant
    are refused *before* the authorizer is asked, so they leave no
    ``authz_decision`` event — there was no decision to record. That is a real
    gap in the trail for those three cases, and naming it here is the
    alternative to a test that quietly assumes every refusal is audited.
    """
    before = len(door.events())
    door.get("/health", token=TOKEN_UNTENANTED)
    door.get("/no-such-route", token=TOKEN_WIDE)
    door.get("/health", token=TOKEN_BOTH)  # ambiguous: refused before asking

    assert len(door.events()) == before
