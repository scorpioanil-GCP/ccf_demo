# 378-34 (P4 strict) — SEC-020: no store is presumed fresh; a composition the SDK cannot verify refuses before questions run

`D-IMPL-378`, SEC-020 residual P4, ruled by Dave on 2026-10-08 at 12:29 MST:
*"An unmarked existing store must not be presumed fresh. Require verifiable
fresh creation or refuse acquisition-backed serving. Unsupported network
compositions must refuse before questions run."* Lane `378e-p4strict`, built
on the P4 (a) marker of fragment 378-23. Option (b), an adapter declaring its
own freshness, is not built. **SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.** In
`tests/products/test_unmarked_and_unverifiable_question_stores.py`, red before
the change and green after:

- **An unmarked existing store.** A store booted for one question and asked
  it (about the withheld subject, whose source returned a fresher claim, or
  about an identifier that names nothing), then stripped of its marker as a
  store from before the marker carries none; and a copy of such a store taken
  without its marker. Booted again plainly and asked about an identifier that
  names nothing through a resolver with no acquisition phase, both raised
  `UnmarkedStoreNotPresumedFresh`, with identical text, on both anchors. Before
  the change both answered and the two answers differed. The marked original
  beside the copy raised `QuestionStoreReopened`.
- **Replay unaffected.** A paved-road decision replayed to its own address
  over its unmarked question store, by a writer boot and by a read-only boot,
  and a serve through that same fabric raised `UnmarkedStoreNotPresumedFresh`.
  The four records lane `378d-s020next` served on `8cfe77b2`, before any
  marker existed, replayed to their own addresses on this lane's tree, and a
  serve through each reopened store raised `UnmarkedStoreNotPresumedFresh`
  where it had answered before.
- **Verifiable fresh creation.** A second boot for a question at the same
  path, run while the first was inside its boot, raised `QuestionFabricNotFresh`,
  and the first fabric read the empty store it created; before the change the
  second booted, wrote three entities, and the first booted over them. A store
  created at the path after the freshness check raised `QuestionFabricNotFresh`;
  before, the question fabric booted over it.
- **Before questions run.** An acquisition phase, a population phase, or both,
  composed over a store whose connection names no path raised
  `AcquisitionOverUnverifiableStore` when the resolver was constructed, with
  nothing asked of the source; before, it was constructed and refused at its
  first call. The paved road over a substrate setting its adapter does not
  take as a path, for an in-process and a network adapter, raised
  `AcquisitionOverUnverifiableStore` at `open_product`, with nothing minted;
  before, it opened and every question was refused at its boot.
- **Controls, green before and after.** A store booted fresh for one question
  answered that question. A store a door created for a deployment, closed and
  booted again, answered again, alike. An acquisition composition over a plain
  boot of a file-backed store is still constructed, and still refused at its
  first call (`AcquisitionNeedsAQuestionFabric`), which is what lets
  `RecordedEnvironment` rebuild a resolver over a reopened store.
- Six severings, one per check: removing the unmarked-store refusal reddened
  six tests; the construction refusal three; the open refusal two; the
  exclusive create one; the post-reservation check one; and skipping the
  deployment marker reddened the kept-store control.

**What it does not cover.** A marker sits beside its store and binds to it by
path alone: it vouches against reuse of a store by deployments and operators,
not against an actor who can write into the store's directory and remove,
copy or forge a marker, or replace a store at a marked path. Only governed
calls are refused: a deployment's own writes into a reopened store go through.
A store with no marker beside it — one created before this change, by a boot
below these doors, or copied without its marker, a deployment's own store
included — is refused for governed calls until it is recreated through a door.
A store whose connection names no path cannot be verified fresh or marked, so
it serves only compositions without an acquisition phase; the in-process
development store is new at every boot by its adapter's construction (measured)
but nothing in the SDK verifies that. The SDK checks and reserves a path, but
the adapter creates the store at the boot: a store another actor writes at the
path after the SDK's last check is opened as the one the boot created — by a
boot for a question, as its question fabric; by any other boot, vouched for by
its deployment marker (both measured). A stale question marker makes a later
question boot at that path refuse and a later plain boot read the store as a
question's, which fails closed.

## ccf.products.resolver.UnmarkedStoreNotPresumedFresh

- Surface: ccf.products.resolver.UnmarkedStoreNotPresumedFresh
- Public surface: true
- Change type: added
- Before: absent; a governed call with no acquisition phase over an existing store with no marker was answered.
- After: an `UnsupportedComposition` (so a `ProductNotResolvable`) raised by `GovernedResolver.__call__` at the point a question fabric is claimed — after the question-level refusals, which read no graph, and before the graph is read — when `BootedFabric.store_creation` is `"unmarked"` and the call declares no acquisition phase. Decided by the boot's reading of the markers, never by the subject or the store's contents.
- Why: SEC-020 P4 (a), made strict: an unmarked existing store is not presumed fresh.
- Migration: none; additive.

## ccf.products.resolver.AcquisitionOverUnverifiableStore

- Surface: ccf.products.resolver.AcquisitionOverUnverifiableStore
- Public surface: true
- Change type: added
- Before: absent; an acquisition composition over a store with no path was refused `AcquisitionNeedsAQuestionFabric` at its first call, and the paved road over such a substrate at every question's boot.
- After: a subclass of `AcquisitionNeedsAQuestionFabric`, raised by `GovernedResolver` construction when an acquisition or a population phase is declared over a fabric whose `store_creation` is `"unverifiable"`, and by `open_product` when the environment's substrate setting is not a path-valued setting of the declared adapter's connection contract.
- Why: SEC-020 P4 (a), made strict: an unsupported network composition refuses before questions run.
- Migration: none; additive. A handler for `AcquisitionNeedsAQuestionFabric` also catches it.

## ccf.products.resolver.AcquisitionNeedsAQuestionFabric

- Surface: ccf.products.resolver.AcquisitionNeedsAQuestionFabric
- Public surface: true
- Change type: behavior
- Before: raised at the first call for every acquisition composition over a fabric not booted for its question.
- After: unchanged over a store with a path; over a store with no path its subclass `AcquisitionOverUnverifiableStore` is raised at construction instead.
- Why: SEC-020 P4 (a), made strict.
- Migration: none for a handler of this class; a test that constructed such a composition and expected the refusal at the call sees it at construction.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: reshaped
- Before: `for_question` and `question_store` said whether this boot, or an earlier one, was for one question; nothing said whether an existing store's creation was known.
- After: adds `store_creation: Literal["verified", "unmarked", "unverifiable"] = "unmarked"`, read from the markers beside the store: `"verified"` when every path naming the store carries a question or deployment marker, `"unmarked"` when the store existed with neither, `"unverifiable"` when the adapter's connection names no path. The default, for a value no boot produced, presumes nothing.
- Why: SEC-020 P4 (a), made strict.
- Migration: none for a value a boot returns.

## ccf.deployment.BootedFabric

- Surface: ccf.deployment.BootedFabric
- Public surface: true
- Change type: reshaped
- Before: no `store_creation` field.
- After: the package-level spelling of the same change.
- Why: SEC-020 P4 (a), made strict.
- Migration: none.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: an acquisition composition over a store with no path was constructed; a call with no acquisition phase over an existing unmarked store was answered.
- After: construction raises `AcquisitionOverUnverifiableStore` for the first; the call raises `UnmarkedStoreNotPresumedFresh` for the second, at the claim point. A resolver constructed over an unmarked or a question's store and never called, as `RecordedEnvironment` builds it, is unaffected.
- Why: SEC-020 P4 (a), made strict.
- Migration: compose a store with no path without an acquisition phase; recreate an unmarked store through a deployment door.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: opened over any substrate setting; a substrate the SDK could not verify fresh was refused at every question's boot.
- After: refuses `AcquisitionOverUnverifiableStore` at open when the environment's `substrate.setting` is not a path-valued setting of the adapter `ccf_config.yaml` declares, read off its declared connection contract; nothing is minted, booted or connected to.
- Why: SEC-020 P4 (a), made strict: the paved road always acquires, so it refuses before questions run.
- Migration: name a path-valued setting of a file-backed adapter as the substrate.

## ccf.deployment.manifest.QuestionFabricNotFresh

- Surface: ccf.deployment.manifest.QuestionFabricNotFresh
- Public surface: true
- Change type: behavior
- Before: raised before anything was registered, when a path named by the store existed or none was named.
- After: also raised after registration and before the boot, when another boot already holds a path's question marker, or when a store or another boot's deployment marker appeared at a path after the check; the markers this boot created are removed first.
- Why: SEC-020 P4 (a), made strict: verifiable fresh creation.
- Migration: none.

## ccf.deployment.QuestionFabricNotFresh

- Surface: ccf.deployment.QuestionFabricNotFresh
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.manifest.QuestionFabricNotFresh`.
- After: the package-level spelling of the same change.
- Why: SEC-020 P4 (a), made strict.
- Migration: none.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: `for_question=True` checked the store paths did not exist, then wrote the question marker with a truncating open before the boot; a boot not for a question wrote nothing beside the store.
- After: `for_question=True` creates each question marker exclusively, file and directory synced, and then requires that no store and no deployment marker exists at any path. Any other boot that is about to create its store first creates `<resolved path>.ccf-deployment-store` beside it, exclusively; an existing store is never marked afterwards. Every boot reads the markers into `BootedFabric.store_creation`.
- Why: SEC-020 P4 (a), made strict: verifiable fresh creation, and an existing store with no marker is not presumed fresh.
- Migration: delete or copy a store together with its marker. A store created before this change, or below these doors, is booted as before and refused for governed calls; recreate it through a door.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine.
- Why: SEC-020 P4 (a), made strict.
- Migration: as `load_and_boot`.
