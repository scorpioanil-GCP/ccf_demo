"""`HarnessAdapterProtocol` — the four seams (CLAUDE.md §7.3 — SDK-defined; D-IMPL-24/25).

SDK-defined extension, marked as such: the whitepaper does not specify a harness
binding. CLAUDE.md §7.3 does, and this module is its fabric-side declaration.

**The adapter's fabric-side input is** :class:`~ccf.agents.agent.Agent` **and
nothing more.** No fabric boot handle, no Control Plane registry, and no graph
read or write handle of any kind appears on this surface — not as a parameter,
not as a return type, not by name anywhere in this module, which
``tests/harness/test_protocol.py`` pins by source scan. ``Agent`` already
exposes exactly the three fabric seams an adapter needs — ``consume``,
``invoke_skill``, ``emit_effect`` — and handing an adapter anything else would
widen what a harness can reach past the point any of the claims below could
still be made. What the Protocol *omits* is as load-bearing as what it declares,
in the same discipline as :class:`~ccf.signal.source.SignalSourceProtocol`.

Scoped claims, not architectural boasts (D-21). Three things are true of this
surface, each at the scope of its actual enforcement:

* **Lint-enforced:** no module outside ``ccf_runtime.adapters.*`` may import a
  harness package (CINV-02 `cinv02-harness`, D-IMPL-53). This module imports
  none, and neither does anything else in ``/src``.
* **Declared-surface-enforced:** an adapter typed against this Protocol receives
  no fabric object other than ``Agent``, because no method here accepts one.
  ``tests/harness/test_protocol.py`` pins the absence by source scan, and
  ``ccf.harness`` is not in ``ccf.agents``' import closure, so this plan widens
  no allowlist and owes no transitive-closure argument.
* **Direct-import-checked:** ``Agent`` itself imports no L1–L5 module —
  ``tests/agents/test_consumption_discipline.py`` asserts it. That check is a
  **direct-import** check with **no transitive closure** (D-22), so the claim
  this surface has earned is "``Agent``'s own imports reach no fabric layer",
  not "provably no path from the harness to L1–L5". Do not upgrade the wording.

**The loop is the harness's.** Nothing here is a ``run``, ``step``, ``plan``, or
``invoke``. The seams translate between CCF values and whatever the harness
natively wants; the harness then does its own thing with them. That is why three
seams return :class:`object`: the harness-native carrier is harness-shaped by
definition, and a more precise annotation on this surface would make the fabric
harness-shaped, which §7.3 forbids. The adapter under
``ccf_runtime.adapters.<harness>/`` narrows those types for itself.

**The seams must fit all three D-IMPL-24 harnesses, which are not alike.** Claude
Agent SDK and Google ADK expose callbacks into a loop *they* own; LangGraph has
no loop to hook — the adapter builds the graph. So the seams are shaped as
*translations that produce harness-native artifacts*, never as callback
registrations, because a callback-shaped Protocol would fit two of the three and
force the LangGraph adapter to fake a loop it does not have.

That shaping is now tested against both shapes and **forced no change to this
surface** (06-12 Claude Agent SDK, 06-13 LangGraph). The mechanism, stated so a
later edit does not undo it by accident: because every seam is a *plain
translation the adapter itself calls*, a topology-owning adapter can call it
from inside a node it built — LangGraph's effect node is literally a call to
:meth:`HarnessAdapterProtocol.capture_effect` — while a callback-shaped seam
would have required the harness to call CCF, which is the thing LangGraph has
no loop to do. **No method or field here names a harness, and no implementation
in ``/src`` branches on harness identity**; the two shapes are accommodated by
the seams being translations, not by a conditional. Google ADK (06-14) is the
third data point and is callback-shaped like Claude, so the interesting case is
already covered.

Seam status is D-IMPL-25, not this module's to reinterpret: context injection,
effect capture, and replay hooks are mandatory for every conforming adapter;
skill exposure is mandatory exactly when the bound agent's EXPOSABLE skill-set
is non-empty — the bound skills whose type is in
:data:`ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES` (``TP-03``,
``D-IMPL-361``). A bound ``peering``, ``mcp_product`` or ``procedure`` skill is
never a harness tool. ``effects: unsupported`` is a *declared value* on
:class:`HarnessCapabilities`, never a missing field — and D-10 makes the
declaration only half the requirement: the conformance suite drives an
effect-producing path and asserts the refusal fired and nothing reached the
graph. A capability nobody exercises is a comment.

Algorithmic module (CINV-03): this declaration performs no semantic work and
imports no LLM client. **Adapters implementing it must not claim the tag** —
they bind a harness that reaches a model, which makes them the semantic
boundary of the Algorithmic ⇄ Semantic Alternation, not an algorithmic module.

Citation: CLAUDE.md §7.3 (SDK-defined extension); D-IMPL-24 (all three v0
harnesses); D-IMPL-25 (seam scope); D-IMPL-53 (the lint carve-out); D-25 /
D-IMPL-55 (the replay slot seam 4 writes into).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol, runtime_checkable

from ccf.agents.agent import Agent, EmittedEffect
from ccf.contracts.base import CCFContract
from ccf.products.contract import ContextProductContract
from ccf.replay.record import HarnessTrace

__ccf_mode__ = "algorithmic"

__all__ = [
    "EFFECT_CAPABILITIES",
    "EffectCapability",
    "EffectRefusal",
    "HarnessAdapterProtocol",
    "HarnessCapabilities",
]

#: What an adapter may declare about its effect-capture seam (D-IMPL-25).
#:
#: ``governed`` — harness outputs are routed back through governed emission and
#: returned as an :class:`~ccf.agents.agent.EmittedEffect`.
#: ``unsupported`` — a read-only consumer adapter. This is a *conformance-verified
#: absence*, not an opt-out: D-10 requires the suite to drive an effect-producing
#: path and assert that the refusal fired, that nothing reached the graph, and
#: that no write handle was obtainable from the adapter's public surface.
EffectCapability = Literal["governed", "unsupported"]

#: The declarable effect capabilities, for composition-root validation.
EFFECT_CAPABILITIES: frozenset[str] = frozenset({"governed", "unsupported"})


class HarnessCapabilities(CCFContract):
    """What an adapter declares about itself, in typed form.

    ``extra=forbid`` and frozen by inheritance: a capability the SDK does not
    know about is a disagreement between adapter and fabric, not an extension
    point, and a capability that could be mutated after the composition root
    read it would be a claim with no shelf life.

    Neither field has a default. ``effects`` in particular is **required**: a
    defaulted capability would let an adapter that never thought about effect
    capture inherit a claim about it, which is precisely the difference
    D-IMPL-25 draws between a conformance-verified absence and an
    unimplemented seam. The other three seams are unconditionally mandatory, so
    there is nothing to declare about them — an adapter that does not bind them
    is not a conforming adapter, and a field saying so would be a field that can
    lie.

    Attributes:
        harness_id: Stable identifier of the harness this adapter binds. Lands
            verbatim in :attr:`~ccf.replay.record.HarnessTrace.harness_id`, so
            it is the value a replay reads to answer "which harness ran this".
        effects: The effect-capture seam's declared capability (D-IMPL-25, D-10).
    """

    harness_id: str
    effects: EffectCapability


class EffectRefusal(CCFContract):
    """A harness output the effect-capture seam declined to emit.

    A **returned typed value, never an exception** — the established discipline
    for gate refusals across the SDK (``GateRefusal``, ``GrantRefusal``,
    ``RegistrationRefusal``): a refusal is an outcome the caller inspects and
    audits, and an exception would make "the harness produced something and the
    fabric refused it" indistinguishable from a bug in the adapter.

    An adapter declaring ``effects: unsupported`` returns this for every output.
    An adapter declaring ``effects: governed`` returns it when the output is not
    admissible. In neither case does anything reach L3: emission is a value the
    caller carries to L2, single-writer holds across this boundary by the shape
    of the seam (CLAUDE.md §7.3 seam 3, §10).

    Attributes:
        harness_id: Which adapter refused.
        agent_definition_hash: The agent the output was produced under (D-06),
            so the refusal stays attributable without consulting live state.
        reason: Why, in the adapter's own words. Audited, not parsed.
    """

    harness_id: str
    agent_definition_hash: str
    reason: str


@runtime_checkable
class HarnessAdapterProtocol(Protocol):
    """Structural contract for a harness binding (CLAUDE.md §7.3; D-IMPL-25).

    Implementations live under ``runtime/ccf_runtime/adapters/<harness>/`` and
    nowhere else (D-04, D-IMPL-53). Conformance is verified by the shared
    factory-parametrized suite run against the **real** SDKs with no LLM calls
    (D-09) — a double written to the Protocol we designed can pass while the
    real surface disagrees, which is the failure this whole seam exists to
    prevent.

    ``runtime_checkable`` supports composition-root wiring checks; it verifies
    method presence only, so static conformance still rests on mypy.

    Every method is keyword-only after ``self``: these arguments are never
    positional-by-accident, and adding a seam parameter later must not silently
    reorder an existing call.
    """

    def capabilities(self) -> HarnessCapabilities:
        """Declare this adapter's harness identity and effect capability.

        Read by the composition root before anything is bound, and by the
        conformance suite before it drives the effect path (D-10).
        """
        ...

    def inject_context(
        self,
        *,
        agent: Agent,
        products: tuple[ContextProductContract, ...],
        instructions: tuple[str, ...],
    ) -> object:
        """Seam 1 — typed context into the harness's own context surface.

        Mandatory (D-IMPL-25). Returns the harness-native carrier the harness
        will actually consume: ``ClaudeAgentOptions`` under the Claude Agent
        SDK, an ``LlmAgent`` instruction (string or ``ReadonlyContext`` closure)
        under Google ADK, and — because a topology-owning adapter has no loop
        to hand options to — the compiled ``StateGraph`` together with the
        initial state and run configuration under LangGraph. Typed
        :class:`object` deliberately — see the module docstring. Note how far
        apart those three carriers are: that distance is the reason this return
        type is not narrowed.

        ``products`` are already-gated Context Products the agent has already
        admitted through :meth:`~ccf.agents.agent.Agent.consume`; the harness
        never touches L3 or raw signal, because nothing on this surface can
        reach either.

        ``instructions`` are **already-rendered** strings from
        :func:`ccf.agents.prompts.render_instruction`, produced from the
        artifacts the factory already pinned onto ``agent``. **The adapter must
        not re-resolve or re-render prompt artifacts** — the factory pinned
        them, and this seam consumes them (``PHASE_I2_GATE.md`` §5). Re-resolution
        would let two decisions under the same agent version render different
        instructions, which makes the agent version a lie (T-06-64).
        """
        ...

    def expose_skills(self, *, agent: Agent) -> tuple[str, ...]:
        """Seam 2 — exactly the currently-bound exposable skill-set, as harness tools.

        Mandatory exactly when the agent's bound skill-set has a member whose
        type is in :data:`ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES`
        (D-IMPL-25, re-read by ``TP-03`` / ``D-IMPL-361``: a non-empty
        EXPOSABLE skill-set). Bound ``peering``, ``mcp_product`` and
        ``procedure`` skills are skipped, never rendered and never raised on.
        Returns the skill names the adapter actually exposed, sorted, so the
        conformance suite can compare them against the exposable subset of
        :attr:`~ccf.agents.agent.Agent.bound_skill_names` directly: a skill the
        agent has not been granted must not exist from the harness's point of
        view, and returning names rather than harness-native tool objects is
        what makes that assertion structural instead of a reading of adapter
        code (T-02-27; CLAUDE.md §6.2 channel 2, §7.3 seam 2).

        The harness-native tool objects the adapter builds — Claude's
        ``create_sdk_mcp_server`` tools, ADK's ``FunctionTool``s, LangGraph's
        ``StructuredTool``s — are the adapter's own business and are attached to
        the carrier :meth:`inject_context` returned. Binding is resolved at
        invoke time from the ledger-backed view the factory injected, so a
        revocation takes effect without the agent's identity changing (D-07).
        """
        ...

    def capture_effect(
        self, *, agent: Agent, output: Mapping[str, Any]
    ) -> EmittedEffect | EffectRefusal:
        """Seam 3 — a harness output back through governed emission.

        Mandatory (D-IMPL-25), and mandatory *including* the ``unsupported``
        case: an adapter declaring ``effects: unsupported`` implements this and
        returns :class:`EffectRefusal` for every output, which is what makes the
        absence conformance-verifiable rather than merely unimplemented (D-10).

        The return value is the entire effect. A harness never acquires a write
        handle to the graph — no such handle appears on this surface to be
        acquired — and carrying an admitted effect into L3 is L2's job (single-writer,
        CLAUDE.md §10, §7.3 seam 3). All three v0 harnesses expose a genuine
        refusal hook rather than merely an absent write path (Claude's
        ``PermissionResultDeny``, ADK's short-circuiting ``before_tool_callback``,
        LangGraph's adapter-owned node), so the refusal is something the adapter
        can actually assert, not something it can only decline to do.
        """
        ...

    def replay_trace(self, *, execution: object) -> HarnessTrace:
        """Seam 4 — the harness's execution into replay dimension 3.

        Mandatory (D-IMPL-25). Translates the harness-native execution result —
        Claude's ``ResultMessage``, ADK's ``Event`` stream, the final state a
        LangGraph run produced — into the
        :class:`~ccf.replay.record.HarnessTrace` block that
        :func:`~ccf.replay.record.build_replay_record` records **verbatim**
        under ``model_version.harness_trace`` (D-25, D-IMPL-55).

        Only harness-attributable values belong here: which harness, the model
        version *it* reported, its trace reference, its token counts. These are
        exactly the fields D-18 excludes from the harness-portability
        comparison, and the reason they live in a named block is that one agent
        definition run under three adapters must agree exactly on everything CCF
        governs and differ only here. Writing a governed field from this seam is
        not possible: the block is a leaf, and dimension 3's ``assembly_mode``
        and ``model_version`` are the fabric's own claims (T-06-62).

        ``execution`` is whatever the harness hands back, and 06-13 found the
        one asymmetry worth naming: a topology-owning harness exposes its run
        configuration only *inside* the topology, so the adapter captures it in
        a node it owns and the execution result carrying it is a plain final
        state. That is an adapter concern, not a Protocol one — the seam takes
        :class:`object` and the adapter narrows it — but an adapter author who
        expects a rich vendor result object here will not find one.

        An adapter that cannot determine a field leaves it at its positive
        :data:`~ccf.replay.record.NO_HARNESS` sentinel rather than guessing —
        an absent trace and a dropped one must not be the same artifact
        (T-06-63).
        """
        ...
