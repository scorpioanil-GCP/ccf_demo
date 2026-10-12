# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The similarity substrate seam (L4's Similarity category).

Whitepaper §7.4 (Similarity operators rank over a *corpus*, with the index
version pinned in L); DESIGN.md §2B.1 and the D-IMPL-03 ruling (a
``SimilarityIndex`` Protocol with pluggable reference implementations, never a
vendor baked into the algebra).

This package holds the read-only and mutable Protocols
(:mod:`ccf.similarity.protocol`), the text-to-vector seam
(:mod:`ccf.similarity.embedder`, D-IMPL-07), and three implementations behind
them: the deterministic in-memory ``TokenOverlapIndex``, ``SqliteVecIndex`` on
sqlite-vec (the dev default, D-IMPL-03), and ``ChromaIndex`` (D-13), which is
importable only when the optional ``chroma`` extra is installed. All three pass
the same conformance suite (D-16, ``tests/conformance/test_similarity_index.py``).

Nothing above this package names a backend: the Similarity operator is typed
against ``SimilarityIndexProtocol``, so which index a deployment ranks against
is deployment configuration all the way down.

The package module is algorithmic (CINV-03); the modules that invoke an
embedder are not, and say so in their own docstrings.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
