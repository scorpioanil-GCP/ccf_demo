# The Wave 2 Examples Gap Ledger — what `D-IMPL-358` ruling 11 did to the undispositioned example trees, dispositioned

**Chartered under the ledger charter of `D-IMPL-261` (Dave, 2026-09-05), the same charter as
`docs/D-IMPL-353-EXAMPLES-GAP-LEDGER.md`. Written at Dave's instruction to *"ledger them out of this
wave's repair, then freeze SDK + s1-01"* (2026-09-30).** Inventory only. **No example in these rows was
edited, no test was weakened, and no rerun was made to turn anything green.** Every number below is read
out of the step-12 estate census bundles — base `51158a58` against candidate `1a4d62d3`, same
environment on both sides.

**Dispositions, Dave's four states, verbatim from `D-IMPL-261`:** **OPEN** — the example exposed an SDK
deficiency that remains. **FIXED-<phase>** — the example exposed it and the named phase changed the SDK
to address it. **ESTATE-LIMITATION** — the limitation belongs to Fluree/data/environment rather than CCF.
**NOT-A-GAP** — investigation established that the observed behavior was correct SDK behavior or an
example/test defect.

**Both rows are NOT-A-GAP, and the reason is a RULING rather than an investigation.** Dave ruled on
2026-09-30: *"TemporalBoundaryPolicy is mandatory. Resolve and enforce it on every governed serve.
Missing policy refuses. Do not add an opt-in/unasked path."* So the SDK behavior these rows record is
the behavior that was ruled correct, and what remains is an example-side **incomplete declaration** —
`NOT-A-GAP`'s second clause, *"an example/test defect"*. **It is not NOT-A-GAP in the sense of "no work
owed".** Each tree owes one `temporal_boundary:` declaration, and the target column says so.

**Scope.** A row is here only if the Wave 2 change exposed it in a tree under `examples/` that carries
**no disposition** of its own. The frozen specimens `cp-00`…`cp-04` are NOT here and need no row: 558 of
their nodes ran in the census and the outcome distribution is byte-identical on both sides (393 passed /
4 failed / 111 xfailed / 48 skipped / 2 error), so Wave 2 cost them nothing. `s1-00`, `door-cp-05` and
`cp-05`…`cp-14` are not here either: their reds are base-existing and already carried by
`SEC353-G-01..G-09`. `archive/` is a dated reference surface and no finding is sourced from it
(`D-IMPL-351`). `s1-01` is not here because it was REPAIRED in this wave (`50e15fa5`, `9926f594`).

**STATUS: LEDGERED OUT OF WAVE 2'S REPAIR.** These 277 nodes are a known, measured, accepted consequence
of a locked ruling. They are **not** a silent pass into the freeze: the freeze's scope is the SDK and
`s1-01`, and this file is the record of what the freeze deliberately leaves red.

**Roster.** 2 rows, `SEC358-G-01..02`, append-only.

---

## Summary by disposition

| disposition | rows |
| --- | --- |
| **OPEN** (0) | — |
| **FIXED-<phase>** (0) | — |
| **ESTATE-LIMITATION** (0) | — |
| **NOT-A-GAP** (2) | G-01 every governed serve in a tree with no declared `temporal_boundary:` refuses `temporal-boundary-undeclared` — 263 nodes; G-02 assertions that no longer reach their subject because the bound refuses ahead of acquisition and ahead of every other governed refusal — 14 nodes |

Counts are of rows. The two node populations are disjoint and sum to the census's 277.

---

## The ledger

Columns are Dave's (`D-IMPL-261`): `Gap ID | requirement | observed behavior | why this is an SDK/estate
issue | evidence | disposition | phase fixed / target phase`.

| Gap ID | requirement | observed behavior | why this is an SDK/estate issue | evidence | disposition | target |
| --- | --- | --- | --- | --- | --- | --- |
| **SEC358-G-01** | A governed serve answers the question asked, or says why it cannot. | Every governed serve in a tree that declares no `temporal_boundary:` returns `RefusalEnvelope(kind='temporal-bound-refusal', reason='temporal-boundary-undeclared')`. **263 nodes across 15 trees.** | **Neither.** The SDK behavior is the one Dave ruled correct: ruling 11 admits no default and no fabricated binding, and `refuse_temporal_bound` refuses an undeclared policy by design (`src/ccf/products/refusal.py::refuse_temporal_bound`), consulted unconditionally on every serve (`src/ccf/products/resolver.py::GovernedResolver.__call__`). The defect is example-side: 32 of 32 config-driven trees never declared the policy, because before Wave 2 there was none to declare. | step-12 census, base `51158a58` vs candidate `1a4d62d3`; per-module table below | **NOT-A-GAP** | one `temporal_boundary:` declaration per tree, on the pattern `s1-01` now carries (`examples/s1-01-hello-context-product/artifacts/temporal-boundary.yaml` + one `manifest.yaml` entry). Deferred past Wave 2 by ruling; no target phase named yet |
| **SEC358-G-02** | A test that names a specific refusal observes that refusal. | **14 nodes** fail or error without their own text naming the temporal bound: `DID NOT RAISE ScopeNotEntitled` / `UnknownCovenantSource` / `ControlRoomUnreachable` / `Exception`, `acquisition emitted no research_node`, and across a process boundary `the peer did not answer: the question could not be answered with sufficient confidence`. | **Neither, and it is the same cause one layer down.** The temporal bound is judged BEFORE acquisition and ahead of every other governed refusal, so a test written to observe a later refusal never reaches it, and a test that depends on acquisition having run sees nothing acquired. Dave: these are step-13 **inputs**, not a resolver reorder — the bound stays first. | the 14 node ids listed below; in `cp-17`, `cp-13-canonical` and `dr-02` the temporal marker appears 40/38/40 times beside them. In `cp-22` it appears twice: the peer refuses in its own process and only the attenuated symptom crosses the wire, which is that tree's design — **weaker evidence, named as weaker** | **NOT-A-GAP** | resolves with G-01: once a tree declares its boundary, each of these assertions reaches its subject again. Each still needs re-reading afterwards, because a declaration does not prove the assertion was right |

---

## G-01 and G-02 by module — the roster, not a total

| module | G-01 direct | G-02 shadowed | failed | error |
| --- | --- | --- | --- | --- |
| `test_cp_03_canonical_output.py` | 12 | 0 | 0 | 12 |
| `test_cp_04_canonical_output.py` | 6 | 0 | 6 | 0 |
| `test_cp_06_canonical_output.py` | 15 | 0 | 2 | 13 |
| `test_cp_13_canonical_output.py` | 13 | 2 | 3 | 12 |
| `test_cp_15_ownership.py` | 12 | 0 | 4 | 8 |
| `test_cp_15_replay.py` | 1 | 0 | 0 | 1 |
| `test_cp_15_review.py` | 4 | 0 | 0 | 4 |
| `test_cp_15_sabotage.py` | 3 | 0 | 3 | 0 |
| `test_cp_16_granularity.py` | 9 | 0 | 9 | 0 |
| `test_cp_16_replay.py` | 4 | 0 | 4 | 0 |
| `test_cp_16_sabotage.py` | 12 | 0 | 0 | 12 |
| `test_cp_16_surveillance.py` | 13 | 0 | 2 | 11 |
| `test_cp_17_replay.py` | 4 | 0 | 2 | 2 |
| `test_cp_17_sabotage.py` | 4 | 3 | 7 | 0 |
| `test_cp_17_wall.py` | 9 | 0 | 0 | 9 |
| `test_cp_18_ranking.py` | 13 | 0 | 0 | 13 |
| `test_cp_18_replay.py` | 2 | 0 | 0 | 2 |
| `test_cp_18_sabotage.py` | 3 | 0 | 3 | 0 |
| `test_cp_19_replay.py` | 3 | 0 | 1 | 2 |
| `test_cp_19_sabotage.py` | 2 | 0 | 2 | 0 |
| `test_cp_19_typology.py` | 11 | 0 | 2 | 9 |
| `test_cp_21_large_exposure.py` | 21 | 0 | 8 | 13 |
| `test_cp_21_sabotage.py` | 23 | 0 | 0 | 23 |
| `test_cp_22_agent_internal.py` | 1 | 8 | 1 | 8 |
| `test_cp_23_portfolio.py` | 20 | 0 | 4 | 16 |
| `test_cp_23_sabotage.py` | 8 | 0 | 0 | 8 |
| `test_cp_24_sabotage.py` | 9 | 0 | 0 | 9 |
| `test_cp_24_whatif.py` | 15 | 0 | 2 | 13 |
| `test_dr_02_packaging.py` | 8 | 1 | 9 | 0 |
| `test_hw1_empty_fabric_refusal.py` | 2 | 0 | 2 | 0 |
| `test_hw1_two_transports.py` | 1 | 0 | 1 | 0 |
| **total** | **263** | **14** | **77** | **200** |

Failures and errors are counted separately and are never added together into a single "red" number:
an error is a test that never ran its body, and reading the two as one hides that.

## G-02 — the 14 node ids

- `tests/examples/test_cp_13_canonical_output.py::test_a_role_with_no_entitlement_row_is_refused_never_narrowed` — failed
- `tests/examples/test_cp_13_canonical_output.py::test_an_unknown_evidence_node_refuses_distinctly` — failed
- `tests/examples/test_cp_17_sabotage.py::test_a_claim_outside_the_classification_vocabulary_never_reaches_the_product` — failed
- `tests/examples/test_cp_17_sabotage.py::test_an_acquisition_keyed_to_another_principal_is_not_refused` — failed
- `tests/examples/test_cp_17_sabotage.py::test_an_unreachable_control_room_stops_every_principal` — failed
- `tests/examples/test_cp_22_agent_internal.py::test_a_caller_cannot_steer_the_determination` — error
- `tests/examples/test_cp_22_agent_internal.py::test_agent_b_assembles_in_process_behind_no_door` — error
- `tests/examples/test_cp_22_agent_internal.py::test_debt_governs_without_travelling` — error
- `tests/examples/test_cp_22_agent_internal.py::test_no_ccf_shaped_structure_crosses_the_wire` — error
- `tests/examples/test_cp_22_agent_internal.py::test_the_exchange_crosses_a_real_process_boundary` — error
- `tests/examples/test_cp_22_agent_internal.py::test_the_extraction_is_lossy_by_a_wide_margin` — error
- `tests/examples/test_cp_22_agent_internal.py::test_the_reply_answers_the_question` — error
- `tests/examples/test_cp_22_agent_internal.py::test_the_wire_answer_agrees_with_the_in_process_product` — error
- `tests/examples/test_dr_02_packaging.py::test_an_upstream_refusal_becomes_this_products_refusal` — failed

---

## Roster check

Summary: `G-01`, `G-02`. Ledger: `SEC358-G-01`, `SEC358-G-02`. Same two, same order. The per-module table's
totals (263 + 14) equal the census's 277 new reds, and the two populations are disjoint by
construction — G-02 is exactly the subset whose own failure text does not name the temporal bound.

**The 15 trees, named so a reader cannot stop at a count:** `cp-03-canonical`, `cp-04-canonical`,
`cp-06-canonical`, `cp-13-canonical`, `cp-15`, `cp-16`, `cp-17`, `cp-18`, `cp-19`, `cp-21`, `cp-22`,
`cp-23`, `cp-24`, `dr-02`, `hw1`. `cp-03-canonical` and `cp-04-canonical` are SEPARATE trees from the
frozen `cp-03` / `cp-04` specimens; conflating them on a filename prefix would mis-file 18 nodes into
the frozen bucket, which a first pass of this census did before it was corrected.
