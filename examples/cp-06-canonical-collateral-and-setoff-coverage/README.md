<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
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
make example-cp-06-canonical ASKED_AT=--asked-at=now          # refused: see below
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
```

The default question is the one `CP-SPEC-014` asks: BGC Group's facility `FAC-5B8418`,
intent `lgd-assessment`, freshness `as-filed`, the obligor as the borrower scope, asked at
**2026-09-07T12:00Z**. The v2 namespaces are not in `ccf_dataprep/.env`, which names v1.

**The demonstration clock (amended 2026-10-11).** `ccf_config.yaml` declares a labelled
**demonstration serve instant**, 2026-09-07T12:05Z (`demonstration_serve_instant:`,
`D-IMPL-378` C1, honored on the paved road since the SDK round of 2026-10-11): the product
— in-process and through its door alike — serves as if it were five minutes after the
demonstration question, inside its one-hour `temporal_boundary`. It is the one time anchor
this tree's runs share with `CP-SPEC-014`, `dr-01` and `dr-02`; nothing on a question can
move it; the SDK refuses it outside its own development substrates; every replay record
written under it names the declaration. Until this amendment the default asked at the
wall clock; it now asks the dated demonstration question, and `--asked-at now` is refused
`asked-at-outside-temporal-bound` (an instant after the serve clock is outside the boundary). With
the declaration removed, the demonstration question is refused
`asked-at-outside-temporal-bound` on the real clock
(`tests/examples/test_cp_06_canonical_output.py::test_the_demonstration_question_on_the_real_clock_is_refused_as_expired`).
A question at a different dated instant needs a deployment declaring its own anchor: set
`serve_instant` five minutes after it first.

**Asking the retained evidence** (`D-IMPL-383`, 2026-10-16). With `CCF_REPLAY_EVIDENCE_ROOT`
set to a private (mode `700`) folder, the door keeps every decision's evidence there, and
three commands answer from it without serving or asking a new question:

```
SERVE=examples/cp-06-canonical-collateral-and-setoff-coverage/server/serve.py
.venv/bin/python $SERVE decisions --involving 2549001IGRCG4F0RLD36 --since 2026-10-13 --until 2026-10-13
.venv/bin/python $SERVE why <decision>      # why it refused, or the policies, inputs and data it used
.venv/bin/python $SERVE replay <decision>   # re-executes it from the evidence: REPRODUCED or not
```

`--involving` takes an identifier (a facility id or a legal-entity identifier), not a
company name. A bare date covers that whole local day; times print in UTC and local time.
A decision is named by its record address or a unique prefix of at least 8 characters.
The commands need none of the four source variables above: they open the product with
`read_sources=False`, which replays and explains but answers no new question (`CP06C-F-07`).

**A source that cannot be reached is a recorded refusal, not a crash** (`CP06C-F-06`,
2026-10-16). `ccf_config.yaml` declares the two legs' connection errors under
`seam_refusals` with `cause: source-unavailable`, so an outage answers `source-unavailable`
— *"a source this product reads could not be reached … ask again later"* — and is kept,
listed by `decisions` and explained by `why` like any other decision. The driver's own
message, which names hosts and ports, stays in the record. Any other failure still
propagates: only the product can say a failure is an outage rather than a defect.

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
intent), and a scope the caller does not hold is **refused** (`CSCC-G20`; the specimen
serves a coverage of zero over it). Both are deliberate differences, recorded in
`CP-SPEC-006C` §G.3 and in `FINDINGS.md`, never averaged into the lane comparison.

### 4. "No such facility" and "not in your scope" are one answer

Acquisition looks the facility up once. If there is no such facility, or its borrower is
not in the `borrower_scope` the caller stated, it refuses right there — before any
collateral, set-off or register read — through two refusals declared in `ccf_config.yaml`
`seam_refusals`. At the default disclosure level both come back as the same
`subject-unavailable` answer, byte for byte apart from the fresh replay digest and the
echoed facility id, through the bank's own door on both routes (`CSCC-G25`), and both make
the same source calls (`CSCC-G26`). The record keeps which it was: `facility-not-held` or
`outside-requested-borrower-scope`, never the borrower's identifier. Before this
(SEC-020, measured 2026-10-16), an unknown facility escaped as an opaque runtime failure
with no record while an out-of-scope one was fully read and then refused — so the answer,
and the time it took, told a caller whether the facility existed.

What remains, stated rather than hidden: an existing facility's lookup still returns one
row where an unknown one returns none (`verify.py --timing` measures it against a rule
fixed beforehand); a caller who names the right borrower, or every borrower, still learns
the facility exists, because `borrower_scope` is the caller's statement and not a
permission (SEC-020 Part 4, provisional); and the scope rule is now stated twice — in the
policy step and in acquisition — because the SDK applies the policy step only after
acquisition (`CP06C-F-09`, a candidate SDK ease-of-use blocker, kept visible by a strict
expected failure).

## Artifact-by-artifact

| file | role |
|---|---|
| `ccf_config.yaml` | the product, its request contract, operators, resolution rules, λ_c table, D_c profile, policy, perspective, replay binding, TTL and door — one document, one authority per value |
| `ccf_environment.yaml` | the NAMES the two sources and the door's credential are read from; no value |
| `artifacts/source-vocabulary.yaml` | every IRI, table and column the two legs read |
| `artifacts/projection.yaml` | Π's declared values: seniority ranks, the unknown rank, the lien-priority basis note, the sharing roster cap |
| `artifacts/gates.yaml` | the twenty-six declared product gates and the tests that claim them |
| `spec/CP-SPEC-006C_…md` | the successor's specification, Gate 1 approved 2026-09-16 |
| `produce.py` | the spine: `boot` and `answer` |
| `deployment.py` | `acquire`, the envelopes (edges first), `assess`, the gate |
| `acquisition.py` | the two legs, unchanged from the specimen except that the road hands it its settings, and that one facility lookup now decides whether anything else is read (SEC-020) |
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
(`G19`); let a scope the caller does not hold past the facility lookup (`G20`); let an
unknown facility raise instead of refusing (`G25`); check the scope only after the graph
walks (`G26`); mint the substrate once per opened product (`G22`). `CSCC-G23` is live since `D-IMPL-341` (validation pass
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

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

**And it can still fail.** At the CP-14 instant 47 of the 50 facilities with pledged
collateral serve and 3 are refused `ttl-bounds` on evidence older than an appraisal cycle;
`CSCC-G24` holds that refusal on one of them, and `CSCC-G23` holds the anchor on the
facilities that serve.
