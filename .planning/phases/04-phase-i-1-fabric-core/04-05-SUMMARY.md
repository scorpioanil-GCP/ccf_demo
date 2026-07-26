---
phase: 04-phase-i-1-fabric-core
plan: 05
subsystem: slice-l4-l6-replay-artifacts
tags: [l4, l5, l6, operators, projection, product-gates, replay, artifact-store, vertical-slice]
requires:
  - 04-01 (packaging, pytest/mypy config, CI)
  - 04-02 (CINV-01/02/03 lints)
  - 04-03 (CCFContract, canonical_bytes/content_hash, claims, SignalEnvelope, ControlPlaneRegistry)
  - 04-04 (GraphReader/GraphView, SQLite backend, AssemblyWorker, boot composition root)
provides:
  - operator contract (pure view→view, explicit temporal_boundary, provenance sub-chain) + one genuine operator per canonical category
  - SimilarityIndexProtocol (D-IMPL-03 seam) with a deterministic integer-scored reference index
  - ProjectionPlan structural Protocol + two-stage ProjectionEngine + OperatorRegistry with fail-fast duplicates
  - ContextProductContract, product-class registration requiring Control-Plane MAX_TTL, and the three-gate sequence as the only construction path of a servable product
  - DecisionReplayRecord (five dimensions, logical snapshot) and serve() whose replay append returns the delivery capability
  - ArtifactStoreProtocol + FileArtifactStore (sha256 content-addressed, write-once)
  - the banking fixture set and the proto-quickstart end-to-end slice test
affects:
  - the operator subsystem plan widens the registry/parameter surface against this contract; composition-preservation tests attach to the same pure view→view shape
  - the λ_c/D_c plan supplies the TTL derivation that currently arrives as a fixture-declared product TTL
  - the Postgres wave changes nothing here — operators read a GraphView, not a backend
  - I.2 extends replay dimension 4 (agent version, skill-set) and I.4 extends dimension 2 (HITL) additively; the record shape was designed to be extended, not replaced
  - the MCP-backed ArtifactStore (I.3) implements ArtifactStoreProtocol; nothing above it changes
tech-stack:
  added:
    - PyYAML for fixture loading (already a project dependency; first use)
  patterns:
    - operators are pure functions from an immutable GraphView to an immutable GraphView, so composition can be asserted bit-for-bit with no state underneath to diverge
    - capability-returning writes — the successful replay append returns the object that can deliver, so the ordering invariant has no skippable branch
    - module-private construction tokens for both ServableProduct and DeliveryCapability, mirroring the single-writer boot token
    - integer-percent similarity scores, because the canonical serializer refuses floats
key-files:
  created:
    - src/ccf/operators/__init__.py
    - src/ccf/operators/base.py
    - src/ccf/operators/categories.py
    - src/ccf/similarity/__init__.py
    - src/ccf/similarity/protocol.py
    - src/ccf/projection/__init__.py
    - src/ccf/projection/plan.py
    - src/ccf/projection/engine.py
    - src/ccf/products/__init__.py
    - src/ccf/products/contract.py
    - src/ccf/products/gates.py
    - src/ccf/artifacts/__init__.py
    - src/ccf/artifacts/protocol.py
    - src/ccf/artifacts/file_store.py
    - src/ccf/replay/__init__.py
    - src/ccf/replay/record.py
    - src/ccf/replay/serve.py
    - tests/gates/test_product_gates.py
    - tests/replay/test_serve_writes_replay.py
    - tests/integration/test_proto_quickstart.py
    - tests/fixtures/banking/ontology.yaml
    - tests/fixtures/banking/events.yaml
    - tests/fixtures/banking/controlplane.yaml
  modified:
    - src/ccf/contracts/canonical.py
decisions:
  - "Operators take a GraphView and return a GraphView, not a GraphReader. The engine performs the fabric's single as-of read; every operator downstream transforms a value. There is then no state underneath an operator that could differ between two orderings, which is what makes (A∘B)(G) = A(B(G)) assertable bit-for-bit rather than merely hoped for."
  - "Policy classification is read from a per-entity-class attribute mapping rather than one global key. A single key forces every entity asserted in one envelope to share a classification, which is false of any real ontology and would have made the restricted-covenant case unrepresentable without corrupting the facility claim."
  - "Similarity scores are integer percent. The canonical serializer refuses floats outright, and a score that cannot be canonically serialized cannot appear in a provenance chain that replay compares byte for byte."
  - "The engine records operators_invoked from execution, never from the plan's declaration. The two sets are produced independently — one by the producer, one by the thing that ran them — which is the only reason the L6 lineage strict-equality gate is a check rather than a tautology."
  - "MAX_TTL is resolved from the Control Plane twice: at product-class registration (so a missing ceiling fails while the fabric is being wired) and at gate time (so the ceiling a decision was gated against is the one the audit log records). No TTL number exists anywhere in /src."
  - "Gate refusals are returned values, not raised exceptions. A refusal returned as data cannot be swallowed by a bare except, and the caller has no product in hand to proceed with. Exceptions are reserved for broken deployments (a MAX_TTL that vanished after registration), which must not be reported the same way as a bad product."
  - "serve() is one expression because the replay append returns the delivery capability. A two-statement write-then-deliver has a skippable statement; a capability-returning append has no branch that reaches delivery without a record."
  - "ServableProduct.deliver accepts only a gated product, so the two structural gates compose: a delivered product has passed all three validation gates AND has a replay record, and neither guarantee is reachable without the other."
  - "The graph snapshot id is derived by content_hash over exactly the four D-IMPL-06 constituents rather than assigned. An assigned id could be reused across two different states, and a replay comparing ids would then agree about disagreeing state."
  - "Model version is recorded as the literal \"none\" rather than omitted. \"No model participated\" is a positive claim the record makes; an absent field is indistinguishable from a record that forgot to look."
metrics:
  duration: ~50 min
  completed: 2026-07-25
  tasks: 3
  commits: 5
---

# Phase 4 Plan 05: The D-01 Vertical Slice — L4 to L6, Replay, and Artifacts Summary

The fabric now runs end to end: banking signal envelopes enter through L1/L2,
land in the SQLite graph, are computed over by a four-category operator chain,
interpreted by Π, gated into a typed Context Product, and delivered — but only
after their decision record is content-addressed into the ArtifactStore.

## What Was Built

**Task 1 — the algebra and the two-stage engine** (`1c9d801`). Four operators,
one per canonical category, each of which actually reshapes state: Policy
substitutes the principal-permissible subgraph and prunes the edges incident to
what it removed; Similarity ranks a declared entity class against a corpus with
its index version pinned into provenance; Temporal cuts on both bitemporal
axes; Traversal expands breadth-first over typed edges to a declared depth. The
whitepaper's ordering is enforced by the planner (`CATEGORY_ORDER`), so
Policy-before-Similarity is a property of the engine rather than of whoever
wrote the plan — a projection cannot express the forbidden order because it
declares a *set* of operators, not a sequence.

`ProjectionPlan` is a `typing.Protocol` with `required_operators()` and
`invoke()`, dispatched structurally. The engine resolves and orders the
declared keys, threads each intermediate into the next, and builds its own
record of what ran. That independence is the point: the L6 lineage gate
compares two sets produced by two parties, and a plan that could tell the
engine what ran would have turned that gate into a tautology.

**Task 2 — the three gates** (`0f2ca39` RED, `baf65c8` GREEN). `run_gates` is
the only way to obtain a `ServableProduct`; the type takes a module-private
token, exactly as the writer takes a boot token. The sequence is fixed —
empty-operator, then lineage strict equality, then TTL bounds — and each
refusal is a typed value carrying the failing detail. MAX_TTL exists only in
the Control Plane: `register_product_class` refuses to register a class whose
ceiling is unregistered or mistyped (D-IMPL-39), and the gate resolves the
pinned version again at gate time so the audit log records what the decision
was actually measured against.

**Task 3 — replay, artifacts, and the proto-quickstart** (`906ec34` RED,
`a732197` GREEN). `FileArtifactStore` addresses artifacts by
`sha256(canonical_bytes(...))` and is write-once by never opening an existing
artifact for writing; the versioned URI carries the hash and has no surface
that could ever say "latest". `DecisionReplayRecord` carries all five
dimensions with a *logical* snapshot — boundary, tenant, store watermark, and
the touched-substate manifest lineage already enumerates — so year-scale replay
does not require a graph copy per decision.

The serve path is the plan's structural claim made literal:

```
ReplayWriter.write_replay_record(record) -> DeliveryCapability
DeliveryCapability.deliver(gated_product) -> ServedProduct
```

A caller holding no capability has nothing to deliver with, and the only source
of a capability is an append that returned. When the store raises, the exception
propagates out of the append and no branch reaches delivery — not because
someone remembered to check.

The proto-quickstart drives all of it from three YAML fixtures. The event
stream is built to fail loudly: a counterparty asserted by two source systems
at the same observed time (one claim, two lineage entries), that same envelope
re-delivered verbatim (nothing accumulates), a later observation of the same
counterparty (supersession, with the corroborated claim and its evidence still
readable), a restricted covenant that Policy must remove together with the edge
that would otherwise leak it by absence, and a permitted-but-irrelevant
facility that Similarity must rank out. Each of the three gates is then tripped
by a deliberately broken candidate, and the record round-trips from the store to
a matching content hash.

## Key Implementation Details

- **Corroboration and supersession are both in the fixture stream, deliberately.**
  Claim identity includes `valid_from`, so two sources agreeing about the same
  state at the same observed time corroborate, while a later observation
  supersedes. The fixture exercises both, and the test reads the *history*
  rather than the current view to see it.
- **Similarity does not delete what it was not asked about.** Entity classes
  outside `ranked_entity_classes` pass through untouched. An operator that
  dropped everything it did not rank would not be ranking; it would be
  filtering, and the distinction matters because the projection reads classes
  the ranking never scored.
- **Every operator output prunes dangling edges.** A view retaining an edge to
  a node the principal may not see leaks by absence. Pruning is part of the
  substitution contract (INV-CH7-40), not tidying.
- **Nothing in this plan reads a clock.** `temporal_boundary` and `now` are
  arguments at every level — operator, engine, gate, record. The fixture
  supplies both as data, which is what makes the slice replayable at all.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Canonical serializer could not render a set of nested models**

- **Found during:** Task 3 (surfaced immediately by the proto-quickstart, which
  is the first code to hash a whole `GraphView`)
- **Issue:** `_normalize` delegated to `value.model_dump(mode="python")`, and
  Pydantic rebuilds set-valued fields as *sets of dicts*. Dicts are unhashable,
  so `TypeError: unhashable type: 'dict'` fired for any contract holding
  `frozenset[LineageEntry]` — that is, every claim in the fabric. Content
  addressing, composition assertions, and replay hashing were all affected; the
  defect was invisible until something hashed a contract containing claims,
  which nothing before this plan did.
- **Fix:** `_normalize` now walks `type(value).model_fields` directly, keeping
  each nested model a model until this function renders it. No behavioral
  change to any already-passing case (the full prior suite stayed green).
- **Files modified:** `src/ccf/contracts/canonical.py` (not in the plan's
  `files_modified`; the alternative was working around the SDK's single
  canonical form, which is the one thing that module exists to prevent)
- **Commit:** `a732197`

**2. [Rule 2 - Architectural fidelity] Policy classification is per entity class**

- **Found during:** Task 3, while building the fixture stream
- **Issue:** `PolicyFilterParameters` originally declared one global
  `classification_attribute`. That forces every entity asserted in a single
  envelope to share one classification value, which made the restricted-covenant
  case unrepresentable without corrupting the co-asserted facility claim — the
  fixture would have had to choose between demonstrating policy substitution and
  keeping claim identity honest.
- **Fix:** `classification_attribute_by_class: Mapping[str, str]`, with an
  unmapped class treated as inadmissible (fail-closed). Ontologies name a
  class's sensitivity in the class's own vocabulary; this is the more faithful
  model as well as the one the fixture needs.
- **Files modified:** `src/ccf/operators/categories.py`
- **Commit:** `a732197`

### Interpretations

- **`SimilarityIndexProtocol` and its reference implementation share a module.**
  The plan says "define the Protocol in `similarity/protocol.py` now with a
  naive exact/in-memory reference for the slice", and `files_modified` lists no
  third file, so `TokenOverlapIndex` lives beside the Protocol with the
  distinction stated in its docstring. The sqlite-vec and Chroma
  implementations (04-11) get their own modules.
- **`run_gates` takes `product_class` in addition to `registry`.** The plan's
  signature is `run_gates(candidate, *, engine_resolved, now, registry)`. The
  registry alone cannot answer "which MAX_TTL applies to this product class"
  without the SDK inventing a key-naming convention — which would be a domain
  value in `/src`. The registered class carries its own pinned
  `(key, version)`, established at registration, and the gate resolves against
  the registry using it. MAX_TTL still comes only from the Control Plane, and
  the audit log proves it (`test_max_ttl_is_read_from_the_control_plane_at_gate_time`).
- **The proto-quickstart boots its own fabric rather than extending
  `fabric_boot`.** The `conftest.py` fixture hard-codes its own resolution spec;
  the integration test's whole point is that the spec comes from
  `ontology.yaml`. It calls the same `ccf.boot.boot` composition root — the
  discipline that matters (no test-only writer, no fake store) is intact, and
  `conftest.py` was left unmodified.
- **`grep -ril "covenant" src/` is clean; `counterparty` appears in three
  docstrings.** All three are prose stating that the whitepaper's worked
  topology is *user configuration the SDK must not inherit* (two of them landed
  in 04-03/04-04). They are the No-Hardcoding Rule being explained, not
  violated; no entity class, attribute name, or identifier is referenced by any
  code path in `/src`.
- **λ_c-derived TTL is not yet wired.** The product's `expires_at` comes from a
  fixture-declared product TTL, bounded by the Control-Plane MAX_TTL ceiling.
  The D-IMPL-31 two-granularity derivation (product TTL derived over constituent
  signal validities) belongs to the λ_c/D_c subsystem plan; the ceiling half of
  the rule, which is what this plan's gate owes, is enforced.

## TDD Gate Compliance

Tasks 2 and 3 both ran a clean RED → GREEN, each with the failing suite
committed before any implementation existed:

| Gate | Commit | State |
|---|---|---|
| RED (gates) | `0f2ca39` | collection error — `ccf.products` absent |
| GREEN (gates) | `baf65c8` | 15 passed |
| RED (replay/artifacts) | `906ec34` | collection error — `ccf.artifacts`, `ccf.replay` absent |
| GREEN (replay/artifacts) | `a732197` | 12 passed |

Task 1 was implementation-first, which D-15 permits for plumbing; its
behavior is asserted by the proto-quickstart rather than by a dedicated
operator suite, because the operator subsystem plan owns the
composition-preservation harness (D-14) and a thin interim suite would have
been rewritten by it.

## Verification

| Check | Result |
|---|---|
| `.venv/bin/pytest tests -q` | 115 passed |
| `.venv/bin/pytest tests/gates -q` | 15 passed |
| `.venv/bin/pytest tests/replay -q` | 12 passed |
| `.venv/bin/pytest tests/integration -q` | 15 passed |
| `.venv/bin/mypy --strict src` | Success, 36 source files |
| `.venv/bin/python -m tools.lints --all` | exit 0, zero allowlist entries added |
| `.venv/bin/pytest tools/lints/tests -q` | 45 passed |
| `grep -rc "datetime.now()" src/ccf/operators src/ccf/projection` | total 0 |
| `grep -ril "covenant" src/` | no output |
| Four operator classes, one per category | `PolicyFilter`, `SimilaritySelect`, `TemporalAsOf`, `TraversalNeighborhood`, conformance asserted at import |
| Operator/projection/products/replay/artifacts modules tagged `__ccf_mode__` | all algorithmic |
| Writer imported by any file added in this plan | none — CINV-02 green |
| Post-commit deletion check, all 5 commits | no deletions |

## Known Stubs

None. Three bounded-scope items, all named in the plan or in CONTEXT.md:

- `TokenOverlapIndex` is the D-IMPL-03 *reference* index — lexical Jaccard
  overlap, deliberately not production retrieval. The seam is real; sqlite-vec
  and Chroma implement the same Protocol in 04-11.
- Product TTL derivation is fixture-declared pending the λ_c/D_c plan (see
  Interpretations). The MAX_TTL ceiling is enforced.
- The MCP-backed ArtifactStore is Phase 6 per D-12 and is deliberately not
  scaffolded — an empty module named for it would be a promise the seam has not
  been asked to keep.

## Threat Flags

None new. The three registered threats are mitigated as planned: T-04-10
(repudiation at delivery) by the capability-returning append plus the
failing-store test; T-04-11 (artifact tampering) by content addressing,
write-once semantics, and a round-trip hash assertion; T-04-12 (unbounded TTL)
by the TTL gate against a Control-Plane ceiling that must exist before the
product class can be registered at all.

## Self-Check: PASSED

All 23 created files and 1 modified file exist on disk; all five commit hashes
(`1c9d801`, `0f2ca39`, `baf65c8`, `906ec34`, `a732197`) are present in
`git log`.
