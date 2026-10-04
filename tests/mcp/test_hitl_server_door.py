"""The MCP HITL door under D-IMPL-353 §2 P4 and P6.

* **P4** — the bodies hold no authorizer: the builder's ``authorizer`` and
  ``clock`` have no defaults, the source has no ``authorizer is None`` arm,
  and the tool's wire schema carries no ``authorized`` (the wrapper injects
  it) and no binding field.
* **P6** — the binding is minted by the door from the capability's
  principal, the verified token's :class:`~ccf.hitl.principal.AuthenticationClaims`
  and the injected clock; a caller-typed ``assurance_level`` is not a
  parameter the tool has, so it is a ``TypeError`` at the boundary rather
  than a refusal; a token carrying no claims is refused with the shared
  ``ERROR_AUTHENTICATION_UNATTESTED`` code; and the queue resource reads the
  capability's tenant.
* **`D-IMPL-363`** — what the human signs is their own
  :class:`~ccf.hitl.identity_binding.HitlActionClaims`, carried as ONE
  ``attestation`` object parameter (C12(a)), which is what the tool's exact
  wire schema is pinned to here. Verification itself is exercised against the
  real transport in ``tests/mcp/test_sec005_attestation_door.py``; this suite
  keeps its recording stub.

The bodies are exercised through the guarded callables ``FastMCP`` holds
(``tool.fn`` / ``template.fn``), with the verified token put in context the
way the sibling MCP suites do (both namespaces that read it are patched).
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from typing import Any

import pytest
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AnyHttpUrl, AuthSettings
from mcp.server.fastmcp import FastMCP

import ccf_runtime.mcp.hitl_server as hitl_server
import ccf_runtime.mcp.tenancy as tenancy
from ccf.authz.capability import (
    Authorized,
    HitlQueueRead,
    HitlSubmit,
    verify,
)
from ccf.hitl.principal import AUTHENTICATION_CLAIM, AuthenticationClaims
from ccf.hitl.transport import HitlActionSubmission, PendingHitlEvent
from ccf_runtime.identity_binding import ERROR_AUTHENTICATION_UNATTESTED
from ccf_runtime.mcp.auth import (
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
    tenant_claims,
)
from ccf_runtime.mcp.hitl_server import (
    HITL_QUEUE_URI_TEMPLATE,
    SUBMIT_HITL_ACTION_TOOL,
    build_hitl_server,
)

from http_api.gate_fixtures import SCOPE_EVERYTHING, wide_authorizer

TENANT = "mcp-door-tenant"
CLIENT_ID = "mcp-door-auditor"
SCOPE = SCOPE_EVERYTHING  # the one scope the wide mapping grants
CLOCK_TIME = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
VALID_HASH = "d" * 64
CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://acme-bank/dev-token-file",
    method="bearer-token",
    assurance_level="aal3",
    session_ref="mcp-door-session",
)


def _grant(*, claims: AuthenticationClaims | None) -> TokenGrant:
    return TokenGrant(
        client_id=CLIENT_ID,
        scopes=(SCOPE,),
        tenants=frozenset({TENANT}),
        authentication=claims,
    )


def _token(*, claims: AuthenticationClaims | None) -> AccessToken:
    grant = _grant(claims=claims)
    extra = {} if claims is None else {AUTHENTICATION_CLAIM: claims.model_dump(mode="json")}
    return AccessToken(
        token="unit-token",
        client_id=CLIENT_ID,
        scopes=[SCOPE],
        claims={**tenant_claims(grant), **extra},
    )


def _verified_as(monkeypatch: pytest.MonkeyPatch, token: AccessToken) -> None:
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)


def _server(
    routed: list[tuple[Authorized[HitlSubmit], HitlActionSubmission]],
    viewed: list[Authorized[HitlQueueRead]],
) -> FastMCP:
    def action_route(authorized: Authorized[HitlSubmit], *, submission: HitlActionSubmission) -> str:
        routed.append((authorized, submission))
        return "{}"

    def queue_view(authorized: Authorized[HitlQueueRead]) -> tuple[PendingHitlEvent, ...]:
        viewed.append(authorized)
        return (
            PendingHitlEvent(
                event_key="mcp-door-event",
                event_class="approval-gate",
                tenant=authorized.tenant,
                workflow_state_ref=f"{authorized.tenant}/exec-1",
                product_content_hash=VALID_HASH,
            ),
        )

    return build_hitl_server(
        server_name="mcp-door-hitl",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(grants={"unit-token": _grant(claims=CLAIMS)})
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=wide_authorizer(tenant=TENANT, key="mcp-door/mapping"),
        clock=lambda: CLOCK_TIME,
    )


def _arguments(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "tenant": TENANT,
        "event_key": "mcp-door-event",
        "action": "approve",
        "product_content_hash": VALID_HASH,
    }
    arguments.update(overrides)
    return arguments


# --- P4 -------------------------------------------------------------------------


def test_p4_the_builder_requires_the_authorizer_and_clock_and_the_bodies_have_no_none_arm() -> None:
    parameters = inspect.signature(build_hitl_server).parameters
    assert parameters["authorizer"].default is inspect.Parameter.empty
    assert parameters["clock"].default is inspect.Parameter.empty
    source = inspect.getsource(hitl_server)
    assert "authorizer is None" not in source
    assert "_enforce_tenant_authz" not in source
    assert "TenantAuthorizerProtocol | None" not in source


def test_the_tool_schema_carries_no_binding_field_and_no_capability() -> None:
    """The wire schema is the `HitlActionRequest` field set plus the tenant
    segment, and nothing else (P6; `D-IMPL-363` C12(a)).

    Under `D-IMPL-363` the two detached-signature parameters
    (``signed_binding_signature`` / ``signed_binding_key_id``) are replaced by
    ONE ``attestation`` object in the same shape as the HTTP body's, so the
    exact set changes while the property does not: no field the door mints is
    a parameter a caller can supply.
    """
    server = _server([], [])
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL)
    assert tool is not None
    properties = set(tool.parameters["properties"])
    assert properties == {
        "tenant",
        "event_key",
        "action",
        "product_content_hash",
        "annotation",
        "attestation",
    }
    for minted in (
        "authorized",
        "subject_id",
        "identity_provider_ref",
        "method",
        "assurance_level",
        "session_ref",
        "action_time",
        # Replaced, not deprecated (`D-IMPL-363`): the two-parameter detached
        # signature is gone from this surface rather than accepted beside the
        # attestation.
        "signed_binding_signature",
        "signed_binding_key_id",
    ):
        assert minted not in properties
    # The attestation is an optional OBJECT on the wire (C12(a)) — not the
    # pair of strings it replaced, which is what makes the set change a shape
    # change rather than a rename.
    attestation = tool.parameters["properties"]["attestation"]
    assert {"type": "object", "additionalProperties": True} in [
        {key: arm[key] for key in ("type", "additionalProperties") if key in arm}
        for arm in attestation["anyOf"]
    ], attestation
    assert {"type": "null"} in attestation["anyOf"], attestation


# --- P6 -------------------------------------------------------------------------


def test_p6_the_binding_is_minted_from_capability_claims_and_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routed: list[tuple[Authorized[HitlSubmit], HitlActionSubmission]] = []
    server = _server(routed, [])
    _verified_as(monkeypatch, _token(claims=CLAIMS))
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn
    tool(**_arguments())
    ((authorized, submission),) = routed
    verify(authorized, kind=HitlSubmit, resource="mcp-door-event")  # genuine, this event
    assert authorized.tenant == TENANT
    assert authorized.principal == CLIENT_ID
    principal = submission.principal
    assert principal.approver.subject_id == CLIENT_ID
    assert principal.approver.identity_provider_ref == CLAIMS.identity_provider_ref
    assert principal.authentication.method == CLAIMS.method
    assert principal.authentication.assurance_level == "aal3"  # the TOKEN's
    assert principal.authentication.session_ref == CLAIMS.session_ref
    assert principal.action_time == CLOCK_TIME
    assert submission.event_key == "mcp-door-event"
    assert "tenant" not in HitlActionSubmission.model_fields


def test_a_caller_typed_assurance_is_unrepresentable_at_the_tool_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routed: list[tuple[Authorized[HitlSubmit], HitlActionSubmission]] = []
    server = _server(routed, [])
    _verified_as(monkeypatch, _token(claims=CLAIMS))
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn
    for minted, value in (
        ("assurance_level", "aal3"),
        ("subject_id", "someone-else"),
        ("action_time", CLOCK_TIME.isoformat()),
        ("authorized", object()),
    ):
        with pytest.raises(TypeError):
            tool(**_arguments(**{minted: value}))
    assert routed == []


def test_an_unattested_token_is_refused_with_the_shared_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routed: list[tuple[Authorized[HitlSubmit], HitlActionSubmission]] = []
    server = _server(routed, [])
    _verified_as(monkeypatch, _token(claims=None))
    tool = server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn
    with pytest.raises(ValueError) as refused:
        tool(**_arguments())
    assert json.loads(str(refused.value))["error_code"] == ERROR_AUTHENTICATION_UNATTESTED
    assert routed == []


def test_the_queue_resource_reads_the_capabilitys_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    viewed: list[Authorized[HitlQueueRead]] = []
    server = _server([], viewed)
    _verified_as(monkeypatch, _token(claims=CLAIMS))
    (template,) = [
        template
        for template in server._resource_manager.list_templates()
        if template.uri_template == HITL_QUEUE_URI_TEMPLATE
    ]
    body = json.loads(template.fn(tenant=TENANT))
    (authorized,) = viewed
    verify(authorized, kind=HitlQueueRead, resource=HitlQueueRead.action_id)
    assert authorized.tenant == TENANT
    assert body["tenant"] == TENANT
    assert [event["event_key"] for event in body["events"]] == ["mcp-door-event"]
