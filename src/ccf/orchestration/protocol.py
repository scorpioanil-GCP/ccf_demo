"""`OrchestrationProtocol` — the seam an external orchestrator drives CCF through.

SDK-defined extension, marked as such (CLAUDE.md §8.1 — the whitepaper
assumes a control plane; it does not specify an orchestration seam).
D-IMPL-17 committed the seam; D-IMPL-60 widened it to three real driver
integrations (Google ADK, the Claude Agent SDK, LangGraph), each under
``runtime/ccf_runtime/orchestration/<sdk>/`` — never under
``runtime/ccf_runtime/adapters/<sdk>/``, a separate-module-tree split the
D-06 lint enforces bidirectionally.

**The doctrine, in one sentence.** `OrchestrationProtocol` is implemented by
drivers (and an in-SDK reference adapter over `WorkflowEngine`); the engine
is the authority the Protocol drives, not a third peer harness — the
conformance isinstance target is drivers/the reference adapter, never the
bare engine.

**Identical replay obligations to the in-SDK engine.** An execution driven
through this Protocol carries exactly the replay obligations the in-SDK
engine carries for the same workflow: the suspended state lands on the
Control Plane store through the audited write surface, the execution trace
writes through to the ArtifactStore at suspend and terminal, and the
terminal outcome hands the dimension-5 step-sequence block and dimension-4
delegation chain to replay. Scoped per D-22 to what the type system
enforces: the Protocol's surface accepts only WorkflowFactory-built handles
and returns only the typed outcome contracts the engine itself produces;
the obligations themselves are *proven*, not asserted, by the
factory-parametrized conformance suite (``tests/conformance/
test_orchestration.py``), which compares each driver leg's replay landing
byte-for-byte against the reference adapter's.

**What the seam is not.** It is not a loop, and it is not a workflow engine:
starting and resuming are the only verbs, because everything between them —
node execution, routing interpretation, state persistence, audit — is the
engine's, and a Protocol that exposed any of it would let an external
orchestrator hold authoritative state (T-07-30). The orchestrator holds its
own topology position and nothing else.

The outcome contracts (typed suspend handle, terminal trace, exception
routing, refusal) live beside the machine in ``/runtime``
(:mod:`ccf_runtime.workflow.engine`) per the record-next-to-the-machine
doctrine; this ``/src`` module therefore types them at the
:class:`~ccf.contracts.base.CCFContract` boundary — every outcome is a
typed, canonical-serializable contract — and imports nothing from
``/runtime`` and no orchestrator SDK (CINV-02 holds: zero harness imports
in ``/src``).

Citation: CLAUDE.md §8.1 (SDK-defined extension); D-IMPL-17 (seam scope and
the identical-replay-obligations condition); D-IMPL-60 (three driver legs,
the module-tree split, one conformance suite); ORCH-02.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.workflow.factory import Workflow

__ccf_mode__ = "algorithmic"

__all__ = ["OrchestrationProtocol"]


@runtime_checkable
class OrchestrationProtocol(Protocol):
    """Structural contract for an external orchestrator driver (CLAUDE.md §8.1).

    Implementations live under ``runtime/ccf_runtime/orchestration/<sdk>/``
    plus the in-SDK reference adapter over the engine; the bare engine is
    never the isinstance target (module docstring doctrine). Conformance is
    verified by the factory-parametrized suite against the real SDKs.

    ``runtime_checkable`` supports composition-root wiring checks; it
    verifies method presence only, so static conformance still rests on
    mypy. Every method is keyword-only after ``self``: these arguments are
    never positional-by-accident.
    """

    async def start_execution(
        self, *, workflow: Workflow, execution_id: str
    ) -> CCFContract:
        """Start one execution from a WorkflowFactory-built handle.

        The handle is the ONLY accepted description of what to run
        (ORCH-01 — "via the Task Factory" holds at this seam exactly as it
        holds at the engine's own boundary). Runs until the CCF engine
        suspends on a hitl-gate or reaches a terminal condition, and
        returns the engine's own typed outcome: the suspend handle
        (gate, event key, trace artifact) or the terminal trace (step
        sequence block, delegation chain, trace artifact) — the replay
        landing, verbatim.
        """
        ...

    async def resume_execution(
        self, *, workflow: Workflow, execution_id: str, decision: str
    ) -> CCFContract:
        """Continue a suspended execution under a bound decision.

        ``decision`` must name a transition target the workflow artifact
        declares from the suspended node — routing is the artifact's
        statement, and a decision the artifact declares no transition for
        comes back as the engine's typed refusal, never as orchestrator
        improvisation (CINV-01). Returns the same typed outcome vocabulary
        as :meth:`start_execution`.
        """
        ...
