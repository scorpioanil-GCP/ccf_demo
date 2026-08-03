"""L5 — Context Projection (Π), the System of Interpretation.

Whitepaper §7.5; DESIGN.md §2B.2. Π is a typed transformation performing
subgraph *substitution*: its output is itself a valid context for the
principal, so it composes with the operator algebra as if it were the full
graph (INV-CH7-40). Construct once, interpret many.

Two modules: :mod:`ccf.projection.plan` declares the structural
``ProjectionPlan`` interface (dispatch by structural typing, never by
inheritance — INV-CH7-41), and :mod:`ccf.projection.engine` runs the two-stage
execution §7.5 separates — the operator plan settles the facts
(principal-agnostic, memoizable), the projection plan settles their
significance for one principal's decision (principal-conditioned), and neither
concern leaks into the other (INV-CH7-42).

Algorithmic package (CINV-03): the slice is Mode 1, pure algorithmic — no LLM
participates in projection here or anywhere else in I.1.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
