# 378-73-b — Write-then-read: a tenant's own client-lane filing decides its client-lane reads (design 1.2, F1-1c)

`D-IMPL-378`. Dave, 2026-10-09 06:06 MST, confirmed 06:21: *"A; fix F1-1b and F1-1c now; X17(a)."* His choices on the
design, 2026-10-09 10:54 MST, design 1.2, verbatim: *"Q1 (A), a tenant’s own filing decides its own reads. Q2, the A6
names rule. Q3 (a), build it with 1.3. Q4 (a), disclose the write-timing difference. Do not change the storage
layer."* Built in lane `lane-s020` with designs 1.1 and 1.3. SEC-020 stays open.

**The finding, measured on test fixtures.** The asker files a query pin's canonical bytes on its own client lane
(`put_artifact`) and reads them back. Under N4 as C8's fragment `377-02` records it ("a governed filing by the caller's
own tenant still takes the governed dereference for every principal of that tenant"), the read answered the governed
shell where the record writer had filed the pin and the asker's own bytes where it had not. The closing test's
write-then-read cells, the asker's three and a second principal's three, were 18 of the 21 red cells on `633c4e53`;
after the change all are green.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: blob and presence took the governed dereference wherever the caller's tenant had filed the address under any `ReplayMint` class (N4), and names did the same (decision 1 (A): `governed or not own`).
- After: blob and presence serve the client lane wherever the caller's tenant filed the address under a class not declared under `ReplayMint`; a governed filing of the same bytes by that tenant no longer overrides it. Record-shaped bytes and bytes not at their address still go to the governed read, as do addresses the tenant filed only as governed evidence and addresses it never filed. Names follows rule A6: the tenant's client-lane names; for record-shaped bytes or bytes not at their address the governed decision decides whether the governed names are added (a record's owner keeps its provenance) and its refusal never replaces the client-lane names. The names resource now reads the stored bytes internally for that test; they never leave the server. `put` and the storage layer are unchanged.
- Why: F1-1c, X17 (a). Red tests: the closure gate's write-then-read cells; `tests/mcp/test_f1_1c_write_then_read.py` (3 tests, red on `633c4e53`).
- Migration: none for data or configuration. Any principal of a tenant reads back what another principal of it filed on the client lane, bytes that are also governed evidence included (C8's tenant-shared client lane, kept). Not closed, and disclosed: the write timing of content-addressed deduplication (`FileArtifactStore.put` skips the file write when the bytes are already stored, by any filing); measured by the design seat at the store level, median 447.7 µs already stored against 455.7 µs new, p10–p90 roughly 160–3,000 µs for both; not measured over the wire.
