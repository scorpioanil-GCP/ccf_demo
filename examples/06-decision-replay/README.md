# examples/06-decision-replay — record, then reproduce exactly (EXAM-07)

## What this demonstrates

An **energy/grid-operations** decision — a load-shed authorization for an
overloaded feeder — is made against a real fabric, then reproduced **from the
replay record alone**. The **Decision Replay record** (the five-dimension
record — fabric snapshot, policy bindings, model version, perspective
conditioning, generation path — that lets a decision be reproduced exactly;
whitepaper §7.10 ("The Five-Dimension Replay Record")) is the subject: every
dimension is exercised, resolved from the **ArtifactStore** (the Protocol-based
persistence surface for CCF artifacts — snapshots, products at rest, replay
records, Control Plane bundles — with file-backed and MCP-backed reference
implementations; CLAUDE.md §7.4 — SDK extension) at its **exact recorded
version**, never a moving target, and the reproduced **Context Product** (a
typed, validated, replay-ready unit of decision context the fabric derives and
serves — a contract, not a stored record; whitepaper §6.3 (specification), §7.6
(delivery)) is **byte-equal** to the original.

The human dimension is exercised twice. An ApprovalGate approval travels the
hardened, auth-bound door (bearer token, derived principal, required D-16 signed
binding). Then an **OverrideBoundary** (the HITL primitive at which a human
substitutes a value the agent would have produced — original output and override
both land in replay; CLAUDE.md §8.2 — SDK extension) captures the shift
supervisor substituting the agent's shed determination: the override decision's
own record resolves from the store, and dimension 2 provably carries BOTH the
agent's original value and the human's substitution, byte-assertably — an
override that lost the original would be unrepudiable.

## Where the guarantee lives

`run.py` is the **call spine**: it asserts nothing and prints nothing. Every
assertion is in `tests/examples/test_decision_replay_output.py`, grouped by the
replay dimension it covers, where `pytest` runs it and a failure fails the build
(D-09). `make example-06` running clean means the spine executed; the test
module is what says it was *right*.

The one thing the spine does itself, and must: **it selects which policy
bindings were in force.** Each `PolicyBinding` handed to `build_replay_record`
is built from a pin read off `BootedFabric.pins` by key. `pins` is never passed
to the record builder, and `ResolvedPins` grows no helper that would turn a pin
set into bindings — D-06 keeps that selection in adopter code, because dimension
2 assembled by a rule nobody in the deployment wrote down is not an audit
record.

## Run it

```
make example-06
```

Raw fallback: `PYTHONPATH=src:runtime python examples/06-decision-replay/run.py`.

The assertions:

```
PYTHONPATH=src:runtime python -m pytest tests/examples/test_decision_replay_output.py
```

> **Expected-value changes are a reviewed event.** If you enrich the artifacts,
> run the test module, review what changed, then deliberately edit
> `artifacts/expected.yaml` (and `dispatch.expected_output` in
> `artifacts/skill-dispatch.yaml`) to match what you reviewed — landed in the
> same commit as the enrichment, with the commit body summarizing what changed
> and why. No `make regen-*` targets exist, and none will be added.

## The story

**Boot.** One `load_and_boot` call over `artifacts/manifest.yaml` parses every
document the deployment puts in force, registers the `role: register` ones, and
boots on the resulting pins. The four-category operator chain comes from
`build_operator_registry` over the four `operator-parameters-*.yaml` documents.

**Record.** The L1 envelopes in `artifacts/events.yaml` are ingested (lineage
accumulation, a similarity distractor, and a policy-restricted feeder are all in
the stream); the projection runs and the product passes the three delivery
gates. A skilled `AnalyticsInsightsAgent` (`artifacts/agent-definition.yaml`,
skilled per `artifacts/skill-catalog-entry.yaml` and
`artifacts/skill-dispatch.yaml`) consumes the product with a real grant in
force. The grid-ops workflow suspends at the `load-shed-authorization` gate; the
shift supervisor approves through `create_app(auth=BearerTokenAuth(...))` with a
signed principal binding (`artifacts/hitl-policy.yaml` requires it), while an
unmapped-scope token is refused deny-by-default with the typed 403
(`artifacts/scope-mapping.yaml`). Then the supervisor overrides the agent's shed
determination at the OverrideBoundary (`artifacts/hitl-drive.yaml`, key
`override` — original and substitute both declared there), and both decisions'
five-dimension records land in the ArtifactStore.

**Replay.** From the record address alone: the product re-executes and its
canonical bytes equal the original's; the agent definition resolves at its
recorded content hash; the prompt artifact and skill grant resolve
content-addressed at the versions the record pins; the recorded `grant_set_hash`
recomputes from the stored grant — the decision replays against the skills the
agent actually had. The approval's signed binding verifies from the record alone
and reproduces the grant-derived approver. The override record replays too:
dimension 2 round-trips the `OverrideActionRecord` with both values present
byte-for-byte and the overrider's signature verifying. Two negatives close the
story: a moving-target ref refuses (`MovingTargetRefused`), and a COPY of the
record with a bumped policy-bundle version refuses to reproduce
(`ReplayUnresolvable`) — the audit record is version-sensitive.

## Artifact-by-artifact

Every `*.yaml` under `artifacts/` is exactly **one artifact class**, which is
what makes an honest `$schema` header possible per document. `manifest.yaml`
enumerates the ones the deployment puts in force; seven are registered by the
driver instead, each for a reason stated in its own header.

| Artifact | In manifest | What it declares |
| --- | --- | --- |
| `manifest.yaml` | — | Everything in force, by `path`/`key`/`class_id`/`role` |
| `resolution-spec.yaml` | `register` | Entity and relationship resolution rules |
| `policy-bundle.yaml` | `register` | The fabric's policy bundle — the version replay resolves back |
| `operator-parameters-traversal.yaml` | `register` | Seeds, edge types, depth bound |
| `operator-parameters-temporal.yaml` | `register` | Which bitemporal axes to reconcile |
| `operator-parameters-policy.yaml` | `register` | Classification attribute map, permitted classifications |
| `operator-parameters-similarity.yaml` | `register` | Query, threshold, corpus attribute map |
| `perspective.yaml` | `register` | The Π role-conditioning, verbatim into dimension 4 |
| `product-class.yaml` | `register` | Schema lane, TTL anchor, `required_operator_keys` (Gate 2's declared side) |
| `product-governance.yaml` | `register` | MAX_TTL, product TTL, index version, plan id, replay record class |
| `agent-policy-regime.yaml` | `register` | The agent's axis-4 regime and skill-governance envelope |
| `agent-debt-profile.yaml` | `register` | The agent's axis-5 staleness tolerance |
| `task-skill.yaml` | `register` | What the task's first step may invoke |
| `approval-policy.yaml` | `register` | Who may approve at the gate, and how many |
| `events.yaml` | `load` (SDK-fixed) | The L1 signal envelopes |
| `decision.yaml` | `load` | This run's boundary, decision instant, and clock seed |
| `expected.yaml` | `load` | What the served product should contain |
| `agent-registration.yaml` | `load` | Where the driver-registered documents file |
| `skill-dispatch.yaml` | `load` | The grant request, the callable's output, the dispatch |
| `hitl-drive.yaml` | `load` | Approver, drive values, node outputs, the `override` block |
| `tokens.yaml` | `load` | Recognised tokens, lifecycle, scopes — all synthetic |
| `replay-probes.yaml` | `load` | The two negative probes and the store's class names |
| `agent-definition.yaml` | driver | Six specialization axes (author-versioned) |
| `prompt-artifact.yaml` | driver | The versioned prompt template (author-versioned) |
| `skill-catalog-entry.yaml` | driver | The governed skill (author-versioned) |
| `task-definition.yaml` | driver | The two-step decision path (author-versioned) |
| `workflow-definition.yaml` | driver | Routing only (author-versioned) |
| `hitl-policy.yaml` | driver | The D-16 signed-binding requirement |
| `scope-mapping.yaml` | driver | Which scopes reach which tenants and actions |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §7.10 (Decision Replay — forensic reconstruction; "The
  Five-Dimension Replay Record")
- whitepaper §6.3 / §7.6 (Context Product contract and delivery gates)
- whitepaper §7.4 / §7.5 (operator chain and projection, re-executed at replay)
- CLAUDE.md §7.4 (ArtifactStore — replay resolves exact artifact versions, never
  "latest") — SDK extension
- CLAUDE.md §8.2 (HITL: ApprovalGate and OverrideBoundary,
  audit-by-construction — both values in the record) — SDK extension
- CLAUDE.md §6.2 (skilling — the skill-set in force lands in replay) — SDK
  extension
- CLAUDE.md §6.4 (No-Hardcoding Rule), §9 (examples charter item 7) — SDK
  extension

## What to change first

`artifacts/` is the specialization surface. To move this example to your domain,
edit in this order:

1. `artifacts/resolution-spec.yaml` + `artifacts/events.yaml` — your entity
   classes, relationships, and signal stream; then update
   `artifacts/expected.yaml` via the reviewed-regeneration workflow above.
2. `artifacts/hitl-drive.yaml`, key `override` — your own agent-output shape's
   values under `original:` and `substitute:` (the driver's deployment-typed
   `ShedDetermination` fields must match the keys), and the overrider identity.
   Set `override.drive.action` to `confirm` and re-run to watch a kept value
   still land as a recorded action, not an absence.
3. `artifacts/skill-catalog-entry.yaml` + `artifacts/agent-definition.yaml` —
   your skill and the governance envelope that admits it;
   `dispatch.expected_output` in `artifacts/skill-dispatch.yaml` is the second
   expected block to re-review.
4. `artifacts/tokens.yaml` + `artifacts/scope-mapping.yaml` — your token table
   and authorization statement. Add the `metering` scope to the mapping and
   re-run to watch the 403 leg fail, proving the refusal comes from the
   artifact, not the code.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| Exact reproduction (whitepaper §7.10; D-IMPL-06/44) | The re-executed product's canonical bytes differ from the original's, or the content addresses disagree |
| Exact-version resolution (CLAUDE.md §7.4; D-IMPL-26) | The agent definition does not resolve at its recorded content hash, the resolved version differs from the recorded dimension-4 URI, or the prompt/grant resolve at anything but the pinned versions |
| Moving targets refused | A ref carrying the moving-target version token resolves instead of raising `MovingTargetRefused` |
| Skill-set in force (D-07; CLAUDE.md §6.2) | The recorded `grant_set_hash` does not recompute from the grant artifact resolved out of the store — the decision would replay against skills the agent never had |
| Hardened HITL surface in replay (D-14/D-16; §8.2) | The recorded signed binding fails verification, or the reproduced approver principal differs from the recorded one |
| OverrideBoundary capture (§8.2; T-07-16) | Dimension 2 of the override record omits either the agent's original value or the human's substitution, the `OverrideActionRecord` fails to round-trip, or the overrider's binding echoes a hash other than the proposal-time hash (TOCTOU) |
| Version sensitivity of the audit record (D-IMPL-26/38) | A COPY of the record with a bumped policy-bundle version still reproduces instead of refusing (`ReplayUnresolvable`) |
| Gate 2 independence (INV-CH7-47) | The plan's `required` comes from the operator registry rather than from `product-class.yaml` — in the record phase or in the replay environment, which reconstructs the same plan |
| Workflow trace on dimension 5 (§8.1) | The recorded step-sequence block is absent or not the engine's serialization |
| Tenant authorization at the door, deny-by-default (HARD-04; D-IMPL-68) | The unmapped-scope token reaches the queue, the refusal is not the typed `ERROR_TENANT_UNAUTHORIZED` 403, or the deny is missing from the audit log (or carries the wrong mapping version) |
