# Phase 15.2 — Deferred Items (live hand-off contract)

Maintained file: citations here are held true of the current tree by the
citation gate (`MAINTAINED_RECORDS` in `tools/lints/citations.py`). Amend in
place; inheriting plans and Phase 16 read this as authoritative.

## DI-15.2-01 — GQ-16 endpoint-closure wording needs a clarifying amendment

**Found during:** plan 15.2-05 (the seam opening).

**What:** `GQ-16` (docs/GRAPH_QUERY_SEMANTICS.md:316) states the
endpoint-closure half "holds for **every** answer", while `GQ-05`
(docs/GRAPH_QUERY_SEMANTICS.md:122) defines the degenerate answer as "the
tenant's full as-of view under `GQ-07`" and `GQ-21`
(docs/GRAPH_QUERY_SEMANTICS.md:446) pins that answer byte-identical to the
pre-seam `as_of()` — which never pruned a persisted edge whose endpoint
carries no entity claim (INV-CH7-20: edges are first-class, never derived
joins; pinned by
`tests/conformance/test_graphstore.py::test_relationships_are_first_class_with_their_own_lineage`).
Read literally together, the three clauses conflict on exactly one shape: a
dangling first-class edge in the degenerate answer.

**Resolution taken in 15.2-05:** the fallback applies endpoint closure to
**constrained** answers only — any predicate family present, or
`allowed_entities` non-`None` — because closure's own rationale is
exclusion (leak-by-absence of a *removed* node), and the degenerate
everything-question removes nothing. Rationale recorded in
`src/ccf/graph/fallback.py::_endpoint_closure`.

**Deferred:** a clarifying amendment to `GQ-16` under the `GQ-35`
amendment lane, stating the degenerate exemption explicitly so adapters
(plans 15.2-06/-12/-13) implement the same scoping from the prose rather
than from the fallback's docstring. Until amended, the differential suite
(byte-identity against the fallback) is the enforcement that keeps
adapters aligned on this shape — corpus should include a dangling-edge
degenerate query so the divergence is exercised, not assumed.
