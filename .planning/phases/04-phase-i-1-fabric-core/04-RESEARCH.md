# Phase 4: Phase I.1 — Fabric Core - Research

**Researched:** 2026-07-25
**Domain:** Python 3.12 SDK — typed graph state, operator algebra, Pydantic v2 contracts, custom AST lints, dual-backend persistence (SQLite/Postgres)
**Confidence:** HIGH (design is fully resolved on paper; stack verified against PyPI; risk lives in calibration, not unknowns)

## Summary

Phase 4 writes the first production code of the CCF SDK: the L1–L6 Data and Context Layer per `docs/DESIGN.md` §2A/§2B, with the four CI invariant lints (CINV-01..04) gating from the first commit. This is unusually well-specified work — all 49 D-IMPL rulings are RESOLVED, DESIGN.md gives contract-level signatures for every component, and FEASIBILITY.md §11 gives a per-invariant verification table (the D-17 gate checklist). The planner's job is sequencing and fidelity, not invention. Research therefore focused on: (a) the concrete stack and versions, (b) implementation patterns for the load-bearing mechanisms (single-writer DI stack, idempotent upsert with lineage set-union, composition-preservation property tests, custom AST lints), and (c) pitfalls that would silently violate a named invariant.

The user's CONTEXT.md decisions materially shape the plan: vertical slice first on SQLite with a realistic **banking** proto-quickstart fixture (D-01/D-02/D-03 — including a CLAUDE.md §9 amendment and a new D-IMPL entry to log), Postgres and Chroma in later waves (D-11/D-13), MCP-backed ArtifactStore deferred to I.3 (D-12 — a recorded scope amendment to success criterion 4), custom in-repo AST checkers on GitHub Actions (D-06..D-09), and Hypothesis-based composition-preservation testing plus TDD on contracts/invariants (D-14/D-15).

**Primary recommendation:** Plan Wave 1 as packaging + CI-lint scaffold + slice contracts; Wave 2 as the SQLite vertical slice with the banking fixture; then subsystem waves per D-04; Postgres/Chroma conformance waves near the end; gate wave last. Every public class docstring cites its whitepaper section (CLAUDE.md §11).

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions (verbatim from 04-CONTEXT.md)

**Build sequencing**
- **D-01:** Vertical slice first — a thin L1→L6 path (minimal ingest → assembly → SQLite graph → operator chain → projection → typed Context Product with replay record) lands early; subsequent plans widen it.
- **D-02:** The slice's proof point is a **proto-quickstart**: a private test-fixture precursor of `examples/00-quickstart`, formalized as the real example in Phase 8. It must be **realistic, not hello-world** — real multi-type ontology, multi-source events exercising idempotent upsert and lineage accumulation, a genuine operator chain, products that actually trip the validation gates, full five-dimension replay record. Planner bar: "would this slice catch a broken invariant?"
- **D-03 (REVISES CLAUDE.md §9):** Dave changed the examples-domain policy: the v0 examples suite becomes a **horizontal mix of domains**, with **example 00 (and the I.1 slice fixtures) in a banking scenario** — not the single neutral field-service domain §9 currently mandates. Phase 4 must amend CLAUDE.md §9 accordingly and log the ruling in `docs/DECISIONS.md` (new D-IMPL-NN, Approver: Dave, 2026-07-25). Banking fixtures also give realistic policy/regulatory pressure on the fabric, serving D-02.
- **D-04:** Widening work is organized **by subsystem**, matching DESIGN.md component boundaries: operators+composition tests, projection engine, product contract+gates, λ_c/D_c, replay+ArtifactStore, Control Plane registry, CDC ingress, Postgres backend, Chroma index.
- **D-05:** Wave 1 = repo/packaging scaffold (`ccf` + `ccf-runtime` packages, pyproject, CI skeleton with lints) **plus only the typed contracts the slice needs**. Remaining contracts land with their subsystem plans — no speculative full contract layer up front.

**CI lint mechanics**
- **D-06:** The No-Hardcoding, zero-harness-imports, and `@algorithmic` lints are **custom in-repo AST checkers** (a `tools/` or `tests/lints/` module, themselves unit-tested), run as CI steps. No ruff/flake8 plugin packaging.
- **D-07:** Lints **gate CI from the first fabric commit** — they land in the Wave 1 scaffold, blocking, never report-only.
- **D-08:** No-Hardcoding detection = heuristics (prompt-shaped multi-sentence strings, numeric-table/dict constants in `/src`, factory-bypass construction) **plus a reviewed, versioned allowlist file** for legitimate literals. Every exception is an explicit, reviewable allowlist entry.
- **D-09:** CI runs on **GitHub Actions** (private repo): lint job + test matrix; Postgres provided as a service container.

**Backend & infra logistics**
- **D-10:** Local Postgres testing via **testcontainers-python**; CI uses the GitHub Actions postgres service container. Same test suite runs in both.
- **D-11:** Postgres reference GraphStore lands **after the slice, in a later wave within I.1**, implemented against the by-then-stable Protocol conformance suite. Slice and early subsystem plans run on SQLite.
- **D-12:** ArtifactStore in I.1 = **Protocol + file-backed dev impl only**; the MCP-backed reference impl moves to I.3 with the rest of the MCP machinery. ⚠ This amends Phase 4 success criterion 4 (which names the MCP-backed impl) — planner must record the scope amendment in `.planning/ROADMAP.md`/gate materials rather than silently miss it.
- **D-13:** **Chroma is IN for I.1** as the second SimilarityIndex reference impl (budget granted under D-IMPL-03's "if budget allows"). Gets its own subsystem plan against the shared conformance suite.

**Test strategy depth**
- **D-14:** Composition-preservation `(A∘B)(G) = A(B(G))` tested with **property-based generation (Hypothesis) for every shipped operator pair, plus curated banking fixture graphs** for known edge cases (empty results, policy-filtered nodes, temporal boundaries). Covers both FEASIBILITY.md D-08 test classes.
- **D-15:** Test discipline = **TDD on contracts and invariants** (tests-first for validation gates, single-writer, lineage strict equality, replay record shape, Protocol conformance); implementation-first permitted for plumbing/scaffolding.
- **D-16:** Backend parity via **one shared, parametrized Protocol conformance suite** run identically against SQLite/Postgres and sqlite-vec/Chroma; backend-specific tests only for substrate quirks.
- **D-17:** Gate bar = the FEAS-03 **per-invariant checklist green** (each named invariant maps to a passing named test/lint); line coverage reported informationally, **no numeric coverage gate**.

### Claude's Discretion
- Exact heuristic set and thresholds for the No-Hardcoding AST checker (bounded by D-08's allowlist mechanism).
- Slice contract subset selection (D-05), plan/wave counts, and internal module layout within `/src` per DESIGN.md.
- Banking fixture ontology specifics (entity/relationship types, event mix) — bounded by D-02's realism bar; keep values in fixture artifacts, never `/src` (No-Hardcoding Rule applies to fixtures' code too).

### Deferred Ideas (OUT OF SCOPE)
- MCP-backed ArtifactStore reference impl → Phase 6 (I.3), per D-12.
- None other — discussion stayed within phase scope.

</user_constraints>

## Project Constraints (from CLAUDE.md)

Directives with the same authority as locked decisions (CLAUDE.md rev 4):

- **Whitepaper fidelity wins over everything.** Cite the whitepaper section in the docstring of every public class; SDK-extension components cite CLAUDE.md instead and are labeled **SDK-defined** (§11).
- **No-Hardcoding Rule (§6.4):** no inline prompts, no agent/task definitions in code, no threshold/table/routing constants in `/src`, `/runtime`, or `/examples`. Code = interpreters and factories. Applies to fixture *code* too (values go in fixture artifacts).
- **Zero harness imports in `/src`** (§7.3); harness code only in `/runtime/adapters/<harness>/` (not built in I.1, but the lint ships now).
- **Single-writer:** only L2/Assembly holds a `GraphWriter`; enforced by DI at boot, not convention (§10).
- **Algorithmic ⇄ Semantic Alternation:** `@algorithmic` modules never import `LLMClientProtocol` or any LLM vendor SDK (§11).
- **Typed contracts at every boundary:** Pydantic v2 `extra=forbid` (§11, D-IMPL-01).
- **Prefer Protocols over inheritance**; every pluggable substrate ships a reference impl (§11).
- **Homecams is pattern triangulation only — never port code** (§2.1).
- **Phase discipline:** branch `phase-i1`; merge to `main` only at `D-GATE-I.1`; redesign requires a Phase D mini-cycle (§3, §2.2). Commit at deliverable boundaries with messages naming the D-IMPL/section served.
- **Model mandate:** Opus 5 (else Opus 4.8), high effort, for Phase I execution (§3).
- **Review protocol §3.1** at phase end, with Codex/Cursor credentials per the CLAUDE.md §3.1 note (`CODEX_API_KEY`, `CURSOR_API_KEY` from `/home/parkave/homecams_v2/.env`).
- **Doc edits owed by this phase (per CONTEXT.md D-03/D-12):** CLAUDE.md §9 amendment, new D-IMPL entry in `docs/DECISIONS.md`, `.planning/ROADMAP.md` criterion-4 amendment.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FABR-01 | Context Graph primitive, Postgres + SQLite backends (D-IMPL-02) | DESIGN.md §2A.5.1–.2 six-semantics Protocol; upsert/lineage patterns below; conformance-suite pattern (D-16); psycopg 3.3.4 + stdlib sqlite3 verified |
| FABR-02 | Operator algebra, four categories, composition-preservation tests | DESIGN.md §2B.1; pure-function operator pattern; Hypothesis 6.161.5 property harness (D-14); canonical-serialization equality pattern |
| FABR-03 | Projection engine Π, structural typing, two-stage execution | DESIGN.md §2B.2; `ProjectionPlan` structural Protocol (`required_operators()` + `invoke()`); D-IMPL-49 selection signature |
| FABR-04 | Context Product Contract `extra=forbid` + three validation gates | DESIGN.md §2B.3; Pydantic v2 `model_config = ConfigDict(extra='forbid')`; gate-sequence-as-only-construction-path pattern |
| FABR-05 | λ_c / D_c from Control Plane config only | DESIGN.md §2B.4; D-IMPL-38/39/40/47 declared-schema no-silent-default discipline; No-Hardcoding lint verifies zero tables in `/src` |
| FABR-06 | Five-dimension Decision Replay record + engine | DESIGN.md §2B.5; write-at-serve-time-by-construction pattern; D-IMPL-06 logical snapshots; D-IMPL-26 hash addressing |
| FABR-07 | Control Plane in-process versioned registry + remote extension point | DESIGN.md §7; append-only version mapping; audit-plane events |
| FABR-08 | ArtifactStore Protocol + impls | Protocol + **file-backed dev impl only in I.1** (CONTEXT D-12 amends scope; MCP impl → I.3). Content-addressed sha256 + versioned-URI mapping per D-IMPL-26 |
| FABR-09 | CDC→G ingress reference (Pattern 1) | DESIGN.md §2A.4.1; `CDCSourceAdapter` implements `SignalSourceProtocol`; Debezium-*style* envelope mapping — transport is deployment infra, so I.1 needs a file/stream-fed change-event adapter, not a Kafka/Debezium dependency |
| CINV-01 | No-Hardcoding lint | Custom `ast` checker (D-06) + versioned allowlist (D-08); heuristics recommended below |
| CINV-02 | Zero-harness-imports lint (+ single-writer static gate) | `ast` import walker over `/src` with deny-list; `GraphWriter` import restricted to `ccf.assembly` + composition root; strict mypy |
| CINV-03 | `@algorithmic` lint | Module-tag scan + import check for `LLMClientProtocol`/vendor SDKs (D-IMPL-09 single crisp target) |
| CINV-04 | Replay-by-construction + single-writer boot check | Test-harness assertions per DESIGN.md §9; in I.1 the reachable subset is product-serve replay write + boot check (HITL/workflow/skill checks arrive with their subsystems in I.2/I.4 — scaffold the harness now, mark those cases as not-yet-applicable) |
</phase_requirements>

## Architectural Responsibility Map

Single-process Python SDK — tiers here are DESIGN.md layer/plane boundaries, not network tiers.

| Capability | Primary owner | Secondary | Rationale |
|------------|--------------|-----------|-----------|
| Signal normalization (`SignalEnvelope`) | L1 `ccf.signal` | adapters in `ccf-runtime` | Envelope type in library so both packages share it (D-IMPL-04/33) |
| CDC ingress adapter | `ccf-runtime` (async) | — | Ingestion adapters are runtime-package, async per D-IMPL-04(b) |
| Entity resolution, temporal stitching, policy binding | L2 `ccf.assembly` | Control Plane (bundle versions) | Four converging concerns; sole `GraphWriter` holder (D-IMPL-41) |
| Graph persistence (six semantics) | L3 `ccf.graph` + `GraphStore` backends | — | Reader/writer Protocol split (D-IMPL-34) |
| Operators + planner + registry | L4 `ccf.operators` | intermediate cache (D-IMPL-36) | Pure sync read-only functions over `GraphReader` |
| Projection Π | L5 `ccf.projection` | — | Structural typing, stateless, two-stage |
| Product contract + three gates | L6 `ccf.products` | Control Plane (MAX_TTL) | Gate sequence is the only construction path of a servable product |
| λ_c / D_c computation | `ccf` (mechanism) | Control Plane (all values) | Zero tables in code (FABR-05) |
| Replay record + engine | `ccf.replay` | ArtifactStore | Written at serve time by construction |
| Control Plane registry | `ccf.controlplane` | — | Versioned config + audit plane; every other subsystem depends on it — sequencing pressure lands here first (docs/ROADMAP.md I.1 risk note) |
| ArtifactStore | Protocol in `ccf` + file impl | MCP impl deferred to I.3 | D-IMPL-26/27; CONTEXT D-12 |
| CI lints | `tools/` or `tests/lints/` (repo, not package) | GitHub Actions | D-06; unit-tested checkers |

## Standard Stack

All versions verified on PyPI 2026-07-25 via `pip index versions`.

### Core (runtime dependencies of `ccf` / `ccf-runtime`)
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| Python | 3.12+ | sole target | D-IMPL-01 (system has 3.12.3) `[VERIFIED: local]` |
| pydantic | 2.13.4 | all typed contracts, `extra=forbid` | D-IMPL-01 `[VERIFIED: PyPI + slopcheck]` |
| psycopg | 3.3.4 (`psycopg[binary]`) | Postgres reference GraphStore | Modern Postgres driver, sync-capable (fabric core is sync) `[VERIFIED: PyPI + slopcheck]` |
| sqlite3 (stdlib) | — | SQLite-for-dev GraphStore | No dependency needed; JSON1 built in `[VERIFIED: stdlib]` |
| sqlite-vec | 0.1.9 | SimilarityIndex reference (dev default) | D-IMPL-03 `[VERIFIED: PyPI + slopcheck]` |
| chromadb | 1.5.9 | second SimilarityIndex impl | CONTEXT D-13 `[VERIFIED: PyPI + slopcheck]` — heavy transitive tree (onnxruntime, opentelemetry, kubernetes); make it an **optional extra** (`ccf[chroma]`), never a core dep |
| pyyaml | 6.0.3 | reading Control Plane / fixture YAML artifacts | D-IMPL-28 format `[VERIFIED: PyPI + slopcheck]` |

### Supporting (dev/test/CI)
| Library | Version | Purpose | When |
|---------|---------|---------|------|
| pytest | 9.1.1 | test runner | everywhere `[VERIFIED: PyPI + slopcheck]` |
| hypothesis | 6.161.5 | composition-preservation property tests | D-14 `[VERIFIED: PyPI + slopcheck]` |
| testcontainers | 4.15.0 | local Postgres in tests | D-10 `[VERIFIED: PyPI + slopcheck]`; Docker 29.2.1 present locally |
| mypy | 2.3.0 | strict type gate incl. single-writer static gate | DESIGN.md §9 CINV-02 row `[VERIFIED: PyPI + slopcheck]` — note mypy is now on a 2.x line; pin and verify strict-mode flags at scaffold time |
| pytest-cov | 7.1.0 | informational coverage (no gate, D-17) | `[VERIFIED: PyPI + slopcheck]` |
| stdlib `ast` | — | CINV lint checkers | D-06 rules out plugin frameworks; stdlib `ast.walk`/`NodeVisitor` is sufficient — do NOT add libcst unless concrete need arises `[VERIFIED: stdlib]` |

### Alternatives Considered
| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| stdlib `ast` | libcst 1.8.6 | libcst preserves formatting/comments — useful for autofix, unnecessary for reject-only lints; extra dep |
| psycopg 3 | asyncpg / SQLAlchemy | Fabric core is **sync** (D-IMPL-04); asyncpg is async-only; SQLAlchemy adds an ORM layer the six-semantics Protocol doesn't need — physical layout is backend-internal, hand-rolled SQL is appropriate here |
| Hypothesis | plain parametrized fixtures | D-14 explicitly requires Hypothesis **plus** curated fixtures — use both |

**Installation (Wave 1 scaffold):**
```bash
pip install -e "./src[dev]"   # exact extras layout is planner discretion; deps:
# runtime: pydantic pyyaml sqlite-vec psycopg[binary]
# optional: chromadb  (extra: chroma)
# dev: pytest hypothesis testcontainers mypy pytest-cov
```

## Package Legitimacy Audit

slopcheck 2026-07-25, ecosystem pypi, run in a scratch venv: all ten candidates passed the registry check and installed cleanly (slopcheck blocks slop before install; nothing was blocked or flagged).

| Package | Registry | Verified version | slopcheck | Disposition |
|---------|----------|------------------|-----------|-------------|
| pydantic | PyPI | 2.13.4 | OK | Approved |
| hypothesis | PyPI | 6.161.5 | OK | Approved |
| pytest | PyPI | 9.1.1 | OK | Approved |
| testcontainers | PyPI | 4.15.0 | OK | Approved |
| sqlite-vec | PyPI | 0.1.9 | OK | Approved (0.x — pin exactly) |
| chromadb | PyPI | 1.5.9 | OK | Approved as optional extra |
| psycopg | PyPI | 3.3.4 | OK | Approved |
| pyyaml | PyPI | 6.0.3 | OK | Approved |
| mypy | PyPI | 2.3.0 | OK | Approved |
| pytest-cov | PyPI | 7.1.0 | OK | Approved |

**Removed [SLOP]:** none. **Flagged [SUS]:** none.

## Architecture Patterns

### System flow (the I.1 vertical slice, per DESIGN.md §2A.5.4 / §2B)

```
change event / fixture event
        │
   CDCSourceAdapter (ccf-runtime, implements SignalSourceProtocol)
        │  emits SignalEnvelope (tenant_id, envelope_id, source, timestamps, opaque payload)
        ▼
   AssemblyWorker (ccf.assembly — SOLE GraphWriter holder)
        │  entity resolution → temporal stitching → policy binding
        ▼
   GraphStore backend (SQLite first; Postgres later wave)
        │  idempotent upsert on (tenant_id, entity_uri); lineage set-union;
        │  supersession edges; bitemporal T
        ▼  (GraphReader only from here down)
   Operator plan (Planner): Policy → Similarity → Temporal → Traversal (dependency order)
        ▼
   ProjectionPlan (structural: required_operators() + invoke())
        ▼
   Three gates: empty-operator guard → lineage strict equality → TTL bounds
        ▼
   ContextProductContract served  ──►  Replay record written (5 dimensions) BEFORE delivery
                                        └► ArtifactStore (file-backed)
```

### Recommended package layout (planner discretion within DESIGN.md names)
```
src/ccf/                    # library package "ccf"
├── contracts/              # shared Pydantic bases (extra=forbid), SignalEnvelope
├── signal/                 # L1 — envelope + SignalSourceProtocol
├── assembly/               # L2 — AssemblyWorker, EntityResolutionStrategy, temporal stitching, policy binding; ONLY importer of graph._writer
├── graph/                  # L3 — ContextGraph, GraphReader/GraphWriter Protocols, backends/ (sqlite.py, postgres.py)
├── operators/              # L4 — four categories, registry, planner, intermediate cache
├── projection/             # L5 — ProjectionPlan structural Protocol, engine
├── products/               # L6 — ContextProductContract, three gates, product cache
├── halflife/               # λ_c, D_c, DebtFactorScorer Protocols (mechanism only)
├── replay/                 # five-dimension record, replay engine, logical snapshots
├── controlplane/           # versioned registry, audit plane, artifact classes
├── artifacts/              # ArtifactStoreProtocol + file-backed impl, sha256 addressing
├── similarity/             # SimilarityIndex Protocol, sqlite-vec impl; chroma impl optional
└── boot.py                 # composition root — the ONE place GraphWriter is constructed
runtime/ccf_runtime/        # package "ccf-runtime": CDC adapter (async), future MCP/A2A/harness
tools/lints/                # CINV-01..03 AST checkers + allowlist.yaml + their unit tests
tests/                      # conformance suites, gates, composition harness, boot check, fixtures/banking/
.github/workflows/ci.yml    # lint jobs + test matrix + postgres service container
```

### Pattern 1: Single-writer DI stack (D-IMPL-41, four layers)
**What:** (1) `GraphReader`/`GraphWriter` as separate `typing.Protocol`s; read-path constructors accept only `GraphReader`. (2) `boot.py` composition root constructs exactly one `GraphWriter` and injects it into `AssemblyWorker` only. (3) Static gate: the writer's concrete module (e.g. `ccf.graph._writer`) is import-linted to `ccf.assembly` + `ccf.boot`; strict mypy rejects out-of-L2 `GraphWriter` type references. (4) Runtime backstop: writer constructor requires a boot token minted once by the composition root; a second mint (or second writer construction) raises at boot.
**When:** Wave 1/slice — the boot check test (CINV-04 runtime complement) is TDD-first per D-15.
**Claim strength:** carry DESIGN.md's honest residual claim verbatim — "no unforced path exists and every forced path fails CI or fails at boot," never absolute prevention.

### Pattern 2: Idempotent upsert + lineage set-union (SQLite/Postgres)
**What:** compound unique index on `(tenant_id, entity_uri)` **at the persistence tier**; upsert via `INSERT ... ON CONFLICT (tenant_id, entity_uri) DO UPDATE` (identical syntax family in SQLite ≥3.24 and Postgres — one semantic, two dialects). Lineage is deliberately NOT idempotent: the same observation twice → one entity record, but lineage rows accumulate per `(source, timestamp, passage_anchor)` — model lineage as an append-only child table keyed by envelope_id, with set-union semantics on merge (dedupe on full lineage-entry identity, never overwrite). Supersession = new row + `superseded_by`/`superseded_at` on the prior row; **no `UPDATE` of claim content, no `DELETE`, ever**.
**Conformance:** one parametrized pytest suite (fixture param: backend factory) asserting all six D-IMPL-34 semantics — this suite is written against SQLite in the slice and is the acceptance bar the later Postgres wave implements against (D-11/D-16).

### Pattern 3: Pure-function operators + composition-preservation harness
**What:** each operator is a frozen, side-effect-free callable `(GraphReader-view, params, tenant_id, temporal_boundary) → typed subgraph production` with its own provenance sub-chain. Composition test: for every shipped pair (A,B), Hypothesis generates graph states (banking-shaped strategies: entities, typed relationships, bitemporal claims, policy labels, lineage), then asserts canonical serialization of `(A∘B)(G)` == `A(B(G))` **bit-for-bit**.
**Bit-for-bit prerequisite — canonical serialization:** define one canonical JSON serialization early (sorted keys, sorted set-valued collections, RFC3339 UTC timestamps, no floats where Decimal/int suffice, `sha256(canonical_bytes)` as identity). This single utility underpins composition tests, D-IMPL-26 content addressing, replay hashes, and function-determinism (INV-CH7-31). Build it in the slice; everything else depends on it.
**Also:** the D-08 second test class — staged two-stage projection output == direct composition — lives in the same harness (FEASIBILITY.md §11 row).

### Pattern 4: Three gates as the only construction path
**What:** the servable product type is constructible only through a gate function that runs empty-operator guard → lineage strict equality (declared `operators_invoked` set == engine-resolved set) → TTL bounds (`now < expires_at ≤ now + MAX_TTL`, MAX_TTL fetched from Control Plane per class — unregistered MAX_TTL fails at product-class **registration**, D-IMPL-39). Refusal = structured rejection type, never exception-as-control-flow-swallowed, never silent. Enforce "only path" the same way as single-writer: a module-private constructor + lint/mypy visibility, or a required gate-token argument.

### Pattern 5: Replay-written-at-serve-time by construction
**What:** the serve function's success path *is* `write_replay_record(...) then deliver(product)` — delivery is unreachable without the replay append (make the replay writer return the delivery capability). Dimensions in I.1: (1) logical graph snapshot id = temporal boundary + tenant + store-state watermark + touched-substate manifest from lineage (D-IMPL-06 — no physical copy); (2) policy-bindings versions; (3) model version = "none" (Mode 1 — no LLM anywhere in I.1); (4) perspective conditioning (principal/role; agent fields arrive in I.2); (5) content generation path (operator plan + step sequence). Record persists to file-backed ArtifactStore, content-addressed.

### Pattern 6: Custom AST lints (Claude's discretion on heuristics — recommendation)
**What:** one `tools/lints/` runner walking `/src`, `/runtime`, `/examples` with stdlib `ast`:
- **Prompt-shape heuristic (CINV-01a):** flag `ast.Constant` strings that score ≥2 of: (a) ≥3 sentences; (b) imperative/role-preamble openers ("You are", "Always", "Never", "Respond"); (c) template-brace density (`{...}` or `{{...}}` ≥3); (d) length >200 chars of prose (not paths/SQL/URLs). SQL strings will be the main false-positive class — exempt strings inside `graph/backends/` via allowlist entries, not code exceptions.
- **Numeric-table heuristic (CINV-01b):** flag module-level dict/list constants in `/src` whose values are predominantly numeric, and any float/int default on a Pydantic field in parameter-schema modules (D-IMPL-38 no-silent-default).
- **Factory-bypass (CINV-01c):** flag `Agent(`/`Task(` instantiation outside factory modules — scaffold the rule now (fires nothing in I.1; I.2 inherits it).
- **Harness imports (CINV-02):** deny-list (`google.adk`, `claude_agent_sdk`, `anthropic` outside `LLMClientProtocol` adapters, `langgraph`, configurable) over `/src` `Import`/`ImportFrom` nodes; same walker restricts the `GraphWriter` module.
- **`@algorithmic` (CINV-03):** module tag = a module-level dunder (e.g. `__ccf_mode__ = "algorithmic"`) or docstring marker; tagged modules may not import `LLMClientProtocol` or vendor SDKs. Prefer the dunder — trivially AST-detectable.
- **Allowlist (D-08):** `tools/lints/allowlist.yaml`, entries = `{file, rule, fingerprint(hash of literal), reason, reviewer}` — versioned, reviewed, exact-match.
Each checker gets its own unit tests with positive and negative fixture snippets (D-06).

### Anti-Patterns to Avoid
- **Convenience write helper on GraphReader or a "test-only" writer** — defeats layer 1 of D-IMPL-41. Tests get a writer only through the composition root/boot fixture.
- **Silent defaults for λ_c, D_c thresholds, MAX_TTL, similarity thresholds** — every parameter class is declared-schema, versioned, no-silent-default (D-IMPL-38/39/40). A missing value is a registration/validation failure, not a fallback.
- **Whitepaper worked-example numbers (0.85/0.75 thresholds, cost bands, SLO figures) creeping into code or even test defaults in `/src`** — illustrative only (DESIGN.md Appendix B F-1). Fixture values live in fixture artifacts.
- **`datetime.now()` inside operators/gates** — kills determinism and Hypothesis reproducibility. Inject a clock/`temporal_boundary`; `now` is an explicit input everywhere.
- **Storing floats or unordered collections in canonically-serialized artifacts** — breaks bit-for-bit equality across backends/platforms.
- **Making chromadb a hard dependency** — its transitive tree (onnxruntime, opentelemetry, kubernetes client) bloats install and could itself trip supply-chain review; optional extra + skip-if-not-installed test marker.
- **Async in the fabric core** — operator/projection path is sync (D-IMPL-04); only ingestion adapters in `ccf-runtime` are async.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Contract validation | custom validators | Pydantic v2 `extra=forbid` | D-IMPL-01 ruling; JSON Schema export free |
| Property-based graph generation | random fixture generator | Hypothesis strategies (+ `st.composite` for graph shapes) | shrinking on failure is the whole value (D-14) |
| Postgres in tests | mocks/fakes | testcontainers locally, service container in CI | D-10; conformance must run on the real substrate |
| Vector search | cosine loops | sqlite-vec / chromadb | D-IMPL-03/CONTEXT D-13 |
| Content hashing | custom digest scheme | `hashlib.sha256` over the one canonical serializer | D-IMPL-26 |
| Python parsing for lints | regex over source | stdlib `ast` | regex misses string context, imports-in-functions, aliasing |

**Deliberate hand-rolls (correct per rulings):** GraphStore SQL (no ORM — physical layout is backend-internal), the CINV lint checkers (D-06 forbids plugin frameworks), the in-process Control Plane registry.

## Common Pitfalls

### 1. CINV-01 false positives stall Wave 1
**What:** prompt-shape heuristics flag SQL, docstrings, error messages; developers route around the lint.
**Avoid:** lints only examine `ast.Constant` in code (docstrings excluded by position), allowlist is cheap to use but reviewed; tune against the slice's real code before widening. FEASIBILITY rates this med-risk as *calibration, not design gap*.

### 2. Lineage accumulation accidentally made idempotent
**What:** an upsert that overwrites the lineage column satisfies "idempotent upsert" tests while violating INV-CH7-17 (multi-source evidence must accumulate).
**Avoid:** TDD test (D-15): same logical observation from two sources → one entity row, two lineage entries; same envelope twice → one lineage entry.

### 3. Bit-for-bit equality fails across SQLite vs Postgres
**What:** timestamp precision (Postgres microseconds vs stored text), row ordering, numeric affinity differences make the conformance suite backend-flaky.
**Avoid:** canonical serializer normalizes at the *contract* layer (UTC RFC3339 fixed precision, sorted collections); comparisons happen on serialized contracts, never raw rows.

### 4. Success criterion 4 verified as written, not as amended
**What:** the gate review checks "MCP-backed reference impl" per `.planning/ROADMAP.md` and fails, or worse, someone builds MCP machinery early.
**Avoid:** a Wave-1-or-early task edits `.planning/ROADMAP.md` criterion 4 + logs the D-03 CLAUDE.md §9 amendment + new D-IMPL entry in `docs/DECISIONS.md` (Approver: Dave, 2026-07-25). Three doc edits, explicitly owed by CONTEXT.md.

### 5. Control Plane registry built last
**What:** λ_c/D_c, MAX_TTL, operator parameters, policy bundles all read Control Plane versions — if the registry lands late, subsystems stub it divergently.
**Avoid:** docs/ROADMAP.md flags this exactly ("the artifact hub every other pillar depends on, so sequencing pressure lands here first"). The slice needs a minimal versioned registry; give the full registry an early subsystem wave.

### 6. Hypothesis + property tests too slow / flaky in CI
**What:** graph-shaped strategies with DB writes explode runtime; deadline errors on the Postgres leg.
**Avoid:** composition tests run against in-memory/SQLite graph fixtures (operators are pure reads — the property doesn't need Postgres); pin `derandomize=True` profile in CI plus a nightly randomized profile; keep the Postgres leg for the conformance suite, not the property harness.

### 7. Boot-token backstop leaks into ergonomics
**What:** the writer token pattern makes every test spin the full composition root.
**Avoid:** one shared pytest fixture (`fabric_boot`) that runs the real composition root against a temp SQLite backend — this is also exactly the CINV-04 boot-check surface, and keeps tests honest (no bypass constructor).

### 8. `@algorithmic` lint has nothing to bite on in I.1
**What:** I.1 is Mode-1 pure — no LLM client exists yet, so CINV-03 trivially passes and could be mis-scaffolded.
**Avoid:** define `LLMClientProtocol`'s module path now (even as a stub Protocol in `ccf`) so the lint has its single crisp import target (D-IMPL-09), and unit-test the lint with a fixture module that *would* violate it.

## Code Examples

Patterns only — real code lands in Phase I plans with whitepaper citations per CLAUDE.md §11.

### Contract base (D-IMPL-01)
```python
# Source: pydantic v2 docs (ConfigDict) — pattern per DESIGN.md §2A.2.1
from pydantic import BaseModel, ConfigDict

class CCFContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
```

### Reader/writer Protocol split (D-IMPL-34/41)
```python
# Source: typing.Protocol (PEP 544); design per DESIGN.md §2A.5.2–.3
from typing import Protocol

class GraphReader(Protocol):
    def as_of(self, *, tenant_id: str, at: datetime) -> "GraphView": ...

class GraphWriter(Protocol):  # module import-linted to ccf.assembly + ccf.boot
    def upsert_entity(self, *, tenant_id: str, entity: EntityClaim,
                      lineage: LineageEntry) -> UpsertResult: ...
```

### Idempotent upsert (both backends, one semantic)
```sql
-- SQLite ≥3.24 and Postgres share ON CONFLICT syntax; per DESIGN.md §2A.5.2 semantic 2
INSERT INTO entities (tenant_id, entity_uri, ...)
VALUES (?, ?, ...)
ON CONFLICT (tenant_id, entity_uri) DO UPDATE SET ...;
-- lineage: separate append-only table; INSERT OR IGNORE on full-entry identity (set-union)
```

### Composition-preservation property (D-14)
```python
# Source: hypothesis docs (st.composite); design per DESIGN.md §9 harness
from hypothesis import given, settings
import itertools

@given(graph=banking_graph_states())          # custom composite strategy
@settings(deadline=None)
def test_composition_preservation(graph, pair):   # parametrized over all shipped pairs
    a, b = pair
    lhs = canonical_bytes(compose(a, b)(graph))
    rhs = canonical_bytes(a(b(graph)))
    assert lhs == rhs                              # bit-for-bit
```

### Import lint core (CINV-02)
```python
# Source: stdlib ast docs — D-06 custom checker pattern
import ast, pathlib

DENY = {"google.adk", "langgraph", "claude_agent_sdk"}
WRITER_MOD, WRITER_OK = "ccf.graph._writer", {"ccf.assembly", "ccf.boot"}

def check(path: pathlib.Path, module_name: str) -> list[str]:
    tree = ast.parse(path.read_text())
    errs = []
    for node in ast.walk(tree):
        names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                 else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
        for name in names:
            if any(name == d or name.startswith(d + ".") for d in DENY):
                errs.append(f"{path}:{node.lineno} harness import {name}")
            if name.startswith(WRITER_MOD) and not any(module_name.startswith(ok) for ok in WRITER_OK):
                errs.append(f"{path}:{node.lineno} GraphWriter import outside L2")
    return errs
```

## State of the Art

| Concern | Current approach (verified) | Note |
|---------|------------------------------|------|
| Pydantic | v2.13 — `ConfigDict`, `model_json_schema()` for D-IMPL-28 export | v1-style `class Config` is deprecated; use ConfigDict only |
| pytest | 9.x | major-version jump vs training-era 8.x; check plugin compat (pytest-cov 7.1.0 is current and compatible) `[VERIFIED: PyPI]` |
| mypy | 2.3.0 | mypy crossed to 2.x; verify strict flags/behavior at scaffold time `[ASSUMED: flag surface unchanged]` |
| chromadb | 1.5.x | post-1.0 API (`PersistentClient`, collections); older 0.4-era snippets are stale `[ASSUMED: API shape]` |
| sqlite-vec | 0.1.9 | still 0.x — pin exact; loadable-extension model (`sqlite_vec.load(conn)`) `[ASSUMED: API shape]` |
| Debezium for CDC | not a dependency | Pattern 1 is Debezium-*style*; transport is deployment infra (DESIGN.md §2A.4.1) — I.1 ships a change-event adapter fed from fixtures/files |

## Runtime State Inventory

Not applicable — greenfield phase; `/src`, `/runtime`, `/tests` are empty (verified by `ls`). No stored data, live services, OS registrations, or build artifacts exist for this codebase.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | mypy 2.3 strict-mode flag surface matches 1.x expectations | State of the Art | Wave 1 CI scaffold needs minor flag adjustments — low |
| A2 | chromadb 1.5 client API is `PersistentClient`/collection-based | Standard Stack | Chroma subsystem wave adapts; behind SimilarityIndex Protocol so blast radius is one module — low |
| A3 | sqlite-vec 0.1.9 loadable-extension API (`load(conn)`, `vec0` virtual tables) unchanged | Standard Stack | Same containment as A2 — low |
| A4 | GitHub Actions `postgres` service container remains the standard CI pattern (D-09 presumes it) | CI | Well-established; fallback is testcontainers in CI too — very low |
| A5 | pytest 9 has no breaking change affecting parametrized conformance-suite patterns | Test strategy | Pin and verify at scaffold — low |

All load-bearing architectural claims are `[CITED: docs/DESIGN.md / docs/DECISIONS.md / CLAUDE.md]` — the project's own resolved rulings, not external sources. No assumption above needs a user ruling; all are contained behind Protocols or the Wave 1 scaffold.

## Open Questions

1. **Which contracts are "the slice subset" (D-05)?**
   - Known: slice needs SignalEnvelope, entity/relationship/lineage claim types, GraphReader/Writer, one operator per category (minimal params), one ProjectionPlan, ContextProductContract + gates, replay record, minimal Control Plane registry surface.
   - Recommendation (Claude's discretion, granted): exactly that list; defer DebtFactorScorer/TrustScorer, fidelity-lifecycle, re-hydration, closed-loop types to their subsystem waves. Note D-IMPL-44 re-hydration and D-IMPL-50 lifecycle are §2B.5 components — planner should decide whether they're I.1 scope or flagged; FABR-06 names "record + engine," and FEASIBILITY lists them as I.1-adjacent components — recommend a late I.1 subsystem plan covering hash-verified re-hydration test class (FEAS-03 D-09 row) at minimum against the file-backed store.
2. **Banking fixture ontology specifics** — Claude's discretion; recommend counterparty/facility/guarantee/covenant topology per whitepaper INV-CH7-20 (it is the whitepaper's own worked domain, so fidelity review is easy), with values exclusively in YAML fixture artifacts.
3. **CINV-04 partial applicability in I.1** — HITL/workflow/skill capture checks can't run until I.2/I.4. Recommend: harness scaffold with the product-serve replay check + boot check active, and explicit `not-yet-applicable` markers the gate review can read (avoids a false "CINV-04 green" claim).

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | D-IMPL-01 | ✓ | 3.12.3 | — |
| Docker | testcontainers Postgres (D-10) | ✓ | 29.2.1 | — |
| Local Postgres server | — | ✗ (not needed) | — | testcontainers provides it |
| GitHub Actions | CI (D-09) | ✓ (private repo exists per §2.2) | — | — |
| pip/PyPI access | installs | ✓ (verified during audit) | — | — |

**Blocking gaps:** none. Note: local pip is PEP-668 externally-managed — project work must use a venv (standard for the pyproject scaffold anyway).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + hypothesis 6.161.5 (none installed yet — Wave 0/1 gap) |
| Config file | none — lands in Wave 1 pyproject scaffold |
| Quick run command | `pytest tests -x -q -m "not postgres and not chroma"` (markers per D-16) |
| Full suite command | `pytest tests -q` (+ `tools/lints` runner + `mypy --strict src`) |

### Phase Requirements → Test Map
| Req | Behavior | Test type | Automated command | Exists? |
|-----|----------|-----------|-------------------|---------|
| FABR-01 | six GraphStore semantics on both backends | parametrized conformance suite | `pytest tests/conformance/test_graphstore.py` | ❌ Wave 0/slice (TDD per D-15) |
| FABR-02 | composition-preservation, all pairs | Hypothesis property harness | `pytest tests/properties/test_composition.py` | ❌ subsystem wave |
| FABR-03 | staged == direct composition (D-08 class 2) | property harness class 2 | same harness | ❌ subsystem wave |
| FABR-04 | three gate rejection paths + MAX_TTL registration failure | contract unit tests | `pytest tests/gates/` | ❌ TDD-first |
| FABR-05 | zero hard-coded tables; values from Control Plane | CINV-01b lint + missing-value-fails tests | lint runner | ❌ Wave 1 |
| FABR-06 | replay write precedes delivery; hash-resolved versions | CINV-04 harness + rehydration hash test | `pytest tests/replay/` | ❌ |
| FABR-07 | versioned registry, append-only mapping | unit tests | `pytest tests/controlplane/` | ❌ |
| FABR-08 | ArtifactStore Protocol conformance (file impl) | conformance suite | `pytest tests/conformance/test_artifactstore.py` | ❌ |
| FABR-09 | change events → valid envelopes → graph via L2 only | integration test on slice | `pytest tests/integration/test_cdc_slice.py` | ❌ |
| CINV-01..03 | lints reject violating fixtures, pass clean tree | lint unit tests + CI jobs | `pytest tools/lints/tests && python -m tools.lints` | ❌ Wave 1 (D-07: blocking from first commit) |
| CINV-04 | replay-before-transition + exactly-one-writer boot | test harness + boot check | `pytest tests/invariants/` | ❌ |

### Sampling Rate
- **Per task commit:** quick run + lint runner.
- **Per wave merge:** full suite incl. Postgres leg (testcontainers or service container) + `mypy --strict`.
- **Phase gate:** D-17 bar — the FEAS-03 per-invariant checklist (FEASIBILITY.md §11 table) fully green, each row mapped to a named passing test/lint; coverage reported informationally only.

### Wave 0 Gaps
- [ ] Entire test infrastructure (pyproject, pytest/hypothesis/mypy config, markers `postgres`/`chroma`) — Wave 1 scaffold per D-05
- [ ] `tools/lints/` checkers + allowlist.yaml + their unit tests — Wave 1, blocking (D-07)
- [ ] `.github/workflows/ci.yml` with lint jobs + test matrix + postgres service container — Wave 1 (D-09)
- [ ] `tests/fixtures/banking/` fixture artifacts (YAML ontology/events) — slice wave (D-02/D-03)

## Security Domain

Internal SDK, no network surface in I.1 (HTTP/MCP/A2A arrive in I.3/I.4). Applicable now:

| ASVS category | Applies | Control |
|---------------|---------|---------|
| V4 Access control | yes (tenancy) | `(tenant_id, entity_uri)` compound uniqueness at persistence tier; kw-only `tenant_id` on every execute call (D-IMPL-05); no untenanted path |
| V5 Input validation | yes | Pydantic `extra=forbid` at every boundary; three gates as structured refusal |
| V6 Cryptography | yes (integrity) | `hashlib.sha256` content addressing only — no hand-rolled crypto; signing is I.3 (D-IMPL-15) |
| V1/V10 supply chain | yes | slopcheck-audited deps (table above); pin exact versions; chromadb optional extra; never commit secrets (CLAUDE.md §2.2) |

| Threat (project threat model) | Mitigation in I.1 |
|------------------------------|-------------------|
| T-02-26 second writer via store | no store→L3 path; D-IMPL-41 stack + boot check |
| SQL injection in backends | parameterized queries only in GraphStore impls (never f-string SQL — also keeps CINV-01 quiet) |
| Cross-tenant leakage | tenant-scoped conformance tests: reads never cross `tenant_id` |

## Sources

### Primary (HIGH confidence)
- `docs/DESIGN.md` §2A, §2B, §7, §9 (contract signatures, invariant table, CINV-01..04 designs) — the authoritative planning input
- `docs/FEASIBILITY.md` §10–§12 (verdicts, FEAS-03 per-invariant table, gate-list check)
- `docs/ROADMAP.md` Milestone I.1 (scope + risk highlights); `.planning/ROADMAP.md` Phase 4
- `04-CONTEXT.md` (Dave's 17 locked decisions)
- CLAUDE.md rev 4 (§5, §6.4, §7.4, §10, §11, §3.1)
- PyPI registry via `pip index versions` + slopcheck install run, 2026-07-25 (all versions in Standard Stack)
- Local environment probes (Python 3.12.3, Docker 29.2.1)

### Secondary (MEDIUM confidence)
- Pydantic v2 ConfigDict pattern, typing.Protocol (PEP 544), SQLite/Postgres `ON CONFLICT` parity — stable, long-standing APIs from training knowledge, consistent with verified current versions

### Tertiary (LOW confidence — flagged in Assumptions Log)
- mypy 2.3 flag surface, chromadb 1.5 client API details, sqlite-vec 0.1.9 API details — verify at the relevant wave's start

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package version registry-verified + slopcheck-clean today
- Architecture: HIGH — fully specified by resolved Phase D design; research adds implementation patterns only
- Pitfalls: MEDIUM-HIGH — drawn from design risk notes (FEASIBILITY) plus engineering judgment on determinism/lint calibration

**Research date:** 2026-07-25
**Valid until:** ~2026-08-25 (stable stack; re-verify chromadb/sqlite-vec/mypy specifics at their waves)
