# 378-68-a — words only: which `DeploymentStoreNotVerified` refusals come before anything is created, and what a `claimed` refusal at promotion leaves

`D-IMPL-378`, lane `378j-fixup` item A: the "j" batch panel's J-CLAIMED-LEAVES-STORE, reproduced by the coordinator on
`dl-378-integ` @ `6cd6023e`. **No behavior changes.** **SEC-020 stays OPEN.**

The security how-to (section 4.12), `load_and_boot`'s Raises and fragment `378-61` said that
`DeploymentStoreNotVerified` is raised before anything is created at the path, and the how-to that it "creates nothing
at the path". That is true of the refusals a boot meets at its look: a marker beside a store that reads `pending` or
is `unreadable`, a marker that appeared, or a stale marker replaced by another file, while the boot held the
store-creation lock, and a lock that cannot be taken. It is not true of one `claimed` refusal: the marker this boot
created, replaced by another file or rewritten in place after the boot created its store and its one read found it
empty, is refused at the promotion. The boot then closes that store and leaves it beside the foreign marker (53,248
bytes on the coordinator's reproduction and on this lane's probe `probe_abc.py`), and every later boot of the path
meets that marker beside a store. It fails closed: measured with a marker whose text the SDK does not write, each
later boot, writer or read-only, is refused `unreadable` and changes nothing there, until an operator resolves it as
section 4.12's procedure says (move the store aside).

**What measures it:**
`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_claimed_refusal_at_promotion_leaves_the_store_the_boot_created_and_read_and_the_next_boot_refuses`
(both shapes: replaced by another file, rewritten in place). It pins the behavior as it stands, so it is green before
and after the words change.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: its Raises said `DeploymentStoreNotVerified` is raised "after registration and before anything is created at the path", for every reason, `claimed` included.
- After: unchanged behavior; its Raises says which refusals come at the boot's look, before the boot creates a store or a marker, and that a `claimed` refusal at the promotion comes after the boot created its store and read it empty, leaving that store beside the foreign marker, where every later boot of the path meets it.
- Why: `D-IMPL-378`, the "j" batch panel's J-CLAIMED-LEAVES-STORE (an advertised guarantee the code does not keep). Measured by `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_claimed_refusal_at_promotion_leaves_the_store_the_boot_created_and_read_and_the_next_boot_refuses`.
- Migration: none in code. An operator who meets `DeploymentStoreNotVerified` with reason `claimed` may find a store at the path that the refused boot created; resolve it as the security how-to (section 4.12) says.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: behavior
- Before: fragment `378-61` said it is raised "after registration and before anything is created at the path" for every `reason`.
- After: unchanged behavior, stated as it is: `pending`, `unreadable`, `lock-unavailable` and the `claimed` refusals at the boot's look come before the boot creates a store or a marker; the `claimed` refusal at the promotion comes after the boot created its store and read it empty, and that store stays beside the foreign marker. Its docstring is unchanged: its "before anything is created at the path" names only refusals at the boot's look.
- Why: `D-IMPL-378`, J-CLAIMED-LEAVES-STORE. Measured as for `ccf.deployment.manifest.load_and_boot`.
- Migration: none in code; as for `ccf.deployment.manifest.load_and_boot`.
