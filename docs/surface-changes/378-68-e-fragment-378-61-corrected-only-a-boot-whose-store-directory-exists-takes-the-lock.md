# 378-68-e — words only: fragment `378-61` corrected — only a plain boot whose store's directory exists holds, or creates, the store-creation lock

`D-IMPL-378`, lane `378j-fixup` follow-up R: the "j" batch panel's J-NODIR-NOLOCK, in fragment `378-61`. **No behavior
changes.** **SEC-020 stays OPEN.**

Fragment `378-61` said, in its "Serialized." paragraph, "Every plain boot holds `<resolved path>.ccf-store-creation.lock`
(...) from its look at the path to the hand-back"; in its `load_and_boot` entry, that "a plain boot holds the
store-creation lock of every path from its look to the hand-back"; and in that entry's Migration, "Every plain boot,
read-only included, creates `<resolved path>.ccf-store-creation.lock` beside its store". Each is true of every path
whose directory exists. A path whose directory does not exist takes no lock, and the boot creates nothing there, not
even the directory: it leaves the path to the adapter, and the SDK's SQLite adapter refuses the boot with SQLite's own
error (`sqlite3.OperationalError`), so there is nothing to serialize. `378-61` is left as written; this fragment
corrects it, as `378-68-a` corrected that fragment's `DeploymentStoreNotVerified` entry.

**What measures it:**
`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_plain_boot_whose_store_directory_does_not_exist_takes_no_lock_and_creates_nothing`,
a writer boot and a read-only boot. It pins the behavior as it stands, so it is green before and after the words
change.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: fragment `378-61` said that a plain boot holds the store-creation lock of every path from its look to the hand-back, and, in its Migration, that every plain boot, read-only included, creates `<resolved path>.ccf-store-creation.lock` beside its store.
- After: unchanged behavior, stated as it is: what `378-61` says of the store-creation lock holds for every path whose directory exists; a path whose directory does not exist takes no lock and has nothing created there, not even the directory, and the SDK's SQLite adapter refuses the boot with `sqlite3.OperationalError`. The function's docstring is unchanged: it makes neither statement.
- Why: `D-IMPL-378`, the "j" batch panel's J-NODIR-NOLOCK. Measured by `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_plain_boot_whose_store_directory_does_not_exist_takes_no_lock_and_creates_nothing`.
- Migration: none in code. `378-61`'s requirement, that the store's directory let the deployment's user create the lock file, applies where that directory exists.
