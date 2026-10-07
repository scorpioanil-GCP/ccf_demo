"""`LangGraphAdapter` — the LangGraph binding of the four seams (XPRC-03).

SDK-defined extension (CLAUDE.md §7.3; D-IMPL-24, D-IMPL-25). The whitepaper
specifies no harness binding; §7.3 does, and this is the second of its v0
reference implementations. Structural conformance to
:class:`~ccf.harness.protocol.HarnessAdapterProtocol` is the contract, and the
same factory-parametrized suite that accepts the Claude Agent SDK adapter is
the acceptance bar — one suite, two params, no assertion loosened for either
(D-09).

**This adapter owns the execution topology, and that is the whole point of
binding it second.** The Claude Agent SDK and Google ADK expose callbacks into
a loop *they* own; LangGraph has no loop to hook — the caller builds the graph.
06-11 shaped the seams as *translations producing harness-native carriers*
rather than as callback registrations precisely so this case would fit, and
research assumption A4 named this adapter as the real test of that bet. So the
seams here are called from *inside* nodes this module constructs: seam 3 is a
node body, seam 4 reads what a node captured. A callback-shaped Protocol would
have forced this module to fake a loop LangGraph does not have.

**One tool, two seams, never conflated (D-IMPL-17).** This module binds the
CLAUDE.md §7.3 *agent-loop* seams and nothing else. LangGraph used as an
orchestrator — durable multi-step workflow execution, external-engine
integration behind the orchestration Protocol — is a **distinct** integration,
belongs to the Orchestration Layer (CLAUDE.md §8.1), and is **out of scope for
Phase I.3: it is Phase I.4 orchestration scope.** The graph this module builds
is a harness-seam artifact, not an orchestration integration, and a reader who
mistakes one for the other would let a workflow inherit agent-loop trust
assumptions it was never granted (T-06-76).

**What this adapter cannot do.** It cannot write to the graph. It holds no
graph write handle, no graph read handle, no graph store, no fabric boot
handle, and no Control Plane registry — none of them is a constructor
parameter, an attribute, or a name anywhere in this module, which the
conformance suite pins by source scan in the same discipline
``tests/harness/test_protocol.py`` applies to the seam itself: a fabric surface
named in a comment or a docstring is a surface someone was thinking about
handing to an adapter (T-06-61). Owning the topology does not widen this: the
effect node returns a typed value into a state channel and reaches L2 only as
the value :meth:`LangGraphAdapter.capture_effect` returned, produced by
:meth:`ccf.agents.agent.Agent.emit_effect`. Carrying that value onward is L2's
job and nobody else's (single-writer, CLAUDE.md §10, §7.3 seam 3).

Scoped claims, not architectural boasts (D-21):

* **Protocol-shape-enforced.** No method on
  :class:`~ccf.harness.protocol.HarnessAdapterProtocol` accepts a fabric object
  other than :class:`~ccf.agents.agent.Agent`, so an adapter typed against it
  cannot receive one. This adapter's constructor takes deployment configuration
  only and holds no fabric object at all — the bound agent arrives per seam
  call (D-23).
* **Lint-enforced.** ``cinv02-harness`` denies ``langgraph`` in every module
  outside ``ccf_runtime.adapters.*`` (D-IMPL-53). This module is inside that
  carve-out and the carve-out was not widened to admit it.
* **Conformance-enforced.** The shared suite asserts set equality between the
  exposed tool names and ``agent.bound_skill_names`` across a grant/revoke
  round trip and across two agents (T-06-73), scans this object's public
  surface against the shared write-surface name list (T-06-74), and drives the
  ``unsupported`` effect branch to prove the refusal fires (D-10).

**Prompt artifacts are consumed, never re-resolved.** ``instructions`` arrive
at seam 1 already rendered by :func:`ccf.agents.prompts.render_instruction`
from the artifacts the Agent Factory pinned. This module resolves no URI, reads
no template, and calls no renderer (T-06-64).

**This module claims no algorithmic-mode tag, deliberately.** Adapters bind a
harness that reaches a model, so they are the semantic boundary of the
Algorithmic ⇄ Semantic Alternation, not an algorithmic module.

Imports name ``langgraph.graph``, ``langgraph.prebuilt``, and
``langchain_core`` explicitly: the top-level ``langgraph`` namespace exports
nothing.

Citation: CLAUDE.md §7.3 (SDK-defined extension), §6.2 channel 2 (skill
exposure), §8.1 and §10 (the orchestration boundary and single-writer);
D-IMPL-17 (the two-seam disambiguation); D-IMPL-24 (LangGraph as a v0
reference target); D-IMPL-25 (seam scope); D-IMPL-53 (the lint carve-out);
D-IMPL-55 (the replay slot seam 4 writes into).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from ccf.agents.agent import Agent, EmittedEffect
from ccf.contracts.canonical import canonical_bytes
from ccf.harness.protocol import EffectCapability, EffectRefusal, HarnessCapabilities
from ccf.products.contract import ContextProductContract
from ccf.replay.record import NO_HARNESS, HarnessTrace
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.toolsurface import HARNESS_EXPOSABLE_SKILL_TYPES, render_tool_surface

__all__ = [
    "AGENT_HASH_METADATA_KEY",
    "HARNESS_ID",
    "MODEL_METADATA_KEY",
    "USAGE_METADATA_KEY",
    "HarnessState",
    "LangGraphAdapter",
    "LangGraphCarrier",
]

#: This adapter's stable harness identity. Lands verbatim in
#: :attr:`~ccf.harness.protocol.HarnessCapabilities.harness_id` and in
#: :attr:`~ccf.replay.record.HarnessTrace.harness_id`. A mechanism identifier
#: naming the package this module binds — not a deployment value, which is why
#: every genuinely deployment-owned value (model, thread, tags, effect
#: capability) is a constructor argument instead.
HARNESS_ID = "langgraph"

#: The run-metadata key the harness itself populates with the model a chat
#: model actually ran, by LangChain's own tracing convention. Read at seam 4,
#: never written here: the fabric records what it invoked and the harness
#: records what it invoked, and writing this one from the configured model
#: would be exactly how a harness overwrites a governed claim (T-06-62). Absent
#: when no model ran, in which case the positive sentinel stands.
MODEL_METADATA_KEY = "ls_model_name"

#: The run-metadata key carrying the harness's own token accounting, by the
#: same convention. Read at seam 4, never written here.
USAGE_METADATA_KEY = "usage_metadata"

#: The correlation key this adapter *does* set, at seam 1, so that what the
#: harness carried through its own configuration machinery is identifiable in
#: the state a run produces. It identifies the agent version a run was
#: conditioned on; it is not a replay claim.
AGENT_HASH_METADATA_KEY = "ccf_agent_definition_hash"

#: Node names in the adapter-owned topology. Mechanism vocabulary — the names
#: of this module's own three nodes — not deployment values: a deployment
#: declares agents, skills, and policy, never the internal shape of a seam.
_SKILLS_NODE = "skills"
_EFFECT_NODE = "effect"
_TRACE_NODE = "trace"


class HarnessState(TypedDict, total=False):
    """The typed state schema of the adapter-owned graph.

    LangGraph's context surface *is* the state channel set, so seam 1's
    injection is a value on this schema rather than a prompt argument. Every
    channel is optional (``total=False``) because a run may exercise any subset
    of the seams: a read-only binding never produces an ``output``, and a graph
    driven with no model reports no usage.

    Attributes:
        instructions: The already-rendered instruction strings, verbatim.
        products: Each admitted Context Product's canonical bytes, decoded, so
            what the harness sees is byte-identical to what replay records.
        skills: The tool names the harness may call — exactly the bound set.
        output: A harness output offered to the effect seam.
        effect: What the effect seam returned — an
            :class:`~ccf.agents.agent.EmittedEffect` or an
            :class:`~ccf.harness.protocol.EffectRefusal`, never a write.
        trace: What the harness carried through its own run configuration,
            captured for seam 4.
    """

    instructions: tuple[str, ...]
    products: tuple[str, ...]
    skills: tuple[str, ...]
    output: dict[str, Any]
    effect: object
    trace: dict[str, Any]


@dataclass(frozen=True)
class LangGraphCarrier:
    """The harness-native carrier seam 1 returns for LangGraph.

    A compiled graph, the initial state, and the run configuration — the three
    arguments ``graph.invoke(state, config)`` takes. This is what "the adapter
    owns the topology" means concretely: for a harness that exposes a loop,
    seam 1 returns options *for* that loop; here it returns the loop itself,
    already built, with the context already on it. The Protocol types seam 1's
    return as :class:`object` for exactly this reason — a carrier is
    harness-shaped by definition, and naming this dataclass on the fabric
    surface would make the fabric LangGraph-shaped.

    ``tools`` is the real :class:`~langgraph.prebuilt.ToolNode` assembled from
    the agent's currently-bound skill-set, exposed so a deployment can wire it
    into its own message-passing topology; it holds exactly the tools named in
    ``state['skills']`` and nothing else.
    """

    graph: Any
    state: HarnessState
    config: RunnableConfig
    tools: ToolNode


class LangGraphAdapter:
    """LangGraph's binding of the four seams (CLAUDE.md §7.3).

    Structurally conforms to
    :class:`~ccf.harness.protocol.HarnessAdapterProtocol`; declared by shape,
    not by inheritance, in the SDK's Protocol-over-inheritance discipline
    (CLAUDE.md §11).

    **The bound agent arrives per seam call, and is not held.** One adapter
    instance serves any number of agents, and each call resolves that agent's
    own currently-bound skill-set from the ledger-backed view the factory
    injected (D-07, D-23). Holding an agent as well would create two answers to
    "whose skills are these" and let a per-adapter cache outlive a revocation
    (T-06-73).

    Args:
        model: The model identifier this deployment binds, placed on the run
            configuration so the harness's own machinery carries it. Injected
            because it is a deployment value; the SDK ships no model name. It
            is never read back as a replay claim — see
            :data:`MODEL_METADATA_KEY`.
        thread_id: LangGraph's own run-correlation identifier, placed under the
            run configuration's ``configurable`` mapping, which is where
            LangGraph looks for it. A deployment value: which conversation or
            unit of work a run belongs to is the deployment's statement.
        run_tags: Tags placed on the run configuration. Deployment vocabulary
            for the harness's own tracing.
        effects: This adapter's declared effect-capture capability
            (D-IMPL-25, D-10). Required with no default: a defaulted capability
            would let an adapter inherit a claim about effect capture it never
            made. Injected rather than fixed so a deployment can bind the same
            harness read-only, and so the conformance suite can drive both
            branches of the capability space.
    """

    def __init__(
        self,
        *,
        model: str,
        thread_id: str,
        run_tags: tuple[str, ...] = (),
        effects: EffectCapability,
    ) -> None:
        self._model = model
        self._thread_id = thread_id
        self._run_tags = run_tags
        self._effects: EffectCapability = effects

    # --- seam 0: what this adapter declares about itself ---------------------

    def capabilities(self) -> HarnessCapabilities:
        """Declare this adapter's harness identity and effect capability."""
        return HarnessCapabilities(harness_id=HARNESS_ID, effects=self._effects)

    # --- seam 2 helpers ------------------------------------------------------

    def _bound_entry(self, agent: Agent, skill_name: str) -> SkillCatalogEntry:
        """The catalog entry currently bound under ``skill_name``.

        Resolution goes through :meth:`~ccf.agents.agent.Agent.invoke_skill`
        with no arguments — the introspection form — so a name the agent is not
        currently granted raises
        :class:`~ccf.agents.errors.SkillNotBound` here rather than becoming a
        tool the harness can see.
        """
        entry = agent.invoke_skill(skill_name)
        if not isinstance(entry, SkillCatalogEntry):  # pragma: no cover - defensive
            raise TypeError(
                f"introspecting skill {skill_name!r} returned"
                f" {type(entry).__name__}, not a catalog entry"
            )
        return entry

    def _skill_tool(self, agent: Agent, skill_name: str) -> StructuredTool:
        """One ``StructuredTool`` closing over this agent's skill seam.

        The tool's description and argument schema come from the one shared
        derivation (:func:`ccf.skills.toolsurface.render_tool_surface`) over
        the entry's own declared ``description`` and ``argument_schema``
        (D-IMPL-56) — never adapter-authored, so all three reference adapters
        render the identical surface for the same entry (D-17). The declared
        arguments arrive as named keyword arguments and are carried to
        :meth:`~ccf.agents.agent.Agent.invoke_skill` as its
        ``Mapping[str, str]``.

        Dispatch is the fabric's, every time the harness calls the tool:
        binding is re-resolved from the ledger-backed view at each invocation,
        so a revocation between two turns takes effect on the second one
        without the agent's identity changing (D-07).
        """
        entry = self._bound_entry(agent, skill_name)
        surface = render_tool_surface(entry)

        def call(**arguments: str) -> str:
            invocation = agent.invoke_skill(
                skill_name,
                arguments={key: str(value) for key, value in arguments.items()},
            )
            return canonical_bytes(invocation).decode("utf-8")

        return StructuredTool.from_function(
            func=call,
            name=entry.name,
            description=surface.description,
            args_schema=surface.input_schema,
        )

    def _tool_node(self, agent: Agent) -> ToolNode:
        """The harness-native tool node for exactly this agent's bound skills.

        Built from ``agent.bound_skill_names`` and nothing else — never from
        the skill catalog, which holds every entry the deployment registered
        rather than the ones this agent was granted. Computing exposure over a
        shared catalog is the over-exposure defect T-06-73 registers, and it is
        invisible with one agent; the D-23 two-agent case is what makes it
        visible.

        Filtered by :data:`~ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES`
        before rendering (``TP-03``, ``D-IMPL-361``): a bound ``peering``,
        ``mcp_product`` or ``procedure`` skill is skipped — never rendered and
        never raised on — so the agent's exposable skills still reach the
        harness.
        """
        return ToolNode(
            [
                self._skill_tool(agent, skill_name)
                for skill_name in agent.bound_skill_names
                if self._bound_entry(agent, skill_name).skill_type
                in HARNESS_EXPOSABLE_SKILL_TYPES
            ]
        )

    def expose_skills(self, *, agent: Agent) -> tuple[str, ...]:
        """Seam 2 — exactly the currently-bound skill-set, as harness tools.

        Returns the skill names actually exposed, sorted, read back off the
        assembled :class:`~langgraph.prebuilt.ToolNode` rather than off the
        list that built it — the harness's own registry is the thing the
        conformance suite's set equality against
        :attr:`~ccf.agents.agent.Agent.bound_skill_names` is really about
        (CLAUDE.md §6.2 channel 2, §7.3 seam 2). A skill the agent has not been
        granted does not exist from the harness's point of view: it is not
        built into a tool, it is not in the tool node, and it is not on the
        state channel the graph carries.
        """
        return tuple(sorted(self._tool_node(agent).tools_by_name))

    # --- seam 1 --------------------------------------------------------------

    def _run_config(self, agent: Agent) -> RunnableConfig:
        """The run configuration the compiled graph is invoked with.

        Carries the deployment's model, thread, and tags, plus the one
        correlation key this adapter sets (:data:`AGENT_HASH_METADATA_KEY`), so
        that seam 4 can read back something the harness actually carried
        through its own machinery rather than a value this object still holds.
        """
        return RunnableConfig(
            tags=list(self._run_tags),
            metadata={
                AGENT_HASH_METADATA_KEY: agent.identity.definition_hash,
                "ccf_model": self._model,
            },
            configurable={"thread_id": self._thread_id},
        )

    def _build_graph(self, agent: Agent, tools: ToolNode) -> Any:
        """Compile this adapter's own three-node topology.

        The topology is the adapter's because LangGraph has none of its own to
        hook: ``skills`` publishes the exposed tool names onto the state,
        ``effect`` routes any harness output through the governed seam, and
        ``trace`` captures what the run configuration carried. Every node is a
        plain function, so the graph runs end to end with no model configured
        and no network (D-09).
        """

        def skills(state: HarnessState) -> HarnessState:
            return {"skills": tuple(sorted(tools.tools_by_name))}

        def effect(state: HarnessState) -> HarnessState:
            output = state.get("output")
            if output is None:
                return {}
            return {"effect": self.capture_effect(agent=agent, output=output)}

        def trace(state: HarnessState, config: RunnableConfig) -> HarnessState:
            return {
                "trace": {
                    "metadata": dict(config.get("metadata") or {}),
                    "tags": list(config.get("tags") or []),
                    "configurable": dict(config.get("configurable") or {}),
                }
            }

        builder: Any = StateGraph(HarnessState)
        builder.add_node(_SKILLS_NODE, skills)
        builder.add_node(_EFFECT_NODE, effect)
        builder.add_node(_TRACE_NODE, trace)
        builder.add_edge(START, _SKILLS_NODE)
        builder.add_edge(_SKILLS_NODE, _EFFECT_NODE)
        builder.add_edge(_EFFECT_NODE, _TRACE_NODE)
        builder.add_edge(_TRACE_NODE, END)
        return builder.compile()

    def inject_context(
        self,
        *,
        agent: Agent,
        products: tuple[ContextProductContract, ...],
        instructions: tuple[str, ...],
    ) -> object:
        """Seam 1 — typed context into the harness's own context surface.

        Returns a :class:`LangGraphCarrier`: the compiled graph, the initial
        state carrying the already-rendered instructions and each admitted
        product's canonical bytes, the run configuration, and the tool node for
        exactly this agent's bound skills.

        ``products`` are products the agent already admitted through
        :meth:`~ccf.agents.agent.Agent.consume`; they are serialized canonically
        so what the harness sees is byte-identical to what replay records. The
        harness touches no L3 handle and no raw signal, because nothing on this
        seam can reach either — and owning the topology does not change that,
        because the nodes this module builds close over the same three fabric
        seams :class:`~ccf.agents.agent.Agent` exposes and nothing more.

        ``instructions`` are rendered strings. This method resolves no artifact
        and renders no template (T-06-64).
        """
        tools = self._tool_node(agent)
        state: HarnessState = {
            "instructions": instructions,
            "products": tuple(
                canonical_bytes(product).decode("utf-8") for product in products
            ),
            "skills": tuple(sorted(tools.tools_by_name)),
        }
        carrier: object = LangGraphCarrier(
            graph=self._build_graph(agent, tools),
            state=state,
            config=self._run_config(agent),
            tools=tools,
        )
        return carrier

    # --- seam 3 --------------------------------------------------------------

    def _refusal_reason(self) -> str:
        """Why a read-only binding refuses, in this adapter's own words."""
        return f"{HARNESS_ID} declared effects={self._effects!r}"

    def capture_effect(
        self, *, agent: Agent, output: Mapping[str, Any]
    ) -> EmittedEffect | EffectRefusal:
        """Seam 3 — a harness output back through governed emission.

        Called from inside the adapter-owned effect node, which is what a
        topology-owning harness makes of a *translation*-shaped seam: the node
        returns the typed value this method produced into a state channel, and
        that value is the entire effect. Implemented for both declared
        capabilities, which is what makes the ``unsupported`` case
        conformance-verifiable rather than merely unimplemented (D-10).

        Under ``governed`` the output goes through
        :meth:`~ccf.agents.agent.Agent.emit_effect` and comes back as a typed
        :class:`~ccf.agents.agent.EmittedEffect`; under ``unsupported`` every
        output comes back as a typed
        :class:`~ccf.harness.protocol.EffectRefusal`. Either way this adapter
        holds no write handle and constructs none, so nothing reaches L3 here
        (CLAUDE.md §10, §7.3 seam 3).
        """
        if self._effects != "governed":
            return EffectRefusal(
                harness_id=HARNESS_ID,
                agent_definition_hash=agent.identity.definition_hash,
                reason=self._refusal_reason(),
            )
        return agent.emit_effect(output)

    # --- seam 4 --------------------------------------------------------------

    def replay_trace(self, *, execution: object) -> HarnessTrace:
        """Seam 4 — the harness's execution into replay dimension 3.

        LangGraph's execution result is the final state a run produced, and the
        run configuration is visible only from inside the graph — which is why
        the adapter-owned ``trace`` node captures it there. This method reads
        that captured block and nothing else: what the harness carried through
        its own configuration machinery, not what this object still holds.

        Only harness-attributable values are read: the model the *harness*
        reported running (:data:`MODEL_METADATA_KEY`, populated by a chat
        model's own tracing, never by this adapter), the thread identifier
        LangGraph resolved for the run, and the harness's own token accounting
        (:data:`USAGE_METADATA_KEY`). A field the run did not report is left at
        its positive :data:`~ccf.replay.record.NO_HARNESS` sentinel rather than
        guessed — an absent trace and a dropped one must not be the same
        artifact (T-06-63), and filling ``model_version`` from the configured
        model would be a harness overwriting a governed claim (T-06-62).

        Raises:
            TypeError: ``execution`` is not a LangGraph run's final state, or
                carries no captured trace block. Typed :class:`object` on the
                Protocol because a harness-native execution result is
                harness-shaped by definition; narrowing it is this adapter's
                job.
        """
        if not isinstance(execution, Mapping):
            raise TypeError(
                f"replay_trace expected a graph run's final state, got"
                f" {type(execution).__name__}"
            )
        captured = execution.get("trace")
        if not isinstance(captured, Mapping):
            raise TypeError(
                "replay_trace expected the run's final state to carry a"
                " captured trace block; the adapter-owned trace node did not run"
            )
        metadata: Mapping[str, Any] = captured.get("metadata") or {}
        configurable: Mapping[str, Any] = captured.get("configurable") or {}
        usage: Mapping[str, Any] = metadata.get(USAGE_METADATA_KEY) or {}
        return HarnessTrace(
            harness_id=HARNESS_ID,
            model_version=str(metadata.get(MODEL_METADATA_KEY) or NO_HARNESS),
            trace_provider=HARNESS_ID,
            trace_id=str(configurable.get("thread_id") or NO_HARNESS),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )
