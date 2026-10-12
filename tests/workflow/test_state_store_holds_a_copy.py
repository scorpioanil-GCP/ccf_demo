# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The outcome, the trace artifact and the approval binding never carry what the state store held (``D-IMPL-380``, third round).

Dave, 2026-10-10 09:18 MST (the ``D-IMPL-380`` amendment, ruling 2 (a)), verbatim: *"Fix the wording and all three
writers. Do not treat the state store as trusted."* *"The workflow state store is not trusted because it is the
Control Plane. That is the same hole as the artifact store, one writer over."* And at 09:23 MST: *"The state-store
change is in the one function every state write uses, and the saved-bytes limit is written down."*

``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._write_state`` is the one function every Control Plane state
write passes through. At ``7d9d2898`` it handed the state store the engine's own ``WorkflowStateRecord``, whose
``trace`` holds the engine's own trace entries, and in every passage but ``_restore_request``, which writes the trace
first (from a record read back from the store), the state write comes before ``_write_trace``.
A state store that rewrote a trace entry inside ``put_if`` had its rewrite reach the trace artifact, the completed
outcome's ``step_sequence_block`` and the suspension's approval binding (builder probe
``delta-2/probes/test_probe_state_store_alias.py``; reproduced by the coordinator). The artifact store's copy (the
second round) runs only after the state store has already altered the shared entries.

The attacker: a state store whose ``put_if`` rewrites the first trace entry's ``target`` of every workflow-state
record it is handed (``object.__setattr__``; a trace entry is a frozen model) and then saves it. The artifact store is
honest. What the engine built is the saved record with the store's suffix removed, because the suffix is the only
thing the store changed; the test asserts that is what the engine hands on:

* **completed**: ``step_sequence_block`` is the canonical trace as built, and ``trace_artifact`` is that trace's
  reference;
* **suspended** and **exception-routed** (no step list, as ruled in answer 3): the trace artifact, fetched from the
  honest artifact store and re-hashed, is the trace as built;
* **suspended**: the pending approval request binds the content hash of the record as built.

The saved-bytes limit, state-store form, is what this does not test: the state store saves its altered copy, and a
later passage that reads the record back reads what it saved. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from http_api.composition_authority import deployment_store
from tests.workflow.capabilities import execute_as
from tests.workflow.test_engine import (  # noqa: F401 — `registry` is a pytest fixture, used by name
    _Bindings,
    _covenant,
    _PermissiveDebt,
    _refresh,
    _ticking_clock,
    registry,
)

SUFFIX = "-state-store-rewrite"

#: Each outcome that carries a trace reference: the workflow that reaches it, the failing step it needs, its type.
PATHS: dict[str, tuple[Callable[[ControlPlaneRegistry], Any], frozenset[str], type]] = {
    "completed": (_refresh, frozenset(), WorkflowCompleted),
    "suspended": (_covenant, frozenset(), WorkflowSuspended),
    "exception-routed": (_covenant, frozenset({"fetch-certificates"}), WorkflowExceptionRouted),
}


def _rewriting_state_store(monkeypatch: pytest.MonkeyPatch, registry: ControlPlaneRegistry) -> list[int]:
    """Make the registry's state store rewrite the first trace entry of every workflow-state record it is handed."""
    store = registry.state_store
    real = store.put_if
    rewrites: list[int] = []

    def put_if(authorized: Any, record_class: str, record: object, **kwargs: Any) -> int:
        trace = getattr(record, "trace", None)
        if record_class == WORKFLOW_STATE and trace and not trace[0].target.endswith(SUFFIX):
            object.__setattr__(trace[0], "target", f"{trace[0].target}{SUFFIX}")
            rewrites.append(1)
        return real(authorized, record_class, record, **kwargs)  # type: ignore[no-any-return]

    monkeypatch.setattr(store, "put_if", put_if)
    return rewrites


def _as_built(record: WorkflowStateRecord) -> WorkflowStateRecord:
    """The record the engine built: the saved record with the store's suffix removed from every trace target."""
    return record.model_copy(
        update={"trace": tuple(e.model_copy(update={"target": e.target.removesuffix(SUFFIX)}) for e in record.trace)}
    )


@pytest.mark.parametrize("path", sorted(PATHS))
def test_a_state_store_that_rewrites_the_trace_leaves_the_outcome_the_trace_artifact_and_the_binding_as_built(
    registry: ControlPlaneRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    build, failing, outcome_type = PATHS[path]
    rewrites = _rewriting_state_store(monkeypatch, registry)
    artifacts = deployment_store(tmp_path / "artifacts", workflow_traces=True)
    bindings = _Bindings(failing=failing)
    transport = InMemoryHitlTransport()
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=artifacts,
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
        debt_binding=_PermissiveDebt(),
    )
    workflow = build(registry)

    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))

    assert isinstance(outcome, outcome_type), f"[{path}] {type(outcome).__name__}: {outcome}"
    saved = registry.state_store.get(WORKFLOW_STATE, f"{workflow.definition.tenant}/exec-1")
    assert isinstance(saved, WorkflowStateRecord), f"[{path}] no state record: {saved!r}"
    assert rewrites and saved.trace[0].target.endswith(SUFFIX), (
        f"[{path}] the case was not constructed: the state store must have saved its rewrite"
    )
    as_built = _as_built(saved)
    trace_as_built = canonical_bytes(as_built.trace)

    # Every property is checked before any is asserted, so a red names each one that failed.
    problems: list[str] = []
    fetched = artifacts.get(content_address=outcome.trace_artifact.content_address)
    if SUFFIX.encode("utf-8") in fetched or fetched != trace_as_built:
        problems.append(f"the trace artifact is not the trace as built: {fetched.decode('utf-8')!r}")
    if content_hash(as_built.trace) != outcome.trace_artifact.content_address:
        problems.append("trace_artifact does not name the trace as built")
    if isinstance(outcome, WorkflowCompleted) and outcome.step_sequence_block.encode("utf-8") != trace_as_built:
        problems.append(f"step_sequence_block carries the state store's rewrite: {outcome.step_sequence_block!r}")
    if isinstance(outcome, WorkflowSuspended):
        bound = [e.product_content_hash for e in transport.pending(tenant=outcome.tenant) if e.event_key == outcome.event_key]
        if bound != [content_hash(as_built)]:
            problems.append(
                f"the approval request is not bound to the suspension record as built: {bound}"
                f" against {content_hash(as_built)} (the saved record hashes to {content_hash(saved)})"
            )
    assert not problems, f"[{path}] " + "; ".join(problems)
