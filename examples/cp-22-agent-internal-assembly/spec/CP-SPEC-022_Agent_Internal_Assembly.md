---
class_id: cp-22.specification
semver: "1.0.0"
standard: Context Product Specification Standard v0.3
status: GATE 1 — requirements and questions only; no implementation
authored: 2026-09-21
measured_against:
  repo: ccf_code @ ec0c153e
  estate: 192.168.4.76 — Postgres ccf_v2, Fluree fibo-v2, Mongo fibo_v2
---

# Agent-Internal Assembly — Context Product Specification

**CP-22 is not a new Context Product.** It is a proof about *where* a Context
Product can be assembled: **inside an agent that is itself a server in someone
else's protocol.**

---

## 0 · What this document is

Gate 1 for rung 22, under Dave's GO of 2026-09-21 and the narrow framing given
with it:

> A2A transports the agent interaction; CCF is used internally by Agent B to
> construct governed context. Resist any attempt to turn the boundary between
> them into a new CCF protocol unless the implementation proves that something
> is actually missing.

This restates rather than reopens the re-scope Dave ruled on 2026-09-20 and
recorded at `docs/GATE-0-COVERAGE-CP15-24.md` §4.2.

### 0.1 Already proven — reused unchanged, and NOT reopened

| proven by | what it gives CP-22 |
|---|---|
| `examples/hw1-companies-over-revenue` | the `inprocess` binding and `ProductClient`, whose two-transport consumer already isolates the in-process route |
| `D-IMPL-343` (the paved road) | `open_product(...)` as the second in-process route; a named `plan_factory` |
| `D-GATE-cp-15`..`D-GATE-cp-21` | governed assembly, entitlement at the resolver, `D_c`, the replay record, governed refusal |
| `D-IMPL-326` | gate acceptance authority — this document's §G.1 is CP-22's |
| `D-IMPL-261` | examples are probes; a red run is SDK evidence before it is an example fix |

**None of it is rebuilt.** CP-22 adds no product class, no operator, no policy
mechanism and no artifact schema.

### 0.2 Genuinely new — ONE thing, and it is a boundary rather than a mechanism

Everything CP-22 exercises inside the fabric is proven. What is new is
**everything outside it**:

> **Nothing before CP-22 ran CCF inside a process that is simultaneously a
> server for a protocol CCF does not own, and had the governed product
> *terminate there* — never crossing the wire.**

Every shipped rung's door serves **the Context Product itself**: MCP egress,
the HTTP API, `LfA2AWire` peering. In each, the product *is* the payload and
the consumer is CCF-aware. **CP-22 inverts that.** Agent A asks a question in
A2A's vocabulary; Agent B assembles a governed product in-process, **reads an
answer out of it, and replies with the answer**. The product, its contract,
its debt, its address and its replay record **stay inside Agent B**.

Three consequences, and they are the rung:

1. **The governed-to-ungoverned extraction is a real seam and nobody has
   written it.** A Context Product is a typed contract with debt, expiry and
   lineage. An A2A answer is a string a language model will read. Turning the
   first into the second is a lossy, deliberate act that has had no home.
2. **A governed REFUSAL must become an agent answer.** No rung has translated
   `SubjectUnavailableRefusal`, a declared-gate refusal, or a debt-tolerance
   withholding into another protocol's reply. The temptation is to leak the
   envelope; the requirement is to answer honestly in A2A's own terms.
3. **The temptation to build a protocol is concrete and already half-built.**
   `runtime/ccf_runtime/peering/lf_a2a.py` exists and speaks A2A. It is the
   *wrong* thing here (§0.3) — and the fact that a reader reaching for "A2A"
   finds it is precisely why the boundary needs a gate rather than a comment.

### 0.3 Deliberately OUT of scope — and one exclusion is load-bearing

**Withdrawn by ruling (2026-09-20), not deferred:** an A2A Context Product
door; a `peering_product` skill; Context Product identity parity across MCP and
A2A; any new A2A SDK capability; batch A8.

**AND CP-22 MUST NOT USE `ccf_runtime.peering.lf_a2a`.** This is the sharpest
line in the rung. `LfA2AWire` is the **Peering** transport — a governed,
**peer-symmetric exchange between two fabrics that each have a Control Plane**,
in which a Context Product genuinely crosses the boundary and
`PeeringAdmissionGate` rules on admitting it. CP-22 is not that:

| | Peering (`LfA2AWire`) | CP-22 |
|---|---|---|
| what crosses | a signed Context Product | an agent's answer |
| who is on the far side | another **fabric** | another **agent**, with no fabric |
| what the far side does | admits it through a Control Plane gate | reads a sentence |
| does the far side know CCF exists | yes, necessarily | **no** |

Reaching for `LfA2AWire` because the word "A2A" appears in both would convert
an agent conversation into a fabric federation and silently impose a Control
Plane the counterparty does not have. **`LEX`-style gate `AIA-G09` asserts the
import is absent.**

Also out: children/composition; any `ccf_dataprep` change; CP-20; `D-IMPL-346`.

### 0.4 The four-question build test (Standard v0.3)

| question | answer |
|---|---|
| **What decision does this serve?** | Agent A's — a banking question it asked a peer agent, whose answer it will act on without ever learning where the evidence came from. |
| **What would a naive implementation get wrong?** | It would put the Context Product on the wire. The payload is JSON-serializable and A2A carries JSON, so exporting the contract "for transparency" is one line and looks generous — and it makes Agent A a CCF consumer, imposes CCF's vocabulary on a protocol that did not ask for it, and turns an internal governance decision into an external compatibility surface. |
| **What is genuinely new here?** | The governed-to-ungoverned extraction seam, and the translation of a governed refusal into another protocol's answer. |
| **What is deliberately not proven?** | That CCF *should* be exposed over A2A. This rung proves it need not be. |

---

## A · Decision frame

**Agent A** is an ordinary agent in a developer's multi-agent workflow. It
speaks A2A. It has never heard of CCF, holds no CCF credential, and reads no
CCF type. It asks a banking question.

**Agent B** is a peer agent that happens to be built on CCF. On receiving
Agent A's question it:

1. resolves the question into a governed product request under **its own**
   principal — Agent A's identity does not become a CCF principal;
2. assembles the product **in-process** at its own `asked_at`;
3. **reads the answer out** and discards everything else;
4. replies in A2A's vocabulary.

**The CCF requirement begins when Agent B needs governed context and ends when
Agent B holds the Context Product.** Everything before and after is A2A's.

---

## B · Contract

### B.1 What CP-22 declares

**CP-22 declares no new Context Product class.** It reuses an existing,
already-gated product as Agent B's evidence. The rung's artifact surface is:

| element | value |
|---|---|
| **Consumed class** | an existing rung's, unchanged — see `Q2` |
| **New classes** | **none** |
| **New operators** | **none** |
| **New SDK surface** | **none** |
| **Declared gates** | §G.1 — 12 gates, `AIA-G01`..`AIA-G12` |
| **Harness** | `a2a-sdk` 1.1.2, used as given (§F.2) |

### B.2 The measures

What Agent A receives, and what it provably does not.

### B.3 Request parameter surface

**Agent A's question has no CCF request surface**, and that is the point. It
arrives as an A2A message. Agent B maps it onto the consumed product's declared
request — and **that mapping is Agent B's code, not an SDK mechanism**.

Whether the mapping is trusted is `Q3`.

---

## C · Data catalog — measured against `.76` and the installed tree, 2026-09-21

### C.1 Harness readiness

| element | measured |
|---|---|
| `a2a-sdk` | **1.1.2**, installed |
| server surface | `a2a.server.agent_execution.AgentExecutor`, `a2a.server.request_handlers.DefaultRequestHandler`, `a2a.server.routes.create_jsonrpc_routes` / `create_agent_card_routes` / `add_a2a_routes_to_fastapi` — all resolve |
| client surface | `a2a.client.A2ACardResolver`, `ClientFactory`, `ClientConfig`, `create_client` — all resolve |
| `google-adk` | **2.5.0** with `google.adk.a2a` present — the alternative harness, **not** chosen (`Q1`) |
| `fastapi` / `uvicorn` | 0.140.0 / 0.51.0 — present, so the server needs no new dependency |

**No dependency is added by this rung.**

### C.2 The in-process route, measured end to end

A standalone script outside the product tree — the shape Agent B's handler
takes — booted `examples/cp-21-large-exposure` via `open_product`, asked one
governed question under a named principal, and read a use-case answer out:

```
AGENT-LEVEL ANSWER: binding limit internal-appetite, headroom 6958634550.00
governance available but NOT required to leave: DecisionReplayRecord
```

**Cost: 25 lines**, imports and the question included. **No SDK change, no
adapter, no new artifact.** This is the whole of what CP-22 must add on the CCF
side, and it is already this cheap.

### C.3 The traps, each with the binding chosen

**Trap 1 — THE EXPORT TEMPTATION, and it is the rung.** `ContextProductContract`
is a Pydantic model; A2A carries JSON. `result.payload` on the wire is one
line and reads as generosity. It is the failure this rung exists to refuse:
Agent A becomes a CCF consumer without consenting, CCF's vocabulary becomes an
external compatibility surface, and the next version of the payload is a
breaking change to a protocol CCF does not own. **Binding:** the A2A reply
carries no CCF-shaped structure, and `AIA-G05` asserts it **structurally** —
by scanning the outbound payload for CCF contract member names and types,
never by reading a docstring.

**Trap 2 — THE REFUSAL LEAK.** A governed refusal is a rich, correct object
with a reason, an error code and a replay reference. Forwarding it is
tempting because it is *informative*. It exports CCF vocabulary to an agent
that cannot act on it and leaks internal governance structure. **Binding:**
Agent B answers in A2A's own terms — that it cannot answer, and a
use-case-level reason — and `AIA-G06` asserts the reply contains no CCF
refusal vocabulary while `AIA-G07` asserts it is **not silently a success**.

**Trap 3 — AGENT A'S IDENTITY BECOMING A CCF PRINCIPAL.** The natural-looking
move is to pass Agent A's A2A identity through as the perspective, so the
answer is "properly scoped". That would make an unverified, externally
supplied identity a Control Plane principal. **Binding:** Agent B assembles
under **its own** declared principal, always; `AIA-G08` asserts the resolved
perspective is Agent B's regardless of what the A2A request claims.

**Trap 4 — THE HALF-BUILT PROTOCOL.** `ccf_runtime.peering.lf_a2a` exists
(§0.3). **Binding:** `AIA-G09` asserts no import of `ccf_runtime.peering` in
this tree.

**Trap 5 — DEBT BECOMING INVISIBLE.** The product's `D_c` is measured and then
discarded at the extraction seam. If Agent B ignores it, a badly-supported
answer is indistinguishable from a well-supported one **to Agent A, who has no
other signal**. This is the one place where the extraction genuinely loses
something that matters. **Binding:** `D_c` is not exported, but it **governs**:
above Agent B's declared tolerance the product is withheld and Agent A is told,
in A2A's terms, that the question cannot be answered confidently. `AIA-G10`
asserts the tolerance is load-bearing — the same question at a tighter
tolerance yields a different A2A reply.

---

## D · Assembly recipe

### D.1 The exchange

```
Agent A  --A2A message-->  Agent B
                             |  (1) map the question to a governed request
                             |  (2) assemble in-process, Agent B's principal
                             |  (3) read the answer out; discard the rest
                             v
Agent A  <--A2A message--  Agent B
```

### D.2 Step table

| # | step | owner |
|---|---|---|
| 1 | receive the A2A message; resolve the task | **A2A / harness** |
| 2 | map the question onto the product's declared request | **Agent B's code** |
| 3 | assemble in-process under Agent B's principal | **CCF** |
| 4 | branch on served / refused / withheld-above-tolerance | **CCF's verdict, Agent B's branch** |
| 5 | extract the use-case answer, or compose an honest "cannot answer" | **Agent B's code** |
| 6 | reply | **A2A / harness** |

Steps 1 and 6 are harness-owned and **no adapter is written for them**.

### D.3 Determinism class

Fully algorithmic on the CCF side. Whether Agent B runs a model to phrase the
reply is Agent B's business and outside the contract; the demonstration keeps
it deterministic so the gates can assert bytes.

### D.4 Validation gates (contract level)

Unchanged from the consumed product's. CP-22 adds none.

---

## E · Volatility and debt

Inherited from the consumed product. **CP-22 declares no λ_c table.** The one
new question is Trap 5's: debt governs but does not travel.

---

## F · Source binding and readiness

### F.1 Element readiness

Everything required is present and measured (§C.1, §C.2). **No estate gap.**

### F.2 Symbols to be used, verified against the installed tree, 2026-09-21

`ccf.products.product.open_product` · `ProductRequest` · `Perspective` ·
`ccf.replay.serve.ServedProduct` · `ccf.client.ProductClient` with
`ccf.client.adapters.inprocess` · `a2a.server.agent_execution.AgentExecutor` ·
`a2a.server.request_handlers.DefaultRequestHandler` ·
`a2a.server.routes.create_jsonrpc_routes` · `a2a.client.ClientFactory`.
**Every one resolves; none is invented.**

### F.3 Every `[TBC]`, with an owner

| # | item | owner |
|---|---|---|
| 1 | `Q1` — which harness | **Dave** (a binding is recommended) |
| 2 | `Q2` — which product Agent B consumes, and by which route | **Dave** (a binding is recommended) |
| 3 | `Q3` — how much of Agent A's question is trusted | **Dave** |

### F.4 — THE QUESTIONS OWED

#### `Q1` — which harness carries the A2A side?

| | option | consequence |
|---|---|---|
| **A** | **`a2a-sdk` directly** *(recommended)* | the protocol, nothing above it; ~60 lines for an `AgentExecutor` + routes + a client; no agent framework's opinions leak into the demonstration; matches how `lf_a2a.py` already uses the same library, so the shape is familiar without being reused |
| B | `google-adk`'s native A2A | closer to "a real agent", but drags ADK's agent/session/runner model into a rung whose subject is a boundary, and makes the demonstration ADK-shaped |

**Recommendation: A.** Gate 0 said *"the example should show one, not build an
adapter"*; `a2a-sdk` is the smaller of the two and keeps the rung about the
seam rather than about an agent framework.

#### `Q2` — what does Agent B consume, and by which in-process route?

| | option | consequence |
|---|---|---|
| **A** | **`open_product` against an existing paved rung** *(recommended)* | measured at 25 lines (§C.2); reads the **curated `.76` estate**, as CLAUDE.md §9 requires of every example; Agent A's question is a real banking question; no new binding document |
| B | `ProductClient` + `CCF_BINDING=inprocess:` against `hw1` | the thinnest possible glue and the route Gate 0 named — **but `hw1` is the only tree with a `binding.yaml` (measured: 1 of 27)**, and its deployment is a **seeded local sqlite**, so CP-22 would read no curated estate |
| C | write CP-22 its own product | a new class for a rung whose whole point is that it needs none |

**Recommendation: A**, with a measured note. Option B is cheaper by a few
lines and is what Gate 0 anticipated, but it would make CP-22 the one rung on
the ladder that demonstrates nothing against the live estate. **If Dave prefers
B for cost, that is a coherent choice and the estate exception should be stated
in the README rather than discovered.**

Under A, **which** rung is a second-order choice; the recommendation is a rung
whose answer is a single legible fact an agent would actually ask for.

#### `Q3` — how much of Agent A's question does Agent B trust?

This is the only question with a governance consequence, and it is where a
careless answer invents the protocol Dave's framing forbids.

| | option | consequence |
|---|---|---|
| **A** | **a fixed, narrow mapping** *(recommended)* | Agent B accepts one subject and one instant from the message and supplies everything else — intent, perspective, tolerance — from its own declaration. Agent A cannot reach the policy envelope at all. |
| B | pass A2A metadata through as request parameters | Agent A can shape the governed request from outside, which is a CCF request surface over A2A wearing a disguise — **the thing the framing forbids** |
| C | derive the perspective from Agent A's A2A identity | Trap 3; makes an unverified external identity a Control Plane principal |

**Recommendation: A**, and B and C should be closed explicitly rather than left
open, because both are what a well-meaning implementer reaches for next.

---

## G · Operate and govern

### G.1 Product gates — 12, `AIA-G01`..`AIA-G12`

Deliberately fewer than recent rungs. CP-22 re-proves nothing; every gate below
is about the **boundary**, which is the only thing this rung owns.

| id | statement | sabotage |
|---|---|---|
| `AIA-G01` | Agent B assembles the product **in-process**, in the same process that serves A2A — no MCP door, no HTTP door, no subprocess | assembly is moved behind a door |
| `AIA-G02` | Agent A's request carries **no CCF vocabulary** — no product class, no principal, no tolerance, no instant semantics beyond a plain timestamp | a CCF term is required to ask |
| `AIA-G03` | the A2A reply **answers the question** — the use-case fact is present and correct against the same question asked in-process | the extraction returns something the product does not say |
| `AIA-G04` | the in-process product and the A2A answer **agree**: the fact Agent A receives equals the fact the product carries, for the same question and instant | the extraction drifts from its source |
| `AIA-G05` | **no CCF-shaped structure crosses the wire** — the outbound payload contains no contract member names, no content address, no lineage, no replay reference, no `D_c`, asserted by scanning the bytes | the payload is exported "for transparency" |
| `AIA-G06` | a governed **refusal** becomes an honest A2A answer carrying **no CCF refusal vocabulary** — no error code, no envelope, no replay reference | the refusal envelope is forwarded |
| `AIA-G07` | a refusal is **never silently a success** — Agent A can tell an unanswerable question from an answered one | a refusal returns an empty-but-successful answer |
| `AIA-G08` | Agent B assembles under **its own** principal, whatever the A2A request claims | the caller's claimed identity reaches the perspective |
| `AIA-G09` | this tree **imports no `ccf_runtime.peering`** — CP-22 is an agent conversation, not a fabric federation | `LfA2AWire` is reached for |
| `AIA-G10` | **`D_c` governs without travelling** — a tighter declared tolerance changes the A2A reply for the same question | the tolerance reaches nothing |
| `AIA-G11` | the governed decision is **reconstructible inside Agent B** from its own record, though nothing of it reached Agent A | the record is not written, or not resolvable |
| `AIA-G12` | the whole exchange runs **across a real process boundary** — Agent A in one process, Agent B in another, over a real socket | the "A2A" call is an in-process function call wearing the protocol's name |

**`AIA-G12` is the one most at risk of being faked**, and it is why it is
named: a test that calls Agent B's handler directly proves the extraction and
**nothing about A2A**.

### G.2 What this rung measures for the backlog

- the **extraction seam**'s shape and cost — the first instance; if a second and
  third rung write the same thing, that is the case for an SDK surface, and not
  before (§H of the evaluation criteria);
- whether the in-process replay environment is still hand-assembled
  (`CP06C-F-01`, now at its fourth or fifth copy);
- that the `inprocess` binding and `open_product` are **not on a public page**
  (Gate 0's B5) — an adopter building Agent B today has no page to read.

---

## Gate 1 summary

**CP-22 requires no SDK change, no new class, no new operator and no new
dependency.** The CCF half is measured at **25 lines** and already works. What
the rung owns is a **boundary**, and the entire risk is that someone widens it
into a protocol.

**Three questions are owed** (`Q1` harness, `Q2` consumed product and route,
`Q3` trust in Agent A's question), each with a recommendation. `Q2` carries a
real trade-off Dave should settle: the cheapest route reads no curated estate.

**Twelve gates are proposed.** Nothing is implemented. Stopping for ruling.
