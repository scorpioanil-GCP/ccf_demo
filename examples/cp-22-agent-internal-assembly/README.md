# cp-22 — Agent-Internal Assembly

**The specification is
[`spec/CP-SPEC-022_Agent_Internal_Assembly.md`](spec/CP-SPEC-022_Agent_Internal_Assembly.md)**,
written and ruled on before any of this code existed.

## What this demonstrates

> ### CCF terminates inside Agent B.
> ### A2A is an external agent protocol and is **not** a CCF delivery surface.

Agent A is an ordinary agent in a multi-agent workflow. It asks a peer a
banking question over A2A. It has never heard of CCF, holds no CCF credential,
and reads no CCF type.

Agent B answers by assembling a governed Context Product **in its own process**,
reading one fact out of it, and replying — and the product, its contract, its
content address, its Context Debt, its lineage and its replay record **never
leave**.

**Nothing before this rung ran CCF inside a process that is simultaneously a
server for a protocol CCF does not own.** Every shipped door — MCP egress, the
HTTP API, peering — serves *the Context Product itself* to a CCF-aware
consumer. This inverts that.

**CP-22 declares no Context Product class, no operator, no artifact schema and
no new dependency.** It consumes `examples/cp-21-large-exposure` unchanged.

## Run it

```
make -s example-cp-22
make -s example-cp-22 NOISE=--noise      # the caller tries to steer the answer
make -s example-cp-22 STRICT=--strict    # the peer's own debt tolerance refuses
```

Agent B consumes cp-21, so it reads **cp-21's** environment —
`CCF_CP_21_POSTGRES_DSN`, `CCF_CP_21_POSTGRES_SCHEMA`, `CCF_CP_21_FLUREE_URL`,
`CCF_CP_21_FLUREE_LEDGER`, `CCF_CP_21_MONGO_URI`, `CCF_CP_21_MONGO_DB` and the
four `CCF_CP_21_TOKEN_*` credentials. **CP-22 declares none of its own**, which
is itself the point: no new binding mechanism was added.

`run.py` starts Agent B in a **separate OS process** and asks from this one.

## The story

### What crosses, and what does not

Agent A sends two fields. That is the whole inbound surface:

```json
{"subject": "B3BS7ACMDUWISF18KY76", "instant": "2026-08-25T00:00:00+00:00"}
```

A subject names *what*; an instant names *when*. **Neither can widen an
envelope, select a rendering, or raise a tolerance.** Everything that
governs — the product, the principal, the role, the intent, the regime, the
connection basis, the mitigation posture and the debt tolerance — is declared
in `artifacts/agent-b.yaml` and is unreachable from the wire.

Agent A gets back four fields:

```
   Bausch Health Companies Inc. is within its binding exposure limit as of 2026-08-25.

   counterparty   Bausch Health Companies Inc.
   headroom       6958634550.00
   as of          2026-08-25T00:00:00+00:00
```

### The extraction is lossy on purpose, and the measurement says how much

| | |
|---|---|
| the governed payload | **11,389 bytes** over **18** top-level members |
| the A2A answer | **216 bytes** over **4** fields |
| ratio | **52.7 : 1** — 17 of 18 members dropped |

Dropped at the seam: the member roster, the normalized capital base with its
unit authority, the effective-dated regime with quoted rulebook text, every
applicable limit with its counting rules, the conflict between two internal
authorities, the disclosed freshness asymmetry, Context Debt by the
per-factor-minimum law, the content address and the replay record.

**Agent A asked whether there is headroom. It gets whether there is headroom.**

### Debt governs without travelling

`D_c` decides whether Agent B **may use** the product. It does not cross.

Two Agent B processes differing **only** in their declared tolerance:

| declared tolerance | measured debt | reply |
|---|---|---|
| `0.98` | 0.30 | the answer |
| `0.20` | 0.30 | an honest non-success |

Same question, same instant, same subject. The tolerance is load-bearing and
invisible.

### A refusal becomes another protocol's failure

When the determination refuses or is withheld, Agent B does **not** return an
empty success and does **not** forward the envelope. The CCF refusal — its
reason, its error code, its replay reference — is read, branched on, and
**dropped**. Agent A sees a protocol-level failure carrying one sentence:

```
the peer could not answer: the question could not be answered with sufficient confidence
```

### Why `ccf_runtime.peering` is not used, and is gated against

The SDK ships an A2A transport already. It is the **wrong** thing here, and
`AIA-G09` asserts the import is absent:

| | Peering (`LfA2AWire`) | CP-22 |
|---|---|---|
| what crosses | a signed Context Product | an agent's answer |
| the far side | another **fabric** | another **agent** |
| what it does | admits it through a Control Plane gate | reads a sentence |
| knows CCF exists | yes, necessarily | **no** |

Reaching for it because the word "A2A" appears in both would convert an agent
conversation into a fabric federation and impose a Control Plane the
counterparty does not have.

## Artifact-by-artifact

| artifact | what it carries |
|---|---|
| `artifacts/agent-b.yaml` | everything that **governs** — the consumed product, Agent B's principal and role, the policy envelope, the two debt tolerances, and the A2A card values |
| `artifacts/wire-contract.yaml` | the machine-readable invariant — two admitted inbound fields, nine probe fields that must be **ignored**, four admitted outbound fields, and the **seven forbidden classes** as tokens a byte scan can find |
| `artifacts/question.yaml` | Agent A's question, in Agent A's vocabulary — a subject and an instant, and nothing that governs |
| `artifacts/gates.yaml` | the twelve declared gates, each with its sabotage and the observation of it going red |

`agent_a.py` is the **control for the whole rung**: if anything CCF-shaped were
needed to ask this question or read this answer, it would have to appear there.

## Whitepaper / CLAUDE.md sections exercised

| section | how |
|---|---|
| Whitepaper §7.6 — Context Product Contract | assembled, governed, and consumed entirely within one process |
| Whitepaper §7.7 — Context Debt | `D_c` gates whether the answer may be used, and does not travel |
| Whitepaper §7.10 — Decision Replay | the record is written and resolved **inside Agent B** and referenced nowhere on the wire |
| CLAUDE.md §7.2 — A2A federation | the boundary this rung **declines** to use: peering is fabric-to-fabric, and this is not |
| CLAUDE.md §7.3 — harness neutrality | the A2A server and client are `a2a-sdk`'s, used as given; **no adapter is written** |
| CLAUDE.md §6.4 — No-Hardcoding | every governing value and every forbidden token is a declared artifact |
| CLAUDE.md §9 — estate discipline | reads the curated `.76` estate through cp-21; seeds nothing |

## What to change first

| To change | Edit |
|---|---|
| **which product Agent B consumes** | `artifacts/agent-b.yaml` → `consumed_product` |
| **who Agent B is, and what governs** | `artifacts/agent-b.yaml` → `principal`, `envelope`, `debt_tolerance` |
| **what may and may not cross the wire** | `artifacts/wire-contract.yaml` |
| the A2A card, host and port | `artifacts/agent-b.yaml` → `a2a` |
| the question asked | `artifacts/question.yaml` |
| **the extraction itself** | `agent_b.py::_answer_from` — this and `_ask_ccf` are the whole of what a different use case changes |

## What would fail

Twelve declared gates, `AIA-G01`..`AIA-G12`, in
[`artifacts/gates.yaml`](artifacts/gates.yaml). **All twelve were observed RED**
under their own sabotage on 2026-09-21 against the live estate — fourteen
sabotages in all, since `AIA-G02` and `AIA-G05` each carry two. None is
`unavailable`.

One sabotage failed to redden on the first attempt and was **corrected rather
than swapped**: `AIA-G08`'s leaked a caller-supplied tolerance into an
environment variable but never let it *reach* the determination, which does not
mutate the claim the gate asserts.

What breaks this rung, concretely:

- exporting the Context Product, its address, its debt or its lineage
  (`AIA-G05`) — one line, and it reads as generosity;
- forwarding a CCF refusal envelope (`AIA-G06`), or returning an empty success
  instead (`AIA-G07`);
- letting any caller-supplied field reach the policy envelope (`AIA-G08`);
- importing `ccf_runtime.peering` (`AIA-G09`);
- a declared tolerance that reaches nothing (`AIA-G10`);
- testing the exchange with a direct handler call instead of a socket
  (`AIA-G12`) — which would prove the extraction and nothing about A2A.

The findings, including two defects found while building, are in
[`FINDINGS.md`](FINDINGS.md).
