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

**Loop-safety (WR-03; Phase-9 CONTEXT D-10/D-11).** Outcome lookups raise
the shared typed hierarchy
(:class:`~ccf_runtime.orchestration.common.SegmentNotExecutedError`), never
a bare ``KeyError``; the sync introspection seam holds no direct
``asyncio.run``, so callers hosted inside a running event loop work as-is.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from ccf.contracts.base import CCFContract
from ccf.workflow.factory import Workflow
from ccf_runtime.orchestration.common import (
    SegmentNotExecutedError,
    WorkflowDriverError,
)
from ccf_runtime.workflow.engine import WorkflowEngine, WorkflowSuspended

__all__ = ["LangGraphWorkflowDriver"]


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
        #: ``(tenant, execution_id)`` — deliberately NOT a graph state
        #: channel, so nothing CCF-typed reaches the checkpointer.
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

    def _graph(self, workflow: Workflow) -> CompiledStateGraph[_Position]:
        """One compiled StateGraph per drive — the driver's own topology.

        Two nodes. ``drive`` starts the execution through the engine;
        ``gate`` parks on :func:`interrupt` and, on ``Command(resume=...)``,
        hands the decision to the engine's ``resume``. The conditional edge
        loops back to ``gate`` while the engine keeps suspending — a
        workflow with several gates parks once per gate, LangGraph-natively.
        """
        tenant = workflow.definition.tenant

        def _park(outcome: CCFContract, execution_id: str) -> _Position:
            self._outcomes[(tenant, execution_id)] = outcome
            return {
                "execution_id": execution_id,
                "suspended": isinstance(outcome, WorkflowSuspended),
            }

        async def drive(state: _Position) -> _Position:
            outcome = await self._engine.execute(
                workflow, execution_id=state["execution_id"]
            )
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
            outcome = await self._engine.resume(
                workflow,
                execution_id=state["execution_id"],
                decision=str(decision),
            )
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
    def _config(workflow: Workflow, execution_id: str) -> RunnableConfig:
        """Thread identity mirrors the engine's own (tenant, execution_id) key."""
        return {
            "configurable": {
                "thread_id": f"{workflow.definition.tenant}/{execution_id}"
            }
        }

    # -- OrchestrationProtocol -------------------------------------------------

    async def start_execution(
        self, *, workflow: Workflow, execution_id: str
    ) -> CCFContract:
        """Run the graph from the top; park on the gate node if the engine
        suspends; return the engine's own typed outcome, verbatim."""
        graph = self._graph(workflow)
        entry: _Position = {"execution_id": execution_id, "suspended": False}
        await graph.ainvoke(entry, self._config(workflow, execution_id))
        return self._outcome(workflow.definition.tenant, execution_id)

    async def resume_execution(
        self, *, workflow: Workflow, execution_id: str, decision: str
    ) -> CCFContract:
        """Resume the parked graph with ``Command(resume=decision)``; the gate
        node hands the decision to the engine's own resume surface."""
        graph = self._graph(workflow)
        await graph.ainvoke(
            Command(resume=decision), self._config(workflow, execution_id)
        )
        return self._outcome(workflow.definition.tenant, execution_id)

    # -- introspection for the conformance suite -------------------------------

    def checkpointed_values(
        self, *, workflow: Workflow, execution_id: str
    ) -> tuple[object, ...]:
        """Every value the checkpointer persisted for one execution.

        The conformance suite's T-07-30 assertion runs over this: graph
        position (the parked node names) and the two scalar channels are all
        that may appear — no CCF workflow state.
        """
        snapshot = self._graph(workflow).get_state(
            self._config(workflow, execution_id)
        )
        values: dict[str, object] = dict(snapshot.values)
        return tuple(values.values()) + tuple(snapshot.next)
