"""The MCP action door refuses a verdict on a decided gate with ``hitl-gate-closed`` (D-IMPL-378).

When a resumption decides a gate, the HITL transport records the gate's closure
in the same atomic step that judges its verdicts, and from then on refuses a
verdict on that suspension
(``src/ccf/hitl/transport.py::HITLTransportProtocol.close_gate``). The HTTP
door answers that refusal with 409 ``hitl-gate-closed``
(``tests/http_api/test_approval_gate_limits_door.py``). This module pins the
MCP door's half: ``submit_hitl_action`` over the REAL transport raises the
refusal body carrying the same code
(``runtime/ccf_runtime/http_api/errors.py::ERROR_HITL_GATE_CLOSED``), and
nothing is recorded. The positive control shows the same door, credential and
officer recording a verdict while the gate is still open, so the refusal is
the closure's and not the composition's.

The bodies are exercised through the guarded callable ``FastMCP`` holds, with
the verified token put in context the way the sibling MCP suites do
(``tests/mcp/test_sec005_attestation_door.py``). Test vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AnyHttpUrl, AuthSettings

import ccf_runtime.mcp.hitl_server as hitl_server
import ccf_runtime.mcp.tenancy as tenancy
from ccf.authz.capability import Authorized, HitlQueueRead, HitlSubmit
from ccf.hitl.principal import AUTHENTICATION_CLAIM, AuthenticationClaims
from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport, PendingHitlEvent
from ccf_runtime.http_api.errors import ERROR_HITL_GATE_CLOSED
from ccf_runtime.mcp.auth import (
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
    tenant_claims,
)
from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL, build_hitl_server
from ccf_runtime.workflow.engine import WorkflowCompleted
from http_api.gate_fixtures import SCOPE_EVERYTHING, wide_authorizer
from tests.workflow import test_engine as eh
from tests.workflow.test_resume_single_flight import plane

TENANT = "acme-bank"
#: Eligible under the covenant gate's policy
#: (``tests/fixtures/banking/approval_policies.yaml``), and not the starter.
APPROVER = "officer-1"
LATE_OFFICER = "officer-2"
EXECUTION = "mcp-gate-closed"
CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://acme-bank/dev-token-file",
    method="bearer-token",
    assurance_level="aal3",
    session_ref="mcp-gate-closed-session",
)


def _grant() -> TokenGrant:
    return TokenGrant(
        client_id=LATE_OFFICER,
        scopes=(SCOPE_EVERYTHING,),
        tenants=frozenset({TENANT}),
        authentication=CLAIMS,
    )


def _tool(transport: InMemoryHitlTransport, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The MCP submit tool over the REAL transport, as ``LATE_OFFICER``."""

    def queue_view(authorized: Authorized[HitlQueueRead]) -> tuple[PendingHitlEvent, ...]:
        return transport.view(authorized)

    def action_route(authorized: Authorized[HitlSubmit], *, submission: HitlActionSubmission) -> str:
        recorded = transport.submit(authorized, submission=submission)
        return json.dumps(recorded.model_dump(mode="json"))

    server = build_hitl_server(
        server_name="mcp-gate-closed-door",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(source=StaticTokenSource(grants={"unit-token": _grant()})),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=[SCOPE_EVERYTHING],
        ),
        authorizer=wide_authorizer(tenant=TENANT, key="mcp-gate-closed/mapping"),
        clock=lambda: datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
    )
    token = AccessToken(
        token="unit-token",
        client_id=LATE_OFFICER,
        scopes=[SCOPE_EVERYTHING],
        claims={**tenant_claims(_grant()), AUTHENTICATION_CLAIM: CLAIMS.model_dump(mode="json")},
    )
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)
    return server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn


def _call(tool: Any, *, event_key: str, bound: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """``(recorded, refusal)`` for one rejection submitted through the MCP door."""
    try:
        result = tool(
            tenant=TENANT,
            event_key=event_key,
            action="reject",
            product_content_hash=bound,
            annotation=None,
            attestation=None,
        )
    except ValueError as error:
        return None, json.loads(str(error))
    return json.loads(result), None


def test_a_verdict_on_a_decided_gate_is_refused_at_the_mcp_door(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = plane()
    engine, transport, workflow, event_key, bound = eh._suspended_covenant(
        registry, tmp_path, execution_id=EXECUTION
    )
    eh._submit_only(
        transport, tenant=TENANT, event_key=event_key, product_content_hash=bound,
        action="approve", subject_id=APPROVER,
    )
    outcome = asyncio.run(
        engine.resume(eh.resume_as(workflow), workflow, execution_id=EXECUTION, decision="approved")
    )
    assert isinstance(outcome, WorkflowCompleted), outcome
    before = transport.submissions(tenant=TENANT)

    recorded, refusal = _call(_tool(transport, monkeypatch), event_key=event_key, bound=bound)

    assert recorded is None, recorded
    assert refusal is not None and refusal["error_code"] == ERROR_HITL_GATE_CLOSED, refusal
    assert transport.submissions(tenant=TENANT) == before, "the refused verdict was recorded"


def test_the_same_verdict_on_an_open_gate_is_recorded_at_the_mcp_door(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control: no resumption has decided the gate, so the same
    officer's rejection through the same door is recorded against the open
    gate — the door, the credential and the eligibility all admit it."""
    registry = plane()
    _, transport, _, event_key, bound = eh._suspended_covenant(
        registry, tmp_path, execution_id=EXECUTION
    )
    recorded, refusal = _call(_tool(transport, monkeypatch), event_key=event_key, bound=bound)
    assert refusal is None, refusal
    assert recorded is not None and recorded["event_state_at_submit"] == "pending", recorded
    assert recorded["principal"]["approver"]["subject_id"] == LATE_OFFICER
