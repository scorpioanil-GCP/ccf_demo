# CP-14 · credit-memo-context — findings, Gate 2 slice 1

**Scope of this record.** The first integration slice only (Dave, 2026-09-15):
the five-slot composite on the paved road, asked its first real question. Not
the memo's own assembly (spec §D.1), not the gate roster, not a page. Every
finding is classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before
anything was changed; the Gate-1 findings `CP14-F-01`–`F-25` stand as the
specification records them (§F.2) and are not restated here.

**The question asked.** BGC Group (`2549001IGRCG4F0RLD36`) at the CP-14 instant
`2026-09-07T12:00:00+00:00` (`CP14-F-19`, untuned), `as_of` the same instant,
`debt_tolerance` **0.25** — the v2 policy's default at that date, stated
explicitly in this slice — `facility_id` `FAC-5B8418` (BGC's one facility;
`CP14-F-20`, facility grain), `memo_type` the class default `annual-review`.

**The result (stop point B).** The spread producer, real and in another
process, **withheld** the spread at 0.25 (`tolerance-exceeded`); the required
slot refused; the composite refused (`composite-child-refusal` /
`child_admission`); **five child rows** were persisted and reloaded from a
fresh store instance (`D-IMPL-338`). At the diagnostic tolerance 1.0 the spread
was **served and admitted** under `provider-controls` at content address
`122e0a7b0b96565eac64af7cf2fbd0d5238c46529c1914b638b237187cd1c21e` — the same
address the producer's own proofs and the low-road consumer hash to — and the
composite still refused on the four unreachable required slots. Executable:
`tests/examples/test_cp_14_first_slice.py`.

## Findings raised by this slice

| Id | Finding | Category (§B) | Disposition |
| --- | --- | --- | --- |
| `CP14-F-26` | **Four of the five required producers have no door the paved road can reach.** cp-04-canonical and cp-13 ship no door at all; cp-05 and cp-06 ship stdio doors from before `D-IMPL-340` that assert no producer identity. The paved consumer reaches a producer over streamable HTTP at the endpoint a registration NAMES (`D-IMPL-340` ruling 10), and `D-IMPL-343` gives every paved producer a loopback door for free — so the gap is producer-side rung work (each tree re-expressed on the paved road, the design's §8 rows 2–5), never a CP-14 workaround. In this slice their endpoints are pointed at a loopback port nothing listens on, and the SDK's own answer — `producer-unavailable`, a governed row naming the registration — is what is reported. The `producer_id` each registration declares is the identity this consumer REQUIRES the producer to assert; no shipped door asserts it yet | **4 · example / engineered-estate limitation** (the SDK provides the door; the frozen trees have not adopted it — `D-IMPL-261`) | Recorded here and in `ccf_config.yaml`. Owner: the four producer rungs. Not fixed in this tree |
| `CP14-F-27` | **The four unreachable producers' question mappings are written against their contracts but are unexercised.** Each mapping names the producer's demonstration intent and required parameters as its tree declares them (`families`/`lei` for the family walk, `families` for the roll-up, `facility_id` + `borrower_scope` for collateral, `covenant_sources` for the covenant chain) and inherits the memo's tolerance where the contract takes one (the collateral contract takes none — none is invented). Until a door exists, whether each producer accepts the question as mapped is unmeasured | **4 · example limitation** (follows from `F-26`) | Recorded; re-measured when each door lands |
| `CP14-F-28` | **The covenant child's subject is parent logic this slice does not own yet.** cp-13's subject is a set of `ex:PassageAnchor` URIs derived from the facility's credit agreement (spec §D.2); the derivation is the parent's own Traversal step, owed by a later slice. This slice asks with `covenant_sources: []`, which cp-13 would refuse or raise (`CP14-F-21`) — honest about what the mapping can name, and unreachable in any case (`F-26`) | **4 · example limitation** (slice scope) | Owed by the parent-logic slice; the mapping's shape is in place |
| `CP14-F-29` | **The memo's tolerance default from the policy version is not yet derived.** Spec §B.2 defaults `debt_tolerance` from `debtToleranceDefault` at `as_of` (0.30 under v1, 0.25 under v2). The paved road's request contract carries static class defaults; a default read from a ledger at the decision instant is the parent's Policy step (`D-IMPL-343` preserves `constraint_resolver=` as the hatch for it). This slice states the value explicitly — 0.25, the v2 default at the CP-14 instant — and does not raise it | **3 · post-launch enhancement** as an SDK matter (a supported path exists: an explicit value, or a deployment's own constraint resolver); the memo's own step is product logic | Backlog record below; the parent-logic slice carries the step |
| `CP14-F-30` | **`D-IMPL-342` / F-05, seen from the consumer.** The refused spread row carries no `child_replay_ref`; the consumer's record retains the producer's refusal as its door disclosed it — `tolerance-exceeded (tolerance-exceeded: fulfillment was withheld because an applicable declared tolerance was exceeded)` — never the producer's debt block or its record's address. `ineligible` on the row is not the producer's reason; the reason lives in the retained detail and in the producer's own record, which this consumer cannot address | **open SDK finding, ruled** (`D-IMPL-342`) | Not synthesized here; reported as retained |
| `CP14-F-32` | **On a refused composite the admitted child's bytes are not retained in the consumer's store — only its identity on the row.** At the diagnostic tolerance the spread was admitted (row `admitted`, content address recorded) and the composite refused on the other four; the consumer's store holds the five rows and the refusal record, not the admitted spread's contract. A served composite retains its children (dogfood B). So the evidence an examiner has for an admitted-but-unused child is its address, producer, tenant, question identity and lane — not its bytes | **3 · post-launch enhancement** (the row is the ruled evidence; retaining admitted bytes on every exit would widen `D-IMPL-338`'s scope) | Recorded; the proof states the boundary rather than working around it |
| `CP14-F-31` | **`D-IMPL-341` / F-01, inherited — FIXED-341 (2026-09-18).** The admitted spread's `expires_at` was decision-anchored by the SDK despite the class's `from_entity_freshness` declaration and the memo's floor inherited it as-is. Since 341 the spread's expiry runs from its freshest filing (`2026-08-10` → `2026-09-09`), its content address moved (`122e0a7b…` → `22c5ce3d…`, re-pinned from verified output), and the memo's floor inherits an evidence-anchored child expiry | **FIXED-341** | Closed; see `CP14-F-41` for what the corrected producers did to this memo |

## The seventeen unclaimed gates, reconciled (2026-09-19)

Unique outstanding ids, from the specification's 29 minus the roster's 12
(`G02`, `G03`, `G17`–`G20`, `G22`, `G23`, `G26`–`G29`): **`G01`, `G04`, `G05`–`G16`,
`G21`, `G24`, `G25`** — seventeen. `CP14-F-37` named sixteen; `G04` was omitted.

| gate | kind | claim | existing control the coverage ruling rests on | status |
|---|---|---|---|---|
| `G05` | enrichment | the labeled dated diagnostic comparison | — | outside the launch objective |
| `G08`, `G09` | enrichment | template sections and evidence references | — | outside the launch objective |
| `G10`, `G14` | enrichment | peer benchmarks and thinness | — | outside the launch objective |
| `G11` | enrichment | the suppression rule | — | outside the launch objective |
| `G12` | enrichment | the inert `peer_basis` | — | outside the launch objective |
| `G01` | governed | empty-operator guard | `tests/products/test_empty_operator_halves.py::test_sabotage_removing_the_declared_half_is_red_naming_empty_operator_guard`; `tests/products/test_refusal_envelope.py::test_envelope_for_empty_operator_refusal` | **covered by SDK control** |
| `G04` | governed | the governing debt is computed, never read from `memo_context_debt` | SDK half — the served and recorded `D_c` is the scorer's assessment, carried verbatim: `tests/products/test_evidence_derived_debt.py` and the replay rehydration contract. CP-14 half — that this consumer's projection routes no table value into it — **no control exists** | **partial; the CP-14 half is exposed, not covered** |
| `G06` | governed | Policy before Similarity on the ordered trace | `tests/operators/test_planner.py::test_the_plan_runs_categories_in_dependency_order` (Policy → Similarity → Temporal → Traversal from a scrambled declaration) | **covered by SDK control**; the memo's own trace assertion is not written |
| `G07` | governed | tolerance comes from the policy version; boundary `<=` | SDK half — the tolerance is governed by the pinned policy bundle and its default: `tests/products/test_tolerance_exceeded.py::test_an_omitted_tolerance_takes_the_class_default_and_withholds_by_name`; `tests/products/test_policy_constraints.py` cases 1–3. CP-14 half — the `2025-07-01` version boundary and the `0.3003` specimen — **no control** | **partial; the date boundary is exposed** |
| `G13` | governed | a refusal carries the governing F / C / S decomposition with the tolerance in force | `tests/products/test_d_impl_338_refusal_evidence.py` (the refusal's evidence block carries the debt and factors) | **covered by SDK control** |
| `G15` | governed | determinism | in-process: `tests/products/test_delivery_determinism.py::test_a_fulfilled_product_is_the_same_determination_twice`; across processes: `tests/examples/test_cp_06_canonical_output.py::test_the_door_and_the_in_process_run_serve_one_content_address` and the cp-03-canonical cross-deployment suite | **covered** — the cross-process half by example gates outside CP-14, not by an SDK test |
| `G16` | governed | resolution and auditability kept apart (TRAP 1a) | cp-13-canonical's executing gates `CXRC-G01` / `CXRC-G02` (`tests/examples/test_cp_13_canonical_output.py`) | **covered by an example-level gate, not an SDK test** |
| `G21` | governed | mixing floors bind | `tests/products/test_composite.py::test_a_floor_declared_for_ANOTHER_signal_type_does_not_bind_this_one` (the gate's own sabotage, exactly), `::test_the_mixing_refusal_does_NOT_fire_when_the_floor_is_met`; `tests/products/test_d_impl_341_ttl_anchor.py::test_c11_a_composites_mixing_floor_is_measured_from_the_decision_instant` | **covered by SDK control** |
| `G24` | governed | the empty-string `sic` guard fires on CION | this is the consumer's own projection logic; **no SDK-level control can carry it** | **uncovered; stays open with the memo specification** |
| `G25` | governed | no policy, no serve — `as_of` before any policy version refuses with authority `technical` | SDK half — a required value absent after defaults is refused by name (`tests/products/test_policy_constraints.py::test_a_required_parameter_absent_after_defaults_is_refused`) and the refusal-authority vocabulary is closed (`tests/products/test_provenance_semantics.py`). CP-14 half — the policy-version lookup by date — **no control** | **partial; exposed** |

Of the ten governed claims, five rest fully on SDK-level controls (`G01`, `G06`,
`G13`, `G15` in-process, `G21`); two rest on example-level gates outside CP-14
(`G16`, and `G15`'s cross-process half); three are partial (`G04`, `G07`, `G25`:
the SDK mechanism is controlled, the CP-14-specific claim is not); one is
uncovered (`G24`). The ruling of 2026-09-19 accepts the SDK-level controls as
the launch evidence and does not require another implementation inside CP-14;
the partial and uncovered halves are CP-14 obligations that stay open with the
memo specification, which remains open. Nothing was deleted to make the count
fit, and nothing here is marked passed.

## Slice 2 — the second producer, and two children admitted at once (2026-09-15)

**The census.** Before anything was modified, the four unavailable producers
were classified under Dave's A/B/C vocabulary by four independent read-only
readers and an independent pass over the same trees:

| producer | class | verdict | why |
| --- | --- | --- | --- |
| cp-04-canonical (`reference.corporate-family@2.0.0`) | **A** | exposed in place | canonical shape maps one-to-one onto the road's three verbs; `capabilities=` is the one pass-through and the facade offers it; no door existed; the smallest tree (756 code lines) |
| cp-06 (`credit-risk.collateral-coverage`) | **B** | leave frozen; a sibling would be the route | mechanically close to A, but its pre-340 stdio door and `door.yaml` carry a declared gate (`CSC-G12`) whose subject the road deletes, its Π closes over an acquisition value (the commitment) the graph does not carry, and `D-IMPL-340`'s record treats the tree as frozen |
| cp-13 (`credit-risk.covenant-cross-reference`) | **B** | leave frozen; a sibling would be the route | Π and two debt factors close over the acquisition result carried in from the side, and the entitlement principal is a per-call argument on neither the request nor the perspective; frozen under `D-IMPL-340` |
| cp-05 (`credit-risk.exposure-rollup`) | **C** | STOP for this producer; classified below (`CP14-F-33`) | its gross/adjusted determination (`assembler.py::aggregate`) runs AFTER the declared traversal and BEFORE Π, in L4 by `D-IMPL-299`; the facade's post-operator hooks are `project`, `assess` and `gate` only |

**Chosen:** cp-04-canonical, the cheapest honest second producer — not the one
that gives the prettiest memo. Re-expressed in place (`produce.py` 96 → 33
code lines, `deployment.py` 223 → 112, `acquisition.py` 201 → 189, a 25-line
door, 24 lines of `replay:`/`ttl:`/`door:`, a 55-line environment document;
`backends.yaml` deleted; `projection.py` untouched); the served family's content
address at a pinned instant is byte-identical before and after
(`2da50196…`). Its own record: `examples/cp-04-canonical-corporate-family-tree/FINDINGS.md`.

**The two-child diagnostic** (spread tolerance 1.0, both doors live, the three
door-less producers unreachable): the canonical spread AND the family are
admitted simultaneously from two registrations under two producer tenants at
two producer-owned content addresses, both `provider-controls`, both at the
composite's instant; the consumer imported neither producer and read no
child-domain store; the composite still refuses on three required slots with
all five rows persisted. **This is a diagnostic, not the memo outcome.** The
real question at 0.25 still refuses: the spread withholds under the measured
estate state. Executable: `tests/examples/test_cp_14_second_slice.py`.

| Id | Finding | Category (§B) | Disposition |
| --- | --- | --- | --- |
| `CP14-F-33` | **cp-05 cannot be exposed through the paved road as it stands: its deterministic aggregation has no seam.** The exposure roll-up's gross/adjusted determination, guarantee-path de-duplication and reconciliation run today between the hand-run traversal and the governed call (`assembler.py::aggregate`/`enrich`/`reconcile`), which `D-IMPL-299` places in L4 after the declared traversal. `open_product` offers `project` (Π), `assess` (a `DebtAssessment`) and `gate` (a verdict) after the operators, and the operator vocabulary is closed — there is no declared home for a deterministic L4 aggregation on the road. The low road expresses it by ordering (aggregate, then `build_governed_resolver`), so a supported path exists | **2 · launch ergonomics candidate against `D-IMPL-343`** — §C step 1 yes (the low road serves the product today), step 2 open: every producer with a post-traversal aggregation step would leave the road for the whole spine | Raised for a ruling; not built around; cp-05 not converted |
| `CP14-F-34` | **`D-IMPL-343` R-11 named cp-04-canonical the canonical witness, and slice 2 re-expressed it.** The accepted design's R-11 held that cp-04-canonical "remains the canonical witness" for the `canonical` shape while its §8 row 2 planned this tree's re-expression; Dave's slice-2 instruction invited class A for `reference.corporate-family@2.0.0`. The witness role passes to the nine canonical trees that remain (cp-05 through cp-13); `CANONICAL_SHAPE_FLOOR` holds; `CFC-G07` now asserts `paved` under its unchanged node id | ruling synchronization — for Dave's confirmation at the slice review | Recorded |
| `CP14-F-32`, measured — **STOP** | **A refused composite that admitted at least one child cannot be replayed from the store that recorded it.** Measured on both diagnostic records (0.25: the family admitted, the spread withheld; 1.0: the spread and the family admitted, three slots unreachable): `GovernedResolver._retain_child_contracts` files admitted-child bytes on the NON-BLOCKING composition path only (`src/ccf/products/resolver.py`, the call under the blocked/unblocked branch of `resolve_child_outcomes`'s consumer), while `ccf.replay.engine.replay` rebuilds the child view from the store for ANY record with admitted rows (`_reconstruct_child_contracts`); replaying either refused record from the consumer's store raises `ReplayUnresolvable: the child contract '…' consumed for '…' is not retained in the store`. No retained immutable artifact resolves the address anywhere: the producer's own store holds its record and query pins, never the served product's bytes (the record names `product_content_address`), and the product is re-derivable there only by re-execution while the producer's fabric snapshot exists. `D-IMPL-338` made the five rows survive every exit; `D-IMPL-339`'s byte retention did not follow them. Dave's rule for this finding: reconstructing the refused parent requires those bytes and nothing retained resolves the address → **launch-level replay defect** | **1 · launch-blocking SDK capability** (§D: "replay and reconstruct governed decisions from the record and the store"; "preserve sufficient refusal evidence") — §C step 1: no | **STOP raised for a decision — then CLOSED by `D-IMPL-344` (2026-09-16, `d-impl-344-retention @ 8b8e93a0` + `b8212ac6`, merged into this branch at `860a142a`; not on `main`).** Nothing copied into CP-14. The measurement in this row stands as recorded. The proof that held the shipped defect (`…_cannot_be_replayed_from_its_own_store`, asserting the missing bytes and the `ReplayUnresolvable`) is replaced by `test_f32_a_refused_composite_that_admitted_a_child_is_reconstructed_from_its_own_store`: for BOTH records, every admitted address resolves from a fresh store instance and re-hashes, and `replay_refusal` reconstructs the refused determination from the consumer's own store after both producer processes have exited, consulting no plan, operator or product; `replay()` refusing the record by name is a secondary check, not the closure. Slice 1's diagnostic assertion that the consumer's store did NOT hold the admitted spread's bytes — the same defect asserted as expected — inverts with it |

## Slice 2 ACCEPTED (Dave, 2026-09-15) — as proof, not as a merge

What slice 2 proved, and only that: the family provider (`cp-04-canonical`)
re-expressed on the paved road with its product identity preserved
(`2da50196…` byte-identical before and after); two children admitted
simultaneously from two paved producers under two tenants at the `1.0`
diagnostic; and the distinct `0.25` result (the spread withheld, the family
admitted, the composite refused) preserved. **Coverage boundaries:** neither
result proves a served five-child memo, and neither proves a replayable refused
composite — that is `CP14-F-32`, now `D-IMPL-344` (OPEN — DESIGN,
`docs/D-IMPL-344-DESIGN.md`). No CP-14 implementation continues until 344 is
ruled and built; `CP14-F-33` stays a separate paved-road coverage finding whose
measurement belongs to the later exposure slice.

**Structural checks, resolved honestly (2026-09-16, a separate commit).** Two
reds in `tests/examples/test_artifact_schema_headers.py`
(`test_every_example_root_has_a_covered_artifact_directory` and
`test_every_example_roots_artifact_directory_is_non_vacuous`) enforce that every
driver-bearing example root carries a non-empty `artifacts/` directory whose
documents pass the header check — a No-Hardcoding obligation (CLAUDE.md §6.4),
not a shipped-product one. This tree owed exactly one such document already:
the roster leg's source vocabulary (spec §C.1, row "Obligor roster":
`memo_context_debt` ⋈ `legal_entity`), which `acquisition.py` had been carrying
as SQL literals. `artifacts/source-vocabulary.yaml` now declares the two tables,
the join key and the identity columns, and `acquisition.py` reads them from it.
Nothing else was added: no `gates.yaml` (the product-gates checker keeps this
tree at Gate 1 until a real roster appears), no invented evidence, no product
behavior change. The two slice proofs and the header check are the evidence
that the read moved and nothing else did.

## Slice 3 — the collateral slot re-pointed; three children admitted at once (2026-09-17)

**The re-point.** `producers.collateral` now names the paved successor
`cp-06-canonical-collateral-and-setoff-coverage-egress` under
`cp-06-canonical-demo` (`D-GATE-cp-06-canonical`, merged at `3d1433e2`; lane
`1.0.0` by payload measurement — the successor serves the frozen cp-06's product
byte for byte at the CP-14 instant). The endpoint and credential NAMES
(`CCF_CP14_COLLATERAL_URL` / `_TOKEN`) and the `offers` line did not move. **The
question did not move either** (`CP14-F-20`): the facility the memo's request
names is the child's subject and `facility_id`, the obligor is its borrower
scope, intent `lgd-assessment`, freshness `as-filed`, no tolerance — the
successor's own `CP-SPEC-006C` §B.2 fixes exactly that question.

**The three-child diagnostic** (spread tolerance 1.0, three doors live in three
processes): the canonical spread, the family and the collateral are admitted
simultaneously — three registrations, three producer tenants, three
producer-owned content addresses, all `provider-controls`; the collateral child
answers `FAC-5B8418` with a positive coverage ratio; the composite still refuses
on the two unreachable required slots (exposure, covenant, `producer-unavailable`)
with all five rows persisted.

**The real 0.25 result**, three doors live: the spread is withheld by its
producer and crosses as `ineligible` with the reason retained (`CP14-F-30`); the
family and the collateral — whose contract takes no tolerance — are admitted;
the composite refuses on its required spread.

**Both refused records reconstruct** from the consumer's own store after all
three producer processes exited (`D-IMPL-344`): every admitted child's bytes
retained at the row's address — three at 1.0, two at 0.25 — and `replay_refusal`
returning with those addresses, consulting no plan, operator or product.

Proof: `tests/examples/test_cp_14_third_slice.py` (6), with slices 1 and 2
unchanged (3 + 5) — 14 passed against the estate.

**Coverage boundaries, explicit.** Slice 3 proves three-of-five admission and
the reconstruction of a refused three-child composite. It does **not** prove a
served memo: the exposure slot has no paved producer (`CP14-F-33`, unruled — a
seam for post-traversal aggregation) and the covenant slot has none (cp-13 is
class B; a paved sibling on the `cp-06-canonical` route needs its own Gate 1
spec and ruling). Until both exist the composite refuses on a required slot at
every tolerance, which is the SDK working, not a defect. No `gates.yaml`, README
or page: the tree stays at Gate 1 for the product-gates checker.

## Backlog record (§I)

**Policy-derived request defaults.** *capability:* a request parameter's default
read from a Control Plane artifact selected by the decision instant (a policy
version's `debtToleranceDefault` at `as_of`). *evidence:* `CP14-F-29`. *current
supported path:* an explicit value on the request, or the deployment's own
`PolicyConstraintResolver` handed to `open_product(constraint_resolver=)`.
*friction:* the memo's headline scenario (§D.3 scenario 2 — the same obligor, a
different governed answer either side of 2025-07-01) needs the parent's Policy
step to select the version; one resolver class. *adoption impact:* any product
whose fitness threshold is policy-versioned. *launch necessity:* §C step 1 yes
(an explicit tolerance is a governed value); step 2 no. *scope/risk:* a
reference resolver over a ledger-read artifact; none to the paved road.
*recommended release:* with the parent-logic slice of this product.

## What this slice did not touch, by instruction

`D-IMPL-341`, `D-IMPL-342`; `D-IMPL-344` (built on its own branch, merged at `66be7cb8`); `artifacts/gates.yaml` (the tree is at
Gate 1 for the product-gates checker until a roster appears); the README; the
page; the scenario roster; the sabotage sweep; the four producers' trees.

## Completion — five children through five doors (2026-09-17, the consolidated GO)

**What was done.** The covenant slot re-pointed to the paved successor
`examples/cp-13-canonical-covenant-cross-reference` (`CP-SPEC-013C`, lane `1.0.0` by
measurement); the exposure slot reaches frozen cp-05 through the wrapper door
`examples/door-cp-05-credit-exposure-rollup` (exposure option 3, the escape hatch
measured in that tree's `FINDINGS.md`); the covenant question determined from the
obligor's own facility documents (`CP14-F-28`, closed below); Π reading every child
class by name and recording the address each section was composed from; twelve gates
claimed; the transcript of both runs committed. Executable:
`tests/examples/test_cp_14_fourth_slice.py` (9 passed) with the earlier slices (14 passed).

**The two questions, and what each yielded** — measured with all five producers live,
BGC Group at `2026-09-07T12:00:00+00:00`, facility `FAC-5B8418`, `memo_type` the class
default:

| tolerance | spread | family | exposure | collateral | covenant | composite |
| --- | --- | --- | --- | --- | --- | --- |
| **0.25** (governed) | withheld (`ineligible`; its `tolerance-exceeded` is the reason the composite retains, as the first blocking child) | admitted | withheld (`ineligible`; the row carries the admission verdict, not the producer's reason — `D-IMPL-342`) | admitted | withheld (`ineligible`; likewise; the producer's own measure is D_c 0.80 on BGC's two anchors) | **refused** `composite-child-refusal`, five rows, both admitted contracts retained by bytes |
| **1.0** (diagnostic) | admitted | admitted | admitted (D_c 1.0 `fail_closed`) | admitted | admitted | **served** — D_c 1.0 `fail_closed`, F 0 (exposure), C 0.2000 (covenant), S 0.8333; expires 16:00 with the exposure child; the product and record addresses are in the committed transcript, printed separately |

Neither outcome was promised and nothing was tuned: the diagnostic serves BECAUSE the
tolerance is one nobody would act on, and it serves `fail_closed`.

**The four proofs the GO required**, each executable and each distinct in its evidence:

| proof | evidence | source |
| --- | --- | --- |
| a meaningful child-content change changes the corresponding parent field | the collateral child asked without haircuts (a CONTROLLED variant, identified as such): its section's coverage ratio and collateral-after-haircuts move, its set-off does not, its address and the memo's address move, the other four sections and addresses do not | controlled test |
| every printed field is the declared child member | each of the 28 section fields equals the member of the retained child the test independently declares for it, or its one stated transformation (a count); the two corrected lookups are held non-vacuously (a child with non-zero set-off; a spread whose `obligor` block carries no `basis_applied`) | the diagnostic run |
| product identity is not record identity | the served product's content address equals the persisted record's `product_content_address` and differs from the record's own address; both are printed separately by `run.py` | the diagnostic run |
| the same question twice yields one product | a bounded repeat of the diagnostic in a second opened product yields the same five child addresses and the same product address — distinct from replay | a second in-session ask |
| acquisition and composition use the same admitted contracts | every section's `child_content_address` equals its admission row's; the memo's lineage is the set-union of its own operators with the five children's | the diagnostic run |
| served reconstruction uses retained inputs without calling providers again | with every producer process exited, replay rebuilds the child view from the retained contracts, hands it to the memo's plan factory, re-executes and reproduces the served product's address exactly | the diagnostic run's record |
| refused reconstruction preserves the admitted-child evidence and follows the recorded path | `replay_refusal` returns exactly the two admitted addresses, consults no plan, and reports the recorded no-fabric-read path; `replay()` refuses the record by name | the governed run's record |

### Findings raised by the completion

| Id | Finding | Category (§B) | Disposition |
| --- | --- | --- | --- |
| `CP14-F-28` | **CLOSED.** The covenant question is determined from the roster's facility document keys joined to the ledger's evidence anchors; the mapping reads nothing below the anchor. BGC's one document carries two anchors and the child answered exactly those | — | closed by this slice |
| `CP14-F-33` | **STANDS as a paved-road coverage limitation.** Exposure aggregation stays where `D-IMPL-299` put it; the slot is served through the standard door's structural hatch over the frozen low road, at the cost `door-cp-05/FINDINGS.md` measures (~80 code lines, nothing re-implemented). This producer proves nothing about the facade's support for post-traversal aggregation | 3 · post-launch, ruled | recorded; no facade change |
| `CP14-F-34` | **The question mapping receives no source settings.** The road hands `questions(requirement, request)` the requirement and the effective request only; a mapping that must READ to determine a question (the covenant sources) has no seam for the deployment's resolved sources. Bound late: `produce.product` binds `opened.sources` onto the mapping object after open, so the settings are resolved once by the SDK from the environment document and never a second time. ~6 lines; the seam is honest but undeclared | 3 · SDK friction (§E "custom glue"); a supported path exists | recorded; backlog candidate below |
| `CP14-F-35` | **An open SDK evidence question: the child question's identity is an address, not a retained artifact.** The row carries `child_question_address`; the consumer's store does not hold the question at that address. Reconstructing the parent from the retained child CONTRACTS is not reconstructing the exact historical child QUESTION, and re-invoking today's source-reading mapping (which the proof does) is not proof of the latter — the sources it reads could have moved. Not a convenience; not repaired here | open SDK evidence question (§B), beside `D-IMPL-342` | recorded, unrepaired |
| `CP14-F-36` | **The served memo is `fail_closed` at every tolerance that serves it.** Inherited debt is the per-factor minimum and the exposure child's freshness is 0 against its four-hour λ_c on this estate's balances; C is 0.2 from the covenant child. Correct, and a statement about the estate: the memo cannot be served fit-to-act-on without fresher exposure balances. Because that child already sits at D_c 1, the composed scalar and `max(child D_c)` coincide here: the estate shows per-factor propagation, and the scalar counterexample is held by an isolated control (`test_the_per_factor_minimum_differs_from_the_scalar_maximum_on_an_isolated_control`), never by tuning | 4 · engineered-estate limitation | disclosed in README and summary |
| `CP14-F-37` | **Seventeen of the spec's twenty-nine gates are not exercised — a SCOPE status, not an estate limitation and not an SDK gap.** Two kinds, kept apart (spec §0.0a): *optional memo enrichment* the consumer has not written — template sections and evidence references (`G08`, `G09`), peer benchmarks and thinness (`G10`, `G14`), the suppression rule (`G11`), the dated diagnostic comparison (`G05`), the inert `peer_basis` (`G12`); and *governed behavior not yet put under test* — the policy-version tolerance and its boundary (`G07`, `G25`), the refusal's governing decomposition (`G13`), policy-before-similarity on the memo's trace (`G06`), mixing floors (`G21`), the empty-`sic` guard (`G24`), the empty-operator guard (`G01`), TRAP 1a (`G16`), determinism across independent processes beyond the bounded in-session repeat (`G15`). Named, none marked passed, none deleted | scope (unbuilt) | the roster declares only the twelve executed. **Reconciled 2026-09-19 (launch-scope ruling):** the count of seventeen is right — 29 declared in `CP-SPEC-014` §G, 12 executing on the roster — and the list above named sixteen: **`G04` (the governing debt is computed, never read) was the unnamed seventeenth, and it is a governed claim, so the split is seven enrichment / TEN governed**, not nine. The seven enrichment gates (`G05`, `G08`, `G09`, `G10`, `G11`, `G12`, `G14`) are outside the SDK launch objective. For the ten governed claims the ruling is that they rely on their EXISTING SDK-level controls and need no further implementation inside CP-14; the controls are cited per gate below, and where a gate's CP-14-specific half has no control that is exposed rather than marked covered. The full memo specification remains open |
| `CP14-F-38` | **`CP14-F-29` stands**: the tolerance default from the policy version is stated (0.25) and not derived | 3 · post-launch | unchanged |
| `CP14-F-39` | **Two child readings and one identity label were wrong in the delivered result (Dave, correction pass 2026-09-17).** The collateral section printed the child's `coverage.total` (collateral PLUS set-off) as `collateral_after_haircuts`; the spread section read `basis_applied` under the child's `obligor` block, where the producer does not put it, and printed `NOT_EVALUABLE` for a value the child served; `run.py` printed the replay record's address as the product's. Using the correct admitted child does not prove the parent read its fields correctly. Repaired: the section table names every field's child member and its one transformation (`projection.SECTION_FIELDS`), an independent test holds every field to the retained child, and the runner prints the product and record addresses separately and asserts the record names the product | consumer mapping defects, FIXED | the memo's payload and product address changed accordingly; the children's addresses did not |
| `CP14-F-41` | **The collateral producer's corrected expiry passed through this memo, and was resolved by a calibration ruling (`D-IMPL-341`, 2026-09-18).** When `D-IMPL-341` first made the collateral child's expiry run from its evidence, that child was refused `ttl-refusal` / `ttl-bounds` at the CP-14 instant — `FAC-5B8418`'s one asset was valued `2025-12-20` against a one-day window — so a required slot was `ineligible`, the composite refused `child_admission` at every tolerance, and BGC's memo served at no instant. Ten served-memo proofs across slices 3 and 4 were quarantined `xfail(strict=True)` naming the producer's calibration question rather than being weakened. **Dave ruled that question the same day** (cp-06-canonical `CP06C-F-05`): the collateral window follows the valuation cadence it anchors on. The child serves at the CP-14 instant again, all ten proofs converted back to normal passing tests on their ORIGINAL assertions, and the two consequence tests written while the question was open were deleted. What this memo inherits is a child expiry anchored on a valuation (`2026-12-20` for BGC) rather than on the question | 2 · resolved upstream by a producer calibration ruling | Closed 2026-09-18; the conversions are listed in `docs/D-IMPL-341-DESIGN.md` §12.9 |
| `CP14-F-40` | **`memo_type` promised templates the implementation never selected.** The contract described four templates while the label was carried into the payload unread. Closed to the implemented `annual-review` through `argument_domains`; a request naming another is refused `not-in-domain` before any producer is asked | contract alignment, FIXED | the other templates stay planned obligations of the spec |

**Carried, unchanged, and launch-level:** `D-IMPL-341` (`CP14-F-31`), `D-IMPL-342` (`CP14-F-30`),
`D-IMPL-304` (the exposure wrapper's pre-resolution carry, `CP05D-F-04`),
`CP06C-F-01` (the hand-assembled replay environment — the composite variant is its fourth copy).
"No launch blocker newly raised by this package" is the whole of the claim: the three open
SDK items above remain open launch-level findings, and this package does not close them.

### Accepted scope, and capability not exercised

**This delivery proves five-provider acquisition, admitted-content composition, governed
refusal, and reconstruction. It does not complete the full memo-assembly specification.**
Not built: the memo's own assembly beyond the obligor's identity and the five sections —
template sections, evidence references, peer benchmarks, the relationship summary, the
policy-version tolerance and the dated diagnostic comparison (spec §B.1, §D.2; `CP14-F-37`
keeps enrichment and untested governed behavior apart). Not shown: a served memo at the
governed tolerance; determinism across independent PROCESSES (the bounded in-session
repeat is shown); the scalar difference from `max(child D_c)` on this estate (held by an
isolated control).

### Sabotage record (completion)

Run by hand on the candidate after the build, restored by copy and verified with `diff -r`; one run of the completion suite each (nine tests at the first delivery, thirteen after the correction pass), five doors live.

| sabotage | applied to | red | green |
| --- | --- | --- | --- |
| S28 — the collateral section's coverage composed from a constant, not the admitted contract | `projection.py` | `CMC-G28` (the controlled variant) alone — the constant equals today's measurement, so the same-contracts proof stays green; which is why the variant exists | the other 8 |
| S27 — a `collateral_pledge` read added to the consumer's leg | `acquisition.py` | `CMC-G27` alone | the other 8 |
| S23 — `resolve_child_outcomes` imported into the consumer | `deployment.py` | `CMC-G23` / `G27` (one test) | the other 8 |
| SMAP1 — the collateral figure read from the child's `coverage.total` (the delivered defect) | `projection.py` | the field-mapping control alone | the other 12 |
| SMAP2 — the spread's basis read under the child's `obligor` block (the delivered defect) | `projection.py` | the field-mapping control alone | the other 12 |
| S28 (rerun after the correction) — the coverage ratio read from a member the child does not carry | `projection.py` | the field-mapping control; `CMC-G28` (the variant) | the other 11 |
| S28b — the covenant question asked with no sources (the pre-completion shape) | `deployment.py` | 6: the diagnostic serve, the same-contracts, per-factor, variant, covenant-question and served-reconstruction proofs | 3: the governed refusal, its reconstruction, the consumer's shape |
