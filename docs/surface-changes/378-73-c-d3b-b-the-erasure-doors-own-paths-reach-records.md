# 378-73-c — The erasure door's own paths: a writer-filed record reaches parity over MCP (design 1.3, OWED-RULINGS-3 item 5 (B))

`D-IMPL-378`. Dave, 2026-10-09 06:21 MST, OWED-RULINGS-3 item 5, *"5(B)"*: *"Extend it under the same three
authorizations (full parity; needs a second new door-authorized path)."* His choices on the design, 2026-10-09 10:54
MST, design 1.3, verbatim: *"Q1 (b). Keep the 06:21 uniform “cannot verify.” The door-only path must not tell the door
the truth again. Q2 (a), two tools. Q3 (a), no fallback. Q4 (a), the existing permission."* Q1 (b) is built on the
WIDE reading the batch coordinator gave on 2026-10-12: over MCP, an address the tenant never filed, governed evidence
that is not a record, and a client twin of governed evidence answer the 06:21 uniform `class-unverifiable`; a record
the record writer filed reaches the in-process outcome. SEC-009's erasure claim stays open until verified.

**The finding, measured on test fixtures.** Over the MCP-backed store the erasure door could not verify any address its
tenant filed as governed evidence: a writer-filed record was `replay-input` or `admitted` in process and
`class-unverifiable` over MCP (the panel's K37). With design 1.2's client-lane rule and no door change, the door
over MCP admitted erasing governed evidence through its client twin (measured `admitted`; in process
`class-label-mismatch`). Now `tests/mcp/test_erasure_subject_match.py::test_a_record_the_record_writer_filed_reaches_the_in_process_outcome_over_mcp`
reaches `replay-input` and `admitted` in both doors, `::test_a_client_twin_of_governed_evidence_is_never_erased_over_mcp`
refuses the twin `class-unverifiable` through the naming path alone, and `tests/mcp/test_d3b_door_naming_path.py`
shows one answer and no substrate read for every caller that is not the door (no identity, another tenant's bearer, a
reader without the grant, a holder of the grant without the door key, nine forgeries), with the door itself as the
control.

## ccf_runtime.mcp.artifact_server.DOOR_NAMING_TOOL

- Surface: ccf_runtime.mcp.artifact_server.DOOR_NAMING_TOOL
- Public surface: true
- Change type: added
- Before: absent.
- After: `"name_artifact_for_erasure"`, the erasure door's naming path: a tool under the subject match's three authorizations (the `artifact.subject.match` grant, the tenant's `ErasureAuthority`, a door-key signature over a `DoorNamingQuery`) answering the caller's tenant's names at an address and whether its record writer filed it there, never the bytes. Every refusal is `SUBJECT_MATCH_REFUSED`, audited; so is the uniform "cannot verify" for an address the door may not learn about.
- Why: 5 (B), "a second new door-authorized path"; design 1.3, Q2 (a), Q4 (a).
- Migration: none.

## ccf.erasure.subject_match.DOOR_NAMING_CLASS

- Surface: ccf.erasure.subject_match.DOOR_NAMING_CLASS
- Public surface: true
- Change type: added
- Before: absent.
- After: `"ccf.erasure-door-naming"`, what a naming query's door signature asserts under `DOOR_SIGNATURE_ASSERTION`; distinct from `SUBJECT_MATCH_CLASS`, the record class and the probe class, so a signature made for one door path does not verify on the other.
- Why: design 1.3, domain separation. Test: `tests/mcp/test_d3b_door_naming_path.py::test_each_door_paths_signature_is_refused_on_the_other_path`.
- Migration: none.

## ccf.erasure.DOOR_NAMING_CLASS

- Surface: ccf.erasure.DOOR_NAMING_CLASS
- Public surface: true
- Change type: added
- Before: absent.
- After: the package re-export of `ccf.erasure.subject_match.DOOR_NAMING_CLASS`.
- Why: design 1.3; the package exports every subject-match name.
- Migration: none.

## ccf.erasure.subject_match.DoorNamingQuery

- Surface: ccf.erasure.subject_match.DoorNamingQuery
- Public surface: true
- Change type: added
- Before: absent.
- After: what the door asks the naming path: `tenant_id` (on the server, the caller's verified tenant) and `content_address`.
- Why: design 1.3.
- Migration: none.

## ccf.erasure.DoorNamingQuery

- Surface: ccf.erasure.DoorNamingQuery
- Public surface: true
- Change type: added
- Before: absent.
- After: the package re-export of `ccf.erasure.subject_match.DoorNamingQuery`.
- Why: design 1.3.
- Migration: none.

## ccf.erasure.subject_match.DoorNamingAnswer

- Surface: ccf.erasure.subject_match.DoorNamingAnswer
- Public surface: true
- Change type: added
- Before: absent.
- After: the naming path's whole answer: `names` (the caller's tenant's only, at least one) and `filed_by_record_writer`, decided on the server with its substrate's `WriteKinds`.
- Why: design 1.3.
- Migration: none.

## ccf.erasure.DoorNamingAnswer

- Surface: ccf.erasure.DoorNamingAnswer
- Public surface: true
- Change type: added
- Before: absent.
- After: the package re-export of `ccf.erasure.subject_match.DoorNamingAnswer`.
- Why: design 1.3.
- Migration: none.

## ccf.erasure.subject_match.sign_door_naming_query

- Surface: ccf.erasure.subject_match.sign_door_naming_query
- Public surface: true
- Change type: added
- Before: absent.
- After: the door's detached signature over a naming query's canonical bytes, asserting `DOOR_NAMING_CLASS`.
- Why: design 1.3.
- Migration: none.

## ccf.erasure.sign_door_naming_query

- Surface: ccf.erasure.sign_door_naming_query
- Public surface: true
- Change type: added
- Before: absent.
- After: the package re-export of `ccf.erasure.subject_match.sign_door_naming_query`.
- Why: design 1.3.
- Migration: none.

## ccf.erasure.subject_match.verify_door_naming_query

- Surface: ccf.erasure.subject_match.verify_door_naming_query
- Public surface: true
- Change type: added
- Before: absent.
- After: refuses (`SubjectMatchSignatureInvalid`) unless the signature is the declared door key's over exactly the query, asserting `DOOR_NAMING_CLASS`; the same private check as `verify_subject_match_query`, so the two cannot drift.
- Why: design 1.3. Severing it reddens `tests/mcp/test_d3b_door_naming_path.py::test_a_principal_holding_the_grant_but_not_the_door_key_gets_one_answer_on_the_naming_path`.
- Migration: none.

## ccf.erasure.verify_door_naming_query

- Surface: ccf.erasure.verify_door_naming_query
- Public surface: true
- Change type: added
- Before: absent.
- After: the package re-export of `ccf.erasure.subject_match.verify_door_naming_query`.
- Why: design 1.3.
- Migration: none.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: `match_artifact_subject` judged only an address the caller's tenant filed on its client lane; governed evidence answered `subject-unverifiable` without a byte read.
- After: it also judges a record the tenant's record writer filed (genuine record bytes at their address), as the in-process door does; governed evidence that is not a record, a client twin of it, and an address the tenant never filed still answer `subject-unverifiable`. The new `name_artifact_for_erasure` tool is registered beside it.
- Why: 5 (B) parity; Q1 (b) on the wide reading.
- Migration: none.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: no naming path for the erasure door.
- After: `names_for_erasure(query=, door_signature=)` calls the server's naming tool through the same 401-typed session as every other call; a decline or a malformed answer raises `ArtifactStoreError`. Not a Protocol verb.
- Why: design 1.3, the client side of the second door path.
- Migration: none.

## ccf_runtime.erasure.door.ErasureDoor

- Surface: ccf_runtime.erasure.door.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: over the MCP-backed store the door read the requester-facing names resource and blob, and asked the subject match only where the blob answered absent.
- After: over a store offering `names_for_erasure` the door names every address through the naming path and judges it through the subject match only, never reading the names, blob or presence resources; any decline or failure of either path refuses the address, with no fallback. The `replay-input` rule uses the server's provenance bit. A store offering neither (the in-process stores) keeps the old flow.
- Why: 5 (B); design 1.3, Q3 (a). Seven pinned tests were amended to the ruled outcome (coordinator authorization, 2026-10-12), listed in the lane's commits.
- Migration: the door's MCP credential must hold `artifact.subject.match` (already required for record-shaped client filings); without it every address over MCP is refused, where ordinary client filings could be erased before. Upgrade the artifact server with or before the door's client: a new client against an older server is refused `class-unverifiable` for every address (by construction; not measured).
