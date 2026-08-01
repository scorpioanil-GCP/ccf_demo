"""HTTP-door tenant authorization — the HARD-04 matrix legs (10-03 T1).

TDD RED for plan 10-03 Task 1. When ``create_app`` binds BOTH an auth hook
and a tenant authorizer (D-06), the two HITL routes enforce per-tenant
authorization inside their handlers (Pitfall 1 — never a blanket router
``Depends``): ``GET /hitl/queue`` with the ``tenant`` query param under
``hitl.queue.read``, ``POST /hitl/actions`` with ``submission.tenant``
under ``hitl.action.submit``. A deny is a typed 403 carrying
``ERROR_TENANT_UNAUTHORIZED`` — deny-by-default (T-10-01/T-10-10) — and a
refused submit never touches the transport. Both outcomes land on the one
Control Plane audit log with the exact artifact version (T-10-12; D-09/
D-10). Authorizer unbound => posture byte-identical to today.

Every scope string, tenant name, and token value is test deployment
vocabulary (CINV-01).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.authz.artifact import (
    SCOPE_MAPPING,
    ScopeEntry,
    ScopeMappingArtifact,
)
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.authz.refusals import (
    ACTION_HITL_ACTION_SUBMIT,
    ACTION_HITL_QUEUE_READ,
)
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED
from ccf_runtime.mcp.auth import FileTokenSource

from .conftest import Fabric, call

MAPPING_KEY = "authz-http/scope-mapping"
EMPTY_MAPPING_KEY = "authz-http/empty-scope-mapping"
SCOPE_EXACT = "authz:hitl-exact"
SCOPE_PREFIX = "authz:hitl-prefix"
TOKEN_FULL = "authz-http-token-full"
TOKEN_BARE = "authz-http-token-bare"
CLIENT_ID = "authz-http-caller-1"
_VALID_HASH = "d" * 64
_AWARE_TIME = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _submission_body(tenant: str) -> dict[str, Any]:
    principal = HumanPrincipalBinding(
        approver=ApproverIdentity(
            subject_id=CLIENT_ID,
            identity_provider_ref="idp://acme-bank/dev-token-file",
        ),
        authentication=AuthenticationContext(
            method="bearer-token",
            assurance_level="dev",
            session_ref="authz-session-1",
        ),
        action_time=_AWARE_TIME,
        product_content_hash=_VALID_HASH,
    )
    return {
        "event_key": "authz-event-1",
        "tenant": tenant,
        "action": "approve",
        "principal": principal.model_dump(mode="json"),
        "annotation": None,
        "signed_binding": None,
    }


@pytest.fixture(scope="module")
def token_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("authz-http") / "tokens.json"
    path.write_text(
        json.dumps(
            {
                TOKEN_FULL: {
                    "client_id": CLIENT_ID,
                    "scopes": [SCOPE_EXACT, SCOPE_PREFIX],
                },
                TOKEN_BARE: {"client_id": CLIENT_ID, "scopes": []},
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture(scope="module")
def mapping_version(fabric: Fabric) -> str:
    version = fabric.registry.register_typed(
        MAPPING_KEY,
        ScopeMappingArtifact(
            semver="1.0.0",
            scopes={
                SCOPE_EXACT: ScopeEntry(
                    tenant_patterns=("tenant-a",),
                    action_ids=(
                        ACTION_HITL_QUEUE_READ,
                        ACTION_HITL_ACTION_SUBMIT,
                    ),
                ),
                SCOPE_PREFIX: ScopeEntry(
                    tenant_patterns=("tenant-b-*",),
                    action_ids=(ACTION_HITL_QUEUE_READ,),
                ),
            },
        ),
        SCOPE_MAPPING,
    )
    fabric.registry.register_typed(
        EMPTY_MAPPING_KEY,
        ScopeMappingArtifact(semver="1.0.0", scopes={}),
        SCOPE_MAPPING,
    )
    assert isinstance(version, str)
    return version


@pytest.fixture(scope="module")
def transport() -> InMemoryHitlTransport:
    return InMemoryHitlTransport()


def _build_app(
    fabric: Fabric,
    token_file: Path,
    transport: InMemoryHitlTransport,
    *,
    mapping_key: str | None,
    with_auth: bool = True,
) -> Any:
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.http_api.dependencies import ApiDependencies

    deps = ApiDependencies(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=transport,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
    )
    authorizer = None
    if mapping_key is not None:
        authorizer = ControlPlaneTenantAuthorizer(
            control_plane=fabric.registry,
            scope_mapping_key=mapping_key,
            clock=fabric.clock,
        )
    return create_app(
        deps,
        auth=(
            BearerTokenAuth(token_source=FileTokenSource(path=token_file))
            if with_auth
            else None
        ),
        authorizer=authorizer,
        # The auth-unbound legs are posture regressions, not warning
        # tests — acknowledge so the D-IMPL-73 warning stays out of scope.
        acknowledge_insecure_default=not with_auth,
    )


@pytest.fixture(scope="module")
def authz_app(
    fabric: Fabric,
    token_file: Path,
    transport: InMemoryHitlTransport,
    mapping_version: str,
) -> Any:
    return _build_app(fabric, token_file, transport, mapping_key=MAPPING_KEY)


@pytest.fixture(scope="module")
def empty_mapping_app(
    fabric: Fabric,
    token_file: Path,
    transport: InMemoryHitlTransport,
    mapping_version: str,
) -> Any:
    return _build_app(
        fabric, token_file, transport, mapping_key=EMPTY_MAPPING_KEY
    )


def _authz_events(
    fabric: Fabric, *, tenant: str
) -> tuple[AuthzDecisionAuditEvent, ...]:
    return tuple(
        event
        for event in fabric.registry.audit_events()
        if isinstance(event, AuthzDecisionAuditEvent)
        and event.key == tenant
    )


# --- allow legs --------------------------------------------------------------


def test_queue_read_is_allowed_for_an_exactly_scoped_tenant(
    authz_app: Any, fabric: Fabric, mapping_version: str
) -> None:
    response = call(
        authz_app,
        "GET",
        "/hitl/queue",
        params={"tenant": "tenant-a"},
        headers=_auth_header(TOKEN_FULL),
    )
    assert response.status_code == 200
    events = _authz_events(fabric, tenant="tenant-a")
    assert events, "an allow must be audited (D-10)"
    assert events[-1].resolved is True
    assert events[-1].version == mapping_version
    assert events[-1].authz_action_id == ACTION_HITL_QUEUE_READ


def test_queue_read_is_allowed_under_the_prefix_pattern(
    authz_app: Any,
) -> None:
    response = call(
        authz_app,
        "GET",
        "/hitl/queue",
        params={"tenant": "tenant-b-7"},
        headers=_auth_header(TOKEN_FULL),
    )
    assert response.status_code == 200


def test_action_submit_is_allowed_for_the_scoped_tenant(
    authz_app: Any, fabric: Fabric, transport: InMemoryHitlTransport
) -> None:
    response = call(
        authz_app,
        "POST",
        "/hitl/actions",
        json=_submission_body("tenant-a"),
        headers=_auth_header(TOKEN_FULL),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert len(transport.submissions(tenant="tenant-a")) == 1


# --- deny legs (deny-by-default; T-10-01/T-10-10) ---------------------------


@pytest.mark.parametrize(
    ("token", "tenant"),
    [
        (TOKEN_FULL, "tenant-z"),  # no pattern matches this tenant
        (TOKEN_BARE, "tenant-a"),  # grant carries no mapped scope
    ],
)
def test_queue_read_denies_with_the_shared_code(
    authz_app: Any, fabric: Fabric, token: str, tenant: str
) -> None:
    response = call(
        authz_app,
        "GET",
        "/hitl/queue",
        params={"tenant": tenant},
        headers=_auth_header(token),
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == ERROR_TENANT_UNAUTHORIZED
    assert "message" in detail
    events = _authz_events(fabric, tenant=tenant)
    assert events and events[-1].resolved is False


@pytest.mark.parametrize(
    ("token", "tenant"),
    [
        (TOKEN_FULL, "tenant-b-7"),  # prefix scope lacks the submit action
        (TOKEN_BARE, "tenant-a"),  # grant carries no mapped scope
    ],
)
def test_action_submit_denies_and_never_touches_the_transport(
    authz_app: Any,
    fabric: Fabric,
    transport: InMemoryHitlTransport,
    token: str,
    tenant: str,
) -> None:
    before = len(transport.submissions(tenant=tenant))
    response = call(
        authz_app,
        "POST",
        "/hitl/actions",
        json=_submission_body(tenant),
        headers=_auth_header(token),
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == ERROR_TENANT_UNAUTHORIZED
    assert len(transport.submissions(tenant=tenant)) == before
    events = _authz_events(fabric, tenant=tenant)
    assert events and events[-1].resolved is False
    assert events[-1].authz_action_id == ACTION_HITL_ACTION_SUBMIT


def test_an_empty_artifact_denies_everything(empty_mapping_app: Any) -> None:
    response = call(
        empty_mapping_app,
        "GET",
        "/hitl/queue",
        params={"tenant": "tenant-a"},
        headers=_auth_header(TOKEN_FULL),
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == ERROR_TENANT_UNAUTHORIZED


# --- audit completeness (D-09; T-10-12) -------------------------------------


def test_allow_and_deny_both_audit_with_the_artifact_version(
    authz_app: Any, fabric: Fabric, mapping_version: str
) -> None:
    tenant = "tenant-a"
    call(
        authz_app,
        "GET",
        "/hitl/queue",
        params={"tenant": tenant},
        headers=_auth_header(TOKEN_FULL),
    )
    call(
        authz_app,
        "GET",
        "/hitl/queue",
        params={"tenant": tenant},
        headers=_auth_header(TOKEN_BARE),
    )
    events = _authz_events(fabric, tenant=tenant)
    resolved = [event.resolved for event in events[-2:]]
    assert resolved == [True, False]
    assert all(event.version == mapping_version for event in events[-2:])
    assert all(event.action == "authz_decision" for event in events[-2:])


# --- posture regression (D-06; T-07-24) -------------------------------------


def test_authorizer_unbound_leaves_the_routes_open_as_today(
    fabric: Fabric, token_file: Path, transport: InMemoryHitlTransport
) -> None:
    app = _build_app(fabric, token_file, transport, mapping_key=None)
    response = call(
        app,
        "GET",
        "/hitl/queue",
        params={"tenant": "tenant-z"},
        headers=_auth_header(TOKEN_BARE),
    )
    assert response.status_code == 200


def test_authorizer_bound_but_auth_unbound_is_inert(
    fabric: Fabric,
    token_file: Path,
    transport: InMemoryHitlTransport,
    mapping_version: str,
) -> None:
    """D-06: with no auth hook there is no TokenGrant, and enforcement is
    inert — the recorded T-07-24 posture is unchanged."""
    app = _build_app(
        fabric, token_file, transport, mapping_key=MAPPING_KEY, with_auth=False
    )
    response = call(app, "GET", "/hitl/queue", params={"tenant": "tenant-z"})
    assert response.status_code == 200
