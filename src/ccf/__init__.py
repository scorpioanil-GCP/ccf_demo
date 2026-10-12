# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""CCF SDK library package — the L1–L6 Context Fabric.

SDK packaging root. Contains no logic: subsystem modules (signal, assembly,
graph, operators, projection, products, halflife, replay, controlplane,
artifacts, similarity, boot) land in their own plans.

Layering per CLAUDE.md §10 (L1 Signal … L6 Context Products) and
`docs/CCF_Whitepaper_1-2.md` §7.1. Zero harness imports are permitted anywhere
under this package (CLAUDE.md §7.3, CINV-02).
"""

__all__: list[str] = []
