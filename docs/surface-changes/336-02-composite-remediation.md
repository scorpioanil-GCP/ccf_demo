# D-IMPL-336 Amendment 3 — the composite surface, repaired and WIRED

Applied 2026-09-13 under `D-IMPL-336` Amendment 3, after the cross-AI panel
(`docs/D-IMPL-336-PANEL-REVIEW.md`). Supersedes nothing in
`336-01-composite-context-products.md`; that fragment described the surface as
first written, and the panel found it had **no callers**. This one describes
the surface as it now stands on the governed path.

## What changed, in one line each

- **The composite surface is CALLED.** `GovernedResolver.__call__` reads
  `requires` from the registered class and composes; `child_resolutions` is
  written from execution. Both read `NONE` before this.
- **`requires` is AUTHORABLE.** `ProductClassDeclaration` accepts it,
  `register_product_class` forwards it, `_register` passes it.
- **The gate's INPUTS are evidence.** Caller-labelled provenance is replaced by
  `ChildProvenance` (minted by a boot attestor or by a verified peering
  admission) and `ChildInvocation` (minted from the resolved catalog entry).
- **`AdmittedProduct` carries its verified header and content address out**, so
  a consumer can hold evidence the peering gate produced rather than re-read an
  envelope itself.
- **All four ruled composition laws run**, not one.
- **Refusal reasons are a closed `Literal`** and the status map is exhaustive.

## Migration

None required for any non-composite deployment — every branch is inert when a
class declares no `requires`, and every legacy artifact keeps its content
address (measured: `requires` and `child_resolutions` are absent from the
canonical bytes at their sentinels).

**One break, and it is deliberate:** `GovernedResolver` now requires
`composite_children`. The dataclass forbids defaults so a deployment states its
posture; `build_governed_resolver` keeps the non-composite default, so callers
of the helper are unaffected.

## Surface entries

## ccf.halflife.debt.EmptyFactorCompositionError

- Surface: ccf.halflife.debt.EmptyFactorCompositionError
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.halflife.debt.compose_debt_factors

- Surface: ccf.halflife.debt.compose_debt_factors
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.peering.eligibility.ELIGIBILITY_ASSERTION_HEADER

- Surface: ccf.peering.eligibility.ELIGIBILITY_ASSERTION_HEADER
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.peering.eligibility.ELIGIBILITY_ASSERTION_SCHEMA_VERSION

- Surface: ccf.peering.eligibility.ELIGIBILITY_ASSERTION_SCHEMA_VERSION
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.peering.eligibility.EligibilityAssertion

- Surface: ccf.peering.eligibility.EligibilityAssertion
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.peering.eligibility.EligibilityAssertionMalformed

- Surface: ccf.peering.eligibility.EligibilityAssertionMalformed
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.peering.eligibility.decode_eligibility_assertion

- Surface: ccf.peering.eligibility.decode_eligibility_assertion
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.peering.eligibility.encode_eligibility_assertion

- Surface: ccf.peering.eligibility.encode_eligibility_assertion
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.peering.eligibility.mint_eligibility_assertion

- Surface: ccf.peering.eligibility.mint_eligibility_assertion
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.AdmittedChild

- Surface: ccf.products.composite.AdmittedChild
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.AmbiguousProducerError

- Surface: ccf.products.composite.AmbiguousProducerError
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.CHILD_REFUSAL_REASONS

- Surface: ccf.products.composite.CHILD_REFUSAL_REASONS
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ChildAdmissionBypassError

- Surface: ccf.products.composite.ChildAdmissionBypassError
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ChildAdmissionRefusal

- Surface: ccf.products.composite.ChildAdmissionRefusal
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ChildCandidate

- Surface: ccf.products.composite.ChildCandidate
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ChildInvocation

- Surface: ccf.products.composite.ChildInvocation
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ChildRefusalReason

- Surface: ccf.products.composite.ChildRefusalReason
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.CompositeAdmissionGate

- Surface: ccf.products.composite.CompositeAdmissionGate
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.CompositeChildResolverProtocol

- Surface: ccf.products.composite.CompositeChildResolverProtocol
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.CompositionOutcome

- Surface: ccf.products.composite.CompositionOutcome
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ELIGIBILITY_EVIDENCE_POLICY

- Surface: ccf.products.composite.ELIGIBILITY_EVIDENCE_POLICY
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ELIGIBILITY_LOCAL_REGISTER

- Surface: ccf.products.composite.ELIGIBILITY_LOCAL_REGISTER
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ELIGIBILITY_PRODUCER_ATTESTED

- Surface: ccf.products.composite.ELIGIBILITY_PRODUCER_ATTESTED
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.EligibilityEvidence

- Surface: ccf.products.composite.EligibilityEvidence
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.EligibilityEvidencePolicy

- Surface: ccf.products.composite.EligibilityEvidencePolicy
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.GATE_CHILD_ADMISSION

- Surface: ccf.products.composite.GATE_CHILD_ADMISSION
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.LocalFabricAttestor

- Surface: ccf.products.composite.LocalFabricAttestor
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.LocalProvenance

- Surface: ccf.products.composite.LocalProvenance
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ProvenanceForgeryError

- Surface: ccf.products.composite.ProvenanceForgeryError
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.VerifiedPeerProvenance

- Surface: ccf.products.composite.VerifiedPeerProvenance
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.compose_children

- Surface: ccf.products.composite.compose_children
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.eligibility_evidence_policy_key

- Surface: ccf.products.composite.eligibility_evidence_policy_key
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.invocation_from_dispatch

- Surface: ccf.products.composite.invocation_from_dispatch
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.peer_provenance_from_admitted

- Surface: ccf.products.composite.peer_provenance_from_admitted
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.resolve_producing_grant

- Surface: ccf.products.composite.resolve_producing_grant
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.contract.ChildRequirement

- Surface: ccf.products.contract.ChildRequirement
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.contract.OptionalAbsenceTreatment

- Surface: ccf.products.contract.OptionalAbsenceTreatment
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.contract.requirements_declaration_is_coherent

- Surface: ccf.products.contract.requirements_declaration_is_coherent
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.gates.refuse_dependency_invalidation

- Surface: ccf.products.gates.refuse_dependency_invalidation
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.replay.record.CHILD_ADMITTED

- Surface: ccf.replay.record.CHILD_ADMITTED
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.replay.record.CHILD_OUTCOME_STATUSES

- Surface: ccf.replay.record.CHILD_OUTCOME_STATUSES
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.replay.record.ChildResolution

- Surface: ccf.replay.record.ChildResolution
- Public surface: true
- Change type: added
- Before: absent — the composite surface as first written, before the panel found it had no callers
- After: part of the wired composite path (D-IMPL-336 Amendment 3)
- Why: the declaration, admission and composition halves of a governed composite product, now reachable from GovernedResolver rather than from tests alone
- Migration: none required — inert for any class declaring no `requires`; see the one deliberate break above

## ccf.products.composite.ProducedHere

- Surface: ccf.products.composite.ProducedHere
- Public surface: true
- Change type: removed
- Before: a caller-chosen label that ESTABLISHED local authority by being written. Replaced by `LocalProvenance`, which only a boot-bound attestor can mint (F6)
- After: absent — replaced by the evidence type named above
- Why: the panel's root cause (a) — the gate verified the child and trusted the context. A label a caller writes cannot establish the thing it claims
- Migration: construct provenance through `LocalFabricAttestor.attest(...)` or `peer_provenance_from_admitted(...)`. There is deliberately no way to write the claim directly

## ccf.products.composite.ProducedElsewhere

- Surface: ccf.products.composite.ProducedElsewhere
- Public surface: true
- Change type: removed
- Before: a caller-supplied `protected_header` dict the gate read a 'signed' assertion out of, with nothing having verified it. Replaced by `VerifiedPeerProvenance`, mintable only from an `AdmittedProduct` (F16)
- After: absent — replaced by the evidence type named above
- Why: the panel's root cause (a) — the gate verified the child and trusted the context. A label a caller writes cannot establish the thing it claims
- Migration: construct provenance through `LocalFabricAttestor.attest(...)` or `peer_provenance_from_admitted(...)`. There is deliberately no way to write the claim directly

## ccf.products.composite.ProducingFabric

- Surface: ccf.products.composite.ProducingFabric
- Public surface: true
- Change type: removed
- Before: the base of the two labels above; replaced by `ChildProvenance`, which additionally carries `touched_entities` as execution evidence rather than as an optional keyword (F3)
- After: absent — replaced by the evidence type named above
- Why: the panel's root cause (a) — the gate verified the child and trusted the context. A label a caller writes cannot establish the thing it claims
- Migration: construct provenance through `LocalFabricAttestor.attest(...)` or `peer_provenance_from_admitted(...)`. There is deliberately no way to write the claim directly

## ccf.peering.admission.AdmittedProduct

- Surface: ccf.peering.admission.AdmittedProduct
- Public surface: true
- Change type: reshaped
- Before: carried the validated contract, the merged lineage and the peer
- After: additionally carries the AUTHENTICATED protected header and the content address computed over the verified bytes, as two new optional properties
- Why: a consumer needing a claim from the header must be able to reach one this gate verified. Both are PASSED from the locals `admit` ran its policy checks against, never re-derived by a second `declared_header()` call — carrying, not recomputing, is what makes the value provably the checked one (F16)
- Migration: none — both members default to `None` and every existing construction site is unchanged; the shipped gate fills them

