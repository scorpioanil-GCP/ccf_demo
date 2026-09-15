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

`D-IMPL-341`, `D-IMPL-342`, `D-IMPL-344`; `artifacts/gates.yaml` (the tree is at
Gate 1 for the product-gates checker until a roster appears); the README; the
page; the scenario roster; the sabotage sweep; the four producers' trees.
