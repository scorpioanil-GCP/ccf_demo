# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The workflow engine derives its trace's reference BEFORE the store holds the trace (``D-IMPL-380``, ruling 1 (a)).

Dave, 2026-10-10 05:34 MST (the ``D-IMPL-380`` amendment), verbatim: *"Hash before put in both writers. Compare the
store's answer to that precomputed reference. Do not hash the object again after the store has held it. The test
mutates the dictionary and forces a change into the frozen record. The save is refused, and no audit entry is
written."*

``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._write_trace`` handed the trace to the store and only
afterwards derived the trace's content address from it, so a store that changed the trace while it held it, filed
the changed trace and answered the changed trace's genuine reference passed the field-by-field check
(``D-IMPL-378`` decision 5). The trace's entries are frozen Pydantic models, but ``object.__setattr__`` bypasses
that guard, and an in-process store can call it.

The attacker: a store that rewrites a field of the trace's first entry with ``object.__setattr__`` inside ``put``,
files the rewritten trace through the deployment's real store, and answers honestly for what it filed. On each
outcome that carries a trace reference, the execution is refused ``WorkflowTraceReferenceMismatch`` (asserted by the
class NAME, so a tree without the ordering fails on its behavior, never on an import), and no outcome — and so no
``trace_artifact`` — is returned. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import WorkflowCompleted, WorkflowEngine, WorkflowExceptionRouted, WorkflowSuspended
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

#: The refusal the precomputed reference raises, by name.
REFUSAL = "WorkflowTraceReferenceMismatch"

#: Each outcome that carries a trace reference: the workflow that reaches it, the failing step it needs, its type.
PATHS: dict[str, tuple[Callable[[ControlPlaneRegistry], Any], frozenset[str], type]] = {
    "completed": (_refresh, frozenset(), WorkflowCompleted),
    "suspended": (_covenant, frozenset(), WorkflowSuspended),
    "exception-routed": (_covenant, frozenset({"fetch-certificates"}), WorkflowExceptionRouted),
}


class _RewritesWhileHeld:
    """Rewrites the first entry of the trace it is handed, files the rewritten trace, answers what it filed."""

    def __init__(self, inner: ArtifactStoreProtocol) -> None:
        self._inner = inner
        self.as_built: str | None = None
        self.as_rewritten: str | None = None

    def put(self, authorized: Any, artifact: Any) -> Any:
        trace = artifact.artifact
        if self.as_built is None and isinstance(trace, tuple) and trace:
            self.as_built = content_hash(trace)
            object.__setattr__(trace[0], "target", f"{trace[0].target}-laundered")
            self.as_rewritten = content_hash(trace)
        return self._inner.put(authorized, artifact)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.mark.parametrize("path", sorted(PATHS))
def test_a_store_that_rewrites_the_trace_while_it_holds_it_is_refused_and_no_trace_reference_is_handed_out(
    registry: ControlPlaneRegistry, tmp_path: Path, path: str
) -> None:
    build, failing, _outcome_type = PATHS[path]
    store = _RewritesWhileHeld(deployment_store(tmp_path / "artifacts", workflow_traces=True))
    bindings = _Bindings(failing=failing)
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=store,
        hitl_transport=InMemoryHitlTransport(),
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
        debt_binding=_PermissiveDebt(),
    )
    workflow = build(registry)

    outcome: Any
    try:
        outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    except Exception as raised:  # noqa: BLE001 — judged by its type's name below, never by its text
        outcome = raised

    assert store.as_built is not None and store.as_built != store.as_rewritten, (
        f"[{path}] the case was not constructed: the store must have changed the trace's address"
    )
    if not isinstance(outcome, Exception):
        handed = getattr(outcome, "trace_artifact", None)
        pytest.fail(
            f"[{path}] the engine returned {type(outcome).__name__} carrying trace_artifact"
            f" {getattr(handed, 'content_address', None)} for the trace the store rewrote; the trace as the engine"
            f" built it is {store.as_built}, as the store rewrote it {store.as_rewritten}"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"[{path}] not refused by the precomputed reference ({REFUSAL}): {type(outcome).__name__}: {outcome}"
    )
