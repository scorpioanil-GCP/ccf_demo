# Measurement note — what was checked against the estate, and two corrections

**Every figure in `CP-SPEC-008` was measured before the specification claimed
it. This note records those measurements, the queries behind them, and two
places where an early reading was wrong and the specification changed.**

It sits beside the specification because an engineer planning a build should be
able to see which claims were checked and how, rather than taking a table on
trust. All reads were `SELECT`; nothing was written to either store.

---

## 1 · The two clocks, checked separately

A booking lag and a covenant history are different properties, and an estate can
carry one without the other. They were checked apart.

### Does the assertion-time axis change the answer?

*What would prove it:* the same facility, `as_of` held, where moving
`known_as_of` from before to after an amendment's booking date **changes the
admitted set**.

**Yes, on amendments.** `AMD-01BB3F-2` carries an effective date of 2025-08-14
and a booking date of 2025-10-05. Held at `as_of=2025-09-09`:

```
known_as_of = 2025-09-09   admitted [AMD-01BB3F-1]
                           excluded [(AMD-01BB3F-2, assertion-time)]
known_as_of = 2026-09-11   admitted [AMD-01BB3F-2, AMD-01BB3F-1]
                           excluded []
```

Drawdown `DRW-01BB3F-0000`, USD 4,500,000, falls on 2025-09-09 — inside the
52-day gap. Measured through the assembled product, not against the source
query.

**Not on covenants**, and this is why the specification serves covenant terms
labelled unversioned. The booking-date predicate appears on **0 of 180**
covenants, at every transaction point sampled, so there is nothing on a covenant
for `known_as_of` to filter.

### Is there a covenant history to reconstruct?

*What would prove it:* a later amendment replacing a covenant assertion, where
reading the ledger at the earlier transaction point still returns the prior one.

**No — and it is an absence in the demonstration data, not a limit on the
approach.** Three checks, all negative:

```
covenant thresholds, by transaction point
  t:1500   180   (baseline)
  t:2000   180 | changed 0 | added 0
  t:3000   180 | changed 0 | added 0
  t:4000   180 | changed 0 | added 0
  t:5000   180 | changed 0 | added 0
  t:5591   180 | changed 0 | added 0      <- head
```

No covenant's validity interval is ever closed (the closing predicate is present
on 2 covenants and constant), and no covenant carries a supersession marker at
any point. The ledger does carry 1,107 supersession markers — on warning
signals, credit ratings, issuance events, prior observations and register
versions. **None of them are covenants**, so none is in this product's slice.

The covenant data is loaded once and not versioned thereafter. An estate that
versioned covenant terms would extend this product's answer without changing its
shape.

---

## 2 · Correction — a real number about the wrong population

**The specification briefly claimed that most amendments lack a booking date,
and built a debt metric on it. That was a count over the wrong population.**

The claim was *"112 of 137 amendments carry no booking date"*. 137 counts every
`amends` edge in the ledger. Measured by what the edge points at:

| target | edges |
|---|---|
| Trade | **89** |
| **Credit facility** | **25** |
| Trade lifecycle event | 16 |
| Syndicated loan | 7 |

This product reads **facility** amendments. In that slice:

```
amendments whose target is a credit facility    25   (across 18 facilities)
  carrying an effective date                    25
  carrying a booking date                       25
  missing either                                 0
```

### What changed in the specification

- The finding was withdrawn — there is no population of clockless amendments in
  this product's slice.
- **The product-specific debt metric was removed.** Defined as *placeable ÷
  served*, the ratio is 1 on every facility and the debt 0 on every answer: a
  figure that reads the same whatever the answer is. No replacement was
  invented, because a debt figure exists to report a shortfall and this product,
  on this estate, has none of that kind.
- **Two gates were withdrawn** — one guarding an amendment with no booking date,
  one watching the debt ratio. Both guard a population of zero. Their ids are
  left as gaps rather than reused.

### What replaced it, and what that measurement showed

Removing the scorer exposed two things the earlier shape had hidden.

**The reference path is defaultless, and the λ_c table had never been read.**
`build_governed_resolver` refuses a call supplying neither a scorer nor the
material to build one. Supplying that material meant looking half-lives up **by
observation type** — and the table was keyed `amendment_structure`,
`covenant_terms`, `facility_reference`, three descriptive labels no consumer
had ever resolved. While the deployment scored for itself the table sat in the
Control Plane looking like configuration and functioning as documentation. It
is now keyed `amendment` / `covenant` / `facility`, which is what the entity
rules mint and what the scorer asks for.

**`D_c` is 0 on every answer under the reference scorer too, and that is the
honest state rather than a defect to engineer around.** Measured across three
`as_of` instants on the demonstration facility:

```
as_of               D_c   signal    admitted amendments
2024-06-01            0   ok                          0
2025-01-15            0   ok                          0
2025-09-09            0   ok                          1

factors: freshness=1  completeness=1  semantic_consistency=1
```

Freshness is the term that would move, and it does not: every observation is
minted from a live read inside the run, so it is 1 by construction. So the
withdrawal did not cost this product a working signal — **it removed a per-run
ratio dressed as one**, and what stands in its place is the platform assessment
saying, correctly, that there is no shortfall of any of the three kinds to
report. §E.2 states that rather than manufacturing a metric to have one.

### Why it survived three checks

The number *was* measured; a query ran and its output was quoted. What was never
checked is **which population the query ranged over**.

The tell was available from the first pass and missed twice: *"facilities with
amendments: 135"* alongside *"facilities carrying at least one covenant: 45"* is
an arithmetic impossibility for one population, and both figures sat in this
note.

**The rule, and it is not the same as "measure it": a count is only as good as
the population it ranged over, so state the population in the same breath as the
number.** *"137 amendments"* describes the ledger. *"25 facility amendments"*
describes this product. Only the second belongs in a specification.

---

## 3 · Correction — a suspected store defect that was not one

While checking whether the ledger preserves earlier state, a bounded read
returned **182 covenants at the earliest transaction point** while *all typed
subjects* returned **0** at the same point. Both cannot be true of one ledger
state, and the tempting conclusion was that the bound was being ignored.

**It is not.** The control:

| probe | `t:1` | `t:2000` | head |
|---|---|---|---|
| all typed subjects | **0** | 17,230 | 17,871 |
| amendment edges | **0** | 130 | 143 |
| supersession markers | **0** | 1,107 | 1,107 |
| covenant edges | **182** | 182 | 182 |

Three of four move monotonically, and a bound past the head is refused. The
explanation is the loader's own ordering: thin relationship claims were written
first and attributed nodes afterwards, so the covenant *edges* existed from the
first transaction while their attributes arrived later.

**The bounded read is sound**, which is what `CIF-G08` — re-serving at a
recorded transaction point — rests on.

---

## 4 · Population summary, as the specification carries it

| population | measured |
|---|---|
| Covenant nodes | 180, across 45 facilities |
| Amendments to credit facilities | **25, across 18 facilities** |
| Of those, carrying both clocks | **25** |
| Engineered booking lags, each with a drawdown inside | 3 |
| Drawdowns | 151 |
| Register versions | 2 |
| Covenants carrying a booking date | **0** |
| Covenants carrying a supersession marker | **0** |
