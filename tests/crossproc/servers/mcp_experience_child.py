"""Child process: the authenticated Experience-surface MCP edge (EXPR-01).

Run as ``python tests/crossproc/servers/mcp_experience_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — the readiness
handshake ``tests/crossproc/conftest.py`` blocks on (D-16). Nothing on the
parent's path to that line sleeps.

**The product is assembled, not fabricated.** The product resolver reuses
:func:`crossproc.servers.mcp_egress_child.build_servable_product` — the whole
L1→L6 banking slice runs in this process, and only a gate-admitted
``ServableProduct`` reaches the wire, exactly as on the egress edge.

**The agent leg goes through the Agent Factory + Control Plane, with zero
privileged paths.** The injected invoker constructs the agent through
:class:`~ccf.agents.factory.AgentFactory` against a live
``ControlPlaneRegistry`` — the same construction path every in-process client
takes — dispatches the named bound skill, and lands the decision in a
Decision Replay record written through :class:`~ccf.replay.serve.ReplayWriter`
over a real ``FileArtifactStore``. The experience server module itself holds
none of this: it sees three Protocol callables and nothing else.

**The builders are shared with the parent on purpose.** ``build_world`` and
``build_servable_product`` are imported by ``test_experience_edge.py`` to
compute the values it expects to receive; two copies of either would agree
only until someone edited one of them.

**Every domain value comes from ``tests/fixtures/banking/``** — tenant, agent
definition, policy regime, skill entry, grant, approver vocabulary, clock
instants. Delete the fixtures and this file has nothing to serve (CLAUDE.md
§6.4 applied to fixture code).
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

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

from ccf.agents.factory import AgentFactory  # noqa: E402
from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf.contracts.canonical import canonical_bytes, content_hash  # noqa: E402
from ccf.controlplane.artifacts import (  # noqa: E402
    declared_artifact_class,
    parse_artifact,
)
from ccf.controlplane.audit import AuditLog  # noqa: E402
from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: E402
from ccf.graph.protocols import GraphView  # noqa: E402
from ccf.products.contract import (  # noqa: E402
    ContextProductContract,
    ProductLineage,
)
from ccf.products.gates import ServableProduct  # noqa: E402
from ccf.projection.engine import ExecutionResult, ExecutionStep  # noqa: E402
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
from ccf.replay.record import PolicyBinding, build_replay_record  # noqa: E402
from ccf.replay.serve import ReplayWriter  # noqa: E402
from ccf.skills.callables import CallableRegistry  # noqa: E402
from ccf.skills.catalog import (  # noqa: E402
    SKILL_CATALOG_ENTRY,
    SkillCatalog,
    SkillCatalogEntry,
)
from ccf.skills.grants import GrantLedger, SkillGrant  # noqa: E402
from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition  # noqa: E402
from ccf_runtime.mcp.auth import (  # noqa: E402
    FileTokenSource,
    SourceBackedTokenVerifier,
)
from ccf_runtime.mcp.experience import (  # noqa: E402
    ExperienceProductNotServable,
    ExposedAgent,
    build_experience_server,
)

from crossproc.servers.mcp_egress_child import (  # noqa: E402
    ProductAddress,
    build_servable_product,
)
from fixtures.banking.skills.callables import covenant_metrics  # noqa: E402
from skills.sinks import ScriptedApprovalSink  # noqa: E402

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

FIXTURES = _TESTS_ROOT / "fixtures" / "banking"

#: The one credential this test server recognises. A test value, meaningful
#: nowhere else; the SDK ships no token of its own.
DEV_TOKEN = "ccf-experience-dev-token"

#: Deployment vocabulary, chosen here because a test *is* the deployment.
CLIENT_ID = "ccf-experience-client"
SCOPE = "ccf:experience"
SERVER_NAME = "ccf-experience-conformance"
ISSUER_URL = "https://issuer.invalid"
RESOURCE_SERVER_URL = "https://experience-server.invalid/mcp"

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


def _yaml(*parts: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FIXTURES.joinpath(*parts).read_text())
    return loaded


class AgentWorld(NamedTuple):
    """One Control Plane, catalog, ledger, and agent — built from fixtures.

    Shared by the child (to serve) and the parent (to compute what it
    expects), so the two cannot drift into agreeing by coincidence.
    """

    registry: ControlPlaneRegistry
    callables: CallableRegistry
    ledger: GrantLedger
    definition: AgentDefinition
    definition_key: str
    definition_version: str
    skill_entry: SkillCatalogEntry
    tenant: str
    boundary: datetime
    principal_id: str


def build_world() -> AgentWorld:
    """Build the fixture agent world the experience edge fronts.

    The agent is the grants fixture's ``auto`` agent (no tier-2 approval),
    granted the ``covenant-metrics-local`` skill through the governed ledger
    path — the same construction every in-process client performs.
    """
    grants_fixture = _yaml("skills", "grants.yaml")
    tool_fixture = _yaml("skills", "covenant_metrics_tool.yaml")
    agent_fixture = _yaml("agents", "covenant_analytics.yaml")

    boundary = datetime.fromisoformat(grants_fixture["clock"]["start"])
    audit = AuditLog()
    registry = ControlPlaneRegistry(clock=lambda: boundary, audit_log=audit)

    for reference in (
        grants_fixture["policy_regimes"]["auto"],
        agent_fixture["referenced_artifacts"]["halflife_debt_profile"],
    ):
        artifact_class = declared_artifact_class(reference["class_id"])
        declared = parse_artifact(
            {
                "class_id": reference["class_id"],
                "semver": reference["semver"],
                "declaration": reference["declaration"],
            },
            artifact_class,
        )
        registry.register_typed(reference["key"], declared, artifact_class)

    catalog = SkillCatalog(registry)
    entry = parse_artifact(
        dict(tool_fixture["variants"]["local_callable"]), SKILL_CATALOG_ENTRY
    )
    assert isinstance(entry, SkillCatalogEntry)
    assert isinstance(catalog.register(entry), str)

    ledger = GrantLedger(
        control_plane=registry,
        catalog=catalog,
        audit=audit,
        sink=ScriptedApprovalSink(
            approve=True,
            approver_id=grants_fixture["approval"]["approver_id"],
        ),
        clock=lambda: boundary,
    )

    definition = parse_artifact(
        dict(grants_fixture["agents"]["auto"]), AGENT_DEFINITION
    )
    assert isinstance(definition, AgentDefinition)
    definition_key = grants_fixture["policy_regimes"]["auto"]["key"] + "/agent"
    definition_version = registry.register_versioned(
        definition_key, definition, AGENT_DEFINITION
    )
    assert isinstance(definition_version, str)

    grant = SkillGrant(
        agent_definition_hash=content_hash(definition),
        **dict(grants_fixture["grants"]["metrics_local"]),
    )
    outcome = ledger.request(
        grant,
        definition=definition,
        actor=grants_fixture["approval"]["requesting_actor"],
    )
    assert isinstance(outcome, str), outcome

    callables = CallableRegistry()
    callables.register(
        tool_fixture["callables"]["registered_key"], covenant_metrics
    )

    return AgentWorld(
        registry=registry,
        callables=callables,
        ledger=ledger,
        definition=definition,
        definition_key=definition_key,
        definition_version=definition_version,
        skill_entry=entry,
        tenant=definition.tenant,
        boundary=boundary,
        principal_id=grants_fixture["approval"]["requesting_actor"],
    )


def replay_inputs(
    world: AgentWorld,
) -> tuple[ExecutionResult, ContextProductContract, Perspective]:
    """The execution/product/perspective the child's invoker records against.

    Shared with the parent so the dimension assertions compare against the
    same values the child recorded. Every domain value is fixture-derived:
    the product is the one class the agent's context contract consumes; the
    perspective role is the definition's own.
    """
    consumed = world.definition.context_contract.consumes[0]
    execution = ExecutionResult(
        plan_id=world.definition_key,
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash=content_hash({"plan": world.definition_key}),
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(
            plan_id=world.definition_key,
            payload={"product_class": consumed.product_class},
        ),
        view=GraphView(tenant_id=world.tenant, as_of=world.boundary),
    )
    product = ContextProductContract(
        schema_name=consumed.product_class,
        schema_version=consumed.schema_version,
        plan_id=world.definition_key,
        tenant_id=world.tenant,
        temporal_boundary=world.boundary,
        expires_at=world.boundary.replace(year=world.boundary.year + 1),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"1.0.0"}),
            graph_snapshot_at=world.boundary,
        ),
        payload={"product_class": consumed.product_class},
    )
    perspective = Perspective(
        principal_id=world.principal_id,
        role=world.definition.perspective.role,
    )
    return execution, product, perspective


def build_server(*, workspace: Path) -> FastMCP:
    """Assemble the product, the agent world, and the experience server."""
    assembled = build_servable_product(
        database_path=workspace / "experience-child.sqlite3"
    )
    world = build_world()
    replay_store = FileArtifactStore(root=workspace / REPLAY_DIRNAME)
    writer = ReplayWriter(
        store=replay_store, artifact_class=REPLAY_ARTIFACT_CLASS
    )

    def resolve_product(
        *, tenant: str, product_class: str, version: str
    ) -> ServableProduct:
        """Serve exactly the one assembled address; refuse anything else."""
        requested = ProductAddress(
            tenant=tenant, product_class=product_class, version=version
        )
        if requested != assembled.address:
            raise ExperienceProductNotServable(str(requested))
        return assembled.servable

    def directory(*, tenant: str) -> tuple[ExposedAgent, ...]:
        """This deployment's one exposed agent, per tenant (T-07-21)."""
        if tenant != world.tenant:
            return ()
        bound = world.ledger.bound_view(content_hash(world.definition))
        return (
            ExposedAgent(
                definition_key=world.definition_key,
                definition_version=world.definition_version,
                name=world.definition.name,
                artifact_version=world.definition.artifact_version,
                archetypes=world.definition.archetypes,
                skills=tuple(bound[name] for name in sorted(bound)),
            ),
        )

    def invoke(
        *,
        tenant: str,
        definition_key: str,
        definition_version: str,
        skill: str,
        arguments: dict[str, str],
    ) -> str:
        """The deployment's factory-path invocation — zero privileged paths.

        Constructs the agent through the Agent Factory against the live
        Control Plane (the only supported construction path, CLAUDE.md
        §6.4), dispatches the bound skill, and lands the decision in a
        replay record before anything returns (T-07-20).
        """
        if tenant != world.tenant:
            raise LookupError(f"unknown tenant {tenant!r}")
        definition_hash = content_hash(world.definition)
        agent = AgentFactory(
            control_plane=world.registry,
            callable_registry=world.callables,
        ).construct(
            definition_key=definition_key,
            definition_version=definition_version,
            bound_skills=world.ledger.bound_view(definition_hash),
        )
        invocation = agent.invoke_skill(skill, arguments=arguments)
        conditioning = agent.perspective_conditioning(
            principal_id=world.principal_id,
            grant_set_hash=world.ledger.grant_set_hash(definition_hash),
        )
        execution, product, perspective = replay_inputs(world)
        record = build_replay_record(
            execution=execution,
            product=product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(
                    key=world.definition.policy_regime.ref,
                    version=world.definition.artifact_version,
                ),
            ),
            assembly_mode="algorithmic",
            recorded_at=world.boundary,
            agent_conditioning=conditioning,
        )
        capability = writer.write_replay_record(record=record)
        return canonical_bytes(
            {
                "invocation": dict(invocation.output),
                "replay_record": canonical_bytes(record).decode("utf-8"),
                "replay_ref": {
                    "uri": capability.replay_ref.uri,
                    "content_address": capability.replay_ref.content_address,
                },
            }
        ).decode("utf-8")

    return build_experience_server(
        server_name=SERVER_NAME,
        product_resolver=resolve_product,
        agent_directory=directory,
        agent_invoker=invoke,
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
