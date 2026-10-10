# 378-68-d — words only: `DeploymentStoreNotVerified` and `BootedFabric` say that only a plain boot whose store's directory exists holds the store-creation lock

`D-IMPL-378`, lane `378j-fixup` follow-up Q: the "j" batch panel's J-NODIR-NOLOCK, which item C corrected in the
security how-to (section 4.12). **No behavior changes.** **SEC-020 stays OPEN.**

`DeploymentStoreNotVerified`'s docstring, and `BootedFabric`'s description of `store_creation`, said that a plain boot
holds the store-creation lock of every path naming its store, from its look at the path to the hand-back. That is true
of every path whose directory exists. A path whose directory does not exist takes no lock and is left to the adapter,
and the SDK's SQLite adapter refuses that boot with SQLite's own error (`sqlite3.OperationalError`), not with
`DeploymentStoreNotVerified`, having created nothing there, not even the directory, so there is nothing to serialize.
Both docstrings now say so and name the test that measures it.

**What measures it:**
`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_plain_boot_whose_store_directory_does_not_exist_takes_no_lock_and_creates_nothing`,
a writer boot and a read-only boot. It pins the behavior as it stands, so it is green before and after the words
change.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: behavior
- Before: its docstring said that a plain boot holds the store-creation lock of every path naming its store, from its look at the path through the hand-back.
- After: unchanged behavior; its docstring says that holds for every path whose directory exists, and that a path whose directory does not exist takes no lock and is left to the adapter: the SDK's SQLite adapter refuses that boot with `sqlite3.OperationalError`, not this refusal, having created nothing there, not even the directory.
- Why: `D-IMPL-378`, the "j" batch panel's J-NODIR-NOLOCK (an advertised lock the code does not take). Measured by `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_plain_boot_whose_store_directory_does_not_exist_takes_no_lock_and_creates_nothing`.
- Migration: none.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: its description of `store_creation` said that a plain boot holds the store-creation lock of every path from its look at the path to the hand-back.
- After: unchanged behavior; it says that holds for every path whose directory exists, and that a path whose directory does not exist takes no lock and is left to the adapter, which on the SDK's SQLite adapter refuses the boot.
- Why: `D-IMPL-378`, J-NODIR-NOLOCK. Measured as for `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- Migration: none.
