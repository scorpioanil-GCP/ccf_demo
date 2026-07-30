"""The Workflow Factory (ORCH-01; CLAUDE.md §6.4/§8.1 — SDK-defined).

**ORCH-01's "via the Task Factory" is literal, extended one level.** The
factory is the only construction path to an executable workflow handle: it
resolves a registered ``ccf.workflow-definition`` **and** its wrapped
TaskDefinition through Control Plane resolution only — never raw storage
(DESIGN.md §3.5) — runs the registry-backed semantic validation the wrapper
contract could not perform locally, and returns a typed, frozen handle that
is the ONLY thing the workflow engine (07-06) will accept. Nothing
constructed here can execute: no ``execute``, ``run``, ``step``, ``loop``,
``plan``, or ``resume`` — TaskFactory's "nothing constructed here can
execute" doctrine, now one level up (D-11; D-IMPL-17). The single
legitimate ``Workflow(...)`` call site is this module, enforced by the
CINV-01c factory-bypass lint (D-12: lint is the mechanism of record).

**Semantic validation lives where the data lives.** The wrapper's
syntactic validators (:mod:`ccf.workflow.definitions`) checked what the
wrapper can see; this module checks what only the resolved artifacts can
answer: every declared non-terminal node names a step in the resolved
TaskDefinition (D-12); every ``gate_policies`` key names a
``hitl-gate``-kind step; every exception ref and gate-policy ref resolves
in the registry at its pinned version (D-13; D-IMPL-26). The D-IMPL-61
propagate-to-terminal semantics need nothing resolved — absence is defined
locally — so nothing about them is re-checked here.

The audit scope is D-22's: refusals here are typed construction errors
(broken definitions, the I.1 refusal-vs-exception line as the agent seam
draws it), and replay capture belongs to the engine that executes, not the
factory that constructs.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.agents.definitions import TASK_DEFINITION, TaskDefinition
from ccf.artifacts.protocol import artifact_uri, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.resolution import ControlPlaneResolution, resolve_pinned
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition

__ccf_mode__ = "algorithmic"

__all__ = [
    "Workflow",
    "WorkflowConstructionError",
    "WorkflowFactory",
    "WorkflowIdentity",
]


class WorkflowConstructionError(ValueError):
    """A workflow definition the factory cannot construct a handle from.

    Broken wiring between the wrapper and its resolved artifacts — a typed
    exception, not a returned refusal, on the I.1 line: a wrapper that
    names steps its task does not declare is a broken definition, never an
    expected artifact outcome.
    """


def _resolve(control_plane: ControlPlaneResolution, uri: str, *, ruling: str) -> object:
    """Resolve one pinned reference, or refuse citing ``ruling``.

    Delegates to the shared :func:`~ccf.controlplane.resolution.resolve_pinned`
    (IN-01 — one implementation of the pinned-resolution rule) and supplies
    the factory's reading of a miss: a reference the factory cannot follow
    is a broken definition (DESIGN.md §3.5).
    """
    artifact = resolve_pinned(control_plane, uri)
    if artifact is None:
        name = parse_artifact_uri(uri)
        key = f"{name.tenant_id}/{name.artifact_class}/{name.name}"
        raise WorkflowConstructionError(
            f"reference {uri!r} resolves to nothing the Control Plane has"
            f" registered under {key!r} ({ruling}); the factory reads"
            " through Control Plane resolution at pinned versions only"
            " (DESIGN.md §3.5)"
        )
    return artifact


class WorkflowIdentity(CCFContract):
    """A constructed workflow's provenance block (D-IMPL-26).

    The derived-at-construction discipline of ``TaskIdentity``, doubled:
    content hash + versioned URI for the wrapper, and for the resolved
    TaskDefinition it wrapped — so replay can answer "which routing, over
    which steps" from the handle alone.
    """

    definition_hash: str
    definition_uri: str
    task_definition_hash: str
    task_definition_uri: str


class Workflow:
    """One factory-built workflow handle — resolved pair + provenance, frozen.

    SDK-defined (CLAUDE.md §8.1; ORCH-01; D-IMPL-17). The only thing the
    workflow engine (07-06) accepts. **There is no execution surface here**:
    execution semantics are the engine's scope, exactly as ``Task`` defers
    them (D-11). Construct through :class:`WorkflowFactory` only (§6.4);
    the CINV-01c lint holds the codebase to it (D-12).

    Args:
        definition: The semantically validated workflow wrapper.
        task_definition: The resolved TaskDefinition the wrapper pins.
        identity: The construction-time provenance block; must describe
            both artifacts, or construction is refused.

    Raises:
        WorkflowConstructionError: the identity block does not describe the
            supplied artifacts (content identity is workflow identity,
            D-IMPL-26).
    """

    def __init__(
        self,
        *,
        definition: WorkflowDefinition,
        task_definition: TaskDefinition,
        identity: WorkflowIdentity,
    ) -> None:
        expected = content_hash(definition)
        if identity.definition_hash != expected:
            raise WorkflowConstructionError(
                "identity.definition_hash does not equal the content hash of"
                f" the workflow definition ({identity.definition_hash!r} !="
                f" {expected!r}); workflow identity is content identity"
                " (D-IMPL-26)"
            )
        expected_task = content_hash(task_definition)
        if identity.task_definition_hash != expected_task:
            raise WorkflowConstructionError(
                "identity.task_definition_hash does not equal the content"
                " hash of the resolved task definition"
                f" ({identity.task_definition_hash!r} != {expected_task!r});"
                " a handle whose provenance does not describe its artifacts"
                " replays a decision that never happened (D-IMPL-26)"
            )
        self._definition = definition
        self._task_definition = task_definition
        self._identity = identity

    @property
    def definition(self) -> WorkflowDefinition:
        """The semantically validated workflow wrapper."""
        return self._definition

    @property
    def task_definition(self) -> TaskDefinition:
        """The resolved TaskDefinition the wrapper pins (D-12)."""
        return self._task_definition

    @property
    def identity(self) -> WorkflowIdentity:
        """The construction-time provenance block (D-IMPL-26)."""
        return self._identity


class WorkflowFactory:
    """Constructs workflow handles from definition artifacts — the only path.

    CLAUDE.md §6.4/§8.1; ORCH-01; D-IMPL-17; D-IMPL-28. Follows the
    TaskFactory discipline: keyword-only constructor injection of the
    resolution surface, no I/O beyond registry resolution, and nothing
    constructed here executes. The single legitimate ``Workflow(...)`` call
    site is this module, enforced by the CINV-01c factory-bypass lint
    (D-12).

    Args:
        control_plane: The injected resolution surface (constructor
            injection, never ambient lookup), as for the Agent & Task
            factories.
    """

    def __init__(self, *, control_plane: ControlPlaneResolution) -> None:
        self._control_plane = control_plane

    def construct(
        self, *, definition_key: str, definition_version: str
    ) -> Workflow:
        """Resolve, semantically validate, and return one workflow handle.

        Steps in order: (1) resolve the wrapper at its pinned version and
        hold it to ``ccf.workflow-definition``; (2) resolve the wrapped
        TaskDefinition through the same surface and hold its Control Plane
        binding to ``ccf.task-definition``; (3) run the registry-backed
        semantic layer — declared-node/step-name agreement (D-12),
        gate-policy step-kind agreement, exception-ref and gate-policy-ref
        resolvability (D-13). Only then is the provenance block computed
        and the ``Workflow`` instantiated.

        Raises:
            WorkflowConstructionError: a semantic check fails, or a
                reference resolves to nothing.
            TypeError: a resolved artifact does not satisfy its declared
                artifact class.
            ControlPlaneMissing: no definition is registered as
                ``(definition_key, definition_version)``.
        """
        resolved = self._control_plane.resolve(definition_key, definition_version)
        definition = WORKFLOW_DEFINITION.validate(resolved)
        assert isinstance(definition, WorkflowDefinition)

        task_ref = definition.task_definition_ref
        task_name = parse_artifact_uri(task_ref)
        task_key = (
            f"{task_name.tenant_id}/{task_name.artifact_class}/"
            f"{task_name.name}"
        )
        bound_class = self._control_plane.artifact_class_of(task_key)
        if bound_class != TASK_DEFINITION.class_id:
            raise WorkflowConstructionError(
                f"task_definition_ref {task_ref!r} names a key the Control"
                f" Plane binds to artifact class {bound_class!r}, not"
                f" {TASK_DEFINITION.class_id!r}; a workflow wraps a task"
                " definition and nothing else (D-12; CLAUDE.md §8.1)"
            )
        task = TASK_DEFINITION.validate(
            _resolve(self._control_plane, task_ref, ruling="D-12")
        )
        assert isinstance(task, TaskDefinition)

        step_kinds = {step.name: step.kind for step in task.steps}

        # D-12 — every declared non-terminal node is a step of the RESOLVED
        # task; the wrapper's own validators could not see the task.
        routable = sorted(
            (
                {definition.start}
                | {t.source for t in definition.transitions}
                | {t.target for t in definition.transitions}
            )
            - definition.effective_terminal_states
        )
        phantom = [name for name in routable if name not in step_kinds]
        if phantom:
            raise WorkflowConstructionError(
                f"workflow node(s) {phantom!r} name no step in the resolved"
                f" task definition {task_ref!r} (steps:"
                f" {sorted(step_kinds)}); the wrapper routes over the"
                " wrapped task's own step names, never steps of its own"
                " (D-12; CLAUDE.md §8.1)"
            )

        # Gate bindings target hitl-gate-kind steps — the kind lives in the
        # resolved task, so the check lives here.
        for gate_name, policy_ref in sorted(definition.gate_policies.items()):
            kind = step_kinds.get(gate_name)
            if kind != "hitl-gate":
                raise WorkflowConstructionError(
                    f"gate policy on step {gate_name!r}, whose kind in the"
                    f" resolved task definition is {kind!r}, not 'hitl-gate';"
                    " approval policies bind to gates exclusively (D-12;"
                    " CLAUDE.md §8.1/§8.2)"
                )
            self._resolve_bound_ref(policy_ref, ruling="D-12")

        # Exception refs resolve at their pinned versions (D-13).
        for _node, exception_ref in sorted(definition.exception_refs.items()):
            self._resolve_bound_ref(exception_ref, ruling="D-13")

        identity = WorkflowIdentity(
            definition_hash=content_hash(definition),
            definition_uri=artifact_uri(
                tenant_id=definition.tenant,
                artifact_class=WORKFLOW_DEFINITION.class_id,
                name=definition.name,
                artifact_version=definition.artifact_version,
            ),
            task_definition_hash=content_hash(task),
            task_definition_uri=task_ref,
        )
        return Workflow(
            definition=definition, task_definition=task, identity=identity
        )

    def _resolve_bound_ref(self, uri: str, *, ruling: str) -> object:
        """Resolve one wrapper-bound reference via :func:`_resolve`."""
        return _resolve(self._control_plane, uri, ruling=ruling)
