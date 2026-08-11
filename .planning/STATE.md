---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: Performance, Documentation & Demonstration
status: executing
last_updated: "2026-08-11T00:20:00.000Z"
last_activity: 2026-08-10 -- Phase 16 parked at wave 3; Context Product design ruling pending
progress:
  total_phases: 16
  completed_phases: 14
  total_plans: 136
  completed_plans: 115
  percent: 88
stopped_at: PHASE 16 PLANNED (2026-08-10) — 21 plans in 12 waves, committed at 6c884f5. Artifacts: 16-CONTEXT.md (D-01..D-15), 16-DISCUSSION-LOG.md, 16-RESEARCH.md (1,616 lines), 16-PATTERNS.md (29 files, 26 analogs), 16-VALIDATION.md (V-1..V-10 + 55-row task map), 16-01..16-21-PLAN.md. NEXT ACTION — `/gsd:execute-phase 16`. THREE DAVE RULINGS AT PLANNING, recorded as D-13/D-14/D-15 in 16-CONTEXT.md: D-13 a docstring correction in src/ is NOT "the fabric changed" (ProductClassDeclaration in src/ccf/controlplane/artifacts.py trips the whitepaper shingle scan with 20 hits; criterion 10's `git diff --stat -- src/ runtime/` gate carries that ONE enumerated exception, allowlisted in gate_16.py as a LITERAL not a pattern). D-14 the four inherited Gate-2 tripwire residuals (R4-WR-03, R5-WR-01, augmented-assignment set opacity, attribute/subscript global/nonlocal) are NOT in Phase 16 — carried forward with an explicit entry, because a phase claiming "no fabric changed" that quietly absorbs tests/products/ mechanism work invites the criterion-10 argument D-13 settles. D-14 has a SECOND LIMB added in review: re-flooring a non-vacuity constant, or retiring an assertion whose sole in-tree witness a ruled deletion removes, is bookkeeping forced by the deletion and NOT one of the four carried residuals — without that limb the executor is blocked at waves 8 and 11. D-15 ERGO-03's surface-audit measurement is FROZEN as a historical record and the running test retires (Dave first ruled re-baseline, then reversed to freeze-and-retire on the second pass; ERGO-03 is a Complete requirement, its evidence is preserved not overwritten). Two discretionary calls made visibly, recorded under Claude's Discretion: KYC/UBO is the NARROW spine (Section 1 + the adoption argument carry banking where the FIBO data lives; Section 2 is atlas-commerce, Section 3 is northwind-logistics — three domains keeps D-IMPL-52 and CLAUDE.md §9's horizontal-mix ruling intact); and D-06's "always-on CI stays network-free" is a DELIBERATE distinction from ci.yml's test job, which already runs Postgres/Neo4j/Mongo/Fluree as blocking service containers — the example matrix is weaker on purpose, and adding containers to the examples job is a third option D-06 did not authorize. DAVE'S CRITERION-4 RULING (verbatim): "I like the example of sending in a configuration that tells the example driver which backend to use as opposed to creating six examples" — so ONE driver, backend resolved from artifacts/backends.yaml, connection.py a PURE INTERPRETER with no substrate name, no endpoint literal and no per-backend branch (delete the artifact and it refuses); memory declares an EMPTY field set as data, not a Python special case; 16-12's Makefile uses a BACKEND= variable, NOT a per-backend target family, because six targets would reintroduce the six-examples shape one layer down. THREE REVIEW ROUNDS, issue trajectory 4B+7W → 2B+6W → 2B+4W, all closed; every finding independently verified against the tree before being acted on. THE DEFECT CLASS THAT DOMINATED REVIEW: the retirement inventory in 16-RESEARCH.md §A.1/§A.2 swept examples/, tests/examples/ and public/ ONLY, and SEVEN gates outside those trees hard-couple to the retiring examples — test_artifact_schema_headers.py's named 10-tuple + PERMANENTLY_DEFERRED + >=100 floor; four headroom-free non-vacuity floors in tests/products/ (9/11/11/9, comment says "no headroom, on purpose"); tests/cli/test_schema_export.py's _QUICKSTART_ARTIFACTS; tools/publish_scan_tests/test_publish_scan.py reading public/tutorial/demo-walkthrough.md; test_gate_two_call_shape.py's plan-recognition tripwire whose SOLE witness is one required=True argparse flag at examples/03-harness-portability/run.py:694 (n=1); and tests/perf_smoke/test_smoke.py[crossproc] → perf/suites/crossproc/conftest.py → examples/04-cross-process/producer_child.py, an ALWAYS-ON execution coupling across three trees with no shared token, invisible to every static shape. MITIGATION SHIPPED: 16-21 is a dedicated wave-2 plan building tools/retirement_sweep.py, a re-runnable repo-wide sweep covering FOUR coupling shapes (path token, module-level scan/MINIMUM_* constant, inline tree-witness assertion, indirect execution), with UNASSIGNED rows a hard gate failure and a 14-file known-instances FLOOR not a ceiling; 16-15/16-17/16-18 re-run it before deleting rather than trusting a snapshot. METHOD WORTH REUSING IN PHASE 17: the last coupling was found by CLONING THE TREE, DELETING THE TEN EXAMPLES AND RUNNING THE ALWAYS-ON SUITE — seven failures, six owned, one orphan. For any phase whose central act is deletion, that rehearsal is strictly stronger than a static inventory and it is cheap; the sweep remains the standing CI gate, the rehearsal is the one-time proof the gate's shapes are complete. Floor arithmetic verified by importing the scan functions: with four new spines contributing one each, counts run 13→12→10 (floor 9) and 15→14→12 (floors 11) across waves 8 and 10, so all four floors SURVIVE to 16-18's wave-11 re-count — do not add headroom. WAVE SHAPE: waves 6–11 are single-plan by NECESSITY not decomposition — mkdocs.yml's nav: is an explicit enumeration with no globs and validation.nav.omitted_files + --strict fail BOTH a nav-less page and a file-less nav entry, so the six plans editing nav serialize; wave 4 carries five parallel plans to compensate. tutorial/adopters-guide.md (447 lines, 35 includes, six of ten examples) is TERMINAL in 16-18. Requirements: DOCS-07..DOCS-18 minted (12), written into REQUIREMENTS.md by 16-01 Task 2 at execution — they are NOT there yet, only DOCS-01..06 are; DEMO-01..03 and EXAM-01..05 re-home rather than retire per D-08; 20/20 IDs covered, no plan with empty requirements. Three plans carry checkpoint:human-verify — 16-01 (the ruling package incl. D-IMPL-94), 16-02 (the FIBO data extension, which WRITES TO FOUR LIVE DGX STORES outside the repo), 16-12 (CI + DGX job). KNOWN GAP AT PLANNING: the FIBO data CANNOT answer the adoption argument's own question — ownershipPercent is an attribute of the Party ENTITY not the ownership EDGE, and every hasOwnershipInterestIn runs Party→Corporation in exactly ONE hop, so "Who ultimately owns Acme?" has no chain to traverse; 16-02 (wave 2, DOCS-09) is the requirement-bearing corp→corp extension every KYC/UBO example and page depends on. Also missing at HEAD: the LangGraph and Claude-Agent-SDK client legs (16-03 spikes both in wave 2 against the EXISTING examples/external server so a transport surprise surfaces early); and three gate-checker suites fail at HEAD (453 passed / 3 failed), fixed by 16-04. WARNING, RE-CONFIRMED 2026-08-10 WITH A THIRD HANDLER: `gsd-sdk query state.planned-phase` returned {"updated":["Status","Last Activity"]} and STILL deleted stopped_at wholesale and corrupted the counters to 124/117 — note 117 is the IDENTICAL garbage value the earlier record-session and add-roadmap-evolution corruptions produced. It is not handler-specific; treat EVERY state.* writer as destructive. Backup STATE.md, run, diff, restore, then hand-edit the one intended line. TOOLING FINDING (gsd not ccf): ROADMAP Success Criteria parse ONE PER LINE — a line-wrapped criterion parses as a single entry and verify-phase turns each parsed entry into one verification truth (workflows/verify-phase.md:77-78); Phases 15.3 and 15.4 wrap theirs and were therefore verified against ONE truth instead of nine and five. Phase 16's ten criteria are authored UNWRAPPED and re-verified to parse as 10. Earlier phases' entries are worth an audit. ALSO: GSD's decision-coverage gate (check.decision-coverage-plan) returns {"passed":true,"skipped":true,"reason":"no trackable decisions"} against 16-CONTEXT.md — its parser does not recognize this file's decision format, so D-01..D-15 are NOT mechanically enforced; they are held by the plans, verified by review, not by a gate. PRIOR CONTEXT — Phase 15.4 COMPLETE, gated (D-GATE-15.4 + addendum), all review defects closed; make ci exit 0 at that point, 2457 passed / 81 skipped; pytest tools/lints/tests 400 passed SEPARATELY (testpaths=['tests'] keeps it out of ci-core; CI runs it as its own step). CLAUDE.md §3.1 was amended (Dave, 2026-08-09) to make the cross-AI panel unsubstitutable — panel IS the step, single-agent review is additive; at close the panel reviews SHIPPED CODE not plans; hand it known findings and tell it not to re-derive them; verify every finding against the tree and record rejections; ordering is execute → panel → single-agent → verify → fix blocking in-phase → present. OPEN DEBT: DI-15.4-01 duplicated Fluree admit prefixes; DI-15.4-02 line-anchored citation drift (45 anchors); DI-15.4-04 load_and_boot runs discovery 3x; DI-15.4-05 the public-vs-private adapter surface (narrowed not closed — GraphWriter now declares close(), the six private reader names stand) and its F2 rider, substrate_vocabulary deriving from in-tree adapters only so cinv04 enforces "no BUILT-IN substrate name in core" — Codex called the third-party zero-cost claim "partly true by construction of the measurement"; the obvious fix (derive from installed entry points) makes a structural invariant environment-dependent, green or red by virtualenv, so the ruling belongs with DI-15.4-05 and 16-06 must not publish the unruled surface (RESEARCH Q-7); the ccf name is taken on PyPI by an unrelated project at 7.0.12; 15.3 residuals WR-04/WR-06/IN-02/IN-03 and 2 GitHub-Actions UAT observations. OPERATIONAL: mongo container is on port 27019 not 27017 (wrong port HANGS — use CCF_TEST_MONGO_URI); fluree leg is 37 not 38; NEO4J_PASSWORD and PGPASSWORD for the DGX are NOT in this environment, so the opt-in live leg cannot be proven locally and must be dispatched in Actions with secrets configured — a Dave-facing prerequisite, not a code task. Dave's four-database FIBO harness is at /home/parkave/fluree/examples/fibo/ (192.168.4.76).
---

# STATE — CCF SDK

## Project Reference

**Core value:** Whitepaper fidelity — every load-bearing primitive in
`docs/CCF_Whitepaper_1-2.md` realized in code with its contracts, invariants,
and composition properties. Priority order: fidelity → general-purposeness →
harness neutrality → adoptability. `/home/parkave/ccf_code/CLAUDE.md` (rev 4)
is canonical for phases, review protocol, invariants, and decision log.

**Current focus:** Phase 16 — documentation rewrite — the deterministic path & the adoption argument

## Current Position

Phase: 16 — Documentation Rewrite — The Deterministic Path & The Adoption Argument
Plan: 6 of 21 complete (waves 1-3); 16-02 open at 2/3, 16-05 open at 2/3
Status: **PARKED — do NOT start wave 4.** Branch `phase-16` (forked from main @
  06fea5c per CLAUDE.md §2.2; merge to main at the D-GATE-16 entry, not before),
  pushed to origin, HEAD 4c70596. Waves 4-12 are deliberately unstarted.
  WHY PARKED: Dave's review of `examples/s1-01-hello-context-product` on
  2026-08-10 found that the Context Product surface is a fidelity defect against
  the whitepaper, not a documentation gap — so documenting it now would document
  the defect. Three of §6.3's eight committed elements (freshness SLA, discovery,
  addressability) are unimplemented while the code claims they live on
  `RegisteredProductClass`; the payload is an unvalidated dict because
  `register_product_class` takes no schema; and `DebtAssessment` is computed by
  `ccf.halflife.debt` and appears on neither the product nor the replay record.
  Every example after 16-05 copies its shape, which is why waves 4-12 wait.
  THE RULINGS SO FAR, all recorded: `D-IMPL-95` (systems of record are read-only
  to L1; CCF's graph is CCF-owned on the same substrate), `D-IMPL-96` (revokes
  criterion 10's "no fabric changed", withdrawing D-13, D-14 and 16-19's
  gate_16.py allowlist with it), plus the vessel ruling — a Context Product is
  ONE standardised vessel, not a class hierarchy; its uniqueness is in how it was
  assembled; the assembler is a Protocol whose declaration is a Control Plane
  artifact. The vessel ruling is NOT yet a D-IMPL entry: it is enumerated in
  `docs/CONTEXT_PRODUCT_REVISION.md` pending Dave's confirmation of the DERIVED
  items and his whitepaper revision.
  NEXT ACTION: Dave is considering `docs/CONTEXT_PRODUCT_REVISION.md` (2026-08-10,
  "let me ponder this over dinner"). Its §9 lists eight open questions; question 6
  — whether the request surface is a typed request contract per class — unlocks
  the others, because it collapses the fixed-subject and fixed-instant defects
  into one design. Expect a Phase D mini-cycle per CLAUDE.md §3 before wave 4.
  The six checkpoint plans, unchanged: 16-01 (done), 16-02, 16-05, 16-12, 16-14,
  16-19.
  NOTE, carried from the block this replaced: the previous Current Position text
  described Phase 15.4's D-IMPL-93 commission, not Phase 16 — a GSD handler left
  it stranded under a Phase 16 heading. That commission is recorded canonically
  in ROADMAP.md and DECISIONS.md; nothing is lost by removing it here.
Progress: [###░░░░░░░] 29% — 6/21 plans, waves 1-3 of 12 complete
  OPEN 16-02 (2/3): Task 3 loads the extended FIBO estate into the DGX stores.
  Dave ran the loaders 2026-08-10; MongoDB, Neo4j and PostgreSQL now all carry
  16 relationships with `ownershipPercent` on 9 EDGES (verified by direct query).
  Two out-of-tree loaders were patched to carry the per-edge percentage —
  `load_neo4j.py` gained one SET clause, `load_postgres.py` one nullable column;
  backups under `/home/parkave/fluree/examples/fibo/.backups/`. FLUREE REMAINS
  UNLOADED and holds 4 of 9 ownership pairs: there is no Fluree loader in that
  harness (`fluree_to_mongo.py` is export-only), and it is not a missing line —
  RDF has nowhere to hang a qualifier on a triple, which is exactly WHY the source
  modelled ownershipPercent on the Party and every chain was one hop. CCF's own
  adapter solves it with the interposed-edge layout (`fluree_write.py`, 15.3
  §R5); the source harness would need the same reification decided deliberately.
  Dave has not ruled write / leave / defer.
  OPEN 16-05 (2/3): Task 3 is a human-verify gate — read spine.py and
  deployment.py side by side and judge whether the CCF/yours boundary is legible.
  Superseded in practice by the Context Product findings above; do not close it
  until the vessel design lands, since the example's shape is what is changing.
  MEASURED FOR THAT REVIEW, worth not re-deriving: the example's own algorithm is
  125 executable lines (`UltimateBeneficialOwnershipPlan`) against 189 of spine
  choreography and 74 of wiring — and 55 of those 74 exist only to satisfy
  `DeploymentBinding`, a Protocol the example invented, calls "the adoption
  checklist", and CCF does not ship. All eight examples call `load_and_boot`
  identically; seven differ only in a filename. The fix is deletion.
  TIMINGS, measured 2026-08-10, not regression-gated: boot 74.3 ms once per
  process; projection execute 8.68 ms per question; the replay append that gates
  delivery 0.29 ms; full example 347 ms (dominated by boot + ~30 ingests at
  ~5 ms each). So a second question in a live service costs ~10 ms, not 347.
  Verified before proceeding: the generator's output is a true superset of the
  shipped FIBO data — 0 entities lost, 0 relationships lost, 5 added, and
  ownershipPercent present on 9 edges where the originals had it on none.
Last activity: 2026-08-10 -- Phase 16 execution started (wave 1 of 12)

## Performance Metrics

- Phases complete and gated: 8/8 — Phase I closed (D-GATE-I, 2026-07-31); v0.1.0 declared
- Requirements delivered: 31/46 mapped to gated phases — RSCH-01..04, DSGN-01..04,
  FEAS-01..04, FABR-01..09, CINV-01..04, AGNT-01..03, XPRC-01..03. **CINV-04 is
  partial**: two deferral skips (`hitl-action-capture`, `workflow-trace-capture`)
  remain active and are Phase 7's to flip.

- D-GATE entries logged: 6 (D-GATE-R, D-GATE-D, D-GATE-F, D-GATE-I.1, D-GATE-I.2, D-GATE-I.3)
- Test baseline on `main`: 987 passed / 2 skipped, mypy --strict clean (99 files), `tools.lints --all` exit 0

| Phase-Plan | Duration | Tasks | Files |
| ---------- | -------- | ----- | ----- |
| 04-01      | ~12 min  | 3     | 10    |
| 04-02      | ~20 min  | 3     | 14    |
| 04-03      | ~25 min  | 3     | 13    |
| 04-04      | ~35 min  | 3     | 16    |
| 04-05      | ~50 min  | 3     | 24    |
| 05-01      | ~35 min  | 3     | 16    |
| 05-02      | ~10 min  | 3     | 12    |
| 05-05      | ~6 min   | 1     | 7     |
| 05-06      | ~12 min  | 2     | 20    |
| 05-07      | ~8 min   | 2     | 3     |
| 07-01      | ~15 min  | 3     | 2     |
| 07-14      | 2 sess.  | 3     | 12    |
| 08-01      | ~10 min  | 2     | 4     |
| 08-02      | ~12 min  | 2     | 8     |
| Phase 08 P03 | ~15 min | 3 tasks | 6 files |
| Phase 08 P04 | 20min | 2 tasks | 6 files |
| 08-09      | ~10 min  | 2     | 8     |
| 08-10      | ~18 min  | 2     | 11    |
| 08-12      | ~12 min  | 2     | 4     |
| 08-13      | ~50 min  | 4     | 5     |

## Accumulated Context

### Roadmap Evolution

- Phase 13.1 inserted after Phase 13: External-Consumer Examples (MCP Egress): independent-harness agents consume CCF via MCP, zero client-side CCF imports — primary adoption path, demonstrated not asserted (Dave, 2026-08-02) (URGENT)
- Phase 13.2 inserted after Phase 13: external-example-hardening — post-execution cross-AI review re-checks for 13.1 (fixtures vs live SDK traffic, LLM tool-surface narrowing, byte-path probe, clean-runner install, .mcp.json verification) (URGENT)
- Phase 13.3 inserted after Phase 13: Review-Residual Hardening (URGENT)
- Phase 15.2 inserted after Phase 15.1: Substrate adapters and query pushdown; tiers 1+2 in scope, tier 3 designed-for
- Phase 16 edited 2026-08-09: status, goal, requirements, success_criteria — scope expanded to four sections (Phase 16 ships 1–3, Section 4 → Phase 17) per 16-CONTEXT.md D-01..D-12; ten Success Criteria added where the entry previously had none

### Decisions

- CLAUDE.md is canonical; GSD phases map 1:1 to R/D/F/I (I sliced into I.1–I.5)
- Monorepo at `github.com/drcastillo/ccf_code` (provisional D-IMPL-10)
- Phase branches per CLAUDE.md §2.2 (`phase-r`, `phase-d`, `phase-f`, `phase-i1`..`phase-i5`); merge to `main` only at D-GATE
- Model mandates: Fable 5 high effort (Phases 1–3 / R, D, F); Opus 5 or Opus 4.8 high effort (Phases 4–8 / I)
- [Phase 02]: Entry ownership: single primary owner per INV key from pillar mapping; dual-pillar entries get See-also, never two owners
- [Phase 02]: Phase 2 planning docs carried from phase-r onto phase-d (Rule 3 — required for plan execution; planning metadata only)
- [Phase 02]: Batch 1 rulings (Dave, 2026-07-25, all AS RECOMMENDED): D-IMPL-01 Python 3.12+ sole target; 02 GraphStore Protocol + Postgres/SQLite; 03 SimilarityIndex + sqlite-vec; 04 ccf + ccf-runtime packages, async-first runtime/sync core; 05 multi-tenant first-class; 07 EmbedderProtocol; 08 Pattern-5 stage Protocols + reference pipeline; 09 LLMClientProtocol + Anthropic Citations adapter; 33 SignalEnvelope superset; 34 six-semantics storage Protocol w/ reader-writer split; 35 EntityResolutionStrategy Protocol; 37 boot-time register(); 38 OperatorParameterSet, no silent defaults; 39 MAX_TTL per class in Control Plane; 40 CAR scale/thresholds in Control Plane; 41 four-layer single-writer stack
- [Phase 02]: Batch 3 rulings (Dave, 2026-07-25, zero provisionals — marathon complete 49/49): 18 AS RECOMMENDED — D-IMPL-26 hybrid content-hash + versioned-URI addressing; 06 logical snapshots + touched-substate manifests; 17 in-SDK Workflow primitive + OrchestrationProtocol w/ LangGraph two-seam disambiguation; 20 HITLTransportProtocol typed queue, MCP primary + webhook notify-only; 27 substrate split by mutability; 36 deterministic intermediate cache; 44 ReHydrationRecipe + ColdSourceArchiveProtocol; 50 SDK-shipped fidelity lifecycle; 18 workflow state at Control Plane; 21 HumanPrincipalBinding via IdentityProvider family; 22 noun-verb CLI; 23 minimal HTTP skeleton, no L1 endpoint; 43 default human-gated closed loop; 30 nine contract elements, "eight" refs annotated as drift (incl. CLAUDE.md §5, per Dave's ruling); 31 two TTL granularities w/ derivation rule; 32 TrustScorer Protocol conjunctive; 42 prose taxonomy enum canonical; 48 Supervision Quality out of v0 scope. D-IMPL-47 REFINED: DebtFactorScorer Protocol + reference F/C/S computations PLUS evolvability — versioned scorers (scorer_id, scorer_version), Control-Plane-updatable class bindings, per-class custom override, replay pins scorer version in force. Full 12-member Phase I gate list RESOLVED
- [Phase 02]: Batch 2 rulings (Dave, 2026-07-25, zero provisionals): 13 AS RECOMMENDED — D-IMPL-28 YAML artifacts + Pydantic v2 schemas + Jinja2 prompt URIs; 11 single Agent class + Protocol-typed archetype bundles, no user subclassing; 14 LF A2A default WireProtocol + typed-HTTP fallback; 12 dynamic Control Plane skill catalog, four skill types; 19 ordered archetype composition w/ explicit conflict rules; 25 three seams mandatory, effects:unsupported = conformance-verified absence; 29 two-tier skilling governance; 13 five MCP edges via one client lib + egress server + separate ArtifactStore contract; 15 IdentityProvider Protocol, mTLS + detached JWS; 16 verify every inbound A2A product, no fast path; 45 TraceCorrelationHook + ExternalTraceProviderProtocol; 46 PassageCitationProvider Protocol. D-IMPL-24 DAVE'S OWN RULING: all three harnesses (Google ADK + Claude Agent SDK + LangGraph) ship v0 reference adapters. D-IMPL-49 REFINED: deterministic (perspective, product_class, selection_params) signature + DESIGN.md obligation to document swarm intent decomposition as orchestration-layer, named post-v0 extension

- [Phase 02]: DESIGN.md Appendix A granularity: subsection-level for §2A/§2B/§3/§6, chapter-level for §4/§5/§7; Appendix C (D-IMPL ruling index, 50 rulings) added so decision-log linkage is mechanically checkable
- [Phase 02]: D-GATE-D logged 2026-07-25 (approver Dave, zero provisionals; 5 blocking findings fixed in-phase, 7 advisory carried to Phase F); phase-d merged to main --no-ff — Phase F unblocked
- [Phase 04]: D-IMPL-52 logged (Dave, 2026-07-25): v0 examples suite is a horizontal mix of domains; example 00 + the I.1 slice fixtures are banking — replaces CLAUDE.md §9's single-neutral-domain rule (§9 amended in 04-01)
- [Phase 04]: D-12 scope amendment recorded on ROADMAP Phase 4 criterion 4 — I.1 ships ArtifactStore Protocol + file-backed dev impl only; the MCP-backed reference impl was added to Phase 6 success criteria so the deferral has a receiving deliverable
- [Phase 04]: Packaging shape — one v0 distribution ships both `ccf` (src layout) and `ccf_runtime` via `packages.find where = ["src","runtime"]`; chromadb confined to the `chroma` extra, never a core dep
- [Phase 04]: CI lint job is intentionally red on `phase-i1` until plan 04-02 lands `tools/lints` — D-07 forbids making the step non-blocking to hide the gap
- [Phase 04]: Assumption A1 resolved empirically — mypy 2.3.0 `--strict` flag surface is unchanged from the 1.x expectation
- [Phase 04]: Single-writer keyed on graph identity (database path), not one-boot-per-process — the invariant is one writer per graph; a process singleton would forbid multi-fabric hosting
- [Phase 04]: Operators are pure GraphView -> GraphView functions; the engine performs the single as-of read, so no state exists underneath an operator that could diverge between two composition orderings
- [Phase 04]: The engine records operators_invoked from execution, never from the plan's declaration — the L6 lineage strict-equality gate compares two independently produced sets or it compares nothing
- [Phase 04]: MAX_TTL is resolved from the Control Plane twice (product-class registration and gate time); no TTL number exists in /src (D-IMPL-39)
- [Phase 04]: Gate refusals are returned values; exceptions are reserved for broken deployments, so a bad product and a broken fabric are never reported the same way
- [Phase 04]: serve() is one expression because the replay append returns the delivery capability — there is no branch that reaches delivery without a recorded decision
- [Phase 04]: Similarity scores are integer percent; the canonical serializer refuses floats, so a float score could never enter a provenance chain replay compares byte for byte
- [Phase 04]: canonical.py normalizes models field-by-field rather than via model_dump() — dumping rebuilds set-valued fields as sets of dicts, making every claim in the fabric unhashable
- [Phase 04]: Every backend's GraphWriter class lives in ccf.graph._writer, never beside its reader — otherwise the CINV-02 lint guards a module while the real write path lives unguarded
- [Phase 04]: claim_id excludes lineage and observed_at — corroboration accumulates instead of manufacturing supersessions, and a claim stays addressable while its evidence grows
- [Phase 05]: D-05 content comparison uses version-normalized fingerprint (artifact_version blanked) so a bump alone never reads as a content change
- [Phase 05]: delegation_chain defaults to single-element NO_AGENT_DEFINITION chain; build_replay_record passes single-element originating-principal chain (I.2)
- [Phase 05]: Factory resolves ccf-artifact:// refs via Control Plane key {tenant}/{class}/{name}, matching URI version against each registered version's declared artifact_version/semver (content hashes also accepted); reads through Control Plane resolution only, never raw storage
- [Phase 05]: Agent seam failures (ConsumptionRefused, SkillNotBound, AgentConstructionError) are typed exceptions, not returned refusals — broken wiring, not expected artifact outcomes (I.1 refusal-vs-exception line)
- [Phase 05]: SkillCatalog stores only a key index; the registry stays the single source of skill entry content — discovery/resolution read the same audited versions as every Control Plane consumer (05-05)
- [Phase 05]: Skill bindings are pure descriptors in 05-05 (D-08) — no transport or resolution code for any of the four types until 05-06 dispatch
- [Phase 05]: build_replay_record gained optional agent_conditioning seam — agent-serialized dimension-4 conditioning recorded verbatim; None keeps I.1 behavior byte for byte (no contract change)
- [Phase 05]: Tier-1 governance envelope reads a `skill_governance` field (typed PolicyRegimeGovernance) from the policy-regime declaration — field name is mechanism schema; permitted scopes and the tier-2 flag are deployment YAML statements (05-06)
- [Phase 05]: Grant transitions audit as new grant_* AuditAction members through the one existing AuditLog — no parallel log type (05-06)
- [Phase 05]: NotYetBound is a typed RuntimeError for mcp/a2a dispatch (build lacks the transport; artifact is fine) — RESEARCH Open Question 2 resolution; tool dispatch returns a ToolInvocation value, the SDK executes no command (05-06)
- [Phase 05]: Agent holds bound_skills by reference to the GrantLedger's live view — grants/revocations take effect at invoke time without touching agent identity; ledger.grant_set_hash() returns the NO_GRANTS sentinel when empty, pure fn stays content_hash(frozenset) (D-07, 05-06)
- [Phase 05]: Gate package (docs/PHASE_I2_GATE.md) follows the I.1 D-17 format; discretionary in-phase choices recorded in the gate doc §4, not as D-IMPL entries; D-GATE-I.2 deliberately NOT logged pending Dave's approval (05-07)
- [Phase 07]: D-IMPL-60 (Dave, 2026-07-29): all three v0 SDKs get real OrchestrationProtocol drivers under `runtime/ccf_runtime/orchestration/<sdk>/` with bidirectional adapter-import ban; D-IMPL-17 cross-referenced, not edited (07-01)
- [Phase 07]: D-IMPL-61 (Dave, 2026-07-30): absent per-node exception ref = propagate-to-terminal — a defined, audited transition to a terminal `failed` state recorded in the trace; validation-error reading declined (let-it-fail stays expressible). Gates 07-04's exception-routing validator (07-01)
- [Phase 07]: D-IMPL-62 (Dave, 2026-07-30): HTTP/CLI HITL action door is submit-only with honest-contract hardening — `HitlActionReceipt` states `submitted` (type-closed) with real queue disposition; MCP in-process resolve-wiring is a ruled asymmetry; auth stays on T-07-24's residual entry (07-14)
- [Phase 07]: D-IMPL-63 (Dave, 2026-07-30): the two D-IMPL-21 identity-binding reference impls are explicit follow-up-phase scope; caller-supplied principal fields are the recorded v0 posture (07-14)
- [Phase 07]: D-IMPL-64 (Dave, 2026-07-30): webhook deferral REJECTED — the notify-only webhook HITL transport ships in v0 (`ccf.hitl.webhook`: injected `WebhookDeliveryProtocol`, typed refusals, no authority surface by construction) (07-14)
- [Phase 07]: D-IMPL-65 (Dave, 2026-07-30): composition-root debt-cascade wiring closes the I.4 gate; NAMED next-phase commitment — the engine will refuse an agent-node handoff with no bound debt assessment (07-14)
- [Phase 07]: fastapi==0.140.0 and httpx==0.28.1 are direct pins with stated reasons; CLI is stdlib argparse (no click/typer); ADK's `fastapi>=0.133` constraint interaction recorded for the gate (07-01)
- [Phase 08]: D-15 executed — `ccf hitl decide` removed tree-wide, `submit` is the one verb; DECISIONS.md entry dated 2026-07-30 (08-02)
- [Phase 08]: HITL HTTP door fails closed on non-TokenGrant grant objects (403 ERROR_INVALID_GRANT, never caller-principal fallback); refusal bodies carry typed `error_code` constants from `http_api/errors.py`, with `ERROR_SIGNED_BINDING_{REQUIRED,INVALID}` reserved for 08-03 (08-02)
- [Phase ?]: 08-03: HitlPolicy artifact (ccf.hitl-policy) with schema-validated signed_binding_required (default false); D-16 refusals typed at the transport and mapped to shared ERROR_SIGNED_BINDING_* constants at both HTTP and MCP doors; R1 closed with was-called assertions
- [Phase 08]: Example 07 store choice is a config artifact (`store.type`) interpreted by one factory seam; file root and MCP endpoint are env-templated so no path or port is committed; the MCP child interprets the same store_mcp.yaml auth block as the client factory, so credentials cannot drift (08-09)
- [Phase ?]: ADK migration taken over suppression: google.adk.workflow.Workflow usable at 2.5.0 (BaseAgent is BaseNode); D-08 allowlist carries the harness Workflow name-collision, allowlist path matching Rule-1-fixed (08-04)
- [Phase 08]: 08-12 — make ci finalized as ci-core + examples (the phase gate command, command-identical to the always-on Actions pipeline, D-10); live legs opt-in via live-legs.yml workflow_dispatch (Ollama model parameterized, default qwen3:0.6b; Anthropic secret-gated fail-fast) per D-11; push of phase-i5 flagged for Dave, not performed
- [Phase 08]: A3 closed with zero adapter change — the discharge test and example 03's Claude leg drive a genuinely SDK-parsed ResultMessage through seam 4; example 03's session runs over the adapter's own seam-1 carrier, and legs/deterministic.py imports all three harness SDKs unconditionally so a missing harness is a failure, not a skip (08-10)
- [Phase 08]: 08-13 — D-GATE-I logged (Dave, 2026-07-31): Phase I approved, v0.1.0 tagged on the main merge commit (358ba0d), push authorized and performed; review disposition X-1 fixed in-phase (composition-coverage row narrowed to the shipped_operators() test registry), C-4 rejected with rationale (README tracks CLAUDE.md mission wording)

### Todos

- Plan Phase 9 (`/gsd:plan-phase 9`) — includes surfacing the six-item D-IMPL ruling batch to Dave (HARD-01)
- Phases 10–14 gated: 10 on the Phase 9 rulings; 11 on the hardened surface + perf-governance ruling; 13 on Phase 10 (parallel to 11/12); 14 on 11+12+13 outputs + docs-toolchain/D-10 rulings

### Blockers

- ~~Phase 4 (Phase I.1) hard-gated on provisional resolution of D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28~~ — CLEARED 2026-07-25: all 12 gating IDs RESOLVED (batch 3 completed 17, 20, 26)
- Every phase gate requires Dave's approval + `D-GATE-<Phase>` entry; `/gsd-review` passing is necessary, never sufficient

## Session Continuity

Last action: 08-13 complete (2026-07-31) — Phase I gated and v0.1.0
declared: D-GATE-I logged, phase-i5 merged to main --no-ff, v0.1.0 tagged
on the merge commit, main/phase-i5/v0.1.0 pushed to origin per Dave's
authorization. Prior: 08-12 — examples suite
wired into CI per D-10/D-11 (EXAM-09, Task 1 f145f1e): ci.yml always-on
`examples` job (make examples, CCF_REQUIRE_HARNESSES=1, timeout-minutes
20, never continue-on-error) plus new live-legs.yml (workflow_dispatch
examples-live-ollama with parameterized small model; secret-gated
examples-live-anthropic with fail-fast); `make ci` finalized = ci-core +
examples. Full local sweep GREEN (Task 2 evidence-only): lint 0, mypy
clean (156 files), pytest 1339 passed / 0 skipped, all eight examples
exit 0, D-09 README/artifacts contract check 8/8 PASS.

Next action: v0 is declared — milestone complete. Post-v0 backlog:
Homecams-on-SDK rebuild, PyPI motion, perf baselines, replay-explorer /
graph-export CLI ideas. Observe the first Actions runs on origin for the
EXAM-09 observed-evidence record.

---

**2026-08-05 session resume.** Phase 15 (SDK Ergonomics) is executing at
18/21 plans; waves 1–11 merged to `main` at `5fbb8e0`, handoff saved at
`60a148b`, tree clean, no worktrees. Full checkpoint context — Dave's six
in-execution rulings, the `_register_closure` evidence for 15-19, the two
self-satisfying-assertion defects 15-21's audit must cite, and the
worktree/`.venv` operational notes — lives in
`.planning/phases/15-sdk-ergonomics-the-integration-surface/.continue-here.md`.
Remaining: wave 12 = 15-19 (example 05 workflow-HITL, autonomous),
wave 13 = 15-20 (external 00-hello-context, autonomous), wave 14 = 15-21
(phase close + Criterion 1 audit, **checkpoint — not autonomous**).
Gates green at handoff: 1908 passed/2 skipped, lint 0, typecheck 169 files,
ten examples, docs-strict, schema-headers.

Resume: `/gsd-execute-phase 15`
