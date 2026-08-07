"""Graph-tier seam and substrate tests (Phase 15.2).

Where the substrate-adapter phase pins the seams it generalizes: the typed
write seam (`_GraphTxn`), reader materialization, query contracts, and SQL
pushdown. Backend-parametrized *semantics* stay in ``tests/conformance``; this
package holds the seam-shape and confinement assertions that are about the
SDK's own structure rather than about any one backend.
"""
