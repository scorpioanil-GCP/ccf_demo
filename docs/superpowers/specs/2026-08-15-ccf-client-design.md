# `ccf.client` — Transport-Agnostic Client Access to Context Products

- **Date:** 2026-08-15
- **Status:** Approved by Dave (brainstorming sections 1–3, this session)
- **Scope:** the client experience only. Examples for *constructing* context
  products are a separate, later effort with a different audience; this design
  deliberately does not speak for that role.
- **Feeds:** Phase 17 (opened through GSD with this document as authoritative
  input).

---

## 1. Core position (Dave's, verbatim in substance)

A Context Product is valuable because of the contract it returns — typed
payload + measured debt + content address + lineage + replay reference +
explicit refusal. If every transport re-implements that contract differently,
the value evaporates. Therefore:

- **CCF owns the client abstraction and the result contract.**
- **Transports are official adapters** — in-process first, MCP second, HTTP
  and A2A later — and every one of them returns the same result shape.
- **The producer side stays completely invisible to the client.** No client
  ever knows about `ccf_config.yaml`, manifests, boot sequences, or artifact
  keys, and no client imports anything from the producer side of an example.

Priority order: (1) in-process — simplest possible first example, proves the
client/producer separation; (2) MCP — highest adoption leverage; (3) HTTP —
thin wrapper later; (4) A2A and others — only after the client contract is
stable.

Outside CCF: how an organisation deploys and scales (containers, auth,
service mesh), and agent frameworks that sit on top of the MCP adapter.

## 2. The client surface

The entire API a client developer ever learns:

```python
from ccf.client import ProductClient

client = ProductClient.for_product("hw1.companies-over-revenue")

result = client.ask(
    parameters={"revenue_threshold": 1_000_000},
    as_of=None,   # optional instant; None means "the server's decision instant"
)

if result.refused:
    log(result.refusal.reason, result.refusal.key)
else:
    use(result.payload)   # + result.debt, .content_address, .replay_ref, .lineage
```

**Exports — exactly four names:** `ProductClient`, `Result` (with its
`Refusal`), `TransportError`, `BindingError`. No manifest types, no Control
Plane types, no deployment types cross this boundary.

`as_of=None` means "use the server's decision instant"; the exact rule is
documented on `ask()`. The first example's documented command passes a fixed
`--as-of` so printed debt and content address reproduce exactly — but the API
default stays `None`.

## 3. Binding resolution

`for_product(product_id, binding=None)` resolves *where*, never *how*:

1. explicit `binding=` kwarg wins;
2. else env var **`CCF_BINDING`** — a scheme-prefixed address string:
   `"inprocess:./deployment"`, later `"mcp+stdio:…"`, `"http://…"`;
3. else `BindingError` with a refusal-quality message naming exactly what to
   set.

The scheme prefix is the only place transport is named in the client's world,
and it lives in the environment, not in code. Switching transports is an ops
action. "Same `consume.py`, different `CCF_BINDING`, identical `Result`" is a
testable property.

**Deliberately not built in v0** (triggered by a second product, not before):
bindings file, per-product env-var naming, discovery chains. The resolution
chain is how 722-line examples happen.

## 4. The `Result` contract and refusal semantics

**Refusal is a value; negligence is an exception; wire failure is an
exception.** A refusal is the fabric *working* — the gates ran and the
governed answer was "no, and here is why." So:

- `Result` carries either the answer or the refusal. The contract spoke in
  both cases.
- Exceptions are reserved for the wire failing (`TransportError`) and for
  caller negligence (reading a guarded field off a refused result).

### 4.1 Field split — the assembly boundary is the rule

A refused `Result` still exposes everything that existed **before** assembly:

- `refused: True`
- `refusal.reason` / `refusal.key` — the contract-level explanation
- the request identity that was refused: product id, parameters, temporal
  boundary
- any pre-assembly lineage/context that existed at the point of refusal

Everything that only exists **after** successful assembly is absent and
guarded:

- `payload`, measured `debt`, `content_address`, `replay_ref`, full
  post-assembly `lineage`, `expires_at`

### 4.2 Fail-closed guard

Accessing any post-assembly field on a refused result **raises** — never
returns `None`. Silent `None` is how refusals become empty answers
downstream. The inversion is deliberate: the exception does not fire when the
fabric says no; it fires when the caller ignores the fabric saying no.

**Accepted trade-off:** a single `Result` type means mypy cannot statically
prove the caller checked; the guard is runtime-only. Right trade for a client
SDK whose first audience is a reader.

## 5. The adapter seam

One Protocol, one method, one canonical outcome type:

```python
class TransportAdapter(Protocol):
    def ask(self, request: WireRequest) -> WireOutcome: ...
```

- `WireRequest` — product id, parameters, temporal boundary. Built by the
  client; adapters only carry it.
- `WireOutcome` — the canonical serialized form of either a served product or
  a refusal. This names the shape MCP egress and the HTTP routes already
  emit; it is not an invention.
- Transport failure never has a `WireOutcome` — the adapter raises
  `TransportError`.

**`Result` is constructed in exactly one place.** Adapters never build
`Result`s; a single decoder inside `ProductClient` turns `WireOutcome` into
`Result`. Shape identity across transports is a code path adapters cannot
avoid, not a convention they follow.

**The in-process adapter round-trips through the same codec** (ruled: yes).
It serializes the live objects to the canonical wire form and hands the
client the same bytes-shaped thing an HTTP body would contain. In-process is
a true degenerate wire, not a privileged fast path; all transports share one
decode path, so a parity bug has exactly one place to live; and the adapter
is physically prevented from leaking live producer-side objects across the
seam. Cost: a microsecond of serialization.

**Small print:**

- Scheme registry: a plain dict `{"inprocess": …, "mcp+stdio": …}` inside
  `ccf.client`. Mechanism, not values. Third-party schemes become an
  extension point when someone real asks.
- `BindingError` subclasses `TransportError`, so `except TransportError`
  remains the one catch-all for "the wire never spoke."
- Home: `src/ccf/client/`. The in-process adapter imports only core
  boot/deployment machinery; the existing harness-import and `@algorithmic`
  lints apply unchanged.

## 6. The parity invariant — enforced, not asserted

One shared **adapter conformance suite**, written once and parameterized over
adapters. An adapter is official when it passes; the MCP adapter ships when
it passes the suite, not when it demos.

| Property | Assertion |
|---|---|
| Same question, same instant | identical `Result` fields, **identical content address**, across all adapters |
| Same refusal | identical `refused` / `reason` / `key` / request identity, across all adapters |
| Guard | post-assembly fields on a refused result raise, on every adapter |
| Wire failure | never masquerades as refusal — kill the transport mid-suite, expect `TransportError` |

This suite is the CI enforcement of the "value evaporates" concern — the same
class of gate as the composition-preservation tests.

## 7. The first example

```
examples/hw1-companies-over-revenue/
├── consume.py        # the ENTIRE example a reader studies. Budget: ≤ 80 lines.
├── deployment/       # the producer's world, opaque to the reader:
│                     #   ccf_config.yaml (single-file form, D-IMPL-136 — survives)
│                     #   demo data in whatever form boot consumes
└── README.md         # run it, read it, what to change first
```

Run experience (lazy boot behind the adapter — ruled):

```
$ export CCF_BINDING="inprocess:./deployment"
$ python consume.py --min-revenue 1000000
```

The developer types one command. The adapter boots the fabric on first
`ask()`, invisibly, from the deployment root the binding names. The client
holds an opaque address string and nothing else. The README's documented
command passes a fixed `--as-of` for reproducible output, and the make target
runs that documented command **verbatim** — no parameter smuggling through
make (per the s1-00 ruling).

`consume.py` is Dave's strawman adapted to `Result`-with-refusal-state: knows
the product identity and the question parameters; imports `ccf.client` and
stdlib only; prints the answer and then what a `SELECT` would not have told
you (debt, content address, replay record), with governance detail behind
`--explain`.

### 7.1 Gates — institutional memory as CI

*A measurement nobody is looking at protects nothing* (Phase 16). Two gates:

1. **Purity gate** (property, not filename): AST-check that `consume.py`
   imports only `ccf.client` + stdlib. Zero producer imports, enforced
   forever.
2. **Budget gate**: reader-visible Python in the example ≤ its declared
   budget (`consume.py` ≤ 80 lines). The 722-line failure mode becomes a red
   CI check, not a retrospective.

## 8. Testing strategy (beyond the parity suite)

- **Codec property tests** — `decode(encode(x)) == x` for served products and
  refusals. The codec is the single point of parity failure; it gets the
  densest tests.
- **Binding resolution** — kwarg beats env; malformed/missing →
  `BindingError` whose message names what to set.
- **Sabotage discipline** — every parity/guard assertion is verified to
  *fail* when its property is deliberately broken. This project's ledgers are
  unambiguous: defects land in verification code, not mechanism.
- **Existing property, new path** — two thresholds → two content addresses,
  now asserted through the client seam.

## 9. Sync/async posture

**Sync-only v0.** One `ask()`. Async doubles the exported surface and the
first audience is a reader. Concrete revisit trigger: the MCP adapter (MCP
client libraries are async-native; the adapter bridges internally, and we
decide then whether a real consumer justifies an async client). The `Result`
contract is unaffected either way.

## 10. Not-list — explicitly out of `ccf.client` v0

| Not shipping | Why / where it lives instead |
|---|---|
| Bindings file, per-product env vars | Future work, triggered by a second product |
| HTTP / A2A adapters | After the contract freezes under in-process + MCP |
| Client-side caching, TTL auto-refresh | Caller's choice; `expires_at` is in the Result |
| Retry / backoff | `TransportError` surfaces immediately; retries are ops policy |
| Auth/credential machinery | Transport-level, carried by the binding's world; org concern |
| Contract-level principal/entitlement at the client seam | Deferred to MCP adapter work; open item D-IMPL-129 lives in this neighborhood |
| Streaming / pagination | No use case in evidence |

## 11. Consequences for standing rulings and gates

- **Example-shape rulings** from the Phase 16 stack (`D-11` phase-16 CONTEXT,
  `D-IMPL-125`, `D-IMPL-127`'s file-shape aspect, `D-IMPL-131`,
  `D-IMPL-139`(a)) are **suspended for Phase 17 examples** by Dave's approval
  of this design. The producer/consumer *separation* itself — the substance
  of `D-IMPL-127` — is strengthened, not dropped: it is now enforced by the
  purity gate and the codec seam rather than by file layout.
- **SDK rulings stand:** `D-IMPL-132` (operators aid assembly),
  `D-IMPL-136` + amendment (single-file `ccf_config.yaml` — the deployment
  dir in §7 uses it), `D-IMPL-137`, `D-IMPL-138`.
- **`tests/examples/test_spine_separation.py`** enforces the suspended `D-11`
  shape and must be re-scoped or retired for Phase 17 examples, or it will
  refuse them.
- Phase 16's 14 remaining documentation plans (`16-07`…`16-20`) documented
  the rejected surface and stay stopped.

## 12. Open items for Phase 17 planning (not design gaps — sequencing)

1. Form of the demo data inside `deployment/` (pre-seeded store vs
   boot-consumed seed artifact) — either satisfies §7; pick during planning.
   Constraint: no client call may trigger producer *provisioning* semantics;
   boot-from-deployment-definition is the adapter's job and is not that.
2. Disposition of the condemned example trees (`s1-00`, `s1-01`, `00`–`08`)
   now present on this branch — remove or quarantine early in Phase 17.
3. MCP adapter specifics (stdio vs HTTP transport, tool shape) — designed
   when reached, against the frozen contract and the conformance suite.
4. Exact `WireOutcome` schema — name and freeze the shape MCP egress / HTTP
   routes already emit; divergences found there are defects to fix, not
   shapes to standardize around.

---

# Amendment 1 — 2026-08-15 (post-research)

**Status:** ruled by Dave, 2026-08-15, after Phase 17 research
(`.planning/phases/17-*/17-RESEARCH.md`).
**Effect:** this amendment is part of the approved design. Where it speaks,
it governs; §§1–11 above are otherwise unchanged.

## Why this amendment exists

§12 framed four items as *sequencing* questions. Research measured the tree
and found that two of them are **design gaps**, not sequencing — the spec
assumed surfaces that do not exist. Rather than let planning discover this,
the gaps are closed here.

What research measured, and what it changed:

| Measured | Consequence |
|---|---|
| For a **served** product, all doors emit `canonical_bytes(product)` and nothing else — one documented transport-level divergence | §12.4's "freeze what exists" holds for this half. Unchanged. |
| For a **refusal**, no door emits anything. The resolver seam is typed `-> ServableProduct` with no refusal in the union; every fabric refusal type reaches no wire. `replay_ref` and the request's `parameters` likewise reach no wire | §12.4 does **not** hold for this half. It is new design surface → **A** below. |
| No `src/`-resident seam yields a gate-admitted product; zero `src` modules import `ccf_runtime` | The spec's §5 seam had no implementable path → **B** below. |
| A second `load_and_boot` against the same graph raises `SingleWriterViolation` | Boot caching is **required**, not an optimization → **C** below. |
| Three `tools/` tests fail today; two are the retirement-sweep machinery, and `RETIREMENT-COUPLINGS.md` is 85 rows stale | The §12.2 retirement inventory cannot be trusted until fixed → **D** below. |

## A — The canonical refusal envelope

**Ruled:** define **one canonical refusal envelope in `src/`**, beside the
served-product serialization, *before* any door is changed. There is nothing
for a door to emit until the shape exists.

Two constraints on the envelope, both derived from what the fabric already
produces rather than invented:

1. **It carries every existing refusal kind without flattening** — the
   request-level reasons, the `GateRefusal` family, `PayloadSchemaViolation`,
   `MixingRefusal`, and any sibling. If the envelope loses *which kind* a
   refusal was, `Result.refusal.reason` becomes mush and §4's
   auditable-refusal guarantee dies at the seam.
2. **It carries the pre-assembly request identity** — product id, parameters,
   temporal boundary — per §4.1's field split. This is also why `replay_ref`
   and `parameters` reaching no wire today is a **defect to fix**, not a
   separate feature request.

**Rollout:** in-process produces the envelope in this phase. **The MCP door is
fixed to produce it in this phase**, as part of deliverable 5 — an MCP adapter
that cannot carry a refusal cannot pass the §6 conformance suite. HTTP follows
when its adapter lands (§10 not-list, unchanged).

`Result` / `Refusal` as approved in §4 are **unchanged**. This amendment
concerns only how that information crosses the seam.

## B — The resolver seam: Protocol *and* reference implementation, both in `src/`

**Ruled:** `ccf.client` reaches a gate-admitted product through a narrow
**resolver Protocol declared in `src/`**, and the SDK ships its **reference
implementation in `src/` as well**.

This is implementable with no new boundary crossing because the composition
touches nothing outside `src/`: `run_gates` is `src/ccf/products/gates.py`,
`serve` is `src/ccf/replay/serve.py`, and the rejected example's 357-line
`produce.py::assemble_and_serve` imports **only** from `ccf` — zero
`ccf_runtime` imports.

Consequences, all of them load-bearing:

- **The `src ↛ runtime` boundary stays intact and CI-enforceable.** No
  exception is documented, because none is needed. §5's "in-process adapter
  imports only core boot/deployment machinery" (D-14) survives as written.
- **`ccf.client` gets its seam** — the in-process adapter boots the deployment
  and calls the resolver.
- **Assemble → gate → serve stops being every deployment's problem.** The SDK
  ships all the *parts* of that composition today but never the composition,
  which is why the rejected example had to write 357 lines of it in front of a
  reader who wanted to ask one question. The missing resolver and the
  oversized example are the same defect seen from two directions.
- **The runtime doors gain a reference resolver they lack today.** They
  currently *require* the deployment to supply one. Not this phase's work; it
  simply stops being a gap.

**Hard constraint:** the composition is **pure mechanism**. Thresholds,
product classes, policy bundles, and every domain value continue to come from
Control Plane artifacts. A resolver that bakes in a decision is the
No-Hardcoding Rule (CLAUDE.md §6.4) firing.

## C — Boot caching is required

**Ruled:** the in-process adapter caches the booted fabric per binding
address, as a hard implementation constraint.

The reason is recorded because it is not the obvious one: **this is not a
performance optimization.** A second `load_and_boot` against the same graph
raises `SingleWriterViolation`. Caching is what makes a second `ask()` legal
at all. (Measured cold boot 74.2 ms, confirming STATE.md's 74.3 ms figure.)

No change at the client surface. Planning resolves cache lifetime, whether a
`close()` exists, and the two-clients-one-binding case.

## D — The retirement inventory goes first

**Ruled:** the retirement inventory and its sweep machinery are repaired
**before** any example-tree removal lands — first, not merely in parallel.

Two of the three currently-failing `tools/` tests *are* the sweep machinery
`D-27` depends on, and `RETIREMENT-COUPLINGS.md` is 85 rows stale (163
committed vs 248 live). An untrustworthy inventory is precisely how a partial
retirement ships, which is the failure mode §11's no-partial-state rule exists
to prevent.

## Effect on §12's open items

| §12 item | Status after this amendment |
|---|---|
| 1 — demo-data form | **CLOSED** by Dave, 2026-08-15 — see *Amendment 1 addendum* below. There is no demo-data mechanism to build: the deployment points at stores already populated with FIBO data. |
| 2 — condemned trees | Governed by **D** above: repair the sweep machinery first. |
| 3 — MCP adapter specifics | Open as stated, plus: the shipped egress tool hard-wires `parameters={}`, so a class with any required parameter is unreachable over MCP. Deliverable 5 cannot pass §6 conformance or §8's two-thresholds property without that fix. |
| 4 — `WireOutcome` schema | **Half-answered.** The served half is a transcription (freeze it). The refusal half, `replay_ref`, and the echoed request identity are new surface governed by **A**. Plan design budget accordingly. |

## Amendment 1 addendum — demo data (Dave, 2026-08-15)

**Ruled: there is no demo-data mechanism in this phase.** The deployment the
client points at is **already populated** — the backend stores were loaded
with a sample of FIBO data for exactly this purpose, and they live outside
the repository.

This is the literal reading of §7's premise, not a compromise on it: *"ask a
question of an already-running Context Product."* The client never seeds,
never ingests, and never knows how the data got there. Consequences:

- **Nothing to commit.** No store file, no seed artifact, no fixture data in
  `examples/`.
- **No ingest anywhere near `ccf.client`.** D-16's prohibition on provisioning
  inside a client call is satisfied by construction rather than by discipline.
- **D-17 stands untouched.** `deployment/` is `ccf_config.yaml` plus
  connection material (`backends.yaml`, which stays separate — a DSN inside a
  content-hashed artifact is a DSN persisted into the audit plane forever).
- **`src/ccf/deployment/config.py:82-91` is not reversed.** The refusal to put
  a signal batch in `ccf_config.yaml` stands; nothing in this phase needs it.

**Scope note:** data production is a *producer-side* concern and belongs to
the later body of work on context-producer examples. The next several examples
are client-side only — the revenue-threshold question first, then FIBO context
products.

**The one consequence to plan around, stated rather than papered over:** an
example that needs a reachable backend **cannot run in always-on CI**, which
is network-free and holds no credentials. The project already has the shape
for this — `.github/workflows/live-legs.yml` runs the DGX databases as an
opt-in job while `sqlite`/`memory` stay in the always-on pipeline (Phase 16
`D-06`, Phase 8 `D-11`). Planning places the example accordingly and states
plainly which pipeline proves it.

## What did not change

The client surface (§2), binding resolution (§3), `Result`/refusal semantics
and the fail-closed guard (§4), `Result` constructed in exactly one place and
the in-process codec round-trip (§5), the conformance suite as the parity gate
(§6), the ≤80-line example with its purity and budget gates (§7), the testing
strategy including sabotage discipline (§8), sync-only v0 (§9), the not-list
(§10), and the ruling consequences (§11).
