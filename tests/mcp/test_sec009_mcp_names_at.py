"""SEC-009 ruling 2 (fix round 1 follow-up) — ``names_at`` over MCP, so the §7.4 reference store is erasable (`D-IMPL-374` (4)).

The erasure door verifies an address's STORED class and tenant through the
store's ``names_at``. The MCP artifact server's backing store answers it; the
server exposes it as a resource scoped to the caller's verified tenant, and
``McpArtifactStore`` reads it — so an erasure requested through the MCP-backed
reference store is VERIFIED and ADMITTED rather than refused
``class-unverifiable``. A third-party store with no ``names_at`` still refuses.

The client is wired to the in-process server by replacing the store's
session runner with one that reads the server's resources under the caller's
grant — the real client code and the real server code, no network.

RED today: the server has no names resource, the client no ``names_at``, and
the door refuses ``class-unverifiable``.
"""

from __future__ import annotations

import base64
import json
import pathlib
from typing import Any

import pytest
from mcp.server.auth.settings import AuthSettings
from mcp.types import BlobResourceContents, TextResourceContents
from pydantic import AnyHttpUrl

import ccf.artifacts.mcp_store as mcp_store_module
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.authz.capability import ArtifactWrite, mint
from ccf.authz.decision import AuthzDecision
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.mcp.artifact_server import build_artifact_server
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from tests.composition import no_erasures
from tests.erasure import harness as h
from tests.mcp import test_artifact_server_authorized as aa
from tests.mcp.guarded_servers import PRINCIPAL, SCOPE, _entitlement_world, authorizer_granting

FOREIGN = "beta-bank"


def _grant(tenant: str = h.TENANT) -> TokenGrant:
    return TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset({tenant}))


def _server(tmp_path: pathlib.Path, store: Any) -> Any:
    source, recorder = _entitlement_world(tmp_path)
    return build_artifact_server(
        server_name="sec009-names",
        store=store,
        token_verifier=SourceBackedTokenVerifier(source=StaticTokenSource(grants={"tok": _grant()})),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=authorizer_granting(tenants=(h.TENANT, FOREIGN)),
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=ControlPlaneRegistry().audit_log,
        erasure_index=no_erasures(),
    )


def _read(server: Any, uri: str, *, tenant: str = h.TENANT) -> list[Any]:
    import anyio

    reset = aa._as_grant(_grant(tenant))
    try:
        return list(anyio.run(server.read_resource, uri))
    finally:
        from mcp.server.auth.middleware.auth_context import auth_context_var

        auth_context_var.reset(reset)


def _names_uri(address: str) -> str:
    return str(h.contract("ccf_runtime.mcp.artifact_server", "artifact_names_uri")(content_address=address))


def _put(store: Any, tenant: str, name: str, document: dict[str, Any]) -> Any:
    resource = f"{h.DOC_CLASS}/{name}"
    authorized = mint(
        ArtifactWrite,
        decision=AuthzDecision(
            allowed=True, matched_scope_pattern=tenant, matched_resource_pattern=resource,
            artifact_version="1.0.0", action_id=ArtifactWrite.action_id, tenant=tenant, resource=resource,
        ),
        principal="filer", decision_id=f"put-{name}",
    )
    return store.put(authorized, document)


def test_the_server_answers_names_at_scoped_to_the_callers_tenant(tmp_path: pathlib.Path) -> None:
    plane = h.compose(tmp_path)
    server = _server(tmp_path, plane.store)
    same = _put(plane.store, FOREIGN, "theirs", {"customer": {"id": h.SUBJECT_ID}, "note": "kyc"})
    assert same.content_address == plane.document.content_address  # the same bytes, filed by two tenants
    (answer,) = _read(server, _names_uri(plane.document.content_address))
    names = json.loads(answer.content)
    assert {(n["tenant_id"], n["artifact_class"]) for n in names} == {(h.TENANT, h.DOC_CLASS)}
    assert all(n["tenant_id"] != FOREIGN for n in names), "another tenant's filing never crosses"


class _InProcessSession:
    """An MCP client session answered by the in-process server, under one grant."""

    def __init__(self, server: Any) -> None:
        self._server = server

    async def read_resource(self, uri: Any) -> Any:
        from mcp.server.auth.middleware.auth_context import auth_context_var

        reset = aa._as_grant(_grant())
        try:
            contents = list(await self._server.read_resource(str(uri)))
        finally:
            auth_context_var.reset(reset)

        class _Result:
            pass

        result = _Result()
        result.contents = [
            BlobResourceContents(uri=str(uri), blob=base64.b64encode(c.content).decode("ascii"), mimeType=c.mime_type)
            if isinstance(c.content, bytes)
            else TextResourceContents(uri=str(uri), text=c.content, mimeType=c.mime_type)
            for c in contents
        ]
        return result


class _Run:
    """The bridge's contract — run a coroutine to completion from sync code —
    on its own thread, as the real ``SyncMcpBridge`` does, so it works when the
    caller (the async door) is itself inside an event loop."""

    def run(self, coroutine: Any) -> Any:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coroutine).result()


def test_an_erasure_through_the_mcp_backed_reference_store_is_verified_and_admitted(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plane = h.compose(tmp_path)
    server = _server(tmp_path, plane.store)
    session = _InProcessSession(server)

    async def run_with_session(*, url: str, operation: Any, http_client_factory: Any) -> Any:
        return await operation(session)

    monkeypatch.setattr(mcp_store_module, "run_with_session", run_with_session)
    client = McpArtifactStore(url="http://artifact.invalid/mcp", bridge=_Run(), write_kinds=h.write_kinds())  # type: ignore[arg-type]
    door = h.door_module("ErasureDoor")(
        engine=plane.engine,
        factory=h.WorkflowFactory(control_plane=plane.registry),
        control_plane=plane.registry,
        transport=plane.transport,
        store=client,
        clock=plane.clock,
        index=h.index_of(plane),
    )
    request = h.request(plane)
    suspended = h.run(
        door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request))
    )
    assert getattr(suspended, "event_key", None), suspended
    names = client.names_at(content_address=plane.document.content_address)
    assert {(n.tenant_id, n.artifact_class) for n in names} == {(h.TENANT, h.DOC_CLASS)}


def test_an_artifact_server_without_the_names_resource_refuses_class_unverifiable(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix round 2, (d): an older server that omits the names resource — the read
    fails, which the client's session runner reports as McpServerUnreachable —
    is refused by name, ``class-unverifiable``, never read as "no class"."""
    from ccf.mcp.errors import McpServerUnreachable

    plane = h.compose(tmp_path)
    server = _server(tmp_path, plane.store)
    session = _InProcessSession(server)

    async def run_with_session(*, url: str, operation: Any, http_client_factory: Any) -> Any:
        class _OlderServer:
            async def read_resource(self, uri: Any) -> Any:
                if str(uri).startswith("ccf-artifact-names://"):
                    raise McpServerUnreachable("Unknown resource")
                return await session.read_resource(uri)

        return await operation(_OlderServer())

    monkeypatch.setattr(mcp_store_module, "run_with_session", run_with_session)
    client = McpArtifactStore(url="http://artifact.invalid/mcp", bridge=_Run(), write_kinds=h.write_kinds())  # type: ignore[arg-type]
    door = h.door_module("ErasureDoor")(
        engine=plane.engine,
        factory=h.WorkflowFactory(control_plane=plane.registry),
        control_plane=plane.registry,
        transport=plane.transport,
        store=client,
        clock=plane.clock,
        index=h.index_of(plane),
    )
    request = h.request(plane)
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    assert refused.value.reason_code == "class-unverifiable"


def test_the_names_resource_requires_the_entitlement_a_governed_read_requires(tmp_path: pathlib.Path) -> None:
    """Fix round 2, N4: naming a GOVERNED artifact (a class the substrate declares
    under ReplayMint) takes the same governed dereference the blob read takes,
    minus bytes. A holder of bare ``artifact.read`` without the record's
    entitlement learns no governed class or name."""
    from ccf.artifacts.protocol import DerivedWrite
    from tests.http_api.composition_authority import composition_replay_mint, deployment_store
    from tests.mcp.guarded_servers import REPLAY_RECORD_CLASS

    store = deployment_store(tmp_path / "governed", REPLAY_RECORD_CLASS)
    server = _server(tmp_path, store)
    pin = store.put(
        composition_replay_mint(ControlPlaneRegistry(), tenant=h.TENANT, artifact_class=REPLAY_RECORD_CLASS),
        DerivedWrite(artifact_class=REPLAY_RECORD_CLASS, name="pin", artifact={"seeds": ["s"]}),
    )
    (answer,) = _read(server, _names_uri(pin.content_address))
    text = answer.content if isinstance(answer.content, str) else answer.content.decode("utf-8")
    assert REPLAY_RECORD_CLASS not in text, text
    assert "pin" not in json.loads(text) if isinstance(json.loads(text), list) else True
