# 17-10 — `mcp+stdio` ships as the second official adapter

Plan `17-10` Tasks 3 and 4. `D-06` has spelled this scheme `mcp+stdio:./server.py`
in `ccf.client.binding` and `ccf.client.client` since the client design was
written; this change is that spelling honoured rather than re-decided, and
`docs/superpowers/specs/2026-08-15-ccf-client-design.md` §6 is what makes it
*official*: **an adapter is official when it passes the conformance suite**, not
when it demos.

## What did **not** change, stated first

- **`tests/client/conformance/suite.py` is untouched.** Binding a real second
  transport required no edit to it — which is the acceptance test for plan
  `17-07`'s adapter-agnostic claim, and the first time that claim has been
  non-trivially true. One leg could not be bound *across* two subjects, and that
  is recorded as a finding in the plan's SUMMARY rather than fixed by narrowing
  an assertion.
- **`ccf.client.__all__` is unchanged** and still carries exactly the four names
  `D-03` fixes it at. An adapter is reached by importing its module, never by a
  fifth exported name.
- **No `Result` is constructed here.** `D-12` keeps that in one place; this
  adapter returns a `WireOutcome` and `ProductClient._result_from` does the
  rest, so shape identity across transports stays a code path an adapter cannot
  avoid.
- **The client surface is still synchronous.** `D-24`'s sync-only ruling named
  this adapter as its revisit trigger; the trigger fired and the answer is
  unchanged — the async client is bridged inside `ask`, and no asynchronous twin
  of it exists.
- **`ccf.client.binding.SCHEME_REGISTRY` grew no mechanism.** The scheme is one
  dict assignment at the bottom of the adapter module, which is the whole of how
  a scheme reaches the registry (`D-05`).
- **The egress door is unchanged.** Task 2 shipped what this adapter consumes;
  Tasks 3 and 4 added no argument, no surface and no behaviour to it.

## ccf.products.door.PRODUCT_REQUEST_TOOL

- Surface: ccf.products.door.PRODUCT_REQUEST_TOOL
- Public surface: true
- Change type: added
- Before: the name was bound in `ccf_runtime.mcp.egress` and only there. Nothing
  in `src/` could refer to the tool it names, because `src/` cannot import
  `runtime/`
- After: the string is bound in `ccf.products.door` and
  `ccf_runtime.mcp.egress` imports it and re-exports it under the same name, so
  every existing `ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL` citation and
  import resolves unchanged
- Why: the *emitting* side is a door in `runtime/` and the *calling* side is
  `ccf.client.adapters.mcp_stdio` in `src/`. This is precisely the argument
  `ccf.products.door` already makes for holding `DoorOutcome` — a fact spelled on
  both sides of a boundary neither can cross is two implementations written to
  the same paragraph rather than one fact. The tool's *name* is SDK mechanism and
  not a deployment value (CINV-01): a deployment chooses whether to expose the
  tool and what prose it advertises, and the SDK chooses what it is called,
  exactly as it chooses the shape of what the tool returns
- Migration: none. The name is still exported from `ccf_runtime.mcp.egress` and
  still holds the identical string, so no import, citation or wire call moves

## ccf.client.adapters.mcp_stdio.McpStdioAdapter

- Surface: ccf.client.adapters.mcp_stdio.McpStdioAdapter
- Public surface: true
- Change type: added
- Before: absent. `inprocess` was the only shipped transport, so every
  cross-adapter comparison in the conformance suite degenerated to a
  self-comparison and the phrase *"same `consume.py`, different `CCF_BINDING`,
  identical `Result`"* had one binding to be true of
- After: a `TransportAdapter` that launches the deployment's own MCP server
  program as a child process, calls the parameterised product tool over stdio,
  and re-shapes the door's `DoorOutcome` as a `WireOutcome`. The address form is
  `mcp+stdio:<program>` and the deployment is the program's own directory —
  stdio means the client launches the server, so a client that starts a
  deployment necessarily knows where it is
- Why: `D-06` and `D-15`. A conformance suite parameterised over adapters is
  worth nothing with one adapter bound, and CLAUDE.md §7.3's portability
  commitment is *demonstrated, not asserted*. With this adapter bound, one
  question at one instant is shown to produce a byte-identical content address
  and the identical replay reference through two genuinely different transports
- Migration: none — additive. A deployment reaches it by setting `CCF_BINDING`
  to an `mcp+stdio:` address and importing
  `ccf.client.adapters.mcp_stdio`, the same way `inprocess` is reached. It ships
  **no** server program and cannot: `build_egress_server` requires five
  deployment values, so the program is the deployment's to write

## ccf.client.adapters.mcp_stdio.SCHEME

- Surface: ccf.client.adapters.mcp_stdio.SCHEME
- Public surface: true
- Change type: added
- Before: absent
- After: the string `mcp+stdio`, bound once so the registry entry, the adapter's
  refusal messages and the tests all say the same thing
- Why: the sibling of `ccf.client.adapters.inprocess.SCHEME` and for its stated
  reason — a scheme spelled at each use site is a scheme two of them can drift on
- Migration: none — additive
