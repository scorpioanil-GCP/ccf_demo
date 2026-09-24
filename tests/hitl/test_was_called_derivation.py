"""R1 was-called derivation assertions (08-03 Task 3; 07-REVIEWS R1).

The R1 finding (Cursor, LOW): the HTTP happy-path proved *subject
equality*, not the derivation call — a regression that kept the 403
conflict check but passed the caller's body principal through on match
(skipping ``principal_from_token_grant``) would still have passed every
prior test; the MCP door's guard was similarly weak
(``inspect.getsource`` contains the name). These tests close R1 with
monkeypatch **wrapping** of the derivation (wrap, don't replace — the
real derivation still runs, so downstream contract assertions hold) and
call-count assertions on both named seams:

* the HTTP door (``ccf_runtime.http_api.routes.hitl``) — derivation IS
  invoked on the auth-bound path, and its return value IS the recorded
  principal (identity, not mere equality);
* the MCP door (``ccf_runtime.mcp.hitl_server``) — same assertion for
  the D-IMPL-20 primary authority channel.

And the negative guard, restated for the posture that replaced the one it
was written against (``SEC-002``): ``create_app`` no longer has an
unauthenticated arm, so *"the derivation is not called from a ``None``
grant"* can no longer be staged by building a door with no auth hook. The
same fact now has a stronger witness — a credential-less request is refused
by the total gate before any handler runs, so the derivation is not reached
at all and nothing lands on the transport.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf_runtime.http_api.errors import (
    ERROR_UNAUTHENTICATED,
    ERROR_UNTENANTED_GRANT,
)

from http_api.conftest import Fabric, call
from http_api.gate_fixtures import SCOPE_EVERYTHING

_VALID_HASH = "c" * 64
_AWARE_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
_TOKEN = "derivation-token"
#: The tenant the MCP leg acts on. One spelling, so the credential's scope
#: and the tool argument cannot drift apart (`SEC-018`).
_MCP_TENANT = "was-called-mcp-tenant"

_CLIENT_ID = "derivation-auditor-1"
_ROLE = "was-called-role"


def _submission_body(*, subject_id: str, tenant: str) -> dict[str, Any]:
    return {
        "event_key": "derivation-event-1",
        "tenant": tenant,
        "action": "approve",
        "principal": {
            "approver": {
                "subject_id": subject_id,
                "identity_provider_ref": "idp://acme-bank/dev-token-file",
            },
            "authentication": {
                "method": "bearer-token",
                "assurance_level": "dev",
                "session_ref": "derivation-session-1",
            },
            "action_time": _AWARE_TIME.isoformat(),
            "product_content_hash": _VALID_HASH,
        },
        "annotation": None,
    }


@pytest.fixture(scope="module")
def fabric(tmp_path_factory: pytest.TempPathFactory) -> Fabric:
    return Fabric(tmp_path_factory.mktemp("was-called"))


#: The tenant the HTTP leg acts on. It is the GRANT's, and the body field of
#: the same name may only agree with it (``SEC-002``): ``tenant :=
#: grant.tenant`` has no second clause, so one spelling here keeps the
#: credential and the submission from drifting apart.
_HTTP_TENANT = "was-called-auth-tenant"

#: This suite's own scope-mapping key, entitlement registry and credential
#: table. A borrowed policy decides about a borrowed vocabulary and fails on
#: refusal kinds that have nothing to do with the derivation seam. The scope
#: STRING is `authority`'s own — its wide mapping keys on that single name —
#: so it is imported rather than invented here.
_MAPPING_KEY = "was-called/scope-mapping"
_GRANTS: dict[str, tuple[object, ...]] = {
    _TOKEN: (_CLIENT_ID, (SCOPE_EVERYTHING,), _HTTP_TENANT),
}


def _seams(fabric: Fabric, root: Path) -> dict[str, Any]:
    """Everything ``create_app`` requires, with this suite's credentials.

    Built through :func:`~http_api.gate_fixtures.authority` rather than seam
    by seam: five separately-built seams are five chances to build a
    permissive one, and none of the five is this module's subject.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.entitlement import (
        PRODUCT_ENTITLEMENT_POLICY,
        ProductEntitlementGrant,
        ProductEntitlementPolicy,
        product_entitlement_key,
    )
    from ccf.products.resolver import ReplayRefusalRecorder
    from ccf.projection.plan import Perspective
    from ccf_runtime.authz.product_entitlement import (
        ControlPlaneProductEntitlementSource,
    )

    from http_api.gate_fixtures import authority

    address = fabric.product_address
    entitlements = ControlPlaneRegistry()
    entitlements.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version="1.0.0",
            principals={
                _CLIENT_ID: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({_ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=entitlements, clock=lambda: _AWARE_TIME
    )
    return authority(
        tenant=(_HTTP_TENANT, address.tenant),
        key=_MAPPING_KEY,
        grants=_GRANTS,
        product_entitlement=source,
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=_ROLE
            )
        ),
        refusal_recorder=ReplayRefusalRecorder(
            artifact_store=FileArtifactStore(root=root / "artifacts"),
            replay_record_class="ccf.decision-replay-record",
            tenant_id=address.tenant,
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=source.disclosure_level_for,
        ),
    )


def _deps(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return ApiDependencies(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=fabric.hitl,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
    )


class _WrapCounter:
    """Wrap-and-count spy: the real derivation still runs (R1 discipline)."""

    def __init__(self, real: Any) -> None:
        self._real = real
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []
        self.returns: list[Any] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.call_count += 1
        self.calls.append(kwargs)
        result = self._real(**kwargs)
        self.returns.append(result)
        return result


# --- Test 1: auth-bound HTTP path actually derives --------------------------


def test_http_auth_bound_path_invokes_the_derivation(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app

    spy = _WrapCounter(hitl_routes.principal_from_token_grant)
    monkeypatch.setattr(
        hitl_routes, "principal_from_token_grant", spy
    )
    # The dev ``FileTokenSource`` mints a grant carrying no tenant, which
    # every door now refuses (``SEC-002``), so the credential comes from the
    # tenanted table instead. What the test asserts is unchanged.
    app = create_app(_deps(fabric), **_seams(fabric, tmp_path))
    tenant = _HTTP_TENANT
    response = call(
        app,
        "POST",
        "/hitl/actions",
        json=_submission_body(subject_id=_CLIENT_ID, tenant=tenant),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
    assert response.status_code == 200
    # The derivation WAS called — with the verified grant, exactly once.
    assert spy.call_count == 1
    assert spy.calls[0]["grant"].client_id == _CLIENT_ID
    # The recorded principal IS the derivation's return value — object
    # identity, not a value that merely equals it (the R1 regression a
    # pass-through-on-match would have hidden).
    (recorded,) = fabric.hitl.submissions(tenant=tenant)
    assert recorded.principal is spy.returns[0]


# --- Test 2: no credential never reaches the derivation ---------------------


def test_a_credentialless_request_never_reaches_the_derivation(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No credential: refused at the gate, so no derivation and nothing lands.

    **Rewritten for the posture that replaced the one it asserted**
    (``SEC-002``). The predecessor built ``create_app(deps,
    acknowledge_insecure_default=True)`` — an application with no auth hook —
    sent an anonymous submission, and asserted that it returned ``200`` with
    the caller's own body subject recorded verbatim. Every clause of that is
    now false by design: the keyword is deleted, the five authority seams are
    required, and a pure-ASGI gate refuses every request that carries no
    recognised credential before any handler runs.

    The finding the old shape asserted was ``T-07-24``'s *unbound default*,
    which is the ``SEC-002`` defect itself — a door whose authentication the
    deployment could decline. What survives is the claim the test was written
    for: the derivation is never fed a ``None`` grant. It now has a stronger
    witness than a spy count on a permissive app, because there is no arm in
    which an ungranted request reaches the route at all.
    """
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app

    from http_api.gate_fixtures import probe

    spy = _WrapCounter(hitl_routes.principal_from_token_grant)
    monkeypatch.setattr(
        hitl_routes, "principal_from_token_grant", spy
    )
    app = create_app(_deps(fabric), **_seams(fabric, tmp_path))
    tenant = "was-called-unauth-tenant"
    # `probe`, not `call`: `call` supplies the suite's credential, and a
    # helper that adds one cannot witness what happens to a request without.
    response = probe(
        app,
        "POST",
        "/hitl/actions",
        json=_submission_body(subject_id="as-sent-subject", tenant=tenant),
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == ERROR_UNAUTHENTICATED
    # Not reached: neither the derivation nor the transport behind it.
    assert spy.call_count == 0
    assert fabric.hitl.submissions(tenant=tenant) == ()


def test_an_untenanted_grant_is_refused_before_the_derivation(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recognised credential naming no tenant is refused, not defaulted.

    The other half of the same posture change, and the one the dev
    ``FileTokenSource`` still produces: authentication succeeds, so the old
    ``None``-grant question does not arise, but ``tenant := grant.tenant``
    has nothing to read. The door refuses with its own code rather than
    picking a tenant for the deployment — a server-side spelling of the
    caller-supplied tenant ``SEC-002`` names — and the derivation is again
    never reached.
    """
    import ccf_runtime.http_api.routes.hitl as hitl_routes
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.mcp.auth import FileTokenSource

    from http_api.gate_fixtures import probe

    spy = _WrapCounter(hitl_routes.principal_from_token_grant)
    monkeypatch.setattr(
        hitl_routes, "principal_from_token_grant", spy
    )
    path = tmp_path / "dev-tokens.json"
    path.write_text(
        json.dumps(
            {_TOKEN: {"client_id": _CLIENT_ID, "scopes": [SCOPE_EVERYTHING]}}
        ),
        encoding="utf-8",
    )
    seams = _seams(fabric, tmp_path)
    seams["auth"] = BearerTokenAuth(token_source=FileTokenSource(path=path))
    app = create_app(_deps(fabric), **seams)
    tenant = "was-called-untenanted-tenant"
    response = probe(
        app,
        "POST",
        "/hitl/actions",
        json=_submission_body(subject_id=_CLIENT_ID, tenant=tenant),
        headers={"Authorization": f"Bearer {_TOKEN}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == ERROR_UNTENANTED_GRANT
    assert spy.call_count == 0
    assert fabric.hitl.submissions(tenant=tenant) == ()


# --- Test 3: the MCP door's derivation seam (R1 names it too) ---------------


def test_mcp_door_invokes_the_derivation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mcp.server.auth.provider import AccessToken
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    import ccf_runtime.mcp.hitl_server as hitl_server
    from ccf.hitl.transport import HitlActionSubmission, PendingHitlEvent
    from ccf_runtime.mcp.auth import (
        FileTokenSource,
        SourceBackedTokenVerifier,
    )
    from ccf_runtime.mcp.hitl_server import (
        SUBMIT_HITL_ACTION_TOOL,
        build_hitl_server,
    )

    spy = _WrapCounter(hitl_server.principal_from_token_grant)
    monkeypatch.setattr(
        hitl_server, "principal_from_token_grant", spy
    )
    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
            {"unit-token": {"client_id": _CLIENT_ID, "scopes": ["h"]}}
        ),
        encoding="utf-8",
    )
    routed: list[HitlActionSubmission] = []

    def action_route(*, submission: HitlActionSubmission) -> str:
        routed.append(submission)
        return "{}"

    def queue_view(*, tenant: str) -> tuple[PendingHitlEvent, ...]:
        return ()

    server = build_hitl_server(
        server_name="was-called-hitl",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=token_file)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=["h"],
        ),
    )
    # BOTH readers of the verified identity: the door, for its subject
    # binding, and `ccf_runtime.mcp.tenancy`, for the tenancy floor installed
    # at registration. Each imported the name into its own namespace, so one
    # patch leaves the other reading the real (empty) context (`SEC-018`).
    import ccf_runtime.mcp.tenancy as tenancy

    from ccf_runtime.mcp.auth import TokenGrant, tenant_claims

    _token = AccessToken(
        token="unit-token",
        client_id=_CLIENT_ID,
        scopes=["h"],
        claims=dict(
            tenant_claims(
                TokenGrant(
                    client_id=_CLIENT_ID,
                    scopes=("h",),
                    tenants=frozenset({_MCP_TENANT}),
                )
            )
        ),
    )
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: _token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: _token)
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn
    tool(
        tenant=_MCP_TENANT,
        event_key="derivation-event-1",
        action="approve",
        subject_id=_CLIENT_ID,
        identity_provider_ref="idp://acme-bank/dev-token-file",
        method="bearer-token",
        assurance_level="dev",
        session_ref="derivation-session-1",
        action_time=_AWARE_TIME.isoformat(),
        product_content_hash=_VALID_HASH,
    )
    assert spy.call_count == 1
    assert spy.calls[0]["grant"].client_id == _CLIENT_ID
    (submission,) = routed
    assert submission.principal is spy.returns[0]
