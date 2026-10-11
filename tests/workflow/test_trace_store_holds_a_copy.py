"""The outcome, the state record and the resume path never carry the trace the store held (``D-IMPL-380``, second round, ruling 2 (a)).

Dave, 2026-10-10 07:39 MST (the ``D-IMPL-380`` amendment), verbatim: *"Each writer gives the store a deep copy made
before the save and keeps its own. The caller and the replay record, including the workflow resume path, get the
untouched copy. The test alters the record and then answers with the original fingerprint. The saved-bytes limit
stays disclosed."*

``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._write_trace`` derives the trace's reference before ``put``
(the first round), so a store that rewrites the trace and answers the REWRITTEN trace's reference is refused. A store
that rewrites the trace and answers the trace's ORIGINAL reference passes that check, because the reference is right.
At ``ef5d27a4`` the store was handed the engine's own trace, whose entries are the very objects behind the completed
outcome's ``step_sequence_block``, inside the state record the engine keeps (an in-memory state store holds the
object), and — on the recovery path (``_restore_request``) — inside the record the engine writes to the state store
after the trace's ``put`` (Fable seat 2, F2-3; reproduced by the coordinator).

The attacker: a store that rewrites a field of the first entry of the trace it is handed with
``object.__setattr__`` inside ``put`` (a trace entry is a frozen model with no mapping field, so this is the one way
to alter it in place), files the rewritten trace through the deployment's real store, and answers the reference of
the trace as it was handed (the original fingerprint). The run proceeds; the test asserts the trace as built is
what the engine hands on:

* **completed**: ``step_sequence_block`` is the canonical trace as built, and the state record read back carries it;
* **suspended** and **exception-routed** (these outcomes carry no ``step_sequence_block``): the state record read
  back carries the trace as built; for a suspension, the approval request is bound to that record's content hash;
* **the resume path** (a resumption recovering a suspension whose request never reached the queue): the state
  record the recovery writes carries the trace as built.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import ArtifactStoreProtocol, DerivedWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import (
    WORKFLOW_TRACE_ARTIFACT_CLASS,
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from http_api.composition_authority import deployment_store
from tests.workflow import test_restore_missing_approval_request as rm
from tests.workflow.capabilities import execute_as
from tests.workflow.test_engine import (  # noqa: F401 — `registry` is a pytest fixture, used by name
    _Bindings,
    _covenant,
    _PermissiveDebt,
    _refresh,
    _ticking_clock,
    registry,
)

#: Each outcome that carries a trace reference: the workflow that reaches it, the failing step it needs, its type.
PATHS: dict[str, tuple[Callable[[ControlPlaneRegistry], Any], frozenset[str], type]] = {
    "completed": (_refresh, frozenset(), WorkflowCompleted),
    "suspended": (_covenant, frozenset(), WorkflowSuspended),
    "exception-routed": (_covenant, frozenset({"fetch-certificates"}), WorkflowExceptionRouted),
}


class _RewritesAndAnswersTheOriginal:
    """Rewrites the first entry of the next trace it is handed, files it, answers the trace's reference as handed."""

    def __init__(self, inner: ArtifactStoreProtocol) -> None:
        self._inner = inner
        self.armed = True
        self.as_handed: bytes | None = None
        self.address_as_handed: str | None = None
        self.address_as_rewritten: str | None = None

    def put(self, authorized: Any, artifact: Any) -> Any:
        trace = artifact.artifact
        if not (
            self.armed
            and isinstance(artifact, DerivedWrite)
            and artifact.artifact_class == WORKFLOW_TRACE_ARTIFACT_CLASS
            and isinstance(trace, tuple)
            and trace
        ):
            return self._inner.put(authorized, artifact)
        self.armed = False
        self.as_handed = canonical_bytes(trace)
        self.address_as_handed = content_hash(trace)
        object.__setattr__(trace[0], "target", f"{trace[0].target}-laundered")
        self.address_as_rewritten = content_hash(trace)
        filed = self._inner.put(authorized, artifact)
        # The original fingerprint: the reference of the trace as it was handed, naming what was filed.
        return filed.model_copy(
            update={
                "content_address": self.address_as_handed,
                "uri": filed.uri.replace(self.address_as_rewritten, self.address_as_handed),
            }
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _constructed(store: _RewritesAndAnswersTheOriginal, case: str) -> bytes:
    assert store.as_handed is not None and store.address_as_handed != store.address_as_rewritten, (
        f"[{case}] the case was not constructed: the store must have changed the trace's address"
    )
    return store.as_handed


def _assert_state_carries(record: object, as_built: bytes, case: str) -> None:
    assert isinstance(record, WorkflowStateRecord), f"[{case}] no state record: {record!r}"
    assert canonical_bytes(record.trace) == as_built, (
        f"[{case}] the state record carries the store's rewrite: {canonical_bytes(record.trace).decode('utf-8')!r};"
        f" the trace as the engine built it is {as_built.decode('utf-8')!r}"
    )


@pytest.mark.parametrize("path", sorted(PATHS))
def test_a_store_that_rewrites_the_trace_and_answers_the_original_reference_leaves_the_trace_as_built(
    registry: ControlPlaneRegistry, tmp_path: Path, path: str
) -> None:
    build, failing, outcome_type = PATHS[path]
    store = _RewritesAndAnswersTheOriginal(deployment_store(tmp_path / "artifacts", workflow_traces=True))
    bindings = _Bindings(failing=failing)
    transport = InMemoryHitlTransport()
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=store,
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
        debt_binding=_PermissiveDebt(),
    )
    workflow = build(registry)

    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))

    as_built = _constructed(store, path)
    assert isinstance(outcome, outcome_type), (
        f"[{path}] the store answered the trace's own reference, so the run must reach {outcome_type.__name__}:"
        f" {type(outcome).__name__}: {outcome}"
    )
    if isinstance(outcome, WorkflowCompleted):
        assert outcome.step_sequence_block.encode("utf-8") == as_built, (
            f"[{path}] step_sequence_block carries the store's rewrite: {outcome.step_sequence_block!r}; the trace"
            f" as the engine built it is {as_built.decode('utf-8')!r}"
        )
    key = f"{workflow.definition.tenant}/exec-1"
    record = registry.state_store.get(WORKFLOW_STATE, key)
    _assert_state_carries(record, as_built, path)
    if isinstance(outcome, WorkflowSuspended):
        assert isinstance(record, WorkflowStateRecord)
        bound = [e.product_content_hash for e in transport.pending(tenant=outcome.tenant) if e.event_key == outcome.event_key]
        assert bound == [content_hash(record)], (
            f"[{path}] the approval request is not bound to the suspension record as built: {bound}"
            f" against {content_hash(record)}"
        )


def test_the_resume_path_writes_the_state_record_with_the_trace_as_built(tmp_path: Path) -> None:
    case = "the resume path"
    run = rm.compose(tmp_path)
    run.transport.die_at_next_enqueue()
    with pytest.raises(OSError):
        rm.start(run)
    stuck = rm.state_of(run)
    assert stuck.status == "suspended" and not rm.requests(run, stuck.current_state), (
        f"[{case}] the case was not constructed: the run must be suspended with no pending request"
    )
    # The recovering engine: the same registry, transport and bindings, its artifact store the attacker.
    store = _RewritesAndAnswersTheOriginal(run.store)
    recovering = rm.Run(
        run.registry,
        WorkflowEngine(
            control_plane=run.registry,
            artifact_store=store,
            hitl_transport=run.transport,
            skill_binding=run.bindings,
            agent_binding=run.bindings,
            clock=_ticking_clock(),
            debt_binding=_PermissiveDebt(),
        ),
        run.transport,
        run.store,
        run.bindings,
        run.workflow,
    )

    rm.resume(recovering)

    as_built = _constructed(store, case)
    after = rm.state_of(run)
    _assert_state_carries(after, as_built, case)
    assert rm.requests(run, after.current_state) == [rm.the_request_a_suspension_files(run, after)], (
        f"[{case}] the restored request is not bound to the suspension record as built"
    )
