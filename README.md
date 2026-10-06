# CCF SDK — Cognitive Context Fabric

A general-purpose SDK for constructing, governing, and serving
**decision-ready context to AI agents** — and for building, orchestrating,
and operating specialized agents on top of that fabric. The SDK is organized
around five Common Pillars: the **Data and Context Layer** (the L1–L6 fabric:
typed Context Graph, composable operators, projections, and governed Context
Products), the **Orchestration Layer** (a workflow primitive with agent nodes
and HITL gates, plus a Protocol for external orchestrators), **Core Agent
Types** (six functional archetypes from which agents are declared as
versioned Control Plane artifacts — never written as code), **Human in the
Loop and Control** (approval, escalation, override, and review primitives,
every human action replay-recorded by construction), and the **Experience
Layer** (MCP server, `ccf` CLI, and an HTTP API skeleton). CCF layers onto
any agent harness — Google ADK, the Claude Agent SDK, LangGraph, or a bespoke
loop — as the trust-and-control plane; it never absorbs the agent loop and it
does not ship one. The canonical specification is the whitepaper at
[`docs/CCF_Whitepaper_1-2.md`](docs/CCF_Whitepaper_1-2.md).

This repository is **private** and the SDK is proprietary; there is no PyPI
distribution.

## Install

Python 3.12+ required. From the repository root:

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

The `dev` extra installs the test toolchain **and all three harness legs**
(Google ADK, Claude Agent SDK, LangGraph). To install a single harness leg
only: `pip install -e ".[langgraph]"` (likewise `adk`, `claude-agent`).

### Hash-verified install (what CI and `make install` run)

CI never resolves a dependency at run time. Every workflow and the Makefile's
`install` target install the committed, hash-pinned `requirements.lock` (the
`dev`, `neo4j` and `mongo` extras plus the build set, `setuptools` and
`setuptools-scm`), then install the project editable with nothing fetched:

```sh
python -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock
.venv/bin/pip install -e . --no-deps --no-build-isolation
```

`--no-build-isolation` is load-bearing: without it pip fetches the build
dependencies unhashed into a temporary environment. The `dependency-lock` lint
(`tools/lints/dependency_lock.py::check_tree`, `SEC-028`) refuses any other
install form.

### Regenerating the lock

After changing a dependency pin in `pyproject.toml`, regenerate the lock with
pip-tools (in the `dev` extra) and commit it with the change:

```sh
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 .venv/bin/pip-compile --generate-hashes \
  --all-build-deps --unsafe-package ccf --no-strip-extras \
  --extra dev --extra neo4j --extra mongo -o requirements.lock pyproject.toml
```

`--all-build-deps` puts the build set in the lock; `--unsafe-package ccf` keeps
the project's own self-referencing extras out of it (an unhashable
`file://` entry `--require-hashes` would refuse). Do not use `--all-extras`: it
would pull `chromadb` into every CI job. pip-compile leaves a `ccf.egg-info/`
stamped `0.0.0` at the repository root (gitignored); delete it afterwards, or
`importlib.metadata` run from the root reports that version instead of the
installed one.
A pin changed in `pyproject.toml` without regenerating the lock fails the
`dependency-lock-freshness` lint
(`tools/lints/dependency_lock_freshness.py::check_tree`, `SEC-028-F1`).

## Quickstart

The smallest possible fabric — register an ontology, ingest events through
L1, assemble, and serve one typed Context Product:

```sh
PYTHONPATH=src:runtime python archive/examples/00-quickstart/run.py
```

Then read
[`archive/examples/00-quickstart/README.md`](archive/examples/00-quickstart/README.md)
for what each assertion demonstrates and what to change first to adapt it.

## The examples suite

These eight are the adoption contract (CLAUDE.md §9): runnable end-to-end
against the reference backends (SQLite graph store, file-backed
ArtifactStore), each a thin generic driver beside the definition artifacts
that carry everything specific (the No-Hardcoding Rule, CLAUDE.md §6.4).

**They live under `archive/examples/` and no `make` target runs them any
more.** They were archived rather than deleted in Phase 23 (`D-IMPL-189`,
`D-IMPL-193`) and their `make` targets were deleted with them (`D-04`,
`D-IMPL-195` ruling 1), because they are no longer the teaching path — a
target is an invitation to run. Nothing about them stopped working: the
modules under `tests/examples/` still execute them on every commit, so the
commands below run today. `make examples` now composes one member,
`example-hw1-harness-clients`.

| Example | Demonstrates | Command |
| --- | --- | --- |
| [`00-quickstart`](archive/examples/00-quickstart/) | The smallest fabric: L1 ingest → graph → operator chain → projection → three L6 gates → one typed Context Product, replay-recorded | `PYTHONPATH=src:runtime python archive/examples/00-quickstart/run.py` |
| [`01-agent-basics`](archive/examples/01-agent-basics/) | Archetype/agent separation: an agent declared from `AnalyticsInsightsAgent` via a definition artifact, constructed only through the Agent Factory, all six specialization axes | `PYTHONPATH=src:runtime python archive/examples/01-agent-basics/run.py` |
| [`02-skilling`](archive/examples/02-skilling/) | Channel-2 specialization: governed skill grant / exercise / revoke through the Control Plane, tier-1 refusal fires, grant-set in force lands in replay | `PYTHONPATH=src:runtime python archive/examples/02-skilling/run.py` |
| [`03-harness-portability`](archive/examples/03-harness-portability/) | One agent definition executed unmodified under all three harnesses (Claude Agent SDK, Google ADK, LangGraph) with equivalence asserted — the harness-neutrality proof | `PYTHONPATH=src:runtime python archive/examples/03-harness-portability/run.py --mode deterministic` |
| [`04-cross-process`](archive/examples/04-cross-process/) | Assembler agent in one OS process, consumer in another: one Context Product over MCP egress and A2A, Control Plane admission verification incl. a tamper refusal | `PYTHONPATH=src:runtime python archive/examples/04-cross-process/run.py` |
| [`05-workflow-hitl`](archive/examples/05-workflow-hitl/) | Multi-step workflow with ApprovalGate + ExceptionEscalation: suspend on the gate, approve through the auth-bound HITL door, human action in the replay record | `PYTHONPATH=src:runtime python archive/examples/05-workflow-hitl/run.py` |
| [`06-decision-replay`](archive/examples/06-decision-replay/) | Replay a prior decision: exact-version resolution of snapshot, policy bundle, agent version, skill-set, and prompt artifacts from the ArtifactStore; byte-equal reproduction | `PYTHONPATH=src:runtime python archive/examples/06-decision-replay/run.py` |
| [`07-artifact-store-mcp`](archive/examples/07-artifact-store-mcp/) | Swap the file-backed ArtifactStore for the MCP-backed reference store; nothing else changes — the §7.4 pluggability proof | `PYTHONPATH=src:runtime python archive/examples/07-artifact-store-mcp/run.py` |

## Verification

```sh
make ci        # lints + mypy --strict + full test suite + the examples suite
```

`make ci` runs the same command strings as the always-on GitHub Actions
pipeline's invariant legs (`.github/workflows/ci.yml`); Actions additionally
runs the lint unit tests and a Postgres service-container leg. The full test
suite is where the archived examples above are executed. The opt-in
live-model legs are the three `example-hw1-harness-clients-live-*` targets in
the `Makefile`; `.github/workflows/live-legs.yml` now carries only the fluree
upstream-drift detector.

## Documentation

- [`docs/CCF_Whitepaper_1-2.md`](docs/CCF_Whitepaper_1-2.md) — the canonical
  specification: every primitive, contract, and invariant.
- [`CLAUDE.md`](CLAUDE.md) — project orientation: the five pillars, the
  Agent Specialization Framework, harness neutrality, and the SDK
  extensions beyond the whitepaper.
- [`docs/DESIGN.md`](docs/DESIGN.md) / [`public/diagrams/`](public/diagrams/) —
  the SDK's architecture against the spec inventory.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — the decision log: every
  `D-IMPL-NN` ruling and every `D-GATE` phase approval.
- [`docs/SPEC_INVENTORY.md`](docs/SPEC_INVENTORY.md) — the whitepaper
  commitment catalog the implementation is verified against.
