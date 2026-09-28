# 358-03 — `TemporalBoundaryPolicy`: declared, versioned, tenant-resolved and PINNED

`D-IMPL-358` Wave 2 step 3. A new Control Plane artifact — how far into the past a
governed request may reach — together with its tenant-scoped key derivation and a
resolution that keeps the version identity the Control Plane returned.

**The truthful claim at this step, stated exactly.** The temporal boundary policy
can be **declared, versioned, resolved by tenant and pinned exactly**. It is
**not** true that requests are now temporally bounded. Nothing here reads a clock,
nothing bounds a request, and no served or refusal record is touched: threading
`PolicyBinding` into live records belongs with the resolver work after `served_at`
exists. The module declares `__ccf_mode__ = "algorithmic"`, so CINV-03 now
enforces structurally that it calls no model — and `D-IMPL-159`'s stated blocker
for an algorithmic module, that it *"may not read a clock at all"*, is exactly this
step's boundary.

**Why a new class rather than a reuse of the sibling.** `EligibilityEvidencePolicy`
answers a different question (how old a *producer's eligibility check* may be) and
is consumed on one boundary. This one is consumed on three — the governed
resolver, the ingress write guard and peering admission — which is also why it
lives in `ccf.controlplane` rather than beside any one of them.

**The defect this entry exists not to repeat, named.**
`ccf/peering/eligibility.py::_evidence_too_old` resolves its policy as
``_version, policy = registry.resolve_latest(key)`` and **discards the version**,
so no replay can name which version of the bound authorized an admission. The
value was in hand and thrown away one line later. Resolution here returns
`PinnedTemporalBoundary`, which holds key, version and policy in one frozen value,
and there is no way to construct one that lost the version. Severing T1 falsifies
it. That sibling carries a **second** conflation this entry also declines to
repeat: its `isinstance` branch reports *both* an absent artifact and a wrong
object at the key as `eligibility-bound-undeclared`, which are different facts
with different remedies.

**A measurement that shapes the pin control, recorded because it would otherwise
be re-derived the easy way.** `ControlPlaneRegistry` derives a version as
`content_hash(artifact)`, so an implementation that discarded the registry's
version and recomputed it from the policy would produce a byte-identical string. A
pin control run against the real registry therefore **cannot** falsify the defect
it exists to catch. `tests/controlplane/test_temporal_boundary.py::test_a_pin_control_on_the_real_registry_is_blind_to_a_recomputed_version`
asserts that blindness directly, and the pin control itself uses a stand-in plane
whose version follows from nothing about the policy. Every other test in the suite
uses the real registry.

## ccf.controlplane.temporal_boundary.TemporalBoundaryPolicy

- Surface: ccf.controlplane.temporal_boundary.TemporalBoundaryPolicy
- Public surface: true
- Change type: added
- Before: absent — no artifact declared how far into the past a request may reach, and no SDK surface existed to hold such a declaration
- After: a `CCFContract` with two required integer members, `max_past_seconds` and `permitted_clock_skew_seconds`, each validated non-negative by one `field_validator` on the `EligibilityEvidencePolicy` precedent. **Neither field has a default**, so a deployment that forgot to declare one cannot silently inherit the SDK's opinion about how much history it answers for. Zero is a legal value and is the STRICTEST bound rather than "unbounded" — read off the accepted semantics the sibling already implements, whose comparison is `age > max_evidence_age_seconds`; the comparison itself is not implemented at this step
- Why: `D-IMPL-358`, and `D-IMPL-38`'s no-silent-default rule — both members are deployment values and the SDK holds neither. A window is a policy decision about how much history a tenant will answer for, so the SDK supplies the shape, the validation, the key and the pinning, and no number
- Migration: none. A new artifact class nothing yet consumes; no existing declaration, content address or behavior changes

## ccf.controlplane.temporal_boundary.TEMPORAL_BOUNDARY_POLICY

- Surface: ccf.controlplane.temporal_boundary.TEMPORAL_BOUNDARY_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: the `ArtifactClass` a deployment registers its boundary under, `class_id="ccf.temporal-boundary-policy"` — `ccf.<kebab-case>` per the convention all 33 existing class ids follow, and the direct sibling of `ccf.eligibility-evidence-policy`
- Why: an artifact class is the identity the audit plane records, so a deployment's registration can be named without re-reading the artifact
- Migration: none. Deliberately NOT added to `SDK_ARTIFACT_CLASSES`, matching all three sibling per-tenant policies, so it is not manifest-addressable; its committed schema arrives through `dump_schemas.py`'s discovered bucket instead

## ccf.controlplane.temporal_boundary.temporal_boundary_policy_key

- Surface: ccf.controlplane.temporal_boundary.temporal_boundary_policy_key
- Public surface: true
- Change type: added
- Before: absent
- After: `temporal_boundary_policy_key(*, tenant_id) -> str`, returning `{tenant_id}/ccf.temporal-boundary-policy`. Tenant-FIRST, on the unanimous precedent of the four existing key helpers and for the reason each of them states: the registry's one tenant comparison reads the segment before the first `/` (`D-IMPL-353` §1.3), so a class-first key could be registered only by a capability whose tenant was the class name
- Why: a derivation rather than a table, so two components cannot disagree about where a tenant's policy lives, and the SDK supplies no tenant and therefore holds no deployment's vocabulary (CINV-01)
- Migration: none. A new key shape under which nothing is yet registered

## ccf.controlplane.temporal_boundary.PinnedTemporalBoundary

- Surface: ccf.controlplane.temporal_boundary.PinnedTemporalBoundary
- Public surface: true
- Change type: added
- Before: absent — the sibling's resolution returned only the policy, discarding the version
- After: a frozen dataclass holding `key`, `version` and `policy` together, plus a `binding` property returning the `PolicyBinding(key, version)` a later step will append to served and refusal records. **One authority for the pin**, because three prospective call sites each building their own `PolicyBinding` would be three chances for one of them to reconstruct a version instead of carrying the resolved one. The `PolicyBinding` import is deferred rather than module-level: `ccf.replay.record` reaches `ccf.products.contract`, which imports `ccf.controlplane.registry`, so a module-level import would close a package-level cycle and pull 56 modules into `ccf.controlplane` for a two-field value
- Why: `D-IMPL-358` step 3 — the exact resolved version is what a replay must pin, and holding it in the same value as the policy makes discarding it impossible to do by accident. There is no constructor that omits it
- Migration: none, and nothing appends this binding yet. The value exists so the step that does has one place to get it from

## ccf.controlplane.temporal_boundary.TemporalBoundaryUndeclared

- Surface: ccf.controlplane.temporal_boundary.TemporalBoundaryUndeclared
- Public surface: true
- Change type: added
- Before: absent
- After: a frozen dataclass carrying `key`, `required_class_id`, `reason` and `detail`, RETURNED rather than raised — absence is a governance outcome a deployment can legitimately be in, and a later governed refusal consumes this condition. It carries no `version` and no `policy` field, so there is nothing to fabricate
- Why: `D-IMPL-358` ruling 11 — on absence the fabric records the policy key or class that was required and the absence reason, and never mints a fake binding or fabricates a version for a policy that does not exist
- Migration: none. The refusal that consumes this is a later step; nothing raises or returns it on a live path yet

## ccf.controlplane.temporal_boundary.TemporalBoundaryMisdeclared

- Surface: ccf.controlplane.temporal_boundary.TemporalBoundaryMisdeclared
- Public surface: true
- Change type: added
- Before: absent — the sibling reports a wrong artifact at its key as `eligibility-bound-undeclared`, the same token it reports absence with
- After: a `TypeError` subclass RAISED when something is registered at the key and is not a `TemporalBoundaryPolicy`. A configuration error, deliberately not folded into the undeclared condition: a deployment that declared the wrong artifact and one that declared none need different things done about them, and reporting the first as the second sends an operator to add what is already present. A `TypeError` subclass so a caller already handling what `ArtifactClass.validate` raises for the same mistake keeps working. Its message names the fully qualified type found and expected, because the bare class name produces the useless "is a TemporalBoundaryPolicy, not a TemporalBoundaryPolicy" whenever two copies of the contract class are live at once — measured during this step's severing campaign
- Why: `D-IMPL-358` — missing, wrong, and unavailable are three different facts, and only one of them is an absence
- Migration: none. A new exception on a path nothing yet calls

## ccf.controlplane.temporal_boundary.resolve_temporal_boundary

- Surface: ccf.controlplane.temporal_boundary.resolve_temporal_boundary
- Public surface: true
- Change type: added
- Before: absent
- After: `resolve_temporal_boundary(*, registry, tenant_id) -> PinnedTemporalBoundary | TemporalBoundaryUndeclared`. Three outcomes for three different facts: a declared policy returns the pin with the exact version the registry returned; an absent one returns `TemporalBoundaryUndeclared`; a wrong artifact raises `TemporalBoundaryMisdeclared`. **Only `ControlPlaneMissing` is caught**, and narrowly — every other registry failure propagates untouched, because a broad `except` would report a control-plane outage as an undeclared bound and silently disable the boundary on exactly the day the control plane was unwell. The tenant arrives as an argument because this is the mechanism; it is supplied by governed composition or runtime context at the call site, never read off a request payload and never declared by an envelope (`D-IMPL-358` ruling 3)
- Why: `D-IMPL-358` step 3 — one resolution surface that cannot lose version identity, and that distinguishes the three facts a later refusal has to report differently
- Migration: none. No caller exists yet; the resolver, ingress write guard and peering admission adopt it in later steps

## docs/schemas/ccf.temporal-boundary-policy.json

- Surface: docs/schemas/ccf.temporal-boundary-policy.json
- Public surface: false
- Change type: added
- Before: absent
- After: the committed JSON Schema for the new artifact class, two required integers with `additionalProperties: false` and `x-ccf-class-id: ccf.temporal-boundary-policy`, emitted by `tools/dump_schemas.py`'s discovered bucket — which walks the tree for `ArtifactClass` instances rather than reading `SDK_ARTIFACT_CLASSES`, and is why all three sibling per-tenant policies have committed schemas while being absent from that mapping
- Why: the committed schema tree is the authoring baseline an adopter reads in their editor (ERGO-12); an artifact class with no schema is a declaration nobody can discover. The freshness check fails without it
- Migration: none — a new file describing a new class
