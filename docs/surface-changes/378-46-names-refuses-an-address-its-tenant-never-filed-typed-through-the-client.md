# 378-46 — The MCP names resource refuses an address its tenant never filed, and the client raises that refusal typed

`D-IMPL-378`, decision 1 (A), ruled by Dave on 2026-10-09 at 06:21 MST, verbatim: *"Names changes approved: approve the
uniform “cannot verify” erasure refusal and refusal instead of an empty names list. Do not mislabel that access refusal
“server unreachable.” Preserve a typed refusal through the MCP client. Amend the pinned tests accordingly."* Lane
`378h-names` built the server change (the final panel's finding F1-1, seat F1) and lane `378i-names` the typed client
refusal. This amends C8's recorded `[]` (fragment `377-02`) for an address the caller's tenant never filed, and the
erasure door's reason code over an MCP-backed store; the in-process door is unchanged. SEC-020 stays open; nothing here
changes a SEC row.

**The finding, measured on test fixtures.** The names resource (`ccf-artifact-names://`) took the governed
dereference only for an address the caller's tenant had filed under a class the substrate declares under
`ReplayMint`. An executed-query pin is such an address and holds no record, so it answered the governed read's
`nonexistent` shell, while an address nobody filed answered `[]`. A pin is named by the hash of its own inputs, the
same whichever principal asked, and in the SEC-020 worlds' `similarity_refreshed` shape the withheld and the
nonexistent deployments file different pins. Reading `names` at a pin present in one deployment only answered the
shell in that deployment and `[]` in the other, as the asker, through the real MCP artifact server
(`tests/mcp/test_f1_names_present_governed_and_absent_alike.py`: 3 failed, 1 passed before the server change; 5
passed after it, with two controls). The blob and presence resources already answered both alike. The server change
alone left the client, `McpArtifactStore.names_at`, reading that refusal as a non-naming answer and raising
`McpServerUnreachable`, so every consumer saw an access refusal as an outage. Measured as the SEC-020 asker through
the shipped client over streamable HTTP, and through the erasure door over it
(`tests/mcp/test_f1_names_refusal_typed_through_the_client.py`): 6 failed, 1 passed (the control) before the client
change; 7 passed after it.

**Not changed by this, measured by lane `378h-names`'s sweep probe on the same fixtures:** the artifact server's
versioned-URI resolution (`ccf-artifact://{tenant}/{class}/{name}@{version}`) answers `found: true` at a present pin's
URI and `found: false` where none is filed; and a principal that can file the pin's bytes on its own client lane
through `put_artifact` reads them back as the governed shell where the pin exists and as its own bytes where it does
not. Both are open and are not addressed here.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: the names resource (`ccf-artifact-names://`) took the governed dereference only for an address the caller's tenant had filed under a class declared under `ReplayMint`; an address the caller's tenant never filed (another tenant's, nobody's, or a string that is not an address) answered `[]`. A governed address holding no record, an executed-query pin above all, therefore answered the governed read's `nonexistent` shell while an address nobody filed answered `[]`, which told an unentitled caller that the pin exists.
- After: an address the caller's tenant never filed takes the governed dereference the blob and presence resources take for it and answers its `nonexistent` shell, the same answer a governed address holding no record gets: a refusal, not an empty names list. A principal the governed dereference admits, and the caller's own client-lane filings, get their names as before. Another tenant's filing still takes no part in the decision (C8): without an own filing the answer is the same shell whatever any other tenant filed.
- Why: decision 1 (A), `D-IMPL-378` (Dave, 2026-10-09 06:21 MST): "approve the uniform “cannot verify” erasure refusal and refusal instead of an empty names list." The finding is the final panel's F1-1. Red tests: `tests/mcp/test_f1_names_present_governed_and_absent_alike.py::test_a_present_governed_pin_and_an_address_nobody_filed_answer_alike` (both parametrizations) and `::test_names_does_not_tell_the_withheld_deployment_from_the_nonexistent_one`.
- Migration: an erasure door built over the MCP-backed store now refuses an address its tenant never filed `class-unverifiable` ("cannot verify"; another tenant's address and nobody's alike, so I6 still refuses both), where it refused `address-not-in-tenant`; the door over a store handed to it in process still refuses `address-not-in-tenant`. A client that read `[]` from the names resource as "my tenant filed nothing at this address" now receives the refusal shell, as it already did for a governed address it may not read. Two pinned expectations changed with it: `tests/mcp/test_erasure_subject_match.py::test_the_mcp_backed_door_reaches_the_in_process_doors_outcome` (its `OVER_MCP` rows) and `tests/mcp/test_c8_governed_judged_per_tenant.py::test_the_owners_answers_do_not_depend_on_any_other_tenants_filing` (`owner-never-filed`).

## ccf.artifacts.protocol.ArtifactReadRefused

- Surface: ccf.artifacts.protocol.ArtifactReadRefused
- Public surface: true
- Change type: added
- Before: absent.
- After: the read side's `ArtifactWriteRefused`: an `ArtifactStoreError`, and not an `ArtifactNotFound`, raised where a store's server answered a read with its governed refusal shell. It carries the shell, parsed, as `envelope` (a `ccf.products.refusal.RefusalEnvelope`). It says the address cannot be verified through this credential, never whether anything is filed there.
- Why: decision 1 (A), `D-IMPL-378`: "Do not mislabel that access refusal “server unreachable.” Preserve a typed refusal through the MCP client."
- Migration: none.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: against the shipped artifact server with the names resource above, `names_at` raised `McpServerUnreachable` ("a non-naming answer") for a governed address the credential may not read and for an address the credential's tenant never filed, because it parsed the refusal shell as a malformed answer. `ccf.replay.provenance.filed_by_record_writer` and `require_filed_by_record_writer` over this store raised it too. A string that is not a content address returns `()` with no round trip, before and after.
- After: `names_at` raises `ccf.artifacts.protocol.ArtifactReadRefused`, carrying the server's shell, for all of those addresses: a typed refusal, never an outage and never an absence. `McpServerUnreachable` remains for an unreachable substrate and for an answer that is neither a list of names nor a refusal envelope. `filed_by_record_writer` and `require_filed_by_record_writer` over this store propagate the typed refusal: never `False`, never `RecordNotFiledByRecordWriter`.
- Why: decision 1 (A), `D-IMPL-378`: "Preserve a typed refusal through the MCP client." Red tests: `tests/mcp/test_f1_names_refusal_typed_through_the_client.py::test_names_at_raises_the_typed_refusal_for_a_query_pin_and_for_addresses_its_tenant_never_filed` (both parametrizations), `::test_record_provenance_over_the_mcp_store_propagates_the_typed_refusal` and `::test_the_erasure_door_over_the_mcp_store_refuses_class_unverifiable_because_of_the_typed_refusal` (three rows); control `::test_an_answer_that_is_neither_names_nor_a_refusal_is_still_an_outage`.
- Migration: a caller that caught `McpServerUnreachable` around `names_at` to retry it no longer receives a refusal that way; catch `ArtifactReadRefused`, or `ArtifactStoreError`, and treat it as "cannot verify". The SDK's own consumers keep their outcomes: the erasure door still refuses `class-unverifiable`, now with the typed refusal as the cause, and the in-process door is unchanged. Measured by lane `378i-names`'s consumer probe, not by a test in this tree: where the bytes of a record were served to one credential and the naming read of the same address was refused, which stands for the server's decision changing between the two reads, `ccf.replay.engine.resolve_artifact` over such a store raises the typed refusal where it raised `McpServerUnreachable`, and the governed evidence read (`ccf_runtime.authz.delivery_boundary.govern_dereference`) over the erasure-consulting composition of it answers its `nonexistent` shell where `McpServerUnreachable` escaped it.
