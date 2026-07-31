"""Engine-enforced debt assessment at agent-node handoffs (07-17).

D-IMPL-65's committed engine refusal, pulled into the 7.1 gap cycle by
D-IMPL-66(b): DESIGN.md §4 names per-handoff ``D_c`` recomputation with
fail-closed routing as a Workflow-primitive invariant (INV-CH7-68); v0
shipped it as composition-root responsibility. These tests pin the engine's
own enforcement, red-first:

* **R1 (the red test).** An engine constructed exactly as today's tests do
  — no debt-assessment binding — must refuse an agent-node handoff with a
  typed :class:`UnboundDebtAssessmentError` (a ``WorkflowWiringError``:
  broken deployment, I.1 refusal doctrine).
* **R2.** The refusal is scoped to *agent* handoffs (D-IMPL-65's sentence):
  a skill-only workflow with no binding completes normally.
* **G1.** A bound, non-breaching assessment is invoked once per agent
  handoff with ``(tenant, step_name, ref)`` and the handoff proceeds.
* **G2.** A Fail-Closed breach routes the node's exception path BEFORE
  ``run_agent`` is ever invoked — declared ref → routed handler
  (:class:`WorkflowExceptionRouted`); absent ref → the reserved ``failed``
  terminal (D-IMPL-61 option-a). ``run_agent`` call count is asserted 0.

Every workflow is factory-built from the banking fixture artifacts
(CLAUDE.md §6.4); thresholds live in the DebtProfile artifact vocabulary
(the :class:`~ccf.halflife.debt.DebtSignal` the assessment already carries)
— no numeric threshold appears here or in the engine (CINV-01).
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.workflow.definitions import WORKFLOW_FAILED_STATE
from ccf_runtime.workflow.engine import (
    UnboundDebtAssessmentError,
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowSuspended,
    WorkflowWiringError,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

from tests.workflow.test_engine import (  # the established fixture surface
    _Bindings,
    _covenant,
    _engine,
    _refresh,
    _ticking_clock,
    registry,  # noqa: F401 — pytest fixture re-export
)


def _assessment(signal: DebtSignal) -> DebtAssessment:
    """A DebtAssessment carrying ``signal`` — the artifact-band vocabulary."""
    return DebtAssessment(
        debt=Decimal("0.5"),
        signal=signal,
        factors=DebtFactors(
            freshness=Decimal("0.5"),
            completeness=Decimal("1"),
            semantic_consistency=Decimal("1"),
        ),
    )


class _StubDebtBinding:
    """A recording DebtAssessmentBinding double — the composition-root seam."""

    def __init__(self, signal: DebtSignal = DebtSignal.OK) -> None:
        self.signal = signal
        self.calls: list[tuple[str, str, str]] = []

    async def assess(
        self, *, tenant: str, step_name: str, ref: str
    ) -> DebtAssessment:
        self.calls.append((tenant, step_name, ref))
        return _assessment(self.signal)


def _bound_engine(
    registry: ControlPlaneRegistry,
    tmp_path: Path,
    debt: _StubDebtBinding,
) -> tuple[WorkflowEngine, _Bindings]:
    """An engine with the debt seam bound through the constructor."""
    bindings = _Bindings()
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=FileArtifactStore(root=tmp_path / "artifacts"),
        hitl_transport=InMemoryHitlTransport(),
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
        debt_binding=debt,
    )
    return engine, bindings


# --- R1: the red test — unbound refusal ---------------------------------------


def test_an_unbound_engine_refuses_an_agent_node_handoff(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """No bound debt assessment + an agent node = typed refusal (D-IMPL-65)."""
    engine, _, bindings = _engine(registry, tmp_path)  # no debt binding
    workflow = _covenant(registry)  # reaches the `analyze-covenants` agent node
    with pytest.raises(UnboundDebtAssessmentError, match="analyze-covenants"):
        asyncio.run(engine.execute(workflow, execution_id="exec-debt-1"))
    assert isinstance(UnboundDebtAssessmentError("x"), WorkflowWiringError)
    # The refusal fires BEFORE the handoff: the agent never ran.
    assert "agent:analyze-covenants" not in bindings.ran


# --- R2: scoped to agent handoffs ---------------------------------------------


def test_a_skill_only_workflow_needs_no_debt_binding(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The refusal is per-agent-handoff, not engine-wide (D-IMPL-65)."""
    engine, _, _ = _engine(registry, tmp_path)  # no debt binding
    workflow = _refresh(registry)  # skills only, no agent node
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-debt-2"))
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "refreshed"


# --- G1: bound and clean — assessed once, handoff proceeds --------------------


def test_a_bound_clean_assessment_precedes_each_agent_handoff(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    debt = _StubDebtBinding(DebtSignal.OK)
    engine, bindings = _bound_engine(registry, tmp_path, debt)
    workflow = _covenant(registry)
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-debt-3"))
    assert isinstance(outcome, WorkflowSuspended)  # reached the hitl gate
    assert "agent:analyze-covenants" in bindings.ran
    assert debt.calls == [
        (
            workflow.definition.tenant,
            "analyze-covenants",
            "ccf-artifact://acme-bank/ccf.agent-definition/"
            "covenant-analytics@1.3.0",
        )
    ]


# --- G2: fail-closed breach routes the exception path, never run_agent --------


def test_a_breach_routes_a_declared_exception_ref_without_running_the_agent(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Declared ref: WorkflowExceptionRouted; run_agent count is 0."""
    debt = _StubDebtBinding(DebtSignal.FAIL_CLOSED)
    engine, bindings = _bound_engine(registry, tmp_path, debt)
    handler = (
        "ccf-artifact://acme-bank/exception-handler/"
        "certificate-fetch-failed@1.0.0"
    )
    workflow = _covenant(
        registry,
        artifact_version="1.2.0",
        exception_refs={
            "fetch-certificates": handler,
            "analyze-covenants": handler,
        },
    )
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-debt-4"))
    assert isinstance(outcome, WorkflowExceptionRouted)
    assert outcome.node == "analyze-covenants"
    assert outcome.handler_ref == handler
    assert [c for c in bindings.ran if c.startswith("agent:")] == []
    assert len(debt.calls) == 1
    key = f"{workflow.definition.tenant}/exec-debt-4"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    assert isinstance(record, WorkflowStateRecord)
    assert record.trace[-1].kind == "exception"
    assert record.trace[-1].source == "analyze-covenants"


def test_a_breach_with_no_ref_propagates_to_the_failed_terminal(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """Absent ref: D-IMPL-61 option-a — the reserved failed terminal."""
    debt = _StubDebtBinding(DebtSignal.FAIL_CLOSED)
    engine, bindings = _bound_engine(registry, tmp_path, debt)
    workflow = _covenant(registry)  # analyze-covenants declares no ref
    outcome = asyncio.run(engine.execute(workflow, execution_id="exec-debt-5"))
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == WORKFLOW_FAILED_STATE
    assert [c for c in bindings.ran if c.startswith("agent:")] == []
