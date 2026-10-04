# 005 — the signed claim set and the time window

`SEC-005`, the remaining leg, as `D-IMPL-363` ruled it on the brief at
`docs/SEC-005-DESIGN-BRIEF.md` (E1–E8 locked at `D-IMPL-356`; thirteen choices
C1–C13 decided). The verdict leg shut under
`docs/surface-changes/005-verdict-joins-the-signed-claim-set.md` is not
reopened.

**The defect, measured before the change** (`main` @ `6f1cb17b`, read-only).
The signed-binding leg verified the client's signature against the binding the
DOOR mints — `action_time` included — so a production signer had to sign the
server's clock reading in advance. Exact under an injected clock, impossible
under a wall clock; recorded as "THE LIMIT, STATED" in
`docs/surface-changes/353-06-the-approval-record-is-server-attested.md`. A
signature over a moved `action_time` was refused at both doors, and door
replay was bounded only by that clock equality.

**What changed.** The human no longer signs the server's statement. The human
signs its own — `HitlActionClaims{tenant, event_key, action,
product_content_hash, subject_id, issued_at, nonce}`, carried as
`SignedHitlAction` in the `attestation` field of the request and the
submission, at both doors in one shape (C12(a)). The binding stays
door-minted and unsigned. One shared verifier,
`ccf.hitl.transport.enforce_attestation`, compares each signed claim with the
capability, the request and the minted binding, and windows the signer's
`issued_at` against the RECORDED `action_time` — directionally
(`issued_at <= action_time + permitted_clock_skew_seconds`,
`action_time − issued_at <= signature_max_age_seconds`) and **without reading
a clock of its own**, so the transport site, a primitive site and a replay
re-verify identically. The window and the per-subject trusted keys are
statements of the pinned `ccf.hitl-policy` artifact — ONE trust source
(C6(a)); the deployment-wide `trusted_keys` constructor arguments are gone, no
fallback. The reference transport refuses a reused `(tenant, event_key,
nonce)` atomically under its lock, after verification and before recording
(E4 / C11(a)). Two codes join the two that existed: `signed-binding-mismatch`
(a verified signature whose claims disagree with the capability, the request,
the minted binding or the key map — including a swapped verdict, migrating
from `signed-binding-invalid` under C4(a)) and `signed-binding-stale`
(outside the window, or a reused nonce). The submission records
`hitl_policy_ref` (`key@version`, where `version` is the Control Plane's
version identifier for the pinned artifact — in the reference registry its
content address, not its semver lane), so dimension 2 carries which policy
admitted the action.

**The CLI door is unsigned-only (E8).** `runtime/ccf_runtime/cli/commands/hitl.py`
posts the action document verbatim and has no signing of its own; a document
that carries no `attestation` is refused under `signed_binding_required: true`.
Attestation arguments are a `D-IMPL-22` item.

**History is not rewritten (the fixture rule).** Existing records and fixtures
stay unchanged. The HITL block is stored on the record as canonical bytes and
nothing on the replay path re-parses a stored signed binding, so every record
written before this change rehydrates to the address it was written at.
`tests/replay/fixtures/golden_13bd250` carries no signed binding and is left
untouched; new-generation fixtures are added beside the historical ones, never
produced by re-pinning an old one.

The replaced names are **removed, not deprecated** (`D-IMPL-356` §0 ruling 4:
nothing has shipped). Each change is recorded at every name the manifest tracks
it under — the defining module and the `ccf.hitl` package re-export. The prefix
`005` is the finding number, not a phase or decision id; the assembler uses it
only as a sort key.

## ccf.hitl.identity_binding.HitlActionClaims

- Surface: ccf.hitl.identity_binding.HitlActionClaims
- Public surface: true
- Change type: added
- Before: absent — the signed payload was the door-minted `HumanPrincipalBinding` itself, `action_time` included
- After: a `CCFContract` (`extra=forbid`) of seven members the signer can know from the served queue view plus its own decision, identity, instant and nonce: `tenant`, `event_key`, `action` (the `HITL_ACTIONS` vocabulary), `product_content_hash` (a content hash), `subject_id`, `issued_at` (timezone-aware; naive is refused) and `nonce` (non-empty, opaque). `action_time` is deliberately absent
- Why: `D-IMPL-363` E1 — a signer must be able to produce the statement without predicting the server's clock, and the statement must still bind the decision (C1(a): `action` is signed and must equal both the presented action and the minted binding's `verdict`)
- Migration: a signer constructs `HitlActionClaims` from the queue view (`PendingHitlEvent.event_key`, `.tenant`, `.product_content_hash`) and its own `action`, `subject_id`, `issued_at` and `nonce`. Uniqueness of the nonce per `(tenant, event_key)` is the signer's obligation (C11(a)); the SDK ships no generator

## ccf.hitl.HitlActionClaims

- Surface: ccf.hitl.HitlActionClaims
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.HitlActionClaims`
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.SignedHitlAction

- Surface: ccf.hitl.identity_binding.SignedHitlAction
- Public surface: true
- Change type: added
- Before: absent — `SignedPrincipalBinding{binding, signature, key_id}` carried a signed copy of the door-minted binding
- After: `SignedHitlAction{claims: HitlActionClaims, signature: str, key_id: str}` — the claims in the clear, the detached compact JWS (`protected..signature`) over `canonical_bytes(claims)`, and the key identifier the verifier holds against the protected header's `kid` and the pinned policy's per-subject key map. This is the `attestation` both doors carry
- Why: `D-IMPL-363` E1 / C12(a) — one object in one shape at both doors; a verifier recomputes the payload from `claims`, so a signed copy and a delivered copy cannot silently differ
- Migration: send `attestation` (this object) in the HTTP body and as the MCP tool's `attestation` argument; the former `signed_binding` field and the former MCP scalars `signed_binding_signature` / `signed_binding_key_id` no longer exist

## ccf.hitl.SignedHitlAction

- Surface: ccf.hitl.SignedHitlAction
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.SignedHitlAction`
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.sign_hitl_action

- Surface: ccf.hitl.identity_binding.sign_hitl_action
- Public surface: true
- Change type: added
- Before: absent — `sign_principal_binding(binding, *, provider, key_id) -> SignedPrincipalBinding` signed the door-minted binding
- After: `sign_hitl_action(claims: HitlActionClaims, *, provider: IdentityProvider, key_id: str) -> SignedHitlAction` — the provider's own detached JWS over the claims' canonical bytes; no key machinery, no JOSE registry and no algorithm choice of its own (CINV-01)
- Why: `D-IMPL-363` E1 — what is signed moved; the signing machinery did not (D-IMPL-15 reuse, D-IMPL-66(a))
- Migration: replace `sign_principal_binding(binding, ...)` with `sign_hitl_action(claims, ...)`; the provider and `key_id` arguments are unchanged

## ccf.hitl.sign_hitl_action

- Surface: ccf.hitl.sign_hitl_action
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.sign_hitl_action`
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.verify_hitl_action

- Surface: ccf.hitl.identity_binding.verify_hitl_action
- Public surface: true
- Change type: added
- Before: absent — `verify_principal_binding(signed, *, provider, public_keys) -> HumanPrincipalBinding`
- After: `verify_hitl_action(signed: SignedHitlAction, *, provider: IdentityProvider, public_keys: Mapping[str, JsonWebKey]) -> HitlActionClaims` — recomputes the payload from `signed.claims`, requires the protected header's `kid` to equal `signed.key_id`, verifies under exactly the keys the caller offers, and raises `AttestationInvalid` otherwise. Trust stays outside the seam: the caller supplies the candidate keys
- Why: `D-IMPL-363` E1 / E5 — the shared verifier offers it only the keys the pinned policy declares for `claims.subject_id`, so a key trusted for another approver signs for no one
- Migration: callers that verified a signed binding directly call `verify_hitl_action` and receive the claims, not a binding; the binding is read from the submission

## ccf.hitl.verify_hitl_action

- Surface: ccf.hitl.verify_hitl_action
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.verify_hitl_action`
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.AttestationInvalid

- Surface: ccf.hitl.identity_binding.AttestationInvalid
- Public surface: true
- Change type: added
- Before: absent — `PrincipalBindingInvalid(IdentityError)` named a signed binding that did not verify
- After: `AttestationInvalid(IdentityError)`, raised by `verify_hitl_action` when the envelope is malformed, the `kid` disagrees with `key_id`, or the signature does not verify under the offered keys; the shared verifier converts it to `SignedBindingInvalidRefused`
- Why: the thing that fails verification is now the attestation, and the name says so
- Migration: catch `AttestationInvalid` (or its base `IdentityError`) where `PrincipalBindingInvalid` was caught

## ccf.hitl.AttestationInvalid

- Surface: ccf.hitl.AttestationInvalid
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.AttestationInvalid`
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.SignedPrincipalBinding

- Surface: ccf.hitl.identity_binding.SignedPrincipalBinding
- Public surface: true
- Change type: removed
- Before: `SignedPrincipalBinding{binding: HumanPrincipalBinding, signature, key_id}` — a signed copy of the door-minted binding, `action_time` included
- After: absent; `SignedHitlAction` carries the signer's own claims instead
- Why: `D-IMPL-363` E1 — signing the server's statement is the 353-06 limit; removed rather than deprecated because nothing has shipped (`D-IMPL-356` §0 ruling 4). Nothing on the replay path re-parsed a stored one, so historical records are unaffected
- Migration: replace with `SignedHitlAction`; see that entry

## ccf.hitl.SignedPrincipalBinding

- Surface: ccf.hitl.SignedPrincipalBinding
- Public surface: true
- Change type: removed
- Before: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.SignedPrincipalBinding`
- After: absent
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.sign_principal_binding

- Surface: ccf.hitl.identity_binding.sign_principal_binding
- Public surface: true
- Change type: removed
- Before: `sign_principal_binding(binding, *, provider, key_id) -> SignedPrincipalBinding`
- After: absent; `sign_hitl_action(claims, *, provider, key_id) -> SignedHitlAction`
- Why: `D-IMPL-363` E1; see `SignedPrincipalBinding`
- Migration: replace with `sign_hitl_action`; the provider and `key_id` arguments are unchanged

## ccf.hitl.sign_principal_binding

- Surface: ccf.hitl.sign_principal_binding
- Public surface: true
- Change type: removed
- Before: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.sign_principal_binding`
- After: absent
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.verify_principal_binding

- Surface: ccf.hitl.identity_binding.verify_principal_binding
- Public surface: true
- Change type: removed
- Before: `verify_principal_binding(signed, *, provider, public_keys) -> HumanPrincipalBinding`
- After: absent; `verify_hitl_action(signed, *, provider, public_keys) -> HitlActionClaims`
- Why: `D-IMPL-363` E1; see `SignedPrincipalBinding`
- Migration: replace with `verify_hitl_action`; the result is the claims, not a binding

## ccf.hitl.verify_principal_binding

- Surface: ccf.hitl.verify_principal_binding
- Public surface: true
- Change type: removed
- Before: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.verify_principal_binding`
- After: absent
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.identity_binding.PrincipalBindingInvalid

- Surface: ccf.hitl.identity_binding.PrincipalBindingInvalid
- Public surface: true
- Change type: removed
- Before: `PrincipalBindingInvalid(IdentityError)`
- After: absent; `AttestationInvalid(IdentityError)`
- Why: `D-IMPL-363` E1; the failing object is now the attestation
- Migration: catch `AttestationInvalid` (or `IdentityError`)

## ccf.hitl.PrincipalBindingInvalid

- Surface: ccf.hitl.PrincipalBindingInvalid
- Public surface: true
- Change type: removed
- Before: the `ccf.hitl` package re-export of `ccf.hitl.identity_binding.PrincipalBindingInvalid`
- After: absent
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.transport.enforce_attestation

- Surface: ccf.hitl.transport.enforce_attestation
- Public surface: true
- Change type: added
- Before: absent — `enforce_signed_binding(authorized, submission, *, identity_provider, trusted_keys, required)` verified the signed copy of the minted binding against a deployment-wide key map and compared the verified binding with the minted one
- After: `enforce_attestation(authorized: Authorized[HitlSubmit], submission: HitlActionSubmission, *, identity_provider: IdentityProvider | None, policy: HitlPolicy) -> HitlActionClaims`. In order: absent attestation → `SignedBindingRequiredRefused`; no provider or no window → `RuntimeError` (broken wiring); `key_id` not declared for `claims.subject_id` in `policy.trusted_keys` → `SignedBindingMismatchRefused`; signature under exactly those keys → `SignedBindingInvalidRefused`; `tenant` ≠ capability tenant, `event_key` ≠ capability resource, `subject_id` ≠ capability principal or ≠ minted approver, `action` ≠ presented action or ≠ minted `verdict`, `product_content_hash` ≠ minted → `SignedBindingMismatchRefused` naming the fields; `issued_at` more than `permitted_clock_skew_seconds` after, or more than `signature_max_age_seconds` before, the RECORDED `submission.principal.action_time` → `SignedBindingStaleRefused`. **It reads no clock.** The nonce is not consumed here
- Why: `D-IMPL-363` E2/E3/E5 and C13(a) (the verifier is renamed; `signed_binding_required` keeps its name). One implementation, invoked independently by the transport and by the primitives — idempotent double verification (D-IMPL-69) that a replay can repeat because every comparison is between recorded values
- Migration: a composition root that called `enforce_signed_binding` passes the resolved `HitlPolicy` (from `resolve_hitl_policy`) instead of `trusted_keys` and `required`; the SDK's own transport and four primitives already do

## ccf.hitl.transport.enforce_signed_binding

- Surface: ccf.hitl.transport.enforce_signed_binding
- Public surface: true
- Change type: removed
- Before: `enforce_signed_binding(authorized, submission, *, identity_provider, trusted_keys, required) -> None`
- After: absent; `enforce_attestation(...) -> HitlActionClaims`
- Why: C13(a); see `enforce_attestation`
- Migration: see `enforce_attestation`

## ccf.hitl.transport.resolve_hitl_policy

- Surface: ccf.hitl.transport.resolve_hitl_policy
- Public surface: true
- Change type: added
- Before: absent — `signed_binding_required(...)` resolved the policy internally and returned only the boolean
- After: `resolve_hitl_policy(*, control_plane: ControlPlaneProtocol | None, hitl_policy_key: str | None) -> tuple[str, HitlPolicy] | None` — the pinned version (the Control Plane's version identifier for the artifact; the reference registry's is the content address, not the semver lane) and the parsed `HitlPolicy` the key resolves to, or `None` when no Control Plane or no key is wired; `signed_binding_required` is now built on it
- Why: `D-IMPL-363` E3 — the verifier needs the policy's window and keys, and the submission records which `key@version` admitted it (`HitlPolicy.pinned_ref`)
- Migration: none for a caller of `signed_binding_required`, whose signature and answer are unchanged

## ccf.hitl.transport.SignedBindingMismatchRefused

- Surface: ccf.hitl.transport.SignedBindingMismatchRefused
- Public surface: true
- Change type: added
- Before: absent — a swapped verdict refused as `SignedBindingInvalidRefused`, and there was no refusal for a claim that verified but disagreed
- After: `SignedBindingMismatchRefused(PermissionError)` — a verified signature whose claims disagree with the capability, the request, the minted binding or the key map (`key_id` not declared for the subject). Mapped to `signed-binding-mismatch` (HTTP 403; MCP tool error) at both doors
- Why: `D-IMPL-363` E6 / C4(a) — a signature over one statement does not authorize another, and the code says which failure that is
- Migration: handle `signed-binding-mismatch` beside `-required` and `-invalid`; a client that mapped a swapped verdict to `-invalid` now sees `-mismatch`

## ccf.hitl.transport.SignedBindingStaleRefused

- Surface: ccf.hitl.transport.SignedBindingStaleRefused
- Public surface: true
- Change type: added
- Before: absent — freshness was clock equality with the door's `action_time`, which no wall-clock signer could satisfy
- After: `SignedBindingStaleRefused(PermissionError)` — `issued_at` outside the directional window against the recorded `action_time` (post-dated beyond the skew, or expired beyond the max age), or a nonce already presented for the `(tenant, event_key)` on the reference transport. Mapped to `signed-binding-stale` at both doors
- Why: `D-IMPL-363` E3 / E4 — the 353-06 limit is closed by a window the signer can meet under a wall clock, and a signed statement is admitted once
- Migration: handle `signed-binding-stale`; a signer that retries re-signs with a fresh nonce and a fresh `issued_at`

## ccf.hitl.transport.HitlPolicy

- Surface: ccf.hitl.transport.HitlPolicy
- Public surface: true
- Change type: reshaped
- Before: `{semver, signed_binding_required: bool = False}`
- After: three members join, each `None` by default and hash-transparent at `None` (CINV-06): `signature_max_age_seconds: int | None` (positive), `permitted_clock_skew_seconds: int | None` (non-negative) and `trusted_keys: Mapping[str, Mapping[str, JsonWebKey]] | None` (approver subject → `kid` → public JWK). A model validator refuses `signed_binding_required: true` without all three at parse (`ArtifactLoadError` through the Control Plane), so a required policy never admits under an invented window. Two helpers: `keys_for(subject_id)` and `pinned_ref(key=, version=) -> "key@version"`
- Why: `D-IMPL-363` E3 / E5 / C6(a) — the window and the trust map are the deployment's statements in the pinned artifact (CINV-01), the ONE trust source; a second source is the hole this wave closes
- Migration: every `ccf.hitl-policy` document that sets `signed_binding_required: true` must now also state `signature_max_age_seconds`, `permitted_clock_skew_seconds` and `trusted_keys`; a document that does not is refused when registered. A policy that does not require signing is unchanged, and keeps its content address

## ccf.hitl.transport.HitlActionRequest

- Surface: ccf.hitl.transport.HitlActionRequest
- Public surface: true
- Change type: reshaped
- Before: `{event_key, action, product_content_hash, annotation, signed_binding: SignedPrincipalBinding | None}`
- After: `signed_binding` is replaced by `attestation: SignedHitlAction | None` (hash-transparent at `None`). `extra=forbid` makes a body that still sends `signed_binding` a boundary refusal
- Why: `D-IMPL-363` E1 / C12(a) — the request carries the signer's own statement, in one shape at both doors
- Migration: send `attestation` instead of `signed_binding`

## ccf.hitl.HitlActionRequest

- Surface: ccf.hitl.HitlActionRequest
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export, `signed_binding` field
- After: the `ccf.hitl` package re-export of `ccf.hitl.transport.HitlActionRequest`, `attestation` field
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.transport.HitlActionSubmission

- Surface: ccf.hitl.transport.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: `signed_binding: SignedPrincipalBinding | None`; no record of which policy admitted the submission
- After: `signed_binding` is replaced by `attestation: SignedHitlAction | None`, and `hitl_policy_ref: str | None` joins — both hash-transparent at `None` — stamped by the transport as the `key@version` of the policy in force (`None` when no policy is wired). The transport's seen-nonce check keys on `(tenant, claims.event_key, claims.nonce)`
- Why: `D-IMPL-363` E1 / E3 — the recorded submission carries what was signed and which policy judged it, so dimension 2 can say so and a replay can re-verify against the same pinned policy
- Migration: none for a stored record — a submission recorded before this change carries neither field and rehydrates to the address it was written at. The base-roster name `HitlActionSubmission.signed_binding` is retired by ruling (`tools/lints/tests/test_base_roster.py::RETIRED_BY_RULING`)

## ccf.hitl.HitlActionSubmission

- Surface: ccf.hitl.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export, `signed_binding` field
- After: the `ccf.hitl` package re-export of `ccf.hitl.transport.HitlActionSubmission`, `attestation` and `hitl_policy_ref` fields
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.transport.InMemoryHitlTransport

- Surface: ccf.hitl.transport.InMemoryHitlTransport
- Public surface: true
- Change type: reshaped
- Before: `__init__(*, control_plane=None, hitl_policy_key=None, identity_provider=None, trusted_keys=None)`; `submit` verified the signed binding against `trusted_keys`
- After: `__init__(*, control_plane=None, hitl_policy_key=None, identity_provider=None)` — no `trusted_keys`. `submit` resolves the policy, stamps `hitl_policy_ref`, runs `enforce_attestation` outside the lock when the policy requires it, and then — inside the lock, after verification and before recording — checks and inserts the nonce in one step, refusing a reuse as `SignedBindingStaleRefused`. Two racing presentations of one attestation cannot both pass
- Why: `D-IMPL-363` C6(a) (one trust source) and E4 / C11(a) (atomic nonce)
- Migration: remove the `trusted_keys=` argument; declare the keys per subject in the pinned policy instead

## ccf.hitl.InMemoryHitlTransport

- Surface: ccf.hitl.InMemoryHitlTransport
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export, `trusted_keys` constructor argument
- After: the `ccf.hitl` package re-export of `ccf.hitl.transport.InMemoryHitlTransport`, without it
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.approval_gate.ApprovalGate

- Surface: ccf.hitl.approval_gate.ApprovalGate
- Public surface: true
- Change type: reshaped
- Before: `__init__(..., identity_provider=None, trusted_keys=None)`; `resolve(..., signed_binding=None)`
- After: `__init__(..., identity_provider=None)` — no `trusted_keys`; `resolve(..., attestation: SignedHitlAction | None = None)`. Enforcement resolves the pinned policy and calls `enforce_attestation`; the TOCTOU product-hash compare and the capability checks are unchanged
- Why: `D-IMPL-363` C6(a) and the brief §4 item 7 — the primitives verify through the same shared verifier against the same single trust source
- Migration: rename `signed_binding=` to `attestation=` at the call site; remove `trusted_keys=` from the constructor

## ccf.hitl.ApprovalGate

- Surface: ccf.hitl.ApprovalGate
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export, `trusted_keys` constructor argument
- After: the `ccf.hitl` package re-export of `ccf.hitl.approval_gate.ApprovalGate`, without it
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.escalation.ExceptionEscalation

- Surface: ccf.hitl.escalation.ExceptionEscalation
- Public surface: true
- Change type: reshaped
- Before: `__init__(..., identity_provider=None, trusted_keys=None)`; `resolve(..., signed_binding=None)`
- After: `__init__(..., identity_provider=None)`; `resolve(..., attestation: SignedHitlAction | None = None)`, enforced through `enforce_attestation` against the pinned policy
- Why: `D-IMPL-363` C6(a); brief §4 item 7
- Migration: rename `signed_binding=` to `attestation=`; remove `trusted_keys=`

## ccf.hitl.ExceptionEscalation

- Surface: ccf.hitl.ExceptionEscalation
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export, `trusted_keys` constructor argument
- After: the `ccf.hitl` package re-export of `ccf.hitl.escalation.ExceptionEscalation`, without it
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.override.OverrideBoundary

- Surface: ccf.hitl.override.OverrideBoundary
- Public surface: true
- Change type: reshaped
- Before: `__init__(..., identity_provider=None, trusted_keys=None)`; `resolve(..., signed_binding=None)`
- After: `__init__(..., identity_provider=None)`; `resolve(..., attestation: SignedHitlAction | None = None)`. The signed `action` must equal the action the boundary derives (`override` / `approve`), else `SignedBindingMismatchRefused`
- Why: `D-IMPL-363` C6(a) and C1(a); brief §4 item 7
- Migration: rename `signed_binding=` to `attestation=`; remove `trusted_keys=`; sign the derived action

## ccf.hitl.OverrideBoundary

- Surface: ccf.hitl.OverrideBoundary
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export, `trusted_keys` constructor argument
- After: the `ccf.hitl` package re-export of `ccf.hitl.override.OverrideBoundary`, without it
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf.hitl.review_queue.ReviewQueue

- Surface: ccf.hitl.review_queue.ReviewQueue
- Public surface: true
- Change type: reshaped
- Before: `__init__(..., identity_provider=None, trusted_keys=None)`; `release(..., signed_binding=None)` / `reject(..., signed_binding=None)`
- After: `__init__(..., identity_provider=None)`; `release(..., attestation=None)` / `reject(..., attestation=None)`. The signed `action` must equal the action the queue derives (`approve` / `reject`), else `SignedBindingMismatchRefused`
- Why: `D-IMPL-363` C6(a) and C1(a); brief §4 item 7
- Migration: rename `signed_binding=` to `attestation=`; remove `trusted_keys=`; sign the derived action

## ccf.hitl.ReviewQueue

- Surface: ccf.hitl.ReviewQueue
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export, `trusted_keys` constructor argument
- After: the `ccf.hitl` package re-export of `ccf.hitl.review_queue.ReviewQueue`, without it
- Why: the package re-exports what the module defines; see the entry above
- Migration: as above

## ccf_runtime.http_api.errors.ERROR_SIGNED_BINDING_MISMATCH

- Surface: ccf_runtime.http_api.errors.ERROR_SIGNED_BINDING_MISMATCH
- Public surface: true
- Change type: added
- Before: absent — the reserved signed-binding codes were `signed-binding-required` and `signed-binding-invalid`
- After: `ERROR_SIGNED_BINDING_MISMATCH = "signed-binding-mismatch"`; HTTP 403 from `POST /hitl/actions` and the MCP `submit_hitl_action` tool error for `SignedBindingMismatchRefused`
- Why: `D-IMPL-363` E6 / C4(a); the reserved-code roster in `tests/http_api/test_auth_hardening.py` is extended by hand, never counted
- Migration: handle the code; a swapped verdict now maps here rather than to `signed-binding-invalid`

## ccf_runtime.http_api.errors.ERROR_SIGNED_BINDING_STALE

- Surface: ccf_runtime.http_api.errors.ERROR_SIGNED_BINDING_STALE
- Public surface: true
- Change type: added
- Before: absent
- After: `ERROR_SIGNED_BINDING_STALE = "signed-binding-stale"`; HTTP 403 and the MCP tool error for `SignedBindingStaleRefused`
- Why: `D-IMPL-363` E3 / E4 / E6
- Migration: handle the code; re-sign with a fresh nonce and `issued_at` to retry

## runtime/ccf_runtime/mcp/hitl_server.py

- Surface: runtime/ccf_runtime/mcp/hitl_server.py
- Public surface: false
- Change type: behavior
- Before: the `submit_hitl_action` tool took `signed_binding_signature: str | None` and `signed_binding_key_id: str | None` and wrapped a signature around the binding it minted
- After: the tool takes ONE `attestation: dict | None` argument — a `SignedHitlAction` document, the same shape as the HTTP body's — validates it (`signed-binding-invalid` when it is not one), mints the binding as before, and maps `signed-binding-mismatch` / `signed-binding-stale` beside the two existing codes. The tool's argument roster is `{tenant, event_key, action, product_content_hash, annotation, attestation}`, pinned as an exact set (C8)
- Why: `D-IMPL-363` C12(a) — one object in one shape at both doors
- Migration: an MCP client sends `attestation` as one object instead of the two scalars

## openapi.json

- Surface: openapi.json
- Public surface: false
- Change type: behavior
- Before: the published HTTP contract carried `SignedPrincipalBinding` and `HitlActionRequest.signed_binding`
- After: it carries `HitlActionClaims` and `SignedHitlAction`, and `HitlActionRequest.attestation` references the latter; the two new error codes appear in the route's responses. Regenerated with `tools/dump_openapi.py` under the D-12 drift baseline, in the same commit as the schema
- Why: the HTTP API publishes the request shape, so the reshaping reaches the committed spec by construction
- Migration: regenerate any client built from the spec; the body field is `attestation`

## docs/schemas/ccf.hitl-policy.json

- Surface: docs/schemas/ccf.hitl-policy.json
- Public surface: false
- Change type: behavior
- Before: two properties, `semver` and `signed_binding_required`
- After: three more, each nullable, defaulted `null` and marked `ccf_hash_transparent`: `signature_max_age_seconds`, `permitted_clock_skew_seconds` and `trusted_keys` (object → object → object of strings). The cross-field rule — all three required when `signed_binding_required` is true — is a model validator and is not expressible in the schema; the committed schema shows the members and the Control Plane refuses the document. Regenerated with `tools/dump_schemas.py`
- Why: the committed schema tree is the authoring baseline an adopter reads in their editor (ERGO-12)
- Migration: a `ccf.hitl-policy` document that requires signing states the three members; see `HitlPolicy`
