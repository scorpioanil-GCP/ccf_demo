# Phase 5 Release Readiness

**Adoption branch:** `decision-replay-finalize`  
**Qualified SDK:** `drcastillo/ccf_code/main@ff470d400976815e9a1e49176ca51f97e4e691b1`

## Release scope

The documentation now covers:

- client consumption;
- Context Product production CP-00 through CP-24;
- spec-first example walkthroughs;
- AI-assisted new-product creation;
- Control Plane/runtime/governance/reference APIs;
- Decision Replay DR-01;
- Assembly Mode 2 DR-02;
- generated public-surface/API reference.

## Decision Replay

Status: **complete**.

The old Replay-deferred publication boundary is closed.

## Mechanical SDK reference

- current committed public-surface manifest: **208 modules**
- Replay: included
- Replay runtime lookup: included
- API signature appendices regenerated from the current manifest

## Final QA gates

Before promotion:

- [x] all relative links under `05-reference` resolve — 76 Markdown files checked, 0 broken;
- [x] no current release-facing page under `05-reference` references the old path numbering;
- [x] no current release-facing page says Decision Replay is deferred;
- [x] DR-01/DR-02 source, specification and validation paths were verified at the pinned SDK commit;
- [x] branch containment checked before promotion; branch is not behind `ccf_adoption/main`.

## Known external cleanup

The adoption documentation is correct against current code/tests/examples.

The SDK-native Replay how-to/anatomy prose still contains one stale statement about private `_operator_parameters`. Because `ccf_code` is read-only here, correcting that source wording is outside this branch and should be completed by the SDK release owner.

## Promotion

**APPROVED FOR NON-DESTRUCTIVE PROMOTION TO `main`.**
