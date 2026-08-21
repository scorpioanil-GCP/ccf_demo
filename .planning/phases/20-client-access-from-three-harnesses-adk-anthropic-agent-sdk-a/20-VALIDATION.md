---
phase: 20
slug: client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-20
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `20-RESEARCH.md` § Validation Architecture. The per-task map is
> completed by the planner; everything above it is measured.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (measured) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/examples -q` |
| **Full suite command** | `make ci` |
| **Estimated runtime** | quick ~10s · `make ci` minutes |

**Interpreter rule — `.venv/bin/python` always.** Bare `python` does not exist on this
host; a plan that writes `python` reports a false red. **CI's interpreter posture is
per-job, not blanket** — the earlier blanket claim here was wrong and is corrected: the
`test` job runs `make PYTHON=python …` because it installs into the hosted interpreter,
while the **examples job provisions a `.venv`** and runs bare `make examples`
(`.github/workflows/ci.yml`), so `$(PYTHON)` already resolves to `.venv/bin/python`
there. It matters because the reason is destined for a Makefile comment in `20-02`.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/examples -q`
- **After every plan wave:** `make ci-core` — a gate `ci-core` does not reach is not a
  gate (DEF-17-08)
- **Before `/gsd:verify-work`:** `make ci` exit 0, then the §3.1 cross-AI panel on
  shipped code
- **Max feedback latency:** ~10 seconds at task granularity

---

## Criterion → Validation Map

The ten ROADMAP Success Criteria are the gate target and are closed. Each must be
verified by a command, not by inspection.

| # | Criterion | Level | Automated command | Exists? |
|---|-----------|-------|-------------------|---------|
| 1 | ADK registers/calls/prints, zero `ccf` imports | example run + AST gate | `make example-hw1-harness-clients`; `pytest tests/examples/test_client_example_purity.py -q` | ❌ new |
| 2 | Anthropic Agent SDK, same | example run + AST gate | same | ❌ new (Q1 verdict: viable) |
| 3 | LangGraph, same | example run + AST gate | same | ❌ new |
| 4 | Same content address as `consume.py` | assertion inside the runner | `make example-hw1-harness-clients` | ❌ new |
| 5 | AST purity gate + named sabotage control | unit tests + controls | `pytest tests/examples/test_client_example_purity.py -q` | ⚠️ module exists; per-root permitted set + controls are new |
| 6 | Deterministic default, `--live` opt-in | CI target + no-model guard | `make examples`; new no-model guard test with its own control | ❌ new |
| 7 | No new SDK mechanism | diff assertion at close | `git diff --stat <base>..HEAD -- src/ccf/client/` empty | ✅ command exists, assertion new |
| 8 | Duplicates resolved in-phase | tree assertion + green pipeline | `test -d examples/s2-01-external-consumers` must fail; `make example-ext-00`; `make gate-tools` | ⚠️ partly exists |
| 9 | README content | structural test | new test asserting required README elements by name (now **ten** elements — leg 2's `--live` `ANTHROPIC_BASE_URL` requirement and the prompt's source were added at revision) | ❌ new |
| 10 | `make ci` exit 0, target wired | full pipeline | `make ci`; plus a test asserting the new target is in the `examples:` prerequisite list | ⚠️ `make ci` exists, wiring assertion new |

**Three corrections to this map, made at plan revision and worth reading before the
first wave.**

1. **Criteria 1-3 say the client *prints the returned Context Product*, and an address
   check does not measure that.** Every address assertion reads a 64-hex string; a client
   printing the content address and nothing else would pass the whole phase with criteria
   1-3 false. `20-03` T3 adds
   `examples/hw1-harness-clients/runner/run.py::payload_violations`, which requires
   declared company `name` markers in each leg's stdout and requires the marker **set** to
   match the reference run's. Three controls, listed in the register below.
2. **`make ci-core` is RED at this phase's base commit, and Phase 20 caused it.**
   `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
   byte-compares `docs/surface/examples/RETIREMENT-COUPLINGS.md` against a fresh sweep;
   the report indexes `.planning/**`, and this phase's own CONTEXT and ROADMAP commits
   added references to `examples/s2-01-external-consumers/`. `gate-tools` runs that suite
   and both `ci-core` and `ci` compose `gate-tools`. Plan `20-01` task 4 establishes the
   green baseline; **every plan thereafter regenerates the report as its final task step**,
   because a `Makefile` edit (29 line-numbered rows), a `.planning/REQUIREMENTS.md` edit,
   an example tree moving, or simply the preceding plan's own `*-SUMMARY.md` re-stales it.
   The residual the chain cannot close — `20-08`'s own SUMMARY — is recorded as
   `<open_residual>` in `20-08-PLAN.md` with a manual close sequence, and exempting the
   test from `make ci` is named there as a `D-IMPL-NN` for Dave rather than a planner's
   call.
3. **Ruling 6 adds enforcement without adding a criterion, and the map is unchanged
   above because of it.** Dave's ruling 6 (`.planning/ROADMAP.md`, Phase 20) says
   explicitly that *the ten Success Criteria are unchanged*. What it adds is a gate:
   leg 2 must send prompt text, no plan named the prompt's source, and
   `cinv01a-prompt-shape` was **measured unable to catch it** — four realistic short
   agent prompts scored 0-1 against `PROMPT_SCORE_THRESHOLD = 2`, so an executor could
   ship a hardcoded system instruction into the flagship teaching example and pass
   purity, budget, payload and `make ci` with nothing red. The closure is `20-02` T4
   plus `20-04` T2, tracked by the new requirement `CLNT-32` rather than by an
   eleventh criterion. The design's blast radius was measured before adoption and is
   recorded in `20-02-PLAN.md`'s `<lint_blast_radius>`; the two genuine violations it
   surfaced are remediated in the same task, not allowlisted.

---

## Per-Task Verification Map

*Completed by the planner — one row per task, each with an automated command.*

Twenty-five tasks across eight plans in **eight** waves. **Every task carries an
`<automated>` verify** — there is no task whose completion is judged by inspection,
and no run of three consecutive tasks without an automated check.

**The waves are fully serial, and that is a revision, not the original shape.** Three
things forced it. `20-05` asserts `ls examples/hw1-harness-clients/*.py | wc -l` is `3`
and reads AST properties of the runner's `--live` handling, both of which `20-04` is
concurrently producing — so `20-05` moved behind `20-04`. Every plan from `20-01` on now
writes `docs/surface/examples/RETIREMENT-COUPLINGS.md`, and two same-wave plans writing
one generated file is a merge conflict waiting to happen. And every plan from `20-03` on
asserts a **tree-global** gate (`make ci-core` or `make ci`), which no plan can honestly
assert while a sibling is mutating the same tree — the recorded hazard behind
*sabotage agents must not share a tree*.

**The same rule holds inside a plan, between its own tasks, and that is a
correction.** `make ci-core` composes `gate-tools`, which runs the
retirement-inventory currency test, so a task that mutates the tree re-stales the
report for every later task until the regeneration runs. **In every plan, exactly
one task asserts the tree-global gates: the task that regenerates the inventory,
which is always the last one.** Earlier tasks assert scoped gates — targeted pytest
runs, greps, `make` targets for a single example. Two plans had the defect and both
are fixed: `20-05` T1 and `20-07` T2 each asserted `make ci-core` before their own
plan's regeneration step. A sweep of all eight plans' `<acceptance_criteria>` for
`make ci`/`ci-core` found no third instance — `20-03` T3, `20-04` T3, `20-06` T3 and
`20-08` T3 each assert it in the task that regenerates, and `20-01` and `20-08` T2
assert only scoped gates.

**`20-02` gained a fourth task at plan revision, and the ordering moved with it.**
`20-02` T4 (the `cinv01a` destination arm, Dave's ruling 6(b)) is now that plan's
last task, so it is the task that regenerates the inventory and the only one in
`20-02` that asserts `make ci-core`. T3 was demoted to scoped gates. The rule is
unchanged — exactly one task per plan asserts the tree-global gates, and it is the
one that regenerates last — only the task it lands on moved. Re-verified across all
eight plans after the revision: no task asserts `make ci`/`ci-core` before its own
plan's regeneration step.

Commands are
abbreviated here; each task's own `<acceptance_criteria>` carries the full form.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 20-01-T1 | 20-01 | 1 | CLNT-23..31 | source assertion | `grep -c '^- \[ \] \*\*CLNT-2[3-9]...' .planning/REQUIREMENTS.md` = 9; `git cat-file -t $(head -1 20-BASE-COMMIT.txt)` | ⬜ pending |
| 20-01-T2 | 20-01 | 1 | CLNT-27 | source assertion + invariant | `grep -q 'D-IMPL-163' docs/DECISIONS.md`; append-only diff check; `pytest tests/invariants/test_citation_coverage.py -q` | ⬜ pending |
| 20-01-T3 | 20-01 | 1 | CLNT-27 | document schema assertion | `.venv/bin/python -c` yaml probe: six rows, role keys, 3 above / 3 below, plus the marker fast-fail (distinct, ≥4 chars, non-substring, non-hex, no chrome collision) | ⬜ pending |
| 20-01-T4 | 20-01 | 1 | CLNT-27 | pipeline + idempotency | `pytest tools/docs_tests/test_retirement_sweep.py -q`; `make gate-tools`; two-run byte-compare of the regenerated report | ⬜ pending |
| 20-02-T1 | 20-02 | 2 | CLNT-27 | behavior | `.venv/bin/python -c` two consecutive `seeded_subject` drives; `git status --porcelain examples/hw1-companies-over-revenue/` empty | ⬜ pending |
| 20-02-T2 | 20-02 | 2 | CLNT-24 | behavior | `run.py > /tmp/hw1-runner.out && grep -Eq '[0-9a-f]{64}' /tmp/hw1-runner.out` (**redirect, not a pipe** — without `pipefail` a pipeline reports `grep`'s status, so a runner that prints an address then exits non-zero would pass); `compare_addresses` probe | ⬜ pending |
| 20-02-T3 | 20-02 | 2 | CLNT-31 | make wiring + unit | `make -n example-hw1-harness-clients`; `pytest tests/examples/test_hw1_harness_clients_wiring.py -q`. **Scoped gates only — `make ci-core` is asserted by T4, the task that now regenerates last** | ⬜ pending |
| 20-02-T4 | 20-02 | 2 | CLNT-32 | lint gate + 5 controls | `pytest tools/lints/tests/test_no_hardcoding.py -q`; `.venv/bin/python -m tools.lints --all`; `git diff tools/lints/allowlist.yaml` empty; `make example-ext-00`; `CLNT-32` in both tables; `git diff --stat -- src/` = 0; `make ci-core` | ⬜ pending |
| 20-03-T1 | 20-03 | 3 | CLNT-23 | AST assertion + behavior | zero-`ccf` AST probe on `client_adk.py`; no-domain-literal grep; hand drive prints 64-hex | ⬜ pending |
| 20-03-T2 | 20-03 | 3 | CLNT-23 | AST assertion + behavior | same probe on `client_langgraph.py`; `git diff --stat -- pyproject.toml` = 0 | ⬜ pending |
| 20-03-T3 | 20-03 | 3 | CLNT-24 | behavior + 6 controls | `make example-hw1-harness-clients`; distinct 64-hex count = 1; `payload_violations` probe (address-only stdout refused, empty marker list refused); `marker_violations` probe (substring, hex-only and chrome-colliding marker sets each refused); unknown-leg exits non-zero | ⬜ pending |
| 20-04-T1 | 20-04 | 4 | CLNT-26 | behavior + 3 controls | `offline_cli_environment` nine-variable probe; drift / exhaustion / orphan refusals observed | ⬜ pending |
| 20-04-T2 | 20-04 | 4 | CLNT-23, CLNT-32 | AST assertion + behavior | zero-`ccf` AST probe on `client_anthropic.py`; no `api.anthropic.com`; `pyproject.toml`/`ci.yml` unchanged; **prompt is data** — `grep -c 'CCF_HARNESS_PROMPT'` ≥ 1 and `grep -c 'environ.get'` = 0; `tools.lints --rules no-hardcoding --all` exits 0 | ⬜ pending |
| 20-04-T3 | 20-04 | 4 | CLNT-24, CLNT-26, CLNT-32 | behavior | `make example-hw1-harness-clients`; distinct 64-hex count = 1; `pgrep -f model_stub.py` empty; runner sets `CCF_HARNESS_PROMPT`; the `--live` `ANTHROPIC_BASE_URL` requirement is stated in the runner docstring and the refusal message | ⬜ pending |
| 20-05-T1 | 20-05 | 5 | CLNT-26 | in-process drive + 3 controls | `pytest tests/examples/test_hw1_harness_clients_no_model.py -q`; full `tests/examples` green (no guard leak). **Scoped gates only — `make ci-core` is asserted by T2, the task that regenerates the inventory** | ⬜ pending |
| 20-05-T2 | 20-05 | 5 | CLNT-26 | AST assertion + 3 controls | `grep -c '--live"' run.py` = 1; no `live-model`/`live-deployment`; `pytest …no_model.py -q` | ⬜ pending |
| 20-06-T1 | 20-06 | 6 | CLNT-25 | AST gate + controls C-20-1..7 | `pytest tests/examples/test_client_example_purity.py -q`; per-root probe; `grep -c rglob` = 0 | ⬜ pending |
| 20-06-T2 | 20-06 | 6 | CLNT-25 | budget gate + C-20-9 | `pytest tests/examples/test_client_example_budget.py -q`; `declared_budget` non-None; every client fits; headroom ≤ 30 lines over the largest client | ⬜ pending |
| 20-06-T3 | 20-06 | 6 | CLNT-25 | command identity + C-20-8 | `pytest tests/examples/test_client_example_purity.py -q`; `make ci-core` | ⬜ pending |
| 20-07-T1 | 20-07 | 7 | CLNT-29 | tree assertion | `test ! -d examples/s2-01-external-consumers`; one client per harness; `D-IMPL-125` unchanged | ⬜ pending |
| 20-07-T2 | 20-07 | 7 | CLNT-29 | tree assertion + 5 controls | `pytest tests/examples/test_hw1_harness_clients_retirement.py -q`; `grep -rn 's2-01' tests/` = 0. **Scoped gates only — T1's move stales the inventory, so `make gate-tools` and `make ci` are asserted by T3, the task that regenerates** | ⬜ pending |
| 20-07-T3 | 20-07 | 7 | CLNT-30 | pipeline + idempotency | `grep -c '^## ' 00-hello-context/README.md` = 7; `make example-ext-00`; `make gate-tools`; sweep re-run diff empty | ⬜ pending |
| 20-08-T1 | 20-08 | 8 | CLNT-31 | structural + gate re-run | `pytest test_client_example_purity.py test_client_example_budget.py test_citation_coverage.py -q`; gated lines unchanged | ⬜ pending |
| 20-08-T2 | 20-08 | 8 | CLNT-31, CLNT-26 | structural + 5 controls | `pytest tests/examples/test_hw1_harness_clients_readme.py -q`; three live targets; none in `examples:` | ⬜ pending |
| 20-08-T3 | 20-08 | 8 | CLNT-28, CLNT-32 | diff assertion + 2 controls | `make ci`; `git diff --stat $(cat 20-BASE-COMMIT.txt)..HEAD -- src/ \| wc -l` = 0; ten rows flipped (CLNT-23..32); ruling-6 `D-IMPL` entry appended carrying both blast-radius numbers | ⬜ pending |

---

## Wave 0 Requirements

Every missing verification target is created by a plan that runs **before or with**
the first task that depends on it. There is no separate Wave 0 plan because there is
no framework to install and no harness to stand up — `wave_0_complete: true` records
that each gap below has an owner and that its owner precedes its consumers.

| Wave 0 gap | Owned by | Wave | Consumed by |
|---|---|---|---|
| `examples/hw1-harness-clients/artifacts/scenario-rows.yaml` — the declared input | 20-01 T3 | 1 | 20-02 |
| `examples/hw1-harness-clients/runner/run.py` — seed-and-close runner | 20-02 T1/T2 | 2 | 20-03, 20-04, 20-05 |
| `make`-target-wiring test | 20-02 T3 | 2 | 20-08 (which must not duplicate it) |
| **`cinv01a` destination arm — the gate must exist before the files it governs** | 20-02 T4 | 2 | 20-03 (legs 1 and 3), 20-04 (leg 2), `CLNT-32` |
| **`CCF_HARNESS_PROMPT` — the prompt as runner-supplied data** | 20-04 T3 | 4 | 20-04 T2's client, 20-08's README |
| Per-root permitted set + controls C-20-1..C-20-8 | 20-06 T1/T3 | 6 | criterion 5 |
| Declared budget the budget gate parses, plus C-20-9 | 20-06 T2 | 6 | `test_client_example_budget.py` |
| No-model socket guard + controls for legs 1 and 3 | 20-05 T1 | 5 | criterion 6 |
| Tree assertion that `examples/s2-01-external-consumers/` is gone | 20-07 T2 | 7 | criterion 8 |
| Green baseline for `docs/surface/examples/RETIREMENT-COUPLINGS.md` — the gate is RED at the phase base | 20-01 T4 | 1 | `make gate-tools`, and every `ci-core`/`ci` assertion from `20-03` on |
| Regenerated `docs/surface/examples/RETIREMENT-COUPLINGS.md` after the move | 20-07 T3 | 7 | `make gate-tools`, `CLNT-16` |
| README-structure test | 20-08 T2 | 8 | criterion 9 |
| Product-payload assertion for every leg | 20-03 T3 | 3 | criteria 1-3 |
| Marker check `run.py::marker_violations` — the properties the payload assertion greps for | 20-03 T3 | 3 | criteria 1-3, via `payload_violations` |
| Criterion-7 empty-diff assertion + its fixed base | 20-01 T1, 20-08 T3 | 1, 8 | criterion 7 |

**Five ordering constraints are load-bearing and are encoded in `depends_on`:**

1. `20-07` (which deletes `tests/examples/test_s2_client_transport_spike.py`) depends
   on `20-04` (which extracts that module's offline `claude` recipe into
   `examples/hw1-harness-clients/runner/model_stub.py::offline_cli_environment`).
   `20-07` also carries a mechanical precondition check that stops the plan if the
   extraction is absent.
2. `20-06` (the budget gate) depends on the three client files existing, because the
   budget must be **measured** from the shipped files rather than guessed.
3. `20-05` depends on `20-04`, not on `20-03`: it asserts three `client_*.py` in the
   example root and reads the runner's `--live` AST, and `20-04` creates the third file
   and rewrites that handling. As same-wave siblings, `20-05` would see two files and go
   red for a reason unrelated to what it tests.
4. Every plan writes `docs/surface/examples/RETIREMENT-COUPLINGS.md` and every plan from
   `20-03` on asserts a tree-global gate, so the waves are serial. Parallelism here would
   buy two waves of wall-clock and cost a shared generated file plus concurrent sabotage
   mutations in one tree.
5. **The `cinv01a` tightening is in wave 2, one wave before the first client program.**
   Dave's ruling 6(b) gates files that `20-03` and `20-04` write. A gate installed after
   its subjects is a retrofit, and a retrofit is how this hole arrived: the rule was
   measurably unable to catch a short agent prompt, and nothing was watching. `20-02` is
   the last plan that writes no harness client, so it is the last place the gate can be
   installed before the thing it governs exists. Note this is **wave 2, not wave 3** —
   legs 1 and 3 send prompt text as surely as leg 2 does, so "before leg 2" would have
   been one wave too late.

No framework install is needed. **No package is installed by this phase** — all four
harness/MCP packages are already pinned dev dependencies.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| x86_64 wheel bundles the `claude` CLI | criterion 2, 10 | No network/CI token in-session; platform-tagged wheel resolution cannot be observed from this ARM host | One CI run, or `pip download claude-agent-sdk==0.2.128 --platform manylinux_2_17_x86_64 --no-deps` and inspect the wheel for `_bundled/claude` |

---

## Validation Sign-Off

- [x] All tasks have an automated verify or a Wave 0 dependency — 24/24 carry `<automated>`
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — every gap has a named owner and precedes its consumers
- [x] No watch-mode flags
- [x] Every new gate carries a named sabotage control (`CLNT-12` / `D-22`) — see the register below
- [x] `nyquist_compliant: true` set in frontmatter

### Sabotage-control register — every new gate, and the plan that carries its controls

| Gate | Added by | Controls | Count |
|---|---|---|---|
| `make`-target wiring in `examples:` | 20-02 T3 | missing target · empty prerequisites · no `examples:` line | 3 |
| **`cinv01a` destination arm — a prompt refused by where it goes** (Dave, ruling 6(b)) | 20-02 T4 | **CONTROL 4** the blocker's own shape (`prompt_score` 1) refused at `client.query(...)` · **CONTROL 5** a role-preamble-free prompt (`prompt_score` 0) refused at `system=` · **CONTROL 6** resolution through a name bound to an `os.environ.get` fallback · **CONTROL 7** the `{"role", "content"}` mapping refused, and clean without `"role"` · **CONTROL 8** a legitimate developer diagnostic, a sub-floor fixture and a SQL `query(...)` all stay green | 5 |
| Per-leg address comparison | 20-02 T2, 20-03 T3 | empty observation · divergent address · unknown leg name | 3 |
| **Product payload printed, not just the address** (criteria 1-3) | 20-03 T3 | address-only stdout · marker-set divergence from the reference run · empty marker list | 3 |
| **Marker validity — the properties `payload_violations` greps for** (Dave, revision 3) | 20-03 T3 | **CONTROL D** a name that is a substring of another declared name · **CONTROL E** a name composed only of hex digits · **CONTROL F** a name whose words collide with the console vocabulary `consume.py::main` prints | 3 |
| Model stand-in fail-loud behaviour | 20-04 T1 | drift · exhaustion · orphan declaration | 3 |
| Leg-2 determinism (stand-in failure is the run's failure) | 20-04 T3 | removed declared exchange | 1 |
| No-model socket guard | 20-05 T1 | `create_connection` refused · `socket.connect` refused · restore after exit | 3 |
| `--live` singularity / non-forking | 20-05 T2 | second live flag · second driving call site · no `--live` at all | 3 |
| AST purity, per-root permitted set | 20-06 T1 | **C-20-1..C-20-7** | 7 |
| **Budget gate, newly armed against the harness root** | 20-06 T2 | **C-20-9** — a padded copy of the *harness* root, because the two pre-existing vacuity controls both build from `CLIENT_EXAMPLE_ROOTS[0]` | 1 |
| Command identity for the new root | 20-06 T3 | **C-20-8** · two-token divergence · two-recipe-line target | 3 |
| Retirement tree assertions | 20-07 T2 | condemned dir present · record-less destination · missing root · two LangGraph clients · `00-hello-context` missing a client | 5 |
| README structure | 20-08 T2 | missing element · empty `required` · empty text | 3 |
| Live targets outside `examples:` | 20-08 T2 | missing target · live target inside `examples:` | 2 |
| Criterion-7 empty diff | 20-08 T3 | a base/path pair that DOES differ · an unresolvable base | 2 |

**50 named controls.** Each plan's acceptance criteria require the executor to record,
per control, the exact mutation that made it fail and the observed output — and to
state explicitly *"controls that could not be made to fail: none"*, or to name them.

The count moved from 45 to 50 on Dave's ruling 6(b) at the plan gate, which
tightens `cinv01a-prompt-shape` in-phase. **CONTROL 8 is the one that is not
about catching prompts**, and it is deliberate: a tightened heuristic that flags
every long string is a gate nobody can keep green, so one control proves the arm
still passes legitimate developer diagnostics, a sub-`MIN_PROMPT_CHARS` test
fixture, and a SQL `query(...)` — the sink name that collides with a database
idiom. The blast radius behind the design (94 findings rejected, 2 adopted and
remediated) is recorded in `20-02-PLAN.md`'s `<lint_blast_radius>`.

The count moved from 42 to 45 on Dave's revision-3 ruling that the company-name marker
properties must be *asserted, not only stated in prose*: `payload_violations` is
what makes criteria 1-3 real rather than address-only, and it is only as strong as
the markers it greps for, so a degenerate marker set would leave that gate green
while the property it protects is false. One control per property, because one
control standing for all three would leave two of them unmeasured.

**Two deliberate absences, recorded so neither reads as a gap.**

- **No control for "two ADK clients under `examples/`."** `H-14` keeps
  `examples/external/00-hello-context/`, which holds its own `client_adk.py` and
  `client_anthropic.py`, so two of each is the **mandated** state after `20-07`. `H-13`'s
  claim is the LangGraph 2→1 reduction and nothing wider; the ADK and Anthropic
  duplication is discharged by a historical marking, not a count. `20-07` T2 instead
  asserts positively that `00-hello-context` still holds all three of its clients, with
  CONTROL 5 watching that assertion fail.
- **No new control for the retirement-inventory currency gate.** It is a *pre-existing*
  gate this phase makes green and then keeps green, not a gate this phase adds. What it
  gets instead is a tamper mitigation: `20-01` T4 asserts `tools/retirement_sweep.py`
  itself is unedited, so the report cannot be made "current" by moving the goalposts,
  and `20-08`'s `<open_residual>` names exempting the test from `make ci` as a
  `D-IMPL-NN` for Dave rather than an option.

**Approval:** pending
