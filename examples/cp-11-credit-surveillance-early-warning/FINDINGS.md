# cp-11 findings

The authoritative findings record for `credit-surveillance-early-warning`. Every
`CP11-F-NN` id resolves here. Status vocabulary is `D-IMPL-261`'s: **OPEN**,
**FIXED-`<phase>`**, **ESTATE-LIMITATION**, **NOT-A-GAP**. A constraint or an
estate property is not OPEN work.

**Two of these produced SDK rulings, and one of those was a defect in the first
ruling.** This rung is where `D-IMPL-334` was earned and where `D-IMPL-335`
corrected it — the second found only because a Context Product drove the
mechanism through real assembly, which no test in `tests/` did.

---

## `CP11-F-01` — the article's central mechanism did not exist in the SDK · FIXED-`D-IMPL-334`

**Raised at Gate 1 and the reason Gate 1 was HELD.** The canonical vault article
names step 7 — supersession as a Policy event the Control Plane propagates,
cascading invalidation to every downstream product whose `operators_invoked`
touched the affected entity — and says of it: *"Step 7 is why this product is in
the catalog."*

**Measured across `src/` and `runtime/` on 2026-09-12, none of its four parts
existed.** Supersession was a graph write-path column filtered at as-of read
time, never reaching the Control Plane; there was no event bus, subscriber
registry or notify path; there was **no product cache to invalidate** (the only
cache is a per-execution operator memo whose own docstring defers the
invalidation story to `D-IMPL-36`); and nothing read `operators_invoked` for
invalidation. `decay: supersede-only` was purely a half-life mode returning
`Decimal(1)`, and `ArtifactStoreProtocol` offers no delete by design.

**Gate 1 was held rather than shipping the substitute.** Steps 1–6 with
re-derivation in place of step 7 would have proved a different product.

**`D-IMPL-334` built it as serve-time dependency invalidation** — an append-only
Control Plane register the writer appends to and a serve-time gate reads. No
cache, no eviction, no notification, because the SDK stores no product to evict.
The design's finding was that the expensive capability already existed in the
data: `ContextFabricSnapshot.touched_entities` has ridden in every replay record
all along.

**The residual limitation is unchanged and stays explicit** in §0.4 and §E.4:
this prevents **re-serving** an obsolete product; it does **not** recall a copy a
consumer already holds. `EWS-G22` keeps the product from claiming otherwise.

---

## `CP11-F-02` — both readings of the composite are unusable as the estate declares them · FIXED-gate-1

Naive accumulation of the non-decaying class: **30 of 50 obligors** breach the
board band and 48 of 50 breach the sweep band. A control firing on 60% of the
book is not a control. Supersession applied: **0 of 50** reach credit-committee
or board. A control that never fires demonstrates as little as one that always
does.

The mechanism is right and the *thresholds* were calibrated against the wrong
reading. §E.2 declares demonstration values under `D-IMPL-323`, labeled at every
site, with the measurement that forced the change recorded.

---

## `CP11-F-03` — all 50 prior-observation anchors carry the same `validFrom` · ESTATE-LIMITATION

Measured: every `PriorObservation` node in the ledger carries
`validFrom 2024-08-19`. The estate seeds **one cold-start point per obligor**,
not a sweep history, so the default delta is the full window for every obligor
and a shorter delta must be asked for explicitly.

**Not worked around.** The product still defaults `since` to the anchor rather
than to a fixed lookback, because the product *is* a delta and a delta needs a
prior. The fixed `window_days` is the last resort, reached only when neither a
requested `since` nor an anchor resolves.

---

## `CP11-F-04` — `gdelt_mention.tone` is a query filter, not a measurement · ESTATE-LIMITATION

It reads like a per-mention sentiment score. **All 951 rows carry the identical
literal string `<-5`** — the GDELT query filter that selected the corpus.

Weighting a mention by its "tone" would weight every mention by a constant while
appearing to discriminate, which is worse than not weighting at all: it would
look like a signal. The product does not consume it, and `EWS-G15` asserts no
`tone` value reaches any weight, score or payload field.

---

## `CP11-F-05` — no Item 4.02 non-reliance events · ESTATE-LIMITATION

`filing_profile` records two obligors with a lifetime 4.02 count; **zero appear
as dated events in the window.** The auditor leg is Item 4.01 only — 6 events
across 5 obligors.

Recorded rather than simulated. A manufactured non-reliance event would
demonstrate the product handling a condition the estate does not contain.

---

## `CP11-F-06` — the ledger `t` axis carries no delta · ESTATE-LIMITATION

The article specifies step 3 as *"a delta query against two ledger points, not a
lookback window."* **That is not available on this estate.**

Measured by pinned read against a head of `t = 5729`: **0 `WarningSignal` before
`t = 421`, all 538 by `t = 491`, and 538 at every point thereafter.** The entire
signal population arrives in one bulk load and nothing is ever added. Its
siblings land in the same band — `SignalSource` complete by `t = 421`,
`PriorObservation` by `t = 422`.

**A ledger-point delta over this estate returns everything or nothing.**

**The substitution is declared rather than made silently** (§B.3): the delta is
defined on **valid time** — the signals whose source observation date falls in
`(since, asked_at]`. This is the rung-9 discipline applied to a delta rather than
to a decay: the question is about the world, so it is asked against the world's
clock.

---

## `CP11-F-07` — the Fluree `WarningSignal` node carries no timestamp · ESTATE-LIMITATION

Its predicates are `rdf:type`, `rdfs:label`, `provenance`, `signalAbout`,
`triggeredBy` and `supersededBy`. **The date appears only inside the label
string** — `"8-K item 1.01 signal — 254900HM1ABRDJ7T5718 (2025-03-05)"`.

**The dated leg is PostgreSQL.** The graph carries identity, attribution and the
supersession chain; the relational store carries the clock. Parsing a date out of
a label is forbidden: **a label is prose, not a clock.** `EWS-G20` asserts it
structurally — the source-vocabulary artifact declares no label term at all, so
there is nothing for the code to take a date from.

> The first draft of that gate grepped `acquisition.py` for `rdfs:label` and went
> **red against correct code**, because the docstring that explains this rule
> contains the string. A gate a comment can break is a gate about comments.

---

## `CP11-F-08` — 32 of 36 WARN name matches are wrong, and visibly so · NOT-A-GAP

| anchor | matched employer | score |
|---|---|---|
| TransDigm Group INC | **Transdev** | 0.7059 |
| B&G Foods, Inc. | **US Foods, Inc.** | 0.7059 |
| SP Plus Corp | **Lamps Plus** | 0.7059 |
| MUELLER INDUSTRIES INC | **Pride Industries** | 0.7059 |
| Caesars Entertainment, Inc. | **Sony Pictures Entertainment** | 0.7083 |

Accepting them attributes other companies' layoffs to these obligors.

**Not a gap, because the estate already holds the line**: only the 4 `resolved`
matches became signals. The product consumes `resolved` only and **publishes the
ambiguous count with its reason**, so a reader can see what was withheld and why
— an absence with a reason rather than a silence.

---

## `CP11-F-09` — the λ_c table's sector dimension was inert, and Gate 1 did not notice · FIXED-gate-2

`signal_weight` keys on `(signal_type, sector)` and its nine sector values are
exactly the standard **SIC division names**. `legal_entity` carries a four-digit
`sic` and a *specific* `sic_description` — `"Plastics Products, NEC"`.

**Measured at Gate 2: zero of the 50 anchors' descriptions match a sector name.**
Every obligor fell to `Unclassified`, and **36 of the table's 45 rows were
unreachable** — configuration that nobody reads, which is `D-GATE-cp-08`'s
principle found again.

**Fixed** by resolving the SIC code to its published division, declared in
`artifacts/source-vocabulary.yaml` with its own semver and provenance rather than
in code, because the boundaries are domain values and because a reader must be
able to tell a classification this product *asserts* from a fact it *read*. The
mapping then resolves **50 of 50**.

**It changed §E.2's measured populations, and both curves are preserved so the
defect stays auditable:**

```
CORRECTED, sector dimension live:
threshold   0.05  0.10  0.15  0.20  0.25  0.30  0.35  0.40
obligors      48    46    28    17    11     7     3     3

as measured at Gate 1, every obligor Unclassified:
obligors      48    45    25    14     8     3     2     0
```

The three thresholds did not move — 0.15 / 0.25 / 0.35, re-affirmed by Dave on
the corrected populations of 28 / 11 / 3. The numbers beside them did.
`EWS-G26` asserts the resolution over the **whole anchor set** and requires it to
discriminate, because one sector for every anchor would be inertness wearing a
different name.

---

## `CP11-F-10` — `D-IMPL-334` recorded the ingestion instant, not the world instant · FIXED-`D-IMPL-335`

**Found at Gate 2, and only findable here.** `_writer.py` used
`claim.observed_at` as the invalidation boundary. Through **L2 assembly** that is
always the ingestion instant, because `D-IMPL-332` fixed `observed_at` as *when
the fabric learned the claim* and `valid_from` as *when it became true in the
world*, and `worker._stitch` writes exactly that.

Measured on this product: the boundary read **2026-08-19**, the instant the
fabric wrote, instead of **2026-07-28**, the instant the superseding evidence
became true.

**The consequence was not merely conservative** (Dave's correction, and it is the
substance): a product whose `graph_snapshot_at` falls in `[T_world, T_ingest)`
was refused **on the basis of when the fabric happened to learn something rather
than on when anything changed**. A refusal keyed to ingestion latency is keyed to
an accident of operations, and the interval it wrongly covers is exactly as wide
as the lag between the world and the fabric.

**Why no SDK test could see it.** `D-IMPL-334` shipped with 14 tests and 8
sabotages, all green. Every one built its claims **directly**, where
`observed_at` is whatever the author supplied and the two clocks never separate.
`CP-SPEC-011` is the first product to drive the mechanism through real assembly.

**`D-IMPL-335`** — `valid_from` when the claim carries one, `observed_at` only
when it does not, with an L2 regression that gives two envelopes the **same**
`ingestion_timestamp` and different `observed_time`. `EWS-G25` pins the corrected
instant both ways: it must be `2026-07-28` and must **not** be `2026-08-19`.

**This is `D-IMPL-261` in its clearest instance yet.** The example is a probe; it
found a defect in an SDK change that had already been designed, ruled, built,
tested, sabotaged and merged.
