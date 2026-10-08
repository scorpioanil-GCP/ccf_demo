"""The workflow execution state record — defined next to its machine.

SDK-defined (CLAUDE.md §8.1; D-IMPL-18/27). Two placement rulings meet in
this module, and both are written down here because 07-06 resolves them in
writing (Open Question 2):

**Why /runtime, not /src.** The workflow *contracts* — the definition
wrapper and the factory — are synchronous ``/src`` library surface (07-04).
The *engine* is a running state machine and therefore runtime host code
(D-14; D-IMPL-04's library-and-runtime split), and the Control Plane state
seam's doctrine is that "a consumer that needs a typed record defines it
next to the machine that transitions it"
(:mod:`ccf.controlplane.state`). The machine is in ``/runtime``, so the
record is too.

**The D-IMPL-18/27 mutability split.** The record here is *live suspended
state*: mutable until terminal, keyed ``(tenant, execution_id)``, held on
the native :class:`~ccf.controlplane.state.ControlPlaneStateStore` and never
on the ArtifactStore (D-IMPL-27). What routes to the ArtifactStore is the
immutable, replay-relevant *trace* — written through at each suspend and at
terminal (D-IMPL-18) as content-addressed canonical bytes. Confusing the
two is the mutability rule failing.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

__ccf_mode__ = "algorithmic"

__all__ = [
    "TRACE_ENTRY_KINDS",
    "WORKFLOW_STATE",
    "WORKFLOW_STATUSES",
    "TraceEntry",
    "WorkflowStateRecord",
    "suspension_left_by",
]

#: The workflow-state record class on the Control Plane state seam
#: (D-IMPL-18/27). A namespace partition owned by this machine, exactly as
#: ``GRANT_STATE`` is the grant machine's alone.
WORKFLOW_STATE = "ccf.workflow-state"

#: The transition kinds the engine records. Mechanism identifiers, not
#: domain values: each names a category of state-machine event the engine
#: itself performs, exactly as ``TASK_STEP_KINDS`` names the step
#: vocabulary. Which transitions actually occur is the artifact's statement.
TRACE_ENTRY_KINDS: frozenset[str] = frozenset(
    {"transition", "suspend", "resume", "exception"}
)

#: The execution statuses the machine moves through. Mechanism identifiers
#: in the same doctrine: ``running`` between nodes, ``suspended`` on a
#: hitl-gate, ``exception-routed`` when an exception path handed the state
#: to its ref'd handler (D-13), ``terminal`` once a declared terminal state
#: — or the reserved D-IMPL-61 ``failed`` terminal — is reached.
WORKFLOW_STATUSES: frozenset[str] = frozenset(
    {"running", "suspended", "exception-routed", "terminal"}
)


class TraceEntry(CCFContract):
    """One recorded state transition in an execution's trace (CLAUDE.md §8.1).

    SDK-defined. Frozen and canonically serializable, so the trace the
    engine serializes for replay dimension 5 is byte-stable: the same
    execution serializes to the same block, and the block is recorded
    verbatim (07-05).

    Attributes:
        sequence: Position in this execution's trace, from zero. Ordering is
            the entry's own claim, never inferred from timestamps.
        source: The state the machine left.
        target: The state — or, for an exception routed to a handler, the
            pinned handler ref (D-13) — the machine moved to.
        kind: Which category of event this was (:data:`TRACE_ENTRY_KINDS`).
        occurred_at: Timestamp from the engine's injected clock.
    """

    sequence: int
    source: str
    target: str
    kind: str
    occurred_at: datetime

    @field_validator("kind")
    @classmethod
    def _kind_is_known(cls, value: str) -> str:
        if value not in TRACE_ENTRY_KINDS:
            raise ValueError(
                f"unknown trace entry kind {value!r}; the engine records"
                f" {sorted(TRACE_ENTRY_KINDS)} (CLAUDE.md §8.1)"
            )
        return value


class WorkflowStateRecord(CCFContract):
    """One execution's live state on the Control Plane seam (D-IMPL-18/27).

    SDK-defined. The typed, opaque record the engine writes through the
    audited surface and validates on read (isinstance, foreign-record typed
    error) — the ``GrantStateRecord`` discipline applied to workflows. Keyed
    ``(tenant, execution_id)`` so two tenants running the same workflow
    definition concurrently never collide (D-23).

    Attributes:
        tenant: Owning tenant of this execution.
        execution_id: Caller-supplied execution identity within the tenant.
        current_state: The node the machine is at.
        status: Where the machine is in its lifecycle
            (:data:`WORKFLOW_STATUSES`).
        trace: Every transition recorded so far, in order.
        workflow_definition_uri: The pinned versioned URI of the workflow
            definition this execution runs (D-IMPL-26).
        started_by: The principal that started the execution (SEC-006;
            `D-IMPL-366` G1 (a)); ``None`` on a pre-change record.
        workflow_definition_hash: The content hash of that definition —
            what actually binds the execution to it. The URI alone does
            not: it is built from the artifact's OWN declared tenant, name
            and artifact_version, so a second definition registered under a
            different Control Plane key carries an identical URI while
            declaring different routing. Resume compares this, so an
            execution never continues under a definition it was not started
            with — the thing the URI check already claimed and could not
            deliver (SEC-001, security review 2026-09-23).
    """

    tenant: str
    execution_id: str
    current_state: str
    status: str
    trace: tuple[TraceEntry, ...]
    workflow_definition_uri: str
    workflow_definition_hash: str
    #: The STARTER — the ``Execute`` capability's principal, stamped once in
    #: ``WorkflowEngine.execute`` and carried unchanged through every later
    #: record of the execution (SEC-006; `D-IMPL-366` G1 (a)). The engine
    #: copies it onto every gate event as ``requested_by`` and judges approver
    #: eligibility against it at resumption, so the requester of a second gate
    #: is still the starter, not the ``Resume`` holder who reached it.
    #: Hash-transparent at ``None`` (CINV-06; D-IMPL-243): a record persisted
    #: before this field existed rehydrates unchanged — and, under a bound
    #: plane, such an in-flight suspension REFUSES at resolution (G5 (a),
    #: fail-closed; see the migration note).
    started_by: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @field_validator("status")
    @classmethod
    def _status_is_known(cls, value: str) -> str:
        if value not in WORKFLOW_STATUSES:
            raise ValueError(
                f"unknown workflow status {value!r}; the machine moves"
                f" through {sorted(WORKFLOW_STATUSES)} (CLAUDE.md §8.1;"
                " D-IMPL-18)"
            )
        return value


def suspension_left_by(record: WorkflowStateRecord) -> WorkflowStateRecord | None:
    """The suspension a ``running`` record's passage past a gate left, rebuilt exactly.

    SDK-defined (``D-IMPL-378``; Dave's D2 ruling of 2026-10-07). A resumption
    commits its passage past a gate as the record ``running`` at its decision,
    carrying the suspension's trace plus one ``resume`` entry out of the gate
    (``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume``). So the
    suspension it left is that record with the gate as its state, ``suspended``
    as its status and the trace without its last entry, every other field
    unchanged: the very record whose content hash the gate's closure
    (``src/ccf/hitl/transport.py::HITLTransportProtocol.close_gate``) and every
    verdict on that suspension name. A finisher, or the erasure door, finds an
    interrupted passage's durable claim through it, without asking which engine
    wrote the record.

    Returns ``None`` when ``record`` is not ``running`` or its last trace entry
    is not a ``resume`` into its current state: no passage past a gate left it.
    """
    if record.status != "running" or not record.trace:
        return None
    last = record.trace[-1]
    if last.kind != "resume" or last.target != record.current_state:
        return None
    return WorkflowStateRecord(
        tenant=record.tenant,
        execution_id=record.execution_id,
        current_state=last.source,
        status="suspended",
        trace=record.trace[:-1],
        workflow_definition_uri=record.workflow_definition_uri,
        workflow_definition_hash=record.workflow_definition_hash,
        started_by=record.started_by,
    )
