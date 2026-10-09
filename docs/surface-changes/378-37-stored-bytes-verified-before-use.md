# 378-37 — Stored bytes are checked against their address before child admission, the erasure door or the MCP client lane use them

`D-IMPL-378`, Dave's batch ruling of 2026-10-08 12:29 MST, item E1 (a), verbatim: *"Approve random per-answer
issuance and the named conformance amendments. Preserve record content-address integrity. Random references must
have indistinguishable distributions; equality is no longer the criterion."* Lane `378e-integrity`, which Dave told
to continue under that ruling at 16:40 MST. **SEC-020 and SEC-009 stay OPEN**: nothing here changes a SEC row.

An artifact's address is the sha256 of its stored canonical bytes, and a store's own `get` returns whatever it
holds (the file-backed store returns what is on disk). Three SDK readers took bytes altered in place under an
address as the artifact the address names. Each now re-hashes the bytes before anything uses them and refuses a
mismatch by name: child admission's read of a locally dispatched child's record, the erasure door's read of each
requested address, and the MCP artifact server's client lane.

**Fragment 378-30's title, corrected here rather than rewritten.** 378-30 is titled "record integrity on every
reader". Its body names the readers that change covered: the replay engine's read, `OpenedProduct.record_of` and
the governed evidence read. Child admission's record read and the erasure door's read did not re-hash until this
change, and a store's own `get` still checks nothing.

**What the tests measure, on test fixtures.** `tests/replay/test_record_content_address_integrity.py`: after a
control on the genuine bytes, the stored file is altered in place under its address. The composite raises
`ChildRecordAltered` and the admission gate never receives the altered entities; the erasure door refuses the
request `subject-unverifiable` and starts no approval; the artifact server's blob and presence resources answer the
recorded `nonexistent` / `evidence-absent` determination instead of the altered bytes. Each was red before the
change, and one severing of each check turns its test red again. Two controls over the MCP-backed store pass before
and after: the child read and the erasure door read genuine bytes, and `McpArtifactStore`'s own re-hash refuses
altered ones.

## ccf.products.child_resolver.ChildRecordAltered

- Surface: ccf.products.child_resolver.ChildRecordAltered
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ChildRecordMismatch`, and so a `ValueError`, raised by `GrantBoundChildResolver`'s read of a locally dispatched child's record when the bytes its replay reference resolves to do not hash to that address. Raised before the bytes are parsed, so before the record's provenance or product is checked and before anything read out of them reaches the admission gate. Wrapped opaque at the MCP egress door, like `ChildRecordMismatch`.
- Why: Dave's E1 (a) (`D-IMPL-378`): "Preserve record content-address integrity."
- Migration: none; code that catches `ChildRecordMismatch` also catches it. Catch `ChildRecordAltered` to tell bytes altered under a reference from a record about another product.

## ccf.products.child_resolver.GrantBoundChildResolver

- Surface: ccf.products.child_resolver.GrantBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: a locally dispatched child's record was read through its replay reference and parsed without checking the bytes against the address. Over the file-backed store, bytes altered in place under the address were taken as the child's record, and their touched entities went to the composite admission gate: measured, the composite served and the gate received the altered value.
- After: the bytes are re-hashed against the address before they are parsed. A mismatch raises `ChildRecordAltered`, so the composite does not serve and the gate receives nothing from them. Over the MCP-backed store, the store's own re-hash already read altered bytes as absent (`ArtifactNotFound`) and still does.
- Why: Dave's E1 (a) (`D-IMPL-378`): "Preserve record content-address integrity."
- Migration: none for a store that returns what was written. A store that returns other bytes under an address now gets `ChildRecordAltered` where children used to be admitted on those bytes.

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: as for `ccf.products.child_resolver.GrantBoundChildResolver`, whose record read it delegates to.
- After: as for `ccf.products.child_resolver.GrantBoundChildResolver`.
- Why: Dave's E1 (a) (`D-IMPL-378`).
- Migration: as for `ccf.products.child_resolver.GrantBoundChildResolver`.

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: `request` and `complete` judged each requested address's subject, and the `replay-input` retention rule, from the bytes the store returned at the address, without checking them against it. After a record's bytes were altered in place to drop the subject from its replay-input field, a request the door had refused `replay-input` started its approval workflow.
- After: each address's bytes are re-hashed against the address right after they are read. A mismatch is refused `subject-unverifiable`, with a message saying the bytes do not hash to the address, before the retention judgment, before the workflow starts on `request`, and before the index append and the record filing on `complete`.
- Why: Dave's E1 (a) (`D-IMPL-378`): "Preserve record content-address integrity."
- Migration: none for a store that returns what was written. A request naming an address whose stored bytes no longer hash to it is now refused `subject-unverifiable` instead of being judged on those bytes.

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: as for `ccf_runtime.erasure.ErasureDoor`.
- After: as for `ccf_runtime.erasure.ErasureDoor`.
- Why: Dave's E1 (a) (`D-IMPL-378`).
- Migration: as for `ccf_runtime.erasure.ErasureDoor`.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: on the client lane (an address the caller's tenant filed only in classes not declared under `ReplayMint`), the blob and presence resources served the stored bytes and `{"found":true}` whether or not those bytes hashed to the address. Bytes altered in place crossed under the old address and were audited as a client-lane serve. `McpArtifactStore` refused them on arrival; any other MCP client took them.
- After: client-lane bytes are re-hashed against the address before they are routed or served. Bytes that do not hash to it go to the governed dereference, which answers them as a missing address: the recorded `nonexistent` / `evidence-absent` determination, on blob and presence alike. Bytes that hash to the address are served exactly as before.
- Why: Dave's E1 (a) (`D-IMPL-378`): "Preserve record content-address integrity."
- Migration: none for a store that returns what was written.
