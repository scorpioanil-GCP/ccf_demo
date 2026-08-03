---
phase: 14-documentation-suite
plan: 07
subsystem: docs
tags: [docs, snippets, examples, tutorial]
requires: ["14-01"]
provides: ["DOCS-01 adopter's guide", "snippet section markers in the six arc sources", "D-08 negative control"]
affects: ["public/tutorial/adopters-guide.md", "examples/*/run.py", "tools/docs_tests/"]
tech-stack:
  added: []
  patterns: ["marker-anchored snippet include", "whole-file artifact include", "subprocess-built throwaway mkdocs project as a negative control"]
key-files:
  created:
    - tools/docs_tests/test_snippet_gate.py
  modified:
    - public/tutorial/adopters-guide.md
    - examples/00-quickstart/run.py
    - examples/01-agent-basics/run.py
    - examples/02-skilling/run.py
    - examples/05-workflow-hitl/run.py
    - examples/06-decision-replay/run.py
    - examples/external/00-hello-context/client_bare.py
decisions:
  - "Marker names come from each file's own stage vocabulary; 00-quickstart uses the eight stages its module docstring already names."
  - "05-workflow-hitl's HITL leg is split into three adjacent regions (approval / refusals / admitted) rather than one long span, so the fail-closed refusal path gets its own narrated block."
metrics:
  duration: ~35m
  completed: 2026-08-03
---

# Phase 14 Plan 07: Adopter's guide and the snippet drift gate — Summary

An install-to-production tutorial in which every code block and every artifact
shown is literal-included from an example CI already runs, plus the negative
control that proves a renamed marker breaks the build in the same commit.

## What was built

**Task 1 — named section markers (commit `6e45ea2`).** 31 paired
`# --8<-- [start:NAME]` / `[end:NAME]` regions across the six sources the guide
narrates. Comment lines only: the filtered diff over `examples/` contains
nothing but marker lines, and `make lint`, the full examples suite (all nine
plus the external leg) and `pytest` (1533 passed, 2 skipped) stayed green.

Marker vocabulary, recorded here so the guide and any future page share one set:

| Source | Regions |
| --- | --- |
| `examples/00-quickstart/run.py` | `ontology`, `ingest`, `assemble`, `operators`, `project`, `gate`, `record`, `serve` |
| `examples/01-agent-basics/run.py` | `agent-artifacts`, `agent-factory`, `specialization-axes`, `agent-replay` |
| `examples/02-skilling/run.py` | `skill-catalog`, `skill-grant`, `skill-exercise`, `skill-refusal`, `skill-revoke` |
| `examples/05-workflow-hitl/run.py` | `workflow-construct`, `workflow-suspend`, `hitl-approval`, `hitl-refusals`, `hitl-admitted`, `workflow-resume`, `hitl-replay` |
| `examples/06-decision-replay/run.py` | `replay-reproduce`, `replay-agent-version`, `replay-version-sensitivity` |
| `examples/external/00-hello-context/client_bare.py` | `mcp-connect`, `mcp-discover`, `mcp-resource` |

Every one of the 31 is consumed by the guide — verified by set difference, not
by eye.

**Task 2 — the adopter's guide (commit `ab567c7`).** Seven `##` sections in the
DOCS-01 arc order: install, ontology and the first Context Product, agent
declaration, skilling, workflow with a HITL gate, replay, and the
external-consumer view; plus a closing "where to go next". 34 include
directives — 30 marker-anchored code regions and 4 whole-file artifact
includes (`00-quickstart/artifacts/ontology.yaml`,
`01-agent-basics/artifacts/agent.yaml`, `02-skilling/artifacts/skills.yaml`,
`05-workflow-hitl/artifacts/workflow.yaml`). Zero pasted code: no `def ` or
`class ` appears anywhere in the page. 14 links into `reference/` pages, all
resolving under the strict build's link and anchor validation. Each section
names the one `make` command that runs its example.

**Task 3 — the negative control (commit `b57c2e3`).** `tools/docs_tests/test_snippet_gate.py`
builds throwaway mkdocs projects in `tmp_path` and asserts: a deleted
`[start:...]` marker fails with a `Snippet` message; a missing include file
fails separately (the extension guards the two at different call sites, so a
config regression could restore one without the other); the unmodified source
builds at exit 0. The subprocess is bounded by an explicit timeout and the
working tree is never mutated — sources are copied before being stripped.

## Verification

| Check | Result |
| --- | --- |
| `tools.lints --all` | exit 0 |
| `make examples` (all nine + external leg) | exit 0 |
| `pytest -q` with `CCF_REQUIRE_HARNESSES=1` | 1533 passed, 2 skipped |
| `mkdocs build` (strict) | exit 0 |
| `tools/publish_scan.py site` and `--pre-build` | exit 0 |
| `pytest tools/docs_tests -q` | 3 passed |
| Renaming `[start:ontology]` in `00-quickstart` | build fails: `Snippet section 'ontology' could not be located` — reverted |
| Marker consumption (31 declared vs consumed) | empty difference |
| `git status --porcelain public/ examples/ mkdocs.yml` after the suite | matches baseline |

## Deviations from Plan

None — plan executed as written. Two mechanical notes:

- The plan's `<read_first>` named `public/tutorial/demo-walkthrough.md` as a
  sibling Tutorial page to match in voice. That file does not exist in this
  tree (the nav lists exactly one Tutorial page). The prose-then-include rhythm
  the plan describes was followed regardless: no fence ever stands alone.
- The worktree has no `.venv`; `make` targets were run with `PYTHON` and `ENV`
  overridden onto the primary interpreter, per the execution brief.

## Known Stubs

None. The guide links to Reference pages that are stubs at this moment
(`14-06` and siblings fill them in the same wave); the links resolve, which is
what the strict build checks, and the pages are owned by other plans.

## Threat Flags

None. Every include in the guide targets `examples/`; the include-escape guard
(`pub04`) and the post-build publish scan both pass.

## Self-Check: PASSED

- `public/tutorial/adopters-guide.md` — FOUND
- `tools/docs_tests/test_snippet_gate.py` — FOUND
- commits `6e45ea2`, `ab567c7`, `b57c2e3` — FOUND in `git log`
