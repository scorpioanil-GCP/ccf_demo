# Reconstruct a governed determination

Reproduce a decision the fabric already made — a served Context Product, or a
governed refusal — from its replay record and the store, through the SDK's
engine, with no second call to any source or producer.

This page documents the path that exists today, sourced from the replay proofs
the shipped producers carry in their own test suites. It is a recipe, not a
framework: what you supply is an environment of three methods, and the engine
does the rest and checks all of it. Everything below is literal-included from
`examples/dr-01-replay-a-governed-determination/replay.py`, which runs against the
curated estate.

Run it with the producer's environment exported (for the default tree, the
`CCF_CP_06C_*` names its `ccf_environment.yaml` declares):

```sh
.venv/bin/python examples/dr-01-replay-a-governed-determination/replay.py
.venv/bin/python examples/dr-01-replay-a-governed-determination/replay.py --refuse
```

## Two addresses, two entry points

A determination has **two addresses, and they are different things.** The
**product address** is the content hash of the served contract — the bytes a
consumer received. The **record address** is where the five-dimension replay
record landed in the artifact store. The record names the product it served;
the product does not name its record. A refusal has a record address and no
product address at all.

The engine has **two entry points**, and which one applies is decided by what
the record says happened, not by what you would like to prove:

- `replay()` reproduces a **served** product: it re-executes the recorded
  operator path over the recorded snapshot, rehydrates the product through
  your environment, holds the TTL anchor to the recorded instant, and holds the
  rebuilt product to the record's product address. It returns only if every
  check passed.
- `replay_refusal()` reconstructs a **refused** determination: the same
  prologue, the same re-execution where a projection ran, and then the recorded
  refusal held positively to its recorded evidence and child rows. It never
  rehydrates a product — the record names none — and a served record handed to
  it, or a refused record handed to `replay()`, is refused by name as a
  record-kind mismatch.

## What you supply

**Three arguments.** `RecordedEnvironment` in `ccf.replay.environment` is the
supported implementation of `ReplayEnvironment` — the record to reconstruct,
the product opened against the deployment that produced it, and the fabric to
read through. It derives everything else from those.

Before it existed (`D-IMPL-346`) an adopter wrote the Protocol's three methods
themselves, and six example trees each wrote the same 40–95 lines. If you need
a seam the supported class does not have — a test that sabotages its own
environment, say — implement the Protocol directly or subclass this; the engine
is what makes a replay true either way, and it trusts neither. A wrong plan
fails the step sequence, a wrong parameter set fails the parameter hash, and a
wrong envelope fails the address check.

```py
--8<-- "examples/dr-01-replay-a-governed-determination/replay.py:environment"
```

What the class builds, and where each part comes from:

- **`resolve_plan`** returns the projection for the recorded plan id, from the
  deployment's own `plan_factory` over the recorded operator plan and the
  **effective request** — the class defaults and policy bounds as they folded
  at decision time, carried on dimension 2 as `request_resolution`. Never the
  caller's raw parameters, and never a value resolved now.
- **`resolve_operators`** returns a registry holding the recorded operators
  with their parameter artifacts bound from that same effective request, over
  a reader scoped to the recorded snapshot boundary.
- **`rehydrate_product`** rebuilds the delivered contract: the payload from the
  re-executed projection, the envelope from the deployment's product class,
  and every member the record carries copied **verbatim** — the anchor instant
  (`ttl_anchor_at`, from which `expires_at` is reconstructed), the debt in
  force and what it pointed at, the sources' refresh recency, the obligation.
  Re-deriving any of them produces a different decision wearing this one's
  identifier, and the address check catches it.

## What the engine does with it

```py
--8<-- "examples/dr-01-replay-a-governed-determination/replay.py:reconstruct"
```

The engine resolves the record at its exact address, refuses a record written
under an earlier generation of the canonical form, resolves every pinned
binding on dimension 2 at its recorded version through the Control Plane, holds
the record's claim about whether a request resolution ran, reconstructs any
admitted children from the contracts the deciding fabric retained by content
address, and only then re-executes. A served product is then rehydrated, its
anchor held to the recorded instant, and its address held to the record's.

## Prerequisites, stated plainly

- **The retained store.** The record, the query pins, every retained child
  contract and child question, and the served product itself live in the
  artifact store the product was opened over (`scratch/<store_dirname>` on the
  paved road). Replay reads from that store by address; it cannot recreate
  what was not retained.
- **The snapshot.** The reader must reach the graph state the record pins. On
  the paved road that is the substrate the question was answered on, reopened
  through `load_config_and_boot` over the same documents; the engine scopes the
  reader to the recorded boundary before anything reads through it.
- **The same declarations at their pinned versions.** The product class, the
  policy bundle, the operator parameter artifacts and — for an
  evidence-anchored class — the half-life table are resolved at the versions
  dimension 2 pins. A rebound version fails the replay by name.
- **The documents.** The environment reads the product class and the TTL
  window from the deployment's `ccf_config.yaml`, and the substrate naming from
  its `ccf_environment.yaml`.

## Who supplies the environment, and what that does not permit

**The environment is producer-side work**: the deployment that served the
product is the one that knows its plan factory, its documents and its
substrate, so it is the one that can supply the three methods. That describes
*who* provides the environment. It does not permit the environment to contact
the original child producers, invoke the question mapping, or re-acquire
anything: the retained-question and retained-contract guarantees are unchanged,
and a replay that called a producer would be a new determination, not a
reconstruction. `retained_child_question` in `ccf.replay.engine` is the audit
read for what a parent actually asked — from the parent's own retained bytes,
held to the row's address, calling nothing.

For a **composite**, the environment also answers `resolve_composite_plan`
over the reconstructed children; the fourth CP-14 slice's suite carries the
reference form.

## One private dependency

Binding each operator's parameter artifact from the effective request is done
by `GovernedResolver._operator_parameters`, which the SDK does not expose as
public contract. The recipe reaches it by building a resolver from the opened
product's own arguments — `build_governed_resolver(**opened.build_arguments(fabric))`
— and calling the private method. That is the one line here that is not a
supported surface, and it is why the example lives beside the product trees
rather than inside one: a paved tree's structural classifier forbids the
builder call within the tree. Supporting this path without a private call is
an SDK change, recorded as such; it is not made here.

## Limitations the record does not lift

- The replay hold reads a product's **declared anchor basis** from the
  rehydrated declaration your environment supplies, not from a basis pinned in
  the record. A basis that changed between serve and replay fails — the
  address check catches it — but under a name that describes the wrong thing.
- **Refusal records do not pin the half-life table**, so a refused
  determination's anchor evidence is not re-derivable under its own pins; the
  refusal is held to what it recorded.
- These are limitations, stated as limitations. They are not lifted by the
  current examples passing.
