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
