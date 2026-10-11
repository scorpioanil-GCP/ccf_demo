# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The workflow engine hands out only the reference of the execution trace it wrote (``D-IMPL-378`` decision 5 (a)).

Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation on the "j" batch's decision 5, verbatim: *"(a) Fix
the four writers in one small lane."* Decision 5 (a) itself (06:06 MST, confirmed at 06:21 MST), verbatim:
*"Verify the returned record address against the record actually written."* It was built for
``src/ccf/replay/serve.py::ReplayWriter.write_replay_record``; this module holds its neighbor, the engine's trace
write-through in ``runtime/ccf_runtime/workflow/engine.py::WorkflowEngine``, to the same rule.

At suspension, at an exception route and at a terminal, the engine files the execution's trace on the artifact
store (``D-IMPL-18``) and hands the reference the store answered to its caller as the outcome's
``trace_artifact``. The engine handed that answer out unchecked. The small lane found it by reading the code; this
module measures it on ``dl-378-integ`` @ ``6cd6023e``: a store that filed the second execution's trace faithfully
and answered with the first execution's trace reference had the second execution's outcome carry the first
execution's trace reference, on each of the three outcomes that carry one.

What the engine knows before the store answers (``D-IMPL-26``): the trace's address is the content hash of the
trace, its name is the execution id, the tenant is the capability's that authorized the run, the class is
``ccf.workflow-trace``, and the URI is ``ccf-artifact://{tenant}/{class}/{execution id}@{address}``.

What is asserted, by mechanism:

1. **The hole as evidenced.** On each outcome that carries a trace reference (suspended, exception-routed,
   completed), a store answering another execution's genuine trace reference is refused by name
   (``WorkflowTraceReferenceMismatch``), and no outcome is returned.
2. **Every field of the reference.** One field of the trace's reference answered as another trace's (the address,
   the URI, the name) or as another tenant's or class's is refused by name; so is a changed field carried in a
   ``str`` subclass that claims to equal the trace's own.
3. **Control.** An honest store's reference is handed out on each of the three outcomes, and it is the trace's own.

The refusal is asserted by its class NAME as a string, so a tree without the check fails each test on its
behavior (the reference handed out), never on an import. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol, artifact_uri
from ccf.contracts.canonical import content_hash
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
from tests.workflow.capabilities import execute_as
from tests.workflow.test_engine import (  # noqa: F401 — `registry` is a pytest fixture, used by name
    _Bindings,
    _covenant,
    _PermissiveDebt,
    _refresh,
    _ticking_clock,
    registry,
)

#: The refusal this check raises, by name (absent on a tree without the check).
REFUSAL = "WorkflowTraceReferenceMismatch"

#: The one field each lying store changes, and the foreign value it answers with.
#: ``None`` means "the other trace's value for that field".
FIELDS: dict[str, str | None] = {
    "content_address": None,
    "uri": None,
    "name": None,
    "tenant_id": "another-tenant",
    "artifact_class": "another-trace-class",
}

#: Each outcome that carries a trace reference: the workflow that reaches it, the failing step it needs, its type.
PATHS: dict[str, tuple[Callable[[ControlPlaneRegistry], Any], frozenset[str], type]] = {
    "completed": (_refresh, frozenset(), WorkflowCompleted),
    "suspended": (_covenant, frozenset(), WorkflowSuspended),
    "exception-routed": (_covenant, frozenset({"fetch-certificates"}), WorkflowExceptionRouted),
}


class _Answers:
    """A store that files every write faithfully through ``inner`` and answers with ``answer(the honest ref)``.

    ``answer`` is ``None`` until a test sets it, so one engine can run an honest execution first. A buggy or hostile
    artifact server whose bytes are right and whose reference is not; reads delegate unchanged. The engine's only
    write to this store is the trace.
    """

    def __init__(self, inner: ArtifactStoreProtocol) -> None:
        self._inner = inner
        self.answer: Callable[[ArtifactRef], ArtifactRef] | None = None
        self.filed: list[ArtifactRef] = []

    def put(self, authorized: Any, artifact: Any) -> ArtifactRef:
        honest = self._inner.put(authorized, artifact)
        self.filed.append(honest)
        return honest if self.answer is None else self.answer(honest)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _ClaimsEquality(str):
    """A ``str`` whose equality answers for itself: equal to anything, unequal to nothing."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


def _engine(registry: ControlPlaneRegistry, tmp_path: Path, *, failing: frozenset[str]) -> tuple[WorkflowEngine, _Answers]:
    store = _Answers(deployment_store(tmp_path / "artifacts", workflow_traces=True))
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
    return engine, store


def _run(engine: WorkflowEngine, workflow: Any, execution_id: str) -> Any:
    """The outcome of executing ``workflow``, or the exception raised instead."""
    try:
        return asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id=execution_id))
    except Exception as raised:  # noqa: BLE001 — judged by its type's name below, never by its text
        return raised


def _own_ref(registry: ControlPlaneRegistry, workflow: Any, execution_id: str, filed: ArtifactRef) -> ArtifactRef:
    """The trace's own reference, from the execution's persisted trace — the case's construction check."""
    tenant = workflow.definition.tenant
    record = registry.state_store.get(WORKFLOW_STATE, f"{tenant}/{execution_id}")
    assert isinstance(record, WorkflowStateRecord), "the case was not constructed: the execution must have a record"
    address = content_hash(record.trace)
    own = ArtifactRef(
        content_address=address,
        uri=artifact_uri(
            tenant_id=tenant,
            artifact_class=WORKFLOW_TRACE_ARTIFACT_CLASS,
            name=execution_id,
            artifact_version=address,
        ),
        tenant_id=tenant,
        artifact_class=WORKFLOW_TRACE_ARTIFACT_CLASS,
        name=execution_id,
    )
    assert filed == own, "the case was not constructed: the store must have filed the trace under its own reference"
    return own


def _not_own(handed: object, own: ArtifactRef) -> list[str]:
    """The fields of ``handed`` that are not, as exact strings, ``own``'s (the test's own reading, type first)."""
    return [
        field
        for field in ArtifactRef.model_fields
        if not (type(getattr(handed, field, None)) is str and getattr(handed, field) == getattr(own, field))
    ]


def _assert_refused_by_name(outcome: Any, *, own: ArtifactRef, case: str) -> None:
    """No outcome was returned, and the refusal is the check's own, by its type's name."""
    if not isinstance(outcome, Exception):
        handed = getattr(outcome, "trace_artifact", None)
        pytest.fail(
            f"[{case}] the engine returned {type(outcome).__name__} carrying, unchecked, a trace reference whose"
            f" {_not_own(handed, own)} are not the trace's own (the trace at {own.content_address} named"
            f" {own.name}): {handed!r}"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"[{case}] refused, but not by the returned-reference check ({REFUSAL}): {type(outcome).__name__}: {outcome}"
    )


# --- 1. the hole as evidenced: another execution's trace reference, on each outcome ------------


@pytest.mark.parametrize("path", sorted(PATHS))
def test_a_store_answering_another_executions_trace_reference_is_refused_by_name(
    registry: ControlPlaneRegistry, tmp_path: Path, path: str
) -> None:
    """The first execution runs honestly; the second execution's trace write is answered with the first's reference.

    Measured on ``6cd6023e``: the second execution's outcome carried the first execution's trace reference.
    """
    build, failing, outcome_type = PATHS[path]
    engine, store = _engine(registry, tmp_path, failing=failing)
    workflow = build(registry)
    first = _run(engine, workflow, "exec-1")
    assert isinstance(first, outcome_type), f"the case was not constructed: the honest run must reach {path}: {first}"
    first_ref = store.filed[-1]
    store.answer = lambda _honest: first_ref

    outcome = _run(engine, workflow, "exec-2")

    assert len(store.filed) == 2 and store.filed[-1].name == "exec-2", (
        "the case was not constructed: the store must have filed the second execution's trace"
    )
    _assert_refused_by_name(
        outcome, own=_own_ref(registry, workflow, "exec-2", store.filed[-1]), case=f"{path}, another execution's trace"
    )


# --- 2. every field of the returned reference (the completed outcome) ---------------------------


def _foreign_trace_ref(tenant: str) -> ArtifactRef:
    """The reference another execution's trace would have: an empty trace, named for another execution."""
    address = content_hash(())
    return ArtifactRef(
        content_address=address,
        uri=artifact_uri(
            tenant_id=tenant, artifact_class=WORKFLOW_TRACE_ARTIFACT_CLASS, name="another-exec", artifact_version=address
        ),
        tenant_id=tenant,
        artifact_class=WORKFLOW_TRACE_ARTIFACT_CLASS,
        name="another-exec",
    )


def _one_field_changed(field: str, *, foreign: ArtifactRef) -> Callable[[ArtifactRef], ArtifactRef]:
    value = FIELDS[field]
    replacement = getattr(foreign, field) if value is None else value
    return lambda honest: honest.model_copy(update={field: replacement})


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_with_any_field_not_the_traces_own_is_refused_by_name(
    registry: ControlPlaneRegistry, tmp_path: Path, field: str
) -> None:
    """One field of the trace's reference answered as another trace's (or another tenant's, or class's)."""
    engine, store = _engine(registry, tmp_path, failing=frozenset())
    workflow = _refresh(registry)
    store.answer = _one_field_changed(field, foreign=_foreign_trace_ref(workflow.definition.tenant))

    outcome = _run(engine, workflow, "exec-1")

    assert len(store.filed) == 1, "the case was not constructed: the store must have filed the trace"
    _assert_refused_by_name(outcome, own=_own_ref(registry, workflow, "exec-1", store.filed[0]), case=f"one field, {field}")


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_field_that_only_claims_equality_is_refused_by_name(
    registry: ControlPlaneRegistry, tmp_path: Path, field: str
) -> None:
    """Another trace's value in one field, carried in a ``str`` subclass that says it equals the trace's own.

    The comparison reads the type first, so the claim is not taken: the field differs, and the engine refuses by name
    rather than handing anything out.
    """
    engine, store = _engine(registry, tmp_path, failing=frozenset())
    workflow = _refresh(registry)
    value = FIELDS[field]
    disguised = _ClaimsEquality(
        getattr(_foreign_trace_ref(workflow.definition.tenant), field) if value is None else value
    )
    store.answer = lambda honest: honest.model_construct(**{**dict(honest), field: disguised})

    outcome = _run(engine, workflow, "exec-1")

    assert disguised == getattr(store.filed[0], field), "the case was not constructed: the value must claim equality"
    _assert_refused_by_name(
        outcome, own=_own_ref(registry, workflow, "exec-1", store.filed[0]), case=f"claimed equality, {field}"
    )


# --- 3. control -------------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(PATHS))
def test_control_an_honest_stores_trace_reference_is_handed_out_and_is_the_traces_own(
    registry: ControlPlaneRegistry, tmp_path: Path, path: str
) -> None:
    """The deployment's file store answers exactly the trace's own reference, and the outcome carries it."""
    build, failing, outcome_type = PATHS[path]
    engine, store = _engine(registry, tmp_path, failing=failing)
    workflow = build(registry)
    outcome = _run(engine, workflow, "exec-1")
    assert isinstance(outcome, outcome_type), outcome
    own = _own_ref(registry, workflow, "exec-1", store.filed[-1])
    assert outcome.trace_artifact == own, outcome.trace_artifact
    assert store.resolve_uri(uri=own.uri) == own.content_address
