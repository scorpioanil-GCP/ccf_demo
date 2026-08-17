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
- [ ] **DOCS-07**: The Phase 16 ruling package — `D-IMPL-94` records the Mode 2 attachment point above `serve()` and what `assembly_mode` describes, plus the criterion-10 carve-out, the Gate-2 tripwire carry-forward with its two-limb bound, and the ERGO-03 freeze — with no accompanying source diff
- [ ] **DOCS-08**: The three pre-existing gate-checker failures are green and `make ci` composes `tools/lints/tests`, `tools/publish_scan_tests` and `tools/docs_tests`, so its "full local reproduction of the always-on pipeline" claim is true rather than aspirational
- [ ] **DOCS-09**: The KYC/UBO enterprise source estate carries corp→corp `hasOwnershipInterestIn` edges with per-edge `ownershipPercent`, generated deterministically from a definition artifact, written to the source estate and never to CCF's L3, so "Who ultimately owns Acme?" has a chain to traverse
- [ ] **DOCS-10**: **One** example driver resolves its backend from a supplied configuration artifact — the substrate name from `DeploymentManifest.backend` and the `connection=` field/env-var shape from a declarative backends document, never from a per-backend code fork and never from a value baked into the driver — and a CI matrix asserts `content_hash` equality of the served Context Product across `sqlite`, `memory`, `postgres`, `neo4j`, `mongo` and `fluree`, with `sqlite`+`memory` always-on and network-free, the four DGX databases opt-in, and no credential in the tree
- [ ] **DOCS-11**: Every example physically separates the CCF call spine from deployment code into distinct modules carrying the canonical ordered marker set, legible to a repository reader rather than only to the rendered site
- [ ] **DOCS-12**: Section 1 ships agent-free deterministic examples and published pages teaching Context Products, the four Context Operator categories and the six axes of `G(E, R, T, P, Π, L)`, introducing `assembly_mode: algorithmic` as a governance choice with two siblings named as Phase 17's
- [ ] **DOCS-13**: Section 2 ships external client legs for the Claude Agent SDK, Google ADK and LangGraph that import nothing from `ccf`, asserted by an AST matcher with a negative control and an exactly-three-harnesses assertion, plus their published pages
- [ ] **DOCS-14**: Section 3 ships embedding CCF in a host application (in-process, MCP egress, A2A admission, ArtifactStore swap) and developing agentic skills within CCF, plus their published pages, stating plainly that SDK agents are governed identity and are structurally barred from calling a model
- [ ] **DOCS-15**: An adoption-argument page names RAG over a vector store, hand-rolled context assembly, and a semantic layer plus prompt templates, and states what each lacks against cited shipped mechanism, with the UBO question as its worked demonstration and the passage-anchor honesty caveat carried
- [ ] **DOCS-16**: Carried advisories A-1, A-2, A-3 and A-8 are discharged in the published tree with positive per-advisory evidence rather than a green build
- [ ] **DOCS-17**: `examples/00`–`08` and `examples/external/00-hello-context` are retired with every published page that sourced from them re-cut, proven by standing gates for dangling includes, stale prose paths, Gate-2 wording and documented commands
- [ ] **DOCS-18**: The phase closes with a mechanical no-fabric-change assertion carrying D-13's single enumerated exception, a full gate sweep, and a requirement ledger that matches the tree
- [ ] **DOCS-19**: The four `D-IMPL-126` consumption papercuts are closed in the fabric — a `ProductRequestContract` is reachable from a manifest-returned `DeclaredArtifact` by one named call, `ServableProduct` states why it is unconstructible on both attribute channels while leaving `hasattr` returning `False`, a product-only deployment constructs `ApiDependencies` with three handles and gets a typed 503 naming the absent field on every route it did not wire, and every canonical HTTP body publishes its own content address under `X-CCF-Content-Address`
- [ ] **DOCS-20**: The MCP egress door carries a parameterised tool alongside its unchanged resource
- [ ] **DOCS-21**: The Experience MCP server's client-parameterised handlers are gated, or their ungated status is pinned
- [x] **DOCS-22**: `ProductDiscovery` carries a fourth axis, `audiences`, and the full surface obligation for a shipped §6.3 element is discharged (`D-IMPL-135`)
- [ ] **DOCS-23**: A single `ccf_config.yaml` is a typed, schema-exported authoring document whose unknown top-level keys are refused by name (`D-IMPL-136`)
- [ ] **DOCS-24**: Reserved sections derive `path`, `key`, `class_id`, `role` and `registration` for `ccf.*` classes, while adopter-owned sections still state `class_id`, `role` and `registration` (`D-IMPL-134`, `D-IMPL-136`)
- [ ] **DOCS-25**: A deployment authored in the single-file form registers artifacts at identical content addresses to the same deployment authored across files, and every existing multi-file deployment is unchanged (`D-IMPL-136` §10)

### Demonstration (DEMO)

- [x] **DEMO-01**: A synthetic fake data store — deterministic, multi-entity, domain values entirely in definition artifacts — ships as the demonstration substrate
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto `examples/s1-01-hello-context-product`'s deterministic source-estate generator. Not retired and not re-minted: the requirement is unchanged, the example carrying it moves.
- [x] **DEMO-02**: An end-to-end runnable example: data ingested through L1→L2, folded into the Context Graph, projected into typed Context Products, consumed by an agent that solves a concrete reasoning problem it could not solve from raw data alone
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto `examples/s3-02-agentic-skills`, which is where an agent consuming typed Context Products against a real use case now lives.
- [x] **DEMO-03**: A narrated walkthrough document in the docs site tracing the demo step-by-step ("how data folds into context"), literal-including the example's code and artifacts; demo runs in CI like the v0.1 examples
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto `public/tutorial/hello-ccf.md`, the narrated Section-1 walkthrough that replaces `demo-walkthrough.md`.

### Examples (EXAM)

- [ ] **EXAM-01**: Every v0.1 example (00–07) has a detailed narrated README — what it demonstrates, artifact-by-artifact explanation, whitepaper/CLAUDE.md sections exercised, and "what to change first to adapt it"
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto the seven-heading README of every new Section-1/2/3 example. The examples `00`–`07` retire under `DOCS-17`; the narrated-README obligation travels with the suite rather than dying with it.
- [ ] **EXAM-02**: Example scenarios are enriched to exercise more of the SDK surface (specialization axes, skilling, HITL, replay) through richer definition artifacts — example code stays thin and generic per No-Hardcoding
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto `examples/s3-02-agentic-skills`, the Section-3 example whose artifacts carry the specialization axes, skilling, HITL and replay surface.
- [ ] **EXAM-03**: The upgraded suite stays CI-green with a single documented command per example; any expected-output change is a reviewed, deliberate event
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto the `make example-s*` target surface, which is the single documented command per example for the rebuilt suite.
- [x] **EXAM-04**: An external agent with zero CCF imports client-side consumes typed Context Products, lineage, and the replay record over the authenticated MCP surface, deterministically in CI, across bare-MCP, Anthropic-SDK, and Google-ADK legs (family charter + `examples/external/00-hello-context`)
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto `examples/s2-01-external-consumers`, which carries the same zero-CCF-import claim across the three `D-09` harnesses.
- [x] **EXAM-05**: The external-consumer example is hardened against the four-AI consensus concerns — live-captured diff-reviewed fixtures with a schema guard and request-fingerprint replay matching, a server-side tool allowlist, byte-path/README/duration assertion hardening — and the three external-consumption tools (`get_context`, `get_lineage`, `get_replay_record`) are promoted into the SDK Experience surface, enabled by default
  - **[Phase 16 re-homing, `D-08`]** Re-homes onto `examples/s2-01-external-consumers`, alongside EXAM-04: the hardening obligations (diff-reviewed fixtures with a schema guard, request-fingerprint replay matching, a server-side tool allowlist, the three promoted Experience-surface tools) travel to the example that replaces `examples/external/00-hello-context`.

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
  - **Both checked at D-GATE-15.1 (Dave, 2026-08-05), clause by clause against the tree rather than against the SUMMARYs that reported them.** ERGO-18's five clauses: `ManifestEntry.registration` is `Literal["typed","versioned"]`, required with no default (`src/ccf/controlplane/artifacts.py::ManifestEntry`); `load_and_boot` dispatches on it with no fallback to `register_typed` (`src/ccf/deployment/manifest.py:335`); and four tests assert the *refusal fires* rather than that the examples avoid the pattern — `test_an_author_versioned_class_declared_typed_registration_is_refused`, `test_an_envelope_squat_on_an_sdk_class_id_is_refused`, `test_the_ccf_namespace_reservation_is_wide_not_a_four_id_list`, `test_a_manifest_entry_naming_no_registration_is_refused` (6 collected, 6 passed, each watched to fail with the source reverted). ERGO-19's four clauses: two separately authored artifacts (nine `artifacts/projection-requirements.yaml` documents, distinct from the product-class artifact); the binder placed between plan construction and `ProjectionEngine.execute` (verified at `examples/00-quickstart/run.py` — plan at `:231-234`, binder at `:235`, `.execute(` at `:238`); refusal on disagreement (`refuse_operator_set_divergence`, `tests/deployment/test_binder.py` + the tripwires — 32 passed, watched to fire at all nine example sites from a one-key edit to *either* document); and Gate 2 documented as assembly-path integrity at eight-plus sites, with a two-vocabulary sweep confirming every surviving mention of the corrected-away claim in `src/`, `runtime/`, `tests/`, `examples/` and `public/` is a negation. **The residuals the gate carried forward — R-2 the binder's placement, R-3 its authorship, R-4 the HTTP `/schema` route — are open and unclosed**; neither requirement's text asserts them closed, which is why both are met as written.
  - **UNCHECKED 2026-08-06, then RE-CHECKED 2026-08-06.** The gate above was **withdrawn** (`D-GATE-15.1 (withdrawal, 2026-08-06)`) and both requirements returned to `Pending`, because the code review the workflow runs *after* the phase gate returned 3 verified Criticals — one of them (**CR-02**) a test that claimed four keys and asserted over three while the fourth took the path the test said it must not, which is this requirement pair's own defect class inside the phase convened to close it. Five review rounds followed (Criticals **3 → 1 → 1 → 1 → 0**), closed by plans 15.1-11 … 15.1-17, and Dave **re-approved on 2026-08-06** (`D-GATE-15.1 (re-approved, 2026-08-06)`). **Both requirements are re-checked only after re-verifying every clause against the tree as it stands now** — not against the 2026-08-05 verification above, whose line numbers the CR-01 fix has since moved, and not against any SUMMARY. **ERGO-18, clause by clause, observed 2026-08-06:** `RegistrationMode = Literal["typed", "versioned"]` (`src/ccf/controlplane/artifacts.py::RegistrationMode`) and `ManifestEntry.registration: RegistrationMode` (`src/ccf/controlplane/artifacts.py::ManifestEntry`) — a bare annotation, so required with no default; `load_and_boot` dispatches (`src/ccf/deployment/manifest.py::load_and_boot`, `if entry.registration == "versioned":`) with the `isinstance(outcome, RegistrationRefusal)` narrowing raising loudly and an in-code comment stating there is **deliberately no fallback** to `register_typed`; the refusal runs in preflight inside the same function (`src/ccf/deployment/classes.py::refuse_registration_the_sdk_fixes`), applied to **every** entry before any document is read; the `ccf.` reservation is a **prefix** test (`_CCF_NAMESPACE = "ccf."` at `classes.py:124`, used at `:330`), not an id list. Refusal tests re-run at the re-approval: `pytest tests/deployment/test_manifest.py -k "registration or squat or namespace_reservation"` → **6 passed, 31 deselected**, and they assert the refusal *fires* rather than that the examples avoid the pattern. **ERGO-19, clause by clause, observed 2026-08-06:** **nine** `artifacts/projection-requirements.yaml` documents (00, 01, 02, 03, 04, 06, 07, 08, `external/00`), separately authored from the product-class artifact; the binder placed between plan construction and `ProjectionEngine.execute` — re-verified at `examples/00-quickstart/run.py`, plan at `:233-236`, `refuse_operator_set_divergence` at `:237`, `.execute(` at `:240` (all three re-measured 2026-08-09 at the Phase 15.4 close; each moved down two lines when D-10's `connection=` mapping replaced the per-database keyword in every example); the refusal itself, `src/ccf/deployment/binder.py::refuse_operator_set_divergence`, whose signature is `(*, declared, plan) -> None` and whose module imports exactly two names and so holds no graph handle; and Gate 2 documented as **assembly-path integrity** at seven sites in `src/`, `public/` and the generated schema, with a two-vocabulary sweep of `src/`, `runtime/`, `examples/`, `tests/` and `public/` returning **20** occurrences of "independent witness" / "two independent sources" and **every one a negation or a quoted-then-answered superseded claim**. Tests re-run: `tests/deployment/test_binder.py` **5 passed**, `tests/products/test_gate_two_call_shape.py` **62 passed**, `tests/examples/test_gate_two_divergence.py` **2 passed**. **What the re-approval does NOT assert closed**, and what neither requirement's text claims: R-2, R-3 and R-4 stay open, and the fifth review's **R5-WR-01** (`_Binding.until` covers the comprehension's outermost iterable) and **R5-WR-02** (the unrun table cell, corrected in place) are accepted as recorded **open** residuals, alongside **R4-WR-03** (loop-carried rebinding), the augmented-assignment mutable-set opacity, the attribute/subscript limit, **IN-F1/IN-F2/IN-F4**, and the incomplete stale-claim sweep — whose remaining scope is **not** restated here, because restating it is how it under-counted five times: `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md` is authoritative and carries the measured tree list (amended 2026-08-06, plan 15.1-20, after `public/` and `tools/` were closed). All residuals are enumerated there with their source review documents. Both requirements are met **as written**; none of their clauses asserts any of those residuals closed.

### Substrate Query (SUBQ)

- [x] **SUBQ-01**: The normative query-semantics prose (`docs/GRAPH_QUERY_SEMANTICS.md`) exists with stable backticked GQ-NN clause anchors and a semver lane from day one (v1 including `allowed_entities` per D-12), deciding every named edge semantic — including the uniform rule and the induced-subgraph rule — with no implementation-defined escape hatches (D-05 artifact 1, D-12)
- [x] **SUBQ-02**: The frozen `GraphQuery` contract family — including `allowed_entities: frozenset | None`, sentinel-defaulted (D-02 extended) — and the `GraphReader.query()` seam ship with canonical ordering and serialization owned by the interface, never the adapter, and `content_hash(GraphQuery)` as the per-round-trip replay pin
- [x] **SUBQ-03**: `ccf.graph.fallback` is the reference implementation of the prose — including `allowed_entities` set-intersection semantics — with docstrings citing GQ clauses in the lint-verified anchored form, and adapters always answer with no capability negotiation (D-04, D-05 artifact 2)
- [x] **SUBQ-04**: The two conformance suites ship — differential byte-identity against the fallback over a generated corpus that includes `allowed_entities`-bearing shapes, plus property assertions (INV-CH7-14/-23/-24/-26, each mapped to the property that actually asserts it) running on the fallback itself, so the oracle is audited by something it does not define (D-05 artifact 3)
- [x] **SUBQ-05**: The `Operator` Protocol gains the optional `read_intent()` pushability declaration, with the `apply(full_view) == pushed(intent)` equivalence proven per shipped operator, the pushability matrix pinned by test, and `SimilaritySelect` not pushable (D-03)
- [x] **SUBQ-06**: Engine-owned multi-segment segmentation per the D-IMPL-87 resolution — one query per pushable segment, post-in-process segments carrying survivors as `allowed_entities` with `seeds` `None` under the uniform rule, a survivor-set size-cap mechanism whose value is Control Plane configuration defaulting to `None` (D-10), per-plan equivalence proven on Similarity-bearing plans, the executed query-hash sequence pinned into the replay record from execution with full canonical query bytes in the ArtifactStore keyed by hash (D-11), and `SnapshotReader.query()` scope-checked for replay (D-01 amended)
- [x] **SUBQ-07**: `as_of()` is derived from `query()` as the degenerate everything-question, with zero churn across all 15 existing call sites (D-07)
- [x] **SUBQ-08**: Five adapters — sqlite, postgres, memory, neo4j, mongo — answer `GraphQuery` including native `allowed_entities` translation under both suites, with memory always-on in `make ci` and neo4j/mongo extras-gated behind container-gated CI legs (D-06); Mongo conformance via the sanctioned D-04 degrade posture (`$match` narrowing + fallback traversal, plan 15.2-13 stage 1) satisfies this requirement — `$graphLookup` promotion is a budgeted enhancement recorded for ratification, not part of the requirement
  - **Shipped outcome, recorded 2026-08-08 (plan 15.2-14):** the hedge in the text above was not needed — plan 15.2-13 shipped **stage 2, promoted with proof**, not the sanctioned degrade. `$graphLookup` traversal runs in the engine over a doubled-edge collection, with A3 (`restrictSearchWithMatch` accepts every plain-match predicate the hop filter needs, no `$expr`) verified against a live MongoDB 7.0.39 *before* any promotion code ran, and `translated_answers == 4 / fallback_answers == 0` asserted across the four Pitfall-3 trap shapes. The requirement text is left as minted rather than rewritten: the hedge was a deliberate risk instrument ("either outcome satisfies this"), and editing it after the fact would erase the record of a risk that was priced correctly. What Dave ratifies is the promotion, recorded in the design-choice register.
  - **Pushdown-vs-degrade proof completed 2026-08-08 (plan 15.2-14), on a BLOCKING §3.1 review finding.** Byte-identity to the fallback is a *conformance* bar, not a *pushdown* bar: D-04/`GQ-34` make the degraded posture byte-identical **by design**, so a `_translate_query` that always returned `None` would pass the entire differential corpus. SQL proved the push with `_pushed()` telemetry and Mongo with `translated_answers == len(queries)`; **Neo4j asserted neither** — the phase's strongest-pushdown-substrate claim rested on evidence that could not distinguish a working Cypher translation from an absent one. `tests/graph/test_neo4j_backend.py::test_cypher_traversal_is_pushed_not_silently_degraded` now asserts `translated_answers == 4 / fallback_answers == 0` across depth-0, depth-1, the out-then-in depth-2 path, and the resurrection shape, with the `memory` backend as the differential control. **Corrected 2026-08-08 (Dave's ruling, WARNING-1 from `15.2-VERIFICATION.md`; the sentence originally read "All five adapters now carry a push proof"):** the **four translating** adapters — sqlite, postgres, Neo4j, MongoDB — each carry a push proof, not merely a conformance proof. The **memory** backend carries no push proof by design and never will: it has no `_translate_query` and no telemetry counters, because it is the zero-engine floor (D-06) that answers everything through `ccf.graph.fallback` — which is exactly what qualifies it as the adversarial floor for the seam and as the differential control named above. All five carry the conformance proof.
- [x] **SUBQ-09**: `ProductSource` mounts only an `AdmittedProduct`, refuses a payload without graph-shaped state at mount with a typed refusal, passes the same differential suite, and nothing enters L3 (D-08)
- [x] **SUBQ-10**: The `SourceAttestation` contract ships with per-dimension modes, product-class accepted modes (D-09's "minima", realized as unordered accepted-mode sets — no strength ordering exists between modes), an engine refusal naming the failing dimension, and the attestation in force pinned into replay (D-09)
- [x] **SUBQ-11**: The substrate-neutral write seam — `BaseGraphWriter` driving typed transaction operations implemented per backend inside `ccf.graph._writer` — preserves single-writer (INV-CH7-10/CINV-02) for all five backends
  - **CHECKED 2026-08-08, plan 15.2-14 (the phase-close audit), clause by clause against the tree — not against any SUMMARY.** **SUBQ-01:** `docs/GRAPH_QUERY_SEMANTICS.md` exists at semantics **1.0.1**; **35 distinct** backticked `GQ-NN` anchors over 91 citing lines; the semver lane is declared in the document's first seven lines and states v1 includes `allowed_entities`; the uniform rule (`GQ-15`) and the induced-subgraph rule (`GQ-16`) are both normative clauses; `grep -ci 'implementation-defined'` → **0**. The requirement's "no implementation-defined escape hatches" clause is what forced the 1.0.1 amendment: `GQ-16`'s v1.0.0 "every answer" wording left the dangling-edge degenerate shape decided by `ccf.graph.fallback::_endpoint_closure`'s docstring (recorded in-phase as DI-15.2-01). That was the escape hatch, and it is closed — the scoping is now the prose's, with the amendment history under `GQ-35` recording what changed and why. `python -m tools.lints --all` → exit 0 (the citation guard resolves every anchored `GQ-NN` citation in `/src` and `/tests` against this document). **SUBQ-11:** `_GraphTxn` is the nine-operation typed Protocol and `BaseGraphWriter` drives it with zero SQL text (`grep 'execute(self\.'` → no hits); **five** per-backend implementations exist and all five live inside `ccf.graph._writer` — `_SqliteTxn`/`SqliteGraphWriter`, `_PostgresTxn`/`PostgresGraphWriter`, `_MemoryTxn`/`MemoryGraphWriter`, `_Neo4jTxn`/`Neo4jGraphWriter`, `_MongoTxn`/`MongoGraphWriter`; the ast-walk confinement test proves no `*GraphWriter`/`*GraphTxn` class exists outside that module (the sole exception being the `GraphWriter` **Protocol** in `ccf.graph.protocols`, a D-IMPL-41 layer-1 interface declaration, not write code); CINV-02 is green in `make ci`. The five-backend clause is now asserted by the suite that owns those semantics rather than inferred from neighbouring ones: `tests/conformance/test_graphstore.py` parametrizes the six D-IMPL-34 write semantics over all five backends (DI-15.2-02, closed at this audit) — 24 passed always-on (`sqlite` + `memory`), 12 passed `-m postgres` (PostgreSQL 16.14), 12 passed `-m neo4j` (Neo4j Kernel 5.26.29 community), 12 passed `-m mongo` (MongoDB 7.0.39). Every write in all four runs goes through booted L2; nothing constructs a writer.
  - **Reviewer tension recorded against SUBQ-01, and why the box is still checked.** One §3.1 reviewer argued SUBQ-01 cannot be Complete while `D-IMPL-90` (DI-15.2-03) is open, on the reasoning that a temporal-filtering divergence is itself "an implementation-defined behavior". The tension is recorded rather than dismissed, and the box stands, because the two requirements cut at different joints: **SUBQ-01 is about the prose deciding**, and `GQ-09` decides validity unambiguously — `valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)`, over instants, with no escape hatch and no adapter discretion. What `D-IMPL-90` describes is an **adapter that fails to implement a decided clause** for one timestamp rendering. That is a conformance defect against `GQ-31`, which is SUBQ-04/SUBQ-08 territory, not a gap in the vocabulary. Both readings are in front of Dave: `D-IMPL-90` is named as the gating decision of the D-GATE-15.2 package, and if he reads the divergence as reaching SUBQ-01, SUBQ-04 or SUBQ-08, those rows return to Pending on his word.

- [x] **SUBQ-12**: A sixth adapter — `fluree` — answers `GraphQuery` under both conformance suites (differential byte-identity against the audited `ccf.graph.fallback` oracle over the full generated corpus, `allowed_entities` families and D-IMPL-87 resurrection shapes included, plus the six D-IMPL-34 write semantics), **with the translation proven by its own `translated_answers`/`fallback_answers` telemetry rather than by byte-identity alone** — D-04/`GQ-34` make the degraded posture byte-identical by design, so a `_translate_query` that always returned `None` would pass the entire differential corpus. Fluree v4 only (D-IMPL-91), temporal fields as canonical RFC3339 text properties filtered in query, with Fluree's native transaction-time `t` never implementing `as_of` (D-IMPL-88). Stage-1 conformance — non-traverse pushdown with fallback traversal, the sanctioned D-04 degrade — satisfies this requirement on its own; **stage-2 promotion of the bounded undirected walk over the adapter-internal interposed edge-node model is a budgeted enhancement**, promoted only at byte-identity over the full corpus and recorded for ratification, not part of the requirement (Phase 15.3 D-04, D-05, D-12)
- [x] **SUBQ-13**: The JSON-LD buffered-batch write path — `_FlureeTxn` + `FlureeGraphWriter` in `ccf.graph._writer` — satisfies the nine typed `_GraphTxn` operations with **per-operation rowcounts resolved before commit** by read-before-buffer plus own-buffer merging, never from the single POST's aggregate `flakes_added`, committing as one ground `delete`+`insert` body; preserving single-writer (INV-CH7-10) and write confinement (CINV-02) with **no write code in `ccf.graph.backends.fluree`**, and adding no new Python dependency, no optional extra and no mypy override (Phase 15.3 D-01, D-02, D-03, D-12)
- [x] **SUBQ-14**: The Phase 15.2 no-refactor claim is **mechanically demonstrated rather than narrated**: `make gate-15.3` enforces the `D-IMPL-92` permitted-change surface — a path allowlist, no existing backend name removed from any enumeration, per-file added-line budgets printed beside their measured mongo baselines, and an AST assertion that no pre-existing class or function body in `ccf.graph._writer` changed — and exits non-zero on anything outside it; the gate package is committed with the phase; and the `fluree` container leg is a fourth **always-on** blocking leg in `ci.yml`, green on `main` after merge (Phase 15.3 D-08, D-09, D-10, D-11 as amended by `D-IMPL-92`, D-12)

### Context Product Surface (CPS)

- [x] **CPS-01**: Every Context Product delivered to a consumer carries its Context Debt, and no delivery path exists that drops it — across all three delivery paths (`runtime/ccf_runtime/mcp/egress.py`, `runtime/ccf_runtime/http_api/routes/product.py`, `runtime/ccf_runtime/mcp/experience.py`) — registered as a CINV-04 `Check` row with an owning test and an adversarial case, not asserted in prose
- [x] **CPS-02**: All **nine** §6.3 contract elements are present across the shipped product types (`D-IMPL-30`, Dave, 2026-07-25 — Assembly Mode included; every "eight" reference is editorial drift that ruling authorizes treating as such), each verified by a field-enumeration assertion that fails when one is unrepresented, so the defect class that hid three of them cannot recur silently
- [ ] **CPS-03**: A product class declares its payload schema and a payload violating that declaration is refused, reusing the shipped declared-schema machinery rather than a second one — **PENDING at phase close on the second clause.** The declaration ships (`register_product_class` takes a payload schema, `src/ccf/products/contract.py`) and the refusal ships and is tested (`refuse_bound_payload`, `src/ccf/products/bind.py::refuse_bound_payload`, `tests/products/test_payload_bind.py`), reusing `refuse_payload` rather than a second comparison. But **no shipped delivery door calls it** — `runtime/` has zero imports of `refuse_bound_payload`, and its only caller outside its own tests is `examples/04-cross-process/producer_child.py::resolve`. So "is refused" is true of the mechanism and not yet of any door. Found independently by two close-time panel reviewers (`15.5-CLOSE-REVIEWS.md`, P3/C1/C3); the placement is `D-IMPL-102`'s and wiring it into the doors is a delivery-path change adjacent to limb 3's "no fourth gate", and it was put to Dave as residual R1. **RULED (`D-IMPL-113`, Dave, 2026-08-11): the bind is an adopter obligation the SDK documents and does not enforce.** The door cannot call it — `ProductResolverProtocol` resolves the `RegisteredProductClass` behind the seam, so the door never holds the object the refusal needs, and enforcing one layer out would put an SDK-owned payload verdict on the serve path that `D-IMPL-102` limb 3 declined. `CPS-03` is therefore **Pending by design, not by omission**; the obligation is stated at the seam in `src/ccf/products/bind.py` — **AMENDED 2026-08-12 (`D-IMPL-121`, Dave), and the row must be read through BOTH rulings.** `D-IMPL-113` extends to `src/ccf/products/request.py::refuse_request`, because its reasoning is about the *seam* rather than about either function: both request-time refusals are adopter obligations the SDK states at the seam and does not enforce. **Pending by DESIGN under `D-IMPL-113` AND `D-IMPL-121`, not by omission** — stated with both entry numbers per `D-IMPL-113`'s own instruction that *"the requirement row must say which, or a later reader will read an unmet requirement as an oversight."* **Two factual corrections, re-measured at `4b407e0` rather than carried.** (1) The sibling refusal `src/ccf/products/request.py::refuse_request` has **one** caller, not zero — `examples/s1-01-hello-context-product/spine.py::assemble_and_serve` — and the `deferred-items.md` entry recording zero was **wrong when written**, by nine hours, in the same phase; see `DI-15.5-05` for the git-confirmed ordering. (2) The `producer_child.py` anchor above was line-numbered and had drifted; it is re-cited in the `path::Symbol` form `D-IMPL-114` requires. **The obligation is now discharged and asserted:** both `runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol` and `runtime/ccf_runtime/mcp/experience.py::ExperienceProductResolverProtocol` name both refusals, state what an omitting resolver serves, state why the door cannot call them, and cite both shipped example call sites — and `tools/docs_tests/test_resolver_seam_obligations.py` asserts it stays that way, because a docstring nobody checks is a docstring that rots
- [x] **CPS-04**: Perspective is derived from the verified grant at every exposed door, a caller cannot assert a role it was not granted, and `ProjectionEngine.execute` keeps taking a `Perspective` so replay feeds the recorded one
- [x] **CPS-05**: Per-product-class entitlement gates every exposed door — the MCP egress door, the HTTP product route and the Experience front door — through a Control Plane artifact with no permissive default and no field able to express a bypass, enforced by field enumeration, and downstream of authentication at each
- [x] **CPS-06**: The assembler is a Protocol with a shipped mechanism-only reference implementation whose production instance is a declared agent from the `context_assembly` archetype, binding sources, tools, enlisted agents and its debt profile through axes 4 and 5 and channel 2
- [x] **CPS-07**: A product answers a runtime request — subject and instant are arguments, never artifact literals — and the question asked is pinned into replay through `graph_query_sequence` and `QueryPinWriter`
- [x] **CPS-08**: Aggregate products compose lineage by union and implement `D-IMPL-31`'s mixing-refusal rule, with declarable constituent-validity floors whose breach refuses assembly
- [x] **CPS-09**: The four anti-leakage lints stay green throughout: zero harness imports in `src/`, no LLM client in an `@algorithmic` module, no prompt or threshold literal outside an artifact, no substrate name outside the backend registry
- [x] **CPS-10**: `examples/s1-01-hello-context-product` demonstrates an agent asking about any company at any time and is the shape every later example copies
- [x] **CPS-11**: Replay reproduces byte-exactly after every contract change, with `rehydrate_product`'s content-address check run against each candidate field placement before the placement is committed, and re-run before the first edit and after every commit of any plan that changes a hashed contract
- [x] **CPS-12**: No committed baseline drifts un-narrated
- [x] **CPS-13**: Micro-benchmark medians stay inside the 10% relative band after the field and gate additions, measured deliberately because `make perf` is not part of `make ci`, against a chain of baselines that starts before any change lands
- [x] **CPS-14**: The eight open design questions are put to Dave with measured costs, ruled, and recorded as `D-IMPL` entries before the tracks they gate are implemented

### Decision-Completeness and Defect Closure (DCD)

- [x] **DCD-01**: The fixed-versus-declared fork is measured rather than argued — every candidate placement for a debt-evidence carrier has a verdict produced by running the real `rehydrate_product` tripwire, the record-only placement's consumer reach is counted against the three shipped doors, and the spike recommends nothing
- [ ] **DCD-02**: Debt points at what it summarises, and `Observation` carries an identity those pointers can name; the SDK enumerates no observation identity vocabulary and owes nothing about *which* observations matter (`D-IMPL-117`) — **PARTIAL, and the partiality is by ruling.** The *carrying mechanism* is COMPLETE: `src/ccf/halflife/decay.py::Observation` gained an optional subject behind a named positive sentinel (plan `15.6-05`, `D-IMPL-120`), and `src/ccf/products/contract.py::ContextProductContract` gained `debt_evidence` with its dimension-5 twin and 7 rehydrator edits (plan `15.6-06`, `D-IMPL-118`), exercised with populated values in `tests/replay/test_engine_rehydration.py::test_a_rehydration_that_swaps_one_pointer_is_divergence` and its siblings. What is **Pending by design** is the *population* on the delivered product: `D-IMPL-119` limb 3(b) rules that until the assembly path is principal-scoped an evidence pointer is an opaque handle or is not emitted at all, so `examples/s1-01-hello-context-product/deployment.py::KycScenario` returns the sentinel unconditionally. The slot and its replay plumbing exist so a later phase fills a slot rather than rebuilding one
- [x] **DCD-03**: Source-refresh recency is a slot distinct from computed freshness, with no SDK definition of a source, no cadence, no staleness threshold and no default; an unpopulated slot is a positive assertion under a named sentinel — **COMPLETE** (plans `15.6-07` and `15.6-13`). `src/ccf/products/contract.py::ContextProductContract` carries `source_refresh_recency`, whose type is `src/ccf/halflife/assessment.py::SourceRefreshWindow` after `D-IMPL-124` Shape B replaced the per-source map: a freshness window with **no human-interpretable source identities and no count**. Divergence asserted by `tests/replay/test_engine_rehydration.py::test_a_rehydration_that_drops_the_recency_is_divergence` and `::test_a_rehydration_that_moves_one_refresh_instant_is_divergence`
- [x] **DCD-04**: Each `DebtSignal` can carry a declared, **opaque** obligation reference bound through the Control Plane and resolved at replay to the binding in force at decision time, with **no obligation vocabulary anywhere in `src/`**, enforced by a structural assertion no shipped lint reaches — **COMPLETE** (plan `15.6-08`, ruled by `D-IMPL-118`). Replay-at-decision-time is asserted by `tests/replay/test_engine_rehydration.py::test_a_replay_reproduces_the_obligation_in_force_at_decision_time` and its negative twin `::test_a_rehydration_that_resolves_todays_binding_is_divergence`; the anti-vocabulary invariant is `tests/invariants/test_no_obligation_vocabulary.py`, whose `CONTAINER_FORMS` enumerates **24** container forms after the close-review round closed the `dict` shape it originally missed
- [x] **DCD-05**: Every Track B contract change replays byte-exactly through the real serve path after the graph has moved on, and an adversarial twin diverges — **COMPLETE**, and re-run per change rather than once: `tests/replay/test_engine_rehydration.py` carries a drop-and-perturb divergence case for each of the three carried members (`::test_a_rehydration_that_drops_the_evidence_is_divergence`, `::test_a_rehydration_that_drops_the_recency_is_divergence`, `::test_a_rehydration_that_drops_the_obligation_is_divergence`), plus `::test_a_record_written_before_the_obligation_seam_still_replays` for the pre-seam shape
- [x] **DCD-06**: `DI-15.5-01` — the noisy dispatch benchmark's band covers its measured variance across three consecutive runs, with no code change and no re-baseline — **COMPLETE** (plan `15.6-02`). One loosen-only `[override]` at `threshold = 0.1246`, derived from five recorded medians, verified in force by reading the gate's *resolved* threshold rather than the TOML, with two separate sets of three consecutive green runs. **The gate-time PERF-04 re-baseline of 2026-08-13 does not touch this clause**: it revised two `test_operators.py` ids under Dave's explicit approval and left this benchmark's approved median and its override unchanged
- [x] **DCD-07**: `DI-15.5-04` — the `IntermediateCache` key is computed only when a lookup could hit, with the composition-preservation suites passing unmodified and the `D-IMPL-36` witness narrowing recorded — **COMPLETE** (plan `15.6-02`). `src/ccf/operators/planner.py::IntermediateCache` defers key materialization to the first call that could hit; the unreachability probe is identical before and after (640 engine runs, 0 engine hits, 1 other hit); `tests/properties/test_composition.py` and two sibling suites pass with `git diff --exit-code` clean; the narrowing is recorded in the class docstring and in `docs/surface-changes/15.6-02-intermediate-cache-key.md`
- [x] **DCD-08**: `DI-15.5-05` — both resolver seams state, **at the seam**, what a resolver omitting each refusal is serving, under a recorded ruling — **COMPLETE** (plan `15.6-09`). The ruling is `D-IMPL-121` (Dave, 2026-08-12), extending `D-IMPL-113`; the statement lands in both `runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol` and `runtime/ccf_runtime/mcp/experience.py::ExperienceProductResolverProtocol`; and `tools/docs_tests/test_resolver_seam_obligations.py` asserts it rather than trusting it
- [x] **DCD-09**: `DI-15.5-06` — the surface manifest records a Protocol's `__call__`, so the already-shipped resolver break becomes a visible `reshaped` diff line; the manifest's non-Protocol blind spot is closed or descoped with a recorded reason — **COMPLETE as ruled** (plan `15.6-10`, `D-IMPL-122`). `tools/dump_surface.py` reads a Protocol's `__call__` and type aliases; the frozen baseline stayed frozen and the diff was reconciled; the phase's single manifest regeneration landed here. **The descoping is the recorded half and must travel with the requirement:** 39 multi-method Protocols remain information-free, including all seven `D-IMPL-110` names, so the manifest is **not** evidence of surface stability for them
- [x] **DCD-10**: `DI-15.5-08` — the `.py`-target unanchored citation population is reduced over the ruled scope and cannot regrow, gated in **both** directions — **COMPLETE over the ruled scope** (plan `15.6-11`, `D-IMPL-123`: 101 of 114, holding back the 13 records `D-IMPL-114` names). `tests/invariants/test_citation_coverage.py::MAXIMUM_UNANCHORED_PY_CITATIONS` is **0** — the tree's first ceiling — with `::MINIMUM_SCANNED_CITATION_HOSTS` and `::MINIMUM_CITATIONS_READ` as the floors. It fired at this very gate, on the gate package itself
- [x] **DCD-11**: `docs/schemas/` is shingle-scanned by the shipped `publish_scan` machinery through a scan root wired into `docs-strict`, not by a one-time sweep — **COMPLETE** (plan `15.6-03`). `make docs-strict` now runs **four** steps, the third being the `docs/schemas` scan root; 0 findings over 26 files. **Known-blind, recorded rather than implied:** this scanner and `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` disagree about the same tree, because `tools/dump_schemas.py::emit` copies docstrings verbatim into schema `description` fields and only one of the two blocks. That is `DI-15.6-01`(b), Dave's *"real coverage hole"*, owned by Phase 16
- [x] **DCD-12**: The phase gate is `make ci` exit 0, with the CLAUDE.md §3.1 close sequence run in its stated order — **COMPLETE** (plan `15.6-12`, `D-GATE-15.6`, Dave 2026-08-13). `make ci` exit 0 observed at the gate HEAD: **3086 passed / 81 skipped**. The sequence ran in order — execute → cross-AI panel `--all` against shipped code → single-agent review → verify every finding → fix every blocking finding in-phase → present — and produced **three** rounds of findings, the third being the observed gate catching five citation defects in the gate package itself

**DCD-01 is discharged across its two owning plans, with one stated exception.**
Plan `15.6-01` produced `docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md` and
`tests/spikes/test_debt_evidence_placement_cost.py` — four placement verdicts by
executed round trip, the record-only placement's reach counted at **0** wire
consumers against all three shipped doors, and no recommendation anywhere in the
document. Plan `15.6-04` converted the measurement into rulings `D-IMPL-118`,
`D-IMPL-119` and `D-IMPL-120`. **The exception, stated rather than elided:** the
clause reads *"a verdict produced by running the real `rehydrate_product`
tripwire"*, and only **2 of the 4** placements were exercisable end to end
against it — `tests/replay/test_engine_rehydration.py` ran at **exit 0, 24
passed** for the declared and record-only placements, while the nested and
top-level placements are marked **NOT EXERCISABLE** in the evidence document,
each naming the exact source changes that would have to land first, with their
verdicts produced instead by an executed round trip carried through the **real**
`ContentGenerationPath.debt` field. No later plan carries `DCD-01`.

**DCD status at `D-GATE-15.6` (Dave, 2026-08-13): eleven Complete, one Partial.**
The one Partial is `DCD-02`, and it is partial **by ruling rather than by
omission** — `D-IMPL-119` limb 3(b) forbids emitting an evidence pointer until
the assembly path is principal-scoped, so the phase shipped the carrier, the
dimension-5 twin and the seven rehydrator edits and left the delivered field
holding its sentinel. Three of the eleven Complete rows carry a scope that must
travel with them and is stated in the row rather than left for a later reader to
discover: `DCD-09` descopes 39 multi-method Protocols, `DCD-10` holds back the
13 citation sites `D-IMPL-114` names, and `DCD-11` ships a scan root beside a
known coverage hole (`DI-15.6-01`(b)) that Phase 16 owns. No DCD row is Pending
by omission.

### Client Access (CLNT)

Minted at Phase 17 planning (2026-08-15) under the inserted-phase precedent
already stated in `.planning/ROADMAP.md` §Coverage — a phase mints its own
requirement IDs at planning rather than borrowing a predecessor's. The
`CLNT-` lane was verified free before minting (`command grep -rn "CLNT"
.planning/REQUIREMENTS.md docs/` returned nothing, `17-RESEARCH.md` §8). One
phase, one prefix: the inherited-discharge rows (CLNT-16..CLNT-19) carry
`CLNT-` too rather than opening a second lane for cleanup.

Every row is derived from a `D-NN` already ruled in
`.planning/phases/17-client-access-ccf-client-and-the-transport-agnostic-first-ex/17-CONTEXT.md`
and from `docs/superpowers/specs/2026-08-15-ccf-client-design.md` including its
Amendment 1. The ruling ids are named in each row so a later reader can check
the requirement against the decision rather than against a memory of it.

- [ ] **CLNT-01**: `ccf.client` exports exactly four names — `ProductClient`, `Result`, `TransportError`, `BindingError` — reached through `ProductClient.for_product(product_id, binding=None)` and `client.ask(parameters, as_of=None)`, synchronous only, with the `as_of=None` rule documented on `ask()` and the four-name surface asserted by an equality on `__all__` rather than a membership check (`D-03`, `D-04`, `D-24`)
- [ ] **CLNT-02**: `Result` carries either the answer or the refusal as a value — the fabric refusing is the fabric working — and accessing any post-assembly field (`payload`, `debt`, `content_address`, `replay_ref`, post-assembly `lineage`, `expires_at`) on a refused result **raises**, asserted once per guarded field rather than by one `pytest.raises` standing for six, while a refused result still carries `refused`, `refusal.reason`, `refusal.key`, the refused request identity and any pre-assembly lineage (`D-07`, `D-08`, `D-09`)
- [ ] **CLNT-03**: Exceptions are reserved for the wire failing and for caller negligence — `TransportError` for connection, timeout and auth, `BindingError` subclassing it so `except TransportError` remains the one catch-all, and no code path converts a refusal into an exception or an exception into a refusal (`D-10`)
- [ ] **CLNT-04**: Binding resolution is exactly three steps — explicit `binding=` kwarg, else the `CCF_BINDING` env var carrying a scheme-prefixed address, else `BindingError` whose message names the literal `CCF_BINDING` and the call that overrides it — over a plain-dict scheme registry, with no bindings file, no per-product env-var naming and no discovery chain, and the kwarg's precedence proven by which adapter ran rather than by a stored attribute (`D-05`, `D-06`, `D-21`)
- [ ] **CLNT-05**: One transport seam — `TransportAdapter.ask(WireRequest) -> WireOutcome` — where `WireRequest` carries product id, parameters and temporal boundary, `WireOutcome` is the canonical serialized form of either a served product or a refusal, and a transport failure has no `WireOutcome` at all because the adapter raises (`D-11`)
- [ ] **CLNT-06**: `Result` is constructed in exactly one decoder inside `ProductClient`, proven by a source assertion that no second construction site exists anywhere in `src/`, `runtime/` or `examples/` — shape identity across transports is a code path an adapter cannot avoid rather than a convention it follows (`D-12`)
- [ ] **CLNT-07**: One canonical refusal envelope lives in `src/`, defined before any door emits it, carrying every shipped refusal kind without flattening — the request-level reasons, the `GateRefusal` family, `PayloadSchemaViolation`, `MixingRefusal` and any sibling — plus the pre-assembly request identity, with an exhaustiveness assertion that fails the day a new refusal type ships untranslated (`D-28`)
- [ ] **CLNT-08**: `decode(encode(x)) == x` holds for served products and for refusals, and the in-process adapter round-trips through that same codec so it is a true degenerate wire rather than a privileged fast path and cannot leak a live producer-side object across the seam (`D-13`, `D-20`)
- [ ] **CLNT-09**: The resolver Protocol **and** its reference implementation both live in `src/`, composing assemble → gate → serve as pure mechanism with every threshold, product class and policy value arriving from Control Plane artifacts, adding no `src → runtime` import — asserted, not asserted-about — so the composition stops being every deployment's problem (`D-29`)
- [ ] **CLNT-10**: The in-process adapter boots the fabric lazily on first `ask()` from the deployment root the binding names, caches the booted fabric per binding address for the process lifetime so a second `ask()` is legal at all rather than merely fast, and triggers no producer provisioning — proven positively by a second `ask()` that does not re-boot, and negatively by a gate over `src/ccf/client/` (`D-14`, `D-16`, `D-30`)
- [ ] **CLNT-11**: One adapter conformance suite, written once and parameterized over adapters, asserting identical `Result` fields and identical content address for the same question at the same instant, identical refusal identity, the guard on every adapter, and that a wire failure never masquerades as a refusal — an adapter is official when it passes — and re-asserting through the client seam that two thresholds are two content addresses (`D-15`, `D-23`)
- [ ] **CLNT-12**: Every parity, guard and example gate this phase adds carries a named sabotage control demonstrating the check fails when its property is deliberately broken, written in the same plan as the assertion rather than deferred (`D-22`)
- [ ] **CLNT-13**: The first example is `consume.py` beside an opaque `deployment/` directory and a README — the client knows the product identity and the question parameters, imports `ccf.client` and stdlib only, prints the answer and then what a `SELECT` would not have told you, with governance detail behind `--explain` — run by one documented command carrying a fixed `--as-of` that the make target runs verbatim with no parameter smuggling (`D-01`, `D-02`, `D-17`, `D-18`)
- [ ] **CLNT-14**: Two CI gates carry the Phase 16 lesson that a measurement nobody is looking at protects nothing — an AST purity gate proving `consume.py` imports only `ccf.client` and stdlib, catching `import`, `from`-import and function-body-deferred forms alike, and a budget gate holding reader-visible Python to its declared budget so the 722-line failure mode is a red check rather than a retrospective (`D-19`)
- [ ] **CLNT-15**: The MCP product door carries client-supplied parameters and emits the canonical refusal envelope, and the MCP adapter ships on passing the same conformance suite as in-process rather than on demoing (`D-15`, `D-28`, `D-IMPL-133`)
- [ ] **CLNT-16**: The retirement sweep machinery is green and its committed inventory current **before** any example tree moves — an untrustworthy inventory is how a partial retirement ships — and the `tools/` suites the always-on pipeline runs are reachable from the local gate so "all green" is a true claim rather than a claim about the subset `make ci` reaches (`D-31`)
- [ ] **CLNT-17**: The condemned example trees are dispositioned with every gate, make target, CI job, floor constant and published snippet that references them handled in the same change — no partial state — and the suspended example-shape rulings are discharged by retiring the gates that enforce them rather than by leaving those gates blind (`D-25`, `D-26`, `D-27`)
- [ ] **CLNT-18**: No demo data is committed to `examples/` — no store file, no seed artifact, no fixture data — and the example's README and its CI placement state plainly which pipeline proves it, given that an example needing a reachable backend cannot run in the always-on, network-free, credential-free pipeline (`D-32`)
- [ ] **CLNT-19**: The product-door exhaustiveness gate sees the in-process client seam, with the absent client-seam entitlement check recorded as a named, asserted exemption rather than as a gate that stays green because it cannot reach the door (`17-RESEARCH.md` §5.4, v0 not-list)
- [ ] **CLNT-20**: `AssemblyDebtScorerProtocol` has a shipped reference implementation in `src/` that reads every figure from a Control Plane artifact, states its row-selection choice at the seam with its reason and override path, and fails closed on an empty assembly (CLAUDE.md §11; 2026-08-16 spec Amendment A.1)
- [ ] **CLNT-21**: `binding.yaml` is a data-only document carrying exactly one `module:attribute` reference — the projection — and the loader refuses a second **by name**, so the narrow exception cannot widen into the rejected `D-IMPL-141` shape (2026-08-16 spec Amendment A.3/A.4 criterion 3′)
- [ ] **CLNT-22**: The reference debt scorer is the default, proven through its effect on a produced `DebtAssessment` rather than by attribute inspection, and a deployment of config + data-only binding + one projection module produces a gated, content-addressed product (2026-08-16 spec §8, criteria 1/2/4/5)


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
| DOCS-07 | Phase 16 | Pending |
| DOCS-08 | Phase 16 | Pending |
| DOCS-09 | Phase 16 | Pending |
| DOCS-10 | Phase 16 | Pending |
| DOCS-11 | Phase 16 | Pending |
| DOCS-12 | Phase 16 | Pending |
| DOCS-13 | Phase 16 | Pending |
| DOCS-14 | Phase 16 | Pending |
| DOCS-15 | Phase 16 | Pending |
| DOCS-16 | Phase 16 | Pending |
| DOCS-17 | Phase 16 | Pending |
| DOCS-18 | Phase 16 | Pending |
| DOCS-19 | Phase 16 | Pending |
| DOCS-20 | Phase 16 | Pending |
| DOCS-21 | Phase 16 | Pending |
| DOCS-22 | Phase 16 | Complete |
| DOCS-23 | Phase 16 | Pending |
| DOCS-24 | Phase 16 | Pending |
| DOCS-25 | Phase 16 | Pending |
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
| SUBQ-01 | Phase 15.2 | Complete |
| SUBQ-02 | Phase 15.2 | Complete |
| SUBQ-03 | Phase 15.2 | Complete |
| SUBQ-04 | Phase 15.2 | Complete |
| SUBQ-05 | Phase 15.2 | Complete |
| SUBQ-06 | Phase 15.2 | Complete |
| SUBQ-07 | Phase 15.2 | Complete |
| SUBQ-08 | Phase 15.2 | Complete |
| SUBQ-09 | Phase 15.2 | Complete |
| SUBQ-10 | Phase 15.2 | Complete |
| SUBQ-11 | Phase 15.2 | Complete |
| SUBQ-12 | Phase 15.3 | Complete |
| SUBQ-13 | Phase 15.3 | Complete |
| SUBQ-14 | Phase 15.3 | Complete |
| CPS-01 | Phase 15.5 | Complete |
| CPS-02 | Phase 15.5 | Complete |
| CPS-03 | Phase 15.5 | **Pending** |
| CPS-04 | Phase 15.5 | Complete |
| CPS-05 | Phase 15.5 | Complete |
| CPS-06 | Phase 15.5 | Complete |
| CPS-07 | Phase 15.5 | Complete |
| CPS-08 | Phase 15.5 | Complete |
| CPS-09 | Phase 15.5 | Complete |
| CPS-10 | Phase 15.5 | Complete |
| CPS-11 | Phase 15.5 | Complete |
| CPS-12 | Phase 15.5 | Complete |
| CPS-13 | Phase 15.5 | Complete |
| CPS-14 | Phase 15.5 | Complete |
| DCD-01 | Phase 15.6 | Complete |
| DCD-02 | Phase 15.6 | **Partial** (plans `15.6-05`, `15.6-06`) — carrier and replay plumbing Complete; pointer population **Pending by design** under `D-IMPL-119` limb 3(b), until the assembly path is principal-scoped |
| DCD-03 | Phase 15.6 | **Complete** (plans `15.6-07`, `15.6-13`, `D-IMPL-124` Shape B) |
| DCD-04 | Phase 15.6 | **Complete** (plan `15.6-08`, `D-IMPL-118`) |
| DCD-05 | Phase 15.6 | **Complete** (plans `15.6-06`, `15.6-07`, `15.6-08`, `15.6-13`) |
| DCD-06 | Phase 15.6 | **Complete** (plan `15.6-02`) — unaffected by the 2026-08-13 PERF-04 re-baseline, which revised two other ids |
| DCD-07 | Phase 15.6 | **Complete** (plan `15.6-02`) |
| DCD-08 | Phase 15.6 | **Complete** (plan `15.6-09`, `D-IMPL-121`) |
| DCD-09 | Phase 15.6 | **Complete as ruled** (plan `15.6-10`, `D-IMPL-122`) — 39 multi-method Protocols descoped with a recorded reason, which travels with the requirement |
| DCD-10 | Phase 15.6 | **Complete over the ruled scope** (plan `15.6-11`, `D-IMPL-123`) — 101 of 114; the 13 `D-IMPL-114` names are held back by ruling |
| DCD-11 | Phase 15.6 | **Complete** (plan `15.6-03`) — with `DI-15.6-01`(b), the schema-description channel, recorded as a known coverage hole owned by Phase 16 |
| DCD-12 | Phase 15.6 | **Complete** (plan `15.6-12`, `D-GATE-15.6`, Dave 2026-08-13) |
| CLNT-01 | Phase 17 | Pending |
| CLNT-02 | Phase 17 | Pending |
| CLNT-03 | Phase 17 | Pending |
| CLNT-04 | Phase 17 | Pending |
| CLNT-05 | Phase 17 | Pending |
| CLNT-06 | Phase 17 | Pending |
| CLNT-07 | Phase 17 | Pending |
| CLNT-08 | Phase 17 | Pending |
| CLNT-09 | Phase 17 | Pending |
| CLNT-10 | Phase 17 | Pending |
| CLNT-11 | Phase 17 | Pending |
| CLNT-12 | Phase 17 | Pending |
| CLNT-13 | Phase 17 | Pending |
| CLNT-14 | Phase 17 | Pending |
| CLNT-15 | Phase 18 | Pending |
| CLNT-16 | Phase 17 | Pending |
| CLNT-17 | Phase 17 | Pending |
| CLNT-18 | Phase 17 | Pending |
| CLNT-19 | Phase 17 | Pending |
| CLNT-20 | Phase 17 | Pending |
| CLNT-21 | Phase 17 | Pending |
| CLNT-22 | Phase 17 | Pending |

**The CPS lane was verified clause by clause against the tree at Phase 15.5's
close (plan `15.5-14`), not against any SUMMARY.** Phase 15.1's re-approval had
to re-verify every clause because the earlier verification's line numbers had
moved; this was done once, by reading the code and running the named tests. The
evidence per row:

| Req | Evidence in the tree |
|---|---|
| CPS-01 | `tests/invariants/test_replay_by_construction.py::test_no_enumerated_door_can_drop_the_debt_the_vessel_carries` — the owning test, parametrized over `PRODUCT_DOOR_MODULES`, asserting both that the vessel carries `debt` and that every enumerated door serializes the *whole* vessel; `tests/invariants/test_replay_by_construction.py::test_a_door_that_serialized_around_the_vessel_would_be_detected` is the adversarial companion, which runs the same predicate against a door engineered to serialize around the vessel |
| CPS-02 | In `tests/products/test_contract_elements.py`: `::test_the_contract_has_nine_elements` (nine), `::test_every_element_is_borne_by_a_named_field` (each borne by a named field), `::test_the_pending_set_is_empty_which_is_the_ratchets_terminal_state` (the pending set is empty — the ratchet's terminal state), `::test_no_element_is_borne_by_a_field_two_elements_share` (no two elements share a field), and `::test_the_present_set_and_the_pending_set_partition_the_nine` (present and pending partition the nine) |
| CPS-03 | **Pending by design (`D-IMPL-113` **and** `D-IMPL-121`).** Both rulings are named because the row must say which, or an unmet requirement reads as an oversight. Declaration and both request-time refusals ship and are tested; calling them is the adopter's obligation, stated at both resolver seams and asserted by `tools/docs_tests/test_resolver_seam_obligations.py`. `refuse_request` has one shipped caller (`examples/s1-01-hello-context-product/spine.py::assemble_and_serve`), not zero as previously recorded. Not an omission |
| CPS-04 | `tests/invariants/test_mcp_role_separation.py::test_no_door_discards_what_entitled_perspective_returned` — no door discards what `entitled_perspective` returned, and the perspective the door authorized is asserted *by value* against what the resolver received, not by parameter presence |
| CPS-05 | `tests/authz/test_product_entitlement_door.py`, `tests/http_api/test_product_entitlement.py`, `tests/crossproc/test_experience_edge.py` — all three doors; `docs/schemas/ccf.product-entitlement-policy.json` has `additionalProperties: false` at both levels with both grant sets `required` and undefaulted, so no field can express a bypass. Strengthened at close: the door now compares the lookup key's tenant against the policy's own `tenant_id` (`7453e87`) |
| CPS-06 | `src/ccf/agents/assembler.py:242` (`ContextAssemblerProtocol`), `:292` (`DeterministicAssembler`, the mechanism-only reference), declared from the `context_assembly` archetype |
| CPS-07 | `tests/products/test_request_contract.py`; `tests/examples/test_s1_01_output.py:691` — a later instant pins a *different* question, and the inverted guard fails loudly if two subjects ever start pinning alike again (`D-IMPL-111` limb (a)); `ContentGenerationPath.request` carries the `ProductRequest` verbatim (limb (b)) |
| CPS-08 | `src/ccf/products/composition.py::compose_expiry` (ceiling, derivation, and the stalest constituent) and `src/ccf/products/composition.py::refuse_mixing`; `tests/properties/test_aggregate_composition_laws.py` — order-independence on the set axes, monotone growth, and a refusal for any floor breach anywhere in the set |
| CPS-09 | `python -m tools.lints --harness-imports --algorithmic --no-hardcoding --substrate-names`, each exit 0 individually and under `--all`. **Criterion 9 is exactly these four and carries no diff-size bound** — `D-IMPL-96` revoked that proxy |
| CPS-10 | `make example-s1-01` (`Makefile:89`, added by `15.5-13`, leading the `examples:` aggregate so it runs in CI); three declared questions across two companies and two instants |
| CPS-11 | In `tests/replay/test_engine_rehydration.py`: `::test_the_debt_the_decision_was_made_with_replays_byte_exactly` (the debt a decision was made with replays byte-exactly) and `::test_the_question_the_decision_answered_replays_byte_exactly` (the question it answered does, after four months of later state), with `::test_a_replay_that_re_seeds_from_another_question_diverges` as the adversarial twin that diverges when the recorded subject is swapped |
| CPS-12 | `tests/test_surface_completeness.py` passes in both directions against the regenerated manifest — every moved symbol has a fragment, every fragment names a moved symbol. `make schemas` and `make openapi` produce no diff. **With one stated exception:** the manifest cannot see a `Protocol.__call__`, so the two resolver seams' 3→5-argument break is narrated in `docs/surface-changes/15.5-15-resolver-seam.md` but produces no manifest line (`D-IMPL-110`) |
| CPS-13 | `make perf-micro` exit 0, all twelve benchmarks PASS. The three `test_gates.py` benchmarks — the ones a new contract field or the payload bind would move — are within ±1.8% of baseline |
| CPS-14 | `docs/DECISIONS.md` `D-IMPL-98` .. `D-IMPL-106` (the eight questions, ruled with measured costs from `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md`), plus `D-IMPL-107` .. `D-IMPL-112` raised and ruled during execution |

Coverage: 94/94 v0.2 requirements mapped, each to exactly one phase.
Counted from the traceability table above by counting its rows, not from the
previous sentence: 56 rows before Phase 16's minting, 68 after, 82 after Phase
15.5's, 94 after Phase 15.6's.
**DCD-01..DCD-12 were minted at execution rather than at planning**, by plan
`15.6-03` task 1 (2026-08-12), under the same inserted-phase precedent
CPS-01..14, DOCS-07..18, SUBQ-12..14 and ERGO-18..19 were minted under — an
inserted phase mints its own requirement IDs rather than borrowing a
predecessor's. Two things about this minting are worth stating because a later
reader will otherwise reconstruct them wrongly. First, **the minting is at
execution, not at planning**, which is a departure from the CPS precedent and a
deliberate one recorded in `.planning/ROADMAP.md` § Phase 15.6: `grep -c "DCD-"
.planning/REQUIREMENTS.md` returned **0** at `ef475e1`, the twelve IDs were
claimed across the twelve plans' `requirements:` frontmatter meanwhile, and
coverage was complete in substance and provisional until this plan landed.
Second, **DCD opens a new lane rather than extending CPS**, on the same joint
CPS was opened against SUBQ: Phase 15.5 established what a Context Product *is*
on delivery, and 15.6 closes what a delivered debt assessment does not yet let
an analyst *act on* — plus five carried, API-neutral defects that belong to no
CPS clause. The mapping is one DCD ID per named roadmap work item: the five
`DI-15.5-NN` defects are DCD-06 (`-01`), DCD-07 (`-04`), DCD-08 (`-05`),
DCD-09 (`-06`) and DCD-10 (`-08`); the three Track B gaps are DCD-02 (gap 1,
observation-contribution evidence), DCD-03 (gap 2, source-refresh recency) and
DCD-04 (gap 3, the `forced_llm` obligation binding); and the four remaining IDs
carry the phase's own machinery — DCD-01 the research spike, DCD-05 the standing
replay obligation every Track B contract change is held to, DCD-11 the
`docs/schemas/` scan root, and DCD-12 the `make ci` phase gate with the
CLAUDE.md §3.1 close sequence.
**CPS-01..CPS-14 were minted at Phase 15.5 planning and recorded here by plan
15.5-05 (2026-08-11)**, under the same inserted-phase precedent DOCS-07..18,
SUBQ-12..14 and ERGO-18..19 were minted under — an inserted phase mints its own
requirement IDs at planning rather than borrowing a predecessor's. Two things
about this minting are worth stating because a later reader will otherwise
reconstruct them wrongly. First, **CPS opens a new lane rather than extending
SUBQ or ERGO**, which is the opposite call from SUBQ-12..14's (Phase 15.3 D-12,
where a sixth adapter was held to be the same requirement family as the first
five). The reason the calls differ: 15.3 added a substrate to a surface that
already existed, whereas 15.5 changes what a Context Product *is* on delivery —
the vessel, its declared payload schema, the three absent §6.3 elements, debt
reaching the consumer, entitlement at the door, and the request contract. That
is a distinct surface, not another instance of one. Second, **CPS-01..CPS-13
correspond one-to-one to the phase's ten ROADMAP success criteria plus its three
standing verification obligations** (replay byte-exactness, baseline narration,
micro-benchmark headroom), and **CPS-14 is the ruling package itself** — the
requirement that the eight open questions are ruled *before* the tracks they
gate are implemented, which is the one requirement whose failure mode is a plan
guessing a design decision rather than a defect in shipped code.
**DOCS-07..DOCS-18 were minted at Phase 16 planning and recorded here by plan
16-01 (2026-08-10)**, under the same inserted-phase precedent SUBQ-12..14 and
ERGO-18..19 were minted under — a phase mints its own requirement IDs at
planning rather than borrowing a predecessor's. Three things about this minting
are worth stating because a later reader will otherwise reconstruct them wrongly.
First, **DEMO-01..03 and EXAM-01..05 re-home rather than retire** (Phase 16
`D-08`): each of those eight rows now carries a bracketed re-homing note naming
the new example or page that carries it, and no duplicate ID was minted for work
that already has one. The suite those requirements were satisfied against is
retired by DOCS-17; the requirements are not, and their Status column is
untouched by the re-homing. Second, **DOCS-01..DOCS-06 stay Pending against
Phase 14**, deliberately: Phase 16 rewrites what they delivered rather than
reopening them, so re-pointing their Phase column at 16 would erase the record
of which phase built the pages this one replaces. Third, Phase 16 is the largest
single minting in this file (twelve IDs) because the phase absorbed Phase 14.1
whole plus a scope expansion Dave ruled on 2026-08-09 — a greenfield examples
suite, a four-section documentation rewrite, and a six-backend CI matrix — and
the lane is sized to the phase rather than to the original roadmap sentence.
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
SUBQ-12..SUBQ-14 were minted at Phase 15.3 planning (2026-08-08) under the same
inserted-phase precedent, and they **extend the existing SUBQ lane rather than
opening a new one** (Phase 15.3 D-12). SUBQ-08 already reads "five adapters
answer `GraphQuery` under both suites"; a sixth is the same requirement family,
and one coverage lane stays one lane. A vendor-named `FLUR-NN` lane was rejected
additionally as a substrate-neutrality smell that would outlive the phase, and
because the phase's entire claim is that adding a substrate is *routine* —
minting a lane for it would quietly contradict the claim.
**SUBQ-12's stage hedge is a deliberate risk instrument, not hedging language.**
The 15.3 research rates the stage-2 traversal translation MEDIUM-LOW confidence
and names three Fluree-specific structural breaks with no Mongo analogue, so the
hedge is materially more likely to be exercised here than it was for Mongo
(SUBQ-08, where it went unused). Following the SUBQ-08 precedent, the shipped
outcome is to be recorded **beside** the minted text and the text left as
minted: editing a hedge after the fact erases the record of a risk that was
priced correctly.
**SUBQ-12's telemetry clause is written to avoid SUBQ-08's correction.** SUBQ-08
was corrected on 2026-08-08 (Dave's ruling, WARNING-1) from "all five adapters
carry a push proof" to "the four *translating* adapters do; memory carries the
conformance proof only." SUBQ-12 therefore says *translation proven by its own
`translated_answers`/`fallback_answers` telemetry rather than by byte-identity
alone* from the moment it is minted.
**SUBQ-06 text corrected 2026-08-08 (plan 15.2-14, on a BLOCKING finding from
the §3.1 self-review).** The minted text said post-in-process segments carry
"survivors as seeds + `allowed_entities`" — which re-asserts the reading
D-IMPL-87 explicitly rejected. The resolution's own words are the authority:
"seeds say where walks start, not which nodes they may cross." Promoting every
survivor to a seed would make every survivor a walk start (seeds are included
per `GQ-10`), widening the pushed answer beyond the in-process semantics and
re-opening the entity-resurrection defect the whole mini-cycle was convened to
close. The shipped engine does the correct thing —
`src/ccf/projection/engine.py` passes `seeds=None, allowed_entities=survivors`,
pinned by
`tests/projection/test_segmentation.py::test_the_second_query_carries_the_survivors_as_allowed_entities`
— and plan 15.2-07 recorded the discrepancy as a deliberate plan-language
reading rather than changing the requirement row. Leaving a **Complete**
requirement whose text states a rejected design is a repudiation defect: a
later reader would take the row as the ruling. The text now matches the
ruling and the code; no code changed.
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
