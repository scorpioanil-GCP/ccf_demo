# 378-42 — The erasure door's server-side subject match: a verdict for the door alone, never the bytes (D3b)

`D-IMPL-378`, Dave's rulings of 2026-10-08 16:40 MST, item 5, verbatim: *"D3b: blocking against my 'fix both now'
instruction. Build the narrowly authorized server-side subject-match path without serving the bytes. Test that it
creates no unauthorized subject/existence oracle. Keep the affected erasure claim open until verified."* Lane
`378f-d3b`. **SEC-009 stays OPEN, and so does the erasure claim this change qualifies**, until the final panel
verifies it; nothing here changes a SEC row.

Through the MCP-backed erasure door, a client filing that validates as a Decision Replay record was refused
`subject-unverifiable`: the artifact server answers those client-lane bytes as a missing address, so the door could
not read them to verify the subject, and a principal could keep a client file out of reach of that door by shaping it
as a record. In process the same filing was erased. The door now asks the artifact server's new
`match_artifact_subject` tool wherever the store answers a requested address as absent; the server judges the bytes
where they are with the door's own judgment (`ccf.erasure.judge_subject`, now shared by both) and answers one
verdict. The tool answers the erasure door of the caller's tenant alone: the deployment grants
`artifact.subject.match` by name, the caller's tenant has an `ErasureAuthority`, and the query carries that
authority's door-key signature — all decided before the substrate is read.

**What the tests measure, on test fixtures** (`tests/mcp/test_erasure_subject_match.py`, over a real MCP
`ClientSession` to the built server with every JSON-RPC message kept): the MCP-backed door reaches the in-process
door's outcome for every client-filing row, and no message carries the document; a caller with no identity, another
tenant's bearer, a same-tenant reader without the grant, and a principal holding the grant but not the door key each
get one byte-identical answer across two worlds and four argument sets, with no substrate read; another tenant's own
door learns nothing about this tenant's address; governed evidence is never judged. The previously strict-xfail
residual, `tests/erasure/test_replay_input_retention_provenance.py::test_over_the_mcp_backed_store_a_record_shaped_client_filing_is_erased_like_any_client_artifact`,
passes without its mark. Not changed: over the MCP-backed store a record the fabric's record writer filed is still
refused `class-unverifiable` (in process, `replay-input`).

## ccf.authz.actions.ACTION_ARTIFACT_SUBJECT_MATCH

- Surface: ccf.authz.actions.ACTION_ARTIFACT_SUBJECT_MATCH
- Public surface: true
- Change type: added
- Before: absent.
- After: `"artifact.subject.match"`: the action the MCP artifact server's `match_artifact_subject` tool declares; its resource is the action id itself. Distinct from every read, write and erase, so a scope mapping reaches the tool only by naming it.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none. A deployment whose erasure door files through the MCP-backed store grants `artifact.subject.match` to the door's MCP credential, and to nothing else, or the door refuses record-shaped client filings `subject-unverifiable` as before.

## ccf.authz.capability.ArtifactSubjectMatch

- Surface: ccf.authz.capability.ArtifactSubjectMatch
- Public surface: true
- Change type: added
- Before: absent.
- After: The capability kind for `artifact.subject.match`, minted only by `mint()` from an authorizer's allow, never at composition, and outside the MCP guard's read kinds, so a stated (ambient stdio) identity is refused it before any decision.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.SUBJECT_MATCH_CLASS

- Surface: ccf.erasure.subject_match.SUBJECT_MATCH_CLASS
- Public surface: true
- Change type: added
- Before: absent.
- After: `"ccf.erasure-subject-match"`: what a subject-match query's door signature asserts in its protected header under `DOOR_SIGNATURE_ASSERTION`. A door-key signature made for an erasure record or for the door's composition probe does not verify as a query, and a query's does not verify as a record's.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.SUBJECT_MATCH_CLASS

- Surface: ccf.erasure.SUBJECT_MATCH_CLASS
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.SUBJECT_MATCH_CLASS`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.SubjectJudgment

- Surface: ccf.erasure.subject_match.SubjectJudgment
- Public surface: true
- Change type: added
- Before: absent.
- After: The judgment over stored bytes, in its order: `bytes-not-at-address`, `bytes-unparseable`, `subject-not-found`, `subject-in-replay-input`, `subject-found`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.SubjectJudgment

- Surface: ccf.erasure.SubjectJudgment
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.SubjectJudgment`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.SubjectMatchAnswer

- Surface: ccf.erasure.subject_match.SubjectMatchAnswer
- Public surface: true
- Change type: added
- Before: absent.
- After: A contract carrying one `verdict` (a `SubjectMatchVerdict`): the whole answer of the subject match. No bytes, no document, no value read out of it.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.SubjectMatchAnswer

- Surface: ccf.erasure.SubjectMatchAnswer
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.SubjectMatchAnswer`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.SubjectMatchQuery

- Surface: ccf.erasure.subject_match.SubjectMatchQuery
- Public surface: true
- Change type: added
- Before: absent.
- After: A contract: what the erasure door asks about one requested address — `tenant_id`, `content_address`, `subject_ref` (both sha256 hex), the subject class's `key_paths` and `subject_ref_salt`. On the server the tenant is the caller's verified tenant, never a wire value.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.SubjectMatchQuery

- Surface: ccf.erasure.SubjectMatchQuery
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.SubjectMatchQuery`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.SubjectMatchSignatureInvalid

- Surface: ccf.erasure.subject_match.SubjectMatchSignatureInvalid
- Public surface: true
- Change type: added
- Before: absent.
- After: A `ValueError` raised by `verify_subject_match_query`: no signature by the declared door key of the query's tenant verifies over exactly the query.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.SubjectMatchSignatureInvalid

- Surface: ccf.erasure.SubjectMatchSignatureInvalid
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.SubjectMatchSignatureInvalid`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.SubjectMatchVerdict

- Surface: ccf.erasure.subject_match.SubjectMatchVerdict
- Public surface: true
- Change type: added
- Before: absent.
- After: The wire verdict: `subject-unverifiable` (bytes not at the address, unparseable, or an address the server does not judge), `subject-not-found`, `subject-in-replay-input`, `subject-found`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.SubjectMatchVerdict

- Surface: ccf.erasure.SubjectMatchVerdict
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.SubjectMatchVerdict`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.judge_subject

- Surface: ccf.erasure.subject_match.judge_subject
- Public surface: true
- Change type: added
- Before: absent.
- After: `judge_subject(payload, query)`: the erasure door's judgment over stored bytes, once — re-hash against the address FIRST, then parse, then a value at a declared key path hashing to the salted reference, then whether the subject also sits in a replay-input field. The in-process door and the MCP artifact server both apply it.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.judge_subject

- Surface: ccf.erasure.judge_subject
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.judge_subject`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.sign_subject_match_query

- Surface: ccf.erasure.subject_match.sign_subject_match_query
- Public surface: true
- Change type: added
- Before: absent.
- After: `sign_subject_match_query(query, *, signer, key_id)`: the erasure door's detached signature over the query's canonical bytes, asserting `SUBJECT_MATCH_CLASS`; returns `protected..signature`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.sign_subject_match_query

- Surface: ccf.erasure.sign_subject_match_query
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.sign_subject_match_query`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.subject_match_verdict

- Surface: ccf.erasure.subject_match.subject_match_verdict
- Public surface: true
- Change type: added
- Before: absent.
- After: `subject_match_verdict(judgment)`: the wire verdict for a judgment; anything but a found or not-found subject is `subject-unverifiable`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match_verdict

- Surface: ccf.erasure.subject_match_verdict
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.subject_match_verdict`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.subject_match.verify_subject_match_query

- Surface: ccf.erasure.subject_match.verify_subject_match_query
- Public surface: true
- Change type: added
- Before: absent.
- After: `verify_subject_match_query(query, *, door_signature, authority, identity_provider)`: refuses, `SubjectMatchSignatureInvalid`, unless the authority is the query's tenant's and the signature verifies over exactly the query against its declared door keys and asserts `SUBJECT_MATCH_CLASS`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf.erasure.verify_subject_match_query

- Surface: ccf.erasure.verify_subject_match_query
- Public surface: true
- Change type: added
- Before: absent.
- After: Re-export of `ccf.erasure.subject_match.verify_subject_match_query`.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf_runtime.mcp.artifact_server.SUBJECT_MATCH_TOOL

- Surface: ccf_runtime.mcp.artifact_server.SUBJECT_MATCH_TOOL
- Public surface: true
- Change type: added
- Before: absent.
- After: `"match_artifact_subject"`: the name of the artifact server's subject-match tool.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf_runtime.mcp.artifact_server.SUBJECT_MATCH_REFUSED

- Surface: ccf_runtime.mcp.artifact_server.SUBJECT_MATCH_REFUSED
- Public surface: true
- Change type: added
- Before: absent.
- After: The one message every caller the subject match does not answer receives, whichever check refused it (no erasure authority for the caller's tenant, a query that is not one, or no door-key signature over exactly it). It names no address, subject or store.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf_runtime.mcp.artifact_server.SubjectMatchRefused

- Surface: ccf_runtime.mcp.artifact_server.SubjectMatchRefused
- Public surface: true
- Change type: added
- Before: absent.
- After: A `PermissionError` the subject-match tool raises, always with `SUBJECT_MATCH_REFUSED`, before the substrate is read; it crosses MCP as the tool's error result.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: the server registered five surfaces: the blob, presence, names and naming resources and `put_artifact`.
- After: it also registers the tool `match_artifact_subject` (action `artifact.subject.match`, resource the action id, the grant's sole tenant, registered mutating so a stated identity is refused). Past the guard it requires an `ErasureAuthority` for the caller's tenant and that authority's door-key signature over the query rebuilt under the caller's tenant, else raises `SubjectMatchRefused`; it then judges only an address the caller's tenant filed on its client lane (no own name under a class the substrate declares under `ReplayMint`), reading the bytes from the substrate as the in-process door reads them, and answers `SubjectMatchAnswer`; governed evidence, another tenant's address and an empty one answer `subject-unverifiable` without a byte read. Every answer and every refusal past the guard appends one `authz_decision` audit event.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none for a deployment that does not grant `artifact.subject.match`: every call is refused by the authorizer. Grant it to the erasure door's credential only.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: the store read, wrote and resolved artifacts and answered naming; it asked the server for nothing else.
- After: it also offers `match_subject(*, query, door_signature)`, which calls the server's `match_artifact_subject` tool (the tenant does not cross the wire) and returns the verdict; a refusal, a server without the tool, or an answer that is not a verdict raises `ArtifactStoreError`, judged after the session closes so it is never reported as an outage.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none.

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: over the MCP-backed store, a request naming a client-lane filing the artifact server answers as absent — a record-shaped one, the residual — was refused `subject-unverifiable`, because the door could not read the bytes to verify the subject.
- After: where its store answers a requested address as absent (`ArtifactNotFound`) and offers `match_subject`, the door signs the query with its door key and asks; the verdict is judged exactly as bytes it reads are (`judge_subject`, the same function), so it reaches the in-process door's outcome. A store with no `match_subject`, a match that does not answer, and any answer that is not a verdict refuse `subject-unverifiable`, as before. Bytes the door reads are judged with `judge_subject` too, with the same refusal codes and messages.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none. Over the MCP-backed store the deployment grants `artifact.subject.match` to the door's MCP credential and declares the door's authority in the server's `ErasureTrust`; without them such filings stay `subject-unverifiable`.

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: over the MCP-backed store, a request naming a client-lane filing the artifact server answers as absent — a record-shaped one, the residual — was refused `subject-unverifiable`, because the door could not read the bytes to verify the subject.
- After: where its store answers a requested address as absent (`ArtifactNotFound`) and offers `match_subject`, the door signs the query with its door key and asks; the verdict is judged exactly as bytes it reads are (`judge_subject`, the same function), so it reaches the in-process door's outcome. A store with no `match_subject`, a match that does not answer, and any answer that is not a verdict refuse `subject-unverifiable`, as before. Bytes the door reads are judged with `judge_subject` too, with the same refusal codes and messages.
- Why: Dave's 16:40 MST item 5, D3b (`D-IMPL-378`): "Build the narrowly authorized server-side subject-match path without serving the bytes."
- Migration: none. Over the MCP-backed store the deployment grants `artifact.subject.match` to the door's MCP credential and declares the door's authority in the server's `ErasureTrust`; without them such filings stay `subject-unverifiable`.
