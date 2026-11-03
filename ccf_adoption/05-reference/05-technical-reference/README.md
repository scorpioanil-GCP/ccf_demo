# Technical Reference

**New: [Context Skills](CONTEXT_SKILLS.md)** — how a bank agent is granted authority to ask a Context Product, with the SK-01 implementation and SME/Information Architect analysis. Current Fluree requirement: **4.2.4**.

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Use this section when you already know the task and need exact SDK behavior.

> The technical reference tracks current `ccf_code/main`. Historical learning examples and the Oct-9 source-derived design snapshot retain their stated pins unless explicitly refreshed.

## Core reference

- [SDK Overview](SDK_OVERVIEW.md)
- [Consumer API](CONSUMER_API.md)
- [Context Products](CONTEXT_PRODUCTS.md)
- [Assembly and L1–L6](ASSEMBLY_AND_LAYERS.md)
- [Graph and Storage](GRAPH_AND_STORAGE.md)
- [Operators and Projection](OPERATORS_AND_PROJECTION.md)
- [Similarity](SIMILARITY.md)
- [Half-life and Context Debt](HALFLIFE_AND_DEBT.md)
- [Control Plane](CONTROL_PLANE.md)
- [Deployment and Configuration](DEPLOYMENT_CONFIGURATION.md)
- [Artifacts and Stores](ARTIFACTS_AND_STORES.md)
- [Security and Authorization](SECURITY_AND_AUTHORIZATION.md)
- [Decision Replay](DECISION_REPLAY.md)

## Integration reference

- [Agents, Harnesses, and Orchestration](AGENTS_HARNESSES_ORCHESTRATION.md)
- [HITL](HITL.md)
- [Peering, MCP, and Runtime](PEERING_MCP_RUNTIME.md)
- [CLI and HTTP Operations](CLI_HTTP_OPERATIONS.md)

## Exact current surface

- [Current Public Surface Index](PUBLIC_SURFACE_INDEX.md)
- [Generated API Signatures](api/README.md)

Current `main` surface manifest: **243 public modules**.  
v1.0.1 surface manifest: **217 public modules**.  
Modules added since v1.0.1: **26**.

Use the generated API pages for exact names and shapes; use the prose pages for semantics, migration and security posture.

## Support

- [Migration and Delivery Limits](MIGRATION_AND_LIMITATIONS.md) — HTTP codes, HITL exceptions, MCP upgrades, and controlled-delivery scope
- [Refresh Evidence and Migration Scope](REFRESH_EVIDENCE.md)
- [Quick Reference](QUICK_REFERENCE.md)
- [Historical → Paved Road](HISTORICAL_TO_PAVED_ROAD.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Glossary](GLOSSARY.md)

## Release status

This reference tracks released SDK **v1.0.2**. The earlier bank delivery and its verification remain separate. Release status remains recorded in [Release Notes](../../RELEASE_NOTES.md).

## Latest refresh

The current-main behavior and governance posture are summarized in [SDK Update Status](../../SDK_UPDATE_STATUS.md). See [Refresh Evidence](REFRESH_EVIDENCE.md) for the comparison and verification scope.
