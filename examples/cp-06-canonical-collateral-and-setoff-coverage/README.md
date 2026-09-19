# Collateral & Set-off Coverage (canonical) — rung 6 on the paved road

`credit-risk.collateral-coverage` @ `1.0.0` · Tier 2 · Fluree `fibo-v2` + PostgreSQL
`ccf_v2` · reads the curated `.76` estate, writes nothing · `CP-SPEC-006C`

**The same product as the frozen rung-6 specimen, served by a different producer
with a fifth of the plumbing — and with the one number Π divides by recorded in
the graph instead of carried in from the side.**

## What this demonstrates

**Producer substitution on the paved road.** `examples/cp-06-collateral-and-setoff-coverage`
is frozen (`D-IMPL-261`) and still serves on the low road. This tree serves the same
class from its own tenant and its own door, and the lane it serves was **decided by
measurement**: at the CP-14 instant, for both facilities `CP-SPEC-006C` §A.2 names, the
successor's canonical payload hashes to the specimen's, field for field (`CSCC-G13`). So
it is `1.0.0` — a second producer of one product — and what differs is exactly what a
sibling under its own tenant cannot share: `tenant_id`, `plan_id`, the policy-bundle
version. Payload equivalence is not contract identity.

**The commitment IS the graph.** The specimen handed its Π the facility's commitment and
an enforceability register through a closure over acquisition. The paved road hands Π
the effective request and nothing from the side, so here the facility node carries its
commitment as an attribute, every deposit node carries its own enforceability, and Π
reads the governed view (`CSCC-G14`). A facility the view does not know the size of is
refused by the product's own gate; nothing substitutes a zero.

**What the road removed.** No registry, boot call, effective-request re-derivation,
ingest loop, fifteen-keyword builder call, store, record readback, hand-written door or
`door.yaml`. Two documents, two regions, four callables.

Six things the product shows, unchanged from the specimen, each of which changes the
conclusion rather than the decimals: haircuts, set-off, the jurisdiction basis, the
allocation basis, per-asset valuation dates, and a lien the register says was released.

## Run it

```
export CCF_CP_06C_FLUREE_URL=http://<host>:8090   CCF_CP_06C_FLUREE_LEDGER=fibo-v2
export CCF_CP_06C_POSTGRES_DSN=postgresql://...     CCF_CP_06C_POSTGRES_SCHEMA=ccf_v2
make example-cp-06-canonical
make example-cp-06-canonical FACILITY=--facility=FAC-044206 SCOPE=--scope=529900E95812SYWMCE44
make example-cp-06-canonical ASKED_AT=--asked-at=2026-09-07T12:00:00+00:00
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
```

The default question is the one `CP-SPEC-014` asks: BGC Group's facility `FAC-5B8418`,
intent `lgd-assessment`, freshness `as-filed`, the obligor as the borrower scope. The v2
namespaces are not in `ccf_dataprep/.env`, which names v1.

## The story

### 0. Two regions, and the SDK owns the rest

`produce.py` binds `acquire`, `project`, `assess` and `gate` to the two documents in one
`open_product` call and asks one governed question. The door is `open_door` over the
same opened product, reached by `run.py --door`.

### 1. The commitment moved into the graph, and replay can now reconstruct it

`deployment.envelopes` puts `commitment` on the facility node; `resolution.entity_rules`
admits it; `projection.py` reads it off the anchor's own node in the view. A changed
commitment in the view changes the ratio in inverse proportion, and Π's constructor takes
no commitment and no jurisdiction register, so there is no side channel to obtain the old
value from. Replay rebuilds the product from the recorded snapshot with no acquisition
object alive.

### 2. The lane is a measurement, not a claim

Both declared facilities at `2026-09-07T12:00:00+00:00`: full canonical payload hashes
equal, zero field-level differences, the same debt factors, the same expiry. The frozen
specimen is the control, run in-process by the same test against the same estate.

### 3. Two governed axes the specimen left open

`intent` is judged on the declared discovery set (`CSCC-G19`; the specimen accepts any
intent), and a scope the caller does not hold yields an empty graph **and a refusal**
(`CSCC-G20`; the specimen serves a coverage of zero over it). Both are deliberate
differences, recorded in `CP-SPEC-006C` §G.3 and in `FINDINGS.md`, never averaged into
the lane comparison.

## Artifact-by-artifact

| file | role |
|---|---|
| `ccf_config.yaml` | the product, its request contract, operators, resolution rules, λ_c table, D_c profile, policy, perspective, replay binding, TTL and door — one document, one authority per value |
| `ccf_environment.yaml` | the NAMES the two sources and the door's credential are read from; no value |
| `artifacts/source-vocabulary.yaml` | every IRI, table and column the two legs read |
| `artifacts/projection.yaml` | Π's declared values: seniority ranks, the unknown rank, the lien-priority basis note, the sharing roster cap |
| `artifacts/gates.yaml` | the twenty-three declared product gates and the tests that claim them |
| `spec/CP-SPEC-006C_…md` | the successor's specification, Gate 1 approved 2026-09-16 |
| `produce.py` | the spine: `boot` and `answer` |
| `deployment.py` | `acquire`, the envelopes (edges first), `assess`, the gate |
| `acquisition.py` | the two legs, unchanged from the specimen except that the road hands it its settings |
| `projection.py` | Π, unchanged except that the commitment comes off the view |
| `server/serve.py` | the standard door launcher, stdio or loopback |
| `run.py` | presentation only |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §7.3 (single writer, thin edges first), §7.4 (policy before traversal, two
registered operators), §7.5 (Π reads the view), §7.6 (the three gates plus the product's
own), §7.7 (per-class λ_c, `D_c = 1 − F·C·S`), §7.10 (five-dimension replay; a refused
determination reconstructs through `D-IMPL-344`). CLAUDE.md §6.4 (no value in code),
§7.1 (the standard egress door), §9 (the estate is evidence; illustrative values
disclosed), §10 (L2 the only writer). `D-IMPL-340` (cross-deployment acquisition),
`D-IMPL-343` (the paved road), `D-IMPL-344` (refusal reconstruction).

## What to change first

The two documents. A different estate is four names in `ccf_environment.yaml`; a
different haircut policy or λ_c is `ccf_config.yaml`; a different set of edge types is
`artifacts/source-vocabulary.yaml` and the `traversal.typed-neighborhood` declaration.
`projection.py` is the domain and is yours to change; nothing in it is SDK mechanism.

## What would fail

Apply the haircut as a premium (`CSCC-G01`); count excluded set-off (`G02`); collapse
the two allocation bases (`G04`); drop the amendment walk (`G05`); flatten valuation
dates (`G07`); serve fabric URIs (`G09`); hand Π the commitment through a closure or a
module constant instead of the view (`G14`); compose the resolver beside the opened
product (`G15`); edit one specimen file or reuse its tenant (`G16`); take the producer
identity from the answer rather than the registration (`G18`); drop `discovery.intents`
(`G19`); serve a coverage of zero over an empty view (`G20`); mint the substrate once per
opened product (`G22`). `CSCC-G23` is live since `D-IMPL-341` (validation pass
2026-09-18): the served `expires_at` runs from the freshest asset valuation date the
admitted view carries, and the contract records that instant as `ttl_anchor_at`.

**The window follows the clock the anchor reads** (`FINDINGS.md` `CP06C-F-05`, ruled
2026-09-18). The expiry is anchored on the freshest asset valuation date, so the window
states how long a coverage answer stays current AFTER a valuation: it is the appraisal
cycle this product's own table declares (`half_life.real_property_appraisal`, ~365 days),
the cadence of the valuation class governing 74 of this estate's 95 pledged assets. It
replaced a one-day window taken from the deposit-balance half-life, which named a cadence
the anchor cannot read. **Illustrative calibration** under `D-IMPL-323`: this example runs
against a point-in-time demonstration estate rather than continuously refreshed production
data, and the value is chosen to make the governed behavior observable in that snapshot,
not as a recommended production coverage-policy threshold.

**What it does not claim.** It does not establish that the DEPOSIT BALANCES are fresh —
this estate's deposit records carry no as-of date at all, so they contribute no instant to
the anchor and nothing here dates the set-off leg, which is why coverage is served with
collateral value, set-off value and total kept apart. It does not claim every asset was
revalued within the window either: a marketable security is aged in `F` by its own one-day
cadence, and every asset's valuation date and age stay in the payload.

**And it can still fail.** At the CP-14 instant 47 of the 50 facilities with pledged
collateral serve and 3 are refused `ttl-bounds` on evidence older than an appraisal cycle;
`CSCC-G24` holds that refusal on one of them, and `CSCC-G23` holds the anchor on the
facilities that serve.
