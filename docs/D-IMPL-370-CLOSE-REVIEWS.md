# D-IMPL-370 — the BATCH-CLOSE panel on batch 3 (after integration)

**Subject:** `integration-remaining-rows` @ `61587828`, the diff from `bad6ee01` (end of batch 2): SEC-028-F1
(`row-sec-028-f1` @ `c11a7221`), SEC-024 choice C (`row-sec-024` @ `c61f0c85`), SEC-025 (`row-sec-025` @
`17acbe22`), SEC-020 (`row-sec-020` @ `b41e7058`). Code, tests, workflows and the four executor reports inlined
(164,607 bytes). **Reviewers:** Codex (diff only; sandbox dead, stated), Cursor (tree, symbols resolved), Fable
(tree, measured probes). **Executor:** Opus, excluded. **Date:** 2026-10-06. **Verifier:** the orchestrator
re-measured or inspected every claim that carries a disposition.

## Findings, verification, disposition

| # | Seat(s) | Row | Finding | Verified how | Disposition |
| --- | --- | --- | --- | --- | --- |
| B1 | Cursor (BLOCKING), Codex (advisory), Fable (BLOCKING, **measured**) | SEC-020 | The constant-fill baseline is wrong: walk starts union the class seeds with the request seed (`src/ccf/graph/fallback.py`, GQ-11), so on a populated fabric a nonexistent subject's view is **not** empty; rendering a withheld subject over `over_empty_view()` makes it differ from a nonexistent one on the same fabric (measured: `computed_empty`, `debt.debt` 0 vs 0.2929, freshness, scorers; on `from_entity_freshness` nonexistent SERVED, withheld REFUSED — a serve/refuse existence oracle). The pre-fix silent `{}` path was indistinguishable on that fabric, so in the wide-view shape the fix **created** the leak. The shipped test put the nonexistent subject on an empty fabric, departing from the row text. The `GovernedResolver` comment claiming an empty view is what a nonexistent subject yields is false | Orchestrator **inspected** the seed union and the fixture's `seed_entity_classes: ["account"]`; Fable **measured** both subjects on the same fabric | **CONFIRMED, BLOCKING. SEC-020 reopened for its one corrective round:** masked re-execution (the plan re-executed over the real view with the withheld subject's records masked; siblings remain), both subjects on the same shared fabric in the test for both anchors, the false comment corrected; GQ-11 untouched (a scope change, refused). If the round cannot land, SEC-020 is reverted from the integration branch and parked |
| B2 | Fable (BLOCKING, **measured**) | SEC-020 | Replay of a withheld decision raises `ReplayDivergence`: `src/ccf/replay/environment.py::RecordedEnvironment.rehydrate_product` never sets `computed_empty` (in the hash when non-`None`); dimension 5 does not carry it; the signal is not in the record. Pre-existing class for any empty-finding product (no test replays one), reached by withheld decisions since this row | Fable measured; orchestrator inspected the rehydrator | **CONFIRMED, BLOCKING.** In the same corrective round: carry what rehydration needs into the record (hash-transparent sentinel), rehydrate `computed_empty`, a replay test of a withheld decision with the identical address, the nonexistent-on-empty control fixed if in reach or carried as **SEC-020-C-01** |
| B3 | orchestrator | SEC-020 | `tests/contracts/test_hash_transparency.py::test_the_marked_fields_in_the_tree_are_exactly_the_ticked_table` red on the integrated tree: `ProjectionOutput.withheld` is marked hash-transparent and absent from the `D-IMPL-243` roster; the executor's regression set did not include `tests/contracts` | **MEASURED**: red at `61587828`, 41 passed on `row-sec-025` (which lacks SEC-020) | **CONFIRMED, regression.** Same corrective round: the roster entry |
| B4 | Cursor | SEC-020 | `tests/products/test_empty_operator_halves.py` AST check accepts `rendered = execution` (the withheld branch dropped) | inspected | **ADVISORY**, offered to the corrective round as optional |
| B5 | Fable | SEC-025 | No caller outside tests is broken (`product.py` and cp-20 build `QuestionBoundChildResolver` with `child_questions`; no `__call__`-only wrapper in `src`/`runtime`/`examples`). `ChildArguments` carries no request, so local/mcp legs are usable only by single-subject composites — fails closed, **undisclosed** in the fragment's Migration line | Fable grep + inspection | **ADVISORY, FIXED in this pass** (the fragment's Migration line amended, `SURFACE-CHANGES.md` reassembled) |
| B6 | Cursor | SEC-025 | Local/mcp legs bind the subject only (not intent/freshness/parameters); `ChildCandidate.asked_question` is resolver-authored, so a custom resolver could mint a matching subject; the request-less `__call__` path fails closed | inspected; already disclosed by the executor | **CARRIED** as **SEC-025-C-01** |
| B7 | Fable | SEC-024 | One more wire site changed by the ruling, unnamed in the record: `runtime/ccf_runtime/http_api/routes/product.py` renders a `WireRequest` `ValidationError` into the 400 detail (loses `input_value=`). `.errors()` still carries input (pydantic 2.13.4) and both in-tree consumers read `loc`/`msg` only. Same class carried by name: `hitl/webhook.py`, `orchestration/claude_agent/driver.py` (exception text to the model), `hitl_server.py` / `routes/hitl.py` (`str(error)` ×14) | Fable measured `.errors()`; inspected the sites | **RECORDED** (the ruling's consequence, choice C) and **CARRIED** as **SEC-024-C-01** |
| B8 | Cursor | SEC-024 | `traceback.format_tb` still emits source lines (a secret interpolated in a raise line's source would log); `ExceptionGroup.exceptions` not walked | inspected | **ADVISORY, CARRIED** as **SEC-024-C-02** |
| B9 | Cursor, Fable | SEC-028-F1 | `LOCKED_EXTRAS` is a second source of truth beside README; lint green on the committed tree, nothing adjacent | inspected | **CARRIED** (already named) |
| B10 | all | all | Executor reports vs tree: SEC-020's "empty view ≡ nonexistent" contradicted (B1); `ProjectionOutput.withheld` is hash-transparent at the `False` **sentinel**, the `True` mark participates (the executor's wording was imprecise); otherwise no contradiction | — | noted |

## Rejected

None.

## Regression on the integrated tree `61587828`, measured by the orchestrator

| Suite | Result |
| --- | --- |
| artifacts, mcp, contracts, replay, peering, crossproc, products, projection, http_api, surface, deployment, lints tests, invariants | **6277 passed, 3 failed, 1 skipped, 1 xfailed** |
| the 3 failures | the two standing reds (citation ratchet at 365; the worktree child-process test) and **B3, new** |
| `tools.lints --all` | rc=0 |
| `mypy` | no issues in 243 files |
| `tools/docs_tests` | **320 passed** (the retirement sweep green after regeneration) |
| `tests/examples` (no estate export) | 28 failed, 992 passed, 743 skipped — identical to the base |

## Reopen — SEC-020 corrective round

Dispatched as SEC-020's one corrective round with B1 (masked re-execution, same-fabric test), B2 (replay rehydration), B3
(roster) and B4 (optional). Result on `row-sec-020` @ `1a2359e4` (pushed, kept as evidence): all four landed —
`ProjectionEngine.execute_with_entities_masked`, a masked reader over one store read pinned to the real snapshot, the
withheld subject and every relationship touching it removed before the walk, acquired content re-fed; `ContentGenerationPath.computed_empty`
(hash-transparent at `None`) written by `build_replay_record` and copied back by `rehydrate_product`, with two paved-road replay
tests (a withheld decision and the nonexistent-on-empty control, which was diverging before, now both replay to their own
address); both new fields ticked in the `D-IMPL-243` roster; the AST check tightened. Exploit module **9 passed, 2 xfailed
(strict)**; eight severings each reddened it with sha-checked restores; 595-address census 0 moved.

**But the row is NOT resolved, and the executor measured why.** On one class-seeded fabric a nonexistent subject's walk
(class seeds ∪ request seed) still **reads the withheld subject's own claims** — it is an in-scope entity — while the
masked rendering excludes them. Whenever the withheld subject's observations are fresher or staler than its siblings'
(measured: withheld at 11:55, siblings at 11:30), `from_decision` differs at `debt.debt` and `debt.factors.freshness`, and
`from_entity_freshness` also at `expires_at` and `ttl_anchor_at`. In practice a withheld subject's freshness almost
never equals its siblings', so on class-seeded plans the masked rendering is distinguishable in nearly every real case —
a shape in which the **base tree did not leak** (both subjects read the same full view). The row's own test holds the
residual as two strict xfails. **The correct rule is now identified and is not what either round built:** render the
withheld subject from the plan re-executed **without the request seed** (the walk starts a nonexistent subject gets, by
construction: class seeds only), not from the view with the subject's records masked. On a class-seeded plan that keeps
the withheld subject's claims in the view exactly as a nonexistent subject sees them; on a subject-seeded plan it yields
the empty view. That is a third round, which the cap forbids. **Disposition: SEC-020 PARKED.** The integration merge
`01cb38a6` is **REVERTED** at `014f6e23` (assembled documents regenerated; `tests/contracts/test_hash_transparency.py`
back to green), so the integration branch carries neither the round-1 leak nor the round-2 residual. The replay
rehydration fix (B2), which also repaired a pre-existing divergence for empty-finding products, lives on the parked branch
and is re-integrated with the row. **Proposal for Dave:** authorize one further SEC-020 round on the request-seed rule,
with the same-fabric unequal-age case promoted from xfail to a required assertion.
