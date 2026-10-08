# cp-10 findings

The authoritative findings record for `rating-and-spread-migration`. Every
`CP10-F-NN` id resolves here. Status vocabulary is `D-IMPL-261`'s: **OPEN**,
**FIXED-`<phase>`**, **ESTATE-LIMITATION**, **NOT-A-GAP**. A constraint or an
estate property is not OPEN work.

**Three of these were found by the author against his own approved work**, and
two of them reopened a closed gate. That is what the rung is for.

---

## `CP10-F-01` — the estate holds no FINRA TRACE data · ESTATE-LIMITATION

The vault's §C assumes TRACE for the spread leg; dataprep's own digest flagged
its coverage as unconfirmed. **Confirmed absent.** Instrument identifiers are
`syn-i-*` and the spread is a *decomposition*, not an observation: a public
Treasury benchmark, a public ICE BofA option-adjusted spread by rating band, and
an engineered issuer-specific residual.

**Not worked around.** The specification does not call the spread leg TRACE and
the payload does not either. Every spread series carries a
`component_provenance` block naming what each of its three numbers actually is,
and `RSM-G18` asserts both halves — that the residual is labeled
`synthetic — engineered` and that the string `TRACE` appears nowhere in the
payload.

---

## `CP10-F-02` — no thinly-traded instruments with observation gaps · ESTATE-LIMITATION

Coverage is 468–499 of 499 dates per instrument. The vault's §F sparse-series
requirement cannot be exercised against this estate.

**Removed from the rung by ruling** (Dave, 2026-09-12) rather than simulated. A
gap manufactured to satisfy a requirement would demonstrate the product handling
a condition the estate does not contain, which is a claim about nothing.

---

## `CP10-F-03` — no agency ratings anywhere in the estate · NOT-A-GAP

Verified across all 118 tables: no agency column exists. The internal scale is
`synthetic — internal` and its agency-style letters are labeled as internal at
every site that carries them.

The licensing boundary is therefore satisfied **by construction rather than by a
filter** — but the boundary can still fail by *presentation*, so `RSM-G20`
asserts that no agency name appears anywhere in the payload. An SDK example
ships with the SDK and is copied by adopters; licensed values in one would be
redistribution exactly as they would be in a product.

---

## `CP10-F-04` — the benchmark basis is `static_issue_band` · ESTATE-LIMITATION

The market component is the OAS of the band the instrument was **issued** into,
and that band does not migrate with the obligor.

**Measured.** All 30 rated obligors were in their issue band at the window's
start; **2 of 30 had left it by the end** — one of them a §A.3 divergence case
netted against `BBB` while graded `BB+`. Because `BB` trades far wider than
`BBB` (156→306 vs 98→149 bp over the §D.4 window), **the error is directional**:
the market component is understated and the residual overstated, precisely for
the obligors the product cares most about.

**Reported, never corrected, and the reason is the product's whole subject.**
Inferring a replacement band from the internal grade would make the market
component a function of the grade the divergence is measured against — and a
residual computed that way **could never disagree with the grade**. Four
bindings at §C.4 TRAP 4, enforced by `RSM-G23`: every spread figure names its
basis; a migrated obligor is flagged with the direction of the error; the
payload never claims unqualified *"pure issuer deterioration"*; and the reported
issue bands are asserted to match the **instruments'** own.

---

## `CP10-F-05` — two naive aggregations produced confidently wrong answers · NOT-A-GAP

Both were run by this specification's author during Gate-1 measurement, and both
are recorded as the product's own counterfactual rather than quietly corrected.

- **Endpoint differencing** reported zero divergence *and inverted the sign*.
- **Temporal proximity** reported six confirmations where there is one — because
  quarterly reviews land every ~90 days, so some review is near any date.

They are §C.4 TRAP 1 and TRAP 2. `RSM-G09` defends against the first by
asserting detection runs against each bond's own median rather than an absolute
threshold; `RSM-G11` defends against the second by requiring all three tests —
later, downgrade, off-cycle — asserted separately.

---

## `CP10-F-06` — cross-instrument averaging halved the anchor's peak · FIXED-gate-1-amendment

**Found at Gate 2 build, against the Gate-1 specification's own headline
figure**, and Gate 1 was reopened for this amendment alone (Dave, 2026-09-12).

The first implementation averaged an obligor's instruments before detecting
anything. Celanese's two bonds have median residuals of **29.015** and **29.538**
bp — normally indistinguishable. On 2024-12-11 the five-year reaches **8.039×**
its own median and the twenty-five-year reaches **1.27×**. Averaging first halves
the peak and erases the term-structure signal entirely: the concern is at the
short end, and the blend says nothing about where.

**The repair.** The instrument is the primary observation unit. Episodes are
detected per bond against that bond's own median; instruments are never averaged
before detection. The obligor-level figure survives as a **derived summary that
never travels without its dispersion**, because a mean over instruments that may
be pricing different things reads exactly like an observation. Measured: **5,267
(obligor, date) pairs** in this estate carry one bond at more than twice the
other. The grade comparison stays at obligor level — a grade assesses an
obligor, a spread prices a bond, and the product does not invent a per-bond
grade to make the units match.

Enforced by `RSM-G09` and `RSM-G24`, and made structural in `ccf_config.yaml`:
`pricedAt` hangs the spread off the **bond**, so a spread point cannot be
reached except through the instrument it priced.

---

## `CP10-F-07` — historical-series freshness cannot be computed across the full archive · FIXED-gate-2

The original §E.1/§E.2 treatment averaged freshness across all historical
observations, driving `F` from the intended current-state measure to an
**archive-length** measure. This product keeps years of daily quotes by
construction — that history is how a migration is detected at all — so the
default drove `F` to approximately zero and `D_c` to `fail_closed` on a serve
whose newest quote was two days old.

**Measured on the anchor at `as_of` 2026-08-20:**

```
observations in the view   rsm_spread 996 · rsm_grade 9 · rsm_instrument 2 · rsm_obligor 1
observations entering F    rsm_spread   2 · rsm_grade 1 · rsm_instrument 2 · rsm_obligor 1

F over the leading edge   0.664139      F over every observation   0.004750
D_c 0.3651, signal ok                   D_c 0.9955, fail_closed
```

**`supersede-only` was tested first and rejected**, because Dave required the
existing path be proven inadequate before the SDK changed. Over nine
observations one day apart it gives `F` per observation
`[1, 1, 1, 1, 1, 1, 1, 1, 1]`, mean `1.000000` — it means *this class does not
decay*, so every historical point still enters `F`, each now reading as
perfectly fresh. Curve-mean understates freshness by counting history as stale;
`supersede-only` overstates it by declaring history evergreen. Neither says
*"the newest quote for this bond is two days old."*

**Fixed by `D-IMPL-333`**, an SDK ruling: a λ_c row declares `freshness_over`
(`series-mean`, the default, or `leading-edge`) and, for the leading-edge form, a
`series_key_attribute` naming the field that partitions observations into series.
Both hash-transparent, so every existing table keeps its identity and its `F`.
§E.1/§E.2 were reopened for the correction and nothing else (§E.1.1).

**The example raised it rather than working around it** (`D-IMPL-289`'s shape).
A local scorer here would have hidden a defect every product with a time series
will hit.

---

## `CP10-F-08` — the confirmation test could not distinguish "not rated" from "rated and never moved" · FIXED-gate-2

**Found running §D.4 scenario 2 at Gate 2.** `_confirmation` returned `None` for
both states, so the product reported Sabre — rated `B` at the peak and still `B`
through two later reviews — as though the obligor carried no grade at all.

**Scenario 2 is precisely the second state**, so the product could not express
the case its own specification declares. For a credit officer these are
different findings: one says *nobody has looked*, the other says *somebody
looked, twice, and disagreed with the market.*

**The repair.** Three outcomes rather than an absence: `changed` (carrying the
three tests of `RSM-G11` separately), `unchanged` (carrying the grade in force
throughout and the count of later reviews that left it alone), and
`not-evaluable`. Enforced by `RSM-G11`, which asserts both halves — the anchor's
confirmation and Sabre's standing disagreement.

## Security remediation — `EX-09` (2026-10-07)

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before the change: §B.4, the example's own code rather than the SDK. Changed under `D-IMPL-261`'s "objectively wrong" reason, authorized by `D-IMPL-376` ruling (7): *"SDK input rejection is useful defense, but leaves fragile example code for adopters to copy."*

- **`EX-09`.** `acquisition.py::_Relational.rows` built `SET search_path TO {schema}` by f-string (security review 2026-09-23). It now composes the statement with the driver's own `psycopg.sql` — `SQL("SET search_path TO {}").format(Identifier(schema))` — so the configured schema reaches PostgreSQL as one quoted identifier, whatever it contains. The documented schema `ccf_v2` is one lowercase identifier, so it names the same schema quoted or not.

Evidence: `tests/examples/test_ex_09_search_path_identifier.py`.
