"""The reference tenant authorizer (10-01 Task 3; HARD-04; D-IMPL-68).

What this suite proves, drafted from what would fail here:

==========================================  ==================================
Invariant / requirement                     What would fail here
==========================================  ==================================
deny-by-default (T-10-01)                   an unmatched grant, an empty
                                            grant, or an unregistered mapping
                                            would yield an allow
version pinning (``SEC-002``)               a v2 registration between two
                                            calls would change the decided
                                            artifact version, letting a
                                            bearer who can register artifacts
                                            re-issue the policy that
                                            authorizes it
resource axis (``SEC-002``)                 an action would authorize every
                                            resource it can name
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
#: The resource these tests decide about — test fixture vocabulary.
RESOURCE = "test-resource-1"
CLIENT = "caller-1"
INSTANT = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)


def _clock() -> datetime:
    return INSTANT


def _registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry(clock=_clock)


def _mapping(
    *, patterns: tuple[str, ...] = ("tenant-*",),
    action_ids: tuple[str, ...] = (ACTION_HITL_QUEUE_READ,),
    resource_patterns: tuple[str, ...] = (RESOURCE,),
    semver: str = "1.0.0",
) -> ScopeMappingArtifact:
    return ScopeMappingArtifact(
        semver=semver,
        scopes={
            SCOPE: ScopeEntry(
                tenant_patterns=patterns,
                action_ids=action_ids,
                resource_patterns=resource_patterns,
            )
        },
    )


def _authorizer(
    registry: ControlPlaneRegistry, *, version: str
) -> ControlPlaneTenantAuthorizer:
    return ControlPlaneTenantAuthorizer(
        control_plane=registry,
        scope_mapping_key=MAPPING_KEY,
        scope_mapping_version=version,
        clock=_clock,
    )


def _decide(
    authorizer: ControlPlaneTenantAuthorizer,
    *,
    scopes: tuple[str, ...] = (SCOPE,),
    tenant: str = "tenant-a",
    action_id: str = ACTION_HITL_QUEUE_READ,
    resource: str = RESOURCE,
) -> AuthzDecision:
    return authorizer.authorize(
        grant=_grant(*scopes),
        tenant=tenant,
        action_id=action_id,
        resource=resource,
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
    assert isinstance(version, str)
    authorizer = _authorizer(registry, version=version)

    decision = _decide(authorizer)

    assert decision == AuthzDecision(
        allowed=True,
        matched_scope_pattern="tenant-*",
        matched_resource_pattern=RESOURCE,
        artifact_version=version,
        action_id=ACTION_HITL_QUEUE_READ,
        tenant="tenant-a",
        resource=RESOURCE,
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
    ("grant_scopes", "tenant", "action_id", "resource"),
    [
        # tenant mismatch
        ((SCOPE,), "other-tenant", ACTION_HITL_QUEUE_READ, RESOURCE),
        # action mismatch
        ((SCOPE,), "tenant-a", ACTION_HITL_ACTION_SUBMIT, RESOURCE),
        # scope absent
        (("some:other",), "tenant-a", ACTION_HITL_QUEUE_READ, RESOURCE),
        # empty grant
        ((), "tenant-a", ACTION_HITL_QUEUE_READ, RESOURCE),
        # `SEC-002`: everything matches EXCEPT the resource. Without the
        # fourth axis this leg is an allow, which is the finding.
        ((SCOPE,), "tenant-a", ACTION_HITL_QUEUE_READ, "another-resource"),
    ],
)
def test_an_unmatched_grant_is_denied_and_audited(
    grant_scopes: tuple[str, ...], tenant: str, action_id: str, resource: str
) -> None:
    from ccf_runtime.authz.artifact import SCOPE_MAPPING

    registry = _registry()
    version = registry.register_typed(MAPPING_KEY, _mapping(), SCOPE_MAPPING)
    assert isinstance(version, str)
    authorizer = _authorizer(registry, version=version)

    decision = _decide(
        authorizer,
        scopes=grant_scopes,
        tenant=tenant,
        action_id=action_id,
        resource=resource,
    )

    assert decision.allowed is False
    assert decision.artifact_version == version
    assert decision.action_id == action_id
    assert decision.tenant == tenant
    assert decision.resource == resource
    assert decision.matched_resource_pattern is None
    (event,) = _authz_events(registry)
    assert event.resolved is False
    assert event.version == version


def test_two_narrow_entries_never_compose_into_a_wide_one() -> None:
    """``SEC-002``: ONE scope entry has to satisfy every axis.

    What would fail here: a matcher that returned the first tenant hit and the
    first resource hit found across *different* entries. Scope A reaches
    tenant-a for resource-a; scope B reaches tenant-b for resource-b; a grant
    holding both would then authorize tenant-a × resource-b, which neither
    entry states.
    """
    registry = _registry()
    version = registry.register_typed(
        MAPPING_KEY,
        ScopeMappingArtifact(
            semver="1.0.0",
            scopes={
                "scope:a": ScopeEntry(
                    tenant_patterns=("tenant-a",),
                    action_ids=(ACTION_HITL_QUEUE_READ,),
                    resource_patterns=("resource-a",),
                ),
                "scope:b": ScopeEntry(
                    tenant_patterns=("tenant-b",),
                    action_ids=(ACTION_HITL_QUEUE_READ,),
                    resource_patterns=("resource-b",),
                ),
            },
        ),
        SCOPE_MAPPING,
    )
    assert isinstance(version, str)
    authorizer = _authorizer(registry, version=version)

    crossed = authorizer.authorize(
        grant=_grant("scope:a", "scope:b"),
        tenant="tenant-a",
        action_id=ACTION_HITL_QUEUE_READ,
        resource="resource-b",
    )
    intended = authorizer.authorize(
        grant=_grant("scope:a", "scope:b"),
        tenant="tenant-a",
        action_id=ACTION_HITL_QUEUE_READ,
        resource="resource-a",
    )

    assert crossed.allowed is False
    assert intended.allowed is True


def test_nothing_at_the_pinned_version_denies_and_still_audits() -> None:
    registry = _registry()
    authorizer = _authorizer(registry, version="no-such-version")

    decision = _decide(authorizer)

    assert decision.allowed is False
    assert decision.matched_scope_pattern is None
    assert decision.matched_resource_pattern is None
    (event,) = _authz_events(registry)
    assert event.resolved is False
    assert event.authz_action_id == ACTION_HITL_QUEUE_READ


# --- per-call re-resolution (D-07) -------------------------------------------


def test_a_later_registration_does_not_change_the_decided_version() -> None:
    """``SEC-002``: the pin is what closes the re-issue escalation.

    This test is the **inverse** of the D-07 per-call-``resolve_latest``
    behavior it replaces, and deliberately so. Under that behavior a bearer
    who could register Control Plane artifacts could register a wider scope
    mapping and have it in force on its very next request — the policy that
    authorizes you being writable by you. The pin means a later registration
    is inert until somebody re-constructs the authorizer, which is a redeploy
    rather than a request.

    What would fail here: ``resolve_latest`` coming back, under any spelling.
    """
    from ccf_runtime.authz.artifact import SCOPE_MAPPING

    registry = _registry()
    v1 = registry.register_typed(MAPPING_KEY, _mapping(), SCOPE_MAPPING)
    assert isinstance(v1, str)
    authorizer = _authorizer(registry, version=v1)

    first = _decide(authorizer, tenant="tenant-a")
    # A WIDER mapping, registered after the authorizer was built: it reaches
    # a tenant v1 does not, under the same scope and action.
    v2 = registry.register_typed(
        MAPPING_KEY,
        _mapping(patterns=("tenant-*", "escalated-*"), semver="2.0.0"),
        SCOPE_MAPPING,
    )
    second = _decide(authorizer, tenant="escalated-1")

    assert v1 != v2
    assert first.artifact_version == v1
    assert second.artifact_version == v1
    assert second.allowed is False, (
        "a mapping registered after construction reached a decision; the pin"
        " is not holding (SEC-002)"
    )


def test_the_authorizer_never_calls_resolve_latest() -> None:
    """Structural, not stylistic: a registry whose ``resolve_latest`` explodes.

    What would fail here: any path back to last-registered-wins. The replay
    engine has banned ``resolve_latest`` since ``D-IMPL-26`` for the same
    reason — a pin that can be resolved to *whatever is newest* is not a pin.
    """
    from ccf_runtime.authz.artifact import SCOPE_MAPPING

    registry = _registry()
    version = registry.register_typed(MAPPING_KEY, _mapping(), SCOPE_MAPPING)
    assert isinstance(version, str)

    def explode(key: str) -> tuple[str, object]:
        raise AssertionError(
            f"the authz path resolved {key!r} as latest (SEC-002)"
        )

    object.__setattr__(registry, "resolve_latest", explode)
    authorizer = _authorizer(registry, version=version)

    assert _decide(authorizer).allowed is True


@pytest.mark.parametrize(
    ("key", "version"), [("", "1"), (MAPPING_KEY, "")]
)
def test_an_empty_pin_is_refused_at_construction(
    key: str, version: str
) -> None:
    """A pin discovered on the first request is a pin nobody set."""
    with pytest.raises(ValueError):
        ControlPlaneTenantAuthorizer(
            control_plane=_registry(),
            scope_mapping_key=key,
            scope_mapping_version=version,
            clock=_clock,
        )


def _near_miss() -> tuple[ControlPlaneRegistry, ControlPlaneTenantAuthorizer]:
    registry = _registry()
    version = registry.register(
        MAPPING_KEY, {"semver": "1.0.0", "scopes": {}}
    )
    assert isinstance(version, str)
    return registry, _authorizer(registry, version=version)


def test_a_wrong_class_artifact_under_the_key_is_a_type_error() -> None:
    """A near-miss mapping under the key is refused, never interpreted."""
    _registry_, authorizer = _near_miss()

    with pytest.raises(TypeError):
        _decide(authorizer)


def test_a_near_miss_artifact_still_audits_the_attempt() -> None:
    """WR-04: the authorization *attempt* leaves an ``authz_decision``
    deny trace before the near-miss wiring error is raised — the
    misconfiguration window is exactly where the attempt log matters."""
    registry, authorizer = _near_miss()

    with pytest.raises(TypeError):
        _decide(authorizer)

    (event,) = _authz_events(registry)
    assert event.action == "authz_decision"
    assert event.resolved is False
    assert event.key == "tenant-a"
    assert event.actor == CLIENT
    assert event.authz_action_id == ACTION_HITL_QUEUE_READ
    assert event.authz_matched_pattern is None
    assert event.occurred_at == INSTANT


# --- seam shape --------------------------------------------------------------


def test_the_reference_impl_conforms_to_the_protocol() -> None:
    assert isinstance(
        _authorizer(_registry(), version="1"), TenantAuthorizerProtocol
    )


def test_the_shared_constants_exist_for_both_doors() -> None:
    """D-02/D-08: door-declared action IDs and the one refusal code are
    shared vocabulary, declared once."""
    assert ACTION_HITL_QUEUE_READ == "hitl.queue.read"
    assert ACTION_HITL_ACTION_SUBMIT == "hitl.action.submit"
    assert ERROR_TENANT_UNAUTHORIZED == "tenant-unauthorized"
