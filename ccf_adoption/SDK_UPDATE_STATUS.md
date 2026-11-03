# SDK 1.0.2 documentation baseline — 18 October 2026

**Runtime/examples/API:** `v1.0.2` at `5f85b389efe9e4b1de62e84a5af62ca4b2e12178`.\
**Merged main and release documentation:** `2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe`.\
**Previous adoption source pin:** `3f914416e9e85cb348d20659d80f3c7e2d3685e6`.

The inspected merged main has the same SDK source, runtime, examples and configuration as the release tag. Later changes are handoff, planning, license explanation and release documentation. Keep executable examples pinned to the tag rather than building a post-tag development version from main.

## Changes reconciled

- **All 243 public modules** regenerated from the release manifest. Four existing module entries changed since the prior pass; no module was added. State identity exports, `WorkflowStateRecord.state_store_identity` and `workflow_request_retired` are included.
- **Workflow compatibility:** permanent store identity, lifetime leases for process-scoped path-backed stores/queues, atomic per-pause enqueue and `retire`, exact-pause verdict checks, and legacy rebind/fresh approval. See [migration requirements](05-reference/05-technical-reference/MIGRATION_AND_LIMITATIONS.md).
- **Evidence persistence:** the file name-index race is repaired; blocking lock, filesystem and durability limits remain explicit.
- **32 SDK example guides**, two supporting producers and the local covenant-review example use the release execution baseline. Fluree remains **4.2.4**; complete DSNs, explicit ports and producer credentials remain required.
- **25 analysis companions and HTML copies** carry current implementation walkthroughs while retaining historical specification/standard/recipe bytes. New authoring prompts target 1.0.2.
- **Bank-deployment correction:** cp-06C's product door constructs no workflow engine or approval queue. Caller-provided borrower scope is not authorization. Recorded videos have not been rerun on this tag.

## Release and delivery status

The release register reports **27/30 security findings closed**; **SEC-013, SEC-020 and SEC-027** remain open. SEC-020 parts 1–3 are accepted for tested cp-06C only, and SEC-030 has a limited MCP scope. The release was authorized under D-IMPL-392; no hosted CI run exists for it. See [source notes](https://github.com/drcastillo/ccf_code/blob/2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe/packaging/bank-controlled/RELEASE-NOTES-1.0.2.md) and [security boundaries](05-reference/05-technical-reference/SECURITY_AND_AUTHORIZATION.md#current-security-disposition-and-exact-delivery-scope--17-october-2026).

October 13's delivered wheel and license Schedule A are unchanged. Preparing a local package does not establish delivery, deployment, video access or a written license extension. The distribution record must identify the actual packaged wheel hash and validation performed.

## Verification

The documentation/configuration checks and nine local covenant-review tests pass. A targeted Linux release-source run passed **150 tests, with 2 expected skips**; the original D-IMPL-392 wheel also passed 13/13 installation checks on macOS and Linux and a two-process retained-replay check. Its checksum exactly matches the release record. See [refresh evidence](05-reference/05-technical-reference/REFRESH_EVIDENCE.md) for artifact identities, initial environment failures and test scope. These checks do not qualify the full private estate. The [source/configuration inventory](examples/SDK_BASELINE.json) separates current execution from historical qualification.
