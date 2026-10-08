# 378-03 — SEC-020: the withheld rendering scores with a registry built from the read before acquisition, and a record filed before dimension 5 carried the empty finding replays (SEC-020 stays open)

`D-IMPL-378`. Dave, 2026-10-07: "Apply the offered similarity-registry fix, but
keep the row open." **SEC-020 stays OPEN.** This entry removes one measured
difference between a withheld subject and a nonexistent one (channel 5 of the
`D-IMPL-377` close-out, review finding I-2) and lifts one replay limit
(channel 7, review finding M-5, which was never an existence channel). The
security how-to, section 4.12, lists what still tells a withheld subject from a
nonexistent one.

**Channel 5, the similarity corpus.** Route A (`377-01`) re-executes a withheld
subject's plan without the request seed over the fabric as it stood before the
call's acquisition seam ran, but the re-execution reused the operator registry
built from the view read after acquisition. An index-backed operator holds a
corpus read out of the view its registry is built from, so a similarity
operator scored the walk over the records before acquisition against the text
acquisition had just written for the asked subject. Measured on `main` @
`7bf069cc`, on a fabric that already held the withheld account, with an
acquisition keyed on the subject that changed its similarity text to the
query: under `from_decision` the two products differed at `computed_empty`,
`debt.debt`, `debt.factors.freshness` and `debt.scorers`; under
`from_entity_freshness` the withheld subject was served and the nonexistent
one refused `ttl-anchor-refusal`. With the change, both anchors match: every
member of the served product, and the refusal shell except
`replay_reference`. The exploit test is
`tests/products/test_withheld_similarity_registry.py::test_i2_a_withheld_subject_is_scored_against_the_corpus_read_before_acquisition`.

**The trade, measured.** The registry now follows the rule the walk already
follows, so it shares that rule's limit (close-out channel 1, "An acquisition
not keyed on the subject"). On the same fabric with an acquisition that
ingests the same refreshed claim whatever is asked, the two products differed
before this change at `debt.debt` and `debt.factors.freshness` (and, under
`from_entity_freshness`, at `expires_at` and `ttl_anchor_at`), both served.
With it they differ under `from_decision` at `computed_empty`, `debt.debt`,
`debt.factors.freshness` and `debt.scorers`, and under `from_entity_freshness`
the withheld subject is refused `ttl-anchor-refusal` while the nonexistent one
is served. Held as a strict expected failure:
`tests/products/test_withheld_similarity_registry.py::test_channel_1_a_population_read_still_tells_the_two_apart_with_similarity`.

**Channel 7, records filed before dimension 5 carried the empty finding.**
`ac4e4573` (merged to `main` in `8e8374c3`, 2026-09-05) put
`ContextProductContract.computed_empty` on the product, inside its content
address. The record writer first copied it into dimension 5 in `1a2359e4`; that
work's integration `77d5e2a9` and its revert `91fd7965` both reached `main` in
`29a3c5a4`, with no net change, and its reapply `6247cd63` reached `main` in
`7bf069cc` (2026-10-07). Every record `main` filed for a product carrying a
finding between those two merges, the `v1.0.0` and `v1.0.1` tags included,
failed replay with `ReplayDivergence`, under the code that filed it as well.
Measured: the record bytes the writer at `d9305603` stored for the paved
fixture's computed-empty question are byte-identical to the current writer's
record for that question with dimension 5's `computed_empty` removed. They
diverge without this change and replay to their recorded product address with
it. The test is
`tests/replay/test_record_filed_before_dimension_5_finding.py::test_m5_a_record_filed_before_dimension_5_carried_the_finding_replays_to_its_own_address`.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: when Π raised the withheld signal, `__call__` re-executed the plan without the request seed over the as-of read taken immediately before the declared acquisition seam, using the operator registry built from the view read after acquisition. A similarity operator in that registry scored the walk against the text acquisition had just written for the asked subject.
- After: when an acquisition seam ran, the re-execution runs on a `ProjectionEngine` over the same reader whose registry `build_operator_registry` builds from that read before acquisition, with the same operator parameters (the same effective request over the same pinned artifacts). Only the withheld branch builds it: the served path keeps the registry built from the view after acquisition, so a subject Π does not withhold is still matched against the text its own acquisition wrote (`tests/products/test_withheld_similarity_registry.py::test_i2_a_served_subject_is_still_scored_against_the_text_its_acquisition_wrote`). With no seam declared nothing changes.
- Why: SEC-020 close-out channel 5, review finding I-2; `D-IMPL-378`. The withheld rendering is the walk a subject that names nothing gets, and that subject's corpus is the text before acquisition.
- Migration: none in code. If your `acquire` is not keyed on the subject and the plan carries a similarity operator, read "The trade, measured" above: that shape now differs at more members, and as refused against served under `from_entity_freshness`. With an acquisition seam declared, a withheld answer now also builds the operator registry a second time from the read before acquisition. On a test fabric of about 1,500 entities with a similarity operator in the plan, the withheld median was 1.06 to 1.08 times the nonexistent one over two runs of eight calls each, ranges overlapping (1.11 in one run before this change). If that read holds an entity whose declared corpus attribute is missing, the withheld call raises `SimilarityCorpusAttributeError`, as a nonexistent subject's call over that same state does.

## ccf.projection.engine.ProjectionEngine

- Surface: ccf.projection.engine.ProjectionEngine
- Public surface: true
- Change type: behavior
- Before: the docstring of `execute_without_request_seed` said the governed resolver built the engine's registry from the view read after acquisition.
- After: no code change. The docstring states the caller's obligation: a caller passing `before_acquisition` calls the method on an engine whose registry was built from that same read, and on a registry built from a later view an index-backed operator scores the walk against text the acquisition wrote. `GovernedResolver` now meets it.
- Why: SEC-020 close-out channel 5, review finding I-2; `D-IMPL-378`.
- Migration: a deployment that calls `execute_without_request_seed(..., before_acquisition=...)` itself should build the engine's registry with `build_operator_registry(view=<that same read>, ...)`, as `GovernedResolver` does.

## ccf.projection.plan.ProjectionOutput

- Surface: ccf.projection.plan.ProjectionOutput
- Public surface: true
- Change type: behavior
- Before: the docstring listed similarity over an entity the acquisition refreshed among the channels that still tell a withheld subject from a nonexistent one.
- After: no code change. The docstring says the re-run scores with a registry built from the read before acquisition and that the two products were measured equal on a test fixture whose acquisition changed the subject's similarity text; the rest of its list is unchanged.
- Why: SEC-020 close-out channel 5, review finding I-2; `D-IMPL-378`.
- Migration: none.

## ccf.replay.engine.replay

- Surface: ccf.replay.engine.replay
- Public surface: true
- Change type: behavior
- Before: a record whose dimension 5 carried no `computed_empty`, for a product that carried one, was rebuilt without the finding and raised `ReplayDivergence` on its content address.
- After: when the product rebuilt from the record does not reproduce the recorded address, the record carries no `computed_empty` and the rebuilt product carries none, the product is rebuilt once more with the finding the writer of the record's era attached, `ComputedEmptyFinding.of(execution, emptiness=emptiness_of(ExecutionEvidence.of(execution)))`, applied to the re-execution replay has already held to the record (step sequence, query pins, graph substate, store pin). It is accepted only if it then hashes to the address the record names; otherwise `ReplayDivergence` is raised as before, naming the first rebuild's address. A record carrying the member reaches this rule only if its own rebuild already failed. No writer, record, byte or address changes, and `replay_refusal`, which rebuilds no product, is untouched.
- Why: SEC-020 close-out channel 7, review finding M-5; `D-IMPL-378`. A record that predates the member replays under the semantics it was written under. The member is hash-transparent at `None`, so a record cannot say whether it predates the member or served a product with no finding, and the record's own product address decides. Controls: `tests/replay/test_record_filed_before_dimension_5_finding.py::test_m5_control_the_record_the_current_writer_files_replays_with_its_finding_copied` and `tests/replay/test_record_filed_before_dimension_5_finding.py::test_m5_control_the_record_s_own_product_address_still_arbitrates`.
- Migration: none. A record filed before the change replays through any `ReplayEnvironment` that copies `path.computed_empty`, which is `None` on such a record, including `src/ccf/replay/environment.py::RecordedEnvironment`.
