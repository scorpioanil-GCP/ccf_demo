# 371-22 — SEC-022: A2A envelopes carry signed issuance claims; replays and stale issuances are refused; the peered composite leg is bound to its signed question

`D-IMPL-371` (and `D-IMPL-368`/`D-IMPL-369`/`D-IMPL-370`), row `SEC-022`, ruled
at Q14 (a) on all four parts of
`docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md`: the window
source is the fabric's instant, the seen-set is in-process by default behind a
small Protocol, the window is declared in the trust-policy artifact with no SDK
default, and envelopes without the new claims are refused. `D-IMPL-371` adds
the signed question binding that completes SEC-025's peered leg (SEC-025-U1).

**What this does NOT do.** It does not bound request bodies before parsing on
the LF leg (`SEC-021-U1`, open by ruling), and it changes no transport: the
envelope keeps its three members and only its `protected` member grows
(measured: an honest peered header is 1343 bytes against the 2048 bound).

**Bounds, stated.** The reference seen-set covers one gate in one process and
is never pruned; a deployment with several receivers must share one through
`SeenNonceSetProtocol`. The nonce is spent immediately before the admission
record is written, so an `AdmissionNotRecorded` failure after it leaves the
nonce spent and a retry of the same envelope refused `replayed` (fail closed).
On the composite route, the peering gate's own refusal (`replayed`,
`stale-issuance`) still surfaces as `provenance-unverified`, because
`src/ccf/products/child_resolver.py::GrantBoundChildResolver._admit_peered`
drops gate refusals by name — not changed by this row.

## ccf.peering.issuance.IssuanceClaims

- Surface: ccf.peering.issuance.IssuanceClaims
- Public surface: true
- Change type: added
- Before: absent — the signed envelope carried no issuance instant, nonce or question
- After: a `CCFContract` of `schema_version`, `issued_at` (timezone-aware; naive refused), `nonce` (non-empty, opaque), `answered: IssuedAnswer` and `echo: IssuedRequest`, carried as ONE protected-header member so the JWS payload stays the product's content-address preimage
- Why: Q14 (a) and `D-IMPL-371`: an envelope must say when it was issued, under which nonce and for which question, or it cannot be held to a window, refused as a replay, or bound to the subject its composite asked
- Migration: a producer (the deployment's emitter; the SDK ships no signer) mints `IssuanceClaims` with its own `issued_at` and `nonce` and signs with `assertions={ISSUANCE_CLAIMS_HEADER: encode_issuance_claims(claims), ...}`. Nonce uniqueness per `(tenant, peer)` is the producer's obligation; the SDK ships no generator. `issued_at` must be the producer's real issuance instant, not a wall-clock read the consumer cannot match

## ccf.peering.issuance.IssuedAnswer

- Surface: ccf.peering.issuance.IssuedAnswer
- Public surface: true
- Change type: added
- Before: absent
- After: the four question axes (`subject`, `intent`, `freshness`, `asked_at`) a producer signed it answered; member for member the shape of `ccf.products.door.AnsweredQuestion`, which cannot be a field type here without an import cycle
- Why: the composite's shared answer check needs the answered axes; composition converts this to the door's type
- Migration: as for `IssuanceClaims`

## ccf.peering.issuance.IssuedRequest

- Surface: ccf.peering.issuance.IssuedRequest
- Public surface: true
- Change type: added
- Before: absent
- After: the request (`product_id`, `parameters`, `temporal_boundary`) a producer signed it answered; member for member the shape of `ccf.products.door.WireRequest`
- Why: the composite's shared answer check refuses an answer that echoes no request
- Migration: as for `IssuanceClaims`

## ccf.peering.issuance.ISSUANCE_CLAIMS_HEADER

- Surface: ccf.peering.issuance.ISSUANCE_CLAIMS_HEADER
- Public surface: true
- Change type: added
- Before: absent
- After: the protected-header member name the claims travel in, `ccf-issuance`
- Why: one named seam, beside `ccf_producer` and `ccf-child-eligibility`
- Migration: a producer signs the encoded claims under this name

## ccf.peering.issuance.ISSUANCE_CLAIMS_SCHEMA_VERSION

- Surface: ccf.peering.issuance.ISSUANCE_CLAIMS_SCHEMA_VERSION
- Public surface: true
- Change type: added
- Before: absent
- After: the claim set's lane, `1.0.0`; a consumer refuses any other lane rather than reading unknown members as absent
- Why: an added binding must never be silently ignored
- Migration: none

## ccf.peering.issuance.IssuanceClaimsMalformed

- Surface: ccf.peering.issuance.IssuanceClaimsMalformed
- Public surface: true
- Change type: added
- Before: absent
- After: the decode-boundary error for an absent, unparseable or unknown-lane member; the gate turns it into a `claims-missing` refusal
- Why: malformed and stale are different failures and are reported differently
- Migration: none

## ccf.peering.issuance.mint_issuance_claims

- Surface: ccf.peering.issuance.mint_issuance_claims
- Public surface: true
- Change type: added
- Before: absent
- After: assembles `IssuanceClaims` at the current lane from caller-supplied `issued_at`, `nonce`, `answered` and `echo`; reads no clock and generates no nonce
- Why: a clock read or a generator here would be an SDK default for a deployment choice (CINV-01, `D-IMPL-358`)
- Migration: a producer (the deployment's emitter; the SDK ships no signer) mints `IssuanceClaims` with its own `issued_at` and `nonce` and signs with `assertions={ISSUANCE_CLAIMS_HEADER: encode_issuance_claims(claims), ...}`. Nonce uniqueness per `(tenant, peer)` is the producer's obligation; the SDK ships no generator. `issued_at` must be the producer's real issuance instant, not a wall-clock read the consumer cannot match

## ccf.peering.issuance.encode_issuance_claims

- Surface: ccf.peering.issuance.encode_issuance_claims
- Public surface: true
- Change type: added
- Before: absent
- After: renders the claims as canonical bytes for the protected header
- Why: the string a producer signs and the string a consumer re-derives cannot differ by key order or whitespace
- Migration: a producer (the deployment's emitter; the SDK ships no signer) mints `IssuanceClaims` with its own `issued_at` and `nonce` and signs with `assertions={ISSUANCE_CLAIMS_HEADER: encode_issuance_claims(claims), ...}`. Nonce uniqueness per `(tenant, peer)` is the producer's obligation; the SDK ships no generator. `issued_at` must be the producer's real issuance instant, not a wall-clock read the consumer cannot match

## ccf.peering.issuance.decode_issuance_claims

- Surface: ccf.peering.issuance.decode_issuance_claims
- Public surface: true
- Change type: added
- Before: absent
- After: parses the header member back into `IssuanceClaims`, raising `IssuanceClaimsMalformed` on absence, non-JSON, wrong shape or an unknown lane
- Why: absence is not a pass
- Migration: none

## ccf.peering.issuance.issuance_staleness

- Surface: ccf.peering.issuance.issuance_staleness
- Public surface: true
- Change type: added
- Before: absent
- After: the two directional window comparisons of `ccf.hitl.transport.enforce_attestation`: `post-dated` when `issued_at` is more than the skew after `now`, `expired` when it is more than the max age before it; both edges are inside
- Why: never an absolute delta: a clock running ahead and an envelope held back are different failures with different bounds
- Migration: none

## ccf.peering.issuance.SeenNonceSetProtocol

- Surface: ccf.peering.issuance.SeenNonceSetProtocol
- Public surface: true
- Change type: added
- Before: absent
- After: a `runtime_checkable` Protocol with one atomic method, `admit_once(*, tenant_id, peer_id, nonce) -> bool` (`True` on first sight)
- Why: Q14-2 (a): in-process by default, pluggable so several receivers can share one set
- Migration: a deployment running more than one receiver implements this over a shared store and passes the same instance (or client) to every `PeeringAdmissionGate` as `seen=`; otherwise each receiver refuses only the replays it saw itself

## ccf.peering.issuance.InProcessSeenNonceSet

- Surface: ccf.peering.issuance.InProcessSeenNonceSet
- Public surface: true
- Change type: added
- Before: absent
- After: the reference `SeenNonceSetProtocol`: a set behind a lock, one per gate. Entries are retained for the gate's lifetime and are not pruned (the same retention question as the HITL reference transport's `CR-363-07`)
- Why: the in-process default the ruling names
- Migration: none for a single receiver; see `SeenNonceSetProtocol` for several

## ccf.peering.admission.GATE_ISSUANCE

- Surface: ccf.peering.admission.GATE_ISSUANCE
- Public surface: true
- Change type: added
- Before: absent
- After: the gate token `peering-issuance`, shared by the issuance check and the replay consult
- Why: a refusal an operator reads names the seam
- Migration: none

## ccf.peering.admission.IssuanceRefusal

- Surface: ccf.peering.admission.IssuanceRefusal
- Public surface: true
- Change type: added
- Before: absent
- After: an `AdmissionRefusal` with `failure` in `{claims-missing, stale-issuance, replayed}`, `issued_at`, `max_age_seconds` and `skew_seconds`; audited `resolved=False` like every refusal; envelope kind `issuance-refusal` (minimal disclosure: `tenant_id`, `peer_id`, `failure`; HTTP: fulfillment withheld)
- Why: Q14 (a) and `D-IMPL-371`: an envelope must say when it was issued, under which nonce and for which question, or it cannot be held to a window, refused as a replay, or bound to the subject its composite asked
- Migration: a consumer that switches on refusal types adds this one

## ccf.peering.trust_policy.PeerTrustGrant

- Surface: ccf.peering.trust_policy.PeerTrustGrant
- Public surface: true
- Change type: reshaped
- Before: four declared entitlement sets
- After: plus two REQUIRED members, `signature_max_age_seconds` (positive) and `permitted_clock_skew_seconds` (non-negative); no default, no `Optional`, no hash-transparent sentinel
- Why: Q14-3 (a): the window is declared in the trust-policy artifact with no SDK default (`D-IMPL-356`, `D-IMPL-38`); per peer because it is an entitlement
- Migration: every registered `ccf.peering-trust-policy` artifact must state both members for every peer, or it no longer validates; every trust policy's content address changes (nothing pinned one). Choose values for your federation: they are not SDK recommendations

## ccf.peering.admission.AdmissionRecord

- Surface: ccf.peering.admission.AdmissionRecord
- Public surface: true
- Change type: reshaped
- Before: the crossing's lineages and `admitted_at`
- After: plus a required `issuance: IssuanceClaims` — the verified claims persisted beside the instant they were judged at
- Why: freshness is judged once, at live admission; a replayed decision reads what was checked rather than re-windowing it later
- Migration: records written from now on have new content addresses (the nonce participates, so two issuances of the same product file two records); no historical record is rewritten and none was pinned

## ccf.peering.admission.PeeringAdmissionGate

- Surface: ccf.peering.admission.PeeringAdmissionGate
- Public surface: true
- Change type: behavior
- Before: six checks; the same envelope admitted any number of times, at any number of receivers, until its product expired
- After: check 2b after signature verification: an envelope without readable issuance claims is refused `claims-missing`; one issued outside the peer grant's window, judged against the `now` `admit()` already receives, is refused `stale-issuance`. Immediately before the `AdmissionRecord` is persisted, the nonce is spent atomically through `SeenNonceSetProtocol` (new optional `seen=` constructor argument; `None` builds a fresh in-process set for this gate); a nonce already spent refuses `replayed` and writes no second record. Only an admission spends a nonce. The gate gains no clock
- Why: SEC-022, Q14 (a) on all four parts: the window source is the instant the fabric hands down (`D-IMPL-358`); envelopes without the claims are refused (`D-IMPL-293`)
- Migration: every producer must sign the claims (see `IssuanceClaims`); an envelope without them is now refused. Consumers with several receivers pass one shared `seen=`

## ccf.peering.admission.AdmittedProduct

- Surface: ccf.peering.admission.AdmittedProduct
- Public surface: true
- Change type: behavior
- Before: carried the authenticated header and the verified content address
- After: also carries `issuance` — the claims the gate decoded once from the authenticated header
- Why: composition reads the signed question from the verified admission, never from a second decode
- Migration: none

## ccf.products.composite.CompositeAdmissionGate

- Surface: ccf.products.composite.CompositeAdmissionGate
- Public surface: true
- Change type: behavior
- Before: `peered` was absent from the answer-bound legs (SEC-025-U1): a peered child was composed without subject binding
- After: `peered` is answer-bound: the shared `hold_answer_to_question` compares the asked subject to the answered subject the producer SIGNED, read from the candidate's verified `admission` (never from the candidate's own `question_echo`/`answered_question`). A peered candidate with no admission is refused `provenance-unverified` before that check. Binding is by subject; no question address is minted for the peered leg
- Why: `D-IMPL-371`: SEC-022's signed claim set carries the question, completing Q16 (a) on every leg
- Migration: a peered child must carry issuance claims whose `answered.subject` is the subject the composite asked, or it is refused `question-mismatch`; a hand-built peered candidate's own echo fields are disregarded

## docs/schemas/ccf.peering-trust-policy.json

- Surface: docs/schemas/ccf.peering-trust-policy.json
- Public surface: false
- Change type: reshaped
- Before: four required grant members
- After: six: plus `signature_max_age_seconds` and `permitted_clock_skew_seconds`
- Why: regenerated by `make schemas` from `PeerTrustGrant`
- Migration: a trust-policy document validated against the committed schema must state both members per peer

## docs/schemas/ccf.admission-record.json

- Surface: docs/schemas/ccf.admission-record.json
- Public surface: false
- Change type: reshaped
- Before: no issuance member
- After: a required `issuance` object
- Why: regenerated by `make schemas` from `AdmissionRecord`
- Migration: none for a reader of the SDK's own records
