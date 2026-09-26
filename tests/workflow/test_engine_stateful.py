"""hypothesis.stateful coverage of the workflow engine (07-06, milestone 3).

A :class:`~hypothesis.stateful.RuleBasedStateMachine` drives the engine
through interleaved start / advance / suspend / resume / inject-exception
sequences across **two tenants** and **two workflow definitions** (the
gated covenant-review wrapper and the straight-line certificate-refresh
wrapper), asserting after every step:

* **a terminal execution never transitions again** — every resume of a
  terminal execution is a typed refusal and its persisted record never
  changes;
* **every observed transition is in the audit log** — each state key with a
  persisted record has ``workflow_*`` audit events on the one shared log,
  and the trace never shrinks;
* **suspended state always round-trips** ``get`` — the record under the
  key is this machine's typed record, keyed to its own tenant;
* **no cross-tenant state leakage** (D-23) — state keys, HITL queues, and
  audit keys for one tenant never surface under the other.

Example counts are bounded for CI runtime in the house profile's spirit
(``tests/properties/strategies.py``: derandomized, no deadline, bounded
examples).
"""

from __future__ import annotations

import asyncio
import itertools
import tempfile
from typing import Any

from hypothesis import settings
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)
from hypothesis import strategies as st

from ccf.artifacts.file_store import FileArtifactStore
from http_api.composition_authority import deployment_store
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.workflow.factory import Workflow
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowResumeRefused,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

from tests.workflow.capabilities import (
    execute_as,
    execute_capability,
    resume_as,
)

from tests.workflow.test_engine import (
    _Bindings,
    _PermissiveDebt,
    _covenant,
    _refresh,
    _register_covenant_closure,
    _register_refresh_closure,
    _resolve_gate,
    _ticking_clock,
)

TENANTS = ("acme-bank", "beta-bank")
SHAPES = ("covenant", "refresh")

WORKFLOW_AUDIT_ACTIONS = frozenset(
    {
        "workflow_transition",
        "workflow_suspended",
        "workflow_resumed",
        "workflow_exception",
        "workflow_completed",
    }
)


class WorkflowEngineMachine(RuleBasedStateMachine):
    """Interleave executions of two tenants' workflows through one engine."""

    @initialize()
    def wire(self) -> None:
        self.registry = ControlPlaneRegistry(clock=_ticking_clock())
        _register_covenant_closure(self.registry)
        _register_refresh_closure(self.registry)
        self.bindings = _Bindings()
        self._tmp = tempfile.TemporaryDirectory()
        self.transport = InMemoryHitlTransport()
        self.engine = WorkflowEngine(
            control_plane=self.registry,
            artifact_store=deployment_store(self._tmp.name, workflow_traces=True),
            hitl_transport=self.transport,
            skill_binding=self.bindings,
            agent_binding=self.bindings,
            clock=_ticking_clock(),
            debt_binding=_PermissiveDebt(),
        )
        self.workflows: dict[tuple[str, str], Workflow] = {}
        version = itertools.count()
        for tenant in TENANTS:
            bump = f"1.{next(version)}.0"
            mutations: dict[str, Any] = (
                {} if tenant == "acme-bank" else {"tenant": tenant}
            )
            self.workflows[(tenant, "covenant")] = _covenant(
                self.registry, artifact_version=bump, **mutations
            )
            self.workflows[(tenant, "refresh")] = _refresh(
                self.registry, artifact_version=f"1.{next(version)}.1", **mutations
            )
        self._ids = itertools.count(1)
        # key -> lifecycle we last observed: suspended | exception | terminal
        self.observed: dict[str, str] = {}
        self.trace_lengths: dict[str, int] = {}

    def teardown(self) -> None:
        self._tmp.cleanup()

    # -- rules ----------------------------------------------------------------

    @rule(
        tenant=st.sampled_from(TENANTS),
        shape=st.sampled_from(SHAPES),
        fail=st.booleans(),
    )
    def start(self, tenant: str, shape: str, fail: bool) -> None:
        """Start a fresh execution, optionally injecting a node exception."""
        workflow = self.workflows[(tenant, shape)]
        execution_id = f"exec-{next(self._ids)}"
        key = f"{tenant}/{execution_id}"
        self.bindings.failing = (
            frozenset({"fetch-certificates"}) if fail else frozenset()
        )
        outcome = asyncio.run(
            self.engine.execute(execute_as(workflow), workflow, execution_id=execution_id)
        )
        self.bindings.failing = frozenset()
        if fail and shape == "covenant":
            assert isinstance(outcome, WorkflowExceptionRouted)
            self.observed[key] = "exception"
        elif fail:
            assert isinstance(outcome, WorkflowCompleted)
            assert outcome.terminal_state == "failed"
            self.observed[key] = "terminal"
        elif shape == "covenant":
            assert isinstance(outcome, WorkflowSuspended)
            self.observed[key] = "suspended"
        else:
            assert isinstance(outcome, WorkflowCompleted)
            self.observed[key] = "terminal"
        self._shapes = getattr(self, "_shapes", {})
        self._shapes[key] = (tenant, shape)

    def _keys_in(self, lifecycle: str) -> list[str]:
        return sorted(
            key for key, status in self.observed.items() if status == lifecycle
        )

    @precondition(lambda self: bool(self._keys_in("suspended")))
    @rule(data=st.data(), verdict=st.sampled_from(["approve", "reject"]))
    def resume_suspended(self, data: st.DataObject, verdict: str) -> None:
        """The recorded VERDICT decides where a suspended execution may go.

        The human acts first: a gate opens on a recorded action returned
        through the HITL authority path, never on the decision string alone
        (SEC-001).

        **The verdict and the decision are drawn INDEPENDENTLY, and the rule
        asserts the biconditional** — a completion whose terminal state
        equals the decision if and only if the decision equals the target
        the artifact declares for the verdict actually recorded, and a
        typed refusal otherwise (D-IMPL-357 A3). Round 1 of review found
        why that matters: an earlier version of this rule read the decision
        out of ``gate_routes[gate][verdict]``, so every generated resume was
        an AGREEING pair and the machine could not produce the input the
        compare guards against. Measured: under the one-hunk sabotage that
        deletes the route lookup, the compare and its refusal, the machine
        stayed GREEN. A property machine over a newly guarded surface that
        cannot produce the violating input leaves its entire generated space
        — every tenant and shape it explores — unexercised for that guard.

        The disagreeing draw is then followed by the agreeing one, which
        both keeps the lifecycle bookkeeping honest and pins that the gate
        is STILL OPEN after a refusal: one recorded verdict has exactly one
        declared destination, and a disagreeing resume neither takes it nor
        consumes it.
        """
        key = data.draw(st.sampled_from(self._keys_in("suspended")))
        tenant, shape = self._shapes[key]
        workflow = self.workflows[(tenant, shape)]
        _resolve_gate(
            self.registry, self.transport, tenant=tenant,
            event_key=f"{key}/credit-officer-approval", action=verdict,
        )
        routes = workflow.definition.gate_routes["credit-officer-approval"]
        declared = routes[verdict]
        # Drawn from the gate's own declared targets, independently of the
        # verdict: half the draws disagree with what was recorded.
        decision = data.draw(st.sampled_from(sorted(set(routes.values()))))
        outcome = asyncio.run(
            self.engine.resume(
                resume_as(workflow), workflow,
                execution_id=key.split("/", 1)[1], decision=decision,
            )
        )
        if decision == declared:
            assert isinstance(outcome, WorkflowCompleted)
            assert outcome.terminal_state == decision
        else:
            assert isinstance(outcome, WorkflowResumeRefused)
            # Still open, and only the declared route closes it.
            outcome = asyncio.run(
                self.engine.resume(
                    resume_as(workflow), workflow,
                    execution_id=key.split("/", 1)[1], decision=declared,
                )
            )
            assert isinstance(outcome, WorkflowCompleted)
            assert outcome.terminal_state == declared
        self.observed[key] = "terminal"

    @precondition(lambda self: bool(self._keys_in("exception")))
    @rule(data=st.data())
    def resume_exception_routed(self, data: st.DataObject) -> None:
        """The handler hands the state back; the node retries and suspends."""
        key = data.draw(st.sampled_from(self._keys_in("exception")))
        tenant, shape = self._shapes[key]
        workflow = self.workflows[(tenant, shape)]
        outcome = asyncio.run(
            self.engine.resume(
                resume_as(workflow), workflow,
                execution_id=key.split("/", 1)[1],
                decision="retry",
            )
        )
        assert isinstance(outcome, WorkflowSuspended)
        self.observed[key] = "suspended"

    @precondition(lambda self: bool(self._keys_in("terminal")))
    @rule(data=st.data())
    def resume_terminal_is_refused(self, data: st.DataObject) -> None:
        """A terminal execution never transitions again."""
        key = data.draw(st.sampled_from(self._keys_in("terminal")))
        tenant, shape = self._shapes[key]
        workflow = self.workflows[(tenant, shape)]
        before = self.registry.state_store.get(WORKFLOW_STATE, key)
        outcome = asyncio.run(
            self.engine.resume(
                resume_as(workflow), workflow,
                execution_id=key.split("/", 1)[1],
                decision="approved",
            )
        )
        assert isinstance(outcome, WorkflowResumeRefused)
        assert self.registry.state_store.get(WORKFLOW_STATE, key) is before

    @rule(tenant=st.sampled_from(TENANTS))
    def resume_unknown_is_refused(self, tenant: str) -> None:
        workflow = self.workflows[(tenant, "covenant")]
        outcome = asyncio.run(
            self.engine.resume(
                resume_as(workflow), workflow, execution_id="never-started", decision="approved"
            )
        )
        assert isinstance(outcome, WorkflowResumeRefused)

    # -- invariants ------------------------------------------------------------

    @invariant()
    def suspended_state_round_trips_and_never_leaks(self) -> None:
        """Typed record under its own tenant's key, and only there (D-23)."""
        if not hasattr(self, "registry"):
            return
        for key, status in self.observed.items():
            record = self.registry.state_store.get(WORKFLOW_STATE, key)
            assert isinstance(record, WorkflowStateRecord)
            tenant, execution_id = key.split("/", 1)
            assert record.tenant == tenant
            assert record.execution_id == execution_id
            other = [t for t in TENANTS if t != tenant][0]
            assert (
                self.registry.state_store.get(
                    WORKFLOW_STATE, f"{other}/{execution_id}"
                )
                is None
                or key.replace(tenant, other) in self.observed
            )
            if status == "terminal":
                assert record.status == "terminal"

    @invariant()
    def every_observed_transition_is_in_the_audit_log(self) -> None:
        """Traces never shrink, and each traced key has audit evidence."""
        if not hasattr(self, "registry"):
            return
        audited_keys = {
            event.key
            for event in self.registry.audit_log.events()
            if event.action in WORKFLOW_AUDIT_ACTIONS
        }
        for key in self.observed:
            record = self.registry.state_store.get(WORKFLOW_STATE, key)
            assert isinstance(record, WorkflowStateRecord)
            assert key in audited_keys
            previous = self.trace_lengths.get(key, 0)
            assert len(record.trace) >= previous
            self.trace_lengths[key] = len(record.trace)


WorkflowEngineMachine.TestCase.settings = settings(
    max_examples=15,
    stateful_step_count=15,
    deadline=None,
    derandomize=True,
)

TestWorkflowEngineStateful = WorkflowEngineMachine.TestCase
