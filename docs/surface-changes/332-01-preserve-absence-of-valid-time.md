# 332-01 — preserve absence of valid-time

Recorded at the `f0656746` qualification (2026-09-19) from the introducing commit `59cfc0cd`
(*wip(sdk): D-IMPL-332 — _stitch stops manufacturing valid_from; GQ-09 gains its absence limb*,
2026-09-11; the entry was closed by `D-IMPL-332` Amendment 1 on 2026-09-12), which shipped
without a surface-change fragment. `observed_at` means when the fabric learned the claim;
`valid_from` means when the claim was true in the world. If the source does not supply a
valid-time, `valid_from` is absent — not ingestion time. This fragment claims exactly the two
public names `59cfc0cd` reshaped; what absence means to a validity-window read is defined at
`GQ-09` in `docs/GRAPH_QUERY_SEMANTICS.md`, not on a Python name.

## ccf.contracts.claims.EntityClaim

- Surface: ccf.contracts.claims.EntityClaim
- Public surface: true
- Change type: reshaped
- Before: `valid_from: datetime`, required — `_stitch` substituted ingestion time when the source supplied none, so the two temporal fields could answer the same question
- After: `valid_from: datetime | None`, defaulted to `None` and hash-transparent — `None` is an absent answer, not a default value and not an open interval; the fabric no longer manufactures it
- Why: `D-IMPL-332` (`59cfc0cd`) — a record that makes no valid-time claim cannot be excluded by a valid-time bound, because excluding it would assert *it was not true then*, as much an invention as asserting that it was
- Migration: a reader that assumed `valid_from` is always a datetime handles `None`; a claim written before the change reloads to its address, because the member is hash-transparent

## ccf.contracts.claims.RelationshipClaim

- Surface: ccf.contracts.claims.RelationshipClaim
- Public surface: true
- Change type: reshaped
- Before: `valid_from: datetime`, required — as for `EntityClaim`
- After: `valid_from: datetime | None`, defaulted to `None` and hash-transparent — as for `EntityClaim`
- Why: `D-IMPL-332` (`59cfc0cd`) — the same absence, on the relationship axis
- Migration: as for `EntityClaim`
