# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""An entitled caller asking for a class declared nowhere reads exactly as an unentitled caller (R5-CP17-F01).

**SDK-defined** (CLAUDE.md §11). Finding R5-CP17-F01 (cp-17 MWE-G14, round 5
calibration lane): on the standard MCP door an ENTITLED credential asking
``request_context_product`` for a product class no scope mapping names was denied at
the scope mapping's resource axis as a TOOL ERROR naming the class
(``tenant-unauthorized``), while an unentitled credential asking for a real class
got the governed minimal ``subject-unavailable`` shell. The two replies differed, so
the door answered *"does this class exist?"*.

**Ruled** (Dave, 2026-10-11 21:19 MST, verbatim *"Do (a)"*): make the
undeclared-class reply indistinguishable from the generic refusal an unentitled
caller gets — same shape and text, no class name, no differing reason. The deny
stays a deny and stays on the audit log; it is now RECORDED as a governed refusal
(internal truth ``tenant-unauthorized``, on the record only) and disclosed through
the same recorder as the entitlement denial.

Held here over the real door: the permitted case serves; the unentitled caller and
the undeclared class are byte-identical but for the per-answer record reference;
the record behind the undeclared-class reply names why.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import httpx

from ccf.contracts.canonical import canonical_bytes
from ccf.client.wire import WireRequest
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL

from tests.mcp.test_door_declared_principals import (
    BASE_URL,
    FULL,
    UNDECLARED,
    _Door,
    _open,
    _policy,
    _served,
)
from tests.products import paved_fixture as fixture

NOWHERE = f"{fixture.CHILD_CLASS}-declared-nowhere"


def _ask(door: _Door, token: str, product_class: str) -> dict[str, Any]:
    """``_Door.ask`` with the product class as the one variable."""
    from mcp.types import TextContent

    from ccf.mcp.client import run_with_session

    now = datetime.now(UTC)
    parameters = {fixture.THRESHOLD_PARAMETER: 1000}
    arguments = {
        "tenant": door.opened.tenant_id,
        "product_class": product_class,
        "version": fixture.CHILD_VERSION,
        "request": canonical_bytes(
            WireRequest(product_id=product_class, parameters=parameters, temporal_boundary=now)
        ).decode("utf-8"),
        "subject": "acct-1",
        "intent": "fixture-intent",
        "freshness": "fixture-freshness",
        "asked_at": now.isoformat(),
        "parameters": parameters,
    }
    app = door.door.server(
        issuer_url="https://issuer.invalid", resource_server_url=f"{BASE_URL}/mcp"
    ).streamable_http_app()

    async def operation(session: Any) -> Any:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
        return {
            "is_error": bool(result.isError),
            "text": " | ".join(c.text for c in result.content if isinstance(c, TextContent)),
            # THE COMPLETE PUBLIC REPLY (Dave, 2026-10-11 21:44 MST: "Compare the
            # complete public refusal response, including status and structured
            # fields — not just its message"): isError, every content item, any
            # structured content and meta, exactly as the client received them.
            "whole": result.model_dump(mode="json"),
        }

    async def go() -> Any:
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=BASE_URL,
                    headers={"Authorization": f"Bearer {token}"},
                )

            return await run_with_session(url=f"{BASE_URL}/mcp", operation=operation, http_client_factory=factory)

    return asyncio.run(go())


#: The two members a refusal carries that are not the door's statement: the per-answer
#: record reference, and the echo of the caller's OWN question (its product id and
#: instant — what the caller sent, which tells it nothing it did not know).
_PER_QUESTION = frozenset({"replay_reference", "request"})


def _shell(refusal: Mapping[str, Any]) -> tuple[Any, ...]:
    """What the door states about a refusal — every member but the per-question two."""
    return tuple(sorted((k, json.dumps(v, sort_keys=True)) for k, v in refusal.items() if k not in _PER_QUESTION))


def _public(reply: Mapping[str, Any], *, asked_class: str) -> Any:
    """The complete public reply with exactly the per-question members normalized.

    Every content item is parsed and compared whole. Normalized, and nothing else:
    the record reference (issued per answer, Q11) wherever it appears, and the echo
    of the caller's OWN question — its product id and instant, what the caller sent.
    The class name is replaced only where it is that echo; anywhere else it stays,
    so a door statement naming it would differ.
    """

    def scrub(value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {k: scrub(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [scrub(v) for v in value]
        if key in ("replay_reference", "replay_ref"):
            return "<per-answer record>"
        if key in ("temporal_boundary", "asked_at"):
            return "<the caller's instant>"
        if key == "product_id" and value == asked_class:
            return "<the caller's class>"
        if isinstance(value, str) and value.startswith(("{", "[")):
            try:
                return {"<json>": scrub(json.loads(value))}
            except ValueError:
                return value
        return value

    return scrub(reply["whole"])


def test_an_undeclared_class_and_an_unentitled_caller_get_one_reply(tmp_path: Path) -> None:
    with _open(tmp_path, policy=_policy()) as opened:
        door = _Door(opened)
        permitted = _ask(door, f"token-{FULL}", fixture.CHILD_CLASS)
        unentitled = _ask(door, f"token-{UNDECLARED}", fixture.CHILD_CLASS)
        nowhere = _ask(door, f"token-{FULL}", NOWHERE)
        store = opened.artifact_store

        # Permitted: a declared class, an entitled caller — served.
        assert _served(permitted), permitted

        # Refused, both, and indistinguishable.
        assert unentitled["is_error"] is False, unentitled["text"][:300]
        assert nowhere["is_error"] is False, f"a tool error where the governed refusal is owed: {nowhere['text'][:300]}"
        a, b = json.loads(unentitled["text"]), json.loads(nowhere["text"])
        assert a["refusal"] is not None and b["refusal"] is not None
        assert _shell(a["refusal"]) == _shell(b["refusal"])
        assert sorted(a) == sorted(b) and sorted(a["refusal"]) == sorted(b["refusal"])
        assert b["refusal"]["request"]["product_id"] == NOWHERE, "the echo is the caller's own question"
        stated = {k: v for k, v in b["refusal"].items() if k not in _PER_QUESTION}
        assert NOWHERE not in json.dumps(stated), "the door's statement names the undeclared class"
        assert "tenant-unauthorized" not in nowhere["text"]
        assert a["refusal"]["replay_reference"] != b["refusal"]["replay_reference"]
        # The WHOLE public reply, every member, equal once the per-question members
        # are normalized: no status, structured field, code or content item tells
        # the undeclared class from the unentitled caller.
        assert _public(nowhere, asked_class=NOWHERE) == _public(unentitled, asked_class=fixture.CHILD_CLASS), (
            json.dumps(_public(nowhere, asked_class=NOWHERE), indent=1)[:2000],
            json.dumps(_public(unentitled, asked_class=fixture.CHILD_CLASS), indent=1)[:2000],
        )

        # TRUTHFUL AUDIT (Dave, 21:44: "Keep truthful audit events"): the
        # authorizer's deny for the undeclared class is on the log, as a deny, with
        # the resource axis failing — answered differently, decided the same.
        from ccf.controlplane.audit import AuthzDecisionAuditEvent

        decisions = [e for e in opened.control_plane.audit_events() if isinstance(e, AuthzDecisionAuditEvent)]
        nowhere_decisions = [e for e in decisions if e.actor == FULL and getattr(e, "authz_resource", None) == NOWHERE]
        assert nowhere_decisions, [(e.actor, getattr(e, "authz_resource", None)) for e in decisions]
        assert all(not e.resolved and e.authz_failing_axis == "resource" for e in nowhere_decisions)

        # The internal truth is on the record behind the reply, never on the wire.
        from ccf.replay.record import DecisionReplayRecord

        record = DecisionReplayRecord.model_validate_json(
            store.get(content_address=store.resolve_uri(uri=b["refusal"]["replay_reference"]))
        )
        assert "tenant-unauthorized" in record.content_generation_path.assembly_refusal
