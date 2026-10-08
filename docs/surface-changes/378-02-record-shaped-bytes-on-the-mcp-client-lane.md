# 378-02 — record-shaped bytes on the MCP client lane answer as a missing address

Dave's ruling of 2026-10-07 (item 3): bytes a principal files on its own
tenant's client lane, shaped as a Decision Replay record, *"may remain ordinary
client artifacts only if their untrusted origin is explicit and consumers
cannot accept them as governed evidence. Otherwise refuse that path until
provenance is enforced."* Both conditions were measured on `7bf069cc` before
anything changed, and neither held.

- **The origin was not explicit.** The MCP artifact server
  (`runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server`)
  answered such a filing on the blob resource with the record's raw canonical
  bytes and on the presence resource with `{"found":true}`. Those are exactly
  the answers it gives for a governed record the reader may read. The names
  resource lists the stored class, but whether a class is governed is the
  deployment's `WriteKinds`, which no answer carries.
- **Consumers accepted it.** Reading through the MCP-backed reference store
  (`src/ccf/artifacts/mcp_store.py::McpArtifactStore`), the replay engine's
  read path (`src/ccf/replay/engine.py::resolve_artifact`,
  `src/ccf/replay/engine.py::resolve_artifact_at_uri`) resolved it as a record
  naming whichever principal the filer chose.
  `src/ccf/replay/engine.py::replay_refusal` verified a forged copy of a
  genuine refusal record and returned a `RefusalReplayOutcome`. Child admission
  (`src/ccf/products/child_resolver.py::GrantBoundChildResolver`) read its
  touched entities as a child's record. Only the governed read
  (`runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference`)
  refused it.

So the path is refused, at the serve. The red tests are listed under Why.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: the blob (`ccf-artifact-blob://`) and presence (`ccf-artifact-meta://`) resources served an address the caller's own tenant had filed only in classes not declared under `ReplayMint` (the client lane) as the exact stored bytes and `{"found":true}`, whatever those bytes were. Bytes shaped as a Decision Replay record, filed on the tenant's client lane by any principal of it, therefore crossed exactly as a governed record does, and every SDK reader of the MCP-backed store took them as one.
- After: on the client lane, bytes that validate as a `DecisionReplayRecord` are decided by the governed dereference instead of being served. "Validate" means `DecisionReplayRecord.model_validate_json`, the step `resolve_artifact` ends with and the parse every SDK reader of a record makes. The governed dereference serves a record only where the store's naming shows the fabric's record writer filed the address under the record's tenant, and that tenant is the caller's. That is never true of an address the caller's tenant filed only on its client lane. So blob and presence answer such bytes exactly as a missing address: byte-identical answers, behind the same recorded `nonexistent` / `evidence-absent` determination. An `McpArtifactStore` reader gets `ArtifactNotFound` from `get` and `False` from `exists`. Reading through it, `resolve_artifact`, `resolve_artifact_at_uri` and `replay_refusal` raise `ReplayUnresolvable`, and child admission's record read raises `ArtifactNotFound`. Bytes that validator refuses are served as before; measured with one key added to a record and one key removed. Unchanged: the write (the server's `put_artifact` files the bytes and answers their reference), the names resource (it lists the tenant's own filing under its stored class), the governed reads, and C8 (a tenant's blob, presence and names answers for such a filing are the same whether another tenant filed the same bytes nowhere, on its client lane, or through its record writer).
- Why: Dave's client-lane ruling, 2026-10-07 (`D-IMPL-378`). Red tests: `tests/mcp/test_forged_record_mcp.py::test_a_record_forged_on_the_tenants_own_client_lane_answers_as_a_missing_address_does` (until now a strict expected failure); `tests/mcp/test_clientlane_record_shaped.py::test_the_replay_engines_read_does_not_accept_a_record_shaped_client_lane_filing`, `::test_replay_refusal_does_not_verify_a_forged_refusal_record_from_the_client_lane`, `::test_child_admission_does_not_read_a_client_lane_record_as_the_childs_record`, `::test_record_shaped_means_the_record_validator_accepts_the_bytes_not_a_resemblance` (both parametrizations), `::test_a_tenants_answers_for_its_record_shaped_filing_do_not_depend_on_another_tenants_filing`, `::test_the_write_is_not_refused_and_the_names_resource_still_lists_the_filing` and `::test_an_erasure_door_over_the_mcp_backed_store_cannot_read_a_record_shaped_filing_to_verify_its_subject`.
- Migration: a client that files a copy of a Decision Replay record on a client lane and reads it back through the MCP artifact server now gets the missing-address answer. Read a record through a governed read instead. A copy kept as an ordinary client artifact must be in a form the record validator refuses. Each read of such bytes records a `nonexistent` refusal through the door's recorder, as a read of a missing address does. An erasure door built over the MCP-backed store reads each named address's bytes to verify its subject, so it now refuses a request naming such a filing `subject-unverifiable`; before this change it read the bytes and judged them. A door over the store in process reads the bytes directly and judges the subject. The SDK readers that read a store in process, without the artifact server in between, are not changed here: `resolve_artifact`, `replay_refusal` and child admission still accept a record-shaped client-lane filing as a record, because none of them checks who filed it.
