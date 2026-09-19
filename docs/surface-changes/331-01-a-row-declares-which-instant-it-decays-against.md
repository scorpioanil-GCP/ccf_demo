# 331-01 — a λ_c row declares which instant it decays against

Recorded at the `f0656746` qualification (2026-09-19) from the introducing commit `b2ba4e8b`
(*feat(sdk): D-IMPL-331 — a λ_c row declares which instant it decays against*, 2026-09-11),
which shipped without a surface-change fragment. The measurement that opened it: `_stitch`
sets a claim's `observed_at` to ingestion time and routes the source's instant to `valid_from`,
and the reference scorer read only the first — so F measured fabric-learning latency, zero for
every claim in a fabric populated inside the run, and a declared λ_c table could not move F at
all (cp-09: F = 1.000000 on a serve carrying three observations). This fragment claims exactly
the two public names `b2ba4e8b` added to `ccf.halflife.decay`; `HalfLifeEntry.decay_basis` is a
field on an existing contract and is not claimed here.

## ccf.halflife.decay.MissingDecayInstant

- Surface: ccf.halflife.decay.MissingDecayInstant
- Public surface: true
- Change type: added
- Before: absent — an observation with no instant for the basis its row declared could only fall back
- After: a `LookupError` raised when a row declares `decay_basis: valid-from` and the observation carries no `valid_from`; refused rather than fallen back, because a silent fallback to `observed_at` would report a perfectly fresh figure for exactly the observations a deployment declared `valid-from` because it cared about their real age
- Why: `D-IMPL-331` (`b2ba4e8b`) — `valid-from` with no instant is refused by name, never defaulted
- Migration: none for a table that declares nothing; a deployment declaring `valid-from` for a type stamps the source instant on those claims or is refused by name

## ccf.halflife.decay.decay_basis_of

- Surface: ccf.halflife.decay.decay_basis_of
- Public surface: true
- Change type: added
- Before: absent — freshness always decayed against `observed_at`
- After: `decay_basis_of(table: HalfLifeTable, observation_type: str) -> DecayBasis` — the twin of `decay_mode_of`, read at the same point in `freshness`: which of the observation's two instants this row decays against. Every table written before the field existed answers `observed-at`, which is the behavior it already had
- Why: `D-IMPL-331` (`b2ba4e8b`) — `Observation` carries both instants; the row selects
- Migration: none
