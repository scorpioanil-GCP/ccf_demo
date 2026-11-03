# CLI and HTTP Operations

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

This page is for platform/operator use.

## CLI

The current runtime includes command families for agents, artifacts, backends, configuration, HITL, products, Replay, schemas, skills and workflows.

Remote credential handling is under `ccf_runtime.cli.credential`. Credential-resolution failure is explicit; do not silently fall back to an unauthenticated privileged request.

The installed proprietary distribution is `ccf-sdk`; the command remains `ccf`.

## HTTP authorization

The HTTP runtime joins:

- authenticated identity;
- resolved tenant;
- route action/resource declaration;
- authorization decision;
- action-specific capability.

Protected work is default-deny.

### Product-route denial shaping

The product route is special in one narrow way: its route declaration may set `answers_denial=True`.

On `GET /product/{tenant}/{product_class}/{version}`, every deny from the
scope mapping is returned as **`404 subject-unavailable`**, including a missing
product-action scope, an unmapped class, or a held tenant not admitted by the
scope entry's tenant pattern. The gate passes a `GateDenial` to the route, which
records it through `govern_scope_denial(...)`. This replaces the former
`403 request-unauthorized` for these cases.

| Condition | HTTP response |
| --- | --- |
| No credential, or an unrecognized credential | `401 unauthenticated` |
| Credential has no tenant; path tenant is not held; class is outside the product roster | `403` |
| Product-route scope-mapping deny, on any axis | `404 subject-unavailable` |
| Gate cannot mint a capability from an allow | `503` |
| Partial question, malformed parameters, or asked-at without a UTC offset | `400` |
| Asked-at cannot be parsed as a date-time | `422` |
| Authorizer denies another route | `403 request-unauthorized` |

The product refusal is uniform at minimal and reasoned disclosure; full disclosure
can expose its internal cause. The audit event names the failed scope axis; Replay
retains `unauthorized`, `tenant-unauthorized` and the authorization decision id,
without the axis. Pre-authorizer `401`/`403` failures create neither audit event
nor Replay record at this baseline.

**Specification erratum:** Standard v0.3 section 9, spec-generation guidance and
historical example specs retain the older `403` for an unentitled principal.
For the HTTP product route, use `404 subject-unavailable` for that condition;
the separate `403` cases above remain. Preserve the authored snapshots and apply
this migration note when implementing them.

The denial remains visible in audit/Replay. Other routes keep their normal gate-denial behavior.

Use:

- `GateDenial`;
- `denial_from_request(...)`;
- `RouteAuthorization.answers_denial`;
- `govern_scope_denial(...)`.

## Current error/refusal vocabulary

In addition to existing authentication/tenant/product/HITL errors, current runtime includes named codes for:

- `ERROR_EXECUTION_FENCED`;
- `ERROR_HITL_GATE_CLOSED`;
- `ERROR_ARTIFACT_STORE_UNAUTHENTICATED`;
- `ERROR_EVIDENCE_CLASS_SEALED`.

A governed product/evidence refusal should cross as a governed response/status mapping, not become an internal 500 merely because it is a refusal.

## Product MCP door

Current standard product-door options include:

- `open_door(...)`;
- `open_door_with_verifier(...)`;
- optional `expose_product_resource=True`;
- deployment-declared multi-principal entitlement;
- stdio single-principal serving.

For hand-composed products, use `compose_for_door(...)` rather than implementing a custom `ServesProducts` wrapper.

## Review door

`open_review_door(...)` exposes an authorized ReviewQueue surface through the standard HITL transport model.

Reviewer scopes are bound to event-key patterns. Approval/rejection is target-bound to the held review item.

## Artifact/evidence HTTP-MCP posture

Governed evidence reads check exact bytes/reference provenance, entitlement/disclosure and erasure state.

Current artifact protocols expose typed read/resolution/authentication failures. An artifact that exists physically is not automatically readable as governed evidence.

The MCP artifact server also exposes the ruled subject-match/door-naming tools used by erasure paths.

## Workflow resumption

A resumption can now return/raise current fencing and gate-state outcomes rather than relying only on the older "already resumed" intuition.

Important current types include:

- `WorkflowResumeRefused`;
- `ExecutionFenced`;
- `WorkflowTraceReferenceMismatch`;
- `HitlGateClosed` / gate-closure failures.

Operator clients should preserve these typed distinctions instead of collapsing them to a generic retry.

## Replay lookup

The CLI's Replay query/resolve commands retrieve retained evidence. Reconstruction still uses the Python Replay engine and its exact-pin/provenance checks.

## OpenAPI

Prefer the generated/current runtime contract over copied endpoint prose.

## Exact current shapes

Use the [Runtime API](api/runtime.md), [Replay API](api/replay.md), and [Security and Authorization](SECURITY_AND_AUTHORIZATION.md).

See [Migration and Delivery Limits](MIGRATION_AND_LIMITATIONS.md) for MCP upgrade and erasure constraints.

## Retained evidence commands

These commands belong to cp-06-canonical's `server/serve.py`, which integrates `ccf_runtime.cli.evidence`. They are separate from the existing `ccf replay` command that queries a running HTTP server. Run from the SDK root, using the **same persistent evidence directory that the door used**:

```bash
export CCF_REPLAY_EVIDENCE_ROOT='/absolute/path/to/retained-evidence'
export PYTHONPATH=src:runtime
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/server/serve.py decisions --involving 2549001IGRCG4F0RLD36 --since 2026-10-16 --until 2026-10-16 --json
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/server/serve.py why '<decision-address-or-prefix>' --json
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/server/serve.py replay '<decision-address-or-prefix>'
```

Replace the directory, dates and decision placeholder with retained evidence from your run. The directory must already exist, be owned by the process account, mode `0700`, writable, absolute and not a symlink. These commands require no running door and use `read_sources=False`; they do not ask a fresh question. A unique decision prefix must contain at least eight characters. Bare dates mean the local calendar day; output includes UTC and local time.

| Exit status | Meaning |
| --- | --- |
| `0` | Command answered |
| `2` | Malformed command/input |
| `3` | Required evidence unavailable |
| `4` | Replay did not reproduce |

`why` exposes privileged retained details, including information a minimal-disclosure caller may not see. See [Decision Replay](DECISION_REPLAY.md) for retention limits, incomplete questions and the remaining producer-setting requirement for composite replay.

## Declared source outage

A product-class seam binding with `cause: source-unavailable` now yields `SourceUnavailableRefusal`, HTTP **409**, fulfillment withheld. Its external statement says a source could not be reached and to retry later. The driver's detail is withheld below `full` disclosure. Matching uses an exact exception `module.QualName`; it does not import the named class or match subclasses. Under a declared early policy, this can still collapse to the constant `subject-unavailable` response. An unbound unexpected exception is not automatically a source-outage refusal.

Sources: [launcher](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-06-canonical-collateral-and-setoff-coverage/server/serve.py), [CLI module](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/runtime/ccf_runtime/cli/evidence.py), [source refusal](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/docs/surface-changes/383-05-source-unavailable-refusal.md).
