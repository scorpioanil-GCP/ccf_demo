# Phase 4 SDK Change Watch

## CP-14 — Composite Context Products

**Status:** major capability under active development in `ccf_code`; not yet an approved adoption baseline.

David identified CP-14 as exposing a significant omission in the initial SDK design: **composite Context Products**. The changes now being developed are expected to materially expand the product rather than simply add another example.

## Documentation ruling

Until CP-14 reaches the normal approval / merge gate:

- Phase 4 remains pinned to approved `ccf_code/main@374a36007bb2fda3e968a83c2ead7d84993c0b23` (CP-13 gated and merged).
- The assembler learning path teaches construction of an individual Context Product using evidence through CP-13.
- **Composite Context Products are not taught as a settled feature.**
- Existing `ccf.products.composition` behavior on the approved baseline is treated as **partial mechanism**, not the complete composite-product contract.
- L4 **operator composition** is a separate concept and must never be presented as composite Context Product composition.
- Reference Manual material for product composition remains PROVISIONAL until the CP-14 design, API, debt semantics, lineage semantics, request/serve behavior, controls, and tests are approved.

## Why this is a hard boundary

The approved baseline already contains three partial aggregate rules in `ccf.products.composition`: N-way lineage union, TTL floor, and mixing refusal. It explicitly does **not** implement aggregate Context Debt because the aggregate-product surface did not yet exist. CP-14 is therefore expected to close or reshape a previously deferred architectural surface.

Documentation written from the pre-CP-14 code would risk turning an incomplete mechanism into a public contract. We will not do that.

## Reconciliation trigger

When CP-14 is gated and merged to `ccf_code/main`:

1. pin the new approved commit;
2. inventory the new composite-product surface and tests;
3. compare it against this pre-CP-14 boundary;
4. update Phase 4 advanced material and Phase 5 reference coverage;
5. identify whether any Phase 3 conceptual wording or Phase 6 Financial Services examples should expose composition;
6. add a dedicated composite Context Product tutorial only after the capability is stable enough to teach.

This change watch is intentionally separate from the current Phase 4B assembler path so the project can proceed through the substantial approved evidence already available in CP-00 through CP-13.