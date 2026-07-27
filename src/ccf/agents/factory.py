"""The Agent Factory (CLAUDE.md §6.4 — SDK-defined; DESIGN.md §3.5).

**The factory is the only construction path for agents.** It interprets a
declarative definition artifact, validates all six specialization axes,
composes the declared archetype bundles in declaration order, validates every
instruction binding against its resolved prompt artifact (D-13), computes the
D-06 identity block, and instantiates :class:`~ccf.agents.agent.Agent` — the
single legitimate ``Agent(...)`` call site in the codebase, enforced by the
CINV-01c factory-bypass lint (D-12: lint is the mechanism of record; no
construction token exists).

**The factory reads through Control Plane resolution, never raw storage**
(DESIGN.md §3.5). The resolution surface is injected as a Protocol
(:class:`ControlPlaneResolution`), in the same constructor-injection style as
the registry's clock: the in-process
:class:`~ccf.controlplane.registry.ControlPlaneRegistry` conforms, and so
would a remote plane. Every reference resolves at a **pinned version** — a
``ccf-artifact://`` ref asking for ``@latest`` is refused before it can reach
this module (schema-level, D-IMPL-26), and re-refused here by
:func:`~ccf.artifacts.protocol.parse_artifact_uri` as defense in depth.

Construction is deterministic: identical definition version plus identical
referenced-artifact versions produce an identical ``Agent`` configuration,
which is what makes agent identity replayable (DESIGN.md §3.5; D-06).

The composition step is a single seam (:func:`_compose`): bundle lookup
happens here, the D-IMPL-19 rules themselves are the pure functions of
:mod:`ccf.agents.composition`, and each order-resolved default conflict the
composition reports becomes a ``warnings.warn`` here — the factory is where
side effects live; composition stays pure. A hard contradiction propagates
as a construction failure (D-IMPL-19 rule 3).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping

from ccf.agents.agent import Agent, AgentIdentity
from ccf.agents.archetypes import ARCHETYPES, ArchetypeComponent
from ccf.agents.composition import compose
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    InstructionBinding,
    PromptArtifact,
    TaskDefinition,
)
from ccf.agents.errors import AgentDefinitionError
from ccf.agents.prompts import validate_instruction_binding
from ccf.artifacts.protocol import artifact_uri, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.resolution import ControlPlaneResolution, resolve_pinned
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SKILL_CATALOG_ENTRY
from ccf.skills.grants import BoundSkillView

#: The namespace prefix every artifact class the SDK itself owns carries.
#: Mechanism, not a value: it is how a deployment-declared class is told
#: apart from an SDK one without the SDK enumerating its own classes at every
#: call site (IN-05).
SDK_ARTIFACT_CLASS_PREFIX = "ccf."

__ccf_mode__ = "algorithmic"

__all__ = [
    "AgentFactory",
    "ControlPlaneResolution",
    "Task",
    "TaskFactory",
    "TaskIdentity",
]


def _resolve_pinned(control_plane: ControlPlaneResolution, uri: str) -> object:
    """Resolve one pinned ``ccf-artifact://`` reference, or refuse.

    The factory's wrapper around the shared
    :func:`~ccf.controlplane.resolution.resolve_pinned` (IN-01 — one
    implementation of the pinned-resolution rule, not two): the shared helper
    performs the key derivation, the content-hash fast path, the unaudited
    declared-version probe loop, and the WR-08 ambiguity refusal, and this
    wrapper supplies the factory's own reading of a miss. A reference the
    factory cannot follow is a broken definition (DESIGN.md §3.5 — the
    factory reads through Control Plane resolution, never raw storage), so
    the miss is raised rather than returned.

    Raises:
        AgentDefinitionError: the reference names nothing the Control Plane
            has registered.
        ccf.controlplane.registry.AmbiguousPinnedVersionError: two different
            contents under the key declare the same semver the URI pins
            (WR-08) — a pinned ref must name exactly one content.
        ccf.artifacts.protocol.MovingTargetRefused: the URI asks for
            ``@latest`` (defense in depth; the schema refuses it first).
    """
    artifact = resolve_pinned(control_plane, uri)
    if artifact is None:
        name = parse_artifact_uri(uri)
        key = f"{name.tenant_id}/{name.artifact_class}/{name.name}"
        raise AgentDefinitionError(
            f"reference {uri!r} resolves to nothing the Control Plane has"
            f" registered under {key!r}; the factory reads through Control"
            " Plane resolution at pinned versions only (DESIGN.md §3.5)"
        )
    return artifact


def _validated_instruction_artifacts(
    control_plane: ControlPlaneResolution,
    bindings: tuple[InstructionBinding, ...],
) -> dict[str, PromptArtifact]:
    """Resolve and validate every instruction binding (axis 6; D-13).

    Raises:
        PromptValidationError: a binding fails parse-only validation against
            its resolved prompt artifact.
        AgentDefinitionError: a prompt reference resolves to nothing.
        TypeError: a resolved artifact is not a prompt artifact.
    """
    resolved: dict[str, PromptArtifact] = {}
    for binding in bindings:
        prompt = PROMPT_ARTIFACT.validate(
            _resolve_pinned(control_plane, binding.prompt)
        )
        assert isinstance(prompt, PromptArtifact)
        validate_instruction_binding(binding, prompt)
        resolved[binding.prompt] = prompt
    return resolved


def _compose(archetypes: tuple[str, ...]) -> tuple[ArchetypeComponent, ...]:
    """Attach the declared bundles in declaration order (D-IMPL-19).

    Lookup here, rules in :func:`ccf.agents.composition.compose` (pure —
    dedupe identical obligations, declaration-order defaults, typed conflict
    facts, contradiction error), warnings here: each order-resolved default
    conflict the composition reports becomes one ``warnings.warn`` naming
    the key and both archetypes.

    Raises:
        AgentDefinitionError: a declared archetype identifier is known to the
            schema but realized by no shipped bundle.
        ccf.agents.composition.CompositionContradiction: two declared
            archetypes contribute mutually exclusive obligations (rule 3);
            propagates as a construction failure.
    """
    components: list[ArchetypeComponent] = []
    for identifier in archetypes:
        bundle = ARCHETYPES.get(identifier)
        if bundle is None:
            raise AgentDefinitionError(
                f"archetype {identifier!r} is declared but no shipped bundle"
                f" realizes it (shipped: {sorted(ARCHETYPES)}); the definition"
                " cannot be constructed (CLAUDE.md §6.3)"
            )
        components.append(bundle)
    composed = compose(components)
    for conflict in composed.conflicts:
        warnings.warn(
            f"configuration default {conflict.key!r} contributed by both"
            f" {conflict.winning_archetype!r} ({conflict.winning_value!r},"
            f" declared first — wins) and {conflict.losing_archetype!r}"
            f" ({conflict.losing_value!r}); declaration order wins"
            " (D-IMPL-19)",
            stacklevel=3,
        )
    return tuple(components)


class AgentFactory:
    """Constructs agents from definition artifacts — the only supported path.

    CLAUDE.md §6.4; D-IMPL-28. Tests construct agents the same way, from
    fixture artifacts; there is no path to an ``Agent`` that bypasses this
    class, and the CINV-01c lint holds the codebase to it (D-12).

    Args:
        control_plane: The injected resolution surface. Constructor injection,
            never ambient lookup — the factory holds no keys, no versions,
            and no storage handles of its own.
        callable_registry: The deployment's boot-time
            :class:`~ccf.skills.callables.CallableRegistry`, carried onto
            every constructed agent so ``local_callable`` dispatch resolves
            against what this composition root registered (D-19). ``None``
            registers nothing, which is a positive statement: every
            ``local_callable`` entry then resolves to nothing, without an
            import.
    """

    def __init__(
        self,
        *,
        control_plane: ControlPlaneResolution,
        callable_registry: CallableRegistry | None = None,
    ) -> None:
        self._control_plane = control_plane
        self._callable_registry = callable_registry

    def _resolve_reference(self, uri: str) -> object:
        """Resolve one pinned reference via :func:`_resolve_pinned`."""
        return _resolve_pinned(self._control_plane, uri)

    def construct(
        self,
        *,
        definition_key: str,
        definition_version: str,
        bound_skills: BoundSkillView | None = None,
    ) -> Agent:
        """Resolve, validate, compose, and instantiate one agent.

        ``bound_skills`` is the channel-2 seam (CLAUDE.md §6.2), typed so its
        only producer is the grant ledger (WR-03): pass the ledger's live
        :class:`~ccf.skills.grants.BoundSkillView`
        (:meth:`ccf.skills.grants.GrantLedger.bound_view`) and the agent
        resolves its currently-bound skill-set from ledger state at invoke
        time — grants and revocations never re-construct the agent or touch
        its identity (D-07). An arbitrary mapping is refused at construction:
        capabilities reach an agent through governed grants exclusively.
        ``None`` binds nothing: an agent granted nothing has no skills,
        positively.

        The four steps in order: (1) resolve the definition and every
        referenced artifact at pinned versions; (2) hold the resolved
        definition to its artifact class; (3) compose the declared archetype
        bundles in declaration order; (4) validate every instruction binding
        against its resolved prompt artifact (D-13). Only then is the D-06
        identity block computed — hash, versioned-URI annotation, archetype
        tuple, all captured at construction time — and the ``Agent``
        instantiated.

        Raises:
            AgentDefinitionError: a declared archetype has no shipped bundle,
                or a referenced artifact cannot be resolved.
            PromptValidationError: an instruction binding fails parse-only
                validation against its prompt artifact (D-13).
            TypeError: a resolved artifact does not satisfy its declared
                artifact class.
            ControlPlaneMissing: no definition is registered as
                ``(definition_key, definition_version)``.
        """
        resolved = self._control_plane.resolve(definition_key, definition_version)
        definition = AGENT_DEFINITION.validate(resolved)
        assert isinstance(definition, AgentDefinition)

        # Axes 4 and 5: the refs must resolve, at their pinned versions.
        self._resolve_reference(definition.policy_regime.ref)
        self._resolve_reference(definition.halflife_debt_profile.ref)

        # Axis 1: compose the declared bundles in declaration order.
        components = _compose(definition.archetypes)

        # Axis 6: every binding validated against its resolved artifact.
        instruction_artifacts = _validated_instruction_artifacts(
            self._control_plane, definition.instruction_bindings
        )

        identity = AgentIdentity(
            definition_hash=content_hash(definition),
            definition_uri=artifact_uri(
                tenant_id=definition.tenant,
                artifact_class=AGENT_DEFINITION.class_id,
                name=definition.name,
                artifact_version=definition.artifact_version,
            ),
            archetype_composition=definition.archetypes,
        )
        return Agent(
            definition=definition,
            identity=identity,
            components=components,
            instruction_artifacts=instruction_artifacts,
            bound_skills=bound_skills,
            callable_registry=self._callable_registry,
        )


class TaskIdentity(CCFContract):
    """A constructed task's identity block (D-IMPL-26; D-11).

    The same derived-at-construction discipline as
    :class:`~ccf.agents.agent.AgentIdentity`: content hash as canonical
    identity, versioned URI carried as annotation.

    Attributes:
        definition_hash: Content hash of the task definition.
        definition_uri: The definition's versioned URI annotation.
    """

    definition_hash: str
    definition_uri: str


class Task:
    """One declared task, constructed form — data, never execution (D-11).

    SDK-defined (CLAUDE.md §6.4/§8.1). A validated task definition plus its
    identity block and the artifacts its steps and bindings resolved to.
    **There is no execution surface here and none ships in I.2**: no
    ``execute``, ``run``, ``step``, ``loop``, or ``plan`` — the Workflow
    primitive that interprets constructed tasks is I.4 scope (D-11), and no
    replay capture exists for tasks because nothing executes and therefore
    nothing records. Construct through :class:`TaskFactory` only (§6.4);
    the CINV-01c lint holds the codebase to it (D-12).

    Args:
        definition: The validated task definition this object realizes.
        identity: The construction-time identity block; must agree with
            ``definition``, or construction is refused.
        resolved_refs: The step-referenced artifacts, keyed by versioned URI.
        instruction_artifacts: Resolved prompt artifacts keyed by the
            binding's versioned URI (validated per D-13).

    Raises:
        AgentDefinitionError: the identity block does not describe
            ``definition`` (content identity is task identity, D-IMPL-26).
    """

    def __init__(
        self,
        *,
        definition: TaskDefinition,
        identity: TaskIdentity,
        resolved_refs: Mapping[str, object],
        instruction_artifacts: Mapping[str, PromptArtifact],
    ) -> None:
        expected_hash = content_hash(definition)
        if identity.definition_hash != expected_hash:
            raise AgentDefinitionError(
                "identity.definition_hash does not equal the content hash of"
                f" the task definition ({identity.definition_hash!r} !="
                f" {expected_hash!r}); task identity is content identity"
                " (D-IMPL-26)"
            )
        expected_uri = artifact_uri(
            tenant_id=definition.tenant,
            artifact_class=TASK_DEFINITION.class_id,
            name=definition.name,
            artifact_version=definition.artifact_version,
        )
        if identity.definition_uri != expected_uri:
            raise AgentDefinitionError(
                "identity.definition_uri does not name the task definition"
                f" ({identity.definition_uri!r} != {expected_uri!r}); the URI"
                " is derived from the definition's own naming triple and"
                " version (D-IMPL-26; IN-02, applied to the sibling path)"
            )
        self._definition = definition
        self._identity = identity
        self._resolved_refs = dict(resolved_refs)
        self._instruction_artifacts = dict(instruction_artifacts)

    @property
    def definition(self) -> TaskDefinition:
        """The validated task definition this object realizes."""
        return self._definition

    @property
    def identity(self) -> TaskIdentity:
        """The construction-time identity block (D-IMPL-26)."""
        return self._identity

    def resolved_ref(self, uri: str) -> object:
        """Return the artifact a step's ``uri`` resolved to at construction.

        Introspection only — nothing dispatches (D-11).

        Raises:
            KeyError: no step in the definition references ``uri``.
        """
        return self._resolved_refs[uri]

    def instruction_artifact(self, prompt_uri: str) -> PromptArtifact:
        """Return the resolved prompt artifact bound under ``prompt_uri``.

        Raises:
            KeyError: no instruction binding references ``prompt_uri``.
        """
        return self._instruction_artifacts[prompt_uri]


class TaskFactory:
    """Constructs tasks from definition artifacts — the only supported path.

    CLAUDE.md §6.4; D-11; D-IMPL-28. Mirrors :class:`AgentFactory`'s
    resolve → validate → instantiate flow minus archetype composition:
    tasks bind no archetypes, and nothing constructed here can execute —
    execution semantics are I.4's Workflow primitive scope. The single
    legitimate ``Task(...)`` call site is this module, enforced by the
    CINV-01c factory-bypass lint (D-12).

    Args:
        control_plane: The injected resolution surface (constructor
            injection, never ambient lookup), as for :class:`AgentFactory`.
    """

    def __init__(self, *, control_plane: ControlPlaneResolution) -> None:
        self._control_plane = control_plane

    def construct(self, *, definition_key: str, definition_version: str) -> Task:
        """Resolve, validate, and instantiate one task (D-11 — no execution).

        Steps in order: (1) resolve the definition at its pinned version and
        hold it to its artifact class; (2) resolve every skill/agent step
        reference through Control Plane resolution (hitl-gate steps carry no
        reference in I.2) and hold it to what its step kind may reference;
        (3) validate every instruction binding against its resolved prompt
        artifact (D-13). Only then is the identity block computed and the
        ``Task`` instantiated.

        **The two step-kind checks are deliberately asymmetric (IN-05).** An
        ``agent`` step must resolve to exactly ``ccf.agent-definition`` — the
        SDK owns both sides of that relationship, so equality is checkable
        (IN-08). A ``skill`` step cannot be held to one class, because a
        skill target may be a deployment-declared class the SDK has no name
        for; holding it to ``ccf.skill-catalog-entry`` would break the
        extension point. It is instead held to a *negative* rule: the SDK's
        own non-skill classes are refused, and everything else — including
        every deployment-declared class — passes.

        Raises:
            AgentDefinitionError: a step reference resolves to nothing, an
                ``agent`` step references a non-agent-definition class, or a
                ``skill`` step references an SDK-owned non-skill class.
            PromptValidationError: an instruction binding fails parse-only
                validation against its prompt artifact (D-13).
            TypeError: a resolved artifact does not satisfy its declared
                artifact class.
            ControlPlaneMissing: no definition is registered as
                ``(definition_key, definition_version)``.
        """
        resolved = self._control_plane.resolve(definition_key, definition_version)
        definition = TASK_DEFINITION.validate(resolved)
        assert isinstance(definition, TaskDefinition)

        resolved_refs: dict[str, object] = {}
        for step in definition.steps:
            if step.ref is not None:
                resolved_refs[step.ref] = _resolve_pinned(
                    self._control_plane, step.ref
                )
                ref_name = parse_artifact_uri(step.ref)
                ref_key = (
                    f"{ref_name.tenant_id}/{ref_name.artifact_class}/"
                    f"{ref_name.name}"
                )
                actual_class = self._control_plane.artifact_class_of(ref_key)
                if step.kind == "agent":
                    if actual_class != AGENT_DEFINITION.class_id:
                        raise AgentDefinitionError(
                            f"agent step {step.name!r} references"
                            f" {step.ref!r}, which the Control Plane binds to"
                            f" artifact class {actual_class!r}, not"
                            f" {AGENT_DEFINITION.class_id!r}; an agent step"
                            " must reference an agent definition (IN-08;"
                            " CLAUDE.md §8.1)"
                        )
                elif step.kind == "skill":
                    # Asymmetric with the agent case, necessarily (IN-05): a
                    # skill step's target may be a deployment-declared class
                    # the SDK has no name for, so the check cannot be an
                    # equality against one class id. What it *can* do is
                    # refuse the SDK's own non-skill classes — an agent
                    # definition, a prompt artifact, a task definition, a
                    # grant — which are never a skill target and whose
                    # appearance here is miswiring rather than an extension
                    # point. Deployment-declared classes pass untouched.
                    if (
                        actual_class is not None
                        and actual_class.startswith(SDK_ARTIFACT_CLASS_PREFIX)
                        and actual_class != SKILL_CATALOG_ENTRY.class_id
                    ):
                        raise AgentDefinitionError(
                            f"skill step {step.name!r} references"
                            f" {step.ref!r}, which the Control Plane binds to"
                            f" the SDK-owned artifact class"
                            f" {actual_class!r}; a skill step references a"
                            f" {SKILL_CATALOG_ENTRY.class_id!r} or a"
                            " deployment-declared class, never another"
                            " SDK artifact class (IN-05; CLAUDE.md §8.1)"
                        )

        instruction_artifacts = _validated_instruction_artifacts(
            self._control_plane, definition.instruction_bindings
        )

        identity = TaskIdentity(
            definition_hash=content_hash(definition),
            definition_uri=artifact_uri(
                tenant_id=definition.tenant,
                artifact_class=TASK_DEFINITION.class_id,
                name=definition.name,
                artifact_version=definition.artifact_version,
            ),
        )
        return Task(
            definition=definition,
            identity=identity,
            resolved_refs=resolved_refs,
            instruction_artifacts=instruction_artifacts,
        )
