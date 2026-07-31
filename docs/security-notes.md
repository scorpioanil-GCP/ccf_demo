# Security Notes — Key Management (v0)

> SDK-defined documentation (CLAUDE.md §7.2, §8.2; D-IMPL-15, D-IMPL-21).
> Records the shipped v0 key-management posture — where signing keys come
> from, how rotation is handled, and the CI-secrets discipline. This note
> is factual to shipped mechanism; it commits to nothing the SDK does not
> already do. Authored under plan 08-04 (D-14 documentation obligation,
> carried out of D-GATE-I.4.1).

## 1. Where signing keys come from

**No key material ever lives in the repository tree.** The SDK ships key
*machinery* (Protocols and reference implementations); which keys exist is
deployment configuration.

### 1.1 A2A identity (D-IMPL-15)

Cross-boundary Context Product signing uses the `IdentityProvider`
Protocol over a `SigningKeySource` Protocol
(`src/ccf/peering/identity.py`): the provider signs canonical product
bytes into a detached JWS; the key source resolves a `key_id` to private
key material and raises `KeyUnavailable` when it holds none.

- **Sourcing:** the deployment injects a `SigningKeySource` at the
  composition root. The shipped reference, `FileBackedKeySource`, reads
  JWK files from an operator-designated directory *outside* the tree —
  it is the development reference, not a custody recommendation.
  Production deployments implement the Protocol against their own key
  custody (KMS, HSM, vault); the SDK takes no dependency on any vendor.
- **Verification:** verifiers take candidate *public* keys from the
  caller (trust-policy resolution, D-IMPL-16). No key is baked into
  mechanism; a validly signed product from a key the consumer's Control
  Plane does not trust is refused at admission.

### 1.2 SignedPrincipalBinding (D-IMPL-21, HITL identity)

`SignedPrincipalBinding` (`src/ccf/hitl/identity_binding.py`) reuses the
same D-IMPL-15 machinery — the joserfc-backed detached JWS envelope of
the injected `IdentityProvider`. The module holds no key machinery, no
JOSE registry, and no algorithm choice of its own: which keys exist and
which provider signs are the deployment's Control Plane configuration.
Verification (`verify_principal_binding`) takes its acceptable public
keys from the caller, mirroring the A2A posture. Whether a HITL door
*requires* a signed binding is the `ccf.hitl-policy` Control Plane
artifact's statement (`signed_binding_required`, D-16 — default false),
never a code constant.

## 2. Rotation posture

**Key rotation is out of v0 scope and is an operator responsibility.**
The SDK's seams are rotation-*compatible* — every signature carries a
`key_id`, verifiers accept a caller-supplied set of public keys (so old
and new keys can be trusted during a rollover), and `SigningKeySource`
resolution is per-call — but the SDK ships no rotation schedule, no
revocation list, and no key-lifecycle automation. Deployments that need
managed rotation implement it behind the `SigningKeySource` /
`IdentityProvider` Protocols.

## 3. CI-secrets discipline

Per the Phase I.4 gate (§1.2) and CLAUDE.md §3.1:

- `ANTHROPIC_API_KEY` is provided to CI exclusively as a GitHub Actions
  secret. It is never committed, never echoed in workflow logs, and never
  written to any file in the tree.
- Cross-AI reviewer credentials (`CODEX_API_KEY`, `CURSOR_API_KEY`) are
  sourced at review time from the operator-local homecams `.env` file,
  which is outside this repository and never committed here.
- The `.gitignore` excludes environments and credentials as a standing
  rule (CLAUDE.md §2.2: "never a secret in the tree"). Key files for
  `FileBackedKeySource` belong in operator-designated directories outside
  the checkout for the same reason.
