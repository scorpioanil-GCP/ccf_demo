# 15-09 — artifact classes for the signal batch, the perspective, and the product class

Plan 15-09 closes the remaining hand-marshalled shapes ROADMAP Success Criterion 2
names: the signal batch (116 lines across nine sites), the perspective (40 across
ten), and the product-class declaration (90 across ten). Six names are added —
three contracts and three `ArtifactClass` constants — and the **artifact-document
format for event files changes**, which is recorded here as its own entry because
a `__all__`-derived manifest diff can never show it.

`ccf/signal/envelope.py` is **not edited**. `SignalEnvelope` and `SourceIdentity`
are unchanged, `raw_payload` stays opaque to L1, and its keys stay the source
system's vocabulary. What changed is the *document*, not the contract: the batch
adopts the SDK's own field names rather than the SDK growing a second set to
accommodate the document's.

The 20 example `events.yaml` files are **not reshaped by this plan**. Each example
rewrite (15-13 through 15-20) reshapes its own, so the document change is
reviewable alongside the code that reads it.

## ccf.controlplane.artifacts.SignalBatch

- Surface: ccf.controlplane.artifacts.SignalBatch
- Public surface: true
- Change type: added
- Before: absent — every example hand-built envelopes in a comprehension,
  translating three keys per event (`source_system_id` into a nested
  `SourceIdentity`, `payload` into `raw_payload`) and reading `tenant_id` out of
  a different document entirely
- After: a `VersionedArtifact` declaring `tenant_id: str` and
  `envelopes: tuple[SignalEnvelope, ...]` with `min_length=1`, plus a
  `model_validator` refusing a batch whose envelopes name another tenant
- Why: the translation is **removed** rather than relocated. A translation moved
  into `/src` is the same defect with a better address, and a second field
  vocabulary for a shape the SDK already owns is exactly what drifts. The batch
  carries `tenant_id` because every event in a batch belongs to one tenant and
  that value currently lives in the ontology document, which D-03 makes
  closed-world over resolution rules only — carrying it here keeps it authored,
  once, in the artifact that needs it rather than in a loader argument no
  artifact records. Disagreement is refused, never repaired: stamping the batch's
  value onto an envelope that said otherwise would put a value nobody authored
  into the fabric's observation record (T-15-09-01)
- Migration: replace the envelope comprehension with
  `parse_artifact(document, SIGNAL_BATCH)` and reshape the event document per the
  `ccf.signal-batch` entry below. The parsed `envelopes` are real
  `SignalEnvelope` instances and need no unwrapping

## ccf.controlplane.artifacts.SIGNAL_BATCH

- Surface: ccf.controlplane.artifacts.SIGNAL_BATCH
- Public surface: true
- Change type: added
- Before: absent — no class-id addressed an event batch, so a D-05 manifest could
  not name one
- After: `ArtifactClass(class_id="ccf.signal-batch", contract=SignalBatch)`,
  registered in `ccf.deployment.classes.SDK_ARTIFACT_CLASSES`
- Why: **this is a `role: load` class under D-IMPL-80** and the asymmetry is the
  point. It is parsed and validated through the same `parse_artifact` seam as
  every other class and `load_and_boot` returns it on the boot result, but it is
  never passed to `register_typed` and never appears in the pin set. Registering
  a batch would content-hash raw event data into Control Plane state, and by
  D-06's own rationale the registered artifact set is dimension 2 of the
  five-dimension Decision Replay record — re-authoring an events file would then
  change "what was in force" exactly as a policy-bundle bump does, which is not
  what an event stream is (T-15-09-05)
- Migration: name `ccf.signal-batch` in the manifest entry with `role: load`. A
  manifest entry naming no `role` is refused; one naming `role: register` for
  this class puts an events file into replay dimension 2, which is the mistake
  D-IMPL-80 exists to make impossible to reach by accident

## ccf.controlplane.artifacts.PerspectiveArtifact

- Surface: ccf.controlplane.artifacts.PerspectiveArtifact
- Public surface: true
- Change type: added
- Before: absent — `Perspective(principal_id=..., role=...)` built by hand at ten
  sites from two keys read out of a control-plane document
- After: a contract subclassing `ccf.projection.plan.Perspective` verbatim plus
  the `semver` lane
- Why: the same shape plan 15-08 used for the operator-parameters classes. A
  parsed artifact **is** a `Perspective`, so there is no second vocabulary to
  drift and no adapter step between reading the document and conditioning the
  projection. `principal_id` and `role` keep the meanings §7.5 gives them
  (INV-CH7-43) and land verbatim in replay dimension 4
- Migration: `parse_artifact(document, PERSPECTIVE)`; the result passes straight
  into projection invocation with no unwrapping

## ccf.controlplane.artifacts.PERSPECTIVE

- Surface: ccf.controlplane.artifacts.PERSPECTIVE
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.perspective", contract=PerspectiveArtifact)`,
  registered in `SDK_ARTIFACT_CLASSES`
- Why: manifest addressability — a class the SDK ships that a manifest cannot
  address is a class no adopter can register
- Migration: name `ccf.perspective` in the manifest entry

## ccf.controlplane.artifacts.ProductClassDeclaration

- Surface: ccf.controlplane.artifacts.ProductClassDeclaration
- Public surface: true
- Change type: added
- Before: absent — `register_product_class(...)` was called with six keyword
  arguments assembled by hand from a control-plane document at ten sites
- After: a `VersionedArtifact` declaring `schema_name`, `schema_version`,
  `ttl_anchor`, `assembly_mode`, `max_ttl_key`, and
  `required_operator_keys: tuple[str, ...]` with `min_length=1`. It declares
  **no** `max_ttl_version`
- Why: two deliberate omissions and one deliberate addition.
  **`max_ttl_version` is absent** because that pin is minted by *registering* the
  `MaxTTL` value and is a content hash of what was registered — the same shape
  D-IMPL-76 ruled on for the policy bundle's admitted-version set. An artifact
  declaring it would be authoring a hash of something it does not contain, and it
  would collapse Gate 3: the TTL ceiling stays an authored artifact value, the pin
  is derived from registering it, and a product's `expires_at` remains a
  separately authored number — Gate 3 checks one against the other, which is only
  a check while the two come from independent places (T-15-09-02).
  **`required_operator_keys` is present** because it is what a projection's
  `required_operators()` returns, and giving it an authored source is what keeps
  the projection's declaration and the engine's resolution two independent
  mechanisms. Gate 2 compares them for strict equality (INV-CH7-47); a projection
  returning the operator registry's own keys makes that comparison a value against
  itself and the gate silently stops being a gate (T-15-09-06). Every example in
  the tree today passes `operators.keys()` or `self._registry().keys()`, which is
  exactly that shortcut; plan 15-21 adds a standing AST guard against it. It lives
  on the product class rather than on a projection artifact because the product
  class is already the artifact that declares what the product *is*, and the
  operator set an interpretation requires is a property of the product, not of the
  code computing it
- Migration: `parse_artifact(document, PRODUCT_CLASS)`, and the document states
  **no** `max_ttl_version` — the contract is closed-world, so including one is a
  parse failure. Keep the `register_product_class` call in adopter code: this plan
  ships no helper that registers on the adopter's behalf, because the manifest
  entry point (15-10) owns registration and a second registration path would make
  "what was in force" answerable from two places. The document must also name at
  least one `required_operator_keys` entry (see below)

## ccf.controlplane.artifacts.PRODUCT_CLASS

- Surface: ccf.controlplane.artifacts.PRODUCT_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.product-class", contract=ProductClassDeclaration)`,
  registered in `SDK_ARTIFACT_CLASSES`
- Why: manifest addressability, same as its siblings
- Migration: name `ccf.product-class` in the manifest entry

## ccf.signal-batch

- Surface: ccf.signal-batch
- Public surface: false
- Change type: reshaped
- Before: the event document used flat keys the SDK contract does not declare —
  `source_system_id:` for what the contract nests as `source: {system_id: ...}`,
  and `payload:` for what the contract calls `raw_payload:`. `tenant_id` was not
  in the event document at all; it was read from `ontology.yaml`
- After: the document is in the SDK's own envelope vocabulary — nested
  `source: {system_id: ...}` and `raw_payload:` — with `tenant_id` declared once
  on the batch, alongside the batch's `semver` lane
- Why: the translation between the two vocabularies is **removed rather than
  relocated**. The SDK does not grow a second field vocabulary for a shape it
  already owns, and D-15B permits the churn. The change is to the *container*
  keys only: `raw_payload`'s contents stay opaque to L1 and its keys stay the
  source system's vocabulary, exactly as `SignalEnvelope`'s docstring states
  (T-15-09-04, accepted). This entry is `Public surface: false` because an
  artifact-document format change can never appear in an `__all__`-derived
  manifest diff — see `docs/surface-changes/README.md`
- Migration: transform each event document mechanically —
  1. `source_system_id: X` becomes `source:` / `  system_id: X`
  2. `payload:` becomes `raw_payload:` (contents unchanged)
  3. add `tenant_id:` at the batch root, carrying the value previously read from
     the ontology document, and add `tenant_id:` on each envelope — the batch
     refuses a disagreement rather than stamping over one
  4. add the artifact's own `semver:` lane at the document root

  `envelope_id`, `ingestion_timestamp` and `observed_time` are unchanged.
  Timestamps ending in `Z` now parse to aware UTC values through the artifact
  loader, so the per-example `_instant` helper that re-parsed them is redundant.
