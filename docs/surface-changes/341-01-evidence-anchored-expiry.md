# 341-01 — `expires_at` describes when the evidence stopped being current

Applied 2026-09-18 under `D-IMPL-341` (Dave's implementation GO with rulings R-1–R-5, recorded in
`docs/DECISIONS.md` before implementation; design `docs/D-IMPL-341-DESIGN.md`). The measurement that
opened it: `CP03C-F-01` — a class declaring `ttl_anchor: from_entity_freshness` had the declaration
copied onto its contract and its expiry computed from the decision instant, so the served
`expires_at` advertised a validity window the evidence never had.

## What did NOT change, stated first

- **A `from_decision` class serves exactly the expiry it served** (`decided_at + window`,
  `D-IMPL-308`); it now also states that instant as `ttl_anchor_at`.
- **The `TTLAnchor` vocabulary, `MaxTTL`, `TtlBinding`, `compose_expiry`'s signature and
  `replay()`'s product-only contract** are unchanged.
- **Every record and product written before this change keeps its content address**: the new
  members are hash-transparent at `None`, and replay treats a record without `ttl_anchor_at`
  as decision-anchored by definition of that sentinel, skipping the anchor hold by name.
- **The freshness and debt calculation is untouched.** The anchor reads the observations the
  reference scorer already builds and the decay basis the λ_c row already declares.

## ccf.products.expiry.FROM_DECISION

- Surface: ccf.products.expiry.FROM_DECISION
- Public surface: true
- Change type: added
- Before: absent — `expires_at` was minted inline as `decided_at + product_ttl_seconds` on both resolver branches and the declared anchor was read by nothing
- After: `Final = "from_decision"` — the `TTLAnchor` member, named once
- Why: D-IMPL-341 R-1 / R-3 (`8f84f710`) — one pure function at the mint, reusing the deployment's declared decay clock; nothing minted, nothing read off a payload, nothing defaulted
- Migration: none

## ccf.products.expiry.FROM_ENTITY_FRESHNESS

- Surface: ccf.products.expiry.FROM_ENTITY_FRESHNESS
- Public surface: true
- Change type: added
- Before: absent — `expires_at` was minted inline as `decided_at + product_ttl_seconds` on both resolver branches and the declared anchor was read by nothing
- After: `Final = "from_entity_freshness"` — the other `TTLAnchor` member, named once
- Why: D-IMPL-341 R-1 / R-3 (`8f84f710`) — one pure function at the mint, reusing the deployment's declared decay clock; nothing minted, nothing read off a payload, nothing defaulted
- Migration: none

## ccf.products.expiry.TTLAnchorResolution

- Surface: ccf.products.expiry.TTLAnchorResolution
- Public surface: true
- Change type: added
- Before: absent — `expires_at` was minted inline as `decided_at + product_ttl_seconds` on both resolver branches and the declared anchor was read by nothing
- After: a `CCFContract` — `anchor_at`, `basis`, `contributing_types` — what a class's TTL anchor resolved to for one decision
- Why: D-IMPL-341 R-1 / R-3 (`8f84f710`) — one pure function at the mint, reusing the deployment's declared decay clock; nothing minted, nothing read off a payload, nothing defaulted
- Migration: none

## ccf.products.expiry.TTLAnchorUndeclared

- Surface: ccf.products.expiry.TTLAnchorUndeclared
- Public surface: true
- Change type: added
- Before: absent — `expires_at` was minted inline as `decided_at + product_ttl_seconds` on both resolver branches and the declared anchor was read by nothing
- After: a `ValueError` — a class declares `from_entity_freshness` over a clock no data could honor; a configuration failure raised at registration, at open and at the builder
- Why: D-IMPL-341 R-1 / R-3 (`8f84f710`) — one pure function at the mint, reusing the deployment's declared decay clock; nothing minted, nothing read off a payload, nothing defaulted
- Migration: none for a `from_decision` class. A class declaring `from_entity_freshness` must declare at least one `decay_basis: valid-from` row **keyed by an entity class the view carries** and stamp the source instant as `observed_time` on those claims; otherwise it is refused by name at open / at the builder (no row) or at gate 3 (no usable instant)

## ccf.products.expiry.refuse_undeclared_ttl_anchor

- Surface: ccf.products.expiry.refuse_undeclared_ttl_anchor
- Public surface: true
- Change type: added
- Before: absent — `expires_at` was minted inline as `decided_at + product_ttl_seconds` on both resolver branches and the declared anchor was read by nothing
- After: `refuse_undeclared_ttl_anchor(*, ttl_anchor: str, entries: Mapping[str, object] | None, product_class: str) -> None` — refuses, by name, an evidence-anchored class no λ_c row could support (`TTLAnchorUndeclared`)
- Why: D-IMPL-341 R-1 / R-3 (`8f84f710`) — one pure function at the mint, reusing the deployment's declared decay clock; nothing minted, nothing read off a payload, nothing defaulted
- Migration: none for a `from_decision` class. A class declaring `from_entity_freshness` must declare at least one `decay_basis: valid-from` row **keyed by an entity class the view carries** and stamp the source instant as `observed_time` on those claims; otherwise it is refused by name at open / at the builder (no row) or at gate 3 (no usable instant)

## ccf.products.expiry.resolve_ttl_anchor

- Surface: ccf.products.expiry.resolve_ttl_anchor
- Public surface: true
- Change type: added
- Before: absent — `expires_at` was minted inline as `decided_at + product_ttl_seconds` on both resolver branches and the declared anchor was read by nothing
- After: the anchor for one decision: the decision instant for `from_decision`; for `from_entity_freshness` the freshest `valid_from` among the per-series leading edges, as of the decision instant, of observation types whose λ_c row declares `decay_basis: valid-from` — over the reference scorer's own observation set, narrowed to the types the table declares; returns a `TTLAnchorResolution`
- Why: D-IMPL-341 R-1 / R-3 (`8f84f710`) — one pure function at the mint, reusing the deployment's declared decay clock; nothing minted, nothing read off a payload, nothing defaulted
- Migration: none for a `from_decision` class. A class declaring `from_entity_freshness` must declare at least one `decay_basis: valid-from` row **keyed by an entity class the view carries** and stamp the source instant as `observed_time` on those claims; otherwise it is refused by name at open / at the builder (no row) or at gate 3 (no usable instant)

## ccf.products.expiry.valid_from_rows

- Surface: ccf.products.expiry.valid_from_rows
- Public surface: true
- Change type: added
- Before: absent — `expires_at` was minted inline as `decided_at + product_ttl_seconds` on both resolver branches and the declared anchor was read by nothing
- After: `valid_from_rows(entries: Mapping[str, object] | None) -> tuple[str, ...]` — the observation types whose λ_c row decays against `valid_from`; the rows that could contribute to an evidence anchor
- Why: D-IMPL-341 R-1 / R-3 (`8f84f710`) — one pure function at the mint, reusing the deployment's declared decay clock; nothing minted, nothing read off a payload, nothing defaulted
- Migration: none

## ccf.products.gates.TTLAnchorRefusal

- Surface: ccf.products.gates.TTLAnchorRefusal
- Public surface: true
- Change type: added
- Before: absent — a missing evidence instant had no name and would have been served decision-anchored
- After: gate 3's second reason, kind `ttl-anchor-refusal`, reason `GATE_TTL_ANCHOR` (`ttl-anchor-unresolvable`), carrying the declared anchor, the decision instant, the rows that could have contributed and the observation types the set held; distinct from `TTLRefusal` (`ttl-bounds`: an anchor exists and its window has passed); nothing actionable at minimal disclosure; HTTP status `STATUS_FULFILLMENT_WITHHELD`
- Why: D-IMPL-341 R-3 — missing evidence is not expired evidence
- Migration: none; the refusal vocabulary grows by one kind, deliberately (`REFUSAL_KINDS`, `PERMITTED_AT_MINIMAL`, `STATUS_BY_KIND`)

## ccf.products.gates.GATE_TTL_ANCHOR

- Surface: ccf.products.gates.GATE_TTL_ANCHOR
- Public surface: true
- Change type: added
- Before: absent
- After: `"ttl-anchor-unresolvable"`, the reason token of the refusal above
- Why: D-IMPL-341 R-3
- Migration: none

## ccf.products.contract.ContextProductContract

- Surface: ccf.products.contract.ContextProductContract
- Public surface: true
- Change type: reshaped
- Before: `expires_at` and the declared `ttl_anchor`; no statement of the instant the window ran from
- After: `ttl_anchor_at: datetime | None`, hash-transparent at `None` — the instant the class's anchor resolved to, on every newly served product (`decided_at` for `from_decision`); `expires_at − ttl_anchor_at` is the declared window
- Why: D-IMPL-341 R-2 — every product states its basis; `None` is the pre-341 sentinel only
- Migration: none for readers; a replay environment that rebuilds the envelope by hand carries `ttl_anchor_at` off the record's dimension 5 (`content_generation_path.ttl_anchor_at`) for a record that has it, and omits it for one that does not

## ccf.replay.record.ContentGenerationPath

- Surface: ccf.replay.record.ContentGenerationPath
- Public surface: true
- Change type: reshaped
- Before: no anchor instant on dimension 5
- After: `ttl_anchor_at: datetime | None`, hash-transparent at `None`, copied from the served product by `build_replay_record`
- Why: D-IMPL-341 R-5 — replay re-derives the anchor and holds it to the record; a record without the member is skipped by name
- Migration: none; records written before this change reload to their addresses

## ccf.replay.record.ChildResolution

- Surface: ccf.replay.record.ChildResolution
- Public surface: true
- Change type: reshaped
- Before: `child_expires_at` only
- After: `child_ttl_anchor: str | None` and `child_ttl_anchor_at: datetime | None`, hash-transparent at `None`, copied from the admitted child's contract by `_row_for_admitted`
- Why: D-IMPL-341 — a consumer may print what the child's contract states about its own anchor, and nothing more (design §8)
- Migration: none

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: reshaped
- Before: no way to reach the λ_c table at the mint
- After: a required constructor argument `half_life_key: str | None` — the table's manifest key, read at the mint for an evidence-anchored expiry and pinned on such a record; `None` for a resolver wired without a table (an evidence-anchored class then refuses by name at gate 3). Required rather than defaulted, on the seam's own no-defaults rule
- Why: D-IMPL-341 R-1 / R-5
- Migration: every direct construction names it; `build_governed_resolver` passes it

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: reshaped
- Before: `half_life_key` was scorer material only, exclusive with a supplied `debt_scorer`
- After: a new optional `evidence_clock_key: str | None = None` — the same manifest key, stated for the resolver when the scorer is supplied (the paved road passes it); the two must agree if both are given; the builder refuses a `from_entity_freshness` declaration over a table with no `valid-from` row (`TTLAnchorUndeclared`)
- Why: D-IMPL-341 R-3 (first row) at the builder, for resolvers wired by hand
- Migration: none for callers that let the builder build the scorer; a caller supplying a scorer and wanting evidence anchoring passes `evidence_clock_key`

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: a `from_entity_freshness` declaration over a table with no `valid-from` row opened and served decision-anchored
- After: refused at open by name (`TTLAnchorUndeclared`); the paved argument bundle carries `evidence_clock_key`
- Why: D-IMPL-341 R-3 (first row) at the paved road's registration moment
- Migration: cp-04-canonical, cp-06-canonical and cp-08 (declared, no such row) are refused at open until their validation passes carry a clock or declare `from_decision`

## ccf.replay.engine.replay

- Surface: ccf.replay.engine.replay
- Public surface: true
- Change type: behavior
- Before: no anchor hold
- After: after rehydration and before the address check, the anchor is held: a decision-anchored record's `ttl_anchor_at` must equal its `recorded_at`; an evidence-anchored record's anchor is re-derived over the re-executed view under the λ_c table the record pinned and must equal the recorded member (`ReplayDivergence` otherwise; `ReplayUnresolvable` if no table is pinned); a record without the member is skipped by name
- Why: D-IMPL-341 R-5
- Migration: none for pre-341 records; a replay environment for a new record carries `ttl_anchor_at` from the record (see `ContextProductContract` above)

## ccf.products.composite.compose_children

- Surface: ccf.products.composite.compose_children
- Public surface: true
- Change type: reshaped
- Before: `compose_children(*, own_factors, requirements, outcomes, asked_at, composition_invocation, own_lineage, max_ttl, ttl_anchor_at, validity_floors)` — one instant served as both the expiry anchor and the instant remaining validity was measured from
- After: adds the required keyword `decided_at: datetime` between `ttl_anchor_at` and `validity_floors` — the decision instant, and the instant `D-IMPL-31`'s mixing law measures each constituent's remaining validity from; `ttl_anchor_at` is used for the expiry only
- Why: `D-IMPL-341` (`8c0388dc`, *the mixing law measures remaining validity from the decision instant*) — the review of `D-IMPL-341` caught the two sharing one argument: with an evidence anchor weeks before the decision, a child's remaining validity was overstated by exactly that gap and a constituent breaching its declared floor at the decision instant composed anyway. How long is left is a fact about now; how long the answer is good for is a fact about its evidence. Recorded at the `f0656746` qualification (2026-09-19); the commit regenerated no manifest and claimed no entry
- Migration: every direct caller passes `decided_at`; the SDK's one caller, `GovernedResolver`, does
