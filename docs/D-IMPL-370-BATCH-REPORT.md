# D-IMPL-370 — batch 3: consolidated report

**Date:** 2026-10-06, ~05:45 MST. **Integration SHA:** `integration-remaining-rows` @ **`014f6e23`** (pushed).
**`main` @ `933ef91f` untouched.** No tag, no release, no SEC identifier closed; the ledger stays **13 of 29**.
This report is cumulative with `docs/D-IMPL-368-PILOT-REPORT.md` and `docs/D-IMPL-369-BATCH-REPORT.md`.

## 1. What Dave asked for at `D-IMPL-370`, and what was done

| Instruction | Done |
| --- | --- |
| Inspect GitHub CI at `bad6ee01` against the baseline, correct the batch report, fix regressions in scope, record pre-existing failures | **Done** (`D-IMPL-369-BATCH-REPORT.md` §3.1). `ci.yml` runs on every push, so the pinned, hash-locked workflows had run all along; the earlier "not run on GitHub" was wrong. Lint green on both. Tests job: the same single pre-existing node at both. Examples job: the same pre-existing hw1 client failure at both. **Docs gate: a pilot regression** at `0d0be21b` (SEC-026 shifted the generated retirement report), fixed by regeneration; green on GitHub at `3a77083c` and after |
| SEC-017 parked, remedy includes within-tenant entitlement | **Recorded**; no closure, no redefinition. One concrete authorization proposal is owed later |
| A2A body bound carried explicitly as unresolved | **Recorded as SEC-021-U1**; no document describes bounded receive queues as bounding request bodies (audited) |
| Lock-freshness follow-up, proved by changing a declared requirement | **SEC-028-F1 INTEGRATED** (`row-sec-028-f1` @ `c11a7221`): raised bound, new dependency and a build requirement each refused on a copy of `pyproject.toml`; orchestrator reproduced two of the three by hand |
| SEC-024 (choice C), SEC-020, SEC-025 after a reviewer measures current behavior | Measured first (`scratchpad/measure-024-020-025.md`): all three rows rewritten before execution. Outcomes below |

## 2. Rows

| Row | Outcome | Rounds | Branch | Evidence |
| --- | --- | --- | --- | --- |
| SEC-028-F1 lock freshness | **INTEGRATED** | 1 of 2 | `c11a7221` | 15 tests, red→green; 7 severings red; lint rc=0; 792 lint tests |
| SEC-024 choice C | **INTEGRATED** | 1 of 2 | `c61f0c85` | 3 cases red→green; C-01 wire tests byte-unchanged; 3 severings red (the new case 2 needs both layers severed; row text corrected) |
| SEC-025 child subject binding | **INTEGRATED** | 1 of 2 | `17acbe22` | 4 subcases red→green + the peered subcase `xfail(strict)` as **SEC-025-U1**; severing the shared check reddened the `D-IMPL-340` test too (one check, not two); 1816 regression tests |
| SEC-020 withheld vs nonexistent | **PARKED and REVERTED** | 2 of 2 | `1a2359e4` (evidence) | Round 1 integrated then found by the close panel to **create** a leak on class-seeded fabrics (measured); round 2 fixed the per-request shape and replay, but measured a remaining residual on class-seeded fabrics whenever the withheld subject's freshness differs from its siblings'. The correct rule (re-execute without the request seed) is identified; a third round is outside the cap. Merge reverted at `014f6e23` |

## 3. Panels

- **Pre-implementation measurement** (Fable, executed): SEC-024's parked case 2 and case 3 were out of scope under
  choice C; SEC-020's "pre-Π" premise was wrong in direction and a projection-level withhold had no way to exist;
  SEC-025 had four leg kinds, not three, and the A2A leg cannot be bound without SEC-022's envelope.
- **Close panel after integration** (`docs/D-IMPL-370-CLOSE-REVIEWS.md`): Codex (diff only), Cursor, Fable. **No
  blocking finding on SEC-024, SEC-025 or SEC-028-F1.** **Two measured BLOCKING findings on SEC-020** (B1 the wrong
  baseline; B2 withheld decisions do not replay) plus a roster regression the orchestrator measured (B3). The corrective
  round closed all three and then measured the residual that parked the row. One SEC-025 disclosure Fable found missing
  was added to its migration note.

## 4. Regression on the integrated tree, measured by the orchestrator

| Suite | `61587828` (all four integrated) | `014f6e23` (SEC-020 reverted) |
| --- | --- | --- |
| the broad set (contracts, products, projection, replay, mcp, peering, crossproc, lints tests, invariants, deployment, surface) | 6277 passed, **3 failed** (two standing + B3) | **2 failed, 5823 passed, 1 skipped, 1 xfailed, 104 warnings in 223.94s (0:03:43)** |
| `tools.lints --all` | rc=0 | rc=0 |
| `mypy` | clean | Success: no issues found in 243 source files |
| `tools/docs_tests` | 320 passed | (unchanged files) |
| `tests/examples` (no estate) | 28 failed / 992 passed / 743 skipped, identical to the base | (unchanged by the revert) |

The two standing reds are the citation ratchet at 365 and the worktree child-process test, both red before this work.

## 5. Rulings needed

1. **SEC-020:** authorize one further round on the request-seed rule (render a withheld subject from the plan
   re-executed **without the request seed**; promote the same-fabric unequal-age case from xfail to required).
   The parked branch carries the replay rehydration fix (also repairs a pre-existing divergence for empty-finding
   products); it re-integrates with the row.
2. **SEC-017:** the concrete authorization proposal is still owed; nothing changed this batch.
3. **SEC-021-U1 / SEC-025-U1:** both wait on SEC-022's envelope design (the request-body limit and the peered
   child's question echo); SEC-022 is the natural next row.

## 6. Carried findings (named, not fixed)

- **SEC-024-C-01** one more wire site changed by the ruling (`http_api/routes/product.py` 400 detail loses
  `input_value=`); same class by name: `hitl/webhook.py`, `orchestration/claude_agent/driver.py`,
  `hitl_server.py`/`routes/hitl.py`; **C-02** `format_tb` emits source lines, `ExceptionGroup` not walked.
- **SEC-025-C-01** local/mcp legs bind the subject only; `asked_question` is resolver-authored; a child whose own door
  refused is not held to the question; `GrantBoundChildResolver` is now request-aware (reverses a `D-IMPL-340`
  recorded shape; disclosed).
- **SEC-028-F1** the ruled extras are a lint constant beside README; markers evaluate against the running interpreter.
- **Process:** executors' regression sets must include `tests/contracts` (B3 was found only by the orchestrator's broad
  run); two executor report writes were refused by the harness and relayed by the orchestrator.

## 7. Where the rounds went

Five executor rounds across four rows: three first rounds clean, SEC-020's two rounds both on the mechanism's
baseline. This is the first row where the defect was in the mechanism rather than the proof, and the first where the
close panel's measurement found the fix worse than the base in a realistic shape. The revert is the rule working.

## 8. Recommendation

Rule SEC-020's further round (§5.1) and run it with SEC-022 as the next batch, since SEC-022's envelope unblocks two
parked sub-items. **No further run is authorized by this report.**
