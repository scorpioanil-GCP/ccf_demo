# Architectural invariants

CCF makes a small number of structural promises. Each one is what some
downstream guarantee — replay determinism, auditability, portability — actually
rests on, and each is enforced by a mechanism that fails the build or the call
rather than by a convention someone is expected to remember.

This page names all seven, says why the architecture forces each, and names the
specific thing that enforces it. An invariant with no named enforcement is an
aspiration, and the SDK does not ship those.

## Single writer to the graph

**The promise.** Exactly one component holds a write handle to the Context
Graph: L2 Context Assembly. Nothing else can write, under any circumstance.

**Why the architecture forces it.** Lineage is only trustworthy if every
assertion in the graph passed through the one place that stamps policy bindings
and resolves entities and time. A second writer would produce graph state that
no lineage set describes, which silently voids replay for every decision that
touches it.

**How it is enforced.** The reader and writer are separate protocols, and the
writer handle is supplied by dependency injection at boot — a read-path
constructor is never given one, so a direct write is not merely forbidden but
unrepresentable. Both reference writers live in one module precisely so that a
review can see the whole set of them at a glance.

The write path, and the two paths that look like exceptions but are not:

```mermaid
--8<-- "public/diagrams/seq-single-writer-write-path.mmd"
```

## Admission through assembly

**The promise.** Material arriving from outside the trust boundary — a signed
Context Product from a federated peer — is not admissible to the graph until
the consuming Control Plane has verified it, and even then it enters through
assembly like anything else.

**Why the architecture forces it.** Federation is the point at which someone
else's lineage, someone else's policy regime, and someone else's signing
identity meet yours. Verification at admission is what keeps the consuming
fabric's audit story intact; skipping it for a trusted peer would make the
strength of your audit a property of your peer list.

**How it is enforced.** Verification is unconditional — signature, policy
bindings, contract validation, and lineage integrity, on every inbound product,
with no fast path. A rejection is itself an audited record. Inbound lineage
extends the consumer's by set union, so the producer's operator plan, snapshot
and policy version survive the crossing.

```mermaid
--8<-- "public/diagrams/seq-a2a-admission.mmd"
```

## Composition preservation

**The promise.** Operators compose associatively: applying two operators in
sequence gives the same result as applying their composition, for every pair
the SDK ships.

**Why the architecture forces it.** Replay re-derives a product by re-running a
recorded operator plan. If composition were not preserved, the same plan could
produce a different result depending on how it was scheduled, and "deterministic
reproduction" would be a claim about the scheduler rather than about the
algebra.

**How it is enforced.** Empirically, by a property test suite that exercises
operator pairs rather than by assertion in prose — `tests/properties/` holds
the algebra-level checks and `tests/agents/` the composition checks over
archetypes. A newly shipped operator without its pair coverage is an incomplete
operator.

## The three validation gates

**The promise.** No Context Product reaches a consumer without passing an
empty-operator guard, lineage strict equality, and TTL bounds.

**Why the architecture forces it.** Each gate closes a way a product could be
well-typed and still be a lie: derived from no operators at all, served past the
freshness envelope it advertises, or — for a federated product — carrying a
lineage its producer's signed bytes do not attribute. The lineage strict-equality
gate on the governed path is **assembly-path integrity**, not an independent
witness: the engine runs exactly the operators the class declaration names, so
the gate verifies that the engine transcribed the plan faithfully and cannot
catch a misdeclaration (`D-IMPL-86`). The control that can is the pre-execution
binder, `refuse_operator_set_divergence`, which compares the class declaration
with the projection's own requirements artifact before anything runs
(`D-IMPL-300`). Which control can fail on which path, and the test that proves
each one, is the [controls register](../reference/controls-register.md).

**How it is enforced.** Gate execution is the only route to a servable product
— the serving type cannot be constructed without passing through the gate
runner, so bypassing the gates raises rather than silently succeeding. Each
refusal is a typed object naming which gate refused and why, not a boolean.
Federated products run an additional lineage-attributability check on the same
path. The TTL gate's comparand is the fabric's own instant, read once per serve
(`D-IMPL-358`).

## Algorithmic ⇄ Semantic Alternation

**The promise.** Algorithmic stages and semantic stages alternate; a language
model never sees raw signal.

**Why the architecture forces it.** The value of the fabric is that what
reaches a model is *already* resolved, policy-bound and typed. A model call
inside an algorithmic stage collapses that guarantee and makes the stage
non-deterministic, which takes replay with it.

**How it is enforced.** A lint. Modules marked as algorithmic are rejected if
they import a model client, and the check runs over the library and runtime
trees as a blocking gate: `python -m tools.lints --algorithmic`. There is
deliberately no report-only mode — a non-blocking invariant stops being one.

A model call does not need a model client: a general HTTP client posting to a
vendor endpoint is the same call. So the lint also rejects an algorithmic
module whose string or bytes constants (f-string parts included) name a model
endpoint — `/v1/messages`, `/chat/completions`, `/v1/responses`,
`:generateContent`, `:streamGenerateContent`, `/invoke-model`, or the hosts
`bedrock-runtime`, `api.anthropic.com`, `api.openai.com`,
`generativelanguage.googleapis.com` and `aiplatform.googleapis.com`, matched
case-insensitively (`tools/lints/algorithmic.py::MODEL_ENDPOINT_FRAGMENTS`,
`LOW-05`). Importing an HTTP client is not itself a finding; the library's
graph, peering and MCP modules do that legitimately. What a static lint cannot
see is a model URL that arrives from configuration, the environment or the
network, or one assembled entirely from fragments none of which is an endpoint
spelling — that is a deployment-review concern, not something this check
claims to cover.

## Audit by construction

**The promise.** Every human action, every workflow trace, every skill grant
and revocation, and the skill-set in force at decision time land in the replay
record structurally — not through an optional hook someone might not wire up.

**Why the architecture forces it.** The audit question a regulator asks is
about the whole decision, machine and human parts together. A HITL surface that
*can* produce an unrecorded action produces one eventually, and the gap is
discovered during the examination rather than before it.

**How it is enforced.** Ordering: the replay write precedes the state
transition, so an unrecorded action is an action that never took effect. The
action record itself is a typed contract with unknown fields forbidden and an
identity binding required, so a partially-populated action is rejected at the
boundary rather than stored as a partial truth. See
[replay anatomy][replay] for the fields involved.

## The No-Hardcoding Rule

**The promise.** No prompt or system-instruction string literal in code; no
agent or task defined in code; no task graph, routing table, threshold,
approval rule or skill grant expressed as a code constant. Code holds
interpreters and factories; artifacts hold the things interpreted.

**Why the architecture forces it.** Two reasons that reinforce each other.
Governance: a value that lives in code cannot be versioned, granted, revoked or
replayed as an artifact. Generality: the moment a domain value enters the
library, the library is no longer general-purpose.

**How it is enforced.** A lint over the library, runtime and examples trees:
`python -m tools.lints --no-hardcoding`, which rejects prompt-shaped literals
and construction that bypasses the factory. It is the one rule with a reviewed
allowlist, and an entry there is a deliberate, visible event.

## Zero harness imports in core

**The promise.** No module in the SDK core imports any agent-harness package.
Harness-specific code lives only behind the adapter protocol, in the runtime's
adapter tree.

**Why the architecture forces it.** CCF's positioning is that it layers onto
whatever harness you have as the trust-and-control plane. A single harness
import in the core turns "works with any harness" into "works with that one",
and the claim cannot be recovered by documentation.

**How it is enforced.** A lint scoped to the library and runtime trees:
`python -m tools.lints --harness-imports`. The examples tree is exempt in
configuration rather than by allowlist, because the harness-portability example
necessarily imports harness packages — and stating the exemption as scope keeps
it visible.

## Where this lives

The mechanisms named above are documented alongside the surfaces they guard:
[storage and the graph][storage], [operators and projection][operators],
[Context Products][products], [HITL][hitl], and
[the harness adapter][harness]. The five pillars each describe the
invariants that hold them up — start with
[Data and Context][datactx].

[replay]: replay-anatomy.md
[storage]: ../reference/protocols/storage-and-graph.md
[operators]: ../reference/protocols/operators-and-projection.md
[products]: ../reference/protocols/context-products.md
[hitl]: ../reference/protocols/hitl.md
[harness]: ../reference/protocols/harness-adapter.md
[datactx]: pillars/data-context.md
