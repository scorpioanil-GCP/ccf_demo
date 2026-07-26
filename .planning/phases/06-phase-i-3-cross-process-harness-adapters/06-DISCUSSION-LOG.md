# Phase 6: Phase I.3 — Cross-Process & Harness Adapters - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-26
**Phase:** 6-phase-i-3-cross-process-harness-adapters
**Areas discussed:** Slice shape & wave order, Harness dependency & test posture, A2A wire implementation risk, Cross-process test topology

---

## Slice shape & wave order

### What carries the vertical slice?

| Option | Description | Selected |
|--------|-------------|----------|
| MCP egress at L6 | Serve one banking Context Product as an MCP Resource; no harness, no signing; produces scaffolding A2A and ArtifactStore reuse | ✓ |
| One harness adapter end-to-end | Proves harness neutrality first, but pulls an external SDK in before any transport exists | |
| MCP-backed ArtifactStore | Clears the D-12 inherited deliverable against an already-pinned conformance suite | |

**User's choice:** MCP egress at L6

### Wave order

| Option | Description | Selected |
|--------|-------------|----------|
| Transport → trust → harness | MCP ingress + ArtifactStore; A2A + identity + admission; adapters; gate | ✓ |
| Harness early, transport late | Surfaces SDK surprises sooner, but skill exposure would be built against `local_callable` only | |
| By seam, across all three at once | Conceptually clean; nothing end-to-end until the final wave | |

**User's choice:** Transport → trust → harness

### MCP module shape

| Option | Description | Selected |
|--------|-------------|----------|
| One client lib, three role modules | Shared client per D-IMPL-13; egress / ArtifactStore / ingress separated per §7.1 | ✓ |
| Split client too, by edge | Per-edge trust typing, but reopens D-IMPL-13 | |
| You decide | Defer to research and planning | |

**User's choice:** One client lib, three role modules

### Code layout

| Option | Description | Selected |
|--------|-------------|----------|
| Protocols in /src, impls in /runtime | Matches §7.3 and the `runtime/ccf_runtime/cdc/` precedent | ✓ |
| Everything cross-process in /runtime | Cleaner separation, but inverts the dependency for `/src` skill dispatch | |
| You decide | Defer to research and planning | |

**User's choice:** Protocols in /src, impls in /runtime

### Remote skill dispatch timing

| Option | Description | Selected |
|--------|-------------|----------|
| Each type with its transport wave | `mcp` dispatch in the MCP wave, `a2a` in the A2A wave; every wave end-to-end | ✓ |
| All remote dispatch in one wave | Consistent, but leaves MCP and A2A waves without a working skill path | |
| Defer a2a dispatch to I.4 | Smaller scope, but likely breaks XPRC-02 and the example-04 fixture | |

**User's choice:** Each type with its transport wave

### Examples vs fixtures

| Option | Description | Selected |
|--------|-------------|----------|
| Test fixtures now, examples in I.5 | Follows the I.1→example-00 and I.2→example-01 precursor precedent | ✓ |
| Build examples 04 and 07 here | Front-loads Phase 8, risks domain/style mismatch with the other six | |
| You decide | Per-wave judgement | |

**User's choice:** Test fixtures now, examples in I.5

### Adapter staging

| Option | Description | Selected |
|--------|-------------|----------|
| One deep, then two against the suite | Claude Agent SDK first to harden the Protocol; matches the D-10 Phase F staging note | ✓ |
| All three in parallel | Fastest, but the Protocol would be designed against a guess | |
| Two mandatory, LangGraph last | Reflects the pre-ruling recommendation; D-IMPL-24 made all three equally v0 | |

**User's choice:** One deep, then two against the suite

---

## Harness dependency & test posture

### Dependency status

**First pass — user asked for clarification** rather than selecting: *"want to
make sure it is easy to install and run all three harnesses. Is this option 2
or 1"*. Clarified that extras compose — per-harness extras and a
one-command aggregate are not mutually exclusive — and that the real
distinction is whether "run an adapter" and "develop the SDK" are the same
dependency group. Re-asked with the composed shape.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-harness + [harnesses] + dev | Three per-harness extras, an aggregate installing all three, `dev` including it | ✓ |
| Aggregate only — [harnesses] | Simplest, but a LangGraph-only deployment installs all three | |
| You decide | Defer naming and composition | |

**User's choice:** Per-harness + [harnesses] + dev
**Notes:** Ease of installing and running all three was raised by the user
unprompted and became a stated requirement (CONTEXT D-08), not merely a
preference. It is the reason the aggregate extra exists.

### Adapter test strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Shared conformance suite, run real | Factory-parametrized suite against all three real SDKs, no LLM calls | ✓ |
| Doubles in CI, real SDKs in a smoke leg | Fast and hermetic, but a double can pass while the real SDK disagrees | |
| Real SDKs including live model calls | Highest fidelity; adds keys, cost, nondeterminism, and tests the harness's own loop | |

**User's choice:** Shared conformance suite, run real

### Missing-SDK behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Skip with a named reason | `importorskip` + per-harness marker; the I.1 named-skip precedent | |
| Hard fail if any harness is missing | No false greens, but blocks local work on unrelated modules | |
| You decide | Planning chooses the mechanism | ✓ |

**User's choice:** You decide
**Notes:** Recorded in CONTEXT under Claude's Discretion with a binding
constraint — a skipped harness leg must be visible and self-explaining,
naming which harness and which extra enables it.

### `effects: unsupported` verification

| Option | Description | Selected |
|--------|-------------|----------|
| Declared + proven inert | Typed declaration *and* a driven effect path asserting nothing reached the graph | ✓ |
| Declaration is sufficient | Simpler; an adapter could declare `unsupported` and still leak effects | |
| You decide | Derive from D-IMPL-25 wording | |

**User's choice:** Declared + proven inert

---

## A2A wire implementation risk

### Build order

| Option | Description | Selected |
|--------|-------------|----------|
| Typed-HTTP first, then LF A2A | De-risks the emergent standard; proves `WireProtocol` early | ✓ |
| LF A2A first, as ruled | Honors D-IMPL-14's ordering literally; front-loads the largest unknown | |
| Only LF A2A in v0 | Contradicts D-IMPL-14; no escape hatch | |

**User's choice:** Typed-HTTP first, then LF A2A
**Notes:** Explicitly recorded as **sequencing within D-IMPL-14, not a
revision of it** — LF A2A remains the ruled v0 default. Same framing as the
D-10 LangGraph staging note at `D-GATE-F`.

### Admission verification placement

| Option | Description | Selected |
|--------|-------------|----------|
| Control Plane gate ahead of L2 | Single-writer carries the guarantee structurally; wires never hold a path to L2 | ✓ |
| Inside each WireProtocol implementation | Close to the wire, but duplicated per transport — the IN-01 drift pattern | |
| You decide | Derive from §7.2 and D-IMPL-16 | |

**User's choice:** Control Plane gate ahead of L2

### Identity and signing scope

| Option | Description | Selected |
|--------|-------------|----------|
| Real JWS, dev-grade key management | Genuine crypto behind `IdentityProvider`; custody is deployment infra | ✓ |
| Protocol + stub, real crypto in I.4 | Smaller, but an admission gate verifying nothing cannot demonstrate criterion 2 | |
| Full mTLS transport security too | Most complete; largely deployment topology with little invariant payoff | |

**User's choice:** Real JWS, dev-grade key management

### Lineage set-union pinning

| Option | Description | Selected |
|--------|-------------|----------|
| Property test on the union law | Hypothesis over generated pairs; extends existing I.1 machinery | ✓ |
| Fixture-based round-trip assertions | Concrete but pins chosen examples, not the law | |
| You decide | Planning chooses | |

**User's choice:** Property test on the union law

---

## Cross-process test topology

### Process topology

| Option | Description | Selected |
|--------|-------------|----------|
| Real subprocesses over loopback | Only topology where "two processes" is literally true; proves criterion 4 | ✓ |
| In-process transport doubles | Fast and deterministic, but single-writer becomes an assertion about structure | |
| testcontainers, as the Postgres leg does | Highest deployment fidelity; heavy for a process-boundary question | |

**User's choice:** Real subprocesses over loopback

### Flake containment

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral ports + readiness handshake | Port 0, child reports address, explicit probe, guaranteed teardown | ✓ |
| Fixed ports with retry-on-bind | Predictable addresses; retries mask rather than remove the race | |
| You decide | Planning handles lifecycle mechanics | |

**User's choice:** Ephemeral ports + readiness handshake
**Notes:** "No sleeps for readiness" recorded as a prohibition, not a preference.

### MCP topology reuse

| Option | Description | Selected |
|--------|-------------|----------|
| Same harness, one shared fixture | Built during the slice, reused by every wave; discipline written once | ✓ |
| MCP in-process, A2A subprocess | Faster majority path, but weakens example 07's deployment-level claim | |
| You decide | Per-surface decision | |

**User's choice:** Same harness, one shared fixture

### Portability equivalence definition

| Option | Description | Selected |
|--------|-------------|----------|
| Equal on governed fields, harness-specific isolated | Exact equality on what CCF governs; model/trace/token fields excluded | ✓ |
| Full record equality | Strongest claim; three SDKs legitimately differ on model version and trace shape | |
| You decide | Planning defines the relation | |

**User's choice:** Equal on governed fields, harness-specific isolated

---

## Claude's Discretion

- **Harness skip mechanism** when an SDK is absent — constrained: a skipped
  leg must be visible and name which harness and which extra enables it.
- Module tree details below the D-03 (MCP roles) and D-04 (Protocol/impl
  split) boundaries.
- Exact extra names and composition mechanics, subject to D-08's
  one-command requirement.

## Deferred Ideas

- MCP client ingress normalization detail (MCP responses → `SignalEnvelope`);
  ArtifactStore MCP resource contract shape under D-IMPL-26; A2A trust-policy
  artifact declaration. Offered as further gray areas; user judged the
  captured set sufficient. Researcher territory, not blocked.
- Full mTLS channel security — named by D-IMPL-15, scoped out of v0 by D-13.
- PKI/HSM key custody — an implementation behind `IdentityProvider`, not a
  redesign.
- LangGraph as an *orchestrator* — distinct `OrchestrationProtocol`
  integration per D-IMPL-17; Phase 7 scope, not to be conflated with the
  LangGraph harness adapter built here.
