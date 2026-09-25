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
typed, canonical-serializable contract — and imports no orchestrator SDK
(CINV-02 holds: zero harness imports in ``/src``). The
:class:`~ccf.authz.capability.Authorized` capability type it names in its
signatures is ``/src``'s own (D-29 — ``src`` never imports ``runtime``) and
is imported under ``TYPE_CHECKING`` only: named, never executed here.

**A driver threads the capability; it mints nothing (D-IMPL-353 §1.2).**
Both verbs take the ``Authorized`` for their own action — ``Execute`` to
start, ``Resume`` to continue — from whoever invoked the driver, and hand it
to the engine's own surface, which verifies it. A driver holds no
capability in any field: it lives in the closure of the call that received
it and dies with it. The engine files under ``authorized.tenant`` (§1.3), so
a driver's own position key is that tenant too, and its introspection
seams take the tenant, never a handle to read one out of.

Citation: CLAUDE.md §8.1 (SDK-defined extension); D-IMPL-17 (seam scope and
the identical-replay-obligations condition); D-IMPL-60 (three driver legs,
the module-tree split, one conformance suite); ORCH-02.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.workflow.factory import Workflow

if TYPE_CHECKING:
    from ccf.authz.capability import Authorized, Execute, Resume

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
        self,
        *,
        authorized: Authorized[Execute],
        workflow: Workflow,
        execution_id: str,
    ) -> CCFContract:
        """Start one execution from a WorkflowFactory-built handle.

        ``authorized`` is the ``Execute`` capability the gate minted for the
        handle's definition key; the driver passes it to the engine, which
        verifies it (D-IMPL-353 §1.2). The handle is the ONLY accepted
        description of what to run
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
        self,
        *,
        authorized: Authorized[Resume],
        workflow: Workflow,
        execution_id: str,
        decision: str,
    ) -> CCFContract:
        """Continue a suspended execution under a bound decision.

        ``authorized`` is the ``Resume`` capability — its own kind, never
        ``Execute`` (§1.5); the driver passes it to the engine's own resume
        surface. ``decision`` must name a transition target the workflow artifact
        declares from the suspended node — routing is the artifact's
        statement, and a decision the artifact declares no transition for
        comes back as the engine's typed refusal, never as orchestrator
        improvisation (CINV-01). Returns the same typed outcome vocabulary
        as :meth:`start_execution`.
        """
        ...
