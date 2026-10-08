# 378-23 (P4) — SEC-020 candidate: a question's store leaves a durable marker, and serves no later question

`D-IMPL-378`, SEC-020 residual P4 ("reopened stores and network stores",
Q9), built as the design lane's recommended option (a): *"Write a durable
marker when a store is booted for a question, and refuse any later serve from
it. Replay is unaffected."* Lane `378d-s020next`. **A candidate: Dave has not
ruled P4**, and the coordinator integrates nothing until he does. Option (b),
an adapter declaring its own freshness, is not built. **SEC-020 stays OPEN.**

**What the tests measure, on test fixtures.** In
`tests/products/test_withheld_subject_child_arguments_and_question_stores.py`,
red before the change and green after:

- **A question's store, booted again.** Each store was booted for one
  question and asked it through an acquisition seam: about the withheld
  subject, whose source returned a fresher claim, or about an identifier
  that names nothing. Booted again without `for_question` and asked about an
  identifier that names nothing through a resolver with no acquisition
  phase, both stores raised `QuestionStoreReopened`, with identical text, on
  both anchors. Before the change both answered, and the two answers differed
  at `debt.debt` and `debt.factors.freshness`, and under
  `from_entity_freshness` also at `expires_at` and `ttl_anchor_at`.
- **The same question fabric, asked again.** A later call on the same handle,
  through a resolver with no acquisition phase, raised `AcquiredFabricReused`
  on both anchors. Before the change it answered from what the first question
  fetched, with the same differences.
- **Replay unaffected.** A paved-road decision (early-withheld, and a
  never-acquired subject) replayed to its own address over its question's
  store booted again, by a writer boot and by a read-only boot; a serve
  through that same reopened fabric raised `QuestionStoreReopened`. Four
  records this lane served on base `8cfe77b2` (late-withheld, early-withheld,
  never-acquired, answered) replayed to their own addresses on the candidate.
- Three severings, one per mechanism: removing the refusal reddened six tests,
  removing the marker write reddened the same six, and taking the claim only
  when acquisition exists reddened the two same-handle tests.

**What it does not cover.** The marker sits beside the store, not inside it.
A store without it beside it is not recognized: a store booted for a question
before this change (measured: the four stores this lane minted on `8cfe77b2`
each answered a serve on the candidate), or a copy taken without it. A store
whose settings name no path (a network graph store, and the in-memory
development store) cannot be booted for a question, so it carries no marker
and cannot carry an acquisition phase; option (b) is what would change that.
The claim on one handle is still held per handle, in one process; across
handles and processes it is the marker that refuses (measured with the first
question asked in a child process). Only governed calls are refused: the
deployment's own write into a reopened store went through. A question refused
before the claim point (its address, its request, its temporal bound) reads no
graph and does not claim the fabric: over a reopened store an undeclared
parameter still got its own `product-request-violation` refusal, and on a
fresh question fabric a second question after such a refusal was served.

## ccf.products.resolver.QuestionStoreReopened

- Surface: ccf.products.resolver.QuestionStoreReopened
- Public surface: true
- Change type: added
- Before: absent; a question's store booted again plainly answered any governed call that declared no acquisition phase.
- After: an `UnsupportedComposition` (so a `ProductNotResolvable`) raised by `GovernedResolver.__call__` at the point a question fabric is claimed — after the question-level refusals, which read no graph, and before the graph is read — when the fabric reads a question's store booted again and the call declares no acquisition phase. Decided by the boot's marker, never by the subject or the store's contents.
- Why: SEC-020 residual P4. That store keeps what its question's acquisition fetched.
- Migration: none; additive.

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: reshaped
- Before: `for_question: bool = False` said whether THIS boot was for one question; nothing said whether the store had been booted for one before.
- After: adds `question_store: bool = False`: the store was booted for one question, by this boot or by an earlier one, read from the marker `<resolved path>.ccf-question-store` beside every path naming the store.
- Why: SEC-020 residual P4.
- Migration: none; the default is a store never booted for a question.

## ccf.deployment.BootedFabric

- Surface: ccf.deployment.BootedFabric
- Public surface: true
- Change type: reshaped
- Before: no `question_store` field.
- After: the package-level spelling of the same change.
- Why: SEC-020 residual P4.
- Migration: none.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: the Q9 claim was taken only by a call that declares an acquisition phase.
- After: every call over a fabric booted for its question claims it, with an acquisition phase or without, so a later call on the same fabric raises `AcquiredFabricReused`; a call with no acquisition phase over a question's store booted again raises `QuestionStoreReopened`. A call that declares an acquisition phase over such a store is still refused `AcquisitionNeedsAQuestionFabric`, unchanged.
- Why: SEC-020 residual P4: Q9 alone bound only where acquisition exists.
- Migration: a composition that asks one fabric booted `for_question=True` more than one question with no acquisition phase now gets `AcquiredFabricReused` at the second; boot a new store for each question, as the paved road does.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: `for_question=True` verified the store fresh and wrote nothing beside it.
- After: `for_question=True` also writes, flushes and syncs `<resolved path>.ccf-question-store` beside every path naming the store, before the store is booted; every boot reads it into `BootedFabric.question_store`. The marker is never read for the store's contents.
- Why: SEC-020 residual P4: a durable record, beside the store, that it was booted for one question.
- Migration: delete a question's store together with its marker. A marker left at a path makes a later plain boot there refuse to serve, which fails closed.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `load_and_boot`.
- After: as `load_and_boot`; both doors share one boot spine.
- Why: SEC-020 residual P4.
- Migration: as `load_and_boot`.
