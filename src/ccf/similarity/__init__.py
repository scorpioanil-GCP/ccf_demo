"""The similarity substrate seam (L4's Similarity category).

Whitepaper §7.4 (Similarity operators rank over a *corpus*, with the index
version pinned in L); DESIGN.md §2B.1 and the D-IMPL-03 ruling (a
``SimilarityIndex`` Protocol with pluggable reference implementations, never a
vendor baked into the algebra).

This package holds the Protocol and the slice's deterministic in-memory
reference index. The sqlite-vec and Chroma implementations arrive with their
own subsystem plan (04-11) against the same Protocol.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
