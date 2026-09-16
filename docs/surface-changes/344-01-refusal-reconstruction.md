# 344-01 — retention follows admission; a refused composite reconstructs from its own store

Applied 2026-09-16 under `D-IMPL-344` (Dave's implementation GO with R-1/R-2/R-3 as proposed
and three corrections recorded verbatim in `docs/DECISIONS.md`; design in
`docs/D-IMPL-344-DESIGN.md`). The measurement that opened it: `CP14-F-32` — a composite that
admitted a child and then refused could not be replayed from the store that recorded it,
because admitted-child bytes were filed on the non-blocking composition path only while the
replay engine read them for every admitted row. *"Retention follows admission, not
composition success."*

## What did NOT change, stated first

- **The served path is byte-identical.** Retention moved one branch earlier in
  `GovernedResolver.__call__` and files the same bytes at the same addresses; `replay()`'s
  return type, its checks and their order are unchanged (`tests/replay` 180 passed;
  `D-IMPL-339`'s fresh-environment replay control unchanged).
- **No record field was added and no generation boundary moved.** A refused record has the
  shape it had; the only new artifacts are admitted-child contracts on refused exits, under
  the class `D-IMPL-339` already registered.
- **`replay()` on a refused record now fails by name** (`ReplayRecordKindMismatch`) where it
  failed before at a plan named `no-fabric-read`. No caller in the tree replays a refusal.

## ccf.replay.engine.replay_refusal

- Surface: ccf.replay.engine.replay_refusal
- Public surface: true
- Change type: added
- Before: absent — a refused decision had no reconstruction path; `replay()` reached `environment.resolve_plan("no-fabric-read")` and reported a missing plan
- After: the same prologue and child reconstruction as `replay()`, then the record's own no-read/no-product claims asserted and the refusal held to the child rows (before projection), or the recorded operator path re-derived and the refusal's evidence held to it with `rehydrate_product` never called (after projection)
- Why: D-IMPL-344 — a governed "no" must reconstruct from the record and the store with producers stopped, and storing the bytes alone did not make it so
- Migration: none; a refused record's caller uses `replay_refusal()` where it could not use `replay()` before

## ccf.replay.engine.RefusalReplayOutcome

- Surface: ccf.replay.engine.RefusalReplayOutcome
- Public surface: true
- Change type: added
- Before: absent — `ReplayOutcome` requires a `product`, so no verified reconstruction of a refusal could be represented
- After: the record, its address, the re-canonicalized refusal block, every admitted child's resolved address, and the snapshot id (`no-fabric-read` before projection); no `product` member exists on the type
- Why: D-IMPL-344 R-1 — a reconstructed refusal must not be readable as a served product one call downstream
- Migration: none

## ccf.replay.engine.ReplayRecordKindMismatch

- Surface: ccf.replay.engine.ReplayRecordKindMismatch
- Public surface: true
- Change type: added
- Before: absent — a refused record handed to `replay()` failed as `ReplayUnresolvable` naming a plan that never existed; a served record could not be refused by a refusal reconstruction
- After: raised by name, in both directions, after the record's bindings and resolution claim are verified and before anything is resolved or re-executed; also for a record contradicting itself about its kind
- Why: D-IMPL-344 — a *don't know* was being reported as a missing plan
- Migration: none; it subclasses `ReplayError`, so a caller catching the base is unaffected
