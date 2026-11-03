# CCF SDK design overview

**Static reconstruction source:** `ccf_code/main@f07e558ed04c81154687d7efcc6312591e7f6f7d` · **Inspected:** 2026-10-09.  
**Current-main overlay:** `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` · see [Current-main design delta](11_CURRENT_MAIN_DELTA.md).

These source-derived design documents explain the SDK architecture, module dependencies, class contracts and execution sequences at the Oct-9 reconstruction pin. Their immutable source links, counts and hash inventory are intentionally preserved rather than silently repinned after the implementation changed.

For current implementation behavior, read the overlay and the current technical reference.

## Design documents

| Document | What it explains |
| --- | --- |
| [CCF SDK architecture](01_ARCHITECTURE.md) | Oct-9 system responsibilities, data/control boundaries and delivery surfaces |
| [Module design and dependency map](02_MODULE_DESIGN.md) | Oct-9 core/runtime package map and import-derived inventory |
| [Core class and contract design](03_CORE_CLASS_DESIGN.md) | Consumer, product and producer class relationships at the snapshot |
| [Product assembly and refusal sequences](04_PRODUCT_ASSEMBLY_SEQUENCES.md) | Opening, acquisition, projection, gating, refusal and delivery at the snapshot |
| [Deployment and backend design](05_DEPLOYMENT_AND_BACKEND_DESIGN.md) | Configuration derivation, backend protocols and writer lifecycle at the snapshot |
| [Composite products and fabric peering](06_COMPOSITION_AND_PEERING_DESIGN.md) | Child requirements, retained evidence, CP14 and fabric peering at the snapshot |
| [Consumer and agent integration design](07_CONSUMER_AND_AGENT_INTEGRATION.md) | Client decoding, harness adapters and CP22 external A2A |
| [Replay, authorization and human-control design](08_REPLAY_AND_CONTROL_DESIGN.md) | Replay evidence, governed reads and human approval boundaries at the snapshot |
| [Example implementation design map](09_EXAMPLE_DESIGN_MAP.md) | Example trees as inspected on Oct 9 |
| [Source inventory and verification scope](10_SOURCE_INVENTORY.md) | Exact inspected source hashes, methodology and verification limits |
| **[Current-main design delta](11_CURRENT_MAIN_DELTA.md)** | **Architectural changes landed through `3f914416`** |

[Context Skills and retained replay design](12_CONTEXT_SKILLS_AND_REPLAY_DESIGN.md) adds current module, contract and sequence diagrams for SK-01 and D-IMPL-383/389.

## Suggested reading

Start with architecture/core classes, then read the current-main delta before applying the design to current code. Use the current [technical reference](../05-reference/05-technical-reference/README.md) for exact APIs and migration semantics.

## Scope and status

Documents 01–10 are a reproducible static design reconstruction, not a live-generated view. They do not declare security closure, example executability or release approval.

The current-main overlay covers the major architectural changes since that snapshot without falsifying the original AST/hash evidence.

The existing introductory video is retained. Business-to-spec companion documents remain in the reference examples index.
