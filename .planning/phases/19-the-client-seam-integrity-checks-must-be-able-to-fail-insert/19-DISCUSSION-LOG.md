# Phase 19: The Client-Seam Integrity Checks Must Be Able to Fail - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `19-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 19-the-client-seam-integrity-checks-must-be-able-to-fail
**Areas discussed:** What identity travels, Closing the D-11 bypass, Producer-claimed address, How failure is proven

---

## What identity travels

### Q1 — What should the producer put on the wire so the echo has an independent operand?

| Option | Description | Selected |
|--------|-------------|----------|
| The question, re-stated by the door | Door fills the echo from the request it resolved and answered; reuses the shape already on the refusal half. Blind to two *identical* questions crossing. | ✓ |
| A canonical digest of the question | One string on the wire; failure names digests, not the wrong question. | |
| A client-minted correlation token | Only option catching crossed identical calls; says nothing about *what* was answered. | |
| Question echo AND correlation token | Strictly stronger; two members, two comparisons, two controls. | |

**Notes:** The blind spot was stated before the choice — two identical in-flight
questions crossing remain undetectable by a content echo, and `as_of=None`
means they could still resolve to different instants. Accepted knowingly.

### Q2 — What does the door echo on the temporal axis when the client sent `as_of=None`?

| Option | Description | Selected |
|--------|-------------|----------|
| As asked — `None` stays `None` | Total three-axis equality, no wildcard on the default path. | ✓ |
| Resolved — the door echoes the instant it used | More informative; forces sent-`None` to match anything, reintroducing vacuity on the most common path. | |
| Both — as-asked for the check, resolved alongside | More information; a second copy of what the vessel already carries. | |

### Q3 — What shape carries the served half's echo?

| Option | Description | Selected |
|--------|-------------|----------|
| `WireRequest`, total equality | No projection, no unread wire member; two identity shapes across the halves. | ✓ |
| `RequestIdentity` both halves, version checked against the vessel | Shape symmetry; `product_version` gets a referent; comparison becomes projection + second assertion. | |
| `RequestIdentity` both halves, three axes compared | Symmetry with the simplest comparison; leaves a wire member no check reads. | |

### Q4 — How does the refusal half get covered?

| Option | Description | Selected |
|--------|-------------|----------|
| Outcome-level echo covers both halves | One equality for served and refused alike; `RefusalEnvelope.request` untouched. | ✓ |
| Outcome echo, plus assert the envelope agrees | Catches producer-internal inconsistency; second comparison, second control. | |
| Served half only this phase | Smaller; leaves a crossed refusal attributable to a question nobody asked. | |

---

## Closing the D-11 bypass

### Q1 — How does the seam stop an adapter from reconstructing the echo?

| Option | Description | Selected |
|--------|-------------|----------|
| Retype the seam to bytes | Adapter cannot construct the outcome; `decode_outcome` moves onto the shipped path. Amends `D-11`. | ✓ |
| Keep the object seam, gate the construction | Cheapest; a lint reaches this repo's adapters and nothing out-of-tree — precisely "bypassable for the next adapter". | |
| Object seam, outcome carries its provenance | Reaches third-party adapters at runtime; a trust token inside a data shape. | |

### Q2 — Do the door shape and the client wire shape collapse into one?

| Option | Description | Selected |
|--------|-------------|----------|
| One shape | No transcoding step, which is where an adapter can re-source the echo. | ✓ |
| Two shapes, adapter transcodes | Preserves door/client separation; keeps the construction step that is the current defect's site. | |
| One shape for tool-style doors, HTTP deferred | Smallest blast radius; two answers to "what does a door emit" in the tree at once. | |

**Notes:** Later scoped by the HTTP question — "one shape" applies to
envelope-carrying doors, not to the HTTP door whose body is the vessel.

### Q3 — Does the request cross as bytes too?

| Option | Description | Selected |
|--------|-------------|----------|
| Symmetric — request serialized on every transport | Producer echoes what it parsed; the check goes live in-process, not only where a pipe exists. | ✓ |
| Outcome bytes only | Live over MCP, inert in-process — the transport every quickstart and fixture uses. | |
| Outcome bytes, in-process echoes its translated `ProductRequest` | One translation step of independence; both values still descend from one object. | |

### Q4 — What is the adapter seam's signature?

| Option | Description | Selected |
|--------|-------------|----------|
| `ask(WireRequest) -> bytes` | Request stays typed because an adapter needs its fields; only the answer becomes bytes. | ✓ |
| `ask(bytes) -> bytes` | Fully symmetric; the MCP adapter decodes immediately, so the blindness is nominal. | |
| `ask(WireRequest) -> bytes`, old path removed outright | Same, plus an explicit no-compatibility-window ruling. | |

**Notes:** The object return disappears by type change regardless. Whether
out-of-tree adapters get a deprecation window was left to planning.

---

## Producer-claimed address

### Q1 — How does the HTTP door reconcile with the one-shape ruling?

A collision surfaced during discussion rather than being asked cold:
`canonical_response` deliberately makes the HTTP body the vessel with siblings
in `X-CCF-*` headers (`D-IMPL-126`), and its docstring already rules the general
principle — *"each surface publishes the same sibling values through whatever
channel it actually has."*

| Option | Description | Selected |
|--------|-------------|----------|
| One shape for envelope doors; HTTP publishes siblings as headers | `D-IMPL-126` stands verbatim; the echo joins the sibling set. | ✓ |
| HTTP gains an envelope representation alongside the bare body | One door, two representations; two serializations to keep in agreement. | |
| HTTP body becomes the envelope | Genuinely uniform; contradicts `D-IMPL-126` and breaks zero-dependency verification. | |

### Q2 — What integrity claim does this phase restore, and is signing in scope?

| Option | Description | Selected |
|--------|-------------|----------|
| Non-adversarial integrity, stated precisely; signing out of scope | Detects wrong-question answers, corruption, mis-routing, canonicalization drift — not an envelope-rewriting adversary. | ✓ |
| Sign the outcome | Real adversarial detection; key distribution, `D-IMPL-15`, lands on a transport whose auth is impersonation (`A5`). | |
| Non-adversarial now, signature sibling reserved | Cheap future-proofing; ships an unread wire member — the pattern being closed. | |

---

## How failure is proven

### Q1 — What is the adversarial subject?

| Option | Description | Selected |
|--------|-------------|----------|
| Hostile in-repo adapter + codec byte sabotage | Single-transport, deterministic, no process choreography. | ✓ |
| A real crossing proxy on the stdio pipes | Highest fidelity; concurrency and timing risk for the same proposition. | |
| Both — adapter as gate, proxy as one demonstration | Strongest evidence; the proxy must be CI-reliable or it becomes a re-run. | |

### Q2 — Do tamper controls become a conformance obligation?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — generic tamper legs on every registered adapter | Possible only because the seam is bytes; costs adapter authors nothing, cannot be opted out of. | ✓ |
| No — adapter-agnostic controls outside the suite | Arguably one proof covers all; nothing per-adapter demonstrates liveness. | |
| Yes, and adapters supply their own fault injector | Highest per-adapter fidelity; real burden, and a weak injector passes while proving little. | |

### Q3 — Does the phase try to catch the defect class?

| Option | Description | Selected |
|--------|-------------|----------|
| Stay narrow on `B0` | `D-IMPL-146`'s accretion principle; the recorded lesson generalizes. | ✓ |
| Sweep and record every runtime integrity check | Cheap to measure; findings become open defects that unscope the phase. | |
| Ship an obligations gate for the class | Standing mechanism; "what counts as an integrity check" is a judgement that goes stale. | |

### Q4 — Is the in-process serialization cost acceptable?

| Option | Description | Selected |
|--------|-------------|----------|
| Accept, no benchmark owed | Same argument the client spec's `D-13` already accepted on the answer half. | ✓ |
| Accept, and measure it in the performance battery | Cost becomes a number; a threshold to maintain. | |
| Avoid the cost — in-process skips request serialization | Reverses the ruling that made the check live in-process at all. | |

---

## Claude's Discretion

- Deprecation window (or clean break) for out-of-tree adapters at the seam
  signature change.
- Where the producer-side door entry lives (`src/ccf/products/door.py` is the
  presumptive home).
- Wave staging of the wire-shape change, and the naming of the echo member and
  the HTTP echo header.

## Deferred Ideas

- An SDK composition helper turning a binding document into a governed resolver
  — raised from a mid-discussion question about why
  `examples/hw1-companies-over-revenue/server/serve.py` is 292 lines (~180 of
  them deployment-value composition, ~35 the MCP server itself). Its own phase.
- Signing outcomes for adversarial tamper detection.
- `A5` — stdio auth is impersonation rather than verification (carried forward
  unclosed from Phase 18).
