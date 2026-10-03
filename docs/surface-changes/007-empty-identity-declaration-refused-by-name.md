# 007 — an empty identity declaration is refused by name at the mint

`SEC-007`, the empty-identity leg (Dave, 2026-10-03: the refusal stays at
resolution time; it must raise `IdentityRefused` and produce a governed
refusal replay record through the existing map; a bare `ValueError` is
insufficient; no empty-identity URI may be minted). A rule whose
`identity_keys` is `()` reached `SpecDrivenEntityResolution.resolve` and, since
`20420d2e`, was refused there — but as a bare `ValueError`, which is not in
`SDK_SEAM_REFUSALS`. Measured on the real governed acquisition path at
`621173a1`: the `ValueError` escaped `opened.answer()` as a traceback and no
replay record was written, while a null VALUE on the same path converted to a
governed refusal with a record.

ONE change, at the one name the manifest tracks it under. The manifest tracks
class SHAPE, so the change type is `reshaped`: the constructor's `key` and
`field` became optional and the reason roster gained `undeclared`. Every
existing value refusal keeps its fields, its reason and its message
byte-for-byte. The adjacent partial-identity `ValueError` is untouched by
ruling.

The prefix `007` is the finding number, not a phase or decision id; the
assembler uses it only as a sort key.

## ccf.assembly.worker.IdentityRefused

- Surface: ccf.assembly.worker.IdentityRefused
- Public surface: true
- Change type: reshaped
- Before: `__init__(*, envelope_id: str, entity_class: str, key: str,
  field: str, reason: str)` — every field required; `reason ∈ {"null",
  "empty", "bool", "float", "non-finite", "non-scalar"}`, all of them faults
  of a VALUE on a declared identity key. A rule declaring zero identity keys
  was refused at the same mint site as a bare `ValueError`, outside this class
- After: `__init__(*, envelope_id: str, entity_class: str, reason: str,
  key: str | None = None, field: str | None = None)`. A seventh reason,
  `undeclared`, names an EMPTY DECLARATION: a matching rule with
  `identity_keys == ()` raises `IdentityRefused(envelope_id=…,
  entity_class=…, reason="undeclared")` with `key is None` and
  `field is None`, because nothing was read and there is no key or field to
  name, and its message reads *"envelope … matched rule for …, which declares
  no identity keys (undeclared); the fabric refuses to mint a URI from empty
  identity (SEC-007)"*. The six value reasons keep `key` and `field` set and
  their message unchanged
- Why: `IdentityRefused` is the SDK-owned seam class the governed path
  converts by mechanism (`SDK_SEAM_REFUSALS`, unchanged), so raising the
  empty-declaration fault BY NAME is what turns a traceback with no record
  into a refusal at the `acquisition` seam whose replay record carries
  `identity-refused` / `nonexistent` and the worker's own detail. The map is
  not widened and the product class declares nothing: the conversion is the
  existing one
- Migration: none for a caller constructing the class — `key` and `field`
  are keyword-only and still accepted, so every existing construction site is
  unchanged. A caller that catches `IdentityRefused` and reads `key` or
  `field` must now accept `None` for the `undeclared` reason. A deployment
  whose resolution spec declares a rule with `identity_keys: []` now receives
  a governed refusal on the paved road where it previously received a
  traceback; the declaration itself still constructs, by ruling, so the
  refusal can name the envelope that reached the mint
