# 378-70-c (P-1 (b)) — SEC-020: a stale deployment marker with no store beside it that the boot cannot read is refused `unreadable` and left, not replaced

P-1 (b), ruled by Dave on 2026-10-09 at 20:13 MST: *"1. b and 2. a"* (recorded on `main` @ `7fbc2474`, the questions put to him from lane `378j-bootlock`'s final report §7). The
option's text, from that report: *"Refuse it `unreadable` before replacing it."* It narrows, for this case only, the
reading Dave confirmed at 16:38 MST by adopting Grok's text, *"A marker with no store is re-verified."* Built in lane
`378j-bootlock`. **SEC-020 stays OPEN.**

Fragment `378-70-a` said, of the comparison decision 17 (b) added, that the bytes of a marker the boot cannot read are
not told apart and that the boot replaces such a marker; fragment `378-61` said that a deployment marker of any state
with no store beside it is replaced and verified afresh. Neither holds for a marker the boot cannot read: it is now
refused. `378-61` and `378-70-a` are left as written; this fragment corrects them.

**What the tests measure, on test fixtures**, in `tests/products/test_deployment_marker_rewritten_in_place_refused.py`
(4 new cases, all red on `b31b6f1`, before the fix). A stale marker with no store beside it, made write-only so that
the boot's look finds it and cannot read it, in two states (`verified` with its store deleted, text the SDK does not
write), left untouched or rewritten in place after the look, is refused `DeploymentStoreNotVerified` with reason
`unreadable` and left exactly as it stood (the same file, mode and bytes), with no store and no staging file created.
Before the fix each was replaced and its boot booted `"verified"`. A marker the boot can read is still replaced and
verified afresh, and same-length rewrites and retargeted links are still refused `claimed`. The severing (the new
check made never true) reddened the four cases and nothing else.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: behavior
- Before: a stale marker with no store beside it that the boot could not read was replaced, its file and type alone compared, and the boot booted `"verified"`; `"unreadable"` with no store beside the marker meant only a directory at the marker's path.
- After: such a marker, a regular file or a symbolic link whose content the boot cannot read, refuses the boot `"unreadable"` before anything is created at the path, and is left as it stands. Anything else that holds no bytes to compare (a FIFO, a socket, a device) is replaced as before. The refusal's text is unchanged; it already names "not a regular file this process can read".
- Why: SEC-020, `D-IMPL-378` P-1 (b), ruled by Dave on 2026-10-09 at 20:13 MST: "1. b and 2. a". Red test: `tests/products/test_deployment_marker_rewritten_in_place_refused.py::test_p1_b_a_stale_marker_the_boot_cannot_read_is_refused_unreadable_and_left`.
- Migration: a deployment whose stale markers its user cannot read is refused until an operator removes the marker or makes it readable (the security how-to, section 4.12, step 2).

## ccf.deployment.DeploymentStoreNotVerified

- Surface: ccf.deployment.DeploymentStoreNotVerified
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- After: as `ccf.deployment.manifest.DeploymentStoreNotVerified`; the package-level spelling of the same class.
- Why: SEC-020, `D-IMPL-378` P-1 (b).
- Migration: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: a plain boot replaced a stale marker with no store beside it whatever it could read of it.
- After: it is refused `DeploymentStoreNotVerified` (`"unreadable"`) where it cannot read that marker; a marker it can read is replaced and its new store verified, as before. Its Raises says so.
- Why: SEC-020, `D-IMPL-378` P-1 (b). Measured as for `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- Migration: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine.
- Why: SEC-020, `D-IMPL-378` P-1 (b).
- Migration: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: its description of `store_creation` said that a boot meeting a deployment marker of any state with no store beside it replaces it and verifies the new store.
- After: unchanged behavior of the field; its description says that holds for a marker the boot can read, and that one it cannot read refuses the boot (`"unreadable"`).
- Why: SEC-020, `D-IMPL-378` P-1 (b).
- Migration: none.

## ccf.deployment.manifest.DeploymentStoreNotEmpty

- Surface: ccf.deployment.manifest.DeploymentStoreNotEmpty
- Public surface: true
- Change type: behavior
- Before: its docstring said a boot whose path carries a deployment marker of any state with no store beside it replaces that marker and takes the read.
- After: unchanged behavior; its docstring says so of a marker the boot can read.
- Why: SEC-020, `D-IMPL-378` P-1 (b).
- Migration: none.
