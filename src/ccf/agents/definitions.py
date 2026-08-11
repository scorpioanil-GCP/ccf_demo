"""The D-IMPL-28 definition-artifact schemas (CLAUDE.md §6 — SDK-defined).

An **agent is a declared, versioned Control Plane artifact — data, not code**
(CLAUDE.md §6.1). This module is the schema half of that commitment: the
typed contracts a serialized agent definition or prompt artifact must satisfy
to be admitted, in the exact style of
:mod:`ccf.controlplane.artifacts` (same loader, same float refusal, same
closed-world discipline). The definitions themselves live in YAML under
version control or the ArtifactStore; `/src` holds only this shape.

Three disciplines are load-bearing:

**Two-field versioning (D-IMPL-28).** ``schema_version`` is the artifact
class's lane — which shape of document this is. ``artifact_version`` is the
author's statement that the *content* changed. The Control Plane's D-05
hash-verified bump check holds authors to that statement at registration.

**All six specialization axes, all required (CLAUDE.md §6.2 channel 1;
D-IMPL-38 no-silent-defaults).** Archetype binding, context contract,
perspective, policy regime, half-life/debt profile, instruction bindings. A
definition missing an axis is refused, not defaulted — a default axis is a
value the SDK chose on a deployment's behalf.

**Refs, never inline (§6.4 No-Hardcoding; D-13).** Policy regimes, debt
profiles, and prompts are referenced by versioned ``ccf-artifact://`` URI.
There is no field on any contract here that could carry prompt text into an
agent definition, and ``@latest`` is refused at validation because a
definition that resolves a moving target describes a different agent every
time it is read (D-IMPL-26).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import field_validator, model_validator

from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver

__ccf_mode__ = "algorithmic"

__all__ = [
    "AGENT_DEFINITION",
    "ARCHETYPE_IDS",
    "ASSEMBLY_ARCHETYPE_ID",
    "EMITS_NOTHING",
    "PROMPT_ARTIFACT",
    "TASK_DEFINITION",
    "TASK_STEP_KINDS",
    "AgentDefinition",
    "ConsumedProduct",
    "ContextContract",
    "EmittedProduct",
    "InstructionBinding",
    "PerspectiveBinding",
    "PromptArtifact",
    "TaskDefinition",
    "TaskStep",
    "VersionedRef",
]

#: The six shipped archetype identifiers (CLAUDE.md §6.3). Identifiers of SDK
#: mechanism, not domain values: each names a functional template the SDK
#: ships, and a definition declaring anything else is malformed rather than
#: merely unknown.
ARCHETYPE_IDS: frozenset[str] = frozenset(
    {
        "workflow",
        "document_intelligence",
        "analytics_insights",
        "monitoring_surveillance",
        "content_generation",
        "context_assembly",
    }
)

#: The archetype an emission binding requires (``docs/DECISIONS.md``
#: D-IMPL-97 ruling 2). Named once here rather than spelled at each site that
#: needs it, so the schema, the factory and the archetype registry cannot drift
#: to two readings of which archetype supplies the emission pattern.
ASSEMBLY_ARCHETYPE_ID = "context_assembly"


def _validate_artifact_ref(value: str) -> str:
    """Return ``value`` if it is a well-formed, pinned artifact URI.

    Delegates to :func:`ccf.artifacts.protocol.parse_artifact_uri`, so a ref
    asking for ``@latest`` or missing a version is refused with the same rule
    every other resolver applies (D-IMPL-26). Store errors are re-raised as
    ``ValueError`` so Pydantic reports them as validation failures.
    """
    try:
        parse_artifact_uri(value)
    except ArtifactStoreError as error:
        raise ValueError(str(error)) from error
    return value


class _TwoLaneVersioned(CCFContract):
    """Shared D-IMPL-28 surface: schema lane + author-bumped artifact version.

    Distinct from the single-lane
    :class:`~ccf.controlplane.artifact_base.VersionedArtifact` because definition
    artifacts carry two statements, not one: which schema shape they satisfy
    (``schema_version``) and which content revision they are
    (``artifact_version``, hash-verified per D-05).
    """

    schema_version: str
    artifact_version: str

    @field_validator("schema_version", "artifact_version")
    @classmethod
    def _versions_are_semver(cls, value: str) -> str:
        return validate_semver(value)


class ConsumedProduct(CCFContract):
    """One Context Product schema an agent reads (axis 2; CLAUDE.md §6.2).

    ``schema_version`` pins the product class's own lane — a consumer that
    names no version consumes whatever the producer ships next, which is a
    contract drift replay cannot survive (whitepaper §6.3).
    """

    product_class: str
    schema_version: str

    @field_validator("schema_version")
    @classmethod
    def _version_is_semver(cls, value: str) -> str:
        return validate_semver(value)


class EmittedProduct(CCFContract):
    """One Context Product schema an agent emits to (axis 2; D-IMPL-97).

    The producing counterpart of :class:`ConsumedProduct`, and pinned on the
    same reasoning: ``schema_version`` names the class's own lane, because a
    producer that named no version would be claiming to satisfy whatever shape
    the class takes next — a contract drift replay cannot survive (whitepaper
    §6.3, INV-CH7-49).

    A separate contract from :class:`ConsumedProduct` rather than a reuse of
    it, because the two are read by different mechanism and refused on
    different grounds: a consumed class is checked at
    :meth:`ccf.agents.agent.Agent.consume`, an emitted class at construction
    against what the deployment has registered. Sharing the type would make
    "which side is this?" a question the code could not answer.
    """

    product_class: str
    schema_version: str

    @field_validator("schema_version")
    @classmethod
    def _version_is_semver(cls, value: str) -> str:
        return validate_semver(value)


#: The positive claim that an agent emits no Context Product.
#:
#: A named sentinel rather than a bare empty tuple, in the
#: :data:`~ccf.replay.record.NO_GRANTS_SET_HASH` voice: *this agent emits
#: nothing* is a statement its author made, distinguishable from an emission
#: binding somebody dropped only because the claim is named. It is also what
#: keeps the widening additive — every agent definition authored before this
#: field existed keeps asserting exactly what it always asserted.
EMITS_NOTHING: tuple[EmittedProduct, ...] = ()


class ContextContract(CCFContract):
    """Axis 2 — the Context Product schemas an agent reads, and emits to.

    CLAUDE.md §6.2. Both directions live here, on one contract, because they
    are one axis: what an agent's fabric relationship *is*. The emission side
    landed with the assembler surface (``docs/DECISIONS.md`` D-IMPL-97 ruling
    2), on the seam this contract's own earlier docstring reserved for it —
    *"emission bindings … extend this contract when the ContextAssembly
    archetype's transport lands; the shape is additive by design"* — rather
    than as a parallel artifact beside it.

    **Additive means additive.** ``consumes`` keeps its shape and its
    non-empty rule; ``emits`` defaults to the positive
    :data:`EMITS_NOTHING` claim, so every shipped definition and every fixture
    parses byte-unchanged and means what it meant.

    **What is *not* checked here.** That an emitting definition is built from
    the ``context_assembly`` archetype, and that the class it emits to is one
    the deployment registered, are both refused by
    :class:`~ccf.agents.factory.AgentFactory` rather than by this schema. The
    schema knows the shape of a document; only the factory holds the archetype
    bundles and the deployment's registered classes, and a check that cannot
    see both sides cannot name both sides.

    Attributes:
        consumes: The product classes this agent reads. At least one — an
            agent that reads nothing has no fabric relationship to declare.
        emits: The product classes this agent assembles and emits, or
            :data:`EMITS_NOTHING`.
    """

    consumes: tuple[ConsumedProduct, ...]
    emits: tuple[EmittedProduct, ...] = EMITS_NOTHING

    @model_validator(mode="after")
    def _contract_is_nonempty(self) -> "ContextContract":
        if not self.consumes:
            raise ValueError(
                "a context contract must name at least one consumed product;"
                " an agent that reads nothing has no fabric relationship to"
                " declare (CLAUDE.md §6.2 axis 2)"
            )
        return self

    @model_validator(mode="after")
    def _emissions_are_distinct(self) -> "ContextContract":
        emitted = [(e.product_class, e.schema_version) for e in self.emits]
        if len(set(emitted)) != len(emitted):
            raise ValueError(
                "a context contract names the same emitted product class and"
                f" lane twice ({sorted(emitted)!r}); an agent emits to a class"
                " or it does not, and a duplicate binding would make one"
                " declaration mean two things (CLAUDE.md §6.2 axis 2)"
            )
        return self


class PerspectiveBinding(CCFContract):
    """Axis 3 — the Π role-conditioning shaping the agent's view (§6.2).

    ``selection_params`` is deployment vocabulary; the SDK enumerates none of
    it. Values are strings because they participate in canonical serialization
    and therefore in content identity — a float here would make the agent's
    identity platform-dependent.
    """

    role: str
    selection_params: Mapping[str, str]


class VersionedRef(CCFContract):
    """A pinned ``ccf-artifact://`` reference (axes 4 and 5; D-IMPL-26).

    A ref, never the artifact: the policy bundle and the debt profile are
    Control Plane artifacts with their own lanes, and inlining either into a
    definition would give one document two version identities.
    """

    ref: str

    @field_validator("ref")
    @classmethod
    def _ref_is_a_pinned_artifact_uri(cls, value: str) -> str:
        return _validate_artifact_ref(value)


class InstructionBinding(CCFContract):
    """Axis 6 — one prompt reference plus its declared parameters (D-13).

    ``prompt`` is a versioned URI; the template text lives in the referenced
    :class:`PromptArtifact`, never here (No-Hardcoding Rule, §6.4). This
    contract deliberately has no field that could carry inline prompt text.
    ``parameters`` are the names the binding declares it will supply, validated
    against the artifact's own declaration by
    :func:`ccf.agents.prompts.validate_instruction_binding`.
    """

    prompt: str
    parameters: tuple[str, ...]

    @field_validator("prompt")
    @classmethod
    def _prompt_is_a_pinned_artifact_uri(cls, value: str) -> str:
        return _validate_artifact_ref(value)


class AgentDefinition(_TwoLaneVersioned):
    """A declared, versioned agent — all six specialization axes (§6.1/§6.2).

    SDK-defined (CLAUDE.md §6; D-IMPL-28). The artifact the Agent Factory
    interprets and the only supported description of an agent; nothing here is
    executable. Changing any axis is a new agent version (channel 1);
    capability changes travel through skilling (channel 2) and never touch
    this contract.
    """

    name: str
    tenant: str
    archetypes: tuple[str, ...]
    context_contract: ContextContract
    perspective: PerspectiveBinding
    policy_regime: VersionedRef
    halflife_debt_profile: VersionedRef
    instruction_bindings: tuple[InstructionBinding, ...]

    @model_validator(mode="after")
    def _archetypes_are_known_and_nonempty(self) -> "AgentDefinition":
        if not self.archetypes:
            raise ValueError(
                "an agent must declare at least one archetype (CLAUDE.md §6.1:"
                " archetypes supply the execution and fabric-interaction"
                " patterns; an agent bound to none has neither)"
            )
        unknown = [a for a in self.archetypes if a not in ARCHETYPE_IDS]
        if unknown:
            raise ValueError(
                f"unknown archetype identifier(s) {unknown!r}; the shipped"
                f" archetypes are {sorted(ARCHETYPE_IDS)} (CLAUDE.md §6.3)"
            )
        return self


#: The three step kinds a workflow step can declare (CLAUDE.md §8.1: "each
#: step in a workflow is either a skill invocation, an agent invocation, or a
#: HITL gate"). Mechanism identifiers, not domain values.
TASK_STEP_KINDS: frozenset[str] = frozenset({"skill", "agent", "hitl-gate"})


class TaskStep(CCFContract):
    """One ordered step declaration in a task definition (CLAUDE.md §8.1; D-11).

    SDK-defined. ``skill`` and ``agent`` steps carry a pinned
    ``ccf-artifact://`` reference to the capability or agent definition they
    invoke — a ref, never the artifact, and never a moving target
    (D-IMPL-26). ``hitl-gate`` steps validate structurally and carry **no
    behavior and no reference in I.2**: gate semantics are I.4's Workflow
    primitive scope (D-11), and binding an approval policy before anything
    can execute would be a claim the artifact cannot yet honor.
    """

    kind: str
    name: str
    ref: str | None = None

    @field_validator("kind")
    @classmethod
    def _kind_is_a_known_step_kind(cls, value: str) -> str:
        if value not in TASK_STEP_KINDS:
            raise ValueError(
                f"unknown step kind {value!r}; a step is a skill invocation,"
                f" an agent invocation, or a hitl-gate"
                f" ({sorted(TASK_STEP_KINDS)}; CLAUDE.md §8.1)"
            )
        return value

    @model_validator(mode="after")
    def _ref_agrees_with_kind(self) -> "TaskStep":
        if self.kind == "hitl-gate":
            if self.ref is not None:
                raise ValueError(
                    f"hitl-gate step {self.name!r} must not carry a ref:"
                    " gate steps validate structurally and carry no behavior"
                    " in I.2 (D-11; gate semantics are I.4 scope)"
                )
            return self
        if self.ref is None:
            raise ValueError(
                f"{self.kind} step {self.name!r} must reference its target by"
                " pinned versioned URI (D-IMPL-26; CLAUDE.md §8.1)"
            )
        _validate_artifact_ref(self.ref)
        return self


class TaskDefinition(_TwoLaneVersioned):
    """A declared, versioned task — schema + validation only (D-11; §6.4/§8.1).

    SDK-defined (CLAUDE.md §6.4; D-IMPL-28). The artifact the Task Factory
    interprets; nothing here is executable, and no execution engine exists in
    I.2 — the Workflow primitive that will interpret constructed tasks is
    I.4 scope (D-11). Steps are ordered and reference agent definitions and
    skills by pinned versioned URI, in the same refs-never-inline discipline
    as agent definitions.
    """

    name: str
    tenant: str
    steps: tuple[TaskStep, ...]
    instruction_bindings: tuple[InstructionBinding, ...] = ()

    @model_validator(mode="after")
    def _steps_are_nonempty(self) -> "TaskDefinition":
        if not self.steps:
            raise ValueError(
                "a task must declare at least one step; a task with no steps"
                " describes no work (CLAUDE.md §8.1)"
            )
        return self


class PromptArtifact(_TwoLaneVersioned):
    """A versioned prompt/instruction artifact (axis 6; §6.4; D-13).

    SDK-defined (CLAUDE.md §6.2 axis 6). The template source and its declared
    parameters travel together so parse-only validation
    (:func:`ccf.agents.prompts.validate_prompt_artifact`) can hold them to
    exact agreement at load time — before any factory construction, and
    without rendering anything.
    """

    name: str
    tenant: str
    template: str
    declared_parameters: tuple[str, ...]


#: The agent-definition artifact class (CLAUDE.md §6.4; D-IMPL-28).
AGENT_DEFINITION = ArtifactClass(
    class_id="ccf.agent-definition", contract=AgentDefinition
)
#: The prompt-artifact class (CLAUDE.md §6.2 axis 6; D-13).
PROMPT_ARTIFACT = ArtifactClass(class_id="ccf.prompt-artifact", contract=PromptArtifact)
#: The task-definition artifact class (CLAUDE.md §6.4/§8.1; D-11).
TASK_DEFINITION = ArtifactClass(class_id="ccf.task-definition", contract=TaskDefinition)
