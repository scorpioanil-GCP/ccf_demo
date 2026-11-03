# CCF SDK — Developer & Engineer Guide

**New: [Context Skills](05-technical-reference/CONTEXT_SKILLS.md)** — how a bank agent is granted authority to ask a Context Product, with the SK-01 implementation and SME/Information Architect analysis. Current Fluree requirement: **4.2.4**.

**Latest tagged/qualified SDK release:** `v1.0.1` @ `a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**Current technical-reference baseline:** `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`

This documentation has two evidence lanes:

- **learning examples** stay pinned to their qualified/historical evidence unless a guide says otherwise;
- **technical/API/security reference** tracks current SDK `main` so the public surface and remediation behavior remain accurate.

## Choose your path

### 1. Client developer

[Hello World of CCF →](01-client-developer/README.md)

Learn ProductClient/Result, governed refusal, in-process/MCP and agent-harness consumption.

### 2. Context Product producer / data engineer

[Producer path →](02-context-product-producer/README.md)

Work through CP-00 → CP-24 using README → completed specification → spec-to-code → run/vary/refuse/validate.

### 3. Decision Replay

[Decision Replay →](03-decision-replay/README.md)

DR-01 covers served/refused reconstruction. DR-02 covers Assembly Mode 2 and governed model packaging.

### 4. Create a new Context Product

[Create Your Own →](04-create-your-own/README.md)

Standard → AI-assisted spec → Gate 1 → code generation → sabotage/validation → Gate 2.

### 5. Exact SDK/API/security reference

[Technical Reference →](05-technical-reference/README.md)

The current technical reference includes the post-v1.0.1 remediation/handoff surface.

## Current main surface

Current `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` has **243 public modules**, compared with **217** at v1.0.1.

The **26 modules added since v1.0.1** are:

- `ccf.controlplane.demonstration_serve_instant`
- `ccf.controlplane.temporal_boundary`
- `ccf.erasure`
- `ccf.erasure.approval`
- `ccf.erasure.contracts`
- `ccf.erasure.errors`
- `ccf.erasure.index`
- `ccf.erasure.store`
- `ccf.erasure.subject_match`
- `ccf.erasure.trust`
- `ccf.graph.governed_reader`
- `ccf.graph.leases`
- `ccf.hitl.approval_policy`
- `ccf.peering.issuance`
- `ccf.products.demonstration_clock`
- `ccf.products.subject_disclosure`
- `ccf.replay.provenance`
- `ccf.skills.wire_arguments`
- `ccf_runtime.erasure`
- `ccf_runtime.erasure.door`
- `ccf_runtime.mcp.agent_directory`
- `ccf_runtime.mcp.composed_product`
- `ccf_runtime.mcp.review_door`

See [Security and Authorization](05-technical-reference/SECURITY_AND_AUTHORIZATION.md), the [Current Public Surface Index](05-technical-reference/PUBLIC_SURFACE_INDEX.md), and [SDK Update Status](../SDK_UPDATE_STATUS.md).

> This reference tracks released SDK 1.0.2. The October 13 bank delivery remains a distinct build; see [SDK Update Status](../SDK_UPDATE_STATUS.md).
