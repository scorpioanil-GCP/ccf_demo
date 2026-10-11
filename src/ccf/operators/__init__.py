# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""L4 — Context Operators, the System of Computation.

Whitepaper §7.4 (the operator algebra and its four canonical categories);
DESIGN.md §2B.1. Operators are typed, pure, read-only, *sync* functions over
graph state (D-IMPL-04 keeps this path sync inside an async-first runtime), and
they compose under

    ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity

with ``∘`` read right-to-left, which is why the planner's dependency order runs
Policy → Similarity → Temporal → Traversal.

The package is five modules, split along the mechanism/values line:

:mod:`ccf.operators.base`
    The operator contract, the canonical categories, and the provenance
    sub-chain every invocation contributes.
:mod:`ccf.operators.params`
    The declared parameter contracts — schema only, never a value, never a
    default (D-IMPL-38).
:mod:`ccf.operators.categories`
    One genuine operator per canonical category.
:mod:`ccf.operators.registry`
    What a fabric may run, under what key, category, parameter schema, and
    version (INV-CH7-29, D-IMPL-37).
:mod:`ccf.operators.planner`
    Declared keys in, totally-ordered plan out; the per-execution intermediate
    memo (D-IMPL-36); and :func:`~ccf.operators.planner.compose`, the composite
    ``A∘B`` the composition-preservation property asserts against.

Algorithmic package (CINV-03): L4 computes, it never interprets.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
