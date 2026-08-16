# 17-04 — the client wire and its one codec

## What did **not** change, stated first

- **No shipped door changed.** Every door emits exactly what it emitted before:
  `canonical_bytes(servable.product).decode("utf-8")` and nothing else. The
  served half of the wire is a *transcription* of that, not a redesign of it.
- **No second serialization was introduced.** `WireOutcome.product_json` carries
  the canonical rendering the doors already produce, verbatim. A base64 or
  nested-JSON envelope was the alternative and was rejected, because it would
  put a second rendering of the vessel on the wire.
- **`ccf.client.__all__` is empty and stays empty in this change.** `D-03` fixes
  the package's public surface at exactly four names — `ProductClient`,
  `Result`, `TransportError`, `BindingError` — and none of the wire types is
  among them. They are the *adapter author's* surface, reached by importing
  `ccf.client.wire` directly.
- **`RefusalEnvelope` and `RequestIdentity` are unchanged.** The wire carries
  the envelope `17-02` froze; it does not restate or reshape it.

## ccf.client.wire.WireRequest

- Surface: ccf.client.wire.WireRequest
- Public surface: true
- Change type: added
- Before: absent — no shape existed for a question in transit. The request's
  `parameters` reached no wire at any door, and neither did the temporal
  boundary a caller asked against
- After: a frozen `CCFContract` carrying `product_id`, `parameters` and
  `temporal_boundary`, with a field validator that refuses any parameter value
  which does not survive the wire unchanged
- Why: `D-11` names the shape an adapter carries but never interprets. The
  parameter guard is what makes the outcome's echo cross-check sound: because
  `parameters` is annotated `Any`, the canonical serializer's correct rendering
  of a `Decimal` or an instant is parsed back as text, the decoded echo then
  differs from what was sent, and the decoder would report a `TransportError`
  on a wire that worked perfectly. Refusing the value at construction — where
  the message can name the wire-stable spelling — is the only alternative to a
  transport failure that never happened
- Migration: none — new type. Callers reaching it are adapter authors; a
  parameter that previously would have been a `Decimal` is spelled with
  `format(value, "f")`, and an instant with `canonical_timestamp`

## ccf.client.wire.WireOutcome

- Surface: ccf.client.wire.WireOutcome
- Public surface: true
- Change type: added
- Before: absent — a served product crossed a door as bare canonical bytes with
  no envelope, and a refusal crossed no door at all
- After: a frozen `CCFContract` carrying `request`, `product_json`,
  `content_address`, `replay_ref` and `refusal`, with a model validator
  enforcing **exactly two states** — served or refused, never both and never
  neither — and requiring the content address on a served outcome while
  forbidding it on a refusal
- Why: `D-11` makes this the canonical serialized form of either half.
  `product_json` is text and never a byte string, which is a ruling rather than
  a detail: the canonical serializer's normalizer admits no byte string in any
  branch, so a `WireOutcome` spelled that way could not be serialized at all.
  Two states are enforced at construction rather than documented, because three
  states would mean every consumer writes its own answer to "what does neither
  mean" and they would not all write the same one
- Migration: none — new type. Note for anyone extending it: the content address
  is an outcome-level sibling of the vessel and never a member of it, for the
  reason `canonical_response` already records — the vessel's bytes *are* the
  product, so carrying the address inside them would change the bytes and
  therefore change the address they claim

## ccf.client.wire.TransportAdapter

- Surface: ccf.client.wire.TransportAdapter
- Public surface: true
- Change type: added
- Before: absent — there was no transport seam for the client role, so nothing
  named what a transport must implement
- After: a `@runtime_checkable` Protocol with exactly one method,
  `ask(request: WireRequest) -> WireOutcome`
- Why: `D-11` — one Protocol, one method. An adapter surface wide enough to
  express policy is an adapter surface on which transports diverge, so the seam
  is deliberately one method. Its contract carries the inversion that matters:
  a transport failure never has a `WireOutcome`, it raises
- Migration: none — new Protocol. Structural typing, so an adapter conforms by
  shape and inherits nothing

## ccf.client.errors.TransportError

- Surface: ccf.client.errors.TransportError
- Public surface: true
- Change type: added
- Before: absent. `ccf_runtime.peering.typed_http.WireTransportError` covers the
  peering wire and is unrelated to the client role; the client taxonomy did not
  exist
- After: a `RuntimeError` subclass meaning *the wire never spoke* — a connection
  that would not open, a timeout, an authentication failure, an address that
  would not resolve, or bytes that do not decode into a well-formed outcome
- Why: `D-10` reserves exceptions for the wire failing and for caller
  negligence, and `D-07` makes a refusal a value. Collapsing the two lets an
  adapter report "the fabric said no" when nothing was ever asked, which is
  unrecoverable downstream because both shapes look well-formed. Declared in
  this plan rather than the one that owns the rest of the taxonomy because the
  codec must raise it and the codec ships first; `BindingError` joins it there
  and subclasses it, so `except TransportError` stays the one catch-all
- Migration: none — new exception type
