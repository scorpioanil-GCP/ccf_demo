# 378-70-b (decision 19 (b), question 2 (a)) — SEC-020: a store-creation lock another holds refuses a plain boot by name, at once or after the wait the deployment declares (`store_creation_lock_wait_seconds`)

`D-IMPL-378` decision 19 (b), ruled by Dave on 2026-10-09 at 16:38 MST, adopting Grok's recommendation: *"(b) Wait a
bounded time, then refuse by name. An unbounded wait is not a lock."* The option he ruled, the "j" batch panel's
F-J2-1 option (b): a bounded wait, a deployment setting with no SDK default (`D-IMPL-38`), after which the boot is
refused by name. Question 2, option (a), adopted by Dave at 17:53 MST: where a deployment sets no bound, a boot that
finds the store-creation lock held refuses at once, by name, as the writer lease does, and the bound stays an
optional deployment setting with no SDK default. Built in lane `378j-bootlock`. **SEC-020 stays OPEN.**

Fragment `378-61` said that a plain boot holds the store-creation lock "waited for with no timeout"; that a boot
started while another is held inside its creation "does not finish until that one has verified the store, then
reopens it"; in its `load_and_boot` entry, "(a second boot of the path waits)"; and under "What it does not cover",
"A boot waits for the store-creation lock with no timeout, so a boot stuck inside its creation holds the others of
that path until it is stopped." Fragments `378-68-d` and `378-68-e` describe docstrings that said a boot finding
another creating the store waits for it. Without a declared wait none of that holds now: the boot is refused at once.
With one declared, it waits that long at most. `378-61`, `378-68-d` and `378-68-e` are left as written; this fragment
corrects them.

**What the tests measure, on test fixtures**, in `tests/products/test_deployment_store_creation_lock_bounded.py` (16
cases; 14 of them red on `556cdce`, before the fix, and the other 2 a control green before and after). With the lock
held by another holder and no wait declared, a plain boot in another process, writer and read-only, is refused at
once. On `83af5650` the same boot was still inside `load_and_boot`, refusing nothing, when a 30-second watch ended.
With a 2-second wait declared, the boot waits at least that long and is then refused the same way. With 120 seconds
declared and a holder that lets go after 2 seconds, the boot returns only after the release and creates and verifies
the store. The config door carries the setting into the manifest it derives and honors it. The setting is typed and
the SDK gives it no value. Two plain boots racing with no wait declared never serve a store they did not verify: the
other boot reopens the store, or is refused as a second writer or `lock-held`, never as stale. The three tests of
`tests/products/test_deployment_marker_serialized_and_stale_refused.py` that measured two boots serializing now
declare a 120-second wait, their assertions unchanged. The severing (the lock taken with a blocking `flock` again)
reddened all five refusal cases.

## ccf.controlplane.artifacts.DeploymentManifest

- Surface: ccf.controlplane.artifacts.DeploymentManifest
- Public surface: true
- Change type: reshaped
- Before: no field bounded a plain boot's wait for the store-creation lock; a boot that found it held waited with no timeout.
- After: an optional `store_creation_lock_wait_seconds`, a positive whole number of seconds (strict: zero, a negative number, a fraction, a boolean and a quoted number are refused at parse), hash-transparent at `None`. `None`, the default and what an absent field parses to, declares no wait. The SDK supplies no value and no upper limit, so a deployment can declare a wait long enough to act like none; the seconds are the deployment's own.
- Why: SEC-020, `D-IMPL-378` decision 19 (b) with question 2 (a). Red test: `tests/products/test_deployment_store_creation_lock_bounded.py::test_19_b_the_wait_is_absent_unless_declared_and_kept_as_declared`.
- Migration: none for a manifest that declares no wait: it keeps its content address, and its boots are refused at once where they used to wait. A deployment whose boots of one store can overlap (several workers starting together, say) declares a wait, or boots again after a `"lock-held"` refusal.

## ccf.deployment.DeploymentManifest

- Surface: ccf.deployment.DeploymentManifest
- Public surface: true
- Change type: reshaped
- Before: as `ccf.controlplane.artifacts.DeploymentManifest`.
- After: as `ccf.controlplane.artifacts.DeploymentManifest`; the package-level spelling of the same class.
- Why: SEC-020, `D-IMPL-378` decision 19 (b).
- Migration: as `ccf.controlplane.artifacts.DeploymentManifest`.

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: reshaped
- Before: no `store_creation_lock_wait_seconds`; the key was refused as unrecognized.
- After: an optional `store_creation_lock_wait_seconds`, the field, type, bounds and default of `DeploymentManifest`'s twin, hash-transparent at `None`.
- Why: SEC-020, `D-IMPL-378` decision 19 (b); `DeploymentConfig`'s deployment-level fields mirror `DeploymentManifest`'s, so the two documents cannot drift.
- Migration: none for a config that declares no wait; it keeps its content address.

## ccf.deployment.config.derive_deployment

- Surface: ccf.deployment.config.derive_deployment
- Public surface: true
- Change type: behavior
- Before: the derived manifest carried `tenant_id`, `backend`, `backend_secrets` and `survivor_cap` from the config's deployment-level fields.
- After: it also carries `store_creation_lock_wait_seconds`, unchanged; a config that declares none derives a manifest that declares none.
- Why: SEC-020, `D-IMPL-378` decision 19 (b). Measured by `tests/products/test_deployment_store_creation_lock_bounded.py::test_19_b_the_config_door_carries_the_declared_wait_into_its_manifest_and_honors_it`.
- Migration: none.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: reshaped
- Before: `reason` was one of `"pending"`, `"unreadable"`, `"claimed"`, `"lock-unavailable"`; a held store-creation lock refused nothing, and the boot waited for it with no timeout.
- After: `reason` may also be `"lock-held"`: another holds the store-creation lock (a boot creating or verifying the store, in this process or another, or any process that locked the file). Refused at once where the deployment declares no `store_creation_lock_wait_seconds`, and once that many seconds have passed with the lock still held where it declares them, counted from the boot's first lock, covering all its locks together. `lock` names the lock's path, and the text names it and says whether a wait was declared. Nothing is created at the path and the marker is not touched; the text does not say an operator must act, since a later boot proceeds once the holder lets go. The refusal does not name the holder. A waiting boot tries the lock again every 0.01 seconds, so a release is noticed at most that much later.
- Why: SEC-020, `D-IMPL-378` decision 19 (b) with question 2 (a). Red tests: `tests/products/test_deployment_store_creation_lock_bounded.py::test_19_b_a_boot_that_finds_the_lock_held_and_no_wait_declared_is_refused_at_once_by_name` and `tests/products/test_deployment_store_creation_lock_bounded.py::test_19_b_a_boot_with_a_declared_wait_waits_that_long_for_a_held_lock_then_is_refused_by_name`.
- Migration: a caller that branches on `reason` meets a fifth value. For `"lock-held"`, boot again once the holder lets go; if `fuser` or `lsof` on the lock shows a process that has stopped or hung, end it. Never remove a lock file a process holds: the next boot would create a new one and run beside that holder (lane probe `probe_lock_file_removed_while_held.py`; the security how-to, section 4.12, step 4).

## ccf.deployment.DeploymentStoreNotVerified

- Surface: ccf.deployment.DeploymentStoreNotVerified
- Public surface: true
- Change type: reshaped
- Before: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- After: as `ccf.deployment.manifest.DeploymentStoreNotVerified`; the package-level spelling of the same class.
- Why: SEC-020, `D-IMPL-378` decision 19 (b).
- Migration: as `ccf.deployment.manifest.DeploymentStoreNotVerified`.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: a plain boot that found the store-creation lock held waited for it with no timeout (fragment `378-61`: "a second boot of the path waits").
- After: it is refused `DeploymentStoreNotVerified` (`"lock-held"`) at once, or, where the manifest declares `store_creation_lock_wait_seconds`, once that many seconds have passed with the lock still held; a boot that gets the lock within them proceeds as before and reopens a store another boot created and verified. Its Raises says so.
- Why: SEC-020, `D-IMPL-378` decision 19 (b) with question 2 (a). Measured as for `ccf.deployment.manifest.DeploymentStoreNotVerified`, and by `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_a_boot_that_meets_another_boot_creating_the_store_waits_for_its_verification_then_reopens` with a wait declared.
- Migration: as `ccf.controlplane.artifacts.DeploymentManifest`.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`, the wait read from `ccf_config.yaml`'s `store_creation_lock_wait_seconds` through the manifest the door derives; both doors share one boot spine.
- Why: SEC-020, `D-IMPL-378` decision 19 (b). Measured by `tests/products/test_deployment_store_creation_lock_bounded.py::test_19_b_the_config_door_carries_the_declared_wait_into_its_manifest_and_honors_it`.
- Migration: as `ccf.controlplane.artifacts.DeploymentConfig`.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: its description of `store_creation` said that a boot that finds another creating the store waits for it.
- After: unchanged behavior of the field; its description says that such a boot is refused by name (`"lock-held"`) at once, or once the deployment's declared wait has passed, and that a boot that gets the lock after another boot created and verified the store reopens it.
- Why: SEC-020, `D-IMPL-378` decision 19 (b).
- Migration: none.

## ccf.deployment.manifest.DeploymentStoreNotEmpty

- Surface: ccf.deployment.manifest.DeploymentStoreNotEmpty
- Public surface: true
- Change type: behavior
- Before: its docstring said that the read is taken by every plain boot whose path held no store when it looked, while the boot holds the store-creation lock.
- After: unchanged behavior; its docstring says the read is taken once the adapter has opened the store the boot creates, and that a boot whose store's directory does not exist takes no lock and, on the SDK's SQLite adapter, no read either, the adapter refusing it first with nothing created there.
- Why: `D-IMPL-378`, the fix-up follow-up's report (section 5), left for this lane. Measured by `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_plain_boot_whose_store_directory_does_not_exist_takes_no_lock_and_creates_nothing`.
- Migration: none.

## ccf.deployment-manifest

- Surface: ccf.deployment-manifest
- Public surface: false
- Change type: reshaped
- Before: no `store_creation_lock_wait_seconds` key; a manifest naming it was refused at parse.
- After: an optional `store_creation_lock_wait_seconds`, an integer greater than zero; the committed `docs/schemas/ccf.deployment-manifest.json` carries it, regenerated.
- Why: as for `ccf.controlplane.artifacts.DeploymentManifest`.
- Migration: as for `ccf.controlplane.artifacts.DeploymentManifest`.

## ccf.deployment-config

- Surface: ccf.deployment-config
- Public surface: false
- Change type: reshaped
- Before: no `store_creation_lock_wait_seconds` key; a config naming it was refused as an unrecognized section.
- After: an optional `store_creation_lock_wait_seconds`, an integer greater than zero; the committed `docs/schemas/ccf.deployment-config.json` carries it, regenerated.
- Why: as for `ccf.controlplane.artifacts.DeploymentConfig`.
- Migration: as for `ccf.controlplane.artifacts.DeploymentConfig`.
