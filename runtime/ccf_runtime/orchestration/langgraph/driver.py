"""`LangGraphWorkflowDriver` — CCF workflows driven through LangGraph's own topology.

SDK-defined (CLAUDE.md §8.1; D-IMPL-17/60 — the first of the three driver
legs). Implements :class:`~ccf.orchestration.protocol.OrchestrationProtocol`
by authoring a LangGraph ``StateGraph`` over the CCF engine's **public**
surface — ``execute`` and ``resume`` on WorkflowFactory-built handles — and
nothing else. The topology here is this module's own (A7, D-19): nothing is
read from, shared with, or imported out of the harness-adapter tree, and the
``d06-orchestration-split`` lint holds that boundary structurally.

**The CCF engine is authoritative for state and audit (T-07-30).** The
suspended :class:`~ccf_runtime.workflow.state.WorkflowStateRecord` lives on
the Control Plane store, written through the engine's audited write surface;
the execution trace writes through to the ArtifactStore; the typed outcomes
the driver returns are the engine's own, verbatim. LangGraph's checkpointer
(:class:`~langgraph.checkpoint.memory.InMemorySaver`) holds **graph position
only** — which node the topology is parked on and two scalar channels — and
the conformance suite asserts that nothing CCF-typed is in it
(:meth:`LangGraphWorkflowDriver.checkpointed_values` is the introspection
seam it asserts through).

**Suspension surfaces LangGraph-natively.** A CCF hitl-gate suspension maps
onto :func:`langgraph.types.interrupt` at the driver's gate node: the graph
run parks, and the driver returns the engine's typed suspend handle. A
resume maps onto ``Command(resume=decision)``: LangGraph replays the gate
node, ``interrupt`` returns the decision, and the node hands it to the
engine's own ``resume`` — routing stays the workflow artifact's statement
(CINV-01), interpreted by the engine, never by the topology.

Not an algorithmic module: it imports an orchestrator SDK, which is exactly
what the CINV-02 carve-out for ``ccf_runtime.orchestration`` exists to
permit here and nowhere else.

**The capability travels in the closure, not the driver (D-IMPL-353 §1.2).**
``start_execution`` and ``resume_execution`` take the ``Authorized`` for
their own action and close the engine call over it; the graph's node
functions are those closures, built per call. The driver holds no capability
in any field and mints nothing — the engine verifies. Position is keyed by
``authorized.tenant``, the tenant the engine files under (§1.3), and the
introspection seam takes that tenant rather than a handle to read one from.
A run presents ONE capability: the ``drive`` node in a start run, the
post-interrupt half of ``gate`` in a resume run; the node a run did not
present a capability for raises the typed driver error if it is ever
reached, which the topology does not do.

**Loop-safety (WR-03; Phase-9 CONTEXT D-10/D-11).** Outcome lookups raise
the shared typed hierarchy
(:class:`~ccf_runtime.orchestration.common.SegmentNotExecutedError`), never
a bare ``KeyError``; the sync introspection seam holds no direct
``asyncio.run``, so callers hosted inside a running event loop work as-is.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from ccf.contracts.base import CCFContract
from ccf.workflow.factory import Workflow
from ccf.authz.capability import Authorized, Execute, Resume
from ccf_runtime.orchestration.common import (
    SegmentNotExecutedError,
    WorkflowDriverError,
)
from ccf_runtime.workflow.engine import WorkflowEngine, WorkflowSuspended

__all__ = ["LangGraphWorkflowDriver"]

#: The engine call a start run closes over the capability: ``execution_id``
#: in, the engine's typed outcome out.
_StartCall = Callable[[str], Awaitable[CCFContract]]

#: The engine call a resume run closes over: ``(execution_id, decision)``.
_ResumeCall = Callable[[str, str], Awaitable[CCFContract]]


def _not_presented(verb: str) -> Callable[..., Awaitable[CCFContract]]:
    """The node a run presented no capability for — typed on reach.

    A start run carries ``Execute`` and never reaches the post-interrupt
    half of ``gate``; a resume run carries ``Resume`` and never re-runs
    ``drive``. The topology guarantees that; this makes reaching the other
    node a :class:`WorkflowDriverError` rather than a silent ``None``.
    """

    async def absent(*_: str) -> CCFContract:
        raise WorkflowDriverError(
            f"no capability was presented for {verb} in this run; a run"
            " carries the capability for its own verb and nothing else"
            " (D-IMPL-353 §1.2)"
        )

    return absent


class _Position(TypedDict):
    """The graph's own state channels — position, and nothing of CCF's.

    Two scalars: the execution id (so a resumed run knows which execution it
    is), and whether the last engine outcome was a suspension (so the
    conditional edge knows where to park). The engine's typed outcomes never
    enter these channels — they would otherwise land in the checkpointer,
    which is exactly the authority inversion T-07-30 names.
    """

    execution_id: str
    suspended: bool


class LangGraphWorkflowDriver:
    """The LangGraph leg of `OrchestrationProtocol` (D-IMPL-60 leg 1).

    Args:
        engine: The CCF workflow engine this driver drives. Injected, never
            constructed here; its wiring is the composition root's business,
            and its authority over state and audit is the whole point.
    """

    def __init__(self, *, engine: WorkflowEngine) -> None:
        self._engine = engine
        self._checkpointer = InMemorySaver()
        #: The engine's typed outcomes, held driver-side keyed by
        #: ``(tenant, execution_id)`` — the capability's tenant (§1.3) —
        #: deliberately NOT a graph state channel, so nothing CCF-typed
        #: reaches the checkpointer. Retention is the driver instance's
        #: lifetime (one entry per execution, no eviction — Phase-9 review
        #: IN-04): sized for conformance-suite and per-composition
        #: lifetimes; a long-lived composition root should recycle the
        #: driver, not hold one forever.
        self._outcomes: dict[tuple[str, str], CCFContract] = {}

    def _outcome(self, tenant: str, execution_id: str) -> CCFContract:
        """The engine's typed outcome for one execution — typed on absence.

        Phase-9 CONTEXT D-10 (WR-03): a never-executed segment is a driver
        condition, not a dict accident — :class:`SegmentNotExecutedError`,
        never a bare ``KeyError``.
        """
        try:
            return self._outcomes[(tenant, execution_id)]
        except KeyError:
            raise SegmentNotExecutedError(
                f"no executed segment for tenant {tenant!r},"
                f" execution {execution_id!r}"
            ) from None

    # -- the topology, authored here against the engine's public surface ------

    def _graph(
        self,
        *,
        tenant: str,
        on_start: _StartCall,
        on_resume: _ResumeCall,
    ) -> CompiledStateGraph[_Position]:
        """One compiled StateGraph per drive — the driver's own topology.

        Two nodes. ``drive`` starts the execution through ``on_start``;
        ``gate`` parks on :func:`interrupt` and, on ``Command(resume=...)``,
        hands the decision to ``on_resume``. Both are closures the calling
        verb built over the engine and the capability it received — the
        graph itself names neither. The conditional edge loops back to
        ``gate`` while the engine keeps suspending — a workflow with several
        gates parks once per gate, LangGraph-natively.
        """

        def _park(outcome: CCFContract, execution_id: str) -> _Position:
            self._outcomes[(tenant, execution_id)] = outcome
            return {
                "execution_id": execution_id,
                "suspended": isinstance(outcome, WorkflowSuspended),
            }

        async def drive(state: _Position) -> _Position:
            outcome = await on_start(state["execution_id"])
            return _park(outcome, state["execution_id"])

        async def gate(state: _Position) -> _Position:
            suspended = self._outcome(tenant, state["execution_id"])
            if not isinstance(suspended, WorkflowSuspended):
                raise WorkflowDriverError(
                    f"gate node reached with non-suspended outcome for"
                    f" {tenant!r}/{state['execution_id']!r}"
                )
            decision = interrupt(
                {"gate": suspended.gate, "event_key": suspended.event_key}
            )
            outcome = await on_resume(state["execution_id"], str(decision))
            return _park(outcome, state["execution_id"])

        def route(state: _Position) -> str:
            return "gate" if state["suspended"] else END

        builder = StateGraph(_Position)
        builder.add_node("drive", drive)
        builder.add_node("gate", gate)
        builder.add_edge(START, "drive")
        builder.add_conditional_edges("drive", route, ["gate", END])
        builder.add_conditional_edges("gate", route, ["gate", END])
        return builder.compile(checkpointer=self._checkpointer)

    @staticmethod
    def _config(tenant: str, execution_id: str) -> RunnableConfig:
        """Thread identity mirrors the engine's own (tenant, execution_id) key."""
        return {"configurable": {"thread_id": f"{tenant}/{execution_id}"}}

    # -- OrchestrationProtocol -------------------------------------------------

    async def start_execution(
        self,
        *,
        authorized: Authorized[Execute],
        workflow: Workflow,
        execution_id: str,
    ) -> CCFContract:
        """Run the graph from the top; park on the gate node if the engine
        suspends; return the engine's own typed outcome, verbatim. The
        ``Execute`` capability is closed over by the ``drive`` node and
        handed to the engine, which verifies it (D-IMPL-353 §1.2)."""
        tenant = authorized.tenant

        async def on_start(execution_id: str) -> CCFContract:
            return await self._engine.execute(
                authorized, workflow, execution_id=execution_id
            )

        graph = self._graph(
            tenant=tenant,
            on_start=on_start,
            on_resume=_not_presented("resume_execution"),
        )
        entry: _Position = {"execution_id": execution_id, "suspended": False}
        await graph.ainvoke(entry, self._config(tenant, execution_id))
        return self._outcome(tenant, execution_id)

    async def resume_execution(
        self,
        *,
        authorized: Authorized[Resume],
        workflow: Workflow,
        execution_id: str,
        decision: str,
    ) -> CCFContract:
        """Resume the parked graph with ``Command(resume=decision)``; the gate
        node hands the decision to the engine's own resume surface under the
        ``Resume`` capability this call received."""
        tenant = authorized.tenant

        async def on_resume(execution_id: str, decision: str) -> CCFContract:
            return await self._engine.resume(
                authorized,
                workflow,
                execution_id=execution_id,
                decision=decision,
            )

        graph = self._graph(
            tenant=tenant,
            on_start=_not_presented("start_execution"),
            on_resume=on_resume,
        )
        await graph.ainvoke(
            Command(resume=decision), self._config(tenant, execution_id)
        )
        return self._outcome(tenant, execution_id)

    # -- introspection for the conformance suite -------------------------------

    def checkpointed_values(
        self, *, tenant: str, execution_id: str
    ) -> tuple[object, ...]:
        """Every value the checkpointer persisted for one execution.

        The conformance suite's T-07-30 assertion runs over this: graph
        position (the parked node names) and the two scalar channels are all
        that may appear — no CCF workflow state. Takes the tenant the engine
        filed under — the capability's — never a handle to read one from.
        No node runs here, so no capability is presented.
        """
        snapshot = self._graph(
            tenant=tenant,
            on_start=_not_presented("start_execution"),
            on_resume=_not_presented("resume_execution"),
        ).get_state(self._config(tenant, execution_id))
        values: dict[str, object] = dict(snapshot.values)
        return tuple(values.values()) + tuple(snapshot.next)
