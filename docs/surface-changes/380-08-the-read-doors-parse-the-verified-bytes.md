# 380-08 (D-IMPL-380, 2026-10-11 00:28 GO) — the Control Plane registry's read doors parse the write-verified bytes and prove the result against the stored reconstruction

`D-IMPL-380`, Dave, 2026-10-10 21:00 MST: *"The isolation ruling was a fresh object the reader cannot
use to rewrite the registry. It was not a second full render on every read. Serving the bytes the
write door already rendered, rebuilt, and verified keeps that property, if the read door parses
those bytes through the artifact's own type and a failed parse refuses. Do not return a cached
object."* And 2026-10-11 00:15: *"A successful parse is insufficient."* *"Preserve type and value
verification after parsing."* *"Keep the reconstruction and its verified bytes consistent under the
same key/version. An existing artifact with missing or inconsistent byte storage is an integrity
failure, not 'artifact missing.' Failed writes must publish neither half."* Built in lane
`380h-verified-bytes`, red tests first. **SEC-020 stays OPEN**; no SEC row closes.

**Why.** The sixth-round read doors reconstructed the stored artifact on every read — two canonical
renders per read — and the invalidation sink reads a tenant's whole, growing
`EntityInvalidationRegister` on every supersession (`D-IMPL-382`). Measured at `533294f2`: the perf
suites 3.1–3.5× slower than the baseline, the hosted smoke ladders over their 300 s cap, and on a
10,000-entry register one read at 75 ms against a 26 ms render. The read now parses the bytes the
write door verified and checks the parse against the protected reconstruction without rendering:
17.8 ms on that register, 4.2× cheaper, and the per-supersession cost falls from ~6.6 renders of
the register to ~3.3 (the remainder is the write-side rebuild, `D-IMPL-382`).

**What the tests measure** (`tests/controlplane/test_registry_serves_verified_bytes.py`, 10 cases):
a validator that behaves at registration and returns changed content on retrieval without raising
is refused by name at `peek`, `resolve` and `resolve_latest`; a parse returning a different value is
refused by the value check with no render; a parse returning a subclass is refused by the type
check; a parse handing back the stored reconstruction itself is refused; bytes that do not hash to
their version, or a record without its bytes, are `RegistryIntegrityFailure` and never
`ControlPlaneMissing`, audited `resolved=False`; a refused write leaves no record; what a read
serves renders to the stored bytes and hashes to the version; and — a cost assertion only — a read
door does not render. The ten sixth-round isolation tests are unchanged.

## ccf.controlplane.registry.RegistryIntegrityFailure

- Surface: ccf.controlplane.registry.RegistryIntegrityFailure
- Public surface: true
- Change type: added
- Before: no such failure existed; the registry held only the reconstruction, and a read reconstructed it.
- After: a `RuntimeError` raised by `peek`, `resolve` and `resolve_latest` when the record under an existing `(key, version)` is missing its verified canonical bytes or those bytes do not hash to the version, carrying `key`, `version`, `door` and `reason`. Distinct from `ControlPlaneMissing` (nothing registered) and from `ArtifactIsolationRefused` (the parse did not prove the artifact). `resolve` and `resolve_latest` record it as a resolve that did not resolve.
- Why: Dave, 00:15: *"An existing artifact with missing or inconsistent byte storage is an integrity failure, not 'artifact missing.'"*
- Migration: none for a caller of the public doors; the record is written whole by the write doors and a consistent registry never raises it.

## ccf.controlplane.registry.ControlPlaneRegistry

- Surface: ccf.controlplane.registry.ControlPlaneRegistry
- Public surface: true
- Change type: behavior
- Before: each read door rendered the stored reconstruction to canonical bytes, parsed and rebuilt it, rendered the rebuild again to compare, and returned the rebuild (two renders per read).
- After: each write door renders the artifact once, keeps the verified canonical bytes beside the verified reconstruction in one record, and the version is the hash of those bytes; each read door checks the record's integrity, parses the bytes through the artifact's own type, and verifies the parse's type, value (equality against the stored reconstruction, no render) and identity before returning it. Every read is still a fresh object sharing nothing with the registry or with any earlier read; nothing is cached; a failed parse or a failed check refuses by name and never reports the artifact missing.
- Why: `D-IMPL-380` 21:00 / 00:15 / 00:28, above. The guarantees are unchanged; the second render is gone.
- Migration: none. A caller that never reached the registry's internals sees the same objects, the same versions and the same refusals; `ArtifactIsolationRefused.reason` on a read now names the parse ("the parse is not equal to the stored reconstruction") rather than the reconstruction.
