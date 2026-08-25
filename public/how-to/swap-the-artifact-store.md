# Swap the artifact store

Move your deployment's persisted artifacts — replay records, products at
rest, Control Plane bundles — from the file-backed development store onto an
MCP-backed store of your own, changing one configuration artifact and nothing
else.

That "nothing else" is the whole claim of CLAUDE.md §7.4. Persistence sits
behind a Protocol; the SDK ships a file-backed reference for development and
an MCP-backed reference for everything else; and users who want their own
substrate stand up an MCP server implementing the artifact resource contract
rather than forking anything. The store is a substrate reached *through*
mechanism — it never becomes a second writer to the graph.

Everything below is literal-included from `archive/examples/07-artifact-store-mcp`,
which runs the identical workload twice against the two stores in CI and
asserts the results are byte-identical.

## Before you start

You need a workload that already persists something — the
[adopter's guide](../tutorial/adopters-guide.md) gets you to a served product
with a replay record. You need an endpoint for your own store, and
credentials for it. The
[artifact store Protocols](../reference/protocols/artifact-store.md) document
the surface an alternative implementation must satisfy.

Run the worked example with:

```sh
PYTHONPATH=src:runtime python archive/examples/07-artifact-store-mcp/run.py
```

## Step 1 — put the store choice in an artifact

Two configuration artifacts, the same shape, a different declared type. This
pair is the entire swap surface:

```yaml
--8<-- "archive/examples/07-artifact-store-mcp/artifacts/store_file.yaml"
```

```yaml
--8<-- "archive/examples/07-artifact-store-mcp/artifacts/store_mcp.yaml"
```

Neither file names a Python symbol, and neither is read by anything except
the factory below. Endpoints and roots are templated from environment
variables so no absolute path and no live endpoint is committed.

## Step 2 — construct through one factory seam

A factory keyed on the declared type is the only place in the deployment
where a backend is named. Everything downstream receives whatever the
artifact declared:

```py
--8<-- "archive/examples/07-artifact-store-mcp/run.py:store-factory"
```

## Step 3 — let the workload persist, without naming a backend

These are the only store-touching lines in the whole workload. The replay
writer, the product at rest, and the policy bundle are three of the artifact
kinds §7.4 puts in scope; each returns a reference carrying both a versioned
URI and an exact content address. The
[Control Plane artifacts reference](../reference/artifacts/control-plane-artifacts.md)
covers how those versions are minted:

```py
--8<-- "archive/examples/07-artifact-store-mcp/run.py:store-persist"
```

## Step 4 — run it twice

The driver runs the workload against the file-backed store, starts the
MCP-backed store as a real subprocess, waits for its readiness handshake and
health check, and runs the *same function* again with only the configuration
name differing. One workload, called twice — that is the structural form of
"nothing else in the deployment changes":

```py
--8<-- "archive/examples/07-artifact-store-mcp/run.py:store-swap"
```

Two properties make that structural rather than merely stated, and both are
worth copying into your own deployment. The workload takes exactly *one*
per-run parameter, so there is nothing else that could vary between the calls.
And both runs boot from the same manifest:

```py
--8<-- "archive/examples/07-artifact-store-mcp/run.py:boot"
```

The store is deliberately **not** a manifest field. Which substrate persists
your artifacts is a deployment environment choice, the same kind of thing as a
database connection string — and a substrate named in a registered,
content-hashed artifact would land in replay dimension 2, making the two runs
genuinely differ in what was in force.

## Step 5 — assert the substrate was invisible

The assertions run under `pytest`, in
`tests/examples/test_artifact_store_output.py`. Three of them, in increasing
strength:

- The served product's canonical bytes match across the two runs.
- The same artifact kinds landed under the same versioned URIs at the same
  content addresses — checked against the role set the deployment declares, so
  a run that quietly stopped persisting one of them fails rather than agreeing
  with itself about nothing.
- Every URI the MCP run recorded resolves against a *fresh* client back to its
  exact address, with the exact bytes behind it — never a "latest" lookup,
  which is what makes replay determinism survive the swap. See
  [replay anatomy](../concepts/replay-anatomy.md).

Two further tests read the example's own source and refuse a second per-run
parameter or a store named in the manifest, so the "nothing else changes"
property cannot be lost to a later edit without a red build.

## What to change first

Edit `artifacts/store_mcp.yaml`. Point its endpoint at an artifact MCP server
of your own implementing the artifact resource contract, and put your
deployment's credentials in the auth block — sourced from your secret store,
not from the tree, per
[manage keys and secrets](security-and-deployment.md). Nothing in the driver
changes. On the next run expect the same URIs printed with your server behind
them, and the same byte-identical product.

Second, `artifacts/resolution-spec.yaml` and `artifacts/events.yaml` for your
own vocabulary and signal stream, then update `artifacts/expected.yaml` to
match what you reviewed. The artifact kinds and names your deployment files
things under live in `artifacts/product-governance.yaml`. Every document in
force is enumerated by `artifacts/manifest.yaml`, so a new artifact is not in
force until it is named there.

Hot graph state and versioned artifacts may sit on different substrates — the
live graph stays on the graph storage Protocol
([storage and Context Graph](../reference/protocols/storage-and-graph.md))
while the artifact store holds the versioned material.
