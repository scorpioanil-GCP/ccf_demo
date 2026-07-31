# 02 — Skilling: governed capability, channel 2

Grant a skill to a running agent through the Control Plane, exercise it,
and revoke it. The governance compatibility check refuses an impermissible
grant; every grant and revocation is audited; the skill-set in force at
the exercise step lands in the Decision Replay record — and the agent
definition **never changes**.

This is the second channel of specialization (CLAUDE.md §6.2):
specialization changes *who the agent is* (example 01); skilling changes
*what the agent can currently do* — under explicit governance, without
re-declaring the agent.

## Run it

```sh
make example-02
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/02-skilling/run.py
```

The driver is an asserted program: exit code 0 means every invariant below
held — **including the governance refusal**; the example fails if the
tier-1 check does not fire. CI treats nonzero as red.

## What it demonstrates

| Invariant | What would fail here |
| --- | --- |
| channel separation (§6.2, D-07) | the grant/exercise/revoke cycle would change `artifacts/agent.yaml` (asserted byte-identical), the definition's content hash, or its registered version set |
| tier-1 governance is non-waivable (D-IMPL-29) | the `protocol-write`-requiring grant would bind; the refusal is a typed returned value naming the exact excess scopes |
| audit-by-construction (§6.2) | a grant or revocation without its `grant_*` action on the one Control Plane audit log, in order: requested, effective, requested, refused, revoked |
| skill-set in force in replay (D-07) | dimension 4's `grant_set_hash` would not equal the content hash of the in-force grant set at the exercise step |
| live bound view | a revoked skill would still dispatch — binding is resolved from ledger state at invoke time, on the same constructed agent |
| skills the agent lacks do not exist (§7.3 seam 2) | an ungranted or revoked skill would be visible from the agent's surface instead of raising the typed `SkillNotBound` |
| no execution surface for the SDK (D-19) | the local callable would be imported from a dotted path in an artifact rather than resolved from the key the composition root registered |
| tier 2 stays out of an auto regime (D-IMPL-29) | the approval sink would be consulted although the regime declares `grant_requires_approval: false` (the sink raises if touched) |

## What it exercises

- **Whitepaper:** §7.8 (Control Plane as the governing and audit plane),
  §7.10.1 (Decision Replay dimension 4).
- **CLAUDE.md:** §6.2 channel 2 (skilling: governed grants, replay
  capture, the policy-regime envelope), §6.4 (No-Hardcoding — scopes and
  skill entries are deployment values), §5 (Control Plane vs Data Plane).

## Domain rationale (D-09)

This example is a **clinical-trials operations** scenario (an enrollment
analyst over trial sites and cohorts, with a restricted unblinded cohort
substituted out): governance-heavy capability control mirrors
regulated-domain reality without banking — per D-IMPL-52 the suite
deliberately crosses unrelated domains (00 banking, 01 field-service).
All domain values live in `artifacts/`; the data is synthetic and
fictional.

## The No-Hardcoding Rule, made visible

`run.py` holds no scope identifier, no skill entry, no grant value and no
expected output — the governance envelope lives in `artifacts/agent.yaml`
(axis 4), the skill catalog entries, grants, expected excess and callable
output content in `artifacts/skills.yaml`. The one callable in code is a
generic record-merging closure; what it answers is artifact data.

## What to change first

`artifacts/skills.yaml` **is** the capability surface:

- add your own catalog entries — four skill types ship (`tool`,
  `local_callable`, `mcp`, `peering`); requirements are opaque
  identifiers your policy regimes must permit;
- widen (or narrow) `skill_governance.permitted_scopes` in
  `artifacts/agent.yaml` — that is an axis-4 change and therefore a new
  agent version (D-05), which is exactly the channel separation on show;
- set `grant_requires_approval: true` to route grants through a tier-2
  `ApprovalSink` of your own.
