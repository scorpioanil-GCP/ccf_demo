# The golden `13bd250` decision record

A `DecisionReplayRecord` with one traversal step over SQLite, **produced by
the `13bd250` tree** (`13bd250e7a9d9ea12daf596ef86597557aad702f`, the Phase
24.5 base, before any 24.5 field existed) and **replayed at HEAD** by
`tests/replay/test_golden_13bd250.py`. It is the fixture `D-IMPL-243` requires
("The fixture is the gate") in the shape amendment 1 rules: leg 1, the
`13bd250` record matches on every marked-`True` field; leg 2, a planted
marked-`False` field refuses by name.

## What is here

| File | What it is |
| --- | --- |
| `produce.py` | The deployment — plan, operators, envelope, product envelope, `ReplayEnvironment` — written to import under both trees. Under `13bd250` it produced everything below; under HEAD the test imports it for the same deployment. |
| `fabric.sqlite3` | The graph the decision was made against, written by the `13bd250` tree's SQLite adapter. Read-only from here on; every test copies it. |
| `artifacts/401bfc181108a613c8bf2e08ced35bee9a96a0a18f2426a49881e94876affadc` | The record's canonical bytes, exactly as the `13bd250` tree's `FileArtifactStore` wrote them. The file name is their sha256. |
| `artifacts/.artifact-names.json` | The store's naming index (`D-IMPL-26`), as written. |
| `manifest.json` | Every identity the record carries, read off the record at production: the record address, the per-step `parameter_hash`es, the `graph_query_sequence` pins, `product_content_address`, `graph_snapshot_id`, and the Control Plane versions the base tree minted. |

## The exact command that produced it

From the repository root, with the `13bd250` tree extracted to `<base>` by
`git archive 13bd250 src tests runtime | tar -x -C <base>`:

```sh
GOLDEN_PRODUCING_COMMIT=13bd250e7a9d9ea12daf596ef86597557aad702f \
PYTHONPATH=<base>/src:<base>/runtime \
.venv/bin/python tests/replay/fixtures/golden_13bd250/produce.py \
  tests/replay/fixtures/golden_13bd250
```

`manifest.json` records `ccf_package_file` — the `ccf/__init__.py` the
producer actually imported — so the tree that wrote the fixture is a
measured fact, not a claim. `produce.py` refuses to overwrite an existing
fixture; to reproduce, run it into an empty directory and `cmp` the record
bytes.

## What the record proves at HEAD

Every 24.5 field the record's walk, lineage and snapshot carry sits at its
sentinel — no admission on the hop, an undirected walk, no store pin — so
under "silence equals yesterday" HEAD's canonicalizer renders the walk
byte-for-byte as `13bd250` did, and `replay()` returns a `ReplayOutcome`
with the recorded `parameter_hash` (`904a3022…`), the recorded pin
(`f1a105fb…`), the recorded product address (`2580912f…`) and the recorded
snapshot id (`21ec74c0…`). Disable one `True` mark in memory and the same
replay raises `ReplayDivergence` — CR-01, on demand. Plant a `False` on a
field the record lacks and it is refused as `canonical_generation_mismatch`,
by name, before a binding is resolved.

Nothing here is edited after production. A new golden record for a later
generation is a new directory named for its producing commit, never a
rewrite of this one.
