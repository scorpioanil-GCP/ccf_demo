# Phase 15.2 — Deferred Items (live hand-off contract)

Maintained file: citations here are held true of the current tree by the
citation gate (`MAINTAINED_RECORDS` in `tools/lints/citations.py`). Amend in
place; inheriting plans and Phase 16 read this as authoritative.

## DI-15.2-01 — GQ-16 endpoint-closure wording needs a clarifying amendment — **CLOSED at 15.2-14**

**Closed 2026-08-08 by plan 15.2-14 (the phase-close audit).** The `GQ-35`-lane
amendment was written: `GQ-16`'s endpoint-closure half now reads "every
**constrained** answer" with the degenerate exemption stated normatively, the
semantics lane moved 1.0.0 → 1.0.1, and the amendment history under `GQ-35`
records what changed, why it was needed, and that it is clarifying rather than
behavioral. `ccf.graph.fallback::_endpoint_closure` now cites the prose for the
scoping instead of arguing for it, and the module docstring names 1.0.1.

**Why it was fixed rather than carried.** SUBQ-01 requires the prose to decide
every named edge semantic "with no implementation-defined escape hatches". Until
the amendment, this one shape was decided by the reference implementation's
docstring — the escape hatch, in the requirement's own words — so SUBQ-01 could
not be flipped truthfully with it open. Nothing in the tree changed: `make ci`
is green with zero test-body edits, and the differential corpus continues to
enforce the shape on every param.

**Amendment discipline note for future amenders:** the amendment was written to
be *line-number-neutral*. The `GQ-16` replacement paragraph is the same four
lines it replaced and the history was appended after `GQ-35`, because the
anchored cite02 citations across `/src` and `/tests` carry line numbers into
this document — a first, naive draft that inserted lines near the top produced
**124 citation-guard findings** in one edit. That discipline is now stated in
the amendment-history preamble of the document itself.

*Original entry, preserved unedited:*

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

## DI-15.2-02 — memory backend not yet a param of the graphstore six-semantics suite — **CLOSED at 15.2-14**

**Closed 2026-08-08 by plan 15.2-14 (the phase-close audit — the fallback owner
this entry named).** `tests/conformance/test_graphstore.py`'s `graph_backend`
fixture now parametrizes over **all five backends**: `sqlite` and `memory`
always-on, `postgres`/`neo4j`/`mongo` each carrying its container mark. The
entry predicted "no test body should need changes" and that held exactly — the
fixture body and the param list are the whole diff.

Closed wider than the entry asked. It named `memory` only, because neo4j and
mongo did not exist when it was written; both landed since (plans 15.2-12/-13)
carrying the same indirect-coverage gap, so all three were added rather than
leaving two-thirds of the gap open under a closed entry.

**Evidence:** six D-IMPL-34 semantics × 5 backends —
`-m "not postgres and not neo4j and not mongo"` 24 passed;
`-m postgres` 12 passed (PostgreSQL 16.14); `-m neo4j` 12 passed (Neo4j Kernel
5.26.29 community); `-m mongo` 12 passed (MongoDB 7.0.39).

**Why it mattered at this gate:** SUBQ-11 claims the typed write seam preserves
single-writer "for all five backends". Before this change the suite that *owns*
those write semantics asserted them against two of the five, and the other three
were covered only by neighbouring suites. The claim is now asserted by the suite
that makes it, not inferred.

*Original entry, preserved unedited:*

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

**15.2-14 routing (2026-08-08): ESCALATED to Dave, deliberately not decided
by the executor.** The audit routed the other two deferred items itself
(DI-15.2-01 by amending the prose it was about, DI-15.2-02 by adding the
fixture params it asked for) and stops here, because the two options are not
equivalent in kind:

- **Option (a) — contract-tier UTC normalization at claim construction.**
  Closes the corner for every adapter at once and is the tidiest answer to
  "why do two renderings of the same instant exist at all". But normalizing a
  claim's datetime at construction changes that claim's canonical bytes, and
  canonical bytes are the content identity the graph's idempotent upsert, the
  lineage set-union, and every replay content-address depend on. An
  offset-authored claim would hash differently before and after the change:
  that is a **replay-compatibility decision**, and the D-IMPL-89 byte-fidelity
  ruling this phase just built on exists precisely because re-deriving a
  historical address from a changed rendering breaks verification. Not an
  executor's call.
- **Option (b) — a corpus case plus a documented alignment rule.** Cheap,
  contained, and makes the divergence exercised rather than latent. But it
  documents a known fallback/adapter disagreement as acceptable, which is a
  deliberate softening of `GQ-31` byte-identity — the phase's central
  conformance claim. Also not an executor's call to make silently.

**Risk posture while open (this is why carrying it is safe):** the divergence
direction is **exclusion**, never inclusion. A non-``Z``-rendered claim is
dropped from a pushed ``require_valid_at_boundary`` answer where the fallback
would have kept it. No principal sees anything they should not; the
T-15.2-03/-26 information-disclosure posture is strictly preserved. The corner
also requires an offset-authored claim datetime, which nothing in the SDK, the
examples, or the fixtures produces — every in-repo path renders ``Z``.

**ESCALATED as `D-IMPL-90` (OPEN) in `docs/DECISIONS.md`, 2026-08-08.** The
§3.1 cross-AI self-review returned this corner as a **BLOCKING** finding —
correctly, and on a sharper reading than the one above: `GQ-31` is
byte-identity, not "no over-disclosure", so a known-diverging shape is a
counterexample to the phase's central conformance clause regardless of which
direction it errs in.

**The audit measured the corner rather than restating it, and the measurement
changes the analysis.** Probe on one `EntityClaim` with
`valid_from = 2026-03-01T08:00:00+05:00`:

| Lane | Rendering | Normalized? |
|---|---|---|
| `model_dump(mode="json")` — what `_writer.py` persists into `claim_json` | `2026-03-01T08:00:00+05:00` | **no** |
| `canonical_bytes(claim)` — what `content_hash` and every answer use | `2026-03-01T03:00:00.000000Z` | **yes** |

**Option (a) does NOT move content hashes.** Both this entry's original text
and the reviewer assumed it would. Claim identity is
`content_hash(_entity_content_key(claim))`, which passes the `datetime` value
through `canonical_bytes` — already UTC-normalized. The identity lane and the
payload lane are independent, and only the payload lane keeps the offset. That
removes the objection that made (a) look like a replay-compatibility break,
and it is why the escalation carries a recommendation rather than a shrug.

Full option/consequence record, and the reason this is an entry rather than a
fix, are in the `D-IMPL-90` entry. Named for Dave in `15.2-14-SUMMARY.md`
under "Questions for Dave" as the gating decision of the D-GATE-15.2 package.
