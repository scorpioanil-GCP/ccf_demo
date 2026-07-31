"""The in-SDK reference adapter — `OrchestrationProtocol` over `WorkflowEngine`.

SDK-defined (CLAUDE.md §8.1; D-IMPL-17/60). The doctrine sentence's "(and an
in-SDK reference adapter over `WorkflowEngine`)" made concrete: a thin class
that implements :class:`~ccf.orchestration.protocol.OrchestrationProtocol`
by delegating to the engine — the engine itself is the authority the
Protocol drives and is never the isinstance target. This is the reference
leg every external driver's replay landing is compared against in the
factory-parametrized conformance suite.

Thin is the point: the adapter adds no state, no routing, and no audit of
its own, so what it proves is exactly that the Protocol's surface is
sufficient to drive the engine — and its replay landing is, byte-for-byte,
the engine's own.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.contracts.base import CCFContract
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.engine import WorkflowEngine

__ccf_mode__ = "algorithmic"

__all__ = ["WorkflowEngineOrchestrationAdapter"]


class WorkflowEngineOrchestrationAdapter:
    """The reference `OrchestrationProtocol` leg (CLAUDE.md §8.1; D-IMPL-60).

    Args:
        engine: The CCF workflow engine this adapter drives. Injected, never
            constructed here — the engine's own wiring (Control Plane,
            ArtifactStore, HITL transport, node bindings, clock) is the
            composition root's business.
    """

    def __init__(self, *, engine: WorkflowEngine) -> None:
        self._engine = engine

    async def start_execution(
        self, *, workflow: Workflow, execution_id: str
    ) -> CCFContract:
        """Delegate to the engine's execute surface, verbatim."""
        return await self._engine.execute(workflow, execution_id=execution_id)

    async def resume_execution(
        self, *, workflow: Workflow, execution_id: str, decision: str
    ) -> CCFContract:
        """Delegate to the engine's resume surface, verbatim."""
        return await self._engine.resume(
            workflow, execution_id=execution_id, decision=decision
        )
