"""`AdkWorkflowDriver` — CCF workflows driven through Google ADK's topology.

SDK-defined (CLAUDE.md §8.1; D-IMPL-17/60 — the second of the three driver
legs). Implements :class:`~ccf.orchestration.protocol.OrchestrationProtocol`
by authoring an ADK ``Workflow`` composition (``google.adk.workflow`` — the
non-deprecated composition surface at ADK 2.5.0) over the CCF engine's
**public** surface — ``execute`` and ``resume`` on WorkflowFactory-built
handles — and nothing else. The topology here is this module's own (A7,
D-19): nothing is read from, shared with, or imported out of the
harness-adapter tree, and the ``d06-orchestration-split`` lint holds that
boundary structurally.

**The CCF engine is authoritative for state and audit (T-07-33).** The
suspended :class:`~ccf_runtime.workflow.state.WorkflowStateRecord` lives on
the Control Plane store, written through the engine's audited write surface;
the execution trace writes through to the ArtifactStore; the typed outcomes
the driver returns are the engine's own, verbatim. ADK's session machinery
(:class:`~google.adk.sessions.InMemorySessionService`) holds **position
only** — which segment of the drive the sequence is parked on, as scalar
session-state values — and the conformance suite asserts that nothing
CCF-typed is in it (:meth:`AdkWorkflowDriver.persisted_state` is the
introspection seam it asserts through).

**Suspension surfaces as control returning to CCF between ADK invocations.**
ADK has no first-class interrupt: a run of the driver's ``Workflow``
carries the drive to the hitl-gate, the gate sub-agent records the parked
position, the sequence ends, and the driver returns the engine's typed
suspend handle. A resume is a *second* ADK run over the resume segment, with
the externally-bound decision handed to the engine's own ``resume`` —
routing stays the workflow artifact's statement (CINV-01), interpreted by
the engine, never by the topology. ADK owns intra-step topology only.

Sub-agents run with no model configured: subclassing ``BaseAgent`` and
implementing ``_run_async_impl`` is ADK's own sanctioned way to run
something that is not a model call, driven by a real ``Runner`` (D-09).

Not an algorithmic module: it imports an orchestrator SDK, which is exactly
what the CINV-02 carve-out for ``ccf_runtime.orchestration`` exists to
permit here and nowhere else.

**Loop-safety (WR-03; Phase-9 CONTEXT D-09..D-11).** The sync introspection
seam dispatches through :func:`~ccf_runtime.orchestration.common.
run_coroutine_sync` — never a direct ``asyncio.run`` — so callers hosted
inside a running event loop get state instead of a nested-run
``RuntimeError``; outcome lookups raise the shared typed hierarchy
(:class:`~ccf_runtime.orchestration.common.SegmentNotExecutedError`,
:class:`~ccf_runtime.orchestration.common.DriverStateRetrievalError`), never
a bare ``KeyError``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import Workflow as AdkWorkflow
from google.genai import types as genai_types

from ccf.contracts.base import CCFContract
from ccf.workflow.factory import Workflow
from ccf_runtime.orchestration.common import (
    DriverStateRetrievalError,
    SegmentNotExecutedError,
    run_coroutine_sync,
)
from ccf_runtime.workflow.engine import WorkflowEngine, WorkflowSuspended

__all__ = ["AdkWorkflowDriver"]

#: The ADK app name this driver's runs register under — driver plumbing, not
#: deployment vocabulary: it never leaves the driver's own session service.
_APP_NAME = "ccf-orchestration-adk"

#: Session-state keys for the scalar position the topology parks on.
_EXECUTION_KEY = "ccf_execution_id"
_SUSPENDED_KEY = "ccf_suspended"
_SEGMENT_KEY = "ccf_segment"


class _EngineSegment(BaseAgent):
    """One segment of the drive as an ADK sub-agent, engine-invoking.

    Holds no fabric object of its own: the engine call is a closure the
    driver hands it, so what ADK schedules is exactly one advancement of the
    CCF execution through the engine's public surface. The event it yields
    carries only scalar position onto ADK's session state — never a typed
    CCF outcome, which stays driver-side (T-07-33).
    """

    _advance: Callable[[], Awaitable[CCFContract]]
    _execution_id: str

    def __init__(
        self,
        *,
        name: str,
        advance: Callable[[], Awaitable[CCFContract]],
        execution_id: str,
    ) -> None:
        super().__init__(name=name)
        object.__setattr__(self, "_advance", advance)
        object.__setattr__(self, "_execution_id", execution_id)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        outcome = await self._advance()
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(
                state_delta={
                    _EXECUTION_KEY: self._execution_id,
                    _SUSPENDED_KEY: isinstance(outcome, WorkflowSuspended),
                    _SEGMENT_KEY: self.name,
                }
            ),
        )


class _GatePark(BaseAgent):
    """The hitl-gate as a sub-agent: record the parked position, end the run.

    This is where control returns to CCF between ADK invocations: the
    sequence's gate step does not block, poll, or hold anything — it marks
    the park on session state and the run ends, leaving the suspended
    ``WorkflowStateRecord`` where it already is, on the Control Plane store.
    """

    _is_suspended: Callable[[], bool]

    def __init__(self, *, name: str, is_suspended: Callable[[], bool]) -> None:
        super().__init__(name=name)
        object.__setattr__(self, "_is_suspended", is_suspended)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self._is_suspended():
            return
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={_SEGMENT_KEY: self.name}),
        )


class AdkWorkflowDriver:
    """The Google ADK leg of `OrchestrationProtocol` (D-IMPL-60 leg 2).

    Args:
        engine: The CCF workflow engine this driver drives. Injected, never
            constructed here; its wiring is the composition root's business,
            and its authority over state and audit is the whole point.
    """

    def __init__(self, *, engine: WorkflowEngine) -> None:
        self._engine = engine
        # ADK ships `py.typed` but leaves this constructor unannotated at
        # 2.5.0, so the call — not the module — is the untyped boundary.
        self._sessions = InMemorySessionService()  # type: ignore[no-untyped-call]
        #: The engine's typed outcomes, held driver-side keyed by
        #: ``(tenant, execution_id)`` — deliberately NOT session state, so
        #: nothing CCF-typed reaches ADK's session machinery.
        self._outcomes: dict[tuple[str, str], CCFContract] = {}

    def _outcome(self, tenant: str, execution_id: str) -> CCFContract:
        """The engine's typed outcome for one execution — typed on absence.

        Phase-9 CONTEXT D-10/D-11 (WR-03): a never-executed segment is a
        driver condition, not a dict accident —
        :class:`SegmentNotExecutedError`, never a bare ``KeyError``. The
        same helper shape on every driver leg, parity-asserted.
        """
        try:
            return self._outcomes[(tenant, execution_id)]
        except KeyError:
            raise SegmentNotExecutedError(
                f"no executed segment for tenant {tenant!r},"
                f" execution {execution_id!r}"
            ) from None

    # -- the topology, authored here against the engine's public surface ------

    async def _run(
        self, workflow: Workflow, execution_id: str, sequence: AdkWorkflow
    ) -> CCFContract:
        """One real ``Runner`` run of the driver's own sequence, no model."""
        tenant = workflow.definition.tenant
        session_id = f"{tenant}/{execution_id}"
        existing = await self._sessions.get_session(
            app_name=_APP_NAME, user_id=tenant, session_id=session_id
        )
        if existing is None:
            await self._sessions.create_session(
                app_name=_APP_NAME, user_id=tenant, session_id=session_id
            )
        # ``node=`` is ADK 2.5.0's parameter for BaseNode roots (an ADK
        # ``Workflow`` is a BaseNode, not a BaseAgent).
        runner = Runner(
            node=sequence, app_name=_APP_NAME, session_service=self._sessions
        )
        async for _ in runner.run_async(
            user_id=tenant,
            session_id=session_id,
            new_message=genai_types.Content(
                role="user", parts=[genai_types.Part(text="")]
            ),
        ):
            pass
        return self._outcome(tenant, execution_id)

    def _suspended(self, tenant: str, execution_id: str) -> bool:
        return isinstance(
            self._outcomes.get((tenant, execution_id)), WorkflowSuspended
        )

    # -- OrchestrationProtocol -------------------------------------------------

    async def start_execution(
        self, *, workflow: Workflow, execution_id: str
    ) -> CCFContract:
        """Drive to the gate through an ADK ``Workflow`` chain; if the
        engine suspends, the gate segment parks the position and control
        returns to CCF; the engine's own typed outcome comes back verbatim."""
        tenant = workflow.definition.tenant
        key = (tenant, execution_id)

        async def advance() -> CCFContract:
            outcome = await self._engine.execute(
                workflow, execution_id=execution_id
            )
            self._outcomes[key] = outcome
            return outcome

        sequence = AdkWorkflow(
            name="ccf_workflow_drive",
            edges=[
                (
                    "START",
                    _EngineSegment(
                        name="drive",
                        advance=advance,
                        execution_id=execution_id,
                    ),
                    _GatePark(
                        name="gate",
                        is_suspended=lambda: self._suspended(
                            tenant, execution_id
                        ),
                    ),
                )
            ],
        )
        return await self._run(workflow, execution_id, sequence)

    async def resume_execution(
        self, *, workflow: Workflow, execution_id: str, decision: str
    ) -> CCFContract:
        """A second ADK run over the resume segment: the externally-bound
        decision goes to the engine's own resume surface, and the sequence
        parks again if the engine suspends on a later gate."""
        tenant = workflow.definition.tenant
        key = (tenant, execution_id)

        async def advance() -> CCFContract:
            outcome = await self._engine.resume(
                workflow, execution_id=execution_id, decision=decision
            )
            self._outcomes[key] = outcome
            return outcome

        sequence = AdkWorkflow(
            name="ccf_workflow_resume",
            edges=[
                (
                    "START",
                    _EngineSegment(
                        name="resume",
                        advance=advance,
                        execution_id=execution_id,
                    ),
                    _GatePark(
                        name="gate",
                        is_suspended=lambda: self._suspended(
                            tenant, execution_id
                        ),
                    ),
                )
            ],
        )
        return await self._run(workflow, execution_id, sequence)

    # -- introspection for the conformance suite -------------------------------

    def persisted_state(
        self, *, workflow: Workflow, execution_id: str
    ) -> tuple[object, ...]:
        """Every value ADK's session machinery persisted for one execution.

        The conformance suite's T-07-33 assertion runs over this: the scalar
        position channels are all that may appear — no CCF workflow state.
        Loop-aware (Phase-9 CONTEXT D-09): dispatch goes through
        :func:`run_coroutine_sync`, so a caller hosted inside a running
        event loop gets state, not a nested-run ``RuntimeError``; substrate
        failures surface as :class:`DriverStateRetrievalError` (T-09-05).
        """
        tenant = workflow.definition.tenant
        try:
            session = run_coroutine_sync(
                self._sessions.get_session(
                    app_name=_APP_NAME,
                    user_id=tenant,
                    session_id=f"{tenant}/{execution_id}",
                )
            )
        except Exception as exc:
            raise DriverStateRetrievalError(
                f"session retrieval failed for tenant {tenant!r},"
                f" execution {execution_id!r}"
            ) from exc
        if session is None:
            return ()
        return tuple(dict(session.state).values())
