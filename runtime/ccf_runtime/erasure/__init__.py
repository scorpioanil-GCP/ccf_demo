# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The erasure door (SEC-009; `D-IMPL-374` (4); design `D-IMPL-367` §4.1).

Runtime because it drives the workflow engine; the contracts, the index and the
decorating store are :mod:`ccf.erasure`. Field-scoped erasure, the retention
lifecycle, pseudonymization and byte destruction are OUT (see :mod:`ccf.erasure`).
"""

from __future__ import annotations

from ccf_runtime.erasure.door import ErasureDoor, ErasureRefused, ErasureWorkflowUngated

__ccf_mode__ = "algorithmic"

__all__ = ["ErasureDoor", "ErasureRefused", "ErasureWorkflowUngated"]
