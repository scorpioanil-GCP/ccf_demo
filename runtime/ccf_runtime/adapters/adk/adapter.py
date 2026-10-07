"""`AdkAdapter` — the Google ADK binding of the four seams (XPRC-03).

SDK-defined extension (CLAUDE.md §7.3; D-IMPL-24, D-IMPL-25). The whitepaper
specifies no harness binding; §7.3 does, and this is the third and last of its
v0 reference implementations, completing D-IMPL-24. Structural conformance to
:class:`~ccf.harness.protocol.HarnessAdapterProtocol` is the contract, and the
same factory-parametrized suite that accepts the Claude Agent SDK and LangGraph
adapters is the acceptance bar — one suite, three params, no assertion loosened
for any of them (D-09).

**This adapter is the Protocol's third data point, and it agreed.** 06-11 bet
that every seam should be a *translation producing a harness-native carrier*
rather than a callback registration. 06-12 (Claude) and 06-13 (LangGraph)
tested that bet from the two ends of the shape space — a harness that owns its
loop, and one that has no loop at all. Google ADK sits with Claude: it owns the
loop and exposes callbacks into it. Two of the four seams here are literally
handed to ADK as callables it will invoke (the instruction provider and the
before-tool gate), and the translation shape absorbed that without a change,
because a translation the adapter itself calls is trivially also a translation
the adapter hands over.

**One asymmetry ADK contributes, worth naming.** ADK's ``LlmAgent.instruction``
accepts a plain ``str``, and a ``str`` is interpolated against session state by
ADK's own instruction machinery. A Context Product's canonical bytes are JSON
and are full of braces, so binding them as a ``str`` would hand the harness a
template whose placeholders are the product's own structure. The callable form
(``Callable[[ReadonlyContext], str]``) is not interpolated, so seam 1 binds
:class:`ContextInjection` — a callable object rather than a closure, so the
values it will hand the harness are inspectable rather than sealed inside cell
variables. That is an adapter concern, not a Protocol one.

**What this adapter cannot do.** It cannot write to the graph. It holds no
graph write handle, no graph read handle, no graph store, no fabric boot
handle, and no Control Plane registry — none of them is a constructor
parameter, an attribute, or a name anywhere in this module, which the
conformance suite pins by source scan in the same discipline
``tests/harness/test_protocol.py`` applies to the seam itself: a fabric surface
named in a comment or a docstring is a surface someone was thinking about
handing to an adapter (T-06-61). The execution vehicle this module owns is no
exception: it yields events and reaches L2 only as the value
:meth:`AdkAdapter.capture_effect` returned, produced by
:meth:`ccf.agents.agent.Agent.emit_effect`. Carrying that value onward is L2's
job and nobody else's (single-writer, CLAUDE.md §10, §7.3 seam 3).

Scoped claims, not architectural boasts (D-21):

* **Protocol-shape-enforced.** No method on
  :class:`~ccf.harness.protocol.HarnessAdapterProtocol` accepts a fabric object
  other than :class:`~ccf.agents.agent.Agent`, so an adapter typed against it
  cannot receive one. This adapter's constructor takes deployment configuration
  only and holds no fabric object at all — the bound agent arrives per seam
  call (D-23).
* **Lint-enforced.** ``cinv02-harness`` denies ``google.adk`` in every module
  outside ``ccf_runtime.adapters.*`` (D-IMPL-53). This module is inside that
  carve-out and the carve-out was not widened to admit it.
* **Conformance-enforced.** The shared suite asserts set equality between the
  exposed tool names and ``agent.bound_skill_names`` across a grant/revoke
  round trip and across two agents (T-06-79), scans this object's public
  surface against the shared write-surface name list (T-06-80), and drives the
  ``unsupported`` effect branch through ADK's own short-circuiting before-tool
  hook to prove the refusal fires (D-10, T-06-81).

**Prompt artifacts are consumed, never re-resolved.** ``instructions`` arrive
at seam 1 already rendered by :func:`ccf.agents.prompts.render_instruction`
from the artifacts the Agent Factory pinned. This module resolves no URI, reads
no template, and calls no renderer — and :class:`ContextInjection` holds the
rendered strings rather than a way to produce them, so there is nothing for the
harness to re-render when it calls back.

**This module claims no algorithmic-mode tag, deliberately.** Adapters bind a
harness that reaches a model, so they are the semantic boundary of the
Algorithmic ⇄ Semantic Alternation, not an algorithmic module.

**This adapter's harness-facing side is actually type-checked, unlike the
other two.** ``google-adk`` 2.5.0 ships a ``py.typed`` marker, so the
``ignore_missing_imports`` override declared for it is inert and strict mypy
resolves ADK's real types here. Two consequences worth knowing: the vendor
types are checked rather than silently ``Any`` (which is why the imports below
name leaf modules such as ``google.adk.tools.function_tool`` — the package root
re-exports lazily and strict mypy will not accept an implicit re-export), and
:meth:`AdkAdapter._effect_gate` still returns an untyped callable on purpose,
because ADK annotates its before-tool hook positionally while calling it by
keyword, and matching the annotation would mean accepting positional arguments
ADK never passes.

Citation: CLAUDE.md §7.3 (SDK-defined extension), §6.2 channel 2 (skill
exposure), §10 (single-writer); D-IMPL-24 (Google ADK as a v0 reference
target); D-IMPL-25 (seam scope); D-IMPL-53 (the lint carve-out); D-IMPL-55 (the
replay slot seam 4 writes into).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

from ccf.agents.agent import Agent, EmittedEffect
from ccf.contracts.canonical import canonical_bytes
from ccf.harness.protocol import EffectCapability, EffectRefusal, HarnessCapabilities
from ccf.products.contract import ContextProductContract
from ccf.replay.record import NO_HARNESS, HarnessTrace
from ccf.skills.catalog import SkillCatalogEntry
from ccf.skills.toolsurface import (
    HARNESS_EXPOSABLE_SKILL_TYPES,
    RenderedToolSurface,
    render_tool_surface,
)
from ccf.skills.wire_arguments import ArgumentRefused, refuse_undeclared_arguments

__all__ = [
    "AGENT_HASH_STATE_KEY",
    "HARNESS_ID",
    "MODEL_STATE_KEY",
    "REFUSAL_RESPONSE_KEY",
    "TRACE_METADATA_KEY",
    "USAGE_STATE_KEY",
    "AdkAdapter",
    "AdkCarrier",
    "ContextInjection",
]

#: This adapter's stable harness identity. Lands verbatim in
#: :attr:`~ccf.harness.protocol.HarnessCapabilities.harness_id` and in
#: :attr:`~ccf.replay.record.HarnessTrace.harness_id`. A mechanism identifier
#: naming the package this module binds — not a deployment value, which is why
#: every genuinely deployment-owned value (model, session, agent name, effect
#: capability) is a constructor argument instead.
HARNESS_ID = "google-adk"

#: The session-state key the *harness side* populates with the model a run
#: actually used, for runs where ADK does not report one on the event itself.
#: Read at seam 4, never written here: the fabric records what it invoked and
#: the harness records what it invoked, and writing this one from the
#: configured model would be exactly how a harness overwrites a governed claim
#: (T-06-62). Absent when nothing reported a model, in which case the positive
#: sentinel stands.
MODEL_STATE_KEY = "ccf_reported_model"

#: The session-state key carrying the harness's own token accounting, on the
#: same terms. Read at seam 4, never written here.
USAGE_STATE_KEY = "ccf_reported_usage"

#: The correlation key this adapter *does* set, at seam 1, onto the session
#: state ADK's own session machinery carries into a run. It identifies the
#: agent version a run was conditioned on; it is not a replay claim.
AGENT_HASH_STATE_KEY = "ccf_agent_definition_hash"

#: Where the adapter-owned execution vehicle puts what it observed from inside
#: the run, on the event's ``custom_metadata``. Seam 4 reads this block: ADK
#: exposes a run's session only to what is running inside it, so — exactly as
#: for a topology-owning harness — the capture happens in there and the
#: execution result is what the event stream carried back out.
TRACE_METADATA_KEY = "ccf_trace"

#: The key an ADK before-tool short-circuit response carries the governed
#: refusal under. ADK treats *any* truthy mapping returned from
#: ``before_tool_callback`` as the tool's response and does not call the tool,
#: so this is the refusal in the form ADK itself acts on.
REFUSAL_RESPONSE_KEY = "ccf_effect_refusal"


def _declaration_parameters(surface: RenderedToolSurface) -> genai_types.Schema:
    """The shared surface's ``inputSchema``, as ADK's declaration schema.

    A pure translation of :attr:`RenderedToolSurface.input_schema` into the
    ``google.genai`` ``Schema`` an ADK function declaration carries — nothing
    is authored here; every type and description is the artifact's own
    declared value rendered by the one shared derivation (D-IMPL-56, D-17).
    """
    rendered = surface.input_schema
    json_schema = genai_types.JSONSchema(
        type=genai_types.JSONSchemaType(rendered["type"]),
        properties={
            name: genai_types.JSONSchema(
                type=genai_types.JSONSchemaType(spec["type"]),
                description=spec["description"],
            )
            for name, spec in rendered["properties"].items()
        },
        required=list(rendered["required"]),
    )
    return genai_types.Schema.from_json_schema(json_schema=json_schema)


class _DeclaredSkillTool(FunctionTool):
    """A ``FunctionTool`` whose declaration is the shared rendered surface.

    ADK's stock ``FunctionTool`` infers name, description, and parameters
    from the bound function. Inference would make ADK's tool surface a
    signature transcription while the other two adapters render the entry's
    declared ``argument_schema`` — exactly the divergence D-17 forbids — so
    this subclass overrides the declaration with the one shared derivation's
    values verbatim (D-IMPL-56).

    **Execution is overridden too** (``TP-04``, ``D-IMPL-361``). ADK's stock
    ``run_async`` filters the model's arguments to the bound callable's
    signature (google-adk 2.5.0, ``function_tool.py:220-224``), and a declared
    schema's property names are arbitrary strings that need not be Python
    identifiers, so no signature can carry them. Measured before this override:
    every declared argument was filtered out and ``invoke_skill`` received the
    empty mapping; an undeclared key was dropped by the same filter. This
    override receives ADK's raw ``args``, refuses any key the declared schema
    does not name — through the adapter's typed ``EffectRefusal``, never by
    dropping it — and hands the rest to dispatch unchanged.

    **The whole argument rule is the seam's** (``TP-04`` follow-on,
    ``D-IMPL-361``). This early undeclared-key refusal stays, delegating to the
    shared validator (:func:`ccf.skills.wire_arguments.refuse_undeclared_arguments`)
    so its message is the family's; a missing required argument and a
    wrong-typed value are refused by
    :meth:`~ccf.agents.agent.Agent.invoke_skill`, which receives the args as
    ADK delivered them (not stringified), and the tool renders that refusal as
    the same ``EffectRefusal``.
    """

    def __init__(
        self,
        func: Callable[[Mapping[str, Any]], str],
        *,
        name: str,
        surface: RenderedToolSurface,
        refuse: Callable[[ArgumentRefused], dict[str, Any]],
    ) -> None:
        super().__init__(func=func)
        self.name = name
        self.description = surface.description
        self._ccf_surface = surface
        self._ccf_dispatch = func
        self._ccf_refuse = refuse

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        """Dispatch the model's declared arguments; refuse any undeclared one.

        ``TP-04`` (``D-IMPL-361``): declared arguments arrive, undeclared ones
        are refused, never dropped. The undeclared-key refusal is decided before
        ``invoke_skill`` is reached; the rest of the rule (missing, mistyped) is
        refused inside ``invoke_skill`` before dispatch (``TP-04`` follow-on).
        Either way a refused call dispatches nothing.
        """
        try:
            refuse_undeclared_arguments(
                args,
                declared=self._ccf_surface.input_schema["properties"],
                surface=self.name,
            )
            return self._ccf_dispatch(args)
        except ArgumentRefused as refused:
            return self._ccf_refuse(refused)

    def _get_declaration(self) -> genai_types.FunctionDeclaration:
        return genai_types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=_declaration_parameters(self._ccf_surface),
        )


@dataclass(frozen=True)
class ContextInjection:
    """What ADK will call to obtain the agent's instruction (seam 1).

    ADK's ``LlmAgent.instruction`` accepts ``str`` or
    ``Callable[[ReadonlyContext], str | Awaitable[str]]``. This is the callable
    form, deliberately, for two reasons:

    * A ``str`` instruction is **interpolated** by ADK's own instruction
      machinery against session state. A Context Product's canonical bytes are
      JSON, so binding them as a ``str`` would hand the harness a template
      whose placeholders are the product's own structure — a silent corruption
      of the exact bytes replay records. The callable form is not interpolated.
    * A callable *object* rather than a closure keeps the values inspectable.
      What the harness will be handed is the frozen content of these two
      fields, not something sealed inside cell variables, so the conformance
      suite's generic carrier walk sees exactly what ADK will see.

    Attributes:
        instructions: Already-rendered instruction strings, verbatim. Rendered
            once by the fabric from the artifacts the factory pinned; this
            object holds the results, never a way to produce them (T-06-64).
        products: Each admitted Context Product's canonical bytes, decoded, so
            what the harness sees is byte-identical to what replay records.
    """

    instructions: tuple[str, ...] = ()
    products: tuple[str, ...] = ()

    def __call__(self, context: object) -> str:
        """Return the injected instruction for one ADK invocation.

        ``context`` is ADK's ``ReadonlyContext``. It is accepted because ADK's
        instruction-provider contract passes it and ignored because everything
        this seam injects was pinned before the run began: reading run state
        here would make the injected context depend on the harness's own
        progress, which is the opposite of what a pinned context contract
        means.
        """
        return "\n".join((*self.instructions, *self.products))


class _EventCapture(BaseAgent):
    """The adapter-owned execution vehicle, so a run needs no model (D-09).

    ADK's ``Runner`` drives an agent; a real ``LlmAgent`` would reach a model,
    which the conformance suite forbids and which would cost money on every CI
    run. Subclassing ``BaseAgent`` and implementing ``_run_async_impl`` is
    ADK's own sanctioned way to run something that is not a model call, and it
    is what makes this adapter's seam-4 evidence a *real run through a real
    Runner* rather than a hand-built result object.

    It captures, from inside the run, what ADK's session machinery carried
    there — the session identity and the harness-reported values on the session
    state — and emits them on an event's ``custom_metadata``. That is the
    same discipline the LangGraph adapter applies for the same reason: a
    correlation value read back off the adapter's own fields would prove
    nothing about what the harness carried.

    It holds no fabric object and does not close over one. Everything it
    reports comes from the invocation context ADK hands it.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state: Mapping[str, Any] = dict(ctx.session.state)
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            custom_metadata={
                TRACE_METADATA_KEY: {
                    "session_id": str(ctx.session.id),
                    "model": str(state.get(MODEL_STATE_KEY) or NO_HARNESS),
                    "agent_definition_hash": str(
                        state.get(AGENT_HASH_STATE_KEY) or NO_HARNESS
                    ),
                    "usage": dict(state.get(USAGE_STATE_KEY) or {}),
                }
            },
        )


@dataclass(frozen=True)
class AdkCarrier:
    """The harness-native carrier seam 1 returns for Google ADK.

    ADK's context surface is not one object: an ``LlmAgent`` carries the
    instruction provider, the tool list, and the callbacks, while the session
    state a ``Runner`` is driven with carries the run's correlation values. So
    the carrier is both, plus the execution vehicle that makes a no-model run
    possible. The Protocol types seam 1's return as :class:`object` for exactly
    this reason — a carrier is harness-shaped by definition, and naming this
    dataclass on the fabric surface would make the fabric ADK-shaped.

    Attributes:
        llm_agent: The configured ``LlmAgent`` — instruction provider, exactly
            this agent's bound tools, and the before-tool gate bound.
        runnable: The adapter-owned ``BaseAgent`` a ``Runner`` can drive with no
            model configured.
        injection: The instruction provider ADK will call, exposed so a
            deployment can see what will be injected without invoking it.
        skills: The tool names the harness may call — exactly the bound set.
        session_state: The initial session state to seed ADK's session service
            with, carrying this adapter's one correlation key.
    """

    llm_agent: LlmAgent
    runnable: BaseAgent
    injection: ContextInjection
    skills: tuple[str, ...] = ()
    session_state: dict[str, Any] = field(default_factory=dict)


class AdkAdapter:
    """Google ADK's binding of the four seams (CLAUDE.md §7.3).

    Structurally conforms to
    :class:`~ccf.harness.protocol.HarnessAdapterProtocol`; declared by shape,
    not by inheritance, in the SDK's Protocol-over-inheritance discipline
    (CLAUDE.md §11).

    **The bound agent arrives per seam call, and is not held.** One adapter
    instance serves any number of agents, and each call resolves that agent's
    own currently-bound skill-set from the ledger-backed view the factory
    injected (D-07, D-23). Holding an agent as well would create two answers to
    "whose skills are these" and let a per-adapter cache outlive a revocation
    (T-06-79).

    Args:
        model: The model identifier this deployment binds, placed on the
            ``LlmAgent``. Injected because it is a deployment value; the SDK
            ships no model name. It is never read back as a replay claim — see
            :data:`MODEL_STATE_KEY`.
        agent_name: The name ADK gives this deployment's agent. Part of the
            deployment's own vocabulary — it is what appears as an event's
            author — and ADK requires it to be an identifier, which CCF agent
            keys are not obliged to be.
        session_id: ADK's own run-correlation identifier, the session a run
            belongs to. A deployment value: which unit of work a run belongs to
            is the deployment's statement, and seam 4 reads it back as the
            trace reference only because the harness carried it there.
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
        agent_name: str,
        session_id: str,
        effects: EffectCapability,
    ) -> None:
        self._model = model
        self._agent_name = agent_name
        self._session_id = session_id
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

    def _skill_tool(self, agent: Agent, skill_name: str) -> FunctionTool:
        """One ``FunctionTool`` closing over this agent's skill seam.

        The tool's description and argument schema come from the one shared
        derivation (:func:`ccf.skills.toolsurface.render_tool_surface`) over
        the entry's own declared ``description`` and ``argument_schema``
        (D-IMPL-56) — never adapter-authored and never signature-inferred, so
        all three reference adapters render the identical surface for the
        same entry (D-17); :class:`_DeclaredSkillTool` carries it into ADK's
        declaration. The model's raw argument mapping reaches ``call`` through
        :meth:`_DeclaredSkillTool.run_async` and is carried to
        :meth:`~ccf.agents.agent.Agent.invoke_skill` as ADK delivered it — not
        stringified, so the seam's type check sees the real value; a key the
        declared schema does not name, a missing required argument or a
        wrong-typed value is refused as this adapter's typed
        :class:`~ccf.harness.protocol.EffectRefusal`, never dropped or coerced
        (``TP-04`` and its follow-on, ``D-IMPL-361``).

        Dispatch is the fabric's, every time the harness calls the tool:
        binding is re-resolved from the ledger-backed view at each invocation,
        so a revocation between two turns takes effect on the second one
        without the agent's identity changing (D-07).
        """
        entry = self._bound_entry(agent, skill_name)
        surface = render_tool_surface(entry)

        def call(arguments: Mapping[str, Any]) -> str:
            invocation = agent.invoke_skill(skill_name, arguments=dict(arguments))
            return canonical_bytes(invocation).decode("utf-8")

        def refuse(refused: ArgumentRefused) -> dict[str, Any]:
            return self._refusal_response(self._refusal(agent, str(refused)))

        call.__name__ = entry.name
        call.__doc__ = surface.description
        return _DeclaredSkillTool(
            call, name=entry.name, surface=surface, refuse=refuse
        )

    def _tools(self, agent: Agent) -> tuple[FunctionTool, ...]:
        """The harness-native tools for exactly this agent's bound skill-set.

        Built from ``agent.bound_skill_names`` and nothing else — never from
        the skill catalog, which holds every entry the deployment registered
        rather than the ones this agent was granted. Computing exposure over a
        shared catalog is the over-exposure defect T-06-79 registers, and it is
        invisible with one agent; the D-23 two-agent case is what makes it
        visible.

        Filtered by :data:`~ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES`
        before rendering (``TP-03``, ``D-IMPL-361``): a bound ``peering``,
        ``mcp_product`` or ``procedure`` skill is skipped — never rendered and
        never raised on — so the agent's exposable skills still reach the
        harness.
        """
        return tuple(
            self._skill_tool(agent, skill_name)
            for skill_name in agent.bound_skill_names
            if self._bound_entry(agent, skill_name).skill_type
            in HARNESS_EXPOSABLE_SKILL_TYPES
        )

    def expose_skills(self, *, agent: Agent) -> tuple[str, ...]:
        """Seam 2 — exactly the currently-bound skill-set, as harness tools.

        Returns the skill names actually exposed, sorted, read back off the
        constructed ``FunctionTool`` objects rather than off the list that
        built them — what the harness's own tool surface reports is the thing
        the conformance suite's set equality against
        :attr:`~ccf.agents.agent.Agent.bound_skill_names` is really about
        (CLAUDE.md §6.2 channel 2, §7.3 seam 2). A skill the agent has not been
        granted does not exist from the harness's point of view: it is not
        built into a tool, it is not on the ``LlmAgent``, and the before-tool
        gate would short-circuit it if the harness named it anyway.
        """
        return tuple(sorted(tool.name for tool in self._tools(agent)))

    # --- seam 1 --------------------------------------------------------------

    def inject_context(
        self,
        *,
        agent: Agent,
        products: tuple[ContextProductContract, ...],
        instructions: tuple[str, ...],
    ) -> object:
        """Seam 1 — typed context into the harness's own context surface.

        Returns an :class:`AdkCarrier`: an ``LlmAgent`` carrying the
        :class:`ContextInjection` provider, exactly this agent's bound tools,
        and the before-tool gate; the adapter-owned execution vehicle a
        ``Runner`` can drive with no model; and the initial session state.

        ``products`` are products the agent already admitted through
        :meth:`~ccf.agents.agent.Agent.consume`; they are serialized
        canonically so what the harness sees is byte-identical to what replay
        records. The harness touches no L3 handle and no raw signal, because
        nothing on this seam can reach either.

        ``instructions`` are rendered strings. This method resolves no artifact
        and renders no template (T-06-64).
        """
        tools = self._tools(agent)
        injection = ContextInjection(
            instructions=instructions,
            products=tuple(
                canonical_bytes(product).decode("utf-8") for product in products
            ),
        )
        carrier: object = AdkCarrier(
            llm_agent=LlmAgent(
                name=self._agent_name,
                model=self._model,
                instruction=injection,
                tools=list(tools),
                before_tool_callback=self._effect_gate(agent),
            ),
            runnable=_EventCapture(name=self._agent_name),
            injection=injection,
            skills=tuple(sorted(tool.name for tool in tools)),
            session_state={AGENT_HASH_STATE_KEY: agent.identity.definition_hash},
        )
        return carrier

    # --- seam 3 --------------------------------------------------------------

    def _refusal_reason(self) -> str:
        """Why a read-only binding refuses, in this adapter's own words."""
        return f"{HARNESS_ID} declared effects={self._effects!r}"

    def _unbound_reason(self, tool_name: str) -> str:
        """Why a tool outside the bound skill-set is refused."""
        return f"{tool_name!r} is not in the agent's bound skill-set"

    def _refusal(self, agent: Agent, reason: str) -> EffectRefusal:
        """The typed refusal, built once and rendered two ways."""
        return EffectRefusal(
            harness_id=HARNESS_ID,
            agent_definition_hash=agent.identity.definition_hash,
            reason=reason,
        )

    def _effect_gate(self, agent: Agent) -> Any:
        """ADK's own before-tool hook, closed over this agent's grants.

        ADK calls ``before_tool_callback(tool=..., args=..., tool_context=...)``
        and treats any truthy mapping it returns as the tool's response,
        **without calling the tool**. That short-circuit is a genuine governed
        refusal rather than an absent write path, which is what lets D-10's
        proof assert that a refusal *fired* on this harness rather than merely
        that nothing happened.

        Two conditions refuse: a tool outside this agent's currently-bound
        EXPOSABLE skill-set, and — when this adapter declared ``effects:
        unsupported`` — every tool, because a read-only binding must not let
        the harness reach a dispatch path at all. Permitted means bound AND of
        a type in :data:`~ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES`
        (``TP-03`` follow-on, ``D-IMPL-361``): a bound ``peering``,
        ``mcp_product`` or ``procedure`` skill is never a tool here, so the gate
        refuses it with the same unbound-reason message. The refusal ADK receives is the canonical
        serialization of the same typed
        :class:`~ccf.harness.protocol.EffectRefusal`
        :meth:`capture_effect` returns, so the two cannot describe the refusal
        differently.
        """

        def before_tool(
            *, tool: Any, args: Mapping[str, Any], tool_context: Any
        ) -> dict[str, Any] | None:
            if self._effects != "governed":
                return self._refusal_response(
                    self._refusal(agent, self._refusal_reason())
                )
            permitted = {
                name
                for name in agent.bound_skill_names
                if self._bound_entry(agent, name).skill_type
                in HARNESS_EXPOSABLE_SKILL_TYPES
            }
            if tool.name not in permitted:
                return self._refusal_response(
                    self._refusal(agent, self._unbound_reason(str(tool.name)))
                )
            return None

        return before_tool

    def _refusal_response(self, refusal: EffectRefusal) -> dict[str, Any]:
        """A typed refusal in the shape ADK short-circuits a tool call with."""
        return {REFUSAL_RESPONSE_KEY: canonical_bytes(refusal).decode("utf-8")}

    def capture_effect(
        self, *, agent: Agent, output: Mapping[str, Any]
    ) -> EmittedEffect | EffectRefusal:
        """Seam 3 — a harness output back through governed emission.

        Implemented for both declared capabilities, which is what makes the
        ``unsupported`` case conformance-verifiable rather than merely
        unimplemented (D-10). Under ``governed`` the output goes through
        :meth:`~ccf.agents.agent.Agent.emit_effect` and comes back as a typed
        :class:`~ccf.agents.agent.EmittedEffect`; under ``unsupported`` every
        output comes back as a typed
        :class:`~ccf.harness.protocol.EffectRefusal` — the same value ADK's
        before-tool gate short-circuits with, so the declared capability and
        the harness's behaviour cannot disagree.

        Either way this adapter holds no write handle and constructs none, so
        nothing reaches L3 here (CLAUDE.md §10, §7.3 seam 3).
        """
        if self._effects != "governed":
            return self._refusal(agent, self._refusal_reason())
        return agent.emit_effect(output)

    # --- seam 4 --------------------------------------------------------------

    def replay_trace(self, *, execution: object) -> HarnessTrace:
        """Seam 4 — the harness's execution into replay dimension 3.

        ADK's execution result is the ``Event`` stream a ``Runner`` yielded, so
        ``execution`` is the sequence of events a run produced. Two sources are
        read, in that order, and both are the harness's own:

        * ADK's own reported fields on an event — ``model_version`` and
          ``usage_metadata`` — which a real model run populates.
        * Failing those, the block the adapter-owned execution vehicle captured
          from inside the run (:data:`TRACE_METADATA_KEY`), carrying what ADK's
          session machinery brought into the run on the session state.

        Nothing is read off this adapter's own fields. A field no source
        reported is left at its positive
        :data:`~ccf.replay.record.NO_HARNESS` sentinel rather than guessed — an
        absent trace and a dropped one must not be the same artifact (T-06-63),
        and filling ``model_version`` from the configured model would be a
        harness overwriting a governed claim (T-06-62).

        Raises:
            TypeError: ``execution`` is not an ADK event stream, or carries no
                captured trace block. Typed :class:`object` on the Protocol
                because a harness-native execution result is harness-shaped by
                definition; narrowing it is this adapter's job.
        """
        events = self._events(execution)
        captured = self._captured(events)
        usage: Mapping[str, Any] = self._reported_usage(events) or captured["usage"]
        return HarnessTrace(
            harness_id=HARNESS_ID,
            model_version=self._reported_model(events) or str(captured["model"]),
            trace_provider=HARNESS_ID,
            trace_id=str(captured["session_id"] or NO_HARNESS),
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
        )

    @staticmethod
    def _events(execution: object) -> tuple[Event, ...]:
        """Narrow the harness-native execution result to an ADK event stream."""
        if isinstance(execution, (str, bytes)) or not isinstance(
            execution, (list, tuple)
        ):
            raise TypeError(
                f"replay_trace expected a sequence of ADK events, got"
                f" {type(execution).__name__}"
            )
        events = tuple(execution)
        if not all(isinstance(event, Event) for event in events):
            raise TypeError(
                "replay_trace expected every element of the execution result to"
                " be an ADK event"
            )
        return events

    @staticmethod
    def _captured(events: tuple[Event, ...]) -> Mapping[str, Any]:
        """The block the adapter-owned execution vehicle captured in the run."""
        for event in events:
            metadata: Mapping[str, Any] = event.custom_metadata or {}
            block = metadata.get(TRACE_METADATA_KEY)
            if isinstance(block, Mapping):
                return block
        raise TypeError(
            "replay_trace expected the event stream to carry a captured trace"
            " block; the adapter-owned execution vehicle did not run"
        )

    @staticmethod
    def _reported_model(events: tuple[Event, ...]) -> str:
        """The model ADK itself reported on an event, if a model ran."""
        for event in events:
            reported = event.model_version
            if reported:
                return str(reported)
        return ""

    @staticmethod
    def _reported_usage(events: tuple[Event, ...]) -> Mapping[str, Any]:
        """ADK's own token accounting on an event, if a model ran."""
        for event in events:
            usage = event.usage_metadata
            if usage is None:
                continue
            return {
                "input_tokens": usage.prompt_token_count or 0,
                "output_tokens": usage.candidates_token_count or 0,
            }
        return {}
