"""Child process: the authenticated HITL MCP transport (D-IMPL-20 authority).

Run as ``python tests/crossproc/servers/mcp_hitl_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — the readiness
handshake ``tests/crossproc/conftest.py`` blocks on (D-16). Nothing on the
parent's path to that line sleeps.

**The queue and the gate are real.** A live
:class:`~ccf.hitl.transport.InMemoryHitlTransport` holds the fixture pending
event; an action arriving over the wire is resolved by a real
:class:`~ccf.hitl.approval_gate.ApprovalGate` — audited, TOCTOU-guarded —
and the resolution's pre-serialized block lands on replay dimension 2
through :func:`~ccf.replay.record.build_replay_record` and a
:class:`~ccf.replay.serve.ReplayWriter` over a ``FileArtifactStore``, before
anything returns. The HITL server module itself holds none of this: it sees
two Protocol callables and nothing else.

**The builders are shared with the parent on purpose.** ``pending_event``
and ``principal_binding`` are imported by ``test_hitl_mcp.py`` to compute
the exact dimension-2 block it expects; two copies would agree only until
someone edited one.

**Every domain value comes from ``tests/fixtures/banking/hitl.yaml``** —
tenant, event, approver identity, authentication context, action instant.
Delete the fixture and this file has nothing to serve (CLAUDE.md §6.4
applied to fixture code).
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# The child is spawned as a bare `python <file>`, so it gets none of pytest's
# sys.path work. Resolving the roots from __file__ is what makes it runnable
# from anywhere, which the fixture depends on.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import httpx  # noqa: E402
import yaml  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.contracts.canonical import canonical_bytes, content_hash  # noqa: E402
from ccf.controlplane.audit import AuditLog  # noqa: E402
from ccf.graph.protocols import GraphView  # noqa: E402
from ccf.hitl.approval_gate import ApprovalGate, GateResolution  # noqa: E402
from ccf.hitl.principal import (  # noqa: E402
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (  # noqa: E402
    HitlActionSubmission,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    ProductLineage,
)
from ccf.projection.engine import ExecutionResult, ExecutionStep  # noqa: E402
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
from ccf.replay.record import PolicyBinding, build_replay_record  # noqa: E402
from ccf.replay.serve import ReplayWriter  # noqa: E402
from ccf_runtime.mcp.auth import (  # noqa: E402
    FileTokenSource,
    SourceBackedTokenVerifier,
)
from ccf_runtime.mcp.hitl_server import build_hitl_server  # noqa: E402

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

FIXTURES = _TESTS_ROOT / "fixtures" / "banking"

#: The one credential this test server recognises. A test value, meaningful
#: nowhere else; the SDK ships no token of its own.
DEV_TOKEN = "ccf-hitl-dev-token"

#: Deployment vocabulary, chosen here because a test *is* the deployment.
CLIENT_ID = "ccf-hitl-client"
SCOPE = "ccf:hitl"
SERVER_NAME = "ccf-hitl-conformance"
ISSUER_URL = "https://issuer.invalid"
RESOURCE_SERVER_URL = "https://hitl-server.invalid/mcp"

TOKEN_FILENAME = "tokens.json"
REPLAY_DIRNAME = "replay"

#: The artifact class the child files replay records under. Deployment
#: vocabulary chosen by this test deployment.
REPLAY_ARTIFACT_CLASS = "ccf.decision-replay"


def authorized_http_client(token: str = DEV_TOKEN) -> httpx.AsyncClient:
    """An HTTP client presenting ``token`` as a bearer credential."""
    return httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"})


def write_token_file(*, workspace: Path) -> Path:
    """Write the child's token file and return its path."""
    token_file = workspace / TOKEN_FILENAME
    token_file.write_text(
        json.dumps({DEV_TOKEN: {"client_id": CLIENT_ID, "scopes": [SCOPE]}}),
        encoding="utf-8",
    )
    return token_file


def _hitl_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "hitl.yaml").read_text()
    )
    return loaded


def pending_event() -> PendingHitlEvent:
    """The fixture pending approval-gate event — shared with the parent.

    The ``product_content_hash`` is derived identity, computed by mechanism
    at build time exactly as the HITL suites do — a hash is never a fixture
    value (D-IMPL-26).
    """
    document = dict(_hitl_fixture()["event"])
    return PendingHitlEvent(
        **document, product_content_hash=content_hash(document)
    )


def principal_binding(*, product_content_hash: str) -> HumanPrincipalBinding:
    """The fixture credit officer's complete binding — shared with the parent."""
    approver = _hitl_fixture()["approvers"]["credit_officer"]
    return HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=product_content_hash,
    )


def _clock() -> Callable[[], datetime]:
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def _replay_inputs(
    event: PendingHitlEvent,
) -> tuple[ExecutionResult, ContextProductContract, Perspective]:
    """The minimal execution/product/perspective the child records against."""
    boundary = datetime(2026, 7, 30, tzinfo=UTC)
    execution = ExecutionResult(
        plan_id=event.workflow_state_ref,
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash=content_hash({"plan": event.workflow_state_ref}),
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(
            plan_id=event.workflow_state_ref,
            payload={"event_key": event.event_key},
        ),
        view=GraphView(tenant_id=event.tenant, as_of=boundary),
    )
    product = ContextProductContract(
        schema_name="ccf.hitl-decision-context",
        schema_version="1.0.0",
        plan_id=event.workflow_state_ref,
        tenant_id=event.tenant,
        temporal_boundary=boundary,
        expires_at=boundary + timedelta(days=1),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"1.0.0"}),
            graph_snapshot_at=boundary,
        ),
        payload={"event_key": event.event_key},
    )
    perspective = Perspective(
        principal_id=event.workflow_state_ref, role=event.event_class
    )
    return execution, product, perspective


def build_server(*, workspace: Path) -> FastMCP:
    """A live transport, a real gate, and the HITL MCP server over both."""
    transport = InMemoryHitlTransport()
    event = pending_event()
    transport.enqueue(event=event)

    gate = ApprovalGate(transport=transport, audit=AuditLog(), clock=_clock())
    writer = ReplayWriter(
        store=FileArtifactStore(root=workspace / REPLAY_DIRNAME),
        artifact_class=REPLAY_ARTIFACT_CLASS,
    )

    def queue_view(*, tenant: str) -> tuple[PendingHitlEvent, ...]:
        """The tenant's pending events, straight off the typed transport."""
        return transport.pending(tenant=tenant)

    def route_action(*, submission: HitlActionSubmission) -> str:
        """Resolve through the real gate; land the action on replay dim 2.

        The recording obligation belongs to the primitive-consuming
        deployment (the D-22 scoping in :mod:`ccf.hitl.transport`), and this
        deployment discharges it before anything returns: no path exists
        from a completed resolution back to the wire that skips the replay
        append.
        """
        resolution = gate.resolve(
            tenant=submission.tenant,
            event_key=submission.event_key,
            action=submission.action,
            principal=submission.principal,
            annotation=submission.annotation,
        )
        if not isinstance(resolution, GateResolution):
            return canonical_bytes(
                {"refused": True, "reason": resolution.reason}
            ).decode("utf-8")
        execution, product, perspective = _replay_inputs(resolution.record.event)
        record = build_replay_record(
            execution=execution,
            product=product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(
                    key=resolution.record.event.policy_ref or "",
                    version="1.0.0",
                ),
            ),
            assembly_mode="algorithmic",
            recorded_at=submission.principal.action_time,
            hitl_actions=resolution.hitl_actions_block,
        )
        capability = writer.write_replay_record(record=record)
        return canonical_bytes(
            {
                "refused": False,
                "approved": resolution.record.approved,
                "replay_record": canonical_bytes(record).decode("utf-8"),
                "replay_ref": {
                    "uri": capability.replay_ref.uri,
                    "content_address": capability.replay_ref.content_address,
                },
            }
        ).decode("utf-8")

    return build_hitl_server(
        server_name=SERVER_NAME,
        queue_view=queue_view,
        action_route=route_action,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=write_token_file(workspace=workspace))
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(ISSUER_URL),
            resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
            required_scopes=[SCOPE],
        ),
    )


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import anyio
    import uvicorn

    with tempfile.TemporaryDirectory() as workspace:
        server_app = build_server(workspace=Path(workspace))

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(server_app.streamable_http_app(), log_level="error")
        )

        async def serve() -> None:
            async def announce() -> None:
                # A 5 ms poll of *this process's own* server object — it
                # observes a real state flag rather than guessing a duration,
                # and the parent learns nothing until the flag flips.
                while not server.started:
                    await anyio.sleep(0.005)
                print(f"READY {port}", flush=True)

            async with anyio.create_task_group() as group:
                group.start_soon(announce)
                await server.serve(sockets=[bound])

        anyio.run(serve)


if __name__ == "__main__":
    main()
