# D-IMPL-341 — design: `expires_at` describes when the evidence stopped being current

**Status: design only (2026-09-18), awaiting the implementation GO. No SDK, runtime,
example or test-behavior code in this package.** Branch `d-impl-341-design` from the
verified baseline `main @ f8c33898` (post-`D-GATE-342`). The decisions of record are
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
