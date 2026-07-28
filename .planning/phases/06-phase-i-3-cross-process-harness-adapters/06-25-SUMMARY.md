---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 25
subsystem: skills
tags: [d-impl-59, federation, naming, skilling, admission, governance]
requires: ["06-18", "06-19", "06-20", "06-21", "06-24"]
provides:
  - "SkillType member `peering` — the federation category as a skill type token"
  - "PeeringBinding / PeeringInvocation / PeeringSkillRegistry / PeeringSkillUnregistered"
  - "`peering_skills=` on Agent and AgentFactory"
  - "tests/integration/test_agent_slice.py — the peering wired/unwired inversion pair at the agent seam"
  - "tests/integration/test_agent_slice.py — a peering skill read writes no admission record (D-IMPL-59 part 4)"
  - "tests/skills/test_catalog.py — the retired `a2a` token is refused by name"
affects:
  - "src/ccf/skills/catalog.py, src/ccf/skills/dispatch.py, src/ccf/skills/__init__.py"
  - "src/ccf/agents/agent.py, src/ccf/agents/factory.py"
  - "tests/fixtures/banking/skills/ — the peering entries, both version lanes"
tech-stack:
  added: []
  patterns:
    - "retiring an enum member is a breaking schema change: both version lanes take a major bump and the old token is refused by name, never aliased"
    - "sibling skill types get identical wiring proofs (wired/unwired inversion pair), so a divergence reads as one type being special"
key-files:
  created: []
  modified:
    - src/ccf/skills/catalog.py
    - src/ccf/skills/dispatch.py
    - src/ccf/skills/__init__.py
    - src/ccf/agents/agent.py
    - src/ccf/agents/factory.py
    - tests/fixtures/banking/skills/remote_products_peering.yaml (relocated from remote_products_a2a.yaml)
    - tests/fixtures/banking/skills/covenant_metrics_tool.yaml
    - tests/skills/test_catalog.py
    - tests/skills/test_dispatch.py
    - tests/integration/test_agent_slice.py
decisions:
  - "SkillType member `a2a` -> `peering`; the retired member is REMOVED and refused by name, not aliased"
  - "Both version lanes take a MAJOR bump on affected entries — retiring an enum member is breaking; grant schema_version unmoved (see deviations)"
  - "Version bumps scoped to affected artifacts rather than every skill-catalog-entry fixture (see deviations)"
  - "A2ASkillUnregistered -> PeeringSkillUnregistered and _invoke_a2a -> _invoke_peering, neither enumerated by the plan's naming table"
metrics:
  duration: ~70 min
  tasks: 2
  completed: 2026-07-27
---

# Phase 06 Plan 25: the skilling and agent-construction surface speaks Peering

D-IMPL-59 part 1 is complete across the skill half: the skill type token, its
binding and invocation contracts, its registry, the agent/factory parameter that
carries it, and the banking fixtures all name the **category** — a peer fabric
holding its own Control Plane — rather than the transport that first carried it.
Nothing in the tree describes the federation category as `a2a` any more, and no
code was deleted.

## Verification path — the source actually exercised

06-24's finding held and was re-confirmed before the first edit. There is no
`.venv` inside an agent worktree, and the main checkout's interpreter has **both**
`ccf` and `ccf_runtime` installed editable against the **main** repo, so the
plan's literal `.venv/bin/python -m pytest` would have verified the wrong tree.
Every mypy, lint and pytest invocation here used:

```
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 /home/parkave/ccf_code/.venv/bin/python -m pytest -q
```

Both resolutions confirmed inside this worktree:

- `ccf.__file__` = `/home/parkave/ccf_code/.claude/worktrees/agent-acfebc5235dcf45ea/src/ccf/__init__.py`
- `ccf_runtime.__file__` = `/home/parkave/ccf_code/.claude/worktrees/agent-acfebc5235dcf45ea/runtime/ccf_runtime/__init__.py`

## Results

| Check | Result |
|---|---|
| `pytest -q -rs` (baseline before any change) | 983 passed, 2 skipped — matches 06-24's recorded count exactly |
| `pytest -q -rs` (final, `CCF_REQUIRE_HARNESSES=1`) | **987 passed, 2 skipped** — baseline + the 4 new tests, no regression |
| `mypy` | Success, 99 source files |
| `tools.lints --all` | exit 0 |
| `git diff --diff-filter=D --name-only pre-peering -- src/ runtime/ tests/ tools/` | **no output** |
| `grep -rn "a2a_skills\|A2AInvocation\|A2ASkillRegistry\|A2ABinding\|A2ASkillUnregistered" src runtime tests tools` | 0 |
| `grep -rn "ccf\.a2a\|ccf_runtime\.a2a" src runtime tests tools` | 0 |
| `grep -c 'Literal\["local_callable", "tool", "mcp", "peering"\]' src/ccf/skills/catalog.py` | 1 |
| `grep -rn '"a2a"' src/ccf/skills/` | 0 |
| `grep -c "peering_skills" src/ccf/agents/{agent,factory}.py` | 4 and 4 |

`git rev-parse pre-peering` = `f45a23d639816ef40f3b169194628f4669012c9b`, matching
the sha 06-24 recorded. The no-deletion constraint was checked against that tag,
not `HEAD~1`.

## Renames

| From | To | Rename status |
|---|---|---|
| `tests/fixtures/banking/skills/remote_products_a2a.yaml` | `tests/fixtures/banking/skills/remote_products_peering.yaml` | **R054** |

Moved with `git mv`. R054 clears git's default 50% threshold, so the merge path
sees a rename rather than a deletion — but only after the comment prose was
condensed (deviation 5).

### Identifier renames

| From | To |
|---|---|
| `SkillType` member `"a2a"` | `"peering"` |
| `A2ABinding` | `PeeringBinding` |
| `A2AInvocation` | `PeeringInvocation` |
| `A2ASkillRegistry` | `PeeringSkillRegistry` |
| `A2ASkillUnregistered` | `PeeringSkillUnregistered` |
| `_invoke_a2a` | `_invoke_peering` |
| `a2a_skills=` on `Agent` / `AgentFactory` | `peering_skills=` |
| `_BINDING_CONTRACTS` key `"a2a"` | `"peering"` |

Deliberately **not** renamed, on 06-24's rule that a transport is correctly named
for the protocol it speaks: `lf_a2a.py`, `typed_http.py`,
`tests/fixtures/banking/a2a.yaml` (peering *transport* configuration — its
`receive_path: /ccf/a2a/inbound` and `lf_a2a:` block are literal A2A wire paths),
the vendor `a2a` / `a2a_pb2` package prefixes in the dispatch import scan, and
`LfA2AWire`. The `mcp` skill type, `McpBinding`, `McpSkillRegistry` and
`mcp_skills` stay put per D-IMPL-59 part 3.

## Fixture version pairs

Recorded because a version bump that is not recorded is indistinguishable from
one that did not happen.

**`tests/fixtures/banking/skills/remote_products_peering.yaml`**

| Artifact | `schema_version` | `artifact_version` | `skill_version` pin |
|---|---|---|---|
| `entry` — remote-exposure-products | 1.0.0 → **2.0.0** | 1.0.0 → **2.0.0** | — |
| `grant` — treasury-remote-products | 1.0.0 → 1.0.0 (unmoved) | 1.0.0 → **1.1.0** | 1.0.0 → **2.0.0** |
| `denied.entry` — remote-privileged-products | 1.0.0 → **2.0.0** | 1.0.0 → **2.0.0** | — |
| `denied.grant` — treasury-remote-privileged | 1.0.0 → 1.0.0 (unmoved) | 1.0.0 → **1.1.0** | 1.0.0 → **2.0.0** |
| `agent_invocable.entry` — portfolio-remote-products | *new* at 2.0.0 | *new* at 2.0.0 | — |
| `agent_invocable.grant` | *new* at 1.0.0 | *new* at 1.0.0 | 2.0.0 |
| `retired_token.entry` | *new* at 1.0.0 | *new* at 1.0.0 | — (deliberately the retired token) |

**`tests/fixtures/banking/skills/covenant_metrics_tool.yaml`**

| Artifact | `schema_version` | `artifact_version` |
|---|---|---|
| `variants.a2a` → `variants.peering` — covenant-metrics-remote | 1.0.0 → **2.0.0** | 1.0.0 → **2.0.0** |

**Why major on both lanes.** Retiring a `SkillType` member is *breaking*: an
artifact valid under the old schema is invalid under the new one, because the old
token is refused rather than migrated. `schema_version` moves because the member
was removed from the class's shape; `artifact_version` moves because an entry
under the new token is not interchangeable with its predecessor. This is strictly
larger than the D-IMPL-54 / D-05 precedent, where a binding *value* change was a
content change only and moved `artifact_version` a minor step. Grant
`schema_version` does **not** move — the skill-grant class's shape is untouched by
a skill-type rename — while grant `artifact_version` takes a minor bump for the
re-pin, exactly as D-IMPL-54 did.

## The two threat-register properties, and how they were proved to bite

**T-06-106 — a grant under the old token silently reinterpreted.**
`tests/skills/test_catalog.py::test_the_retired_a2a_token_is_refused_by_name`
asserts the retired token is not in `SKILL_TYPES` and that an entry declaring it
raises, with the error naming both the offending token and the surviving
`peering` member — refused *by name*, against the enumerated closed world, rather
than by accident. What would fail it: adding `a2a` back as an alias, or widening
`SkillType` to tolerate it for backwards compatibility.

**T-06-107 — a peering skill read becoming a fabric write.**
`tests/integration/test_agent_slice.py::test_a_peering_skill_invocation_writes_no_admission_record`
asserts three things after a successful invocation through the agent seam: no
`ccf.admission-record` artifact exists in the Control Plane, no returned product
is an `AdmittedProduct`, and the audit plane carries `skill_invoked` but neither
`peering_admitted` nor `peering_admission_refused`.

**Observed failure (acceptance criterion).** The conflation was simulated by
monkeypatching `ccf.skills.dispatch._invoke_peering` to also persist an
`AdmissionRecord` and append a `peering_admitted` audit action — i.e. a dispatch
path wired to the admission gate:

```
>           assert fabric.registry.keys_of_class(ADMISSION_RECORD.class_id) == ()
E           AssertionError: assert ('tenant-unde...on-record/x',) == ()
E             Left contains one more item: 'tenant-under-test/ccf.admission-record/x'
1 failed, 13 deselected
```

The scratch block was removed immediately; the committed tree has no `neuter`
reference and the full suite is green. The falsification was done by monkeypatch
rather than by editing `/src`, so no neutered source could be left behind.

## Prior-wave closures carried forward intact

- **06-18** — `GATE_LINEAGE_ATTRIBUTABILITY` (in `src/ccf/products/gates.py`,
  untouched here) and the federated gate sequence are unchanged;
  `tests/gates/test_federated_gates.py` and
  `tests/peering/test_admission_attributability.py` pass.
- **06-19** — `AdmissionRecord` stays in `src/ccf/peering/admission.py` with
  `class_id` exactly `ccf.admission-record`; persistence on admission and the
  contract-parametrized `resolve_artifact` / `resolve_artifact_at_uri` path are
  untouched. `tests/peering/test_admission_record.py` passes, and this plan's new
  test *reuses* its `_record()` builder for the falsification rather than
  reimplementing one.
- **06-21** — the transport instance scan and its live count guard still bind;
  the rename added no skill-reachable transport. The A2-scoped `AdmittedProduct`
  assertion survives verbatim in `tests/crossproc/test_peering_exchange.py`:
  `grep -cE "advisory A2\b|\(A2\)|finding A2\b"` = **2**, `grep -c "unforgeable"`
  = **0**. The strong form was **not** restored.
- **06-24** — `tests/peering/test_peering_verdict.py` (the part-4 property, 6
  tests) passes untouched. Its gate-id `peering-*` value convention was honoured:
  the new test asserts against `peering_admitted` /
  `peering_admission_refused`, not the retired `a2a_*` names.
- **06-24's docs boundary** — `docs/PHASE_I3_GATE.md` and `docs/DECISIONS.md`
  were **not** touched. Recording the rename in the gate document is 06-22's job.

## Deviations from Plan

### 1. [Rule 3 — Blocking] Acceptance criterion and mandated behaviour are in direct conflict

- **Found during:** Task 1.
- **Issue:** the criterion `grep -rlc 'skill_type: *a2a' tests/fixtures/ | wc -l == 0`
  cannot hold at the same time as the behaviour bullet *"a catalog artifact
  declaring the old `a2a` token is refused by name"* plus its mandated test. The
  refusal test needs an artifact carrying the retired token, and under the
  No-Hardcoding Rule (§6.4) that document is a **fixture value**, never a test
  literal. Satisfying the grep literally would have meant inlining the retired
  document in test code — trading a real invariant for a grep.
- **Fix:** the retired token lives in a `retired_token:` block in
  `remote_products_peering.yaml`, clearly commented as negative-test material.
  Verified that the only two matches in `tests/fixtures/` are that block and its
  own explanatory comment — **no live entry declares it**, which is what the
  criterion was protecting. The stricter reading now holds instead: no
  *registered* or *dispatchable* fixture entry names the category `a2a`.
- **Files modified:** `tests/fixtures/banking/skills/remote_products_peering.yaml`.

### 2. [Rule 3 — Blocking] Plan named a constant that does not exist

- **Found during:** Task 1.
- **Issue:** the naming-surface table and the `read_first` both name a
  `BINDING_BY_TYPE` mapping "at line 137". No such symbol exists; the actual
  mapping is the private `_BINDING_CONTRACTS`.
- **Fix:** renamed the `"a2a"` key in `_BINDING_CONTRACTS`. No `BINDING_BY_TYPE`
  was created to make the plan's literal text true.
- **Files modified:** `src/ccf/skills/catalog.py`.

### 3. [Rule 3 — Blocking] `PeeringBinding`'s importers had to move in task 1's commit

- **Found during:** Task 1.
- **Issue:** the plan assigns `A2ABinding` → `PeeringBinding` to task 1 and
  `dispatch.py` to task 2, but `dispatch.py` imports that class. Committing task 1
  alone as specified would have left an **unimportable tree** — every test in the
  suite failing at collection.
- **Fix:** the six `PeeringBinding` references in `dispatch.py` (import,
  annotations, `isinstance`, docstrings) moved in task 1's commit; everything else
  in `dispatch.py` waited for task 2. A broken intermediate commit is worse than
  minor scope bleed, and the commit message records the reason.
- **Files modified:** `src/ccf/skills/dispatch.py`.

### 4. [Rule 2 — Consistency of the seam's vocabulary] Two identifiers the naming table did not enumerate

- **Found during:** Task 2.
- **Issue:** `A2ASkillUnregistered` (which 06-24 explicitly deferred to *this*
  plan) and the private `_invoke_a2a` appear nowhere in the plan's naming-surface
  table, though the plan's own success criterion is that **no** identifier names
  the category `a2a`. Leaving `A2ASkillUnregistered` would have meant a
  `PeeringSkillRegistry` raising an `A2A`-named error — the exact defect class
  this wave exists to remove, and a user-visible one.
- **Fix:** renamed to `PeeringSkillUnregistered` and `_invoke_peering`. The
  user-facing refusal message strings ("peering endpoint … already registered",
  "no peering transport is registered for endpoint") followed.
- **Files modified:** `src/ccf/skills/dispatch.py`, `src/ccf/agents/agent.py`,
  `tests/skills/test_dispatch.py`.

### 5. [Rule 3 — Blocking] Rename similarity fell below the merge gate's threshold

- **Found during:** Task 2 — exactly the constraint 06-24's deviation 4 predicted.
- **Issue:** adding the `agent_invocable` and `retired_token` blocks plus
  version-rationale comments grew the fixture 87 → 155 lines. Similarity dropped
  to **R047**, three points under git's default 50%, so the move surfaced as
  `D` + `A` — a *reported deletion* and therefore a merge-path blocker, even
  though nothing was lost. Splitting the move and the growth into separate commits
  does **not** help: the constraint is checked cumulatively against `pre-peering`.
- **Fix:** condensed four comment blocks (the versioning rationale, the grant
  re-pin note, the `agent_invocable` preamble and the `retired_token` preamble)
  from ~32 lines to ~17, keeping every load-bearing statement and moving the long
  form into this SUMMARY. Final: **R054**. No fixture data was removed.
- **Files modified:** `tests/fixtures/banking/skills/remote_products_peering.yaml`.

### 6. [Rule 2 — Missing critical coverage] The "existing end-to-end test" the plan relies on did not exist for peering

- **Found during:** Task 2.
- **Issue:** the plan asserts the factory→agent→dispatch threading is *"asserted
  by the existing end-to-end skill-invocation test rather than by inspection"*.
  `tests/integration/test_agent_slice.py` carried that inversion pair for `mcp`
  **only**. For `peering` the threading was covered by nothing above the dispatch
  function, so a rename that updated declarations but broke the threading would
  have passed the whole suite.
- **Fix:** added `_peering_granted_agent` plus the wired/unwired pair, mirroring
  the MCP helper's shape rather than diverging from it (the plan's `read_first`
  asks for exactly this). The unwired half re-asserts the fail-closed
  refusal-by-name through the rename.
- **Files modified:** `tests/integration/test_agent_slice.py`,
  `tests/fixtures/banking/skills/remote_products_peering.yaml` (the
  `agent_invocable` block the pair needs).

### 7. [Informational] Version-bump scope held to the affected artifacts

`schema_version` names the artifact *class's* lane, so a strict reading would move
it on **every** `skill-catalog-entry` fixture — including the dozens of `tool`
entries in `grants.yaml` that the rename does not touch. The plan says "every
**affected** fixture", and that narrower reading was taken: only entries whose
`skill_type` was `a2a`. Recorded because the wider sweep is a defensible
alternative a reviewer may prefer, and nothing in the mechanism enforces
consistency (`schema_version` is validated as semver and otherwise a declaration).

### 8. [Informational] The `NotYetBound` tail assertion was widened

`test_the_not_yet_bound_message_names_no_outstanding_transport` asserted the tail
names neither `A2A` nor `MCP`. Since `peering` is now the fourth bound type's
name, `"Peering"` and `"peering"` were added to that assertion — otherwise the
test would have kept guarding a string that no longer describes the type.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema at a
trust boundary was introduced. This plan is a re-description of existing
structure plus three property tests; the one schema change (a retired enum
member) *narrows* what is admissible rather than widening it. Both register
entries are addressed and both were shown to bite.

## Commits

| Commit | Task |
|---|---|
| `9acf32a` | Task 1 — the catalog token and binding contract, versioned as a schema change |
| `0d57313` | Task 2 — the dispatcher and the agent construction surface |

## Self-Check: PASSED

- `tests/fixtures/banking/skills/remote_products_peering.yaml` — FOUND
- `tests/fixtures/banking/skills/remote_products_a2a.yaml` — absent, as intended (moved, R054)
- `src/ccf/skills/catalog.py` declares `PeeringBinding` and the four-member `SkillType` — FOUND
- `src/ccf/skills/dispatch.py` declares `PeeringInvocation`, `PeeringSkillRegistry`, `PeeringSkillUnregistered` — FOUND
- `peering_skills=` on both `Agent` and `AgentFactory` — FOUND (4 references each)
- commits `9acf32a`, `0d57313` — FOUND in `git log`
- `git rev-parse pre-peering` = `f45a23d639816ef40f3b169194628f4669012c9b` — FOUND
- no deletions vs `pre-peering` over `src/ runtime/ tests/ tools/` — CONFIRMED
