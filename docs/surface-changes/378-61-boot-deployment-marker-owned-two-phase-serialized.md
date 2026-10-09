# 378-61 (repairs 1.1 and 1.2) — SEC-020: a plain boot's deployment marker is its own, two-phase and removed on every failed boot; every plain boot that creates a store reads it, serialized; a stale marker with no store beside it is replaced and verified afresh, and where safe verification cannot be established the boot is refused

`D-IMPL-378`, ruled by Dave on 2026-10-09 at 10:54 MST. Repair 1.1: *"Remove markers created by this boot on every
failed-boot path, including failure during close. Remove only markers this boot owns. A marker left by a crash must
not imply completed verification."* Repair 1.2: *"Run the emptiness check whenever a plain boot creates a new store.
Serialize creation and verification; test competing boots. If safe verification cannot be established, refuse until
an operator resolves the stale marker."* Repair 1.2 restores the trigger of OWED-RULINGS-3 item 2A (b) as ruled at
06:21 MST (*"Run the same one emptiness read when a plain boot creates a new store"*), which fragment 378-53-b built to
a lane's narrower wording. A boot whose path holds a deployment marker of any state but no store is creating a new
store, which it can verify exactly as a fresh creation, so it is verified, not refused: the lane's proposal P-1 (B),
built for that case only at the coordinator's direction (the lane first built every stale marker as a refusal). Built
in lane `378j-boot`, on the markers of fragments 378-23 and 378-34 and the read of fragments 378-40 and 378-53-b.
**SEC-020 stays OPEN.**

**What the tests measure, on test fixtures**, in `tests/products/test_deployment_marker_owned_and_crash_safe.py`
(15 tests; the cases committed first failed before repair 1.1, and the kill inside the read, added after, failed
against `fe25536c`'s code) and `tests/products/test_deployment_marker_serialized_and_stale_refused.py` (18 tests; the
cases committed first failed before repair 1.2, and the 10 no-store cases failed before P-1 (B), where each was
refused):

- **Every failed boot removes the marker it created.** Before, a plain boot whose `boot()` failed after its marker
  existed (a store planted inside the boot and given a second name, refused at open as `WriterLeaseHeld`; its writer
  lease held elsewhere, refused at the mint as `SingleWriterViolation`; an interrupt), or whose `close()` raised while
  the read's refusal was cleaned up, left the marker, and the retry booted the planted store `"verified"` and answered
  a governed call. After, no marker remains, the retry opens the store `"unmarked"`, and a governed call over it is
  refused (`UnmarkedStoreNotPresumedFresh`). The read's refusal reaches the caller when `close()` raises, the close's
  error attached as a note.
- **Only markers this boot owns.** A marker replaced by another file, or rewritten in place, during the boot is left
  where it is when the boot fails, and is never made to read verified (`DeploymentStoreNotVerified`, `"claimed"`).
- **Crash-safe.** A marker reads `state: pending` until the boot's read has completed and `state: verified` only after
  (written to a staging file, synced, renamed over the marker, the directory synced). A boot killed (`SIGKILL`, in
  another process) after its store exists, after `boot()` or inside the read, leaves a `pending` marker beside it, and
  every later boot of the path, writer or read-only, is refused (`DeploymentStoreNotVerified`, `"pending"`); before,
  the next boot booted it `"verified"`. Beside an existing store, the single-line marker of the code before this
  change, text the SDK does not write, and a symbolic link at the marker's path are refused (`"unreadable"`).
- **The ruled trigger.** A store created where a question marker stands is read, and a plant there is refused
  (`DeploymentStoreNotEmpty`); before, no read was taken.
- **A stale marker with no store beside it is verified afresh.** A deployment marker of any state — `pending` from a
  boot killed before its store existed, `verified` with its store deleted, the single-line marker, foreign text, a
  symbolic link — with no store beside it is replaced, under the store-creation lock, by the boot's own `pending`
  marker (an atomic rename from a synced staging file, after checking it is still the file, by device and inode, that
  the boot looked at); the
  boot reads the new store once and marks it `verified`. A used store planted at the path after the boot's look and
  before the store opens is refused by that read (`DeploymentStoreNotEmpty`) and the boot's marker removed, so the
  retry opens it `"unmarked"` and a governed call over it is refused. Before (`fe25536c`), the verified case booted a
  planted store `"verified"` with no read (the small lane's P-B); before P-1 (B), every case was refused.
- **Stale, refused before anything is created.** A store-creation lock that cannot be taken (`"lock-unavailable"`) and
  a marker made between the boot's look and its exclusive create, or a stale marker replaced by another file between
  the boot's look and its replacement of it (`"claimed"`), are refused, the marker untouched.
- **Serialized.** Every plain boot holds `<resolved path>.ccf-store-creation.lock` (an exclusive `flock`, taken in path
  order, waited for with no timeout) from its look at the path to the hand-back. Two processes: a boot started while
  another is held inside its creation does not finish until that one has verified the store, then reopens it,
  reading nothing. Free-running, two processes per trial, 12 trials per test for writer+writer and writer+read-only
  pairs, on fresh paths and on paths holding a stale marker; lane probes `probe_race.py` and `probe_race_stale.py`, 100
  trials each for writer+writer, writer+read-only and read-only+read-only, on fresh and on stale paths: in every one of
  the 600 trials one boot created and read the store and the other reopened it, and on the stale paths the stale
  marker was replaced and verified. Before (`fe25536c`, 40 trials on fresh paths), the boot whose adapter created the
  store booted it `"verified"` with no read in 28 (writer+writer) and 15 (writer+read-only).
- **Severings**, each one anchor, restored from saved bytes: the narrow cleanup restored reddened the three `boot()`
  failures; the marker written `verified` at creation reddened the two crash cases and the two-phase test; the
  promotion moved before the read reddened the kill inside the read; the lock dropped reddened all five
  serialization tests, and in 100 free-running trials per pairing, on fresh paths the second boot was refused as stale
  in every one, while on stale paths the second boot replaced the first one's live marker and was refused, or made the
  first refuse, in every one; the read dropped for a replaced marker reddened all eight no-store cases (no read, and
  the plant booted `"verified"`); the identity re-check before the replacement removed (the coordinator's severing,
  vacuous against the lane's first 33 tests) reddened the test added for it, both cases.

**What it does not cover.** The marker binds to its store by path, so it does not stand against an actor who can
write into the store's directory: a marker forged beside a used store still answers, as before, and a writer outside
the SDK that replaces a marker between a boot's ownership check and its unlink, or between its re-check and its
replacement, loses its file. The re-check compares the stale marker's device and inode only: the same file rewritten
in place between the boot's look and its replacement, or deleted and created again with the same inode number (on
ext4 an immediate recreation kept it in 200 of 200 tries), is not told apart and is replaced like any stale marker;
the boot still verifies the store it opens. The read has the limits section 4.12 states. A replaced marker's text is not kept. A boot
waits for the store-creation lock with no timeout, so a boot stuck inside its creation holds the others of that path
until it is stopped. A boot over a marker beside a store that this change refuses waits for an operator; the
security how-to (section 4.12) gives the procedure.

## ccf.deployment.manifest.DeploymentStoreNotVerified

- Surface: ccf.deployment.manifest.DeploymentStoreNotVerified
- Public surface: true
- Change type: added
- Before: absent; a deployment marker vouched for its store by existing, whatever its boot did after creating it.
- After: a `ValueError` raised by `load_and_boot` and `load_config_and_boot`, for a boot not for a question, after registration and before anything is created at the path, where safe verification cannot be established. `marker` names the deployment marker, `reason` the check (`"pending"` or `"unreadable"`: a marker beside an existing store that records no completed verification; `"claimed"`; `"lock-unavailable"`), and `lock` the store-creation lock for `"lock-unavailable"`. The marker is left as it stands; the text names its path and what an operator does. A marker of any state with no store beside it is not refused: the boot replaces it and verifies a new store.
- Why: SEC-020, `D-IMPL-378` repairs 1.1 and 1.2. Red tests: `tests/products/test_deployment_marker_owned_and_crash_safe.py::test_1_1_a_boot_killed_before_its_read_completes_leaves_a_marker_no_later_boot_reads_as_verified` and `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_a_store_creation_lock_that_cannot_be_taken_refuses_the_boot_by_name`.
- Migration: a store beside a marker an earlier build wrote (one line, no state) is refused (`"unreadable"`) until an operator resolves it as section 4.12 describes; delete or copy a store together with its marker.

## ccf.deployment.DeploymentStoreNotVerified

- Surface: ccf.deployment.DeploymentStoreNotVerified
- Public surface: true
- Change type: added
- Before: absent.
- After: the package-level spelling of `ccf.deployment.manifest.DeploymentStoreNotVerified`.
- Why: SEC-020, `D-IMPL-378` repairs 1.1 and 1.2.
- Migration: none; additive.

## ccf.deployment.manifest.DeploymentStoreNotEmpty

- Surface: ccf.deployment.manifest.DeploymentStoreNotEmpty
- Public surface: true
- Change type: behavior
- Before: raised only by a plain boot that created its deployment marker in this boot.
- After: raised by every plain boot that creates its store (a path that held no store when the boot looked), whoever made a marker beside it, a store created where a question marker stands included, and a path whose stale deployment marker the boot replaced with its own included. Its text is unchanged.
- Why: SEC-020, `D-IMPL-378` repair 1.2, restoring OWED-RULINGS-3 item 2A (b) as ruled. Red tests: `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_a_plain_boot_creating_a_store_where_a_question_marker_stands_takes_the_read` and `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_b_a_store_planted_after_the_look_beside_a_stale_marker_is_refused_by_the_read_and_the_marker_removed`.
- Migration: none for a deployment that boots a new store at a fresh path and writes into it after the boot.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: a plain boot left a one-line deployment marker beside a store it created, read the store only if it had created that marker, and removed the marker only when that read refused the store; its Raises named neither `WriterLeaseHeld` nor `SingleWriterViolation`.
- After: a plain boot holds the store-creation lock of every path from its look to the hand-back (a second boot of the path waits); refuses a marker beside a store that does not show a completed verification, a marker made, or replaced by another file, outside its lock, or a lock it cannot take (`DeploymentStoreNotVerified`); replaces a stale marker of any state that stands with no store beside it by its own; creates its marker reading `pending` and makes it `verified` only after its read; reads every store it creates; and on any failure after its marker exists, closes its handle and removes the markers still its own. Its Raises adds `DeploymentStoreNotVerified`, `UngovernedClassificationAttribute`, `SingleWriterViolation`, `WriterLeaseHeld`, `WriterLeaseRequired` and the adapter's own errors. A boot for a question is unchanged: its marker stays on a refusal, and it takes no store-creation lock.
- Why: SEC-020, `D-IMPL-378` repairs 1.1 and 1.2; the Raises from the findings brief's item 1.6 (the panel's F-G2-4). Red tests: `tests/products/test_deployment_marker_owned_and_crash_safe.py::test_1_1_a_boot_that_fails_inside_boot_leaves_no_marker_and_the_retry_over_the_plant_is_refused`, `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_a_boot_that_meets_another_boot_creating_the_store_waits_for_its_verification_then_reopens` and `tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_b_a_stale_marker_with_no_store_beside_it_is_replaced_and_the_new_store_read_once_and_verified`.
- Migration: delete or copy a store together with its deployment marker. A store whose marker is deleted boots `"unmarked"` and answers no governed call, as before; a path whose store is deleted and whose marker is kept boots again, the marker replaced and a new store verified. Every plain boot, read-only included, creates `<resolved path>.ccf-store-creation.lock` beside its store, so the store's directory must let the deployment's user create that file.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine.
- Why: SEC-020, `D-IMPL-378` repairs 1.1 and 1.2.
- Migration: as `load_and_boot`.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: `store_creation` was read from the markers before the boot and before its read: a deployment marker's existence alone gave `"verified"`.
- After: `store_creation` is read when the boot hands the fabric back, after its read; `"verified"` needs a question marker or a deployment marker that records a completed verification beside every path.
- Why: SEC-020, `D-IMPL-378` repair 1.1 (*"A marker left by a crash must not imply completed verification."*).
- Migration: none.
