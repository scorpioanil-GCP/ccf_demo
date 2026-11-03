# SDK Overview

**New: [Context Skills](CONTEXT_SKILLS.md)** — how a bank agent is granted authority to ask a Context Product, with the SK-01 implementation and SME/Information Architect analysis. Current Fluree requirement: **4.2.4**.

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

The CCF SDK is a governed layer for assembling, serving and reconstructing decision-ready context.

## Core/runtime split

- `ccf` — contracts, fabric mechanisms, Control Plane, products, Replay, authorization, agents/HITL/peering/erasure seams;
- `ccf_runtime` — concrete HTTP/MCP/CLI surfaces, authorization gates, harness adapters, workflow/orchestration drivers, peering wires and erasure/review doors.

## L1–L6

| Layer | Package | Responsibility |
| --- | --- | --- |
| L1 | `ccf.signal` | typed source observations and ingress temporal checks |
| L2 | `ccf.assembly` | identity resolution and the single governed writer |
| L3 | `ccf.graph` | governed context state and snapshot-scoped readers |
| L4 | `ccf.operators` | read-only policy/temporal/similarity/traversal computation |
| L5 | `ccf.projection` | perspective-conditioned shaping |
| L6 | `ccf.products` | request/product contract, gates, refusal, composition and delivery |

Cross-cutting mechanisms include authorization, Control Plane/deployment, debt/half-life, Replay, HITL/workflow, peering, skills, erasure and client delivery.

## Current-main surface

Current `main` has **243 public modules** versus **217** in v1.0.1.

Major post-v1.0.1/current-main additions include:

- tenant temporal-boundary policy and trusted serve time;
- development-only declared demonstration serve instant;
- request subject/value floors and pattern domains;
- multi-principal declared product entitlement;
- deployment-declared agent skill grants;
- subject-withholding declarations and current SEC-020 probe/store controls;
- whole-artifact erasure plus subject-match/naming surfaces;
- governed record provenance and stronger stored-byte/reference integrity;
- per-entity invalidation records;
- writer leases, SQLite file-identity coordination and store-creation verification;
- signed HITL actions, approver eligibility, explicit gate closure and review door;
- missing-approval-request workflow recovery plus execution/trace fencing;
- signed peering issuance, signing-key-scoped nonce replay defense and ingress bounds;
- standard product-resource serving and `compose_for_door`;
- harness/Claude isolation and skill wire-argument validation;
- `ccf-sdk` distribution identity and the current fixed-delivery license.

See [SDK Update Status](../../SDK_UPDATE_STATUS.md).

## Consume

Use the `ccf.client` consumer API and treat a governed refusal as data, not as a transport failure. Exact current client signatures are in [Consumer API](api/consumer.md).

## Produce

The paved road remains:

approved spec → governed config/environment → acquisition/projection/debt/gate → `open_product(...)` → question/answer → retained evidence/Replay.

Current deployment declarations may also include entitlement, grants, temporal boundary and demonstration serve instant.

For a hand-composed governed product that still needs the standard MCP door, use `compose_for_door(...)`.

## Governance boundaries

A few rules are especially load-bearing on current main:

- authorization capability and Context Product policy are distinct;
- caller `asked_at` is not unrestricted fabric-clock authority;
- a `never` subject-withholding declaration needs a positive plan-factory declaration;
- content addressing requires checking the bytes/reference at the relevant reader/writer seam;
- registry/store existence is not the same as governed evidence provenance;
- a human verdict is not sufficient without event, eligibility, attestation and gate-state binding;
- development demonstration time is not a production override;
- release qualification and current-main documentation are separate.

## Package/license identity

The installed distribution is **`ccf-sdk`**; imports remain `ccf` and `ccf_runtime`, and the CLI remains `ccf`.

Current SDK root `LICENSE.md` fixes the delivered source/wheel in its Schedule A. This current-main reference can track later code for pre-education without altering that fixed delivery record.

## Current vs released

The technical/API/security reference tracks the SDK 1.0.2 release tag; the inspected merged main has identical runtime code.

SDK 1.0.2 was released on 17 October 2026 with disclosed open items and an accepted local release check. See [migration and delivery limits](MIGRATION_AND_LIMITATIONS.md).
