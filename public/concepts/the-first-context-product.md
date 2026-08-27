# The first Context Product

A Context Product is a **specified** thing before it is a built thing. A data
engineer writes a specification to a Standard — what the product resolves, which
store it binds to, which operators run in which order, how it decays, when it
stops being servable — and then the SDK either can express that specification or
it cannot.

This page follows one such specification into one shipped example and out the
other side as an answer. The specification is
`examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`;
the example is `examples/cp-00-institutional-holders`; and the answer is a typed
Context Product carrying four things a plain `SELECT` cannot return.

**The specification was written first, and that is the method rather than a
formality.** A specification written after the code describes the SDK. Written
before it, it states what must be buildable, and the build finds out whether it
is. Where the SDK could not express something the document ordered, the shortfall
was **recorded and left open** — which is only possible if the document exists
before the code that would otherwise have quietly reshaped it.

Every code excerpt below is pulled out of the tree by a snippet include rather
than transcribed into this page. A transcribed snippet drifts silently the day
the code changes; an include cannot, because a dangling one is a hard error in
the documentation build. That is the standard this page holds itself to: a claim
about mechanism is either an include from a source CI already gates, or a fact
about a declared artifact a reader can open.

## What the numbers on this page are

> **These examples teach METHOD — how to engineer and construct a Context Product with the CCF SDK — not the figures.** Every count and dollar amount below is here to show how a specification binds to a real store, and for no other reason.
>
> The surrounding data estate carries **deliberately engineered names and relationships** — 30,365 rows marked `synthetic — engineered`, 13,840 `synthetic — internal` and 20 `derived`, measured across the tables that carry a provenance column — even though the two tables *this* product reads carry none of them: 22,476 of 22,476 rows and 156 of 156 rows measure `provenance = 'public'`.
>
> **No number here is a fact about any real company.**
>
> What a reader is actually looking at is **one quarterly archive spanning many periods** — 46 of them, one pinned by the specification — rather than a live feed.
> Its issuer matching is **~22.5% `weak` BY DESIGN** rather than by defect: the band travels with each row and is filtered nowhere, because it is a completeness signal this product declares rather than a defect it removes in silence.
>
> These rows are public regulatory filings. Calling their *behaviour* invented
> would be inaccurate in the cautious direction, which misleads a reader about
> what they are holding exactly as badly as overclaiming would.

That block is repeated in paraphrase beside each figure cluster below rather
than left here as a header to scroll past.

## The specification's operator table, as data

Section D of the specification is a numbered table: one operator per step, with
its capability class, its inputs, what it emits, how it fails, and its latency
budget. A prose table cannot be held against a run, so this example ships the
same table as an **artifact**, with one addition the Standard does not ask for —
per step, the **SDK mechanism and the layer it lives at** — and one addition the
example needs: per step, a **witness**.

A witness is a fact a completed run either produced or did not: an operator key
in the served lineage, a non-empty assembled view, a matching projection plan id,
a `ServableProduct` actually held, a named key present in the payload. The
vocabulary is closed at five kinds, and a step that cannot name one of them is a
step nothing can prove ran. The honest response to that is to remove the step
from the specification, never to invent a sixth kind of witness.

```yaml
--8<-- "examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml"
```

Read the `sdk_mechanism` and `sdk_layer` columns down the page and the shape of
the argument appears: **the steps are not all at one layer.** Two of them are
L4 operators. One is L2, on the write path. One is L5, inside Π. One runs at the
source boundary in the deployment's own reader. The last is not an operator at
all — the Standard itself retires `Compose`, and contract assembly is always the
final step.

**About the `p95_budget_ms` column**, and it is worth being blunt: the artifact
says `budgets_are_measured: false` beside it, and it means it. Those numbers are
design targets an engineer is invited to challenge. **Nothing on this page is a
latency measurement.**

**The engineer challenged them, and the budget lost.** After this page was
written the assembly was run forty times against the live estate, and the
measured p95 came back at roughly **twelve times** the envelope the
specification declares for itself — almost all of it in one step, the write of
every filed position through the fabric's single writer. The specification
carries the figures, the instrument that produced them and the step-by-step
attribution; this page carries none of it, and the column above is still what
it was: a set of targets, not a set of readings. That distinction is the point.
A budget that is contradicted by measurement is a specification doing its job —
it is what a design target is *for* — and it is a very different artifact from a
column of numbers quietly relabelled as facts.

## A name mismatch between two vocabularies is a mapping, not a gap

The Specification Standard has a closed vocabulary of **eight** operator names.
The SDK has a closed vocabulary of **four** operator categories. Those two
numbers do not reconcile, and the first instinct on meeting that is to file six
SDK gaps. That instinct is wrong here, and the way to tell is to ask a single
question about each name: **which layer does the capability live at?**

| The Standard's name | Where the capability lives in CCF |
| --- | --- |
| `Policy` | An L4 operator category, 1:1 |
| `Traversal` | An L4 operator category, 1:1 |
| `Similarity` | An L4 operator category, 1:1 |
| `Resolve` | **L2** — entity resolution on the write path. It cannot be an L4 operator, because L4 is read-only and L2 is the single writer |
| `Projection` | **L5** — Π is a *layer* in CCF, not an operator. The Standard listing it beside Traversal is an authoring convenience |
| `Federate` | **The peering surface, above L6** — admission, trust policy, identity and the federated gates |
| `Evaluate` | **Present as Π, not as a named operator.** An operator's `apply` returns a *view*, and `Evaluate`'s modes — aggregate, score, reconcile, rank into a measure — all produce *numbers*. Computation that yields measures rather than graph state runs inside the projection |
| `Enrich` | **Genuinely absent.** The SDK has nothing that is *"attach declared attributes to already-resolved entities in a bounded number of round trips."* This one is a real shortfall and is recorded as one |

And the asymmetry runs the other way too. The SDK holds `temporal` as a separate
category with **no name among the Standard's eight** — the Standard folds it into
a Traversal *mode*. A vocabulary that has a name its counterpart lacks, in both
directions, is the signature of two vocabularies derived from a common source and
then named differently. It is not the signature of two that diverged in
substance.

Seven of the eight, then, are a documentation mapping. One is a gap. Saying
"they all map" would have been the easier sentence and the wrong one.

## The code that runs each step

The example splits into two files that import nothing from each other. One holds
the fabric's calls and names no table, column, entity, artifact key, substrate,
parameter or number. The other holds every one of those and makes no fabric call
the first one does not. The split is structural rather than editorial: a reader
can tell which code is CCF's from the directory listing.

What follows are three regions of the fabric's half, included from the tree.

### Π, where the caller's threshold is applied

The threshold is a **request parameter**, declared required with no default, and
it is applied here at L5 — never in the graph query. The consequence is the one
worth carrying away: every threshold compiles to the *same* pinned read, so what
the caller's number changes is the payload, and therefore the product's content
address, rather than what was read. That is also what makes the assembled state
identical across callers, which is why the specification's first optimisation is
to materialize that state rather than to make the read faster.

```py
--8<-- "examples/cp-00-institutional-holders/produce.py:project"
```

### The three validation gates

Registering the TTL ceiling is what **mints** its version pin, because a pin is a
content hash of what was registered — which is why the ceiling reaches this call
through the deployment rather than through the product class's own document.

The lineage the product claims is then filled **from the declaration**, never
copied out of the execution record. A claim copied out of a transcript is a
transcript. The second gate holds the two to strict equality in both directions,
so a declared operator that did not run and an operator that ran undeclared are
both refusals.

And a `ServableProduct` is not constructible outside the gate call. Holding one
*is* the evidence the gates ran — evidence rather than assumption, because the
refusal branch below it is reachable and raises.

```py
--8<-- "examples/cp-00-institutional-holders/produce.py:gate"
```

### The decision is recorded before it is delivered

The executed graph queries are persisted, then the replay record, and **delivery
is what the successful append returns**. There is no branch that reaches a served
product without a recorded decision, and no moment at which the record pins a
question the store cannot resolve.

```py
--8<-- "examples/cp-00-institutional-holders/produce.py:serve"
```

### The single writer, for completeness

One handle writes to the Context Graph anywhere in the process. Nothing else
holds one and nothing can obtain one — and the system of record this deployment
read from is not reachable from the write path at all.

```py
--8<-- "examples/cp-00-institutional-holders/produce.py:ingest"
```

## The whole Control Plane, in one document

Everything specific to this product — the backend *kind*, the product class and
its declared operators, the two operator parameter sets, the request contract,
the resolution rules, λ_c, the debt bands, the policy regime, the perspective —
is one authored document. Delete it and neither module has anything left to
interpret.

Two things about it are worth reading for, beyond the values. Every entry names
the specification section that authored it, so the document is diffable against
the specification rather than merely consistent with it in someone's memory. And
the debt bands are written out **with their arithmetic**, so they are values an
engineer can challenge rather than numbers a reader has to assume were derived.

```yaml
--8<-- "examples/cp-00-institutional-holders/ccf_config.yaml"
```

Note what is *not* in that document: no host, no port, no path, no credential.
Connection material is deployment environment rather than Control Plane state,
and a connection string written into a content-hashed artifact is a connection
string persisted into the audit plane forever. It reaches the deployment through
a declared environment variable's **name**, and through nothing else.

## What the answer carries that a `SELECT` cannot

Run the example and the last thing it prints is headed *"What a plain SELECT
would not have told you."* Four items, and each is a different kind of claim.

**The measured Context Debt.** `D_c = 1 − (F · C · S)`, computed over what this
question actually assembled rather than declared beside it. `F` decays from the
*source's* instant — when the filed fact began to hold — and not from the instant
the fabric happened to read it, which is the difference between measuring the age
of the data and measuring the age of the run. `C` is two components multiplied
and named separately, because this product has two different incompletenesses.
`S` is 1, and the reason is stated rather than left as a magic constant: there is
exactly one source, and a single source cannot disagree with itself.

**The policy-bundle version in force**, as a content hash of what was registered,
carried inside the product's own lineage rather than beside it.

**The content address**, over the whole vessel including the debt figure. Two
thresholds are two addresses.

**The replay reference**, resolving a record that pins the graph snapshot
instant, the policy version, the perspective, the operator plan, and the question
that was asked — parameters and all, so replay re-asks the same question rather
than a similar one.

A plain `SELECT` returns rows. None of those four is a row, and none of them is
recoverable from the rows afterwards.

**The figures behind that, restated where a reader meets them.** They exist to
teach the method of constructing a Context Product and never the numbers; the
estate around this product carries names and relationships that were put there on
purpose; not one figure here is a fact about any real company; and what they
describe is a quarterly archive of 46 filing periods rather than a live feed, in
which roughly a fifth of the rows carry a `weak` issuer match because the matcher
was built to say so.

## What this example is honest about not being

It qualifies as a Context Product on a **recorded, qualified basis**, and the
specification says so in its own first section: of the four questions the
Standard asks, this product answers *no*, *yes*, *yes* and *partial*. It does not
qualify on assembly merit. It qualifies on the validity-window and replay
obligations, and on being the first rung of a ladder. A reviewer is entitled to
challenge the admission on exactly that basis, which is why it is written down as
one rather than smoothed over.

Its lifecycle state is `draft`. It is not registered and not certified, because
registering before the operate-and-govern section is complete is the named common
error rather than a shortcut.

And it has a written shelf life. The declared TTL is anchored on the reported
quarter end, so a year after that period the delivery gate refuses — and **that
refusal is the gate working**, not a defect. Saying so here is cheaper than
discovering it from a red build in 2027.

## Where to go next

Run it: `make example-cp-00`. The example's own README carries the mechanics —
what to export first, the seven fabric steps in the order they run, every file in
the tree and which side of the mechanism/adaptation line it sits on, what to
change first, and what each failure mode prints.

Read `examples/cp-00-institutional-holders/spec/CP-SPEC-000-institutional-holders.md`
beside it. The example prints that document above its own output for a reason: a
Context Product without its specification is a payload, and a specification
without a running product is a wish.
