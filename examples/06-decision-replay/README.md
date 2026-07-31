# examples/06-decision-replay — record, then reproduce exactly (EXAM-07)

An **energy/grid-operations** decision — a load-shed authorization for an
overloaded feeder — is made against a real fabric by a skilled
`AnalyticsInsightsAgent`, suspended at an ApprovalGate, and approved
through the **hardened, auth-bound HITL door**
(`create_app(auth=BearerTokenAuth(...))` + a required D-16
`SignedPrincipalBinding`). Then, **from the replay record alone**, the
decision is reproduced: graph snapshot, policy bundle version, agent
version, skill-set in force, and prompt-artifact version resolve from the
ArtifactStore at their **exact recorded versions** — never a moving
target — and the reproduced Context Product is **byte-equal** (canonical
serializer) to the original. This is the replay leg of the D-14
absorption: the hardened HITL surface demonstrated *in replay*.

## Run it

```
make example-06
```

(or `PYTHONPATH=src:runtime python examples/06-decision-replay/run.py`).
Exit code 0 means every assertion held; any failure exits nonzero.

## What it demonstrates

| Invariant | What would fail here |
| --- | --- |
| Exact reproduction (whitepaper §7.10; D-IMPL-06/44) | The re-executed product's canonical bytes differ from the original's, or the content addresses disagree |
| Exact-version resolution (CLAUDE.md §7.4; D-IMPL-26) | The agent definition does not resolve at its recorded content hash, the resolved version differs from the recorded dimension-4 URI, or the prompt/grant resolve at anything but the pinned versions |
| Moving targets refused | A ref carrying the moving-target version token resolves instead of raising `MovingTargetRefused` |
| Skill-set in force (D-07; CLAUDE.md §6.2) | The recorded `grant_set_hash` does not recompute from the grant artifact resolved out of the store — the decision would replay against skills the agent never had |
| Hardened HITL surface in replay (D-14/D-16; §8.2) | The recorded signed binding fails verification, or the reproduced approver principal differs from the recorded one (grant-derived subject, hash of what the approver saw) |
| Version sensitivity of the audit record (D-IMPL-26/38) | A COPY of the record with a bumped policy-bundle version still reproduces instead of refusing (`ReplayUnresolvable`) |
| Workflow trace on dimension 5 (§8.1) | The recorded step-sequence block is absent or not the engine's serialization |

## Citations

- Whitepaper §7.10 (Decision Replay — forensic reconstruction), §7.10.1
  (five dimensions)
- CLAUDE.md §5 (Decision Replay Record), §7.4 (ArtifactStore — replay
  resolves exact artifact versions, never "the newest"), §8.2 (HITL
  audit-by-construction), §6.2 (skilling and replay capture), §6.4
  (No-Hardcoding Rule), §9 (examples charter item 7)
- D-IMPL-06/07 (snapshots), D-IMPL-26 (addressing), D-IMPL-44
  (re-hydration), D-IMPL-21/62/66(a)/67 (HITL identity), D-16 (signed
  bindings), D-14 (examples bind auth — replay leg)

## Domain rationale (D-09)

Grid operations: replaying a past operational decision — *who* authorized
the load shed, under *which* cryptographic binding, against *exactly which*
telemetry state, policy bundle, agent version, and skill-set — is the
vivid audit case. When a shed is questioned months later, the record
either reproduces the decision exactly or honestly refuses; nothing in
between.

The tokens in `artifacts/tokens.yaml` are synthetic, illustrative values
for a runnable demo (T-08-20 accepted) — never production credentials.

## What to change first

`artifacts/` is the specialization surface: the fabric vocabulary
(`ontology.yaml`, `events.yaml`), the decision's declared parameters and
the store class names (`controlplane.yaml`), the agent and its skill
(`agent.yaml`, `prompt.yaml`, `skills.yaml`), the workflow and gate
(`task.yaml`, `workflow.yaml`), and the D-16 policy + approver + tokens
(`hitl.yaml`, `tokens.yaml`). `run.py` is thin mechanism structured as
`record()` / `replay_decision()`; deleting the artifacts leaves it nothing
to run (§6.4).
