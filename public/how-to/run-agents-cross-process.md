# Run agents cross-process

Have an assembler agent produce a typed Context Product in one process and a
decisioning agent consume it in another — over MCP egress and over A2A
federation — with the consuming Control Plane verifying the product before it
is allowed anywhere near the graph.

Two SDK commitments meet on this page. MCP is a bidirectional surface
(CLAUDE.md §7.1), so the same product is readable as an MCP Resource by any
MCP-capable runtime. A2A federation is a v0 commitment rather than a deferral
(CLAUDE.md §7.2), so a product crossing an organizational boundary carries its
policy bindings with it and is admitted only after the consumer verifies
them. The single-writer invariant
survives the crossing: an admitted product still reaches the graph through the
assembly worker and nowhere else.

Everything below is literal-included from `examples/04-cross-process`, which
runs two real OS processes in CI.

## Before you start

You need two fabrics — the producer's and the consumer's — and a signing key
for the producer that lives outside the repository tree. See
[manage keys and secrets](security-and-deployment.md) for the key-custody
posture; nothing on this page puts key material in version control.

Run the worked example with:

```sh
make example-04
```

## Step 0 — two deployments, two manifests

Producer and consumer are separate deployments with separate Control Planes,
separate graphs, and separate replay records. Each boots from its own manifest,
and the consumer's names its own resolution spec, its own policy bundle, and its
own view of what it will admit:

```py
--8<-- "examples/04-cross-process/run.py:boot"
```

Several of the consumer's documents are content-identical to a producer
document and are still separate files. That is deliberate. The agreement between
the two is what admission checks, and an agreement stated once and read by both
sides could not fail.

## Step 1 — declare who you trust

The consumer's Control Plane states, as a versioned artifact, exactly which
peers it will admit from: which signing keys are theirs, which producer
identities may claim them, which product schemas they may send, and which
policy regimes those products may assert. Anything outside that statement is
refused, however validly it is signed. The
[peering Protocols](../reference/protocols/peering.md) document the typed
surface, and the
[Control Plane artifacts reference](../reference/artifacts/control-plane-artifacts.md)
covers versioning:

```yaml
--8<-- "examples/04-cross-process/artifacts/peering-trust.yaml"
```

Note what is *not* in that document: key material. Signing keys are generated
per run and never committed, so what an artifact can carry is the trust-policy
request — which identifier the peer may sign under, which producing agent it may
assert, which schema it may send, which regime it may claim. The driver
completes it with the run's public key, registers it, and pins it to a version.
A payload ceiling is registered alongside it, because a trust boundary that will
accept an arbitrarily large body is not a boundary:

```py
--8<-- "examples/04-cross-process/run.py:peer-trust-policy"
```

## Step 2 — stand up the admission gate

The gate is the one door an inbound product may pass through. It holds the
identity provider that verifies signatures, the Control Plane it checks
policy bindings against, the audit log every verdict lands in, and the store
that keeps admission records:

```py
--8<-- "examples/04-cross-process/run.py:peer-gate"
```

## Step 3 — start the producer and receive

The producer runs in its own process with its own fabric, graph, and key. It
announces readiness on stdout with the ports it bound, so there are no fixed
ports and no sleeps anywhere in the handshake:

```py
--8<-- "examples/04-cross-process/run.py:peer-spawn"
```

## Step 4 — read the product over MCP

The first front door. The product is fetched as an MCP Resource and validated
against the typed contract — see the
[Context Product Protocols](../reference/protocols/context-products.md). What
ties the two transports together is that the bytes MCP served are exactly the
bytes the A2A signature was made over, so both doors serve one product rather
than two renderings of one; the example's test module asserts that byte
equality:

```py
--8<-- "examples/04-cross-process/run.py:mcp-egress"
```

## Step 5 — admit over A2A

Admission verifies the signature against the peer's own trust entry, then
checks the policy bindings, and only then merges lineage. Nothing reaches the
graph before that call returns. It returns a refusal *value* rather than
raising, so a driver that ignored the result would proceed with nothing
admitted; matching on the admitted case is what makes the boundary
unskippable. Merging is a set-union: the producer's operator plan, policy
versions, and graph snapshot survive alongside the consumer's. Inbound lineage
extends the consumer's; it never replaces it:

```py
--8<-- "examples/04-cross-process/run.py:peer-admit"
```

Before anything is reported admitted, an immutable admission record is
persisted at an exact content address, and the audit verdict points at it by
that address. The driver reads the address back off the audit log and resolves
the record through the store. There is no "latest" and no overwrite path — see
the [artifact store Protocols](../reference/protocols/artifact-store.md):

```py
--8<-- "examples/04-cross-process/run.py:peer-admission-record"
```

## Step 6 — let it into the graph, through L2 only

The admitted value enters the graph through a door on the assembly worker
that is typed to accept nothing but a gate-produced admitted product. The
graph digest is taken before and after to show that the substrate moves only
at that call:

```py
--8<-- "examples/04-cross-process/run.py:peer-ingest"
```

## Step 7 — verify the negative path

A real signature spliced onto different payload bytes, sent over the real
socket, is refused as a typed value, and the consumer's storage is
byte-identical before and after. The refusal is audited too, and the example's
test module asserts the audit entry. A trust boundary you have not watched
refuse something is a trust boundary you have not tested:

```py
--8<-- "examples/04-cross-process/run.py:peer-refusal"
```

## What to change first

Start in `artifacts/producer-peering.yaml` and `artifacts/peering-trust.yaml`.
Replace the peer identities, key identifier, and producer hash with your own,
and set the consumer's inbound ceilings and receive path to your deployment's
numbers and URL space. The two documents state one federation relationship from
both sides; change them together or admission will refuse, which is the check
working.

Then rename the tenant in both manifests and swap the vocabulary in
`artifacts/resolution-spec.yaml` and the payloads in `artifacts/events.yaml`.

On the next run, expect the served product and the merged lineage to change;
review the output and update `artifacts/expected.yaml` in the same commit.
Neither driver changes, which is the point.

If your deployment needs a different wire, the Context Product contract is
the stable layer and the transport is replaceable — see the
[runtime surfaces reference](../reference/protocols/runtime-surfaces.md).
