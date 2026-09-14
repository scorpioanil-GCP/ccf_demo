# D-IMPL-336 O2 — a child invocation is bound to an EFFECTIVE grant

Applied 2026-09-13 under `D-IMPL-336` Amendment 4, checkpoint 1. Closes **O2**,
which the panel raised against Amendment 3's own repair and stated precisely:
*"the token replaced free strings but did not bind them."*

Amendment 3 replaced the caller's free `skill_name` / `skill_version` /
`grant_hash` strings with a `ChildInvocation` minted from a resolved catalog
entry. That closed half the hole. The entry was real; the `grant_hash` beside
it was still whatever the assembler typed, and nothing compared the two. A
child produced by a genuinely granted skill could be recorded against a grant
that authorized something else, or against one that had been revoked.

## What changed

- **`BoundSkillView.grant_hash_for(name)`** — new. The ledger already resolved
  which grant put each bound skill in force (as `holders`, to detect
  collisions) and then discarded it. It is returned now, so authority and
  capability travel together. Resolved from ledger state at access time, like
  every other read on the view, so a revoked grant stops answering immediately.
- **`ResolvedProducer`** — new, and minted **only** by
  `resolve_producing_grant`. It pairs the entry with the grant hash that put it
  in force. A plain frozen dataclass would have reproduced O2 exactly — a real
  entry beside a caller's string — so it carries the same construction-token
  discipline as `ChildInvocation` and `AdmittedChild`.
- **`resolve_producing_grant(requirement, bound_skills)`** — `bound_skills` is
  now the agent's live `BoundSkillView` rather than `Mapping[str,
  SkillCatalogEntry]`, and the return is `ResolvedProducer | None`. The looser
  type was a door: a plain dict of entries carries no evidence that any of them
  was ever granted, so *"resolved from the in-force grants"* was a claim in the
  docstring rather than a property of the call.
- **`invocation_from_dispatch(producer)`** — the `grant_hash` keyword is
  **gone**, not deprecated. While it existed the function minted authority from
  any entry plus any string. An accepted parameter that no longer binds
  anything is the defect class this work exists to repair (the same reasoning
  that made an accepted-and-ignored `RefusalRecorderProtocol` parameter get
  backed out rather than shipped).

## What did not change

`GrantLedger`'s state machine, `bound_view`, `GrantCollisionError`, and the
`D-09` single-use grant rule are untouched. `_effective_entries` keeps its
signature and its behavior; it derives from the new `_effective_grants`.

## Proof

`tests/products/test_composite.py` — `test_o2_a_revoked_grant_cannot_initiate_a_child`,
`test_o2_an_ungranted_entry_produces_nothing_however_real_it_is`,
`test_o2_a_resolved_producer_cannot_be_authored`,
`test_positive_control_producer_substitution_leaves_the_contract_alone`
(rewritten as grant → **revoke** → grant, which is what a Control Plane
operator actually performs; holding both producers effective at once is
`AmbiguousProducerError`, asserted separately).

**Still open.** `invocation_from_dispatch` proves an in-force grant authorized
the producer. It does **not** yet prove a dispatch actually ran — that evidence
arrives with the reference `CompositeChildResolverProtocol` implementation, and
until it does the claim here is exactly "granted", never "invoked".

## Surface entries

## ccf.products.composite.ResolvedProducer

- Surface: ccf.products.composite.ResolvedProducer
- Public surface: true
- Change type: added
- Before: absent — the entry and the grant hash travelled separately, and only the entry was evidence
- After: a token-minted pair carrying the catalog entry and the hash of the grant that put it in force (D-IMPL-336 O2)
- Why: pairing a real entry with a caller-chosen grant hash let an authorized producer be recorded against an unrelated or revoked grant
- Migration: obtain one from `resolve_producing_grant`; it cannot be constructed

## ccf.products.composite.resolve_producing_grant

- Surface: ccf.products.composite.resolve_producing_grant
- Public surface: true
- Change type: reshaped
- Before: took `Mapping[str, SkillCatalogEntry]` and returned `SkillCatalogEntry | None`
- After: takes the agent's live `ccf.skills.grants.BoundSkillView` and returns `ResolvedProducer | None` (D-IMPL-336 O2)
- Why: a plain mapping of entries carries no evidence that any of them was granted, so the in-force claim was a docstring rather than a property of the call
- Migration: pass `ledger.bound_view(agent_definition_hash)` instead of a dict; read `.entry` off the result where the entry itself is wanted

## ccf.products.composite.invocation_from_dispatch

- Surface: ccf.products.composite.invocation_from_dispatch
- Public surface: true
- Change type: reshaped
- Before: `invocation_from_dispatch(entry, *, grant_hash)` — minted authority from any entry plus any string
- After: `invocation_from_dispatch(producer)` — both halves come from the ledger (D-IMPL-336 O2)
- Why: an accepted parameter that no longer binds anything is the defect class this work repairs, so the keyword is removed rather than deprecated
- Migration: resolve through `resolve_producing_grant` and pass the `ResolvedProducer`; there is no compatibility shim

## ccf.skills.grants.BoundSkillView.grant_hash_for

- Surface: ccf.skills.grants.BoundSkillView.grant_hash_for
- Public surface: true
- Change type: added
- Before: absent — the ledger resolved which grant put each bound skill in force and discarded it
- After: returns that grant hash, resolved from ledger state at access time (D-IMPL-336 O2)
- Why: there was no supported way to ask which grant authorized a bound entry, which is what forced callers to supply one
- Migration: none required — additive; raises `KeyError` for a skill this agent does not hold
