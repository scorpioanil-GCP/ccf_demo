"""The reference tenant authorizer (10-01 Task 3; HARD-04; D-IMPL-68).

What this suite proves, drafted from what would fail here:

==========================================  ==================================
Invariant / requirement                     What would fail here
==========================================  ==================================
deny-by-default (T-10-01)                   an unmatched grant, an empty
                                            grant, or an unregistered mapping
                                            would yield an allow
per-call re-resolution (D-07; T-10-02)      a v2 registration between two
                                            calls would not change the
                                            decided artifact version
audit-by-construction (D-09/D-10; T-10-03)  an allow or a deny would leave no
                                            ``authz_decision`` event in the
                                            one Control Plane audit log
typed resolution (D-03)                     a wrong-class artifact under the
                                            key would be interpreted instead
                                            of refused
==========================================  ==================================

Every scope string, tenant name, and mapping value is test fixture data
(CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
)
from ccf_runtime.authz.protocol import (
    AuthzDecision,
    ControlPlaneTenantAuthorizer,
    TenantAuthorizerProtocol,
)
from ccf_runtime.authz.refusals import (
    ACTION_HITL_ACTION_SUBMIT,
    ACTION_HITL_QUEUE_READ,
)
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED
from ccf_runtime.mcp.auth import TokenGrant

MAPPING_KEY = "test/scope-mapping"
SCOPE = "test:hitl"
CLIENT = "caller-1"
INSTANT = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)


def _clock() -> datetime:
    return INSTANT


def _registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry(clock=_clock)


def _mapping(
    *, patterns: tuple[str, ...] = ("tenant-*",),
    action_ids: tuple[str, ...] = (ACTION_HITL_QUEUE_READ,),
    semver: str = "1.0.0",
) -> ScopeMappingArtifact:
    return ScopeMappingArtifact(
        semver=semver,
        scopes={
            SCOPE: ScopeEntry(
                tenant_patterns=patterns, action_ids=action_ids
            )
        },
    )


def _authorizer(
    registry: ControlPlaneRegistry,
) -> ControlPlaneTenantAuthorizer:
    return ControlPlaneTenantAuthorizer(
        control_plane=registry, scope_mapping_key=MAPPING_KEY, clock=_clock
    )


def _grant(*scopes: str) -> TokenGrant:
    return TokenGrant(client_id=CLIENT, scopes=scopes)


def _authz_events(
    registry: ControlPlaneRegistry,
) -> tuple[AuthzDecisionAuditEvent, ...]:
    return tuple(
        event
        for event in registry.audit_events()
        if isinstance(event, AuthzDecisionAuditEvent)
    )


# --- allow -------------------------------------------------------------------


def test_a_matching_grant_is_allowed_and_audited() -> None:
    registry = _registry()
    version = registry.register_typed(MAPPING_KEY, _mapping(), SCOPE_MAPPING)
    authorizer = _authorizer(registry)

    decision = authorizer.authorize(
        grant=_grant(SCOPE),
        tenant="tenant-a",
        action_id=ACTION_HITL_QUEUE_READ,
    )

    assert decision == AuthzDecision(
        allowed=True,
        matched_scope_pattern="tenant-*",
        artifact_version=version,
        action_id=ACTION_HITL_QUEUE_READ,
        tenant="tenant-a",
    )
    (event,) = _authz_events(registry)
    assert event.action == "authz_decision"
    assert event.resolved is True
    assert event.key == "tenant-a"
    assert event.version == version
    assert event.actor == CLIENT
    assert event.authz_action_id == ACTION_HITL_QUEUE_READ
    assert event.authz_matched_pattern == "tenant-*"
    assert event.occurred_at == INSTANT


# --- deny-by-default (T-10-01) ----------------------------------------------


@pytest.mark.parametrize(
    ("grant_scopes", "tenant", "action_id"),
    [
        ((SCOPE,), "other-tenant", ACTION_HITL_QUEUE_READ),  # tenant mismatch
        ((SCOPE,), "tenant-a", ACTION_HITL_ACTION_SUBMIT),  # action mismatch
        (("some:other",), "tenant-a", ACTION_HITL_QUEUE_READ),  # scope absent
        ((), "tenant-a", ACTION_HITL_QUEUE_READ),  # empty grant
    ],
)
def test_an_unmatched_grant_is_denied_and_audited(
    grant_scopes: tuple[str, ...], tenant: str, action_id: str
) -> None:
    from ccf_runtime.authz.artifact import SCOPE_MAPPING

    registry = _registry()
    version = registry.register_typed(MAPPING_KEY, _mapping(), SCOPE_MAPPING)
    authorizer = _authorizer(registry)

    decision = authorizer.authorize(
        grant=_grant(*grant_scopes), tenant=tenant, action_id=action_id
    )

    assert decision == AuthzDecision(
        allowed=False,
        matched_scope_pattern=None,
        artifact_version=version,
        action_id=action_id,
        tenant=tenant,
    )
    (event,) = _authz_events(registry)
    assert event.resolved is False
    assert event.authz_matched_pattern is None
    assert event.version == version


def test_no_registered_mapping_denies_by_default_and_still_audits() -> None:
    registry = _registry()
    authorizer = _authorizer(registry)

    decision = authorizer.authorize(
        grant=_grant(SCOPE),
        tenant="tenant-a",
        action_id=ACTION_HITL_QUEUE_READ,
    )

    assert decision.allowed is False
    assert decision.matched_scope_pattern is None
    (event,) = _authz_events(registry)
    assert event.resolved is False
    assert event.authz_action_id == ACTION_HITL_QUEUE_READ


# --- per-call re-resolution (D-07) -------------------------------------------


def test_the_artifact_is_re_resolved_on_every_call() -> None:
    """Registering v2 between two calls changes the decided artifact
    version without reconstructing the authorizer (D-07; T-10-02)."""
    from ccf_runtime.authz.artifact import SCOPE_MAPPING

    registry = _registry()
    v1 = registry.register_typed(MAPPING_KEY, _mapping(), SCOPE_MAPPING)
    authorizer = _authorizer(registry)

    first = authorizer.authorize(
        grant=_grant(SCOPE),
        tenant="tenant-a",
        action_id=ACTION_HITL_QUEUE_READ,
    )
    v2 = registry.register_typed(
        MAPPING_KEY,
        _mapping(patterns=("tenant-a",), semver="2.0.0"),
        SCOPE_MAPPING,
    )
    second = authorizer.authorize(
        grant=_grant(SCOPE),
        tenant="tenant-a",
        action_id=ACTION_HITL_QUEUE_READ,
    )

    assert first.artifact_version == v1
    assert second.artifact_version == v2
    assert v1 != v2
    assert second.allowed is True
    assert second.matched_scope_pattern == "tenant-a"


def test_a_wrong_class_artifact_under_the_key_is_a_type_error() -> None:
    """A near-miss mapping under the key is refused, never interpreted."""
    registry = _registry()
    registry.register(MAPPING_KEY, {"semver": "1.0.0", "scopes": {}})
    authorizer = _authorizer(registry)

    with pytest.raises(TypeError):
        authorizer.authorize(
            grant=_grant(SCOPE),
            tenant="tenant-a",
            action_id=ACTION_HITL_QUEUE_READ,
        )


# --- seam shape --------------------------------------------------------------


def test_the_reference_impl_conforms_to_the_protocol() -> None:
    registry = _registry()
    assert isinstance(_authorizer(registry), TenantAuthorizerProtocol)


def test_the_shared_constants_exist_for_both_doors() -> None:
    """D-02/D-08: door-declared action IDs and the one refusal code are
    shared vocabulary, declared once."""
    assert ACTION_HITL_QUEUE_READ == "hitl.queue.read"
    assert ACTION_HITL_ACTION_SUBMIT == "hitl.action.submit"
    assert ERROR_TENANT_UNAUTHORIZED == "tenant-unauthorized"
