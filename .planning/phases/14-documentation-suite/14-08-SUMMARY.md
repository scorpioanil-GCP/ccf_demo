---
phase: 14-documentation-suite
plan: 08
subsystem: docs
tags: [docs, how-to, snippets, examples, security]
requires: ["14-01", "14-04"]
provides:
  - "DOCS-04 the five task-shaped How-to pages"
  - "DOCS-05 the operator security and deployment guide, finished"
  - "16 snippet section markers in examples 03, 04 and 07"
affects:
  - "public/how-to/*.md"
  - "examples/03-harness-portability/run.py"
  - "examples/04-cross-process/run.py"
  - "examples/07-artifact-store-mcp/run.py"
tech-stack:
  added: []
  patterns:
    - "marker-anchored snippet include (vocabulary shared with plan 14-07)"
    - "whole-file artifact include"
    - "task-shaped How-to: task sentence, prerequisites, steps, run command, what-to-change-first"
key-files:
  created: []
  modified:
    - public/how-to/grant-and-revoke-a-skill.md
    - public/how-to/run-agents-cross-process.md
    - public/how-to/compose-a-workflow-with-hitl.md
    - public/how-to/swap-the-artifact-store.md
    - public/how-to/bind-a-harness-adapter.md
    - public/how-to/security-and-deployment.md
    - examples/03-harness-portability/run.py
    - examples/04-cross-process/run.py
    - examples/07-artifact-store-mcp/run.py
decisions:
  - "Marker names for example 04 use the `peer-` prefix, not `a2a-`: the plan's own acceptance criterion enumerates marker names with `grep -o 'start:[a-z-]*'`, and a digit inside `a2a` truncates the captured name to `a`, silently collapsing eight distinct regions to one and making the consumption assertion vacuous. `peer-` matches the module vocabulary (`ccf.peering`) and keeps every name inside the character set the assertion can actually read."
  - "The security page gained a fourth top-level section rather than a rewrite of the first three; Phase 9/10 substance is untouched, per the plan's explicit instruction."
metrics:
  duration: ~50m
  completed: 2026-08-03
---

# Phase 14 Plan 08: Task how-to pages and the operator security guide — Summary

Six How-to pages: five that narrate an example CI already runs green, every
code block literal-included, plus the moved security and deployment notes
finished as an operator task page with navigation into the generated
reference.

## What was built

**Task 1 — snippet markers for the three remaining sources (commit `f965360`).**
16 paired `# --8<-- [start:NAME]` / `[end:NAME]` regions across the three
example sources plan 14-07 did not touch. Comment lines only: the filtered
diff over `examples/` is empty of anything but marker lines.

| Source | Regions |
| --- | --- |
| `examples/04-cross-process/run.py` | `peer-trust-policy`, `peer-gate`, `peer-spawn`, `mcp-egress`, `peer-admit`, `peer-admission-record`, `peer-ingest`, `peer-refusal` |
| `examples/07-artifact-store-mcp/run.py` | `store-factory`, `store-persist`, `store-swap`, `store-equivalence` |
| `examples/03-harness-portability/run.py` | `harness-agent`, `harness-replay-hook`, `harness-legs`, `harness-governed-fields` |

Names follow the plan 14-07 vocabulary (lowercase, hyphenated, drawn from
each file's own stage names), bringing the repository total to 47 regions.
All 16 are consumed by a page in Task 2 — verified by set difference, not by
eye. Plan 14-07's six sources were not edited; `examples/02-skilling` and
`examples/05-workflow-hitl` markers are reused by reference only.

**Task 2 — the five task pages (commit `58ffa49`).** Each is shaped as a
task: a one-sentence statement of what you are doing, prerequisites, numbered
steps with literal-included code and artifacts, the `make` target that runs
the worked example, and a "what to change first" closing adapted from the
example's README.

| Page | Narrates | Includes | `reference/` links |
| --- | --- | --- | --- |
| `grant-and-revoke-a-skill.md` | `examples/02-skilling` | 6 | 4 |
| `run-agents-cross-process.md` | `examples/04-cross-process` | 9 | 5 |
| `compose-a-workflow-with-hitl.md` | `examples/05-workflow-hitl` | 9 | 3 |
| `swap-the-artifact-store.md` | `examples/07-artifact-store-mcp` | 6 | 3 |
| `bind-a-harness-adapter.md` | `examples/03-harness-portability` | 6 | 3 |

36 include directives in total — 29 marker-anchored code regions and 7
whole-file artifact includes. Zero pasted code: `def ` and `class ` appear
nowhere in any How-to source. Each page names exactly one `make example-NN`
target.

**Task 3 — the security and deployment page finished (commit `9595ec8`).**
Pre-edit section count captured with the command the plan names:
`SECDOC_BEFORE="$(grep -c '^## ' public/how-to/security-and-deployment.md)"`
→ **3**. After the edit: **4**. Sections 1–3 (key sourcing, rotation posture,
CI-secrets discipline) are untouched; the substance authored in Phases 9 and
10 is preserved verbatim. Three additions, as specified:

1. An opening task framing — what an operator is doing on this page and, more
   usefully, what the page does *not* cover.
2. Links down into the generated reference for every surface named: peering
   Protocols, HITL Protocols, runtime surfaces, the HTTP API contract, Control
   Plane artifacts, and replay anatomy. 7 `reference/` links, up from 0.
3. A `## 4. Deployment posture` section covering the three decisions an
   operator must make before exposing the HTTP surface — the insecure-default
   acknowledgement and the bound-but-inert-authorizer shape, the deny-by-
   default / re-resolved-per-call / both-outcomes-audited authorization
   posture, and where key custody lives. Written from shipped mechanism only
   (`runtime/ccf_runtime/http_api/app.py`,
   `runtime/ccf_runtime/authz/protocol.py`, `src/ccf/peering/identity.py`);
   it commits to nothing the SDK does not already do, which is the page's own
   stated contract.

No key material, no example secret, and no path to one was added. No code
block was pasted — every block is either an include or a shell command.

## Verification

| Check | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make examples` (all nine + external leg) | exit 0, all OK |
| `make test` | 1539 passed, 2 skipped |
| `make docs` (strict) | exit 0 |
| `tools/publish_scan.py site` | exit 0 |
| `tools/publish_scan.py --pre-build` | exit 0 |
| Marker balance in the three sources | 8/8, 4/4, 4/4 |
| Only marker lines added to `examples/` | filtered diff empty |
| No non-marker line added to 14-07's two files | filtered diff empty |
| Marker consumption (16 declared vs consumed) | empty difference |
| Includes per page ≥ 2 | 6, 9, 9, 6, 6 |
| `grep -qE 'def \|class ' public/how-to/*.md` | no match |
| `reference/` links on the security page ≥ 5 | 7 |
| Security page `## ` count ≥ `SECDOC_BEFORE` | 4 ≥ 3 |
| Key-shaped literal on the security page | no match |
| Negative control: dead `reference/` link | build **failed** with 2 strict warnings — reverted |

The negative control is worth recording: a green strict build is the plan's
stated link-and-anchor assertion, so the build was deliberately made to fail
once by pointing a security-page link at a nonexistent reference page. It
aborted with `Aborted with 2 warnings in strict mode!`, confirming the
assertion has teeth rather than passing vacuously. Reverted and rebuilt green.

## Deviations from Plan

**1. [Rule 1 — Bug] Marker prefix `a2a-` renamed to `peer-`**

- **Found during:** Task 2, while running the plan's marker-consumption
  acceptance criterion.
- **Issue:** the criterion enumerates marker names with
  `grep -rho 'start:[a-z-]*' ... | cut -d: -f2 | sort -u`. The character
  set `[a-z-]` excludes digits, so `start:a2a-trust-policy` captures as `a`.
  All eight example-04 regions collapsed to a single name, and the check
  reported "16 declared" as "10 declared" while passing. A criterion that
  cannot see six of the regions it exists to police is not an assertion.
- **Fix:** renamed the eight regions to the `peer-` prefix
  (`peer-trust-policy`, `peer-gate`, `peer-spawn`, `peer-admit`,
  `peer-admission-record`, `peer-ingest`, `peer-refusal`; `mcp-egress` was
  already digit-free) and updated the consuming page. The prefix matches the
  module the code lives in (`ccf.peering`). The check now reports 16 declared,
  0 unused.
- **Files modified:** `examples/04-cross-process/run.py`,
  `public/how-to/run-agents-cross-process.md`
- **Commit:** `58ffa49`

**2. [Rule 3 — Blocking] Two prose phrasings rewritten to survive the
no-pasted-code assertion**

- **Found during:** Task 2 acceptance.
- **Issue:** `! grep -qE 'def |class ' public/how-to/*.md` matches the
  substring `class ` anywhere, including the ordinary English phrase
  "first-class exception paths". Two pages tripped it on prose, not on code.
- **Fix:** rephrased both ("A2A federation is a v0 commitment rather than a
  deferral"; "exception paths that are ordinary transitions rather than error
  handling"). Both readings are more precise than the originals, so nothing
  was lost. Noted here because it is a live constraint for any future page:
  the assertion cannot distinguish prose from code, so prose must avoid the
  literal `class ` and `def `.
- **Files modified:** `public/how-to/run-agents-cross-process.md`,
  `public/how-to/compose-a-workflow-with-hitl.md`
- **Commit:** `58ffa49`

**3. [Mechanical] `make` in the worktree**

The worktree has no `.venv`; per the execution brief, the primary
interpreter was symlinked in (`ln -s /home/parkave/ccf_code/.venv .venv`,
gitignored, nothing tracked changed), which makes every `make` target and the
plan's literal `.venv/bin/python` commands work as written.

## Known Stubs

None. The five pages link to Reference and Concepts pages that are stubs at
this moment — plans 14-05 and 14-06 fill them in the same wave — but every
link resolves, which is what the strict build validates, and those pages are
owned by other plans. No link was created to a path the nav does not already
declare, and no sibling plan's file was created or edited.

## Threat Flags

None. Every include on every page targets `examples/`; the pre-build
include-escape guard (`pub04`) and the post-build publish scan both pass. The
security page carries no key material and no key-shaped literal, and its
substance was extended rather than rewritten, so the T-14-39 concern (claiming
a posture the SDK does not ship) is addressed by construction — every claim in
the new section was read out of `http_api/app.py`, `authz/protocol.py`, or
`peering/identity.py` first.

One deliberate judgement worth flagging for review: `swap-the-artifact-store.md`
whole-file-includes `examples/07-artifact-store-mcp/artifacts/store_mcp.yaml`,
which contains a per-run example credential that, per the artifact's own
header comment, authorizes nothing but a temporary directory and points at
`.invalid` identities that cannot resolve. It is already in the repository and
already runs in CI; the swap surface is the page's whole subject, so showing
only half of the pair would have been the worse trade. The publish scan passes.

## Self-Check: PASSED

- `public/how-to/grant-and-revoke-a-skill.md` — FOUND
- `public/how-to/run-agents-cross-process.md` — FOUND
- `public/how-to/compose-a-workflow-with-hitl.md` — FOUND
- `public/how-to/swap-the-artifact-store.md` — FOUND
- `public/how-to/bind-a-harness-adapter.md` — FOUND
- `public/how-to/security-and-deployment.md` — FOUND
- commits `f965360`, `58ffa49`, `9595ec8` — FOUND in `git log`
- working tree clean after the full verification sweep
