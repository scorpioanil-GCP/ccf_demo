# examples/cp-00-institutional-holders — the first Context Product: one store, one system of record

`cp-00` is the first rung of the Context Production ladder. It takes a written
specification — `spec/CP-SPEC-000-institutional-holders.md`, authored to the
Context Product Specification Standard v0.3 **before any of this code existed**
— and finds out whether the CCF SDK can express it.

That ordering is the point. A specification written after the code describes
the SDK; written before it, it states what must be buildable and lets the build
discover whether it is. Where the SDK could not express something the document
orders, the gap was **recorded and left open** rather than closed here.

## What this demonstrates

**A Context Product is a *specified* thing, and this is the smallest honest one.**
One store. One system of record. Assembly Mode 1 — pure algorithmic, with no
model anywhere in the trust path. One question, one caller-chosen threshold, and
the specification printed above the JSON that answers it so a reader never sees
half of what a Context Product is.

`run.py` prints the document first and the dataset second. Pass `--spec brief`
once the document is familiar and it prints the front matter and the operator
step table, which are the two parts a reader returns to.

**What this example does that no other shipped example does: it implements the
producer seam.** `examples/cp-00-institutional-holders/assembler.py::HoldersAssembler`
conforms to `src/ccf/agents/assembler.py::ContextAssemblerProtocol` structurally
— it inherits nothing, and imports the Protocol only so that a reader and a test
can check the conformance the type system is otherwise silent about. That seam
had never been exercised by a shipped example. An example that reached past it
to the spine would have proved nothing about it, which is why
`examples/cp-00-institutional-holders/run.py::main` goes through the assembler
and not around it.

**Two substrates, deliberately visible as two.** The CCF graph is a per-run
local file this process creates and throws away. The system of record is a
separate relational store this deployment only ever *reads*. The smaller example
`examples/s1-00-companies-over-revenue` puts both on one substrate; that is one
deployment, not a rule, and a reader who generalised from it would have learned
the wrong lesson. Nothing in
`examples/cp-00-institutional-holders/produce.py::assemble_and_serve` knows which
arrangement it is running under, because the kinds are declared in
`ccf_config.yaml` and composed in `backends.yaml`.

**The threshold is the caller's, not the deployment's.** It is a request
parameter, declared **required with no default**. Two thresholds are two
products with two content addresses. It is applied at Π and never in the graph
query, so every threshold compiles to the *same* pinned read — which is what
makes "the rows assembled" one well-defined set rather than a per-caller one.

### The shape of the data — read this before you read a number

> **These examples teach METHOD — how to engineer and construct a Context Product
> with the CCF SDK — not the figures.** Every count and dollar amount in this
> tree is here to show how a specification binds to a real store, and for no
> other reason.
>
> The surrounding data estate carries **deliberately engineered names and relationships** — measured estate-wide across the tables that carry a
> provenance column: 30,365 rows marked `synthetic — engineered`, 13,840
> `synthetic — internal` and 20 `derived` — even though the two tables *this*
> product reads carry none of them. `ccf_v2.institutional_holder` measures
> 22,476 of 22,476 rows and `ccf_v2.legal_entity` 156 of 156 rows at
> `provenance = 'public'`.
>
> **No number here is a fact about any real company.**
>
> What a reader is actually looking at is **one quarterly archive spanning many periods** — 46 of them, one of them pinned by the specification — rather than a live feed.
> Its issuer matching is **~22.5% `weak` BY DESIGN** rather than by defect.
> The weak band travels with the row and is filtered nowhere: it is a
> completeness signal this product *declares*, not a defect it removes in
> silence.
>
> What is deliberately **not** said: these rows are public regulatory filings.
> Calling their behaviour invented would be inaccurate in the cautious
> direction, which misleads a reader about what they are holding exactly as
> badly as overclaiming would.

Those four statements are repeated beside each figure cluster below rather than
left here as a header to scroll past.

## Run it

### Before you run

This example reads a **live system of record**, and it reaches it through one
declared environment variable and through nothing else:

```sh
export CCF_CP_00_POSTGRES_DSN="postgresql://<read-only-role>@<your-host>/<your-database>"
```

**What the variable must point at:** a PostgreSQL database carrying the `ccf_v2`
schema with the two 13F tables this product reads — `institutional_holder` and
`legal_entity`. **What the role needs:** `SELECT` on those two tables and
nothing more. **What it must not have:** any write privilege at all. Nothing
this product runs writes to the store it reads, and the connection is opened
read-only in `examples/cp-00-institutional-holders/deployment.py::source_dsn`'s
caller; a role without write privilege makes that a property of the deployment
rather than a promise of the code.

**No host, no port, no credential and no path to anybody's `.env` appears
anywhere in this tree, and none may be added.** `backends.yaml` holds the
variable's *name* and a remedy string, and holds nothing else — a connection
value is deployment environment, not Control Plane state, and a DSN written
into a content-hashed artifact is a DSN persisted into the audit plane forever.

**There is no default and no fallback.** An unset variable raises, carrying the
remedy `backends.yaml` itself declares, from
`examples/cp-00-institutional-holders/deployment.py::source_dsn`. That absence
of a fallback is the mechanism keeping the tree free of connection values: there
is nothing in-tree to fall back *onto*.

### The one command

```sh
make example-cp-00
```

Optional, and both are optional for the same reason — a build tool is not a
request channel:

```sh
make example-cp-00 MIN_POSITION=500000000     # your threshold, as a request parameter
make example-cp-00 SPEC=brief                 # front matter and the step table only
```

Omit `MIN_POSITION` and `examples/cp-00-institutional-holders/run.py::main` asks
the demonstration question declared in `artifacts/question.yaml`. **That default
lives in the artifact, not in the code and not in the Makefile.** The contract
still declares the parameter required with no default: a request that omits it
is refused as `missing-required-parameter`, returned as data, below this CLI. A
CLI convenience and a contract obligation are different things and nothing here
conflates them.

`--explain` prints the governance transcript: the operators invoked, the TTL
anchor, the assembly mode read off replay dimension 3, the graph snapshot
instant, the completeness and semantic-consistency factors, what was consulted
and which skills were in force.

### What CI does instead

CI cannot reach a LAN host, and the live-legs workflow carries no database
secrets, so `tests/examples/test_cp_00_output.py` **stands up a `postgres:16`
service container itself** and seeds it from
`tests/examples/fixtures/cp_00_13f_schema.sql` and `cp_00_13f_rows.sql`. The
fixture is seeded by the test and never committed as a database. One code path,
two substrates: the module runs this example's own modules against the seeded
store, and computes its expected answer by issuing the very `SELECT` this
example argues against, so the assertions come from an independent instrument
rather than from a remembered number.

`make example-cp-00` proves the program **runs**. `make leg-postgres` proves it
is **correct**. The target is deliberately *not* a prerequisite of the always-on
`examples:` aggregate: always-on CI is network-free, and a red check nobody can
make green is worse than no check.

## The story

An analyst covering one issuer needs to know **who holds it and how much**,
above a position size they choose, for one reported filing period. The
specification declares what that product is; the artifacts declare this
deployment's vocabulary; and
`examples/cp-00-institutional-holders/produce.py::assemble_and_serve` makes the
fabric calls — in seven named regions, and it names no table, no column, no
entity, no artifact key, no substrate, no parameter and no number.

Before the seven, two things happen that are worth separating.

**Step 1 of the specification's operator table runs at the source boundary, and
it is a real operator.** The anchor issuer fans out across several candidate
securities in one reported period — six at the anchor, in the estate this was
written against — and only one of them is the security the question is about.
`examples/cp-00-institutional-holders/deployment.py::DominantSecurityResolution`
conforms to `src/ccf/operators/base.py::Operator`, declares the canonical
category `traversal`, is registered into and resolved back out of this
deployment's own `src/ccf/operators/registry.py::OperatorRegistry`, and ranks the
candidates by number of filed positions with the tie broken on the URI ascending.
Its result is expressed as the **subgraph** it returns, because `apply` returns a
view and an operator cannot emit a scalar. It is example-scoped and adds no name
to the SDK.

**Then the door.** `src/ccf/products/request.py::refuse_request` compares the
caller's request against the surface the class declares — the address first, then
the class-declared parameters, whose declared world is closed. This runs *before
the graph is touched*, so a question this class does not answer costs nothing and
returns a reason rather than an approximation. The verdict is a value, not an
exception: a bad question is a bad question, not a broken deployment, and a
verdict returned as data cannot be swallowed by a bare `except`.

Then the seven, in the order they run:

1. **`boot`.** One call — `src/ccf/deployment/config.py::load_config_and_boot` —
   reads the single `ccf_config.yaml`, derives and parses every section it names,
   registers the `role: register` ones into the Control Plane, and boots L2/L3 on
   the resulting pins. Connection values arrive here **from the caller**; the
   configuration declares the backend as a *kind* and never as a location.

2. **`ingest`.** The L1 envelopes — one per filed position on the resolved
   security — are handed to the booted worker, which is the **only** write handle
   to L3 anywhere in the process. Nothing else holds one and nothing can obtain
   one. The system of record is not reachable from here at all: the fabric's
   write path leads into the fabric's own state and nowhere else.
   `src/ccf/assembly/worker.py::SpecDrivenEntityResolution` selects its rule by
   the *presence* of a key in the envelope payload, so one envelope asserts both
   the anchor issuer and that row's holder.

   The instant on each envelope is the **reported quarter end**, never this run's
   clock. That single mapping is what the whole freshness story turns on: it
   becomes the claim's `valid_from` — when the *source's* fact began to hold —
   which is what the λ_c curve reads. A column a plain `SELECT` ignores becomes a
   measured `D_c`.

3. **`operators`.** The graph is read at the temporal boundary the request asked
   as of, and the L4 registry is built from whatever parameter sets the deployment
   declared. This one declares two, and the spine never counts them.
   `src/ccf/operators/categories.py::PolicyFilter` runs first — it is not
   decorative even where it excludes nobody, because that is where the ordering
   is learned, and it can *empty* the answer if an entity class has no
   classification attribute declared. `src/ccf/operators/categories.py::TemporalAsOf`
   holds the boundary: a claim whose valid interval does not cover it is a later
   filing, and serving it would answer a different question.

4. **`project`.** Π runs at L5 through
   `src/ccf/projection/engine.py::ProjectionEngine`.
   `examples/cp-00-institutional-holders/deployment.py::HoldersOverThresholdProjection`
   keeps the managers whose reported position is **at or above** the caller's
   number — the comparison is `>=`, declared in the payload so a consumer never
   has to infer it — and ranks them by position descending, then by the identity
   authority ascending, so the order is total and the bytes are stable. The
   Standard's `Evaluate` lives here too, for a result-shape reason rather than a
   determinism one: its modes produce *measures*, and an operator returns a view.

5. **`gate`.** Registering the TTL ceiling is what **mints** its pin, which is
   why the ceiling reaches this call through the deployment rather than through
   the class document. The product is then built with the lineage the Control
   Plane *claims* — filled from the declaration, never copied out of the
   execution, because a claim copied from a transcript is a transcript — and the
   three validation gates run in `src/ccf/products/gates.py::run_gates`. A
   `src/ccf/products/gates.py::ServableProduct` is not constructible outside that
   call, so holding one *is* the evidence the gates ran.

6. **`record`.** The five-dimension Decision Replay record is built by
   `src/ccf/replay/record.py::build_replay_record` from the execution, the served
   product, the perspective and the pins in force — including the question that
   was asked, parameters and all, so replay re-asks the same question rather than
   a similar one.

7. **`serve`.** `src/ccf/replay/serve.py::serve` persists the executed graph
   queries, then the record, and **delivery is what the successful append
   returns**. There is no branch that reaches a served product without a recorded
   decision, and no moment at which the record pins a question the store cannot
   resolve.

### What the answer carries that a `SELECT` does not

The run prints it under *"What a plain SELECT would not have told you"*: the
measured Context Debt and its routing signal, the policy-bundle version in force,
the product's content address, the replay record's address, the assembler's
identity and version, and the pinned debt profile.

The debt figure is the one worth reading twice, because it is **measured, not
declared**. `D_c = 1 − (F · C · S)`. `F` is a decay computation over the rows the
fabric *assembled* — not the rows the caller's threshold selected, because
scoring the survivors would make an impossibly high threshold *raise* instead of
answering *"nobody"*. `C` is two components multiplied and named separately:
completeness over the declared attribute keys, and the fraction of rows whose
issuer match is `strong`. `S` is 1, and the reason is stated rather than left as
a magic constant — there is exactly one source here, and a single source cannot
disagree with itself.

The half-life is 137 days: one calendar quarter plus the 45-day filing deadline
the source's own reporting rule sets. The demonstration question is asked 148
days after the pinned quarter end, which puts `D_c` near 0.56 — inside this
deployment's nominal serving band and below its forced-LLM threshold of 0.60,
which `ccf_config.yaml` annotates at that exact figure as *serves, nominal*. Those bands were
computed with `src/ccf/halflife/debt.py::FreshnessScorer` rather than by hand,
and their arithmetic is written out in `ccf_config.yaml` so an engineer can
challenge the numbers instead of assuming they were derived. For a Mode 1
product the forced-LLM band is a **disclosure** band, not a routing instruction:
there is no model in the path to route to.

**About those figures, restated where you meet them.** They teach the method of
constructing a Context Product, never the numbers; the estate around this
product carries names and relationships that were put there on purpose; not one
of them is a fact about any real company; and what they describe is a quarterly
archive of 46 filing periods rather than a live feed, in which roughly a fifth
of the rows carry a `weak` issuer match because the matcher was built to say so.

### What the specification's latency column is *not*

`spec/CP-SPEC-000-institutional-holders.md` §D.2 publishes a p95 budget per step
and `artifacts/assembly-recipe.yaml` carries the same numbers as data with
`budgets_are_measured: false` beside them. **That flag is still true and stays
true:** not one cell in the budget column was derived from a measurement. They
are design targets an engineer is invited to challenge.

**AMENDED 2026-08-27.** This section used to end *"Nothing has been measured.
No timing claim in this tree is a measurement."* That is no longer so, and the
old sentence is kept here rather than deleted because the distinction it was
protecting is the one that still matters. What changed: the assembly was **run
40 times against the live estate** and its latency measured end to end — **p50
10,141 ms, p95 11,786 ms** — with the instrument named beside the numbers in
§G. What did **not** change: the per-step budget cells are still declarations,
so a reader must not read the measured total back into the column. And the
engineer challenged the budget and **lost by an order of magnitude** — the
measured p95 is **11.8×** the declared 1,000 ms envelope, essentially all of it
in the L2 ingest of 1,748 envelopes at ~5.7 ms each. §D.2 attributes it step by
step; the specification's own §F marker 15 records what is closed and what is
still open, which is the per-call cost in money, because this deployment has no
meter and a guessed dollar figure would be worse than an honest gap.

## Artifact-by-artifact

Every file in the tree, what it holds, and which side of the line it sits on.
`[MECHANISM]` is the fabric's and you would write it whatever your domain;
`[ADAPT]` is yours.

| File | Side | What it holds |
| --- | --- | --- |
| `spec/CP-SPEC-000-institutional-holders.md` | `[ADAPT]` | **The specification, and the reason the rest exists.** Seven sections to the Standard: decision frame, contract, data catalog, assembly recipe, volatility and debt, source binding, operate and govern. Printed by the example before its own output. Every `[TBC]` in it is a marked gap with a named owner rather than a guess. |
| `ccf_config.yaml` | `[ADAPT]` | **The whole Control Plane configuration, in one document.** The backend *kind*; the product class and its declared operator keys; the two operator parameter sets; the request contract; the entity- and relationship-resolution rules; λ_c; the debt bands; the policy regime; the default perspective. Every value carries the specification section that authored it. |
| `backends.yaml` | `[ADAPT]` | **How a connection is composed — never a connection.** Two blocks kept visibly apart: `profiles:` for the CCF graph (a per-run local file under the caller's run root) and `sources:` for the system of record (an environment variable's *name* plus the remedy string an operator reads when it is unset). No host, port, path or credential. |
| `artifacts/question.yaml` | `[ADAPT]` | **The caller's vocabulary** — the anchor LEI as `subject`, the intent, the freshness requirement, the instant the question is asked as of, the pinned reported period, and the threshold the bundled demonstration asks. `role: load`: a question is not a permission, so it belongs in no Control Plane state and in no replay dimension. |
| `artifacts/ttl.yaml` | `[ADAPT]` | The class's TTL (365 days — the amendment window, not the filing cycle) and its ceiling. Separate from `ccf_config.yaml` because registering the ceiling's *value* is what mints its pin, so the value cannot be a field of the document whose pin it becomes. |
| `artifacts/expected.yaml` | `[ADAPT]` | **What the served product should contain, declared** — so the test module has a source for its expectations other than itself. It derives nothing from a run and there is no regeneration target. It deliberately carries **no row count**: a count is a fact about the store's contents at the moment of the read, not about this product's declaration. |
| `artifacts/assembly-recipe.yaml` | `[ADAPT]` | **The specification's §D operator step table, as data.** Per step: the operator, the SDK mechanism, the layer, the inputs, what it emits, its failure behaviour, its budget — and a **witness**, a fact a completed run either produced or did not. A prose table cannot be held against a run; this one can, and a step nothing executes is red. |
| `produce.py` | `[MECHANISM]` | **The fabric's half, and `[ADAPT]` nothing.** Seven named marker regions and no domain vocabulary at all. Delete `ccf_config.yaml` and this module has nothing left to interpret. It asserts nothing and prints nothing. |
| `deployment.py` | `[ADAPT]` | **This deployment's own values, and `[MECHANISM]` nothing.** The source vocabulary (schema, two tables, their columns), the attribute names those columns become inside the fabric, the two connection functions, the L1 read, step 1's operator, Π, and the scenario the spine asks for. It makes no fabric call the spine does not. |
| `assembler.py` | mixed | **The producer seam, implemented.** The seam is the SDK's; the identity and wiring are yours. Conforms to `src/ccf/agents/assembler.py::ContextAssemblerProtocol` by structure, not by inheritance, and says in its own docstring why it is not `src/ccf/agents/assembler.py::DeterministicAssembler`. It prints nothing and opens no marker region. |
| `run.py` | `[ADAPT]` | **The client.** It prints the specification, asks the question through the assembler, prints the JSON, and prints what a plain `SELECT` would not have told you. It asserts nothing; the assertions live in `tests/examples/`. It carries **no** marker region, so not one printed line is published-snippet surface. |

Exactly one module drives the run and prints — `run.py`. Exactly one opens the
canonical marker regions — `produce.py`. Both are deliberate, and both are
checked.

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §7.3 — the Context Graph in mechanism detail: the compound unique
  index, the idempotent upsert with multi-source lineage accumulation, and
  single-writer enforcement at boot
- whitepaper §7.4 — Context Operators and the canonical categories, two of which
  this product's plan declares and one of which it supplies itself
- whitepaper §7.5 — Context Projection Π as a typed transformation
- whitepaper §7.6 — the Context Product Contract and its three validation gates
- whitepaper §7.7 — Context Half-life λ_c and Context Debt `D_c`, measured over
  what was assembled rather than declared beside it
- whitepaper §7.10 — Decision Replay, and the record written before delivery
- CLAUDE.md §6.1 / §6.2 — the assembler as an SDK-defined producer surface, and
  the skill-set in force at decision time (empty here, as a positive statement)
- CLAUDE.md §6.4 — the No-Hardcoding Rule: every threshold, entity class,
  attribute name, TTL, λ_c rate and policy regime is an artifact
- CLAUDE.md §9 — the examples suite discipline: thin generic code beside
  artifacts that carry everything specific
- CLAUDE.md §10 — the L1–L6 layering and the single-writer invariant
- CLAUDE.md §11 — Working Principles

## What to change first

**`produce.py` is the file you do NOT change.** Every line in it is a call you
would have to make anyway, and it names nothing of this domain. If you find
yourself editing it to fit your data, the thing you actually needed was an
artifact.

In order:

1. **`backends.yaml`** — point `sources:` at your own store by declaring your own
   environment variable's name and your own remedy string. Change the `profiles:`
   block only if your CCF graph belongs somewhere other than a per-run local
   file. Neither block gains a value; between them they hold a name and a rule.

2. **`ccf_config.yaml`'s `resolution:` section** — your entity classes, your
   identity keys, your attribute keys and your relationship rules. Every
   attribute key here is a name your reader must emit and a name completeness
   counts, so a key that differs between the two is a silently missing attribute
   that moves your `C` factor.

3. **`deployment.py`'s source block and reader** — your schema, your tables, your
   columns, and the read that pins whatever axes your specification fixes.
   Keep the read *threshold-independent* if you want the freshness figure to
   describe what the fabric read rather than what one caller selected.

4. **Π** — replace `examples/cp-00-institutional-holders/deployment.py::HoldersOverThresholdProjection`
   with your own computation. This is the one piece of real code you write. Give
   it a **total** sort order, or your payload hashes two ways for one input.

5. **`ccf_config.yaml`'s `product_class:` and `request_contract:`** — your schema
   name and lane, your TTL anchor, your assembly mode, and the questions your
   class answers. A parameter the class never declared is refused rather than
   forwarded.

6. **`ccf_config.yaml`'s `half_life:` and `debt_profile:`, together** — these are
   regulatory posture rather than tuning; they decide when your fabric escalates
   instead of answering. Set them *together*: bands chosen in ignorance of the
   half-life refuse your product on its first call.

7. **`artifacts/assembly-recipe.yaml`** — your steps, each with a witness. If a
   step you want to declare cannot name a witness, the honest response is to
   remove the step, never to invent a sixth kind of witness.

8. **`spec/CP-SPEC-000-institutional-holders.md`** — re-author it. Not last in
   practice: write it **first**, then discover what the SDK can and cannot
   express, and record what it cannot rather than quietly reshaping the
   specification to fit.

9. **`artifacts/expected.yaml`** — last, after one reviewed run. Expect a failing
   `pytest tests/examples/test_cp_00_output.py` until you do; that failure is the
   workflow, not a bug.

## What would fail

| What goes wrong | What you see, and where it comes from |
| --- | --- |
| `CCF_CP_00_POSTGRES_DSN` is unset | A `RuntimeError` naming the variable and carrying the remedy string `backends.yaml` itself declares, raised in `examples/cp-00-institutional-holders/deployment.py::source_dsn`. There is no default and no fallback — that is the mechanism, not an inconvenience. |
| A request omits the threshold | `missing-required-parameter`, returned **as data** by `src/ccf/products/request.py::refuse_request` and refused **before the graph is touched**. The demonstration's fallback is a CLI convenience in `artifacts/question.yaml`; the contract has no default. |
| A request carries a parameter the class never declared | `undeclared-parameter`, at the same door. The declared world is closed: a parameter that reached plan selection undeclared would be an argument nobody governed. |
| The lineage the product claims is not what the engine resolved | **Gate 2**, strict equality in *both* directions inside `src/ccf/products/gates.py::run_gates`. A declared operator that did not run and an operator that ran undeclared are both refusals. This is why the claim is filled from the declaration and never copied out of the execution. |
| The product's operator set is empty | **Gate 1**. An answer assembled by nothing is not servable. |
| The TTL is out of bounds | **Gate 3**, and it produces two very different refusals. If it names the **lower** bound, the pinned period is more than 365 days old and *the gate is working* — this example has a written shelf life. If it names the **upper** bound, the deployment's `MAX_TTL` is below 31,536,000 s and the deployment is mis-configured. Raise the ceiling; do not shorten the product's TTL to fit a default nobody chose. |
| The anchor resolves to no security in the pinned period | Fail closed, never an empty payload — raised at the source read before anything is ingested. |
| The as-of boundary is set to the reported quarter end | The view **empties**, and **no shipped gate catches it**. This is the natural mistake after reading the TTL anchor, and it is why the assembly recipe declares an `entities_assembled` witness: the boundary must be at or after the ingest instant, because a claim's `observed_at` is when the fabric learned it. |
| A gate refusal is treated as something to proceed past | It cannot be. `src/ccf/products/gates.py::ServableProduct` is not constructible outside `run_gates` — the attempt raises `src/ccf/products/gates.py::GateBypassError` — so holding one is evidence rather than an assumption, and the refusal branch in the spine is reachable. |
| A prompt, a threshold, an entity class or a routing value appears in code | The No-Hardcoding Rule (CLAUDE.md §6.4). Delete `ccf_config.yaml` and `artifacts/` and neither `produce.py` nor `deployment.py` has anything left to interpret; an example that still ran meaningfully without them would have violated the rule. |
| A domain value drifts into the spine | The spine/deployment split. `produce.py` names no table, column, entity, artifact key, substrate, parameter or number, and `deployment.py` makes no fabric call the spine does not. |

Nothing in that table is checked by `run.py`. The template this README is written
to is checked by
`tests/examples/test_cp_readme_template.py::test_every_context_product_readme_matches_the_template`;
the recipe's step-for-step witnesses by
`tests/examples/test_cp_00_recipe_steps.py::test_every_declared_step_is_witnessed_by_the_run`;
the served answer against an independent `SELECT` by
`tests/examples/test_cp_00_output.py::test_the_threshold_selects` and its
neighbours; that no module here imports an LLM client by
`tests/examples/test_cp_00_is_algorithmic.py::test_no_context_product_module_imports_an_llm_client`;
and the No-Hardcoding row by `python -m tools.lints --all`.
