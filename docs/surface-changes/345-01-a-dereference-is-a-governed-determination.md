# 345-01 — a replay reference dereferences to what the serve was allowed to disclose

`D-IMPL-345` (design `docs/D-IMPL-345-DESIGN.md`; rulings R-1..R-5 and `S-02`),
raised by `S-01` at the CP-17 close panel.

Dave, on the contract (verbatim): **"The authorization decision must be held to
the same authenticated principal and applicable product grant that governs
serve."** And on the store repair: **"This belongs at the store, not as
separate HTTP/MCP route filtering. HTTP inherits the refusal. The MCP
artifact/blob resource inherits the same refusal through the store. Do not
special-case `/etc/hostname`, HTTP paths, or MCP paths."**

## What did NOT change, stated first

- **Replay reconstruction is untouched.** `ccf.replay.engine.replay`,
  `replay_refusal`, `resolve_artifact` and `resolve_artifact_at_uri` keep their
  signatures and behavior; `ccf.replay.record` gains no member; no record's
  bytes or content address move; `D-IMPL-341` expiry, `D-IMPL-342` retained
  evidence and `D-IMPL-344` admitted-child retention are read and never
  written.
- **The product door is unchanged.** `GET /product/...` decides, records,
  discloses and renders exactly as it did; its renderer is the same function
  under the same local name.
- **The MCP doors are unchanged.** `get_replay_record` stays authenticated and
  not entitled (`D-IMPL-129`), the MCP artifact role keeps its four surfaces,
  and `recorded_boundary` — which both MCP builders call — is not widened.
- **Artifact PUT is unchanged**, and remains the named `D-IMPL-73` limitation.
- **`AUTH_POSTURE_SENTENCE`, `_INSECURE_DEFAULT_MESSAGE` and `openapi.json` are
  byte-identical.** The committed spec is generated from an app built with no
  auth hook, and the routes' declared request and response models did not move.

## ccf.artifacts.protocol.held_content_address

- Surface: ccf.artifacts.protocol.held_content_address
- Public surface: true
- Change type: added
- Before: absent — each store's read path joined the caller's string to its
  substrate directly
- After: `(content_address: str) -> str`, the one shape check every store's
  read path runs before touching its substrate. Total rather than a list of
  dangerous shapes: a string either is 64 lowercase hex characters or it is
  not an address
- Why: `S-02`. Measured on the file-backed store: a crafted address read the
  host's `/etc/hostname`, and `.artifact-names.json` returned the store's whole
  naming index — every tenant, class, name and address it holds — to any
  caller, including over HTTP. Naming the dangerous shapes one at a time is how
  a filter acquires a hole
- Migration: none for a caller passing real content addresses. A caller passing
  something else now receives `MalformedContentAddress`, which is an
  `ArtifactNotFound`

## ccf.artifacts.protocol.MalformedContentAddress

- Surface: ccf.artifacts.protocol.MalformedContentAddress
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactNotFound` subclass raised by `held_content_address`
- Why: it is true (nothing can be stored at a string that cannot be an
  address), and subclassing keeps the refusal indistinguishable from ordinary
  absence for every caller that already handles absence — a malformed address
  answering differently from an unused one would be an existence oracle at
  every door at once
- Migration: none. `except ArtifactNotFound` already catches it

## ccf.artifacts.protocol.CONTENT_ADDRESS_PATTERN

- Surface: ccf.artifacts.protocol.CONTENT_ADDRESS_PATTERN
- Public surface: true
- Change type: added
- Before: absent — what an address IS was stated in prose on the Protocol and
  enforced nowhere
- After: the compiled `\A[0-9a-f]{64}\Z` the check reads, beside the `D-IMPL-26`
  addressing rule it belongs to
- Why: stated once so two store implementations cannot disagree about what an
  address is, and so the one that disagreed downward could not become a path
  reader
- Migration: none. A new public constant

## ccf.products.disclosure.DISCLOSURE_FULL

- Surface: ccf.products.disclosure.DISCLOSURE_FULL
- Public surface: true
- Change type: added
- Before: absent — `DISCLOSURE_MINIMAL` was named and `"full"` was spelled
- After: `Final[DisclosureLevel] = "full"`, beside `DISCLOSURE_MINIMAL`
- Why: `D-IMPL-345` R-2 makes `full` load-bearing — it is the only level at
  which a whole governed record may cross a door — and a load-bearing posture
  is named rather than spelled at the site that tests it
- Migration: none. A new public constant

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: added
- Before: absent — the replay and artifact routes read the store directly
- After: the ONE governed step both evidence routes call, alongside
  `govern_entitlement`, `govern_absence` and `govern_raised_refusal`. Four
  holds from retained state: the record's own principal; the identical
  `authorize` call the serve made, under the tenant the determination was keyed
  on; the disclosure level read through the recorder; then delivery. Every
  failure and every absence is one recorded, disclosed
  `SubjectUnavailableRefusal`
- Why: `S-01`. A dereference was a lookup, so a principal refused at minimal
  disclosure could read the cause its own shell withheld, and any bearer
  holding another principal's record address could read that record and the
  evidence it named
- Migration: a deployment that binds `product_entitlement=` and
  `refusal_recorder=` at `create_app` gets the governed behavior with no code
  change. One that binds neither now receives `503 product-door-ungoverned` on
  the three evidence GETs instead of `200` — the product route's own posture
  (R-1), and a **breaking delivery-surface change** in the sense `D-IMPL-258`
  (3) used of the `403`→`404` move: intentional, and not to be shimmed back

## ccf_runtime.http_api.routes.replay.build_router

- Surface: ccf_runtime.http_api.routes.replay.build_router
- Public surface: true
- Change type: reshaped
- Before: `build_router(deps)` — the router took the provider bundle and
  nothing else, because its two handlers decided nothing
- After: `build_router(deps, *, entitlement_source=None, refusal_recorder=None)`
  — the same two seams the product router takes, both defaulted, so every
  existing call site keeps working and an unbound door refuses rather than
  reads
- Why: `S-01`. The handlers now authenticate through the app's dependency,
  call `govern_dereference` and encode what it returns; a router that could
  not be handed the seams could not be governed
- Migration: none for `create_app`, which threads both. A caller building this
  router by hand gets the ungoverned posture (`503`) until it passes them

## ccf_runtime.http_api.routes.artifact.build_router

- Surface: ccf_runtime.http_api.routes.artifact.build_router
- Public surface: true
- Change type: reshaped
- Before: `build_router(deps)`
- After: `build_router(deps, *, entitlement_source=None, refusal_recorder=None)`
- Why: as above. `GET` became a governed dereference and is records-only
  (R-3); `POST` is untouched and takes no seam, because a write makes no
  governed determination here
- Migration: none for `create_app`. A hand-built router's `GET` answers `503`
  until the seams are passed; its `PUT` is unaffected

## ccf_runtime.authz.delivery_boundary.DisclosingRecorderProtocol

- Surface: ccf_runtime.authz.delivery_boundary.DisclosingRecorderProtocol
- Public surface: true
- Change type: added
- Before: absent — `RefusalRecorderProtocol` names only `record`
- After: that Protocol's `record` plus `tenant_id` and `disclosure_level_for`,
  the two members `ReplayRefusalRecorder` already carries as fields
- Why: R-2, verbatim — *"Read disclosure authority through the recorder, not
  the entitlement source. The entitlement source answers whether the caller is
  entitled; it is not the authority for what the serve disclosed."* Declared in
  `delivery_boundary` rather than beside `RefusalRecorderProtocol` so that a
  door which only records refusals — both MCP builders — needs neither member
- Migration: none for a deployment binding the SDK's recorder. A hand-written
  record-only recorder is refused at `create_app` when product entitlement is
  bound

## ccf_runtime.authz.delivery_boundary.disclosing_boundary

- Surface: ccf_runtime.authz.delivery_boundary.disclosing_boundary
- Public surface: true
- Change type: added
- Before: absent
- After: `recorded_boundary`'s check first, then the two members R-2 needs. A
  **sibling** of `recorded_boundary` rather than a widening of it
- Why: `recorded_boundary` is one function shared with the egress and
  experience MCP builders, which this ruling leaves byte-for-byte unchanged;
  tightening it there would change the construction posture of two doors
  `D-IMPL-345` does not touch
- Migration: none

## ccf_runtime.authz.delivery_boundary.DereferenceRequest

- Surface: ccf_runtime.authz.delivery_boundary.DereferenceRequest
- Public surface: true
- Change type: added
- Before: absent
- After: `reference`, `by_uri`, `wants_bytes` — what the caller asked for and
  nothing recovered from what it names
- Why: the reference a caller supplied is the only caller-supplied member a
  dereference refusal echoes, so the type that carries it into the boundary
  carries nothing else
- Migration: none

## ccf_runtime.authz.delivery_boundary.DereferencedEvidence

- Surface: ccf_runtime.authz.delivery_boundary.DereferencedEvidence
- Public surface: true
- Change type: added
- Before: absent
- After: `content_address`, `record`, and `payload` for a bytes ask — the
  store's own bytes rather than a re-serialization, so the address a caller
  verifies them against is the one it asked for
- Why: the routes encode what the governed step returns, so the step returns a
  named thing rather than a tuple a route has to know the order of
- Migration: none

## ccf_runtime.authz.delivery_boundary.DEREFERENCE_PRODUCT_ID

- Surface: ccf_runtime.authz.delivery_boundary.DEREFERENCE_PRODUCT_ID
- Public surface: true
- Change type: added
- Before: absent
- After: `"ccf.evidence-dereference"`, the `product_id` every dereference
  refusal carries in its request identity, for every outcome
- Why: `disclose` leaves `request` untouched at every level, because on a serve
  it is what the caller itself asked. A class recovered from the target and
  placed there would cross below `full` and tell the caller both that the
  target exists and what class it was decided on — `D-IMPL-260` (2): the
  earlier allowance that request identity may differ *"was never permission for
  authorization state to change"* an identity field
- Migration: none

## ccf_runtime.authz.delivery_boundary.SURFACE_HTTP_REPLAY_READ

- Surface: ccf_runtime.authz.delivery_boundary.SURFACE_HTTP_REPLAY_READ
- Public surface: true
- Change type: added
- Before: absent — three surface tokens existed, all of them serve surfaces
- After: `"http-replay-read"`, on the resource identity of a replay-read
  determination
- Why: a dereference is a different question from a serve, and an examiner
  reading a record must be able to tell which was asked without inferring it
  from the address
- Migration: none

## ccf_runtime.authz.delivery_boundary.SURFACE_HTTP_ARTIFACT_READ

- Surface: ccf_runtime.authz.delivery_boundary.SURFACE_HTTP_ARTIFACT_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `"http-artifact-read"`
- Why: as above, for the artifact noun
- Migration: none

## ccf_runtime.authz.delivery_boundary.EVIDENCE_SURFACES

- Surface: ccf_runtime.authz.delivery_boundary.EVIDENCE_SURFACES
- Public surface: true
- Change type: added
- Before: absent
- After: the frozenset of the two tokens above. One of the two constants that
  together identify a read-refusal record; `DEREFERENCE_PRODUCT_ID` is the
  other
- Why: both, never either. A record filed through the still-open write path
  could carry one and borrow the other's meaning; requiring both makes that
  forgery a record with no recoverable identity — and it is readable by its
  forger and nobody else, because the principal hold binds every record to its
  author
- Migration: none

## ccf_runtime.authz.refusals.ACTION_REPLAY_READ

- Surface: ccf_runtime.authz.refusals.ACTION_REPLAY_READ
- Public surface: true
- Change type: added
- Before: absent — three action ids existed, none for an evidence read
- After: `"replay.read"`, on the one `authz_decision` event every replay
  dereference appends
- Why: R-5. An allowed read writes no new replay record — reading historical
  evidence creates no determination — but it must leave a trail, and the
  entitlement decision's own event names neither the reference asked nor the
  address delivered, and is absent entirely when the record being read is one
  the boundary itself wrote. This is the seam `D-IMPL-129` named for exactly
  this purpose
- Migration: none

## ccf_runtime.authz.refusals.ACTION_ARTIFACT_READ

- Surface: ccf_runtime.authz.refusals.ACTION_ARTIFACT_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `"artifact.read"`
- Why: a separate id from `replay.read` because the two routes are separately
  mountable and an examiner filtering on one must not silently receive the
  other, even though `D-IMPL-345` decides both the same way
- Migration: none

## ccf_runtime.http_api.errors.ERROR_EVIDENCE_PRINCIPAL_MISMATCH

- Surface: ccf_runtime.http_api.errors.ERROR_EVIDENCE_PRINCIPAL_MISMATCH
- Public surface: true
- Change type: added
- Before: absent
- After: `"evidence-principal-mismatch"` — internal truth, recorded, and below
  `full` never on the wire
- Why: the typed vocabulary every other door refusal already uses
- Migration: none

## ccf_runtime.http_api.errors.ERROR_EVIDENCE_CLASS_UNRECOVERABLE

- Surface: ccf_runtime.http_api.errors.ERROR_EVIDENCE_CLASS_UNRECOVERABLE
- Public surface: true
- Change type: added
- Before: absent
- After: `"evidence-class-unrecoverable"` — the caller's own record retains no
  product class, so the grant that governed its serve cannot be re-decided
- Why: conservative by ruling. Ownership is never inferred from current state
  for a record that predates the identity members, and such a record stays
  readable in-process and by replay exactly as today
- Migration: none

## ccf_runtime.http_api.errors.ERROR_EVIDENCE_DISCLOSURE_WITHHELD

- Surface: ccf_runtime.http_api.errors.ERROR_EVIDENCE_DISCLOSURE_WITHHELD
- Public surface: true
- Change type: added
- Before: absent
- After: `"evidence-disclosure-withheld"` — the caller owns the record and
  holds the grant, but the level in force for it is below `full`
- Why: R-2. A record IS the internal truth, and a dereference may not upgrade a
  caller to the cause its own shell withheld
- Migration: none

## ccf_runtime.http_api.errors.ERROR_EVIDENCE_ABSENT

- Surface: ccf_runtime.http_api.errors.ERROR_EVIDENCE_ABSENT
- Public surface: true
- Change type: added
- Before: absent
- After: `"evidence-absent"` — ONE code for every absence at every level: no
  such address, a malformed one, a URI naming no registered version, bytes that
  are not a record, bytes that do not hash to their address
- Why: the non-record artifact classes are addressed by the hash of their own
  inputs — a graph-query pin by its query, a child question by its five
  members — so a caller able to tell *bytes that are not a record* from
  *nothing* could confirm that a particular traversal or question happened.
  `D-IMPL-345` authorizes no reader for those bytes at any level, so the
  distinction has no legitimate consumer
- Migration: none

## ccf_runtime.http_api.routes.governed_refusal_response

- Surface: ccf_runtime.http_api.routes.governed_refusal_response
- Public surface: true
- Change type: added
- Before: the same function existed as `routes.product._refusal_response`,
  private to one route
- After: the shared renderer three routes encode through — `{kind,
  refusal_type, refusal}` with the status from the disclosed kind. `product.py`
  imports it under its historical local name, so its own text is unchanged
- Why: D-27's sameness property is by construction only if there is one
  emission path. A second route rendering its own body would be two branches
  that happen to agree on the day they were written
- Migration: none. The private name still resolves inside `routes.product`
