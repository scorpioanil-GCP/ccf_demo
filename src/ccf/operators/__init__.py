"""L4 — Context Operators, the System of Computation.

Whitepaper §7.4 (the operator algebra and its four canonical categories);
DESIGN.md §2B.1. Operators are typed, pure, read-only, *sync* functions over
graph state (D-IMPL-04 keeps this path sync inside an async-first runtime), and
they compose under

    ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity

with ``∘`` read right-to-left, which is why the planner's dependency order runs
Policy → Similarity → Temporal → Traversal.

This package holds the operator contract (:mod:`ccf.operators.base`) and the
slice's one genuine operator per category (:mod:`ccf.operators.categories`).
The registry, parameterization surface, and the full composition-preservation
harness widen in the operator subsystem plan.

Algorithmic package (CINV-03): L4 computes, it never interprets.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
