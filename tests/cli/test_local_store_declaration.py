"""``--local`` declares what its own mechanism writes (D-IMPL-353 §1.2; the join).

The local fabric composes a workflow engine and no resolver, so its store
declares exactly the engine's trace class under ``Execute | Resume`` and
nothing else: a replay class it does not write would be a lane nothing here
holds a ``ReplayMint`` for, and the trace class undeclared would make the
first workflow run fail closed at the store. The mode is still suspended
(`SEC-002`); this is about the bundle it builds.
"""

from __future__ import annotations

from pathlib import Path

from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import Execute, Resume
from ccf_runtime.cli.local import build_local_dependencies
from ccf_runtime.workflow.engine import WORKFLOW_TRACE_ARTIFACT_CLASS
from tests.composition import declared_hitl_policy_key


def test_the_local_store_declares_the_trace_class_under_execute_and_resume(tmp_path: Path) -> None:
    store = build_local_dependencies(root=tmp_path, hitl_policy_key=declared_hitl_policy_key()).artifact_store
    kinds = getattr(store, "write_kinds", None)
    assert isinstance(kinds, WriteKinds)
    assert kinds.for_class(WORKFLOW_TRACE_ARTIFACT_CLASS) == (Execute, Resume)


def test_the_local_store_declares_nothing_it_does_not_write(tmp_path: Path) -> None:
    store = build_local_dependencies(root=tmp_path, hitl_policy_key=declared_hitl_policy_key()).artifact_store
    assert store.write_kinds.declared_classes == frozenset({WORKFLOW_TRACE_ARTIFACT_CLASS})


def test_the_engine_and_the_store_are_the_same_deployment(tmp_path: Path) -> None:
    bundle = build_local_dependencies(root=tmp_path, hitl_policy_key=declared_hitl_policy_key())
    assert bundle.workflow_engine is not None
    assert bundle.workflow_engine.artifact_store is bundle.artifact_store
