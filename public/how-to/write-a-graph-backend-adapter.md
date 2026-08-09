# Write a graph backend adapter

Put a graph substrate CCF has never heard of behind the fabric, shipped as your
own installable distribution, with no line changing in the SDK.

An adapter is found through an entry point, resolved by name, and held to the
same conformance suites the built-in adapters run. Nothing about that path is
reserved for adapters written by this repository: the seam is the published
surface, and a third-party adapter reaches it the same way.

The smallest complete worked example is `tests/fixtures/ccf-demo-adapter/` in
the SDK repository — a real second distribution that registers an adapter named
`demo` and runs in CI beside the built-in adapters. Read it alongside this page;
everything below is in there in about 900 lines, and its own `README.md` is the
companion to this one.

## Before you start

You need a substrate that can store rows and give them back, and you need to
decide one thing early: **whether your adapter will translate queries at all.**
It does not have to. Declining pushdown is a first-class outcome — the SDK's
shared fallback answers every query family over materialized records, so an
adapter that translates nothing is still a conforming adapter, and it is the
tier a third party reaches without reimplementing the query surface. Start
there; add native translation later, when you have a measured reason.

## What an adapter owes

Six things, and no base class you must inherit from except one.

| # | What | Shape |
| --- | --- | --- |
| 1 | A **store** | Satisfies the `BackendStore` Protocol: a `graph_identity` property, a `reader` property, and `close()` |
| 2 | A **reader** | Satisfies the `GraphReader` Protocol — the read seam the operators run against |
| 3 | A **transaction** | Implements the nine typed write operations |
| 4 | A **writer** | Subclasses the SDK's neutral `BaseGraphWriter`, contributing the transaction and nothing else |
| 5 | A **config model** | Your connection settings, deriving from `CCFContract` |
| 6 | A **registration** | One `BackendRegistration` record naming all of the above |

Only #4 is inheritance. Everything else is structural: you conform by having
the right shape, not by importing a class and extending it
([Protocols over inheritance](../concepts/invariants.md)).

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

## How the fabric finds your adapter

Declare an entry point in the `ccf.graph_backends` group pointing at the
`REGISTRATION` object in your write module:

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

Discovery never imports your package — listing what a deployment has installed
reads metadata only. Only resolving your adapter by name imports it, and it
imports exactly one adapter. So an installed adapter nobody selected costs a
deployment nothing, and your module-level code does not run at every boot.

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

Those last two refusals fail the *whole* discovery call, not just the offending
name. That is deliberate and fail-closed: an environment whose answer to "which
code does this name select" is ambiguous has not earned a boot.

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

You do not declare your adapter's version or distribution name. The registry
**derives** both from your distribution's own installed metadata, which is why a
third-party adapter gets its replay pin for free and cannot misstate it.

## What a development checkout looks like

`make install` installs the SDK and then installs the demo fixture adapter, so
in any development checkout `ccf backends list` reports the fixture's name
alongside the built-in ones.

That is the command answering correctly about the environment it is in — the
question it asks is *what is installed here* — and not a statement that the
fixture is a supported substrate. It is a test fixture, and it is **not** a
dependency of the `ccf` distribution, so installing CCF never pulls it.

## The private-surface gap, stated plainly

**Some of what an adapter needs is not exported.** As of the phase that added
the out-of-tree proof, six names an adapter reaches for are absent from their
modules' `__all__`: `materialize_view`, `_ordered_view`, `_entity_records`,
`_relationship_records` and `_LineageRowsFor` from the graph reader module, and
`_GraphTxn` from the writer's private module.

None of them is currently avoidable. Ordering belongs to the interface rather
than to an answerer, so an adapter that sorted results for itself would fork the
convention the shared helper exists to hold; and the entity and relationship
record helpers have no public counterpart at all, so history reads are not
implementable from public names alone. The SDK's `BaseGraphReader` *is* public
but is SQL-shaped — it expects SQL statements and a `_query(sql, params)` — so a
non-relational store cannot use it.

This page states the gap rather than routing around it: the surface a
third-party adapter must reach for is not yet the same as the published surface,
and closing that distance is an open decision rather than something an adapter
author can fix. Write against these names knowing they are private, and expect
them to be the part of your adapter most exposed to churn.

## How to prove it works

Run the two conformance suites with your adapter as a parameter. They are the
acceptance bar, and they are the same bar every built-in adapter clears:

- **The `GraphStore` conformance suite** asserts the six invariant write
  semantics every conforming backend must carry.
- **The substrate differential suite** asserts that your adapter's answers over
  the generated query corpus are **byte-identical** to the shared fallback's,
  plus determinism and the tenant boundary.

Byte-identity is the honest bar precisely for an adapter that declines pushdown:
the fallback answers, so the assertion is that routing through your store
changed nothing. If you *do* add native translation later, the same suite is
what catches a translation that disagrees with the prose.

A parity test asserts that the suites' parameter lists and the set of registered
adapters agree in both directions, so an installed adapter that no parameter
names fails loudly instead of producing a suite that passes while testing one
substrate fewer.

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
