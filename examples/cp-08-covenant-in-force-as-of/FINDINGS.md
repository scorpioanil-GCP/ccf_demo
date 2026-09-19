# Findings — cp-08 covenant-in-force as-of

**This file is cp-08's authoritative findings record.** Every `CP08-F-NN` id
cited anywhere in this tree resolves here, and nowhere else. Where the decision
log (`docs/DECISIONS.md`) and an earlier draft of the specification described
the same facts under shifted numbers, this file is the reconciliation, and §0
says exactly what moved.

Findings are evidence. Each one below states what was measured, against what,
and what the product did about it. A finding is never closed by prose alone.

---

## 0 · Provenance of these ids, because they moved once

The ids were minted at Gate 1 in the specification's §F.3, which the
engineer-voice rewrite (`df6742a9`) removed without relocating them. In the
interval `D-IMPL-329` described the two constraints Gate 2 inherits, and
numbered them `CP08-F-03` and `CP08-F-04` against content that the Gate-1 spec
had carried as `CP08-F-04` and `CP08-F-02`. Nothing false was ever published —
the *facts* are identical in both records — but for one sitting the same id
named two different claims, and a citation in the tree could not be resolved.

**The numbering below is the one that now stands**, chosen to match what the
tree actually cites rather than to match either prior document:

| id | claim | why this number |
|---|---|---|
| `CP08-F-01` | the SDK refused a relative default of `offset_seconds: 0` | unchanged since Gate 1 |
| `CP08-F-02` | the estate marks no covenant supersession, so `include_superseded` is refused | unchanged since Gate 1; cited at `ccf_config.yaml`'s `unsupported_arguments` |
| `CP08-F-03` | `assertedAt` is on amendments, never on covenants | `D-IMPL-329`'s numbering, which is Dave's ruling record |
| `CP08-F-04` | covenant terms cannot be reconstructed for a past date | `D-IMPL-329`'s numbering; the four citations in the tree already use it |
| `CP08-F-05` | the TTL anchor reads the scored view, not the served set; the demonstration expires under truthful bookings | raised 2026-09-18 under `D-IMPL-341`'s validation pass |

**The Gate-1 `CP08-F-03` is WITHDRAWN and is not reused.** It claimed *"112 of
137 amendments carry no `assertedAt`"* and was a count over the wrong
population. It is not restated here as a finding because it was never true of
this product; `spec/MEASUREMENT-NOTE.md` §2 carries the correction, the
measurement that produced it, and the rule it yielded.

---

## `CP08-F-01` — a relative default could not express "the request's own instant"

**Status: RESOLVED.** `D-IMPL-328` (Dave, 2026-09-11). Fixed in the SDK, in its
own commit, before any cp-08 code was written.

**What was measured.** `RelativeDefault` refused `offset_seconds: 0`. cp-08's
`as_of` and `known_as_of` both need exactly that: their default is *today* and
*now* — the request's own instant, unchanged.

**Why the workarounds were worse than the gap.** A literal date in
`ccf_config.yaml` is a date that ages silently, which is the defect `CP07-F-03`
measured one rung earlier. Computing it in `deployment.request` puts a
governance value back into deployment code and gives one bound a second
authority (`D-IMPL-315`) — and does so for the one parameter whose entire
subject is *which instant governed this decision*.

**The resolution.** Zero is admitted as the identity offset. Authority,
provenance and replay treatment are identical to any other offset: the resolved
absolute value is recorded with `authority=default`, not a rule recomputed
later. The offset rule now refuses only a *positive* offset, because a default
may not reach into the future.

**Where it is cited.** Nowhere in this tree, and that is correct: the finding
is resolved, so `ccf_config.yaml`'s `relative_defaults` block cites
`D-IMPL-328` — the decision that closed it — rather than the finding it closed.

---

## `CP08-F-02` — the estate marks no covenant supersession, so the parameter is refused rather than answered

**Status: CLOSED as a scope decision.** Not a defect to repair, and not
something this product may design around silently.

**What was measured**, three ways, all negative:

- `supersededBy` appears on **0 of 180 covenants**, at every ledger point
  sampled.
- Covenant thresholds are **unchanged across the entire ledger** — 180 at
  `t:1500` through head `t:5591`, zero changed and zero added at every point.
- **No covenant interval is ever closed** — `validTo` is constant at 2.

The ledger does carry **1,107 supersession markers**, and they belong to
`WarningSignal`, `CreditRating`, `IssuanceEvent`, `PolicyVersion` and others —
**not to the covenant slice this product reads.** A count taken across all of
them describes the ledger, not this product.

**What the product does.** `include_superseded` is declared and **refused by
name**, with its reason, through the request contract's
`unsupported_arguments`. It is not answered with an empty set.

**Why the refusal rather than an empty set, which is the whole finding.** An
empty superseded set is an *affirmative claim* — it reads as *"nothing was
superseded"*, which this estate cannot support. A refusal says *"this product
cannot answer that"*, which is true. The two are opposite statements wearing
the same shape, and only one of them is honest here.

**Where it is cited.** `ccf_config.yaml`'s `unsupported_arguments`.
**Gated by** `CIF-G10` — the refusal is asserted by name, with its declared
reason, by an executing test.

---

## `CP08-F-03` — `assertedAt` is on amendments, never on covenants

**Status: NOT-A-GAP** (`D-IMPL-261` charter vocabulary). It is a standing
constraint on any successor, not an outstanding work item, and the shipped
implementation honors it. `D-GATE-cp-08` records it as remaining explicit.

**What was measured.** `ex:assertedAt` appears on **0 of 180 covenants** — on
all three booking-lag facilities and across the whole ledger at every point
sampled. It lives on the **amendment** nodes. So nothing on a covenant can be
filtered by `known_as_of`, and the covenant set is identical either side of a
booking gap.

One level up it is real and load-bearing: `AMD-01BB3F-2` carries
`validFrom 2025-08-14` and `assertedAt 2025-10-05`, so it is excluded at
`known_as_of=2025-09-09` and admitted after.

**The rule this leaves, and it is the only part that survives.** The product's
bitemporal subject is **the amendment slice**. An implementation may filter
amendments by `known_as_of`, and **must not pretend covenants carry an
`assertedAt` field**.

**What does NOT survive.** The Gate-1 wording of this id added *"112 of 137
amendments carry no `assertedAt`"* and built a debt metric on it. That count
ranged over every `ex:amends` edge in the ledger; this product reads the **25**
that point at a credit facility, and **all 25 carry both clocks**. The claim,
the metric and two gates were withdrawn together. See `MEASUREMENT-NOTE.md` §2.

**Gated by** `CIF-G02`, `CIF-G03` and `CIF-G06` — a later `known_as_of` admits
no fewer amendments; across a booking gap the two clocks admit different
amendment sets; and every omitted amendment is accounted for by axis.

---

## `CP08-F-04` — covenant terms cannot be reconstructed for a past date

**Status: ESTATE-LIMITATION** (`D-IMPL-261` charter vocabulary). Not this
product's to fix and not an outstanding work item: it is a property of the
estate, not of the assembly. `D-GATE-cp-08` records it as remaining open in
that sense — what would close it is an estate wave, not a change here.

**What was measured.** Covenants carry no assertion time (`CP08-F-03`) and no
supersession marker (`CP08-F-02`), and their thresholds never change. The
estate's covenant history is a single staged load, not an amendment lifecycle.
**There is nothing for time-travel to reconstruct.**

**What the product does.** It serves the **current** covenant terms beside a
**historical** amendment answer, and labels them unversioned — as a payload
field, not as prose in a README. That is the one place a consumer could mistake
this for a product that reconstructs covenant state.

**Why the label rather than omission.** The terms are genuinely useful context
for the amendment answer. Dropping them would make the product less useful
without making it more honest; serving them unlabelled would make it less
honest without making it more useful.

**What would close it.** An estate wave that versions covenant terms. The same
two-axis cut would then apply to the terms as well as to the amendments,
without changing this product's shape.

**Where it is cited.** `acquisition.py`, `projection.py`,
`artifacts/source-vocabulary.yaml`, `ccf_config.yaml`.
**Gated by** `CIF-G12` — the served covenants are labelled unversioned.

---

## `CP08-F-05` — the anchor is read from the scored view, and truthful bookings expire the demonstration

**Status: raised 2026-09-18 under `D-IMPL-341`'s validation pass; the spec's words and the mechanism's set differ, and the difference is stated rather than tuned away.**

### What changed in this tree

`deployment.ingest` now stamps each amendment claim's `valid_from` with its
`assertedAt` — the booking date, this product's assertion-time axis — and the
`amendment` λ_c row declares `decay_basis: valid-from`. Two consequences,
both measured against the estate:

- **Freshness moves.** The reference curve ages an amendment from when the
  ledger booked it: 0.94 on the demonstration facility's booking day, 0.83 at
  the end of the 180-day window. Before 341 every observation was dated by the
  run that ingested it and `F` read 1 by construction (`produce.py`,
  `README.md` and `spec/MEASUREMENT-NOTE.md` §2 all said so; the first two are
  corrected, the note is the historical measurement).
- **The expiry runs from the evidence.** `expires_at` is the freshest booking
  among the facility's amendments at or before the question plus the amendment
  half-life, recorded as `ttl_anchor_at`. `FAC-01BB3F`'s freshest booking is
  `2025-10-05`, so its window closed `2026-04-03T00:00Z`; a wall-clock question
  has been refused `ttl-refusal` / `ttl-bounds` since, and stays refused until
  the ledger books a newer amendment. Until 341 the same question served with
  an expiry that ran from the question and never aged. **The refusal is the
  correct answer**, asserted as
  `test_the_wall_clock_question_is_refused_because_its_evidence_has_expired`;
  the serving tests now ask on the booking day (`INSTANT`), the natural instant
  inside the window, as the positive control. No data, window or tolerance was
  moved.

### The precise mismatch

`CP-SPEC-008` §E.3 says the TTL is "anchored on the latest assertion among the
**served** set". The mechanism `D-IMPL-341` rules (R-1) anchors on the freshest
`valid-from` leading edge **in the observation set the freshness factor scores**
— the admitted view, which for this product is every amendment of the facility,
including those Π then excludes on either axis. Measured: a closed question
(`as_of` = `known_as_of` = `2025-09-09`) serves `AMD-01BB3F-1` alone, excludes
`AMD-01BB3F-2` on the assertion axis, and anchors on `-2`'s booking
(`2025-10-05`) all the same. The two readings coincide for a live question and
diverge for a closed one. Which set the spec should name — or whether the
mechanism should read Π's served set — is a ruling, not this tree's call.
`CIF-G15` (the dual TTL) is the gate that would give a closed answer its own,
longer window; it stays unimplemented by the same ruling.

### Sabotage, run and restored

The SDK's S1 — `resolve_ttl_anchor` returns the decision instant for an
evidence-anchored class — turns both new controls red
(`test_the_expiry_runs_from_the_freshest_booking_not_the_question`,
`test_the_wall_clock_question_is_refused_because_its_evidence_has_expired`): the
expiry runs from the question again and the wall-clock question serves. Restored,
`cmp` verified, 2026-09-18.

### What the estate could not supply

Covenant and facility claims stay dated by the request instant: the estate
carries no assertion date on a covenant (`CP08-F-03`) and no timestamp on the
facility record, and their rows keep the `observed-at` basis. Only the
amendment row — the moving part — reads a source clock.

## Carried gates — declared in the specification, not in the roster

These are **not** `CP08-F-NN` findings and are not given ids here; their
authority is `CP-SPEC-008` §G.1 and §G.3, and their absence from
`artifacts/gates.yaml` is what makes them visible. Recorded here so a reader of
this file sees the whole outstanding picture in one place.

| gate | why it is not declared |
|---|---|
| `CIF-G07` | specified against amendments with no booking date. This estate's facility slice has none, so the gate could not fail. Id left empty, not reused. |
| `CIF-G13` | asserted the replay property `CIF-G16` now carries, but read the citation from an attribute `ProductLineage` does not have, so its subset test could not fail. Restated under a new id rather than repaired under the old one. |
| `CIF-G14` | watched a debt ratio that reads the same on every answer. Withdrawn with the metric. Id left empty, not reused. |
| `CIF-G15` | the dual TTL. **Specified and deliberately not implemented** — where *closed* ends and *live* begins is an operator's policy decision rather than one this deployment may take. Carried open; its behavior must not be invented. |

---

## What this rung established

**Booking lag proves two clocks. It does not prove covenant supersession.**
The two claims were measured apart, on instruction, and they came back
differently: the first holds on amendments, the second is absent from the
estate entirely. A product may not teach a property its data does not have.

**A count is only as good as the population it ranged over.** State the
population in the same breath as the number. *"137 amendments"* describes the
ledger; *"25 facility amendments"* describes this product. Only the second
belongs in a specification.

**Configuration that nobody reads is documentation, not control.** (Dave,
2026-09-11.) This rung's λ_c table was keyed on three descriptive labels no
consumer ever resolved, and was found only when a defaultless scorer refused to
build without it. Ask of any table, threshold or roster: what reads this, and
what breaks if I change it?
