# cp-11 — Credit Surveillance / Early Warning

**What changed on this name since we last looked — and does it matter?**

Five signal classes on five decay regimes, where one of them **does not decay at
all** and is bounded by supersession instead.

## What this demonstrates

- **A fact that never becomes false, but can stop being relevant.** An 8-K
  acceleration filing is as true a year later as the day it landed —
  `signal_weight.decay_days` is `NULL` for that whole class. What ends its
  relevance is a **later filing**. Read as *"contributes forever"*, 30 of 50
  obligors breach the board band and the control is worthless. Read correctly,
  25 of Super Micro's 26 filings contribute **nothing** and the score means
  something.
- **Three states, and they partition.** Every signal is `current`, `superseded`
  or `not-participating` — exactly one, so nothing is counted twice. The last is
  its own answer and never collapses into `superseded`: a signal the chain does
  not mirror **has not been superseded — it was never in a chain to be
  superseded from.** Absence is not supersession.
- **A delta on the world's clock.** The product *is* a delta and a delta needs a
  prior, so `since` defaults to the obligor's prior-observation anchor. The
  article asks for a delta between two ledger points; measured, this estate's
  whole signal population arrives in one bulk load between `t=421` and `t=491`,
  so a ledger delta would return everything or nothing. The substitution to
  valid time is **declared**, not made silently.
- **Two decay models that must not touch.** `signal_weight.decay_days` drives the
  composite warning score — *what the evidence says*. The registered λ_c drives
  `F`, the Context Debt freshness term — *how old the evidence is*. They share
  arithmetic and answer different questions. Measured over 14 anchors: ordering
  by composite produces **36 inversions** against ordering by `F`.
- **Serve-time dependency invalidation, end to end.** An acceleration lands, the
  obligor's context moves, and a product that read that obligor at an older
  snapshot is refused on its next serve — **including a product that never
  mentioned early warning**. This rung earned `D-IMPL-334` and then found the
  defect in it that became `D-IMPL-335`.
- **Absence reported as absence.** A signal class the obligor has no evidence in
  is **absent**, never scored zero. Tupperware has no trend deltas at all; that
  is not a stable balance sheet.

**Illustrative calibration.** This example runs against a point-in-time
demonstration estate rather than continuously refreshed production data.
Freshness half-lives and related thresholds are calibrated to make the governed
behavior observable in that snapshot. They demonstrate how the SDK applies these
controls and should not be interpreted as recommended production coverage-policy
thresholds.

**What the fabric does not do, stated plainly.** It refuses to **re-serve** an
obsolete product. It does **not** notify anyone, does not recall a copy a
consumer already holds, and evicts nothing — there is no product cache to evict
from. A holder learns by asking again; what changed is that asking now returns a
current answer or a refusal, never the stale one.

## Run it

The example reads the live estate. Four variables, and **the namespaces are the
v2 ones, which are not in the estate's own `.env`** — that file names v1:

```bash
export CCF_CP_11_POSTGRES_DSN='postgresql://<user>:<pw>@192.168.4.76:5432/parkavedb'
export CCF_CP_11_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_11_FLUREE_URL=http://192.168.4.76:8090
export CCF_CP_11_FLUREE_LEDGER=fibo-v2

make -s example-cp-11
```

Every request parameter is optional. Omitted, the program asks the demonstration
question in `artifacts/question.yaml` — an anchor, a delta bound and a debt
tolerance are **request** parameters, and a build tool is not a request channel.

```bash
# the headline: the heaviest-signalled name, reaching the credit-committee band
make -s example-cp-11

# the thinly-evidenced name: two classes ABSENT, and the debt says so
make -s example-cp-11 LEI=G8NWFN4YP7CR6FOP4886

# the governed refusal — a tolerance below the debt this answer carries
make -s example-cp-11 DEBT_TOLERANCE=0.20

# an earlier decision instant: fewer signals, and `as_of` proves it reaches the read
make -s example-cp-11 AS_OF=2026-07-20T00:00:00+00:00
```

## The story

Super Micro Computer, `54930022CZO1N2UGVW07`, over the two years to 2026-08-19.

**139 signals** land in the delta: 26 8-K filings, 93 adverse-media mentions and
20 XBRL trend deltas. Two classes — spread widening and WARN notices — have **no
evidence at all**, and the payload says `absent` rather than scoring them zero.

Of the 26 filings, **25 are superseded and contribute nothing.** They have not
aged out; a later filing replaced each one, and the exclusion list says so in
those words — *"a later filing replaced this one; its relevance ended rather than
decayed."* That distinction is the rung. The remaining filing plus 93 decayed
media mentions produce a composite of **0.3134**, which reaches the
**credit-committee-referral** band.

The estate declares that band at 0.55. This product declares it at 0.25, and the
payload carries **both**, because the difference is a calibration decision and a
payload showing only the value in force would hide that a decision was taken.
Under the estate's own bands — calibrated against the accumulating reading this
product refuses — no obligor in the book reaches credit-committee at all.

`D_c` reads **0.5818**, signal `ok`: `F` 0.6970, `C` 0.6000, `S` 1.0000.
Completeness is 0.6 because three of five classes carry evidence. That is the
Context Debt measuring the *evidence*, while the composite above measures what
the evidence *says* — and over 14 anchors the two orderings disagree 36 times.

Ask the same question of Tupperware and the shape inverts: a single Item 2.04 at
severity 1.0, 23 media mentions, **zero** trend deltas, a composite of 0.0900
reaching no band, and `D_c` **0.8628 · fail_closed**. A thinly-evidenced name
producing high debt and no escalation is the fabric working, not failing.

## Artifact-by-artifact

| file | what it carries |
|---|---|
| `ccf_config.yaml` | the Control Plane document. Two entity classes, the λ_c table with its `decay_basis`, `freshness_over` and `series_key_attribute`, the operator parameters, the request contract, the debt profile, and the identity of the one declared product gate. Delete it and `produce.py` has nothing to interpret. |
| `artifacts/source-vocabulary.yaml` | every source term the product reads — the Fluree IRIs, the tables, **the SIC → division mapping with its own semver and provenance**, and the **declared** list of classes that participate in supersession. |
| `artifacts/escalation-policy.yaml` | the bands this product declares, their measured populations, and the estate's own bands beside them. |
| `artifacts/question.yaml` | the demonstration question. The `as_of` pin lives here because it is a request parameter. |
| `artifacts/gates.yaml` | all 29 declared gates with their executing test, sabotage and observed result. |
| `backends.yaml` | where the fabric's own L3 lives for a run. Never a source store. |
| `acquisition.py` | the two source legs, bounded at the decision instant. PostgreSQL carries the clock; Fluree carries the chain. |
| `deployment.py` | this deployment's own values: the request shape, the envelopes and their order, the measured `C` and `S`, and the deployment half of the one declared gate. |
| `projection.py` | Π. The delta, the supersession filter, the decayed contributions, the composite, the bands, the coverage and the exclusion list. |
| `produce.py` | the spine. Boot, acquire, govern — and nothing else. |
| `run.py` | the client. Asks one question and prints what came back. |

## Whitepaper / CLAUDE.md sections exercised

- **§7.7 Context Half-life and Context Debt** — a class that does not decay at
  all beside four that do; `decay_basis: valid-from`; `freshness_over:
  leading-edge` keyed on the signal class.
- **§7.6 supersession** — and the gap it left. This rung is where serve-time
  dependency invalidation (`D-IMPL-334`) was earned and where the instant it
  records was corrected (`D-IMPL-335`).
- **§7.3 the T axis** — world time, fabric-learning time and supersession, kept
  distinct and enumerated in the spec's §B.4.
- **§7.4 / §7.5 operators and projection** — a policy operator scoping the
  subgraph, a typed-neighborhood traversal, and a Π that computes a delta.
- **CLAUDE.md §6.4 No-Hardcoding** — the SIC boundaries, the participant list
  and the escalation bands are all artifacts, not constants.
- **CLAUDE.md §9** — both legs read live, nothing is written, and the
  illustrative calibration is disclosed at every site that carries it.

## What to change first

**`artifacts/source-vocabulary.yaml`'s `supersession_participants`.** It is one
line, and it is the most instructive edit in the tree. Today it names
`8k_event` alone. Empty it and every signal becomes `not-participating` —
nothing is dropped, and the composite rises to the accumulating reading. That is
`CP11-F-02`'s first trap, reachable in one edit.

After that: `artifacts/escalation-policy.yaml`'s three floors, to watch the band
populations move; and `--since`, to see the delta's left edge change what is in
scope without changing anything about how it is scored.

## What would fail

- **Reading "no decay" as "accumulates forever."** 30 of 50 obligors breach the
  board band. `EWS-G07` asserts a superseded signal contributes zero.
- **Reading absence from a chain as supersession.** The 113 signals in classes
  with no chain would be dropped silently, and the product would report a clean
  composite over a fraction of its evidence. `EWS-G08`.
- **Inferring which classes participate in supersession from the data.** It
  works today and changes behavior the day another class gains a chain — in the
  most dangerous direction, by beginning to drop signals nobody asked it to
  drop. `EWS-G27`.
- **Letting the SIC sector fall to `Unclassified`.** 36 of the weight table's 45
  rows become unreachable while the configuration still looks complete.
  `EWS-G26`.
- **Wiring the two decay models together.** The debt figure would rise and fall
  with the product's own finding. `EWS-G29`.
- **Claiming the fabric notified or recalled anything.** It refuses to re-serve;
  it cannot reach a copy a consumer holds. `EWS-G22`.
