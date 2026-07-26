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
from ccf.controlplane.artifacts import ArtifactClass, validate_semver

__ccf_mode__ = "algorithmic"

__all__ = [
    "AGENT_DEFINITION",
    "ARCHETYPE_IDS",
    "PROMPT_ARTIFACT",
    "AgentDefinition",
    "ConsumedProduct",
    "ContextContract",
    "InstructionBinding",
    "PerspectiveBinding",
    "PromptArtifact",
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
    :class:`~ccf.controlplane.artifacts._VersionedArtifact` because definition
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


class ContextContract(CCFContract):
    """Axis 2 — which Context Product schemas the agent reads (CLAUDE.md §6.2).

    Emission bindings (which projection an assembler emits to) extend this
    contract when the ContextAssembly archetype's transport lands; the shape is
    additive by design.
    """

    consumes: tuple[ConsumedProduct, ...]

    @model_validator(mode="after")
    def _contract_is_nonempty(self) -> "ContextContract":
        if not self.consumes:
            raise ValueError(
                "a context contract must name at least one consumed product;"
                " an agent that reads nothing has no fabric relationship to"
                " declare (CLAUDE.md §6.2 axis 2)"
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
