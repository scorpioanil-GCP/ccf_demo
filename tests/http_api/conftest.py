"""Shared fabric for the HTTP API skeleton tests (07-10; EXPR-03).

One Control Plane, one grant ledger, one workflow engine, one HITL
transport, one artifact store — every handle the
:class:`ccf_runtime.http_api.dependencies.ApiDependencies` bundle carries,
built from the banking fixture artifacts (CLAUDE.md §6.4: everything
domain-specific comes from ``tests/fixtures/banking/``; delete the fixtures
and these tests have nothing to serve).

The app under test is exercised through httpx's in-process ASGI transport —
no server is ever hosted (the app is built, never bound; T-06-14 applied to
HTTP).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    TaskDefinition,
)
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.gates import ServableProduct
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    DecisionReplayRecord,
    PerspectiveConditioning,
    PolicyBinding,
    build_replay_record,
)
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.grants import GrantLedger
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.mcp.egress import ProductNotServable
from ccf_runtime.workflow.engine import WorkflowEngine
from skills.sinks import ScriptedApprovalSink

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _load(relative: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / relative).read_text())
    return loaded


def _register_declared(
    registry: ControlPlaneRegistry, references: dict[str, Any]
) -> None:
    for reference in references.values():
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


def _register_covenant_closure(plane: ControlPlaneRegistry) -> None:
    """Register everything the covenant-review workflow's refs resolve to."""
    prompt_fixture = _load("prompts/covenant_summary.yaml")
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    plane.register_typed(
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    agent_fixture = _load("agents/covenant_analytics.yaml")
    _register_declared(plane, agent_fixture["referenced_artifacts"])
    agent = parse_artifact(agent_fixture["agent_definition"], AGENT_DEFINITION)
    assert isinstance(agent, AgentDefinition)
    task_fixture = _load("tasks/covenant_review_task.yaml")
    plane.register_versioned(
        task_fixture["keys"]["referenced_agent_definition"],
        agent,
        AGENT_DEFINITION,
    )
    _register_declared(plane, task_fixture["referenced_artifacts"])
    task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    workflow_fixture = _load("workflows/covenant_review_workflow.yaml")
    plane.register_versioned(
        workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
    )
    _register_declared(plane, workflow_fixture["referenced_artifacts"])


def _register_refresh_closure(plane: ControlPlaneRegistry) -> None:
    """Register the straight-line certificate-refresh workflow's closure."""
    task_fixture = _load("tasks/certificate_refresh_task.yaml")
    _register_declared(plane, task_fixture["referenced_artifacts"])
    task = parse_artifact(task_fixture["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    workflow_fixture = _load("workflows/certificate_refresh_workflow.yaml")
    plane.register_versioned(
        workflow_fixture["keys"]["task_definition"], task, TASK_DEFINITION
    )


def _register_workflow(
    plane: ControlPlaneRegistry, workflow_fixture: str
) -> tuple[str, str]:
    fixture = _load(workflow_fixture)
    definition = parse_artifact(
        fixture["workflow_definition"], WORKFLOW_DEFINITION
    )
    assert isinstance(definition, WorkflowDefinition)
    key = fixture["keys"]["workflow_definition"]
    version = plane.register_versioned(key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return key, version


def _ticking_clock() -> Callable[[], datetime]:
    """A deterministic injected clock — no wall clock in any test path."""
    state = {"now": datetime(2026, 7, 30, tzinfo=UTC)}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


class _Bindings:
    """Injected node bindings — the deployment seam, stubbed for tests."""

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        return {}

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        return {}


class _PermissiveDebt:
    """A non-breaching DebtAssessmentBinding stub (07-17; INV-CH7-68)."""

    async def assess(
        self, *, tenant: str, step_name: str, ref: str
    ) -> DebtAssessment:
        return DebtAssessment(
            debt=Decimal("0"),
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal("1"),
                completeness=Decimal("1"),
                semantic_consistency=Decimal("1"),
            ),
        )


def _replay_record() -> DecisionReplayRecord:
    """A complete five-dimension record, threaded from fixture-shaped values."""
    boundary = datetime(2026, 2, 1, tzinfo=UTC)
    execution = ExecutionResult(
        plan_id="plan-1",
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(plan_id="plan-1", payload={"k": "v"}),
        view=GraphView(tenant_id="acme-bank", as_of=boundary),
    )
    product = ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id="acme-bank",
        temporal_boundary=boundary,
        expires_at=datetime(2026, 4, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=boundary,
        ),
        payload={"k": "v"},
    )
    return build_replay_record(
        execution=execution,
        product=product,
        perspective=Perspective(principal_id="principal-1", role="analyst"),
        policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
        assembly_mode="algorithmic",
        recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
        agent_conditioning=PerspectiveConditioning(
            principal_id="principal-1",
            role="analyst",
            delegation_chain=("workflow:acme-bank/e-replay",),
        ),
        workflow_step_sequence="[]",
    )


class Fabric:
    """Every injected handle the API bundle carries, plus test bookkeeping."""

    def __init__(self, root: Path) -> None:
        self.clock = _ticking_clock()
        self.audit = AuditLog()
        self.registry = ControlPlaneRegistry(
            clock=self.clock, audit_log=self.audit
        )
        _register_covenant_closure(self.registry)
        _register_refresh_closure(self.registry)
        self.covenant = _register_workflow(
            self.registry, "workflows/covenant_review_workflow.yaml"
        )
        self.refresh = _register_workflow(
            self.registry, "workflows/certificate_refresh_workflow.yaml"
        )

        # -- skilling material (grants fixture) ------------------------------
        grants_fixture = _load("skills/grants.yaml")
        self.grants_fixture = grants_fixture
        for regime in grants_fixture["policy_regimes"].values():
            artifact_class = declared_artifact_class(regime["class_id"])
            declared = parse_artifact(
                {
                    "class_id": regime["class_id"],
                    "semver": regime["semver"],
                    "declaration": regime["declaration"],
                },
                artifact_class,
            )
            self.registry.register_typed(
                regime["key"], declared, artifact_class
            )
        self.catalog = SkillCatalog(self.registry)
        tool_fixture = _load("skills/covenant_metrics_tool.yaml")
        for document in (
            tool_fixture["entry"],
            *grants_fixture["skills"].values(),
        ):
            entry = parse_artifact(document, SKILL_CATALOG_ENTRY)
            assert isinstance(entry, SkillCatalogEntry)
            outcome = self.catalog.register(entry)
            assert isinstance(outcome, str)
        self.sink = ScriptedApprovalSink(
            approve=True,
            approver_id=grants_fixture["approval"]["approver_id"],
        )
        self.ledger = GrantLedger(
            control_plane=self.registry,
            catalog=self.catalog,
            audit=self.audit,
            sink=self.sink,
            clock=self.clock,
        )
        self.actor: str = grants_fixture["approval"]["requesting_actor"]
        auto_agent = parse_artifact(
            grants_fixture["agents"]["auto"], AGENT_DEFINITION
        )
        assert isinstance(auto_agent, AgentDefinition)
        self.auto_agent = auto_agent
        self.auto_agent_key = f"{auto_agent.tenant}/agents/{auto_agent.name}"
        version = self.registry.register_versioned(
            self.auto_agent_key, auto_agent, AGENT_DEFINITION
        )
        assert isinstance(version, str)
        self.auto_agent_version = version

        # -- runtime substrates ---------------------------------------------
        self.store = FileArtifactStore(root=root / "artifacts")
        self.hitl = InMemoryHitlTransport()
        self.engine = WorkflowEngine(
            control_plane=self.registry,
            artifact_store=self.store,
            hitl_transport=self.hitl,
            skill_binding=_Bindings(),
            agent_binding=_Bindings(),
            clock=self.clock,
            debt_binding=_PermissiveDebt(),
        )
        self.factory = WorkflowFactory(control_plane=self.registry)

        # -- a stored replay record the replay noun resolves ----------------
        self.replay_record = _replay_record()
        self.replay_ref: ArtifactRef = self.store.put(
            tenant_id="acme-bank",
            artifact_class="ccf.decision-replay-record",
            name="e-replay",
            artifact=self.replay_record,
        )

        # -- one gate-admitted product the product noun serves --------------
        from crossproc.servers.mcp_egress_child import build_servable_product

        assembled = build_servable_product(
            database_path=root / "product-fabric.sqlite3"
        )
        self.product_address = assembled.address
        servable = assembled.servable
        served = assembled.served

        # Every call the widened D-IMPL-108 seam receives, in order — so a
        # test can assert on the *value* the door forwarded rather than only
        # on the status code the caller saw. A door that had passed some
        # other perspective, or re-derived one, would be indistinguishable
        # from a correct one at the response body.
        self.resolver_calls: list[tuple[Perspective, Any]] = []
        #: The one gate-admitted product this fabric serves, exposed so a
        #: test can compare served bytes against it without calling the
        #: resolver (which now requires an authorized perspective).
        self.product_servable = servable
        #: The same vessel SERVED — its record appended, its reference carried —
        #: which is the only served shape a door releases (`D-IMPL-260` P-A).
        self.product_served = served

        def resolver(
            *,
            tenant: str,
            product_class: str,
            version: str,
            perspective: Perspective,
            request: Any,
        ) -> Any:
            self.resolver_calls.append((perspective, request))
            address = assembled.address
            if (tenant, product_class, version) == (
                address.tenant,
                address.product_class,
                address.version,
            ):
                return served
            raise ProductNotServable(
                f"no gate-admitted product at {tenant}/{product_class}/"
                f"{version}"
            )

        self.product_resolver = resolver


@pytest.fixture(scope="module")
def fabric(tmp_path_factory: pytest.TempPathFactory) -> Fabric:
    return Fabric(tmp_path_factory.mktemp("http-api"))


@pytest.fixture(scope="module")
def app(fabric: Fabric) -> Any:
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    return create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        # This fixture is about the routes, not the posture; the D-IMPL-73
        # warning has its own dedicated suite (test_insecure_default_warning).
        acknowledge_insecure_default=True,
    )


def call(app: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
    """One in-process ASGI request — no server hosting, ever."""

    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(go())
