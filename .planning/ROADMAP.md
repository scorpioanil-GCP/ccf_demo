# ROADMAP — CCF SDK

## Milestones

- [x] **v0.1** — Whitepaper-faithful v0 SDK: fabric core (L1–L6), Agent Specialization Framework, cross-process + harness adapters, orchestration/HITL/experience, eight-example suite, full CI. Completed 2026-07-31, tag `v0.1.0`, D-GATE-I. → [archive](.planning/milestones/v0.1-ROADMAP.md)
- [ ] **v0.2** — Performance, Documentation & Demonstration: hardening intake (WR-01/02/03 + posture rulings), reproducible perf battery with committed baselines and regression gates, synthetic-data end-to-end demonstration, upgraded examples suite, adopter-grade documentation suite. (current)
- [ ] **v0.3** — Assembly Modes: close the whitepaper-fidelity gap in which two of the three Assembly Modes (§7.6) are declarable but undemonstrated. Pattern 5 unstructured ingestion (D-IMPL-08), a credit-memo exemplar demonstrating Mode 2 (`llm_packaged`) and Mode 3 (`swarm_assembled`) agent-swarm assembly over structured *and* unstructured sources with A2A coordination, and Part 2 of the two-part assembly document. (planned — see `14-HUMAN-UAT.md` G-02 for the evidence)

## Current Milestone: v0.2 Performance, Documentation & Demonstration

**Canonical authority:** `/home/parkave/ccf_code/CLAUDE.md` (revision 4). Every
phase ends with the §3.1 protocol: `/gsd-review` self-review → blocking/advisory
triage → STOP and present to Dave → approval logged as a `D-GATE` entry in
`docs/DECISIONS.md`. Six items in this milestone are gated on Dave rulings,
surfaced as one Phase D mini-cycle in Phase 9 (HARD-01); no gated item is
implemented before its ruling — implement per rulings only, never defaults.

**Phase ordering (research convergence):** harden first, measure second,
demonstrate, upgrade the examples, document last — docs describe hardened
postures, cite measured numbers, and literal-include the CI-run demonstration
and the upgraded examples.

## Phases

- [x] **Phase 9: Hardening — Defect Fixes & Ruling Batch** - Thread-safe HITL transports, loop-safe ADK driver, and the six-item D-IMPL ruling batch surfaced to Dave as one mini-cycle (completed 2026-08-01)
- [x] **Phase 10: Hardening — Authorization & Posture** - Per-tenant HITL door authorization, ApprovalGate × signed-binding composition, create_app posture warning — implemented per Dave's rulings (completed 2026-08-01)
- [x] **Phase 11: Performance Battery** - `perf/` tree with four suites, deterministic synthetic dataset generator, committed runner-class-keyed baselines, `make perf`, opt-in regression-gated CI (completed 2026-08-02)
- [x] **Phase 12: Synthetic-Data Demonstration** - Fake data store + end-to-end data→context→agentic-reasoning example, running in CI (completed 2026-08-02)
- [x] **Phase 13: Examples Suite Upgrade** - v0.1 examples 00–07 upgraded with detailed narrated READMEs and richer scenarios/artifacts exercising more SDK surface, CI stays green (completed 2026-08-02)
- [x] **Phase 13.1: External-Consumer Examples (MCP Egress)** (INSERTED) - Independent agents built in their own harness (Anthropic SDK, ADK, bare MCP client) consume CCF context via MCP egress with zero CCF imports client-side — CCF as a black box; demonstrates §7.1 MCP-as-egress as the primary adoption path (completed 2026-08-02)
- [x] **Phase 13.2: External-Example Hardening** (INSERTED) - Hardens `examples/external/00-hello-context` against the four-AI cross-review consensus concerns — live-captured diff-reviewed fixtures with a permanent schema guard and request-fingerprint replay matching, a server-side tool allowlist, and byte-path/README/duration assertion hardening — and executes Dave's 2026-08-02 ruling promoting `get_context`, `get_lineage` and `get_replay_record` into the SDK Experience surface, enabled by default. 5/5 plans (completed 2026-08-03). *(Bullet added 2026-08-25 — the phase was planned, executed and completed with a `## Phase Details` section but no entry here and no progress-table row. Same omission as Phase 17 and Phase 23; see the Phase 14.1 note for why an absent box is not cosmetic. No `D-GATE-13.2` exists and none is backfilled — `D-IMPL-171` rules the ten gate-less phases gated by their ROADMAP completion rows.)*
- [x] **Phase 13.3: Review-Residual Hardening** (INSERTED) - Closes the actionable residuals from the Phase 13.2 cross-AI review that execution did not resolve: allowlist fail-fast semantics with a serve-time assert that artifact `tools.*.name` values equal the SDK tool constants; a mandatory fingerprint-mismatch unit test plus fail-loud replay startup when a response fixture lacks its `*-request.json` sibling; capture-proxy spec tightening (HTTP 200 + JSON bodies only, query strings forwarded, headers never persisted); and `CINV-01` consistency for the `list_agents`/`invoke_agent` tool descriptions still shipping as docstring prose. 2/2 plans (completed 2026-08-03). *(Bullet added 2026-08-25 alongside Phase 13.2's, for the same reason and with the same `D-IMPL-171` note.)*
- [x] **Phase 14: Documentation Suite** - mkdocs site with generated Protocol/API reference, adopter's guide, schema reference, security notes, PERFORMANCE.md, narrated demo walkthrough — `make docs --strict` in always-on CI (10/10 plans executed and verified 5/5; **closed as-shipped 2026-08-03**. The G-01 framing defect stands deliberately: the docs describe an integration surface Phase 15 will replace, so the fix lands in Phase 16 against the new surface rather than twice against the old one. The published site carries no provisional banner — this note is roadmap-internal, per Dave, 2026-08-03)
- [x] ~~**Phase 14.1: Documentation — The Deterministic Path & The Adoption Argument** (INSERTED)~~ — **SUPERSEDED by Phase 16**, 2026-08-03, before any plan was written. Every success criterion is absorbed there. *(Checkbox marked resolved 2026-08-07 — not because the phase was executed, but because an unchecked box made `roadmap.analyze` return `next_phase: "14.1"`, routing auto-advance into a phase that was deliberately never planned. The strikethrough and this note are the record of what actually happened; the progress table below reads "Superseded by 16".)*
- [x] **Phase 15: SDK Ergonomics — The Integration Surface** (INSERTED) - Loaders, artifact classes, factories, and wiring helpers so the day-1 integration is a fraction of today's ~450-line example; abstraction line held at marshalling-and-wiring so no governance decision leaves adopter code and no replay dimension is hidden (completed 2026-08-05)
- [x] **Phase 15.1: Ergonomics Gap Closure — Governance Enforced, Not Conventional** (INSERTED) - Closes the two HIGH defects found by post-gate cross-AI review (D-GATE-15 amendment, 2026-08-05): CR-1, author-versioned classes can bypass the D-05 bump check through the manifest, closed by a per-entry `registration: typed | versioned` mode that `load_and_boot` dispatches on and **refuses** when an author-versioned class asks for `typed`; CR-2, Gate 2 (INV-CH7-47) is self-satisfying in all nine examples because lineage and `engine_resolved` are filled from the same `execution.operators_invoked` — and the remedy the review prescribed is itself circular, since `execution.operators_invoked ≡ frozenset(declared.required_operator_keys)` through five pure transforms. Closed instead by **design E2** (D-IMPL-86, Dave, 2026-08-05): the projection's required operator set becomes its own Control Plane artifact, a binder refuses when it diverges from the product-class declaration, and Gate 2 is documented for what it actually verifies — assembly-path integrity. Also corrects `SURFACE-AUDIT.md` §4.1, whose "eight instances" is an undercount, and restates the new AST gates as tripwires rather than structural enforcement (URGENT — Phase 16 must not document a self-satisfying gate) (completed 2026-08-06)
- [x] **Phase 15.2: Substrate Adapters and Query Pushdown** (INSERTED) - The fabric asks a substrate a question instead of loading its graph. `GraphReader.as_of()` today returns every entity and relationship for a tenant per read, which does not scale to a financial-services graph and lets a graph-native engine conform without ever being used as one. Introduces the read seam operators express intent against and the adapters that answer it — SQL, Cypher, Gremlin, aggregation pipelines, or client-side scan, each inside its own adapter. **Tier 1** storage adapters and **tier 2** Context-Product-as-a-source (in-process, MCP, or A2A — the §6.6 recursive-enrichment case, whose admission governance already exists in `ccf.peering.admission`) are in scope; **tier 3** raw external sources are deferred but must not require a refactor to add (Dave, 2026-08-07). Must preserve operator purity, as-of correctness (INV-CH7-14), single-writer (INV-CH7-10), and cross-substrate replay determinism (completed 2026-08-08)
- [x] **Phase 15.3: Fluree Adapter (Tier-1 Substrate)** (INSERTED) - A Fluree v4 storage adapter behind the Phase 15.2 read/write seams — the substrate-consolidation option for deployments (notably a financial institution developing its KG on Fluree) that want CCF's Context Graph co-located on Fluree they already operate. openCypher-over-wire translation per the 15.2-12 template; httpx wire client, zero new packages; temporal fields encoded as properties (Fluree's native time travel is transaction-time and MUST NOT implement as-of, per D-IMPL-88); an adapter going green against the unchanged 15.2 conformance/differential suites is the 15.2 no-refactor claim demonstrated on a real substrate. Ruled by D-IMPL-88 (Dave, 2026-08-07); CCF stays substrate-neutral — the bank's KG itself is approached as an external *source* (MCP ingress now; tier 3 later), never CCF's foundation (completed 2026-08-09)
- [x] **Phase 15.4: Backend Registration Seam — The Substrate Stops Naming Its Adapters** (INSERTED) - Commissioned by D-IMPL-93 (Dave, 2026-08-09). Today the dependency arrow points the wrong way: `src/ccf/boot.py` and `src/ccf/graph/_writer.py` **import** `ccf.graph.backends.*`, `_open_backend`/`_preflight_backend` carry two-to-three keyword arguments per substrate, and `controlplane/artifacts.py` hand-maintains a `Literal` naming all six — so adding an adapter costs ~96 added lines across three core files, and both remaining D-IMPL-92 budgets are now exhausted (`manifest.py` 24/25, `artifacts.py` 9/10, tied). Invert it: each backend declares itself (name → factory + required connection config + preflight rule), the core holds a registry and looks up instead of branching, per-substrate kwargs collapse into one config mapping, and the `Literal` derives from the registry. Success is **structural, not numeric** — no import of `ccf.graph.backends.*` from outside `backends/`, and no substrate name in core outside the registry, both lint-enforced in the same machinery as the existing harness-import lint, replacing the line budgets D-IMPL-92 itself calls an admitted proxy. Per-adapter substrate cost goes to zero, which is what "the SDK needs no refactor to accept a new substrate" was always trying to say. Migrates all six existing backends; D-IMPL-92's gate is superseded by the structural check, not deleted (completed 2026-08-09)
- [x] **Phase 15.5: The Context Product Surface — Vessel, Assembler, Debt, Entitlement** (INSERTED) - Commissioned by Dave 2026-08-10, mid-Phase-16, on reading `examples/s1-01-hello-context-product`: *"today I would put an MCP server in front of the fluree database and run a query and return the results. What is the benefit of using CCF?"* The example precomputed one answer to one design-time question at one fixed instant — which Chapter 1 names as the thing CCF replaces, *"the difference between the verb aggregate and the verb assemble."* Measured behind that reaction: three of §6.3's eight committed contract elements (freshness SLA, discovery, addressability) are unimplemented while `contract.py` states they live on `RegisteredProductClass`, where only `assembly_mode` of the four actually is; `register_product_class` takes no payload schema so `payload` is an unchecked dict; `DebtAssessment` is computed by `ccf.halflife.debt`, exercised in five examples, and appears on neither the product nor the replay record; and `Perspective` is passed into `execute()` by the caller with nothing deriving it from the verified grant, so the whole content-shaping layer sits downstream of an unverified claim. Rulings in force: `D-IMPL-96` revokes the "no fabric changed" constraint that concealed this, `D-IMPL-97` rules the Context Product a single standardised vessel whose uniqueness is in how it was assembled and whose assembler is a Protocol implemented by a declared agent, and Dave ruled entitlement requires a fabric change. Phase 16 is parked at 6/21 and resumes against the corrected surface — documenting it first would have documented the defect (completed 2026-08-12)
- [x] **Phase 15.6: Decision-Completeness and Defect Closure** (INSERTED, COMPLETE 2026-08-13, D-GATE-15.6) - Commissioned by `D-IMPL-116`/`D-IMPL-117` (Dave, 2026-08-11), before Phase 16 resumes. Two explicit tracks that must not be planned as one: **Track A** closes the five carried, API-neutral defects (`DI-15.5-01`, `-04`, `-05`, `-06`, `-08`); **Track B** closes `D-IMPL-112`'s three named gaps — which observations contributed the decay, when the underlying sources were last refreshed, and what `forced_llm` obliges — shipping **carrying mechanism, not judgement**, with the surface impact and the third product-content-address move accepted as authorized costs. Gap 1 gets a research spike first, in the `15.5-01` shape. Requirements `DCD-01..DCD-12`, **minted at execution in plan `15.6-03` task 1** (no `DCD-` row exists in `REQUIREMENTS.md` until that plan lands; the IDs are claimed across the plans' `requirements:` frontmatter meanwhile). Verification is `make ci`, not `make ci-core`
- [x] **Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument** — **RETIRED 2026-08-17 (`D-IMPL-152`), NOT RESUMABLE.** Executed 6 of 21 plans, then stopped when its example surface was rejected (a 722-line example whose consumer imported the producer). Superseded by Phase 17, which restarted from the client side and shipped `examples/hw1-companies-over-revenue`, and Phase 18, which added an MCP server to that same example. The 14 unexecuted plans are moved to `abandoned/` — preserved as history, **not a work queue**. The plan set is retired; the obligations several of those plans carried (§9 examples 01–04, the adopters guide, `make ci`'s claim) are **NOT discharged** and must be re-derived against the current surface when they become current. See `RETIRED.md` in the phase directory. Original scope follows: - One document, two sections (deterministic + external MCP consumption; CCF-agent assembly + MCP/A2A consumption), banking scenarios from the whitepaper, re-cut snippet markers so a reader can see which code is CCF and which is theirs
- [x] **Phase 17: Client Access — `ccf.client` and the Transport-Agnostic First Example** (INSERTED) - CCF owns the client abstraction and the result contract: `~ccf.client` at exactly four exported names, one decode path every transport returns through, the in-process adapter, the adapter conformance suite as a named CI gate, `~ccf.products.resolver.GovernedResolver`, the reference `~ccf.products.debt_scorer.AssemblyDebtScorer`, a data-only `binding.yaml`, and `examples/hw1-companies-over-revenue` whose `consume.py` is 78 lines importing only stdlib, `~ccf.client` and the adapter — against Phase 16's rejected 722-line example. **12 of 14 plans executed**; `17-08` and `17-10` deferred out under `D-IMPL-146` (completed 2026-08-16, `D-GATE-17`). *(This bullet was missing from the list until 2026-08-17 — the phase was planned, executed and gated with a detail section and a progress row but no entry here. Added at the Phase 18 lift, because an unchecked-or-absent box is what routed auto-advance into a never-planned phase once before; see the Phase 14.1 note.)*
- [x] **Phase 18: MCP Transport — The Second Door and the Portability Proof** (INSERTED) - Turns "transport-agnostic" from a design property into a demonstrated one. The MCP egress tool stops hard-wiring `parameters={}` so a product class declaring a required parameter becomes reachable over MCP — no coercion guessing, and no wider than the HTTP door, proven by one shared case table run against both; the MCP door learns to emit the canonical refusal envelope while a **governance** refusal still raises; and `mcp+stdio` ships as the second official adapter, sync at the surface with the async client bridged internally, registered by one dict entry and constructing no `Result`. It is official when it passes the conformance suite written before it existed — and **`suite.py` must not move to let it in**, which is the acceptance test for `17-07`'s adapter-agnostic claim. The phase's discharge is the same question at the same instant yielding the same content address in-process and over MCP (completed 2026-08-17)
- [x] **Phase 18.1: Simplify the MCP Example — Client-Side Access, Server Off-Stage** (INSERTED) - Inserted 2026-08-18 on Dave reading the example: too complicated for a beginner, and the client's own command names the server program. **A client-experience phase that ships no new transport, no new adapter and no change to the client seam — and exactly one piece of new mechanism, by ruling: `D-18` (Dave, 2026-08-18) makes the loader refuse, BY NAME, a `server:` value resolving back inside the deployment root (~4 lines and one test), because it makes `D-09`'s argument mechanical rather than documentary. Recorded in `docs/surface-changes/18.1-04-the-deployment-declares-its-server.md` and ruled in `D-IMPL-153`.** Three changes: `CCF_BINDING` names a **deployment** rather than a script, with the server command declared in `binding.yaml` as data, so the reader's command never mentions `serve.py`; `server/serve.py` (292 lines, ~180 of them deployment-value composition) is cut to a readable length, into a second `server/` module and never into `deployment/`, which `D-IMPL-141` A.3 forbids; and the README states the frame — **the same Context Product reached a different way**, why a server exists at all (the first example ran in-process and produced it directly), and that **how the server is assembled is deliberately out of scope until the assembly examples**. A server in a client-side example is not a scope violation; explaining it is. An earlier draft proposing an `mcp+http` adapter was **withdrawn same-day** as SDK work in an example's clothes
- [x] **Phase 19: The Client-Seam Integrity Checks Must Be Able to Fail** (INSERTED) - Closes `B0`, the open blocking defect deferred out of Phase 18's close review by `D-IMPL-151`. `src/ccf/client/codec.py` argues — correctly — that the request echo is *cross-checked, never reconstructed*, because reconstruction "cannot detect a transport that answered a *different question*". Both shipped adapters reconstruct: `DoorOutcome` carries no request identity, so `_decode` sets `request` from its own argument and `client.py` passes that same object as `sent`, making `check_outcome`'s comparison an object against itself. `verify_content_address` is inert for the same reason — the claimed address is computed by the adapter from the bytes the codec then re-hashes. **Both integrity checks are structurally unable to fail, on the one transport where a crossed-question wire is physically possible.** The phase's job is to make them able to fail: the wire form carries request identity, the address is claimed by the producer rather than recomputed by the consumer, and a control that answers a different question is caught by a single-transport client rather than only by the cross-adapter parity diff. Note `decode_outcome`/`encode_outcome` have no call site outside tests — both adapters build `WireOutcome` directly under `D-11`, and that permission is what admits the reconstruction, so the seam's enforceability is part of the scope. **Until this lands, the SDK must not be described as detecting a transport that answered a different question, or a vessel altered in transit** (`D-IMPL-151`)
- [x] **Phase 20: Client Access from Three Harnesses — ADK, Anthropic Agent SDK and LangGraph Agents Reaching One Context Product over MCP** - The continuation of the client-side arc (17 → 18 → 18.1 → 19). Three agents, each built in a *different* third-party harness, reach **the same Context Product** through the MCP door shipped in Phase 18.1 — registering it as an ordinary tool, calling it, printing the product to the console. Example 1 is ADK, example 2 is the Anthropic Agent SDK, example 3 is LangGraph, and they are deliberately the same program three ways so that what differs is visibly all harness API and none of it CCF. Each client program imports its harness, an MCP client and stdlib — and **nothing from `ccf`**, gated in the `CLNT-14` shape rather than asserted. This is the first demonstration of §7.3's claim that *a harness which already speaks MCP needs no adapter for consumption*; two prior attempts exist on disk (`examples/external/00-hello-context` from Phase 13.1, and the runner-less Phase 16 orphans in `examples/s2-01-external-consumers`) and neither is against the current surface. **No new SDK mechanism**: no new transport, no new adapter, no change to `ccf.client`, and how the MCP server is assembled stays off-stage until the assembly examples. **Scope confirmed and all four open questions ruled before planning (Dave, 2026-08-20)**: the three legs are CI-green by default on the `examples/external/00-hello-context` replay pattern with `--live` opt-in and no populated-deployment requirement in CI; one directory with three clients and one README; the Phase 16 orphans quarantined or removed and the Phase 13.1 clients marked pre-Phase-17 surface, with Phase 20's trio canonical going forward; requirements continue the `CLNT-NN` lane; and the replay harness is **copied** into the new directory rather than shared with `00-hello-context`, so a canonical example is never coupled to one just marked historical. The ten Success Criteria are the gate target and are not to be expanded during planning

- [x] **Phase 21: Requirement-Ledger Reconciliation — What Is Actually Discharged** (INSERTED) - Commissioned by Dave 2026-08-21 at the Phase 20 close. `.planning/REQUIREMENTS.md` carries **54 not-`Complete` rows** — 21 against Phase 17, 18 against Phase 16, 6 against Phase 14, 3 against Phase 9, 3 against Phase 13, 1 against Phase 18, 1 against Phase 15.5, 1 against Phase 15.6 — while the GSD plan counter reads **100%**, because it matches SUMMARY files to PLAN files and is structurally unable to see that Phase 16 was *retired* rather than executed (14 of its plans sit unexecuted in `abandoned/`). Spot-checks at the Phase 20 close prove the rows split **both ways**: `CLNT-01` requires `ccf.client` to export exactly four names and it does — discharged, never ticked — while `DOCS-17` requires `examples/00`–`08` to be retired and **all nine directories are still in the tree**. Neither a wholesale tick nor a wholesale drop is honest, so the phase's job is **evidence, row by row**: each of the 54 gets a verdict backed by a citation a reader can follow, or a named absence. **Phase 16's eighteen `DOCS-` rows are reported to Dave as a split and ruled by him, not by the executor** (deferred at the Phase 20 sitting: *"tell me after the audit"*). Adjacent and already ruled: the ten phases with no `D-GATE` entry are gated by their ROADMAP completion rows and are **not** backfilled (`D-IMPL-171`) — that gap needs no work from this phase, only that the phase not quietly re-open it. **No fabric change**: `src/` and `runtime/` are untouched, asserted against a base pinned before execution. This phase is what has to land before v0.2 can honestly close.
- [x] **Phase 21.1: The Guard That Did Not Guard — Closing the Check-Vacuity Class** (INSERTED) - Commissioned by Dave 2026-08-22 after the `D-GATE-21` provenance re-run of the close panel surfaced three NEW blocking findings, the first of which is `B-1`'s own fix being vacuous one level down. `tracked_under` validates the pathspec TUPLE and not its MEMBERS, so a one-key typo in any single member of a multi-member constant still reports "tree untouched" over a real breach of the `D-11` scope fence. Scope is the whole *check-cannot-fail* class in one pass — `RR-1`, `RR-2`, `RR-3` blocking, plus `RR-4` and `RR-6` advisory — rather than a narrow fix followed by another residual wave. `D-GATE-21` stays in force; this is a fix wave on the verification machinery, NOT a re-opening of the 54-row audit.
- [x] **Phase 22: The Adoption Argument — What RAG, Hand-Rolled Assembly and a Semantic Layer Lack** (INSERTED, COMPLETE 2026-08-23, `D-GATE-22`) - Commissioned by Dave 2026-08-23 immediately after `D-GATE-21.1`, taking up the Phase 21 work list in the order `D-IMPL-176` sequenced it: *"DOCS-15 first — cheapest, highest adoption leverage, one page, subject already gated in `s1-01`. Only coupling is that tree's survival under CLNT-17."* One published page naming RAG over a vector store, hand-rolled context assembly, and a semantic layer plus prompt templates, stating what each lacks against **cited shipped mechanism**, with the UBO question as its worked demonstration and the passage-anchor honesty caveat carried. Re-derived against today's surface — Phase 16's `16-08`/`16-13` are unexecuted, abandoned and not resumable. Builds nothing and removes nothing: `src/` and `runtime/` stay diff-empty.
- [x] **Phase 22.1: The Hygiene Block — The Tool That Could Not Tell "None" From "Could Not Look"** (INSERTED, COMPLETE 2026-08-23, `D-GATE-22.1`) - Three items cleared so the ledger stops lying and the retirement decision rests on a number that cannot be silently wrong: `tools/retirement_sweep.py` fails CLOSED at its three swallow sites, `RECON-10` is re-measured from the tree rather than from its own stale row text, and the 27 `human_needed` items across 11 phase records are assembled into ONE decision packet for Dave. Builds no feature; `src/`, `runtime/` and `examples/` stay diff-empty. Commissioned by Dave 2026-08-23 immediately after `D-GATE-22`. **Performs no part of the archive move** (`D-IMPL-189`), and leaves `DOCS-17` and `CLNT-17` reading `Not built`.
- [x] **Phase 23: The Archive Move — Retiring the Ten Condemned Example Trees Without Deleting Them** (INSERTED, COMPLETE 2026-08-25, `D-GATE-23`) - Performs `D-IMPL-189`'s archive-with-repoint as the allowed intermediate state for `DOCS-17`: the **ten** trees `DOCS-17` condemns move **INTACT** to `archive/examples/` — **265 files, 58 left under `examples/`, and NOTHING DELETED**, proven a pure rename set in the STRONG form (265 `R100`, 0 D/A/M, 0 insertions, 0 deletions; the weaker `R=265 D=0 M=0` form was REJECTED in-phase because `--diff-filter=M` cannot fire on a renamed path). 111 published references re-pointed across 15 pages, proven a pure prefix substitution by REVERSING it to byte-identical; 14 `make example-*` targets deleted with their `.PHONY` names and the two `live-legs.yml` jobs that invoked them; `make docs-strict` green. `DOCS-17` verdicted **`Partial`** for the first time, in the wording `D-IMPL-191` ruling 4 constrained it to — *out of the `examples:` aggregate*, NOT *out of live CI*. **DELETION REMAINS OWED for every scheduled row** (`D-IMPL-191` ruling 3); `CLNT-17` is EXCLUDED and stays `Not built`. Thirteen plans, thirteen serial waves, 77 commits from `PHASE_BASE` `b87fe58`, merged `--no-ff` at `5a96628`. All **EIGHTEEN** Success Criteria met, locked before Wave 1 per `D-GATE-19` and amended ONLY by ruling. The §3.1 close found **THREE blocking defects, all fixed in-phase and each re-sabotaged** — the headline one being that criterion 10 was never actually discharged: `archive_sweep_problems` ASSERTED a row-count floor while only DOCUMENTING per-tree coverage, so suppressing all 21 rows of one archived tree left 110 rows against a floor of 10 and the predicate returned EMPTY. **Nine of ten trees could have gone dark silently** — the phase's own defect class, a tool that reports clean because it did not look, arriving INSIDE the control written to prevent it. Also ruled at the gate: the chunked-**foreground** form of `make ci` is an allowed satisfaction of criterion 15 on this host under four named conditions, and **criterion 15's TEXT is an owed follow-up, NOT discharged**. *(This bullet was missing from the list until 2026-08-25 — the phase was planned, executed, gated and merged with a `## Phase Details` section and a progress row but no entry here, so `roadmap.analyze` read 27/27 with Phase 23 invisible to it. Identical to the omission recorded against Phase 17, and to the Phase 14.1 note explaining why an absent box is not cosmetic: it is what routed auto-advance into a never-planned phase once before.)*

## Phase Details

### Phase 9: Hardening — Defect Fixes & Ruling Batch

**Goal**: The v0.1 audit's ruling-free defects are fixed and every decision-shaped v0.2 item has a Dave ruling on record, unblocking the rest of the milestone
**Depends on**: Nothing (first phase of v0.2; builds on v0.1.0 on `main`)
**Requirements**: HARD-01, HARD-02, HARD-03
**Success Criteria** (what must be TRUE):

  1. The six-item D-IMPL ruling batch (WR-01 mapping shape, ApprovalGate×D-16 composition, perf governance, docs toolchain/publishing, D-10 amendment, create_app warning) is presented to Dave as one Phase D mini-cycle and every ruling is logged in `docs/DECISIONS.md`
  2. In-memory HITL transports survive a threaded stress test (with timeout) without corruption or deadlock, and the HITLTransportProtocol carries a documented concurrency contract
  3. The ADK workflow driver runs inside an existing event loop with no nested `asyncio.run`, raises typed errors, and cross-adapter parity tests pass across all three drivers (WR-03 fixed before/with WR-02 so the sync/async seam is clean when locks arrive)
  4. The full eight-example CI sweep still passes byte-identically — no expected-output regeneration (any regeneration is a blocking review event)

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 09-01-PLAN.md — Six-item D-IMPL ruling batch mini-cycle with Dave + D-14 pre-phase hash manifest

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 09-02-PLAN.md — WR-03: shared loop-aware dispatch + typed driver errors across all three drivers + parity tests

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 09-03-PLAN.md — WR-02: threading.Lock transport + concurrency contract + hammer test + phase-close byte-identity check

### Phase 10: Hardening — Authorization & Posture

**Goal**: Every HITL door refuses unauthorized tenants by default and every audited human action carries the authorization decision — implemented exactly per the Phase 9 rulings
**Depends on**: Phase 9 (WR-01 mapping shape, ApprovalGate composition, create_app confirmation rulings)
**Requirements**: HARD-04, HARD-05
**Success Criteria** (what must be TRUE):

  1. An unauthorized principal hitting any HITL door (HTTP and MCP) for any action receives a typed 403 deny-by-default refusal, verified by a cross-door × cross-action test matrix
  2. Every authorization decision lands in the audit record; authorization stays out of `/src` core behind `TenantAuthorizerProtocol`, and the SDK invents no scope vocabulary
  3. ApprovalGate.resolve × signed_binding_required behaves per Dave's ruling, with tests pinning the composed behavior
  4. `create_app` on an insecure default posture emits a loud, visible warning (per the confirmed ruling), and examples 05/06 demonstrate tenant authorization

**Plans:** 4/4 plans complete

Plans:

- [x] 10-01-PLAN.md — Authz foundation: ScopeMappingArtifact, TenantAuthorizerProtocol + interpreter, audit extension, A1/A2 spikes
- [x] 10-02-PLAN.md — Signed-binding verification on all four primitive resolution surfaces (D-IMPL-69)
- [x] 10-03-PLAN.md — Door enforcement (HTTP + MCP) + cross-door × cross-action matrix (D-IMPL-68)
- [x] 10-04-PLAN.md — create_app insecure-default warning (D-IMPL-73), call-site sweep, examples 05/06 + manifest re-baseline

### Phase 11: Performance Battery

**Goal**: Adopters and CI can measure the hardened SDK reproducibly, with committed baselines and relative regression gates that catch real slowdowns without runner-variance flake
**Depends on**: Phase 10 (baselines must measure the hardened surface; perf-governance ruling from Phase 9)
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):

  1. `make perf` runs the micro-benchmark suite (operators, factory, validation gates) locally and reports p50/p95/p99 reproducibly
  2. Fabric load/scale curves for assembly and projection across graph sizes are produced from a deterministic, domain-neutral synthetic dataset generator that builds fixtures only through L2/factory paths (no lint-exempted shortcuts)
  3. Cross-process latency (MCP egress, A2A/peering) and replay-at-scale suites run and empirically support the year-scale replay claim
  4. An opt-in `perf.yml` CI job compares against committed runner-class-keyed baselines using relative-median thresholds from `perf/thresholds.toml`, and the re-baseline ritual is documented

**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 11-01-PLAN.md — Foundation: pytest-benchmark extra + A1 check, gate.py + thresholds.toml + gate unit tests, Makefile perf targets
- [x] 11-02-PLAN.md — Synthetic generator: perf/synth/ neutral artifacts + seeded topology/decision stream, rung fixtures, determinism tests

**Wave 2** *(blocked on Wave 1)*

- [x] 11-03-PLAN.md — Micro-benchmark suite (~10–15 benchmarks incl. composed-vs-sequential, run_coroutine_sync) + fabric-scale assembly/projection curves
- [x] 11-04-PLAN.md — Cross-process latency suite (real subprocess MCP/peering) + replay-at-scale ladder with byte-exact + curve-shape assertions

**Wave 3** *(blocked on Wave 2)*

- [x] 11-05-PLAN.md — Bitrot smoke test, opt-in perf.yml, perf/README.md re-baseline ritual, full-battery budget calibration

### Phase 12: Synthetic-Data Demonstration

**Goal**: A newcomer can run one command and watch raw synthetic data become governed context that lets an agent solve a problem it could not solve from the raw data alone
**Depends on**: Phase 10 (demonstrates hardened postures); independent of Phase 11
**Requirements**: DEMO-01, DEMO-02, DEMO-03
**Success Criteria** (what must be TRUE):

  1. A deterministic, multi-entity synthetic fake data store ships as the demonstration substrate, with every domain value in definition artifacts (No-Hardcoding — example code stays thin and generic)
  2. The runnable example ingests the store through L1→L2, folds it into the Context Graph, projects typed Context Products, and an agent consumes them to solve a concrete reasoning problem unreachable from raw data alone
  3. The demo runs in CI alongside the v0.1 examples with a single documented command, deterministically
  4. A narrated step-by-step walkthrough document ("how data folds into context") exists that literal-includes the example's code and artifacts by path, ready for the docs site

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 12-01-PLAN.md — Scenario artifact + deterministic SQLite demo generator + checksum pin tests (DEMO-01)

**Wave 2** *(blocked on Wave 1)*

- [x] 12-02-PLAN.md — run.py end-to-end: baseline contrast, L1→L6 pipeline, agent + cycle-detection skill, byte-compared narration, --live (DEMO-02)

**Wave 3** *(blocked on Wave 2)*

- [x] 12-03-PLAN.md — Makefile/CI wiring, README, docs/demo-walkthrough.md with literal includes (DEMO-03)

### Phase 13: Examples Suite Upgrade

**Goal**: The v0.1 examples suite (00–07) teaches the SDK on its own — every example narrates what it demonstrates and why, and its artifacts exercise enough SDK surface that an adopter can adapt it directly
**Depends on**: Phase 10 (hardened postures demonstrated — e.g., examples 05/06 tenant authorization); can run parallel to Phases 11/12
**Requirements**: EXAM-01, EXAM-02, EXAM-03
**Success Criteria** (what must be TRUE):

  1. Every example 00–07 has a detailed narrated README covering what it demonstrates, an artifact-by-artifact explanation, the whitepaper/CLAUDE.md sections exercised, and "what to change first to adapt it"
  2. Example scenarios exercise materially more SDK surface (specialization axes, skilling, HITL, replay) through richer definition artifacts, while example code stays thin and generic per the No-Hardcoding Rule
  3. The upgraded suite runs green in CI with a single documented command per example, and any expected-output change was a reviewed, deliberate event
  4. An adopter reading only an example's README and artifacts can identify the exact artifact to edit for their own domain — the code/artifact boundary is visible in every example

**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 13-01-PLAN.md — Shared README template skeleton + CCF gloss table + [ADAPT]/[MECHANISM] marker convention (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 13-02-PLAN.md — Examples 00 + 01: enrichment + narrated READMEs; 01 exercises all six specialization axes meaningfully (Wave 2)
- [x] 13-03-PLAN.md — Examples 02 + 03 + 04: skilling depth, harness-portability (deterministic leg), A2A admission narration (Wave 2)
- [x] 13-04-PLAN.md — Examples 05 + 06: ReviewQueue into 05, OverrideBoundary into 06, replay-recorded HITL (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 13-05-PLAN.md — Example 07 enrichment + 08 README retrofit + suite-wide `make ci` phase gate (Wave 3)

### Phase 13.3: Review-Residual Hardening (INSERTED)

**Goal:** Close the actionable residuals from the Phase 13.2 cross-AI review (13.2-REVIEWS.md consensus items that were not resolved by execution): (1) allowlist fail-fast semantics — `ValueError` on unknown `tool_allowlist` entries and a serve-time assert that artifact `tools.*.name` values equal the SDK tool constants; (2) mandatory fingerprint-mismatch unit test plus fail-loud replay startup when a response fixture lacks its `*-request.json` sibling; (3) capture-proxy spec tightening — record only HTTP 200 + JSON bodies, forward query strings, never persist headers; (4) CINV-01 consistency — parameterize (or explicitly exempt and pin with a test) the `list_agents`/`invoke_agent` tool descriptions that still ship as docstring prose.
**Requirements**: EXAM-05 (hardening residuals)
**Depends on:** Phase 13.2
**Plans:** 2/2 plans complete

Plans:

- [x] 13.3-01-PLAN.md — SDK builder hardening: allowlist fail-fast, Optional providers, CINV-01 description parameterization (D-01/D-03/D-04/D-12–14) + builder pinning tests (Wave 1)
- [x] 13.3-02-PLAN.md — Example-side hardening: serve.py artifact-name assert, replay orphan scan + path fingerprint, capture-proxy 200+JSON/query spec + permanent tests/examples/ guards (Wave 2)

### Phase 13.2: external-example-hardening (INSERTED)

**Goal:** Harden `examples/external/00-hello-context` against the four-AI cross-review consensus concerns — live-captured diff-reviewed fixtures with a permanent schema guard and request-fingerprint replay matching, a server-side tool allowlist, and byte-path/README/duration assertion hardening — and execute Dave's 2026-08-02 ruling promoting `get_context`, `get_lineage`, and `get_replay_record` into the SDK Experience surface, enabled by default.
**Requirements**: EXAM-05
**Depends on:** Phase 13.1
**Plans:** 5/5 plans complete

Plans:

**Wave 1**

- [x] 13.2-01-PLAN.md — SDK promotion (D-13) + allowlist parameter (D-05) in experience.py, caller/test updates, EXAM-05 minting, D-IMPL entry (D-14)

**Wave 2** *(blocked on Wave 1)*

- [x] 13.2-02-PLAN.md — serve.py shrinks to composition (D-15); artifact-driven 3-tool allowlist wired

**Wave 3** *(blocked on Wave 2)*

- [x] 13.2-03-PLAN.md — Live fixture capture (D-01a/D-02), capture proxy, fixture-diff utility (D-04), D-10 reviewed regeneration (checkpoint)

**Wave 4** *(blocked on Wave 3)*

- [x] 13.2-04-PLAN.md — Fingerprint-checked replay (D-03) + fixture schema smoke-test (D-01b)
- [x] 13.2-05-PLAN.md — run.py assertion hardening (D-07/08/09 + allowlist visibility), .mcp.json docs verification (D-12), fresh-venv one-off (D-11), `make ci` phase gate

### Phase 13.1: External-Consumer Examples (MCP Egress) (INSERTED)

**Goal:** An engineer with an existing agent in their own harness (Anthropic SDK, Google ADK, or a bare MCP client) can point it at the CCF MCP egress server and consume decision-ready, typed Context Products — with zero CCF imports on the client side. CCF operates as a black box behind MCP; the replay record still lands on the fabric side. This demonstrates §7.1 MCP-as-egress / §8.3 Experience Layer as the primary adoption path, rather than asserting it.
**Rationale (Dave, 2026-08-02):** Users must never be forced to construct agents inside CCF — that becomes tech debt. The harness-independent MCP consumption path is the most important example set the suite needs.
**Requirements**: EXAM-04
**Suggested scope:** `examples/external/00-hello-context` (locked D-01 layout — new `examples/external/` family unified by consumption model, examples 00–08 unchanged): four client legs (`client_bare.py`, `client_anthropic.py`, `client_adk.py`, plus the `.mcp.json` leg), CCF only as an authenticated MCP server URL; family charter README per D-02/D-03; runnable in CI (`make example-ext-00`), deterministic leg for CI plus optional live leg.
**Depends on:** Phase 13. Must land before Phase 14 (Documentation Suite) so the docs can literal-include it.
**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 13.1-01-PLAN.md — Groundwork: mint EXAM-04, add `anthropic` extra, `examples/external/` family charter README
- [x] 13.1-02-PLAN.md — Fabric side: finserv artifacts, serve.py (authed experience MCP + get_context/lineage/replay tools + serve-side replay), replay_server.py

**Wave 2**

- [x] 13.1-03-PLAN.md — Client legs: client_bare.py, client_anthropic.py, client_adk.py + versioned model-API fixtures

**Wave 3**

- [x] 13.1-04-PLAN.md — run.py assertions (401, D-15, D-16, zero-CCF-import grep), seven-heading README + .mcp.json leg, Makefile/CI wiring

### Phase 14: Documentation Suite

**Goal**: A competent engineering team can go from install to a governed, replayable deployment using the docs alone — with every API signature generated, every number measured, and every snippet literal-included from CI-run code
**Depends on**: Phase 11 (measured baselines for PERFORMANCE.md), Phase 12 (demo walkthrough content), Phase 13 (docs literal-include the upgraded examples), Phase 9 (docs toolchain/publishing + D-10 rulings; reference generation may start in parallel with Phase 11)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06
**Success Criteria** (what must be TRUE):

  1. The adopter's guide walks day-1 to production (install → ontology → agent → workflow → replay) end-to-end, with every code snippet literal-included from CI-run examples — no pasted snippets, no hand-written signatures
  2. The Protocol/API reference is generated from the citation-bearing docstrings via mkdocs-material + mkdocstrings, and the site build provably never publishes the whitepaper or internal phase deliverables
  3. The definition-artifact schema reference covers the adopter's primary authoring surface, and how-to + concepts pages (pillars, invariants, replay anatomy, whitepaper cross-reference index) exist
  4. Security & deployment notes document the hardened postures from Phases 9–10, and the OpenAPI spec is regenerated from `create_app()` with a CI drift check
  5. `make docs --strict` passes in always-on CI (logged D-10 amendment), and PERFORMANCE.md publishes the Phase 11 measured baselines with methodology and environment manifest

**Plans**: 10 plans in 4 waves

Plans:
**Wave 1**

- [x] 14-01-PLAN.md — docs toolchain foundation: `docs` extra, `site/` gitignored, `public/` docroot + stubs, `mkdocs.yml` with `check_paths: true` and raised link validation
- [x] 14-02-PLAN.md — `tools/publish_scan.py` never-publish gate (no allowlist) + its controls, then the D-20 rework of the 13 whitepaper-quoting docstrings

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 14-03-PLAN.md — committed `openapi.json`, `make openapi` regenerator, and the always-on drift assertion against `create_app()`
- [x] 14-04-PLAN.md — D-03 move: `git mv` walkthrough, security notes and all 11 diagrams into `public/`; repoint inbound refs; Dave rules the CLAUDE.md edit

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 14-05-PLAN.md — Concepts section: five pillar pages with in-page diagrams, invariants, replay anatomy, whitepaper cross-reference index, diagram-coverage test
- [x] 14-06-PLAN.md — Reference section: 12 curated Protocol pages, 8 generated artifact-schema pages, the HTTP contract page, and the mkdocstrings drift control
- [x] 14-07-PLAN.md — snippet markers in six example sources + the adopter's guide, all literal-included; snippet drift control
- [x] 14-08-PLAN.md — five task how-to pages over green CI-run examples + the security & deployment page finished as a how-to
- [x] 14-09-PLAN.md — run the perf battery, Dave-gated baseline commit (D-IMPL-75), PERFORMANCE.md with methodology and environment manifest

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 14-10-PLAN.md — `docs-strict` gate target, `make ci` D-IMPL-72 amendment, always-on CI docs job with artifact upload

### Phase 14.1: Documentation — The Deterministic Path & The Adoption Argument (SUPERSEDED)

**Status**: superseded by Phase 16, 2026-08-03, before any plan was written. Dave's
discuss-phase read of the SDK surface found a defect underneath the documentation defect:
the integration surface the docs describe is itself too verbose to document well. Rewriting
the documentation against a surface we intend to change is wasted work, so the ergonomics
pass (Phase 15) comes first and the documentation rewrite (Phase 16) follows it, carrying
every success criterion below plus the structure Dave specified in this discussion.

Nothing in this entry is dropped — see Phase 16, which absorbs it whole.

### Phase 15: SDK Ergonomics — The Integration Surface

**Goal**: The day-1 integration an adopter writes against CCF is a fraction of what it is
today, because the SDK absorbs the mechanical work it currently leaves to every deployment —
without hiding one governance decision from the adopter or one dimension from the replay
record
**Depends on**: Phase 14 (closed as-shipped; its documentation stands as the record of the
surface being replaced)
**Requirements**: ERGO-01..ERGO-17 (minted 2026-08-04; see `.planning/REQUIREMENTS.md`)
**Origin**: Dave, 2026-08-03, coding against the CCF SDK documentation. "The whole purpose of
the SDK is to provide as much abstraction around details as possible and save me the time of
doing them manually."

**The evidence that opened it** (measured against `examples/00-quickstart/run.py`, 451 lines):

  - ~85 lines are CI assertions and print summaries — no adopter writes them, but they are
    inside the published snippets, inflating the apparent integration cost
  - ~105 lines are YAML→typed-object marshalling: `_resolution_spec`, `_envelopes`, and four
    hand-built operator parameter sets. `src/ccf/controlplane/artifacts.py` registers exactly
    **two** artifact classes with a declarative parse path (`ccf.half-life-table`,
    `ccf.debt-profile`); every other artifact shape is marshalled by hand in example code
  - ~45 lines are the projection Π — genuinely deployment code (whitepaper §7.5) and not a
    target
  - ~55 lines are the actual CCF call spine — roughly eight calls, L1 through L6

  The No-Hardcoding Rule (CLAUDE.md §6.4) pushed the *values* into artifacts correctly and
  left most of the *interpreters* in `/examples`, where they are copy-paste fodder. §6.4 says
  code contains interpreters and factories, never the things interpreted — the interpreter
  for half-life tables lives in `/src` where it belongs; the interpreter for operator
  parameters does not exist.

**Success Criteria** (what must be TRUE):

  1. A holistic audit of the adopter-facing surface exists, naming every point where a
     deployment writes mechanical code the SDK could supply, with the day-1 line count
     measured before and after
  2. Declarative artifact classes and loaders cover the shapes an adopter must currently
     hand-marshal — resolution specs, signal envelopes, operator parameters, product-class
     declarations, perspectives — reached through the same `parse_artifact` seam that already
     serves half-life tables and debt profiles
  3. Boot, registry population, and operator-registry construction are reachable from
     artifacts without per-deployment wiring code
  4. Every shipped helper is answerable to "what does this hide from the replay record?" with
     "nothing" — the abstraction line is **marshalling and wiring only** (D-15A below)
  5. The eight-example suite and `examples/external/` are rewritten to the streamlined
     surface and stay CI-green, with the day-1 example demonstrably smaller
  6. Every removed or reshaped public surface is recorded, so Phase 16 can document the
     surface that exists rather than the one that was

**Rulings carried in from the discussion (Dave, 2026-08-03):**

  - **D-15A — the abstraction line is marshalling and wiring only.** Helpers may absorb
    YAML→typed-object loading, registry population, boot wiring, and operator construction
    from artifacts. Every point where a deployment *asserts something the fabric then
    verifies* stays explicit in adopter code. The worked case: `run_gates()` takes the
    engine's resolved operators separately from the product's own lineage claim precisely so
    lineage strict equality has two independent sources; a helper computing both from one
    input would make the gate tautological and silently delete a whitepaper invariant.
    Dave reserves the right to revisit surface by surface where an ergonomic win requires
    touching a governance boundary — such cases are surfaced as decisions, not resolved by
    the phase.
  - **D-15B — free rein on the public API, pre-1.0.** The phase may reshape, rename, collapse,
    or remove any public surface in the way; examples and docs are rewritten to match.
    `v0.1.0` stays tagged as the historical artifact. Anyone building against v0.1/v0.2 today
    has a migration, and that is accepted.

**Non-goals**: new fabric capability; demonstrating Assembly Modes 2 or 3 (v0.3); the
documentation rewrite itself (Phase 16). Simplification that costs an invariant is not
simplification — it is a fidelity defect, and CLAUDE.md §1 ranks fidelity first.

**Plans**: 21 plans across 14 waves

Plans:
**Wave 1** — the public-surface baseline (nothing else may start first)

- [x] 15-01-PLAN.md — Public-surface baseline: `tools/dump_surface.py` (`--check` + `--report`), committed manifest, documented-drift gate, surface-change fragment home (ERGO-01, ERGO-17)

**Wave 2** — standing guards, built on the baseline

- [x] 15-02-PLAN.md — `ccf.deployment` package shell + the D-15A gate-independence guard + the no-allowlist import ban (ERGO-02, ERGO-04)
- [x] 15-03-PLAN.md — Executable surface audit baseline + falsification of research assumptions A1/A3/A6 (ERGO-03)

**Wave 3**

- [x] 15-04-PLAN.md — D-IMPL-78: widen CINV-01 over `tests/` (two edits: `LINTED_TREES` and `RULE_TREE_SCOPE`) (ERGO-16)
- [x] 15-05-PLAN.md — D-02 timestamp handling in the artifact load path (ERGO-06)
- [x] 15-06-PLAN.md — class-id → `ArtifactClass` lookup + `tests/deployment/` package (ERGO-05)

**Wave 4**

- [x] 15-07-PLAN.md — `ccf.resolution-spec` + `EntityResolutionSpec` semver in place, with its own regeneration checkpoint (D-IMPL-77) (ERGO-07)

**Wave 5**

- [x] 15-08-PLAN.md — Four operator-parameters artifact classes + both `artifacts.py` docstring amendments (ERGO-08)

**Wave 6**

- [x] 15-09-PLAN.md — Signal-batch, perspective, and product-class artifact classes (ERGO-09)

**Wave 7**

- [x] 15-10-PLAN.md — `ccf.deployment-manifest` + `load_and_boot` + the plain pin set (ERGO-10)

**Wave 8**

- [x] 15-11-PLAN.md — `build_operator_registry`, two-phase and view-aware, pin set passed in (D-IMPL-76) (ERGO-11)
- [x] 15-12-PLAN.md — Committed JSON Schemas + `ccf schema export` through an HTTP route (D-IMPL-79) (ERGO-12)

**Wave 9**

- [x] 15-13-PLAN.md — Rewrite example 00 quickstart — the day-1 integration (ERGO-13, ERGO-16, ERGO-12)

**Wave 10**

- [x] 15-14-PLAN.md — Rewrite examples 01 agent-basics and 02 skilling (ERGO-13, ERGO-16, ERGO-12)
- [x] 15-15-PLAN.md — Rewrite examples 03 harness-portability and 07 artifact-store-mcp (ERGO-13, ERGO-16, ERGO-12)
- [x] 15-16-PLAN.md — Rewrite example 08 e2e-demo + the DEMO-03 narration review (ERGO-13, ERGO-16, ERGO-12)

**Wave 11**

- [x] 15-17-PLAN.md — Rewrite example 06 decision-replay, pins kept explicit (ERGO-14, ERGO-16, ERGO-12)
- [x] 15-18-PLAN.md — Rewrite example 04 cross-process + re-domain to banking, as two commits (ERGO-14, ERGO-16, ERGO-12)

**Wave 12**

- [x] 15-19-PLAN.md — Rewrite example 05 workflow-hitl (ERGO-14, ERGO-16, ERGO-12)

**Wave 13**

- [x] 15-20-PLAN.md — Rewrite the external example's `serve.py`, client legs untouched (ERGO-15, ERGO-12)

**Wave 14**

- [x] 15-21-PLAN.md — Phase close: curated surface-change log, the single manifest regeneration and criterion-1 audit, the tree-wide `$schema` and D-14 gates, `/gsd-review` and presentation to Dave (ERGO-01, ERGO-03, ERGO-12, ERGO-17)

### Phase 15.1: Ergonomics Gap Closure — Governance Enforced, Not Conventional (INSERTED)

**Goal**: The two governance guarantees Phase 15 shipped as *convention* become guarantees the code *enforces* — a manifest cannot route an author-versioned artifact class around the D-05 bump check, and the operator set a deployment declares can no longer agree with the set it executes by construction, because the two now come from separately authored artifacts bound by a check — placed between plan construction and `ProjectionEngine.execute`, per the D-IMPL-86 correction of 2026-08-05 — that refuses when they disagree (design E2, D-IMPL-86)
**Depends on**: Phase 15 (closed and gated; D-GATE-15 amended rather than revoked)
**Blocks**: Phase 16 — the documentation rewrite must not describe a self-satisfying gate
**Requirements**: ERGO-18, ERGO-19
**Requirements note**: ERGO-18/19 are minted during this phase's first plan, per the Phase 15/16 precedent recorded in §Coverage. ERGO-01..17 stay Complete — this phase closes defects in what they delivered, it does not reopen them.
**Origin**: Post-gate cross-AI design review commissioned by Dave after D-GATE-15, on
discomfort with the shipped state (`15-REVIEWS-round3.md`, 2026-08-05). Four independent
systems — gemini, codex, cursor, ollama — reviewed the *shipped code*, not the plans, against
"is this a sound design approach, and should this phase have shipped at all?" All four: sound,
yes. Risk LOW (gemini), MEDIUM (codex, cursor). Two HIGH defects, each verified against source
by the orchestrator rather than accepted on report.

**The two confirmed defects:**

  - **CR-1 — author-versioned classes can bypass the D-05 bump check via the manifest.**
    `SDK_ARTIFACT_ROLES` fixes exactly one class, `ccf.signal-batch`.
    `refuse_role_the_sdk_fixes` accepts `role: register` for `ccf.workflow-definition`,
    `ccf.agent-definition` and `ccf.task-definition`, all of which then route through
    `register_typed` — which runs no hash-verified bump check. The 15-19 split ruling is a
    convention the shipped examples follow, not an enforced invariant:
    `test_the_author_versioned_definitions_kept_their_bump_check` proves the examples do it
    right; nothing proves the manifest refuses the wrong thing. Raised independently by codex
    and cursor; gemini raised the same split as its only HIGH. Codex stated the falsifiable
    test: "If adopters can put workflow/task/agent definitions in the manifest with
    `role: register` and thereby use `register_typed`, the design is unsound."
  - **CR-2 — Gate 2 is self-satisfying in every example, a NINTH instance of the phase's own
    signature finding.** Verified across 9 files: each constructs
    `ProductLineage(operators_invoked=execution.operators_invoked, ...)` and then calls
    `run_gates(candidate, engine_resolved=execution.operators_invoked)` — the same value on
    both sides of lineage strict equality. Files: `00-quickstart`, `01-agent-basics`,
    `02-skilling`, `03-harness-portability`, `04-cross-process/producer_child`,
    `06-decision-replay`, `07-artifact-store-mcp`, `08-e2e-demo`,
    `external/00-hello-context/serve`. The phase closed the *upstream* `required_operators()`
    collapse and numbered around this one; `test_gate_independence.py` admits callers outside
    `ccf.deployment` may pass the same value twice. Raised by cursor alone.

**The fix all three substantive reviewers converged on, independently**: a per-entry
registration mode in the manifest — `registration: typed | versioned` — that `load_and_boot`
dispatches on, routing author-versioned classes to `register_versioned` and **refusing** any
manifest that registers them through `register_typed`. Everything stays in the manifest; one
mental model; governance enforced rather than conventional. Gemini's variant:
`version_policy: strict_bump`. Codex adds "tests proving workflow/task/agent definitions
cannot bypass bump checks through the manifest." Cursor: "same ergonomics win without the
split." Both codex and cursor called the shipped split **backwards** — the more
governance-sensitive the artifact, the *less* declarative Phase 15 made it.

**Success Criteria** (what must be TRUE):

  1. A manifest that declares an author-versioned class (`ccf.workflow-definition`, `ccf.agent-definition`, `ccf.task-definition`) for typed registration is **refused at load**, with a test that asserts the refusal — not a test that the examples happen to avoid the pattern
  2. The registration mode is declared per entry in the manifest and dispatched by `load_and_boot`; the artifact author does not have to know which of two registration paths their class belongs to
  3. `lineage.operators_invoked` is filled from the product-class declaration — never from `execution.operators_invoked` — in every example that runs Gate 2, and the projection's required operator set comes from its own Control Plane artifact rather than from the product-class artifact, so the declared and executed sets are separately authored (D-IMPL-86, design E2)
  4. A binder **refuses** when `product_class.required_operator_keys != frozenset(plan.required_operators())`, placed where a plan exists — between plan construction and `ProjectionEngine.execute`, **not** inside `load_and_boot`, which has no plan in scope (D-IMPL-86 correction, 2026-08-05) — and a test proves the refusal fires when the two artifacts are edited into disagreement. This is where authorable drift fails, and it is reachable by editing an artifact rather than only by writing a bug. The residual the placement creates — nothing outside `examples/` holds a deployment to calling the binder — is named in the deliverables and surfaced at the gate, not left in a docstring
  5. Gate 2 is documented for what it verifies — **assembly-path integrity**, the claim transcribed into the Contract equalling the engine's execution of the plan — and every site asserting that it compares two independently authored sets is corrected, including `src/ccf/products/gates.py`'s module docstring and `:244-250`, the `ProductClassDeclaration` docstring at `src/ccf/controlplane/artifacts.py::ProductClassDeclaration`, and `docs/SURFACE-AUDIT.md` §3.1 item 1. D-IMPL-57's intra-fabric "the engine's resolution is an independent witness" premise is corrected with it: the engine is a faithful transcriber of the plan, which holds under every design considered
  6. A tripwire refuses any call site filling both of Gate 2's arguments from `execution`, closing the shape CR-2 found
  7. `docs/SURFACE-AUDIT.md` §4.1 is corrected: "eight instances" is an undercount, and the ninth (the Gate 2 call-site pattern) is entered with the same accounting discipline
  8. The new AST gates are restated as **tripwires** — they catch known patterns — rather than as structural enforcement on par with single-writer DI, strengthened by D-IMPL-86's finding that no AST gate can distinguish an authored literal from a transcribed one
  9. The public-surface manifest and the `--check` drift gate stay green; no replay dimension is hidden by anything this phase adds

**Scope amendment (Dave, 2026-08-05, D-IMPL-86):** the original "two HIGH items only" ruling
is widened by design E2, which adds a projection-requirements artifact class and a
binder — new mechanism, not defect closure. E2 also revises the gated 15-09 decision, so this
phase runs as a Phase D mini-cycle under CLAUDE.md §3.1 with D-IMPL-86 as the ruling of record.
Rationale: shipping the cheaper option first would have Phase 16 document an "assembly-path
integrity" framing that a later phase then rewrites — Phase 14's G-01 defect repeated.

**Non-goals** (everything else the two-HIGHs ruling excluded still stands):
reopening the Phase 15 abstraction line (D-15A stands); **D-IMPL-81** (pinning the manifest
itself) — ruled out, it stays open debt against Phase 16 or later; **codex's per-gate
independence matrix** (`Invariant | Declared source | Observed source | Test proving they can
diverge`, with a divergence test for every gate) — ruled out, CR-2's mutation test covers
Gate 2 only; the Phase 16 documentation rewrite; the remaining agreed concerns from the review
that are not the two HIGH items — `BootedFabric.artifacts` role blurring and erosion pressure
are recorded, not closed here.

**Plans**: 10 plans in 7 waves

Plans:
- [x] 15.1-01-PLAN.md — mint ERGO-18/19, widen `ControlPlaneProtocol` with `register_versioned` (D-IMPL-82), add the `ccf.projection-requirements` artifact class (E2), widen the surface-change fragment glob
- [x] 15.1-02-PLAN.md — `registration: typed | versioned` required-no-default on `ManifestEntry` (D-IMPL-85), dispatch in `load_and_boot`, `ArtifactPin.registration` (D-IMPL-83), 163-entry migration
- [x] 15.1-03-PLAN.md — `SDK_VERSIONED_ARTIFACT_CLASSES`, the registration refusal, the `ccf.`-namespace reservation (D-IMPL-84), and the four refusal tests
- [x] 15.1-04-PLAN.md — the binder `refuse_operator_set_divergence` (E2 element 3) and its divergence/agreement pair
- [x] 15.1-05-PLAN.md — examples 00, 01, 02 onto E2: lineage from the product-class claim, plan from the projection-requirements artifact, binder call
- [x] 15.1-06-PLAN.md — examples 03, 04-producer, 07 onto E2
- [x] 15.1-07-PLAN.md — examples 06, 08, external/00 onto E2; the two correct replay legs and `test_ext00_hardening.py` left untouched
- [x] 15.1-08-PLAN.md — the Gate 2 call-shape tripwire (E2 element 5), the binder-call coverage check, and example-scale divergence coverage
- [x] 15.1-09-PLAN.md — documentation corrections: `gates.py` both sites, `ProductClassDeclaration`, `SURFACE-AUDIT` §3.1 and §4.1 (nine), tripwire restatement, D-IMPL-57's premise
- [x] 15.1-10-PLAN.md — phase close: surface regeneration, criterion evidence, `/gsd-review` + triage, present to Dave (checkpoint)

**Waves**: 1 → 01; 2 → 02; 3 → 03; 4 → 04; 5 → 05, 06, 07 (parallel); 6 → 08, 09 (parallel); 7 → 10 (checkpoint)

### Phase 15.2: Substrate Adapters and Query Pushdown (INSERTED)

**Status**: inserted 2026-08-07 from a design conversation with Dave; not yet
discussed or planned. The goal and constraints below are Dave's, recorded at
insertion; success criteria and requirement IDs are `/gsd:discuss-phase 15.2`'s
to write.

**Goal**: The fabric asks a substrate a *question* instead of loading its graph.
Today `GraphReader.as_of()` returns a fully materialized `GraphView` — every
entity and relationship for a tenant, per read — so a substrate can conform but
can never answer. That does not scale to a financial-services graph, and it
forecloses graph-native engines: a Neo4j or Neptune adapter would translate
"give me everything" rather than push traversal into an engine built for it.
This phase introduces the read seam operators express intent against, and
adapters that answer it — SQL in the Postgres adapter, Cypher in Neo4j, Gremlin
in Neptune, aggregation pipelines in Mongo, client-side scan where there is no
query engine at all.

**Depends on**: Phase 15.1 (the binder and registration seams it must not disturb)
**Blocks**: Phase 16 — do not document a read surface this phase will reshape

**Scope: two tiers now, a third designed for.**

- **Tier 1 — storage adapters.** Substrates answering queries over graph state.
  No lineage of their own; L2 supplies it, as today.
- **Tier 2 — a Context Product as a source.** In-process, over MCP, or over A2A,
  from this fabric or another — the recursive enrichment §6.6 names and the
  composition `ContextAssemblyAgent` exists for. The governance already exists in
  `src/ccf/peering/admission.py` (`union_lineage`, `SignatureRefusal`,
  `ContractRefusal`, `PolicyBindingRefusal`, `LineageContinuityRefusal`,
  `AdmissionBypassError`). What is missing is that admission is an *ingress path
  to L3*; nothing lets an operator treat an upstream product as a queryable
  source at read time.
- **Tier 3 — raw external sources** (REST, lake, vector store) are **out of scope
  for this phase and will be added later.** The design must accommodate them
  without a major refactor (Dave, 2026-08-07).

**Design constraints — the tier-3 no-refactor commitment, made testable:**

  1. **Provenance is an explicit per-adapter obligation in the interface, never an
     assumption.** Tier 1 carries none, tier 2 arrives with it, tier 3 will have
     none. An interface that assumes any of the three breaks on the others. Each
     adapter declares what it can attest to; the fabric refuses what does not meet
     the product's requirements.
  2. **Admission is a seam every non-graph source passes through** — wired for
     tier 2 now, reusable by tier 3 — not a tier-2-shaped special case that tier 3
     must route around.
  3. **Canonical ordering and serialization belong to the interface, not the
     adapters**, so replay determinism is inherited rather than re-implemented,
     and two conformant substrates cannot produce two different Context Products
     from the same data.

**Invariants this phase must preserve** (they are why the materialized view exists
and why this is a design phase rather than a Protocol addition):

  - **Operator purity.** An operator is a pure function over graph state
    (whitepaper §7.4). A lazy result that can change under it is not a value it can
    be pure over — whatever the seam returns must be a frozen, deterministic value.
  - **As-of correctness (INV-CH7-14).** Every adapter must answer "the state you
    held at T": claims observed later absent, claims superseded later still
    current. Not every substrate does temporal natively; those adapters must
    implement it.
  - **Single-writer (INV-CH7-10)** and **policy binding at assembly time
    (INV-CH7-03)** hold unchanged. No adapter acquires a write handle.
  - **Replay portability.** The same question against the same data yields the same
    bytes on any conformant substrate.

**Open questions for discuss-phase:** which substrate(s) beyond Postgres/SQLite
prove the seam (Neo4j as the strongest pushdown test; a KV store as the adversarial
floor; Mongo has an in-house triangulation point per CLAUDE.md §2.1); whether a
substrate conformance suite is a deliverable; and whether existing operators change
shape or only what they are handed.

**Requirements**: SUBQ-01..SUBQ-11 — minted at planning, 2026-08-07 (REQUIREMENTS.md
rows land in plan 15.2-01); not counted in Coverage below.

**Plans**: 14 plans in 9 waves *(redrawn 2026-08-07 against the D-IMPL-87 resolution — the prior 13-plan set is void and archived in `void-plans-pre-D-IMPL-87/`; multi-segment pushdown with `allowed_entities` under the uniform rule, CP-valued survivor cap, hash+ArtifactStore replay pin, prose-lane versioning)*

Plans:
**Wave 1**

- [x] 15.2-01-PLAN.md — Query-semantics prose v1 (`GQ-NN` clauses incl. uniform rule, induced subgraph, size cap, fixed point; semver lane per D-12) + SUBQ-01..11 requirement minting (amended texts)
- [x] 15.2-02-PLAN.md — Substrate-neutral write seam: typed `_GraphTxn` operations in `ccf.graph._writer` (entailed by D-05/D-06 + INV-CH7-10)
- [x] 15.2-03-PLAN.md — Substrate-neutral read materialization core extracted from `BaseGraphReader` (rows → records → canonical order → freeze; the read-side twin of 15.2-02)

**Wave 2** *(blocked on Wave 1)*

- [x] 15.2-04-PLAN.md — `GraphQuery` (with `allowed_entities`)/`TraversalSpec`/`QueryFragment`/`SourceAttestation` frozen contracts + hash-pin tests incl. allowed_entities distinctness

**Wave 3** *(blocked on Wave 2)*

- [x] 15.2-05-PLAN.md — `ccf.graph.fallback` (incl. allowed_entities set-intersection) + `GraphReader.query()`/`attestation` widened atomically everywhere + `as_of()` derivation (D-07) + property suite on the fallback incl. resurrection closure

**Wave 4** *(blocked on Wave 3)*

- [x] 15.2-06-PLAN.md — Memory backend (KV floor) + boot/manifest wiring + differential suite + query corpus incl. allowed_entities/resurrection strategies
- [x] 15.2-07-PLAN.md — `read_intent()` + engine-owned multi-segment segmentation (uniform rule, survivors → seeds + allowed_entities) + D-10 cap mechanism + per-plan equivalence with Gate 2 pinned + pushability matrix

**Wave 5** *(blocked on Wave 4)*

- [x] 15.2-08-PLAN.md — Replay pins per D-11: dim-5 hash tuple + query bytes in the ArtifactStore (`ccf.graph-query`) + D-10 cap value on the deployment manifest with dim-2 pin + replay recompute-and-compare
- [x] 15.2-09-PLAN.md — SQLite/Postgres native pushdown (recursive CTE, hop admissibility + allowed_entities membership in the recursive term)
- [x] 15.2-10-PLAN.md — `ProductSource`: tier-2 Context-Product-as-source over the admission gate

**Wave 6** *(blocked on Wave 5)*

- [x] 15.2-11-PLAN.md — Attestation accepted modes on product classes + pre-execute refusal + gate-path enforcement + dim-1 replay pin + combined three-field record-compatibility matrix

**Wave 7** *(blocked on Wave 6)*

- [x] 15.2-12-PLAN.md — Neo4j adapter (Cypher pushdown incl. parameterized allowed_entities) + `neo4j` extra + container-gated CI leg

**Wave 8** *(blocked on Wave 7)*

- [x] 15.2-13-PLAN.md — Mongo adapter ($match + $in first, staged $graphLookup) + `mongo` extra + container-gated CI leg

**Wave 9** *(blocked on Wave 8 — checkpoint)*

- [x] 15.2-14-PLAN.md — Phase close: single surface regeneration, full gates + three container legs, one perf run, §3.1 review, present to Dave with D-IMPL-87 re-ratification evidence

### Phase 15.3: Fluree Adapter (Tier-1 Substrate) (INSERTED)

**Status**: inserted 2026-08-07 by D-IMPL-88 (Dave); **discussed 2026-08-08**
(12 locked decisions D-01..D-12, ratifying D-IMPL-88 precondition (b)) and
**planned 2026-08-08** (five plans, five waves). The goal and the constraints
below are Dave's ruling plus the feasibility research
(`.planning/research/FLUREE-ADAPTER.md`), recorded at insertion; the success
criteria and requirement IDs below were written at planning against
`15.3-CONTEXT.md`, `15.3-RESEARCH.md` and `D-IMPL-92`.

**Goal**: CCF's Context Graph runs on Fluree v4 through the Phase 15.2 seams —
a tier-1 storage adapter answering `GraphQuery` with pushed openCypher and
satisfying the `_GraphTxn` write seam with batched HTTP commits — with zero
changes to the SDK core, the query vocabulary, or the conformance suites. A
post-gate adapter going green against the unchanged 15.2 suites (suite diff:
one fixture parameter) is the 15.2 no-refactor claim demonstrated on a real
substrate.

**Depends on**: Phase 15.2 (the read/write seams, the differential + property
suites and corpus, the container-leg and extras/boot/manifest precedents, and
the 15.2-02 remote-batched-substrate hedge D-IMPL-88 applied)

**Posture (D-IMPL-88):** CCF stays substrate-neutral. Fluree is an adapter
(this phase) and a source (MCP ingress today; tier 3 when it lands) — never a
foundation. The bank's KG is a system of record CCF assembles *from*, not
CCF's graph.

**Constraints recorded at insertion (research-derived; discuss-phase ratifies):**

- **Target the v4 line** (BSL 1.1 → Apache 2.0; Additional Use Grant clean for
  CI containers and wire-only adapters). **Precondition:** confirm the
  institution runs v4, not legacy v2-AGPL — a v2 shop changes the deliverable
  entirely (D-IMPL-88 precondition (a)).
- **Translation template is 15.2-12 (Neo4j):** v4 speaks openCypher — bounded
  var-length paths, hop predicates, `UNWIND`/param for `allowed_entities`.
  SPARQL cannot express bounded depth; Cypher is the traversal target.
- **Temporal fields are properties, filtered like SQL/Neo4j/Mongo.** Fluree's
  native time travel (`t`) is transaction time and MUST NOT implement as-of
  (INV-CH7-14 filters on observed/superseded claim data; divergent on late
  arrivals and supersession — non-conformant against the differential corpus
  by construction).
- **No new Python dependency:** httpx wire client (already a core pin).
  `fluree-py` is not on PyPI (unregistered, squattable — supply-chain hazard;
  do not install); `aioflureedb` targets the dead v2 API.
- **Write posture:** buffered batch recommended — `_FlureeTxn` accumulates
  typed operations, commits as one atomic `POST /update`; per-op rowcounts by
  read-before-buffer, sound under INV-CH7-10 single-writer. Bolt explicit
  transactions rejected (Raft/peer deployments refuse BEGIN); per-op
  autocommit rejected (abandons atomicity). Discuss-phase ratifies
  (D-IMPL-88 precondition (b)).
- **Known pitfalls carried from research:** JSON-LD datatype coercion (fixed
  minimal `@context`, no ledger default context); read-after-write (thread
  last commit `t` via `Fluree-Min-T`); one CCF-owned ledger with `tenant_id`
  as predicate (SQL multi-tenant posture); exact image pin (breaking changes
  have shipped inside a minor); container-gated CI leg per the 15.2 pattern.

**Effort shape (revised at planning, 2026-08-08).** The insertion-time estimate
(one plan-pair, two to three tasks, one wave) was revised **upward on the
stage-2 side** by the phase research and held on the read side. Packaging is
near zero (httpx is a core pin; one pytest marker; no extra, no mypy override,
no lazy import). The store envelope is comparable to Neo4j's. `_FlureeTxn` is
~1.5–2× `_Neo4jTxn`. **Stage-1 read translation is NOT nearly verbatim** — the
policy family cannot use dynamic property access and the 1 MB query-body cap
needs a byte-budget decline. **Stage 2 is the hardest single piece in the
phase**: three Fluree-specific structural breaks require an adapter-internal
physical-model change (edge-as-node interposition), and the openCypher
front-end is six weeks old at the pin. Five plans, five waves, strictly
sequential.

**Success Criteria** (what must be TRUE):

  1. The four probes that fail *silently* — F-A1 container round trip, F-A4
     ground-batch semantics, F-A5 zero datatype coercion, F-A6 dynamic property
     access — run against the pinned `fluree/server:4.1.4` **before any code
     depends on them**, and the two that fail *loudly* (F-A2, F-A3) run before
     any stage-2 promotion code
  2. A fabric boots against Fluree v4 with no extra installed, writes through L2
     as one buffered ground JSON-LD POST, and reports **12 passed** on the
     unchanged `tests/conformance/test_graphstore.py` under `-m fluree`
  3. The `fluree` param answers the **unchanged** differential corpus
     byte-identically against the audited fallback oracle, and the push is
     proven by discriminating `translated_answers`/`fallback_answers` telemetry
     that has been watched to fail — not by byte-identity a degrade would also
     satisfy
  4. Stage 2 either promotes at byte-identity over the full corpus with the
     depth 0/1/2/3 doubling asserted first, **or** ships stage 1 with a
     maintained `DI-15.3-NN` entry — both satisfy SUBQ-12 under its stage hedge
  5. `make gate-15.3` implements `D-IMPL-92` as corrected, has been watched to
     exit non-zero on three distinct violations, and the gate package is
     committed with the phase — including its own stated limits
  6. The `fluree` leg is a fourth **always-on, blocking** service leg in
     `ci.yml` pinned to `4.1.4` exactly, with a scheduled `live-legs.yml` drift
     job against the floating `4.1`, and `docs/GRAPH_QUERY_SEMANTICS.md`,
     `perf/baselines/` and `perf/thresholds.toml` byte-untouched across the
     whole phase

**Requirements**: SUBQ-12, SUBQ-13, SUBQ-14

**Plans:** 6/5 plans complete

Plans:

**Wave 1**

- [x] 15.3-01-PLAN.md — Probes F-A1/F-A4/F-A5/F-A6 before any dependent code, the `fluree` marker/fixture/`leg-fluree` plumbing, and the F-A4(a) ruling gate (checkpoint)

**Wave 2** *(blocked on Wave 1)*

- [x] 15.3-02-PLAN.md — `FlureeGraphStore` envelope, `_FlureeTxn`/`FlureeGraphWriter` buffered-batch write path, Tier-B registration, and the six write semantics green

**Wave 3** *(blocked on Wave 2)*

- [x] 15.3-03-PLAN.md — Stage-1 non-traverse pushdown, the differential param, the fourth always-on CI leg, and the falsification-tested pushdown telemetry

**Wave 4** *(blocked on Wave 3)*

- [x] 15.3-04-PLAN.md — F-A2/F-A3, the interposed bounded undirected walk with depth 0/1/2/3 asserted, and promotion at byte-identity or a recorded stage-1 degrade

**Wave 5** *(blocked on Wave 4)*

- [x] 15.3-05-PLAN.md — `make gate-15.3` implementing D-IMPL-92 (checkpoint), the scheduled drift detector, and the committed gate package

### Phase 15.4: Backend Registration Seam — The Substrate Stops Naming Its Adapters (INSERTED)

**Status**: commissioned 2026-08-09 by `D-IMPL-93` (Dave). The goal and
constraints below are Dave's, recorded at commissioning; success criteria and
requirement IDs are `/gsd:discuss-phase 15.4`'s to write. This section was
added 2026-08-09 to repair a malformed insertion — the summary-list entry was
written without its detail section, which left every GSD handler unable to
resolve the phase.

**Goal**: The dependency arrow between the core and its graph adapters points
the wrong way, and adding a substrate costs roughly 96 lines across three core
files. `src/ccf/boot.py` and `src/ccf/graph/_writer.py` import
`ccf.graph.backends.*`; `_open_backend` and `_preflight_backend` carry two to
three keyword arguments per substrate; `controlplane/artifacts.py` hand-maintains
a `Literal` naming all six. Invert it. Each backend declares itself — name,
factory, the connection configuration it requires, its preflight rule — the core
holds a registry and looks up instead of branching, the per-substrate keyword
arguments collapse into one configuration mapping, and the `Literal` is replaced
by a registry check. Per-adapter cost goes to zero, which is what "the SDK needs
no refactor to accept a new substrate" was always trying to say.

**Success is structural, not numeric.** Two properties, both enforced by lint in
the same machinery as the existing harness-import lint (`tools/lints/`): no
import of `ccf.graph.backends.*` from outside `backends/`, and no substrate name
in core outside the registry. These replace `D-IMPL-92`'s per-file added-line
budgets, which `D-IMPL-92` itself calls an admitted proxy and which are now
exhausted — `manifest.py` at 24 of 25 and `artifacts.py` at 9 of 10, tied, so a
seventh substrate breaches both on arrival. `D-IMPL-92`'s gate is **superseded
by the structural check, not deleted**.

**Depends on**: Phase 15.3 (the sixth backend, whose landing exhausted the
budgets), Phase 15.2 (the read and write seams the registry must not disturb)
**Blocks**: Phase 16 — do not document a backend surface this phase reshapes

**Scope**: all six existing backends migrate — sqlite, postgres, memory, neo4j,
mongo, fluree. Nothing about operator purity, as-of correctness (`INV-CH7-14`),
single-writer (`INV-CH7-10`), or cross-substrate replay determinism may weaken.
`D-11`'s line on mechanism change elsewhere under `src/ccf`, the
`docs/GRAPH_QUERY_SEMANTICS.md` freeze, and the corpus rule all stand.
`D-IMPL-92`'s prohibition on raising a budget to make a gate pass stands: under
`D-IMPL-93` the remedy for an exhausted budget is the registry, never a larger
number.

**Requirements**: none mapped. The phase is measured against the sixteen
decisions plus two corrections in `15.4-CONTEXT.md` (`D-01`..`D-16`, `C-01`,
`C-02`) and the twenty validation claims `V1`..`V20` in `15.4-RESEARCH.md`.

**Success Criteria** (what must be TRUE):

  1. No module under `src/` or `runtime/` outside `ccf.graph.backends` imports
     `ccf.graph.backends.*`, enforced by the `cinv02-backend-import` rule in
     `make lint`
  2. No substrate name appears in `src/ccf` outside the adapters' own package —
     in code or in docstring prose — enforced by the `cinv04-substrate-name` and
     `cinv04-substrate-prose` rules, whose vocabulary is read off disk rather
     than typed into the checker
  3. All six adapters migrate behind the registry; `boot()` and
     `load_and_boot()` take an adapter name and one connection mapping, with the
     `D-15B` migration note written
  4. An adapter installed from outside this repository passes the same
     conformance suites the six built-in adapters pass, and
     `git diff --stat src/ccf` over its arrival is empty
  5. Single-writer, as-of correctness, operator purity and cross-substrate
     replay determinism are unweakened: four container legs green,
     `tests/conformance/query_corpus.py` and `docs/GRAPH_QUERY_SEMANTICS.md`
     byte-untouched for the whole phase

**Plans:** 12/12 plans complete, plus a post-review fix pass (13 SUMMARYs)

Plans:

**Wave 1**

- [x] 15.4-01-PLAN.md — The two structural lint rules and the widened single-writer rule, with negative controls

**Wave 2** *(blocked on Wave 1)*

- [x] 15.4-02-PLAN.md — The registry: registration record, entry-point and in-package discovery, the three refusals
- [x] 15.4-03-PLAN.md — Split `_writer.py` into six per-backend write modules (+ WR-01)

**Wave 3** *(blocked on Wave 2)*

- [x] 15.4-04-PLAN.md — Per-adapter config models and registration records (+ WR-05)

**Wave 4** *(blocked on Wave 3)*

- [x] 15.4-05-PLAN.md — `boot()` becomes a registry lookup; 23 call sites migrate; the handle carries its adapter pin

**Wave 5** *(blocked on Wave 4)*

- [x] 15.4-06-PLAN.md — Manifest and artifacts: registry preflight, secret references, `Literal` dropped, schema regenerated, 20 call sites

**Wave 6** *(blocked on Wave 5)*

- [x] 15.4-07-PLAN.md — Turn the structural lints on; retire the D-IMPL-92 line-budget gate
- [x] 15.4-08-PLAN.md — Decision Replay dimension 2 pins the adapter
- [x] 15.4-09-PLAN.md — `ccf backends list` over `GET /backends`

**Wave 7** *(blocked on Wave 6)*

- [x] 15.4-10-PLAN.md — The out-of-tree proof adapter distribution and its install wiring

**Wave 8** *(blocked on Wave 7)*

- [x] 15.4-11-PLAN.md — Conformance params, param/registry parity, the zero-cost measurement, the authoring guide

**Wave 9** *(blocked on Wave 8)*

- [x] 15.4-12-PLAN.md — Surface record, citations, full sweep, gate package (**checkpoint**)

### Phase 15.5: The Context Product Surface — Vessel, Assembler, Debt, Entitlement

**Status**: planned 2026-08-10, commissioned mid-Phase-16. Phase 16 is parked at
6/21 and resumes against the surface this phase corrects.

**Why it exists.** Dave read `examples/s1-01-hello-context-product` and asked the
question the whole SDK has to answer: *"today I would put an MCP server in front
of the fluree database and run a query and return the results. What is the
benefit of using CCF?"* The example pinned its subject, its temporal boundary and
its `now` as literals in artifacts — one company, one frozen instant, one answer.
Chapter 1 already names that as the thing CCF replaces: *"assembled at decision
time, not precomputed against design-time queries… the difference between the two
is the difference between the verb aggregate and the verb assemble."* By the
whitepaper's own vocabulary the reference example aggregates.

**What was measured behind that reaction** (at `b771468`, field by field, not
inferred):

- Three of §6.3's eight committed elements — **freshness SLA, discovery,
  addressability** — are unimplemented, while `contract.py` states all four
  class-level elements *"live"* on `RegisteredProductClass`, where only
  `assembly_mode` of the four actually is.
- `register_product_class` accepts **no payload schema**, so `payload:
  Mapping[str, Any]` is an unchecked dict — the substantive gap under the vessel
  model, whose entire discipline is the declared schema.
- `DebtAssessment` is computed by `ccf.halflife.debt`, exercised in five shipped
  examples, and appears on **neither** `ContextProductContract` **nor**
  `DecisionReplayRecord`. Five of the six axes reach the wire; the sixth — the one
  saying how much to trust the other five — does not.
- `Perspective` is passed **into** `execute()` by the caller and nothing derives
  it from the verified grant, so Π conditioning and the policy operators both key
  off an unverified claim. `build_egress_server` binds no authorizer at all.
- The `context_assembly` archetype ships but `ArchetypeComponent` is declarative
  — `archetype_id`, `fabric_interaction_pattern`, `replay_obligations`,
  `configuration_defaults` — so it declares the emission *pattern* and carries no
  assembly behaviour. The assembler is a new surface, not a fill-in-the-blank.

**Rulings in force.** `D-IMPL-96` revokes the "no fabric changed" constraint that
concealed all of this — it was an anti-leakage rule that became a no-change rule,
policed by a `git diff --stat` that cannot tell an adapter leaking in from a
defect being fixed. `D-IMPL-97` rules the Context Product **one standardised
vessel**, not a class hierarchy: identity is `schema_name` plus a declared payload
schema, uniqueness is in **how it was assembled**, and the assembler is a Protocol
whose implementation is a **declared agent** from the `context_assembly`
archetype. Dave ruled separately that entitlement requires a fabric change.

**The design agenda, carried from `docs/CONTEXT_PRODUCT_REVISION.md` §9–§10.**
Seven open questions reach planning unresolved, and one gates the others: whether
the **request surface is a typed request contract per class** — Dave's *"company
name and top investors above 25%"* — because that is what makes a product
**callable** rather than configurable, and it collapses the fixed-subject and
fixed-instant defects into one design instead of two patches. The rest: debt's
shape on the wire and whether recency and salience are one field or two; whether
debt lands on the product, the replay record, or both; what *"a material event
transpired"* means mechanically without domain values in the core; whether payload
validation is a fourth gate or a registration-time bind; debt composition
weighting for aggregate products; and the unruled coupling — **if entitlement
bounds what an assembler may consult on a caller's behalf, completeness and
therefore debt differ per principal, so debt cannot be computed once per
product.**

**Success Criteria**

  1. Every Context Product delivered to a consumer carries its Context Debt, and no delivery path exists that drops it
  2. All **nine** elements of the §6.3 contract are present in code, each verified by an executable assertion rather than by prose, so the class of defect that hid three of them cannot recur silently (`D-IMPL-30`, Dave, 2026-07-25, resolved reading (a): the contract has nine elements including Assembly Mode, and every "eight" reference — CLAUDE.md §5's included — is editorial drift the ruling explicitly authorizes treating as such; six are present today, freshness SLA / discovery / addressability are the three absent)
  3. `register_product_class` accepts a declared payload schema and a payload violating it is refused, reusing the JSON-Schema machinery already proven on eight artifact classes
  4. Perspective is derived from the verified identity at every exposed door and a caller cannot assert a role it was not granted, while `execute()` keeps taking a Perspective so replay determinism is untouched
  5. Per-product-class entitlement gates the egress door, reusing the shape `peering/trust_policy.py` already implements per peer
  6. The assembler exists as a Protocol whose implementation is a declared agent from the `context_assembly` archetype, binding sources, tools, enlisted agents and its debt profile through axes 4 and 5 and channel 2
  7. A product answers a runtime request — subject and instant are arguments, never artifact literals — and the question asked is pinned in replay through `graph_query_sequence` and `QueryPinWriter`
  8. Aggregate products compose lineage by union and implement `D-IMPL-31`'s already-resolved mixing-refusal rule — `expires_at = min(class MAX_TTL ceiling, derivation over constituent signal validities)`, with declarable constituent-validity floors whose breach **refuses assembly** rather than emitting a product labelled fresher than its stalest load-bearing constituent (ruled by Dave 2026-07-25 and never implemented; this criterion is implementation of a standing ruling, not a new design decision)
  9. The four anti-leakage lints stay green throughout: zero harness imports in `src/`, no LLM client in an `@algorithmic` module, no prompt or threshold literal outside an artifact, no substrate name outside the backend registry
  10. `examples/s1-01-hello-context-product` demonstrates an agent asking about any company at any time and is the shape every later example copies

**Plans:** 15/15 complete. 15 plans in 7 waves (15.5-15 added at wave 3 by D-IMPL-108). Requirements `CPS-01`..`CPS-14` were minted by plan
15.5-05 at execution (commit `e18f4bf`) and are now present in `.planning/REQUIREMENTS.md`. Three plans
carry blocking checkpoints: 15.5-05 (the eight-question ruling package), 15.5-13
(Dave calls the product for two companies at two instants) and 15.5-14 (the gate).

**Wave 1** *(no dependencies — none of these needs a ruling)*

- [x] 15.5-01-PLAN.md — Ruling evidence: measure what the eight questions cost
- [x] 15.5-02-PLAN.md — The nine-element executable enumeration (the anti-recurrence artifact)
- [x] 15.5-03-PLAN.md — Product-entitlement artifact, in the `PeerTrustGrant` shape
- [x] 15.5-04-PLAN.md — Delete `DeploymentBinding` from `s1-01`

**Wave 2** *(05 blocked on 01; 06 blocked on 03)*

- [x] 15.5-05-PLAN.md — The ruling package + CPS requirement minting (**checkpoint**)
- [x] 15.5-06-PLAN.md — Authenticate, bind entitlement and resolve Perspective at all three exposed doors (MCP egress, HTTP product route, Experience front door)

**Wave 3** *(blocked on the rulings)*

- [x] 15.5-07-PLAN.md — The three absent contract elements + the declared payload schema

**Wave 4** *(blocked on Wave 3)*

- [x] 15.5-08-PLAN.md — The typed request contract (addressability realized)

**Wave 5** *(blocked on Waves 3-4)*

- [x] 15.5-09-PLAN.md — Payload validation enforcement
- [x] 15.5-10-PLAN.md — The assembler Protocol + reference implementation
- [x] 15.5-11-PLAN.md — Context Debt reaches the consumer
- [x] 15.5-12-PLAN.md — Aggregate composition: lineage union, TTL floor, `D-IMPL-31` refusal

**Wave 6** *(blocked on Wave 5)*

- [x] 15.5-13-PLAN.md — `s1-01` answers about any company at any time (**checkpoint**)

**Wave 7** *(blocked on Wave 6)*

- [x] 15.5-15-PLAN.md — Widen the product resolver seam once, carrying the typed request and the authorized Perspective (closes DI-15.5-03)
- [x] 15.5-14-PLAN.md — Phase close: full sweep, surface manifest, review, gate package (**checkpoint**)

**Blocks**: Phase 16 — the documentation rewrite resumes against this surface, not the one it found

### Phase 15.6: Decision-Completeness and Defect Closure

**Why this phase exists.** `D-GATE-15.5` approved Phase 15.5 with debt
*"informative and correctly attributed, and not yet decision-complete"*
(`D-IMPL-112`, Dave's verdict at the `15.5-13` checkpoint). Phase 16's job is
writing examples and the adoption argument — and an example demonstrating debt
an analyst cannot act on teaches the wrong lesson. Dave ruled 2026-08-11 that
15.6 runs **before** Phase 16 resumes.

**The measured reason it goes first, and it is not the defects.** The five
carried defects are API-neutral and could wait. The decision-completeness work
is where every API change lives: `Observation` is public surface and gains an
identity field; `DebtAssessment` gains evidence pointers; and because
`debt: DebtAssessment | None` is a field on `ContextProductContract`
(`src/ccf/products/contract.py::ContextProductContract`), **the product content
address moves a third time**. Phase 16 writes examples, and examples encode
expected outputs — moving the address after ten examples exist regenerates ten;
moving it now regenerates **one**. Phase 16 has already been invalidated once by
exactly this: 6 of 21 plans landed before 15.5 moved the surface, and 4 of the
remainder name the product or door surface directly.

**Two explicit tracks** (Dave, 2026-08-11). They differ in risk and must not be
planned as one.

**Track A — defect closure. API-neutral, bounded, mostly mechanical.**
- `DI-15.5-01` — the `test_run_coroutine_sync_overhead` ±11% flake.
- `DI-15.5-04` — `IntermediateCache` computes a `content_hash` key for a cache
  that is unreachable by construction; ~0.20s of a 0.41s benchmark. Making it
  lazy is behaviour-identical but narrows a `D-IMPL-36` contract.
- `DI-15.5-05` — binder refusals with no calling code path. Rule it as
  `D-IMPL-113` ruled the analogous bind case, or wire it.
- `DI-15.5-06` — `tools/dump_surface.py` records a Protocol's `__init__`, never
  its `__call__`; 56 manifest entries carry the information-free
  `(*args, **kwargs)`, 30 of them `*Protocol`, against 54 Protocol classes. This
  is an **audit** fix, not a surface change — it makes the already-shipped 3-arg
  → 5-arg resolver break visible. `D-IMPL-110` carries the measured inventory.
- `DI-15.5-08` + `D-IMPL-114` — the `path::Symbol` citation sweep. Known
  population: this phase's 3 and `DI-15.4-02`'s 45; never measured tree-wide.

**Track B — decision-completeness. API-affecting; scoped to `D-IMPL-112`'s
three named gaps, NOT to the open question.**
1. **Which observations contributed the decay.** `Observation` carries
   `(observation_type, observed_at)` and no join key, which is exactly why
   `D-IMPL-99` ruled per-subject and per-claim NOT MEASURABLE. **A build, not a
   wiring task.** Dave ruled 2026-08-11: **research spike first, then plan** —
   the `15.5-01` shape, which deleted an option from the decision space for
   free. The spike measures what an `Observation` identity costs across its 10
   files and the manifest, what it does to the content address, and whether
   evidence pointers can ride the **record** rather than the product.
2. **When the underlying source filings were last refreshed** — source-refresh
   recency as a fact distinct from computed freshness. Nothing models it today.
3. **What `forced_llm` obliges** — a declared obligation vocabulary per debt
   signal. Mechanism ships; the vocabulary is user configuration, never `src/`
   values (CLAUDE.md §11).

**Track B ships CARRYING MECHANISM, not judgement (`D-IMPL-117`, Dave,
2026-08-11).** Surface impact is **accepted** — the `Observation` identity
field, the `DebtAssessment` evidence pointers and the third content-address
move are authorized costs, not risks to design around. The judgement about what
a client needs belongs to the **context product creator**, expressed through the
product's evolutionary capability; the SDK owes the **data structure and the API
to populate and extract**, and owes none of the content. So: an `Observation`
identity and a way for debt to point at what it summarises, owing nothing about
*which* observations matter; a slot for source-refresh recency, owing no
definition of a source or a cadence; a signal-to-obligation binding that
survives replay, owing **no obligation vocabulary** (user configuration —
CLAUDE.md §11, the posture `D-IMPL-101` took on salience).

**The spike's primary question, which `D-IMPL-117` reframes.** Not *"can we
avoid the address move"* — that cost is accepted. It is: **are these three
things fixed fields on the vessel, or declared content in the shape the payload
schema already uses?** `D-IMPL-97` puts cross-cutting governance in fixed
structure and domain content in a declared schema, and debt evidence sits across
that line — the *pointer mechanism* is governance, but *what evidence is worth
carrying* is the creator judgement this phase assigns away from the SDK. Fixed
wrongly, every deployment carries a shape someone else chose; declared wrongly,
debt evidence is unvalidated free-form and replay cannot reason over it. Measure
it against the vessel model and against `D-IMPL-100`'s constraint: every added
field must be reconstructible from the record, the class, or the projection
output, or `src/ccf/replay/engine.py::ReplayEnvironment` raises.

**The standing test for this phase:** *"would someone act on this?"* rather than
*"is this correct?"* Phase 15.5 answered the second. Only the first makes the
examples honest — and under `D-IMPL-117` the SDK answers it by making the
content *carriable*, not by choosing it.

**Verification is `make ci`, not `make ci-core`.** Two 15.5 executors reported
`docs-strict` unverified and both times it was the only thing broken. `make ci`
costs ~75s more. Also sweep `docs/schemas/` and `openapi.json` for whitepaper
shingles — they sit outside the D-20 scanner, and prose republished there fires
no gate.

**Requirements**: DCD-01..DCD-12 — **minted at execution in plan `15.6-03` task 1**, not at
planning: `grep -c "DCD-" .planning/REQUIREMENTS.md` returns **0** at `ef475e1`, and no row exists
until that plan lands. All twelve IDs are claimed across the plans' `requirements:` frontmatter,
so coverage is complete in substance and **provisional until Wave 1 lands**. No requirement IDs
were mapped to this phase at insertion, so coverage is driven by the roadmap's named work items
and every one maps to exactly one DCD ID.

**Three figures in this entry are stale and the plans use re-measured ones** (`15.6-RESEARCH.md`,
measured at `29e1568`):

  - `DI-15.5-06`'s manifest inventory is **60 / 34 / 56**, not `D-IMPL-110`'s 56 / 30 / 54, and
    **five** of the information-free entries are `Literal` type aliases rather than Protocols —
    teaching `dump_surface.py` to read `__call__` will not fix those.
  - `DI-15.5-08`'s citation population is **717 total / 245 checked / 0 findings / 434
    unanchored**, of which the actionable `.py`-target subset is **125 across 31 files** — not
    3 + 45. **The gate is GREEN**; this is elective hardening, not a broken invariant. And
    `cite03-node-id` already exists, so `D-IMPL-114`'s consequence (1) is already discharged.
  - `openapi.json` is **not** fully outside the D-20 scanner — it is snippet-included at
    `public/reference/http-api.md` and lands in the scanned `site/` tree. **`docs/schemas/`
    (26 files) is the standing gap**, and it is the one that matters, because
    `tools/dump_schemas.py` copies docstrings verbatim into schema `description` fields.

**Plans**: 12 plans in 10 waves

Plans:
**Wave 1** *(parallel — disjoint file sets)*

- [x] 15.6-01-PLAN.md — [Track B] The spike: four placements measured against the real rehydration tripwire, the record-only option's three-door reach, the entitlement question, the re-derived address census. Recommends nothing. Retiring owner: `15.6-12` task 1
- [x] 15.6-02-PLAN.md — [Track A] `DI-15.5-01` loosen-only perf band override + `DI-15.5-04` lazy `IntermediateCache` key + the `D-IMPL-36` witness-narrowing fragment
- [x] 15.6-03-PLAN.md — [Verify] `DCD-01..12` minted · `tests/invariants/test_no_obligation_vocabulary.py` (the hole no shipped lint reaches) · the `docs/schemas/` scan root wired into `docs-strict`

**Wave 2** *(blocked on 15.6-01 — checkpoint)*

- [x] 15.6-04-PLAN.md — [Track B] Ruling gate: the fixed-versus-declared fork, **the unruled entitlement-leak question**, and required-versus-optional on `Observation`. New `D-IMPL` entries

**Wave 3** *(blocked on Wave 2 — Track B serializes; each plan moves a hashed contract)*

- [x] 15.6-05-PLAN.md — [Track B] Gap 1a: `Observation` gains its identity; the s1-01 assembler stops discarding the join key it already holds

**Wave 4**

- [x] 15.6-06-PLAN.md — [Track B] Gap 1b: `DebtAssessment` gains the evidence carrier; the replay quartet; address move 1 of 3

**Wave 5**

- [x] 15.6-07-PLAN.md — [Track B] Gap 2: the source-refresh recency slot (`LineageEntry` is blocked — `D-IMPL-58` plus a `sha256` file pin); address move 2 of 3

**Wave 6**

- [x] 15.6-08-PLAN.md — [Track B] Gap 3: `DebtProfile` binds an opaque obligation per `DebtSignal`, resolved at replay to the binding in force; address move 3 of 3. The vocabulary ships in an example artifact, never in `src/`

**Wave 7** *(checkpoint)*

- [x] 15.6-09-PLAN.md — [Track A] `DI-15.5-05` ruled + the seam obligation discharged and asserted + the two Track A scoping rulings Waves 8 and 9 need

**Wave 8** — ordered: `15.6-13` then `15.6-10`. Not concurrent.

- [x] 15.6-13-PLAN.md — [Track B] `D-IMPL-124` Shape B: the source-refresh map becomes a non-identifying freshness window (`oldest_source_refresh_at` / `newest_source_refresh_at`); `SourceRefresh` deleted; address move 4. **Must precede 15.6-10's manifest regeneration**
- [x] 15.6-10-PLAN.md — [Track A] `DI-15.5-06`: `dump_surface` reads a Protocol's `__call__`; **the phase's single manifest regeneration**, after the last Track B `src/` edit

**Wave 9**

- [x] 15.6-11-PLAN.md — [Track A] `DI-15.5-08`: the scoped citation sweep + a two-direction ratchet (the tree's first ceiling; its floor named `MINIMUM_*` so the retirement sweep can see it)

**Wave 10** *(checkpoint)*

- [x] 15.6-12-PLAN.md — [Close] Retire the spike, `make ci`, cross-AI panel `--all` against shipped code, single-agent review, verify every finding, gate package, present to Dave

**Sequencing constraints that are rulings, not optimizations:** Track A and Track B
are planned separately (`D-IMPL-116`); Wave 3–6 serialize because 15.6-06 and
15.6-07 both edit `DebtAssessment`, all three move the product content address, and
each needs its own fragment and its own `expected_output.txt` regeneration;
`DI-15.5-06` and `DI-15.5-08` go **last**, in that order, because both are
instruments Track B's own `src/` edits perturb — `DI-15.5-06` and Track B both
produce `docs/surface-changes/` fragments and both regenerate the surface manifest,
so a `DI-15.5-06` landing first would leave every Track B fragment authored against
a manifest it was about to move again.


### Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument

> **RETIRED 2026-08-17 — `D-IMPL-152`. This section is history, not a plan.**
> Phase 16 is not paused, parked or resumable. Earlier text in this repository
> saying *"resume Phase 16 at 7/21"* is superseded. The 14 unexecuted plans live
> in `abandoned/` and must not be executed from there. See `RETIRED.md` in the
> phase directory for what is retired (the approach) and what is not (the
> obligations several of those plans carried).


**Status**: discussed 2026-08-09. The scope was expanded at that discussion on
Dave's authority and this entry was rewritten to match (2026-08-09) — the
pre-discussion goal below is absorbed in full, nothing dropped. The authoritative
record is
`.planning/phases/16-documentation-rewrite-the-deterministic-path-the-adoption-ar/16-CONTEXT.md`
(decisions `D-01`..`D-12`); every line here is carried from it or from material
already recorded elsewhere in this roadmap. Requirement IDs (DOCS-07..NN) remain
`/gsd:plan-phase 16`'s to mint.

**STOPPED 2026-08-15 — example surface rejected by Dave; superseded by Phase
17.** The first example reached 722 lines of Python with the consumer importing
the producer's configuration (`.planning/HANDOFF-2026-08-15.md`). The remaining
14 documentation plans (16-07…16-20) documented that surface and stay stopped.
What survives: the SDK itself (3305 tests), the single-file `ccf_config.yaml`
authoring form (`D-IMPL-136` + amendment), the property-based gates
(`D-IMPL-137`/`-138`), and `backends.yaml` separation. The example-shape rulings
are suspended per `docs/superpowers/specs/2026-08-15-ccf-client-design.md` §11.

**Goal**: rebuild the adopter-facing **examples suite** and **published
documentation** against the post-Phase-15 surface, organized as four sections of
increasing depth. Phase 16 ships **Sections 1–3**, all against mechanism the SDK
demonstrably ships today; **Section 4 is Phase 17's**, arriving with the fabric
that enables it (`D-01`).

  - **Section 1 — "Hello CCF."** Deterministic assembly only, agent-free. A
    beginner's path through Context Products, Context Operators, and the six axes
    of `G(E, R, T, P, Π, L)`.
  - **Section 2 — External agents over MCP.** Client agents reach CCF with zero
    CCF dependency. Claude Agent SDK, Google ADK, and LangGraph legs.
  - **Section 3 — Advanced CCF.** Embedding CCF in your own application, and
    developing agentic skills within CCF against a real use case.
  - **Section 4 — LLM packaging and agent swarms.** *Phase 17.* Assembly Mode 2
    (`llm_packaged`) and Mode 3 (`swarm_assembled`).

The examples are **greenfield** — `examples/00`–`08` retire and the suite is
rebuilt against the Phase 15.4 registry seam as one parameterized runner proven
across all six backends. **KYC / UBO resolution and refresh** on the FIBO dataset
is the use-case spine, and the adoption argument gets its own page naming the
alternatives. The pre-discussion goal it replaces, carried verbatim from the
milestone entry above: *"one document, two sections (deterministic + external MCP
consumption; CCF-agent assembly + MCP/A2A consumption), banking scenarios from
the whitepaper, re-cut snippet markers so a reader can see which code is CCF and
which is theirs."*

**What it inherits, already on the record:**

- **Phase 14.1 whole** — superseded 2026-08-03 before any plan was written; every
  success criterion in that entry is absorbed here, plus the structure Dave
  specified in that discussion.
- **Phase 14's G-01 framing defect**, deferred deliberately: the shipped docs
  describe an integration surface Phase 15 replaced, so the fix lands here against
  the new surface rather than twice against the old one.
- **A hard constraint from Phase 15.1, recorded URGENT**: Phase 16 must not
  document a self-satisfying gate. Gate 2 (INV-CH7-47) is **assembly-path
  integrity** — the claim transcribed into the Contract equalling the engine's
  execution of the plan — not a comparison of two independently authored sets.
- **Eleven open residuals** carried at D-GATE-15.1 (re-approved 2026-08-06).
  `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md` is the
  authoritative inheritance list — **not** `docs/SURFACE-AUDIT.md` §6.4, which
  predates the last four remediation rounds.
- **Two process findings** from the 15.1 close: the code-review gate runs *after*
  the phase gate (which cost that phase a withdrawn approval), and `make ci` does
  not reach `tools/` though CI does — three suites there fail pre-existing.

**Requirements**: mints its own DOCS-07..NN at planning; not counted in Coverage
below. DEMO-01..03 and EXAM-01..05 re-home onto the new suite rather than being
retired (`D-08`).
**Plans:** 4/21 plans executed (16-02 at 2/3, paused at its DGX checkpoint)

Plans:
**Wave 1**

- [x] 16-01-PLAN.md — ruling package (`D-IMPL-94`), DOCS-07..18 minted, ERGO-03 measurement frozen

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 16-02-PLAN.md — FIBO source-estate extension: corp→corp ownership edges with per-edge percentages *(2/3 — Task 3 loads the four DGX stores and needs operator credentials; `roadmap.update-plan-progress` marked this `[x]` because it counts SUMMARY files, and 16-02's SUMMARY is `status: paused-at-checkpoint`)*
- [x] 16-03-PLAN.md — Section-2 client-leg transport spike: LangGraph + Claude Agent SDK
- [x] 16-04-PLAN.md — gate-checker unblock, three standing docs tripwires
- [x] 16-21-PLAN.md — repo-wide retirement-coupling sweep, its inventory and its gate (split from 16-04)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 16-05-PLAN.md — Section-1 example 1: spine/deployment split, KYC/UBO deterministic assembly
- [ ] 16-06-PLAN.md — advisory pages A-1/A-2/A-3/A-8 + discharge gate

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 16-07-PLAN.md — one driver, backend from a configuration artifact + six-backend equality matrix
- [ ] 16-08-PLAN.md — Section-1 example 2: freshness (λ_c) and Context Debt (D_c)
- [ ] 16-09-PLAN.md — Section-2 example: MCP fabric + four zero-CCF client legs
- [ ] 16-10-PLAN.md — Section-3 example A: embed CCF in a host application
- [ ] 16-11-PLAN.md — Section-3 example B: agentic skills, workflow, HITL, replay

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 16-12-PLAN.md — Makefile + CI wiring + DGX opt-in job + credential gate
- [ ] 16-20-PLAN.md — Section-2 zero-import AST guard, three-harness assertion, README (split from 16-09)

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 16-13-PLAN.md — Section-1 published pages, six-axes concept, G-01 pillar rewrite

**Wave 7** *(blocked on Wave 6 completion)*

- [ ] 16-14-PLAN.md — the adoption-argument page + its standing gate

**Wave 8** *(blocked on Wave 7 completion)*

- [ ] 16-15-PLAN.md — Section-2 published pages; retire `examples/03-harness-portability`

**Wave 9** *(blocked on Wave 8 completion)*

- [ ] 16-16-PLAN.md — Section-3 skills pages + eight reference/how-to re-cuts

**Wave 10** *(blocked on Wave 9 completion)*

- [ ] 16-17-PLAN.md — Section-3 embed pages; retire `examples/04-cross-process`, `07-artifact-store-mcp`

**Wave 11** *(blocked on Wave 10 completion)*

- [ ] 16-18-PLAN.md — terminal retirement: adopters guide, seven examples, final nav

**Wave 12** *(blocked on Wave 11 completion)*

- [ ] 16-19-PLAN.md — phase close: `make gate-16`, gate package, §3.1 review protocol

**Cross-cutting constraints:**

- The example's spine contributes one gate call site, one projecting body and one resolved binder site, so the three headroom-free tests/products/ floors survive waves 8 and 10 until plan 16-18 re-floors at wave 11
- Every out-of-swept-tree coupling this plan owns is named in files_modified before the sweep runs, so the sweep confirms rather than discovers

**Success Criteria** (what must be TRUE):

  1. Sections 1–3 are published in `public/` and each runs end-to-end by a single documented command, with Section 4 absent and named as Phase 17's (`D-01`)
  2. Section 1 invokes no agent — deterministic assembly only — so UAT gap G-01's agent-first framing is closed by construction rather than by editing the condemned pages (`D-12`)
  3. Every Section 2 client leg imports nothing from `ccf`, with the zero-CCF-dependency claim visible in the client's own import list and asserted in CI, across all three harnesses: Claude Agent SDK, Google ADK, LangGraph (`D-09`, `D-IMPL-24`)
  4. One parameterized example runner, with a CI matrix asserting equivalent Context Products across `sqlite`, `memory`, `postgres`, `neo4j`, `mongo` and `fluree`; `sqlite` + `memory` run in always-on CI which stays deterministic and network-free, the four DGX databases are an opt-in live-legs job, and no credential enters the tree (`D-06`)
  5. `examples/00`–`08` are retired and every published page that sources snippets from them is re-cut in the same phase — there is no partial state (`D-07`)
  6. Each example physically separates the **CCF call spine** from **deployment code** into distinct, separately-markered regions, legible to someone reading the repository and not only the rendered site, using Phase 14's `D-07` marker vocabulary (`D-11`)
  7. An adoption-argument page names what teams build instead — RAG over a vector store, hand-rolled context assembly, a semantic layer plus prompt templates — and states what each lacks: no replay, no policy binding at assembly, no lineage to a passage, no staleness measure; its worked demonstration is the UBO question, "Who ultimately owns Acme?" (`D-10`)
  8. Gate 2 (INV-CH7-47) is documented as **assembly-path integrity** and nowhere as a comparison of two independently authored sets, and the `tests/examples/test_*_output.py` checks that compare `required_operator_keys` against `operators_invoked` are not promoted as independence proofs (`D-IMPL-86`, SURFACE-AUDIT §5.3 A-4)
  9. The carried advisories this phase owns are discharged in the published tree: A-1 (`from ccf.deployment import …` as the single preferred day-1 import), A-2 (a maintainer page for the surface toolchain), A-3 (the pre-15 surface described in the shipped docs), A-8 (`role: load` artifacts reachable on `BootedFabric.artifacts` and absent from the replay pin set)
  10. Nothing leaks into the core: zero harness imports in `src/`, no LLM client in any `@algorithmic` module, no prompt/agent/task/threshold literal outside an artifact, and no substrate name outside the backend registry — all four CI-enforced — while changes to the fabric itself are permitted and expected where this phase finds a defect (`D-IMPL-96`, Dave, 2026-08-10, revoking the former "no fabric changed" wording and with it `D-13`'s docstring carve-out, `D-14`'s two-limb bound, and plan 16-19's `gate_16.py` allowlist; Mode 2 packaging still attaches **above** `serve()` per `D-IMPL-94`, and there is still no Mode 2 packaging stage, no Mode 3 coordinator, no `src/ccf/unstructured/`, and no tier-3 external sources)

### Phase 17: Client Access — `ccf.client` and the Transport-Agnostic First Example

**Status**: opened 2026-08-15. Brainstormed and converged with Dave the same
day; the design is approved in full. **The authoritative input is
`docs/superpowers/specs/2026-08-15-ccf-client-design.md`** — every commitment
there is design-ruled; this entry is orientation, not a second specification.
Branch: `phase-17` (cut from the `phase-16` tip so the SDK-keep work —
single-file config loader, property gates — travels with it).

**Goal**: CCF owns the client abstraction and the result contract; transports
are official adapters that all return the same `Result` shape; the producer
side stays completely invisible to the client. Ship, in order:

1. **`ccf.client`** — `ProductClient.for_product()` + `ask()`; a four-name
   public surface (`ProductClient`, `Result`/`Refusal`, `TransportError`,
   `BindingError`); refusal is a value, negligence is an exception, wire
   failure is an exception; fail-closed guards on post-assembly fields;
   `CCF_BINDING` scheme-prefixed resolution, deliberately minimal.
2. **In-process adapter** — a true degenerate wire: lazy boot behind the seam,
   round-tripped through the same canonical codec every wire adapter uses
   (`Result` constructed in exactly one place).
3. **Adapter conformance suite** — the CI parity gate: identical `Result`
   fields and content address across adapters, identical refusals, guard
   behavior, wire-failure separation. An adapter is official when it passes.
4. **First example** — `consume.py` (≤ 80 lines, imports `ccf.client` + stdlib
   only, both CI-gated) beside an opaque `deployment/` dir; one command to run.
5. **MCP adapter** — second, against the frozen contract, ships when it passes
   the conformance suite. HTTP / A2A later, as adapters only.

**Scope discipline** (Dave, at section-3 approval): this phase is the **client
role only**. Examples for *constructing* context products are a separate,
later body of work with a different audience.

**Inheritances and consequences:**

- The Phase 16 example-shape rulings are suspended (spec §11); the
  producer/consumer separation of `D-IMPL-127` is strengthened — enforced now
  by the purity gate and the codec seam rather than file layout. SDK rulings
  `D-IMPL-132`/`-136`/`-137`/`-138` stand.
- `tests/examples/test_spine_separation.py` enforces the suspended shape and
  must be re-scoped or retired before it refuses the new examples.
- Condemned example trees (`s1-00`, `s1-01`, `00`–`08`) are removed or
  quarantined early in this phase (spec §12.2).
- The "Section 4 — LLM packaging and agent swarms" work that Phase 16's entry
  reserved under the *name* "Phase 17" is **not this phase**; it re-homes to a
  later phase number when its enabling fabric arrives.
- Open in the neighborhood, not gating: `D-IMPL-129` (`invoke_agent`
  entitlement), 16-26 (client parameters on both doors, `D-IMPL-133`).

**Requirements**: `CLNT-01`..`CLNT-19`, minted at planning 2026-08-15 and written
into `.planning/REQUIREMENTS.md` with the traceability rows. The lane was verified
free before minting.
**Plans**: 10 plans in 8 waves.

Plans:
**Wave 1**

- [ ] 17-01-PLAN.md — Retirement sweep repaired and the `tools/` gate reachable (`D-31`)
- [ ] 17-02-PLAN.md — The canonical refusal envelope in `src/`, before any door emits it (`D-28`)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 17-03-PLAN.md — The resolver seam: Protocol and reference implementation, both in `src/` (`D-29`)
- [ ] 17-04-PLAN.md — The wire: `WireRequest`, `WireOutcome`, one codec (`D-11`, `D-20`)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 17-05-PLAN.md — The client surface: four names, the guard, three-step binding (`D-03`..`D-12`)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 17-06-PLAN.md — The in-process adapter: lazy cached boot through the resolver (`D-13`, `D-16`, `D-30`)

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 17-07-PLAN.md — The conformance suite and its sabotage controls (`D-15`, `D-22`, `D-23`)

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 17-08-PLAN.md — Condemned-tree disposition and the example gates re-scoped (`D-25`..`D-27`) — **checkpoint, not autonomous**

**Wave 7** *(blocked on Wave 6 completion)*

- [ ] 17-09-PLAN.md — The first example: `consume.py`, opaque `deployment/`, purity + budget gates (`D-17`..`D-19`, `D-32`) — **human-verify, not autonomous**

**Wave 8** *(blocked on Wave 7 completion)*

- [→] 17-10-PLAN.md — **DEFERRED out of Phase 17 by `D-IMPL-146`, then LIFTED INTO PHASE 18 by
  `D-IMPL-147`** (Dave, 2026-08-17) as that phase's first plan. The file now lives at
  `.planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/17-10-PLAN.md`
  and **keeps its `17-10` ID on purpose** — three shipped test docstrings and two immutable
  decision entries cite it as a stable identifier per `D-IMPL-144`. Not executed in Phase 17.

**Also deferred, and NOT yet lifted:** `17-08` (condemned-tree disposition) remains in this
phase's directory under its `D-IMPL-146` banner. It is **blocked on real work, not sequencing**:
deleting the `s1` trees would leave `refuse_request` with no surviving demonstration anywhere in
`examples/`, and `tools/docs_tests/test_resolver_seam_obligations.py::test_both_seams_cite_both_call_sites`
requires two *distinct* cited examples per seam with the cite-it-twice escape closed by design.
The remedy is to write a producer-side example, not to relax the gate.

**Cross-cutting constraints:**

- `D-31` precedes any example-tree removal; `D-28` precedes any door work; `D-29` precedes the
  adapter; the conformance suite precedes the MCP adapter being called done
- Exactly one `Result` construction site across all ten plans (`D-12`); no plan introduces a
  `src → runtime` import (`D-29`)
- Every gate this phase adds carries a sabotage control that passes a divergent subject into the
  real assertion function — the single exception (a make-target composition) is named as such in 17-01

**Two rulings wait for Dave mid-execution:** `D-IMPL-140` (a `binding.yaml` document — proposed,
isolated behind a loader in 17-06 Task 1 so a different ruling rewrites one task), and 17-08's
checkpoint on `examples/00`–`08`, cited 111 times across 15 published pages.

### Phase 18: MCP Transport — The Second Door and the Portability Proof (INSERTED)

**Status**: opened 2026-08-17 by `D-IMPL-147` (Dave), immediately after `D-GATE-17` merged
Phase 17 to `main` at `b32348f`. Branch: `phase-18`, cut from `main` — not from `phase-17`,
because Phase 17's work is already merged and there is nothing in-flight to carry.

**The authoritative input is unchanged**: `docs/superpowers/specs/2026-08-15-ccf-client-design.md`
plus its Amendment 1. This phase adds no new design; it executes the transport half of a design
that was already ruled. In particular §6 (*"an adapter is official when it passes"*), §9 (the
sync-only ruling and its named revisit trigger, which is this adapter) and Amendment 1 §A (the
`D-28` rollout: *"the MCP door is fixed to produce it in this phase"*) are the governing text.

**Goal**: make the portability claim *mechanized* rather than asserted. Phase 17 shipped one
transport and a decode path that every transport must return through; a single adapter cannot
falsify a claim about adapters, so the conformance suite's cross-adapter comparisons currently
degenerate to self-comparisons. A second real adapter is what makes them comparisons.

**Why this phase and not something else** — the candidates were weighed with Dave on 2026-08-17
and recorded so the ordering is not re-derived: `17-08` (deleting the condemned `s1` trees) is
blocked on writing a producer example first; Phase 16's 14 remaining documentation plans describe
a surface that no longer exists; and the carried advisory findings are hardening rather than
surface. The second transport was chosen because the conformance suite was **already written to
take a second subject** and says so in its own docstring — *"Plan 17-10 adds a second module
exactly like this one and changes nothing in suite.py."*

**Plans**

**Wave 1**

- [x] 17-10-PLAN.md — The MCP door carries parameters and refusals; the MCP adapter passes the
  suite (`D-15`, `D-28`, `D-IMPL-133`). **Lifted from Phase 17 by `D-IMPL-147` and keeping its
  `17-10` ID deliberately** — see that entry and the banner in the plan file. Four tasks:
  the egress tool's parameter surface; the refusal envelope at the door; the `mcp+stdio` adapter;
  the conformance binding. Requirements `CLNT-12`, `CLNT-15`.

**Premises re-measured on `main` @ `b32348f` before the lift, so the phase starts on facts:**

- `mcp==1.28.1` is **already a declared, pinned dependency** and installed. `T-17-SC`'s blocking
  human checkpoint for an `[ASSUMED]` package therefore does **not** fire; no install is needed.
- All seven artifacts the plan reads or extends exist: the conformance suite (759 L), the
  in-process adapter (445 L), `~ccf.client.binding`, `~ccf.client.codec`,
  `~ccf.products.refusal`, and `~ccf_runtime.mcp.egress` (599 L).
- **Task 3's harness-lint boundary question is answered NEGATIVE.** `src/` already imports `mcp`
  in four modules (`~ccf.mcp.client`, `~ccf.artifacts.mcp_store`, `~ccf.signal.mcp_source`,
  `~ccf.signal.mcp_envelope_map`) and `tools/lints/harness_imports.py` denies a frozenset of
  *harness* packages that does not contain MCP — MCP is CCF's own integration surface
  (`CLAUDE.md` §7.1), not a harness. The lint is green today with those imports in place, so the
  adapter's import is permitted and no `D-IMPL` ruling is owed.
- `17-09`, the plan's former `depends_on`, is merged; the dependency is discharged and cleared.

**Cross-cutting constraints, inherited and still binding:**

- Exactly **one** `Result` construction site (`D-12`) — the adapter builds none, and `17-05`'s
  single-construction-site scan is the enforcement, so a `Result` built here fails a test rather
  than merely violating a convention.
- **Sync-only at the client surface** (`D-24`). No async `ask()`, and `~ccf.client.__all__` stays
  at exactly the four ruled names. If the internal bridge is genuinely unworkable — *measured,
  not felt* — that is a stop-and-report for Dave, and it is precisely the revisit trigger §9
  anticipated.
- A transport failure **never** becomes a refusal (`D-07`/`D-10`); it raises `TransportError`, and
  `17-07`'s control 5 is watching for a swallowing adapter.
- No `src → runtime` import (`D-29`).
- Every gate carries a sabotage control that **passes a divergent subject into the real assertion
  function**. For this phase the subject is a *callable*, not a source root — a control that
  copies a module to `tmp_path` and breaks it cannot fire, because the copy is never what the
  shipped assertion reads. That defect class spans `17-05`, `17-06` and this plan, and the rule
  is stated once in the plan's `<context>` rather than per-task.

**Two things this phase must be willing to falsify rather than satisfy:**

1. **`suite.py` must not change.** If binding a real second adapter requires editing the suite,
   the suite was not adapter-agnostic and that is a **finding to report against `17-07`**, not an
   edit to make quietly. `git diff tests/client/conformance/suite.py` being empty is the claim.
2. **The `16-26` absorption is a measurement, not a preference.** The egress tool's
   `parameters={}` has a *recorded reason* — a flat tool-argument map cannot carry `D-IMPL-103`'s
   declared nested types without guessing coercions, and a declared-parameter surface would make
   the tool wider than the HTTP door. That reason is a **constraint on the fix, not an obstacle
   to it**: amend the docstring paragraph, never delete it, so the constraint survives as a
   constraint after the limitation it caused is lifted.

**Carried into this phase from `D-GATE-17`, unfixed and non-blocking:** the per-module budget
gate, the client exception taxonomy leaking past `TransportError`, `_parse` swallowing
`SyntaxError` under a `# pragma: no cover`, the documentation-only credential posture on
`connection:`, the purity gate admitting any `ccf.client.*` submodule, the `projection.py`
docstring overclaim, the `required[0]` positional assumption, `load_reference` mutating
`sys.path`, and `question.asked_at` optional and read by nothing. **A process disposition also
carried:** *a plan should not ship an artifact and the gate that judges it* — `17-09` did both.

### Phase 18.1: Simplify the MCP Example — Client-Side Access, Server Off-Stage (INSERTED)

**Goal:** make the MCP example demonstrate **client access to the same Context Product,
reached a different way** — and stop the client's command from naming the server program.
This is a client-experience phase. It ships **no new transport, no new adapter, no
`mcp+http` and no change to the client seam** — and **exactly one piece of new
mechanism**, ruled rather than accreted. `D-18` (Dave, 2026-08-18) makes
`load_binding_document` refuse **by name** a `server:` value that resolves back
*inside* the deployment root: roughly four lines and one test. It is deliberate. `D-10`
puts that key's containment base at the deployment root's **parent**, which is right for
the ordinary case and admits an inward-reaching value on the way, and without the
refusal the only thing holding the line was one assertion in `test_hw1_two_transports`
— which covers the shipped example and no adopter. It makes `D-09`'s argument (a server
program is not deployment content) mechanical rather than documentary. Recorded in
`docs/surface-changes/18.1-04-the-deployment-declares-its-server.md` and ruled in
`D-IMPL-153`.

**Why this phase exists.** Dave, 2026-08-18, reading the example: *"the complexity was too
overwhelming. Also it was not clear what the client had to implement. The client is not
responsible for setting up the MCP server, yet when the MCP example is called the client
code references the server.py … Today you have both conflated and yet again it's too
confusing for a beginner."*

**The measured cause.** The documented command is
`CCF_BINDING="mcp+stdio:examples/…/server/serve.py examples/…/deployment" python consume.py`
— the client's own binding string **names the server program**, and `consume.py` **spawns
it** as a child process (`src/ccf/client/adapters/mcp_stdio.py::_call`). MCP stdio has no
listening endpoint, so the spawn itself is inherent to the transport and is **not the
defect**. The defect is that the spawn is *the client's business* in the reader's field of
view.

**Scope — three changes, none of them new mechanism, plus the one refusal `D-18` rules
in (see the goal above, and `D-IMPL-153`):**

1. **`CCF_BINDING` names a deployment, not a script.**
   `mcp+stdio:examples/hw1-companies-over-revenue/deployment` — and the deployment declares
   its own server command in `binding.yaml`, as **data**, beside the wiring already there.
   The server is still spawned, because stdio always spawns; what changes is that *how this
   deployment is reached* becomes the deployment's business, exactly as the projection and
   the graph already are. The reader's command never mentions `serve.py`.
2. **`server/serve.py` is cut to a readable length.** Of its 292 lines, ~180 are
   deployment-value composition — boot the fabric, 21 named arguments to
   `build_governed_resolver`, entitlement-policy registration, per-boot token minting — and
   only ~35 are the MCP server. **Constraint:** `D-IMPL-141` Amendment A.3 grants
   `deployment/` exactly one Python module (the projection) and
   `tests/client/test_data_only_deployment.py` refuses a second by name, so composition
   moves into a second `server/` module — never into `deployment/`.
3. **The README states the frame, in Dave's own terms (2026-08-18).** It must say plainly:
   - this example reaches **the same Context Product** as the first one, **a different way**
     — the product is the constant, the access path is the variable;
   - **why a server appears at all**: to demonstrate client access over MCP, something must
     produce the product. The first example needed no server because the client ran
     **in-process with the SDK** and produced the product directly;
   - **that how the MCP server was assembled is deliberately out of scope here**, and is
     covered in a later set of examples on the **assembly of Context Products**.

   A server appearing in a client-side example is not a scope violation — *explaining* it
   is. Keep it off-stage, and say so.

**Explicitly out of scope.** No new transport, no new adapter, no `mcp+http`, no change to
the client seam. An earlier draft of this phase proposed shipping a third adapter so the
server could be started independently; that was **withdrawn on 2026-08-18** as SDK work
wearing an example's clothes — it would have landed producer-side mechanism inside a
deliberately client-side phase, and Phase 19 would have rewritten it immediately. The
`A5` advisory (stdio auth is impersonation, because FastMCP's bearer middleware is
HTTP-only) is **not** addressed here and stays carried forward from Phase 18.

**Relationship to the arc.** The examples progress **client-side first, producer-side
later**: this phase is the client-access half, and how a Context Product is *built* is the
subject of the later assembly examples. `consume.py` stays what it is — the reader's whole
example, importing only stdlib, `ccf.client` and an adapter, under the `CLNT-14` purity and
budget gates.

**Requirements:** **None new — confirmed at research.** The phase re-verifies four already
minted requirements rather than minting a fifth: `CLNT-13` (the documented command and its
`make` recipe are one string), `CLNT-14` (the AST purity and declared-budget gates stay green
and non-vacuous), `CLNT-15` (the MCP adapter still ships on passing the conformance suite),
and `CLNT-21` (`binding.yaml` stays data plus exactly one reference, now with `server:`
present). `CLNT-12`'s standard is inherited: every new check carries a named sabotage control
in the same plan.
**Depends on:** Phase 18 (`D-GATE-18`). **Independent of Phase 19** — no seam change, so
either order works.
**Plans:** 5 plans

**Wave structure — strictly linear, one plan per wave (1→2→3→4→5).** Each wave is blocked on
the one before it. `18.1-03` and `18.1-04` share no `files_modified` and could in principle run
together, but the `C-1` human review reads `serve.py`'s trimmed docstring (`D-13`) and the
README's shrunk `server/` paragraph (`D-16`) as one split argument, so splitting them across a
wave boundary would hand the reviewer half the subject.

**Cross-cutting constraints:** none — no `must_haves.truths` entry is shared by two or more
plans, which is a consequence of the linear structure: each wave owns a distinct claim.

**Two constraints that hold across every wave, and are not truths of any single plan:**
`.venv/bin/python` always (bare `python` does not exist on this host, and a plan that writes it
reports a false red); and no `state.*` or `roadmap.*` SDK writer is ever run — `.planning/`
files are hand-edited.

Plans:
- [x] 18.1-01-PLAN.md — Clear the pre-existing red gate (D-19, first sweep); `server:` as a
      data key, contained against the deployment root's parent, refused by name when it reaches
      inward (D-01, D-10, D-18); both real deployments declare a server
- [x] 18.1-02-PLAN.md — The address grammar flips to one token, in one commit across every
      site that spelled two (D-05); four named refusals driven end to end from `CCF_BINDING`
      (D-06, D-07, D-08)
- [x] 18.1-03-PLAN.md — `server/serve.py` is cut: the door stays, composition moves to
      `server/compose.py`; the docstring is trimmed to what only the server can say (D-11,
      D-12, D-13)
- [x] 18.1-04-PLAN.md — The README states the frame (D-14, D-15, D-16, D-17); the surface
      change is recorded and the no-new-surface claim is narrowed where D-18 exceeds it; the
      C-1 no-generalizing constraint is checked by a human
- [x] 18.1-05-PLAN.md — The phase-close re-sweep, run after the last SUMMARY (D-19, second
      sweep), so the phase closes with no carried red

### Phase 19: The Client-Seam Integrity Checks Must Be Able to Fail (INSERTED)

**Goal:** make the two client-seam integrity checks *capable of failing* when a transport
answers the wrong question or alters a vessel in transit. They cannot today, on either
shipped adapter.

**Why this phase exists.** `D-GATE-18` approved Phase 18's portability claim and explicitly
did **not** approve a tamper-detection claim. `B0` — the finding behind that reservation —
was deferred here by `D-IMPL-151` as an **open blocking defect**, not accepted risk.

**The defect, measured.** `src/ccf/client/codec.py` argues, correctly and at length, that the
request echo is *cross-checked, never reconstructed*, because reconstruction *"cannot detect a
transport that answered a different question … a proxying or multiplexing transport that
crosses two in-flight questions produces a perfectly well-formed outcome for the wrong
request."* **Both shipped adapters reconstruct.** `DoorOutcome` carries no request identity, so
`mcp_stdio._decode` sets `request` from its own argument and the seam call in
`src/ccf/client/client.py::ProductClient` passes that *same object* as `sent` — making
`check_outcome`'s `if outcome.request != sent` a comparison of an object with itself.
`verify_content_address` is inert for the same reason: the "claimed" address is computed by
the adapter from the identical bytes the codec then re-hashes, so the check is
`sha256(x) != sha256(x)`. Both are inert **on the one transport where a crossed-question
wire is physically possible**.

*(Citation corrected 2026-08-20 by plan `19-08`. This paragraph cited `client.py:172`,
which was **already stale when this section was written** — `19-RESEARCH.md` §9.3 measured
the true line as `:186` at the phase's base commit, and `19-02` moved it again; the seam
call is at line 228 as measured today. The pointer is now the **symbol**, per `D-IMPL-114`,
because a line anchor is wrong the moment code moves and this one was wrong on arrival.
Two honest notes: the whole paragraph is a description of the defect **as it was**, and
that defect is closed — `mcp_stdio._decode` no longer exists, the seam returns bytes, and
neither operand is client-sourced any more (`D-IMPL-156`, `D-IMPL-157`); and `client.py` is
an **ambiguous basename**, so the citation lint DROPPED the old pointer rather than checking
it, which is why a stale number survived three phases with every gate green.)*

**Scope, at least:**
- The wire form carries **request identity**, so the echo is read off the wire rather than
  reconstructed from client state — a wire-shape change touching `DoorOutcome`, both doors,
  the adapter and the codec.
- The content address is **claimed by the producer** and recomputed by the consumer, so the
  claim is checkable — which is what `verify_content_address`'s docstring already promises.
- **The seam's enforceability is in scope, not just the payload.** `decode_outcome` and
  `encode_outcome` have **no call site outside tests**: both adapters build `WireOutcome`
  directly, which `D-11` permits — and that permission is exactly what admits the
  reconstruction. A fix that leaves the seam bypassable re-opens the defect for the next
  adapter.
- A control that answers a *different question* must be caught by a **single-transport
  client**, not only by the cross-adapter parity diff. Parity is blind by construction to a
  check broken identically on both subjects, which is why this survived Phase 18's suite.

**Standing constraint until this lands (`D-IMPL-151`, `D-GATE-18`):** the SDK must not be
described — in documentation, release notes, examples or conversation — as detecting a
transport that answered a different question, or a vessel altered in transit. `codec.py`'s
prose was corrected in-phase to say so at the source.

**Requirements:** carries Phase 18's `B0`. **Depends on:** Phase 18 (`D-GATE-18`).

**Plans:** 8 plans in 4 waves

Plans:
- [x] 19-01-PLAN.md — One wire shape carrying the question the door parsed and the address it computed; the MCP tool's required encoded request
- [x] 19-02-PLAN.md — The seam retyped to `ask(WireRequest) -> bytes`; both adapters stop constructing outcomes; in-process becomes a degenerate wire in both directions
- [x] 19-03-PLAN.md — Single-transport controls: a crossed question and an altered vessel caught by one client, plus codec-level byte sabotage and the ordering guard
- [x] 19-04-PLAN.md — The conformance tamper legs: every registered adapter wrapped in a byte-corrupting decorator it cannot opt out of
- [x] 19-05-PLAN.md — The AST gate proving no module under `src/ccf/client/adapters/` constructs the outcome, with its named sabotage control
- [x] 19-06-PLAN.md — The HTTP door reconciled: the request echo joins the `X-CCF-*` siblings, absent when no question was posed
- [x] 19-07-PLAN.md — The narrower true claim across `src/` and `runtime/`, the amended clock sentence, and the regenerated surface manifest with its migration fragment
- [x] 19-08-PLAN.md — Five `D-IMPL` entries, `CLNT-05`'s amendment, the client spec's Amendment 2, and `B0` closed in the Phase 18 review file


### Phase 20: Client Access from Three Harnesses — ADK, Anthropic Agent SDK and LangGraph Agents Reaching One Context Product over MCP

**Goal:** Three agents, each built in a different third-party harness — ADK, the Anthropic Agent SDK, LangGraph — reach the same Context Product through the MCP door shipped in Phase 18.1, registering that door as an ordinary tool, calling it, and printing the product to the console.

Same product, same door, three harnesses. This is the continuation of the client-side arc
(17 → 18 → 18.1 → 19), and the first time `CLAUDE.md` §7.3's claim — *"a harness that
already speaks MCP needs no adapter for consumption"* — is **demonstrated** against the
current surface rather than asserted in a design document.

**Why this phase exists.** The client seam is finished and the second door is proven, but
every consumer that has exercised the MCP door to date is CCF's own `consume.py`. The
adoption question the examples have not yet answered is the one an adopter actually asks:
*I already have an agent, in my harness — what do I write to get CCF context into it?* The
answer is supposed to be "an MCP tool registration and nothing else." Three harnesses
answering it identically is the proof; one harness answering it is an anecdote.

**What exists, and why it does not discharge this.** Two prior attempts are on disk and
neither is current:

- `examples/external/00-hello-context/` (Phase 13.1, 2026-08-02) has exactly this shape —
  `client_adk.py`, `client_anthropic.py`, `client_bare.py`, deterministic in CI via
  `run.py` and a replay server, with `--live` opt-in legs. It was built against the
  **pre-Phase-17 surface** and stands up its own `serve.py`; it predates `ccf.client`,
  the `mcp+stdio` adapter, the Phase 18.1 deployment-declares-its-server binding, and the
  Phase 19 wire form. Its *runner design* is the precedent this phase should inherit; its
  *client code* is not.
- `examples/s2-01-external-consumers/` holds `client_claude_agent.py` (177 lines) and
  `client_langgraph.py` (200 lines) with no README, no runner, and **no `make` target** —
  orphans of the retired Phase 16 (`D-IMPL-152`). They are history, not a work queue.

**Scope — three client programs, one door, no new mechanism:**

1. **Example 1 — ADK.** A Google ADK agent on the client side that registers the
   `examples/hw1-companies-over-revenue` MCP door as a tool, asks the same question
   `consume.py` asks, and prints the returned Context Product to the console.
2. **Example 2 — Anthropic Agent SDK.** Identical in every respect except the harness.
3. **Example 3 — LangGraph.** Identical in every respect except the harness.

The three programs are deliberately the *same program three ways*. What the reader is meant
to see is how little differs — and that what differs is entirely harness API, never CCF.

**The client-side purity claim, and how it is held.** Each client program imports its
harness, an MCP client, and stdlib — and **nothing from `ccf`**. That is the whole point:
CCF is a black box behind a tool. This must be **gated**, not asserted, in the shape
`CLNT-14` already established for `consume.py`, and — per `CLNT-12`'s inherited standard —
every new gate carries a named sabotage control in the same plan that adds it.

**Explicitly out of scope.**
- **No new SDK mechanism.** No new transport, no new adapter, no change to `ccf.client` or
  the codec, no `HarnessAdapterProtocol` implementation. This phase consumes an existing
  door from outside; a diff reaching into `src/ccf/client/` is a blocking review event.
  (`D-IMPL-24`/`D-IMPL-25` harness-adapter work is a *producer-side* concern and is not
  what this phase is about — a harness consuming MCP needs no adapter, which is the claim
  under test.)
- **How the MCP server is assembled**, which stays off-stage until the assembly examples,
  exactly as Phase 18.1's README frame requires.
- **No fourth harness**, and no live-model requirement in the default path.

**Rulings carried in from the scope confirmation (Dave, 2026-08-20).** All four open
questions this entry raised are **ruled and locked before planning**. `/gsd:discuss-phase 20`
proceeds against them rather than re-opening them:

1. **CI determinism — adopt the replay pattern of `examples/external/00-hello-context`.**
   Seed or replay so all three legs are **CI-green by default**, with `--live` (or
   equivalent) opt-in for a real populated deployment. **"Unrun" is rejected** — it
   contradicts CLAUDE.md §9's *a broken example is a broken build*. **A live populated
   deployment must NOT be a CI requirement for these examples.** This is the load-bearing
   ruling of the four; the rest are layout and hygiene.
2. **Where they live — one directory, three clients.** `examples/hw1-harness-clients/` (or
   similar; exact name settled at discuss) holding the three thin client programs plus
   **one** README stating the frame: same product, three harnesses, MCP tool only. Sibling
   directories multiply READMEs and obscure that the only variable is the harness.
3. **The duplicates — the tree must not carry three ADK and two LangGraph clients at mixed
   vintages.** The Phase 16 orphans in `examples/s2-01-external-consumers/` are
   **quarantined or removed** as this phase's cleanup, on the ground that they have no
   runner, no README and no `make` target. The Phase 13.1 clients under
   `examples/external/00-hello-context/` either **stay as historical external examples** or
   are **clearly marked pre-Phase-17 surface** — either way they must not be confusable
   with the Phase 20 trio. **Phase 20's three clients are the canonical "foreign harness →
   MCP door" demonstration going forward.**
4. **Requirement lane — continue `CLNT-NN`.** This is still client-access work, not a new
   domain. No new prefix.
5. **The replay harness is COPIED into the new directory, not shared** with
   `examples/external/00-hello-context/` (Dave, 2026-08-20, on the residual discuss point
   raised by rulings 1 and 3 touching the same file). What Phase 20 inherits is the
   **runner design** — replay by default, `--live` opt-in — not a long-term shared
   implementation contract with a retired-vintage example. Ruling 3 marks that directory's
   clients historical; coupling a canonical example to one just labelled historical means a
   change for the new clients risks fixing or breaking the old surface and the reverse, and
   **Phase 20 must not break when `00-hello-context` eventually ages out or is
   quarantined**. Duplicating a small replay harness is cheap; shared ownership across
   "canonical now" and "historical" is expensive and confuses the tree for the next reader.
   `00-hello-context` keeps its own copy. **Settled for discuss unless a strong
   counter-measurement appears.**

6. **The leg-2 prompt must be data, and `cinv01a-prompt-shape` is tightened in-phase**
   (Dave, 2026-08-20, at the plan gate — this **widens** the scope closed above, and is
   recorded here rather than absorbed silently). Leg 2 sends prompt text; no plan named its
   source; and the enforcement is measurably absent for the shape it needs —
   `prompt_score` scores short realistic agent prompts 0–1 against
   `PROMPT_SCORE_THRESHOLD = 2` (one signal is `MIN_SENTENCES = 3`), so
   `tools/lints/no_hardcoding.py` returns no finding for a hardcoded system instruction in
   an example client. Measured at the gate, four shapes, all clean. The ruling has three
   parts: **(a)** the prompt is data outside the client module — a prompt artifact under the
   example directory, or argv/env supplied by the runner — never an instruction string
   literal in client source; **(b)** the prompt-shape check is extended so a short agent
   prompt embedding domain instruction is refused, with a named sabotage control per
   `CLNT-12`; **(c)** the new control **stands on its own after `H-13`**, which moves the
   only file currently stating the rule in its own docstring
   (`examples/s2-01-external-consumers/client_claude_agent.py`). A teaching example that
   hardcodes the agent's instructions while every other gate stays green is §6.4 failing
   silently, and this phase is the first to step into a hole that predates it.
   **The ten Success Criteria below are unchanged**; this adds enforcement, and any
   requirement it needs is minted in the `CLNT-NN` lane.

**Scope is confirmed and closed at these three clients.** The ten Success Criteria below
are the gate target and **are not to be expanded during planning** (Dave, 2026-08-20). If a
ruling above turns out to affect SDK surface rather than example layout, that is a
`D-IMPL-NN` and a stop — not a quiet widening of this phase.

**Success Criteria** (what must be TRUE):

  1. An ADK agent registers the Phase 18.1 MCP door as a tool, calls it, and prints the returned Context Product to the console, in a client program that imports nothing from `ccf`
  2. An Anthropic Agent SDK agent does the same against the same door, in a client program that imports nothing from `ccf`
  3. A LangGraph agent does the same against the same door, in a client program that imports nothing from `ccf`
  4. The Context Product each of the three harnesses prints carries the same content address as the one `examples/hw1-companies-over-revenue/consume.py` prints for the same question at the same `as_of` — the harness is the variable, the product is the constant
  5. Client-side CCF-import purity is enforced by a gate rather than by inspection: an AST check refuses a `ccf.*` import in any of the three client programs, and that check carries a named sabotage control demonstrating it can fail
  6. Every leg runs deterministically in the default path with no live model call, and a `--live` opt-in exists for each harness — or the alternative is ruled explicitly rather than allowed to become "documented but never run"
  7. No new SDK mechanism ships: no new transport, no new adapter, no change to `ccf.client` or the codec, and no `HarnessAdapterProtocol` implementation — verified by the phase diff touching no file under `src/ccf/client/`
  8. The prior-vintage duplicates (`examples/s2-01-external-consumers/`, and the pre-Phase-17 clients under `examples/external/00-hello-context/`) are resolved by an explicit decision that is executed in-phase, not left in the tree at three surface vintages
  9. Each example's README names its harness, what the reader must install, what the reader would change first to point it at their own deployment, and that how the MCP server is assembled is deliberately out of scope until the assembly examples
  10. `make ci` is exit 0 at the phase close, and any new `make` target for these examples is wired the way the phase's CI-determinism ruling requires

**Requirements:** minted at planning (lane settled by open question 4). Inherits `CLNT-12`'s
standard — every new check carries a named sabotage control in the same plan.
**Depends on:** Phase 18.1 (`D-GATE-18.1`, the door and the deployment-declares-its-server
binding) and Phase 19 (`D-GATE-19`, the wire form the door now speaks).
**Plans:** 8 plans in 8 waves (planned 2026-08-20; re-waved 2026-08-20 at plan
revision). The waves are fully serial. Three things forced it and none is a
preference: `20-05` asserts a file count and an AST shape that `20-04` is
concurrently producing; every plan writes the generated
`docs/surface/examples/RETIREMENT-COUPLINGS.md`, which is byte-compared by
`make gate-tools` and is **red at this phase's base commit** because Phase 20's own
planning documents reference `examples/s2-01-external-consumers/`; and every plan
from `20-03` on asserts a tree-global gate, which no plan can honestly assert while
a sibling mutates the same tree.

**Two constraints that hold across every wave** (carried from 18.1/19, and not truths of any
single plan): `.venv/bin/python` always — bare `python` does not exist on this host and a plan
that writes it reports a false red; and no `state.*` or `roadmap.*` SDK writer is ever run —
`.planning/` files are hand-edited.

Plans:
**Wave 1**

- [x] 20-01-PLAN.md — Mint CLNT-23..31, record the `D-32` narrowing (`D-IMPL-163`), pin the criterion-7 diff base, author `artifacts/scenario-rows.yaml`, and regenerate `RETIREMENT-COUPLINGS.md` to establish the phase's green `make gate-tools` baseline

**Wave 2** *(blocked on Wave 1)*

- [x] 20-02-PLAN.md — The fabric-side runner: copy `deployment/`+`server/`, seed and close the writer, resolve `command + args`, run `consume.py` for criterion 4's reference address, wire `example-hw1-harness-clients` into `examples:`

**Wave 3** *(blocked on Wave 2)*

- [x] 20-03-PLAN.md — Legs 1 and 3: `client_adk.py` and `client_langgraph.py`, zero `ccf` imports, structural leg discovery, per-leg address comparison

**Wave 4** *(blocked on Wave 3)*

- [x] 20-04-PLAN.md — Leg 2: the copied fail-loud SSE model stand-in, the extracted offline `claude` recipe, `client_anthropic.py`, `--live` semantics

**Wave 5** *(blocked on Wave 4)*

- [x] 20-05-PLAN.md — Criterion 6: the no-model socket guard over legs 1 and 3 with three controls, and the `--live`-is-one-flag AST assertion with three more

**Wave 6** *(blocked on Wave 5)*

- [x] 20-06-PLAN.md — The AST purity gate: per-root permitted sets kept prefix-matching, `ccf` refused by name, the measured budget and its own control, command identity, controls C-20-1..C-20-9

**Wave 7** *(blocked on Wave 6)*

- [x] 20-07-PLAN.md — Retirement: `s2-01` → `docs/retired/16-external-consumers/`, the transport spike retired after its recipe was extracted, six references swept, `00-hello-context` marked historical in prose and asserted intact, the LangGraph-only count claim, the coupling inventory regenerated

**Wave 8** *(blocked on Wave 7)*

- [x] 20-08-PLAN.md — The one README, its structure test, three `--live` targets outside `examples:`, criterion 7's asserted empty diff, and `make ci` exit 0

### Phase 21: Requirement-Ledger Reconciliation — What Is Actually Discharged (INSERTED)

**Goal:** give every one of the 54 not-`Complete` requirement rows a verdict backed by evidence in the tree, so that a tick means something and v0.2 can be closed on a ledger that matches reality.

**Why this phase exists.** Commissioned by Dave 2026-08-21 at the Phase 20 close, after `D-GATE-20` recorded the debt rather than absorbing it. The plan counter reads 100% and the ledger reads 54 outstanding; both cannot be true. The counter is the one that is wrong, and it is wrong in this project's own recurring shape — a check structurally incapable of reporting the thing it appears to report.

**What is already ruled, and is not this phase's to decide:**

- The ten phases with no `D-GATE` entry (9, 10, 11, 12, 13, 13.1, 13.2, 13.3, 14, 16) are gated by their ROADMAP completion rows, and **no gate entry is backfilled** — `D-IMPL-171` (Dave, 2026-08-21). Backfilling would be authoring gates after the outcome, which `D-GATE-19` refused for success criteria.
- Phase 16's eighteen `DOCS-` rows are **Dave's to rule** once this phase reports the split. The executor produces the evidence; it does not flip or drop them.

**Out of scope, explicitly:** building anything a `not-built` verdict identifies. This phase *finds and records*; the work it surfaces is scoped as its own phase afterwards, with Dave ruling on what is worth building at all. An executor that starts closing gaps it discovered has turned an audit into an unplanned implementation phase.

**Requirements:** `RECON-01` .. `RECON-10`, minted at planning 2026-08-21. `RECON-01` parse + vocabulary (criteria 1, 2) · `RECON-02` evidence discipline (3, 6) · `RECON-03` refusal + sabotage control (4, 5) · `RECON-04` named absence + work list (7, 8) · `RECON-05` the Phase 16 split (9) · `RECON-06` channel agreement (10) · `RECON-07` the 27 `human_needed` items (11) · `RECON-08` untouched fabric (12) · `RECON-09` close hygiene (13, 14) · `RECON-10` the three stale counters (D-19, adjacent to criterion 1).

**These ten rows are minted into `.planning/REQUIREMENTS.md` in wave 1**, as `Pending`, following the `CLNT-23`..`32` precedent from Phase 20 — reversing an earlier planning decision to defer them to the gate (revised 2026-08-21 after the plan checker). The deferral's stated reason was that the ledger is this phase's subject and its 133-row / 54-working-set figures are asserted by every plan; that reason is defeated by the mechanism the plans already adopt — the working set is a **frozen 54-member roster taken by the strict parse at the pinned base**, so the phase's own edits cannot move the predicate, and ten added rows are absorbed the same way. The table reads 133 at the pinned base and **143** from plan `21-01` task 2 forward; the ten `RECON-` rows are this phase's own and are **not** members of the 54 it audits. Decisively: rows added at the gate would be written *after* Dave's approval, inside a `checkpoint:human-verify` task, and would therefore never be seen by the close-time cross-AI panel, never by the single-agent review, and never by Dave — ten rows entering the ledger carrying verdicts nobody reviewed, which is the exact ledger-debt pattern this phase was commissioned to end, one level up. Their verdicts are written in plan `21-06`, before the panel; plan `21-07` adds no ledger rows.

**Plans:** 7 plans in 7 waves (serial — every audit plan writes to `.planning/REQUIREMENTS.md`, so no two can share a wave)

Plans:
- [x] 21-01-PLAN.md — the CI `docs`-job full-history checkout, the pinned diff base, the three rulings, the ten `RECON-` rows minted as `Pending`, and the standing checks, before any verdict is written
- [x] 21-02-PLAN.md — verdicts for the 22 `CLNT` rows (Phase 17's 21, plus Phase 18's `CLNT-15`)
- [x] 21-03-PLAN.md — verdicts for the remaining 14: `HARD-01`..`03`, `EXAM-01`..`03`, `DOCS-01`..`06`, `CPS-03`, `DCD-02`
- [x] 21-04-PLAN.md — Phase 16's eighteen `DOCS-` rows and the two-sided split Dave rules from
- [x] 21-05-PLAN.md — the work list, the 27 `human_needed` items, the observations, and the three counter corrections
- [x] 21-06-PLAN.md — the ten `RECON-` verdicts (before the close panel), the completeness assertion (held back until every row is written), the position files, and `make ci`
- [x] 21-07-PLAN.md — the §3.1 close panel, the single-agent review, and `D-GATE-21`

**Success Criteria** (what must be TRUE):

  1. All 54 not-`Complete` rows in `.planning/REQUIREMENTS.md` carry a verdict, counted by a STRICT parse of the traceability table rather than by a substring match, and the verdict count equals the not-`Complete` count with no row missed and none carrying two
  2. Verdicts use the vocabulary Phase 15.6 already established in this ledger — `Complete`, `Complete as ruled`, `Complete over the ruled scope`, `Partial` — extended by `Not built` and `Orphaned`, in the `DCD-02`..`DCD-12` status-cell shape
  3. Every verdict other than `Not built` and `Orphaned` cites its evidence in the status cell as a full repo-relative `path::symbol` form that the citation lint resolves
  4. A bare basename in a requirement row is REFUSED by a standing check, so the `F-3`/`WR-08` ambiguous-basename hole cannot silently drop one of this phase's own citations
  5. That refusal carries a named sabotage control: a row given a deliberately false or ambiguous citation is observably RED, proven by a standing test and not by a probe recorded in a SUMMARY (`D-IMPL-170`)
  6. Every row whose property an existing test already guards names that test alongside its citation, and no test is written in this phase for the purpose of manufacturing such a name
  7. Every `Not built` and `Orphaned` verdict names the specific absence it rests on, in a form a reader can check by looking rather than by trusting
  8. The `Not built` rows are delivered to Dave as a scoped work list — each with a one-line statement of what closing it would mean — and nothing on that list is built in this phase
  9. Phase 16's eighteen `DOCS-` rows are reported as a two-sided split with evidence on both sides, and are left unflipped and undropped pending Dave's ruling
  10. The checkbox list and the traceability table agree on EVERY requirement id the ledger contains — 133 at the pinned base and 143 once this phase mints its own ten `RECON-` rows in wave 1 — asserted by a standing check that reads the count from the ledger rather than carrying one, so the ledger's two status channels cannot drift apart; criterion AMENDED 2026-08-21 from "every one of the 133 requirement ids" on Dave's ruling, because a criterion that hardcodes a row count is falsified by any phase that mints a row, this one included
  11. All 27 `human_needed` verification items across 11 phase records are named with their phases and left untouched, and the phase record states plainly that they are out of scope and why — the roster is re-derived by parsing every `.planning/phases/*/[0-9]*-VERIFICATION.md` for a `human_verification:` block, NOT by `gsd-sdk query audit-uat`, which filters on frontmatter `status:` and drops Phase 12 (`status: passed`, 1 item) and Phase 18 (`status: gaps_found`, 2 items); criterion AMENDED 2026-08-21 from "the 24 ... across 9 phases" on Dave's ruling after the plan-checker measured 27
  12. `src/` and `runtime/` are untouched — `git diff --stat <pinned-base>..HEAD -- src/ runtime/` prints nothing, with a control proving the assertion is not vacuous
  13. `make ci` is exit 0 at the phase close, with `docs/surface/examples/RETIREMENT-COUPLINGS.md` regenerated LAST after every `.planning/` edit
  14. A `D-GATE-21` entry is logged on Dave's approval, and the phase does not close without it (`CLAUDE.md` §3.1)

### Phase 21.1: The Guard That Did Not Guard — Closing the Check-Vacuity Class (INSERTED)

**Goal:** close the *check-cannot-fail* defect class across the whole ledger-verification module in one pass, so that every standing assertion Phase 21 installed can actually be observed failing when its subject is broken.

**Why this phase exists.** Commissioned by Dave 2026-08-22, immediately after the `D-GATE-21` provenance re-run. That re-run put the phase's shipped artifacts through the official panel path (`gemini`, `codex`, `cursor`; executing model excluded) with the committed tree as payload per `D-IMPL-178`, and surfaced three NEW blocking findings that the first close panel did not reach. The first of them is the phase's own thesis one level down: `B-1` was fixed by adding `tracked_under` as a refusal in `fabric_diff`, and `tracked_under` validates the pathspec **tuple** rather than its **members** — so `fabric_diff(base, ("scr/", "runtime/"))` returns the empty string with NO refusal, because `runtime/` matches 71 tracked files and satisfies the truthiness test on behalf of the typo. Every multi-member emptiness assertion in the module — `FENCE` has five members — can therefore report "tree untouched" over a real breach of the `D-11` scope fence. `gemini` and `codex` found it independently, from opposite ends, because §3.1's *point them at what is adjacent* instruction aimed them at `B-1`'s neighbourhood rather than at `B-1` itself.

**Why the whole class rather than the three blockers.** Dave's ruling: closing only `RR-1`, `RR-2` and `RR-3` would leave the remaining *check that cannot fail* findings — `RR-4` and `RR-6` — as known holes in the machinery just installed, and would buy a second residual wave. One pass on the class is cheaper and more honest.

**What is already ruled, and is not this phase's to decide:**

- `D-GATE-21` **stays in force** and is NOT amended. This is a fix wave on the verification machinery, not a re-opening of the 54-row audit.
- The 54 rows' verdicts stand. Where closing a blocker requires a ledger change, that change is NAMED, and it is the exception rather than the mode.
- `D-21` is still binding: no standing check may carry a hardcoded row count, and every fixed set is a frozen roster of named ids.
- `D-15` is still binding: `.planning/STATE.md` and `.planning/ROADMAP.md` are hand-edited; no `state.*` or `roadmap.*` writer is invoked.

**Scope widened 2026-08-22, before Wave 1.** Research found the class's *generator* by mutation: neutering each refusal branch one at a time leaves **eight refusals deletable with all 51 tests still green**, two of them unreachable dead code, because NOTHING in the module proves that a CONTROL's mutation reaches the assertion it vouches for. That is why `CONTROL A`, `CONTROL 5` and `CONTROL 13` all shipped mis-aimed. Dave ruled the generator in scope — closing the eight without it would clear the board and leave the engine running — bounded to THIS MODULE ONLY: no repo-wide reachability framework. Criteria 12, 13 and 14 and requirement `VAC-06` were added BEFORE any execution, per `D-GATE-19`.

**Out of scope, explicitly:** the policy and work-list items Dave ruled carried at the `D-GATE-21` sitting — `A-1` (Pending staleness policy), the `DOCS-17`/`CLNT-17`/`DOCS-14`/`EXAM-02` knot, and any further wording change to the §Coverage `42` sentence beyond what `D-IMPL-177` already settled. No expansion of product surface: `src/`, `runtime/`, `examples/`, `public/` stay diff-empty.

**Plans:** 10 plans in 10 waves (serial — every implementation plan writes to the same single module, `tools/docs_tests/test_requirement_ledger.py`, so no two can share a wave). **The six `VAC-` rows are minted into `.planning/REQUIREMENTS.md` in wave 1 and verdicted in wave 9**, before the close panel reads the tree, on the `RECON-01`..`10` precedent: rows written inside the gate checkpoint carry verdicts no reviewer and no approver has seen.

**The sequencing that matters.** A check that is TRUE only after later work must not land in an early wave or it ships red; an INVARIANT check lands early where it is already true. Waves 1–3 are invariant fixes — measured true on today's tree, zero existing assertions disturbed. Wave 4 is documents only. Waves 5–8 are the generator, and the meta-control (criterion 13) lands LATE over a FROZEN set of controls rather than early over a growing one: every control this phase ships exists by the end of wave 6; the forward-binding property comes from its coverage limb rather than from its landing date; and landing it early would invert the RED/GREEN order by forcing the `CONTROL A` and `CONTROL 13` re-aims to precede the fixes they vouch for. The pathspec-aim meta-control is committed in wave 8 BEFORE those re-aims, so it is observed RED naming exactly the two controls this project shipped mis-aimed.

Plans:
- [x] 21.1-01-PLAN.md — per-member pathspec validation: `fabric_diff` quantifies over MEMBERS, `CONTROL 18` per multi-member constant, and the six `VAC-` rows minted in both channels
- [x] 21.1-02-PLAN.md — the dual-verdict cell: one union predicate both verdict gates consume, `CONTROL 19` on the exact `RR-2` shape, zero real rows disturbed
- [x] 21.1-03-PLAN.md — duplicate-id collapse and index non-vacuity: both channels refuse a repeated id BY NAME, `_index()` refuses an index that resolved nothing, and a `.planning/` document becomes citable at all — the plan-check blocker, closed before wave 9 needs it
- [x] 21.1-04-PLAN.md — the Phase 16 lane roster: the split document states its nineteen named ids and rules on `DOCS-22`, mirrored into `21-FINDINGS.md`, and the ledger cell AMENDED (the plan carried it as an open question; Dave ruled it at the plan gate, `D-IMPL-179` limb 1, and the plan's frontmatter and closing criterion were left stale by that ruling — the ruling wins)
- [x] 21.1-05-PLAN.md — limb identity: one refusal dispatcher, a frozen `LIMBS` roster, a neutering switch with its own off-guard, the dead limb removed and the two unreachable-by-hardcoding limbs repaired to reachable
- [x] 21.1-06-PLAN.md — a named CONTROL for every refusal Phase 21 left unwatched, each observed RED with its own limb neutered, plus standing controls on the two mechanisms this phase itself introduced that can disarm everything else
- [x] 21.1-07-PLAN.md — the meta-controls: `CONTROL_AIM`, coverage in both directions, and every limb-aimed and discriminator control proven to reach what it vouches for
- [x] 21.1-08-PLAN.md — the per-member derived base, and `CONTROL 13` and `CONTROL A` re-aimed onto the constants they vouch for with the aim proof watched RED naming both first
- [x] 21.1-09-PLAN.md — close hygiene: the six `VAC-` rows verdicted and gated, the `D-21` count sweep watched finding a planted count, `make ci` exit 0 with the generated report regenerated LAST
- [x] 21.1-10-PLAN.md — the §3.1 close: cross-AI panel on the SHIPPED tree, single-agent review, every finding verified, blocking findings fixed in-phase, then STOP for `D-GATE-21.1` (checkpoint — not autonomous)

**A fifth blocker, found at plan-check and closed in the plan set rather than carried:** `VAC-03`'s only possible evidence lives under `.planning/phases/`, and **no legal citation spelling existed** — `CITATION`'s path group excludes a leading dot so the citation does not survive extraction, and the `::symbol` alternative is refused on a non-Python path. Cite it and the row is refused as absent; omit it and `uncited_verdicts` refuses the row. The same defect Phase 21 hit on `.github/workflows/ci.yml` and nobody connected to `.planning/`. Closed in wave 3, inside the one permitted `tools/` write, with `D-07` intact and a control watching both the acceptance and the refusal.

**Four defects in the criteria as written, found at planning and NOT settled by the planner.** Each is carried to the gate as a question for Dave: (a) criteria 2 and 8 invert RED and GREEN, and criterion 2's literal reading also collides with criterion 10; (b) criterion 8 is unsatisfiable for the controls criterion 12 forces onto refusals that already ship; (c) criterion 12 offers two dispositions and reaches neither for a limb that is unreachable only because its subject is hardcoded — repaired to reachable rather than deleted, since the literal binary would delete a shallow-clone guard this project has actually needed, and once repaired the limb satisfies criterion 12's FIRST disposition outright, which makes the ask to Dave the smaller one; (d) criterion 13's red-on-the-aimed-limb wording does not fit the four positive discriminator controls. Two further readings are recorded: criterion 14's "no hardcoded SHA" scopes to DERIVED bases and not to the pinned base or `UNRESOLVABLE_BASE`, and criterion 5 requires amending a document `D-IMPL-175` already accepted, so the amendment is additive, dated, and its nineteenth row is a NEW ask.

**Requirements:** `VAC-01` .. `VAC-06`, to be minted at planning. `VAC-01` per-member pathspec validation (criteria 1, 2) · `VAC-02` the dual-verdict cell (3, 4) · `VAC-03` the Phase 16 lane roster (5) · `VAC-04` duplicate-id collapse and index non-vacuity (6, 7) · `VAC-05` control discipline and close hygiene (8, 9, 10, 11) · `VAC-06` the generator of the class — refusal reachability and control aim (12, 13, 14), added 2026-08-22 on Dave's widened-scope ruling BEFORE Wave 1.

**Success Criteria** (what must be TRUE):

  1. `tracked_under` refuses a pathspec in which ANY member matches no tracked file, not merely one whose members ALL fail — `fabric_diff(base, ("scr/", "runtime/"))` raises rather than returning the empty string
  2. Every multi-member pathspec constant the module asserts emptiness over carries a standing control that mutates exactly ONE member and is observed RED, and each such control is run against the pre-fix module and observed GREEN there
  3. A status cell carrying an unbolded leading verdict and a later bolded DIFFERENT verdict is reported as carrying two verdicts, with a control that hands the shipped function that exact shape and watches it refuse
  4. `verdict_token` and `doubled_verdicts` cannot disagree about what a cell's verdict is without at least one of them refusing, and a control proves the disagreement is detected rather than silently resolved
  5. `21-DOCS-16-SPLIT.md` rules on every Phase 16 `DOCS-` row the ledger contains and states its lane roster explicitly, and `DOCS-22` carries the same evidence discipline as the other eighteen in both that document and `21-FINDINGS.md`
  6. A duplicate requirement id in either status channel is REFUSED rather than silently collapsed into a dict, with a control that inserts one and watches the refusal fire
  7. `_index()` refuses an index that resolved nothing, so a zero-unresolvable-citation result cannot be produced by an index that had no subject, with its own non-vacuity control
  8. Every control this phase adds is watched failing against the pre-fix module and passing against the post-fix module, and the plan SUMMARY records BOTH runs rather than asserting the control works
  9. No standing check this phase ships carries a hardcoded row count (`D-21`), and every fixed set is a frozen roster of named ids asserted id-for-id
  10. `make ci` is exit 0 with `docs/surface/examples/RETIREMENT-COUPLINGS.md` regenerated LAST and committed
  11. `D-GATE-21` is unamended and the 54 rows' verdicts are unchanged except where a blocker's fix requires it, and every such change is named in the phase record
  12. Every refusal branch in the module takes exactly ONE of three dispositions — reachable, watched RED under a named CONTROL when its subject is broken; unreachable, REMOVED so no dead limb survives carrying a docstring that aims a control at it; or a SHIM, reachable only under a sibling's neutering and existing to keep that degradation SILENT, controlled under aim kind `shim` (`D-IMPL-181`)
  13. Every CONTROL in the module is proven to reach the assertion it vouches for — its mutation is watched RED on the aimed limb and GREEN when that limb is intact — so a mis-aimed control (`CONTROL A`, `CONTROL 5`, `CONTROL 13` are the three known instances) cannot ship unnoticed again
  14. A control that derives a diff base derives it PER MEMBER and carries no hardcoded SHA, and a member matching no tracked file makes that control REFUSE rather than silently skip
  15. A CONTROL aimed at a SHIM carries the INVERTED obligation — with the sibling limb neutered it proves the shim keeps the failure SILENT rather than crashing, and it goes RED when the shim is removed or broken so the crash returns; coverage quantifies over `shim` entries exactly as over every other kind, with no exempt roster

### Phase 22: The Adoption Argument — What RAG, Hand-Rolled Assembly and a Semantic Layer Lack (INSERTED)

**Goal:** publish one page that names the three things an adopter is actually choosing between — RAG over a vector store, hand-rolled context assembly, and a semantic layer plus prompt templates — and states what each lacks against **cited shipped mechanism**, with the UBO question as its worked demonstration and the passage-anchor honesty caveat carried. Discharges `DOCS-15`.

**Why this phase, and why now.** Dave's sequencing at the `D-GATE-21` sitting, verbatim (`D-IMPL-176` point 1): *"DOCS-15 first — cheapest, highest adoption leverage, one page, subject already gated in `s1-01`. Only coupling is that tree's survival under CLNT-17."* It is one of the five `Not built` rows the Phase 21 audit delivered as a scoped work list (`21-FINDINGS.md` §2), and the only one of the five that stands nearly alone — the other four are a single knot (`DOCS-14`, `DOCS-17`, `CLNT-17`, `EXAM-02`) that cannot be sequenced apart. Commissioned by Dave 2026-08-23, immediately after `D-GATE-21.1`.

**The absence is measured, not asserted (`D-10`).** The page does not exist in any form: no page under `public/` names RAG, a vector store, hand-rolled context assembly or a semantic layer, and no page carries the UBO question. Both greps return zero. There is no partial limb to credit.

**Re-derived against today's surface, NOT lifted.** The adoption argument was Phase 16's `16-08` and `16-13`. Both are unexecuted, both sit in `abandoned/`, and both were written against a surface that no longer exists. `D-IMPL-176` and the `DOCS-15` row both require re-derivation against what ships now — `ccf.client`, the two-transport `hw1` example, the three harness legs, and `s1-01`'s five-way-gated UBO demonstration. Phase 16 is not resumable (`D-IMPL-152`), and its `s3-` directory scheme is explicitly not binding (`D-IMPL-176` point 4).

**The subject already exists and is already gated.** `examples/s1-01-hello-context-product` asks one product class three questions and returns three different answers from one graph and one ingest; Jane Doe's real 30.0% interest in Acme is a sum over ownership paths that **no document in any source system states**, which is precisely the claim a vector store over chunked documents structurally cannot serve. The page has a subject to point at rather than one to invent.

**The one coupling, stated up front rather than discovered mid-phase.** `CLNT-17` proposes retiring `examples/s1-00-companies-over-revenue/` and `examples/s1-01-hello-context-product/`. Writing the adoption argument against `s1-01` makes this page a further reason that tree survives, and `17-08` already blocked its own removal on a measurement — deleting `s1-01` removes the last shipped `examples/` call site of `ccf.products.request::refuse_request`, which a standing seam-obligation gate asserts exists. Whether the page cites the example directly or cites only `src/`/`public/` mechanism and points at the example as illustration is an open question for discuss, not a planning detail.

**The honesty caveat is load-bearing, not decoration.** The `passage_anchor` contract ships (`D-IMPL-46`), but Pattern 5 — unstructured ingestion — was never built, so **no shipped pipeline produces passage anchors from documents.** Passage-level provenance for extractive claims is RAG's one genuine strength. A page that compares CCF against RAG while implying CCF extracts passage anchors from your documents overclaims at exactly the point where it is most exposed. Phase 16's abandoned `16-13` recorded the same caveat and the same gate shape; the caveat survives the rewrite even though the plan does not.

**What is already ruled, and is not this phase's to decide:**

- All five `Not built` rows stay on the work list (`D-IMPL-176`). This phase takes exactly one of them and drops none of the rest.
- **Replacements before removals** (`D-IMPL-176` point 2). This phase builds and removes nothing; `D-27` still forbids partial retirement.
- The `00`–`08` half of `D-27` remains Dave's and undecided; the quarantine stands.
- `D-15` is binding: `.planning/STATE.md` and `.planning/ROADMAP.md` are hand-edited, no `state.*` or `roadmap.*` writer is invoked, and `docs/surface/examples/RETIREMENT-COUPLINGS.md` is regenerated LAST after any `.planning/` write.
- The published-page machinery applies unchanged: the citation lint, `test_no_stale_example_paths.py`, `test_documented_commands_exist.py` and the publish scan all read `public/`, and a new page is subject to every one of them.

**Out of scope, explicitly:** `DOCS-12`, `DOCS-13`, `DOCS-14`, `DOCS-17`, `CLNT-17` and `EXAM-02`. `D-IMPL-176` point 4 frames the published-pages limb across `DOCS-12/13/14/15` as **one documentation workstream, not four independent page projects** — that framing is recorded and deferred; Dave's point 1 nevertheless sequences `DOCS-15` first and alone, and this phase honours the sequencing. **No SDK surface:** `src/` and `runtime/` stay diff-empty. No example tree is created, moved or removed. The 27 `human_needed` items (`D-20`) and `RECON-10`'s outstanding limb are untouched.

**Open questions for the discuss sitting** (each is a `D-NN` at discuss or a `D-IMPL-NN` and a STOP if it reaches SDK surface):

1. **Where the page lives.** `public/concepts/`, `public/tutorial/`, or a new top-level section — and whether it is one page or a page plus a nav entry.
2. **Whether the page may cite `examples/s1-01-...` directly**, given `CLNT-17` proposes deleting that tree, or whether it must cite only durable mechanism and treat the example as illustration.
3. **What "cited shipped mechanism" means mechanically** — which standing gate proves each of the three claims names a real symbol, page or make target rather than a plausible one. This is the difference between the page and an essay.
4. **Whether three alternatives are the right set**, or whether a fourth (a graph database with no governance plane; a context-management framework) belongs.
5. **Whether the staleness claim needs a demonstration it does not have.** `16-08` intended `examples/s1-02-freshness-and-debt` as the worked demonstration for the `λ_c`/`D_c` claim; it was never built. `s1-01` measures `D_c` and crosses the Forced-LLM band, which may be sufficient — or the claim gets stated without a dedicated demonstration, or dropped.

**Requirements:** `DOCS-15` (existing, `Not built`). Any further rows minted at planning, in wave 1 and verdicted before the close panel reads the tree, per the `RECON-`/`VAC-` precedent.

**Plans:** 6/6 plans complete (`D-GATE-22`, 2026-08-23). Planned as 5 in 5 waves and closed as **6 in 6** — plan `22-06`, the `CLAUDE.md` §3.1 close gate, was added at planning because five autonomous plans in a row end with nothing that stops. (planned 2026-08-23; `.planning/` and `mkdocs.yml`
and `tools/` and `public/` only — `src/`, `runtime/` and `examples/` are the
scope fence). **No requirement rows are minted**, so criterion 14's wave-1 mint
clause is discharged explicitly by a proven-empty id-set diff against `951eb4a`
rather than by silence; the standing wording gate is anchored in the ledger by
node-id citations in the `DOCS-15` status cell, on the `DOCS-16` precedent.

Plans:
- [x] 22-01-PLAN.md — the page's title, orientation, the UBO question and what a governed answer has to do; five `--8<--` includes from `s1-01`; the `nav:` entry and the corrected page-count comment (wave 1)
- [x] 22-02-PLAN.md — the three approaches named and every contrast recast as a question-fact; the client surface cited in prose node ids; the staleness claim narrowed; the passage-anchor caveat (wave 2)
- [x] 22-03-PLAN.md — `tools/docs_tests/test_adoption_wording.py`, one module and two obligations `AW-1`/`AW-2`, seven non-vacuity floors, eleven controls, seven sabotage runs across nine mutations, the three-condition denial-exemption limb (vocabulary, ordering, contrastive pivot) with one mutation per condition, and the `D-06` disposition (wave 3)
- [x] 22-04-PLAN.md — `DOCS-15` verdicted in both ledger channels with resolving citations including a control; the `s1-01` coupling recorded on `DOCS-15` and `CLNT-17`; the coupling report regenerated in the venv (wave 4)
- [x] 22-05-PLAN.md — the per-member fabric diff with the misspelled-member contrast; the phase record hand-edited into `STATE.md`; the report re-regenerated after the last SUMMARY write, its diff proven CONFINED to `.planning/STATE.md` and `.planning/phases/22-*` rows under *Measured but not assigned* rather than byte-identical; `make ci` on six foreground legs with the test leg chunked (wave 5)
- [x] 22-06-PLAN.md — the CLAUDE.md §3.1 close in its order, on the `21.1-10` precedent: the cross-AI panel on the SHIPPED tree verified as having run, the blocking human checkpoint for Dave, and `D-GATE-22` logged only after approval — the plan does not run the panel, it gates on it (wave 6, **not autonomous**)

**Success Criteria** (what must be TRUE) — **LOCKED AT THE DISCUSS SITTING 2026-08-23, BEFORE PLANNING AND BEFORE WAVE 1**, per `D-GATE-19`'s forward binding. Derived from the fifteen decisions in `22-CONTEXT.md`; every one of Dave's four rulings at that sitting is represented. Criteria are never authored retroactively.

  1. One published page exists under `public/concepts/`, is reachable from `mkdocs.yml`'s `nav:` under Concepts, and **its title names the question rather than any named alternative** — a title naming RAG would promise the assertion criterion 4 forbids the body from making
  2. The page names **all three** alternatives `DOCS-15` requires — RAG over a vector store, hand-rolled context assembly, and a semantic layer plus prompt templates — **and no fourth**
  3. Every code-backed claim on the page is a literal `--8<--` include from a CI-gated source, so moving the source or renaming a marker **fails the strict build**; prose naming a symbol without an include does not satisfy this for a code-backed claim
  4. **No sentence on the page asserts a capability limit of an external approach.** Every contrast is either recast as a checkable fact about the UBO question, or — for a residual case that genuinely cannot be recast — paired with the shipped mechanism supplying the missing property and called out as such, with the citation on the CCF half
  5. A standing wording gate over `public/` refuses **both** (a) a sentence asserting a capability limit of an external approach without grounding and (b) any claim that CCF extracts passage anchors from documents — **each obligation watched RED under its own injected violation**, with non-vacuity floors proving the walk read a populated tree and that the positive assertion had something to assert over, and a false-positive control proving a legitimate construction is not an offender
  6. The passage-anchor honesty caveat is carried on the page in its own words: the `passage_anchor` contract ships (`D-IMPL-46`), Pattern 5 was never built, and **no shipped pipeline produces passage anchors from documents**
  7. The UBO question is the page's worked demonstration, cited from `examples/s1-01-hello-context-product` — its spine marker regions, its definition artifacts, and the test that asserts its numbers — and **no file under `examples/` is modified to make that possible**
  8. The hand-rolled-assembly contrast is cited against the client surface (`src/ccf/client`, the `hw1` example) and every such citation resolves under the citation lint, `public` already being in its `GATED_TREES`
  9. **No new snippet include and no new prose path reference is added against `examples/00`–`08` or `examples/external/00-hello-context`** — this page adds nothing to the 102 includes `DOCS-17` must re-cut
  10. The page's dependency on `examples/s1-01-hello-context-product` is recorded where `CLNT-17` will be read — on both the `DOCS-15` and `CLNT-17` rows of `.planning/REQUIREMENTS.md` — **and lands mechanically** as coupling rows owned by `17-08` in `docs/surface/examples/RETIREMENT-COUPLINGS.md`, so the coupling survives nobody remembering it
  11. The staleness claim rests only on what `s1-01` already measures — debt crossing this deployment's Forced-LLM band — or is narrowed or dropped; **no `examples/s1-02-*` tree is created**
  12. `src/` and `runtime/` are diff-empty against the phase base and no example tree is created, moved or removed — proven by a **per-member** pathspec diff (`VAC-01`, Phase 21.1 criterion 1), never by a whole-tuple one that a one-key typo satisfies
  13. `make ci` is exit 0 on all six legs, with `docs/surface/examples/RETIREMENT-COUPLINGS.md` regenerated **LAST** and **in the venv** — the system `python3` silently drops rows — and committed
  14. `DOCS-15` carries a verdict in **both** status channels of `.planning/REQUIREMENTS.md`, citing files that exist as written; any rows this phase mints are minted in wave 1 and verdicted **before** the close panel reads the tree, on the `RECON-`/`VAC-` precedent
  15. If the per-claim symbol-resolver test (`22-CONTEXT.md` `D-06`, non-blocking) does not land, it is **named as owed in the phase record** rather than silently absent

### Phase 22.1: The Hygiene Block — The Tool That Could Not Tell "None" From "Could Not Look" (INSERTED)

**Goal:** clear three hygiene items so the requirement ledger stops lying about
what is owed, and so the retirement decision — the largest remaining piece of
v0.2 — rests on a coupling count that cannot be silently wrong. The phase
BUILDS NOTHING and REMOVES NOTHING: `src/`, `runtime/` and `examples/` are
diff-empty across it.

**Why this phase, and why now.** Commissioned by Dave 2026-08-23, immediately
after `D-GATE-22`, while scoping the four-row knot. Three findings made it its
own phase rather than a preamble to the archive move. **(1)** `tools/retirement_sweep.py`
— the tool whose report decides which files are safe to delete — swallows
failure at three sites, so a module that will not import contributes no rows
and the tool prints a confident total at exit 0. It cannot distinguish *"there
is no coupling"* from *"I could not look."* This was found during the Phase 22
discuss sitting, recorded, and ruled OUT OF SCOPE for that phase; it is this
project's own check-vacuity class (`D-GATE-21.1`) one tool over, and it sits
directly upstream of the retirement decision. **(2)** `RECON-10`'s outstanding
limb appears already discharged: its row text was written at `f285ac2` and the
correction it says is missing landed at `014f646`, the next commit the same
day, under Dave's `D-IMPL-177`. A row that reads `Partial` because it is one
commit stale is the same defect class as a counter that never got corrected.
**(3)** 27 `human_needed` items across 11 phase records are NAMED and not
discharged (`D-20`), and no one has ever put them in front of Dave in one
place. **The archive move is explicitly NOT in this phase** (`D-IMPL-189`);
it is a separate, later step.

**Success Criteria** (what must be TRUE) — **LOCKED AT THE DISCUSS SITTING
2026-08-23, BEFORE PLANNING AND BEFORE WAVE 1**, per `D-GATE-19`'s forward
binding. Confirmed by Dave in the same sitting that ruled `D-IMPL-189`.
Criteria are never authored retroactively.

  1. `tools/retirement_sweep.py` fails **CLOSED** at all three swallow sites — `:789` (a module that will not import), `:982` (a floor scan that will not run) and `:1124` (a sabotage run that cannot be measured). A subject that cannot be examined is RECORDED as unexaminable and the run exits non-zero; the tool never prints a count as though the walk completed. The two narrower sites — `:447` (unreadable bytes) and `:484` (untokenizable source) — are **examined and either fixed or their exemption recorded with the reason stated**, rather than left unmentioned
  2. **A non-vacuity floor**: a test proves the sweep read a NON-EMPTY module set and produced rows, so "fails closed" cannot be satisfied by a walk that looked at nothing. The floor is distinct from the refusal assertion and fails for its own reason
  3. **A control watched RED BEFORE GREEN**, twice: an unimportable module planted in a scanned tree makes the sweep exit non-zero **naming the module**; and the original reproduction — the system `python3` printing **258** coupling rows at exit 0 where the venv prints **264** — now REFUSES rather than under-reporting. Any control that cannot be made to fail is NAMED as such rather than glossed
  4. `docs/surface/examples/RETIREMENT-COUPLINGS.md` is regenerated **LAST**, **in the venv**, and committed; `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` is green
  5. `RECON-10` is **re-measured limb by limb against the tree** — never accepted from its own row text — and verdicted to what the measurement supports, citing `D-IMPL-177`. If the measurement does not support discharge, the row stays `Partial` and the reason is stated
  6. The 27 `human_needed` items are assembled from all 11 phase records into ONE decision packet: each item QUOTED, its phase named, and a one-line statement of what accepting it would mean. **Delivered, not ruled** — nothing is discharged in this phase, and the packet says so
  7. `DOCS-17` and `CLNT-17` **remain `Not built`**. No `Partial`, no "archived", no "out of CI" wording is written for either row, because the state it would describe does not exist on the tree (`D-IMPL-189` point 4)
  8. `src/`, `runtime/` and `examples/` are **diff-empty** against the phase base, proven by a **per-member** pathspec diff with each member proven to name tracked files — never by a whole-tuple diff a one-key typo satisfies (`VAC-01`, Phase 21.1 criterion 1)
  9. `make ci` is exit 0 on all six legs, the test leg run as **foreground** chunks whose coverage of the suite is PROVEN — collected counts summing to the full collect AND the chunks' node-id sets set-equal to the full collection and pairwise disjoint, because a sum alone is satisfied by a partition that double-counts one directory and omits another

### Phase 23: The Archive Move — Retiring the Ten Condemned Example Trees Without Deleting Them (INSERTED)

**Goal:** the **ten** example trees `DOCS-17` condemns move **intact** to an
archive location — out of the `examples:` aggregate and the always-on CI job,
and every published snippet include and prose path re-pointed so
`make docs-strict` stays green. **NOTHING IS DELETED.** On completion `DOCS-17`
is verdicted **`Partial`** for the first time, on the seam `D-IMPL-189` point 3
names: limb done — **out of the `examples:` aggregate** (AMENDED at the
close, 2026-08-25: this goal paragraph still carried the clause *"out of live
CI"* that `D-IMPL-191` ruling 4 amended and that criterion 12 FORBIDS the
shipped cell from claiming — nothing gated the goal prose, which is how it went
two rulings stale without a red), sources preserved under archive, includes
re-pointed, strict build green; limb owed — full retirement and the re-cut
against a replacement surface.

**`CLNT-17` IS NOT IN THIS PHASE AND STAYS `Not built`.** Scope corrected
2026-08-24 on Dave's challenge, before planning, on the measurements below.
The entry as first drafted carried all twelve trees; that was wrong.

**Why this phase, and why now.** Commissioned by Dave 2026-08-24, immediately
after `D-GATE-22.1` and the push of `main` to `origin`. `D-IMPL-189` (Dave,
2026-08-23) ruled archive-with-repoint an **allowed intermediate state**, and
this is the phase that performs it — `D-IMPL-189` point 4 is explicit that the
`Partial` verdict is written **in the archive phase, when the state exists on
the tree, and not before**, which is why Phase 22.1 performed no part of the
move and left the rows `Not built`.
**This is the only retirement work unblocked today.** The two rulings still
outstanding both govern DELETION: `D-27`'s `00`–`08` half remains Dave's and
undecided, and `D-IMPL-176` point 2 (*replacements before removals*) requires
`DOCS-14`/`EXAM-02` to exist first. Nothing is deleted here, so neither gate
binds — `D-IMPL-189` states the non-collision directly: *"Nothing is deleted
under this ruling, so no such state arises."*

**Scope, MEASURED against today's tree rather than carried from the ruling
(`D-19`, `D-IMPL-174`).** Re-measured 2026-08-24 at `efa0044`:

- **265 tracked files across the ten trees** — `examples/00-quickstart` … `examples/08-e2e-demo` plus `examples/external/00-hello-context`. Confirms `D-IMPL-189` exactly.
- **102 snippet includes** across **15 published pages**, concentrated in `public/tutorial/adopters-guide.md` and `public/tutorial/demo-walkthrough.md`, plus **9 prose paths** — 102 + 9 = **111**, which is `D-08`'s pinned figure and `21-04`'s re-measure. **`D-IMPL-189`'s own "99 snippet includes and 108 prose paths" does NOT match the tree and must not be quoted into any plan**; the ruling's cost estimate rests on it. Three includes does not move the estimate, but the figure is wrong and is named here rather than silently corrected.
- **CI: ten of the eleven `examples:` aggregate members go** — `example-00` … `example-08` and `example-ext-00` (`Makefile:256`). The single survivor is `example-hw1-harness-clients`. **The always-on examples job is 91% condemned trees**, which is the concrete benefit this phase buys.
- **Tests:** 25 of the 31 files under `tests/examples` name the condemned set.
- The published pages do not LINK to the examples — they `--8<--` **inline the source at build time**, so a moved file is a broken strict build rather than a stale link. `pymdownx.snippets` resolves `base_path` against the repo root (not `public/`), so an archive anywhere in the tree stays includable, and `check_paths: true` makes a wrong path fatal. `tools/docs_tests/test_no_stale_example_paths.py` independently asserts every prose path AND every include resolves on disk. **A half-finished repoint cannot go green**, which is why `docs-strict` is this phase's primary witness.

**WHY `CLNT-17`'s `s1` PAIR IS EXCLUDED — measured, not preferred.** The
question *"aren't the `s1` trees the client-side examples we just completed?"*
was put by Dave 2026-08-24 and the answer is **no**: the client-side pair is
`examples/hw1-companies-over-revenue` (Aug 16, Phases 17/18) and
`examples/hw1-harness-clients` (Aug 20, Phase 20), neither condemned nor in
this phase. `examples/s1-00-companies-over-revenue` (Aug 14) is the
**predecessor** `hw1-companies-over-revenue` rebuilt — its README is titled
*"HW-1 — companies over a revenue threshold you choose"*, the same scenario.
`examples/s1-01-hello-context-product` (Aug 10) is not a client example at all.
Three measurements exclude them:

1. **The benefit is ZERO, not small.** Neither `s1` tree is in the `examples:` aggregate. `example-s1-01` *"needs a Fluree server"* and `example-s1-00` *"needs Docker or `CCF_TEST_POSTGRES`"* — both are already outside the always-on job. Archiving them buys none of what it buys for the ten.
2. **Archiving `s1-01` would make a `D-IMPL-189` commitment FALSE.** All **7** published references to the `s1` pair are to `s1-01`, all on `public/concepts/answers-no-document-contains.md` — the page Phase 22 shipped 2026-08-23, five of them `--8<--` includes. Re-pointing them at an archive is precisely what `D-IMPL-189` forbids: *"it does not permit the published pages to be re-cut against the archive as though the archive were the teaching material."* `s1-00` has **0** published references.
3. **BOTH `s1` TREES ARE LIVE FIXTURES FOR CORE SUITES, NOT EXAMPLE TESTS.** `s1-00` is named by **11** test files including `tests/deployment/test_config_derivation.py`, `test_config_document.py`, `test_config_equivalence.py` and a `tests/deployment/fixtures/s1-00-multifile/` tree; `s1-01` by **6** including `tests/products/test_gate_two_call_shape.py`, `test_request_contract.py`, `test_resolver_seam.py`, `tests/replay/test_engine_rehydration.py` and `tests/halflife/test_debt.py`. Moving them means touching four core suites for no CI benefit.

**TWO FINDINGS ABOUT `CLNT-17` RAISED HERE AND NOT RULED — they are Dave's,
and no plan in this phase may act on either.** (1) **`CLNT-17`'s stated blocker
is wrong on the tree.** Its cell says deleting `s1-01` removes *"the last
shipped `examples/` call site of `ccf.products.request::refuse_request`"*, which
is why `17-08-SUMMARY.md` carries `status: blocked-at-task-3`. There are
**three** `.py` call sites and two are in `s1-00` — `s1-00/consume.py`,
`s1-00/produce.py`, `s1-01/spine.py`. The premise has been carried unexamined
since Phase 17. (2) **`CLNT-17` may be mis-framed as an example-retirement
row at all**, given finding 3 above; if the `s1` pair is core test
infrastructure, *"retire these example trees"* is the wrong obligation and will
keep reading as owed work nobody can safely do.

**RULED 2026-08-24 (`D-IMPL-190` ruling 2) — THE PAIRED TESTS STAY UNDER
`tests/`; ONLY THE SOURCES MOVE.** This AMENDS `D-IMPL-189` point 1, and both
clauses are named per the standing policy `D-GATE-22` set for `D-IMPL-188`.
**OLD:** *"their paired tests moved with them"*. **NEW:** the paired tests
remain under `tests/` and are re-pointed at the archive paths. **The
measurement that decided it:** `pyproject.toml:142` sets
`testpaths = ["tests"]`, so moving them out of `tests/` removes them from the
suite entirely; `tests/examples` collected **515 tests** AT PLANNING TIME (a dated
measurement, not a live gate — see criterion 7, `D-IMPL-198`), and the suite baseline
is **4105 passed / 118 skipped**, byte-for-byte identical across `D-GATE-21`,
`D-GATE-21.1`, `D-GATE-22` and `D-GATE-22.1`, each citing it as the mechanical
proof the phase changed no behaviour. Moving them drops the suite to roughly
3590 and moves that baseline for the first time — to achieve a DOCUMENTATION
archive. `D-IMPL-189`'s clause was written before anyone checked `testpaths`.
**The 4105 / 118 baseline is expected to HOLD across this phase and is to be
written as a Success Criterion.**

**Explicitly NOT in this phase.** Deletion of anything. `CLNT-17` and the `s1`
pair. Re-cutting the published pages against a replacement surface. `DOCS-14`
and `EXAM-02`, which still owe that replacement. The `00`–`08` half of `D-27`.
The 27-item human-verification packet, delivered and awaiting Dave (`D-20`).
And the standing observation that the archived pages teach the pre-Phase-15
integration surface (Phase 14's `G-01`) — the move RELABELS that, it does not
close it.

**Success Criteria** (what must be TRUE) — **LOCKED AT THE DISCUSS SITTING
2026-08-24, BEFORE PLANNING AND BEFORE WAVE 1**, per `D-GATE-19`'s forward
binding and `D-IMPL-174`. Each criterion is ONE LINE: a wrapped criterion
parses as a single verification truth, which is how 15.3 and 15.4 shipped
gated against less than they read as.

  1. The ten trees are moved **INTACT** to an archive location **outside `examples/`** (`D-IMPL-191` ruling 1): **265** tracked files present at the new location, the move proven to be a pure RENAME set (`git diff -M --diff-filter=R` accounts for all 265, and `--diff-filter=D` for none), so **nothing is deleted** and no file content changed in the move
  2. `examples/` retains **exactly four** trees — `hw1-companies-over-revenue`, `hw1-harness-clients`, `s1-00-companies-over-revenue`, `s1-01-hello-context-product` — and no `00`–`08` or `external/00-hello-context` directory remains under it, measured by `git ls-files` rather than by `ls`
  3. The `examples:` aggregate at `Makefile:256` names **exactly one** target, `example-hw1-harness-clients`; **FOURTEEN** targets are **DELETED, not renamed** — all ten of `example-00`…`example-08` and `example-ext-00`, **PLUS the four live-leg targets `example-03-live-ollama`, `example-03-live-anthropic`, `example-ext-00-live-anthropic` and `example-ext-00-live-adk`, which run condemned-tree scripts and sat in a gap between this criterion's old enumeration and its own no-archive-form rule (`D-IMPL-195` ruling 1)**; no archive-form target replaces any of them; and `.github/workflows/live-legs.yml` carries **no reference to a deleted target**, because a deleted target with a live workflow still calling it is a broken workflow rather than a retirement (`D-IMPL-191` ruling 2, AMENDED by `D-IMPL-195` ruling 1)
  4. All **102** snippet includes and **9** prose paths across the **15** published pages are re-pointed, and `make docs-strict` exits 0 on all four steps
  5. **A control watched RED BEFORE GREEN**: one include left un-repointed makes the strict build FAIL naming the path, AND `tools/docs_tests/test_no_stale_example_paths.py` fails independently of the build — proving the two witnesses are not the same witness
  6. The `D-08` reference count is re-measured at both ends and its movement RECORDED with the new value: the pinned **111** is stated as moved-by-design rather than silently changed, per `D-19` and `D-IMPL-174`
  7. The paired tests **STAY under `tests/`** and are re-pointed (`D-IMPL-190` ruling 2): `tests/examples` is gated as an ACCOUNTED DELTA TOO (`D-IMPL-198` ruling 1, correcting the *515 UNCHANGED* clause `D-IMPL-196` wrote in the same sentence that fixed the total limb) — **ZERO node ids LOST** under `tests/examples` against `PHASE_BASE`, every ADDITION NAMED, the total **RE-MEASURED at Waves 11/12** and never quoted from an entry: at this writing 515 + 4 (Wave 3, `test_artifact_schema_headers.py`) + 2 (`D-IMPL-197`, `test_hw1_harness_clients_readme.py`) = **521** measured, lost-set EMPTY; and the test leg is gated as an **ACCOUNTED DELTA against `PHASE_BASE`, not an absolute count** (`D-IMPL-196`) — **ZERO node ids LOST**, **every ADDITION NAMED** wave by wave in its SUMMARY, and the resulting total **RE-MEASURED at the close in foreground chunks proven to cover the suite, never inherited from any entry**; the superseded pin was *4105 passed / 118 skipped byte-for-byte the `D-GATE-21`/`21.1`/`22`/`22.1` baseline*, which became unachievable the moment criteria 17, 18 and blocker B2 required guards that belong beside their subjects under `tests/` — re-pinning schedules the same false red for the next wave, and relocating the guards would separate a control from what it vouches for (`D-GATE-21.1` `RR-9`)
  8. The two **EXECUTING** tests still execute against the archive — `tests/examples/test_cross_process_output.py` and `tests/examples/test_ext00_hardening.py` — and a control proves each RUNS the archived source rather than silently skipping, because a skipped test and a passing test are indistinguishable in the total
  9. `tools/retirement_sweep.py`'s `Retirement` table (lines 131-167) re-points the ten moved trees to **Phase 23 plans**, replacing the retired `16-15`/`16-17`/`16-18` owners; the `s1` pair's `17-08` rows are left untouched (`D-IMPL-191` ruling 3)
  10. Archived paths **STILL COUNT** as live couplings, proven by a control: suppressing an archived path's coupling row is watched RED, so the sweep cannot go blind to the archive — the Phase 22.1 defect class arriving one tree over
  11. `docs/surface/examples/RETIREMENT-COUPLINGS.md` is regenerated **LAST**, **in the venv**, and committed; `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` passes at the final commit
  12. `DOCS-17` is verdicted **`Partial`** in BOTH channels with a cell that says **"out of the `examples:` aggregate"** and **NOT "out of live CI"**, and that NAMES what still exercises the archived trees — **19 of 31** `tests/examples` files read them, **2** execute them — where **EXECUTE MEANS *SPAWNS A PROCESS*** (`D-IMPL-198` ruling 2): `tests/examples/test_cross_process_output.py` and `tests/examples/test_ext00_hardening.py`, NOT the 14 modules that `exec_module` archived source in-process and NOT the 18 that merely reference — the figure **RE-MEASURED by the plan and gated against what it measures**, never accepted from a decision entry, because the superseded **25** NEVER REPRODUCED AT EITHER END (19 at `PHASE_BASE`, 19 at `HEAD` — it was wrong from the start, not drift) because it was produced by a regex that matched inside `s1-00-companies-over-revenue` and the `hw1-` names (`D-IMPL-191` ruling 4, AMENDED by `D-IMPL-195` ruling 3)
  13. `CLNT-17`'s row is **BYTE-IDENTICAL** to its state at `efa0044`, verified by content hash rather than by reading, and stays **`Not built`** (`D-IMPL-190` ruling 1); no `s1` tree is moved, renamed or re-pointed
  14. `src/`, `runtime/` and `pyproject.toml` are **diff-empty** against the phase base **EXCEPT the four path-string-only citation updates AMENDED IN by `D-IMPL-192`, enumerated here by SYMBOL rather than by line per `D-IMPL-114` and `D-IMPL-123` — the module docstring of `src/ccf/products/bind.py`, `runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol`, `runtime/ccf_runtime/mcp/experience.py::ExperienceProductResolverProtocol` (these three each citing `examples/04-cross-process/producer_child.py::resolve`) and `runtime/ccf_runtime/mcp/experience.py::ContextProviderProtocol` (citing `examples/external/00-hello-context/serve.py::context_provider`), each re-pointed to its `archive/examples/...` path**; a FIFTH edit under any of the three members is a scope breach, the five `s1-01` citations are NOT touched, each of the four is proven PATH-STRING-ONLY, and the rest is proven by a **per-member** pathspec diff with each member proven to name tracked files — the `VAC-01` guard, because a misspelled member diffs empty exactly like a clean one
  15. `make ci` exits 0 on all six legs, the test leg run as **FOREGROUND** chunks whose coverage of the suite is PROVEN — collected counts summing to the full `--collect-only` total, and the chunks' node-id sets set-equal to the full collection and pairwise disjoint
  16. **Non-vacuity floors**: a test proves the include-repoint check saw a NON-EMPTY set of includes, and a test proves the moved-file check saw a NON-EMPTY set of files — neither may be satisfied by a check that looked at nothing
  17. `tools/publish_scan.py::INCLUDE_ALLOWED_PREFIXES` admits the archive root so re-pointed includes stop being publication-boundary violations, AND **a test GUARDS that tuple, watched RED by removing a prefix** — the constant's own comment calls it *"a POSITIVE allowlist, because the charter is default-deny"*, a grep found NO test naming it, and widening an unguarded default-deny boundary as a side effect of getting a build green is not a trade this phase makes (`D-IMPL-194`)
  18. `tools/docs_tests/test_no_stale_example_paths.py::PATH_TOKEN` no longer strips a leading `archive/` — its lookbehind omits `/`, so *archive/examples/X* yields the token *examples/X* and a CORRECTLY re-pointed page is RED on a correct tree — with controls in **BOTH** directions, because a one-character lookbehind widening can blind the check entirely: a correctly re-pointed page yields **ZERO** offenders AND a genuinely stale `examples/…` path still yields **at least one**, `tests/examples` still matching through its own alternation branch (`D-IMPL-194`)

**Requirements:** `DOCS-17` (`Not built` → `Partial` on completion, per
`D-IMPL-189` point 3). **`CLNT-17` is untouched and stays `Not built`.** Mints
none.

**Depends on:** Phase 22.1 (`D-GATE-22.1`) — the retirement sweep must fail
closed before its report is trusted to say what is safe to move; `D-IMPL-189`
(the ruling that authorizes the intermediate state); Phase 22 (`D-GATE-22`),
whose page is the reason `s1-01` is excluded.


## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 9. Hardening — Defect Fixes & Ruling Batch | 3/3 | Complete   | 2026-08-01 |
| 10. Hardening — Authorization & Posture | 4/4 | Complete    | 2026-08-01 |
| 11. Performance Battery | 5/5 | Complete    | 2026-08-02 |
| 12. Synthetic-Data Demonstration | 3/3 | Complete    | 2026-08-02 |
| 13. Examples Suite Upgrade | 5/5 | Complete   | 2026-08-02 |
| 13.1. External-Consumer Examples (MCP Egress) | 4/4 | Complete   | 2026-08-02 |
| 13.2. External-Example Hardening | 5/5 | Complete — no `D-GATE`; gated by this row per `D-IMPL-171`. *(Row added 2026-08-25; the phase had a detail section but neither a checklist bullet nor a row here.)* | 2026-08-03 |
| 13.3. Review-Residual Hardening | 2/2 | Complete — no `D-GATE`; gated by this row per `D-IMPL-171`. *(Row added 2026-08-25, with Phase 13.2's and for the same reason.)* | 2026-08-03 |
| 14. Documentation Suite | 10/10 | Complete   | 2026-08-03 (verified 5/5; G-01 deliberately deferred to 16) |
| 14.1. Docs — Deterministic Path & Adoption Argument | — | Superseded by 16 | — |
| 15. SDK Ergonomics — The Integration Surface | 21/21 | Complete    | 2026-08-05 (gated with carried debt; CR-1/CR-2 close in 15.1) |
| 15.1. Ergonomics Gap Closure — Governance Enforced, Not Conventional | 20/10 | Complete    | 2026-08-07 |
| 15.2. Substrate Adapters and Query Pushdown | 14/14 | Complete    | 2026-08-08 |
| 15.3. Fluree Adapter (Tier-1 Substrate) | 6/5 | Complete    | 2026-08-09 |
| 15.4. Backend Registration Seam — The Substrate Stops Naming Its Adapters | 12/12 + post-review fix pass (13 SUMMARYs) | Complete — **`D-GATE-15.4` APPROVED** (Dave, 2026-08-09), with two addenda: the close-time cross-AI panel and two structural invariants it found unenforced, and a correction naming finding F2 as `DI-15.4-06`. *(Row added 2026-08-25 — the phase had a checklist bullet and a detail section but no row here, so the table skipped 15.3 to 15.5.)* | 2026-08-09 |
| 15.5 Context Product Surface — Vessel, Assembler, Debt, Entitlement | 15/15 | Complete | 2026-08-11 |
| 15.6 Decision-Completeness and Defect Closure | 13/13 | Complete | 2026-08-13 |
| 16. Documentation Rewrite — Deterministic Path & Adoption Argument | 16/16 executed | **RETIRED 2026-08-17 (`D-IMPL-152`)** — not resumable; 14 unexecuted plans moved to `abandoned/`; obligations re-derived, not lifted | 2026-08-17 |
| 17. Client Access — `ccf.client` & Transport-Agnostic First Example | 12/14 | Complete | 2026-08-16 (`D-GATE-17`; `17-08` deferred and still in-phase, `17-10` lifted to 18 by `D-IMPL-147`. Row corrected 2026-08-17 — it read `0/10 — Planned 2026-08-15` through the phase's entire execution, gate and merge) |
| 18. MCP Transport — The Second Door and the Portability Proof | 1/1 | Complete — **`D-GATE-18` APPROVED**, merged `--no-ff` at `e57c93c`. *(Row corrected 2026-08-18: it read "AWAITING `D-GATE-18`" after the gate was granted and the branch merged.)* Approves the portability claim and **not** a tamper-detection claim; `B0` travels to Phase 19 | 2026-08-17 |
| 18.1. Simplify the MCP Example — Client-Side Access, Server Off-Stage | 5/5 + close-fixes | Complete — **`D-GATE-18.1` APPROVED** (Dave). `make ci-core` exit 0 at `04cccc2`: 3909 passed / 118 skipped / 0 failed. Close panel found 3 blockers, all fixed in-phase and independently re-sabotaged; 7 advisories carried; 1 finding recorded UNVERIFIED and not actioned. `D-IMPL-153` (the one new mechanism), `D-IMPL-154`/`D-IMPL-155` (tooling hazards) | 2026-08-19 (`D-GATE-18.1`) |
| 19. The Client-Seam Integrity Checks Must Be Able to Fail | 8/8 + close-fixes | Complete — **`D-GATE-19` APPROVED** (Dave). `make ci` exit 0 at `cff00ae`: 4013 passed / 118 skipped / 0 failed; suite 3901 → 4013 (+112). Closes `B0` (`D-IMPL-151`) on the axes measured — a crossed question and an altered vessel are each caught by a **single-transport** client, neither assertion naming a second subject. Verified by breaking ten properties and observing 43 control-reds; controls that could not be made to fail: none. Close review found the phase's own `C-17` gate could not fail for three in-tree spellings (`B0` re-openable with the build green) — reproduced end-to-end and fixed test-file-only. `D-IMPL-156`–`162`. **Success Criteria were ABSENT from this entry**; gated on plan `must_haves` + the full §3.1 record, and future phases must carry criteria before execution. Carried, not reopened: `F-2`, `F-3`, `WR-04` | 2026-08-20 (`D-GATE-19`) |
| 20. Client Access from Three Harnesses — ADK, Anthropic Agent SDK & LangGraph over MCP | 8/8 + close-fixes | Complete — **`D-GATE-20` APPROVED** (Dave). 51 commits, `9e4bd0e`..`921e3b9`, merged to `main`. CI run `32534167036` at `921e3b9` green on all four jobs; suite collects 4223, `tests/examples` 478 passed / 37 skipped. Three harnesses and `consume.py` print one content address `5d7bfa49…c37f5` with the declared payload names, clients importing nothing from `ccf`. **All TEN Success Criteria present in this entry BEFORE execution — the first honouring of the forward-binding rule `D-GATE-19` minted.** Criterion 7 asserted mechanically: `src/` diff empty vs the pinned base, so no new SDK mechanism shipped. `CLNT-23..32` discharged (ten rows). Close review found FIVE blocking findings — `B-1`/`B-2`/`B-3` (panel) and `CR-01`/`CR-02` (single-agent) — **all five fixed in-phase, each with a standing sabotage control watched go red**; four panel findings REJECTED and recorded as rejected. `D-IMPL-163`..`170`. Two pre-existing CI failures found and fixed here (shallow-clone base, stale generated `RETIREMENT-COUPLINGS.md`). Carried, not reopened: `A-1`..`A-4` and `WR-01`..`WR-09` (incl. `WR-08`, the `D-IMPL-155` ambiguous-basename hazard) | 2026-08-21 (`D-GATE-20`) |
| 21. Requirement-Ledger Reconciliation — What Is Actually Discharged | 7/7 + close-fixes | Complete — **`D-GATE-21` APPROVED** (Dave, 2026-08-22), merged to `main`. **All FOURTEEN Success Criteria met**, authored one-per-unwrapped-line before Wave 1 and amended twice on Dave's rulings. **The phase FOUND and RECORDED and built nothing**: the pinned-base diff over `src/ runtime/ examples/ public/ tests/ pyproject.toml` is empty on every path, and so is the diff over `tools/lints/citations.py` and all eleven `human_verification` records. `make ci` exit 0 on all six legs at the merge commit — `test` **4105 passed / 118 skipped**, byte-for-byte the wave-1 baseline, which is the mechanical proof `D-05` held; `gate-tools` 406 + 205, up from 406 + 154 at the phase's start; the ledger module is **51** tests. **THREE BLOCKING FINDINGS AT CLOSE, ALL FIXED IN-PHASE, EACH WITH A STANDING CONTROL WATCHED GO RED**, and two of the three were found INDEPENDENTLY BY TWO PANEL REVIEWERS: `B-1`, a misspelled pathspec and a clean tree are the same string, so a one-key typo made any emptiness assertion vacuous while `CONTROL A` and `CONTROL 13` watched a different constant — proven both ways, `TESTS_TREE → tests-typo/` is 45 passed all green against the wave-6 module and 2 failed against the fix; `B-2`, no standing check required a verdicted row to cite anything at all, which is exactly how `DCD-02` survived five waves; `B-3`, a gap named in a wave hand-off never reached `21-FINDINGS.md`, the document Dave rules from — recorded, not closed (`D-11`). **THREE FINDINGS REJECTED and recorded AS REJECTED with the refuting evidence**; **seven advisories carried**, Dave ruling no action at gate. **Dave ruled three times at the sitting**: `D-IMPL-175` accepts the eighteen-row Phase 16 split as written and keeps `DOCS-18` limb 1 closed; `D-IMPL-176` keeps all five `Not built` rows on the work list, sequences the knot (`DOCS-15` first; replacements before removals; the `00`–`08` half of `D-27` still his) and **frees the `s3-` naming scheme — Phase 16 is not resumable and the obligation is the content, not the old section label**; `D-IMPL-177` settles the `All **42**` counter as the milestone-scoped count through 15.1, corrected in one line. `RECON-09` was amended `Partial` → `Complete` only AFTER the gate entry existed. **Execution record follows.**  The contract is the FOURTEEN Success Criteria above, authored one-per-unwrapped-line before Wave 1 and amended twice on Dave's rulings; nothing here is graded against anything else. **All 54 not-`Complete` rows carry a verdict** — 38 `Complete`, 2 `Complete as ruled`, 9 `Partial`, 5 `Not built`, 0 `Orphaned` — and **the phase's own ten `RECON-` rows carry verdicts too, written in wave 6 BEFORE the close panel** so the ledger Dave approves is the ledger the panel reads: eight `Complete`, and `RECON-09` and `RECON-10` `Partial` with the outstanding limb named on each. Zero `Pending` remains anywhere in the ledger. **Two things are DEFERRED TO DAVE and are not an executor's to close:** Phase 16's eighteen rows, reported as a two-sided split in `21-DOCS-16-SPLIT.md` and left unflipped and undropped (`D-12`), and the five-row work list whose four-row knot cannot be sequenced apart (`D-11`). **Two counters corrected, one reported rather than guessed:** `Coverage: 94/94` → `143/143`, the Phase 21 entry's `52` → `54` at three sites, and §Coverage's `All **42**` reported under `D-19`(a) because the parse cannot settle what the sentence means. **The completeness gate is standing** and has been watched go red: the module is 45 tests, `gate-tools` 406 + 199, and CONTROL 15 was added because a specified sabotage reported GREEN for a measured reason. `src/`, `runtime/` and `tests/` are diff-empty against the pinned base. **The phase does NOT close without `D-GATE-21`.** **Wave 5 landed 2026-08-22** (`21-05`, two task commits `eedeefb`, `587ff78`). **`21-FINDINGS.md` IS THE DOCUMENT DAVE RULES FROM** — five sections and nothing else. The census across the 54, by strict parse at writing time: **38 `Complete`, 2 `Complete as ruled`, 9 `Partial`, 5 `Not built`, 0 `Orphaned`**; two-thirds of the ledger's outstanding debt was work that had already shipped and was never ticked. **The work list is five rows in two groups, and four of them are one knot** — `DOCS-17`, `CLNT-17`, `DOCS-14` and `EXAM-02` cannot be sequenced apart, because the replacements have to exist before the condemned trees can go and the condemned trees are where the replacements' subject matter currently lives; `DOCS-15` stands nearly alone and is the cheapest with the highest adoption leverage. Nothing on it was built (`D-11`). **All 27 `human_needed` items across 11 records are named, quoted verbatim and shown untouched mechanically**, the roster re-derived by parsing every `.planning/phases/*/[0-9]*-VERIFICATION.md` for a `human_verification:` block — 16 files match the glob, 11 carry it. The **24-vs-27 delta and its cause are stated**: `gsd-sdk query audit-uat` filters on frontmatter `status:` and loses Phase 12 (`status: passed`, 1 item) and Phase 18 (`status: gaps_found`, 2 items) — this phase's own subject a third time, in a third tool; named, not fixed (`D-20`). **Two counters corrected, one reported rather than guessed:** `Coverage: 94/94` → `143/143` with the running totals extended; the Phase 21 entry's `52` → `54` at three sites with Phase 15.5 and 15.6 added to a lane list that did not sum to its own count; and **`All **42**` REPORTED, NOT CORRECTED** under `D-19`(a), because the sentence claims to be the table's row count while the paragraphs beneath it enumerate a defined subset summing to exactly 42 — the parse cannot settle which it means, and a ruling closes it. **Every counter's location was re-resolved at execution time and one had moved 38 lines**: `D-19` cites the `Coverage:` counter at `:423` and it is at `:461` — the phase's own ruling carrying a stale line citation while the phase was being executed. No GSD state or roadmap writer was invoked (`D-15`); both files were backed up, hand-edited, and diffed. `roadmap.get-phase 21 --raw` re-parses to **14** criteria AFTER the hand-edit. No test written (`D-05`); `gate-tools` unmoved at 406 + 189. **Wave 4 landed 2026-08-22** (`21-04`, three task commits `624ab9f`, `6fb22fd`, `b00d529`). **ALL 54 ROWS NOW CARRY A VERDICT IN BOTH CHANNELS**; the only rows still reading `Pending` are this phase's own ten `RECON-` rows, which are `21-06`'s. The Phase 16 lane's eighteen `DOCS-` rows are reported to Dave as `21-DOCS-16-SPLIT.md` — **ten `Complete`, five `Partial`, three `Not built`, zero wholly `Orphaned`** — with one orphaned LIMB, inside `DOCS-18`, whose no-fabric-change assertion `D-IMPL-96` revoked in Dave's own words. **The thin side-C pile is the finding, not a failure of the audit:** `RETIRED.md` retires the APPROACH and not the NEED, so an obligation about a need survives, and only the machinery of the rejected approach died with it. **Eight rows had in-phase or later-phase work the ledger never recorded** — `DOCS-19`..`21` and `DOCS-23`..`25` shipped in Phase 16's own post-stop plans, and `DOCS-13`'s three harness legs shipped in Phase 20, gated harder than the row asked (`ccf` is refused BY NAME, not merely absent from a permitted set). **`DOCS-17` is blocked on Dave, not on an executor:** `D-IMPL-145` limb 2 quarantined `examples/00`–`08` deliberately and plan `17-08` returned the `00`–`08` half of `D-27` undecided; re-measured here rather than carried, the cost is **111 references across 15 published pages, 102 of them snippet includes**, unmoved. **A SABOTAGE THAT REPORTED GREEN AND SHOULD NOT HAVE:** re-aiming `D-IMPL-94`'s citation from `docs/DECISIONS.md:352` to `:356` left `--citations` at exit 0, because `D-IMPL-96` CROSS-CITES `D-IMPL-94` in its own body — an anchored line citation into the decision log is weaker than it looks, and a control aimed at a cross-citing neighbour proves nothing. Re-aimed at `:354`, `cite02-anchor` went RED in both channels. Nothing retired, nothing built: all nine of `examples/00-quickstart` through `08-e2e-demo` are still in the tree and the pinned-base fence over `src/ runtime/ examples/ public/ tests/ pyproject.toml` is empty. No test written (`D-05`); `gate-tools` unmoved at 406 + 189. **Wave 3 landed 2026-08-22** (`21-03`, three task commits `16b6fe2`..`73bc457`). **36 of the 54 rows now carry a verdict in BOTH channels**; the 18 that do not are ALL the Phase 16 lane and are `21-04`'s. The 14 added: `HARD-01`..`03`, `EXAM-01`..`03`, `DOCS-01`..`06`, `CPS-03` and `DCD-02` — 9 `Complete`, 1 `Complete as ruled`, 3 `Partial`, 1 `Not built`. `CPS-03` takes `Complete as ruled` per `D-IMPL-173`, citing BOTH `D-IMPL-113` and `D-IMPL-121` with the *by design, not by omission* clause, written into all **three** places the row is stated — the CPS-lane evidence table still read `Pending by design` and is not parsed by `traceability_rows`, so nothing mechanical would have caught it. **The documentation lane was not the citation problem wave 2 forecast:** all six Phase 14 rows took `D-17` route 1 and cited a guarding test, so route 2 went unused there — Phase 14 shipped pages PLUS a gate per claim, and gates are Python. Route 2 was spent where the evidence genuinely is a ruling, and **every anchored line citation was run through the shipped `_anchor_verdict` and required to return `True` rather than `None` before it was written**, then one was mis-aimed and watched turning `cite02-anchor` red. `EXAM-02` is the wave's one `Not built`, named to four checkable absences and classified `Not built` rather than `Orphaned` because `RETIRED.md` retires the approach and not the need. Two named gaps carried to `21-05` that are NOT `Not built` rows: `DOCS-06`'s unwired CI wiring (no test reads the `ci` target or the workflow) and `DOCS-03`'s six uncovered artifact classes. No test written anywhere (`D-05`); `gate-tools` unmoved at 406 + 189, which is the proof. **Wave 2 landed 2026-08-22** (`21-02`, three task commits `1a7a8b6`..`6fa56f4`). **22 of the 54 rows now carry a verdict in BOTH channels** — `CLNT-01`..`CLNT-22`, zero `Pending` left in that lane: 21 `Complete` (`CLNT-05` `Complete as ruled`, against `D-IMPL-157`) and `CLNT-17` **`Not built`**, its absence named to four surviving artefacts rather than asserted. Every citation is a full repo-relative `path.py::symbol` that resolves, and every one names the guarding test (`D-04`); no test was written under `tests/` and none was written to manufacture a name (`D-05`). The **zero-CITATION vacuity guard** `21-01` withheld landed here, immediately after the first eight citations existed and in the same commit — relocated, never weakened — with its precondition and `CONTROL 5b`, all watched red against the shipped function. Measured and carried forward: `.github/workflows/ci.yml:NN` is UNUSABLE as a status-cell citation (the lint's path group refuses a leading dot), which the documentation lane will feel harder. **Wave 1 landed 2026-08-21** (`21-01`, six commits `c51406b`..`845da98`). The CI `docs` job's shallow checkout is fixed, the diff base is pinned at `c51406b`, `D-IMPL-172`/`173`/`174` are logged, the phase's own `RECON-01`..`10` rows are minted `Pending` in BOTH channels (table 133 → 143 rows), and `tools/docs_tests/test_requirement_ledger.py` ships 33 tests — eleven numbered controls plus two positive twins, every mutation watched RED against the shipped function. No verdict written yet. **Planned 2026-08-21** — commissioned by Dave at the Phase 20 close. 54 not-`Complete` rows get a verdict backed by evidence; Phase 16's eighteen are reported as a split and ruled by Dave, not by the executor. Fourteen Success Criteria authored one-per-unwrapped-line BEFORE execution per `D-GATE-19`, AMENDED at the 2026-08-21 discuss session (the original ten gated against a miscount of 52 and a three-verdict vocabulary Dave overrode). No fabric change. Adjacent gap already ruled and not this phase's work: `D-IMPL-171` | 2026-08-22 (`D-GATE-21`) |
| 21.1. The Guard That Did Not Guard — Closing the Check-Vacuity Class | 10/10 | **Complete** — **`D-GATE-21.1` APPROVED by Dave 2026-08-23**, logged at `docs/DECISIONS.md:532` with `D-GATE-21` BYTE-IDENTICAL (verified by sha256 of its line, not by reading it) and `docs/DECISIONS.md` append-only across the gate commit: 12 insertions, ZERO deletions. **Wave 10 landed 2026-08-23** (`21.1-10`, nine commits `d478d06`..`e3c6c6d`) — the CLAUDE.md §3.1 close in its order. **THE PANEL FOUND FOUR MORE INSTANCES OF THE PHASE'S OWN DEFECT CLASS, ALL FOUR INSIDE THE MACHINERY BUILT TO CLOSE IT, AND ALL FOUR ARE FIXED IN-PHASE.** gemini, codex and cursor read the SHIPPED tree per `D-IMPL-178` — 553 KB / 8,272 lines INLINED rather than pointed at by path, the payload's omissions NAMED — briefed on the known defects and told to report what is ADJACENT. Reviewers converged from four directions on ONE thing: **`RR-1`'s fix quantifies PER MEMBER and the controls vouching for it quantified PER CONSTANT.** Each proven by SABOTAGE against the shipped module, never by argument: `fabric_diff` degraded to validate only the two ends left **all 94 tests GREEN** (nine of `UAT_RECORDS`' eleven members watched by nothing); `CONTROL A` narrowed to the first member left **all 94 GREEN**; a `VAC-07` row minted in BOTH channels with an unevidenced `**Complete**` and never rostered was named by **ZERO of EIGHT gates** — `RR-3`'s mechanism on the roster of the phase whose subject `RR-3` is; and `_index()` accepted an index thinned from **5,073 basenames to 1** so long as it kept the anchor, after which `refuse_unresolvable` returned `[]` over the real ledger. Closed by `CONTROL 41`, `CONTROL 38b`, `CONTROL 42` with `derived_phase_own_roster`, `_index.thinned_index` with `CONTROL 43`, and `dispatcher_bypasses` widened to bare raises and `async def` with `CONTROL 44` — five new controls, every one REGISTERED in `CONTROL_AIM` so the meta-controls hold it too. **A CLOSE FIX REGENERATED THE PHASE'S DEFECT CLASS AND THE MACHINERY CAUGHT IT IN SECONDS**: adding `_index.thinned_index` made `CONTROL 22` — asserting a substring BOTH limbs satisfy — go GREEN with the limb it names neutered, and `CONTROL 35` reported it by name; `CONTROL 22` now asserts the limb id. **A RED FOR THE WRONG REASON NEARLY PASSED FOR A CAUGHT DEFECT** inside the verification of a finding about exactly that: the first sabotage reddened the suite via an unrelated `IndexError`, and taken at face value the blocking finding would have been filed REJECTED. **FIVE FINDINGS REJECTED AND RECORDED AS REJECTED** with their refuting evidence — one of them caused by the executor's own brief paraphrasing `D-IMPL-123`'s ceiling scope loosely, named as such. 22 panel findings plus 9 from the additive single-agent review; every citation resolved individually; no reviewer failed to review. **THREE ROWS AMENDED, EACH AFTER THE GATE ENTRY EXISTED AND NOT BEFORE** (the `RECON-09` discipline): `VAC-05` `Partial` → `Complete` with its tick, `VAC-03`'s Dave-only limb closed by `D-IMPL-183`, and `VAC-06`'s "56 aim proofs" dated to wave 7 as read-by-no-assertion rather than re-measured to 72 — a present-tense count in prose no gate reads is `D-21`'s subject outside code. `DOCS-22` amended AND rostered per ruling 2, one row only, with `CONTROL 45` proving the rostering is not decorative. **CI exit 0 on all six legs**: lint 0; typecheck 0 over 211 files; `test` **4105 passed / 118 skipped**, byte-for-byte the `D-GATE-21` baseline; `gate-tools` 406 + 266; eleven examples; `docs-strict` strict-built. **The test leg ran as THREE pytest invocations, not one**, because background runs were terminated twice at 68% — every directory covered, total on the known baseline, and recorded rather than glossed. Fence diff EMPTY on every path; only `tools/docs_tests/test_requirement_ledger.py` written under `tools/` (`D-11`). Module 51 → **112**; `CONTROLS` 63; `LIMBS` 36. **CARRIED, NOT CLOSED** (`D-IMPL-185`, `D-IMPL-187`): `R-α`, `A-7`, `RR-5`/`RR-7`/`RR-8`/`RR-10`, `A-1`..`A-8`, and the scalar `Aim.kind` — the most substantive residual, since a control spanning two kinds can declare only one. **Wave 9 landed 2026-08-22** (`21.1-09`, four commits `6c38d7a`, `5239623`, `6fe2ef1`, plus the metadata pair). **THE PHASE'S OWN SIX ROWS ARE VERDICTED IN BOTH CHANNELS, BEFORE THE CLOSE PANEL, AND `PHASE_OWN_ROSTER` NOW GATES THEM** — five in the Complete family and one honest `Partial`. **`VAC-05` reads `Partial`** because criterion 11's second half is a phase record not closed until `D-GATE-21.1` exists, and Dave writes that; amended after, exactly as `RECON-09` was. **`VAC-06` reads `Complete as ruled`** naming `D-IMPL-181` AND `D-IMPL-182`, because the row as written admits TWO dispositions and the shipped module needs THREE. **`VAC-03` is the first row in this ledger to cite a `.planning/` document** — the shape that had NO legal spelling until wave 3's `LOOSE_CITATION` and could not satisfy the subsumption gate until wave 5 closed `RR-11`; it extracts with the leading dot intact, produces no truncated twin, resolves clean and leaves the gate empty, and every line anchor was re-resolved and READ at write time. Verdicts written FIRST and the roster extended AFTER in ONE commit: a roster extension landing first makes four gates true-only-later and ships a red module. Five sabotages watched refusing BY NAME over the new roster members. **`make ci` HAD BEEN RED SINCE WAVE 4 AND NO WAVE SAW IT** — waves 4–8 each recorded `tools/docs_tests`, `gate-tools` and `tools.lints --all`, and none ran the gate. `test_the_unanchored_python_citation_population_cannot_regrow` was failing on two citations wave 4 wrote in the `path.py:LINE` form, against `D-IMPL-114`'s `path.py::Symbol` rule and `D-IMPL-123`'s ceiling of ZERO. **Criterion 10's own subject arriving inside the plan that owns criterion 10: a gate nobody runs is a gate that cannot fail.** Fixed by CONVERTING both, not by raising the ceiling. **THE `D-21` SWEEP IS A STANDING CHECK NOW, NOT A GREEN GREP RECITED NINE TIMES** — `carried_counts(source)` runs in `gate-tools` → `ci-core` → `ci` and carries a SECOND limb the grep never had: no fixed set may be compared by LENGTH, which covers the grep's own hole (`len(LIMBS) > 0` is invisible to it, a single digit and no `=`). Watched finding TWO planted counts in the real module file, named by line and by roster, green again on removal. `CONTROL 39` (guard, 2 targets) and `CONTROL 40` (limb, 3 targets) registered, enumerated and aim-proven; every red the control's own `AssertionError`; `CASCADING_REDS` still frozen EMPTY. **THREE INSTANCES OF THE PHASE'S OWN DEFECT CLASS FOUND IN THIS WAVE'S OWN WORK BEFORE THE SUMMARY**: `FIXED_SETS` written as a transcription shipped MISSING TWO, including the sweep's own `CARRIED_COUNT_SHAPES`, found by writing the enumeration and diffing it; `CONTROL 39`'s first draft named `LIMBS` inside a `len(...)` in its own body and the standing sweep caught it on line 6665; and `CONTROL 40` written with `pytest.raises` produced a `Failed`, not an `AssertionError`, so `CONTROL 35` scored its neutered red a CASCADE. **CRITERION 11 MEASURED, NOT ASSERTED**: the table at the `D-GATE-21` merge `f60e186` parsed by the shipped strict parse and compared cell-for-cell against today — **NOT ONE of the 54 moved**, in cell text or verdict token; only `DOCS-22` (outside the 54, verdict unchanged) and the six new rows. `D-GATE-21` unamended, verified by content hash. **`make ci` EXIT 0 ON ALL SIX LEGS**: lint 0, typecheck clean over 211 files, `test` **4105 passed / 118 skipped** byte-for-byte the `D-GATE-21` baseline (the mechanical proof `D-05` held), `gate-tools` 406 + 248 (205 at the phase's start), eleven examples, `docs-strict` strict-built. Module 51 → 91 → **94**. Coupling report regenerated LAST, after the SUMMARY commit — NO DIFF, so no report commit; the committed report is current and its `.planning/REQUIREMENTS.md` row reads 99 couplings before and after; pinned-base fence empty on every path; `D-15` honoured with 8 frontmatter keys and 15 Success Criteria intact. **RESIDUALS NAMED, NOT CLOSED**: `R-α`, advisory `A-7`, and the carried `RR-5`/`RR-7`/`RR-8`/`RR-10` and `A-1`..`A-8`. Open for Dave: `DOCS-22`'s verdict, six criterion readings, and `D-GATE-21.1` itself. **Wave 5 landed 2026-08-22** (`21.1-05`, four task commits `9d22684`, `ca26de7`, `4ca1bbf`, `9360865`). **`RR-11` CLOSED under `D-IMPL-180` — the gate that forbade its own pattern.** `test_each_widened_pattern_subsumes_the_lint_pattern_it_replaced` compared path STRINGS, so a dotted citation's correct `.planning/…` match was scored a SILENT DROP against the lint's truncated twin `planning/…` — which it COVERS. Re-measured: lint `CITATION` → `planning/REQUIREMENTS.md` at `(11, 37)`, `LOOSE_CITATION` → `.planning/REQUIREMENTS.md` at `(10, 37)`; as PATH STRINGS the twin is "missing", as SPANS nothing was lost. The predicate is now `uncovered_lint_citations(document, lint, widened, name)` taking its subject as an ARGUMENT, with **the anti-vacuity clause moved INTO it** so a control can watch it refuse. `CONTROL 23b` — a letter suffix, not 24, which belongs to wave 6 — committed BEFORE the fix and watched RED (1 failed / 65 passed at `9d22684`, 66 passed at `ca26de7`), carrying FOUR limbs because three weaker implementations pass fewer than four — including **the substring trap**, where a lint path that is a SUBSTRING of an unrelated widened path is still a drop. Verified on the REAL ledger: the `.planning/` citation wave 4 had to withhold now extracts, resolves and leaves the gate empty; `D-07` intact. **`VAC-06`'s MACHINERY — the generator of the vacuity class.** `_refuse(limb, message)` is the one dispatcher every refusal raises through, appending `[limb:<id>]` so every existing control keeps passing UNAMENDED on the substring it already asserts; `LIMBS` is a frozen roster of NAMED `<function>.<branch>` ids asserted by MEMBERSHIP and never by length (criterion 9); `neutered(limb)` turns ONE limb off for a block and restores in a `finally`. **The switch is guarded three ways, all STANDING rather than one-off so waves 6–8 can aim controls at them:** an autouse fixture asserting `neutering_switch_offenders()` empty after EVERY test, a standing at-rest test, and `_require_registered` deliberately NOT a limb and NOT routed through `_refuse` — a guard on the switch that can disarm every other guard must not itself be disarmable. A source-level `ast` test holds three properties: no `raise AssertionError` outside a test body or the dispatcher, every `_refuse` id registered AND prefixed with its enclosing function, and every registered id has a site — **an id with no site is the mirror of a site with no id**. Measured bijective: 31 limbs, 31 sites. **THE THREE DISPOSITIONS, ALL NAMED (criterion 12).** REMOVED: `refuse_unresolvable`'s zero-row limb, structurally dead because `traceability_rows` refuses the same input one function earlier, its id out of `LIMBS` in the same commit, suite green after the deletion exactly as research measured. REPAIRED: `base_ledger_text(base=None)`, so the shallow-clone guard — a CI failure this project hit for REAL at the Phase 20 close — is reachable rather than deleted, per `D-IMPL-179` limb 2; every call site unchanged. KEPT: `uncited_verdicts`' empty-roster limb — **research classified it unreachable and that classification is WRONG**; no production caller passes an empty roster but a CONTROL can, which is the distinction between a limb no INPUT can reach and a limb no CALLER happens to reach. Both get controls in `21.1-06`; both probed reachable here. **`CONTROL 5` RE-AIMED, and what let the mis-aim survive was the ASSERTION, not the docstring:** `"no rows"` appears in BOTH limbs' messages, so measured before the removal, with the upstream limb neutered the DOWNSTREAM one caught the same subject and the control stayed GREEN over an entirely different refusal. It asserts the LIMB ID now and goes RED under `neutered("traceability_rows.zero_rows")` — **the first time in this module's life a control has been proven to reach the limb it names** (criterion 13's shape, which `21.1-07` generalises). Nine sabotages watched red against the SHIPPED module, each reddening exactly its own guard. Module 65 → 68 tests, `tools/docs_tests` 176 → 179, `gate-tools` 406 + 219 → 406 + 222 with no `Makefile` edit, `tools.lints --all` exit 0, `D-21` sweep exits 1, pinned-base fence empty on every path, and the ONLY file written under `tools/` is the ledger module itself. **Wave 4 landed 2026-08-22** (`21.1-04`, two task commits `fa2512d`, `c874aed`; DOCUMENTS ONLY, no code and no module write). `RR-3` CLOSED (criterion 5): the ledger carries NINETEEN Phase 16 `DOCS-` rows and `21-DOCS-16-SPLIT.md` ruled on EIGHTEEN, with `DOCS-22` appearing ZERO times there and ZERO times in `21-FINDINGS.md` — it lived only in plan `21-04`'s PLAN and SUMMARY, which is `B-3` again. **The MECHANISM is the finding and it was not an oversight:** the split was built from the 54-row WORKING SET, whose predicate is *verdict not in the Complete family at the pinned base*, and `DOCS-22`'s cell read a bare, unbolded, UNCITED `Complete` — so it was in the family, never entered the working set, and never reached the split. Measured: lane minus working set == `['DOCS-22']`, and the split's eighteen are the lane's eighteen working-set members exactly. **An unevidenced `Complete` bought exemption from the audit that would have checked it.** The lane roster is now stated as NINETEEN NAMED ids re-derived by parsing the ledger with its derivation on the page (`D-21` — a count cannot see an absence or a swap); roster == table == sections == the ledger's Phase 16 `DOCS-` ids, ID FOR ID. Totals re-derived from the amended table — eleven `Complete`, five `Partial`, three `Not built`, old figures beside new — the one moved figure moving by ADDITION, not by re-verdicting. `DOCS-22` measured against the tree rather than read off the ledger: **`Complete`**, both limbs of `D-IMPL-135` — the `audiences` axis at `src/ccf/products/contract.py::audiences` with EIGHT named assertions gating it per property, the load-bearing one holding the values OPAQUE to every module outside `contract.py`; and all three parts of the surface obligation with live referents, the `_SHAPE_MOVED_BY_FRAGMENT` claim keyed to `register_product_class` and NOT to `ProductDiscovery` because `D-IMPL-138`(c) ruled measure-don't-pre-decide and a `contract`-kind export's shape move surfaces transitively. The absence is NAMED (`D-10`): no product-catalog door, out of scope by Dave's own deferral rather than owed. **The ledger cell amended under `D-IMPL-179` limb 1 — ONE row, two lines** (`:47`, `:341`), `DCD-10` shape in BOTH channels, tick unmoved because the verdict was and stays in the Complete family; the other 78 `A-5` rows untouched, `D-GATE-21` and `D-IMPL-175` both unamended, the nineteenth row carried as a NEW ask under its own heading. Citations 127 → 132; before the amendment the row carried NO citation, so no gate had anything to check about it. **A NEW BLOCKING FINDING, `RR-11`, and it blocks wave 9:** being the first to actually USE wave 3's `LOOSE_CITATION` showed that a `.planning/` line citation extracts and resolves exactly as built — and REDDENS `test_each_widened_pattern_subsumes_the_lint_pattern_it_replaced`, whose subsumption predicate compares path STRINGS, so for a dotted path the lint's truncated twin `planning/…` at offset 669 is scored a silent drop against the widening's `.planning/…` at 668. **The check cannot be satisfied by the shape `LOOSE_CITATION` exists to admit** — wave 3 shipped the pattern and a gate forbidding its use, and neither was observed because no dotted citation existed. NOT fixed here: wave discipline serializes module writes and control numbers 24+ are allocated to waves 5–8. `VAC-03`'s verdict at `21.1-09` needs a `.planning/` citation, so it must close before wave 9. `tools/docs_tests` 176 passed unmoved, `tools.lints --all` exit 0, coupling report regenerated LAST with no diff, pinned-base fence empty on every path. **Wave 3 landed 2026-08-22** (`21.1-03`, four task commits `58bd861`, `4ce0c95`, `d527c3a`, `9448ffa`). `RR-4` CLOSED (criterion 6): a repeated requirement id is refused BY NAME in BOTH parsers, independently. Pre-fix, `HARD-02`'s row duplicated under `Phase 99` with its citations intact parsed to 150 rows holding the id TWICE while `channel_disagreements`, `vocabulary_offenders`, `doubled_verdicts`, `unverdicted(working_set)`, `uncited_verdicts` and `refuse_unresolvable` ALL returned empty — and in the checkbox channel the dict kept the LAST bullet and resolved the row to `False`. The refusal lives in the PARSERS because FOUR dict builds plus TWO comprehensions read `traceability_rows`; **the `D-GATE-21` re-run record's claim of two dict builds at `:779` and `:1648` is wrong on both the count and the line numbers** and the correction is recorded. `uncited_verdicts` APPENDS rather than collapsing, so a duplicated row's citations MERGE and an uncited duplicate is masked by its cited twin — closed upstream by the parser refusal. Both refusals NAME every repeated id; `len(rows) == len(set(ids))` was deliberately not written (criterion 9). `RR-6` CLOSED (criterion 7): `_index()` refuses unless it resolves `INDEX_ANCHOR = src/ccf/client/client.py`, a NAMED path the module already cites — stronger than refusing an empty mapping, which ACCEPTS a THINNED index, and thinned is the shape that makes the moved-path branch go silent while the ambiguity branch is guarded only by `CONTROL 1` happening to assert the word AMBIGUOUS. **The plan-check blocker is closed: a `.planning/` document could not be cited AT ALL.** The lint's `CITATION` opens its path group `[A-Za-z0-9_]`, excluding `.`, so `.planning/REQUIREMENTS.md:1` extracted `planning/REQUIREMENTS.md` — one character late, a path not in the tree — while the `::symbol` spelling is refused as non-Python. Module-local `LOOSE_CITATION` **REPLACES** `CITATION` in the extraction tuple rather than joining it: measured, a widened pattern carried beside the lint's extracts the citation TWICE in EITHER order, because the dedup is a `set[str]` over the path STRING. `D-07` intact — the lint is byte-identical. **Bound reproduced: 127 citations before and 127 after, set-equal AND order-equal, zero added and zero dropped**, and `refuse_unresolvable` over the real ledger still returns `[]`. `NODE_ID` was dropped only after its subsumption by `LOOSE_NODE_ID` was PROVED by set equality of the `(id, path)` pairs — 213 = 213. **A control beyond the plan, and the plan's 'remove the now-dead import' step declined with a reason:** `test_each_widened_pattern_subsumes_the_lint_pattern_it_replaced` keeps both lint patterns imported as the reference it measures against, because the REPLACEMENT opens a fresh vacuity hole — once the tuple stops consulting the lint's patterns a later narrowing drops citations SILENTLY and the non-emptiness precondition carries no count and cannot see it. Sabotage 7 shipped a `LOOSE_CITATION` requiring the leading dot: **`CONTROL 23` stayed GREEN** and only this check went red on the module's own machinery. Controls committed BEFORE their fixes and watched failing (`D-IMPL-170`, criterion 8): 3 failed / 60 passed at `58bd861` → 63 passed at `4ce0c95`; 2 failed / 63 passed at `d527c3a` → 65 passed at `9448ffa`. Seven sabotages watched red against the shipped module, each reddening exactly its own control. Module 60 → 65 tests, `gate-tools` 406 + 214 → 406 + 219, `tools.lints --all` exit 0, `D-21` sweep exits 1, pinned-base fence empty on every path. **Wave 2 landed 2026-08-22** (`21.1-02`, two task commits `3c8908e`, `5de6857`). `RR-2` CLOSED: `cell_verdicts` returns the SET of verdicts a cell asserts — the leading token unioned with every bolded vocabulary run — and BOTH `doubled_verdicts` and `roster_rows_with_two_verdicts` consume it, so the ledger-wide gate and the gate the working set is actually held to cannot drift apart (criteria 3 and 4). Pre-fix, `HARD-02` doctored to `Complete — later **Partial** (…)` with its citations intact passed EIGHT gates with ZERO refusals while `verdict_token` still read it `Complete`; post-fix both gates refuse it by name and name the verdicts `['Complete', 'Partial']`. **The rule was chosen by MEASURING three candidates across every real row and the other two are traps:** the union flags ZERO rows — so this fix required NO ledger edit and criterion 11's exception clause is unused on this axis — while *"any vocabulary word anywhere"* flags THIRTEEN including `DCD-02`, `DCD-09`, `DCD-10`, `CPS-03` and `EXAM-02`, all ruled on by Dave, and *"the leading verdict must be bolded"* flags SEVENTY-FIVE, roughly half the table. `verdict_token` is UNCHANGED. Controls committed at `3c8908e` BEFORE the fix and watched failing 2 / 58, green 60 / 60 at `5de6857`, both runs verbatim in the SUMMARY (`D-IMPL-170`, criterion 8). A second control, `test_the_two_one_verdict_gates_read_the_same_predicate`, asserts BY SOURCE that both gates call the shared predicate and neither reads `BOLDED_RUN` — sabotage 3 gave the roster gate its own currently-equivalent copy of the union rule and only that control went red, which is the drift `CONTROL 19` cannot see. **Residual `R-α` is stated OPEN, not closed:** both verdicts unbolded is a wider shape than criteria 3 and 4 name and every stronger predicate measured flags ruled rows. Module 58 → 60 tests, `gate-tools` 406 + 212 → 406 + 214, `tools.lints --all` exit 0, `D-21` sweep exits 1, pinned-base fence empty on every path. **Wave 1 landed 2026-08-22** (`21.1-01`, three task commits `1241ccd`, `58465f7`, `389fbf4`). `RR-1` CLOSED: `fabric_diff` quantifies its pathspec refusal PER MEMBER and NAMES the offender, so `fabric_diff(base, ("scr/", "runtime/"))` raises instead of returning `''` — criterion 1. `CONTROL 18` carries `FABRIC`, `FENCE` and `UAT_RECORDS`, mutating exactly ONE member per case at BOTH ends of the tuple, over a `MULTI_MEMBER_PATHSPECS` roster DERIVED by set equality on names from the module's own arity rather than transcribed — criterion 2. **`CHANGED_TREE` is single-member; the `D-GATE-21` re-run record's claim that it is multi-member is WRONG** and the correction is recorded at the constant. Controls committed at `58465f7` BEFORE the fix and watched failing 7 / 51, green 58 / 58 at `389fbf4`, both runs verbatim in the SUMMARY (`D-IMPL-170`, criterion 8). Three further sabotages watched red: `paths[:1]` reddens every `-last` case, `paths[-1:]` every `-first` case, and `TESTS_TREE → ("tests-typo/",)` reddens the `tests/`-untouched assertion that was 45 green pre-`B-1`. The six `VAC-` rows are minted `Pending` in BOTH channels in one commit with the `Coverage:` counter RE-DERIVED by the shipped strict parse, `143/143` → `149/149`. No count is carried in any new check (`D-21`); the sweep `grep -nE "== *[0-9]{2,}|len\(.*\) *[=!<>]= *[0-9]"` exits 1 on the module. Module 51 → 58 tests, `gate-tools` 406 + 205 → 406 + 212, `tools.lints --all` exit 0, pinned-base fence empty on every path. **Planned 2026-08-22** — 10 plans in 10 serial waves against `VAC-01`..`VAC-06`; four defects in the fourteen criteria found at planning and carried to the gate rather than settled, plus one blocker found at plan-check (`VAC-03` had no legal citation spelling) and closed in wave 3. Revised twice on 2026-08-22 after the plan checker. First: `CONTROL_AIM` carries a SET of aim targets, not one, because `CONTROL C` covers two limbs and `CONTROL A` four constants — single targets would have let a control satisfy its registry entry while remaining unproven, which is `RR-9` inside the meta-control built to end `RR-9`. Second: the prescribed `.planning/` citation mechanism extracted the citation TWICE in either pattern order, so the extractor now carries ONE pattern per shape rather than a widened pattern beside the lint's; `guard` became a fifth aim kind because `meta` would have left the two controls holding this phase's own switch-guards registered, enumerated and aim-unproven; a frozen `CONTROLS` roster stops the enumeration dropping a control in silence; and seven `-k` selectors left stale by the renumbering — each matching a real, already-green test and therefore exiting 0 — were re-pointed and given a per-task selector proof **Wave 6 landed 2026-08-22** (`21.1-06`, three task commits `b231dd9`, `fcd8eb3`, `aa729d6`). **CRITERION 12 CLOSED FOR EVERY LIMB AN INPUT CAN REACH.** Fourteen controls, `CONTROL 24`–`33` plus `27b`, `27c`, `28b`, `31b`, each watched RED with its own limb neutered against the SHIPPED module and GREEN with the limb intact — the reading criterion 8 takes for a refusal that already ships, because there is no fix to be red against and neutering one NAMED branch is stronger evidence than a pre-fix run. **RESEARCH UNDERCOUNTED BY TEN.** Its table B named eight unfalsified refusals out of the twenty branches it inventoried; re-run across all THIRTY registered limbs — one neutered at a time, the whole module re-run each time — EIGHTEEN went unnoticed. The ten extra are wave 5's own additions and are almost all in the CONTROL FIXTURES, the mutation helpers every other control depends on to have mutated the thing it claims to have mutated. **`CONTROL 32` and `CONTROL 33` hold the two mechanisms this phase itself built that can disarm everything else** — the dispatcher's unregistered-limb guard in both directions, and the `_NEUTERED` off-switch, whose restore is watched surviving an exception raised inside the block and whose fixture predicate is watched REPORTING a deliberate leak. Both are STANDING tests carrying their saboteur under `SABOTEUR:` for `21.1-07` to lift into `CONTROL_AIM` under the `guard` aim kind. Three saboteurs on those two mechanisms and one on the moved-path branch each reddened EXACTLY their own control and nothing else. **`RR-12` OPENED, and it blocks `21.1-07`'s coverage assertion:** four limbs are reachable ONLY with a sibling limb neutered — `_duplicated_table_row.twin_identical` and all three `_duplicated_checkbox_bullet` limbs — because they are DEGRADATION SHIMS that keep the neutered path from crashing rather than guards any input reaches. Deleting them reinstates the crash wave 5 shaped them to prevent, so they are recorded rather than removed and `21.1-07` needs a third disposition for them. Module 68 → 82 tests, `tools/docs_tests` 179 → 193, `gate-tools` 406 + 222 → 406 + 236, `tools.lints --all` exit 0, the `D-21` count sweep exits 1, pinned-base fence empty on every path, and no ledger row touched. **Wave 7 landed 2026-08-22** (`21.1-07`, four task commits `e8916d4`, `e62c090`, `f1cd3b8`, `6436163`). **CRITERION 13 CLOSED FOR EVERY KIND THIS PLAN OWNS — the GENERATOR of the phase's defect class now has a standing check.** `CONTROL_AIM` carries FIFTY-FOUR entries, one per control, in six aim kinds — 23 `limb`, 18 `guard`, 4 `discriminator`, 2 `shim`, 2 `pathspec`, 5 `meta` — each declaring a FROZENSET of targets rather than one value, because `CONTROL C` covers two limbs and `CONTROL A` four constants and a single-target registry would let either satisfy its entry while remaining unproven for the rest. `CONTROL 34` holds the declaration complete in BOTH directions by set equality on NAMES: every `LIMBS` id claimed by some `limb` or `shim` entry, every claimed id a registered limb, every kind in `AIM_KINDS`, every `pathspec` target a constant `asserted_pathspecs()` resolves, every inverted-obligation entry carrying a saboteur, and `meta` entries carrying NO thunk — which makes their exclusion from every invocation loop structural rather than a filter someone can drop. The enumeration is frozen against a named `CONTROLS` roster, because a predicate that stops matching a control satisfies coverage VACUOUSLY for it while both directions still pass; the four positive twins, named outside the `test_control_` convention, are the standing proof that is not hypothetical. **`RR-12` CLOSED under `D-IMPL-181` and criterion 15 — the shims are PROVEN, not excused.** `CONTROL 27d` and `27e` reach all four shim limbs, fire each BY NAME with its sibling disarmed, then watch the helper degrade SILENTLY when the shim itself is disarmed on top. `_duplicated_checkbox_bullet.twin_identical` is unreachable under EVERY input and every real regex — `twin == line` needs the flipped tick to equal the tick it replaced and the class `[ xX]` admits no such value — so it is reached by substituting a PATTERN OBJECT whose reported group span rewrites to itself, on the idiom `CONTROL 22` and `29` already use. No exempt roster. **FIFTY-SIX AIM PROOFS RUN AS STANDING TESTS**, not probes: `CONTROL 35` proves 27 limb-target pairs across 26 limbs, `36` four discriminators, `36b` twenty-one guard pairs, `36c` all four shims — each per TARGET, not per entry. **EVERY RED WAS THE CONTROL'S OWN `AssertionError`; not one crash anywhere**, and `CASCADING_REDS` freezes that as a NAMED, today-empty roster so a control that starts crashing where it used to assert reddens the run rather than counting as coverage — the property `D-IMPL-181` exists to protect. `CONTROL 32` and `33` took `guard` and not `meta`: filing the two controls that hold the mechanisms which can disarm everything else under a kind excluded from every invocation loop would have left them registered, enumerated and AIM-UNPROVEN. **EIGHT SABOTAGES, each naming its offender and each restored**, including `CONTROL 5` re-pointed at a real limb it does not observe — the historical defect reproduced mechanically and caught in under a second. Module 82 → 89 tests, `tools/docs_tests` 193 → 200, `gate-tools` 406 + 236 → 406 + 243, `tools.lints --all` exit 0, `D-21` sweep exits 1, pinned-base fence empty on every path, no ledger row touched. | 2026-08-23 |
| 22. The Adoption Argument — What RAG, Hand-Rolled Assembly and a Semantic Layer Lack | 6/6 | **Complete** — **`D-GATE-22` APPROVED by Dave 2026-08-23** at `c786faf`; six plans in six serial waves on `main` (no phase branch, `d7a70eb`), 51 commits from the phase base `951eb4a`. Plan `22-06` is the gate-close plan and its deliverable is `22-CLOSE-REVIEWS.md` plus the `D-GATE-22` entry, so five plans carry a `SUMMARY.md` and six executed. The §3.1 close found **eight blocking defects in the phase's own gate** and all eight were fixed in-phase, each watched RED before green. *Counter corrected in Phase 22.1: this cell read `0/5` and `PLANNED 2026-08-23` with an empty completion date after the phase had closed — the checklist entry above was ticked at `783e791` and this row was not.* Originally planned as five plans in five waves, all sequential (the page, the contrast, the gate, the ledger, the proof); no requirement rows minted. **DISCUSSED 2026-08-23** — `22-CONTEXT.md` + `22-DISCUSSION-LOG.md` at `815f810`. Fifteen decisions across four areas in Dave's order. **The fifteen Success Criteria are LOCKED in the entry above, BEFORE planning and BEFORE Wave 1** (`D-GATE-19`). Two rulings shape the phase: `D-02` — every *what the alternative lacks* claim is RECAST as a checkable fact about the QUESTION, because you can include what CCF does and cannot include what RAG lacks, and an uncited *lacks* sentence is `DCD-02`'s class; and `D-04` — **the wording gate SHIPS with the page** (one module, both obligations, `public/`-scoped), reversing the stretch-goal call on a price change once `test_gate_two_wording.py` was found to be the instrument. Dave: *"if the criterion matters, something can go red when it is violated."* Verified before locking: `s1-01/spine.py` already carries the SAME SEVEN marker regions the adopter's guide includes from `00-quickstart` and **nothing has ever included from it**, so the page is a pure `public/` addition with ZERO changes under `examples/`. | — |
| 22.1. The Hygiene Block — The Tool That Could Not Tell "None" From "Could Not Look" | 3/3 waves + close | **Complete** — **`D-GATE-22.1` APPROVED by Dave 2026-08-23.** Six commits on `main` from `589763d`; all nine criteria met, LOCKED before Wave 1 (`D-GATE-19`). The sweep FAILS CLOSED: reproduced 267 → 261 rows at exit 0 under system `python3` before, exit 1 naming the module after; the refusal precedes the WRITE. `RECON-10` was ONE COMMIT stale, not owed (`D-IMPL-177` at `014f646`, its row text at `f285ac2`) → `Complete as ruled`; verdicting it DISARMED `CONTROL 6`/`7`, caught by `CONTROL 36b`, subject now derived. 27 items assembled, count reconciled (24 + 1 + 2), **delivered NOT ruled**. **The §3.1 panel found this phase's own defect class inside it** — deleting one line (`unexaminable=unexaminable()`) left all 41 tests GREEN while the tool fully regressed; `D-IMPL-188`'s residual one module over, now held. 13 findings: 9 fixed, 1 accepted, 2 rejected, 1 confirmed correct — **including one rejection that was itself wrong and is recorded as such**. 10 sabotages, every prediction held. Gates: lint 0, typecheck 211, `gate-tools` 406+313, docs-strict 0, examples 0; test **4105/118** unchanged, unrun-by-mechanical-argument per Dave's ruling. `DOCS-17`/`CLNT-17` stay `Not built` (`D-IMPL-189`). | 2026-08-23 (`D-GATE-22.1`) |
| 23. The Archive Move — Retiring the Ten Condemned Example Trees Without Deleting Them | 13/13 | **Complete — `D-GATE-23` APPROVED** (Dave, 2026-08-25), merged to `main --no-ff` naming the entry. **All EIGHTEEN Success Criteria met.** 76 commits on `phase-23` from `PHASE_BASE` `b87fe58`. **THE SS3.1 CLOSE FOUND THREE BLOCKING DEFECTS AND ALL THREE ARE FIXED IN-PHASE**, each re-sabotaged after the fix. `B1` is a LOCKED CRITERION THAT WAS NEVER ACTUALLY DISCHARGED: criterion 10 says the sweep *"cannot go blind to the archive"*, but `archive_sweep_problems` ASSERTED a row-count floor while only DOCUMENTING per-tree coverage — suppressing every one of the 21 rows for `archive/examples/03-harness-portability` left 110 rows against a floor of 10 and returned EMPTY, so **nine of ten trees could have gone dark silently**. Fixed at `d6cbca7` with per-tree assertion, both clauses proven independently load-bearing, and verified by the orchestrator rather than read off the report. `B2` a ledger cell claiming six deleted `make` commands (zero survive); `B3` three corrections a prior wave ASSIGNED to the close and never made — **nothing gated any of the three, which is how they went two rulings stale without a red**. Panel (codex, cursor, gemini; `claude` excluded) read the SHIPPED tree with source inlined and every cited symbol checked against it: eleven findings — 3 blocking fixed, 3 advisory fixed, 4 advisory carried, **4 REJECTED with refuting evidence, two of them the executor's own payload omission recorded as such**. codex `F-1` and cursor `F-1`/`F-3` converged INDEPENDENTLY on `B1`. **`make ci` was RED from Wave 10 to Wave 12 and two waves reported green over a partial window** — `tests/invariants` and `make ci` were run by neither; fixed by CONVERSION to symbol form per `D-IMPL-114`, never by raising `D-IMPL-123`'s ceiling. **DAVE BLESSED THE CHUNKED FOREGROUND FORM of `make ci` as an allowed satisfaction of criterion 15 on this host**, under four conditions all met here (`make -n ci` proves the chunk list is the whole recipe; every command foreground with its exit code recorded; the deviation named in the gate entry; the existing coverage proof discharged). A follow-up updating criterion 15's TEXT is OWED and not discharged. Six legs exit 0: `test` **4115 passed / 118 skipped**, `gate-tools` **415 + 339**, `docs-strict` 0, full collection **4233**. Criterion 7 discharged as the accounted delta — 4223 → 4233, **LOST-UNRECOVERED ZERO**, ten additions each named; `tests/examples` 515 → 521. Criterion 14: **8 changed lines** across 3 files under `src/`+`runtime/`, `pyproject.toml` diff-empty. Execution record follows. Row updated BY HAND (`D-15`); no `roadmap.*` writer was invoked in any wave of this phase, and **not one Success Criterion line was authored, edited, renumbered or re-wrapped by execution** — the eighteen stand as locked at the discuss sitting, amended only by `D-IMPL-192`, `D-IMPL-194` (both pre-planning) and `D-IMPL-196`/`D-IMPL-197`/`D-IMPL-198` (the mid-phase checkpoint, applied by the orchestrator). **THE MOVE HAPPENED at Wave 4** — 265 files at `archive/examples/`, proven a pure rename set in the strong form (265 `R100`, 0 D/A/M, 0 insertions and 0 deletions), four trees left under `examples/`. **Wave 11 wrote the verdict `D-IMPL-189` point 4 held back until the state existed on the tree**: `DOCS-17` reads **`Partial`** in BOTH channels, done-limb worded as `D-IMPL-191` ruling 4 amended it (*out of the `examples:` aggregate*, NOT *out of live CI*), owed-limb deletion plus the re-cut. Every figure in the cell re-measured at Wave 11 rather than quoted: `tests/examples` 31 files / **521** collected, **19 of 31** naming a condemned tree with the file SET IDENTICAL at both ends (so the superseded 25 reproduced at neither), **14** loading archived source in-process, **2** SPAWNING A PROCESS (`D-IMPL-198` ruling 2), both run at 46 passed / 0 skipped. Criterion 7's `tests/examples` limb discharged as the accounted delta: **442 -> 448 test functions, LOST-SET EMPTY, all six additions named**. Criterion 6 discharged: the `D-08` pin **MOVED 111 -> 122** with includes unchanged at 102 and pages unchanged at 15, stated as moved-by-design, the eleven new references being the `python` invocation lines that replaced the fourteen deleted `make example-*` commands, and the pre-move spelling now **0** under `public/`. Criterion 13 held: `CLNT-17` content-hashed against `efa0044` before and after — EQUAL, still `Not built`, **and no plan, task, cell or commit message in this phase assigns it any verdict, limb or disposition**. **THE PLAN'S OWN TASK-2 VERIFY PINNED 111 AND FAILED ON A CORRECT TREE** — criterion 6's subject arriving inside the task written to close it. **Six sabotages watched, four of them CAUGHT NOTHING and that is recorded rather than smoothed**: the cell's wording, a prose-only edit to the `CLNT-17` row, and BOTH channels carrying different verdicts for the same row all pass 114 green. **THREE ITEMS STILL OPEN FOR DAVE** (the Phase 20 unbounded `src/` assertion is RULED by `D-IMPL-197`; the two `CLNT-17` framing questions are raised and NOT ruled). **WAVE 12 RAN THE FIRST FULL-SUITE PIPELINE SINCE WAVE 4 AND FOUND `make ci` RED.** `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow` had been failing since `d0ed316` (Wave 10), which wrote a `path.py:LINE` citation (`archive/examples/08-e2e-demo/run.py:4`) into `deferred-items.md` against `D-IMPL-123`'s ceiling of ZERO; Waves 10 and 11 each reported green having run neither `tests/invariants` nor `make ci`. FIXED BY CONVERSION, not by raising the ceiling (`8e431eb`), on `21.1-09`'s precedent. **SIX LEGS AT EXIT 0**, every one in the foreground with its exit code read without a pipe: lint 0; typecheck clean over **211** files; test **4115 passed / 118 skipped / 0 failed** as FOUR foreground chunks whose coverage is PROVEN three ways (1007+1056+986+1184 = **4233** = the full `--collect-only` total; both set-equality directions EMPTY; all six pairwise intersections 0); `gate-tools` **415 + 339**; `examples` running EXACTLY ONE target with three harness legs at one content address; `docs-strict` 0 on all four steps recorded separately. **`make ci` was NOT run as one command and that is recorded as a deviation** — the pipeline measures ~870 s against a 600 s foreground cap, and backgrounding it is the move criterion 15 exists to forbid; it is discharged as its own ten commands, proven complete by `make -n ci`. Criterion 7's suite limb: **4223 -> 4233, LOST-UNRECOVERED = ZERO**, 63 lost ids all recovered at their archive re-path and **ten genuine additions each named to its wave** (Wave 3's eight plus `D-IMPL-197`'s two); the superseded **4105** pin was quoted once and compared against nothing. Criterion 14 re-taken at phase end with the `VAC-01` floor per member: `src` 142 tracked -> `bind.py` only, `runtime` 71 -> the two `mcp` modules, `pyproject.toml` 1 -> EMPTY, **8 changed lines = four edits x both sides**, every one a pure prefix substitution; the five `s1-01` citations and `request.py` byte-identical. **TEN INDEPENDENT SABOTAGES of this phase's own verification code, TWO PREDICTIONS WRONG and recorded as corrections, one sabotage itself MIS-AIMED and recorded as mis-aimed.** Two NEW findings carried: criterion 18's control comment names a mutation the shipped alternation makes INERT (the branch is load-bearing, not the lookbehind — proven by three regexes side by side), and `tests/examples/test_surface_audit.py` DOES NOT EXIST while three live source files cite it. **Sixteen criteria byte-identical to `PHASE_BASE`; criteria 7 and 12 AMENDED BY RULING at `a6d7367` and `06786db`, both decision commits, neither authored by execution.** The coupling report is regenerated LAST in the venv after every `.planning/` write. **STILL OPEN AND NOT THIS GATE'S:** the deletion half of `D-27`; the two `CLNT-17` framing questions (raised, expressly NOT ruled; content-hash EQUAL at both ends, still `Not built`); `DOCS-14`/`EXAM-02`'s replacement surface; and deferred items 7-10, item 7 — no witness reads the RENDERED body a `--8<--` include pulls in — now carried by six waves. **Deletion remains OWED for every scheduled row** (`D-IMPL-191` ruling 3). | 2026-08-25 (`D-GATE-23`) |

## Coverage

All **42** v0.2 requirements mapped, each to exactly one phase — the
milestone-scoped count: the set defined at milestone definition plus what the
inserted phases minted through Phase 15.1. It is **not** the traceability
table's row count, which is **149** and was never 42 — the figure produced by
the strict parse (`tools/docs_tests/test_requirement_ledger.py::traceability_rows`)
rather than assumed. *Re-measured in Phase 22.1: this clause read `143`, correct
when `D-IMPL-177` landed at `014f646` and drifted by six as Phases 21.1 and 22
minted rows. The clause was right and its figure was not; `D-19`/`D-IMPL-174`
require the replacement to come from the parse, so it does.* It arrives in two halves.

**Ruled by Dave at the `D-GATE-21` sitting, 2026-08-22, and logged as
`D-IMPL-177`.** Phase 21 examined this counter under `D-19` and REPORTED rather
than guessed it, because the sentence described itself two incompatible ways and
the parse could not settle which it meant. The ruling settles it: *"v0.2
requirements" for that sentence means the milestone-definition set plus what
inserted phases minted through 15.1 — the 42 the breakdown already enumerates.*
The number is therefore unchanged and the **descriptive clause** is corrected
above, in one line, exactly as the ruling directs; the two halves below remain
true as written. Replacing 42 with 143 without rewriting the breakdown would have
made the next line false. Leave the number at 42 unless milestone scope is later
redefined. Full reasoning:
`.planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-FINDINGS.md` §4.

The **21 defined at milestone definition** (2026-08-01), which is what this
sentence used to count before inserted phases minted more and the number was left
behind (corrected 2026-08-05 at the Phase 15.1 close, flagged by plan 15.1-01):
HARD-01..03 → 9; HARD-04..05 → 10; PERF-01..04 → 11;
DEMO-01..03 → 12; EXAM-01..03 → 13; DOCS-01..06 → 14.

The **21 minted since**, by inserted phases at their own planning:
EXAM-04 → 13.1; EXAM-05 → 13.2; ERGO-01..17 → 15; ERGO-18..19 → 15.1.
(Phases 13.3 and 14.1 minted none — 13.3 closed review residuals against existing
requirements, and 14.1 was superseded by 16 before planning.)

Phase 16 mints its own (DOCS-07..NN) at planning and is not yet counted above.
Phases 15 and 16 were inserted 2026-08-03. They extend v0.2 rather than opening a new milestone:
Phase 15 fixes the surface the v0.2 documentation describes, and Phase 16 rewrites that
documentation against it, so the milestone's "adopter-grade documentation suite" goal is not
actually met until both land. v0.3 (Assembly Modes) is unchanged and still follows.
