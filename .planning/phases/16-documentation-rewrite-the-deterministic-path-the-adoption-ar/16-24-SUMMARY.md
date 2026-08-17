---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 24
subsystem: runtime/mcp/experience
tags: [security, entitlement, mcp, experience-layer, D-IMPL-128, D-IMPL-129]
requires:
  - "16-22 (the surface-changes glob widened past Phase 15)"
  - "16-23 (the sibling 16-* fragment the same reassembly covers)"
provides:
  - "get_context and get_lineage entitled with the resource's own sequence"
  - "ContextProviderProtocol carrying the authorized perspective"
  - "a six-row gated/ungated audit of every tool the module registers"
  - "three known gaps pinned open by a named executable assertion"
affects:
  - "any deployment composing build_experience_server with a consumption tool"
tech-stack:
  added: []
  patterns:
    - "one governance sequence imported by three doors, never re-declared"
    - "declared-address governance operands, deployment-supplied by design"
    - "known gaps pinned by inverting tests rather than by prose"
key-files:
  created:
    - docs/surface-changes/16-24-experience-door-entitlement.md
  modified:
    - runtime/ccf_runtime/mcp/experience.py
    - tests/crossproc/servers/mcp_experience_child.py
    - tests/crossproc/test_experience_edge.py
    - examples/external/00-hello-context/serve.py
    - docs/SURFACE-CHANGES.md
    - tests/test_surface_shape_capture.py
decisions:
  - "D-IMPL-128 limb 1 closed; limb 2 left open as a named residual"
  - "D-IMPL-129's three ungated tools shipped authenticated and pinned"
metrics:
  duration: ~2h
  completed: 2026-08-14
requirements: [DOCS-21]
---

# Phase 16 Plan 24: The Experience Door's Tools Are Entitled Summary

`D-IMPL-128` limb 1 closed: `get_context` and `get_lineage` on the SDK's
external MCP front door now traverse the identical
`verified_grant()` → `entitled_perspective(...)` sequence the `context_product`
resource beside them traverses, the authorized perspective is forwarded into
`ContextProviderProtocol` and *used* by both shipped providers, and the three
tools a Context Product entitlement cannot honestly decide ship authenticated
with the absence stated unhedged and pinned by a test whose inversion is the
signature of the fix.

**Phase base:** `BASE = 8d249540d8d66002bc084a48c78f8387440b6b69`. Every diff
criterion below is taken against `$BASE..HEAD`, never a bare `git diff` — this
plan commits per task, after which the bare form is empty for every path and
would certify nothing.

## Commits

| SHA | Type | What |
| --- | --- | --- |
| `8b4101d` | test | RED: the undeclared principal the tool serves at BASE |
| `cce7c6a` | feat | Task 1 — the gate, the audit, the adopter updates |
| `a0c8dcc` | test | Task 2 — the over-the-wire proof, the in-process legs, the pins |
| `945f9f1` | docs | Task 3 — the measured fragment, the reassembly, the escalations |
| `0125c04` | docs | the two ratchets this change tripped, satisfied not worked around |

## The negative control, verbatim

Task 2(c) required the headline test to be shown failing against the ungated
handler before the fix. It was written first and run at `8b4101d`, where
`get_context`'s body was still
`return context_seam(tenant=tenant, entity=entity)`:

```
>       assert is_error, body
E       AssertionError: {"debt":null,"debt_evidence":[],"expires_at":"2026-03-01T10:05:05.000000Z","lineage":{"graph_snapshot_at":"2026-03-01T10:00:00.000000Z","operators_invoked":["policy.principal-subgraph","similarity.corpus-select","temporal.as-of-boundary","traversal.typed-neighborhood"],"policy_bundle_versions":["1d3001f6f414d1cf006da97b6c6822cd22555bdd6fdec5a7da939069434b67db"]},"obligation_in_force":"ccf.no-obligation-in-force","payload":{"entities":[{"entity_class":"counterparty","entity_uri":"counterparty://e66aec6411531e9b69438d734ea4c6de6e530e711d6a4995efeb08a27bc0784d"},{"entity_class":"facility","entity_uri":"facility://c1350196a8899a4c75d2017c4fd132b072dd5d1e29d6a70f2bdffc523e8888ec"},{"entity_class":"guarantee","entity_uri":"guarantee://99f26795eae54ab5a63eb2a8bd61269075e497a6eb6ba775a9d37e32e493316d"}],"entity_count":3,"relationship_types":["guarantees","obligor_of"],"role":"credit-analyst"},"plan_id":"acme-bank.credit-exposure-summary.plan","schema_name":"acme-bank.credit-exposure-summary","schema_version":"1.0.0","source_refresh_recency":null,"temporal_boundary":"2026-03-01T10:00:00.000000Z","tenant_id":"acme-bank","ttl_anchor":"from_decision"}
E       assert False

tests/crossproc/test_experience_edge.py:841: AssertionError
FAILED tests/crossproc/test_experience_edge.py::test_a_verified_but_undeclared_principal_is_refused_by_the_context_tool[child_server_port0]
1 failed in 1.10s
```

The failure message **is** the evidence: a verified caller the tenant's policy
does not declare received the whole assembled Context Product — payload,
lineage, operators invoked, policy bundle versions, temporal boundary.

**No temporary revert was needed and none was performed**, because the test was
written before the implementation rather than after it. The plan offered both
routes ("before implementing Task 1, **or** by temporarily reverting"); the
first is stronger, since there is no window in which a revert could be left
half-undone. `git diff --stat $BASE..HEAD -- src/ pyproject.toml .planning/` is
empty, and the only files that differ from `$BASE` are the seven listed below.

## Verification — one line per gate

| Gate | Result |
| --- | --- |
| `make ci-core` | **exit 0** — 3170 passed / 118 skipped (3154 / 118 at `$BASE`) |
| `make examples` | **exit 0** — `example-ext-00` PASS 1–8, PASS 6 (resource ≡ `get_context` bytes) included |
| `make docs-strict` | **exit 0** |
| `CCF_TEST_FLUREE_URL=… make leg-fluree` | **exit 0** — 76 passed |
| `python -m tools.lints --all` | **exit 0** (`LINTED_TREES` = `src, runtime, examples, tests`) |
| `python -m mypy` | **exit 0** — 195 source files |
| `pytest tests/crossproc` | **exit 0** — 129 passed |
| `pytest tests/invariants/test_mcp_role_separation.py` | **exit 0** — 32 passed |
| `pytest tests/test_surface_drift.py tests/test_surface_completeness.py` | **exit 0** — 16 passed |

## Task 1 acceptance criteria, measured

| Criterion | At `$BASE` | Now |
| --- | --- | --- |
| `grep -c "grant=verified_grant()"` | 1 | **3** (resource, `get_context`, `get_lineage`) |
| `grep -c "entitled_perspective("` | 1 | **3** |
| `grep -c "requested_role=None,"` | 1 | **3** |
| `grep -n "verified_grant()"` lines | 2 | **6** |
| `grep -c "_missing("` | 6 | **6** (unchanged — the address refusal has its own helper) |
| audit rows in the module docstring | — | **6**, verified against `EXPERIENCE_TOOLS` from Python |

The six `verified_grant()` lines were **read**, not counted: 879 → `context_product`,
922 → `list_agents`, 965 → `invoke_agent`, 1018 → `get_context`,
1063 → `get_lineage`, 1095 → `get_replay_record`. Each sits inside the handler
it is claimed for; none is in a docstring.

### The resource is unchanged — the filtered diff, verbatim

`git diff $BASE..HEAD -- runtime/ccf_runtime/mcp/experience.py | grep "^-" | grep -v "^---"`
returns exactly eight lines:

```
-    def __call__(self, *, tenant: str, entity: str) -> str:
-            ExperienceProductNotServable: nothing servable at that address.
-            provider or no description supplied (D-03).
-            """List one tenant's exposed agents with their rendered tool surfaces."""
-            """Serve one tenant's entity-scoped product via the injected seam."""
-            return context_seam(tenant=tenant, entity=entity)
-            """Serve the product's lineage via the injected seam."""
-            """Serve the most-recent replay record via the injected seam."""
```

Not one line is from the `context_product` resource body, from
`EXPERIENCE_PRODUCT_URI_TEMPLATE`, or from `ExperienceProductResolverProtocol`.
This is the sole evidence for must_have truth 6 and success criterion 5.

### The predicted break, and the accounting correction

`test_a_server_exposing_no_agent_tools_needs_no_agent_seams` broke exactly as
the plan predicted and was repaired with the named two-keyword edit. **No second
pre-existing test broke of its own accord.**

One accounting note, recorded rather than glossed. The plan's criterion reads
"exactly one pre-existing test fails at this point", where "this point" is the
end of Task 1. That is only reachable if Task 1's `experience.py` change lands
*with* the mechanically-forced adopter updates the plan assigns to Task 2(a)
and 2(b) — widening `ContextProviderProtocol` and requiring
`entitled_product_class` makes the crossproc child's `build_server` raise at
build time, which would fail every test that composes it. Rather than commit a
knowingly-broken tree, Task 1's commit `cce7c6a` carries the `experience.py`
change **plus** those two adopter updates, which are Task 2's files but are the
same edit either way. Task 2's commit then carries the proof apparatus alone.
The plan's own Task 2(a)/(b) text names both updates, so nothing was done that
the plan did not ask for; only the commit boundary moved.

## Task 2 acceptance criteria, measured

| Criterion | At `$BASE` | Now |
| --- | --- | --- |
| `test_experience_edge.py` collected | 19 | **35** (strictly greater) |
| `grep -c "parametrize"` | 1 | **3** (strictly greater) |
| `grep -c "ERROR_PRODUCT_POLICY_ABSENT"` | 0 | **7** |

The parametrized ids name **both surfaces for each scenario**, asserted on the
id list rather than the grep count:

```
…decide_one_scenario_alike[child_server_port0-the-resource-an-entitled-caller]
…decide_one_scenario_alike[child_server_port0-the-resource-an-undeclared-principal]
…decide_one_scenario_alike[child_server_port0-the-resource-a-foreign-tenant]
…decide_one_scenario_alike[child_server_port0-the-get-context-tool-an-entitled-caller]
…decide_one_scenario_alike[child_server_port0-the-get-context-tool-an-undeclared-principal]
…decide_one_scenario_alike[child_server_port0-the-get-context-tool-a-foreign-tenant]
```

The entitled leg asserts served-vs-served on the **product bytes**, not on the
absence of an error, so "they agree" cannot mean only that both said yes.

### The foreign-tenant vacuity trap, honoured

The plan warned that the child's `provide_context` already raises
`ExperienceProductNotServable` for a foreign tenant, so "it errored" passes
identically before and after the fix. Both discriminators are asserted:

- **which refusal** — `ERROR_PRODUCT_POLICY_ABSENT`, the entitlement's
  deny-by-default path, which a bare `LookupError` from the provider cannot
  produce; the same test additionally asserts `ExperienceProductNotServable` is
  **not** in the refusal;
- **that the provider was never entered** — a call counter, asserted *equal*
  across the refusal **and** asserted to *increment* across a served call in the
  same test, so "unchanged" is not satisfiable by a counter that never moves.

### No pre-existing assertion was deleted or weakened

`git diff $BASE..HEAD -- tests/crossproc/test_experience_edge.py | grep "^-" | grep -v "^---"`
returns five lines, all signatures or one-line docstrings:

```
-    bridge: SyncMcpBridge, url: str, name: str, arguments: dict[str, Any]
-    """Call one tool; return ``(is_error, first text content)``."""
-            http_client_factory=authorized_http_client,
-    """The other half of D-03: omission is legal when nothing is exposed."""
-    def provide_context(*, tenant: str, entity: str) -> str:  # pragma: no cover
```

Nothing from the pre-existing governance bodies. The two D-03 tests gained
`entitled_product_class` **and** an assertion naming the leg they test
(`"provider or description" in message` plus
`"entitled_product_class" not in message`), so neither can be satisfied by the
new check.

### T-16-24-05 is `mitigate` in full, not partial

Both halves shipped. **By value:** a recording stub asserts the received
`Perspective`'s `principal_id` is the verified client and its `role` is the
entitlement-authorized role — not a keyword in the source. **By refusal:** a
two-role policy with a resolver proposing the role the product was *not*
assembled under, and the provider refuses. Neither leg was descoped.

Three legs run in-process, each for a stated reason recorded in its own
docstring rather than for convenience: the counter cannot cross the process
boundary without inventing an IPC channel the fixture does not have; the
class-outside-the-grant scenario has no wire representation on a tool whose
class is deployment-declared; and the role-mismatch leg needs a two-role policy
where the shipped child grants one and widening it would disturb every other
leg. In-process calls stand in for the bearer middleware by setting the same
`auth_context_var` the middleware sets — what is under test there is the
*entitlement* decision, which runs on the verified identity however it arrived.

## Task 3 — the two surface comparisons, kept apart

The plan's figures were measured at `68e91ac`, before `16-22` and `16-23`
landed. Re-measured at this plan's actual base:

**Frozen-baseline-vs-live** (completeness — `test_surface_completeness.py::_diff()`):

| | added | removed | reshaped |
| --- | --- | --- | --- |
| at `$BASE` | 247 | 0 | 55 |
| after | 247 | 0 | 55 |

**The counts did not move.** Stated plainly rather than implied: this fragment
is **not** what keeps that gate green. `build_experience_server` and
`ContextProviderProtocol` were already in `reshaped` — claimed by
`15.5-06-egress-entitlement.md` and `15.6-10-protocol-call-capture.md` — and
stay in `reshaped`. Zero new diff lines. Two entries are filed anyway because
the earlier fragments' `Before`/`After` describe different changes, and the gate
accepts multiple entries per name.

**Committed-manifest-vs-live** (drift — `tools/dump_surface.py --report`):

| | added | removed | reshaped |
| --- | --- | --- | --- |
| at `$BASE` | 6 | 0 | 2 |
| after | 6 | 0 | 4 |

Drift gains **exactly** the two names this plan moved. It was already non-empty
at `$BASE` (the plan expected `0/0/0` from `68e91ac`) because the committed
manifest trails the live surface across Phase 16; the gate survives because
`unclaimed_drift` claims by name-or-module and both appear in the fragment
union.

### The reassembly branch, chosen on a measured predicate

```
>>> [p.name for p in fragment_paths()][-3:]
['16-22-consumption-papercuts.md', '16-23-mcp-product-tool.md', '16-24-experience-door-entitlement.md']
```

The fragment **is** visible, so `16-22`'s glob widening is in force and the
first branch applies: `make surface-changes` was re-run and the regenerated
`docs/SURFACE-CHANGES.md` committed (`26 insertions(+), 2 deletions(-)` against
`$BASE`). The regeneration also covers `16-23`'s fragment; that is a
deterministic regeneration of a derived artifact, and `16-23`'s source fragment
was not touched.

The non-emptiness assertion ran **first** and did not raise:

```
['ccf_runtime.mcp.experience.build_experience_server',
 'ccf_runtime.mcp.experience.ContextProviderProtocol']
```

Only then was the intersection drawn: both names are present in the
completeness `_diff()` under `reshaped`, the direction each entry claims.

## Deviations from Plan

### [Rule 3 — Blocking] Two ratchets tripped and were satisfied, not worked around

Neither was in `files_modified`; both blocked `make ci-core`, and both are
correct gates catching a real property of this change.

**1. `tests/invariants/test_citation_coverage.py` — six unanchored Python-target
citations, ceiling 0.** `D-IMPL-114` rules that prose cites `path.py::Symbol`
because a line anchor is wrong the moment code moves. Every citation this plan
added was converted to the symbol form; the ceiling was **not** raised. The
ruling proved itself in the same session: the `serve.py:679-694` range cited in
the fragment had already rotted, because this plan's own edit shifted it, and
the citations lint caught it within minutes of the fragment being written.

**2. `tests/test_surface_shape_capture.py` — `build_experience_server`'s
committed shape moved.** This is exactly the case `D-IMPL-96` reopened for
Phase 16 and `D-IMPL-130` supplied a claim mechanism for; the orchestrator's
brief named it in advance. Claimed in `_SHAPE_MOVED_BY_FRAGMENT` against this
plan's fragment, alongside `16-22`'s and `16-23`'s entries. The test verifies
the cited fragment exists and names the surface, so the list cannot go mute.
`ContextProviderProtocol` needs no entry — the assertion already excludes
Protocols.

Both are in commit `0125c04`, so `git log` distinguishes a deliberate addition
from an accidental regression, which the coverage ratchet's own failure text
asks for.

### [Rule 3 — Blocking] The commit boundary between Tasks 1 and 2 moved

Recorded in full under "The predicted break, and the accounting correction"
above. No work was added or dropped; a mechanically-forced adopter edit landed
one commit earlier than the plan's task split implies, to avoid committing a
knowingly-broken tree.

### Instrumentation choice inside the crossproc child

Task 2(a) offered a call counter in the child *or*, if it could not cross the
process boundary, an in-process leg. It cannot, so the in-process route was
taken — and rather than leave a dead counter in the fixture, the child's
`provide_context` was given the **role check** instead. That is a non-dead use
of the widened argument and makes a served call over the wire itself evidence
that the right role arrived.

## What this plan did **not** do

- **`D-IMPL-128` limb 2 is not closed.** Client-chosen `entity`/`subject` is not
  entitlement-scoped; `entitled_perspective` carries no subject dimension. It
  remains a named residual, unassigned by ruling, because closing it needs a
  perspective-scoped assembly path `D-IMPL-119` limb 2 measured as empty on the
  shipped path and `D-IMPL-124` Shape D was blocked on. Per the ruling's own
  words and recorded in the fragment: **the gating is not cited as evidence that
  entity-scoping is unnecessary.**
- **No scoped assembly was built.** No file under `src/` moved; `git diff --stat
  $BASE..HEAD -- src/ pyproject.toml` is empty.
- **No sibling plan's file, the ROADMAP, `16-CONTEXT.md`, `16-RESEARCH.md`,
  `16-PATTERNS.md`, `docs/DECISIONS.md`, `REQUIREMENTS.md` or
  `deferred-items.md` was touched.** `git diff --stat $BASE..HEAD --name-only`
  lists seven files, all owned by this plan or claimed as a ratchet deviation.

## For Dave

**One item needs a ruling, and it is `D-IMPL-129`'s own consequence made
concrete.** The three ungated tools ship exactly as ruled — authenticated,
labelled, pinned — but the pin is now an *executable assertion that the SDK's
front door serves a client-chosen tenant's agent population, dispatches its
agents' bound skills, and hands out its Decision Replay records to any verified
caller.* The test asserts what they disclose, not merely that they returned:
the agent listing's `definition_key` and rendered tool surfaces, the
invocation's dispatched skill output, and the replay record's
`perspective_conditioning`. That is the ruled disposition working as intended —
a gap that cannot rot — but it is worth Dave seeing the shape of what is pinned
open before it sits in `main`. `invoke_agent` in particular takes **every**
argument from the client, the tenant included.

**A correction to `D-IMPL-129`'s own text, recorded in the fragment rather than
by editing the decision log:** it cites the HITL door precedent at
`runtime/ccf_runtime/hitl_server.py:267-290`. That path does not exist; the
correct one is `runtime/ccf_runtime/mcp/hitl_server.py::_enforce_tenant_authz`.
A later reader following the ruling would be sent to a file that is not there.
Correcting `docs/DECISIONS.md` is outside this plan's scope fence, so the
correction is stated in the fragment and flagged here.

## Self-Check: PASSED

Files claimed created/modified, verified present:

- `FOUND: docs/surface-changes/16-24-experience-door-entitlement.md`
- `FOUND: runtime/ccf_runtime/mcp/experience.py`
- `FOUND: tests/crossproc/servers/mcp_experience_child.py`
- `FOUND: tests/crossproc/test_experience_edge.py`
- `FOUND: examples/external/00-hello-context/serve.py`
- `FOUND: docs/SURFACE-CHANGES.md`
- `FOUND: tests/test_surface_shape_capture.py`

Commits claimed, verified in `git log`: `8b4101d`, `cce7c6a`, `a0c8dcc`,
`945f9f1`, `0125c04`.

No stubs. No placeholder values. No `TODO` or `FIXME` introduced. No entry
added to `tools/lints/allowlist.yaml`. No new dependency —
`git diff --stat $BASE..HEAD -- pyproject.toml` is empty.
