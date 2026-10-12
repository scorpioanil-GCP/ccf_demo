# 378-73-a — The MCP versioned-URI resolution decides a governed class through the governed read (design 1.1, F1-1b)

`D-IMPL-378`. Dave, 2026-10-09 06:06 MST, confirmed 06:21: *"A; fix F1-1b and F1-1c now; X17(a)."* His choices on the
design, 2026-10-09 10:54 MST, design 1.1, verbatim: *"Q1 (a), a refusal shell and a typed client error. Q2 (a), keep
the class/name permission. Q3, a two-parent error class is acceptable. One base fails a pinned test, and the two
parents name two different failures."* Built in lane `lane-s020` (SEC-020 package 4, with designs 1.2 and 1.3).
SEC-020 stays open; nothing here changes a SEC row.

**The finding, measured on test fixtures.** The MCP artifact server's resolution resource
(`ccf-artifact://{tenant}/{class}/{name}@{version}`) answered `found: true` where a name was filed and `found: false`
where it was not, from the naming index alone, with no governed decision (the final panel's K20). For a class the
substrate declares under `ReplayMint`, a query pin above all, that told a deployment that filed the pin from one that
did not: the closing test's X17 (a) resolution cells were red (`tests/products/test_sec020_combined_proof.py::test_a_pin_filed_in_one_deployment_reads_alike_in_both`,
3 of the 21 red cells on `633c4e53`). It also resolved a record its tenant had sealed (Q12) and a record of another
principal. After the change those cells are green, and so is every cell of the module (2232 passed, 0 failed), with
the reported limitation blocks unchanged (D1 (a) 30/88, P6 24/44, E2 (ii) 82/82).

## ccf_runtime.authz.delivery_boundary.govern_resolution

- Surface: ccf_runtime.authz.delivery_boundary.govern_resolution
- Public surface: true
- Change type: added
- Before: absent.
- After: one versioned-URI resolution of governed evidence, decided by `govern_dereference`'s own hold chain (now the private `_govern_verified`, entered by both after their capability check). It verifies an `Authorized[ArtifactRead]` bound to `"<class>/<name>"` first, rebuilds the URI from the capability's verified tenant, and returns the evidence (its address) to a principal the chain admits, or the one recorded, disclosed shell to everyone else. `govern_dereference` keeps its signature and behavior.
- Why: design 1.1, Q2 (a): keep `D-IMPL-353` §1.2's class/name vocabulary for the resolution resource's capability. Red tests: `tests/mcp/test_f1_1b_resolution_decides_governed_classes.py` (6 of its 7 tests red on `633c4e53`; the client-lane control is green before and after).
- Migration: none.

## ccf.artifacts.protocol.ArtifactResolutionRefused

- Surface: ccf.artifacts.protocol.ArtifactResolutionRefused
- Public surface: true
- Change type: added
- Before: absent.
- After: an `ArtifactUriUnresolvable` and an `ArtifactNotFound` (two parents, as ruled) that `McpArtifactStore.resolve_uri` raises where the server answered a governed resolution with its refusal shell; it carries the shell, parsed, as `envelope`. Never `McpServerUnreachable`.
- Why: design 1.1, Q1 (a) and Q3. With `ArtifactUriUnresolvable` as the only base, `tests/replay/test_record_content_address_integrity.py::test_child_admission_over_the_mcp_backed_store_reads_the_genuine_record_and_not_altered_bytes` fails (measured by the design seat).
- Migration: none; a caller that handles `ArtifactUriUnresolvable` or `ArtifactNotFound` handles it unchanged.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: the resolution resource verified no capability in its body and answered `found: true`/`found: false` from the naming index for every class.
- After: the body verifies its `"<class>/<name>"` capability first. For a class the substrate declares under `ReplayMint` the resolution is decided by `govern_resolution`: an admitted principal gets `found: true` and the address as before; everyone else gets the governed shell, the same for a present pin, an admitted child contract, a child question, a sealed record, another principal's record and a URI nobody filed. Every other class resolves exactly as before, FW-6's `found: false` for an erased address included.
- Why: F1-1b, X17 (a). Red tests: the closure gate's three `mcp-resolution` cells and `tests/mcp/test_f1_1b_resolution_decides_governed_classes.py`.
- Migration: another principal of a tenant can no longer resolve a governed record it may not read, and no principal resolves a query pin, an admitted child contract or a child question over MCP; replay over the MCP-backed store already could not read those bytes.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: `resolve_uri` read a refusal shell as a non-resolution answer and raised `McpServerUnreachable`.
- After: `resolve_uri` raises `ArtifactResolutionRefused`, carrying the shell, for the server's governed refusal; `McpServerUnreachable` remains for an unreachable substrate and for an answer that is neither a resolution nor a refusal envelope.
- Why: design 1.1, Q1 (a): "a typed client error".
- Migration: none for callers that catch `ArtifactUriUnresolvable` or `ArtifactNotFound`.
