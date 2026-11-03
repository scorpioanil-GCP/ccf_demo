# Phase 4 — Using the SDK

## Status

- **4A — Consumer path:** APPROVED
- **4B — Assembler path:** APPROVED
- **4C — Progressive tutorial:** APPROVED
- **4D — Advanced SDK concepts:** next

Checkpoint records:

- `CHECKPOINT_4A.yaml`
- `CHECKPOINT_4B.yaml`
- `CHECKPOINT_4C.yaml`

## Approved evidence baseline

Phase 4A–4C remain pinned to the approved SDK baseline:

- `drcastillo/ccf_code/main@374a36007bb2fda3e968a83c2ead7d84993c0b23`
- CP-13 gated and merged
- CP-14 composite Context Product work is active development and excluded from settled Phase 4A–4C claims

Dataprep evidence baseline:

- `drcastillo/ccf_dataprep/main@fcf7dddf79c7f443300d745e90bf39510ef12ab7`

## 4A result

The approved consumer path establishes that an adopter can consume an existing Context Product without learning producer internals, either through `ccf.client` or through an MCP-capable harness.

A corrective documentation amendment subsequently added source excerpts to `CONSUME_OVER_MCP.md` so the MCP integration is demonstrated directly rather than only described. That correction did not change the approved consumer architecture.

## 4B result

The approved assembler path teaches an adopter how to move from a real decision problem to a governed, testable Context Product without collapsing domain authority, data reality, SDK mechanism, and control evidence into one undifferentiated development task.

Key artifacts remain under `04-using-sdk/assembler/`.

## 4C result

The approved progressive tutorial is built around **CP-01 Counterparty Reference Snapshot**, the first real rung of the approved Context Product ladder.

Artifacts under `04-using-sdk/tutorial/`:

- `README.md` — tutorial purpose, anchor and learning sequence
- `CP01_PROGRESSIVE_TUTORIAL.md` — end-to-end tutorial with source excerpts and run/refusal/validation steps
- `TUTORIAL_SOURCE_MANIFEST.yaml` — pinned SDK/Dataprep evidence and explicit execution boundary

The tutorial covers:

1. restore and verify the portable Dataprep estate;
2. understand the decision and data reality before code;
3. read the approved SDK-level CP-SPEC;
4. inspect Control Plane and backend boundaries;
5. read the caller, assembler seam and governed fabric spine with source excerpts;
6. run the default served path;
7. run a Policy-driven governed refusal;
8. inspect TTL/freshness, Context Debt, lineage, content address and replay;
9. run deterministic correctness tests;
10. understand the example's known findings, synthetic-data limits and claims not proven.

## Cross-repo validation

The pinned Dataprep repository confirms that the portable verifier and v2 estate contain the `ccf_v2` relational substrate CP-01 depends on, including legal-entity/crosswalk landmarks and the jurisdiction-entitlement machinery used by the Policy example.

The adoption session did **not** independently rerun the private estate. The tutorial therefore distinguishes source-grounded runnable commands from an independently reproduced run result. A published release run should record the exact portable bundle snapshot and verifier result used.

## CP-14 boundary

CP-14 is expected to add the missing significant composite Context Product capability.

Approved Phase 4A–4C remain deliberately pre-CP-14:

- L4 operator composition is included;
- one Context Product is assembled end-to-end;
- composite Context Products are excluded;
- the current partial pre-CP-14 composition helpers are not presented as the final product-composition contract.

## Phase 4D

Phase 4D begins **Advanced SDK Concepts** on the same approved CP-00–13 baseline while the CP-14 change watch remains active.

Advanced material may cover established topics such as:

- operator composition and planning;
- Projection and role-conditioned interpretation;
- Context Half-life and Context Debt mechanics;
- Control Plane vs Data Plane;
- Decision Replay;
- policy/refusal semantics;
- deployment and transport extension seams;
- Assembly Modes and their current maturity boundaries.

Composite Context Products will be incorporated only after CP-14 is approved and merged.
