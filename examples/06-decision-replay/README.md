# examples/06-decision-replay — record, then reproduce exactly (EXAM-07)

## What this demonstrates

An **energy/grid-operations** decision — a load-shed authorization for an
overloaded feeder — is made against a real fabric, then reproduced **from
the replay record alone**. The **Decision Replay record** (the
five-dimension record — fabric snapshot, policy bindings, model version,
perspective conditioning, generation path — that lets a decision be
reproduced exactly; whitepaper §7.10 ("The Five-Dimension Replay
Record")) is the subject: every dimension is exercised, resolved from the
**ArtifactStore** (the Protocol-based persistence surface for CCF
artifacts — snapshots, products at rest, replay records, Control Plane
bundles — with file-backed and MCP-backed reference implementations;
CLAUDE.md §7.4 — SDK extension) at its **exact recorded version**, never
a moving target, and the reproduced **Context Product** (a typed,
validated, replay-ready unit of decision context the fabric derives and
serves — a contract, not a stored record; whitepaper §6.3
(specification), §7.6 (delivery)) is **byte-equal** to the original.

The human dimension is exercised twice. An ApprovalGate approval travels
the hardened, auth-bound door (bearer token, derived principal, required
D-16 signed binding). Then an **OverrideBoundary** (the HITL primitive at
which a human substitutes a value the agent would have produced —
original output and override both land in replay; CLAUDE.md §8.2 — SDK
extension) captures the shift supervisor substituting the agent's shed
determination: the override decision's own record resolves from the
store, and dimension 2 provably carries BOTH the agent's original value
and the human's substitution, byte-assertably — an override that lost
the original would be unrepudiable.

## Run it

```
make example-06
```

Raw fallback: `PYTHONPATH=src:runtime python examples/06-decision-replay/run.py`.
Exit code 0 means every assertion held; any failure exits nonzero.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-06`, review the assertion output, then
> deliberately edit the `expected:` block in `artifacts/controlplane.yaml`
> (and the drive/expected values in `artifacts/skills.yaml` and
> `artifacts/hitl.yaml`) to match what you reviewed — regeneration is a
> reviewed event, landed in the same commit as the enrichment, with the
> commit body summarizing what changed in the output and why. No
> `make regen-*` targets exist, and none will be added.

## The story

`run.py` is structured as two explicit phases: `record()` makes the
decision, `replay_decision()` reproduces it.

**Record.** The fabric boots from `artifacts/ontology.yaml` and ingests
the L1 envelopes in `artifacts/events.yaml` (lineage accumulation, a
similarity distractor, and a policy-restricted feeder are all in the
stream). The four-category operator chain and the projection run with
the parameters declared in `artifacts/controlplane.yaml` (key
`operator_parameters`), and the product passes the delivery gates. A
skilled `AnalyticsInsightsAgent` (declared in `artifacts/agent.yaml`,
skilled per `artifacts/skills.yaml`) consumes the product with a real
grant in force. The grid-ops workflow suspends at the
`load-shed-authorization` gate; the shift supervisor approves through
`create_app(auth=BearerTokenAuth(...))` with a signed principal binding
(see `artifacts/hitl.yaml`, key `hitl_policy`), while an unmapped-scope
token is refused deny-by-default with the typed 403 (see
`artifacts/scope_mapping.yaml`). Then the supervisor overrides the
agent's shed determination at the OverrideBoundary (see
`artifacts/hitl.yaml`, key `override` — original and substitute both
declared there), and both decisions' five-dimension records land in the
ArtifactStore.

**Replay.** From the record address alone: the product re-executes and
its canonical bytes equal the original's; the agent definition resolves
at its recorded content hash; the prompt artifact and skill grant
resolve content-addressed at the versions the record pins; the recorded
`grant_set_hash` recomputes from the stored grant — the decision replays
against the skills the agent actually had. The approval's signed binding
verifies from the record alone and reproduces the grant-derived
approver. The override record replays too: dimension 2 round-trips the
`OverrideActionRecord` with both values present byte-for-byte and the
overrider's signature verifying. Two negatives close the story: a
moving-target ref refuses (`MovingTargetRefused`), and a COPY of the
record with a bumped policy-bundle version refuses to reproduce
(`ReplayUnresolvable`) — the audit record is version-sensitive.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/ontology.yaml` | Entity classes, relationship types, resolution rules, tenant | `[ADAPT]`: all vocabulary. `[MECHANISM]`: rule field names (`match_key`, `identity_keys`, …) |
| `artifacts/events.yaml` | The L1 signal envelopes the fabric ingests | `[ADAPT]`: payloads, sources, instants. `[MECHANISM]`: envelope field names |
| `artifacts/controlplane.yaml` | Policy bundle, operator parameters, product class, store class names, `expected:` block | `[ADAPT]`: every value, incl. `expected:`. `[MECHANISM]`: `keys`, `artifacts`, parameter key names |
| `artifacts/agent.yaml` | The declared agent: six specialization axes incl. the skill-governance envelope | `[ADAPT]`: axis values. `[MECHANISM]`: definition field names |
| `artifacts/prompt.yaml` | The versioned prompt template | `[ADAPT]`: template, parameters. `[MECHANISM]`: field names |
| `artifacts/skills.yaml` | The catalog entry, the grant, dispatch arguments and expected output | `[ADAPT]`: skill vocabulary, outputs. `[MECHANISM]`: `skills`/`grant`/`dispatch` structure |
| `artifacts/task.yaml` | The two-step decision path (telemetry skill, hitl gate) | `[ADAPT]`: step names, refs. `[MECHANISM]`: step `kind` values |
| `artifacts/workflow.yaml` | Routing only: transitions, terminals, gate policy | `[ADAPT]`: names, terminals. `[MECHANISM]`: routing keys |
| `artifacts/hitl.yaml` | D-16 policy, approver, drive values, and the `override` block (original + substitute + overrider) | `[ADAPT]`: identities, values, `override.*` content. `[MECHANISM]`: `hitl_policy`, `keys`, `drive`/`override` key names |
| `artifacts/tokens.yaml` | Recognised tokens, lifecycle, scopes — all synthetic | `[ADAPT]`: token strings, ids, scopes. `[MECHANISM]`: `label`, `status` keys |
| `artifacts/scope_mapping.yaml` | Which scopes reach which tenants/actions (deny-by-default) | `[ADAPT]`: scopes, tenant patterns. `[MECHANISM]`: mapping grammar keys |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §7.10 (Decision Replay — forensic reconstruction; "The
  Five-Dimension Replay Record")
- whitepaper §6.3 / §7.6 (Context Product contract and delivery gates)
- whitepaper §7.4 / §7.5 (operator chain and projection, re-executed at
  replay)
- CLAUDE.md §7.4 (ArtifactStore — replay resolves exact artifact
  versions, never "latest") — SDK extension
- CLAUDE.md §8.2 (HITL: ApprovalGate and OverrideBoundary,
  audit-by-construction — both values in the record) — SDK extension
- CLAUDE.md §6.2 (skilling — the skill-set in force lands in replay) —
  SDK extension
- CLAUDE.md §6.4 (No-Hardcoding Rule), §9 (examples charter item 7) —
  SDK extension

## What to change first

`artifacts/` is the specialization surface. To move this example to your
domain, edit in this order:

1. `artifacts/ontology.yaml` + `artifacts/events.yaml` — your entity
   classes, relationships, and signal stream; then update the
   `expected:` block in `artifacts/controlplane.yaml` (entity classes,
   relationship types, `entity_count`) via the reviewed-regeneration
   workflow above.
2. `artifacts/hitl.yaml`, key `override` — your own agent-output shape's
   values under `original:` and `substitute:` (the driver's
   deployment-typed contract fields must match the keys), and the
   overrider identity. Set `drive.action` to `confirm` and re-run to
   watch a kept value still land as a recorded action, not an absence.
3. `artifacts/skills.yaml` + `artifacts/agent.yaml` — your skill and the
   governance envelope that admits it; `dispatch.expected_output` is the
   third expected block to re-review.
4. `artifacts/tokens.yaml` + `artifacts/scope_mapping.yaml` — your token
   table and authorization statement. Add the `metering` scope to the
   mapping and re-run to watch the 403 leg fail, proving the refusal
   comes from the artifact, not the code.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| Exact reproduction (whitepaper §7.10; D-IMPL-06/44) | The re-executed product's canonical bytes differ from the original's, or the content addresses disagree |
| Exact-version resolution (CLAUDE.md §7.4; D-IMPL-26) | The agent definition does not resolve at its recorded content hash, the resolved version differs from the recorded dimension-4 URI, or the prompt/grant resolve at anything but the pinned versions |
| Moving targets refused | A ref carrying the moving-target version token resolves instead of raising `MovingTargetRefused` |
| Skill-set in force (D-07; CLAUDE.md §6.2) | The recorded `grant_set_hash` does not recompute from the grant artifact resolved out of the store — the decision would replay against skills the agent never had |
| Hardened HITL surface in replay (D-14/D-16; §8.2) | The recorded signed binding fails verification, or the reproduced approver principal differs from the recorded one (grant-derived subject, hash of what the approver saw) |
| OverrideBoundary capture (§8.2; T-07-16) | Dimension 2 of the override record omits either the agent's original value or the human's substitution, the `OverrideActionRecord` fails to round-trip, or the overrider's binding echoes a hash other than the proposal-time hash (TOCTOU) |
| Version sensitivity of the audit record (D-IMPL-26/38) | A COPY of the record with a bumped policy-bundle version still reproduces instead of refusing (`ReplayUnresolvable`) |
| Workflow trace on dimension 5 (§8.1) | The recorded step-sequence block is absent or not the engine's serialization |
| Tenant authorization at the door, deny-by-default (HARD-04; D-IMPL-68) | The unmapped-scope token reaches the queue, the refusal is not the typed `ERROR_TENANT_UNAUTHORIZED` 403, or the deny is missing from the audit log (or carries the wrong mapping version) |
