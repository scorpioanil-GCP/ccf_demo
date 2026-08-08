# REQUIREMENTS — CCF SDK v0.2

**Milestone:** v0.2 Performance, Documentation & Demonstration
**Defined:** 2026-08-01
**Prior milestone:** v0.1 (shipped 2026-07-31, tag `v0.1.0`) — see `.planning/milestones/v0.1-REQUIREMENTS.md`

## v0.2 Requirements

### Hardening (HARD)

- [ ] **HARD-01**: The D-IMPL ruling batch (WR-01 mapping shape, ApprovalGate×D-16 composition, perf governance, docs toolchain/publishing, D-10 amendment, create_app warning) is surfaced to Dave as one Phase D mini-cycle and rulings logged in `docs/DECISIONS.md`
- [ ] **HARD-02**: In-memory HITL transports are thread-safe with a documented Protocol concurrency contract and a passing stress test (WR-02)
- [ ] **HARD-03**: ADK workflow driver is loop-safe (no nested `asyncio.run`) with typed errors and cross-adapter parity tests (WR-03)
- [x] **HARD-04**: HITL doors enforce per-tenant authorization per Dave's WR-01 ruling — deny-by-default, typed 403, authz decision in the audit record, cross-door × cross-action test matrix (WR-01)
- [x] **HARD-05**: ApprovalGate.resolve × signed_binding_required composed per Dave's ruling; create_app emits a loud warning on insecure default posture

### Performance (PERF)

- [x] **PERF-01**: Adopter can run `make perf` locally and get a reproducible micro-benchmark suite (operators, factory, validation gates) with p50/p95/p99
- [x] **PERF-02**: Fabric load/scale curves measure assembly and projection across graph sizes via a deterministic, domain-neutral synthetic dataset generator (built through L2/factory paths)
- [x] **PERF-03**: Cross-process latency (MCP egress, A2A/peering) and replay-at-scale suites prove the year-scale replay claim empirically
- [x] **PERF-04**: Committed runner-class-keyed baselines + `thresholds.toml` with relative-median regression gating in an opt-in `perf.yml` CI job; re-baseline ritual documented

### Documentation (DOCS)

- [ ] **DOCS-01**: Adopter's guide — day-1-to-production narrative (install → ontology → agent → workflow → replay)
- [ ] **DOCS-02**: Generated Protocol/API reference from citation-bearing docstrings (mkdocs-material + mkdocstrings), whitepaper never published
- [ ] **DOCS-03**: Definition-artifact schema reference — the adopter's primary authoring API
- [ ] **DOCS-04**: How-to guides + concepts pages (pillars, invariants, replay anatomy, whitepaper cross-reference index)
- [ ] **DOCS-05**: Security & deployment notes + OpenAPI polish with drift check
- [ ] **DOCS-06**: `make docs --strict` builds in always-on CI (logged D-10 amendment); PERFORMANCE.md publishes measured baselines with methodology

### Demonstration (DEMO)

- [x] **DEMO-01**: A synthetic fake data store — deterministic, multi-entity, domain values entirely in definition artifacts — ships as the demonstration substrate
- [x] **DEMO-02**: An end-to-end runnable example: data ingested through L1→L2, folded into the Context Graph, projected into typed Context Products, consumed by an agent that solves a concrete reasoning problem it could not solve from raw data alone
- [x] **DEMO-03**: A narrated walkthrough document in the docs site tracing the demo step-by-step ("how data folds into context"), literal-including the example's code and artifacts; demo runs in CI like the v0.1 examples

### Examples (EXAM)

- [ ] **EXAM-01**: Every v0.1 example (00–07) has a detailed narrated README — what it demonstrates, artifact-by-artifact explanation, whitepaper/CLAUDE.md sections exercised, and "what to change first to adapt it"
- [ ] **EXAM-02**: Example scenarios are enriched to exercise more of the SDK surface (specialization axes, skilling, HITL, replay) through richer definition artifacts — example code stays thin and generic per No-Hardcoding
- [ ] **EXAM-03**: The upgraded suite stays CI-green with a single documented command per example; any expected-output change is a reviewed, deliberate event
- [x] **EXAM-04**: An external agent with zero CCF imports client-side consumes typed Context Products, lineage, and the replay record over the authenticated MCP surface, deterministically in CI, across bare-MCP, Anthropic-SDK, and Google-ADK legs (family charter + `examples/external/00-hello-context`)
- [x] **EXAM-05**: The external-consumer example is hardened against the four-AI consensus concerns — live-captured diff-reviewed fixtures with a schema guard and request-fingerprint replay matching, a server-side tool allowlist, byte-path/README/duration assertion hardening — and the three external-consumption tools (`get_context`, `get_lineage`, `get_replay_record`) are promoted into the SDK Experience surface, enabled by default

### SDK Ergonomics (ERGO)

- [x] **ERGO-01**: A committed public-surface signature manifest + `make surface` regenerator + CI drift assertion, baselined at phase start before any surface change
- [x] **ERGO-02**: A standing gate-independence guard — `run_gates` keeps two independently sourced inputs, enforced by a perturbation regression test, an AST identifier guard over `src/ccf/deployment/`, and a no-allowlist lint ban on `ccf.deployment` importing `ccf.products.gates`
- [x] **ERGO-03**: The criterion-1 surface audit is an executable check recording per-example mechanical line counts before and after, reporting relocation and removal as separate figures
- [x] **ERGO-04**: `ccf.deployment` exists in `/src`, algorithmic-tagged, `mypy --strict`-clean, with a docstring recording the CINV-03 reading ("no model call, not no I/O") and the `run_gates` worked example
- [x] **ERGO-05**: A class-id → `ArtifactClass` lookup covering SDK-shipped classes with `declared_artifact_class` fallthrough, kept in sync with `artifacts.__all__` by test
- [x] **ERGO-06**: Timestamp-shaped scalars load as strings and parse via `datetime.fromisoformat`; PyYAML's resolver is suppressed in the artifact path; designator-less timestamps refused naming D-IMPL-38
- [x] **ERGO-07**: `ccf.resolution-spec` — a closed-world typed artifact class over entity and relationship rules, with `EntityResolutionSpec` gaining `semver` in place (D-IMPL-77) and its own regeneration checkpoint
- [x] **ERGO-08**: A typed `ArtifactClass` per SDK-shipped operator category contracted by the existing `*Parameters` models; `DeclaredArtifact` remains the documented path for deployment-authored operators; both `artifacts.py` docstring sites amended
- [x] **ERGO-09**: Typed artifact classes for the signal batch, perspective, and product-class declaration
- [x] **ERGO-10**: A `ccf.deployment-manifest` artifact class enumerating every artifact explicitly (path, key, class), and one call that loads, validates, registers, and boots — returning the `FabricHandle` plus a plain typed pin set; backend kind declared in the manifest, connection supplied by the caller
- [x] **ERGO-11**: A two-phase, view-aware operator-registry builder taking artifacts plus a `GraphView`, with the ordering constraint in the signature and the policy pin supplied by the adopter (D-IMPL-76)
- [x] **ERGO-12**: `ccf schema export` emits JSON Schema per artifact class via a new HTTP route (D-IMPL-79); schemas are committed, example artifacts carry `$schema` headers, and a CI freshness gate guards drift
- [x] **ERGO-13**: Examples 00–03, 07, 08 are rewritten to the streamlined surface and stay CI-green
- [x] **ERGO-14**: Examples 04 (both files, including D-10's re-domaining to banking as a separate commit), 05, and 06 are rewritten and stay CI-green
- [x] **ERGO-15**: `examples/external/00-hello-context/serve.py` is rewritten to the streamlined surface; the client legs keep zero CCF imports
- [x] **ERGO-16**: Every example's CI assertions and print summaries relocate to a parallel `tests/` module with no loss of assertion coverage, and the No-Hardcoding Rule reaches the relocated domain values (D-IMPL-78 — `tests` added to both `LINTED_TREES` and `RULE_TREE_SCOPE`)
  - **Ruled at D-GATE-15 (Dave, 2026-08-05): "every" takes the qualified reading, and the requirement is met as written** — "every example *driver*'s assertions and print summaries relocate, **except** where relocation would move an assertion somewhere nothing runs it, or would break a test the plan was forbidden to touch." Raised as blocking finding B-2 at the phase-close review (codex) because the requirement's checkbox and the delivered measurement disagreed with nothing in between. The 152 residual relocatable lines are exactly the principled exception set, accounted for line by line in `docs/SURFACE-AUDIT.md` §2.3: 65 in files that are not example drivers (incl. the three client legs whose zero CCF imports ERGO-15/EXAM-04 rest on, asserted byte-unchanged), 54 inside example 03's opt-in `_live` leg that `make ci` excludes by D-11, 22 pinned by `tests/examples/test_ext00_hardening.py`'s `PASS 1:`–`PASS 8:` subprocess assertions in a module 15-20 was forbidden to modify, 4 `READY <port>` process-protocol handshakes, and 6 in `08-e2e-demo` where DEMO-03's byte-compared transcript *is* the deliverable. **No exception entry is required**; §2.3 is the accounting of record. Rejected: the literal reading, which would have marked ERGO-16 unmet and required a recorded departure, and the literal-and-close-the-gap reading, which would have reopened two out-of-scope modules.
- [x] **ERGO-17**: A curated surface-change log with rationale and migration guidance, written incrementally as per-plan fragments, covering additions, reshapes, removals **and behavior changes**, handed to Phase 16
- [x] **ERGO-18**: A deployment manifest declares each entry's registration mode (`registration: typed | versioned`), `load_and_boot` dispatches on it, and a manifest that routes an author-versioned SDK class through typed registration — or squats a `ccf.`-prefixed class id with an open envelope — is refused at load, proven by tests that assert the refusal fires rather than that the examples avoid the pattern (CR-1; D-IMPL-82/83/84/85)
- [x] **ERGO-19**: The operator set a deployment declares and the set its projection executes come from two separately authored Control Plane artifacts bound by a binder placed between plan construction and `ProjectionEngine.execute` that refuses when they disagree; Gate 2 is documented as the assembly-path-integrity check it is (CR-2; **D-IMPL-86 and its 2026-08-05 correction**, design E2)
  - **Both checked at D-GATE-15.1 (Dave, 2026-08-05), clause by clause against the tree rather than against the SUMMARYs that reported them.** ERGO-18's five clauses: `ManifestEntry.registration` is `Literal["typed","versioned"]`, required with no default (`src/ccf/controlplane/artifacts.py:759`); `load_and_boot` dispatches on it with no fallback to `register_typed` (`src/ccf/deployment/manifest.py:335`); and four tests assert the *refusal fires* rather than that the examples avoid the pattern — `test_an_author_versioned_class_declared_typed_registration_is_refused`, `test_an_envelope_squat_on_an_sdk_class_id_is_refused`, `test_the_ccf_namespace_reservation_is_wide_not_a_four_id_list`, `test_a_manifest_entry_naming_no_registration_is_refused` (6 collected, 6 passed, each watched to fail with the source reverted). ERGO-19's four clauses: two separately authored artifacts (nine `artifacts/projection-requirements.yaml` documents, distinct from the product-class artifact); the binder placed between plan construction and `ProjectionEngine.execute` (verified at `examples/00-quickstart/run.py` — plan at `:231-234`, binder at `:235`, `.execute(` at `:238`); refusal on disagreement (`refuse_operator_set_divergence`, `tests/deployment/test_binder.py` + the tripwires — 32 passed, watched to fire at all nine example sites from a one-key edit to *either* document); and Gate 2 documented as assembly-path integrity at eight-plus sites, with a two-vocabulary sweep confirming every surviving mention of the corrected-away claim in `src/`, `runtime/`, `tests/`, `examples/` and `public/` is a negation. **The residuals the gate carried forward — R-2 the binder's placement, R-3 its authorship, R-4 the HTTP `/schema` route — are open and unclosed**; neither requirement's text asserts them closed, which is why both are met as written.
  - **UNCHECKED 2026-08-06, then RE-CHECKED 2026-08-06.** The gate above was **withdrawn** (`D-GATE-15.1 (withdrawal, 2026-08-06)`) and both requirements returned to `Pending`, because the code review the workflow runs *after* the phase gate returned 3 verified Criticals — one of them (**CR-02**) a test that claimed four keys and asserted over three while the fourth took the path the test said it must not, which is this requirement pair's own defect class inside the phase convened to close it. Five review rounds followed (Criticals **3 → 1 → 1 → 1 → 0**), closed by plans 15.1-11 … 15.1-17, and Dave **re-approved on 2026-08-06** (`D-GATE-15.1 (re-approved, 2026-08-06)`). **Both requirements are re-checked only after re-verifying every clause against the tree as it stands now** — not against the 2026-08-05 verification above, whose line numbers the CR-01 fix has since moved, and not against any SUMMARY. **ERGO-18, clause by clause, observed 2026-08-06:** `RegistrationMode = Literal["typed", "versioned"]` (`src/ccf/controlplane/artifacts.py:681`) and `ManifestEntry.registration: RegistrationMode` (`:833`) — a bare annotation, so required with no default; `load_and_boot` dispatches at `src/ccf/deployment/manifest.py:436` (`if entry.registration == "versioned":`) with the `isinstance(outcome, RegistrationRefusal)` narrowing raising loudly and an in-code comment stating there is **deliberately no fallback** to `register_typed`; the refusal runs in preflight at `src/ccf/deployment/manifest.py:407` (`refuse_registration_the_sdk_fixes`, defined at `src/ccf/deployment/classes.py:243`), applied to **every** entry before any document is read; the `ccf.` reservation is a **prefix** test (`_CCF_NAMESPACE = "ccf."` at `classes.py:124`, used at `:330`), not an id list. Refusal tests re-run at the re-approval: `pytest tests/deployment/test_manifest.py -k "registration or squat or namespace_reservation"` → **6 passed, 31 deselected**, and they assert the refusal *fires* rather than that the examples avoid the pattern. **ERGO-19, clause by clause, observed 2026-08-06:** **nine** `artifacts/projection-requirements.yaml` documents (00, 01, 02, 03, 04, 06, 07, 08, `external/00`), separately authored from the product-class artifact; the binder placed between plan construction and `ProjectionEngine.execute` — re-verified at `examples/00-quickstart/run.py`, plan at `:231-234`, `refuse_operator_set_divergence` at `:235`, `.execute(` at `:238`; the refusal itself, `src/ccf/deployment/binder.py::refuse_operator_set_divergence`, whose signature is `(*, declared, plan) -> None` and whose module imports exactly two names and so holds no graph handle; and Gate 2 documented as **assembly-path integrity** at seven sites in `src/`, `public/` and the generated schema, with a two-vocabulary sweep of `src/`, `runtime/`, `examples/`, `tests/` and `public/` returning **20** occurrences of "independent witness" / "two independent sources" and **every one a negation or a quoted-then-answered superseded claim**. Tests re-run: `tests/deployment/test_binder.py` **5 passed**, `tests/products/test_gate_two_call_shape.py` **62 passed**, `tests/examples/test_gate_two_divergence.py` **2 passed**. **What the re-approval does NOT assert closed**, and what neither requirement's text claims: R-2, R-3 and R-4 stay open, and the fifth review's **R5-WR-01** (`_Binding.until` covers the comprehension's outermost iterable) and **R5-WR-02** (the unrun table cell, corrected in place) are accepted as recorded **open** residuals, alongside **R4-WR-03** (loop-carried rebinding), the augmented-assignment mutable-set opacity, the attribute/subscript limit, **IN-F1/IN-F2/IN-F4**, and the incomplete stale-claim sweep — whose remaining scope is **not** restated here, because restating it is how it under-counted five times: `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md` is authoritative and carries the measured tree list (amended 2026-08-06, plan 15.1-20, after `public/` and `tools/` were closed). All residuals are enumerated there with their source review documents. Both requirements are met **as written**; none of their clauses asserts any of those residuals closed.

### Substrate Query (SUBQ)

- [ ] **SUBQ-01**: The normative query-semantics prose (`docs/GRAPH_QUERY_SEMANTICS.md`) exists with stable backticked GQ-NN clause anchors and a semver lane from day one (v1 including `allowed_entities` per D-12), deciding every named edge semantic — including the uniform rule and the induced-subgraph rule — with no implementation-defined escape hatches (D-05 artifact 1, D-12)
- [x] **SUBQ-02**: The frozen `GraphQuery` contract family — including `allowed_entities: frozenset | None`, sentinel-defaulted (D-02 extended) — and the `GraphReader.query()` seam ship with canonical ordering and serialization owned by the interface, never the adapter, and `content_hash(GraphQuery)` as the per-round-trip replay pin
- [x] **SUBQ-03**: `ccf.graph.fallback` is the reference implementation of the prose — including `allowed_entities` set-intersection semantics — with docstrings citing GQ clauses in the lint-verified anchored form, and adapters always answer with no capability negotiation (D-04, D-05 artifact 2)
- [x] **SUBQ-04**: The two conformance suites ship — differential byte-identity against the fallback over a generated corpus that includes `allowed_entities`-bearing shapes, plus property assertions (INV-CH7-14/-23/-24/-26, each mapped to the property that actually asserts it) running on the fallback itself, so the oracle is audited by something it does not define (D-05 artifact 3)
- [x] **SUBQ-05**: The `Operator` Protocol gains the optional `read_intent()` pushability declaration, with the `apply(full_view) == pushed(intent)` equivalence proven per shipped operator, the pushability matrix pinned by test, and `SimilaritySelect` not pushable (D-03)
- [x] **SUBQ-06**: Engine-owned multi-segment segmentation per the D-IMPL-87 resolution — one query per pushable segment, post-in-process segments carrying survivors as seeds + `allowed_entities` under the uniform rule, a survivor-set size-cap mechanism whose value is Control Plane configuration defaulting to `None` (D-10), per-plan equivalence proven on Similarity-bearing plans, the executed query-hash sequence pinned into the replay record from execution with full canonical query bytes in the ArtifactStore keyed by hash (D-11), and `SnapshotReader.query()` scope-checked for replay (D-01 amended)
- [x] **SUBQ-07**: `as_of()` is derived from `query()` as the degenerate everything-question, with zero churn across all 15 existing call sites (D-07)
- [x] **SUBQ-08**: Five adapters — sqlite, postgres, memory, neo4j, mongo — answer `GraphQuery` including native `allowed_entities` translation under both suites, with memory always-on in `make ci` and neo4j/mongo extras-gated behind container-gated CI legs (D-06); Mongo conformance via the sanctioned D-04 degrade posture (`$match` narrowing + fallback traversal, plan 15.2-13 stage 1) satisfies this requirement — `$graphLookup` promotion is a budgeted enhancement recorded for ratification, not part of the requirement
- [x] **SUBQ-09**: `ProductSource` mounts only an `AdmittedProduct`, refuses a payload without graph-shaped state at mount with a typed refusal, passes the same differential suite, and nothing enters L3 (D-08)
- [x] **SUBQ-10**: The `SourceAttestation` contract ships with per-dimension modes, product-class accepted modes (D-09's "minima", realized as unordered accepted-mode sets — no strength ordering exists between modes), an engine refusal naming the failing dimension, and the attestation in force pinned into replay (D-09)
- [ ] **SUBQ-11**: The substrate-neutral write seam — `BaseGraphWriter` driving typed transaction operations implemented per backend inside `ccf.graph._writer` — preserves single-writer (INV-CH7-10/CINV-02) for all five backends

## Future Requirements (deferred)

- Perf SaaS/dashboarding integration
- Docs hosting/publishing decision (beyond CI build)
- HTTP load testing (locust/k6)
- RBAC/policy engine for the HTTP door; OIDC provider integration
- 55MB-blob history rewrite

## Out of Scope

- Absolute-time perf gates on shared runners — flake by construction; relative-median thresholds only
- Hand-written API signatures or pasted snippets in docs — generated reference and literal-includes only (drift prevention)
- Domain values in demo/example code — No-Hardcoding Rule (CLAUDE.md §6.4); everything domain-specific in definition artifacts
- Defaulting any of the six Dave-ruling items — implement per rulings only

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARD-01 | Phase 9 | Pending |
| HARD-02 | Phase 9 | Pending |
| HARD-03 | Phase 9 | Pending |
| HARD-04 | Phase 10 | Complete |
| HARD-05 | Phase 10 | Complete |
| PERF-01 | Phase 11 | Complete |
| PERF-02 | Phase 11 | Complete |
| PERF-03 | Phase 11 | Complete |
| PERF-04 | Phase 11 | Complete |
| DEMO-01 | Phase 12 | Complete |
| DEMO-02 | Phase 12 | Complete |
| DEMO-03 | Phase 12 | Complete |
| EXAM-01 | Phase 13 | Pending |
| EXAM-02 | Phase 13 | Pending |
| EXAM-03 | Phase 13 | Pending |
| EXAM-04 | Phase 13.1 | Complete |
| EXAM-05 | Phase 13.2 | Complete |
| DOCS-01 | Phase 14 | Pending |
| DOCS-02 | Phase 14 | Pending |
| DOCS-03 | Phase 14 | Pending |
| DOCS-04 | Phase 14 | Pending |
| DOCS-05 | Phase 14 | Pending |
| DOCS-06 | Phase 14 | Pending |
| ERGO-01 | Phase 15 | Complete |
| ERGO-02 | Phase 15 | Complete |
| ERGO-03 | Phase 15 | Complete |
| ERGO-04 | Phase 15 | Complete |
| ERGO-05 | Phase 15 | Complete |
| ERGO-06 | Phase 15 | Complete |
| ERGO-07 | Phase 15 | Complete |
| ERGO-08 | Phase 15 | Complete |
| ERGO-09 | Phase 15 | Complete |
| ERGO-10 | Phase 15 | Complete |
| ERGO-11 | Phase 15 | Complete |
| ERGO-12 | Phase 15 | Complete |
| ERGO-13 | Phase 15 | Complete |
| ERGO-14 | Phase 15 | Complete |
| ERGO-15 | Phase 15 | Complete |
| ERGO-16 | Phase 15 | Complete |
| ERGO-17 | Phase 15 | Complete |
| ERGO-18 | Phase 15.1 | Complete |
| ERGO-19 | Phase 15.1 | Complete |
| SUBQ-01 | Phase 15.2 | Pending |
| SUBQ-02 | Phase 15.2 | Complete |
| SUBQ-03 | Phase 15.2 | Complete |
| SUBQ-04 | Phase 15.2 | Complete |
| SUBQ-05 | Phase 15.2 | Complete |
| SUBQ-06 | Phase 15.2 | Complete |
| SUBQ-07 | Phase 15.2 | Complete |
| SUBQ-08 | Phase 15.2 | Complete |
| SUBQ-09 | Phase 15.2 | Complete |
| SUBQ-10 | Phase 15.2 | Complete |
| SUBQ-11 | Phase 15.2 | Pending |

Coverage: 53/53 v0.2 requirements mapped, each to exactly one phase.
ERGO-18 and ERGO-19 were minted during Phase 15.1 planning under the Phase 15/16
precedent already stated in `.planning/ROADMAP.md` §Coverage — an inserted phase
mints its own requirement IDs at planning rather than borrowing a predecessor's —
and ERGO-01..17 stay Complete because Phase 15.1 closes defects in what they
delivered rather than reopening them.
SUBQ-01..SUBQ-11 were minted at Phase 15.2 planning, plan 15.2-01 (2026-08-07),
under the same inserted-phase precedent, with texts amended per the D-IMPL-87
resolution (multi-segment pushdown: `allowed_entities` under the uniform rule,
the Control-Plane-valued size cap, the hash+ArtifactStore replay pin,
prose-lane vocabulary versioning). The pre-amendment texts never landed — the
void 13-plan set drawn against pre-amendment D-01 was not executed, so this
minting is the first and only appearance of the SUBQ IDs.
ERGO-01..ERGO-17 marked Complete at the Phase 15 close (plan 15-21); the
evidence for each is `docs/SURFACE-AUDIT.md` and the per-plan SUMMARYs under
`.planning/phases/15-sdk-ergonomics-the-integration-surface/`. Marking them
Complete records that the phase's own gates are green — it is not the phase
gate, which is Dave's approval and the `D-GATE-15` entry in `docs/DECISIONS.md`
(CLAUDE.md §3.1).
ERGO-18 and ERGO-19 were marked Complete **after** the Phase 15.1 gate, not
before it: Dave approved on 2026-08-05 (`D-GATE-15.1`), and the clause-by-clause
re-verification recorded under ERGO-19 above was done against the tree at that
point. Checking a requirement before the gate that authorizes it would be the
same overclaim Phase 15.1 exists to close.
That approval was **withdrawn on 2026-08-06** and both requirements were returned
to `Pending`; they are Complete again on the **re-approval** of 2026-08-06
(`D-GATE-15.1 (re-approved, 2026-08-06)`), after five review rounds took the
phase's Critical count from **3 → 1 → 1 → 1 → 0** and after every clause of both
requirements was re-verified against the tree as it stands, not against the
2026-08-05 verification whose line numbers the CR-01 fix has since moved. The
withdrawal is preserved here rather than smoothed over, because the reason for it
is a process fact Phase 16 must not repeat: the `code_review_gate` runs **after**
the phase gate, so a human can be asked to approve a phase before any code review
of that phase exists. A gate presentation should carry its code review.
