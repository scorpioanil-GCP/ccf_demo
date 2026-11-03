# DR-01 — Replay a Governed Determination

> **Current execution baseline:** SDK `v1.0.2@5f85b389`. Follow [setup and configuration](../../examples/CONFIGURATION.md); dated qualification results below retain their original scope.

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/dr-01-replay-a-governed-determination/README.md`  
**Qualified specification:** DR-01 is a replay capability over an already-specified product; the default demonstration uses `examples/cp-06-canonical-collateral-and-setoff-coverage/spec/CP-SPEC-006C_Collateral_And_Setoff_Coverage_Canonical.md`.  
**Qualified source:** `examples/dr-01-replay-a-governed-determination`

> **Read the DR-01 README and the default product's qualified specification before opening `replay.py`.**

## Why this example exists

DR-01 is the smallest adopter-facing proof that a governed determination can be reconstructed from its retained record.

It demonstrates **both outcomes**:

- a served Context Product, reconstructed with `replay()`;
- a governed refusal, reconstructed with `replay_refusal()`.

The replay does not ask the producer the question again. It does not re-acquire the source estate. It re-executes the recorded operator path over the recorded snapshot and holds the result to the addresses and governance state the decision recorded.

## Prerequisites

Complete the producer/data-estate setup in the parent README first.

The default example opens:

`examples/cp-06-canonical-collateral-and-setoff-coverage`

Export the `CCF_CP_06C_*` variables declared by that product's `ccf_environment.yaml`.

From the SDK repository root:

```bash
make venv
```

## Files to read

Read in this order:

1. `examples/dr-01-replay-a-governed-determination/README.md`
2. `examples/cp-06-canonical-collateral-and-setoff-coverage/spec/CP-SPEC-006C_Collateral_And_Setoff_Coverage_Canonical.md`
3. `examples/dr-01-replay-a-governed-determination/replay.py`
4. `src/ccf/replay/environment.py`
5. `src/ccf/replay/engine.py`
6. `src/ccf/replay/record.py`

The product spec tells you what determination was authorized. DR-01 then shows how that already-made determination is reconstructed.

## Run a served determination

```bash
.venv/bin/python examples/dr-01-replay-a-governed-determination/replay.py
```

The script opens the default CP-06 product, asks the pinned question, reads the resulting replay record, builds a `RecordedEnvironment`, and reconstructs the product through the SDK replay engine.

## Run a refused determination

```bash
.venv/bin/python examples/dr-01-replay-a-governed-determination/replay.py --refuse
```

This asks with a borrower scope the principal does not hold and then reconstructs the **refusal itself**.

A refusal is a first-class decision. It has a replay record even though it has no product address.

## Two addresses

A served determination has two different addresses:

- **record address** — the content address of the five-dimension replay record;
- **product address** — the content address of the served Context Product.

The record names the product that was served.

A refusal has a record address but no product address.

## The supported environment

The adopter-facing environment is:

```python
RecordedEnvironment(
    record=record,
    opened=opened,
    fabric=fabric,
)
```

`RecordedEnvironment` reconstructs the deployment-side ingredients from:

- the retained replay record;
- the opened product;
- the fabric scoped to the recorded snapshot.

It uses the deployment's own plan factory and the **effective request recorded on dimension 2**, not today's caller parameters.

## What replay holds fixed

The engine holds the reconstruction to recorded state, including:

- exact replay-record address;
- exact artifact/policy versions;
- recorded graph snapshot;
- recorded operator sequence;
- recorded operator parameters;
- effective request resolution;
- child contracts/questions where composition occurred;
- TTL anchor and expiry basis;
- Context Debt and debt evidence;
- source refresh recency;
- obligation in force;
- served product content address.

A wrong plan, wrong parameter set, wrong snapshot, rebound declaration or different product bytes fails loudly.

## Validate it

The default DR-01 recipe is the adopter-facing form of the replay controls on the canonical CP-06 product.

Run the two focused controls:

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tests/examples/test_cp_06_canonical_output.py::test_replay_reproduces_the_served_product_from_the_recorded_graph_inputs \
  tests/examples/test_cp_06_canonical_output.py::test_a_refused_determination_reconstructs_through_the_344_path_without_a_product \
  -q
```

## What to vary

### Refusal path

Start with `--refuse`. This is the most important variation because it shows that replay is not limited to successful product delivery.

### Another paved product

`replay.py` accepts `--tree`, `--subject`, `--intent`, `--freshness`, `--asked-at`, and `--parameters`.

Only point it at another product when you also supply that product's valid request and environment. The default arguments are CP-06-specific.

### Tamper controls

The tests are the right place to study negative controls. Replay is meaningful because a changed plan, parameter hash, artifact version, snapshot or product address is rejected rather than approximately reproduced.

## What this proves

- A served determination can be reproduced to the same content address.
- A governed refusal can be reconstructed as a refusal without inventing a product.
- Replay uses retained/pinned state rather than current state.
- The supported `RecordedEnvironment` removes the old need for hand-built replay environments.
- Replay is part of the governed delivery model, not a post-hoc audit log.

## What it does not prove

- That missing retained evidence can be recreated later.
- That replay may contact the original producer or re-acquire source data.
- That every arbitrary product tree can use the CP-06 command-line defaults.
- That replay repairs a bad or incomplete historical record.

## Engineering lesson

The design principle is:

> **Retain enough governed evidence at decision time that reconstruction is possible without trusting today's world.**

That is why the record contains five dimensions and why exact-version/content-address checks are part of replay rather than optional audit metadata.
