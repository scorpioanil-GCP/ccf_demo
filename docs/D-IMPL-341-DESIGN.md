# D-IMPL-341 — design: `expires_at` describes when the evidence stopped being current

**Status: COMPLETE, awaiting merge review (2026-09-18) on `d-impl-341-expiry` — the ruled mechanism
unchanged, four example trees migrated, two in-scope SDK defects corrected (§12.6(f), §12.7), and
Dave's three closing rulings applied (§12.8). Merge HOLD, not merged. §0–§11 are the design as accepted with Dave's five rulings (R-1–R-5, recorded in
`docs/DECISIONS.md` before implementation); §12 records what was built, where it differs, and
every measurement — including the one the design got wrong.** Design baseline
`main @ f8c33898` (post-`D-GATE-342`), design at `f55915d2`. The decisions of record are
`docs/DECISIONS.md` `D-IMPL-341` (OPEN, 2026-09-15, from `CP03C-F-01`), `D-IMPL-31` (TTL at
two granularities with a declared derivation), `D-IMPL-308` (the TTL runs from the decision
instant, never collapsed onto the graph boundary), `D-IMPL-331` (a λ_c row declares which of
an observation's two instants it decays against; `valid-from` with no instant is refused by
name, never fallen back) and `D-IMPL-336` F14 (the composite floor).

**The contract this design locks (Dave, 2026-09-18):** *`expires_at` must describe when the
evidence stopped being current, not when the decision happened. A decision-time anchor can
overstate validity: if the evidence was already old when the decision was made, serving
`decision_time + ttl` advertises a validity window the evidence never had.* Until 341 ships,
CP-14 must not interpret an inherited child expiry as proving a filing-anchored freshness
window (§8).

Every citation is a `file::symbol` that resolves on `f8c33898`; methods are named in prose
beside their class.

## 1 · Baseline behavior on `f8c33898`

1. **The mint.** `__call__` on `src/ccf/products/resolver.py::GovernedResolver` computes
   `expires_at = decided_at + product_ttl_seconds` on the non-composite branch, where
   `decided_at` is the class's declared decision-instant parameter off the effective request
   or `asked_at` (`D-IMPL-308`). The class's declared
   `src/ccf/products/contract.py::TTLAnchor` (`from_decision | from_entity_freshness`) is
   copied onto the contract as `ttl_anchor` and read by nothing: the declaration is recorded
   and not computed.
2. **The composite branch** calls `src/ccf/products/composite.py::compose_children` with
   `ttl_anchor_at=decided_at`; `src/ccf/products/composition.py::compose_expiry` then takes
   `min(decided_at + ceiling, min over admitted children's expires_at)` — F14's floor, anchored
   on the decision instant for the parent's own term.
3. **Gate 3** (`src/ccf/products/gates.py::_refuse_ttl`, `src/ccf/products/gates.py::TTLRefusal`)
   holds `now < expires_at <= now + MAX_TTL` with `now = decided_at` and the ceiling from the
   pinned `src/ccf/products/contract.py::MaxTTL`. Under decision anchoring the lower bound can
   never fire.
4. **The evidence clock already exists and is already governed.** Every claim carries two
   instants — `observed_at` (when the fabric learned it) and `valid_from` (when the source
   observed it) — and each λ_c row declares which one it decays against
   (`src/ccf/controlplane/artifacts.py::HalfLifeEntry` `decay_basis`, `D-IMPL-331`). The
   freshness factor `F` is measured over one observation per entity record the execution's
   view carries (`_observations` on `src/ccf/products/debt_scorer.py::AssemblyDebtScorer`),
   reduced per series to its newest member as of the decision instant
   (`src/ccf/halflife/decay.py::leading_edge`, `D-IMPL-333`), by that same clock
   (`src/ccf/halflife/decay.py::_instant_for`). **Nothing reads that clock for `expires_at`.**
5. **The record** pins the `MaxTTL` and `src/ccf/controlplane/artifacts.py::TtlBinding`
   artifacts on dimension 2 (`src/ccf/replay/record.py::PolicyBinding`) and carries the
   decision instant, but no anchor instant. Replay environments rebuild the envelope
   themselves — cp-06-canonical's `_FreshEnvironment` computes
   `expires_at = temporal_boundary + ttl` — and `src/ccf/replay/engine.py::replay` holds the
   rebuilt product to the recorded content address.
6. **Measured overstatement** (the OPEN entry): the canonical spread's freshest filing
   2026-08-10, asked 2026-09-07T12:00Z, declared expiry 2026-09-09T00:00Z, served `expires_at`
   2026-10-07T12:00Z. Two gates hold the declaration as strict expected failures:
   `tests/examples/test_cp_03_canonical_output.py::test_expires_at_is_anchored_on_the_filing_not_the_question`
   (`OFC-G07`) and
   `tests/examples/test_cp_06_canonical_output.py::test_expires_at_is_anchored_on_the_freshest_valuation_not_the_question`
   (`CSCC-G23`).

## 2 · Affected classes and their current anchor settings

| class (tree) | `ttl_anchor` | window / ceiling | source instant on its claims today | λ_c `decay_basis` | expiry gate today |
|---|---|---|---|---|---|
| `credit-risk.spread` (cp-03-canonical) | `from_entity_freshness` | 30 d / per config | **filing date** as `observed_time` (`valid_from`) | `valid-from` on all three rows | `OFC-G07` xfail |
| `reference.corporate-family` (cp-04-canonical) | `from_entity_freshness` | 30 d / 180 d | **none** — `observed_time=at` (the request instant); the acquisition reads no GLEIF assertion date | default `observed-at` | none |
| `credit-risk.collateral-coverage` (cp-06-canonical) | `from_entity_freshness` | per config | **none on claims** — `observed_time=at`; the per-asset `valuation_date` is in the payload only | default `observed-at` | `CSCC-G23` xfail |
| `credit-risk.covenant-in-force` (cp-08) | `from_entity_freshness` | 30 d / 180 d | **none on claims** — `observed_time=at`; amendments carry `asserted_at` (optional; covenants none) in the payload only | default `observed-at` | none |
| `credit-risk.covenant-cross-reference` (cp-13-canonical, and frozen cp-13) | `from_decision` | 7 d / 14 d | anchors only; the estate carries no temporal predicate on definitions, passages or terms | `supersede-only`, no basis | `CXR-G03` (decision instant + ceiling) |
| `credit-risk.credit-memo-context` (cp-14, composite) | `from_decision` | 12 h ceiling | n/a — floors on its children | one-year rows | `CMC-G03` (floor) |
| `credit-risk.exposure-rollup` (frozen cp-05, wrapper door) | `from_decision` | per config | n/a | — | (spec §B.1 element 3) |
| cp-07, cp-09, cp-10, cp-11, cp-12 | `from_decision` | per config | `valid-from` rows on cp-09–cp-12's moving series | mixed | `TLP-G03`, `RSM-G03`, `EWS-G03`, `FXR-G04` (decision instant + ceiling) |
| frozen cp-01, cp-02, cp-03, cp-04 (hand-composed, not on the governed path) | `from_entity_freshness` by hand | — | source instant carried; `expires_at()` computed in the deployment | — | own gates (e.g. `FTS-G01`); untouched |

Two facts the table makes visible. Only one governed class (cp-03-canonical) already carries
the evidence instant on its claims under a `valid-from` row. The other three
`from_entity_freshness` classes declared the anchor and never gave the fabric the instant it
would need — the same "declared, not carried" shape `D-IMPL-331` closed for `F`.

## 3 · The authoritative clock, by product class

**The rule, stated once.** For a class declaring `from_entity_freshness`, the anchor instant is
derived from the SAME evidence the freshness factor is scored over and by the SAME clock:

- the observation set is dimension 1's — one observation per entity record the execution's
  view carries, exactly as `AssemblyDebtScorer._observations` builds it;
- reduced per series to its leading edge as of `decided_at` (`leading_edge`), so a replay at an
  earlier instant sees the edge that was leading then;
- **only observations whose λ_c row declares `decay_basis: valid-from` contribute**, and the
  instant taken is that row's own — `valid_from`, the source's instant. An `observed-at` row's
  instant is when the fabric learned the claim, which is not evidence currency
  (`D-IMPL-331`'s measured defect) and is never used as an anchor;
- the anchor is the **freshest** of those leading edges (the reference `derivation`; §10 R-1),
  and `expires_at = anchor + product_ttl_seconds`, still capped by gate 3's ceiling
  `decided_at + max_ttl_seconds`.

No new timestamp is minted anywhere. The clock is the one the deployment already declared
for decay; a deployment that wants an evidence-anchored expiry must carry the source instant
onto its claims (`observed_time` → `valid_from`) and say so on the row — the two things
cp-03-canonical already does.

| class | authoritative clock after 341 | what the deployment must carry (values, not SDK) |
|---|---|---|
| cp-03-canonical spread | the filing date: the newest `valid_from` among the leading edges of the three filing rows — equal to the payload's `latest_filed_in_payload` | nothing; already carried and declared |
| cp-06-canonical collateral | the valuation date: the newest `valid_from` among the leading edges of the valuation rows (`marketable_securities_valuation`, `real_property_appraisal`; `deposit_balance` if a balance date exists) | `observed_time=valuation_date` on those claims; `decay_basis: valid-from` on those rows |
| cp-04-canonical family | the relationship's assertion date, if the estate carries one for the family edges the walk admitted (the acquisition reads none today) | either carry it as `observed_time` with a `valid-from` row on the edge types, or declare `from_decision` — the deployment's call at its validation pass (§10 R-4) |
| cp-08 covenant-in-force | the amendment's `asserted_at` (already read, optional) as the leading edge of the amendment series; covenants carry no instant and contribute nothing | `observed_time=asserted_at` on amendment claims; `decay_basis: valid-from` on the `amendment` row; a served set with no asserted amendment refuses by name (§4) |
| cp-13-canonical (and frozen cp-13) | **no evidence clock, and none is pretended.** The class decays `supersede-only`: filed text does not age, it is superseded, and the estate carries no extraction or assertion instant. `from_decision` is the honest declaration: `expires_at` is the re-check cadence for supersession under the whitepaper's TTL (*"after TTL expires … a new request reconstructs it against current graph state"*, `docs/CCF_Whitepaper_1-2.md:1455`), not an evidence age. The contract carries `ttl_anchor: from_decision` and `ttl_anchor_at = decided_at`, so a reader can see the basis rather than infer one | nothing |
| cp-14 memo (composite) | its own term is `from_decision` (`decided_at + window`); the served `expires_at` is F14's floor over the children (§8) | nothing |
| cp-05, cp-07, cp-09–cp-12 | `from_decision`, unchanged; `ttl_anchor_at = decided_at` | nothing |

**Why `freshest`, and what it is not.** Every declared expiry gate on the governed path and
every hand-composed specimen anchors on the freshest evidence plus the class window
(`OFC-G07`, `CSCC-G23`, frozen cp-01/02/03), and the OPEN entry's reading (1) says the same.
Under `stalest` (the oldest leading edge), a coverage product resting on a one-day mark and a
one-year appraisal would expire a year ago and be unservable while each series sits inside its
own λ_c; staleness per series is what `F`, the per-signal floors
(`src/ccf/products/contract.py::ConstituentValidityFloors`) and
`src/ccf/products/composition.py::refuse_mixing` already measure. `D-IMPL-31`'s fuller form —
per-signal validities from `src/ccf/products/contract.py::FreshnessSLA` ages, minimized —
is a different quantity that no class has populated; it is named in §10 R-1 and not built
here. The derivation is declared per class (`D-IMPL-31`: *"choice per class is
configuration"*), `freshest` being the reference default.

## 4 · The fallback rule for a class without a clock

- **At registration (structural).** A class declaring `from_entity_freshness` whose λ_c table
  declares no `decay_basis: valid-from` row is refused by name when the class is registered:
  the declaration cannot be honored by any data, and a boot that let it through would serve a
  decision-anchored expiry under an evidence-anchored label — the defect this decision ends.
- **At serve (by name, never by fallback).** A class whose touched observation set carries no
  `valid-from` observation with a non-null `valid_from` refuses at gate 3 with a reason that
  says so (`ttl-anchor-unresolvable`; §10 R-3). Nothing falls back to `observed_at` or to
  `decided_at`: an anchor that silently moved to the decision instant would reproduce the
  measured overstatement under a name that says it did not.
- **Stale evidence refuses.** When `anchor + window <= decided_at`, gate 3's existing lower
  bound fires (`ttl-bounds`, with the anchor named in the refusal). The whitepaper is exact
  here: *"a product whose TTL has expired is not merely stale; it is invalid under the
  contract"* (`docs/CCF_Whitepaper_1-2.md:1527`). cp-03-canonical's product gate keeps its
  "no obligor" half; its "outside the window" half becomes what its own docstring says it is
  — deleted, not moved — at that example's validation pass.
- **A class with no meaningful evidence clock declares `from_decision`** (cp-13). The anchor
  vocabulary is not widened: `supersede-only` is a decay statement, and `from_decision` is
  already the honest expiry statement for it.

## 5 · Ownership point

The one place `expires_at` is minted: `__call__` on `GovernedResolver`, both branches. A new
pure function in a new module, `ccf.products.expiry` —
`resolve_ttl_anchor(*, ttl_anchor, derivation, observations, table, decided_at) ->
TTLAnchorResolution(anchor_at, basis, contributing_types)` — carries no value and reads the
observations the scorer already built. The non-composite branch uses `anchor_at + window`; the
composite branch passes `anchor_at` to `compose_children` where it passes `decided_at` today,
so the parent's own term and F14's floor anchor on the same instant. The projection, the
deployment, the door and the replay environment own nothing of it.

## 6 · Minimal interface and schema changes

| change | posture |
|---|---|
| `ContextProductContract.ttl_anchor_at: datetime | None` — the instant the class's anchor resolved to (`decided_at` for `from_decision`) | additive, hash-transparent `True` at `None`: every product minted before 341 keeps its address; every product minted after carries it and is self-describing (`expires_at − ttl_anchor_at` is the window) |
| `ContentGenerationPath.ttl_anchor_at: datetime | None` (dimension 5) | additive, `True`; `None` on every record written before 341 and it means "decision-anchored, as it was" |
| `ChildResolution.child_ttl_anchor: str | None`, `child_ttl_anchor_at: datetime | None` | additive, `True`; copied from the admitted child's contract so a consumer can print what §8 permits |
| `ProductClassDeclaration.ttl_derivation: "freshest" | "stalest"` | additive on the product-class artifact, `True` at `"freshest"`; may be dropped by R-1 |
| gate 3: a second reason on the TTL gate, `ttl-anchor-unresolvable` (§4) | the refusal vocabulary is closed by set equality (`tests/products/test_refusal_envelope.py::test_the_refusal_vocabulary_is_closed_by_set_equality`); the exact form is R-3 |
| registration: the declaration-vs-table check (§4) | a new named `ValueError` at registration, no new artifact |

Unchanged: `TTLAnchor`'s vocabulary, `MaxTTL`, `TtlBinding`, `compose_expiry`'s signature,
`replay()`'s outcome type, the record generation.

## 7 · Replay and backward compatibility

- **Old records rehydrate and reproduce the historical decision.** A record with
  `ttl_anchor_at None` on dimension 5 is decision-anchored by definition of the sentinel; a
  replay environment reconstructs `expires_at = decided_at + window` for it exactly as it does
  today, and the rebuilt product carries no `ttl_anchor_at`, so it hashes to the recorded
  address. No record is rewritten; no generation boundary is added; nothing recomputes an old
  decision under the new rule.
- **New records reproduce under the new rule from the record.** The environment reads
  `path.ttl_anchor_at` and reconstructs `expires_at = ttl_anchor_at + window`; the engine adds
  one hold, skipped by name when the member is `None`: the rebuilt product's `ttl_anchor_at`
  equals the record's, and the anchor re-derived over the re-executed view equals it too — the
  same re-derivation the engine already performs for every other dimension-5 claim, so an
  anchor is evidence-bound at replay and not merely copied (§10 R-5 asks whether to take the
  re-derivation now).
- **The existing replay contract is kept**, not overridden: `rehydrate_product` on
  `src/ccf/replay/engine.py::ReplayEnvironment` still owns the envelope; it gains one input it
  already had access to. The paved-road replay environment (`CP06C-F-01`) is not built here.
- **Newly served products advertise the corrected expiry** and hash differently from what the
  same evidence would have produced before; nothing has shipped that pins those addresses.
- **Schema/version:** contract and record members are additive and transparent (`D-IMPL-243`);
  the product-class artifact gains one transparent field; no artifact version is bumped.

## 8 · Child-row versus composite semantics

**What a consumer may state about one child's expiry.**

- *Before 341* (a child contract with no `ttl_anchor_at`): only "the producer's stated expiry"
  and "the producer's declared anchor". It may not infer evidence age from `expires_at`, may not
  print "current as of", "filing-anchored" or "valid until" against the evidence, and may not
  treat `ttl_anchor: from_entity_freshness` on the child as proof of anything the producer
  computed — this is exactly CP-14's standing instruction.
- *After 341* (the child contract carries `ttl_anchor_at`): "evidence current as of
  `ttl_anchor_at`; the producer's window ends at `expires_at`", read off the row's
  `child_ttl_anchor_at`; a `from_decision` child prints "decision-anchored at
  `ttl_anchor_at`". A child contract minted by a pre-341 producer still lacks the member and
  keeps the before-341 wording — the member is the generation marker.

**What the composite may advertise.** Its `expires_at` is F14's floor:
`min(own term, every admitted child's expires_at)`. The floor is a *bound*, and stays one: a
composite may not outlive its earliest applicable admitted-child expiry, and that does not make
any child's expiry filing-age evidence. The composite's own `ttl_anchor_at` is *its* anchor —
`decided_at` for a `from_decision` composite such as CP-14 — and it must not present the floor
as evidence-anchored unless it declares `from_entity_freshness` itself and its own evidence
resolves. CP-14's "it expires with its stalest child" remains true as a floor statement; its
rows print `child_expires_at` and, when present, `child_ttl_anchor_at`, never a freshness window
of their own.

## 9 · Named gates and the sabotage plan

**Gates that become load-bearing.**

| gate | today | after 341 |
|---|---|---|
| `OFC-G07` (cp-03-canonical) | `xfail(strict=True)` | the marker removed; asserts `expires_at == latest_filed_in_payload + window` **and** `ttl_anchor_at == latest filing`, and that both differ from `asked_at + window` on this estate |
| `CSCC-G23` (cp-06-canonical) | `xfail(strict=True)` | the marker removed once cp-06 carries the valuation instant (§3); asserts against the freshest `valuation_date` and `ttl_anchor_at` |
| cp-04-canonical, cp-08 | no expiry gate | each gains one at its validation pass — either the evidence-anchored assertion or, if the class moves to `from_decision`, the decision-instant assertion its peers carry |
| `TLP-G03`, `RSM-G03`, `EWS-G03`, `FXR-G04`, `CXR-G03`, `CMC-G03` | green | must stay green — `from_decision` classes are unchanged, and now also carry `ttl_anchor_at == decided_at` |
| `tests/examples/test_s1_01_governed_resolver_adoption.py::test_the_ttl_runs_from_the_declared_decision_instant`, `tests/products/test_resolver_seam.py::test_the_ttl_and_the_record_run_from_the_declared_decision_instant`, `tests/products/test_composite_integration.py::test_int01b_the_top_expiry_is_FLOORED_by_the_deepest_constituent` | green | must stay green (`D-IMPL-308`, F14 unchanged for `from_decision`) |

**New SDK suite** `tests/products/test_d_impl_341_ttl_anchor.py`, over the in-process
composite fixture with a class declaring `from_entity_freshness`, a `valid-from` row and claims
whose `observed_time` is a source instant strictly older than `asked_at`:

| control | holds |
|---|---|
| C1 | `expires_at == source_instant + window` and `≠ asked_at + window`; `ttl_anchor_at == source_instant` |
| C2 | with two observations in one series, the anchor is the leading edge as of `decided_at`, and a later observation does not leak into an earlier decision |
| C3 | an `observed-at` row with an ingestion instant newer than the source instant does not move the anchor |
| C4 | a class declaring the anchor over a table with no `valid-from` row is refused by name at registration |
| C5 | a served set with no `valid_from` instant refuses by name at serve; nothing falls back |
| C6 | evidence older than the window refuses `ttl-bounds` naming the anchor |
| C7 | a `from_decision` class serves exactly as before, with `ttl_anchor_at == decided_at` |
| C8 | a composite whose parent declares the anchor floors on `min(anchor + window, children)`, and its rows carry the children's `child_ttl_anchor_at` |
| C9 | the record's dimension 5 carries the anchor; replay reproduces the product and holds the anchor; a record with `ttl_anchor_at None` (a pre-341 record built as bytes with the member deleted) replays unheld and byte-identical |
| C10 | **the forbidden shape, as a negative control on the suite itself:** an assertion of the form `expires_at <= decided_at + window` passes on the sabotaged tree — recorded to show why no control here takes that form |

**Required sabotage S1 — revert to decision-time anchoring:** make `resolve_ttl_anchor` return
`decided_at` for `from_entity_freshness`. Expected red: `OFC-G07`, `CSCC-G23`, C1, C2, C3,
C6, C8, C9; expected green: C4, C5, C7, every `from_decision` gate, and — deliberately — C10's
naive assertion, which is why it is not a control. Further: S2 drop the registration check
(C4); S3 anchor on `observed_at` regardless of the row (C3); S4 take the globally newest
observation instead of the edge as of `decided_at` (C2); S5 drop `ttl_anchor_at` from dimension
5 (C9's hold); S6 pass `decided_at` to `compose_children` for an anchored parent (C8).

## 10 · Rulings asked

- **R-1 — the derivation default.** `freshest` over the `valid-from` leading edges is the
  reference; `stalest` is declarable per class. Confirm `freshest`, and rule whether the
  per-signal-validity form (`D-IMPL-31` over `FreshnessSLA` ages) is deferred until a class
  populates an SLA, as proposed.
- **R-2 — `ttl_anchor_at` on every new product**, `from_decision` included (proposed: yes, so
  every contract states its basis), or only on entity-anchored ones.
- **R-3 — the serve-time refusal.** A second reason on the existing TTL gate
  (`ttl-anchor-unresolvable`) rather than a new refusal kind; the vocabulary is closed by set
  equality and grows by one token, deliberately.
- **R-4 — the three declared-without-a-clock classes.** cp-06-canonical carries the valuation
  instant (its gate already names it); cp-04-canonical and cp-08 either carry an instant the
  estate provides or move to `from_decision`. These are example changes at their validation
  passes under `D-IMPL-261`, never inside the SDK change; until then the SDK refuses their
  declaration by name (§4), which is the honest reading of `CP03C-F-01` applied to them.
- **R-5 — replay re-derivation now.** The engine re-derives the anchor over the re-executed
  view and holds it to the record (proposed), or holds the record's value only.

## 11 · Out of scope, and perspective

Not touched: the paved replay environment; the malformed-door cross-process control;
argument-bound child retention; CP-14 assembly and features; `D-IMPL-342` bookkeeping beyond
this note — `CP03C-F-05` and `CP14-F-35` move to `FIXED-342` at their examples' next validation
pass.

1. The load-bearing fact is that the SDK already owns the evidence clock; 341 reads it for
   `expires_at` instead of inventing one. That is also why three of the four declaring classes
   turn out never to have carried the instant — the design surfaces it rather than hiding it
   behind a fallback.
2. I recommend refusing by name at registration (§4) even though it turns three examples'
   boots red at their validation passes. A softer path — warn, serve decision-anchored — would
   reproduce `CP03C-F-01` under a name that claims it was fixed.
3. The forbidden test shape is named as a negative control (C10) so the suite proves its own
   controls are not that shape.

## 12 · As built (2026-09-18, synchronization of this design to the tree)

Implemented on `d-impl-341-expiry` (from `f55915d2`, on `f8c33898`) under the implementation
GO. What follows names every place the tree differs from §1–§10 and records the measurements
the GO asked for — the class-by-class outcomes were measured, not predicted, and one of them
contradicts §3.

### 12.1 Contracts and API, exactly as built

- **`ccf.products.expiry`** (new): `resolve_ttl_anchor(*, ttl_anchor, view, table, decided_at,
  product_class) -> TTLAnchorResolution | TTLAnchorRefusal`; `TTLAnchorResolution(anchor_at,
  basis, contributing_types)`; `valid_from_rows(entries)`; `refuse_undeclared_ttl_anchor(...)`
  raising `TTLAnchorUndeclared`; the two basis constants. R-1 as ruled: the reference scorer's
  own observation set (`AssemblyDebtScorer._observations` over the execution's view), narrowed
  to the types the table declares, reduced per series by `leading_edge` as of the decision
  instant, only `valid-from` rows contributing, freshest wins. `ttl_derivation` (§6) was not
  added: R-1 ruled `freshest`, and a declarable `stalest` would have been a value nobody asked
  for.
- **Gate 3's second reason**: `src/ccf/products/gates.py::TTLAnchorRefusal` (kind
  `ttl-anchor-refusal`, reason `GATE_TTL_ANCHOR` = `ttl-anchor-unresolvable`; members
  `ttl_anchor`, `now`, `valid_from_rows`, `observation_types`), joined to `REFUSAL_KINDS`,
  `PERMITTED_AT_MINIMAL` (nothing actionable) and the HTTP status table
  (`STATUS_FULFILLMENT_WITHHELD`). Minted at the resolver's mint, before the candidate, on
  both branches, and recorded with the composed child rows (`D-IMPL-338`'s census grew from
  seven exits to eight).
- **`ContextProductContract.ttl_anchor_at`**, **`ContentGenerationPath.ttl_anchor_at`**,
  **`ChildResolution.child_ttl_anchor` / `child_ttl_anchor_at`** — all hash-transparent at
  `None` (four marks ticked in the roster). R-2: every new product states the instant, the
  decision instant included.
- **`GovernedResolver.half_life_key: str | None`** — REQUIRED, not defaulted: the seam's own
  invariant (`test_no_constructor_argument_carries_a_default`) refuses a default, so every
  direct construction names it (`None` = wired without a table; an evidence-anchored class then
  refuses at gate 3). **`build_governed_resolver(evidence_clock_key=...)`** — the same manifest
  key, stated for the resolver when the scorer is supplied, because the builder holds
  `half_life_key` and a supplied `debt_scorer` to be alternatives; the paved road passes it from
  `build_arguments`. An evidence-anchored serve pins the table on dimension 2
  (`PolicyBinding(half_life_key, pins.version_for(...))`); a decision-anchored serve pins
  nothing new.
- **Registration-time refusal (R-3, first row)** lives at `open_product` (the paved road's
  registration moment, before any question) and at `build_governed_resolver` (resolvers wired
  by hand), through one predicate. It was first placed in the config derivation and moved: the
  derivation is also how the frozen, hand-composed specimens' configs are *read*, and reading a
  frozen config is not registering a governed class.
- **Replay (R-5)**: `_hold_ttl_anchor` in `ccf.replay.engine`, called in `replay()` after
  rehydration and before the address check. Decision-anchored: `product.ttl_anchor_at ==
  path.ttl_anchor_at == record.recorded_at`. Evidence-anchored: the anchor re-derived over the
  re-executed view under the λ_c table resolved from the record's own pins must equal the
  recorded member (`ReplayDivergence`); no pinned table is `ReplayUnresolvable`. A record with
  no member returns the named sentinel `not-recorded` and every other check runs.
  `replay_refusal()` is untouched (a refusal names no product).

### 12.2 Class by class, measured on the candidate

| class | registration (predicate over its config) | serve on the candidate | what was learned |
|---|---|---|---|
| cp-03-canonical spread | passes — rows `annual_facts`, `quarterly_facts`, `peer_set` declare `valid-from` | **refuses `ttl-anchor-unresolvable`**. Probe: the view's observation types are `obligor`, `peer_cohort`, `spread_line`, `spread_period`, **every one carrying `valid_from`**; none is a row name | **§3 was wrong for this class.** The instant exists on every claim; the λ_c rows are keyed by the deployment's own observation vocabulary (its custom `assess` reads them), not by the entity classes the reference selection reads, so R-1's selection finds no qualifying row. Prerequisite, recorded and not made: key `decay_basis: valid-from` rows by `spread_period`, `spread_line`, `peer_cohort` (a config change; its own `assess` is unchanged). `OFC-G07` therefore **did not execute** and stays quarantined; the conversion drafted for it was reverted |
| cp-04-canonical family | **refused at open by name** (no `valid-from` row) | — | prerequisite as §3: an assertion date the estate provides, or `from_decision` |
| cp-06-canonical collateral | **refused at open by name** | — | `CSCC-G23` **did not execute**; prerequisite as §3: `observed_time=valuation_date` and `valid-from` rows on the valuation classes |
| cp-08 covenant-in-force | **refused by the predicate** (no `valid-from` row) | not run — its estate variables are not available in this session | prerequisite as §3 |
| cp-13-canonical (and frozen cp-13) | `from_decision`, registers | serves as before; `ttl_anchor_at = decided_at` | its hand-built replay environment omits `ttl_anchor_at`, so its replay-reproduction control is red by the new hold's own message — a one-line environment change at its validation pass |
| cp-14 memo | `from_decision`, registers | slice 1 red (the spread producer refuses as above); slices 2–4 error at the producers' boots (family, collateral refused at open) | blocked by its producers' prerequisites; its own environments also carry no `ttl_anchor_at` yet |
| cp-05 (frozen and wrapper door), cp-13 frozen | `from_decision` | green | unchanged |
| cp-09, cp-10, cp-11, cp-12 | `from_decision` | their output suites were skipped in this session for want of their estate variables | unchanged by construction: the `from_decision` branch serves exactly `decided_at + window` |
| s1-01 | `from_decision`, a declared decision instant | 45 passed against the local Fluree leg | `D-IMPL-308`'s proofs hold; the product additionally states `ttl_anchor_at` |

**The consequence, stated plainly for the review.** On this candidate four example trees cannot
serve (cp-03-canonical at gate 3; cp-04-canonical, cp-06-canonical, cp-08 at open), and
everything that consumes them is red: cp-03's cross-deployment and paved-consumer proofs, and
all four CP-14 slices. Each has a small, recorded prerequisite that is an example change under
`D-IMPL-261` and R-4, not an SDK change. Neither named example gate executed: **`OFC-G07` and
`CSCC-G23` are both blocked by their trees' clock prerequisites**; the executable failure proof
(§12.3) rests on the SDK controls.

### 12.3 The executable failure proof

`tests/products/test_d_impl_341_ttl_anchor.py` — nine controls over the paved fixture
(`open_product`, one product, one difference per control):

| control | holds |
|---|---|
| C1 | `expires_at == source instant + window`, `ttl_anchor_at == source instant`, and `≠ asked_at + window`, `≠ admitted_at + window`; the record carries the anchor and pins the λ_c table |
| C2 | freshest leading edge as of the decision instant; a later-dated observation does not leak in |
| C4 | R-3 row 1: refused by name at open (no basis; `observed-at` basis) and at the builder over a fabric the low road booted |
| C5 | R-3 row 2: `ttl-anchor-refusal` / `ttl-anchor-unresolvable`, naming the rows and the types seen; nothing anchored, nothing claimed |
| C6 | R-3 row 3: `ttl-refusal` / `ttl-bounds` with the anchored expiry named — distinct from C5 |
| C7 | a `from_decision` class serves as before and states `ttl_anchor_at == decided_at == recorded_at`; no table pinned |
| C8 | an evidence-anchored composite floors on `min(anchor + window, children)`, with the parent's own term binding, and its rows carry the child's anchor and instant |
| C9 | replay re-derives the anchor and holds it; a disagreeing derivation fails by name with the record untouched; a pre-341 record — the member deleted from its bytes and the product address re-pointed at the decision-anchored envelope such a record described — reconstructs, and the hold returns `not-recorded` |
| C10 | the negative control: `expires_at <= decided_at + window` holds for the anchored product and stays green under S1 |

**Sabotages, run by hand and restored (`cmp` verified), over the 341 suite, the paved consumer
and the refusal vocabulary (104 controls):**

| sabotage | red | green |
|---|---|---|
| **S1 (required) — decision-time anchoring restored for `from_entity_freshness`** | C1, C2, C5, C6, C8, C9 | C4, C7, and **C10 — the deliberately inadequate `<=` assertion, as the GO required** |
| S2 — the registration-time refusal dropped | C4 | the other 103 |
| S3 — anchor on `observed_at` (the ingestion instant) | C1, C2, C5, C6, C8, C9 | C4, C7, C10 |
| S4 — the globally newest instant instead of the edge as of the decision | C2 | the other 103 |
| S5 — dimension 5 does not carry the anchor | C1, C7, C9 | the other 101 |
| S6 — the composite's own term anchored on the decision instant | C8 (after C8 was tightened so the parent's own term binds — its first form let the child's floor hide S6) | the other 103 |
| S7 — the replay anchor hold dropped | C9 | the other 103 |

The named example gates could not be sabotaged because they could not execute (§12.2).

### 12.4 Scoped regressions at the candidate

`tests/products` + `deployment` + `contracts` + `replay`: 2023 passed, 1 standing red
(`test_class_lookup`, red on the baseline). Paved consumer, 342 suites, refusal vocabulary,
contracts, replay: 371 passed. `make lint` 0; `make typecheck` clean (230 files); surface suites
4 standing reds identical to the baseline; s1-01 45 passed; cp-05 doors green. Deliberate test
growth, named: hash-transparency roster +4; refusal vocabulary +1 kind with its own envelope
test; the hand-rendered pre-field product now omits both transparent sentinels; the
generation-mismatch transparent roster +1; the request-contract member pin +1; the resolver
seam's argument enumeration +1 and its constructor dictionary; the builder's
non-scorer-material exclusions +1; `D-IMPL-338`'s exit census 7 → 8 (2 before, 6 after); the
339/344 replay environments carry `ttl_anchor_at` off the record; one example test names the
resolver's new required argument (cp-03 cross-deployment, which constructs the resolver
directly — and is red anyway, above).

### 12.5 Residual limitations, carried

1. The two named example gates did not execute (§12.2); the failure proof rests on the SDK
   controls until the trees' clock prerequisites land.
2. cp-08 was not run in this session (estate variables absent); its registration refusal is
   measured statically over its config.
3. Every hand-built example replay environment (cp-06-canonical, cp-13-canonical, the CP-14
   slices) must read `ttl_anchor_at` off the record — one line each — at its validation pass;
   until then their replay-reproduction controls are red by the hold's own message.
4. The pinned spread address (`DEMONSTRATION_SPREAD_ADDRESS`) in the CP-14 and cross-deployment
   proofs will move once cp-03-canonical serves evidence-anchored, and must be re-pinned at
   that validation pass, never inside an SDK change.
5. `OFC-G06` (the spread's own window gate refusing a stale obligor) will need re-specifying
   at that pass: gate 3's `ttl-bounds` now fires first, which is what §4 said would make the
   product gate's serving half redundant.

### 12.6 Validation pass (2026-09-18, under "validation and review GO; merge HOLD")

First candidate `8f84f710` preserved as recorded; everything below is measured on the
integrated candidate against the live estate, with the SDK mechanism of §12.1 unchanged except
for one correction named in (f).

**(a) The precise mismatch behind §12.2's first row, and the mapping that resolved it.** The
supported λ_c table keys a row by observation type; the reference selection (R-1) types an
observation by its entity class; the three deployments with a custom `assess` type the same
claims by their own vocabulary (cp-03-canonical by the `signal_class` attribute onto
`annual_facts` / `quarterly_facts`; cp-06-canonical by valuation category onto five rows;
cp-08 by entity class already). One class cannot carry two rates in this table. The mapping
taken, and written beside each row: **the entity-class row carries the class's CLOCK and no
rate** (`decay: supersede-only`, `decay_basis: valid-from`), the rate rows stay as they were,
and the deployment's `assess` is untouched. Measured: the anchor equals the payload's own
anchor member on every served spread (`latest_filed_in_payload` = `ttl_anchor_at`), and `F` and
the anchor read one set of claims by one clock (`spread_period.valid_from`). The design's
assumption that this producer needed **no migration** was wrong on three counts, each recorded
at `CP03C-F-01`: the clock row; the product's own gate, which inferred its window as
`expires_at - temporal_boundary` and read the 30-day window as 1 day the moment the anchor
moved (corrected to `expires_at - ttl_anchor_at`); and precedence — the SDK's TTL gate now runs
before the product's declared gate, so the stale obligor is refused `ttl-bounds`, and an empty
view (absent or suppressed obligor) is refused `ttl-anchor-unresolvable` before the product's
`NO_OBLIGOR` can speak (`OFC-G08`'s byte-identity holds).

**(b) The comparison table** (`from_decision` rows measured through the real path at the CP-14
instant; `from_entity_freshness` rows at the instants named):

| product | declared basis | actual source of anchor | anchor / expiry | outcome change | gate result |
|---|---|---|---|---|---|
| cp-03-canonical spread (BGC) | `from_entity_freshness` | `spread_period.valid_from` = filing date | `2026-08-10T00:00Z` / `2026-09-09T00:00Z` (was `2026-10-07T12:00Z`) | serves; address `122e0a7b…` → `22c5ce3d…` (re-pinned from verified output); F/C/S/D_c unchanged (0.3189 / 0.4915 / 1 / 0.8433, `fail_closed`) | `OFC-G07` live; `OFC-G06` = precedence (`ttl-bounds` first) + the predicate held directly; S1 reds both |
| cp-03-canonical stale obligor | same | filing `2026-08-05` | `2026-09-04T00:00Z` | refused `ttl-refusal` / `ttl-bounds` (was `product-invariant-refusal` naming the product gate) | precedence recorded |
| cp-04-canonical family | **`from_decision`** (was `from_entity_freshness`) | the decision instant — no family edge in `fibo-v2` carries an assertion instant; the nearest `validFrom` is a `prior-obs-…` supersession record shared by 84 subjects | `2026-09-07T12:00Z` / `2026-10-07T12:00Z` (value unchanged) | serves; identity moved (basis + `ttl_anchor_at`); 13 passed | `CP04C-F-06` recorded in config, spec element 8/§E, findings |
| cp-06-canonical collateral (FAC-5B8418) | `from_entity_freshness` | `collateral_node.valid_from` = asset valuation date (stamped from `valuation_date`, `deployment._valuation_instant`) | `2025-12-20T00:00Z` / `2025-12-21T00:00Z` | **at the CP-14 instant: refused `ttl-refusal` / `ttl-bounds`** (was served, `2026-09-08T12:00Z`); on its valuation day: serves, F 0.99905, D_c 0.00095 | `CSCC-G23` live on the positive control; the CP-14-instant refusal asserted as the intentional correction; S1 reds both |
| cp-06-canonical collateral (FAC-044206) | same | valuation `2026-08-15` | `2026-08-15T00:00Z` / `2026-08-16T00:00Z` | refused `ttl-bounds` at the CP-14 instant; serves on its day | same |
| cp-08 covenant-in-force (FAC-01BB3F) | `from_entity_freshness` | `amendment.valid_from` = booking date (`assertedAt`, `deployment._booking_instant`) | `2025-10-05T00:00Z` / `2026-04-03T00:00Z` | **refused `ttl-bounds` at the CP-14 instant and at the wall clock** (was served, expiry = question + 180 d); serves on the booking day (F 0.941, D_c 0.059 — was F 1, D_c 0 by construction); serves through `2026-04-02`, refused from `2026-04-04` | 20 passed at the positive control; the wall-clock refusal asserted; S1 reds both new controls |
| cp-12 (spot check, `from_decision`) | `from_decision` | the decision instant | unchanged value; `ttl_anchor_at` added | 28 passed against the estate | unchanged |
| cp-13-canonical | `from_decision` | the decision instant | unchanged | 26 passed with the replay environment reading `path.ttl_anchor_at` | unchanged |
| CP-14 memo (BGC) | `from_decision` | the decision instant; floor over children | composite refuses `child_admission` at BOTH tolerances | **the collateral slot is `ineligible` (`ttl-refusal` / `ttl-bounds`) at every tolerance**; slices 1–2 green on the re-pinned address; slices 3–4: 10 served-memo tests quarantined strict, the consequence asserted beside them | reported below |

**(c) Intentional corrections, separated from standing failures.** Corrections: the two
cp-06-canonical demonstrations and the cp-08 demonstration now REFUSE at the instants their
suites historically served at, because their evidence is older than their declared windows;
each suite asks at a positive control inside the window (each facility's valuation day; the
covenant facility's booking day) and asserts the refusal at the historical instant. Nothing
about data, windows, tolerances or `asked_at` for the historical questions was moved. Standing
failures, identical to the baseline by node id: `tests/deployment/test_class_lookup.py::
test_the_phases_fragments_claim_exactly_what_was_added`; the four surface suites; the
invariants citation ratchet; the http_api eight; the peering one.

**(d) Two consequences that are rulings, not this pass's calls.** *(Both were ruled on
2026-09-18 and the record of what was measured HERE is left as it stood; §12.8 carries the
rulings and what changed.)*
1. **cp-06-canonical's window and anchor name different evidence** (`CP06C-F-05`). The
   product window is one day, the deposit-balance half-life; the anchor can only read the
   valuation date, the one dated evidence (`ccf_v2.deposit_account` carries no as-of column).
   Under the declarations as written, no facility on this estate serves after `2026-08-21`, and
   CP-14's memo for BGC serves at NO instant (spread window `2026-08-10`–`2026-09-09`;
   collateral window `2025-12-20`–`2025-12-21`). Two honest resolutions: declare
   `from_decision` (the fast-moving evidence carries no source instant; per-asset staleness is
   in the payload), or keep the evidence anchor with a window on the valuation cadence under
   `D-IMPL-323`. CP-14's ten served-memo proofs are quarantined strict on this question.
2. **The frozen specimens that declare `from_entity_freshness` over a resolver wired with
   their own scorer and no λ_c table** cannot answer. Measured at the validation pass as a
   serve-time refusal (`ttl-anchor-unresolvable`); since Dave's ruling of 2026-09-18 it is a
   CONFIGURATION failure refused at the builder (`TTLAnchorUndeclared`) before a question
   proceeds — §12.8 ruling 3. Frozen cp-06's output and door suites — 16 + 2 tests —
   are quarantined `xfail(strict=True)` under `D-IMPL-261`, the specimen untouched;
   cp-00–cp-03's suites were already quarantined and are unchanged; frozen cp-04 never reaches
   a serve. The cp-06-canonical lane (`CSCC-G13`) is held to the recorded payload addresses
   rather than a live specimen.

**(e) The precise mismatch at cp-08** (`CP08-F-05`): `CP-SPEC-008` §E.3 anchors "on the latest
assertion among the SERVED set"; R-1 anchors on the scored VIEW. A closed question
(`as_of` = `known_as_of` = the drawdown) serves `AMD-01BB3F-1` alone, excludes `-2` on the
assertion axis, and anchors on `-2`'s booking regardless. The two readings coincide for a live
question and diverge for a closed one. Reported, not repaired.

**(f) One in-scope SDK defect, corrected.** The first candidate recorded a `TTLAnchorRefusal`
with neither `pre_assembly_lineage` nor `RefusalEvidence`; `replay_refusal` then refused the
record as contradicting itself ("names a plan — a refusal after projection — while its refusal
carries no evidence of that projection", `D-IMPL-344`). It is a post-projection refusal and is
now recorded with the same lineage and execution evidence a gate refusal carries
(`src/ccf/products/resolver.py`). Measured through cp-06-canonical's 344 reconstruction control.

**(g) Replay environments** — cp-06-canonical, cp-13-canonical and the CP-14 fourth slice read
`path.ttl_anchor_at` off the record (decision-anchored records fall back to the recorded
boundary, which equals it); the engine's own re-derivation stays active and held every served
record in the suites above.

**(h) Sabotages, rerun on the integrated candidate and restored (`cmp` verified):** S1–S7 red
exactly the controls §12.3 lists, C10 green under S1. S1 additionally reds seven live example
controls: `OFC-G06` (its precedence limb), `OFC-G07` and `CSCC-G23` — the three that carry a
gate id, and the three that now carry an `observed_red` block on their rosters — plus four
controls that carry no gate id and are therefore outside the product-gates instrument: the two
CP-14-instant refusal controls at cp-06-canonical and cp-08's two. Named separately because a
roster is the only place a gate's sabotage is auditable, and a control without an id is not on
one.

**(i) Scoped regressions on the integrated candidate:** products + replay + contracts 1699
passed; deployment 325 / 1 standing red; cp-03-canonical 19, its paved consumer and
cross-deployment 23; cp-04-canonical 13; cp-06-canonical 30; cp-08 20; cp-12 28;
cp-13-canonical 26; CP-14 slices 11 passed / 10 xfailed; frozen cp-06 6 / 18 xfailed;
frozen cp-04 188 / 48 skipped / 41 xfailed; lint 0; typecheck clean (230); product-gates
19 / 324 / 324; docs gates 349 (the retirement report regenerated); surface: address-only
churn, discarded.


### 12.7 Independent review (2026-09-18) — reviewed SHA `4108aba9`, repair delta below

Five lenses over the pushed candidate, each finding then handed to an independent skeptic
briefed to refute it: **27 raised, 21 survived refutation, 6 refuted** (32 agents). The six
refuted are recorded as rejected, per §3.1's rule that an unverified finding acted on is worse
than no review: an undated period "stamping the question instant" (the SDK maps `observed_time`
straight through and the deployment stamps nothing), the type-narrowing being undocumented (it
is R-1's declared realization), C2's leading-edge reduction being uncovered (it is not), K2
re-raised as new, a missing row validator on the two child members, and cp-08's demonstration
"sitting on an equality edge" (it does, correctly — the filter is inclusive).

Four lenses independently found ONE defect, and it is the review's whole yield as a blocker.

**The blocking defect, and it was mine.** `compose_children` takes a single `ttl_anchor_at` and
hands it to two different laws: `compose_expiry` (the composite's own term) and `refuse_mixing`
(`D-IMPL-31`'s floor, whose `evaluated_at` is the instant a constituent's REMAINING validity is
measured from). Before this branch the resolver passed `decided_at` and the two coincided. This
branch passes the resolved anchor, so for a `from_entity_freshness` composite the mixing law
began measuring remaining validity from an instant in the past — overstating every child's
remaining validity by exactly `decided_at - anchored_at`, and letting a constituent that
breaches its declared floor at the decision instant compose anyway. `D-IMPL-115` records that
floor as a property a deployment "cannot now configure its way past"; this let a declaration do
exactly that. Latent (no shipped class declares floors) and unreachable from the plain branch,
which is why nothing was red.

**Repaired:** `compose_children` now takes `decided_at` beside `ttl_anchor_at` — how long is
left is a fact about now, how long the answer is good for is a fact about its evidence — and
`refuse_mixing` reads the decision instant while `compose_expiry` keeps the anchor. **Control
C11** (two parametrizations) drives the paved consumer with an evidence anchor five minutes
before the decision and a child whose window ends ten minutes after it: the child has ten
minutes left at the decision and fifteen at the anchor, so a twelve-minute floor must refuse and
a nine-minute floor must serve. **Sabotage S8** (restore `evaluated_at=ttl_anchor_at`) reds
exactly C11's refusing case and nothing else, restored `cmp`-verified.

**The other in-scope repairs, each verified against the tree before acting:**

| # | what the review found | repaired |
|---|---|---|
| 1 | an evidence-anchored serve over a λ_c table the manifest declares `role: load` passes registration, resolves the anchor, passes gate 3, and then raises `UnpinnedArtifactError` while BUILDING the record — an exception where a governed refusal belongs | the builder now asks for the pin at registration when the class is evidence-anchored, so an unrecordable deployment is a boot failure. **No control**: `half_life`'s role is not adopter-declarable in a config (`deployment/config.py:195`), so the state is unreachable from a tree and the guard is defensive; said here rather than left to look proven |
| 2 | `build_governed_resolver`'s refusal when the two clock keys disagree had no control | **C12**: two disagreeing names raise naming `D-IMPL-341`; the road's own construction resolves the clock key onto the resolver; the same name twice is refused for the builder's own scorer rule, not 341's |
| 3 | `ReplayEnvironment.rehydrate_product`'s contract enumerates every dimension-5 member an implementation must carry and never named `ttl_anchor_at` — the exact red three example environments hit | the protocol docstring now names it, says to reconstruct `expires_at` from it, and says `None` is the pre-341 shape |
| 4 | the `ttl_anchor_at` comment asserts `expires_at - ttl_anchor_at` IS the declared window; for a composite whose expiry is F14's floor it is at most that | the comment is qualified; §8's "a bound, not a freshness claim" is cited where a reader meets the member |
| 5 | the missing-anchor refusal is decided before gates 1 and 2, not "at gate 3" in sequence | recorded where the token is defined (`gates.py`), including that an example gate naming the same empty view now describes a path the engine reaches first — which is what `OFC-G06` and `CSCC-G20` were re-specified for |
| 6 | cp-06-canonical's spec still said an unheld scope is refused by the product's own gate | the row names the real path: the SDK's anchor gate first, the no-commitment half held directly |
| 7 | cp-06-canonical's `debt()` reached "one clock" by loading `valid_from` into `observed_at` while the five rate rows still declared the default basis — declaration and computation disagreeing in the reader's eye | the rows declare `decay_basis: valid-from` and the scorer passes BOTH instants, each meaning what it says. `F` is unchanged by construction; `CP06C-F-04` keeps the record of the move off the stored age |
| 8 | cp-04-canonical moved to `from_decision` with no executable proof, though §9 committed it to gain one, and the ledger premise carried no rerunnable query | **`CFC-G14`** on the roster and in §G.1, with the control; and `CP04C-F-06` now carries the query and its answer — **639 `owns`/`controls` edges, 0 carrying any date-like predicate** |
| 9 | the CP-14 third-slice test asserted something other than its docstring | the docstring states what it holds and where the payload-level claim moved |
| 10 | CP-14's own ledger still described the pre-341 state, and the memo's consequence lived only in another tree | `CP14-F-31` closed FIXED-341 with the re-pinned address; **`CP14-F-41`** records that the memo serves at no instant and names the ten quarantines; README §2 is labeled the historical measurement |
| 11 | the lane gate compared eight characters, and with the specimen unable to re-serve them the prefixes were the only record | the full 64-character addresses are measured, written into §A.2 and compared in full (`d22b256e…a45c`, `8e3e567b…be63` — both matched exactly); the roster names `CSCC-G13` a SNAPSHOT comparison to be re-measured on drift, never re-pinned; the dead field-level helper removed |
| 12 | §12.6(h) claimed seven S1 reds "recorded on each roster", and four of them carry no gate id | the claim now separates the three roster gates from the four controls outside the instrument |

**Carried, with the reason each is not repaired here:**

1. **The scorer reduces at `view.as_of`; the anchor at `decided_at`** (advisory). They coincide
   for every shipped class, and diverge only if a class combined `from_entity_freshness` with a
   declared decision-instant parameter — none does. Closing it is a ruling (refuse the
   combination at registration, or anchor at `as_of`), not a repair.
2. **`_hold_ttl_anchor` branches on the rehydrated product's declaration, not on a recorded
   basis** (advisory). A class whose basis changed between serve and replay fails under the
   wrong name. A genuine flip is still caught — `ttl_anchor` is inside the hashed body, so the
   address check refuses it — but the message misleads. Recording the basis on dimension 5 is a
   schema change and wants a ruling.
3. **Refusal records pin no λ_c table** (advisory). The served record pins it; the anchor
   refusal and an evidence-anchored `ttl-bounds` refusal do not, so their named evidence is not
   re-derivable under their own pins. Nothing diverges today because `replay_refusal` does not
   recompute gates (`D-IMPL-344` R-2); whether that boundary should move is Dave's.
4. **No control for a composite whose CHILD's expiry binds** an evidence-anchored parent (C8
   holds the parent-binding case; C11 holds a floored composite). A coverage gap, recorded.
5. **The CP-14 fourth-slice environment's 341 line is unexecuted** while the served-memo proofs
   are quarantined: the first green run after the `CP06C-F-05` ruling is its first execution.

**Regressions after the repairs:** products + replay + contracts + deployment 2027 passed / 1
standing red (`test_class_lookup`, baseline); cp-03-canonical 19, paved consumer 7,
cross-deployment 8; cp-04-canonical 14; cp-06-canonical 30; cp-08 20; cp-13-canonical 26; CP-14
slices 3 / 5 / 5+2 xfailed / 6+8 xfailed; lint 0; typecheck clean (230); product-gates
19 / **325** / 325; docs gates 349. S1–S8 rerun, each reding exactly its controls and restored.


### 12.8 The three closing rulings, applied (Dave, 2026-09-18)

**Ruling 1 — collateral: keep evidence anchoring, align the window with valuation cadence**
(`565533b3`). The class stays `from_entity_freshness`. Its window and ceiling move from the
deposit-balance half-life to the appraisal cycle:

| | previous | now | governing declaration |
|---|---|---|---|
| `ttl.product_ttl_seconds` | 86400 s (1 day) | **31536000 s (~365 days)** | `half_life.real_property_appraisal` |
| `ttl.max_ttl_seconds` | 86400 s (24 h) | **31536000 s** | the ceiling equals the window: no answer may advertise more currency than one appraisal cycle from its own evidence |

**The basis, and it is a declaration rather than an outcome.** The expiry is anchored on an
asset VALUATION DATE, so the window must state how long a coverage answer stays current after a
valuation — the valuation cadence this product's own λ_c table declares. Of the two valuation
cadences in that table, the appraisal cycle is the one governing **74 of the 95 pledged assets
in this estate** (real property, receivables, equipment and inventory all decay under it;
measured 2026-09-18 by joining `ccf_v2.collateral_asset` to `ccf_v2.collateral_pledge`). The old
window was chosen when the expiry ran from the REQUEST instant and named the fastest-moving
evidence in the payload; with the expiry anchored on a valuation it named a cadence the anchor
cannot read. Declared **illustrative** under `D-IMPL-323` at the config, the spec, the README and
`CP06C-F-05`.

**What it does not claim, stated at every site that carries the calibration.** It does not
establish that the DEPOSIT BALANCES are fresh: `ccf_v2.deposit_account` carries no as-of column
at all, so a balance contributes no instant to the anchor and nothing here dates the set-off
leg — which is why coverage is served with collateral value, set-off value and total kept apart.
It does not claim every asset was revalued within the window either: a marketable security is
aged in `F` by its own one-day cadence, and each asset's valuation date and age stay in the
payload.

**Measured after, and the term still discriminates:** at the CP-14 instant **47 of the 50
facilities with pledged collateral serve and 3 are refused** `ttl-bounds` on evidence older than
an appraisal cycle. **`CSCC-G24`** is new and holds that refusal on `FAC-D3D1A4` (freshest
valuation `2025-02-18`, so its coverage expired `2026-02-18`), and the consumer's `ineligible`
crossing is asserted on the same subject through this producer's own door. `CSCC-G23` is live at
the demonstration instant. The diagnostic serve that follows is a measured outcome; the duration
came from the declaration above.

**Ruling 2 — covenant: correct the specification to the scored-view rule** (`c3b46c70`).
`CP-SPEC-008` §E.3 and element 8 said "the latest assertion among the SERVED set"; the anchor
comes from the same selected observation set the freshness factor scores, before Π decides what
to display. The specification was wrong and is corrected — no code, no source timestamp, no
second selection algorithm, and nothing reads the finished payload. The clause now carries the
measured closed-question case (`AMD-01BB3F-2` is excluded from the served answer on the
assertion axis and still contributes the anchor, because it is in the scored set) and what the
anchor does not claim: that every displayed fact was refreshed at that instant. `CP08-F-05`'s
scored-view half is closed as a spec correction; its expired-demonstration half stands.

**Ruling 3 — registration: reject missing clock configuration before answering** (`952644d4`).
A resolver wired with neither `half_life_key` nor `evidence_clock_key` can never resolve an
evidence instant, so an evidence-anchored class over it is refused at the builder
(`TTLAnchorUndeclared`) rather than at every question. **`C4b`** holds the three boundaries
apart — missing configuration at the builder, a sound configuration whose observations supply no
instant at serve time (`C5`), an anchor whose window has passed at the expiry gate (`C6`) — and
asserts that a decision-anchored class over the same wiring is untouched. The unpinnable-clock
check added at §12.7 stays beside it, and the guard was not moved back into frozen-config
derivation.

**Measured consequence, reported rather than smoothed:** the frozen cp-06 specimen declares this
anchor with its own scorer and no table, so it can no longer BOOT, where until this ruling it
returned a governed serve-time refusal. Its quarantines (16 output tests, 2 door tests) now name
the registration failure, the frozen door's governance test joins them, and the specimen is
untouched (`D-IMPL-261`).

**Ruling 4 (preserved, not re-litigated) — the composer's two instants.** `compose_children`
still takes `ttl_anchor_at` for the expiry term and `decided_at` for the mixing floor; `C11` and
sabotage `S8` are unchanged by the calibration and rerun green.

**The ten CP-14 quarantines, converted (`3875ac3c`).** With the collateral child serving again
every one of them passes on its ORIGINAL assertions; each is named in §12.9. The two consequence
tests written while the calibration was open are deleted — their premise was the refusal the
ruling dissolved — and nothing they displaced was left replaced: slice 3 holds the
facility-specific question on the retained CHILD again with the retained question beside it, and
slice 4's withheld rows read `tolerance-exceeded` again.

### 12.9 Final evidence

**Per product, at the CP-14 instant (`2026-09-07T12:00Z`) unless stated.** Product address and
replay-record address are different things and are listed apart.

| product | anchor basis | `ttl_anchor_at` | `expires_at` | `F` / `D_c` / signal | outcome | product address | record address |
|---|---|---|---|---|---|---|---|
| spread, BGC | evidence (filing) | `2026-08-10T00:00Z` | `2026-09-09T00:00Z` | 0.3189 / 0.8433 / `fail_closed` | served | `22c5ce3d…9a92d7b9` | `6c6c3a1d…6d46f6da` |
| spread, stale obligor | evidence | — | `2026-09-04T00:00Z` (named in the refusal) | — | refused `ttl-bounds` | — | recorded |
| family | decision | `2026-09-07T12:00Z` | `2026-10-07T12:00Z` | 1 / 0.4082 / `ok` | served | `a09c93d2…f851befa` | `d5da4991…b89d01c5` |
| collateral, `FAC-5B8418` | evidence (valuation) | `2025-12-20T00:00Z` | `2026-12-20T00:00Z` | 0.6086 / 0.3914 / `ok` | served | `611f5dac…c28db03ae` | `60442989…99b05576` |
| collateral, `FAC-044206` | evidence (valuation) | `2026-08-15T00:00Z` | `2027-08-15T00:00Z` | 0.4782 / 0.5218 / `ok` | served | `501ee648…f04eab6d9` | `23ba7f60…39ea6d9a2` |
| collateral, `FAC-D3D1A4` | evidence (valuation) | — | `2026-02-18T00:00Z` (named in the refusal) | — | refused `ttl-bounds` | — | recorded |
| covenant, `FAC-01BB3F` | evidence (booking) | `2025-10-05T00:00Z` | `2026-04-03T00:00Z` | 0.941 / 0.059 / `ok` on the booking day | served on the booking day; refused `ttl-bounds` at the wall clock | measured in-suite | measured in-suite |

The lane payload addresses are unchanged by the calibration and match `CP-SPEC-006C` §A.2 in
full: `d22b256eb343768f185ebbe09eed1949a44226cc1ffccc924550dbbc6f29a45c` and
`8e3e567b194b1aad69bd08da53996dc89bbc4d3f9b335da119147c102d2ebe63`. A payload carries no instant,
which is why the window moved the CONTRACT addresses above and not these.

**The ten CP-14 quarantines, by test identity and disposition — all CONVERTED to normal passing
tests on their original assertions:**

| slice | test | disposition |
|---|---|---|
| 3 | `test_three_children_are_admitted_simultaneously_from_three_producers` | converted |
| 3 | `test_the_real_question_admits_family_and_collateral_and_withholds_the_spread` | converted |
| 4 | `test_the_diagnostic_admits_every_child_that_serves_and_the_composite_outcome_is_measured` | converted |
| 4 | `test_acquisition_and_composition_use_the_same_admitted_child_contracts` | converted |
| 4 | `test_inherited_debt_is_the_per_factor_minimum_across_children_weak_on_different_factors` | converted |
| 4 | `test_every_summary_field_reads_the_declared_child_member` | converted |
| 4 | `test_the_same_diagnostic_question_yields_one_product_address_twice` | converted |
| 4 | `test_a_meaningful_child_content_change_changes_the_corresponding_parent_field` | converted |
| 4 | `test_the_covenant_question_names_the_obligors_own_evidence_nodes` | converted |
| 4 | `test_served_reconstruction_uses_retained_inputs_without_calling_any_provider` | converted |

Two tests were DELETED rather than converted, and both were written by this branch while the
calibration was open: `test_at_the_cp14_instant_the_collateral_child_is_withheld_for_expired_evidence`
(slice 3) and `test_at_the_cp14_instant_the_diagnostic_refuses_on_the_expired_collateral_child`
(slice 4). Their subject was the refusal the ruling dissolved, and the property they were
standing in for — a producer refusal crossing as an `ineligible` child — is now held at
cp-06-canonical on a facility whose evidence really did outlive the window.

**Suites on the final candidate:** products + replay + contracts + deployment 2028 passed / 1
standing red (`test_class_lookup`, baseline); cp-03-canonical 19, paved consumer 7,
cross-deployment 8; cp-04-canonical 14; cp-06-canonical 29; frozen cp-06 4 passed / 16 xfailed
and its door 1 passed / 3 xfailed; cp-08 20; cp-12 28; cp-13-canonical 26; CP-14 slices 3 / 5 / 6
/ 13, no xfails left; lint 0; typecheck clean (230); product-gates 19 / **326** / 326; docs gates
349; surface address-only churn discarded. **Sabotages S1–S8 rerun and restored (`cmp`)**: S1 and
S3 red seven controls (the six plus C11's serving half, whose anchor assertion they break), S2
C4, S4 C2, S5 three, S6 C8, S7 C9, S8 C11's refusing case alone.

**Residual limitations carried past this pass** (unchanged from §12.7 unless noted): the scorer
reduces at `view.as_of` while the anchor reduces at `decided_at` — unexercised, a ruling;
`_hold_ttl_anchor` branches on the rehydrated declaration rather than a recorded basis; refusal
records pin no λ_c table; no control for a composite whose CHILD's expiry binds an
evidence-anchored parent; and the unpinnable-clock guard is defensive with no config-reachable
control. `CIF-G15` (cp-08's dual TTL) remains declared and unimplemented, untouched by ruling 2.


### 12.10 Focused review of the final delta (2026-09-18) — reviewed SHA `6309cd00`

Four lenses over `4108aba9..6309cd00` with an independent skeptic per finding, scoped to the
three rulings and the CP-14 conversions rather than to the whole design: **31 raised, 24
survived refutation, 7 refuted** (35 agents). The reviewed SHA is `6309cd00`; two doc-only
commits (`fc2d144a`, `b80ec83e`) landed while it ran and one lens correctly noticed, re-verifying
against the tip. The 24 survivors deduplicate to **eleven distinct defects, all repaired**:

| # | found | repaired |
|---|---|---|
| 1 | **Ruling 2 reached the specification only.** Three live cp-08 sites still stated "the latest ASSERTION among the served set" — `ccf_config.yaml`'s class comment (citing §E.3 as its authority), `deployment._booking_instant`'s rationale (QUOTING the deleted sentence), and the gate test's docstring — so the tree asserted and denied the ruled rule at once, and the test that IS the scored-view evidence told a reader "not repaired here" | all three restated to the scored-observation-set rule, keeping the §E.3 citation; the gate test's docstring now says the specification was corrected and that it holds the corrected clause |
| 2 | `CSCC-G23`'s docstring still said "the declared one-day window" — the value the calibration replaced, in the file the calibration rewrote | reads "the declared window (the appraisal cycle)"; the assertion was already parameterized |
| 3 | **A duplicate finding id**: the new CP-14 ledger row reused `CP14-F-40`, already held by the `memo_type` finding | renumbered to `CP14-F-41`, with all four citing sites updated |
| 4 | `CSCC-G23`'s roster entry still declared the gate unsabotageable ("quarantined until the SDK honors the anchor") while carrying an `observed_red` block from a real S1 run | the `sabotage:` field names the SDK's S1 |
| 5 | `NO_PRODUCT_ADDRESS` was imported by the fourth slice and used by nothing — the deleted consequence test had been its only consumer, so the "a refused composite records no product address" claim had quietly stopped being asserted | the assertion is restored to the surviving governed-question test |
| 6 | **`CSCC-G24` pinned an estate valuation date**, the shape CLAUDE.md §9 asks estate tests to avoid: a revaluation would red it as a stale pin rather than as a behavior change | no estate date appears in the module at all now. The refusal names an expiry; the anchor it implies is that minus the declared window; the same facility asked INSIDE its window must serve on exactly that anchor and name it as the freshest valuation in its own payload. The estate closes the loop, and the failure message says to re-measure rather than re-pin |
| 7 | Ruling 3's `open_product` half had no control — only the builder half did | **`C4c`**: a config declaring the anchor with no `half_life` section is refused by `open_product`, by name |
| 8 | `TTLAnchorUndeclared` had gained a second meaning and a second raise site while its own docstring still defined only the first, and the module's R-3 taxonomy did not mention the no-table case | both widened to name the two configuration failures and the two registration sites |
| 9 | The calibration's stated basis — the window IS `half_life.real_property_appraisal` — was asserted in four documents and held by nothing | one assertion in `CSCC-G24`'s test holds the two declarations equal. It adds no second authority for the value; it holds the stated relationship |
| 10 | `build_governed_resolver`'s surface: `evidence_clock_key` was an undocumented public parameter that the new refusal message points adopters at, and the `Raises:` block did not name `TTLAnchorUndeclared` | both documented, with what each key is for and why omitting both is refused for an evidence-anchored class |
| 11 | Stale prose the calibration left behind: the `rehydrate_product` contract claimed an omitted anchor "still passes the address check" (it would not — only the `None` sentinel is hash-transparent); CP-SPEC-006C §A.2 described the deleted per-facility control instants and the specimen's old failure mode; the roster header said `G01`–`G23` with 24 gates declared; the lane docstring had a half-edited sentence | each corrected |

**Refuted and recorded as rejected:** that `CSCC-G24` was never observed red and is missing from
the sabotage matrix; that the 365-day currency claim "travels on the wire" while the set-off
leg's undatedness does not; that 56 of the lane baseline's characters were derived from the
system under test; that the serve-time "reaches no λ_c table" branch is now unreachable through
both shipped builders; that two gates pin estate figures against §G.1's claim; and two findings
that the reviewed SHA had moved (true, and the delta was doc-only).

**After the repairs:** cp-06-canonical 29, cp-08 20, CP-14 fourth slice 13, SDK products +
replay + contracts 1704, lint 0, typecheck clean, product-gates 19 / 326 / 326. The controls in
`tests/products/test_d_impl_341_ttl_anchor.py` now number fourteen (C1, C2, C4, C4b, C4c, C5,
C6, C7, C8, C9, C10, C11, C12 and C11's second parametrization), and the module's own index
names them.
