## 1. Verdict

**Do not present this package to Dave for D-GATE-15.2 yet.** The mechanism work for plans 01–13 looks largely faithful to D-IMPL-87 (uniform rule, prose→fallback→adapters, survivor set as `allowed_entities` with `seeds=None`, CP-valued cap, hash+ArtifactStore pins), and several hard invariants check out in tree. But the phase-close deliverable itself is incomplete, one checked requirement still states the *voided* multi-segment design, and Neo4j’s “pushdown” claim is only differential byte-identity — which D-04 makes true under silent degrade. Fix the blockers below before the author gate.

`★ Insight ─────────────────────────────────────`
Byte-identity to the fallback is a *conformance* bar, not a *pushdown* bar. Under D-04, a broken `_translate_query` that always returns `None` still matches the oracle. SQL and Mongo already encode that distinction with `translated_answers`; Neo4j does not.
`─────────────────────────────────────────────────`

---

## 2. Blocking findings

1. **Missing phase-close gate artifact (`15.2-14-SUMMARY.md`).**  
   Plan `15.2-14-PLAN.md` requires this file as the evidence surface (make ci counts, three container legs, perf, D-IMPL-87 re-ratification register, §3.1 triage). Glob finds **0** copies. `docs/DECISIONS.md` has **no** `D-GATE-15.2`. `.planning/STATE.md` still says Phase 15.2 **EXECUTING / Plan 1 of 14**. Deferred-items even points Dave’s DI-15.2-03 question *at* the missing SUMMARY.  
   **Claim unsupported:** “plan 15.2-14 checked SUBQ-01..11 and the phase is ready for the author gate.” Partial audit notes in `REQUIREMENTS.md` do not substitute for the plan’s gate package.

2. **`SUBQ-06` is marked Complete while its text still states the rejected design.**  
   `.planning/REQUIREMENTS.md:79` still says post-in-process segments carry survivors **“as seeds + `allowed_entities`”**. D-IMPL-87 and the shipped engine do the opposite: survivors ride only as `allowed_entities`; `seeds=None` (`src/ccf/projection/engine.py:527-528`; pinned by `tests/projection/test_segmentation.py::test_the_second_query_carries_the_survivors_as_allowed_entities`).  
   **Invariant/decision defect:** a Complete requirement that re-asserts the pre-resolution “survivors-as-seeds” reading Dave rejected. Either the checkbox is false or the requirement text is false — both are gate-blocking.

3. **Neo4j pushdown is not distinguished from silent degrade.**  
   `15.2-12-SUMMARY.md` claims Cypher whole-query translation held by the live `-m neo4j` leg. That leg’s recorded evidence is differential byte-identity (`6 passed` …). `tests/graph/test_neo4j_backend.py` has **zero** `translated_answers` / `_pushed` assertions (contrast `tests/graph/test_sql_pushdown.py::_pushed` and `tests/graph/test_mongo_backend.py` asserting `translated_answers == len(queries)` with an explicit comment that D-04 makes degrade byte-identical).  
   **Claim unsupported:** “Neo4j answers via native Cypher pushdown under the suite.” What is proven is “Neo4j’s answers match the fallback,” which is also true if `_translate_query` always declines. For a phase whose goal is substrate pushdown, and with Neo4j named as the strongest pushdown test, that is not enough.

---

## 3. Advisory findings

1. **`SUBQ-08` text is stale relative to shipped Mongo.** It still says stage-1 `$match`+fallback traversal satisfies the requirement and `$graphLookup` is a budgeted enhancement. Plan 15.2-13 shipped stage-2 promotion with telemetry evidence. Under-claiming, not over-claiming — but the Complete checkbox should match what actually shipped and what Dave is asked to ratify.

2. **`DI-15.2-03` (non-UTC claim timestamps vs pushed `GQ-09`) correctly escalated, not silently closed.** Good discipline. It must appear in the gate package as an open Dave question (contract-tier UTC normalization vs documenting a known `GQ-31` corner). Do not let the phase close without that explicit ask.

3. **`MAX_DEPTH_CEILING = 100` in `neo4j.py` is a library constant.** Documented as an injection-surface bound (not CP policy). Acceptable if the gate register presents it for ratification as planned; easy for a reviewer to misread as a domain threshold unless that register exists (it doesn’t yet — see blocker 1).

4. **Historical SUMMARY drift in `15.2-01-SUMMARY.md`.** Key-decision still says GQ-16 closure holds for *every* answer; prose is now 1.0.1 constrained-only. Harmless if the live prose wins, but don’t let gate readers treat plan-01 SUMMARY as normative.

5. **`15.2-VALIDATION.md` still shows many Nyquist cells as pending.** Process hygiene; not itself a fidelity defect if the SUMMARY eventually carries the real gate evidence.

6. **REQUIREMENTS “CHECKED … not against any SUMMARY” note covers SUBQ-01 and SUBQ-11 in detail; SUBQ-02..10 are `[x]` without the same clause-by-clause dump in that note.** Prefer per-ID evidence in the missing SUMMARY rather than a single mega-footnote.

---

## 4. Specific things checked and found sound

| Area | Evidence |
| --- | --- |
| Prose authority / escape hatch closed | `docs/GRAPH_QUERY_SEMANTICS.md` at **1.0.1**; `GQ-16` scoped to constrained answers; amendment history under `GQ-35`; no `implementation-defined` in the prose; DI-15.2-01 marked closed for the right reason |
| Uniform rule / anti-resurrection | Engine threads `allowed_entities=survivors`, `seeds=None`; segmentation test asserts second query carries survivors and no seeds; corpus has `allowed_entities_cases` / resurrection chain; SQL has `test_pushed_resurrection_shape_does_not_cross_outside_the_set` |
| Operator purity / freeze | Answers remain `GraphView`; fallback applies full predicates; GQ-19 re-application path present in engine |
| `as_of` ≡ degenerate `query` | `BaseGraphReader.as_of` → `query(GraphQuery(tenant_id=…, as_of=at))` in `reader.py` |
| Survivor cap mechanism-not-values | Cap is `None`-defaulted on engine/manifest/record; threshold not baked as an SDK domain default |
| Replay pin shape | `graph_query_sequence` on dim 5; `QueryPinWriter`; ArtifactStore before append; replay recompute-compare under recorded `survivor_cap` |
| Single-writer write seam | All five `*GraphWriter` / txn impls in `ccf.graph._writer`; Protocol-only exception in `protocols.py`; confinement test in `test_writer_seam.py`; graphstore fixture now params all five backends |
| Tier-2 ProductSource | Mounts `AdmittedProduct`; typed mount refusal; docstring/code claim no writer / nothing enters L3; differential leg present |
| Attestation | Accepted modes as unordered sets; refusal + gate path; dim-1 pin pattern present |
| Mongo push vs degrade | Explicit `translated_answers` promotion proof + Pitfall-3 trap shapes |
| SQL push vs degrade | `_pushed()` telemetry + byte-equality |
| CI wiring | `ci.yml` has postgres / neo4j / mongo services and marked steps |
| Diff surface vs do-not-disturb | User-supplied diff does not touch `peering/admission.py` or `deployment/binder.py` (consistent with the plan’s undisturbed seams) |
| Deferred DI-15.2-02 | Memory/neo4j/mongo on `test_graphstore.py` fixture — present in tree |

`★ Insight ─────────────────────────────────────`
The D-IMPL-87 fix is load-bearing exactly where SUBQ-06’s stale wording fails: **seeds mean walk starts; `allowed_entities` means the closed universe.** Promoting survivors into `seeds` would re-open entity resurrection. The code got this right; the requirements row did not.
`─────────────────────────────────────────────────`

**Bottom line for the author gate:** mechanism looks strong; package is not. Close blockers 1–3 (write the 15.2-14 SUMMARY with real gate evidence, fix SUBQ-06’s text to match the ruling, add a Neo4j `translated_answers` push proof analogous to SQL/Mongo), keep DI-15.2-03 as an explicit Dave question, then re-run this §3.1 review before presentation.
