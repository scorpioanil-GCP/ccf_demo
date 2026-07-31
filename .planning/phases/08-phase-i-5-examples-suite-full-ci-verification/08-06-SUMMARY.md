---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 06
subsystem: examples
tags: [examples, exam-02, exam-03, agents, skilling, no-hardcoding]
requires: [08-01, 08-05]
provides:
  - "examples/01-agent-basics runnable via make example-01 (EXAM-02): six-axis field-service agent, factory-only, replay dimension 4"
  - "examples/02-skilling runnable via make example-02 (EXAM-03): grant/exercise/revoke, tier-1 refusal, audit + replay capture"
affects: [08-07..08-11 later examples, 08-12 CI examples job]
tech-stack:
  added: []
  patterns:
    - "D-12 LLM seam stub: mechanism-only class in run.py, canned output CONTENT in artifacts (analysis_output.yaml)"
    - "Composition-root callable factory: generic record-merging closure; the record is artifact data (D-19)"
    - "Byte-identity assertion on the definition artifact as the channel-separation proof"
key-files:
  created:
    - examples/01-agent-basics/run.py
    - examples/01-agent-basics/README.md
    - examples/01-agent-basics/artifacts/{ontology,events,controlplane,prompt,agent,analysis_output}.yaml
    - examples/02-skilling/run.py
    - examples/02-skilling/README.md
    - examples/02-skilling/artifacts/{ontology,events,controlplane,agent,skills}.yaml
  modified: []
decisions:
  - "Example 01 mirrors the full four-operator quickstart fabric shape (proven pipeline); example 02 runs a three-operator fabric (policy/temporal/traversal) — a similarity corpus adds nothing to the skilling story"
  - "Example 02's ApprovalSink is an UnconsultedSink that raises if touched — asserting tier 2 stays out of an auto regime rather than merely not using it"
  - "Axis-4/5 resolution asserted two ways in example 01: factory construction succeeds (refusal path is real) AND each referenced key has registered versions with the ref pinned to its declared semver"
metrics:
  duration: "~13 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 06: examples 01 (agent-basics) + 02 (skilling) Summary

The two-channel specialization story as asserted programs: a six-axis
field-service agent factory-constructed from artifacts with its identity in
replay dimension 4 (EXAM-02), then governed skilling in a clinical-trials-ops
domain — grant/exercise/revoke with a tier-1 refusal, full audit trail, and
the in-force grant-set hash in the replay record, the agent definition
byte-identical throughout (EXAM-03).

## What was built

- **Task 1 (684ee57): `examples/01-agent-basics`** — fresh
  `cascadia-fieldworks` field-service domain (technician / work_order /
  site; lineage set-union, similarity rank-out, restricted-site policy
  substitution). Six-axis `response-time-analytics` definition binding the
  `analytics_insights` archetype; `run.py` boots the fabric, serves the
  `work-order-context` product, constructs the agent through `AgentFactory`
  (the only path), asserts all six axes resolve, consumes the served
  product, runs the D-12 `ScriptedAnalyst` stub (`LLMClientProtocol`
  conformance asserted; content from `analysis_output.yaml`), and asserts
  the agent's definition hash / versioned URI / archetype composition in
  the restored replay record's dimension 4.
- **Task 2 (7b89501): `examples/02-skilling`** — fresh `helix-trials`
  clinical-trials-ops domain. Agent whose axis-4 regime permits
  `enrollment-read` and excludes `protocol-write`; two catalog entries
  (permitted local_callable, impermissible tool). Sequence with assertions
  after each step: register → grant (audit `grant_requested`/`grant_effective`,
  D-07 set hash) → exercise (deterministic callable, dimension-4 in-force
  grant-set capture through a served replay record) → impermissible grant
  (typed `RequirementsExceedRegime` naming `protocol-write`, nothing binds,
  `SkillNotBound`) → revoke (`grant_revoked`, live bound view empties,
  `NO_GRANTS_SET_HASH` restored) → `agent.yaml` byte-identical and one
  registered definition version.

## Deviations from Plan

None - plan executed exactly as written. (One self-caught wording fix: the
example-01 README initially spelled `@latest` in prose, tripping the plan's
own "grep returns nothing" criterion; reworded before commit.)

## Verification

- `make example-01 && make example-02` exit 0; `make lint` exit 0
  (CINV-01 over both examples); `make typecheck` clean (156 files)
- `grep -rn "ccf-artifact://" examples/01-agent-basics/artifacts/` shows
  versioned refs only; `grep -rn "@latest"` over both example dirs returns
  nothing
- `grep -c '"""'` = 2 in both run.py files (module docstring only; all
  other commentary is `#` comments)
- example 02 fails (nonzero) if the governance check does not fire: the
  refusal is `assert isinstance(refusal, RequirementsExceedRegime)`
- Threat register: T-08-12 (tier-1 refusal demonstrated) and T-08-13
  (grant/revoke audit assertions) both discharged as asserted behavior

## Known Stubs

None — every artifact value is consumed by its driver; the scripted
analyst and the enrollment callable are deliberate D-12/D-19 deterministic
seams, documented in the READMEs, not unwired placeholders.

## Self-Check: PASSED
