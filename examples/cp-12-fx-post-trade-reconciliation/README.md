# cp-12 — FX post-trade reconciliation

**Rung 12 of the Context Product ladder · `markets.fx-reconciliation.v1`**

> **Why do two systems disagree about the same trade?**
>
> The answer depends on **whose clock you reconstruct against** — and on not
> counting one disagreement twice.

## What this demonstrates

Three systems report a value for the same FX trade. They disagree. The
conventional response is to declare a data-quality issue and pick one as golden.
**Frequently none of them is wrong**: the trading system booked at execution, the
settlement system recorded post-affirmation, and the risk system revalued at a
different market snapshot. All three are internally correct *as of their own
observation time* — and each system's clock is itself skewed by a recorded
amount.

Measured on this estate, the designed timing breaks span **4.08–8.00 pips** and
the designed genuine breaks span **4.01–7.93 pips**. **The ranges overlap almost
completely.** Nothing about the size of a discrepancy says which kind it is.

So this rung is about four things a `SELECT` cannot do:

- **Reconstruct against the true instant.** Each system's recorded instant is
  corrected by that system's recorded clock offset — trading `0 s`, settlement
  `+47 s`, risk `−112 s` — before anything is compared. `TRD-W12-0004` is the
  case that makes it visible: all three systems correct to **07:34:39 exactly**,
  and trading alone still differs. No amount of timing explains that.
- **Refuse to decompose what the evidence cannot resolve.** The rate series is
  5-minute and the observation gaps are frequently shorter. Reporting a zero
  timing component there says *the market did not move* when the truth is *the
  series cannot see whether it did*. The product returns `not-evaluable` with a
  reason — never a zero.
- **Keep the unit of analysis honest.** Three systems give three pairs, and every
  one of the 60 break trades partitions two-against-one. Counting pairs reports
  120 breaks where there are 60 — exactly `2.00×`, measured — and a middle office
  told it has 120 breaks staffs for twice the work.
- **Ask the question at the instant it was true.** 13 of the 60 breaks are
  material at amendment 0 and **gone** at the latest amendment, because the
  amendment reconciled the two systems. Current state has forgotten they
  happened. Both states are served; neither is silently substituted for the
  other.

**The clock offset is this product's context, not a new fabric clock.** The
corrected instant compares two systems and reaches no `valid_from`, no
`observed_at` and no Context Debt term. What the λ_c table ages against is the
instant the source *recorded*.

## Run it

```bash
export CCF_CP_12_POSTGRES_DSN='postgresql://USER:PASSWORD@HOST:5432/DATABASE'
export CCF_CP_12_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_12_FLUREE_URL=http://HOST:8090
export CCF_CP_12_FLUREE_LEDGER=fibo-v2

make -s example-cp-12
```

Both stores are read-only here; nothing this example runs writes to either. The
namespaces are the **v2** ones and are **not** in `ccf_dataprep`'s `.env`, which
names v1.

The demonstration question lives in `artifacts/question.yaml`. Every part of it
is overridable, because each is a **request** parameter and a build tool is not a
request channel:

```bash
make -s example-cp-12 COMPARE_AT=latest          # what current state sees
make -s example-cp-12 NO_ALIGN_CLOCKS=1          # conventional reconciliation
make -s example-cp-12 TRADES=TRD-W12-0004 SCOPE=TRD-W12-0004
make -s example-cp-12 DEBT_TOLERANCE=0.02        # ask for the refusal
```

The three axes produce three different answers and three different content
addresses. That is the point: a governed product's identity includes the
question it was asked.

## The story

`TRD-W12-0002`, USD/CAD, at amendment 0:

| system | rate | recorded | offset | **true instant** |
|---|---|---|---|---|
| trading | 1.388337 | 15:26:46 | 0 s | **15:26:46** |
| settlement | 1.388751 | 16:00:18 | +47 s | **15:59:31** |
| risk | 1.388337 | 15:24:54 | −112 s | **15:26:46** |

Risk *looks* like the outlier — it recorded before either of the others. Corrected
for its own −112-second skew it observed at the same true instant as trading, and
the two agree to the last digit. Settlement observed **33 minutes later**.

Ask the same question of current state and the trade is clean: amendment 1
reconciled all three at 1.3927. The break existed. It was worked, or it was not.
Current state cannot say which, because it has forgotten it happened.

`TRD-W12-0124` is where the product refuses. Its two compared instants are
**31 hours apart** across a weekend, and the nearest preceding tick is **20.0
hours** old. Revaluing against it yields a residual of **−72.49 pips** on a raw
variance of 5.15. The product reports `not-evaluable`, names the reason, and
carries the staleness — because a number with no meaning is worse than no number.

`TRD-W12-0424` is USD/JPY, where the pip is `0.01` and not `0.0001`. Normalised
it reports 5.34 pips against a 2-pip threshold. Unnormalised it reads **100×
smaller** and passes every threshold there is.

## Artifact-by-artifact

| file | what it carries | why it is not code |
|---|---|---|
| `ccf_config.yaml` | the whole Control Plane document: product class, both operators, the request contract, the resolution rules, the λ_c table and the debt profile | delete it and the spine has nothing left to interpret (CLAUDE.md §6.4) |
| `artifacts/pip-scale.yaml` | the pip per currency pair, with `no_default: true` | the scale at which a pair quotes is a market convention this product **asserts**, not a fact it derives — so it carries a semver and a provenance, and an undeclared pair is refused rather than defaulted |
| `artifacts/source-vocabulary.yaml` | the Fluree IRIs, the table names, and `absent_legs` | naming `settlesVia` and `netsWith` as **absent** is the difference between *we looked and found nothing* and *there is nothing to look at* |
| `artifacts/question.yaml` | the demonstration question, including the `as_of` pin | the instant a question is asked as-of is the caller's to state; a program that read a clock would make its own answer unreproducible |
| `artifacts/gates.yaml` | all 28 declared gates, each with its executing test and the sabotage that proved it | a gate nobody can make fire is a declaration, not a control |
| `backends.yaml` | environment-variable **names** only | no host, no port, no credential, anywhere in this tree |
| `acquisition.py` | the two source legs, bounded at the decision instant | PostgreSQL carries the values; Fluree carries the instants. `system_trade_record` has no timestamp column at all |
| `projection.py` | the alignment, the partition, the verdict, the decomposition | `[ADAPT]` — all of it. It refuses six things, each because one was measured |
| `deployment.py` | vocabulary, envelopes, admission, and the deployment half of one declared gate | `[ADAPT]` |
| `produce.py` | boot, acquire, govern | `[MECHANISM]` — the SDK's calls and none of this deployment's vocabulary |

## Whitepaper / CLAUDE.md sections exercised

- **Whitepaper §7.3** — the Context Graph, and the single-writer invariant:
  `booted.handle.worker` is the only write handle in the process.
- **Whitepaper §7.4 / §7.5** — two operators and one projection, composed by the
  SDK. The deployment authors **no operator set**; the plan factory passes the
  resolver's own `required` tuple through.
- **Whitepaper §6.3 / §7.6** — the four request axes as `ProductRequest` fields,
  the typed product contract, and the three validation gates.
- **Whitepaper §7.7** — `λ_c` and `D_c`, with `freshness_over: leading-edge` keyed
  on `system_name` as a first-class claim attribute.
- **Whitepaper §7.10** — the five-dimension replay record, written before
  delivery is reachable.
- **CLAUDE.md §6.4** — the No-Hardcoding Rule. Every domain value in this tree is
  in an artifact.
- **CLAUDE.md §9** — the curated estate as evidence; the illustrative-calibration
  discipline (`CP12-F-15`); examples as probes rather than repair targets.

## What to change first

**Change `artifacts/pip-scale.yaml`.** Add a pair with no entry and ask for it:
the product refuses rather than defaulting to `0.0001`. That one file is the
difference between a variance reported at the right scale and one reported a
hundred times too small.

After that, in order of how much they teach:

1. **`COMPARE_AT=latest`** on `TRD-W12-0002` — watch a real break disappear.
2. **`NO_ALIGN_CLOCKS=1`** on `TRD-W12-0004` — the genuine break becomes
   `not-evaluable`, because without the correction the two instants differ by
   47 seconds and the series cannot resolve that.
3. **`MATERIALITY_PIPS`** — the threshold comes from the estate's own
   `materiality_threshold` table by intent; override it and watch the partition
   change.
4. **The λ_c row in `ccf_config.yaml`** — set it to the 1-hour production
   reference and watch `F` stop discriminating between two real trades
   (`CP12-F-15`, and see the note below).

### Two half-life figures, and they are not the same contract

`CP12-F-15`, and the specification states it at §B.5.0.

| | value | what it is | where it lives | does the served product use it? |
|---|---|---|---|---|
| **Production freshness reference** | **1 hour** | the freshness **SLA** this product would run at against continuously refreshed market data. A reference figure only | prose in `spec/CP-SPEC-012`, **and nowhere else** | **No.** Bound in no artifact in this tree |
| **CP-12's illustrative half-life** | **48 hours** | the value **this example actually runs at** | `ccf_config.yaml` → `half_life.fxr_observation.half_life_seconds: 172800` | **Yes.** Every `F` served here is computed from it |

The reference cannot be demonstrated on this estate: the trade window is eight
days wide, so at one hour every observation has aged to nothing and two real
trades read F `0.2500` and `0.2508` — a spread of `0.0008`, the term no longer
measuring its own subject. At 48 hours they read `0.5151` and `0.8999`.
`FXR-G28` serves under both bindings, pins all four figures, and requires the
served `F` to follow the binding rather than the printed reference.

**48 hours is not a production recommendation.** It is a demonstration value
under CLAUDE.md §9 and `D-IMPL-323`.

## What would fail

- **Counting system pairs.** 120 comparisons over 60 divergences, exactly `2.00×`.
  The payload exposes no field a consumer can count to reach 120 (`FXR-G22`).
- **Decomposing across an interval the tick series cannot resolve.** Measured,
  that misclassifies 22 of 60 (`FXR-G25`).
- **Revaluing against a 20-hour-old tick.** A −72.49-pip residual on a raw
  variance of 5.15 (`FXR-G27`).
- **Defaulting the pip scale.** USD/JPY reads 100× too small and passes every
  threshold (`FXR-G26`).
- **Comparing current state.** 13 of 60 breaks vanish (`FXR-G23`).
- **Letting the corrected instant reach the fabric.** The SDK's freshness figure
  would become a function of this product's own alignment model (`FXR-G24`).
- **Treating a zero-length interval as unresolvable.** It buries the 20 breaks
  the estate designates genuine — 20 of 20 (`CP12-F-10`).
- **Choosing the comparison peer with `next(iter(a_set))`.** Python salts string
  hashes per interpreter, so the content address moves between runs
  (`CP12-F-12`).

All 28 gates are in `artifacts/gates.yaml`, all 28 are executed by
`tests/examples/test_cp_12_output.py`, and **all 28 were observed going red under
a sabotage of the mechanism they name** — 25 by breaking this deployment, 3
because the SDK refuses the bad state before this deployment can reach it.
