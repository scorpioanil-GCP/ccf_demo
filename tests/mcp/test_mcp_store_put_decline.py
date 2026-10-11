"""A write the artifact server declines is a decline, not an outage (`D-IMPL-378`, lane ``378f-small2``).

``src/ccf/artifacts/mcp_store.py::McpArtifactStore.put`` documents ``ArtifactStoreError`` for "the server declined the
write" and ``McpServerUnreachable`` for a substrate it could not reach. It judged the server's answer *inside* the
session operation, and the session runner, ``src/ccf/mcp/client.py::run_with_session``, reports anything an operation
raises that is not an ``McpClientError`` as ``McpServerUnreachable``. So a write the server declined (the call
completed, and the server answered it as an error) reached the caller as an outage: a caller retries it as one, and
cannot tell it from a dead server. ``McpArtifactStore.match_subject`` met the same runner and judges its answer after
the session closes; ``put`` now does the same.

The first test runs the runner as shipped, unpatched, over real streamable HTTP to the conformance child server
(``tests/crossproc/servers/mcp_artifact_child.py::build_server``), whose store declares its replay-record class as
fabric-written under ``ReplayMint``. This client declares no fabric-written class, so its own check admits a
client-lane write to that class before anything is sent, and the server's identical check declines it. The decline
is the server's, and nothing is patched. The second runs the same runner with its transport and session replaced, so
that the other two answers ``put`` judges can be written exactly: no structured reference (a decline), and a
structured answer that is not a reference (unreachability, as before: the write's outcome is unknown). The third
asks the built server as a caller its authorizer refuses: the tenant guard's refusal reaches the client as a tool
error, and is a decline too.
"""

from __future__ import annotations

import contextlib
import socket
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from mcp.types import CallToolResult, TextContent

import ccf.mcp.client as client_module
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import ArtifactStoreError, WriteKinds
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import content_hash
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpClientError, McpServerUnreachable

from crossproc.conftest import spawn_child_server
from crossproc.servers.mcp_artifact_child import (
    REPLAY_RECORD_CLASS,
    TENANT,
    authorized_http_client,
)
from tests.controlplane.capabilities import capability

#: The artifact server child ``tests/conformance/test_artifactstore.py::store_factory`` runs its ``mcp`` param against.
ARTIFACT_CHILD = Path(__file__).resolve().parents[1] / "crossproc" / "servers" / "mcp_artifact_child.py"

#: A test deadline; the SDK chooses none (D-IMPL-38).
CALL_TIMEOUT_SECONDS = 30.0

#: A class the child's store does not declare: the client lane.
CLIENT_CLASS = "decline-test-artifact"
NAME = "the-artifact"


@pytest.fixture
def artifact_server_url() -> Iterator[str]:
    with spawn_child_server(ARTIFACT_CHILD) as port:
        yield f"http://127.0.0.1:{port}/mcp"


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as running:
        yield running


@pytest.fixture
def closed_url() -> str:
    """An endpoint nothing listens on: a port bound and released."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return f"http://127.0.0.1:{port}/mcp"


def _client(url: str, bridge: SyncMcpBridge) -> McpArtifactStore:
    """A client that declares no class as fabric-written, so only the server's declaration can decline a write."""
    return McpArtifactStore(
        url=url, bridge=bridge, write_kinds=WriteKinds({}), http_client_factory=authorized_http_client
    )


def _write(store: McpArtifactStore, artifact_class: str, artifact: object) -> Any:
    return store.put(capability(ArtifactWrite, tenant=TENANT, resource=f"{artifact_class}/{NAME}"), artifact)


def test_a_write_the_server_declines_is_an_artifact_store_error_not_an_outage(
    artifact_server_url: str, bridge: SyncMcpBridge, closed_url: str
) -> None:
    store = _client(artifact_server_url, bridge)
    # Control: the server is reachable, the credential is accepted, and the client lane is written.
    accepted = _write(store, CLIENT_CLASS, {"label": "accepted", "ordinal": 1})
    assert store.exists(content_address=accepted.content_address)

    declined_artifact = {"label": "declined", "ordinal": 2}
    with pytest.raises(ArtifactStoreError) as declined:
        _write(store, REPLAY_RECORD_CLASS, declined_artifact)
    # The decline itself, by name: exactly the store's decline, raised on the server's answer. Not an outage, and
    # not another refusal of the store's family.
    assert type(declined.value) is ArtifactStoreError
    assert not isinstance(declined.value, McpClientError)
    assert str(declined.value) == f"the artifact server declined to store {NAME!r}"
    assert not store.exists(content_address=content_hash(declined_artifact))

    # Control: an outage still reads as one.
    with pytest.raises(McpServerUnreachable):
        _write(_client(closed_url, bridge), CLIENT_CLASS, {"label": "unreachable", "ordinal": 3})


def test_each_answer_put_judges_keeps_its_own_type_through_the_session_runner(
    monkeypatch: pytest.MonkeyPatch, bridge: SyncMcpBridge
) -> None:
    """The runner as shipped, over a fake transport and session: what the server answers is all that varies."""
    answers: list[CallToolResult] = []

    @contextlib.asynccontextmanager
    async def transport(url: str, http_client: object = None) -> AsyncIterator[tuple[object, object, object]]:
        yield (object(), object(), lambda: None)

    class Session:
        def __init__(self, read: object, write: object) -> None:
            pass

        async def __aenter__(self) -> "Session":
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def initialize(self) -> None:
            return None

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
            return answers.pop(0)

    monkeypatch.setattr(client_module, "streamable_http_client", transport)
    monkeypatch.setattr(client_module, "ClientSession", Session)
    store = McpArtifactStore(url="http://artifact.invalid/mcp", bridge=bridge, write_kinds=WriteKinds({}))

    # A completed call with no structured reference is a decline.
    answers.append(CallToolResult(content=[TextContent(type="text", text="no reference")], isError=False))
    with pytest.raises(ArtifactStoreError) as declined:
        _write(store, CLIENT_CLASS, {"label": "no-reference", "ordinal": 4})
    assert type(declined.value) is ArtifactStoreError
    assert str(declined.value) == f"the artifact server declined to store {NAME!r}"

    # A structured answer that is not a reference says nothing about whether the write happened: unreachability.
    answers.append(CallToolResult(content=[], structuredContent={"content_address": 5}, isError=False))
    with pytest.raises(McpServerUnreachable) as malformed:
        _write(store, CLIENT_CLASS, {"label": "malformed", "ordinal": 5})
    assert not isinstance(malformed.value, ArtifactStoreError)
    assert answers == []


class _InThread:
    """The bridge's contract, run on a thread of its own, as ``SyncMcpBridge`` runs it."""

    def run(self, coroutine: Any) -> Any:
        import asyncio  # noqa: PLC0415
        from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coroutine).result()


def test_a_write_the_servers_authorizer_refuses_is_a_decline_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tenant guard refuses before the store is handed anything, and the client still reads a decline.

    The built artifact server (``tests/mcp/test_artifact_server_authorized.py::_world``), its authorizer's one mapping
    granting another tenant only, reached over an in-memory MCP session
    (``tests/mcp/wire_capture.py::route_store_through``) by a verified caller of this tenant.
    """
    from ccf.authz.actions import ACTION_ARTIFACT_WRITE  # noqa: PLC0415
    from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED  # noqa: PLC0415
    from tests.mcp import test_artifact_server_authorized as authorized  # noqa: PLC0415
    from tests.mcp import wire_capture  # noqa: PLC0415
    from tests.mcp.guarded_servers import FOREIGN, authorizer_granting  # noqa: PLC0415
    from tests.mcp.guarded_servers import TENANT as GUARDED_TENANT  # noqa: PLC0415

    world = authorized._world(tmp_path, authorizer=authorizer_granting(tenants=(FOREIGN,)))
    wire = wire_capture.Wire()
    wire_capture.route_store_through(monkeypatch, world.server, authorized._grant(GUARDED_TENANT), wire)
    store = McpArtifactStore(
        url="http://artifact.invalid/mcp",
        bridge=_InThread(),  # type: ignore[arg-type]
        write_kinds=WriteKinds({}),
    )

    with pytest.raises(ArtifactStoreError) as declined:
        store.put(
            capability(ArtifactWrite, tenant=GUARDED_TENANT, resource=f"{CLIENT_CLASS}/{NAME}"),
            {"label": "refused", "ordinal": 6},
        )
    assert type(declined.value) is ArtifactStoreError
    assert str(declined.value) == f"the artifact server declined to store {NAME!r}"
    # Refused by the deployment's authorizer, asked about exactly this write, and nothing reached the store.
    assert [entry["action_id"] for entry in world.authorizer.asked] == [ACTION_ARTIFACT_WRITE]
    assert world.authorizer.asked[0]["resource"] == f"{CLIENT_CLASS}/{NAME}"
    assert world.store.puts == []
    (answer,) = wire.answers("tools/call")
    assert ERROR_TENANT_UNAUTHORIZED in answer
