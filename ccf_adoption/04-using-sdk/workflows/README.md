# AI-Assisted Developer Workflows

These workflows show how to use an AI assistant in **Cowork** to create a Context Product without transferring authority to the model.

## The operating rule

> **SME + data engineer settle the design. AI helps turn the settled design into a rigorous, reviewable, falsifiable specification and then helps generate code from the approved specification.**

An AI assistant may:

- organize evidence;
- identify missing terms;
- draft specification prose from supplied authoritative sources;
- check the Standard for completeness;
- map approved spec sections to SDK configuration/code;
- generate boilerplate and domain adapters;
- compare implementation with the spec;
- generate tests from acceptance criteria;
- identify deviations and gaps.

An AI assistant may **not** invent:

- the business decision;
- scope;
- policy;
- source-system reality;
- ontology bindings not established by evidence;
- freshness/half-life calibration;
- Debt thresholds;
- entitlement grants;
- unsupported SDK behavior.

Unknown authority-owned terms stay `[TBC — owner]`.

## Workflows

1. [Cowork Spec-to-Code](COWORK_SPEC_TO_CODE.md) — complete end-to-end operating model.
2. [Spec Drafting Prompt](AI_SPEC_PROMPT.md) — reusable prompt for Gate-1 specification work.
3. [Code Generation Prompt](AI_CODEGEN_PROMPT.md) — reusable prompt for implementation after Gate 1.
4. [Independent Validation Prompt](AI_VALIDATION_PROMPT.md) — reviewer prompt for spec/code/gate comparison.
5. [Spec-to-Code Map](SPEC_TO_CODE_MAP.md) — where each approved spec section lands in the modern paved-road implementation.
6. [Worked Paved-Road Shape](PAVED_ROAD_CODEGEN_EXAMPLE.md) — minimal source shape based on qualified canonical examples.

## Recommended Cowork sessions

Use separate sessions/work units for:

- **Spec authoring**
- **Implementation**
- **Validation/review**

The validator should begin from the approved spec and current tree, not from the implementation assistant's narrative of what it intended to do.
