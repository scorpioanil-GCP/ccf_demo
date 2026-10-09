# 378-40 (P4s-A b) — SEC-020: a question boot reads its store once before handing it back; a read-only boot for a question is refused

`D-IMPL-378`, SEC-020 follow-up P4s, ruled by Dave on 2026-10-08 at 16:40 MST
(item 3): *"P4s-A: (b); P4s-B: (a). Add the emptiness check and keep
unverifiable stores free of acquisition. The check must precede acquisition
and remain protected by exclusive ownership through use."* Lane `378f-p4e`,
on the P4 (a) markers of fragments 378-23 and 378-34. P4s-B (a) needed no
code: a boot for a question over a store whose connection names no path is
still refused, and an acquisition composition over one still refuses before
any question runs. **SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.** In
`tests/products/test_question_store_empty_at_boot_and_held_through_use.py`:

- **A store written at a question boot's path after the SDK's last check.**
  Before the change, by hand, a used question store copied to the path inside
  the boot, and the deployment's own plain boot creating and filling a store
  there, were each booted as the question's fabric holding 3 entities, and the
  question was answered with its acquisition phase asked; on the paved road, an
  earlier question's store copied to the next question's minted path was
  answered, with `acquire` called. After, each boot raised
  `QuestionStoreNotEmpty`, with nothing asked of the source and the same text
  for the withheld account and for an identifier that names nothing.
- **The order.** The boot's one read, through the governed reader at the latest
  instant a timestamp can name, is the first read of the store: inside the
  boot, before the population phase, the read before acquisition and the
  acquisition phase, by hand and on the paved road. Before the change no such
  read ran.
- **A read-only boot for a question.** Before the change, `load_and_boot` and
  `load_config_and_boot` with `for_question=True, read_only=True` booted with
  lease scope `read-only`, and a plain writer boot of the same path wrote the
  deployment's three accounts into the store while the question's fabric was
  open; the fabric read them back. After, both raised
  `QuestionFabricNotExclusive`, with nothing registered and nothing created at
  the path.
- **What holds the store from the read to the question's end**, green before
  and after (measurements of protections that already existed): by hand, after
  the boot returned and again inside the acquisition phase, a boot for a
  question at the path raised `QuestionFabricNotFresh`, a plain writer boot and
  the composition root's own writer boot `SingleWriterViolation`, a plain
  read-only boot asked a governed question `QuestionStoreReopened`, and a
  second governed call over the question's fabric `AcquiredFabricReused`. On
  the paved road the first three were tried through the single-file door, and
  from another process of the deployment the first three again. The
  question's store held nothing any route tried to write.
- **Control.** A record served over a fresh question store replays to its own
  address through a read-only boot that is not for a question.
- Severings: neutering the emptiness decision reddened the three store tests;
  removing the read reddened those three and the two order tests; neutering the
  read-only refusal reddened its two tests. For the existing lease, removing
  the SQLite writer lease's `flock` reddened the cross-process test, whose
  other process then booted a writer and wrote.

**What it does not cover** (measured by lane probes, not by tests in this
tree). The read sees a claim only if nothing supersedes it at the latest
instant: a store whose every claim was superseded before it with no current
successor, which no SDK writer leaves, written by raw SQL at a question boot's
path, was booted, and its question read its rows. A raw SQLite connection,
outside the SDK's writer lease, wrote into a question's store while the
question ran, and the question read it. A store holding rows only for another
tenant is booted; the paved fixture's answer over it matched its answer over a
fresh store. The read is taken only by a boot for a question: a used question
store with a deployment marker forged beside it, and a used question store
written at a plain boot's path after its marker, each still answered a later
question.

## ccf.deployment.manifest.QuestionStoreNotEmpty

- Surface: ccf.deployment.manifest.QuestionStoreNotEmpty
- Public surface: true
- Change type: added
- Before: absent; a store written at a question boot's path after the SDK's last check was booted as the question's fabric.
- After: a subclass of `QuestionFabricNotFresh` (so a `ValueError`), raised by `load_and_boot` and `load_config_and_boot` with `for_question=True` when the store the adapter opened holds any entity or relationship for the tenant at the boot's one read, taken through the governed reader at the latest instant a timestamp can name, after the writer lease is taken and before the fabric is handed back. The handle is closed first; the question marker stays. Its text states no count.
- Why: SEC-020 P4s-A (b): the emptiness check precedes acquisition.
- Migration: none; additive. A handler for `QuestionFabricNotFresh` also catches it.

## ccf.deployment.QuestionStoreNotEmpty

- Surface: ccf.deployment.QuestionStoreNotEmpty
- Public surface: true
- Change type: added
- Before: absent.
- After: the package-level spelling of `ccf.deployment.manifest.QuestionStoreNotEmpty`.
- Why: SEC-020 P4s-A (b).
- Migration: none; additive.

## ccf.deployment.manifest.QuestionFabricNotExclusive

- Surface: ccf.deployment.manifest.QuestionFabricNotExclusive
- Public surface: true
- Change type: added
- Before: absent; `for_question=True` with `read_only=True` booted a question's fabric that held no writer lease.
- After: a subclass of `QuestionFabricNotFresh` (so a `ValueError`), raised by `load_and_boot` and `load_config_and_boot` for `for_question=True` with `read_only=True`, before anything is registered or created at the path.
- Why: SEC-020 P4s-A (b): the check stays protected by exclusive ownership through use, which the question marker and the boot's writer lease provide; a read-only boot takes no lease.
- Migration: boot a question's fabric as a writer; read a question's store for replay with a read-only boot that is not for a question.

## ccf.deployment.QuestionFabricNotExclusive

- Surface: ccf.deployment.QuestionFabricNotExclusive
- Public surface: true
- Change type: added
- Before: absent.
- After: the package-level spelling of `ccf.deployment.manifest.QuestionFabricNotExclusive`.
- Why: SEC-020 P4s-A (b).
- Migration: none; additive.

## ccf.deployment.manifest.QuestionFabricNotFresh

- Surface: ccf.deployment.manifest.QuestionFabricNotFresh
- Public surface: true
- Change type: behavior
- Before: raised for a store a boot for a question could not show fresh at its path: none named, one existing, or one reserved or created by another boot.
- After: also raised, as its subclass `QuestionStoreNotEmpty`, after the boot when the store it opened holds anything for the tenant, and, as its subclass `QuestionFabricNotExclusive`, before anything is registered when the boot is also read-only.
- Why: SEC-020 P4s-A (b).
- Migration: none for a handler of this class.

## ccf.deployment.QuestionFabricNotFresh

- Surface: ccf.deployment.QuestionFabricNotFresh
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.manifest.QuestionFabricNotFresh`.
- After: the package-level spelling of the same change.
- Why: SEC-020 P4s-A (b).
- Migration: none.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: `for_question` said the boot verified the store's path did not exist and reserved it.
- After: `for_question` also says the store held nothing for the tenant when the boot read it, just before handing the fabric back.
- Why: SEC-020 P4s-A (b).
- Migration: none.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: `for_question=True` reserved the store's path and booted whatever store the adapter opened at it; `read_only=True` beside it booted a fabric with no writer lease.
- After: `for_question=True` reads the store the adapter opened once, after the writer lease is taken and before returning, and raises `QuestionStoreNotEmpty` if it holds anything for the tenant; with `read_only=True` it raises `QuestionFabricNotExclusive` before anything is registered.
- Why: SEC-020 P4s-A (b): the emptiness check precedes acquisition and stays protected by exclusive ownership through use.
- Migration: boot a question's fabric as a writer, at a path that does not exist, and ingest anything it must start with after the boot returns.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine, and the paved road boots every question's fabric through this one.
- Why: SEC-020 P4s-A (b).
- Migration: as `load_and_boot`.
