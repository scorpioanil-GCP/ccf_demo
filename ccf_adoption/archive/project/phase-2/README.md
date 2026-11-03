# Phase 2 — Information Architecture & Product UX

## Status

- **2A — Information architecture:** APPROVED
- **2B — Visual direction:** APPROVED — dark enterprise direction
- **2C — Prototype / reusable page system:** APPROVED WITH AMENDMENTS
- **Checkpoint 2 — Experience Approval:** APPROVED WITH AMENDMENTS

See `CHECKPOINT_2.yaml` for the approval record and amendments.

## Phase 2A artifacts

- `INFORMATION_ARCHITECTURE.md`
- `LEARNING_PATHS.md`
- `PAGE_SYSTEM.md`
- `NAVIGATION_MODEL.yaml`

## Phase 2B artifact

- `SELECTED_VISUAL_DIRECTION.md` — records the explicitly approved dark enterprise direction that superseded the earlier light exploration.

## Approved IA decisions

1. The user-facing portal must not mirror repository layout.
2. Use seven primary destinations: `Start Here`, `Learn CCF`, `Build with CCF`, `Reference`, `Financial Services`, `Govern & Operate`, `Adopt CCF`.
3. Whitepaper and overview video are prominent resources, not isolated top-level navigation dead ends.
4. `Build with CCF` separates **Consume** and **Assemble** routes.
5. The assembler route starts with the decision, SME/data-engineer collaboration, specification, and data-estate readiness before implementation.
6. Controls/governance are a first-class learning path and an embedded persona in Financial Services examples.
7. Data Environments live under `Govern & Operate` but are linked contextually before any tutorial/example that requires the estate.
8. Reference is version-pinned and separate from tutorial prose.
9. Financial Services examples are business-first and evidence-rich.
10. Security assurance remains distinct from demonstrated control mechanisms.

## Approved Phase 2C experience model

The prototype validated the experience structure across:

- approved dark landing page and primary navigation;
- L1–L6 architecture-led hero;
- direct resource strip for overview, whitepaper, architecture, SDK, examples, and Context Products;
- audience entry cards for developers, Financial Services, and evaluators;
- horizontal Financial Services example catalog;
- assembler tutorial / specification-workflow page;
- SDK Reference page;
- Financial Services use-case page;
- Data Reality / Control Demonstrated / Boundary / Not Proven components;
- responsive CSS and basic navigation / carousel wiring.

Phase 2 approval is approval of the **experience model**, not content or link completeness. Deep links that point to content not yet authored will be completed as Phases 3–8 create those destinations.

## Amendments carried forward

1. **Link completeness:** not all Phase 2 prototype links are final. Placeholder/deep links are replaced when their authoritative content is built.
2. **Browser verification:** formal Product Design cloud-browser interaction and console verification remains outstanding because the Work runtime blocked the local preview surface. This must be closed before final release approval.
3. **Production imagery:** prototype imagery is directional; authoritative CCF diagrams and source-controlled assets are preferred for the production portal where available.

Supporting records:

- `CHECKPOINT_2.yaml`
- `prototype/README.md`
- `prototype/PROTOTYPE_STATUS.md`
- `prototype/design-qa.md`

## Framework finding

The selected page system works without a heavy application framework. **MkDocs Material remains a viable production candidate with custom theme/component overrides**; its stock theme alone would not reproduce the approved landing/use-case experience.

## Next

Phase 3 builds the **Start Here / CCF Story** front door using the approved IA, visual system, and Phase 1 source evidence.
