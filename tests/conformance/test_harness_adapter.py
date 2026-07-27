"""The `HarnessAdapterProtocol` conformance suite — the bar for every adapter.

D-09 fixes the shape and rejects doubles deliberately: a double written to the
Protocol *we* designed can pass while the real SDK's surface disagrees, which
is exactly the failure this phase exists to prevent (CLAUDE.md §7.3 —
portability is demonstrated, not asserted). So every leg below drives **real
harness SDK objects along real SDK code paths**, with no model and no network
(``no_model_reachable`` below fails the run if either is attempted).

All three D-IMPL-24 harnesses are now params of :func:`harness_leg` — Claude
Agent SDK (06-12), LangGraph (06-13), Google ADK (06-14). **The test bodies did
not change as they joined**, which is the constraint every assertion here was
written under:

* Nothing below names a harness SDK type, imports one, or asserts on the
  concrete class of a carrier. The carriers three seams return are typed
  ``object`` on the Protocol precisely because they are harness-shaped; the
  suite inspects them through :func:`_carrier_strings` and
  :func:`_carrier_values`, which walk dataclasses, mappings, and sequences
  generically.
* The replay-hooks seam takes a *harness-native execution result*, so a single
  ``Callable[[capability], adapter]`` fixture cannot drive it. Each leg
  therefore supplies its own ``execution`` builder alongside its adapter
  factory, plus the values it will report — see :class:`HarnessLeg`.
* The effect capability is a factory *argument*, because a suite that could
  only observe ``governed`` adapters would never assert the D-10 inert path,
  and D-10 makes declaring ``unsupported`` only half the requirement.
* D-10's "the refusal actually fired" is a claim about each harness's **own**
  refusal hook, which no shared assertion could reach generically. So each leg
  supplies a :attr:`HarnessLeg.refusal` driver that pokes that hook and returns
  the harness-native refusal artifact, or ``None`` when the harness permitted.
  The harness-specific code stays in the leg; the assertion stays shared, and
  it is an inversion — an adapter whose declared ``unsupported`` did not
  actually stop anything fails on the refusal side, and one that refuses
  unconditionally fails on the permitted side.

Everything domain-specific — agent definitions, policy regimes, skill catalog
entries, grants, product classes, model identifiers — comes from
``tests/fixtures/banking``. This module holds mechanism only (CLAUDE.md §6.4).
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import socket
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

import pytest
import yaml

from agents.test_consumption_discipline import WRITE_SURFACE_NAMES
from ccf.agents.agent import Agent, EmittedEffect
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.errors import SkillNotBound
from ccf.agents.factory import AgentFactory
from ccf.agents.prompts import render_instruction
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.harness.protocol import (
    EFFECT_CAPABILITIES,
    EffectCapability,
    EffectRefusal,
    HarnessAdapterProtocol,
    HarnessCapabilities,
)
from ccf.graph.protocols import GraphView
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    NO_HARNESS,
    HarnessTrace,
    PolicyBinding,
    build_replay_record,
)
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.grants import GrantLedger, SkillGrant
from _pytest.outcomes import Failed, Skipped
from conftest import HARNESS_REQUIRED_ENV, harness_unavailable
from skills.sinks import ScriptedApprovalSink

pytestmark = [pytest.mark.conformance, pytest.mark.harness]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"

#: A harness module name no extra installs, used to drive the skip mechanism's
#: real code path (T-06-71). Deliberately not one of the three real harnesses:
#: those get installed as their legs land, and a probe that stops probing the
#: moment a leg arrives is the silently-green failure this guards against.
ABSENT_HARNESS = "ccf_no_such_harness_sdk"


# --- fixture material ---------------------------------------------------------


def _yaml(*parts: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FIXTURES.joinpath(*parts).read_text())
    return loaded


def _agent_fixture() -> dict[str, Any]:
    return _yaml("agents", "covenant_analytics.yaml")


def _prompt_fixture() -> dict[str, Any]:
    return _yaml("prompts", "covenant_summary.yaml")


def _tool_fixture() -> dict[str, Any]:
    return _yaml("skills", "covenant_metrics_tool.yaml")


def _grants_fixture() -> dict[str, Any]:
    return _yaml("skills", "grants.yaml")


def _harness_fixture() -> dict[str, Any]:
    """Per-harness drive values — model ids, server names, reported trace fields.

    A fixture file rather than module constants: a model identifier and an MCP
    server name are deployment vocabulary, and the suite asserting against
    literals it authored would be asserting against itself.
    """
    return _yaml("harnesses.yaml")


# --- the harness-agnostic carrier probe ---------------------------------------


def _carrier_values(carrier: object, *, _depth: int = 0) -> Iterator[object]:
    """Every value reachable inside a harness-native carrier, generically.

    Walks dataclass fields, ``__dict__``, mappings, and sequences. Written
    against no harness in particular so seam-1 assertions hold for a
    ``ClaudeAgentOptions``, an ADK instruction closure's captured state, and a
    LangGraph state channel alike. Depth-bounded: a carrier is a message, not
    an object graph to spider.
    """
    if _depth > 4:
        return
    yield carrier
    children: Sequence[object] = ()
    if is_dataclass(carrier) and not isinstance(carrier, type):
        children = [getattr(carrier, f.name, None) for f in fields(carrier)]
    elif isinstance(carrier, Mapping):
        children = [*carrier.keys(), *carrier.values()]
    elif isinstance(carrier, (list, tuple, set, frozenset)):
        children = list(carrier)
    elif hasattr(carrier, "__dict__") and not isinstance(carrier, type):
        children = list(vars(carrier).values())
    for child in children:
        yield from _carrier_values(child, _depth=_depth + 1)


def _carrier_strings(carrier: object) -> tuple[str, ...]:
    """Every string reachable inside a harness-native carrier."""
    return tuple(v for v in _carrier_values(carrier) if isinstance(v, str))


def _carried(carrier: object, needle: str) -> bool:
    """Whether ``needle`` reached the harness's context surface."""
    return any(needle in text for text in _carrier_strings(carrier))


# --- the world ----------------------------------------------------------------


class World:
    """One Control Plane, catalog, ledger, and two agents, built from fixtures.

    Two agents is the point (D-23): skill exposure computed over the shared
    catalog rather than over each agent's own grants passes with one agent and
    is wrong with two, and a per-adapter cache of "the" agent is invisible
    until a second one exists.
    """

    def __init__(self) -> None:
        agent_fixture = _agent_fixture()
        prompt_fixture = _prompt_fixture()
        grants_fixture = _grants_fixture()
        tool_fixture = _tool_fixture()

        # One injected instant, one shared audit log: the Control Plane is the
        # audit plane, singular (whitepaper §7.8.2), and nothing in the fabric
        # reads a clock.
        self.audit = AuditLog()
        self.registry = ControlPlaneRegistry(
            clock=lambda: BOUNDARY, audit_log=self.audit
        )
        self.prompt: PromptArtifact = _parsed(
            prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT
        )
        self.registry.register_typed(
            prompt_fixture["keys"]["prompt_artifact"], self.prompt, PROMPT_ARTIFACT
        )
        for reference in agent_fixture["referenced_artifacts"].values():
            self._register_declared(reference)
        for regime in grants_fixture["policy_regimes"].values():
            self._register_declared(regime)

        self.catalog = SkillCatalog(self.registry)
        for document in (
            tool_fixture["entry"],
            tool_fixture["variants"]["local_callable"],
        ):
            entry: SkillCatalogEntry = _parsed(document, SKILL_CATALOG_ENTRY)
            assert isinstance(self.catalog.register(entry), str)

        self.ledger = GrantLedger(
            control_plane=self.registry,
            catalog=self.catalog,
            audit=self.audit,
            sink=ScriptedApprovalSink(
                approve=True, approver_id=grants_fixture["approval"]["approver_id"]
            ),
            clock=lambda: BOUNDARY,
        )
        self.actor: str = grants_fixture["approval"]["requesting_actor"]

        # Agent one: the slice agent, which carries a real instruction binding.
        self.definition_a: AgentDefinition = _parsed(
            agent_fixture["agent_definition"], AGENT_DEFINITION
        )
        self.agent_a = self._construct(
            self.definition_a, agent_fixture["keys"]["agent_definition"]
        )
        # Agent two: a different declared agent under a different policy regime.
        self.definition_b: AgentDefinition = _parsed(
            grants_fixture["agents"]["auto"], AGENT_DEFINITION
        )
        self.agent_b = self._construct(
            self.definition_b, grants_fixture["policy_regimes"]["auto"]["key"] + "/agent"
        )

        self.grant_a = self._grant(
            agent_fixture["slice"]["granted_skill"]["grant"], self.definition_a
        )
        self.grant_b = self._grant(
            grants_fixture["grants"]["metrics_local"], self.definition_b
        )

    def _register_declared(self, reference: Mapping[str, Any]) -> None:
        artifact_class = declared_artifact_class(reference["class_id"])
        declared = parse_artifact(
            {
                "class_id": reference["class_id"],
                "semver": reference["semver"],
                "declaration": reference["declaration"],
            },
            artifact_class,
        )
        self.registry.register_typed(reference["key"], declared, artifact_class)

    def _construct(self, definition: AgentDefinition, key: str) -> Agent:
        version = self.registry.register_versioned(key, definition, AGENT_DEFINITION)
        assert isinstance(version, str)
        return AgentFactory(control_plane=self.registry).construct(
            definition_key=key,
            definition_version=version,
            bound_skills=self.ledger.bound_view(content_hash(definition)),
        )

    def _grant(
        self, document: Mapping[str, Any], definition: AgentDefinition
    ) -> SkillGrant:
        return SkillGrant(
            agent_definition_hash=content_hash(definition), **dict(document)
        )

    def bind(self, grant: SkillGrant, definition: AgentDefinition) -> str:
        outcome = self.ledger.request(grant, definition=definition, actor=self.actor)
        assert isinstance(outcome, str), outcome
        return outcome

    def instructions(self) -> tuple[str, ...]:
        """The pinned instructions, rendered exactly once, by the fabric.

        The adapter must consume these; re-resolving or re-rendering a prompt
        artifact inside an adapter would let two decisions under one agent
        version render different instructions (T-06-64).
        """
        binding = self.definition_a.instruction_bindings[0]
        values = _agent_fixture()["slice"]["granted_skill"]["arguments"]
        return (
            render_instruction(
                binding=binding,
                artifact=self.prompt,
                parameter_values={
                    "entity_name": values["entity_name"],
                    "as_of": BOUNDARY.isoformat(),
                },
            ),
        )


def _parsed(document: Mapping[str, Any], artifact_class: Any) -> Any:
    return parse_artifact(dict(document), artifact_class)


BOUNDARY = datetime.fromisoformat(_grants_fixture()["clock"]["start"])
EXPIRES = BOUNDARY + timedelta(hours=1)


def _product(definition: AgentDefinition) -> ContextProductContract:
    """A Context Product inside the agent's own context contract (axis 2)."""
    consumed = definition.context_contract.consumes[0]
    return ContextProductContract(
        schema_name=consumed.product_class,
        schema_version=consumed.schema_version,
        plan_id=_agent_fixture()["keys"]["agent_definition"],
        tenant_id=definition.tenant,
        temporal_boundary=BOUNDARY,
        expires_at=EXPIRES,
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"1.1.0"}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload=dict(_agent_fixture()["slice"]["effect_payload"]),
    )


def _execution(definition: AgentDefinition) -> ExecutionResult:
    """A minimal operator execution, so the record has real dimensions 1 and 5."""
    plan_id = _agent_fixture()["keys"]["agent_definition"]
    return ExecutionResult(
        plan_id=plan_id,
        operators_invoked=frozenset({"traversal.neighbors"}),
        steps=(
            ExecutionStep(
                operator_key="traversal.neighbors",
                category="traversal",
                parameter_hash="ph-1",
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(
            plan_id=plan_id, payload=dict(_agent_fixture()["slice"]["effect_payload"])
        ),
        view=GraphView(tenant_id=definition.tenant, as_of=BOUNDARY),
    )


# --- the parametrized leg -----------------------------------------------------

#: A factory for the adapter under test. Takes the effect capability the
#: produced adapter must declare, because a conformance suite that could only
#: observe ``governed`` adapters would never assert the D-10 inert path.
AdapterFactory = Callable[[EffectCapability], HarnessAdapterProtocol]


#: Drives a harness's **own** refusal hook for one bound skill and returns the
#: harness-native refusal artifact, or ``None`` when the harness permitted the
#: call. The only way D-10's "the refusal fired" can be asserted without a test
#: body naming ``PermissionResultDeny``, a short-circuit response dict, or a
#: graph state channel — the harness-specific poke lives in the leg, the
#: assertion stays shared.
RefusalDriver = Callable[[HarnessAdapterProtocol, Agent, str], object | None]


class HarnessLeg(NamedTuple):
    """One harness's entry into the suite.

    ``adapter`` is the :data:`AdapterFactory`. ``execution`` builds that
    harness's own execution result for the replay-hooks seam — the one seam a
    bare adapter factory cannot drive, because its input is harness-native by
    definition. ``reported_model`` and ``trace_id`` are what that execution
    reports, so the seam-4 assertion compares against the harness's own values
    rather than against anything CCF configured. ``refusal`` is the
    :data:`RefusalDriver` D-10 needs.
    """

    harness_id: str
    adapter: AdapterFactory
    execution: Callable[[], object]
    reported_model: str
    trace_id: str
    refusal: RefusalDriver


def substrate_digest(database_path: Path) -> str:
    """The L3 substrate under ``database_path``, byte for byte.

    Hashing the substrate rather than querying the graph is deliberate: a query
    only sees the rows a reader thought to ask about, while the digest covers
    every byte the substrate holds — including any a second writer would have
    added. **The write-ahead log is part of the substrate**: the SQLite backend
    runs in WAL mode, so a committed write lands in ``<db>-wal`` while the main
    file can stay byte-identical for a long time, and a digest over the main
    file alone would report "unchanged" after a real write. The shared-memory
    index is excluded — it is process coordination state, not durable content.

    The same reasoning, and the same exclusions, as the A2A leg's own digest
    (``tests/crossproc/test_a2a_exchange.py``). ``tests/invariants`` imports
    this one rather than writing a third.
    """
    digest = hashlib.sha256()
    for suffix in ("", "-wal"):
        candidate = database_path.with_name(database_path.name + suffix)
        digest.update(candidate.read_bytes() if candidate.exists() else b"")
    return digest.hexdigest()


#: Every harness leg the suite drives, in D-IMPL-24 order. Named once here so
#: that the portability proof (``test_harness_portability.py``) drives *the
#: same* set rather than its own copy: a leg added to one and not the other
#: would leave the portability claim quietly narrower than the conformance bar.
HARNESS_PARAMS = ("claude-agent", "adk", "langgraph")


def build_harness_leg(param: str) -> HarnessLeg:
    """Build one harness's leg by name, outside any fixture.

    Extracted from the ``harness_leg`` fixture by 06-15 with no change to a
    single leg's body. The portability proof has to hold *all three* legs at
    once — that is what it proves — and a parametrized fixture hands out one at
    a time by construction. Skips and required-harness failures still come from
    :func:`harness_unavailable`, so the skip mechanism is shared too.
    """
    if param == "claude-agent":
        harness_unavailable("claude_agent_sdk", param)
        from claude_agent_sdk import ModelUsage, PermissionResultDeny, ResultMessage

        from ccf_runtime.adapters.claude_agent import HARNESS_ID, ClaudeAgentAdapter

        values = _harness_fixture()[param]

        def adapter(effects: EffectCapability) -> HarnessAdapterProtocol:
            return ClaudeAgentAdapter(
                model=values["model"],
                mcp_server_name=values["mcp_server_name"],
                mcp_server_version=values["mcp_server_version"],
                effects=effects,
            )

        def execution() -> object:
            return ResultMessage(
                subtype=values["result_subtype"],
                duration_ms=0,
                duration_api_ms=0,
                is_error=False,
                num_turns=1,
                session_id=values["session_id"],
                usage={
                    "input_tokens": values["input_tokens"],
                    "output_tokens": values["output_tokens"],
                },
                model_usage={
                    values["reported_model"]: ModelUsage(
                        inputTokens=values["input_tokens"],
                        outputTokens=values["output_tokens"],
                        cacheReadInputTokens=0,
                        cacheCreationInputTokens=0,
                        webSearchRequests=0,
                        costUSD=0.0,
                        contextWindow=0,
                    )
                },
            )

        def refusal(
            under_test: HarnessAdapterProtocol, agent: Agent, skill_name: str
        ) -> object | None:
            """Poke the Claude Agent SDK's own permission hook (D-10 (b)).

            ``can_use_tool`` is the hook the harness consults before running a
            tool and the one it honours ``PermissionResultDeny`` from, so this
            is the harness refusing rather than CCF declining.
            """
            carrier = under_test.inject_context(
                agent=agent, products=(), instructions=()
            )
            gate = carrier.can_use_tool  # type: ignore[attr-defined]
            qualified = f"mcp__{values['mcp_server_name']}__{skill_name}"
            decision = asyncio.run(gate(qualified, {}, None))
            return decision if isinstance(decision, PermissionResultDeny) else None

        return HarnessLeg(
            harness_id=HARNESS_ID,
            adapter=adapter,
            execution=execution,
            reported_model=values["reported_model"],
            trace_id=values["session_id"],
            refusal=refusal,
        )
    if param == "adk":
        harness_unavailable("google.adk", param)

        from google.genai import types as adk_types

        from ccf_runtime.adapters.adk import (
            HARNESS_ID,
            MODEL_STATE_KEY,
            USAGE_STATE_KEY,
            AdkAdapter,
        )

        values = _harness_fixture()[param]

        def adk_adapter(effects: EffectCapability) -> HarnessAdapterProtocol:
            return AdkAdapter(
                model=values["model"],
                agent_name=values["agent_name"],
                session_id=values["session_id"],
                effects=effects,
            )

        def adk_execution() -> object:
            """A **real** ADK ``Runner`` run of the adapter's own vehicle.

            No model is configured anywhere: the adapter ships a ``BaseAgent``
            subclass whose ``_run_async_impl`` yields events, which is ADK's own
            sanctioned way to run something that is not a model call. The
            reported model and token counts are seeded onto ADK's session
            state, which is where the harness's own session machinery carries
            them into the run; the adapter never writes them and reads them
            only back off the event stream a run produced.
            """
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService

            carrier = adk_adapter("governed").inject_context(
                agent=World().agent_a, products=(), instructions=()
            )
            state = {
                **carrier.session_state,  # type: ignore[attr-defined]
                MODEL_STATE_KEY: values["reported_model"],
                USAGE_STATE_KEY: {
                    "input_tokens": values["input_tokens"],
                    "output_tokens": values["output_tokens"],
                },
            }

            async def run() -> tuple[object, ...]:
                sessions = InMemorySessionService()
                await sessions.create_session(
                    app_name=values["app_name"],
                    user_id=values["user_id"],
                    session_id=values["session_id"],
                    state=state,
                )
                runner = Runner(
                    agent=carrier.runnable,  # type: ignore[attr-defined]
                    app_name=values["app_name"],
                    session_service=sessions,
                )
                return tuple(
                    [
                        event
                        async for event in runner.run_async(
                            user_id=values["user_id"],
                            session_id=values["session_id"],
                            new_message=adk_types.Content(
                                role="user", parts=[adk_types.Part(text="")]
                            ),
                        )
                    ]
                )

            return asyncio.run(run())

        def adk_refusal(
            under_test: HarnessAdapterProtocol, agent: Agent, skill_name: str
        ) -> object | None:
            """Poke ADK's own before-tool hook (D-10 (b)).

            ADK treats any truthy mapping returned from ``before_tool_callback``
            as the tool's response and **does not call the tool**, so a returned
            mapping is the harness short-circuiting rather than CCF declining.
            """
            carrier = under_test.inject_context(
                agent=agent, products=(), instructions=()
            )
            harness_agent = carrier.llm_agent  # type: ignore[attr-defined]
            bound = {tool.name: tool for tool in harness_agent.tools}
            response = harness_agent.before_tool_callback(
                tool=bound[skill_name], args={}, tool_context=None
            )
            return response or None

        return HarnessLeg(
            harness_id=HARNESS_ID,
            adapter=adk_adapter,
            execution=adk_execution,
            reported_model=values["reported_model"],
            trace_id=values["session_id"],
            refusal=adk_refusal,
        )
    if param == "langgraph":
        harness_unavailable("langgraph", param)

        from ccf_runtime.adapters.langgraph import (
            HARNESS_ID,
            MODEL_METADATA_KEY,
            USAGE_METADATA_KEY,
            LangGraphAdapter,
        )

        values = _harness_fixture()[param]

        def lg_adapter(effects: EffectCapability) -> HarnessAdapterProtocol:
            return LangGraphAdapter(
                model=values["model"],
                thread_id=values["thread_id"],
                run_tags=tuple(values["run_tags"]),
                effects=effects,
            )

        def lg_execution() -> object:
            """A **real** run of the adapter's own compiled graph, no model.

            The one seam a bare adapter factory cannot drive, and for a
            topology-owning harness the topology under test is the adapter's,
            so this drives that — plain-function nodes, ``.invoke()``, no
            network. The reported model and token counts are merged into the
            run configuration's metadata under LangChain's own tracing keys,
            which is where a chat model would have written them; the adapter
            never writes them and reads them only back out of the run's final
            state.
            """
            carrier = lg_adapter("governed").inject_context(
                agent=World().agent_a, products=(), instructions=()
            )
            graph = carrier.graph  # type: ignore[attr-defined]
            config = dict(carrier.config)  # type: ignore[attr-defined]
            config["metadata"] = {
                **config["metadata"],
                MODEL_METADATA_KEY: values["reported_model"],
                USAGE_METADATA_KEY: {
                    "input_tokens": values["input_tokens"],
                    "output_tokens": values["output_tokens"],
                },
            }
            result: object = graph.invoke(
                carrier.state,  # type: ignore[attr-defined]
                config,
            )
            return result

        def lg_refusal(
            under_test: HarnessAdapterProtocol, agent: Agent, skill_name: str
        ) -> object | None:
            """Run the adapter-owned effect node (D-10 (b)).

            LangGraph has no loop to hook, so the refusal surface is the node
            the adapter built — and running the real compiled graph is what
            makes "the refusal fired" an observation of an execution rather
            than of a method call.
            """
            carrier = under_test.inject_context(
                agent=agent, products=(), instructions=()
            )
            final = carrier.graph.invoke(  # type: ignore[attr-defined]
                {
                    **carrier.state,  # type: ignore[attr-defined]
                    "output": dict(_agent_fixture()["slice"]["effect_payload"]),
                },
                carrier.config,  # type: ignore[attr-defined]
            )
            outcome = final.get("effect")
            return outcome if isinstance(outcome, EffectRefusal) else None

        return HarnessLeg(
            harness_id=HARNESS_ID,
            adapter=lg_adapter,
            execution=lg_execution,
            reported_model=values["reported_model"],
            trace_id=values["thread_id"],
            refusal=lg_refusal,
        )
    raise NotImplementedError(param)


@pytest.fixture(params=HARNESS_PARAMS)
def harness_leg(request: pytest.FixtureRequest) -> HarnessLeg:
    """One leg per harness — all three of D-IMPL-24's, as of 06-14."""
    return build_harness_leg(request.param)


@pytest.fixture
def world() -> World:
    return World()


@pytest.fixture(autouse=True)
def no_model_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the suite if anything opens a socket (D-09, T-06-72).

    The whole point of driving real SDK objects rather than doubles is that it
    stays free: no model is invoked and no ``claude`` CLI is spawned. A future
    change that quietly reaches a model would otherwise pass here and cost
    money on every CI run, so the absence is asserted rather than assumed.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the harness conformance suite attempted network egress; it must"
            " drive SDK objects in-process with no model (D-09)"
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


# --- the suite's own guarantees, asserted rather than assumed -----------------


def test_the_no_model_guard_is_actually_installed() -> None:
    """The autouse guard is only evidence if it fires (T-06-72).

    A monkeypatch that silently failed to apply would leave the suite looking
    exactly as green as one that works, while a future change reached a model
    on every CI run.
    """
    with pytest.raises(AssertionError, match="network egress"):
        socket.create_connection(("127.0.0.1", 9))
    with pytest.raises(AssertionError, match="network egress"):
        socket.socket().connect(("127.0.0.1", 9))


def test_an_absent_harness_skips_with_an_instruction_not_a_mystery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The skip message names the harness and the extra that enables it.

    Driven against a module that is genuinely absent rather than a mock, so
    this exercises the real code path. It was ``langgraph`` until 06-13
    installed it — a leg's own arrival must not be able to hollow out the
    mechanism that proves the other legs did not silently skip, so the probe
    is a name no extra will ever install.
    """
    monkeypatch.delenv(HARNESS_REQUIRED_ENV, raising=False)
    with pytest.raises(Skipped) as skipped:
        harness_unavailable(ABSENT_HARNESS, ABSENT_HARNESS)
    message = str(skipped.value)
    assert ABSENT_HARNESS in message
    assert "pip install -e" in message
    assert "harnesses" in message


def test_an_absent_harness_fails_when_the_environment_requires_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-06-71: a green build that skipped all three legs proved nothing.

    This is the test that stops the gate wave from signing off on a suite
    whose only evidence was skipped, and it mirrors ``CCF_REQUIRE_POSTGRES``
    exactly rather than inventing a second convention.
    """
    monkeypatch.setenv(HARNESS_REQUIRED_ENV, "1")
    with pytest.raises(Failed) as failed:
        harness_unavailable(ABSENT_HARNESS, ABSENT_HARNESS)
    assert HARNESS_REQUIRED_ENV in str(failed.value)
    assert not isinstance(failed.value, Skipped)


# --- structural conformance ---------------------------------------------------


def test_the_adapter_conforms_to_the_protocol_structurally(
    harness_leg: HarnessLeg,
) -> None:
    assert isinstance(harness_leg.adapter("governed"), HarnessAdapterProtocol)


def test_the_adapter_declares_a_known_effect_capability(
    harness_leg: HarnessLeg,
) -> None:
    """``effects`` is a declared value, never a missing field (D-IMPL-25)."""
    for capability in ("governed", "unsupported"):
        declared = harness_leg.adapter(capability).capabilities()
        assert isinstance(declared, HarnessCapabilities)
        assert declared.effects == capability
        assert declared.effects in EFFECT_CAPABILITIES
        assert declared.harness_id == harness_leg.harness_id


# --- seam 1: context injection ------------------------------------------------


def test_seam_1_carries_the_pinned_instructions_and_the_typed_product(
    harness_leg: HarnessLeg, world: World
) -> None:
    """The rendered instruction and the product reach the context surface."""
    product = world.agent_a.consume(_product(world.definition_a), now=BOUNDARY)
    instructions = world.instructions()
    carrier = harness_leg.adapter("governed").inject_context(
        agent=world.agent_a, products=(product,), instructions=instructions
    )
    assert _carried(carrier, instructions[0])
    assert _carried(carrier, canonical_bytes(product).decode("utf-8"))


def test_seam_1_hands_the_harness_no_fabric_write_surface(
    harness_leg: HarnessLeg, world: World
) -> None:
    """Nothing reachable from the carrier is or names a fabric write surface."""
    product = world.agent_a.consume(_product(world.definition_a), now=BOUNDARY)
    carrier = harness_leg.adapter("governed").inject_context(
        agent=world.agent_a, products=(product,), instructions=world.instructions()
    )
    for value in _carrier_values(carrier):
        assert type(value).__name__ not in WRITE_SURFACE_NAMES, value


def test_the_adapter_holds_no_fabric_write_surface(
    harness_leg: HarnessLeg, world: World
) -> None:
    """No attribute on the adapter is or names one either (T-06-67)."""
    adapter = harness_leg.adapter("governed")
    for name, member in inspect.getmembers(adapter):
        if name.startswith("__"):
            continue
        assert type(member).__name__ not in WRITE_SURFACE_NAMES, name
        assert not any(
            surface in repr(type(member)) for surface in WRITE_SURFACE_NAMES
        ), name


# --- seam 2: skill exposure ---------------------------------------------------


def test_seam_2_exposes_exactly_the_bound_skill_set(
    harness_leg: HarnessLeg, world: World
) -> None:
    """Set equality, not containment: an ungranted skill must not exist."""
    adapter = harness_leg.adapter("governed")
    assert set(adapter.expose_skills(agent=world.agent_a)) == set()

    world.bind(world.grant_a, world.definition_a)
    exposed = adapter.expose_skills(agent=world.agent_a)
    assert set(exposed) == set(world.agent_a.bound_skill_names)
    assert set(exposed) == {world.grant_a.skill_name}


def test_seam_2_follows_a_revocation_without_re_declaring_the_agent(
    harness_leg: HarnessLeg, world: World
) -> None:
    """Grant, expose, revoke, expose: the tool disappears (D-07)."""
    adapter = harness_leg.adapter("governed")
    identity_before = world.agent_a.identity

    grant_hash = world.bind(world.grant_a, world.definition_a)
    assert world.grant_a.skill_name in adapter.expose_skills(agent=world.agent_a)

    world.ledger.revoke(grant_hash, actor=world.actor)
    assert adapter.expose_skills(agent=world.agent_a) == ()
    assert set(adapter.expose_skills(agent=world.agent_a)) == set(
        world.agent_a.bound_skill_names
    )
    # The skill-set changed; the agent's identity did not (D-07).
    assert world.agent_a.identity == identity_before


def test_seam_2_is_per_agent_not_per_catalog_the_two_agent_case(
    harness_leg: HarnessLeg, world: World
) -> None:
    """D-23: two agents, one adapter, two different tool sets.

    Exposure computed over the shared catalog — which holds both entries —
    would pass every single-agent assertion above and be wrong here.
    """
    adapter = harness_leg.adapter("governed")
    world.bind(world.grant_a, world.definition_a)
    world.bind(world.grant_b, world.definition_b)

    exposed_a = set(adapter.expose_skills(agent=world.agent_a))
    exposed_b = set(adapter.expose_skills(agent=world.agent_b))
    assert exposed_a == {world.grant_a.skill_name}
    assert exposed_b == {world.grant_b.skill_name}
    assert exposed_a != exposed_b
    assert exposed_a.isdisjoint(exposed_b)
    # Neither agent can reach the other's skill, under any name.
    with pytest.raises(SkillNotBound):
        world.agent_a.invoke_skill(world.grant_b.skill_name)
    with pytest.raises(SkillNotBound):
        world.agent_b.invoke_skill(world.grant_a.skill_name)


def test_seam_2_does_not_leak_an_ungranted_catalog_entry_into_the_carrier(
    harness_leg: HarnessLeg, world: World
) -> None:
    """The registered-but-ungranted entry appears nowhere the harness can see."""
    adapter = harness_leg.adapter("governed")
    world.bind(world.grant_a, world.definition_a)
    product = world.agent_a.consume(_product(world.definition_a), now=BOUNDARY)
    carrier = adapter.inject_context(
        agent=world.agent_a, products=(product,), instructions=world.instructions()
    )
    assert not _carried(carrier, world.grant_b.skill_name)
    assert _carried(carrier, world.grant_a.skill_name)


# --- seam 3: effect capture ---------------------------------------------------


def test_seam_3_returns_a_governed_emission_as_a_typed_value(
    harness_leg: HarnessLeg, world: World
) -> None:
    """A harness output reaches L2 only as the value this seam returns."""
    payload = dict(_agent_fixture()["slice"]["effect_payload"])
    effect = harness_leg.adapter("governed").capture_effect(
        agent=world.agent_a, output=payload
    )
    assert isinstance(effect, EmittedEffect)
    assert effect.agent_definition_hash == world.agent_a.identity.definition_hash
    assert dict(effect.payload) == payload
    assert content_hash(effect)


def test_seam_3_refuses_when_the_adapter_declared_effects_unsupported(
    harness_leg: HarnessLeg, world: World
) -> None:
    """D-10: declaring ``unsupported`` is half the job; the refusal must fire."""
    adapter = harness_leg.adapter("unsupported")
    assert adapter.capabilities().effects == "unsupported"
    refusal = adapter.capture_effect(
        agent=world.agent_a, output=dict(_agent_fixture()["slice"]["effect_payload"])
    )
    assert isinstance(refusal, EffectRefusal)
    assert not isinstance(refusal, EmittedEffect)
    assert refusal.harness_id == harness_leg.harness_id
    assert refusal.agent_definition_hash == world.agent_a.identity.definition_hash
    assert refusal.reason
    assert content_hash(refusal)


def test_effects_unsupported_is_inert_not_merely_declared(
    harness_leg: HarnessLeg,
    world: World,
    fabric_boot: Callable[..., Any],
    tmp_path: Path,
) -> None:
    """D-10, in four parts, run for every harness.

    This is what makes ``effects: unsupported`` a *conformance-verified
    absence* rather than an opt-out with better branding. An adapter that
    declared ``unsupported`` while quietly permitting the effect passes none of
    (b); one that reached the graph anyway fails (c); one that could hand a
    write handle over fails (d). Removing any one part makes the test
    meaningfully weaker, so all four are here rather than spread across tests
    that could be deselected independently:

    (a) the capability is a **declared value on a required field**, not a
        missing field that defaulted into a claim;
    (b) the **harness's own** refusal hook fired — and, in inversion, did not
        fire for the same adapter declared ``governed``;
    (c) a real fabric's L3 substrate is byte-identical across the whole drive;
    (d) nothing on the adapter's public surface is or names a write surface.
    """
    database_path = tmp_path / "effects-unsupported.sqlite3"
    fabric_boot(database_path=database_path)
    before = substrate_digest(database_path)

    # (a) declared, and declarable only because the field is required.
    assert HarnessCapabilities.model_fields["effects"].is_required()
    adapter = harness_leg.adapter("unsupported")
    declared = adapter.capabilities()
    assert declared.effects == "unsupported"
    assert declared.effects in EFFECT_CAPABILITIES

    world.bind(world.grant_a, world.definition_a)
    skill_name = world.grant_a.skill_name

    # (b) the harness refused, and would not have refused under `governed`.
    refused = harness_leg.refusal(adapter, world.agent_a, skill_name)
    assert refused is not None, (
        "the harness's own refusal hook did not fire for an adapter declaring"
        " effects: unsupported — a declaration nothing enforces (D-10)"
    )
    permitted = harness_leg.refusal(
        harness_leg.adapter("governed"), world.agent_a, skill_name
    )
    assert permitted is None, (
        "the same hook refused under effects: governed too, so the refusal"
        " above is not evidence the declaration did anything"
    )

    # The Protocol seam agrees with the hook, rather than describing it.
    outcome = adapter.capture_effect(
        agent=world.agent_a, output=dict(_agent_fixture()["slice"]["effect_payload"])
    )
    assert isinstance(outcome, EffectRefusal)
    assert not isinstance(outcome, EmittedEffect)

    # (c) nothing reached L3, write-ahead log included.
    assert substrate_digest(database_path) == before, (
        "driving the effect path against a read-only binding changed the L3"
        " substrate (CLAUDE.md §10)"
    )

    # (d) no write handle was obtainable from the public surface.
    for name, member in inspect.getmembers(adapter):
        if name.startswith("__"):
            continue
        assert type(member).__name__ not in WRITE_SURFACE_NAMES, name


# --- seam 4: replay hooks -----------------------------------------------------


def test_seam_4_records_what_the_harness_reported(
    harness_leg: HarnessLeg, world: World
) -> None:
    trace = harness_leg.adapter("governed").replay_trace(
        execution=harness_leg.execution()
    )
    assert isinstance(trace, HarnessTrace)
    assert trace.harness_id == harness_leg.harness_id
    assert harness_leg.reported_model in trace.model_version
    assert trace.trace_id == harness_leg.trace_id
    assert trace.input_tokens > 0
    assert trace.output_tokens > 0
    assert trace.trace_provider != NO_HARNESS


def test_seam_4_reads_what_the_harness_carried_not_what_the_adapter_held(
    harness_leg: HarnessLeg,
) -> None:
    """The correlation values must be *in* the execution result, not beside it.

    An adapter that filled ``harness_trace`` from its own configuration would
    pass every assertion above while recording a claim no run ever made. So
    the same generic carrier walk the seam-1 assertions use is pointed at the
    execution result: the trace reference and the reported model have to be
    findable inside the thing the harness produced, and the trace the adapter
    derives from it has to agree with them.

    For a callback-shaped harness this is a vendor result object; for a
    topology-owning one it is the final state of a real run, and the values
    got there by travelling through that harness's own run-configuration
    machinery. Both are the same claim, which is why this assertion names
    neither.
    """
    execution = harness_leg.execution()
    carried = _carrier_strings(execution)
    assert any(harness_leg.trace_id in text for text in carried)
    assert any(harness_leg.reported_model in text for text in carried)

    trace = harness_leg.adapter("governed").replay_trace(execution=execution)
    assert trace.trace_id == harness_leg.trace_id
    assert harness_leg.reported_model in trace.model_version


def test_seam_4_cannot_touch_a_governed_replay_dimension(
    harness_leg: HarnessLeg, world: World
) -> None:
    """T-06-62: harness values land in ``harness_trace`` and nowhere else.

    Built without an operator execution, so the comparison is between two
    records that differ only in the harness block.
    """
    trace = harness_leg.adapter("governed").replay_trace(
        execution=harness_leg.execution()
    )
    common: dict[str, Any] = {
        "execution": _execution(world.definition_a),
        "product": _product(world.definition_a),
        "perspective": Perspective(
            principal_id=world.actor, role=world.definition_a.perspective.role
        ),
        "policy_bindings": (PolicyBinding(key="policy.bundle", version="1.1.0"),),
        "assembly_mode": "algorithmic",
        "recorded_at": BOUNDARY,
        "agent_conditioning": world.agent_a.perspective_conditioning(
            principal_id=world.actor,
            grant_set_hash=world.ledger.grant_set_hash(
                world.agent_a.identity.definition_hash
            ),
        ),
    }
    with_trace = build_replay_record(harness_trace=trace, **common)
    without = build_replay_record(harness_trace=None, **common)

    assert with_trace.model_version.harness_trace == trace
    assert with_trace.model_version.assembly_mode == without.model_version.assembly_mode
    assert with_trace.model_version.model_version == without.model_version.model_version
    for dimension in (
        "context_fabric_snapshot",
        "policy_bindings",
        "perspective_conditioning",
        "content_generation_path",
    ):
        assert getattr(with_trace, dimension) == getattr(without, dimension)
