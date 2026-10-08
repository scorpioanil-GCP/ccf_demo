# 377-02 — C8: the artifact server judges "governed" over the caller's own tenant's filings

`D-IMPL-376` ruling (6), the tenant-isolation lane, built red-first. The
finding as worded by the deadline-rows close panel (C8, codex B5): the MCP
artifact server's split (the blob and presence resources) and its SEC-009
names resource computed whether an address is governed evidence over every
name it was filed under in **every** tenant, before filtering to the caller's
own. Content addressing files identical bytes once, so tenant B filing the
same bytes under a `ReplayMint` class turned tenant A's own client-lane blob,
presence and names reads into the `subject-unavailable` shell; A's erasure door
over the MCP-backed store then refused A's own address `class-unverifiable`;
and A's answers told it whether some other tenant held bytes A could compute
(an existence oracle; on the names resource from the address alone). Dave's
ruling: *disclosure alone is NOT accepted for a shared bank deployment*. The
red tests are `tests/mcp/test_c8_governed_judged_per_tenant.py`.

**What the all-tenant rule protected, and why judging per tenant keeps it.**
The "safe direction" keeps governed evidence off the client lane for a
principal the governed dereference would refuse. A governed filing by the
caller's own tenant still sends every principal of that tenant through the
governed dereference, unchanged. The client lane only serves an address the
caller's own tenant filed, and a filing must present the exact bytes (the
store derives the address from them; no verb files a name without its bytes),
so it never returns to a tenant anything that tenant did not already hold.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: the blob (`ccf-artifact-blob://`) and presence (`ccf-artifact-meta://`) resources took the governed dereference when ANY tenant's name for the address had a class declared under `ReplayMint`, and the names resource (`ccf-artifact-names://`) answered the governed refusal's shell in the same case. A tenant's own client-lane filing therefore read as `subject-unavailable` once another tenant filed identical bytes under a governed class, and the names resource answered `[]` for an unknown address but the shell for an address only another tenant had filed governed.
- After: "governed" is judged over the names the caller's own tenant filed the address under, never another tenant's. For an address the caller's own tenant filed on its client lane, the blob, presence and names answers are byte-identical whether or not any other tenant filed the same bytes, under any class. For an address the caller's tenant never filed, the names resource answers `[]` whatever other tenants filed, and the blob and presence resources take the governed dereference. That read held the caller to a record's principal but not to its tenant, so another tenant's genuine replay record was not answered as a missing address in two cases: a caller whose principal id matched the record's, entitled in the record's tenant and at `full` in its own, read it; and at `full` it answered `unauthorized` where a missing address answers `nonexistent`. Both close with hold 0 of `govern_dereference` (`377-06`). Unchanged: a governed filing by the caller's own tenant still takes the governed dereference for every principal of that tenant (N4, `D-IMPL-345`); the client lane's read still appends the `D-IMPL-345` R-5 `authz_decision` event under the caller's class.
- Why: C8 (`D-IMPL-376` ruling (6)). Red tests: `tests/mcp/test_c8_governed_judged_per_tenant.py::test_another_tenants_governed_filing_does_not_change_the_owners_reads`, `::test_the_owners_answers_do_not_depend_on_any_other_tenants_filing` (both parametrizations) and `::test_the_owners_erasure_over_the_mcp_backed_store_is_not_refused_by_another_tenants_governed_filing`.
- Migration: none for a single-tenant store. Where tenants share one artifact store, an owner's reads and erasure requests no longer depend on other tenants' filings. Erasure is unchanged: it is a per-tenant fact and destroys no bytes. Measured on the file-backed door, identically before and after this change: once tenant A erases an address tenant B also filed, B's filing and the bytes stay, B's tenant-scoped reads (`ErasureConsultingStore.scoped`, which the client lane and the governed dereference's erasure consult use) still serve them, and a tenantless read (`ErasureConsultingStore.get` with no tenant; SEC-009 ruling (i) names the replay engine, `record_of` and child admission) withholds them with the reason redacted. Over the MCP-backed store A's request was refused `class-unverifiable` before this change, so that state was reachable only through a door on the file-backed store; it is now reachable through either.
