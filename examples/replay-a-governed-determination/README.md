# replay-a-governed-determination — reconstruct a decision from its record

The adopter-facing form of the replay proof every paved producer carries in its
own test suite. One script, no product of its own: it opens a paved product
tree, asks one question, and reproduces the recorded determination through the
SDK's own engine — `ccf.replay.engine.replay` for a served product,
`replay_refusal` for a refused one — with an environment built from the record
and the deployment's two documents.

The walkthrough is the published how-to, **Reconstruct a governed
determination**, which literal-includes the two regions of `replay.py`. This
README states only what the page cannot: what to export, and what the script
does not do.

## Run it

The producer's own environment names must be exported — for the default tree,
`examples/cp-06-canonical-collateral-and-setoff-coverage`, those are the
`CCF_CP_06C_*` variables its `ccf_environment.yaml` declares, pointing at the
curated estate (read-only; nothing here writes).

```sh
.venv/bin/python examples/replay-a-governed-determination/replay.py
.venv/bin/python examples/replay-a-governed-determination/replay.py --refuse
```

The first reproduces a served product and prints the record address, the
product address, and the address the replay reached; the second asks with a
scope nobody holds and reconstructs the refusal.

## What it does not do

- It calls **no producer** and invokes **no question mapping**: the recorded
  operator path is re-executed over the recorded snapshot, and every retained
  input is read from the store by content address.
- It **re-derives nothing the record carries**: the anchor instant, the debt in
  force, its evidence, the refresh recency and the obligation are copied off
  dimension 5 verbatim.
- It reaches one **private** SDK member — `GovernedResolver._operator_parameters`
  — to bind each operator's parameter artifact from the effective request. That
  dependency is named in the module docstring and on the how-to page, not
  hidden, and it is why this script lives beside the product trees rather than
  inside one.
- It is not a replay framework and not a CI suite. The tested reference is
  `tests/examples/test_cp_06_canonical_output.py`'s replay controls; this is
  the same recipe, written for a reader.
