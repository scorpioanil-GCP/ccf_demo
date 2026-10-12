# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Artifact persistence — the ArtifactStore seam (SDK-defined).

CLAUDE.md §7.4 (the ArtifactStore Protocol and its constraints); DESIGN.md
§8.4 and §2B.5; D-IMPL-26 (addressing) and D-IMPL-27 (substrate split). The
whitepaper commits to replay against exact prior state; *where* those artifacts
live is an SDK concern, and this package is where the SDK declines to answer it
on the user's behalf.

Two things ship in I.1 per D-12: the Protocol and a file-backed development
implementation. The MCP-backed reference store is Phase 6 (I.3) and is
deliberately not scaffolded here — an empty module named for it would be a
promise the seam has not been asked to keep yet.

**The store is never a second writer.** It is a persistence substrate reached
through L2 and Control Plane mechanism. Nothing enters the Context Graph
except through L2, including artifacts retrieved from the store (CLAUDE.md
§7.4, §10). There is no store→L3 edge here, and no way to construct one: this
package imports nothing from :mod:`ccf.graph`.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
