---
phase: 18
plan: D-IMPL-150
subsystem: client-access / examples / contracts
tags: [portability, mcp-stdio, examples, worktree-hazard, D-IMPL-150]
requires:
  - "ccf.client.adapters.mcp_stdio (shipped by 17-10)"
  - "ccf.deployment.load_config_and_boot, ccf.products.resolver.build_governed_resolver (public composition path)"
provides:
  - "examples/hw1-companies-over-revenue/server/serve.py — the example's own MCP server program, public seams only"
  - "tests/examples/test_hw1_two_transports.py — the portability claim as an always-on CI check"
  - "tests/contracts/test_canonical.py::child_environment — one place a spawned child's environment is decided"
affects:
  - "Makefile (example-hw1-mcp target)"
  - "tests/examples/test_client_example_purity.py (command identity is now a set)"
  - "docs/surface/examples/RETIREMENT-COUPLINGS.md (regenerated)"
tech-stack:
  added: []
  patterns:
    - "an example's server program lives in a sibling directory, not the example root and not the deployment root"
    - "documented commands are read from the README and RUN, never restated in the test"
key-files:
  created:
    - examples/hw1-companies-over-revenue/server/serve.py
    - examples/hw1-companies-over-revenue/server/egress-door.yaml
    - tests/examples/test_hw1_two_transports.py
  modified:
    - examples/hw1-companies-over-revenue/consume.py
    - examples/hw1-companies-over-revenue/README.md
    - Makefile
    - tests/examples/test_client_example_purity.py
    - tests/contracts/test_canonical.py
    - tests/client/fixtures/stdio_server.py
decisions:
  - "The example's server program composes through public seams only; `_boot` is never reached."
  - "The fixture's private `_boot` reach is KEPT, on the record, with the reason written into the fixture."
  - "The two-transport proof runs on an EMPTY deployment, because that is the claim a clean checkout can make."
metrics:
  duration: ~2h
  completed: 2026-08-17
---

# Phase 18 `D-IMPL-150`: the example over both transports, and the child's environment

`hw1` now genuinely runs over both transports and the claim is a CI check, not
prose; `tests/contracts/test_canonical.py` no longer validates canonical hashing
of a different checkout's code.

## What was wrong

**A.** Plan `17-10` line 87 recorded as its Output that
`CCF_BINDING="mcp+stdio:…"` *"runs the same `consume.py`"*. It did not.
`consume.py` imported only `ccf.client.adapters.inprocess`, and `D-05` gives the
SDK no discovery chain — a scheme reaches the registry by its adapter module
being imported — so the documented invocation raised:

```
BindingError: `mcp+stdio` names no transport this client can build — registered
schemes are `inprocess`.
```

There was also no server program for the example to launch, and
`mcp+stdio:<program> <root>` names one.

**B.** `tests/contracts/test_canonical.py` spawned its cross-process child with
`env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}` — no `PYTHONPATH`. This
is the identical blind spot `17-10` Task 3 fixed in the adapter. Measured in this
worktree, at this base:

| | resolved `ccf` |
| --- | --- |
| the test process (worktree) | `…/worktrees/agent-a86696ce73f9270bd/src/ccf/__init__.py` |
| its child, stripped env | `/home/parkave/ccf_code/src/ccf/__init__.py` |

So under worktree execution — how every executor in this project runs — the test
asserted cross-process hash stability **of the main checkout's serializer** and
reported green.

## What shipped

### A. The example, over both transports

1. **`consume.py` imports both adapter modules** and chooses neither. The
   existing `D-05` comment was extended rather than replaced. One line added;
   the file is 79 lines against its declared 80-line budget, so the README's
   number did not move.

2. **`examples/hw1-companies-over-revenue/server/serve.py`** — the deployment's
   own MCP server program, built on the **public** composition path:
   `load_binding_document` → `load_config_and_boot` → `conforming_plan_factory`
   / `load_reference` → `build_governed_resolver` → `build_egress_server`.
   `ccf.client.adapters.inprocess._boot` is never reached. Every name imported is
   exported from its package, so what this file does an adopter can do — which
   is the entire point of Ruling 1.

   **Why a sibling directory** rather than beside `consume.py`, which is what the
   fixture's filing would suggest: two shipped gates leave exactly one place.
   `D-IMPL-141` Amendment A.3 grants `deployment/` one Python module (the
   projection) and `tests/client/test_data_only_deployment.py` refuses a second;
   `tests/examples/test_client_example_purity.py` treats every `.py` sitting
   directly in the example root as reader-visible **consumer** code, permitted
   `ccf.client` and stdlib only, and holds it to the same 80-line budget. A
   server program is neither. Both constraints were verified against the shipped
   gates, not assumed.

3. **`server/egress-door.yaml`** carries the four governance values the door
   needs — tool description, required scope, issuer URL, resource-server URL.
   `serve.py` is their interpreter and spells none of them (§6.4). The token
   value is minted per boot with `secrets.token_urlsafe` into a temporary
   directory deleted on exit; nothing is written into the repository.

4. **`make example-hw1-mcp`** and a README section documenting both invocations,
   character-identical to their recipes.

### B. The child's environment

`child_environment(seed)` is now the one place a child spawned from
`test_canonical.py` gets an environment. It propagates `PYTHONPATH` **when the
parent has one** and pins `PYTHONHASHSEED` exactly as before — the minimality is
preserved, not traded away, because a child inheriting the parent's whole
environment would inherit a seed the parent happened to carry, and the seed is
the variable the stability test varies.

## Measured, not asserted

**Both transports return byte-identical output.** Run from the repository root
against the shipped (unpopulated) deployment:

```
   0 of 0 assembled
   context debt D_c   1.0000  →  fail_closed
   content address    948ed10770b7306ffa588e8b90fc502cdc8a0f73fb45adbeac4a4c4a6dc8fd25
   replay record      ccf-artifact://hw1-demo/hw1.replay-record/518eafe5…@81ef7f5c…
```

Identical under `inprocess:` and under `mcp+stdio:`, including the replay
reference. `0 of 0` with `D_c` at `1.0000` is the honest mechanism on an empty
graph (`D-32` — no data is committed to `examples/`), and two transports
returning the same governed refusal to the same question is still the same
answer. No data was manufactured to get a prettier one.

### The gates fail without the fixes

Both were sabotaged and watched:

- **A.** Removing the `mcp_stdio` import from `consume.py` turns
  `test_hw1_two_transports.py` red with the exact `17-10` `BindingError` quoted
  above — `1 failed, 5 passed`. The gate reproduces the defect it was written
  for.
- **B.** `test_a_child_without_pythonpath_cannot_see_what_the_parents_names`
  runs two real children over a sentinel module reachable only through the
  parent's `PYTHONPATH`: the one from `child_environment` imports it, the one
  from the old two-variable environment raises `ModuleNotFoundError`. It is
  deterministic in **any** checkout, which asserting on `ccf`'s location alone
  would not be (in a non-worktree tree both resolutions land on one file).
  `test_the_child_resolves_the_same_ccf_this_test_is_running` states the real
  property alongside it.

## Deviations from plan

### Auto-fixed / in-scope adjustments

**1. [Rule 3 — blocking] The command-identity gate permitted exactly one documented command.**
`tests/examples/test_client_example_purity.py` asserted the README states
*exactly one* line beginning `CCF_BINDING=`, paired with one `make` recipe. A
second documented transport is structurally impossible under that gate. It was
generalized to a set: every documented command has a target, every target is
documented, order is asserted, and `shlex.split` is used because an `mcp+stdio`
address is two whitespace-separated tokens inside one quoted value. Two
assertions were **added** (`test_every_documented_command_names_a_distinct_binding_scheme`,
and the per-target parametrization); none was removed or weakened. This is the
gate that was structurally unable to notice `17-10`'s un-runnable command, and
it now would be.

**2. [Rule 3 — blocking] `docs/surface/examples/RETIREMENT-COUPLINGS.md` was stale.**
`make gate-tools` failed on it. Two causes: the new `server/` files carry
documentary references to another example, and the report was already stale
against the orchestrator's own `D-IMPL-150` entry in `docs/DECISIONS.md` (row
count 50 → 51) at the base commit. Regenerated with
`python tools/retirement_sweep.py --report`, which is what the failing
assertion's own message instructs. The diff is the two new documentary rows, the
`Makefile` line-number shifts from the new target, and that decision-log count.

### Not done, on purpose

**`tests/client/fixtures/stdio_server.py` keeps its private `_boot` reach.**
This was the recorded advisory folded into the work, and the decision is
written into the fixture's own docstring rather than left implicit. Two reasons:

1. The fixture's job is to make the conformance suite's parity legs a claim
   about *two transports*. Sharing one composition is what buys that; if the
   fixture built its own resolver a passing leg would only show that two
   compositions happened to agree — and its docstring already records the
   concrete way that goes wrong (a resolver returning the narrower
   `ServableProduct` emits `replay_ref=None` over MCP and disagrees on a field
   `assert_served_parity` compares).
2. The adoptability question the finding was really about is now answered where
   it matters. `server/serve.py` stands the same door up through public seams
   only, and it is exercised on every push. The public path is demonstrated and
   measured; the fixture buys something else.

Only the fixture's **docstring** was touched — no behavioural change — so the
concurrent `D-IMPL-149` work on `tests/client/conformance/` is unaffected.

## Concurrency

The three files named off-limits in the objective —
`tests/client/conformance/suite.py`,
`tests/client/conformance/test_inprocess_conformance.py` and
`tests/client/conformance/test_mcp_conformance.py` — were **not touched**. No
work here appeared to require it.

## Verification

Run detached, logs outside the repository, `REAL_EXIT` branched on.

| Gate | Result | Baseline |
| --- | --- | --- |
| `make ci-core` | **exit 0** — 3843 passed, 118 skipped, 0 failed | 3832 / 118 |
| `make conformance` | **exit 0** — 56 passed | 56 |
| `make docs-strict` | **exit 0** | exit 0 |
| `make gate-tools` | **exit 0** — 154 passed | (part of `ci-core`) |

**Delta: +11 tests, 0 removed.** Six in `test_hw1_two_transports.py`, three in
`test_canonical.py`, two in `test_client_example_purity.py` (one new assertion,
one from parametrizing the identity check over both targets). The concurrent
`D-IMPL-149` agent will move these numbers again after its merge.

`make ci-core` was first run before the retirement report was regenerated; that
run is the one whose pytest leg reported 3843/118 and whose only failure was the
stale report, fixed as deviation 2 and re-verified by `make gate-tools` at exit 0.

## Known stubs

None.

## Self-Check: PASSED

All created files exist on disk; all three commits are in the branch's history;
`git diff --diff-filter=D` against the base commit reports **no deletions**; and
`git diff --name-only` against the base names none of `STATE.md`,
`ROADMAP.md`, `docs/DECISIONS.md` or the three `tests/client/conformance/` files
reserved for the concurrent `D-IMPL-149` work.

## Threat flags

None. `server/serve.py` stands up an MCP egress door, which is new surface in
the example tree but not new surface in the SDK: it is
`ccf_runtime.mcp.egress::build_egress_server` with all four governance seams
supplied, the same door `tests/client/fixtures/stdio_server.py` and
`examples/04-cross-process` already stand up, and it listens on **stdio only** —
no socket is opened anywhere. The stdio identity posture (a caller established
once before serving, because stdio carries no bearer channel) is stated in the
module docstring and is the same posture the shipped fixture documents.
