# SDK maturity and evidence baseline

> **Historical evidence:** the program status and capability labels below describe the stated source pin. Current main includes CP-00–CP-24 and SK-01; see [SDK update status](../SDK_UPDATE_STATUS.md) and [current example configuration](../examples/CONFIGURATION.md).

## Status

The CCF SDK is **not yet a frozen interface**. The example program is currently at **example 13 of 24**. The examples are intentionally more than demonstrations: each one pressure-tests the SDK against a different financial-services context-product problem and has repeatedly exposed missing capability, ambiguous semantics, or surface-area issues that were then corrected in the SDK.

The SDK has changed several times as a result of that pressure-testing. It is now beginning to settle, but the remaining examples may still expose additional gaps or require contract or surface changes.

This matters to the adoption project. The SDK inventory and reference-manual work must therefore distinguish between **observed current behavior** and **stabilized public contract**. Documentation must not turn today's implementation into a promise that later examples are still allowed to invalidate.

## Baseline for Phase 1B

Phase 1B begins from the latest **approved `ccf_code/main` baseline**, currently:

- repository: `drcastillo/ccf_code`
- branch: `main`
- commit: `1a04e565504f712350b51777cfe398be46d5e157`
- latest approved rung represented on that commit: CP-12 (`fx-post-trade-reconciliation`)

Work in progress for later examples is evidence of ongoing SDK stabilization, not yet authoritative adoption documentation.

## Inventory classifications

Every SDK capability inventoried in Phase 1B must carry one of these maturity labels:

- **STABILIZED** — exercised repeatedly across approved examples, guarded by tests/gates, and not currently known to be under redesign.
- **VALIDATED-CURRENT** — exercised by at least one approved example and backed by implementation/tests, but still subject to change as later examples pressure-test adjacent behavior.
- **PROVISIONAL** — present in the current SDK but insufficiently exercised by the completed example set to present as a settled adoption contract.
- **INTERNAL** — implementation detail that should not be taught as a public SDK surface.
- **DEPRECATED / SUPERSEDED** — retained only for compatibility or historical evidence and should not anchor new adoption material.

These labels describe documentation confidence, not code quality.

## Documentation rules while the SDK settles

1. **Pin every inventory pass to an exact `ccf_code` commit.** Never say only "current SDK."
2. **Use `main` as the approved evidence baseline.** Do not document behavior from an in-progress example branch as authoritative unless David explicitly directs otherwise.
3. **Separate tutorial prose from API promises.** Phase 4 may teach stable patterns early; Phase 5 reference material must wait for sufficient surface stability before presenting exact contracts as durable.
4. **Track example coverage.** For each capability, record which approved examples exercise it. A capability with no approved-example evidence cannot be labeled STABILIZED.
5. **Reconcile after SDK-changing examples.** If a subsequent example changes SDK behavior, mark affected adoption artifacts stale and update the inventory before advancing their documentation checkpoint.
6. **Do not copy stale prose forward.** Executable behavior and approved architectural decisions outrank prose written for earlier examples.
7. **Preserve historical traceability.** When a public contract materially changes, record the old baseline and the replacing baseline rather than silently rewriting the evidence record.

## Planned stabilization checkpoints

The adoption effort can proceed in parallel with the remaining SDK examples, but the work is intentionally asymmetric:

- architecture, product UX, source inventories, learning paths, and institution-neutral CCF concepts can advance now;
- SDK tutorials can advance capability-by-capability when the underlying pattern is sufficiently stable;
- the final Reference Manual API surface should not be declared complete until the example pressure-test program is substantially complete and a later checkpoint explicitly freezes the documentation baseline;
- Security & Assurance should assess a named SDK release/commit, never a moving branch.

## Interpretation

The remaining examples are not a blocker to beginning `ccf_adoption`; they are part of the evidence-generation process that makes the eventual adoption material credible. The documentation effort should converge with SDK stabilization rather than wait for it, while refusing to misrepresent a moving implementation as a frozen contract.
