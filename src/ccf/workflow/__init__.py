"""The Orchestration Layer's workflow contracts (CLAUDE.md §8.1 — SDK-defined).

Everything in this package is an **SDK extension beyond the whitepaper**: the
whitepaper assumes a control plane and a delivery surface but does not
specify multi-agent workflow primitives; the Workflow primitive is committed
by CLAUDE.md §8.1 and D-IMPL-17, and every public docstring here says so.

The load-bearing separation: **a workflow is a declared, versioned Control
Plane artifact — a routing wrapper over a pinned TaskDefinition — and the
factory is the only construction path to an executable handle** (§6.4;
ORCH-01). This package holds the wrapper contract, its syntactic validators,
and the ``WorkflowFactory`` with the registry-backed semantic layer — never
a workflow, and never an engine: execution is plan 07-06's scope, and the
engine accepts only handles this factory built.
"""

from __future__ import annotations

from ccf.workflow.definitions import (
    WORKFLOW_DEFINITION,
    WORKFLOW_FAILED_STATE,
    WorkflowDefinition,
    WorkflowTransition,
)
from ccf.workflow.factory import (
    Workflow,
    WorkflowConstructionError,
    WorkflowFactory,
    WorkflowIdentity,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "WORKFLOW_DEFINITION",
    "WORKFLOW_FAILED_STATE",
    "Workflow",
    "WorkflowConstructionError",
    "WorkflowDefinition",
    "WorkflowFactory",
    "WorkflowIdentity",
    "WorkflowTransition",
]
