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
| `CP14-F-31` | **`D-IMPL-341` / F-01, inherited.** The admitted spread's `expires_at` is decision-anchored by the SDK despite the class's `from_entity_freshness` declaration; the memo's expiry floor inherits it as-is. Not repaired, not described as filing-anchored | **open SDK finding, ruled** (`D-IMPL-341`) | Disclosed; the spread's own gate still holds its filing window |

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
| `CP14-F-32`, measured — **STOP** | **A refused composite that admitted at least one child cannot be replayed from the store that recorded it.** Measured on both diagnostic records (0.25: the family admitted, the spread withheld; 1.0: the spread and the family admitted, three slots unreachable): `GovernedResolver._retain_child_contracts` files admitted-child bytes on the NON-BLOCKING composition path only (`src/ccf/products/resolver.py`, the call under the blocked/unblocked branch of `resolve_child_outcomes`'s consumer), while `ccf.replay.engine.replay` rebuilds the child view from the store for ANY record with admitted rows (`_reconstruct_child_contracts`); replaying either refused record from the consumer's store raises `ReplayUnresolvable: the child contract '…' consumed for '…' is not retained in the store`. No retained immutable artifact resolves the address anywhere: the producer's own store holds its record and query pins, never the served product's bytes (the record names `product_content_address`), and the product is re-derivable there only by re-execution while the producer's fabric snapshot exists. `D-IMPL-338` made the five rows survive every exit; `D-IMPL-339`'s byte retention did not follow them. Dave's rule for this finding: reconstructing the refused parent requires those bytes and nothing retained resolves the address → **launch-level replay defect** | **1 · launch-blocking SDK capability** (§D: "replay and reconstruct governed decisions from the record and the store"; "preserve sufficient refusal evidence") — §C step 1: no | **STOP raised for a decision.** Nothing copied into CP-14. The proof `test_f32_a_refused_composite_that_admitted_a_child_cannot_be_replayed_from_its_own_store` holds the shipped defect and goes red when the SDK retains admitted bytes on every exit |

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

`D-IMPL-341`, `D-IMPL-342`, `D-IMPL-344` (designed separately on its own branch); `artifacts/gates.yaml` (the tree is at
Gate 1 for the product-gates checker until a roster appears); the README; the
page; the scenario roster; the sabotage sweep; the four producers' trees.
