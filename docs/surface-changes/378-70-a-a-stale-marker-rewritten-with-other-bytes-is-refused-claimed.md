# 378-70-a (decision 17 (b)) — SEC-020: a stale deployment marker rewritten with other bytes between a boot's look and its replacement is refused `claimed` and left

`D-IMPL-378` decision 17 (b), ruled by Dave on 2026-10-09 at 16:38 MST, adopting Grok's recommendation: *"(b)
Compare the marker’s bytes."* The option he ruled, lane `378j-boot`'s P-2 (b): *"Also compare the marker's bytes
(and a symbolic link's target), read at the look, immediately before the rename. This catches every rewrite or
recreation that changes the text. A change made after the re-check remains, as does a rewrite to identical bytes,
which is harmless."* Built in lane `378j-bootlock`. **SEC-020 stays OPEN.**

Fragment `378-61` said, under "What it does not cover", that the re-check compares the stale marker's device and
inode only, so the same file rewritten in place between the boot's look and its replacement, or deleted and created
again with the same inode number, is not told apart and is replaced like any stale marker. For a change of bytes
that is no longer so. `378-61` is left as written; this fragment corrects it.

**What the tests measure, on test fixtures**, in `tests/products/test_deployment_marker_rewritten_in_place_refused.py`
(6 cases). A stale marker with no store beside it, in three states (`verified` with its store deleted, the
single-line marker of `fe25536c`, text the SDK does not write), rewritten in place with other bytes after the boot's
look, is refused `DeploymentStoreNotVerified` with reason `claimed`, the outside writer's file and bytes left, and no
store or staging file created. On `83af5650` all three were replaced and booted `"verified"`. Rewritten to identical
bytes, each is replaced and its new store read once and verified, as before. Lane probe
`probe_recreated_same_inode.py`: a stale marker deleted and created again with other bytes (a regular file) or
another target (a symbolic link), where ext4 reused the inode, is refused `claimed` and left. The severing (the
digest of a regular file's bytes never taken) reddened the three rewrite cases, and left the same-bytes cases and
the replaced-by-another-file test green.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: behavior
- Before: a stale marker with no store beside it that was rewritten in place, or deleted and created again under the same inode number, between the boot's look and its replacement kept its device and inode and was replaced; `"claimed"` caught another file put at the path only.
- After: the boot compares what stands at the marker's path immediately before the rename with what its look found: the file (device and inode), its type, and its content, a regular file's bytes or a symbolic link's target, by their SHA-256 digest. A difference refuses the boot `"claimed"` and leaves the marker. Not told apart: a change made after that comparison and before the rename; a rewrite to identical bytes, which changes nothing a boot reads; and the bytes of a marker the boot cannot read (a file it has no permission to open), whose file and type alone are compared (lane probe `probe_unreadable_stale_marker_rewritten.py`: a write-only marker rewritten in place is replaced). In each of those the boot replaces the marker and verifies the new store itself, so it serves nothing it did not read.
- Why: SEC-020, `D-IMPL-378` decision 17 (b). Red test: `tests/products/test_deployment_marker_rewritten_in_place_refused.py::test_17_b_a_stale_marker_rewritten_in_place_after_the_look_is_refused_as_claimed_and_left`.
- Migration: none in code. A boot refused `"claimed"` this way is resolved as any `"claimed"` refusal is (the security how-to, section 4.12): find what writes into the store's directory first.

## ccf.deployment.DeploymentStoreNotVerified

- Surface: ccf.deployment.DeploymentStoreNotVerified
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- After: as `ccf.deployment.manifest.DeploymentStoreNotVerified`; the package-level spelling of the same class.
- Why: SEC-020, `D-IMPL-378` decision 17 (b).
- Migration: none in code.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: a plain boot replaced a stale marker with no store beside it after checking only that it was still the same file (device and inode) its look found.
- After: it also checks the marker's type and content (bytes, or a symbolic link's target) and is refused `DeploymentStoreNotVerified` (`"claimed"`) where they changed; its Raises says so.
- Why: SEC-020, `D-IMPL-378` decision 17 (b). Measured as for `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- Migration: none in code.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine.
- Why: SEC-020, `D-IMPL-378` decision 17 (b).
- Migration: none in code.
