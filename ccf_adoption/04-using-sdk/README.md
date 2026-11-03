# Build with CCF — Using the SDK

**Running examples:** [current setup, Fluree 4.2.4 and connection configuration](../examples/CONFIGURATION.md).

**New: [Context Skills](../05-reference/05-technical-reference/CONTEXT_SKILLS.md)** — how a bank agent is granted authority to ask a Context Product, with the SK-01 implementation and SME/Information Architect analysis. Current Fluree requirement: **4.2.4**.

## Status

Approved learning foundation:

- **4A — Consumer path:** APPROVED
- **4B — Assembler path:** APPROVED
- **4C — Progressive tutorial:** APPROVED

The **qualified learning baseline** remains CCF SDK v1.0.1 (`a4cf2fb7`). The **current technical/API/security baseline** is `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`.

The earlier Phase 4 pages remain learning material tied to their recorded evidence snapshots. For code you intend to run against current `main`, use [SDK Update Status](../SDK_UPDATE_STATUS.md) and the [current technical reference](../05-reference/05-technical-reference/README.md) for the migration delta.

## Two developer paths

### Consume a Context Product

A consumer wants a governed answer without learning producer internals.

See:

- `consumer/`
- [current Consumer API reference](../05-reference/01-client-developer/README.md)

### Assemble a Context Product

An assembler owns the product design, source reality and domain-specific implementation while the paved-road SDK owns the invariant-heavy governed path.

Approved learning foundation:

- `assembler/DATA_ESTATE_SETUP.md`
- `assembler/DECISION_TO_SPEC.md`
- `assembler/ASSEMBLY_MODEL.md`
- `assembler/VALIDATE_AND_SERVE.md`
- `tutorial/CP01_PROGRESSIVE_TUTORIAL.md`

For new development against the stabilized SDK, also use:

- [Cowork Spec-to-Code workflow](../05-reference/04-create-your-own/07-end-to-end-cowork-workflow.md)
- [Spec Drafting Prompt](../05-reference/04-create-your-own/02-ai-assisted-spec.md)
- [Code Generation Prompt](../05-reference/04-create-your-own/04-ai-assisted-codegen.md)
- [Independent Validation Prompt](../05-reference/04-create-your-own/05-validation-and-gate2.md)
- [Spec-to-Code Map](../05-reference/04-create-your-own/03-spec-to-code-map.md)
- [Paved-Road Codegen Example](../05-reference/04-create-your-own/06-paved-road-codegen-example.md)

## Modern implementation rule

**Spec first. Gate 1. Then generate against the paved-road surface of the SDK commit you are actually using.**

For implementation structure, prefer canonical current examples such as CP-03C/CP-04C/CP-06C/CP-13C rather than copying frozen historical specimens.

## Decision Replay

Decision Replay is supported in the qualified release baseline. Use the [Decision Replay guide](../05-reference/03-decision-replay/README.md) for the DR-01 and DR-02 developer examples.

See the archived [Decision Replay closure record](../archive/project/phase-5/DECISION_REPLAY_CLOSURE.md) for the qualification history.

## Current SDK compatibility

For current SDK installation and API behavior, read [SDK update status](../SDK_UPDATE_STATUS.md) and the [technical reference](../05-reference/05-technical-reference/README.md). The SDK distribution is `ccf-sdk`; imports remain `ccf` and `ccf_runtime`. Historical learning guides retain their qualification pins. Security approvals on an integration branch do not establish behavior in the main checkout you deploy.
