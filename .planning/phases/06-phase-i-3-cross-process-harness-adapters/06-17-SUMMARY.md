---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 17
subsystem: L4/L5 decision-time content acquisition (the second consumer of the shared MCP client)
tags: [mcp, acquisition, l4, l5, xprc-01, d-03, d-21, d-23]
requires:
  - "06-03 (projection engine, operator planner)"
  - "06-04 (ccf.mcp.client, SyncMcpBridge, tests/crossproc fixture)"
provides:
  - "ccf.projection.acquisition — ContentRequest/AcquiredContent, the ContentAcquirer Protocol, and the ContentAcquiringPlan structural extension"
  - "ccf.mcp.acquisition.McpContentAcquirer — the L4/L5 client role over the one shared client"
  - "ProjectionEngine acquisition stage + ExecutionResult.acquisitions (replay dimension 5)"
  - "ProjectionEngine.execute(recorded_acquisitions=...) — the replay re-feed path"
affects:
  - "06-16 (ROADMAP criterion 1: the L4/L5 leg is now demonstrated, not asserted)"
  - "any later plan constructing ProjectionEngine — the acquirer keyword is optional and defaults to None"
tech-stack:
  added: []
  patterns: ["declaration/resolution split (required_content mirrors required_operators)", "separate Protocol rather than a widened one, narrowed from a union"]
key-files:
  created:
    - src/ccf/projection/acquisition.py
    - src/ccf/mcp/acquisition.py
    - tests/projection/__init__.py
    - tests/projection/test_acquisition.py
    - tests/crossproc/test_mcp_acquisition.py
    - tests/crossproc/servers/mcp_content_child.py
    - tests/fixtures/banking/content_acquisition.yaml
  modified:
    - src/ccf/projection/engine.py
decisions:
  - "ContentAcquiringPlan is a standalone runtime_checkable Protocol, not a subclass of ProjectionPlan: an added required keyword makes the two disjoint statically, which is what lets execute() take a union and narrow cleanly instead of forcing mypy to synthesize an impossible intersection."
  - "execute() gained recorded_acquisitions rather than the engine gaining a replay mode: replay constructs the engine with acquirer=None, so the absence of a network handle is structural."
  - "The engine re-verifies each re-fed item's content address; a tampered re-feed is refused rather than trusted."
  - "The acquisition seam imports GraphView (a frozen read value). The plan's grep criterion forbidding the literal 'ccf.graph' in that module was corrected — see Deviations."
metrics:
  duration: ~55 min
  completed: 2026-07-26
---

# Phase 06 Plan 17: L4/L5 Decision-Time Content Acquisition Summary

The shared MCP client is now bound at its second consumer: a projection that
declares a content requirement is served that content at decision time, acquired
from a real MCP server in another OS process, and the payload it returns carries
a covenant note whose text exists nowhere in the parent process — with the proof
demonstrated to fail when the engine's acquisition stage is removed.

## What was built

**`ccf.projection.acquisition`** — the seam, transport-free. `ContentRequest`
carries a Control Plane *source key* plus a resource *selector* and no address of
any kind; `AcquiredContent` is a frozen, opaque item plus its content address and
the request that produced it. `ContentAcquirer` is a one-method Protocol taking
`requests` and a **per-call** `tenant_id` and returning values — read-only by
shape, exactly as `Operator` is. `ContentAcquiringPlan` is a separate structural
Protocol adding `required_content()` and an `acquired_content` argument to
`invoke()`, so every I.1/I.2 projection conforms unchanged. Four typed refusals
(`AcquirerNotConfigured`, `UnknownContentSource`, `UndeclaredAcquisition`,
`ContentUnsatisfied`) under one `AcquisitionError` base; no "proceed without the
content" path exists.

**`ccf.mcp.acquisition.McpContentAcquirer`** — the reference implementation and
the third distinct client role (D-03), alongside L1 ingress and the ArtifactStore.
Constructed with resolved source-key → already-addressed `McpResourceClient`
pairs; **no public method accepts a URL, host, or scheme at call time**, so the
SSRF posture (T-06-97) is a property of the shape rather than of a validation
step. It opens no session, no event loop, and no bridge of its own — `read_text`
on the shared client is the whole transport. `{tenant}` in a selector is
substituted from the per-call tenant, which is what keeps two principals over one
acquirer apart (D-23).

**`ProjectionEngine`** — a stage between the operator plan and Π. The ordering is
documented as load-bearing: Policy is an operator, so by the time anything is
fetched the view has already been constrained, and nothing is acquired on behalf
of a principal Policy excluded (INV-CH7-26 applied to acquisition, T-06-100).
`ExecutionResult.acquisitions` records every item in resolution order with its
content address for replay dimension 5, and `execute(recorded_acquisitions=...)`
is the replay re-feed path — a replay builds the engine with `acquirer=None`, so
it has no network handle to reach for (INV-CH7-31, T-06-99). The constructor
still takes no writer, the acquirer holds no graph handle, and acquired content
terminates in the projection payload.

## Verification

| Check | Result |
|---|---|
| `pytest tests/projection -q` | 11 passed in 0.12 s |
| `pytest tests/crossproc/test_mcp_acquisition.py -q` | 7 passed in 3.77 s |
| Full suite (`-p no:randomly` and random order) | **736 passed, 2 skipped** (baseline 718/2; +18) |
| `mypy` | Success, 82 source files (baseline 80) |
| `tools.lints --all` | exit 0 |
| Acquisition stage removed → both payload proofs fail | **demonstrated**, then restored (see below) |
| `grep -rn time.sleep` over the new crossproc files | nothing |
| Orphaned children after the run | 0 |
| No URL/host/scheme literal in either `/src` module | grep returns nothing |
| `new_event_loop\|streamablehttp_client\|ClientSession` in `ccf/mcp/acquisition.py` | count 0 |

**The finding-1 requirement, demonstrated rather than assumed.** With
`_resolve_content` bypassed in `ProjectionEngine.execute` (temporary local edit),
`test_the_payload_carries_the_acquired_value` and
`test_the_served_payload_carries_a_value_only_the_child_had` both **failed**;
restoring the stage made both pass. The unit binding assertion is on the
projection payload and carries a comment forbidding its weakening into an import
or `hasattr` check — that weakening is precisely the "covered by construction"
overclaim (D-21) this plan exists to retire.

## Deviations from Plan

### Corrected criteria

**1. [Criterion correction] `'ccf.graph' not in inspect.getsource(acquisition)`**
- **Criterion (Task 1):** asserted the string `ccf.graph` appears in neither new module.
- **What is actually true:** `ccf/mcp/acquisition.py` satisfies it and the check is
  kept verbatim there. `ccf/projection/acquisition.py` **does** import `GraphView`,
  because `ContentAcquiringPlan.invoke` must declare the same `view: GraphView`
  parameter `ProjectionPlan.invoke` declares. Typing it `object` to make the grep
  pass was tried and rejected: parameter types are contravariant, so a deployment
  plan annotating `view: GraphView` would then **fail** to structurally conform to
  `ContentAcquiringPlan` — the grep would have been satisfied by breaking the
  Protocol the plan's own must-have requires to work. That is implementing a
  defect to make a criterion pass.
- **Correction applied:** for `projection/acquisition.py` the check is
  `'GraphWriter' not in s and 'AssemblyWorker' not in s` (both verified, and both
  are what the criterion's intent — "holds no graph handle" — actually names).
  `GraphView` is a frozen read value; naming it confers no capacity to write. The
  single-writer claim is carried by the cross-process watermark assertion, which
  is executed rather than grepped.

**2. [Criterion correction] "`pytest tests/projection` passes with no test-body
change to pre-existing plan fixtures"**
- `tests/projection/` did not exist. Projection-engine coverage lives in
  `tests/replay/`, `tests/integration/`, and `tests/properties/`. The directory was
  created new, so the "no change to pre-existing tests" half of the criterion is
  vacuous there. It was verified against the real target instead: `git diff` shows
  **zero** modifications to any pre-existing test file in this plan, and the full
  suite is green at +18 with no prior test touched.

### Auto-fixed / added

**3. [Rule 3 - Blocking] `tests/fixtures/banking/content_acquisition.yaml`**
- Not in `files_modified`, but the plan requires every domain value to come from
  `tests/fixtures/banking/`, and no existing fixture carries a content source, a
  selector vocabulary, a second tenant, or note text. A **new** file rather than an
  edit to `controlplane.yaml`, deliberately: sibling wave-3 agents are live and a
  new file cannot conflict with them.
- **Commit:** afff9b3

**4. [Rule 3 - Blocking] `tests/projection/__init__.py`**
- New test package, needed for collection consistency with the rest of `tests/`.
- **Commit:** afff9b3

**5. [Rule 2 - Missing functionality] Content-address verification on re-feed**
- The plan specifies that replay re-feeds recorded content. It did not specify
  what happens when a re-fed item's bytes do not match its recorded
  `content_hash`. Trusting it would make the recorded address decorative and would
  let a tampered replay record produce a "reproduced" decision that never
  happened. The engine now refuses (`ContentUnsatisfied`), with a test.
- **Commit:** f082cd3 / afff9b3

## Honest scope statement (per the plan's own standard)

What is demonstrated, executably: a `ContentAcquiringPlan` declares a request;
the engine resolves it through `McpContentAcquirer` over `ccf.mcp.client`; the
client reaches a real `FastMCP` server in a separate OS process over loopback
streamable HTTP; the returned note lands in the projection payload; the graph is
byte-identical across the execution; two tenants do not cross; and a replay with
`acquirer=None` reproduces the payload. Removing the stage breaks it.

What is **not** claimed: this plan does not deliver the L1 ingress leg (06-06
owns it) or the Experience-layer leg (Phase 7 per `06-CONTEXT.md`, recorded as a
gate row by 06-16). ROADMAP criterion 1 is closed only for L4/L5 by this plan.

## Known Stubs

None. Every surface delivered is exercised end to end, in-process and across a
process boundary.

## Threat Flags

None beyond the plan's registered surface. The one new outbound network edge
(`McpContentAcquirer`) is addressed only at construction and is bound to
loopback in the tests.

## Self-Check: PASSED

- All seven created files present on disk; `src/ccf/projection/engine.py` modified.
- Commits `f082cd3` and `afff9b3` present in `git log`.
- Suite, mypy, and lints re-verified at the values in the table above.
