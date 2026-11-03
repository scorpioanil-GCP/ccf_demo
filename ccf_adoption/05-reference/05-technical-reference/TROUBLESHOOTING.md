# Troubleshooting Guide

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

## “The product refused; is it broken?”

Not necessarily. Refusal is often the expected governed answer.

Inspect the refusal kind/reason, request identity, Replay reference, disclosed evidence and policy bindings. Do not read the payload as though a refused result were served.

## “My dated demo is refused”

For a current paved-road demonstration:

1. declare `demonstration_serve_instant`;
2. declare a compatible `temporal_boundary`;
3. pass **no custom clock** to `open_product`;
4. use the SDK's supported development-store/backend posture.

A custom clock beside the declaration intentionally raises a demonstration-clock conflict.

Do not use this to move production time.

## “My multi-principal product door only serves one principal”

Move the entitlement policy into `ccf_config.yaml -> product_entitlement`.

The standard door composes over that declaration. Deployment code should not try to register the policy by minting its own composition capability.

## “My composite declares a skill but it is not in force”

A declaration under `skills:` is not automatically a grant.

List the skill under `grants:`. The governed ledger still judges policy compatibility/approval and can raise `DeclaredGrantRefused`.

## “EvidenceAfterDecisionRefusal appeared”

Evidence dated after the decision instant reached debt/scoring. Current main returns a governed refusal rather than propagating `TemporalOrderError`.

Fix the evidence/question timeline; do not catch the refusal and score the future evidence anyway.

## “A never-withholding class refuses at construction”

`subject_withholding: never` requires the deployment plan factory to positively declare `withholds_no_subject() -> True`.

Silence intentionally refuses. Only make the declaration if no projection the factory can build withholds the subject.

## “PopulationReadInSubjectKeyedPhase / UnheldSubjectProbeIsHeld”

Current SEC-020 defenses probe the subject-keyed acquisition before the real subject.

- Move subject-independent/population acquisition into the population phase.
- Ensure the probe identifier truly names nothing.
- Or supply the ruled early-policy/non-withholding design where appropriate.

Do not special-case the probe identifier in a source; that defeats the assumption being tested.

## “My SQLite database refuses with WriterLeaseHeld before boot”

Check whether the file has more than one filesystem name (hard links). Current SQLite refuses multi-name DB files at open, **including read-only**.

Remove hard-link backup usage and use a SQLite-safe copy/backup method.

## “A second SQLite writer through another name is not coordinating”

If you rely on file-identity leasing, every writer must declare the **same** absolute/private `writer_lease_lock_dir`.

Different/no lock directories do not produce one identity lock. Also, never rename a live SQLite database; the lease does not make live rename/WAL behavior safe.

## “DeploymentStoreNotVerified(reason=lock-held)”

Another boot holds the store-creation lock.

- with no `store_creation_lock_wait_seconds`: refusal is immediate;
- with a declared positive wait: the boot waits up to that bound, then refuses.

Retry after the holder exits. Do not remove a lock file while a process holds it.

## “DeploymentStoreNotVerified says pending/unreadable/claimed”

The deployment marker does not prove a safely verified store state.

Current markers are two-phase. A crash can leave `pending`; a foreign/legacy/inconsistent marker is not treated as verified.

Follow the current deployment recovery procedure instead of editing the marker into “verified.”

## “ChildRecordAltered”

Bytes fetched under a child Replay reference no longer hash to that address. The child is refused before admission.

Treat this as an integrity failure; do not parse/use the altered record.

## “ReplayReferenceMismatch / QueryPinReferenceMismatch”

The store returned a reference different from the exact artifact/query record the writer filed.

A conforming store must answer the canonical reference of what was written. Do not rewrite the reference in the caller.

## “WorkflowTraceReferenceMismatch”

The artifact store answered a reference that is not the exact workflow trace the engine wrote. The workflow outcome is not returned with that reference.

Investigate the store contract/integrity path.

## “ExecutionFenced”

Another valid transition/recovery won the state write the current operation read.

Re-read the execution state rather than blindly replaying the effect. Application effects still need safe retry/idempotency.

## “The run is suspended but there is no approval request”

Current engine recovery can restore the original missing approval request from the recorded suspension, on the starter's retry or on resume.

It does not rerun the step or manufacture approval. Use one HITL transport per state store for this recovery model.

## “The review queue cannot be released externally”

Use `open_review_door(...)` and route the authenticated review action through its authorized target-bound HITL path.

Do not call `ReviewQueue.release` using a caller-supplied principal string.

## “An unknown product class now looks like an entitlement refusal”

That is intentional on the product HTTP/MCP disclosure path. The external posture avoids an existence oracle; audit/Replay retains the actual internal authorizer denial.

## “Artifact exists but governed read says missing/refused”

Physical storage existence is not sufficient.

Governed evidence checks:

- exact bytes/content address;
- record-writer provenance;
- deciding tenant;
- entitlement/disclosure;
- erasure state.

A client-lane filing is not automatically governed evidence.

## “RegistryIntegrityFailure”

A Control Plane key/version exists but its protected canonical bytes/reconstruction are inconsistent.

That is an integrity failure, not `ControlPlaneMissing`.

## “Erasure subject is unverifiable”

Erasure reads verify the addressed bytes before judging the subject. Altered/misaddressed bytes refuse instead of being trusted for an erase decision.

## “LF peer returns 413 / PeerUnreachable”

Check `max_request_bytes` against the full framed JSON-RPC request and `max_message_bytes` against the decoded document. They are distinct.

## “Nonce-store TypeError after upgrade”

Custom seen-nonce stores use `key_thumbprint`, not `peer_id`, in the current protocol.

## “Which example should I copy?”

Use the current canonical/paved example guidance. Historical frozen examples may intentionally preserve earlier evidence.

## Exact shapes

Use [Generated API Signatures](api/README.md) and [Refresh Evidence](REFRESH_EVIDENCE.md).

## Context Skills and retained evidence

An empty harness tool list is correct for an `mcp_product` Context Skill. `DeclaredGrantRefused` means the requested grant failed governance; unsupported skill types or mismatched declarations can fail earlier without a grant audit event. Missing replay evidence is `ReplayEvidenceUnavailable`; altered retained graph evidence is `ReplayEvidenceAltered`. `SourcesNotRead` means an inspection-only opening was used to answer/resolve or access sources. Composite inspection still needs declared producer endpoint/credential settings even though replay makes no producer call. See [SK-01](../02-context-product-producer/examples/SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md) and [Decision Replay](DECISION_REPLAY.md).
