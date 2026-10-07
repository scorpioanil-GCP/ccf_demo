# 377-06 — C-2 and M-4: a record and a filing are held to the tenant that made them

Two findings of the independent review of the `D-IMPL-376` close-out, built
red-first.

**C-2** (confirmed by the coordinator on the candidate and on `main`). The
governed evidence read held the caller to a record's principal and re-decided
the grant under the record's tenant, but compared the capability's tenant
with the record's nowhere. Measured: a caller whose only tenant was its own
received the full bytes of another tenant's governed replay record (the
preconditions: a principal-id collision, entitlement in the record's tenant,
`full` disclosure, a known address); and, with no collision, at `full` another
tenant's record answered `unauthorized` / `evidence-principal-mismatch` where
a missing address answers `nonexistent` / `evidence-absent` — a cross-tenant
existence oracle. `D-IMPL-345` R-2 holds a caller to the record's retained
principal, tenant and product identity. The coordinator's ruling: the caller
is held to the record's deciding tenant; a record decided under any other
tenant answers exactly as a missing address does, at every disclosure level;
within the caller's own tenant nothing changes.

**M-4.** The store files a name under `"<tenant>/<class>/<name>"` and reads it
back by splitting at the first two separators, so a tenant id containing `/`
was read back as its prefix tenant — and the artifact server's split, which
decides "own" from that reading, served one tenant's client-lane bytes to
another. The ruling: refuse such a tenant at the store's write boundary, by
name.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: three holds — the record's principal, the product grant re-decided under the tenant the record was decided under, and `full` disclosure. The capability's tenant was compared with the record's nowhere, so another tenant's record crossed to a caller whose principal id matched the record's principal, entitled in the record's tenant and at `full` in its own; and at `full` another tenant's record answered `unauthorized` / `evidence-principal-mismatch` where a missing address answers `nonexistent` / `evidence-absent`.
- After: hold 0 runs first: the tenant the record was decided under (`_decided_identity`; the record's own `tenant_id` when no identity is recoverable) must equal `authorized.tenant`, or the read is refused exactly as a missing address is — `nonexistent` / `evidence-absent`, recorded through the door's recorder, at every disclosure level. Hold 2 therefore only ever re-decides a grant under the capability's own tenant. Every caller inherits it: the HTTP `/replay/decisions`, `/replay/resolutions` and `/artifact` routes and the MCP artifact server's governed reads. Unchanged within a tenant: the owner reads its own record, and another principal's genuine record answers `unauthorized` at `full` (R-4). A read-refusal record is decided under the tenant of the recorder that wrote it, so a caller of another tenant whose read was refused at that door cannot read the refusal record back.
- Why: C-2 (`D-IMPL-345` R-2; the `D-IMPL-376` close-out). Red tests: `tests/http_api/test_c2_tenant_hold_http.py::test_another_tenants_record_with_a_colliding_principal_answers_as_a_missing_address_does` and `::test_at_full_another_tenants_record_answers_as_a_missing_address_does`, and the same two in `tests/mcp/test_c2_tenant_hold_mcp.py`; each asks one address before and after another tenant files its record there and requires the same bytes.
- Migration: none where each principal reads its records through a capability for the tenant they were decided under. A deployment that read a record decided under one tenant through a capability for another now receives `nonexistent`; read it through a capability for the record's tenant.

## ccf.artifacts.protocol.authorized_write_target

- Surface: ccf.artifacts.protocol.authorized_write_target
- Public surface: true
- Change type: behavior
- Before: a capability whose tenant contained `NAME_SEGMENT_SEPARATOR` (`/`) was filed. `FileArtifactStore.names_at` split the naming key at its first two separators, so the filing was attributed to the tenant id's prefix, and the MCP artifact server served it to that tenant on its client lane.
- After: refused with `ArtifactWriteRefused` naming the tenant, after `verify_any` and before anything is canonicalized, addressed or opened, so no bytes and no name are filed. Every shipped store's `put` runs it first (`FileArtifactStore`, `McpArtifactStore`; `ErasureConsultingStore` passes its writes to the store it wraps). A tenant id is one naming segment, as a declared class already is (SEC-004).
- Why: M-4 (the `D-IMPL-376` close-out review). Red tests: `tests/artifacts/test_m4_tenant_segment_refused.py` (the addressed write, the derived write, and the artifact-server scenario end to end).
- Migration: a deployment whose tenant ids contain `/` renames them before writing artifacts. Names filed before this change are not re-read: a store that already holds a filing under such a tenant id still attributes it to the prefix.
