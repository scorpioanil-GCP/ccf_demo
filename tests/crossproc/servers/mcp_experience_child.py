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
from datetime import UTC, datetime
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
    AssemblyMode,
    ContextProductContract,
    ProductLineage,
)
from ccf.products.gates import ServableProduct  # noqa: E402
from ccf.products.request import ProductRequest  # noqa: E402
from ccf.products.resolver import ReplayRefusalRecorder  # noqa: E402
from ccf.projection.engine import ExecutionResult, ExecutionStep  # noqa: E402
from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
from ccf.replay.record import (  # noqa: E402
    PolicyBinding,
    ResolutionNotApplicable,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, ServedProduct  # noqa: E402
from ccf.skills.callables import CallableRegistry  # noqa: E402
from ccf.skills.catalog import (  # noqa: E402
    SKILL_CATALOG_ENTRY,
    SkillCatalog,
    SkillCatalogEntry,
)
from ccf.skills.grants import GrantLedger, SkillGrant  # noqa: E402
from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition  # noqa: E402
from ccf.products.entitlement import (  # noqa: E402
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf_runtime.authz.product_entitlement import (  # noqa: E402
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.mcp.auth import (  # noqa: E402
    FileTokenSource,
    SourceBackedTokenVerifier,
    TokenGrant,
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

#: The tool prose this test deployment supplies to the builder — deployment
#: values like ``SERVER_NAME`` (the module authors none of its own; CINV-01).
GET_CONTEXT_DESCRIPTION = "Serve this deployment's assembled banking product"
GET_LINEAGE_DESCRIPTION = "Serve the assembled product's lineage"
GET_REPLAY_RECORD_DESCRIPTION = "Serve the most recent decision replay record"

#: The front door's entitlement policy version lane. A fixture value.
ENTITLEMENT_POLICY_VERSION = "1.0.0"

#: A second recognised credential whose principal the entitlement policy
#: deliberately does not declare, so the parent can prove that a *verified*
#: caller is still refused. Authentication is not entitlement, and a suite
#: with only one token cannot show the difference.
UNENTITLED_TOKEN = "ccf-experience-unentitled-token"
UNENTITLED_CLIENT_ID = "ccf-experience-unentitled-client"

#: The instant the child's authz audit events carry. Injected, never read
#: from a wall clock. Under ``D-IMPL-256`` (1) this is also the instant every
#: recorded denial at this door carries: the governed step reads the
#: entitlement source's declared clock ONCE, so the audit event and the replay
#: record of one determination cannot disagree about when it was reached.
AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)

#: The assembly mode dimension 3 of this deployment's records carries — the
#: same value the agent invoker below writes. A deployment value (CINV-01).
ASSEMBLY_MODE: AssemblyMode = "algorithmic"


def experience_refusal_recorder(
    *,
    store: FileArtifactStore,
    tenant: str,
    disclosure_level_for: Any,
) -> ReplayRefusalRecorder:
    """The recorder this deployment's experience door is built with.

    ``D-IMPL-256`` (2): an entitling delivery boundary holds a recorder from
    construction or it is not built. Composed exactly as
    :func:`~ccf.products.resolver.build_governed_resolver` composes its own —
    **one store, one writer class, one record form** — over the very
    ``replay_store`` this child already stands up for the agent leg's replay
    records. A second store here would be the second-class replay
    ``D-IMPL-253`` Q13 forbids, and it would leave two halves of one
    deployment's audit trail in two directories.

    Shared with the parent (``tests/crossproc/test_experience_edge.py``) on the
    same terms as :func:`build_world` and ``build_servable_product``: two
    copies of a recorder's wiring would agree only until someone edited one.
    """
    return ReplayRefusalRecorder(
        artifact_store=store,
        replay_record_class=REPLAY_ARTIFACT_CLASS,
        tenant_id=tenant,
        assembly_mode=ASSEMBLY_MODE,
        # No bundle key at a delivery boundary, and saying so positively is
        # the honest posture: the record's bindings are exactly what the
        # determination pinned.
        policy_bundle_pin=None,
        disclosure_level_for=disclosure_level_for,
    )


def authorized_http_client(token: str = DEV_TOKEN) -> httpx.AsyncClient:
    """An HTTP client presenting ``token`` as a bearer credential."""
    return httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"})


def write_token_file(*, workspace: Path, tenants: frozenset[str]) -> Path:
    """Write the child's token file and return its path.

    Two credentials, both genuinely recognised: one whose principal the
    entitlement policy declares, one whose principal it does not. The second
    exists so the parent can show that verification and entitlement are two
    different decisions.
    """
    token_file = workspace / TOKEN_FILENAME
    token_file.write_text(
        json.dumps(
            {
                # Both credentials carry the SAME tenants, because what this
                # child exists to demonstrate is that verification and
                # entitlement are two different decisions (`SEC-018` is a
                # third). An unentitled caller refused for *tenancy* would go
                # red for the wrong reason and stop testing the subject.
                DEV_TOKEN: {
                    "client_id": CLIENT_ID,
                    "scopes": [SCOPE],
                    "tenants": sorted(tenants),
                },
                UNENTITLED_TOKEN: {
                    "client_id": UNENTITLED_CLIENT_ID,
                    "scopes": [SCOPE],
                    "tenants": sorted(tenants),
                },
            }
        ),
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


def build_server(
    *, workspace: Path, tool_allowlist: frozenset[str] | None = None
) -> FastMCP:
    """Assemble the product, the agent world, and the experience server.

    ``tool_allowlist`` passes straight through to the builder so the parent
    can assert registration-time omission (D-IMPL-74's D-05 leg) against a
    server otherwise identical to the default-built one.
    """
    assembled = build_servable_product(
        database_path=workspace / "experience-child.sqlite3"
    )
    world = build_world()
    replay_store = FileArtifactStore(root=workspace / REPLAY_DIRNAME)
    writer = ReplayWriter(
        store=replay_store, artifact_class=REPLAY_ARTIFACT_CLASS
    )
    latest_record: dict[str, str | None] = {"record": None}

    def resolve_product(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> ServedProduct:
        """Serve exactly the one assembled address; refuse anything else."""
        requested = ProductAddress(
            tenant=tenant, product_class=product_class, version=version
        )
        if requested != assembled.address:
            raise ExperienceProductNotServable(str(requested))
        return assembled.served

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
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            agent_conditioning=conditioning,
        )
        capability = writer.write_replay_record(record=record)
        latest_record["record"] = canonical_bytes(record).decode("utf-8")
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

    def provide_context(
        *, tenant: str, entity: str, perspective: Perspective
    ) -> str:
        """Serve the one assembled product for its own tenant (T-07-21).

        ``perspective`` arrives because ``D-IMPL-128`` limb 1 widened the seam
        so the door forwards what it authorized. This provider **uses** it
        rather than merely accepting it: the product was assembled under one
        declared capacity, so a perspective that is not that one is refused —
        a provider that took the conditioning and served regardless would put
        ``DI-15.5-03``'s gap back one layer down, where nothing on the wire
        would show it. The consequence the parent leans on: a served call over
        the wire is itself evidence that the right role arrived.
        """
        if perspective.role != assembled.role:
            raise ExperienceProductNotServable(
                f"{tenant}/{entity}: assembled for {assembled.role!r}, the"
                f" door authorized {perspective.role!r}"
            )
        if tenant != assembled.address.tenant:
            raise ExperienceProductNotServable(f"{tenant}/{entity}")
        return canonical_bytes(assembled.servable.product).decode("utf-8")

    def provide_lineage() -> str:
        """Serve the assembled product's lineage as canonical JSON."""
        return canonical_bytes(assembled.servable.product.lineage).decode(
            "utf-8"
        )

    def read_replay_record() -> str:
        """Serve the most recent record the invoker landed, or refuse."""
        record = latest_record["record"]
        if record is None:
            raise ExperienceProductNotServable(
                "no decision has been recorded yet"
            )
        return record

    # The front door's governance. Registration is adopter code: no manifest
    # can name ``ccf.product-entitlement-policy``, so this composition root
    # registers it against the real contract. The permitted class is the one
    # the fabric actually assembled and the permitted role is the one the
    # assembly conditioned on, so an entitlement cannot name something this
    # deployment does not serve.
    door_registry = ControlPlaneRegistry()
    door_registry.register_typed(
        product_entitlement_key(tenant_id=assembled.address.tenant),
        ProductEntitlementPolicy(
            tenant_id=assembled.address.tenant,
            policy_version=ENTITLEMENT_POLICY_VERSION,
            principals={
                CLIENT_ID: ProductEntitlementGrant(
                    permitted_schema_names=frozenset(
                        {assembled.address.product_class}
                    ),
                    permitted_roles=frozenset({assembled.role}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )

    def resolve_perspective(
        *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        """This deployment's role derivation — its statement, not the SDK's.

        The subject is the verified ``client_id``, never a caller's claim.
        Whatever this returns is still checked against the principal's grant
        before a product is resolved.
        """
        return Perspective(
            principal_id=grant.client_id,
            role=requested_role if requested_role is not None else assembled.role,
        )

    entitlement_source = ControlPlaneProductEntitlementSource(
        control_plane=door_registry, clock=lambda: AUDIT_INSTANT
    )

    return build_experience_server(
        server_name=SERVER_NAME,
        product_resolver=resolve_product,
        entitlement_source=entitlement_source,
        perspective_resolver=resolve_perspective,
        # `D-IMPL-256` (2): this door entitles on three paths, so it holds a
        # recorder from construction. Over `replay_store` — the store the
        # agent leg already writes its records to — so one deployment keeps
        # one audit trail rather than two.
        refusal_recorder=experience_refusal_recorder(
            store=replay_store,
            tenant=assembled.address.tenant,
            disclosure_level_for=entitlement_source.disclosure_level_for,
        ),
        # The gated consumption tools' declared address (D-IMPL-128 limb 1).
        # The same two values the policy above is keyed and granted on, so
        # the entitlement cannot name something this deployment does not
        # serve — and never a literal.
        entitled_product_class=assembled.address.product_class,
        lineage_tenant=assembled.address.tenant,
        agent_directory=directory,
        agent_invoker=invoke,
        context_provider=provide_context,
        lineage_provider=provide_lineage,
        replay_record_reader=read_replay_record,
        get_context_description=GET_CONTEXT_DESCRIPTION,
        get_lineage_description=GET_LINEAGE_DESCRIPTION,
        get_replay_record_description=GET_REPLAY_RECORD_DESCRIPTION,
        # The tool carries no arguments, so its tenant is declared rather than
        # named by the caller (`SEC-018`).
        replay_record_tenant=world.tenant,
        tool_allowlist=tool_allowlist,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=write_token_file(
                workspace=workspace,
                # This child serves TWO tenants: the agent world's and the
                # assembled product's. They coincide in the shipped fixture,
                # and the union is passed rather than either one so that a
                # fixture change separating them does not silently lock the
                # credential out of half this server (`SEC-018`).
                tenants=frozenset(
                    {
                        world.tenant,
                        assembled.address.tenant,
                        # # The neighbouring tenant is in the credential DELIBERATELY. These
                        # suites test what the ENTITLEMENT (and the per-tenant queue
                        # partition) decides about a tenant the caller can reach; a
                        # credential stopped by the tenancy floor first would make the
                        # entitlement untested. The floor itself is proven in
                        # `tests/mcp/test_tenant_guard.py`, against these same shipped
                        # servers (`SEC-018`).
                        f"{world.tenant}-not-this-one",
                        f"{assembled.address.tenant}-not-this-one",
                    }
                ),
            ))
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
