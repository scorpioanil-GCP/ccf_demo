# 375-03 — SEC-022 residuals: the replay scope is the signing key

Row `SEC-022`, the two residuals the owner's main-merge record `29a3c5a4` held as
"NOT accepted as closure evidence". Both executed as admitted replays at
`8fceec83`. The red tests are
`tests/peering/test_admission_replay_scope.py`.

**SEC-022-C-01 (ruled: scope by the verified signing key).** The replay consult
spent a nonce under the OBSERVED peer id. A trust policy listing one signing key
under two peer ids therefore admitted the identical signed bytes once under
each. The nonce is now spent under the key the signature verified under, named
by its RFC 7638 thumbprint, so the same bytes under an alias peer id with the
same key are refused `replayed`. That holds whether the alias's grant writes
the key as the same JWK document or as a different one. Two different keys that
share a `kid` label keep separate scopes, so one peer cannot spend another
key's nonces. Verification is offered only the key the protected header names,
so the gate knows which key verified rather than assuming it of the provider.

**What this does NOT do.** It does not prune the reference seen-set (the
`CR-363-07` retention question, unchanged), and it changes no wire format: the
envelope, its claims and the refusal shapes are as `371-22` left them.

## ccf.peering.identity.jwk_thumbprint

- Surface: ccf.peering.identity.jwk_thumbprint
- Public surface: true
- Change type: added
- Before: absent; nothing in the SDK named a key by its key material
- After: `jwk_thumbprint(public_key) -> str`, the RFC 7638 SHA-256 thumbprint (unpadded base64url) over the required members of an `EC`, `OKP` or `RSA` public JWK only, so `kid`, `use` and `alg` do not move it. Raises `KeyUnavailable` for a symmetric (`oct`) or unknown key type, or for a missing required member. Equal to `joserfc`'s `thumbprint()` for the same key
- Why: SEC-022-C-01: the replay scope must be the key the signature verified under, and a `kid` is a label two peers' grants can both use for different keys
- Migration: none; a deployment's shared `SeenNonceSetProtocol` store receives this value and need not compute it

## ccf.peering.issuance.SeenNonceSetProtocol

- Surface: ccf.peering.issuance.SeenNonceSetProtocol
- Public surface: true
- Change type: behavior
- Before: `admit_once(*, tenant_id, peer_id, nonce) -> bool`; spent nonces scoped by the observed peer id
- After: `admit_once(*, tenant_id, key_thumbprint, nonce) -> bool`; spent nonces scoped by the RFC 7638 thumbprint of the key the envelope's signature verified under. No peer id is offered, so an implementation cannot key on one. The manifest records a Protocol's shape as `(*args, **kwargs)`, so this keyword change is visible only here
- Why: SEC-022-C-01: scoped by a peer id, a key listed under two peer ids let the same signed bytes cross once per id
- Migration: a deployment's own implementation renames the `peer_id` keyword to `key_thumbprint` and keys its store on `(tenant_id, key_thumbprint, nonce)`. An implementation left on the old keyword fails loudly with `TypeError` at the first admission rather than silently keeping the per-peer scope. A persistent store's entries spent under peer ids are not found under thumbprints: an envelope admitted shortly before the upgrade, still inside its peer's issuance window, can be admitted once more after it unless those entries are re-keyed under the thumbprints of that peer's grant keys

## ccf.peering.issuance.InProcessSeenNonceSet

- Surface: ccf.peering.issuance.InProcessSeenNonceSet
- Public surface: true
- Change type: behavior
- Before: entries `(tenant_id, peer_id, nonce)`
- After: entries `(tenant_id, key_thumbprint, nonce)`, through the Protocol's renamed keyword
- Why: SEC-022-C-01
- Migration: none for callers of the gate; a direct caller of `admit_once` renames the keyword

## ccf.peering.admission.PeeringAdmissionGate

- Surface: ccf.peering.admission.PeeringAdmissionGate
- Public surface: true
- Change type: behavior
- Before: verification was offered the peer's whole `signing_keys` entry, and the replay consult spent the nonce under `(tenant, observed peer id)`
- After: verification is offered only the key the protected header's `kid` names in the peer's entry (none when it names no key there; the provider refuses that as before). The nonce is spent under `(tenant, thumbprint of that key)`, so the same signed bytes are refused `replayed` under any peer id whose grant lists the same key. A verification that returns with no key offered (a non-conforming `IdentityProvider`) is refused at the signature check as `UnknownSigningKey`, audited, never admitted. The `replayed` refusal's detail names the signing key's scope
- Why: SEC-022-C-01, ruled: the replay key is the verified signing key, not the observed or claimed peer id
- Migration: none for a conforming `IdentityProvider`. Producers must not reuse a nonce under the same signing key, even when the receiver lists that key under more than one peer id
