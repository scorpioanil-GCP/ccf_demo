"""P2 — the tenant on the write IS the capability's tenant (D-IMPL-353 §1.3).

FORK-SHAPED FIRST VERSION. Written against the pre-fix signatures so it
fails at the fork the way the finding fails: by SUCCEEDING — the caller
holds a capability for tenant ``beta-bank`` on ``acme-bank``'s workflow key,
and the execution is filed under ``acme-bank``. The assertions are the
property the fix must deliver; the calls are the fork's.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.workflow.state import WORKFLOW_STATE

from tests.workflow.capabilities import execute_capability
from tests.workflow.test_engine import (  # noqa: F401 — `registry` is the fixture
    _engine,
    _workflow_definition_document,
    registry,
)

ACME = "acme-bank"
BETA = "beta-bank"
ACME_KEY = "acme-bank/workflows/covenant-review"


def test_p2_a_capability_for_tenant_b_cannot_file_an_execution_under_a(
    registry: ControlPlaneRegistry, tmp_path: Path
) -> None:
    engine, transport, _ = _engine(registry, tmp_path)
    definition = _workflow_definition_document("workflows/covenant_review_workflow.yaml")
    version = registry.register_versioned(ACME_KEY, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    # The finding's premise: B's authorizer allowed workflow.invoke on A's key.
    authorized = execute_capability(tenant=BETA, resource=ACME_KEY)
    assert authorized.tenant == BETA and authorized.resource == ACME_KEY

    workflow = WorkflowFactory(control_plane=registry).construct(
        definition_key=authorized.resource, definition_version=version
    )
    asyncio.run(engine.execute(workflow, execution_id="exec-p2"))

    # The property: nothing under A, and nothing on A's HITL queue.
    assert registry.state_store.get(WORKFLOW_STATE, f"{ACME}/exec-p2") is None
    assert transport.pending(tenant=ACME) == ()
