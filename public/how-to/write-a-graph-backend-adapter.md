# Write a graph backend adapter

Put a graph substrate CCF has never heard of behind the fabric, shipped as your
own installable distribution. Your adapter declares itself, the fabric resolves
it by name, and the same conformance suites the built-in adapters run are the
bar it clears.

The smallest complete worked example is `tests/fixtures/ccf-demo-adapter/` in
the SDK repository — a real second distribution that registers an adapter named
`demo` and runs in CI beside the built-in adapters. Read it alongside this page;
everything below is in there in about 900 lines, and its own `README.md` is the
companion to this one.

## Before you start

You need a substrate that can store rows and give them back, and you need to
decide one thing early: **whether your adapter will translate queries at all.**
It does not have to. Declining pushdown is a first-class outcome — the SDK's
shared fallback (`ccf.graph.fallback`) answers every query family over
materialized records, so an adapter that translates nothing is still a
conforming adapter. Start there; add native translation later, when you have a
measured reason.

## What an adapter owes

Six things, and no base class you must inherit from except one.

| # | What | Shape |
| --- | --- | --- |
| 1 | A **store** | Satisfies the `BackendStore` Protocol: a `graph_identity` property, a `reader` property, a `writer_lease()` method, and `close()` |
| 2 | A **reader** | Satisfies the `GraphReader` Protocol — the read seam the operators run against |
| 3 | A **transaction** | Implements the nine typed write operations |
| 4 | A **writer** | Subclasses the SDK's neutral `BaseGraphWriter`, contributing the transaction and nothing else |
| 5 | A **config model** | Your connection settings, deriving from `CCFContract` |
| 6 | A **registration** | One `BackendRegistration` record naming all of the above |

Only #4 is inheritance. Everything else is structural: you conform by having
the right shape, not by importing a class and extending it
([Protocols over inheritance](../concepts/invariants.md)).

**#4 is checked, not merely asked for.** `boot()` refuses a `make_writer` that
returns anything other than a `BaseGraphWriter`, with a `TypeError` naming your
adapter — and it refuses it the same way a writer constructor that *raises* is
handled: the graph is released and the store is closed, so a corrected retry
boots. The reason is narrow and worth knowing: retiring a writer is what
releases the graph for the next boot, and only `BaseGraphWriter.close` does
that. A duck-typed writer with the two upserts and no `close` would boot
successfully once and then leave the graph unbootable for the life of the
process.

**The writer lease is required, and it declares its scope (SEC-013).**
`writer_lease()` is called by the boot mint only — after the in-process
"already has a writer" check passes, before a boot token exists — and never
when the store is opened, because a second read-only store over a live graph
is legitimate. The lease is held for the writer's life and released by
`BaseGraphWriter.close` (or by boot's failure path), always before your
store's `close()`. Return one of two things:

- **A cross-process lease** whose `scope` is `"cross-process"`: your substrate
  itself refuses a second holder, whichever process asks. Raise
  `WriterLeaseHeld` (from `ccf.graph.protocols`) at once when another holder
  has it; never block waiting. Boot turns that into the same
  `SingleWriterViolation` ("already exists") a second boot in one process
  raises. The SQLite reference store takes an `flock` on a sidecar beside the
  database file; the Postgres reference store takes a session advisory lock
  keyed server-side on the schema.
- **`ProcessScopedWriterLease(substrate="<your adapter name>")`**, whose scope
  is `"process"`. This is a **disclosure, not enforcement**: the only exclusion
  is the boot's in-process table, so two *processes* over one graph on your
  substrate are not refused. It is exact for a store no second process can
  reach (an in-process dict). A persistent network store should not return it:
  take a deployment-declared lease at construction and delegate `writer_lease()`
  to `acquire_declared_writer_lease` (from `ccf.graph.protocols`), which refuses
  the mint with `WriterLeaseRequired` when none is declared, as the reference
  network stores do (SEC-013, D-IMPL-374).

A store with no `writer_lease()` is refused at boot by name. The scope is
recorded on the boot token. See
[deployment posture](security-and-deployment.md#45-decide-how-many-processes-share-a-graph-sec-013)
for what each reference store's scope means for a deployment.

The nine transaction operations are `upsert_entity_node`,
`insert_entity_claim`, `select_entity_chain`, `update_entity_supersession`, the
four relationship twins of those, and `insert_lineage`. Two contract rules hold
across all nine and are easy to violate without noticing:

- **Row counts resolve before commit.** A re-arrival of a claim already stored
  must report zero rows affected — that is the writer's entire idempotency
  signal, and a substrate that reports the count after commit reports it wrong.
- **Reads inside a transaction see that transaction's own writes.** A
  `select_*_chain` following an `insert_*_claim` in the same transaction must
  see it.

## The registration record

`BackendRegistration` is the whole of what your adapter tells the fabric about
itself, and it is a record the fabric *interprets* rather than a class you
extend. Five fields:

| Field | What it carries |
| --- | --- |
| `name` | The name a deployment writes in its manifest to select you |
| `config_model` | The typed contract your connection settings satisfy |
| `secret_fields` | Which of those settings carry a credential |
| `open_store` | Constructs the store from validated settings plus resolved credentials |
| `make_writer` | Constructs the write handle from the store and the boot token |

**A conforming `config_model` derives from `CCFContract`.** That is not a
stylistic preference: `CCFContract` carries `extra="forbid"`, so a settings key
your adapter never declared is refused by the contract base rather than being
silently accepted. A model written against a plain open base would lose that
refusal, and no test anywhere would fail.

The record is declared as a **module-level `REGISTRATION`** in your write module
— see [where each piece goes](#where-each-piece-goes) — and that attribute name
is what both discovery paths look for.

`make_writer` is never called by the registry. The composition root calls it,
holding the boot token, and a test asserts it is the only caller under the SDK's
own `src/` and `runtime/` trees. Your adapter supplies the factory; it does not
decide when a writer exists.

## Where each piece goes

Two modules, and the split is not cosmetic:

```
src/your_adapter/
    store.py          # the store and the reader
    <name>_write.py   # the config model, the transaction, the writer, REGISTRATION
```

The `REGISTRATION` record lives in the **write** module, and your entry point
names that module. The read module is imported by many callers; putting the
writer factory there would place write-path code on an unguarded import path.
The write module may import the read module freely. The reverse is forbidden.

The same separation is enforced inside the SDK, from the other side. The neutral
write base lives in its own private module (`ccf.graph._writer`), and a
structural lint denies that module to every core module outside the assembly
layer and the composition root. Your package is not in that lint's scope — see
[what the lints do and do not cover](#what-the-sdks-lints-do-and-do-not-cover) —
but the convention it enforces is the one your two-module layout mirrors, and
following it is what keeps a reader import from dragging the write path along
with it.

## How the fabric finds your adapter

There are two discovery sources, and yours is the second.

**Adapters the SDK ships are found by reading module names off disk**, inside
the SDK's own adapter package. A directory read, never an import, and no
packaging metadata is involved — which is why a stale editable install cannot
make the fabric unbootable, and why an installed distribution cannot shadow a
name the SDK ships.

**Your adapter is found through the `ccf.graph_backends` entry-point group.**
Declare an entry point pointing at the `REGISTRATION` object in your write
module:

```toml
[project.entry-points."ccf.graph_backends"]
your_name = "your_adapter.your_name_write:REGISTRATION"
```

**Entry points live in build-time metadata, not in `pyproject.toml` as read from
disk.** Editing that file changes nothing until you reinstall:

```sh
python -m pip install -e .
```

This is the single most likely first failure. If `ccf backends list` does not
show your adapter after you added the declaration, you have not reinstalled.

Two functions, and the difference between them is what keeps discovery cheap.
`declared_names()` is the *listing* function — it reads both sources, applies
every name refusal, and imports nothing at all. `resolve(name)` is the
*selection* function, and it **imports exactly one adapter**: the one a
deployment named. So an installed adapter nobody selected is never loaded, and
your module-level code does not run at every boot.

## Naming rules

- A name matches `^[a-z][a-z0-9_]*$`: lower case, starting with a letter, no
  dots. Names are compared **exactly** — a versioned document should not need a
  convention to say which case won.
- **The names the SDK's own adapter package holds are reserved.** A distribution
  declaring one of them is refused during discovery, before anything loads, so a
  third party cannot answer for a built-in name. Run `ccf backends list` to see
  which names are taken in your environment.
- **Two installed distributions declaring one name is refused, naming both.**
  The fabric does not choose between them, and it does not resolve the name for
  anyone — the refusal reads as a packaging conflict and tells you which two
  distributions to look at.

`declared_names()` is **fail-closed on all three**: a duplicated, a reserved or a
malformed name declared by *any* installed distribution refuses the whole
discovery call, not just the offending name — including a boot of an adapter
that has nothing to do with it. That is deliberate: an environment whose answer
to "which code does this name select" is ambiguous has not earned a boot. Each
refusal names the distributions involved and says the requested adapter was
never reached, so a packaging conflict reads differently from an adapter that is
simply not installed.

The same fail-closed behaviour reaches the front door.
[`ccf backends list`](../reference/http-api.md) travels `GET /backends`, which
returns the sorted names on the success path and a `503` carrying the registry's
own refusal when the deployment's installed adapters conflict. The CLI holds no
local generation path of its own; it asks the route like any other client.

## Credentials

**Your config model holds references, never values.** A field like
`password_env_var` is a reference; a field holding a password is a defect. The
manifest names the reference, the deployment sets it, and the fabric resolves it
at boot.

A named reference that resolves to something unset or empty is **refused**, not
treated as "no credential supplied". A manifest that names a reference has
asserted a credential is required, so the fabric refuses rather than connecting
anonymously.

Two shapes, and the difference matters to exactly one of them:

- At the boot seam the fabric handles `ResolvedSecret` objects — config field,
  reference name, and value together in one object, so replay can pin *which
  reference* was in force without ever recording what it resolved to.
- **Your `open_store` receives a plain `Mapping[str, SecretStr]`, keyed by
  config field.** That is the whole of what you implement. The reference name
  travels only as far as the pin; you never see it and never need it.

Declare which config fields carry a credential in your registration's
`secret_fields`. An empty set is correct for a substrate with nothing to
authenticate to. A credential supplied for a field you did not declare is
refused, by field name.

`secret_fields` exists so the resolved value can be kept out of the *validated
settings model* entirely — the credential mapping arrives at `open_store`
separately, which is why a validation error over your connection settings has no
credential to echo. The no-persistence half is mechanism rather than discipline:
the SDK's canonical-bytes function refuses a `SecretStr` outright, so a resolved
credential cannot be content-hashed into a versioned artifact even by accident.
See [manage keys and secrets](security-and-deployment.md) for the deployment
side of that boundary.

You do not declare your adapter's version or distribution name. The registry
**derives** both from your distribution's own installed metadata, which is why a
third-party adapter gets its replay pin for free and cannot misstate it.

## What `query()` must answer

The read seam is one method — `GraphReader.query()`, taking a `GraphQuery` and
returning a `GraphView` — and what it *means* is defined normatively in
`docs/GRAPH_QUERY_SEMANTICS.md`, not here. That document is the authority a
dispute is resolved by quoting; its clauses carry `GQ-NN` ids, refusal messages
cite them, and semantic changes arrive as versioned amendments rather than as
silent drift. Read it before you write a translation, and cite clause ids in
your own tests.

Three properties of the seam shape every adapter, and are worth stating here
because they are the ones authors are surprised by:

- **A conformant answerer answers any well-formed query.** There is no
  capability negotiation and no refusal path on this seam. Where you hold no
  native translation you degrade internally to scan-and-filter; you do not tell
  the caller you cannot help.
- **The as-of view arrives as data.** Tenant scope and `as_of` are inside the
  frozen query value, so no answerer reads a clock and none takes tenant as a
  separate argument.
- **An empty answer is a legitimate value, never an error.**

Each issued query's content hash is the per-round-trip replay pin, recorded in
execution order, with the canonical query bytes landing in the ArtifactStore
keyed by those hashes. That is why the query value is frozen and why it carries
no version field of its own.

## How to prove it works

Run the two conformance suites with your adapter as a parameter. They are the
acceptance bar, and they are the same bar every built-in adapter clears:

- **The `GraphStore` conformance suite** asserts the six invariant write
  semantics every conforming backend must carry.
- **The substrate differential suite** asserts that your adapter's answers over
  the generated query corpus are **byte-identical** to the shared fallback's,
  plus determinism and the tenant boundary. The fallback is itself audited by a
  property suite, so the oracle is answerable to something it does not define.

A parity test asserts that the suites' parameter lists and the set of registered
adapters agree in both directions, so an installed adapter that no parameter
names fails loudly instead of producing a suite that passes while testing one
substrate fewer.

**Byte-identity does not measure your translation, and you should not read it as
if it did.** A staged adapter — one that narrows natively by the policy and
temporal families and leaves traversal to the fallback — is fully conformant
(`GQ-34`), because the degraded posture is byte-identical *by design*. So an
adapter that translates nothing and an adapter that translates everything both
pass the differential suite, which is exactly what makes it a correctness bar
rather than a performance one.

What a translation is proved by instead is its own counters. The SDK's reader
base exposes `translated_answers` and `fallback_answers` as per-instance,
monotonic observables; if you do not use that base, keep the equivalent
yourself. They are deliberately **outside** the replay record — what was
natively translated versus scanned is telemetry, and performance is never a
replay input. Assert on them in your own tests to show a translation you added
is the one answering.

## What a development checkout looks like

`make install` installs the SDK and then installs the demo fixture adapter, so
in any development checkout `ccf backends list` reports the fixture's name
alongside the built-in ones.

That is the command answering correctly about the environment it is in — the
question it asks is *what is installed here* — and not a statement that the
fixture is a supported substrate. It is a test fixture, and it is **not** a
dependency of the `ccf` distribution, so installing CCF never pulls it.

## What the SDK's lints do and do not cover

**The structural lints walk this repository's `src` and `runtime` trees. They do
not walk your package**, and neither does the SDK's type checker configuration.
That is a scope statement, not a hole — your adapter is governed by the Protocol
contracts and by the conformance suites instead.

The rule worth understanding is the one restricting imports of the neutral write
base. It denies that module to core modules outside the assembly layer and the
composition root, and it cannot reach a third-party adapter.

**Single-writer does not depend on it reaching one.** The mechanism is the
boot-token mint: it refuses a second live writer for one graph identity, whoever
asks, in-tree or out. The lint is the layer that stops a *core* module reaching
for the writer by accident; the mint is the layer that makes the invariant true.
Both halves are real, and an adapter author who knew only the first would have a
false model of why their adapter cannot corrupt the graph.

One consequence for you: **derive your graph identity from something that names
the graph**, not from the object instance. Two handles on one graph must report
the same identity, or the mint's refusal becomes a false negative and two live
writers coexist. Two genuinely different graphs must report different
identities, or it becomes a false positive and the second boot is refused for
nothing.

## What to change first

Take the worked example and replace two things: its store, and its nine
transaction operations. The registration record, the connection contract, and
the entry-point declaration are the shape every adapter has, and are closer to
boilerplate than to substrate work.

For the deployment side — how a manifest selects your adapter and supplies its
connection settings and credential references — see
[manage keys and secrets](security-and-deployment.md).
