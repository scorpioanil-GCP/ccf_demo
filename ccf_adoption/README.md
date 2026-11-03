# CCF Adoption

**Running examples:** [current setup, Fluree 4.2.4 and connection configuration](examples/CONFIGURATION.md).

**New: [Context Skills](05-reference/05-technical-reference/CONTEXT_SKILLS.md)** — how a bank agent is granted authority to ask a Context Product, with the SK-01 implementation and SME/Information Architect analysis. Current Fluree requirement: **4.2.4**.

Developer, engineer, architecture, and control documentation for the **Cognitive Context Fabric (CCF) SDK**.

**SDK release:** `v1.0.2` — `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)\
**Current technical-reference baseline:** `ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`

## Start here

- [Start Here](03-start-here/START_HERE.md) — concepts and orientation
- [Using the SDK](04-using-sdk/README.md) — guided developer workflows
- [Runnable Examples](examples/README.md) — banking demonstrations using the SDK
- [Developer & Engineer Guide](05-reference/README.md) — client, producer, Decision Replay, create-your-own, and technical reference

## Repository structure

```text
00-dataprep/        pre-education data preparation material
01-evidence/        supporting evidence and provenance
01-whitepaper/      whitepaper-derived material
02-overview/        source-derived architecture/design snapshot
03-start-here/      first-time reader path
04-using-sdk/       developer workflows
05-reference/       SDK learning and reference manual
examples/           runnable adoption examples and banking demonstrations
archive/            internal project history; not part of the learning path
```

Internal project plans/checkpoints are preserved under [`archive/project/`](archive/project/README.md). They are not part of the public learning sequence.

## Baseline policy

The documentation has two evidence lanes:

- **learning/history lane:** examples and design snapshots keep their stated qualified or inspected source pins when preserving that history matters;
- **release-reference lane:** technical/API/security reference and current run instructions track SDK `v1.0.2`; later main documentation supplies release disposition.

The source-derived design package under [`02-overview/`](02-overview/README.md) remains an Oct-9 static reconstruction unless a page explicitly says otherwise. Current implementation deltas are carried by the technical reference and [SDK Update Status](SDK_UPDATE_STATUS.md).

## Current surface

SDK 1.0.2 exposes **243 public modules**, versus **217** in v1.0.1. The generated [Public Surface Index](05-reference/05-technical-reference/PUBLIC_SURFACE_INDEX.md) and [API appendices](05-reference/05-technical-reference/api/README.md) are pinned to `5f85b389efe9e4b1de62e84a5af62ca4b2e12178`.

## Release and remediation status

SDK 1.0.2 is released. The register reports 27/30 security findings closed; SEC-013, SEC-020 and SEC-027 remain open. The prior bank delivery remains distinct, and deployment verification is not implied by this documentation refresh. See the [migration checklist](05-reference/05-technical-reference/MIGRATION_AND_LIMITATIONS.md).

See [Release Notes](RELEASE_NOTES.md) and [Current SDK changes and documentation baseline](SDK_UPDATE_STATUS.md).
