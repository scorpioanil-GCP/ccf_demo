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

**15.2-06 status:** the corpus now includes the dangling-edge shape
(`tests/conformance/query_corpus.py::orphan_cases` — degenerate plus
constrained questions over an edge whose endpoints carry no entity claim),
so the divergence is exercised differentially on every registered param.
The `GQ-35`-lane prose amendment itself remains open.

## DI-15.2-02 — memory backend not yet a param of the graphstore six-semantics suite

**Found during:** plan 15.2-06 (the memory backend + differential suite).

**What:** `tests/conformance/test_graphstore.py` parametrizes the D-IMPL-34
six-semantics suite over sqlite + postgres. The new memory backend passes
its write semantics indirectly (the differential corpus writes through
booted L2, and `tests/graph/test_memory_backend.py` pins boot, idempotent
re-arrival, and two-instances-two-graphs), but the memory backend is not a
`graph_backend` fixture param, so the six semantics are not asserted
against it by the suite that owns them. Out of 15.2-06's declared file set;
the natural home is the plan that next touches the graphstore fixture
(the neo4j/mongo adapter plans extend the same param list).

**Deferred to:** plans 15.2-12/-13 (or the phase-close audit) — add
`pytest.param("memory")` beside sqlite in the `graph_backend` fixture; no
test body should need changes.

## DI-15.2-03 — non-UTC claim timestamps are fail-closed under the pushed validity predicate

**Found during:** plan 15.2-09 (SQL pushdown).

**What:** Claim JSON persists datetimes via the pydantic ``mode="json"``
rendering, which preserves a non-UTC offset (``+05:00``) instead of
normalizing to the canonical ``Z`` form — the contract tier accepts any
aware datetime and nothing in L2 re-renders it. The pushed validity
predicate (`GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185) compares
canonical UTC text, so both backends width-normalize the two ``Z`` forms
(`src/ccf/graph/backends/sqlite.py::_utc_fixed_width`,
`src/ccf/graph/backends/postgres.py::_utc_fixed_width`) and render any
non-``Z`` form as NULL — such a record is EXCLUDED from a
``require_valid_at_boundary`` answer, where the fallback (comparing
datetime values) would include it. Fail-closed, never over-disclosing:
the divergence direction is exclusion, so the T-15.2-03/-26
information-disclosure posture is preserved — but byte-identity
(`GQ-31` at docs/GRAPH_QUERY_SEMANTICS.md:573) has a latent corner the
UTC-only differential corpus cannot exercise.

**Deferred to:** the phase-close audit (15.2-14) to route: either a
contract-tier UTC normalization of claim datetimes at construction (which
closes the corner for every adapter at once and matches the canonical
serializer's existing ``astimezone(UTC)`` discipline), or a corpus case
authoring an offset-bearing claim plus a documented fallback-alignment
rule. Until routed, the fail-closed posture is documented in both
``_utc_fixed_width`` docstrings.
