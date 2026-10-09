# 378-53-b (OWED-RULINGS-3 2A (b)) — SEC-020: a plain boot that creates its store reads it once and refuses one holding anything

`D-IMPL-378`, ruled by Dave on 2026-10-09 at 06:21 MST: *"2A(b), 2B(a)"*. Option 2A (b), from lane `378f-p4e`'s
proposal A: *"A plain boot that created its deployment marker in this boot is creating a new store, so it must
also find it empty. One read per store creation, no Protocol change. Reopening an existing store is unaffected.
This would refuse L4's plant the way L6's is refused now."* 2B (a) keeps writes from outside the SDK disclosed;
the security how-to's section 4.12 still states them, unchanged. Built in lane `378i-small`, on the markers of
fragments 378-23 and 378-34 and the read of fragment 378-40. **SEC-020 stays OPEN.**

**What the tests measure, on test fixtures**, in
`tests/products/test_plain_boot_creating_its_store_finds_it_empty.py` (4 tests; 3 failed before the change):

- **L4.** Before the change, a used question store written at a plain boot's path after the boot left its
  deployment marker there, and before the adapter opened it, was booted with `store_creation` `"verified"`,
  holding 3 entities, and a later governed call over it was answered; through the config door the same plant was
  booted holding 1. After, both doors raise `DeploymentStoreNotEmpty`, leave no marker beside the store, and a
  later plain boot of the path opens it `"unmarked"`, so a governed call over it is refused
  (`UnmarkedStoreNotPresumedFresh`).
- **One read per store creation.** The boot that creates the store reads it once, through the governed reader
  at the latest instant a timestamp can name; a boot that reopens it reads nothing there. Before the change the
  creating boot read it 0 times.
- **Control.** The deployment's own store, created empty and written by its owner after the boot, boots again
  `"verified"` and answers.
- Severing (the plain boot's read dropped, so only a question boot reads) reddened the same 3 tests.

**What it does not cover** (measured by lane probes, not by tests in this tree). The read is the question boot's
read and has its limits (section 4.12). It is taken only by the boot that created the marker: a plain boot whose
path already carried a deployment marker with no store beside it (the store deleted, its marker kept) created its
store without the read, and a used store written there was booted `"verified"` and answered; after a question
about a withheld subject, its later answers moved at `debt.debt` and `debt.factors.freshness`, and under
`from_entity_freshness` also at `expires_at` and `ttl_anchor_at`, against the same store after a question that
acquired nothing (`probe_stale_deployment_marker.py`, `probe_unreached_stores_distinguish_l4b.py`). A copy of a
used store with a deployment marker forged beside it still answers, as before.

## ccf.deployment.manifest.DeploymentStoreNotEmpty

- Surface: ccf.deployment.manifest.DeploymentStoreNotEmpty
- Public surface: true
- Change type: added
- Before: absent; a store written at a plain boot's path after its deployment marker was booted as the deployment's own, the marker vouching for it.
- After: a `ValueError` raised by `load_and_boot` and `load_config_and_boot` when a boot not for a question that created its deployment marker in this boot opens a store holding any entity or relationship for the tenant at its one read, taken through the governed reader at the latest instant a timestamp can name, before the fabric is handed back. The handle is closed and the markers that boot created are removed first. Its text states no count.
- Why: SEC-020, `D-IMPL-378` OWED-RULINGS-3 item 2A (b). Red test: `tests/products/test_plain_boot_creating_its_store_finds_it_empty.py::test_2a_b_a_plain_boot_creating_its_store_refuses_a_store_planted_at_its_path_by_name`.
- Migration: none; additive. Boot a new store at a path that holds nothing, and write into it after the boot returns.

## ccf.deployment.DeploymentStoreNotEmpty

- Surface: ccf.deployment.DeploymentStoreNotEmpty
- Public surface: true
- Change type: added
- Before: absent.
- After: the package-level spelling of `ccf.deployment.manifest.DeploymentStoreNotEmpty`.
- Why: SEC-020, OWED-RULINGS-3 item 2A (b).
- Migration: none; additive.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: a boot not for a question created its deployment marker and booted whatever store the adapter opened at the path, unread.
- After: such a boot, when it created its marker in this boot, reads the store once before returning and raises `DeploymentStoreNotEmpty` if it holds anything for the tenant; a boot that reopens a store (the path held a store or a marker before the boot) takes no read.
- Why: SEC-020, OWED-RULINGS-3 item 2A (b): a boot creating a new store must find it empty, as a boot for a question must.
- Migration: none for a deployment that boots a new store at a fresh path and writes into it after the boot.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine.
- Why: SEC-020, OWED-RULINGS-3 item 2A (b). Red test: `tests/products/test_plain_boot_creating_its_store_finds_it_empty.py::test_2a_b_the_config_door_refuses_a_store_planted_at_a_plain_boots_path_by_name`.
- Migration: as `load_and_boot`.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: `store_creation` `"verified"` said every path naming the store carried a marker.
- After: it also says that a plain boot that wrote its deployment marker in this boot read the store once and found nothing for the tenant.
- Why: SEC-020, OWED-RULINGS-3 item 2A (b).
- Migration: none.
