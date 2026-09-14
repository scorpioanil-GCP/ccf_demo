# D-IMPL-336 — composite Context Products: the swarm composition surface

Applied 2026-09-13 under `D-IMPL-336` (Dave) and its two amendments. Two new
modules and three new fields on existing artifacts. **This is the
aggregate-product surface `D-IMPL-104` deferred**, arriving as that entry said
it would: *"Implementation can wait until the surface appears; the meaning
cannot."*

The pattern, in Dave's terms: *"Skills produce governed Context Products.
Agents orchestrate skills. Composite Context Products declare the child Context
Product classes they require."* — and under it, *"Agents have skills; Context
Products have state."*

## What did NOT change, stated first

- **No content address of any existing artifact moves.** All three new fields
  are hash-transparent at a sentinel that is the state of every artifact
  written before them (`D-IMPL-243`). **Measured, not argued**, against `main`
  by `git archive main src | tar -x` and reconstruction under the base tree:
  `SkillCatalogEntry` at `53a94c2c…` and `ContentGenerationPath` at
  `a74187ca…`, both reproducing byte-for-byte at HEAD.
  `RegisteredProductClass` is covered by its existing `13bd250` digest.
  `tests/contracts/test_hash_transparency.py::test_d_impl_336_marks_are_silent_at_their_sentinels`.
- **No existing grant is invalidated.** A grant references a catalog entry by
  version; the entry's identity is unchanged at the `produces` sentinel, so
  every grant in force stays in force.
- **No new invalidation mechanism.** Eligibility reuses
  `refuse_dependency_invalidation` (`D-IMPL-334`/`D-IMPL-335`), which is
  **promoted from private to public** in this change and otherwise untouched —
  the only rename in the diff, and it exists so the composite can call the
  ruled mechanism rather than grow a second one.
- **No debt formula.** `compose_debt_factors` composes **factors**; `D_c` is
  still `context_debt`'s `1 − (F·C·S)`, with **zero new weights**, exactly as
  `D-IMPL-104` predicted. The additive-form foreclosure in
  `src/ccf/halflife/debt.py` is untouched.
- **No wire contract.** The peered-eligibility assertion travels in
  `IdentityProvider.sign(assertions=...)`, an **existing** parameter that
  already places members in the JWS protected header, which
  `PeeringAdmissionGate` already holds peers to.
- **No scheduler, no parallel framework, no DAG runtime, no event bus, no
  background worker.** Running child skills concurrently is the harness's,
  exactly as the agent loop is (CLAUDE.md §7.3).
- **No example changed and no CP-14 acquisition started.**

## Added

### `ccf.products.composite` — new module

`AdmittedChild` · `ChildAdmissionBypassError` · `ChildAdmissionRefusal` ·
`ChildCandidate` · `CompositeAdmissionGate` · `CompositionOutcome` ·
`AmbiguousProducerError` · `ProducingFabric` / `ProducedHere` /
`ProducedElsewhere` · `compose_children` · `resolve_producing_grant` ·
`GATE_CHILD_ADMISSION` · `ELIGIBILITY_LOCAL_REGISTER` ·
`ELIGIBILITY_PRODUCER_ATTESTED`.

### `ccf.peering.eligibility` — new module

`EligibilityAssertion` · `EligibilityAssertionMalformed` ·
`mint_eligibility_assertion` · `encode_eligibility_assertion` ·
`decode_eligibility_assertion` · `ELIGIBILITY_ASSERTION_HEADER` ·
`ELIGIBILITY_ASSERTION_SCHEMA_VERSION`.

### On existing modules

| Name | Where |
| --- | --- |
| `NO_PRODUCT_CLASS`, `SkillCatalogEntry.produces` | `ccf.skills.catalog` |
| `ChildRequirement`, `OptionalAbsenceTreatment`, `requirements_declaration_is_coherent`, `RegisteredProductClass.requires` | `ccf.products.contract` |
| `compose_debt_factors`, `EmptyFactorCompositionError` | `ccf.halflife.debt` |
| `ChildResolution`, `CHILD_ADMITTED`, `CHILD_OUTCOME_STATUSES`, `ContentGenerationPath.child_resolutions` | `ccf.replay.record` |
| `refuse_dependency_invalidation` (**promoted from `_`-private**) | `ccf.products.gates` |

## THREE CHOICES A READER WILL WANT THE REASON FOR

**`requires` is a tuple, not a frozenset.** Declaration order is the order rows
appear in replay and the order a refusal names. This tree has shipped the
set-read-as-an-order defect twice in consecutive rungs, so the type has to be
able to carry the order.

**Two grants producing one class REFUSE, with no tie-breaker.** Any rule the
SDK invented — grant order, name sort, most recent — would make composition and
replay depend on something the deployment never declared. Interchangeability is
proven by **substitution**, which is a positive control rather than a sabotage.

**The refusal kind is `composite-child-refusal`, not `child-admission-refusal`.**
The first spelling **contained** the existing `admission-refusal` token, and the
vocabulary forbids one token containing another — a consumer prefix-matching
`admission-refusal` would have silently swallowed every composite refusal.
Caught by `test_every_kind_has_its_own_test_function`, which is exactly the
guard that should catch it.

## Disclosure, because retention is not disclosure

`PERMITTED_AT_MINIMAL["composite-child-refusal"]` is `{"product_class"}` alone.
A rejected child's `child_content_address` is **retained in protected replay**
(`D-IMPL-336` Amendment 2: a product produced and rejected is not a product
that never existed) and **withheld externally** — on an information-barrier
composition the existence of a specific rejected child is itself a disclosure.
An examiner reads it from the decision record, where `ChildResolution` carries
it in full.


## Surface entries

## ccf.products.composite.AdmittedChild

- Surface: ccf.products.composite.AdmittedChild
- Public surface: true
- Change type: added
- Before: absent — nothing represented a child product that had passed a composite's admission checks
- After: an unforgeable-through-supported-interfaces capability object; holding one IS the evidence every admission check ran, and `compose_children` accepts nothing weaker
- Why: makes *compose the unauthorized child, then post-filter it* unspellable through any supported route — the `CXR-G22` failure, where a post-filter and a pre-filter return the same hits so the payload cannot tell them apart
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ChildAdmissionBypassError

- Surface: ccf.products.composite.ChildAdmissionBypassError
- Public surface: true
- Change type: added
- Before: absent
- After: raised when an `AdmittedChild` is constructed outside the gate, by constructor or by subclass
- Why: the runtime half of the token control; the claim is bounded to the supported interfaces and does not pretend to defeat `object.__new__`
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ChildAdmissionRefusal

- Surface: ccf.products.composite.ChildAdmissionRefusal
- Public surface: true
- Change type: added
- Before: absent — a child that failed admission had no typed governed refusal
- After: a `GateRefusal` subclass carrying `product_class`, a machine-readable `reason`, and the rejected product's `child_content_address` when one is known
- Why: a product produced and rejected is not a product that never existed (`D-IMPL-336` Amendment 2); its identity is retained so an admission failure cannot read as an absence
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ChildCandidate

- Surface: ccf.products.composite.ChildCandidate
- Public surface: true
- Change type: added
- Before: absent
- After: one served child plus the provenance admission needs: requirement, contract, reported address, producing fabric, skill, version and grant
- Why: the gate recomputes the content address from the contract rather than trusting the reported one, so the candidate must carry both
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.CompositeAdmissionGate

- Surface: ccf.products.composite.CompositeAdmissionGate
- Public surface: true
- Change type: added
- Before: absent — only inbound A2A products had an admission gate (`PeeringAdmissionGate`)
- After: the one gate every child passes whatever produced it: class match, version lane, reconstruction instant, recomputed address, assessable debt, eligibility
- Why: *the composite should not care how a child was constructed* is only true if it checks them all the same way; peering adds checks and never skips them
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.CompositionOutcome

- Surface: ccf.products.composite.CompositionOutcome
- Public surface: true
- Change type: added
- Before: absent
- After: composed factors or a refusal, plus a `ChildResolution` row for every requirement either way
- Why: a requirement that produced nothing and left no row would be indistinguishable from one never declared
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.AmbiguousProducerError

- Surface: ccf.products.composite.AmbiguousProducerError
- Public surface: true
- Change type: added
- Before: absent
- After: raised when two in-force grants declare the same `produces` class; no tie-breaker is applied
- Why: any rule the SDK invented would make composition and replay depend on something the deployment never declared; interchangeability is proven by substitution instead
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ProducingFabric

- Surface: ccf.products.composite.ProducingFabric
- Public surface: true
- Change type: added
- Before: absent
- After: which fabric produced a child — the fact that determines eligibility authority
- Why: a skill's transport label says how bytes were fetched, never whose Control Plane knows the entities' invalidation state
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ProducedHere

- Surface: ccf.products.composite.ProducedHere
- Public surface: true
- Change type: added
- Before: absent
- After: this fabric produced the child, so its own `EntityInvalidationRegister` is authoritative
- Why: reuses `D-IMPL-334`/`D-IMPL-335` rather than building a second mechanism
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ProducedElsewhere

- Surface: ccf.products.composite.ProducedElsewhere
- Public surface: true
- Change type: added
- Before: absent
- After: another fabric produced it; carries the protected header whose signed eligibility assertion is the only thing that can establish eligibility
- Why: the local register is tenant-scoped, so its silence about a remote product is *don't know*, and reading that as *pass* is the collapse this project's measurement rules forbid
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.compose_children

- Surface: ccf.products.composite.compose_children
- Public surface: true
- Change type: added
- Before: absent
- After: walks the declared requirements in order, composes admitted children, refuses on a required failure, and records a row per requirement
- Why: the composition entry point; declaration order is preserved because it is the order rows appear in replay and a refusal names
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.resolve_producing_grant

- Surface: ccf.products.composite.resolve_producing_grant
- Public surface: true
- Change type: added
- Before: absent
- After: resolves a requirement's product CLASS to the one in-force grant whose entry produces it
- Why: class to skill, never skill to class — a requirement naming an implementation would couple the composite to the thing this pattern decouples from
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.GATE_CHILD_ADMISSION

- Surface: ccf.products.composite.GATE_CHILD_ADMISSION
- Public surface: true
- Change type: added
- Before: absent
- After: the gate identifier every child-admission refusal carries
- Why: so a child refusal reads in an audit exactly as a TTL or attestation refusal does
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ELIGIBILITY_LOCAL_REGISTER

- Surface: ccf.products.composite.ELIGIBILITY_LOCAL_REGISTER
- Public surface: true
- Change type: added
- Before: absent
- After: `eligibility_basis` when this fabric's own register was authoritative
- Why: which authority answered is recorded rather than assumed; *eligible* alone would make local and attested evidence indistinguishable
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.composite.ELIGIBILITY_PRODUCER_ATTESTED

- Surface: ccf.products.composite.ELIGIBILITY_PRODUCER_ATTESTED
- Public surface: true
- Change type: added
- Before: absent
- After: `eligibility_basis` when the producing fabric attested it
- Why: the peered counterpart, and different evidence with different trust
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.peering.eligibility.EligibilityAssertion

- Surface: ccf.peering.eligibility.EligibilityAssertion
- Public surface: true
- Change type: added
- Before: absent — nothing let a producer state that it had checked a child's eligibility
- After: a typed, versioned claim bound to child address, requested `as_of`, producer, consumer scope, `checked_at` and composition invocation
- Why: an unbound assertion could be lifted from any envelope into any composition; the invocation binding is what makes replay detectable
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.peering.eligibility.EligibilityAssertionMalformed

- Surface: ccf.peering.eligibility.EligibilityAssertionMalformed
- Public surface: true
- Change type: added
- Before: absent
- After: raised at the decode boundary for an absent, unparseable or unknown-version claim
- Why: *I cannot read the claim* and *I read it and it is about something else* are different findings and must not share a shape
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.peering.eligibility.mint_eligibility_assertion

- Surface: ccf.peering.eligibility.mint_eligibility_assertion
- Public surface: true
- Change type: added
- Before: absent
- After: records a verdict the producer's Control Plane has ALREADY reached; it evaluates nothing
- Why: a mint that also decided would let a caller obtain an attestation without a register ever being consulted
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.peering.eligibility.encode_eligibility_assertion

- Surface: ccf.peering.eligibility.encode_eligibility_assertion
- Public surface: true
- Change type: added
- Before: absent
- After: renders the assertion to canonical bytes for the protected header
- Why: so the string a producer signs and the one a consumer re-derives cannot differ by key order or whitespace
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.peering.eligibility.decode_eligibility_assertion

- Surface: ccf.peering.eligibility.decode_eligibility_assertion
- Public surface: true
- Change type: added
- Before: absent
- After: parses a protected-header member back into the typed assertion, refusing an unknown schema version
- Why: an unknown lane may bind facts this build would silently ignore, so it is refused rather than read leniently
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.peering.eligibility.ELIGIBILITY_ASSERTION_HEADER

- Surface: ccf.peering.eligibility.ELIGIBILITY_ASSERTION_HEADER
- Public surface: true
- Change type: added
- Before: absent
- After: the protected-header member name the assertion travels in
- Why: distinct from the producing-agent assertion, so one cannot be presented as the other
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.peering.eligibility.ELIGIBILITY_ASSERTION_SCHEMA_VERSION

- Surface: ccf.peering.eligibility.ELIGIBILITY_ASSERTION_SCHEMA_VERSION
- Public surface: true
- Change type: added
- Before: absent
- After: the assertion contract's own lane
- Why: lets a consumer refuse a shape it does not understand instead of reading unknown members as absent
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.halflife.debt.compose_debt_factors

- Surface: ccf.halflife.debt.compose_debt_factors
- Public surface: true
- Change type: added
- Before: absent — `D-IMPL-104` ruled the meaning of aggregate debt in 2026-08 and DEFERRED the implementation until an aggregate-product surface existed to carry it
- After: the per-factor minimum over the parent's own factors and its admitted children's, feeding the unchanged `context_debt`
- Why: `D-IMPL-104` predicted exactly this: *one pure function beside `context_debt`*, adding ZERO new weights. Never `max(child D_c)` — measured, that reports 0.500 where the correct composition reports 0.750, understating by a third on a control whose job is to escalate
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.halflife.debt.EmptyFactorCompositionError

- Surface: ccf.halflife.debt.EmptyFactorCompositionError
- Public surface: true
- Change type: added
- Before: absent
- After: raised when the parent's own factors are missing
- Why: composing children alone would emit a parent asserting nothing it assembled itself
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.contract.ChildRequirement

- Surface: ccf.products.contract.ChildRequirement
- Public surface: true
- Change type: added
- Before: absent — a product class could not declare what it composes over
- After: `product_class`, `required` (no default), `compatible_from` (caret-shaped lane), and an optional-only `absence_treatment`
- Why: names a CLASS, never a skill; and it is carried in a TUPLE because declaration order is load-bearing and this tree has shipped the set-read-as-order defect twice
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.contract.OptionalAbsenceTreatment

- Surface: ccf.products.contract.OptionalAbsenceTreatment
- Public surface: true
- Change type: added
- Before: absent
- After: the class-declared `C` factor a declared-absent optional child contributes, plus which outcomes policy permits omitting from the payload
- Why: what a missing optional input costs is a domain judgement; the SDK holds no numeric default, and an optional requirement cannot be declared without one
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.contract.requirements_declaration_is_coherent

- Surface: ccf.products.contract.requirements_declaration_is_coherent
- Public surface: true
- Change type: added
- Before: absent
- After: refuses a `requires` list with a duplicate product class
- Why: two requirements naming one class have no distinct resolution — the same skill would be invoked, recorded and composed twice
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.replay.record.ChildResolution

- Surface: ccf.replay.record.ChildResolution
- Public surface: true
- Change type: added
- Before: absent — `grant_set_hash` answered WHICH SKILLS an agent held and could not answer which one satisfied which requirement
- After: an ordered dimension-5 row binding required class to skill and grant to child address, with the child's version, instants, `D_c`, factors, policy versions, lineage and eligibility basis
- Why: a hash of a set has no mapping in it. Dimension 5 and not 4 because dimension 4 answers *for whom, with what authority* while this answers how the content came to be — the same reasoning `request` and `debt` were placed there under
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.replay.record.CHILD_ADMITTED

- Surface: ccf.replay.record.CHILD_ADMITTED
- Public surface: true
- Change type: added
- Before: absent
- After: the `outcome_status` of a composed child
- Why: one token, so an admitted row is matched by identity rather than by prose
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.replay.record.CHILD_OUTCOME_STATUSES

- Surface: ccf.replay.record.CHILD_OUTCOME_STATUSES
- Public surface: true
- Change type: added
- Before: absent
- After: the closed `outcome_status` vocabulary
- Why: keeps declared-absent, refused, ineligible and unauthorized DISTINCT; collapsing any pair would let a governance failure read as a data gap
- Migration: none required — new name, nothing to update. An adopter wanting composite products declares `requires` on a product class and `produces` on the skills that satisfy it

## ccf.products.gates.refuse_dependency_invalidation

- Surface: ccf.products.gates.refuse_dependency_invalidation
- Public surface: true
- Change type: added
- Before: absent from the PUBLIC manifest — the mechanism existed as the private `_refuse_dependency_invalidation` and was never public API
- After: the same function, published under its public name; body unchanged
- Why: the composite must call the RULED `D-IMPL-334`/`D-IMPL-335` mechanism rather than grow a second invalidation system. The only rename in this change
- Migration: nothing in the tree imported the private name — verified by `grep -rn _refuse_dependency_invalidation src/ tests/ tools/`, which returns nothing after this change. An out-of-tree caller reaching the private name drops the leading underscore; the body is identical

## ccf.skills.catalog.NO_PRODUCT_CLASS

- Surface: ccf.skills.catalog.NO_PRODUCT_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: the sentinel `produces` carries when a skill emits no governed Context Product
- Why: a POSITIVE statement — *this skill emits no product* — and not silence (`D-IMPL-38`); it is also the value at which the field is hash-transparent, so every entry registered before `produces` existed keeps its identity
- Migration: none required. A skill left at the sentinel simply cannot satisfy a composite requirement, which is the intended default

## ccf.skills.catalog.SkillCatalogEntry

- Surface: ccf.skills.catalog.SkillCatalogEntry
- Public surface: true
- Change type: reshaped
- Before: declared `argument_schema` (what it takes) and `requirements` (what policy it needs), and NOTHING about what it produces
- After: gains `produces: str = NO_PRODUCT_CLASS` — the mirror of the existing `SkillRequirements.required_context_products`
- Why: one missing field was the whole gap: a composite's `requires` names a product CLASS, and without a skill declaring what it emits there is nothing to resolve the requirement against. Reuse falls out of it — the same Covenant Skill serves a memo, a surveillance run, an onboarding and a refinancing
- Migration: none required, and no existing artifact moves. Measured against `main`: `SkillCatalogEntry` at the sentinel hashes to `53a94c2c…` on both trees, so every grant in force stays in force

## ccf.skills.SkillCatalogEntry

- Surface: ccf.skills.SkillCatalogEntry
- Public surface: true
- Change type: reshaped
- Before: the package-level re-export of the same class
- After: carries the same new `produces` field
- Why: one class, two import paths; the manifest tracks both
- Migration: none required — see `ccf.skills.catalog.SkillCatalogEntry`

