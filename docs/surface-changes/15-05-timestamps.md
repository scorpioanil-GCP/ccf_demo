# 15-05 — artifact timestamps are read as text (ERGO-06, D-02)

This is the **behavior-only** case, and the worked example for why D-15 ships a
curated log alongside a generated manifest. D-02 changes what `load_artifact`
*returns* for a timestamp-shaped scalar; it adds, removes, and reshapes no
public name. `tools/dump_surface.py --report` reports `added (0)`,
`removed (0)`, `reshaped (0)` for this plan — confirmed empirically — and
`docs/surface/v0.2-surface.json` is untouched. A signature diff is structurally
incapable of seeing this change, so the fragment is where it lives.

The behavior claim is validated instead through the parse path:
`tests/controlplane/test_timestamps.py` pins all five properties — resolver
suppression, `Z` yielding an aware UTC instant, `+00:00` converging on the same
value, the zone-less refusal naming D-IMPL-38, and the shared `yaml.SafeLoader`
being unmutated.

## ccf.controlplane.artifacts.load_artifact

- Surface: ccf.controlplane.artifacts.load_artifact
- Public surface: true
- Change type: behavior
- Before: parsed with `yaml.safe_load`, so PyYAML's timestamp resolver ran and a
  timestamp-shaped scalar arrived as a **naive** `datetime` — which
  `ControlPlaneRegistry.register` then refused as non-canonicalizable, forcing
  every caller to hand-normalize (six distinct helper implementations had
  drifted across eleven sites)
- After: parses through a private `_ArtifactLoader` with the
  `tag:yaml.org,2002:timestamp` resolver removed, so the scalar arrives as
  `str`; a contract field annotated `datetime` parses it into an **aware**
  value, and a date-time naming neither `Z` nor a `±HH:MM` offset is refused at
  parse by `_reject_naive_timestamps` with a message naming D-IMPL-38
- Why: D-02. `Z` is the ISO-8601 UTC designator, not an implicit timezone — the
  author stated UTC explicitly and PyYAML's resolver is what drops it. Refusing
  the author's document punished them for a rule they did not break, because the
  naive value was a *parser* defect rather than an authoring one. The SDK now
  reads timestamps as text and lets the contract parse them, exactly as it
  already refuses floats rather than repairing them. The resolver table is
  copied rather than mutated in place, so YAML parsing elsewhere in the process
  is unaffected.
- Migration: a caller relying on `load_artifact` handing back a `datetime` for a
  field its contract does not annotate as one now receives a `str` — annotate
  the field `datetime` on the contract and Pydantic parses it, aware. A document
  carrying a zone-less date-time is now refused rather than silently read as
  naive; state the zone as `Z` or as an explicit offset. No public
  timestamp-parsing helper is offered, deliberately: one would invite adopters
  to keep hand-normalizing the thing the loader now gets right.
