"""A held review item is released only on the authorized, target-bound path (round 5, item 3).

**SDK-defined** (CLAUDE.md §8.2). Dave, 2026-10-11 20:19 MST: *"Review release
must use the authorized, target-bound approval path."*

Since ``D-IMPL-353`` :meth:`~ccf.hitl.review_queue.ReviewQueue.release` takes an
``Authorized[HitlSubmit]`` that only a door's gate mints, and a deployment could
not compose that door (cp-15 ``UBO-G12``/``UBO-G13``).
:func:`ccf_runtime.mcp.review_door.open_review_door` composes the standard HITL
door over the deployment's queue. Held here over the real MCP door (ASGI, real
bearer verification), one lifespan:

* a reviewer whose scope reaches THIS item releases it with the item's own
  content hash — the resolution names that reviewer and the item leaves the
  queue;
* the same reviewer echoing another hash is refused by the queue (TOCTOU) and
  the item stays pending;
* a reviewer whose scope reaches only OTHER items is refused by the authorizer
  for this one, and it stays pending — the wrong-target release;
* a reviewer may reject what it may release; a verdict that is neither is
  refused before the queue is touched;
* an unknown credential is refused at the verifier (HTTP 401).
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from mcp.types import TextContent

from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.claims import LineageEntry
from ccf.controlplane.audit import AuditLog
from ccf.hitl.principal import AuthenticationClaims
from ccf.hitl.review_queue import ReviewQueue, ReviewQueueItem, ReviewResolution, ReviewResolutionRefused
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.signal.envelope import SourceIdentity
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL

MODULE = "ccf_runtime.mcp.review_door"
TENANT = "review-door-tenant"
BASE_URL = "http://127.0.0.1:8143"
CLOCK = datetime(2026, 10, 11, 20, 0, tzinfo=UTC)
FINDINGS_SCOPE = "review:findings"
SANCTIONS_SCOPE = "review:sanctions"
FINDINGS_REVIEWER = "reviewer-findings"
SANCTIONS_REVIEWER = "reviewer-sanctions"
FINDINGS_ITEM = "findings/person-1/25.0"
SECOND_FINDINGS_ITEM = "findings/person-2/30.0"
SANCTIONS_ITEM = "sanctions/person-3/SDN-1"
CLAIMS = AuthenticationClaims(
    identity_provider_ref="idp://review-door/fixture", method="password",
    assurance_level="aal2", session_ref="review-door-session",
)
ABSENT = "the SDK provides no review door; a held review item cannot be released on the authorized path"


def _module() -> Any:
    if importlib.util.find_spec(MODULE) is None:
        return None
    return importlib.import_module(MODULE)


def _queue() -> tuple[ReviewQueue, dict[str, Any]]:
    queue = ReviewQueue(transport=InMemoryHitlTransport(), audit=AuditLog(), clock=lambda: CLOCK)
    events = {}
    for key in (FINDINGS_ITEM, SECOND_FINDINGS_ITEM, SANCTIONS_ITEM):
        output_ref = artifact_uri(tenant_id=TENANT, artifact_class="ccf.context-product",
                                  name="fixture.product", artifact_version="a" * 64)
        events[key] = queue.submit_for_review(
            tenant=TENANT, event_key=key, workflow_state_ref=f"{TENANT}/record-1",
            item=ReviewQueueItem(output_ref=output_ref, lineage=(LineageEntry(
                source=SourceIdentity(system_id="fixture"), envelope_id=f"node/{key}", observed_at=CLOCK),)),
        )
    return queue, events


def _door(module: Any, queue: ReviewQueue) -> Any:
    source = StaticTokenSource(grants={
        f"token-{FINDINGS_REVIEWER}": TokenGrant(client_id=FINDINGS_REVIEWER, scopes=(FINDINGS_SCOPE,),
                                                tenants=frozenset({TENANT}), authentication=CLAIMS),
        f"token-{SANCTIONS_REVIEWER}": TokenGrant(client_id=SANCTIONS_REVIEWER, scopes=(SANCTIONS_SCOPE,),
                                                 tenants=frozenset({TENANT}), authentication=CLAIMS),
    })
    return module.open_review_door(
        queue, tenant_id=TENANT, token_verifier=SourceBackedTokenVerifier(source=source),
        reviewer_scopes={FINDINGS_SCOPE: ("findings/*",), SANCTIONS_SCOPE: ("sanctions/*",)},
        clock=lambda: CLOCK,
    )


def _act(door: Any, calls: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    """Each ``(token, arguments)`` as one tool call, all in ONE lifespan."""
    app = door.server(issuer_url="https://issuer.invalid", resource_server_url=f"{BASE_URL}/mcp").streamable_http_app()

    async def go() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        async with app.router.lifespan_context(app):
            for token, arguments in calls:

                async def operation(session: Any, arguments: dict[str, Any] = arguments) -> Any:
                    result = await session.call_tool(SUBMIT_HITL_ACTION_TOOL, arguments)
                    return {"is_error": bool(result.isError),
                            "text": " | ".join(c.text for c in result.content if isinstance(c, TextContent))}

                def factory(token: str = token) -> httpx.AsyncClient:
                    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL,
                                             headers={"Authorization": f"Bearer {token}"})

                try:
                    out.append(await run_with_session(url=f"{BASE_URL}/mcp", operation=operation,
                                                      http_client_factory=factory))
                except McpServerUnreachable as refused:
                    out.append({"is_error": True, "unreachable": str(refused), "text": ""})
        return out

    return asyncio.run(go())


def _arguments(event: Any, *, action: str = "approve", content_hash: str | None = None) -> dict[str, Any]:
    return {"tenant": TENANT, "event_key": event.event_key, "action": action,
            "product_content_hash": event.product_content_hash if content_hash is None else content_hash,
            "annotation": "reviewed"}


def _pending(queue: ReviewQueue) -> set[str]:
    return {pending.event_key for pending, _ in queue.items(tenant=TENANT)}


@pytest.fixture()
def opened() -> Any:
    module = _module()
    if module is None:
        return None
    queue, events = _queue()
    return module, queue, events, _door(module, queue)


def _present(opened: Any) -> Any:
    assert opened is not None, ABSENT
    return opened


def test_an_authorized_reviewer_bound_to_the_item_releases_it(opened: Any) -> None:
    _, queue, events, door = _present(opened)
    [outcome] = _act(door, [(f"token-{FINDINGS_REVIEWER}", _arguments(events[FINDINGS_ITEM]))])
    assert not outcome["is_error"], outcome
    resolution = ReviewResolution.model_validate_json(outcome["text"])
    assert resolution.record.released is True
    assert resolution.record.event.event_key == FINDINGS_ITEM
    assert resolution.record.submission.principal.approver.subject_id == FINDINGS_REVIEWER
    assert resolution.record.submission.principal.authentication.assurance_level == "aal2"
    assert FINDINGS_ITEM not in _pending(queue)
    assert {SECOND_FINDINGS_ITEM, SANCTIONS_ITEM} <= _pending(queue)


def test_a_binding_to_another_hash_is_refused_and_the_item_stays_held(opened: Any) -> None:
    _, queue, events, door = _present(opened)
    [outcome] = _act(door, [(f"token-{FINDINGS_REVIEWER}", _arguments(events[FINDINGS_ITEM], content_hash="d" * 64))])
    assert not outcome["is_error"], outcome
    refused = ReviewResolutionRefused.model_validate_json(outcome["text"])
    assert refused.event_key == FINDINGS_ITEM
    assert FINDINGS_ITEM in _pending(queue)


def test_a_reviewer_whose_scope_does_not_reach_the_item_is_refused(opened: Any) -> None:
    """The wrong-target release: a genuine reviewer, a genuine item, not this reviewer's."""
    _, queue, events, door = _present(opened)
    [outcome] = _act(door, [(f"token-{SANCTIONS_REVIEWER}", _arguments(events[FINDINGS_ITEM]))])
    assert outcome["is_error"], f"a reviewer released an item its scope does not reach: {outcome}"
    # Refused by the AUTHORIZER, by its own words — not by the queue, the hash or the verifier.
    assert '"error_code": "tenant-unauthorized"' in outcome["text"], outcome
    assert "against the scope mapping in force" in outcome["text"], outcome
    assert FINDINGS_ITEM in _pending(queue)
    decisions = [e for e in door.control_plane.audit_log.events() if e.action == "authz_decision"]
    assert decisions and decisions[-1].resolved is False and decisions[-1].actor == SANCTIONS_REVIEWER, decisions


def test_reject_is_the_same_path_and_an_unknown_verdict_touches_nothing(opened: Any) -> None:
    _, queue, events, door = _present(opened)
    rejected, unknown = _act(door, [
        (f"token-{FINDINGS_REVIEWER}", _arguments(events[SECOND_FINDINGS_ITEM], action="reject")),
        (f"token-{SANCTIONS_REVIEWER}", _arguments(events[SANCTIONS_ITEM], action="escalate")),
    ])
    assert not rejected["is_error"], rejected
    assert ReviewResolution.model_validate_json(rejected["text"]).record.released is False
    assert SECOND_FINDINGS_ITEM not in _pending(queue)
    assert unknown["is_error"], unknown
    assert SANCTIONS_ITEM in _pending(queue)


def test_an_unknown_credential_is_refused_401(opened: Any) -> None:
    _, queue, events, door = _present(opened)
    [outcome] = _act(door, [("token-nobody-issued", _arguments(events[FINDINGS_ITEM]))])
    assert "401" in outcome.get("unreachable", ""), outcome
    assert FINDINGS_ITEM in _pending(queue)


def test_the_door_states_reviewer_scopes_or_refuses() -> None:
    module = _present(_module())
    queue, _ = _queue()
    with pytest.raises(ValueError, match="reviewer_scopes is empty"):
        module.open_review_door(queue, tenant_id=TENANT, token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(grants={})), reviewer_scopes={}, clock=lambda: CLOCK)
