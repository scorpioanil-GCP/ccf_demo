# Phase 17: Client Access — `ccf.client` and the Transport-Agnostic First Example - Context

**Gathered:** 2026-08-15
**Status:** Ready for planning
**Source:** PRD Express Path (`docs/superpowers/specs/2026-08-15-ccf-client-design.md`)

> **Every decision below is already ruled.** The spec was brainstormed with Dave
> and approved section by section on 2026-08-15. Planning **sequences** these
> decisions; it does not re-open them. A planner that re-litigates a `D-NN` below
> is drifting — the open sequencing questions are in `<deferred>`, and those are
> the only genuinely open items.

<domain>
## Phase Boundary

**In scope — the client role only.** CCF owns the client abstraction and the
result contract. Transports are official adapters that all return the same
`Result` shape. The producer side stays completely invisible to the client.

Ship, in this order:

1. `ccf.client` — the `ProductClient`, the `Result` contract, the error
   taxonomy, the `TransportAdapter` Protocol. **This is the product.**
2. The in-process adapter — the degenerate wire, proving the seam.
3. The adapter conformance suite — the CI parity gate.
4. The first example — a pure client `consume.py` beside an opaque
   `deployment/` directory.
5. The MCP adapter — second, against the already-frozen `Result` contract.

**Out of scope for this phase.** Examples for *constructing* context products
(the producer role) are a separate, later body of work with a different
audience — Dave's explicit ruling at section-3 approval. HTTP and A2A adapters
come after the contract freezes under in-process + MCP. See `<deferred>` for
the full not-list.

**Why this phase exists.** Phase 16's first example was rejected: 722 lines of
Python, with `consume.py` importing the producer's `deployment.MANIFEST` — the
consumer held a path to the producer's Control Plane config. Dave's verdict:
*"seasoned developers such as myself would not want to go near this thing with
a 10 foot pole."* The full post-mortem is `.planning/HANDOFF-2026-08-15.md`.
The SDK itself (3305 passing tests) was never the problem and is not being
rebuilt.

</domain>

<decisions>
## Implementation Decisions

### Core position and ownership

- **D-01** — CCF owns the client abstraction and the result contract.
  Transports are official adapters (in-process, MCP, later HTTP/A2A). A
  Context Product is valuable because of the contract it returns — typed
  payload + measured debt + content address + lineage + replay reference +
  explicit refusal — and if every transport re-implements that contract
  differently, the value evaporates.
- **D-02** — The producer side is completely invisible to the client. No
  client knows about `ccf_config.yaml`, manifests, boot sequences, or artifact
  keys; no client imports anything from the producer side of an example.

### The client surface

- **D-03** — The public surface is **exactly four exported names**:
  `ProductClient`, `Result` (carrying its `Refusal`), `TransportError`,
  `BindingError`. No manifest types, no Control Plane types, no deployment
  types cross this boundary.
- **D-04** — The API is `ProductClient.for_product(product_id, binding=None)`
  and `client.ask(parameters, as_of=None)`. `as_of=None` means "use the
  server's decision instant"; the exact rule is documented on `ask()`.
- **D-05** — Binding resolution is deliberately minimal for v0: explicit
  `binding=` kwarg wins, else the `CCF_BINDING` env var (a scheme-prefixed
  address: `inprocess:./deployment`, later `mcp+stdio:…`, `http://…`), else
  `BindingError` with a refusal-quality message naming exactly what to set.
  **No bindings file, no per-product env-var naming, no discovery chain in
  v0** — a resolution chain is how 722-line examples happen.
- **D-06** — The scheme prefix is the only place transport is named in the
  client's world, and it lives in the environment, not in code. The scheme
  registry is a plain dict inside `ccf.client`; third-party schemes become an
  extension point when someone real asks.

### Result contract and refusal semantics

- **D-07** — **Refusal is a value, not an exception.** A refusal is the fabric
  *working* — the gates ran and the governed answer was "no, and here is why."
  `Result` carries either the answer or the refusal; the contract spoke in both
  cases. Callers branch on `result.refused`.
- **D-08** — **Fail-closed guard.** Accessing any post-assembly field on a
  refused result **raises** — never returns `None`. Guarded fields: `payload`,
  measured `debt`, `content_address`, `replay_ref`, post-assembly `lineage`,
  `expires_at`. Silent `None` is how refusals become empty answers downstream.
  The exception does not fire when the fabric says no; it fires when the caller
  ignores the fabric saying no.
- **D-09** — A refused `Result` still carries everything that existed **before**
  assembly, so the "no" stays auditable: `refused: True`, `refusal.reason`,
  `refusal.key`, the refused request identity (product id, parameters,
  temporal boundary), and any pre-assembly lineage. The assembly boundary is
  the rule that decides which fields survive.
- **D-10** — Exceptions are reserved for the wire failing (`TransportError`:
  connection, timeout, auth) and for caller negligence (D-08).
  `BindingError` subclasses `TransportError`, so `except TransportError`
  remains the one catch-all for "the wire never spoke."
- **Accepted trade-off, recorded so nobody re-derives it:** a single `Result`
  type means mypy cannot statically prove the caller checked; the guard is
  runtime-only. This is the right trade for a client SDK whose first audience
  is a reader.

### The adapter seam

- **D-11** — One Protocol, one method: `TransportAdapter.ask(WireRequest) ->
  WireOutcome`. `WireRequest` carries product id, parameters, temporal
  boundary. `WireOutcome` is the canonical serialized form of either a served
  product or a refusal. **Transport failure never has a `WireOutcome`** — the
  adapter raises `TransportError`.
- **D-12** — **`Result` is constructed in exactly one place**: a single decoder
  inside `ProductClient`. Adapters never build `Result`s. Shape identity across
  transports is therefore a code path adapters cannot avoid, not a convention
  they follow.
- **D-13** — **The in-process adapter round-trips through the same codec**
  (explicitly ruled yes). It serializes live objects to the canonical wire form
  and hands the client the same bytes-shaped thing an HTTP body would contain.
  In-process becomes a true degenerate wire rather than a privileged fast path;
  a parity bug has exactly one place to live; and the adapter is *physically*
  prevented from leaking live producer-side objects across the seam. Cost: a
  microsecond of serialization.
- **D-14** — `ccf.client` lives in `src/ccf/client/`. The in-process adapter
  imports only core boot/deployment machinery. Existing harness-import and
  `@algorithmic` lints apply unchanged.

### Parity — enforced, not asserted

- **D-15** — One shared **adapter conformance suite**, written once and
  parameterized over adapters, asserting: (a) same question + same instant →
  identical `Result` fields and **identical content address** across adapters;
  (b) same refusal → identical `refused`/`reason`/`key`/request identity;
  (c) the D-08 guard holds on every adapter; (d) wire failure never
  masquerades as refusal. **An adapter is official when it passes.** The MCP
  adapter ships on passing the suite, not on demoing.

### The first example

- **D-16** — **Lazy boot behind the adapter.** The binding names a deployment
  root; the in-process adapter boots the fabric on first `ask()`, invisibly.
  The developer types one command. No client call may trigger producer
  *provisioning* semantics — boot-from-deployment-definition is the adapter's
  job and is not that.
- **D-17** — The example is `consume.py` + an opaque `deployment/` dir +
  a README. `consume.py` is the entire example a reader studies: it knows the
  product identity and the question parameters, imports `ccf.client` and stdlib
  only, and prints the answer followed by what a `SELECT` would not have told
  you (debt, content address, replay record), with governance detail behind
  `--explain`. `deployment/` uses the single-file `ccf_config.yaml` authoring
  form (`D-IMPL-136` + amendment).
- **D-18** — The README's documented command passes a **fixed `--as-of`** so
  printed debt and content address reproduce exactly, and the make target runs
  that documented command **verbatim** — no parameter smuggling through make
  (the s1-00 ruling).
- **D-19** — **Two CI gates carry the Phase 16 lesson** that a measurement
  nobody is looking at protects nothing: (a) a **purity gate** — an AST check
  that `consume.py` imports only `ccf.client` + stdlib, a property rather than
  a filename list; (b) a **budget gate** — reader-visible Python in the example
  stays within its declared budget (`consume.py` ≤ 80 lines). The 722-line
  failure mode becomes a red CI check, not a retrospective.

### Testing

- **D-20** — Codec property tests: `decode(encode(x)) == x` for served products
  and refusals. The codec is the single point of parity failure, so it gets the
  densest tests.
- **D-21** — Binding-resolution tests: kwarg beats env; malformed or missing
  binding raises `BindingError` whose message names exactly what to set.
- **D-22** — **Sabotage discipline.** Every parity and guard assertion is
  verified to *fail* when its property is deliberately broken. This project's
  ledgers are unambiguous: defects land in verification code, not mechanism.
- **D-23** — The existing property "two thresholds → two content addresses" is
  re-asserted through the new client seam.

### Posture

- **D-24** — **Sync-only v0.** One `ask()`. Async doubles the exported surface
  and the first audience is a reader. Concrete revisit trigger: the MCP adapter
  (MCP client libraries are async-native; the adapter bridges internally, and
  the async question is decided then). The `Result` contract is unaffected
  either way.

### Inherited consequences this phase must discharge

- **D-25** — The Phase 16 **example-shape** rulings are suspended (spec §11):
  `D-11` of 16-CONTEXT, `D-IMPL-125`, the file-shape aspect of `D-IMPL-127`,
  `D-IMPL-131`, `D-IMPL-139`(a). The producer/consumer **separation** itself —
  the substance of `D-IMPL-127` — is *strengthened*, now enforced by the purity
  gate (D-19) and the codec seam (D-13) rather than by file layout. SDK rulings
  `D-IMPL-132`, `D-IMPL-136` + amendment, `D-IMPL-137`, `D-IMPL-138` **stand**.
- **D-26** — `tests/examples/test_spine_separation.py` enforces the suspended
  shape and **must be re-scoped or retired** before it refuses the new
  examples. It currently passes; it will not pass a Phase 17 example.
- **D-27** — The condemned example trees (`examples/s1-00-*`, `s1-01-*`,
  `00`–`08`) are removed or quarantined early in the phase, with every gate,
  make target, CI job, and published snippet that references them handled in
  the same change — there is no partial state.

### Amendment 1 rulings (Dave, 2026-08-15, post-research)

Research measured the tree and found that two of spec §12's "sequencing" items
were really design gaps. Dave ruled all four. Full text: spec **Amendment 1**.

- **D-28 — The canonical refusal envelope is defined in `src/` first, before
  any door changes.** There is nothing for a door to emit until the shape
  exists. Two derived constraints: (a) it carries every existing refusal kind
  **without flattening** — request-level reasons, the `GateRefusal` family,
  `PayloadSchemaViolation`, `MixingRefusal` and siblings; losing *which kind*
  a refusal was makes `Result.refusal.reason` mush and kills D-09's auditable
  refusal at the seam; (b) it carries the pre-assembly request identity
  (product id, parameters, temporal boundary). Rollout: in-process now; **the
  MCP door is fixed to produce it in this phase** (an MCP adapter that cannot
  carry a refusal cannot pass D-15); HTTP follows its adapter. `Result` and
  `Refusal` (D-07..D-10) are unchanged — this is only how the information
  crosses the seam.
- **D-29 — The resolver Protocol AND its reference implementation both live
  in `src/`.** No `src → runtime` import, no documented exception, D-14
  survives as written. This is implementable because the composition touches
  nothing outside `src/`: `run_gates` is `src/ccf/products/gates.py`, `serve`
  is `src/ccf/replay/serve.py`, and the rejected `produce.py::assemble_and_serve`
  imports only from `ccf`. Consequence: assemble → gate → serve stops being
  every deployment's problem — the SDK ships the parts today but never the
  composition, which is why the rejected example wrote 357 lines of it in
  front of a reader who wanted to ask one question. **Hard constraint:** the
  composition is pure mechanism; thresholds, product classes and policy stay
  in Control Plane artifacts, or the No-Hardcoding Rule is firing.
- **D-30 — The in-process adapter caches the booted fabric per binding
  address.** Not performance: a second `load_and_boot` against the same graph
  raises `SingleWriterViolation`, so caching is what makes a second `ask()`
  legal at all. Cache lifetime, `close()`, and two-clients-one-binding are
  planning's to resolve.
- **D-31 — The retirement inventory and its sweep machinery are repaired
  FIRST**, before any example-tree removal lands — not merely in parallel.
  Two of the three failing `tools/` tests *are* that machinery, and
  `RETIREMENT-COUPLINGS.md` is 85 rows stale (163 committed vs 248 live). An
  untrustworthy inventory is how a partial retirement ships, which is the
  failure D-27's no-partial-state rule exists to prevent.

### Claude's Discretion

These are sequencing and mechanism choices the spec deliberately left to
planning. Decide them with a measurement, not a preference:

- Plan/wave decomposition and how many plans the five deliverables become.
- The exact module layout inside `src/ccf/client/` (file boundaries, where the
  decoder lives, how the scheme registry is expressed).
- Concrete `WireRequest` / `WireOutcome` field names and types — subject to
  the freeze constraint in `<deferred>` item 4.
- The form of the demo data inside `deployment/` (pre-seeded store vs
  boot-consumed seed artifact), subject to D-16.
- Whether the condemned trees are deleted or quarantined, and in which plan.
- Requirement IDs: this phase **mints its own** (the ROADMAP entry says so
  explicitly). Choose a prefix consistent with the project's existing scheme
  (`DOCS-`, `ERGO-`, `EXAM-`, `HARD-`, `PERF-` are taken; something like
  `CLNT-01..NN` fits the client surface).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The design being implemented
- `docs/superpowers/specs/2026-08-15-ccf-client-design.md` — **authoritative.**
  Every `D-NN` above is derived from it. Sections: 2 client surface, 3 binding,
  4 Result/refusal, 5 adapter seam, 6 parity suite, 7 first example, 8 testing,
  9 sync posture, 10 not-list, 11 ruling consequences, 12 open sequencing items.
- `.planning/HANDOFF-2026-08-15.md` — why Phase 16's example was rejected, what
  survives from it, and the standing operational hazards (state-writer
  corruption, `grep` shim, `examples/` not typechecked, venv python path).

### Project law
- `CLAUDE.md` (revision 4) — mission, the five pillars, the No-Hardcoding Rule
  (§6.4), harness neutrality (§7.3), phase review protocol (§3.1), working
  principles (§11).
- `docs/DECISIONS.md` — the `D-IMPL-NN` log. `D-IMPL-132`, `-136` + amendment,
  `-137`, `-138` stand; the shape rulings named in D-25 are suspended.
- `docs/CCF_Whitepaper_1-2.md` — §6.3 (Context Product Contract, nine
  elements), §7.6 (delivery + validation gates), §7.10 (Decision Replay).

### The surface being wrapped (read before designing `WireOutcome`)
- `src/ccf/products/contract.py` — `ContextProductContract`, the served vessel.
- `src/ccf/products/request.py` — `ProductRequestViolation`, `refuse_request`,
  the existing refusal vocabulary (`missing-required-parameter`, etc.).
- `src/ccf/products/bind.py` — request→product binding.
- `runtime/ccf_runtime/mcp/egress.py` — what MCP egress serializes today.
- `runtime/ccf_runtime/mcp/experience.py` — the external front door.
- `runtime/ccf_runtime/http_api/routes/product.py` — what HTTP emits today.
- `runtime/ccf_runtime/authz/product_entitlement.py` — the entitlement seam
  the client surface deliberately does not expose in v0.
- `src/ccf/boot.py` and `src/ccf/deployment/` — what lazy boot must drive.
- `src/ccf/contracts/canonical.py` — `content_hash`, the canonical serializer
  the codec must not contradict.

### The gates and examples being changed
- `tests/examples/test_spine_separation.py` — D-26's subject.
- `examples/s1-00-companies-over-revenue/` — the rejected example; its
  `consume.py` is the anti-pattern, its `ccf_config.yaml` is the keeper.
- `docs/superpowers/specs/` — where this phase's own spec lives.

</canonical_refs>

<specifics>
## Specific Ideas

**The target client file** (Dave's strawman, adapted to D-07's
refusal-as-state). This is the artifact the phase exists to produce:

```python
from ccf.client import ProductClient

client = ProductClient.for_product("hw1.companies-over-revenue")

result = client.ask(
    parameters={"revenue_threshold": args.min_revenue},
    as_of=datetime.fromisoformat(args.as_of) if args.as_of else None,
)

if result.refused:
    print(f"refused: {result.refusal.reason} — {result.refusal.key}")
    return 1

print(f"\nQ: which companies have revenue over {result.payload['threshold']}?")
...
print(f"   context debt D_c   {result.debt.debt:.4f}  →  {result.debt.signal.value}")
print(f"   content address    {result.content_address}")
print(f"   replay record      {result.replay_ref}")
```

**The run experience** — one command, and the transport is an ops detail:

```
$ export CCF_BINDING="inprocess:./deployment"
$ python consume.py --min-revenue 1000000
```

**The portability claim, made testable:** same `consume.py`, different
`CCF_BINDING`, identical `Result`. That property is what the conformance suite
(D-15) mechanizes, and it is the client-side form of the harness-neutrality
argument CLAUDE.md §7.3 makes for adapters.

</specifics>

<deferred>
## Deferred Ideas

**The not-list — explicitly out of `ccf.client` v0** (spec §10):

| Not shipping | Why / where it lives instead |
|---|---|
| Bindings file, per-product env vars | Future work, triggered by a second product |
| HTTP / A2A adapters | After the contract freezes under in-process + MCP |
| Client-side caching, TTL auto-refresh | Caller's choice; `expires_at` is in the Result |
| Retry / backoff | `TransportError` surfaces immediately; retries are ops policy |
| Auth / credential machinery | Transport-level, carried by the binding's world |
| Contract-level principal/entitlement at the client seam | Deferred to MCP adapter work; `D-IMPL-129` lives in this neighborhood |
| Streaming / pagination | No use case in evidence |
| Producer-side construction examples | A later body of work, different audience |

**Open sequencing questions for planning** (spec §12 — these are *not* design
gaps; each has a constraint attached):

*Updated after research + Amendment 1. Two of these were design gaps, not
sequencing; those are now ruled (D-28..D-31) and have left this list.*

1. **Form of the demo data inside `deployment/` — STILL OPEN, and sharper than
   originally stated.** `ccf_config.yaml` cannot carry a `signal_batch` (an
   explicit decision at `src/ccf/deployment/config.py:82-91`) and
   `load_and_boot` does not ingest, so **D-17's single-file requirement and
   "boot-consumed seed artifact" are mutually exclusive as the tree stands.**
   Four options with measured costs: `17-RESEARCH.md` §4.6. Constraints: D-17
   mandates the single-file form; D-16 forbids provisioning inside a client
   call. **Resolve before the example plan is written** — option (d) would
   need a new `D-IMPL-140+` ruling.
2. Disposition of the condemned example trees — governed by **D-31**: repair
   the sweep machinery first, then remove or quarantine with no partial state
   (D-27). *Sequencing only; the ordering is ruled.*
3. MCP adapter specifics (stdio vs HTTP transport, tool shape) — designed when
   reached, against the frozen contract and the conformance suite. **Plus a
   measured blocker:** the shipped egress tool hard-wires `parameters={}`
   (`egress.py:588`), so a class with any required parameter is unreachable
   over MCP. Deliverable 5 cannot pass D-15 conformance or D-23's
   two-thresholds property without that fix (`16-26` / `D-IMPL-133`).
4. **Exact `WireOutcome` schema — HALF-ANSWERED.** The **served** half is a
   transcription: all doors emit `canonical_bytes(product)` and nothing else,
   with one documented transport-level divergence. Freeze it. The **refusal**
   half, `replay_ref`, and the echoed request identity reach no wire at any
   door — that is new design surface governed by **D-28**, and planning must
   allocate design budget for it rather than treating it as a naming exercise.

**Also open, and it is a planning decision rather than a design one:** the
example's directory name and entry-file name interact with four existing
gates. `hw1-*` makes the example *invisible* to `test_spine_separation.py`
and `test_section_one_is_agent_free.py` (they glob `s1-*`); `s1-*` makes it
*refused* by both. `consume.py` rather than `run.py` means
`test_artifact_schema_headers.py` does not recognise the example as an example
root (`EXAMPLE_ROOT_MARKER = "run.py"`). D-26 requires the gates be handled
either way; D-27 forbids partial state. See `17-RESEARCH.md` §5.1–§5.3.

**Neighboring open items, explicitly not gating this phase:** `D-IMPL-129`
(`invoke_agent` dispatches a skill with authentication and no entitlement,
pinned by a test that fails the day someone fixes it), and Phase 16's `16-26`
(client parameters on both doors, `D-IMPL-133`).

</deferred>

---

*Phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex*
*Context gathered: 2026-08-15 via PRD Express Path from the approved design spec*
