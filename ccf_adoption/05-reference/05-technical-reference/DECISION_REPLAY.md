# Decision Replay

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Decision Replay reconstructs a governed determination against the exact state and declarations recorded when the decision was made.

## Five dimensions

`DecisionReplayRecord` retains:

1. Context Fabric Snapshot;
2. Policy Bindings Snapshot;
3. Model Version Record;
4. Perspective Conditioning;
5. Content Generation Path.

## Current Content Generation Path

Current `ContentGenerationPath` includes, among its existing evidence:

- `served_at`;
- `computed_empty`;
- `executed_seeds`;
- `issuance`;
- `subject_withholding`;
- child resolutions;
- operator steps / query sequence;
- debt/debt evidence;
- request/refusal/assembly evidence.

Current helpers include:

- `new_issuance()`;
- `NO_ISSUANCE`;
- `UNSTATED_SUBJECT_WITHHOLDING`.

Per-answer issuance is now a landed record field/mechanism. Do not use replay-reference equality as an assurance criterion for two different answers.

## Served and refused determinations

Use:

- `replay(...)` → `ReplayOutcome`;
- `replay_refusal(...)` → `RefusalReplayOutcome`.

A refusal is reconstructed as the recorded refusal; Replay does not manufacture a product to normalize the shapes.

Erasure can produce `ErasedReplayOutcome` / erased-content evidence where the supplied store consult withholds required material.

## Exact reconstruction

Replay fails closed on missing/rebound/inconsistent evidence.

Current reference/integrity failures include:

- `ReplayReferenceMismatch`;
- `QueryPinReferenceMismatch`;
- `ReplayGenerationMismatch`;
- `ReplayRecordKindMismatch`;
- `ReplayResolutionClaimMismatch`.

`ReplayWriter` derives the reference of the record it wrote and verifies every field of the store's returned reference before any delivery capability leaves the writer. Query-pin writing follows the same rule.

## Record provenance

Current main adds `ccf.replay.provenance`:

- `filed_by_record_writer(...)`;
- `require_filed_by_record_writer(...)`;
- `RecordNotFiledByRecordWriter`;
- `UnattributableRecordStore`.

A record-shaped object filed by a client is not governed evidence merely because its JSON shape looks like a replay record.

Governed evidence reads combine exact bytes/address checks, filing provenance, tenant/principal disclosure, entitlement and erasure consultation.

## Child/replay retained evidence

Current child resolution also verifies:

- retained child-record bytes hash to their address;
- retained child-question references are exactly the reference of the question written.

Failures such as `ChildRecordAltered` and `ChildQuestionReferenceMismatch` occur before altered/misreferenced data is admitted into a parent determination.

## Subject withholding evidence

Replay now carries the class's subject-withholding stance and additional evidence used by the current SEC-020 controls, including executed-seed and issuance information.

That evidence improves forensic explanation. It does not convert a false deployment declaration into truth, and it does not by itself establish universal withheld-vs-nonexistent indistinguishability.

## Read-only reconstruction and erasure

Replay still reconstructs from exact retained evidence and pinned declarations; it never substitutes `latest`.

Where erasure consultation is required, pass the composed consulting store. Passing a raw store bypasses that consult.

## DR examples

- [DR-01 — Replay a Governed Determination](../03-decision-replay/DR01_REPLAY_A_GOVERNED_DETERMINATION.md)
- [DR-02 — Package a Context Product](../03-decision-replay/DR02_PACKAGE_A_CONTEXT_PRODUCT.md)

The tutorials are historical/qualified learning evidence. Use this page and the generated signatures for the current-main contract.

## Exact current shapes

Use [Replay API signatures](api/replay.md).

## Durable evidence and restart replay — D-IMPL-383

Pass a persistent `evidence_root=` to `open_product` and a separate temporary `scratch`. The evidence root holds per-question graphs, the default file-backed replay store and erasure index, the decision-to-graph index and the SDK-managed writer-lock directory. If omitted, evidence stays under `scratch`, retaining the previous lifetime. An evidence root inside `config_root`, or nested/equal evidence and scratch directories, is refused.

The SDK accepts a parameter; it does not read an evidence-directory environment variable. cp-06-canonical's launcher reads `CCF_REPLAY_EVIDENCE_ROOT` and passes it in. That launcher requires an absolute, existing, real directory, owned by its running account, mode `0700`, writable and not a symlink. Without the variable, its temporary evidence disappears when the door stops.

`OpenedProduct.evidence` exposes `ReplayEvidenceIndex`: `entry`, `decisions`, `incomplete` and `graph_path`. A pending marker records the start of a question. The completed mapping is published after its graph is closed and hashed. Interrupted work can therefore appear as begun but unfinished; it is not a governed completed decision.

`opened.replay_decision(record_address)` selects served/refused replay from retained evidence, opens the graph read-only and checks its hash and correspondence to the record. It can return `ReplayOutcome`, `RefusalReplayOutcome` or `ErasedReplayOutcome`. Missing mappings/graphs/records raise `ReplayEvidenceUnavailable`; changed retained graph evidence raises `ReplayEvidenceAltered`.

Durability is not an unlimited crash guarantee: index publication uses staged/fsynced replacement, but the file-backed record store itself does not fsync, so an OS crash can leave a mapping whose record bytes are unavailable. There is no automatic retention cleanup. Back up the retained records, graphs, child contracts and pinned artifacts together with compatible deployment configuration/code.

## Inspect without reacquiring sources

`open_product(..., read_sources=False)` skips source-setting resolution. `sources`, `answer` and `resolve` then raise `SourcesNotRead`; this is an inspection/replay opening, not a degraded serving mode. Reconstruction still needs compatible configuration, operator implementations and plan factories. A known composite limitation remains: declared producer endpoint/credential environment settings are required at open even in this mode, although replay never calls a producer.

`explain_decision(store=..., evidence=..., record_address=...)` returns a `DecisionExplanation`: outcome, retained refusal reason/detail, pinned policy versions, resolved input origins, graph metadata and debt where recorded. It reads retained evidence, not an LLM, and needs no retained graph to explain a retained record. It is an operator/auditor interface: internal details may exceed a minimal-disclosure caller's answer.

## Composite reconstruction — D-IMPL-389

`RecordedEnvironment` now implements the engine's composite replay seam. A child-aware plan factory receives the retained child contracts through `build_with_children`; a plain factory retains its plain call. The environment composes lineage and expiry from each admitted row's operators, policy versions, graph instant and expiry. Missing required admitted-row fields raise `RecordedEnvironmentUnbuildable`.

When child rows exist but none was admitted, a child-aware factory receives an empty `ChildContractView`, matching the original serve. A record without child rows follows the ordinary plan path. No producer is asked, and neither record format nor replay engine was changed. “From the record” still requires the retained store/graphs and compatible code; a record hash alone is not a self-contained replay package.

The SDK's [composite replay tests](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/tests/replay/test_composite_replay_decision.py) cover stopped-producer reconstruction. SK-01 does not itself exercise a replay gate. Its dimension-4 skill-set hash also does not preserve the list of grants; see [Context Skills](CONTEXT_SKILLS.md).

Sources: [distinct evidence root](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/docs/surface-changes/383-02-a-distinct-evidence-root.md), [inspection](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/docs/surface-changes/383-03-asking-the-retained-evidence.md), [source-free opening](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/docs/surface-changes/383-04-replay-without-source-settings.md), [composite reconstruction](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/docs/surface-changes/389-01-composite-replay-from-the-record.md). For runnable launcher commands see [CLI operations](CLI_HTTP_OPERATIONS.md#retained-evidence-commands).
