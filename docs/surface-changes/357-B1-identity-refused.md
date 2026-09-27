# 357-B1 — an identity component is admissible or refused, by name, at the single mint site

`D-IMPL-357` B1 (SEC-007). `SpecDrivenEntityResolution.resolve` — the one L2
mint site (`src/ccf/assembly/worker.py`) — now raises a named refusal
instead of rendering a null, blank, boolean, float, or non-scalar identity
value through bare `str()` into a string every such record shared, which
minted one phantom node and, through the relationship rules, false edges
onto it.

## ccf.assembly.worker.IdentityRefused

- Surface: ccf.assembly.worker.IdentityRefused
- Public surface: true
- Change type: added
- Before: absent — an inadmissible identity value rendered through bare
  `str()` and silently minted a shared phantom URI (SEC-007)
- After: `class IdentityRefused(ValueError)`, raised by
  `SpecDrivenEntityResolution.resolve` with `envelope_id`, `entity_class`,
  `key`, `field` and `reason` (`reason ∈ {"null", "empty", "bool", "float",
  "non-finite", "non-scalar"}` — the widest refusal set ruling B1 declares,
  plus the `non-finite` reason added in fix round 1 for a non-finite
  `Decimal`, which is a scalar and was previously misnamed `non-scalar`)
- Why: presence is not admissibility (D-IMPL-357 B1); the class is public so
  a caller can catch it by name, and B3 converts the SDK's own seam class by
  exactly this qualified string (`ccf.assembly.worker.IdentityRefused`)
- Migration: none for existing deployments — every value that minted before
  this change still mints the identical URI (D-IMPL-357 B2 / D-IMPL-316,
  including `numbers.Integral` values such as `numpy.int64` after fix round
  1); a caller that wants to catch the refusal imports
  `ccf.assembly.worker.IdentityRefused`
