"""The erasure door (SEC-009; `D-IMPL-374` (4); design `D-IMPL-367` §4.1).

Runtime because it drives the workflow engine; the contracts, the index and the
decorating store are :mod:`ccf.erasure`. Field-scoped erasure, the retention
lifecycle, pseudonymization and byte destruction are OUT (see :mod:`ccf.erasure`).
"""

from __future__ import annotations

from ccf_runtime.erasure.door import ErasureDoor, ErasureRefused, ErasureWorkflowUngated

__ccf_mode__ = "algorithmic"

__all__ = ["ErasureDoor", "ErasureRefused", "ErasureWorkflowUngated"]
