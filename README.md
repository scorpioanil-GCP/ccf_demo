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

## Quickstart

The smallest possible fabric — register an ontology, ingest events through
L1, assemble, and serve one typed Context Product:

```sh
make example-00
```

Then read [`examples/00-quickstart/README.md`](examples/00-quickstart/README.md)
for what each assertion demonstrates and what to change first to adapt it.

## The examples suite

The eight examples are the adoption contract (CLAUDE.md §9): runnable
end-to-end against the reference backends (SQLite graph store, file-backed
ArtifactStore), each a thin generic driver beside the definition artifacts
that carry everything specific (the No-Hardcoding Rule, CLAUDE.md §6.4).
`make examples` runs all eight in order — the same command CI runs.

| Example | Demonstrates | Command |
| --- | --- | --- |
| [`00-quickstart`](examples/00-quickstart/) | The smallest fabric: L1 ingest → graph → operator chain → projection → three L6 gates → one typed Context Product, replay-recorded | `make example-00` |
| [`01-agent-basics`](examples/01-agent-basics/) | Archetype/agent separation: an agent declared from `AnalyticsInsightsAgent` via a definition artifact, constructed only through the Agent Factory, all six specialization axes | `make example-01` |
| [`02-skilling`](examples/02-skilling/) | Channel-2 specialization: governed skill grant / exercise / revoke through the Control Plane, tier-1 refusal fires, grant-set in force lands in replay | `make example-02` |
| [`03-harness-portability`](examples/03-harness-portability/) | One agent definition executed unmodified under all three harnesses (Claude Agent SDK, Google ADK, LangGraph) with equivalence asserted — the harness-neutrality proof | `make example-03` (live legs: `make example-03-live-ollama`, `make example-03-live-anthropic`) |
| [`04-cross-process`](examples/04-cross-process/) | Assembler agent in one OS process, consumer in another: one Context Product over MCP egress and A2A, Control Plane admission verification incl. a tamper refusal | `make example-04` |
| [`05-workflow-hitl`](examples/05-workflow-hitl/) | Multi-step workflow with ApprovalGate + ExceptionEscalation: suspend on the gate, approve through the auth-bound HITL door, human action in the replay record | `make example-05` |
| [`06-decision-replay`](examples/06-decision-replay/) | Replay a prior decision: exact-version resolution of snapshot, policy bundle, agent version, skill-set, and prompt artifacts from the ArtifactStore; byte-equal reproduction | `make example-06` |
| [`07-artifact-store-mcp`](examples/07-artifact-store-mcp/) | Swap the file-backed ArtifactStore for the MCP-backed reference store; nothing else changes — the §7.4 pluggability proof | `make example-07` |

## Verification

```sh
make ci        # lints + mypy --strict + full test suite + all eight examples
```

`make ci` runs the same command strings as the always-on GitHub Actions
pipeline's invariant legs (`.github/workflows/ci.yml`); Actions additionally
runs the lint unit tests and a Postgres service-container leg. The opt-in
live-model legs live in `.github/workflows/live-legs.yml`.

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
