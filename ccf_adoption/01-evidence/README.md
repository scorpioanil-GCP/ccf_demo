# Phase 1 — Evidence & Asset Inventory

This directory records the evidence map used to build the CCF adoption experience. It is not a copy of the source repositories. It is a traceability layer that identifies which source artifact supports which adoption concept, tutorial, diagram, or use case.

## Checkpoints

- **1A — CCF concept / diagram / graphics inventory**: `CCF_CONCEPT_ASSET_INVENTORY.md` — **APPROVED**
- **1B — SDK capability / public-surface inventory**: `SDK_CAPABILITY_INVENTORY.md` — **APPROVED WITH AMENDMENTS**
- **1C — Vault → dataprep → SDK-example lineage**: **READY FOR PHASE 1C REVIEW**
  - **1C.1 — lineage contract + canonical exemplar**: `LINEAGE_MODEL.md`, `FINANCIAL_SERVICES_LINEAGE_TEMPLATE.yaml`, `CP04_CANONICAL_LINEAGE.md` — **APPROVED**
  - **1C.2 — approved ladder mapping across CP-00 through CP-12**: `CP00_CP12_LINEAGE_MATRIX.md`, `CP00_CP12_LINEAGE.yaml` — **COMPLETE; advanced by user direction, merge pending Phase 1C close**
  - **1C.3 — gap / limitation / controls-governance review**: `GAPS_LIMITATIONS_CONTROLS.md`, `CP00_CP12_GOVERNANCE_REGISTER.yaml` — **READY FOR REVIEW**

Supporting manifests, maturity rules, and cross-phase constraints:

- `CCF_SOURCE_MANIFEST.yaml` — pinned `ccf` evidence baseline
- `CCF_CODE_SOURCE_MANIFEST.yaml` — pinned approved `ccf_code/main` evidence baseline
- `SDK_MATURITY_AND_BASELINE.md` — moving-SDK rules while the 24-example pressure-test program continues
- `FINANCIAL_SERVICES_EXAMPLE_REQUIREMENTS.md` — required business-first narrative, SME/data-engineer specification workflow, controls/governance personas, engineered-data limitation disclosure, and specification-template placement for Phase 1C and the later Financial Services Use Cases section
- `LINEAGE_SOURCE_MANIFEST.yaml` — pinned Vault, Dataprep and SDK snapshots used by Phase 1C
- `DATA_ESTATE_ONBOARDING.md` — approved Dataprep-estate onboarding posture for the assembler / Hello Context Product path

The four evidence repositories remain read-only:

- `drcastillo/ccf`
- `drcastillo/obsidian-vault`
- `drcastillo/ccf_dataprep`
- `drcastillo/ccf_code`

`drcastillo/ccf_adoption` is the only writable repository for this effort.
