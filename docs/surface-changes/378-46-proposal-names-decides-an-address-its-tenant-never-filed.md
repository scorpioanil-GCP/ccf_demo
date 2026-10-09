# 378-46 — PROPOSAL, not ruled: the MCP names resource answers an address its tenant never filed as it answers a governed one

`D-IMPL-378`, lane `378h-names`, the final panel's finding F1-1 (seat F1). **A proposal for Dave, not a ruled
change.** The lane's brief said: make the names resource decide `governed or not own` the way the blob and presence
reads do, and if the only workable fix changes a ruled behavior, stop at a proposal. Every fix that answers a present
governed address and an absent one alike changes one: C8's recorded `[]` for an address the caller's tenant never
filed (`377-02`), the erasure door's I6 reason code over the MCP-backed store, or N4's "a refusal crosses as the
shell, which the client reads as an unverifiable answer and the erasure door as `class-unverifiable`". This one keeps
N4's wording and changes the first two. The commits that carry it are labeled `proposal(...)` and can be dropped as a
set. SEC-020 stays open; nothing here changes a SEC row.

**The finding, measured on test fixtures.** The names resource (`ccf-artifact-names://`) took the governed
dereference only for an address the caller's tenant had filed under a class the substrate declares under
`ReplayMint`. An executed-query pin is such an address and holds no record, so it answered the governed read's
`nonexistent` shell, while an address nobody filed answered `[]`. A pin is named by the hash of its own inputs, the
same whichever principal asked, and in the SEC-020 worlds' `similarity_refreshed` shape the withheld and the
nonexistent deployments file different pins (the second walk segment's query embeds the entities the in-process
operator left standing). Reading `names` at a pin present in one deployment only answered the shell in that
deployment and `[]` in the other, as the asker, through the real MCP artifact server
(`tests/mcp/test_f1_names_present_governed_and_absent_alike.py`: 3 failed, 1 passed before; 4 passed after). The blob
and presence resources already answered both alike.

**Not changed by this, measured by the lane's sweep probe on the same fixtures:** the artifact server's versioned-URI
resolution (`ccf-artifact://{tenant}/{class}/{name}@{version}`) answers `found: true` at a present pin's URI and
`found: false` where none is filed; and a principal that can file the pin's bytes on its own client lane through
`put_artifact` reads them back as the governed shell where the pin exists and as its own bytes where it does not. Both
are reported to the coordinator, not fixed here.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: the names resource (`ccf-artifact-names://`) took the governed dereference only for an address the caller's tenant had filed under a class declared under `ReplayMint`; an address the caller's tenant never filed (another tenant's, nobody's, or a string that is not an address) answered `[]`. A governed address holding no record, an executed-query pin above all, therefore answered the governed read's `nonexistent` shell while an address nobody filed answered `[]`, which told an unentitled caller that the pin exists.
- After: an address the caller's tenant never filed takes the governed dereference the blob and presence resources take for it and answers its `nonexistent` shell, the same answer a governed address holding no record gets. A principal the governed dereference admits, and the caller's own client-lane filings, get their names as before. Another tenant's filing still takes no part in the decision (C8): without an own filing the answer is the same shell whatever any other tenant filed.
- Why: the `D-IMPL-378` final panel's F1-1: the names resource was a present-or-absent oracle for governed addresses that hold no record, readable with the asker's own credential. Red tests: `tests/mcp/test_f1_names_present_governed_and_absent_alike.py::test_a_present_governed_pin_and_an_address_nobody_filed_answer_alike` (both parametrizations) and `::test_names_does_not_tell_the_withheld_deployment_from_the_nonexistent_one`.
- Migration: an erasure door built over the MCP-backed store now refuses an address its tenant never filed `class-unverifiable` (another tenant's address and nobody's alike, so I6 still refuses both), where it refused `address-not-in-tenant`; the door over a store handed to it in process still refuses `address-not-in-tenant`. A client that read `[]` from the names resource as "my tenant filed nothing at this address" now receives the refusal shell, as it already did for a governed address it may not read.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: against the shipped artifact server, `names_at` returned `()` for an address the credential's tenant never filed (another tenant's, or nobody's), and raised `McpServerUnreachable` (a non-naming answer) for a governed address the credential may not read. A string that is not a content address returns `()` with no round trip, before and after.
- After: `names_at` raises `McpServerUnreachable` for both. The class's code is unchanged; the server's names resource answers both with the governed read's refusal shell, which `names_at` reads as a non-naming answer, as before. `ccf.replay.provenance.filed_by_record_writer` over this store raises it too, where it returned `False`.
- Why: the `D-IMPL-378` final panel's F1-1 (the entry above).
- Migration: a caller of `names_at` over the MCP-backed store cannot tell an address its tenant never filed from a governed address it may not read, or either from an outage. The SDK's own consumers fail closed or never ask: the erasure door refuses `class-unverifiable`, and `resolve_artifact`, child admission and `OpenedProduct.record_of` ask the provenance check only after the store returned bytes that hash to the address and parse as a record, which over this store means the server already served that record to the same credential (measured for `resolve_artifact` by the lane's consumers probe, not by a test in this tree: it stops at `get` with `ReplayUnresolvable`, before and after).
