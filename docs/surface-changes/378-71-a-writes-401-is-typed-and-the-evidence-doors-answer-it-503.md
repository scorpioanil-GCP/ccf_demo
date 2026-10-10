# 378-71 — A write's 401 is the typed authentication refusal, one type for reads and writes, and the HTTP evidence doors answer it with a typed 503

Decision 10 (b), 2026-10-09 16:38 MST (`D-IMPL-378`; the text is Grok's recommendation, which Dave adopted), verbatim: *"(b) Type a 401 on a write, and rename the
type so it covers both."* Decision 21 (a), 2026-10-09 16:38 MST (`D-IMPL-378`; the text is Grok's recommendation, which Dave adopted), verbatim: *"(a) A typed 5xx,
so a rejected credential and an outage are not the same response."* Both are in the 16:38 MST amendment in
`docs/DECISIONS.md`, recorded on `main` @ `c470416f`, and both are built in this batch by Dave's 17:53 MST answer (1)
(a). Lane `378j-auth2`. SEC-020 stays open; nothing here changes a SEC row.

**The write (decision 10 (b)).** Measured on the base (`59f6aaaf`), with the shipped `McpArtifactStore` over streamable
HTTP to the shipped artifact server: `put` raised `ccf.mcp.errors.McpServerUnreachable`, an outage, when the server's
guard answered HTTP 401 — no credential, a credential that is not a bearer token, or a bearer token the server's
verifier does not know — as `tests/conformance/test_artifactstore.py` pinned. It now raises the typed authentication
refusal, chained from the guard's 401 response and judged on its status code, never on message text, with no outage in
its chain; the guard refused before any handler ran, so nothing was written. The guard's 403 and a refused connection
are still `McpServerUnreachable`. Red before the change: 28 failed, 5 passed (the five are controls) across the new and
amended tests below; 34 passed after, with the nonce test added in between.

**One name.** The type repair 2.5 (a) added for reads (`378-67`) was `ArtifactReadUnauthenticated`. It is renamed
`ccf.artifacts.protocol.ArtifactStoreUnauthenticated`, with no alias anywhere under `src/` or `runtime/` (nothing has
shipped), and `378-67` names it so. Its parent is still `ArtifactStoreError` and its place in the hierarchy is
unchanged: not `McpServerUnreachable`, not `ArtifactReadRefused`, not `ArtifactNotFound`, and neither the parent nor a
child of the five reference-mismatch refusals of decision 5 (a).

**The writers that catch a store failure.** A census by AST over `src/` and `runtime/` found 12 artifact-store `put` call
sites and 74 handlers that can catch the type (they name `ArtifactStoreError`, `Exception` or `BaseException`, or are
bare) or that used to catch a write's 401 (they name `McpServerUnreachable` or `McpClientError`). One `put` sits inside
a handler that changes what the typed refusal means: the peering admission gate's record write, whose
`except ArtifactStoreError` turned it into `AdmissionNotRecorded`, "a fabric that cannot reach its own substrate" —
measured with the write typed and nothing else changed. The gate now lets it through by name. Read one by one, every
other handler a write's 401 can reach re-raises it unchanged, settles its own state and re-raises it, routes it as it
routes any step failure, or reports it as an error; none reports it as an absence, a success or a retryable outage.

**The HTTP evidence doors (decision 21 (a)).** The panel's F-J2-2, confirmed by an independent verifier on
`dl-378-integ` @ `6cd6023e` and identical at `fe25536c`: `GET /replay/decisions`, `GET /replay/resolutions` and
`GET /artifact/{content_address}` answered the typed refusal and an outage with the framework's own byte-identical
`500 Internal Server Error`. They now answer the typed refusal `503`, with the shared refusal body: `error_code`
`artifact-store-unauthenticated` and one constant message, the same bytes at all three doors and for every ask, naming
no address, URI, subject or store location. A `503` and not a `500`, on the door's precedent for a fault that is the
deployment's and not the caller's (`route-handle-absent`): the credential is the one the deployment gave its store. The
outage is not the ruling's to change, and is unchanged: `McpServerUnreachable` still escapes and the framework answers
`500`. The two differ in status and in body. Nothing is recorded for either.

**Not changed.** The guard's 403, for a credential without a required scope, still reaches a read and the write as
`McpServerUnreachable`, and the tenancy guard's denial still reaches a read as `McpServerUnreachable` (decision 11 (a),
disclosed in SP §4.10) and the write as the server's decline, `ArtifactStoreError` (`378-43`;
`tests/mcp/test_mcp_store_put_decline.py::test_a_write_the_servers_authorizer_refuses_is_a_decline_too`). The HTTP doors
outside decision 21 (a)'s three, among them `POST /artifact`, are not changed: none of them catches the typed refusal.
`ccf.mcp.client.run_with_session` still reports every 401 as `McpServerUnreachable` to its other consumers; only
`McpArtifactStore` re-types it.

## ccf.artifacts.protocol.ArtifactStoreUnauthenticated

- Surface: ccf.artifacts.protocol.ArtifactStoreUnauthenticated
- Public surface: true
- Change type: behavior
- Before: named `ArtifactReadUnauthenticated` (fragment `378-67`, this batch) and raised by the reads of `McpArtifactStore` only.
- After: one name for reads and the write: also raised by `McpArtifactStore.put` where the server's guard answered HTTP 401. `ArtifactReadUnauthenticated` no longer exists and no alias is kept.
- Why: decision 10 (b), `D-IMPL-378`. Tests: `tests/mcp/test_auth_401_typed_on_a_write.py::test_one_type_names_the_authentication_refusal_for_reads_and_writes_and_the_read_only_name_is_gone` and `::test_a_reference_mismatch_refusal_is_not_the_authentication_refusal` (five rows). The read tests of repair 2.5 (a) look the type up by its new name (`tests/mcp/test_auth_401_typed_through_the_client.py::authentication_refusal`).
- Migration: none for a shipped caller: the old name never shipped. Code written against this batch names `ArtifactStoreUnauthenticated`.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: `put` raised `McpServerUnreachable` when the server's guard answered HTTP 401, as fragment `378-43` recorded ("a rejected bearer token is still `McpServerUnreachable`").
- After: `put` raises `ccf.artifacts.protocol.ArtifactStoreUnauthenticated`, chained from the guard's 401 response, with no outage in its chain, as every read does; nothing is written. A 403 and a refused connection stay `McpServerUnreachable`; a write the server declines stays `ArtifactStoreError` (`tests/mcp/test_mcp_store_put_decline.py::test_a_write_the_server_declines_is_an_artifact_store_error_not_an_outage`).
- Why: decision 10 (b), `D-IMPL-378`. Red tests: `tests/mcp/test_auth_401_typed_on_a_write.py::test_put_raises_the_typed_authentication_refusal_when_the_guard_answers_401` (three credential shapes) and `::test_at_one_write_a_401_a_403_and_a_refused_connection_reach_the_writer_as_two_types`. One pinned test changed with it: the conformance test that asserted `McpServerUnreachable` for `put`, `test_a_store_presenting_a_rejected_token_is_refused_as_an_outage`, now asserts the typed refusal and is renamed `tests/conformance/test_artifactstore.py::test_a_store_presenting_a_rejected_token_is_refused_with_the_typed_authentication_refusal`.
- Migration: a caller that caught `McpServerUnreachable` around `put` and retried no longer receives a 401 that way; retrying the same credential does not succeed. Catch `ArtifactStoreUnauthenticated` (or `ArtifactStoreError`) and treat it as a credential problem. A caller that reads every `ArtifactStoreError` from a write as a declined write or an unreachable substrate must let this type through by name, as the admission gate below now does.

## ccf.peering.admission.PeeringAdmissionGate

- Surface: ccf.peering.admission.PeeringAdmissionGate
- Public surface: true
- Change type: behavior
- Before: at the base, a 401 on the admission record's write escaped `admit` as `McpServerUnreachable`; with the write typed and nothing else changed, the record write's `except ArtifactStoreError` raised `AdmissionNotRecorded` for it.
- After: `ArtifactStoreUnauthenticated` is let through by name, ahead of that clause. Nothing is admitted, no `peering_admitted` verdict is appended, and the issuance nonce is spent, as for the other record failures. A declined write is still `AdmissionNotRecorded`, an outage still `McpServerUnreachable`, and `AdmissionRecordReferenceMismatch` is unchanged.
- Why: decision 10 (b), `D-IMPL-378`. Tests: `tests/peering/test_admission_record_write_401_is_the_typed_refusal.py::test_a_write_401_at_the_admission_record_is_the_typed_refusal_never_admission_not_recorded`, `::test_a_crossing_refused_at_its_record_for_the_credential_has_spent_its_nonce`, and its two controls.
- Migration: a caller of `admit` that handles `AdmissionNotRecorded` meets `ArtifactStoreUnauthenticated` where the store's server refused the deployment's credential.

## ccf.peering.admission.AdmissionNotRecorded

- Surface: ccf.peering.admission.AdmissionNotRecorded
- Public surface: true
- Change type: behavior
- Before: the docstring did not say what a refused store credential raises.
- After: the docstring says it is not raised for one: that write raises `ArtifactStoreUnauthenticated`, let through by name. Docstring only.
- Why: decision 10 (b), `D-IMPL-378`.
- Migration: none.

## ccf.artifacts.protocol.ArtifactReadRefused

- Surface: ccf.artifacts.protocol.ArtifactReadRefused
- Public surface: true
- Change type: behavior
- Before: the docstring distinguished it from `ArtifactReadUnauthenticated`, "a read the server's guard refused".
- After: it names `ArtifactStoreUnauthenticated`, "a call the server's guard refused". Docstring only.
- Why: decision 10 (b), `D-IMPL-378`. The Raises sections of `ccf.replay.engine.resolve_artifact`, `ccf.replay.engine.resolve_artifact_at_uri`, `ccf.erasure.compose_erasure_consult` and `ccf_runtime.authz.delivery_boundary.govern_dereference` name the renamed type the same way; their behavior is unchanged (`378-67`).
- Migration: none.

## ccf_runtime.http_api.errors.ERROR_ARTIFACT_STORE_UNAUTHENTICATED

- Surface: ccf_runtime.http_api.errors.ERROR_ARTIFACT_STORE_UNAUTHENTICATED
- Public surface: true
- Change type: added
- Before: absent.
- After: `"artifact-store-unauthenticated"`, the code the three HTTP evidence doors answer with `503` when the deployment's artifact store presented a credential its server's guard did not authenticate (HTTP 401).
- Why: decision 21 (a), `D-IMPL-378`.
- Migration: a client branching on refusal codes adds this one. It names a deployment fault: the operator renews or corrects the store's credential; the caller's own request was not at fault.

## ccf_runtime.http_api.routes.replay.build_router

- Surface: ccf_runtime.http_api.routes.replay.build_router
- Public surface: true
- Change type: behavior
- Before: `GET /replay/decisions` and `GET /replay/resolutions` let `ArtifactStoreUnauthenticated` escape, and the caller got the framework's opaque `500 Internal Server Error`, byte-identical to an outage's answer.
- After: both answer it `503` with the shared refusal body, `error_code` `artifact-store-unauthenticated` and one constant message, raised from the typed refusal. An outage is still the framework's `500`; `@latest` is still `409` (`tests/http_api/test_evidence_dereference.py::test_c13_a_moving_target_is_still_a_409`).
- Why: decision 21 (a), `D-IMPL-378`. Test: `tests/http_api/test_evidence_doors_answer_a_401_and_an_outage_apart.py::test_the_http_evidence_doors_answer_a_401_with_a_typed_503_and_an_outage_with_the_500_and_record_nothing`, which replaces the pinned `tests/http_api/test_evidence_doors_answer_a_401_and_an_outage_alike.py`.
- Migration: as for `ERROR_ARTIFACT_STORE_UNAUTHENTICATED`.

## ccf_runtime.http_api.routes.artifact.build_router

- Surface: ccf_runtime.http_api.routes.artifact.build_router
- Public surface: true
- Change type: behavior
- Before: `GET /artifact/{content_address}` let `ArtifactStoreUnauthenticated` escape, answered with the framework's opaque `500`, byte-identical to an outage's answer.
- After: it answers it `503` with `error_code` `artifact-store-unauthenticated` and the same constant message as the replay doors. An outage is still the framework's `500`. `POST /artifact` is not changed.
- Why: decision 21 (a), `D-IMPL-378`. Test: as for the replay router.
- Migration: as for `ERROR_ARTIFACT_STORE_UNAUTHENTICATED`.
