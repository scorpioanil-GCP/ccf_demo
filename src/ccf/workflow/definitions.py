"""The WorkflowDefinition wrapper artifact (CLAUDE.md §8.1 — SDK-defined).

A workflow is a Control Plane artifact that **wraps a pinned TaskDefinition
ref and adds ONLY routing**: explicit state-machine transitions over the
task's step names, terminal conditions, per-node exception refs (D-13), and
per-gate approval-policy bindings keyed by step name (D-12). It never
carries steps inline — the steps belong to the referenced
:class:`~ccf.agents.definitions.TaskDefinition`, whose contract this module
leaves byte-identical (D-12). Consistent with the No-Hardcoding Rule
(§6.4), workflow definitions are data interpreted by mechanism; no routing
value exists in this module.

**Validation is split by what each layer can see.** The validators here
check ONLY what the wrapper can decide locally: URI pinning (D-IMPL-26),
internal transition-graph consistency (every transition endpoint is a
declared node), terminal declaration, terminal reachability and
no-unreachable-node checks over the declared graph, gate-policy and
exception-ref keys within the declared names, and the locally-decidable
D-IMPL-61 semantics. The checks that require the *resolved* TaskDefinition
— step-name existence in the referenced artifact, gate bindings targeting
hitl-gate-kind steps, exception-ref resolvability — are deliberately NOT
here: they are the ``WorkflowFactory``'s registry-backed semantic layer
(:mod:`ccf.workflow.factory`), because a Pydantic validator cannot see the
artifact a ref names.

**Absent exception ref = propagate-to-terminal (D-IMPL-61, option-a).** A
node that declares no per-node exception ref does not fail validation:
absence is a *defined, explicit, audited* transition — when the node's
exception path fires and no ref is bound, the workflow transitions to the
reserved terminal :data:`WORKFLOW_FAILED_STATE`, recorded in the trace as a
first-class state transition (CLAUDE.md §8.1). The schema therefore
declares ``failed`` as a defined transition target on every workflow
(:attr:`WorkflowDefinition.effective_terminal_states`), keeps it terminal
by construction (never a source), and keeps "let it fail" expressible.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, field_validator, model_validator

from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver
from ccf.hitl.approval_gate import GATE_ACTIONS

__ccf_mode__ = "algorithmic"

__all__ = [
    "WORKFLOW_DEFINITION",
    "WORKFLOW_FAILED_STATE",
    "WorkflowDefinition",
    "WorkflowTransition",
]

#: The reserved terminal state every workflow declares (D-IMPL-61). A
#: mechanism identifier, not a domain value: it names the propagate-to-
#: terminal destination the ruling defines for a node with no exception ref,
#: exactly as TASK_STEP_KINDS names the step vocabulary.
WORKFLOW_FAILED_STATE = "failed"


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


class WorkflowTransition(CCFContract):
    """One explicit state transition over declared node names (CLAUDE.md §8.1).

    SDK-defined. Workflows are state machines with explicit states,
    transitions, and terminal conditions; a transition is data the engine
    interprets, never behavior.
    """

    source: str
    target: str


class _TwoLaneVersioned(CCFContract):
    """Shared D-IMPL-28 surface: schema lane + author-bumped artifact version.

    The same two-statement discipline as the definition artifacts in
    :mod:`ccf.agents.definitions` (which this module deliberately does not
    import from — that module's private base stays private and its contracts
    stay byte-identical, D-12): ``schema_version`` is the artifact class's
    lane, ``artifact_version`` the author's content statement, held to that
    statement by the Control Plane's D-05 hash-verified bump check.
    """

    schema_version: str
    artifact_version: str

    @field_validator("schema_version", "artifact_version")
    @classmethod
    def _versions_are_semver(cls, value: str) -> str:
        return validate_semver(value)


class WorkflowDefinition(_TwoLaneVersioned):
    """A declared, versioned workflow — a routing wrapper, never steps (D-12).

    SDK-defined (CLAUDE.md §8.1; D-IMPL-17/28). The artifact the
    ``WorkflowFactory`` interprets; nothing here is executable. The wrapper
    adds ONLY transitions, terminal conditions, per-node exception refs, and
    per-gate approval-policy bindings — the wrapped steps live in the
    referenced TaskDefinition at a pinned version (D-IMPL-26).

    The semantic checks this contract cannot perform locally — that every
    declared node names a step in the *resolved* TaskDefinition, that every
    ``gate_policies`` key names a ``hitl-gate``-kind step, and that every
    exception ref resolves in the registry — are the ``WorkflowFactory``'s
    obligations (:mod:`ccf.workflow.factory`).
    """

    name: str
    tenant: str
    task_definition_ref: str
    start: str
    transitions: tuple[WorkflowTransition, ...]
    terminal_states: tuple[str, ...]
    exception_refs: Mapping[str, str] = {}
    gate_policies: Mapping[str, str] = {}
    #: Per-gate verdict→target routing (D-IMPL-357 A1): which declared
    #: transition target each GATE_ACTIONS verdict may take from that gate.
    #: A GENERATION BOUNDARY (D-IMPL-351(a); D-IMPL-243 amendment 1): a
    #: document lacking it is of an earlier generation, and the factory
    #: refuses a routed gate that declares no complete map. Routing values,
    #: never code (CINV-01): the SDK supplies only the verdict vocabulary.
    #: Whether a declared key names a ``hitl-gate``-kind step is, like
    #: ``gate_policies``, the ``WorkflowFactory``'s semantic check against
    #: the resolved TaskDefinition — not this contract's, which cannot see
    #: step kinds at all.
    gate_routes: Mapping[str, Mapping[str, str]] = Field(
        default={}, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )

    @field_validator("task_definition_ref")
    @classmethod
    def _task_ref_is_a_pinned_artifact_uri(cls, value: str) -> str:
        return _validate_artifact_ref(value)

    @field_validator("exception_refs", "gate_policies")
    @classmethod
    def _bound_refs_are_pinned_artifact_uris(
        cls, value: Mapping[str, str]
    ) -> Mapping[str, str]:
        for uri in value.values():
            _validate_artifact_ref(uri)
        return value

    @property
    def effective_terminal_states(self) -> frozenset[str]:
        """The declared terminals plus the reserved ``failed`` state.

        ``failed`` is a defined transition target on every workflow whether
        or not the author lists it (D-IMPL-61): the propagate-to-terminal
        transition must have a destination the schema itself declares, or
        an absent exception ref would be an unrecorded fall-through rather
        than a positive, replayable event in the trace.
        """
        return frozenset(self.terminal_states) | {WORKFLOW_FAILED_STATE}

    def _declared_nodes(self) -> frozenset[str]:
        """Every node name the wrapper's own graph declares."""
        return (
            frozenset({self.start})
            | {t.source for t in self.transitions}
            | {t.target for t in self.transitions}
            | self.effective_terminal_states
        )

    @model_validator(mode="after")
    def _terminals_are_declared_and_terminal(self) -> "WorkflowDefinition":
        if not self.terminal_states:
            raise ValueError(
                "a workflow must declare at least one terminal state:"
                " workflows are state machines with explicit terminal"
                " conditions, and a machine that cannot end describes no"
                " decision (CLAUDE.md §8.1; D-11)"
            )
        sources = {t.source for t in self.transitions}
        outgoing = sorted(self.effective_terminal_states & sources)
        if outgoing:
            raise ValueError(
                f"terminal state(s) {outgoing!r} carry outgoing transitions;"
                " a terminal state is a terminal condition, and the reserved"
                f" {WORKFLOW_FAILED_STATE!r} state is terminal by the"
                " D-IMPL-61 ruling (CLAUDE.md §8.1)"
            )
        return self

    @model_validator(mode="after")
    def _graph_is_internally_consistent(self) -> "WorkflowDefinition":
        sources = {t.source for t in self.transitions}
        declared = sources | {self.start} | self.effective_terminal_states
        undeclared = sorted(
            {t.target for t in self.transitions} - declared
        )
        if undeclared:
            raise ValueError(
                f"transition target(s) {undeclared!r} appear nowhere in the"
                " wrapper's declared transition graph: a target must be a"
                " transition source, the start node, or a terminal state"
                " (CLAUDE.md §8.1; D-11)"
            )
        if self.start not in sources | self.effective_terminal_states:
            raise ValueError(
                f"start node {self.start!r} appears nowhere in the wrapper's"
                " declared transition graph (CLAUDE.md §8.1; D-11)"
            )
        return self

    @model_validator(mode="after")
    def _every_node_is_reachable_and_can_terminate(
        self,
    ) -> "WorkflowDefinition":
        edges: dict[str, set[str]] = {}
        for transition in self.transitions:
            edges.setdefault(transition.source, set()).add(transition.target)

        reachable = {self.start}
        frontier = [self.start]
        while frontier:
            node = frontier.pop()
            for target in edges.get(node, ()):
                if target not in reachable:
                    reachable.add(target)
                    frontier.append(target)
        unreachable = sorted(
            (set(edges) | {self.start}) - reachable
        )
        if unreachable:
            raise ValueError(
                f"node(s) {unreachable!r} are unreachable: never a transition"
                " target and not the start node, so no execution path exists"
                " to them (CLAUDE.md §8.1; D-11)"
            )

        # Terminal reachability over the wrapper's own graph. The implicit
        # D-IMPL-61 transition to `failed` is an *exception* path, never the
        # nominal path, so it does not rescue a nominal dead-end here.
        can_terminate: set[str] = set(self.effective_terminal_states)
        changed = True
        while changed:
            changed = False
            for source, targets in edges.items():
                if source not in can_terminate and targets & can_terminate:
                    can_terminate.add(source)
                    changed = True
        stuck = sorted(reachable - can_terminate)
        if stuck:
            raise ValueError(
                f"no terminal state is reachable from node(s) {stuck!r}"
                " through the declared transitions; a workflow's nominal"
                " path must be able to reach a terminal condition"
                " (CLAUDE.md §8.1; D-11)"
            )
        return self

    @model_validator(mode="after")
    def _bindings_key_declared_nonterminal_nodes(
        self,
    ) -> "WorkflowDefinition":
        declared = self._declared_nodes()
        routable = declared - self.effective_terminal_states
        stray_exceptions = sorted(set(self.exception_refs) - routable)
        if stray_exceptions:
            raise ValueError(
                f"exception ref key(s) {stray_exceptions!r} name no"
                " non-terminal node in the wrapper's declared transition"
                " graph; exception refs are per-node (D-13), and a node the"
                " graph never reaches has no exception path to bind"
                " (D-IMPL-61; CLAUDE.md §8.1)"
            )
        stray_gates = sorted(set(self.gate_policies) - declared)
        if stray_gates:
            raise ValueError(
                f"gate policy key(s) {stray_gates!r} appear nowhere in the"
                " wrapper's declared transition graph (D-12; CLAUDE.md"
                " §8.1). Whether a declared name is a hitl-gate-kind step is"
                " the WorkflowFactory's semantic check against the resolved"
                " TaskDefinition"
            )
        return self

    @model_validator(mode="after")
    def _routes_map_verdicts_onto_declared_targets(self) -> "WorkflowDefinition":
        declared = self._declared_nodes()
        routable = declared - self.effective_terminal_states
        outgoing: dict[str, set[str]] = {}
        for transition in self.transitions:
            outgoing.setdefault(transition.source, set()).add(transition.target)
        stray = sorted(set(self.gate_routes) - routable)
        if stray:
            raise ValueError(
                f"gate route key(s) {stray!r} name no non-terminal node in"
                " the wrapper's declared transition graph; a route is keyed"
                " by a gate, and a terminal state declares no outgoing route"
                " (D-IMPL-357 A1; CLAUDE.md §8.1)"
            )
        for gate, routes in sorted(self.gate_routes.items()):
            unknown = sorted(set(routes) - GATE_ACTIONS)
            if unknown:
                raise ValueError(
                    f"gate {gate!r} routes verdict(s) {unknown!r}, which are"
                    f" not in GATE_ACTIONS {sorted(GATE_ACTIONS)}; a route is"
                    " keyed by the gate's own verdict vocabulary (D-IMPL-357 A1)"
                )
            for verdict, target in sorted(routes.items()):
                if target not in outgoing.get(gate, set()):
                    raise ValueError(
                        f"gate {gate!r} routes verdict {verdict!r} to"
                        f" {target!r}, which is not a declared transition"
                        f" target from {gate!r}; a route names one of the"
                        " gate's own declared targets (D-IMPL-357 A1)"
                    )
            targets = list(routes.values())
            if len(set(targets)) != len(targets):
                duplicated = sorted(
                    {target for target in targets if targets.count(target) > 1}
                )
                raise ValueError(
                    f"gate {gate!r} routes more than one verdict to target(s)"
                    f" {duplicated!r}; two verdicts from one gate must not"
                    " lead to the same target, or a recorded rejection could"
                    " resolve identically to an approval (D-IMPL-357 A1)"
                )
        return self


#: The workflow-definition artifact class (CLAUDE.md §8.1; D-IMPL-17/28).
WORKFLOW_DEFINITION = ArtifactClass(
    class_id="ccf.workflow-definition", contract=WorkflowDefinition
)
