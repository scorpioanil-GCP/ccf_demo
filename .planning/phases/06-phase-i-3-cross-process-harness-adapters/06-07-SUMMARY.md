---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 07
subsystem: a2a-identity-and-trust
tags: [a2a, identity, signing, jws, trust-policy, control-plane, d-imp-15, d-imp-16]
requires:
  - "joserfc==1.7.4 (pinned by 06-02)"
  - "ccf.contracts.canonical.canonical_bytes / content_hash"
  - "ccf.controlplane.artifacts (ArtifactClass, validate_semver) and registry"
provides:
  - "ccf.a2a.identity — IdentityProvider Protocol + detached-JWS ES256 reference impl"
  - "ccf.a2a.identity.SigningKeySource custody seam + FileBackedKeySource dev impl"
  - "ccf.a2a.identity.SignedContextProduct — the on-the-wire signed envelope contract"
  - "ccf.a2a.trust_policy.A2ATrustPolicy — tenant-scoped Control Plane artifact"
  - "ccf.a2a.trust_policy.A2A_TRUST_POLICY artifact class + trust_policy_key()"
affects:
  - "06-08/06-09/06-10 — the A2A admission gate consumes both modules"
  - "first real joserfc import in the tree; typing friction recorded below"
tech-stack:
  added: []
  patterns:
    - "verification takes candidate keys as an argument, so identity holds no trust decision"
    - "unrepresentability as mechanism: the trust contract has no field that turns verification off"
key-files:
  created:
    - src/ccf/a2a/__init__.py
    - src/ccf/a2a/identity.py
    - src/ccf/a2a/trust_policy.py
    - tests/a2a/test_identity.py
    - tests/a2a/test_trust_policy.py
  modified: []
decisions:
  - "Detachment called through the exported jws.detach_content, which dispatches to detach_json_content; detach_json_content is not in joserfc.jws.__all__ and a private import would be a typed hole"
  - "Verification failure does not distinguish tampered payload from wrong key — from the verifier's side they are one fact"
  - "PeerTrustGrant's empty set means 'nothing', never 'anything'"
metrics:
  duration: ~50m
  completed: 2026-07-26
---

# Phase 06 Plan 07: A2A Identity and Trust Policy Summary

Real ES256 detached-JWS signing and verification over the same canonical bytes
the content address is computed from, behind an `IdentityProvider` Protocol with
a development-grade file-backed custody seam; plus the tenant-scoped Control
Plane trust-policy artifact whose contract has no field that could turn
verification off.

## Task 1 — `IdentityProvider` and the detached-JWS reference implementation

`src/ccf/a2a/identity.py`. The signed payload is
`canonical_bytes(product)` — byte for byte the preimage `content_hash` digests —
so a consumer that verifies the signature and recomputes the content address has
checked one artifact rather than two. `SignedContextProduct` models the
detachment explicitly (`payload`, `protected`, `signature` as three base64url
members) rather than as an opaque blob, so an implementation that kept a second
payload inside the envelope does not typecheck.

Typed failures, each distinguishable because the gate's response differs:
`SignatureInvalid`, `UnknownSigningKey`, `AlgorithmNotPermitted`,
`SignatureMalformed`, `KeyUnavailable`, under an `IdentityError` base.

**Verification takes its candidate public keys as an argument.** That is the
load-bearing shape choice: identity answers *is this from the peer it claims*,
and nothing about *is that peer entitled to send this*. A verifier that also
resolved trust could admit a validly signed product from a peer entitled to
send nothing.

**ES256, with the reason EdDSA is refused recorded inline** (`joserfc` raises
`UnsupportedAlgorithmError` by default and warns about RFC 9864 deprecation even
with an explicit registry), so a later contributor does not read the choice as
legacy and modernize it back.

Custody is `SigningKeySource`, with `FileBackedKeySource` as the development
reference. The docstring states what ships (genuine signing and verification,
a dev key source) and what does not (PKI, rotation policy, hardware custody,
channel security — D-13 scopes the last out of v0). No key material, no `kid`,
and no algorithm identifier other than the justified ES256 default appears in
`/src`.

## Task 2 — the trust-policy artifact

`src/ccf/a2a/trust_policy.py`, modelled on `HalfLifeTable`: SDK-owned shape,
deployment-owned values, `semver` declared with no default so a policy whose
author never stated its lane cannot be constructed. `A2ATrustPolicy` carries
`tenant_id` as part of its content, so two tenants naming the same peer hold two
artifacts with two content addresses — cross-tenant separation is structural,
not conventional. `PeerTrustGrant` carries the four D-IMPL-16 sets: signing JWKs
by `kid`, permitted producer hashes, permitted schema names, permitted policy
regimes.

**The D-21 strong claim, and only this one:** the contract has no field that
could turn signature verification off, and `extra="forbid"` closes the other
direction. The module says nothing stronger about anything else. The claim is
enforced by a field-enumeration test rather than by the docstring, because a
docstring cannot fail when someone adds `trusted_peer_fast_path`.

An empty grant permits nothing rather than everything, and an unconfigured peer
raises `PeerNotTrusted` rather than yielding a permissive empty grant — the
permissive reading of either would be the fast path in disguise.

## Task 3 — two-peer and two-tenant tests (D-23)

36 tests across `tests/a2a/`. The D-23 obligation is met as the default case,
not as an extra: two peers with different `kid`s, and neither key admits the
other's product; a `kid`-relabelled envelope does not verify (proving the header
is unauthenticated input and the signature is what binds the principal); a
verifier holding both keys resolves each product to its correct signer. Two
tenants register policies naming the same peer with different permitted sets,
under different Control Plane keys and different versions, and one tenant's
grant does not admit that peer for the other.

**The tamper test was proven to have teeth**, as the plan required: with the
verification call removed from the implementation, both
`test_a_tampered_payload_is_refused_with_a_signature_failure` and
`test_tampering_is_a_different_failure_from_an_unknown_kid` fail. The
implementation was then restored and `git status --porcelain` confirmed the
restoration before committing.

Keys are generated per test into `tmp_path`; a test walks the repository and
asserts no `*.pem`, `*.jwk`, or `*.key` file exists in the tree.

## Notes for plans 06-08 / 06-09 / 06-10

### `joserfc` typing friction — the answers, so nobody rediscovers them

This plan was the first real import of `joserfc`. Three findings, all resolved
in-file with no `pyproject.toml` change and **no new mypy override**:

1. **`joserfc` ships `py.typed` and is fully typed.** It needs no override, and
   adding one would be a regression.
2. **`jws.detach_json_content` is not in `joserfc.jws.__all__`** — it is
   re-exported from the private `joserfc._rfc7515.json`, so under
   `--strict` (`no_implicit_reexport`) `jws.detach_json_content(...)` fails with
   `attr-defined`. The exported public entry point is **`jws.detach_content`**,
   which for a JSON serialization dispatches straight to `detach_json_content`
   (see `joserfc/jws.py:353`). Call it through the export. Do not import the
   private module, and do not hand-roll the detachment.
3. **`serialize_json` / `deserialize_json` / `detach_content` are overloaded on
   `GeneralJSONSerialization` vs `FlattenedJSONSerialization` TypedDicts.** With
   a single header member the overloads resolve to the flattened form without a
   cast. On the verification side, annotate the reattachment dict as
   `FlattenedJSONSerialization` — a bare `dict[str, str]` matches no overload.
   `verified.payload` needs a `bytes(...)` wrap to avoid `no-any-return`.

**`a2a` / protobuf (research assumption A3) is still unexercised.** Nothing in
this plan imports `a2a`; the `a2a.*` override remains proven only to the extent
that it parses. Budget for it in the first plan that actually imports it.

### Environment note

`joserfc` was pinned by 06-02 in `pyproject.toml` but the shared `.venv` had not
been re-synced at the time this executor started. `pip install "joserfc==1.7.4"`
(the exact pin Dave approved at 06-02's blocking-human checkpoint, already in
the project's dependency list — not a new package decision) resolved to
"Requirement already satisfied". No dependency change was made by this plan.

### Seams the admission gate will want

* `IdentityProvider.verify(signed=..., public_keys=...)` — hand it exactly
  `PeerTrustGrant.signing_keys`, which is how the `kid` is bound to the peer.
* `SignedContextProduct.declared_key_id()` / `.declared_header()` — unverified
  by construction, documented as such; they select the key, they do not prove
  anything.
* `SignedContextProduct.content_address()` — verify *and* compare, against the
  same bytes.
* `trust_policy_key(tenant_id=...)` — the derivation, so two components cannot
  disagree about where a tenant's policy lives.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `jws.detach_json_content` is not statically importable under `--strict`**

- **Found during:** Task 1, first `mypy` run
- **Issue:** The plan (following 06-RESEARCH.md Code Example 4) specifies
  `jws.detach_json_content(...)`. Under `mypy --strict` this is
  `Module "joserfc.jws" does not explicitly export attribute
  "detach_json_content"` — the name is re-exported from a private module and is
  absent from `joserfc.jws.__all__`. The alternatives were a private import
  (a typed hole) or hand-rolled detachment (explicitly forbidden, and the
  reason `joserfc` was chosen over PyJWT at all).
- **Fix:** Called `jws.detach_content`, the library's exported entry point,
  which dispatches to `detach_json_content` for a JSON serialization. The
  detachment remains entirely the library's; nothing in `/src` slices base64url
  to build or split a JWS. The reason is recorded in a comment at the call site
  and `detach_json_content` is still named in the module docstring, so the
  plan's grep criterion holds against a truthful statement rather than a dead
  reference.
- **Files modified:** `src/ccf/a2a/identity.py`
- **Commit:** `a85ec55`

### Scope observations logged, not fixed

**`register_typed` refuses a wrongly shaped artifact without an audit event.**
The plan asked that a refused trust-policy registration be audited with
`resolved=False`, per the `controlplane/registry.py` precedent. That precedent
holds on the `register_versioned` D-05 path, where refusals are *returned
values* and are audited. `register_typed`, which is the path a trust policy
takes, raises `TypeError` from `ArtifactClass.validate` **before** it records
anything — so a wrongly typed registration leaves no trace. This is registry
mechanism and is outside this plan's `files_modified`; it is not caused by this
plan's changes. The test was therefore scoped honestly to *resolution* refusals
(which are audited) and its docstring names the gap rather than obscuring it.
Recommend a registry-side fix in a later plan or a Phase-I review finding.

Note that the plan's other half of that criterion — "an artifact registered
without `semver` is refused" — is satisfied more strongly than asked: such an
artifact cannot be *constructed*, so it never reaches the registry at all. Two
tests assert that.

## Verification

| Check | Result |
|---|---|
| `pytest tests/a2a/ -q` | 36 passed |
| `pytest tests/a2a/test_identity.py -k 'two_peer or peer_b or cross_peer' -q` | 4 passed (D-23) |
| `pytest tests/a2a/test_trust_policy.py -k 'two_tenant or tenant' -q` | 3 passed (D-23) |
| `pytest tests/a2a/test_identity.py -k tamper -q` | 2 passed; both fail with verification removed, then restored |
| `pytest tests -q -m "not postgres and not chroma"` | 645 passed, 2 skipped (609 pre-existing + 36 new; matches 06-02's recorded 609) |
| `python -m mypy` | Success: no issues found in 73 source files |
| `python -m tools.lints --all` | exit 0 |
| `git status --porcelain` after the tamper experiment | clean but for the new test dir |
| No `.pem` / `.jwk` / `keys/` added | asserted by test, and by `git status` |

## Known Stubs

None. Both modules are complete against their plan scope; the admission gate
that consumes them is 06-08+ by design, not a stub here.

## Threat Flags

None beyond the plan's register. T-06-30 through T-06-36 are each addressed:
signature binding via `kid` (two-peer test), tamper refusal over canonical bytes,
algorithm-confusion refusal in both directions, unrepresentable verification
skip (field-enumeration test), per-tenant policy separation, no committed key
material, and — with the caveat logged above — audited unresolved lookups.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `a85ec55` | `IdentityProvider` Protocol + detached-JWS ES256 reference impl |
| 2 | `02d13b1` | A2A trust-policy Control Plane artifact (D-IMPL-16) |
| 3 | `80206b3` | Two-peer identity and two-tenant trust-policy proofs (D-23) |

## Self-Check: PASSED

All five created source/test files exist on disk, and all three task commits
(`a85ec55`, `02d13b1`, `80206b3`) are present in `git log`. No shared
orchestrator artifact (`STATE.md`, `ROADMAP.md`) was modified.
