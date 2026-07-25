"""L2 — Context Assembly, and the fabric's sole writer to L3.

Whitepaper §7.1/§7.3; DESIGN.md §2A.3. Assembly is where four concerns
converge (INV-CH7-03): semantic resolution, temporal stitching, policy
binding, and operator invocation. It is also the one component the composition
root constructs with a ``GraphWriter`` (D-IMPL-41) — every other layer of the
SDK reads.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
