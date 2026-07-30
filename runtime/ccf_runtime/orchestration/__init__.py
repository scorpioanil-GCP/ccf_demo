"""Orchestrator driver integrations — D-IMPL-60's module tree.

Each SDK's `OrchestrationProtocol` driver lives under
``ccf_runtime/orchestration/<sdk>/`` — **never** under
``ccf_runtime/adapters/<sdk>/``. The separate module tree is the structural
enforcement of D-IMPL-17's two-seam distinction (an SDK as *agent harness*
vs the same SDK as *orchestrator of CCF workflows*): the D-06 lint
(``tools/lints/orchestration_imports.py``) bans imports bidirectionally
between this tree and the adapters tree, so promoting an adapter's private
topology into a driver — advisory A7's failure mode — is structurally
unrepresentable rather than merely documented.

The in-SDK reference adapter over :class:`~ccf_runtime.workflow.engine.
WorkflowEngine` (:mod:`ccf_runtime.orchestration.reference`) is the
conformance suite's reference leg, per the Protocol module's doctrine
sentence.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
