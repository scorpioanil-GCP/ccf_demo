# Migration and Delivery Limits — SDK 1.0.2

**Release:** `v1.0.2` at `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026).\
**Merged-main documentation inspected:** `2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe` (18 October 2026).

The release runtime, examples, configuration and public manifest are identical to the inspected main. The [1.0.2 release notes](https://github.com/drcastillo/ccf_code/blob/2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe/packaging/bank-controlled/RELEASE-NOTES-1.0.2.md) and [security register](https://github.com/drcastillo/ccf_code/blob/2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe/packaging/bank-controlled/OPEN-SECURITY-ITEMS.md) record the release decision and remaining limits. The October 13 bank build remains a separate delivery; a local package does not establish deployment or amend its license grant.

## Workflow stores and approval transports: required changes

| Component | Required for 1.0.2 | Failure or migration |
| --- | --- | --- |
| Custom `ConditionalStateStore` | Read-only `identity`: 64 lowercase hex characters from a CSPRNG, minted once per substrate, persisted with records and shared by all clients | Missing/malformed identity refuses engine construction. A copied durable store must refuse to open. Deliberate re-mint strands in-flight records, which need operator reconciliation outside the fabric |
| Path-backed store or queue declaring `process` | Exclusive lease taken before reading, held from open to close; expose `writer_lease()` | Refuse a second opener with `WriterLeaseHeld`. The engine checks the offered seam, not that the implementation actually takes the lease |
| Custom HITL transport | Atomic `enqueue` deduplication by `(tenant, event_key, product_content_hash)` and atomic `retire` of that exact fingerprint | Engine construction refuses a transport without `retire`; implement and test the behavior, not just a method stub |
| Verdict submission | Judge the request for the exact pause named by the submission as `claimed`, `pending` or `missing` | A claim/request for a different pause supplies no authority. A directly submitted pending verdict counts at resume only while its request is still waiting |
| Older durable suspended run | Invoke `WorkflowEngine.rebind_legacy_suspension`, then obtain a fresh approval | Old verdicts name the old hash and authorize nothing. No HTTP/MCP/CLI rebind endpoint exists |
| Custom refusal recorder over an agent-conditioned child resolver | Accept `agent_conditioning=` or compatible `**kwargs` | Otherwise construction refuses; both served and refused decisions must retain composing-agent evidence |

Rebind writes trace and state, files the fresh request, then retires the old fingerprint. Failure after the state write can leave a stale request ahead of the fresh one; the next resumption can restore a missing fresh request, but an operator may need `retire` to remove the stale request. An old approval already in flight can return a stale request to the queue; it cannot authorize the new suspension. The shipped in-memory store has no pre-upgrade records after restart.

The engine still requires `bind_approver_eligibility(control_plane)`. Custom transports must enforce the bound planes' eligibility before recording named-policy approval verdicts. Construction checks do not prove persistence, uniqueness, atomicity or eligibility enforcement. Run the [store/queue conformance suite](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/tests/conformance/test_gate_closure_and_conditional_write.py) against your implementation, and force race interleavings when testing atomic operations. The SDK supplies no durable approval-store implementation.

Read [HITL](HITL.md) for conflict and recovery limits. Escalations remain keyed to an execution and are not bound to a particular store.

## Evidence persistence and concurrent writers

Use `evidence_root=` for retained evidence and keep `scratch` temporary. cp-06C's launcher reads `CCF_REPLAY_EVIDENCE_ROOT`; this is a launcher setting, not an environment variable read by the SDK itself. Restart replay needs retained records, graphs, indexes and compatible configuration/code. Evidence discarded by the October 13 build cannot be recovered by an upgrade.

`FileArtifactStore` now locks the complete name-index read/modify/write and uses unique staging files. The lock blocks without a timeout and requires reliable `flock` on a local filesystem. This repair does not qualify arbitrary applications sharing one evidence root. Retention remains the operator's responsibility; no fsync guarantee prevents a power-loss gap between record and index. Back up SQLite files by copying, never by hard linking. See [Artifacts and Stores](ARTIFACTS_AND_STORES.md) and [Decision Replay](DECISION_REPLAY.md).

## HTTP clients and specification authors

The product route's scope-mapping denies return `404 subject-unavailable`, including an unmapped class, missing product-action scope and a held tenant not admitted by the scope mapping. Authentication failures remain `401`; missing tenant, unheld path tenant and a class outside the roster remain `403`. Other routes retain `403 request-unauthorized`. See [the mapping table](CLI_HTTP_OPERATIONS.md#product-route-denial-shaping).

Standard v0.3 section 9 and copied historical specifications retain the older unentitled-principal `403` row. Apply the current product-route mapping; the historical row is not an execution instruction.

## MCP artifact upgrades

Upgrade the artifact server first or with all clients. Keep mixed-version erasure requests disabled until the erasure door client is upgraded: an old door against a new server can admit a client twin of governed evidence; a new door against an old server refuses every address. Older `McpArtifactStore` clients can misreport a governed-resolution refusal as `McpServerUnreachable` instead of `ArtifactResolutionRefused`.

Declare the door's tenant-specific `artifact.subject.match` action/resource grant and matching server `ErasureTrust`. **MCP-backed erasure completion is unsupported**; complete through an in-process store. Remote naming refuses tenant-unfiled addresses, non-record governed evidence and client twins as `class-unverifiable`.

## Tested deployment and remaining limits

The bank configuration opens the governed cp-06C product door over MCP streamable HTTP on loopback, with a SQLite graph store and its SDK identity lock. **It constructs no workflow engine or approval queue.** Custom workflow migration obligations above do not describe components running inside this bank door.

The shared service credential identifies an entitlement cohort, not the individual employee behind an agent. Tenant-boundary protection does not turn caller-supplied `borrower_scope` into an authorization boundary. SEC-020 parts 1–3 are accepted for tested cp-06C only; SDK-wide SEC-020 stays open. The release register records **27/30 closed**, with **SEC-013, SEC-020 and SEC-027 open**. SEC-030 opacity is limited to protected MCP acquisition/resolution/emission, excluding entitlement, HTTP, standing resources, agent tools and HITL. See [security disposition](SECURITY_AND_AUTHORIZATION.md#current-security-disposition-and-exact-delivery-scope--17-october-2026).

## Example learners

Use [release setup and configuration](../../examples/CONFIGURATION.md), **Fluree 4.2.4**, explicit host ports and complete connection strings. Restore the [shared estate](../../00-dataprep/README.md) for estate-backed examples; disposable-fixture examples and the local covenant-review demonstration have separate prerequisites. Preserve demonstration clocks and declared temporal boundaries.

Use [SK-01](../02-context-product-producer/examples/SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md) for the supported YAML Context Skill pattern. The local covenant-review example demonstrates lower-level manual composition and is checked separately against this release. Videos have not been rerun against 1.0.2; use current READMEs for executable commands. Historical qualification results and embedded specification pins retain their original dates and scope.

## Platform and release-tool compatibility

The bank launcher/verifier and SDK-managed filesystem detection target Linux. macOS default paved openings refuse `WriterLeaseRequired` because `/proc/self/mountinfo` is absent; overlay/network filesystems are also outside automatic lock-directory selection. Use supported local Linux storage or an explicit private lock-directory declaration appropriate to the deployment. The older `verify_wheel.sh` expects a development-version commit suffix and rejects the correct `1.0.2` release stamp. See [host platform and release tooling](../../examples/CONFIGURATION.md#host-platform-and-release-tooling).
