---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 05
subsystem: testing
tags: [socket-guard, determinism, ast-assertion, criterion-6, harness-clients]

requires:
  - phase: 20-04
    provides: "`client_anthropic.py` (the third `client_*.py`, making the exact leg count 3) and the rewritten `--live` handling in `runner/drive.py` whose AST this plan reads"
provides:
  - "A socket-refusing guard that legs 1 and 3 are driven in-process inside, proving no network egress at all — strictly stronger than 'no model call'"
  - "Seven numbered controls, every one observed red under a named mutation"
  - "Leg 2's exclusion from the guard, stated by name with `H-07`'s reason and with `model_stub`'s fail-loud behaviour named as its alternative proof"
  - "Three AST properties over `runner/drive.py` asserting `--live` is one flag, one meaning, one driving call site"
  - "A guarded-or-excluded leg-set assertion against `known_legs()`, so a fourth harness cannot join unmeasured"
affects: [20-06, 20-07, 20-08]

tech-stack:
  added: []
  patterns:
    - "Process-global socket refusal as the proof of a determinism claim, copied (never imported) from the producer-side precedent"
    - "A control that distinguishes a whole guard from half a guard: target name resolution, not a literal IP"

key-files:
  created:
    - tests/examples/test_hw1_harness_clients_no_model.py
  modified:
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "CONTROL 1 was rewritten because its specified form could not be made to fail; the finding is written into the shipped docstring rather than quietly fixed"
  - "A seventh control was added beyond the plan's six, so the third `--live` property is not a property nobody has watched fire"
  - "The guard is a test and not part of the runner, because the clients are child processes and a guard in the runner cannot reach their interpreters without the clients importing something"

patterns-established:
  - "Guard arming is asserted in situ, inside the same context the subject runs in, so a drive under a dead guard cannot pass"
  - "A coverage property carries two vacuity guards when it has two ways to read nothing"

requirements-completed: [CLNT-26]

duration: 78min
completed: 2026-08-21
---

# Phase 20 Plan 05: The No-Model Guard and the Single `--live` Flag — Summary

**Legs 1 and 3 are now proven to reach the door with no network egress at all — not even a DNS query — by driving them in-process inside a socket-refusing guard, and `--live` is proven structurally to be one flag with one meaning and one driving call site.**

## Performance

- **Duration:** ~78 min
- **Started:** 2026-08-20T23:40:00Z
- **Completed:** 2026-08-21T00:58:00Z
- **Tasks:** 2 of 2
- **Files modified:** 2 (1 created, 1 regenerated)

## Commits

| Task | Commit | What |
| --- | --- | --- |
| 1 | `1e8a784` | The guard, the in-process drive of legs 1 and 3, CONTROL 1–3, the written leg-2 exclusion |
| 2 | `a50595c` | The three `--live` AST properties, CONTROL 4–7, retirement inventory regenerated |

## What the guard forbids, and what it permits

Stated plainly, because the scope is the whole value of the instrument:

**Forbidden** — inside `tests/examples/test_hw1_harness_clients_no_model.py::install_no_model_guard`, any call reaching `socket.socket.connect` or `socket.create_connection` raises `AssertionError`. That covers every outbound TCP connection *and*, because `create_connection` is patched ahead of its own address resolution, every DNS lookup that would precede one. Legs 1 (`client_adk.py`) and 3 (`client_langgraph.py`) run entirely inside it and do not trip it: `stdio_client` spawns the door over pipes, and pipes are not sockets.

**Permitted** — everything the guard does not wrap. Concretely, **leg 2 is not driven inside it at all**, and that is deliberate rather than an oversight. `H-07` measured that `claude_agent_sdk` routes everything, including its own MCP client, through the bundled `claude` CLI subprocess, which talks HTTP over loopback to the copied model stand-in at `runner/model_stub.py`. That connection is the leg working. A guard that failed on it would be measuring the instrument rather than the subject. Leg 2's determinism is proven a different way — the stand-in declares its exchanges, refuses drift, refuses exhaustion, and a passing run makes exactly two requests — and that proof belongs to plan `20-04`, not here.

The exclusion is written into the module docstring by name and is itself gated: `test_the_excluded_leg_and_its_alternative_proof_are_stated` fails if the paragraph naming `client_anthropic.py`, `leg 2`, `model_stub` and `H-07` is deleted. An exclusion stated is a scope boundary; an exclusion unstated is a hole.

The guard is also scoped so it cannot be *too* narrow to matter in the other direction: `test_every_discovered_leg_is_guarded_or_excluded_by_name` compares `GUARDED_LEGS | {EXCLUDED_LEG}` against `runner/drive.py::known_legs`, so a fourth `client_*.py` makes this module red rather than silently unguarded.

## The observed content address

Both guarded legs printed, and agreed on:

```
5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5
```

The same address the reference client and all three legs produce under `make example-hw1-harness-clients`, which was re-run at this plan's close: three legs plus the reference, all `MATCH`, declared company names on every line, **zero refusal lines**.

## Controls — every one observed red

Seven, not six. Each mutation was applied to the shipped file, `pytest` was run, the named control failed, and the file was restored from a pristine copy.

| Control | What it holds | Mutation applied | Observed |
| --- | --- | --- | --- |
| 1 | The `socket.create_connection` patch refuses **before name resolution** | replaced `socket.create_connection = refuse` with `pass` | `FAILED …::test_the_guard_refuses_before_a_name_is_even_resolved` — `socket.gaierror: [Errno -2] Name or service not known`, surfaced as *"a DNS query left this process before anything refused"* |
| 2 | The `socket.socket.connect` patch refuses | replaced `socket.socket.connect = refuse` with `pass` | `FAILED …::test_the_guard_refuses_socket_connect` |
| 3 | Both names are restored, so no later test in the process is affected | replaced the two restore lines in `finally` with `pass` | `FAILED …::test_the_guard_restores_both_patched_names` |
| 4 | A second live flag is reported | `extra = sorted({…})` → `extra = []` | `FAILED …::test_a_second_live_flag_is_a_violation` |
| 5 | Two driving call sites, one inside `if args.live:`, are both reported | `if len(sites) > 1:` → `if False:` and `inside = [...]` → `inside = []` | `FAILED …::test_a_second_driving_call_site_inside_a_live_branch_is_a_violation` |
| 6 | No `--live` at all is a violation, not an empty finding set | the vacuity branch returns `[]` instead of the violation | `FAILED …::test_no_live_flag_at_all_is_a_violation_rather_than_an_empty_finding` |
| 7 | A leg named inside a live branch is reported | `and node.value in set(legs)` → `and False` | `FAILED …::test_a_leg_named_inside_a_live_branch_is_a_violation` |

**Controls that could not be made to fail: none — after CONTROL 1 was rewritten. Before the rewrite there was one, and it is reported below rather than silently repaired.**

### The finding: CONTROL 1 as specified could not be made to fail

The plan specified CONTROL 1 as *"inside the guard, attempt `socket.create_connection(("127.0.0.1", 1))` and assert it raises the guard's own `AssertionError`."* That was written and it passed. It also passed **with the `socket.create_connection` patch removed entirely** — the module stayed 13/13 green against half a guard.

The cause is that the standard library's own `create_connection` calls `sock.connect(sa)` internally, and `sock.connect` is the *other* patched name. So a loopback-IP probe through `create_connection` is refused either way, and the control could not distinguish a whole guard from half a guard. Measured directly:

```
only socket.socket.connect patched:
  ("127.0.0.1", 1)                     -> AssertionError REFUSED
  ("no-such-host-ccf-probe.invalid",80) -> gaierror [Errno -2] Name or service not known
```

The second line is what the second patch actually buys, and it is a real property rather than a redundancy: `create_connection` resolves its target *before* it connects, so with only `connect` patched a hostname target sends a DNS query — genuine egress — and fails at resolution instead of at the guard. CONTROL 1 now targets `no-such-host.ccf-no-model-guard.invalid` (RFC 2606 reserves `.invalid`), which makes the two patches distinguishable and upgrades the module's claim from "no connection" to "not even a name lookup". The finding, its measurement, and the reason for the rewrite are written into the shipped control's docstring, where the next reader of that control will meet them.

## `--live` — one flag, one meaning, asserted structurally

Three properties over `examples/hw1-harness-clients/runner/drive.py`, parsed with `ast` rather than grepped, because a flag spelled in a docstring or a help string is not a code path:

1. `live_flag_violations` — exactly one `--live*` declaration reaches `add_argument`, and it is `--live`. Zero declarations is itself a violation (CONTROL 6), so a runner that lost criterion 6's opt-in cannot read as compliant.
2. `driving_call_site_violations` — exactly one call site for `drive_leg`, and it sits inside no `ast.If`/`ast.IfExp` whose test consults the live value. Zero call sites is a violation, so a rename makes the property red rather than vacuous.
3. `live_leg_coverage_violations` — no leg discovered by `known_legs` is named inside any branch on the live value, so no leg can be reachable in one mode and not the other. Two vacuity guards, because it has two ways to read nothing: an empty leg set, and a `--live` that is declared and never consulted.

Confirming counts against the tree: `grep -c '--live"' runner/drive.py` → `1`; `grep -c 'live-model\|live-deployment' runner/drive.py` → `0`.

**No test in this module passes `--live` to anything.** `H-09`'s live meaning is *point at a real populated deployment*, which CI does not have; the claim under test is structural — that the flag exists, is singular, and does not fork the driving path. The only `--live` strings executed anywhere in the module are inside `ast.parse` source arguments in CONTROL 4 and CONTROL 5, which are parsed and never run.

## Verification

| Check | Result |
| --- | --- |
| `pytest tests/examples/test_hw1_harness_clients_no_model.py -q` | **14 passed** (task 1 alone: 7; plan required ≥5 then ≥9) |
| `pytest tests/examples -q` | **398 passed, 37 skipped** — the guard leaks into no later test |
| `make ci-core` | **exit 0** — 4032 passed / 118 skipped, then 406 passed, then 154 passed |
| `pytest tools/docs_tests/…::test_the_committed_report_is_current` | **passed** |
| `pytest tests/invariants/test_citation_coverage.py -q` | **5 passed** |
| `python -m tools.lints --citations` | **0 findings** |
| `make example-hw1-harness-clients` | **exit 0**, three legs + reference all `5d7bfa49…`, declared names present, zero refusal lines |
| `git diff --stat 9e4bd0e..HEAD -- src/` | **empty** (criterion 7) |
| `git diff -- tools/lints/allowlist.yaml tools/lints/no_hardcoding.py` | **empty** |
| `git status --porcelain examples/hw1-companies-over-revenue/` | **empty** |
| `ls examples/hw1-harness-clients/*.py \| wc -l` | **3** |

## Deviations from Plan

### 1. [Rule 1 — Bug] CONTROL 1 as specified was vacuous and was rewritten

- **Found during:** Task 1, sabotage verification.
- **Issue:** The plan's CONTROL 1 (`socket.create_connection(("127.0.0.1", 1))`) passed with the `create_connection` patch removed, because the stdlib delegates to the patched `connect`. A control that cannot fail is not a control.
- **Fix:** Retargeted at an unresolvable hostname, which distinguishes the two patches and asserts the stronger property (refusal precedes name resolution). The finding is recorded in the shipped docstring and above, not silently repaired.
- **Files:** `tests/examples/test_hw1_harness_clients_no_model.py`
- **Commit:** `1e8a784`

### 2. [Rule 2 — Missing critical coverage] A seventh control was added

- **Found during:** Task 2.
- **Issue:** The plan named controls for two of the three `--live` properties. `live_leg_coverage_violations` would have shipped as a property nobody had ever watched report anything — the same standing as a guard nobody has watched refuse.
- **Fix:** `CONTROL 7` doctors a tree containing `if args.live and leg != 'adk': continue` and asserts a violation, and exercises both of that function's vacuity guards.
- **Files:** `tests/examples/test_hw1_harness_clients_no_model.py`
- **Commit:** `a50595c`

### 3. [Plan-text drift, no code change] Two names in the plan predate the tree

Reported rather than accommodated, per the standing instruction not to reshape the tree to satisfy a plan snippet:

- The plan's `<interfaces>` and `<mechanical_constraint>` are accurate, but its `<retirement_currency>` and acceptance criteria are written against a runner the plan calls `run.py` in places elsewhere in this phase's plan set. **No `run.py` was created**; every probe here targets `examples/hw1-harness-clients/runner/drive.py`, the real name, which is structurally load-bearing (`H-11` and the `artifacts/` bijection in `tests/examples/test_artifact_schema_headers.py`).
- The plan's task 1 acceptance criterion asks for "at least 5 tests" from a module the plan describes as containing one drive plus three controls. The shipped task-1 module has 7, because the leg-set accounting and the docstring-exclusion gate are also tests.

## Deferred Issues

None. No out-of-scope discovery was made; nothing was logged to `deferred-items.md`.

## Known Stubs

None. Every function in the shipped module has a live caller and a control.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file-access pattern and no schema. It adds a test that *removes* a capability (network egress) for the duration of a context, and the four dispositions in the plan's threat register (`T-20-18` through `T-20-21`) are each discharged by a control observed red in the table above; `T-20-SC` is discharged trivially — no package was installed.

## Self-Check: PASSED

- `tests/examples/test_hw1_harness_clients_no_model.py` — FOUND
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — FOUND, modified
- Commit `1e8a784` — FOUND in `git log`
- Commit `a50595c` — FOUND in `git log`
