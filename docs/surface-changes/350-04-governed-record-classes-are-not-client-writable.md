# 350-04 — a governed record class is written by fabric mechanism, not by a client

`SEC-004` (HIGH) from the security review of 2026-09-23. `ArtifactStoreProtocol.put`
took four values — `tenant_id`, `artifact_class`, `name`, `artifact` — and filed
whatever it was handed. Every one of those arrives off the wire at the HTTP artifact
door (`ArtifactPutRequest`, `runtime/ccf_runtime/http_api/routes/artifact.py`) and at
the MCP `put_artifact` tool, so **a client chose the artifact class its bytes were
filed under, including the class a deployment keeps its Decision Replay records in.**

Measured at `a8df2959` with the four values a request body supplies and nothing else:

```
put ACCEPTED -> cf129f99d0702...85e8ad2586d
uri          -> ccf-artifact://acme/ccf.replay-record/snapshot-2026-09-24@cf129f9...
resolve_uri  -> cf129f99d0702...85e8ad2586d
get          -> b'{"decision":"authorized the trade","planted":true,...}'
```

Content addressing does not close it. An address proves **integrity** — these bytes
hash to this address — and never **provenance**, so a replay resolving that URI would
reproduce the plant and validate it as genuine.

## The Protocol widened, additively

`ArtifactStoreProtocol.put` gains `minted: GovernedWriteToken | None = None` —
keyword-only and defaulted, so every existing call site reads identically at the
signature and every existing implementation still satisfies the runtime-checkable
Protocol. `minted` can only require *more* authority, never less: there is no value of
it that skips the check, and no transport can produce a value of its type. It carries
no section below because a Protocol is not a plain class or function and the generated
manifest does not carry its shape.

## What did NOT change, stated first

- **No existing deployment changes behavior.** The declaration defaults to
  `NOTHING_GOVERNED`, which is the posture every store had before this fragment. A
  store that declares nothing writes every class exactly as it did.
- **No fabric writer was edited.** `ReplayWriter`, `QueryPinWriter`, the HITL action
  writers, the admission writer and the factories are byte-identical. They take an
  `ArtifactStoreProtocol`; `GovernedWriteHandle` **is** one.
- **Read paths are untouched.** `get`, `exists` and `resolve_uri` are unchanged on
  both stores, and `held_content_address` is unchanged. Reads stay governed at the
  delivery boundary (`D-IMPL-345`), not here.
- **Addressing, immutability and the naming index.** Identity is still
  `sha256(canonical_bytes(...))`, `@latest` is still refused by the shared parser, and
  the index is still append-only. No stored artifact moves and no recorded URI stops
  resolving.
- **The HTTP `put` route is not authorized by this change**, deliberately. Authorizing
  it would convert unauthorized forgery into *authorized* forgery — any principal
  holding artifact-write could still mint a replay record — and would leave the MCP
  tool, the CLI and every future transport to re-derive the rule.

## ccf.artifacts.protocol.GovernedRecordClasses

- Surface: ccf.artifacts.protocol.GovernedRecordClasses
- Public surface: true
- Change type: added
- Before: absent — no store could be told that any artifact class was reserved
- After: a frozen `CCFContract` holding `class_ids: frozenset[str]`, built by
  `GovernedRecordClasses.declare(...)`, with `governs(artifact_class) -> bool` and a
  model validator that refuses an id which is empty, is not its own `strip()`, or
  contains `/`. The separator rule is measured rather than stylistic: the naming key is
  `f"{tenant}/{artifact_class}/{name}"`, so a slash-free id admits exactly one
  `(tenant, class, name)` decomposition of a target key, while `class="a/b", name="x"`
  and `class="a", name="b/x"` collide on `t/a/b/x` and only the first would be refused
- Why: `SEC-004` — the SDK cannot name the governed classes. `ccf.replay.serve` already
  calls its record class *"deployment vocabulary, so it is supplied rather than
  assumed"*, and a class list in `/src` would be the hardcoding CLAUDE.md §6.4 forbids.
  So the deployment declares and mechanism enforces, with the declaration bound to the
  store at construction — never per request
- Migration: a deployment that wants the refusal declares its classes and passes
  `governed=` when it constructs its store; a deployment that declares nothing is
  unchanged

## ccf.artifacts.protocol.NOTHING_GOVERNED

- Surface: ccf.artifacts.protocol.NOTHING_GOVERNED
- Public surface: true
- Change type: added
- Before: absent
- After: the explicit empty declaration and both stores' default, named rather than
  left as a bare `frozenset()` so `store.governed is NOTHING_GOVERNED` is answerable
  and a store that governs nothing *says* so instead of leaving the question unasked
- Why: `SEC-004` — the upgrade must be behavior-preserving, and the absence of a
  declaration must be visible rather than silent
- Migration: none

## ccf.artifacts.protocol.GovernedWriteToken

- Surface: ccf.artifacts.protocol.GovernedWriteToken
- Public surface: true
- Change type: added
- Before: absent
- After: the unforgeable evidence that a write is the fabric's own. Constructible only
  with a module-private sentinel, and verified by mint rather than by type, so a
  subclass skipping `__init__` is refused at the write — the
  `ccf.controlplane.state.StateWriteToken` posture. Declared in
  `ccf.contracts.guarded.GUARDED_TYPES` per `D-IMPL-337` with its residual stated
- Why: `SEC-004` — the check is identity against a sentinel and not truthiness,
  because a door forwarding a request-body field would present `True`, `1`, `"minted"`
  or `{"_minted": true}`, and every one of those satisfies `if minted:`
- Migration: none; it is obtained from `GovernedWriteHandle` and from nowhere else

## ccf.artifacts.protocol.GovernedWriteHandle

- Surface: ccf.artifacts.protocol.GovernedWriteHandle
- Public surface: true
- Change type: added
- After: an `ArtifactStoreProtocol` implementation that delegates every method to the
  store it wraps and attaches the minted authority to `put`. This is how the fabric's
  own writer still writes a governed record without a single writer being edited: a
  deployment injects the handle where it injects the store, which is the single-writer
  invariant's own shape (CLAUDE.md §10, *"enforce via dependency injection at boot"*)
- Before: absent
- Why: `SEC-004` — a transport door is handed the store, mechanism is handed the
  handle, and nothing in a request body turns one into the other
- Migration: a deployment that declares governed classes constructs
  `GovernedWriteHandle(store)` and passes **that** to `ReplayWriter`, `QueryPinWriter`
  and any other fabric writer that files under a declared class; the bare store keeps
  going to the doors

## ccf.artifacts.protocol.held_writable_class

- Surface: ccf.artifacts.protocol.held_writable_class
- Public surface: true
- Change type: added
- Before: absent — nothing checked the class a write named
- After: the ONE governance check every store's write path runs, before
  canonicalization, before the address is derived and before the substrate is touched.
  Returns the class unchanged so a call site reads as a pass-through. A presented
  authority is verified first — so a mis-wired door is refused on every class rather
  than only on governed ones — and the declaration is consulted second, depending on
  nothing but the caller's own string and the deployment's boot-time declaration
- Why: `SEC-004` — placed beside `held_content_address` for the reason that one is
  there: the doors are not where the substrate is touched, so a check at one door
  leaves the others filing records
- Migration: none for callers; implementers of `ArtifactStoreProtocol` call it as the
  first statement of their own `put`

## ccf.artifacts.protocol.GovernedWriteRefused

- Surface: ccf.artifacts.protocol.GovernedWriteRefused
- Public surface: true
- Change type: added
- Before: absent
- After: the typed refusal for a client write naming a governed class. Deliberately
  **not** an `ArtifactNotFound` — that would report a refused write as an absence and
  be swallowed by every `except ArtifactNotFound` written for reads — and deliberately
  not an `OSError`, which is the substrate's family and would make a governed refusal
  read like a disk failure. It discloses exactly one bit about the caller's own
  supplied string and does not vary with what the store already holds, so it cannot
  become the write-path twin of the existence oracle `MalformedContentAddress` closes
- Why: `SEC-004`
- Migration: none

## ccf.artifacts.protocol.GovernedWriteForgery

- Surface: ccf.artifacts.protocol.GovernedWriteForgery
- Public surface: true
- Change type: added
- Before: absent
- After: a `GovernedWriteRefused` subclass raised when something that is not a minted
  authority is presented as one. A subclass rather than a sibling for
  `MalformedContentAddress`'s reason: to the caller it is the same refusal, and a door
  catching the parent catches it identically, while a deployment debugging its own
  wiring can still tell the two apart
- Why: `SEC-004`
- Migration: none

## ccf.artifacts.protocol.GovernedClassDeclarationError

- Surface: ccf.artifacts.protocol.GovernedClassDeclarationError
- Public surface: true
- Change type: added
- Before: absent
- After: raised at declaration — at boot, where an operator sees it — when a declared
  class id could not actually be governed. Deliberately not a `ValueError` even though
  it reports a malformed value, because Pydantic absorbs `ValueError` raised from a
  `model_validator` into its own `ValidationError`, and a typed refusal the validation
  framework rewrote into an untyped one would leave callers matching on message text
- Why: `SEC-004`
- Migration: none

## ccf.artifacts.protocol.NAME_SEGMENT_SEPARATOR

- Surface: ccf.artifacts.protocol.NAME_SEGMENT_SEPARATOR
- Public surface: true
- Change type: added
- Before: absent — `"/"` was spelled inline in the URI renderer and in the file store's
  naming key
- After: the separator named once, so the rule that a governed class id may not contain
  it is a fact about the grammar rather than a taste
- Why: `SEC-004`
- Migration: none

## ccf.artifacts.file_store.FileArtifactStore

- Surface: ccf.artifacts.file_store.FileArtifactStore
- Public surface: true
- Change type: reshaped
- Before: `FileArtifactStore(*, root)`; `put` filed any class it was handed
- After: `FileArtifactStore(*, root, governed=NOTHING_GOVERNED)`, a `governed`
  property, and `put(..., minted=None)` whose first statement is
  `held_writable_class`. A refused write leaves the substrate byte-for-byte as it was
  — no artifact file, no naming-index entry — because the check runs before
  canonicalization; a refusal that wrote the bytes and declined only the name would
  still leave the plant retrievable by address
- Why: `SEC-004`
- Migration: none unless the deployment declares governed classes, in which case its
  fabric writers take `GovernedWriteHandle(store)`

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: reshaped
- Before: `McpArtifactStore(*, url, bridge, http_client_factory=None)`; `put` encoded
  and dialed out for any class
- After: a `governed=NOTHING_GOVERNED` keyword, a `governed` property, and
  `put(..., minted=None)` which runs `held_writable_class` **before the payload is
  encoded**, so a governed class never reaches the wire and the refusal is typed rather
  than whatever a remote server happened to answer — the posture `@latest` already had.
  The store behind the artifact server runs the identical check, so a remote client
  that skips this class and speaks to the server directly meets the same refusal
- Why: `SEC-004` — the rule is the store's, so every transport inherits it rather than
  re-deriving it
- Migration: as `FileArtifactStore`
