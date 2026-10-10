# 378-67 — A 401 from the artifact server's guard reaches the MCP client as a typed authentication refusal, and the SDK's absence readers let it through

`D-IMPL-378`, repair 2.5 (a), ruled by Dave on 2026-10-09 at 10:54 MST (sent again unchanged at 10:58), verbatim:
*"Return a typed authentication refusal for 401, preserving its distinction from authorization denial and transport
outage."* The finding is the "i" batch panel's G-NAMES-GUARD-OUTAGE (findings brief §2.5). Lane `378j-auth`. SEC-020
stays open; nothing here changes a SEC row.

**The finding, measured on test fixtures.** With the shipped `McpArtifactStore` over streamable HTTP to the shipped
artifact server, every read (`names_at`, `get`, `exists`, `resolve_uri`, `match_subject`) raised
`ccf.mcp.errors.McpServerUnreachable`, an outage, when the server's guard answered HTTP 401: no credential, a
credential that is not a bearer token, or a bearer token the server's verifier does not know. The guard answers before
any handler runs, so the server decided nothing about what was asked. SP §4.10 said a names read the server refuses
reaches the erasure door "as a typed refusal, never as an outage", which was false for the 401. Red before the change:
15 failed, 3 passed (the three are controls) across `tests/mcp/test_auth_401_typed_through_the_client.py`,
`tests/mcp/test_auth_401_never_read_as_absence.py`, `tests/http_api/test_auth_401_never_a_recorded_absence.py` and the
amended `tests/conformance/test_artifactstore.py::test_a_store_presenting_no_credential_is_refused`; 18 passed after.

**The SDK's absence readers.** The new type is an `ArtifactStoreError`, and four SDK consumers read an
`ArtifactStoreError` from a store read as absence. Measured with the store change alone: the replay resolvers answered
`ReplayUnresolvable` ("no DecisionReplayRecord is stored at ..."), the erasure consult judged an entry
`index-unsupported` and audited `erasure_index_unsupported`, and the governed evidence read answered its recorded
`nonexistent` shell, which is also what its holds answer an unauthorized caller. Each now lets the typed refusal
through by name, so the call fails as it did when the 401 arrived as an outage, with the typed refusal in its place.

**Documentation only (repair 1.6).** The docstrings of `ccf.artifacts.protocol.ArtifactReadRefused` and
`ccf.artifacts.mcp_store.McpArtifactStore.names_at` said the server gives "one answer" for a present governed address
the caller may not read, another tenant's address and an address nobody filed, "never which of those it is". That does
not hold for a governed record: its refusal can carry its own cause (`unauthorized`, `evidence-principal-mismatch`, for
a record determined for another principal), a disclosure that predates `D-IMPL-378`. They now say what is measured
(`tests/mcp/test_auth_401_typed_through_the_client.py::test_the_typed_access_refusal_carries_the_servers_own_cause_which_differs_by_address`).
No behavior changed with them, and the manifest records no docstring text.

**Not changed here.** `McpArtifactStore.put`, a write, kept reporting a credential the guard refused as
`McpServerUnreachable`. Fragment `378-71` (decision 10 (b), Dave, 2026-10-09 16:38 MST) types the write too and
renames the type `ArtifactStoreUnauthenticated`, the name this fragment uses; it was `ArtifactReadUnauthenticated`
until then, before this batch merged, and no alias is kept. The guard's other refusals — a credential without a
required scope (HTTP 403) and the tenancy guard's denials — still reach the client as `McpServerUnreachable`
(`tests/mcp/test_auth_401_typed_through_the_client.py::test_the_guards_other_refusals_are_not_the_authentication_refusal`).
`ccf.mcp.client.run_with_session`, the shared session runner, still reports every 401 as `McpServerUnreachable` to its
other consumers; only `McpArtifactStore` re-types it (its reads here, its write from `378-71`).

## ccf.artifacts.protocol.ArtifactStoreUnauthenticated

- Surface: ccf.artifacts.protocol.ArtifactStoreUnauthenticated
- Public surface: true
- Change type: added
- Before: absent.
- After: an `ArtifactStoreError` raised by every read of `ccf.artifacts.mcp_store.McpArtifactStore` where the artifact server's guard answered HTTP 401, chained from that response. It is not an `ArtifactReadRefused` (an access decision about an address, for a credential the server authenticated, carrying its shell), not an `ArtifactNotFound` (an absence) and not an `McpClientError`, so `except McpServerUnreachable` (a retry) does not catch it. It carries no envelope.
- Why: repair 2.5 (a), `D-IMPL-378` (Dave, 2026-10-09 10:54 MST): "Return a typed authentication refusal for 401, preserving its distinction from authorization denial and transport outage." Test: `tests/mcp/test_auth_401_typed_through_the_client.py::test_a_401_an_access_refusal_and_an_outage_reach_the_caller_as_three_types`.
- Migration: none.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: `get`, `exists`, `names_at`, `resolve_uri` and `match_subject` raised `McpServerUnreachable` when the server's guard answered HTTP 401 (`get` asked the presence resource a second time first, and got the same 401).
- After: each raises `ccf.artifacts.protocol.ArtifactStoreUnauthenticated`, chained from the guard's 401 response, judged on the response's status code and never on message text; `get` makes one round trip for it. `put` is unchanged here (`378-71` types it). A refusal shell still reads as `ArtifactReadRefused` on `names_at` and as absence on `get` (`ArtifactNotFound`) and `exists` (`False`), and a refused connection is still `McpServerUnreachable`.
- Why: repair 2.5 (a), `D-IMPL-378`. Red tests: `tests/mcp/test_auth_401_typed_through_the_client.py::test_names_at_raises_the_typed_authentication_refusal_when_the_guard_answers_401` (three credential shapes), `::test_every_other_read_raises_the_typed_authentication_refusal_when_the_guard_answers_401` (four reads) and `::test_a_401_an_access_refusal_and_an_outage_reach_the_caller_as_three_types`. One pinned expectation changed with it: `tests/conformance/test_artifactstore.py::test_a_store_presenting_no_credential_is_refused`, which asserted `McpServerUnreachable` for `exists` with no credential.
- Migration: a caller that caught `McpServerUnreachable` around a read and retried it no longer receives a 401 that way; retrying the same credential does not succeed. Catch `ArtifactStoreUnauthenticated` (or `ArtifactStoreError`) and treat it as a credential problem. A caller that reads every `ArtifactStoreError` from a read as absence must let this type through by name, as the SDK's own consumers below now do.

## ccf.replay.engine.resolve_artifact

- Surface: ccf.replay.engine.resolve_artifact
- Public surface: true
- Change type: behavior
- Before: over an `McpArtifactStore` whose credential the guard refused, the 401 escaped as `McpServerUnreachable`. Its Raises section did not list `ArtifactReadRefused`, which the provenance check's naming read lets through.
- After: it lets `ArtifactStoreUnauthenticated` through by name, ahead of the clause that answers `ReplayUnresolvable`, so a refused credential is never reported as a missing artifact. Raises lists both types.
- Why: repair 2.5 (a), `D-IMPL-378`. Test: `tests/mcp/test_auth_401_never_read_as_absence.py::test_replay_resolution_reports_a_401_as_the_authentication_refusal_never_as_unresolvable` (`by address`).
- Migration: none; the call fails as it did, with the typed refusal in place of the outage.

## ccf.replay.engine.resolve_artifact_at_uri

- Surface: ccf.replay.engine.resolve_artifact_at_uri
- Public surface: true
- Change type: behavior
- Before: a 401 at the naming resolution or the read escaped as `McpServerUnreachable`.
- After: `ArtifactStoreUnauthenticated` is let through by name, never `ReplayUnresolvable`.
- Why: repair 2.5 (a), `D-IMPL-378`. Test: `tests/mcp/test_auth_401_never_read_as_absence.py::test_replay_resolution_reports_a_401_as_the_authentication_refusal_never_as_unresolvable` (`by URI`).
- Migration: none.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: a 401 from the store's server, when the record was resolved or when a by-URI read's naming was checked, escaped as `McpServerUnreachable`.
- After: `ArtifactStoreUnauthenticated` is let through by name at both places. It is never answered as the `nonexistent` shell — the one absence, which is also what the holds answer an unauthorized caller — and nothing is recorded for it.
- Why: repair 2.5 (a), `D-IMPL-378`: the distinction from authorization denial. Tests: `tests/http_api/test_auth_401_never_a_recorded_absence.py::test_resolving_the_record_reports_a_401_as_the_authentication_refusal_never_as_a_recorded_absence` and `::test_the_by_uri_naming_check_reports_a_401_as_the_authentication_refusal_never_as_a_recorded_absence`.
- Migration: none; the call raises as it did, with the typed refusal in place of the outage.

## ccf.erasure.compose_erasure_consult

- Surface: ccf.erasure.compose_erasure_consult
- Public surface: true
- Change type: behavior
- Before: a 401 while an index entry's record was read through the wrapped store (at composition, or at the first read that meets an entry appended later) escaped as `McpServerUnreachable`. The same function is `ccf.erasure.store.compose_erasure_consult`.
- After: `ArtifactStoreUnauthenticated` is let through by name. The entry is never judged `index-unsupported` for it and no `erasure_index_unsupported` row is audited.
- Why: repair 2.5 (a), `D-IMPL-378`: a refused credential says nothing about the record, so an unsupported entry would be a finding about the index that a credential caused. Test: `tests/mcp/test_auth_401_never_read_as_absence.py::test_the_erasure_consult_reports_a_401_reading_a_record_as_the_authentication_refusal_never_as_unsupported`.
- Migration: none.
