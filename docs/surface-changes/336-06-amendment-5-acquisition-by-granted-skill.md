# 336-06 — Amendment 5: acquisition by granted skill

Recorded at the `f0656746` qualification (2026-09-19) from the introducing commit `87daab4f`
(*refactor(D-IMPL-336): Amendment 5 parts 1-3 — acquisition by granted skill*, 2026-09-13
19:32), which landed between `336-03` and `336-04` without a fragment of its own; `336-04` and
`336-05` mention Amendment 5 in prose only. The commit's own statement: the composite is a
consumer of Context Products; the parallel authorization layer is gone, and verification sits at
the boundary that owns it. What shipped in its place — `GrantBoundChildResolver` and its
companions in `ccf.products.child_resolver` — is claimed by `336-05`.

This fragment claims the two public names `87daab4f` added to `ccf.products.composite` and the
seven it deleted. **The seven deletions are short-lived pairs, stated explicitly**: each was
claimed `added` by `336-02` and is claimed `removed` here, and each is in neither the frozen
baseline (`docs/surface/v0.2-surface-baseline.json`) nor the live surface — which is exactly
the pair of claims the phase-close cross-check derives a short-lived name from.

## ccf.products.composite.ChildAcquisition

- Surface: ccf.products.composite.ChildAcquisition
- Public surface: true
- Change type: added
- Before: absent — how a child had been acquired was inferred from which provenance record was attached to it
- After: a `Literal` alias — at `87daab4f` `"local-dispatch"`, `"mcp"`, `"peered"` — naming how a child was acquired, keyed on the dispatch result's type and cross-checked against the entry's declared `skill_type`. `D-IMPL-340` (`340-01`) later widened it with `"mcp-product"`, which is the member the live surface shows in addition
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — MCP is not automatically peering (`D-IMPL-59`): the existing controls for the actual provider relationship apply, and the acquisition kind is what selects them
- Migration: none

## ccf.products.composite.ELIGIBILITY_PROVIDER_CONTROLS

- Surface: ccf.products.composite.ELIGIBILITY_PROVIDER_CONTROLS
- Public surface: true
- Change type: added
- Before: absent
- After: `Final = "provider-controls"` — the `eligibility_basis` value when the provider's own access controls governed the read and this fabric holds no execution record for the child (the MCP case); a positive statement about which authority applied, never an absence — the local register was not consulted, and the row says so
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`)
- Migration: none

## ccf.products.composite.EligibilityEvidencePolicy

- Surface: ccf.products.composite.EligibilityEvidencePolicy
- Public surface: true
- Change type: removed
- Before: a `CCFContract` declaring how old a producer's eligibility check may be (`D-IMPL-336` Amendment 3, F7), claimed `added` by `336-02`
- After: absent — deleted from `ccf.products.composite` by `87daab4f`; eligibility is stated on the child row by `eligibility_basis`, and acquisition runs through the effective grant and actual skill dispatch
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — the parallel authorization layer is gone. Claimed `added` by `336-02` and `removed` here, this name is a short-lived pair: it is in neither the frozen baseline nor the live surface
- Migration: none on the shipped paths; a deployment that registered this policy directly removes the registration — nothing reads it

## ccf.products.composite.ELIGIBILITY_EVIDENCE_POLICY

- Surface: ccf.products.composite.ELIGIBILITY_EVIDENCE_POLICY
- Public surface: true
- Change type: removed
- Before: the `ArtifactClass` (`ccf.eligibility-evidence-policy`) the policy above registered under, claimed `added` by `336-02`
- After: absent — deleted from `ccf.products.composite` by `87daab4f`
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — the contract it named is gone. Claimed `added` by `336-02` and `removed` here, this name is a short-lived pair: it is in neither the frozen baseline nor the live surface
- Migration: none on the shipped paths; a manifest naming the class id is refused as an unknown `ccf.` class (`D-IMPL-84`) and drops the entry

## ccf.products.composite.eligibility_evidence_policy_key

- Surface: ccf.products.composite.eligibility_evidence_policy_key
- Public surface: true
- Change type: removed
- Before: `eligibility_evidence_policy_key(*, tenant_id: str) -> str` — the per-tenant Control Plane key the bound policy registered under, claimed `added` by `336-02`
- After: absent — deleted from `ccf.products.composite` by `87daab4f`
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — nothing registers the policy, so nothing needs its key. Claimed `added` by `336-02` and `removed` here, this name is a short-lived pair: it is in neither the frozen baseline nor the live surface
- Migration: none

## ccf.products.composite.LocalProvenance

- Surface: ccf.products.composite.LocalProvenance
- Public surface: true
- Change type: removed
- Before: a `ChildProvenance` record for a child this fabric produced, whose own register was authoritative; claimed `added` by `336-02`
- After: absent — deleted from `ccf.products.composite` by `87daab4f`; a locally produced child is acquired through its granted skill like any other and carries its acquisition kind on the row
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — the composite is a consumer of Context Products and does not vouch for a child's origin itself. Claimed `added` by `336-02` and `removed` here, this name is a short-lived pair: it is in neither the frozen baseline nor the live surface
- Migration: none on the shipped paths; a deployment that built provenance records by hand moves to a `CompositeChildResolverProtocol` implementation such as `GrantBoundChildResolver`

## ccf.products.composite.VerifiedPeerProvenance

- Surface: ccf.products.composite.VerifiedPeerProvenance
- Public surface: true
- Change type: removed
- Before: a `ChildProvenance` record for a child another fabric produced, whose envelope had been verified; claimed `added` by `336-02`
- After: absent — deleted from `ccf.products.composite` by `87daab4f`; a genuinely peered child still passes peering verification at the peering boundary that owns it, regardless of how the skill retrieves it
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — verification sits at the boundary that owns it, not in a parallel record. Claimed `added` by `336-02` and `removed` here, this name is a short-lived pair: it is in neither the frozen baseline nor the live surface
- Migration: as for `LocalProvenance`

## ccf.products.composite.LocalFabricAttestor

- Surface: ccf.products.composite.LocalFabricAttestor
- Public surface: true
- Change type: removed
- Before: the boot-bound authority for *this fabric produced it* — `attest(*, product, replay_ref, store)` resolved the decision record and read the touched entities out of replay dimension 1 (`336-03`); claimed `added` by `336-02`
- After: absent — deleted from `ccf.products.composite` by `87daab4f`
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — with the provenance layer gone there is nothing to attest. Claimed `added` by `336-02` and `removed` here, this name is a short-lived pair: it is in neither the frozen baseline nor the live surface
- Migration: none on the shipped paths; `FabricHandle.local_attestor` (`336-03`) no longer carries one

## ccf.products.composite.peer_provenance_from_admitted

- Surface: ccf.products.composite.peer_provenance_from_admitted
- Public surface: true
- Change type: removed
- Before: `peer_provenance_from_admitted(admitted: AdmittedProduct, *, touched_entities: tuple[str, ...]) -> VerifiedPeerProvenance` — built the peer provenance record from an admitted product; claimed `added` by `336-02`
- After: absent — deleted from `ccf.products.composite` by `87daab4f`
- Why: `D-IMPL-336` Amendment 5 (`87daab4f`) — the record it built is gone. Claimed `added` by `336-02` and `removed` here, this name is a short-lived pair: it is in neither the frozen baseline nor the live surface
- Migration: none
