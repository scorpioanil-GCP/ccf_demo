# 005 — the verdict joins the signed claim set

`SEC-005` (Dave, 2026-10-03: *"The verdict joins the signed claim set. A
signature that still verifies after the action is swapped authorizes a
decision the approver never made."*). The signed payload is
`canonical_bytes(binding)`, and until this change the binding carried only who
acted, how they authenticated, when, and what they saw. The decision travelled
beside it as `HitlActionSubmission.action` and again as
`ApprovalGate.resolve`'s own parameter, and `enforce_signed_binding` never read
it — so one valid signature authorized either verdict. Measured before the
change: a binding signed to reject was presented as an approval, admitted, and
the workflow completed at its approving terminal.

ONE change, recorded at both names the manifest tracks it under — the defining
module and the package re-export. The manifest tracks class SHAPE, so the
change type is `reshaped` rather than `added`: what was added is the
`verdict` field inside that shape.

The prefix `005` is the finding number, not a phase or decision id; the
assembler uses it only as a sort key.

## ccf.hitl.principal.HumanPrincipalBinding

- Surface: ccf.hitl.principal.HumanPrincipalBinding
- Public surface: true
- Change type: reshaped
- Before: four required fields — `approver`, `authentication`, `action_time`,
  `product_content_hash`. The verdict was not among them, so
  `canonical_bytes(binding)` did not cover it and
  `ccf.hitl.transport.enforce_signed_binding` compared only the signature and
  the principal
- After: a fifth required field, `verdict: str`, marked
  `json_schema_extra={HASH_TRANSPARENT_KEY: False}` — a `D-IMPL-243`
  generation boundary, rendered into every binding's hash, so a stored object
  lacking it is named by `generation_mismatch` rather than verifying
  silently. `enforce_signed_binding` now raises `SignedBindingInvalidRefused`
  when the verified binding's `verdict` is not the submission's `action`
- Why: a signature that still verifies after the action is swapped authorizes
  a decision the approver never made (`SEC-005`). Binding the verdict into the
  signed bytes is what makes non-repudiation mean what a deployment that
  turned `HitlPolicy.signed_binding_required` on already believed it meant
- Migration: **a client that signs its own binding must include the verdict,
  and it must equal the action the client submits.** The served doors need no
  change — both mint the binding through
  `ccf_runtime.identity_binding.principal_from_authorized`, which binds the
  verdict from the request field the submission already carries. For
  `ccf.hitl.override.OverrideBoundary` the submitted action is derived
  (`override` when a substitute is supplied, otherwise `approve`), so an
  approver signs the verdict matching the resolve they are performing. The
  binding's content hash moves for every instance, by design; no stored signed
  binding is re-verified anywhere in the SDK, so nothing written before this
  change has to keep verifying

## ccf.hitl.HumanPrincipalBinding

- Surface: ccf.hitl.HumanPrincipalBinding
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export of the same class, carrying the
  same four required fields
- After: the same reshape, reached through the package path — recorded
  separately because the manifest tracks the re-export as its own name and
  the completeness gate matches at name granularity
- Why: the same ruling; see the entry above. A reader who imports from
  `ccf.hitl` rather than `ccf.hitl.principal` needs the migration note to be
  findable under the name they actually use
- Migration: identical to the entry above — include `verdict`, equal to the
  action submitted

## ccf_runtime.identity_binding.principal_from_authorized

- Surface: ccf_runtime.identity_binding.principal_from_authorized
- Public surface: true
- Change type: added
- Before: `(authorized, *, authentication, action_time, product_content_hash)
  -> HumanPrincipalBinding` — the door minted a binding with no verdict in it,
  because the contract had no verdict to mint
- After: a required keyword-only `action: 'str'`, stored as the binding's
  `verdict`. Full shape:
  `(authorized: 'Authorized[HitlSubmit]', *, authentication:
  'AuthenticationClaims', action_time: 'datetime', product_content_hash:
  'str', action: 'str') -> 'HumanPrincipalBinding'`
- Why: the verdict has to reach the signed claims from somewhere, and the door
  is the only minting site (`SEC-005`). Required rather than defaulted: a door
  that forgot it would otherwise mint a binding attesting a decision nobody
  made. `Change type: added` rather than `reshaped` because the name is absent
  from the frozen baseline `docs/surface/v0.2-surface-baseline.json`, so the
  completeness gate places it in the `added` partition — the same reason
  `353-06-the-approval-record-is-server-attested.md` records it as added; this
  entry carries the migration note for the keyword that commit did not have.
  Comment 2026-10-03: this entry was not produced by the completeness gate.
  That gate diffs the live surface against the frozen baseline, not the
  previous commit. `principal_from_authorized` was already outside that
  baseline and already claimed as `added` by `353-06`, so the new required
  `action` keyword produced no unclaimed name. It is recorded here because a
  reader of the earlier `added` entry would not learn that the call shape
  changed.
- Migration: any caller invoking this function directly must pass `action=`,
  equal to the action it submits. Both served doors already do — the HTTP door
  from `body.action`, the MCP door from its `action` parameter — so a
  deployment that reaches the fabric only through them needs no change
