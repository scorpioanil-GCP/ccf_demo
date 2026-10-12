# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Context Half-life (λ_c) and Context Debt (D_c) — the operational primitives.

Whitepaper §7.7. Two primitives carry the fabric's "what happens when context
is incomplete, stale, or internally inconsistent" story:

* :mod:`ccf.halflife.decay` — λ_c as *formal decay*, not a TTL. Decision
  relevance falls off a continuous curve; aged context stays reconstructible
  for replay while ceasing to count as current (INV-CH7-57).
* :mod:`ccf.halflife.debt` — D_c as the assembly-time shortfall between the
  coverage a decision requires and the coverage the fabric delivered, and the
  typed Forced-LLM / Fail-Closed signals an elevated D_c raises (INV-CH7-61
  through INV-CH7-65).

Both are pure mechanism. Every rate, multiplier, threshold and weight is
resolved from a versioned Control Plane artifact
(:mod:`ccf.controlplane.artifacts`); a value the deployment never declared is
an error, never a default (INV-CH7-58, D-IMPL-38). This package therefore holds
no half-life table and no threshold band of any kind (CLAUDE.md §11, CINV-01).
"""

from __future__ import annotations

__all__ = ["debt", "decay"]
