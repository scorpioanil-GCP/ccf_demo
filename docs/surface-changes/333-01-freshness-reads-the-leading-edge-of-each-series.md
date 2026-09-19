# 333-01 — freshness reads the leading edge of each series

Recorded at the `f0656746` qualification (2026-09-19) from the introducing commit `5c25048a`
(*feat(halflife): D-IMPL-333 — freshness reads the leading edge of each series*, 2026-09-12),
which shipped without a surface-change fragment. A λ_c row may declare
`freshness_over: leading-edge` with a `series_key_attribute`; the scorer then keeps, per
(observation type, series), the newest observation at or before the decision instant, and every
older member stands behind it as evidence rather than entering F as staleness. This fragment
claims exactly the three public names `5c25048a` added to `ccf.halflife.decay`; the two new
`HalfLifeEntry` fields are fields on an existing contract and are not claimed here.

## ccf.halflife.decay.freshness_over_of

- Surface: ccf.halflife.decay.freshness_over_of
- Public surface: true
- Change type: added
- Before: absent — freshness was always the series mean
- After: `freshness_over_of(table: HalfLifeTable, observation_type: str) -> FreshnessAggregation` — the declared aggregation for a type, `series-mean` by default or `leading-edge`
- Why: `D-IMPL-333` (`5c25048a`) — freshness applies to the leading edge of each logical series as of the decision instant, not to its historical members
- Migration: none; a table declaring nothing keeps the series mean

## ccf.halflife.decay.series_key_attribute_of

- Surface: ccf.halflife.decay.series_key_attribute_of
- Public surface: true
- Change type: added
- Before: absent
- After: `series_key_attribute_of(table: HalfLifeTable, observation_type: str) -> str | None` — the claim attribute that names a logical series for the type, if the row declares one
- Why: `D-IMPL-333` (`5c25048a`) — a leading edge is per series, and the row says which attribute identifies a series
- Migration: none

## ccf.halflife.decay.leading_edge

- Surface: ccf.halflife.decay.leading_edge
- Public surface: true
- Change type: added
- Before: absent
- After: `leading_edge(observations: Sequence[Observation], *, table: HalfLifeTable, now: datetime) -> tuple[Observation, ...]` — reduces each `leading-edge` series to its newest member at or before `now`; the set, not the value — `decay` and `decay_basis` answer how fast and against which instant, this answers which observations
- Why: `D-IMPL-333` (`5c25048a`)
- Migration: none
