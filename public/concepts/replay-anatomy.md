# Anatomy of a Decision Replay record

Reconstructing a decision means reproducing five distinct kinds of state as
they stood when the decision was taken. Lose one of the five and an entire
class of audit question stops being answerable at all — not merely harder to
answer.

The SDK's `DecisionReplayRecord` is that five-dimension structure, plus the
extensions the SDK's own layers contribute. This page names the real fields, so
that reading a record and reading this page are the same exercise.

## The record

`DecisionReplayRecord` is a typed contract carrying `tenant_id`,
`recorded_at`, and one field per dimension. Records are indexed by the
decision's temporal boundary and resolved from the artifact store by exact
version — never by "latest".

| # | Dimension | Field | The question it answers |
| --- | --- | --- | --- |
| 1 | Context Fabric Snapshot | `context_fabric_snapshot` | What did the agent know? |
| 2 | Policy Bindings Snapshot | `policy_bindings` | What rules applied? |
| 3 | Model Version Record | `model_version` | What software reasoned? |
| 4 | Perspective Conditioning | `perspective_conditioning` | For whom, under what authority? |
| 5 | Content Generation Path | `content_generation_path` | How did it get from input to output? |

### Dimension 1 — `ContextFabricSnapshot`

Pins the graph state the decision saw: `graph_snapshot_id`, `tenant_id`,
`temporal_boundary`, `store_watermark`, and the `touched_entities` and
`touched_relationships` the decision actually reached. Recording the touched
substate rather than the whole graph is what keeps year-scale retention
tractable.

### Dimension 2 — `PolicyBindingsSnapshot`

A tuple of `PolicyBinding` entries, each a `key` and a pinned `version`. This
dimension carries the SDK's first extension: `hitl_actions` holds the human
actions that shaped the decision, so approvals, escalations and overrides are
part of the governance answer rather than a separate log.

### Dimension 3 — `ModelVersionRecord`

Carries the `assembly_mode` and `model_version`, and — when a harness was in
the path — a `HarnessTrace` with `harness_id`, `trace_provider`, `trace_id`,
and the token counts. A purely algorithmic derivation records its mode and no
harness trace at all, which is itself the useful fact.

### Dimension 4 — `PerspectiveConditioning`

Who acted, and with what authority: `principal_id`, `role`, and the
`delegation_chain`. Two SDK extensions live here. Agent identity arrives as
`agent_definition_uri` and `agent_definition_hash`, together with the
`archetype_composition` the agent was built from; and the skilling channel
arrives as `grant_set_hash` — the skill-set in force at decision time, so a
decision replays against the capabilities the agent actually held rather than
the ones it holds now.

### Dimension 5 — `ContentGenerationPath`

The derivation itself: `plan_id`, the `operator_plan`, the ordered `steps`, and
the `product_content_address` of what was produced. The workflow extension
lands here as `workflow_step_sequence` — the orchestration trace, recorded
alongside the operator trace rather than beside it.

## Resolution

Replaying is a resolution exercise before it is a re-derivation. Every
reference in the record is content-addressed, and the engine walks them all —
snapshot, policy bundle, agent definition, skill grants, prompt artifacts —
pinning each to an exact version, verifying with the Control Plane that a
version identifier was never rebound to different content, and only then
re-deriving the product under the pinned configuration.

The final step is an assertion, not a comparison for reporting: lineage strict
equality and a substrate hash match. A mismatch fails loudly. There is no
"close enough" reproduction, because an approximate replay is worse than a
refused one — it looks like evidence.

```mermaid
--8<-- "public/diagrams/seq-replay-resolution.mmd"
```

## Where a human action enters the record

The HITL extension to dimension 2 is not an afterthought bolted to the approval
path — it is ordered ahead of it. A workflow reaching an approval gate persists
its execution state, writes its trace through to the artifact store, and parks.
The action a human then takes is validated as a typed record with an identity
binding required, appended to the replay record, and *only then* delivered back
to the state machine.

That ordering is the whole of the audit-by-construction commitment described in
[the invariants page][invariants]: an action that failed to record is an action
that never resumed the workflow.

```mermaid
--8<-- "public/diagrams/seq-hitl-suspend-resume.mmd"
```

## Where this lives

- [Artifact store][store] — where records and their referenced artifacts are
  resolved from, and the addressing scheme that makes exact-version reads
  possible.
- [Context Products][products] — the gates that make a served product
  replay-ready at the moment it is served.
- [HITL][hitl] — the action records that extend dimension 2.
- [Orchestration and workflow][orch] — the traces that extend dimensions 4
  and 5.
- [Agents][agents] — agent versioning and archetype composition.
- [Runtime surfaces][runtime] — the CLI and MCP surfaces for running replay
  queries.

[invariants]: invariants.md
[store]: ../reference/protocols/artifact-store.md
[products]: ../reference/protocols/context-products.md
[hitl]: ../reference/protocols/hitl.md
[orch]: ../reference/protocols/orchestration-and-workflow.md
[agents]: ../reference/protocols/agents.md
[runtime]: ../reference/protocols/runtime-surfaces.md
