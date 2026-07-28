---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 06
subsystem: L1 MCP client ingress + mcp skill dispatch
tags: [mcp, ingress, l1, xprc-01, d-05, d-impl-13, ssrf, d-23]
requires:
  - "06-03 (dispatch's CallableRegistry injection and the D-19 resolved-key posture)"
  - "06-04 (ccf.mcp.client — the ONE shared client; tests/crossproc/conftest.py — THE shared fixture)"
provides:
  - "ccf.signal.mcp_source.MCPSourceAdapter — SignalSourceProtocol over MCP (L1 ingress)"
  - "ccf.signal.mcp_envelope_map — to_envelope + McpMappingError, transport-free"
  - "ccf.skills.dispatch.McpSkillRegistry / McpInvocation / McpSkillUnregistered — the bound mcp dispatch path"
  - "AuditAction member `skill_invoked` on the one existing AuditLog"
  - "tests/crossproc/servers/mcp_ingress_child.py — a source-side child for the shared fixture"
affects:
  - "06-17 (L4/L5 acquisition: second consumer of the same shared client)"
  - "06-10 (a2a dispatch: flips the remaining NotYetBound tail)"
  - "06-12/06-13 (harness skill exposure: mcp is now a working skill type at dispatch)"
tech-stack:
  added: []
  patterns:
    - "adapter/mapping split mirroring ccf_runtime.cdc (transport async, mapping pure and sync)"
    - "logical-name registry as the SSRF control: artifacts name servers, deployments name addresses"
    - "audit-by-construction via required constructor arguments rather than an opt-in hook"
key-files:
  created:
    - src/ccf/signal/mcp_source.py
    - src/ccf/signal/mcp_envelope_map.py
    - tests/signal_layer/__init__.py
    - tests/signal_layer/test_mcp_source.py
    - tests/crossproc/test_mcp_ingress.py
    - tests/crossproc/servers/mcp_ingress_child.py
    - tests/fixtures/banking/mcp_source.yaml
  modified:
    - src/ccf/skills/dispatch.py
    - src/ccf/controlplane/audit.py
    - src/ccf/agents/agent.py
    - tests/skills/test_dispatch.py
    - tests/fixtures/banking/skills/document_fetch_mcp.yaml
decisions:
  - "The adapter calls `run_with_session` from the shared client rather than a new `read_contents` method on `McpResourceClient`: ingress needs per-item contents (uri, mimeType, blob) that `read_text_async` deliberately flattens, and 06-17 is concurrently in `client.py` — reaching for the shared library's existing seam avoids both a duplicate transport and a merge conflict."
  - "`McpBinding.server`/`resource` are resolved through a new `McpSkillRegistry` (logical name → client + URI) rather than treated as an address. This is the SSRF control expressed as a type: an artifact has no field in which an address could arrive."
  - "Audit is enforced by the registry's *constructor*, which requires the AuditLog and a clock. There is no way to wire mcp dispatch without supplying the surface every invocation is recorded on."
  - "Unit tests live in `tests/signal_layer/`, not `tests/signal/` — see Deviations."
metrics:
  duration: ~75 min
  completed: 2026-07-26
---

# Phase 06 Plan 06: L1 MCP Ingress and `mcp` Skill Dispatch Summary

An external MCP server in another OS process is drained into valid L1
`SignalEnvelope`s by an adapter that structurally cannot write to the graph,
and `mcp` skills now dispatch through the one shared client with governance
ahead of the network and an audit record on every attempt — closing the L1
half of XPRC-01's client leg.

## What was built

**`ccf.signal.mcp_envelope_map`** — a pure `to_envelope(contents, *, tenant_id,
system_id, resource_name, ingestion_timestamp)` plus `McpMappingError`, split
from transport exactly as `ccf_runtime.cdc.envelope_map` is. Research Pattern
2's table implemented row for row: `source.system_id` is the deployment's
declared identity (never any part of an address), `ingestion_timestamp` comes
from the injected clock, `observed_time` is `None` **with its reason stated as
the answer rather than as a TODO**, the payload lands opaque in `raw_payload`
(JSON object for text, `{"blob": <base64>}` for binary — carried, never
decoded), and the MCP-shaped delivery facts (`uri`, `mimeType`,
`resource_name`, `_meta`) are quarantined into `source_metadata`. `envelope_id`
is a content hash over the source coordinates and delivered content — so a
polling ingress that re-reads unchanged content collapses under idempotent
upsert instead of manufacturing history. The server's `_meta` is deliberately
outside that hash.

**`ccf.signal.mcp_source.MCPSourceAdapter`** — `SignalSourceProtocol` over the
shared client. Keyword-only constructor taking `system_id`, the injected
`McpResourceClient`, the deployment's `resources` selection, and a clock.
Reads go through `ccf.mcp.client.run_with_session`; the adapter constructs no
session, no loop, no bridge. `envelopes(*, tenant_id)` takes tenancy and
nothing else — the SSRF control (T-06-24) is a property of the signature, not
a validation step, and the unit suite asserts it on the signature for exactly
that reason.

**`ccf.skills.dispatch`** — the `mcp` branch replaces its half of the
`NotYetBound` tail. `McpSkillRegistry` maps a logical `{server, resource}`
pair onto a shared client plus a Control-Plane URI; `resolve` fails *before*
touching the client, so an artifact naming an unregistered target costs no
traffic. `McpInvocation` carries the logical server and resource names (never
the endpoint — INV-CH8-01), the returned text, and the arguments, which are
recorded but never transmitted or interpolated into an address. Both outcomes
append `skill_invoked` to the one existing `AuditLog`. The `a2a` branch still
raises `NotYetBound`, with its message narrowed to name only A2A as
outstanding, and the tail survives so a fifth skill type gets a typed refusal
rather than a fall-through.

**Tests** — 12 unit tests in `tests/signal_layer/test_mcp_source.py`, 6
cross-process tests in `tests/crossproc/test_mcp_ingress.py` (2.3 s, no
orphans), and 6 new `mcp` cases in `tests/skills/test_dispatch.py`. The
cross-process child is a *source*, not a fabric: it boots no graph and imports
no assembly code, which is what makes the parent's "L1 did not interpret"
assertion mean something.

## Verification

| Check | Result |
|---|---|
| `pytest tests/signal_layer -q` | 12 passed |
| `pytest tests/crossproc/test_mcp_ingress.py -q` | 6 passed in 2.3 s |
| `pytest tests/skills -q` | 76 passed |
| Full suite | **742 passed, 2 skipped** (baseline 718/2; +24) |
| `mypy` | Success, 82 source files |
| `tools.lints --all` | exit 0 |
| `grep 'http://\|https://\|localhost\|127.0.0.1'` on both src modules | nothing |
| `grep -c 'new_event_loop\|streamablehttp_client\|ClientSession'` in dispatch.py | 0 |
| `grep -rn time.sleep tests/crossproc/test_mcp_ingress.py` | nothing |
| Orphaned children after the run | 0 |
| Tenancy moved to the constructor (temporary edit) | **2 tests fail**, restored |

## Deviations from Plan

### Corrected plan criteria

**1. `tests/signal/` shadows the stdlib `signal` module — renamed to `tests/signal_layer/`**
- **Found during:** Task 3, on first collection.
- **Issue:** `tests/` is on `sys.path`, so a package named `signal` there
  shadows the standard library module of that name. Collection failed with
  `No module named 'signal.test_mcp_source'`. Worse than a collection failure:
  had it resolved the other way, `asyncio` and `subprocess` — which the
  cross-process suite depends on — would have imported the test package.
- **Fix:** `tests/signal_layer/`, with the reason recorded in its
  `__init__.py` so nobody renames it back. The plan's three
  `tests/signal/test_mcp_source.py` criteria were satisfied at the new path.
- **Commit:** c6f142c

**2. The plan's "at least 5 tests" and cross-process criteria assume one envelope per fixture event row; `events.yaml` repeats an id**
- **Issue:** `events.yaml` deliberately contains `env-002` twice (the
  re-delivery case). A resource selection keyed by resource name collapses
  that to one published resource, so the live drain yields 5 envelopes for 6
  fixture rows. Asserting `len(drained) == len(events["envelopes"])` would
  have forced a *wrong* implementation — one that published the same resource
  name twice, or minted two envelopes for one record.
- **Fix:** the assertion compares against the distinct resource count, with
  the reasoning stated inline.
- **Commit:** c6f142c

**3. "audited on the same path as every other dispatch" — no other dispatch type is audited**
- The plan's wording implies a pre-existing dispatch audit path. There is
  none: `local_callable` and `tool` dispatch are unaudited as of I.2/06-03.
  What was implemented is the defensible reading — the *same log* and the
  *same* `AuditLog.append`, not a parallel surface. Auditing the other two
  types is out of this plan's scope and is **not** done here.

### Auto-fixed / added beyond `files_modified`

**4. [Rule 2 - Missing functionality] `AuditAction` member `skill_invoked` (`src/ccf/controlplane/audit.py`)**
- The plan permits a new member "if the existing members genuinely cannot
  express an `mcp` invocation". They cannot: `resolve` is a Control Plane
  read and the `grant_*` family are grant-state transitions, so recording an
  outbound invocation as either would make the log assert something untrue.
  Additive to the `Literal`; goes through the one existing log.
- **Commit:** 1821eb5

**5. [Rule 3 - Blocking] `Agent.invoke_skill` return type (`src/ccf/agents/agent.py`)**
- `dispatch_skill` can now return `McpInvocation`, which mypy rejected against
  the old union. Two-line type widening plus a docstring correction. **No
  behavioural change and no registry threading** — see Known Gaps.
- **Commit:** 1821eb5

**6. [Rule 3 - Blocking] New fixtures: `tests/fixtures/banking/mcp_source.yaml`; `deployment`/`dispatch`/`grant` blocks added to `document_fetch_mcp.yaml`**
- Required by the No-Hardcoding Rule: the suites needed a system identity, a
  URI scheme, two tenant ids, a server-name→URI registration, and a grant
  document, none of which may live in test code. Put in the mcp skill's *own*
  fixture rather than in the shared `grants.yaml`, to keep out of a
  concurrently-running sibling's way.
- **Commits:** 1821eb5, c6f142c

**7. [Rule 3 - Blocking] `tests/signal_layer/__init__.py`**
- Package marker, matching `tests/skills` and `tests/agents`.
- **Commit:** c6f142c

## Known Gaps

**An `mcp` skill invoked *through an `Agent`* still refuses.** `dispatch_skill`
binds the transport, but `Agent.invoke_skill` passes only `callable_registry`
to it — threading an `McpSkillRegistry` from `AgentFactory` through `Agent`
would require editing `agent.py` and `factory.py`, both outside this plan's
`files_modified` and both read by three concurrently-running sibling plans.
The refusal is now an honest one: `McpSkillUnregistered` naming the missing
registry, rather than the old `NotYetBound` claim that no transport exists,
which is no longer true. Documented in `Agent.invoke_skill`'s docstring.
**A later plan must thread the registry through the factory** before harness
skill exposure (06-12/06-13) can surface an `mcp` skill as a working tool.

This is a wiring gap, not a stub: every surface this plan delivers is
exercised end to end, and nothing returns placeholder data.

## Threat Flags

None beyond the plan's register. The one new outbound surface — the MCP client
edge at L1 and at `mcp` dispatch — is the surface T-06-24 already covers, and
both halves take their addresses from Control Plane configuration fixed before
any read.

## Self-Check: PASSED

- All seven created files present on disk.
- Commits `06ec983`, `1821eb5`, `c6f142c` present in `git log`.
- Suite (742/2), mypy (82 files), and lints (exit 0) re-verified at the values
  in the table above.
- No modification to `STATE.md` or `ROADMAP.md`.
