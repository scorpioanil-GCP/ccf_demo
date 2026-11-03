# Release Notes

## SDK 1.0.2 adoption update — 18 October 2026

**Released SDK:** `v1.0.2`, `5f85b389efe9e4b1de62e84a5af62ca4b2e12178`. The merged main inspected at `2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe` has identical runtime/examples/configuration.

This update reconciles all 243 public manifest modules and the example/configuration inventory, documents new workflow identity/queue contracts and legacy suspension migration, and adds the evidence name-index locking behavior and limitations. It preserves earlier qualification records and embedded source specifications. Fluree remains pinned to **4.2.4**.

The release register reports **27/30 closed**, with **SEC-013, SEC-020 and SEC-027 open**, and records the explicit release override and absence of hosted release CI. October 13's delivered build remains separate. See [current status](SDK_UPDATE_STATUS.md), [migration requirements](05-reference/05-technical-reference/MIGRATION_AND_LIMITATIONS.md) and [verification evidence](05-reference/05-technical-reference/REFRESH_EVIDENCE.md).

The older refresh below describes its state at the time; its candidate/unreleased wording does not describe 1.0.2's present release status.

---

## Documentation refresh — 17 October 2026

**Current SDK source reference:** `3f914416e9e85cb348d20659d80f3c7e2d3685e6`. This is an unreleased current-main documentation baseline. The latest tagged/qualified release documented here remains **v1.0.1**, `a4cf2fb74af4964dcfee29d210d17d94b909d78d`.

- Added the Context Skills reference and SK-01 implementation / SME–Information Architect analysis, including exact declarations, producer question mapping, over-reach refusal and evidence limitations.
- Added a root `examples/context-skills/` entry point and incorporated the companion into the HTML review collection.
- Updated durable replay, inspection commands, source-free opening, composite reconstruction and `source-unavailable` refusal guidance.
- Updated Fluree setup to **4.2.4**, including the starter Docker command and current-vs-historical annotations in the analysis editions.
- Regenerated all API appendices: **243 public modules**, versus 240 at the previous documentation pin and 217 in v1.0.1. Three new modules are `ccf.replay.evidence`, `ccf.replay.inspection` and `ccf_runtime.cli.evidence`; seven existing manifest entries changed.
- Updated scoped SEC-020/SEC-030 disposition and added architecture diagrams for Context Skills and retained replay.

### Example and configuration reconciliation

The follow-up audit aligns every CP runbook with the SDK's explicit-port and complete-DSN guidance. It fixes CP-14's missing producer demonstration configurations, documents separate producer terminals for CP-14/20, and expands CP-21/22's credential settings. The current [configuration guide](examples/CONFIGURATION.md) and [example inventory](examples/SDK_BASELINE.json) also make the required SDK branch explicit.

All 25 copied implementation walkthroughs were synchronized in Markdown, standalone HTML and the master collection while preserving historical SDK source excerpts. Source manifests distinguish their original evidence pins from current execution. The local covenant-review example was rerun against `3f914416`: nine tests pass and the console transcript is unchanged. No live estate qualification is claimed.

### Build and security status

The pinned [SDK register](https://github.com/drcastillo/ccf_code/blob/3f914416e9e85cb348d20659d80f3c7e2d3685e6/packaging/bank-controlled/OPEN-SECURITY-ITEMS.md) reports **25 of 30 security findings closed, 5 open**. SEC-020 parts 1–3 are closed only for the tested cp-06C deployment; SEC-020 remains open SDK-wide. SEC-030 is closed only for the protected MCP tool and address-form template acquisition/resolution and emission path. See [Security and Authorization](05-reference/05-technical-reference/SECURITY_AND_AUTHORIZATION.md) for exclusions.

The delivered source `01fc424d92f8d15856d5f277e9cf18ef59bc7883`, wheel `ccf_sdk-1.0.2.dev1564+g01fc424d9-py3-none-any.whl`, contains neither repair. The replacement candidate `ccf_sdk-1.0.2.dev1608+gd5c98f45a` contains both but is recorded as **not delivered/deployed**. Its SHA-256 is `fed7e86f2731b3e8e6593341af016fbd07ef99cdca0b6ffce8dd774e52d5ad65`. Current main has later composite replay changes beyond the candidate. The fixed source commit in license Schedule A is not changed by this documentation refresh.

Existing HTTP scope mapping, HITL exceptions, shared-credential limits and unsupported MCP-backed erasure completion remain documented in [Migration and Delivery Limits](05-reference/05-technical-reference/MIGRATION_AND_LIMITATIONS.md). Source reconciliation does not constitute release qualification or an independent security retest.

See [SDK Update Status](SDK_UPDATE_STATUS.md) and [Refresh Evidence](05-reference/05-technical-reference/REFRESH_EVIDENCE.md). The CP source snapshots and Oct-9 design inventory preserve their original pins; `archive/` is unchanged.

---

## CCF SDK v1.0.1

**Tagged SDK commit:** `a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**Release status:** qualified **RELEASE GO** on 2026-09-25

v1.0.1 is the security-hardening release that follows v1.0.0.

### Security architecture

The principal change is **authorization as a capability**:

> unauthorized work is made unrepresentable through governed SDK/runtime handles rather than relying on every caller to remember a separate authorization check.

The release adds and hardens:

- typed `Authorized` capabilities bound to tenant, principal, action, resource, and decision identity;
- action-specific authorization types under `ccf.authz`;
- default-deny HTTP and MCP authorization gates;
- tenant-safe capability propagation into registry, artifact, workflow, HITL, grant, Replay, and composition paths;
- route authorization declarations and a total HTTP authorization gate;
- server-attested approval/action paths;
- remote CLI credential resolution;
- tenant resolution/refusal semantics;
- public-surface coverage for the new authorization model.

See [Security and Authorization](05-reference/05-technical-reference/SECURITY_AND_AUTHORIZATION.md).

### Public surface

The committed v1.0.1 surface manifest contains **217 public modules**.

The adoption API appendices and public-surface index are generated from:

`docs/surface/v0.2-surface.json` at `a4cf2fb74af4964dcfee29d210d17d94b909d78d`.

### Decision Replay

Decision Replay remains part of the release baseline.

The v1.0.1 qualification evidence records:

- Replay suite: 201 passed;
- DR-01: 4 passed;
- DR-02: 9 passed standalone and 17 passed after the predecessor import case.

Use:

- [DR-01 — Replay a Governed Determination](05-reference/03-decision-replay/DR01_REPLAY_A_GOVERNED_DETERMINATION.md)
- [DR-02 — Package a Context Product](05-reference/03-decision-replay/DR02_PACKAGE_A_CONTEXT_PRODUCT.md)

### Qualification posture

The tagged candidate `a4cf2fb7` was qualified in a fresh detached worktree and ruled **RELEASE GO**.

The qualification record also preserves explicit residuals and distinguishes tests that were not executed from tests that passed. The canonical census-posture run contains the documented R10 non-pass population; dedicated backend legs and focused release suites provide the release evidence.

### SDK-source cleanup items

Two release-metadata/documentation inconsistencies remain in the read-only SDK repository and should be corrected there:

1. `pyproject.toml` at the v1.0.1 tag still declares `version = "0.1.0"`.
2. `public/how-to/reconstruct-a-governed-determination.md` and `public/concepts/replay-anatomy.md` still describe the retired private `GovernedResolver._operator_parameters` dependency. Current `RecordedEnvironment` uses public `operator_parameters(...)`.

The adoption documentation follows the qualified implementation and does not repeat the stale Replay claim.
