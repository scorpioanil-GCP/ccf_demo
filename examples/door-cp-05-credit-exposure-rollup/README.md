# The exposure door — frozen cp-05 reached through the SDK's standard door

`credit-risk.exposure-rollup` @ `1.0.0` · producer `cp-05-credit-exposure-rollup-egress` under
tenant `cp-05-demo` · reads the curated `.76` estate through the frozen specimen's own
variables, writes nothing · the CP-14 completion GO, exposure option 3

**Not a product tree. A door.** `examples/cp-05-credit-exposure-rollup` is frozen
(`D-IMPL-261`, `D-IMPL-281`) and determines gross and adjusted exposure in its assembler,
after the traversal and before Π (`D-IMPL-299`). The paved road has no seam there
(`CP14-F-33`), and that limitation stands: nothing here relocates the aggregation, adds a
hook, or copies the spine. The specimen's low road — `produce.produce_governed` — already
runs the whole governed path and returns a delivery-minted `ServedProduct` or a recorded
`RefusalEnvelope`; this tree presents that path to `open_door` through the door's own
structural contract (`ServesProducts`, nine members) so CP-14's exposure slot can reach it
from another process under the identity CP-14 registers.

## What this demonstrates

**The escape hatch, and its measured cost.** `adapter.py` is 190 physical lines, of which
about 80 are code: nine attributes read off what the frozen tree already holds, one
`resolve` that translates a `ProductRequest` into the specimen's call, the two
pre-assembly refusals the specimen's own door recorded, and ONE guard the frozen tree
needs and cannot express — the instant. `server/serve.py` is the same 27-line launcher
every paved producer ships. No door, resolver, recorder, producer assertion or replay
machinery is re-implemented.

**The three exposure relationships Dave asked to be preserved, proven through the door**
(`tests/examples/test_door_cp_05_exposure.py`):

- **Materiality changes the presented subset, not the totals.** Two materialities: the
  material roster and its floor move; the gross and adjusted totals, the family and the
  reconciliation do not; every facility-holding member is material or residual under both.
- **The declared limit regime governs the calculation.** Two regimes over the specimen's
  own anchor: the one that counts guarantees and undrawn amounts deduplicates guarantee
  paths and adjusts below gross; the one that counts neither leaves adjusted equal to
  gross with no undrawn. The gross total is the same under both.
- **Deduplication and reconciliation still operate**: `guarantee_dedup.cases` moves with
  the regime; `reconciliation.family_gross_committed` equals the served gross under both.

**Both outcomes, neither promised.** At the labeled diagnostic tolerance (1.0) the frozen
producer SERVES the CP-14 obligor's rollup and the paved consumer admits it under
`provider-controls`; at the governed 0.25 the same producer WITHHOLDS (`tolerance-exceeded`
— its balances are days old against a four-hour half-life, `D_c` 1.0 `fail_closed`), and
the producer's own reason is retained on the consumer's record. Nothing was tuned.

**The instant guard.** The frozen assembly takes no `asked_at`; it answers at the instant
its own `artifacts/question.yaml` pins. A question at any other instant is refused BY NAME
with a replay record — never answered at the pin and presented as the caller's, which a
consumer's admission could not tell apart (`CP05D-F-01`). CP-14's demonstration instant
coincides with the pin; the coincidence is disclosed, not relied on silently.

## Run it

```
export CCF_CP_05_FLUREE_URL=http://<host>:8090   CCF_CP_05_FLUREE_LEDGER=fibo-v2
export CCF_CP_05_POSTGRES_DSN=postgresql://...     CCF_CP_05_POSTGRES_SCHEMA=ccf_v2
make example-door-cp-05                              # prints `READY {port}` and serves
.venv/bin/python examples/door-cp-05-credit-exposure-rollup/run.py --door
```

To ask the product in-process, use the frozen specimen's own `make example-cp-05`. The v2
namespaces are not in `ccf_dataprep/.env`, which names v1.

## The story

### 0. Nine attributes the frozen tree already holds

Tenant, class declaration, default perspective, a Control Plane for the door's
entitlement, the ONE refusal recorder over the specimen's own replay binding, the door
binding from `artifacts/door.yaml`, the environment document beside it, and `resolve`.
`open_door` takes the structural type (`product_door.py`: *"a deployment composed by hand
on the low road reaches the same door with the pieces it already holds"*). This tree is
the first shipped caller of that hatch.

### 1. One call behind `resolve`

`produce_governed(anchor, intent, depth, materiality, debt_tolerance, basis,
follow_guarantees, follow_cross_default, as_of, replay_root)` — the specimen's own
signature, its own two boots per question, its own record on both branches. The wire's
`families` and `freshness` cannot reach it (no such keywords); they are disclosed as the
frozen-tree pass-through gap, not refused, because the specimen never judged either.

### 2. What CP-14 sees

The registration CP-14 already holds — `cp-05-credit-exposure-rollup-egress` /
`cp-05-demo`, offering `credit-risk.exposure-rollup` from `1.0.0` — is what this door
asserts; wrong producer id and wrong tenant refuse independently at the consumer.

## Artifact-by-artifact

| file | role |
|---|---|
| `artifacts/door.yaml` | the door's identity: producer id, producer tenant, required scope, tool description |
| `ccf_environment.yaml` | the NAMES the door's credential and advertised URLs are read from; an inert substrate block the document's contract requires |
| `adapter.py` | the nine members and one `resolve`, over the frozen specimen's modules |
| `server/serve.py` | the standard door launcher, stdio or loopback |
| `run.py` | `--door` only; presentation |
| `FINDINGS.md` | the escape-hatch cost, the frozen-tree limitations, the known carries |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §7.6 (delivery-minted products only cross the door), §7.10 (a record on both
branches). CLAUDE.md §7.1 (the standard egress door), §9 (frozen specimens; the estate is
evidence), §13 (the SDK ships mechanism). `D-IMPL-299` (assembly determines exposure;
projection presents), `D-IMPL-340` (cross-deployment admission), `D-IMPL-343` (the standard
door over a structural product).

## What to change first

`artifacts/door.yaml` for another identity; `ccf_environment.yaml` for other variable
names. To change what is served, change the frozen specimen — which is to say, build its
paved successor; this tree exists precisely so that is not required to finish CP-14.

## What would fail

Re-implement the door or the recorder in `adapter.py`; assert an identity other than the
specimen's tenant; answer a question at another instant at the pin; edit one specimen
file. Each is asserted by `tests/examples/test_door_cp_05_exposure.py`.
