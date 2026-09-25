"""The engine's trace is a derived write the deployment must declare (D-IMPL-353 §1.2; the join).

``WorkflowEngine._write_trace`` files a :class:`~ccf.artifacts.protocol.DerivedWrite`
of :data:`~ccf_runtime.workflow.engine.WORKFLOW_TRACE_ARTIFACT_CLASS` under the
``Execute`` / ``Resume`` capability that authorized the run. The store admits
that write only if the deployment declared the trace class under those kinds
in its :class:`~ccf.artifacts.protocol.WriteKinds`; a store that has not
treats the class as the client lane, and the engine's capability dies at the
store's ``verify_any`` on the FIRST trace write — fail closed, nothing filed,
no execution reported as run. What would fail here: an engine that fell back
to filing the trace some other way, or a store that admitted an undeclared
class under a mechanism kind.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import CapabilityBypassError, Execute, Resume
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import state_key
from ccf.hitl.transport import InMemoryHitlTransport
from ccf_runtime.workflow.engine import WORKFLOW_TRACE_ARTIFACT_CLASS, WorkflowEngine
from ccf_runtime.workflow.state import WORKFLOW_STATE
from http_api.composition_authority import (
    WORKFLOW_TRACE_CLASS,
    deployment_store,
    trace_write_kinds,
)
from tests.workflow.capabilities import execute_as
from tests.workflow.test_engine import _Bindings, _PermissiveDebt, _refresh, _ticking_clock, registry  # noqa: F401


def _engine(registry: ControlPlaneRegistry, store: FileArtifactStore) -> WorkflowEngine:
    bindings = _Bindings()
    return WorkflowEngine(
        control_plane=registry,
        artifact_store=store,
        hitl_transport=InMemoryHitlTransport(),
        skill_binding=bindings,
        agent_binding=bindings,
        clock=_ticking_clock(),
        debt_binding=_PermissiveDebt(),
    )


def test_the_helpers_spelling_of_the_trace_class_is_the_engines() -> None:
    assert WORKFLOW_TRACE_CLASS == WORKFLOW_TRACE_ARTIFACT_CLASS
    assert trace_write_kinds().for_class(WORKFLOW_TRACE_ARTIFACT_CLASS) == (Execute, Resume)


def test_a_store_that_does_not_declare_the_trace_class_fails_the_first_trace_write_closed(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    undeclared = FileArtifactStore(root=tmp_path / "undeclared", write_kinds=WriteKinds({}))
    engine = _engine(registry, undeclared)
    workflow = _refresh(registry)
    with pytest.raises(CapabilityBypassError, match="kind"):
        asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    # Nothing filed: no artifact under any address, no naming-index entry.
    assert [p for p in undeclared.root.iterdir() if len(p.name) == 64] == []
    assert undeclared.names_at(content_address="0" * 64) == ()


def test_the_same_run_over_a_declaring_store_files_the_trace_under_the_capabilitys_tenant(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    """The positive control, and the state key is the seam's derivation."""
    declared = deployment_store(tmp_path / "declared", workflow_traces=True)
    engine = _engine(registry, declared)
    workflow = _refresh(registry)
    outcome = asyncio.run(engine.execute(execute_as(workflow), workflow, execution_id="exec-1"))
    ref = outcome.trace_artifact
    assert ref.tenant_id == workflow.definition.tenant
    assert ref.artifact_class == WORKFLOW_TRACE_ARTIFACT_CLASS
    assert ref.name == "exec-1"
    (named,) = declared.names_at(content_address=ref.content_address)
    assert (named.tenant_id, named.artifact_class, named.name) == (
        workflow.definition.tenant,
        WORKFLOW_TRACE_ARTIFACT_CLASS,
        "exec-1",
    )
    key = state_key(tenant=workflow.definition.tenant, record_id="exec-1")
    assert registry.state_store.get(WORKFLOW_STATE, key) is not None
