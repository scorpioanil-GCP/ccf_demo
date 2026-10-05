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
TaskDefinition (D-12); every ``gate_policies`` **and** ``gate_routes`` key
names a ``hitl-gate``-kind step; every ``hitl-gate``-kind step reachable in
the wrapper's graph routes every ``GATE_ACTIONS`` verdict to a target
(D-IMPL-357 A2 — the wrapper's local validators can restrict a route's key
to a declared node and its target to a declared edge, but only the resolved
task tells this module which nodes are gates at all, and whether the map is
complete); **no ``hitl-gate``-kind step is a declared terminal state** (A2
review round 1, item 7 — a gate named terminal escapes the completeness
population, which subtracts terminal states, and becomes a silent completion
in one position and an unresumable suspension in the other; a gate is a place
a human acts, never a terminal condition); every exception ref and
gate-policy ref resolves in the registry
at its pinned version (D-13; D-IMPL-26). The D-IMPL-61 propagate-to-terminal
semantics need nothing resolved — absence is defined locally — so nothing
about them is re-checked here.

The audit scope is D-22's: refusals here are typed construction errors
(broken definitions, the I.1 refusal-vs-exception line as the agent seam
draws it), and replay capture belongs to the engine that executes, not the
factory that constructs.

**The definition key is the capability's resource, and the tenant is checked
here, once (D-IMPL-353 §1.2/§1.3).** ``construct`` takes an
:class:`~ccf.authz.capability.Authorized` for ``Execute`` or
``Resume`` — the two door-declared actions whose resource is a workflow
definition key — and resolves the key the capability was minted for; there
is no ``definition_key`` parameter, so a caller cannot name one the
authorizer did not decide on. The artifact's declared ``tenant`` is compared
with ``authorized.tenant`` exactly once, at construction, and a mismatch is a
typed refusal (:class:`WorkflowTenantMismatchError`) before any handle — and
therefore any state — exists. After construction nothing consults
``workflow.definition.tenant`` for authority: the engine files under the
capability's tenant and nothing else. This is what makes a cross-tenant
invocation *inexpressible* rather than refused downstream (§2 P2).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.agents.definitions import TASK_DEFINITION, TaskDefinition
from ccf.artifacts.protocol import artifact_uri, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.resolution import ControlPlaneResolution, resolve_pinned
from ccf.hitl.approval_gate import GATE_ACTIONS
from ccf.hitl.approval_policy import APPROVAL_POLICY
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.authz.capability import (
    ActionKind,
    Authorized,
    Execute,
    Resume,
    verify,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "Workflow",
    "WorkflowConstructionError",
    "WorkflowFactory",
    "WorkflowIdentity",
    "WorkflowTenantMismatchError",
]


class WorkflowConstructionError(ValueError):
    """A workflow definition the factory cannot construct a handle from.

    Broken wiring between the wrapper and its resolved artifacts — a typed
    exception, not a returned refusal, on the I.1 line: a wrapper that
    names steps its task does not declare is a broken definition, never an
    expected artifact outcome.
    """


class WorkflowTenantMismatchError(WorkflowConstructionError):
    """The capability's tenant is not the tenant the definition declares.

    D-IMPL-353 §1.3 — the ONE tenant comparison in the workflow surface,
    made at construction. A capability for tenant B minted on a key whose
    artifact declares tenant A constructs nothing: no handle, so no
    execution, so no state and no HITL event can ever exist under A on B's
    authority (§2 P2). Raised before any handle exists; the message names
    both tenants and the key so the refusal is answerable from the text.
    """


def _verify_run_capability(
    authorized: Authorized[Execute] | Authorized[Resume],
) -> None:
    """Refuse unless ``authorized`` is a genuine ``Execute`` or ``Resume``.

    :func:`~ccf.authz.capability.verify` takes exactly one kind; the
    factory accepts the two whose doors reach it. The *current* ``kind``
    attribute selects which check runs and is then held to the mint by
    ``verify`` itself, so a capability whose ``kind`` was reassigned dies
    inside ``verify`` (§1.5g) rather than steering this selection anywhere.
    The resource passed is the capability's own: the key IS the resource
    (§1.2), so this axis is the retarget check and nothing more.
    """
    kind: type[ActionKind] = (
        Execute if getattr(authorized, "kind", None) is Execute else Resume
    )
    verify(
        authorized,
        kind=kind,
        resource=str(getattr(authorized, "resource", "")),
    )


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
        definition_key: The Control Plane key the handle was resolved from
            — the capability's resource (D-IMPL-353 §1.2). The engine binds
            the capability it is handed to this key, so a handle built for
            definition X cannot be run under a capability minted for Y
            (§1.5f).

    Raises:
        WorkflowConstructionError: the identity block does not describe the
            supplied artifacts (content identity is workflow identity,
            D-IMPL-26), or ``definition_key`` is empty.
    """

    def __init__(
        self,
        *,
        definition: WorkflowDefinition,
        task_definition: TaskDefinition,
        identity: WorkflowIdentity,
        definition_key: str,
    ) -> None:
        if not definition_key:
            raise WorkflowConstructionError(
                "a workflow handle carries the Control Plane key it was"
                " resolved from, and the empty string names no key; the key"
                " is the capability's resource (D-IMPL-353 §1.2)"
            )
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
        self._definition_key = definition_key

    @property
    def definition(self) -> WorkflowDefinition:
        """The semantically validated workflow wrapper."""
        return self._definition

    @property
    def definition_key(self) -> str:
        """The Control Plane key this handle was resolved from (§1.2)."""
        return self._definition_key

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
        self,
        authorized: Authorized[Execute] | Authorized[Resume],
        *,
        definition_version: str,
    ) -> Workflow:
        """Resolve, semantically validate, and return one workflow handle.

        The definition key is ``authorized.resource`` — the key the
        authorizer decided on — and there is no parameter to supply another
        (D-IMPL-353 §1.2). Steps in order: (0) verify the capability is a
        genuine, unretargeted ``Execute`` or ``Resume`` (§1.5); (1) resolve
        the wrapper at its pinned version and hold it to
        ``ccf.workflow-definition``; (2) **the one tenant comparison** —
        refuse unless the artifact declares ``authorized.tenant`` (§1.3);
        (3) resolve the wrapped TaskDefinition through the same surface and
        hold its Control Plane binding to ``ccf.task-definition``; (4) run
        the registry-backed semantic layer — declared-node/step-name
        agreement (D-12), gate-policy step-kind agreement, exception-ref and
        gate-policy-ref resolvability (D-13). Only then is the provenance
        block computed and the ``Workflow`` instantiated, carrying the key.

        Raises:
            CapabilityBypassError: ``authorized`` is fabricated, retargeted,
                or of a kind other than ``Execute``/``Resume``.
            WorkflowTenantMismatchError: the artifact under the key declares
                a tenant other than ``authorized.tenant``.
            WorkflowConstructionError: a semantic check fails, or a
                reference resolves to nothing.
            TypeError: a resolved artifact does not satisfy its declared
                artifact class.
            ControlPlaneMissing: no definition is registered as
                ``(authorized.resource, definition_version)``.
        """
        _verify_run_capability(authorized)
        definition_key = authorized.resource
        resolved = self._control_plane.resolve(definition_key, definition_version)
        definition = WORKFLOW_DEFINITION.validate(resolved)
        assert isinstance(definition, WorkflowDefinition)
        if definition.tenant != authorized.tenant:
            raise WorkflowTenantMismatchError(
                f"the capability is for tenant {authorized.tenant!r} and the"
                f" workflow definition registered under {definition_key!r}"
                f" declares tenant {definition.tenant!r}; a handle is"
                " constructed only under a capability for the tenant the"
                " artifact declares, so no execution can be filed under a"
                " tenant the caller was not authorized for (D-IMPL-353 §1.3)"
            )

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

        # D-IMPL-357 A2 (review round 1, item 7) — A GATE IS A PLACE A HUMAN
        # ACTS; IT IS NEVER A TERMINAL CONDITION. A `hitl-gate`-kind step the
        # wrapper also declares terminal is silently two different no-ops
        # depending on how it is reached, and the completeness check below
        # reaches neither, because `routable` subtracts the terminal states:
        #   * named in `terminal_states` AND reached as a transition target —
        #     the execution completes at the gate's name with no suspension,
        #     no human action and no route map required; the gate is reduced
        #     to a label;
        #   * the same step as the START node — `_advance` suspends on the
        #     step's kind before any terminal test, so the execution suspends
        #     and can never resume, since a terminal state carries no
        #     outgoing transitions.
        # Only the resolved task says which names are gates, so the check
        # lives here, and it refuses both shapes at construction rather than
        # leaving one consumer to paper over them.
        gate_terminals = sorted(
            name
            for name in definition.effective_terminal_states
            if step_kinds.get(name) == "hitl-gate"
        )
        if gate_terminals:
            raise WorkflowConstructionError(
                f"step(s) {gate_terminals!r} are declared terminal states and"
                " their kind in the resolved task definition is 'hitl-gate';"
                " a gate is a place a human acts and is never a terminal"
                " condition, so a gate named as one is either a silent"
                " completion with no human action or a suspension that can"
                " never resume (D-IMPL-357 A2; CLAUDE.md §8.1/§8.2)"
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
            # SEC-006 (D-IMPL-366 §4 (5), RULED): the target of a gate-policy
            # binding is a TYPED ccf.approval-policy, class-checked through the
            # Control Plane's key binding exactly as the task ref is above. A
            # DeclaredArtifact under an adopter class id — every pre-change
            # fixture — is refused by name: an approval policy nothing judges
            # is documentation, not a control.
            policy_name = parse_artifact_uri(policy_ref)
            policy_key = (
                f"{policy_name.tenant_id}/{policy_name.artifact_class}/"
                f"{policy_name.name}"
            )
            policy_class = self._control_plane.artifact_class_of(policy_key)
            if policy_class != APPROVAL_POLICY.class_id:
                raise WorkflowConstructionError(
                    f"gate policy on step {gate_name!r} names {policy_ref!r},"
                    f" a key the Control Plane binds to artifact class"
                    f" {policy_class!r}, not {APPROVAL_POLICY.class_id!r}; a"
                    " gate's approval policy is a typed ccf.approval-policy"
                    " the SDK judges approver eligibility against, registered"
                    " by adopter code against its real contract (SEC-006;"
                    " D-IMPL-366 §4 (5); CLAUDE.md §8.2)"
                )

        # Route bindings target hitl-gate-kind steps too — the same check,
        # symmetric to gate_policies above. Noted at A1's review: the wrapper
        # cannot see step kinds, so nothing previously refused a gate_routes
        # key naming a step that is not a gate (D-IMPL-357 A2).
        for gate_name in sorted(definition.gate_routes):
            kind = step_kinds.get(gate_name)
            if kind != "hitl-gate":
                raise WorkflowConstructionError(
                    f"gate route on step {gate_name!r}, whose kind in the"
                    f" resolved task definition is {kind!r}, not 'hitl-gate';"
                    " verdict routes bind to gates exclusively (D-IMPL-357 A2;"
                    " CLAUDE.md §8.1/§8.2)"
                )

        # D-IMPL-357 A2 — every ROUTED hitl-gate step declares where each
        # verdict goes. Scoped to the nodes the wrapper routes to
        # (`routable`), the same population the phantom check above walks.
        for gate_name in routable:
            if step_kinds.get(gate_name) != "hitl-gate":
                continue
            missing = sorted(GATE_ACTIONS - set(definition.gate_routes.get(gate_name, {})))
            if missing:
                raise WorkflowConstructionError(
                    f"hitl-gate step {gate_name!r} does not route verdict(s)"
                    f" {missing!r}; a routed gate declares a target for every"
                    " GATE_ACTIONS verdict, because an undeclared route is"
                    " the route the engine must refuse, not guess"
                    " (D-IMPL-357 A2; D-IMPL-351(a); CLAUDE.md §6.4)"
                )

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
            definition=definition,
            task_definition=task,
            identity=identity,
            definition_key=definition_key,
        )

    def _resolve_bound_ref(self, uri: str, *, ruling: str) -> object:
        """Resolve one wrapper-bound reference via :func:`_resolve`."""
        return _resolve(self._control_plane, uri, ruling=ruling)
