# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Graph-tier seam and substrate tests (Phase 15.2).

Where the substrate-adapter phase pins the seams it generalizes: the typed
write seam (`_GraphTxn`), reader materialization, query contracts, and SQL
pushdown. Backend-parametrized *semantics* stay in ``tests/conformance``; this
package holds the seam-shape and confinement assertions that are about the
SDK's own structure rather than about any one backend.
"""
