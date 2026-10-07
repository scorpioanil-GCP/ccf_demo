# 374-03 — SEC-023: classification authority enforced at the construction of the consumer

`D-IMPL-374` ruling (3) (a), with the coordinator's rulings of 2026-10-06:
(1) the booted fabric carries the resolution spec's authority on every view it
reads, and the registry build, `reader.query` and `PolicyFilter.apply` are the
construction-time enforcement; (2) a view with no authority meeting a
classification consumer is refused by name; (3) an unauthorized OMISSION of a
governed attribute is audited and admitted (`SEC-023-C-01`).

Measured before this entry (`D-IMPL-372`, dated amendment of 2026-10-06 12:12
MST): the boot-time check (`src/ccf/deployment/manifest.py::_refuse_ungoverned_classification`)
read only parsed `PolicyFilterParametersArtifact` objects on the two paved
doors, so four classification paths neither enforced authority nor refused —
a `GraphQuery`-only classification map, a hand-built `PolicyFilter` in
`deployment_operators`, a hand-composed `ccf.boot.boot`, and a per-request
`build_operator_registry`. Each is now a red-then-green test in
`tests/deployment/test_classification_authority_consumer.py`; the omission
audit is in `tests/assembly/test_classification_authority.py`. The boot-time
check stays as the early refusal.

## ccf.graph.protocols.ClassificationAuthority

- Surface: ccf.graph.protocols.ClassificationAuthority
- Public surface: true
- Change type: added
- Before: absent. No classification consumer could see which sources the resolution spec in force authorizes.
- After: a frozen contract `(governed: class -> attribute -> frozenset[system_id], written: class -> frozenset[attribute])` with `require(by_class, *, consumer)`, which raises `UngovernedClassificationAttribute` for a class whose attribute is written from the payload with no authority declaration. Built by `EntityResolutionSpec.classification_authority()`.
- Why: SEC-023, `D-IMPL-374` ruling (3) (a). This is the value threaded from the composition root to every classification consumer.
- Migration: none. A composition root that reads a store without `ccf.boot.boot` stamps its views with `spec.classification_authority()` of the spec its L2 enforces.

## ccf.graph.protocols.ClassificationAuthorityMissing

- Surface: ccf.graph.protocols.ClassificationAuthorityMissing
- Public surface: true
- Change type: added
- Before: absent. A `PolicyFilter` applied over a hand-built view admitted on whatever labels it carried.
- After: a `ValueError` subclass carrying `consumer`, raised when a classification consumer meets a `GraphView` with no authority stamp.
- Why: coordinator ruling (2) under `D-IMPL-374`: fail closed, by name. A view that carries a classification map silently is the hole.
- Migration: read views through `FabricHandle.reader`, or stamp them with `GraphView.with_classification_authority`.

## ccf.graph.protocols.UngovernedClassificationAttribute

- Surface: ccf.graph.protocols.UngovernedClassificationAttribute
- Public surface: true
- Change type: added
- Before: defined in `ccf.deployment.manifest` and raised only at boot.
- After: defined here, beside the view the consumer-time check reads; `ccf.deployment.manifest.UngovernedClassificationAttribute` is the same class, re-exported, so existing imports and `except` clauses keep working. Raised at boot (`operator_key` the manifest key) and by `ClassificationAuthority.require` (`operator_key` the consumer: a manifest key, an operator key, or `GraphQuery`).
- Why: `ccf.graph` cannot import `ccf.deployment`; one class serves both refusal sites.
- Migration: none.

## ccf.graph.protocols.require_classification_authority

- Surface: ccf.graph.protocols.require_classification_authority
- Public surface: true
- Change type: added
- Before: absent.
- After: `require_classification_authority(view, by_class, *, consumer)` — passes a `None` map; otherwise refuses a view with no authority (`ClassificationAuthorityMissing`) and a map the view's authority does not cover (`UngovernedClassificationAttribute`). The one check `PolicyFilter.apply` and `build_operator_registry` run.
- Why: one function, so the consumers cannot disagree about what covering authority means.
- Migration: none. A third-party policy operator that admits on a classification map calls it in `apply`.

## ccf.graph.governed_reader.governed_reader

- Surface: ccf.graph.governed_reader.governed_reader
- Public surface: true
- Change type: added
- Before: absent. `FabricHandle.reader` was the store's reader itself.
- After: wraps a reader so every view it returns carries the authority, and a `GraphQuery` (or pinned query) with a classification map is refused before the substrate is asked anything unless the authority covers it. The result is `SnapshotPinnable` exactly when the wrapped reader is; every other attribute is forwarded.
- Why: `ccf.boot.boot` is the only place both the resolution spec and the reader are in hand.
- Migration: none.

## ccf.graph.protocols.GraphView

- Surface: ccf.graph.protocols.GraphView
- Public surface: true
- Change type: behavior
- Before: records only.
- After: carries an optional classification authority as a PRIVATE attribute (`classification_authority` property, `with_classification_authority(authority)` copy). It is outside the canonical form and outside equality, so a view's content hash and every record built from one are the same stamped or not (proven by `test_the_authority_stamp_leaves_every_record_identity_unchanged`).
- Why: coordinator ruling (1): the stamp must be hash-transparent, so no replay record changes.
- Migration: none.

## ccf.assembly.worker.EntityResolutionSpec

- Surface: ccf.assembly.worker.EntityResolutionSpec
- Public surface: true
- Change type: behavior
- Before: `governed_attributes()` only.
- After: adds `classification_authority()`, the `ClassificationAuthority` this spec enforces at L2.
- Why: SEC-023, `D-IMPL-374`.
- Migration: none.

## ccf.boot.boot

- Surface: ccf.boot.boot
- Public surface: true
- Change type: behavior
- Before: `FabricHandle.reader` was the store's reader.
- After: `FabricHandle.reader` is `governed_reader(store.reader, spec.classification_authority())`. A classification `GraphQuery` the spec's authority does not cover is refused; every view carries the authority.
- Why: path 1 and path 3 of the `D-IMPL-372` amendment — a hand-composed boot never sees operator parameters, so the boot-time check could not cover it.
- Migration: a hand-composed deployment whose classification attribute is written without `attribute_authorities` must declare them; before, it served whatever label the latest source wrote.

## ccf.operators.categories.PolicyFilter

- Surface: ccf.operators.categories.PolicyFilter
- Public surface: true
- Change type: behavior
- Before: `apply` admitted on the view's labels, wherever the view came from.
- After: `apply` first runs `require_classification_authority` on its view: `ClassificationAuthorityMissing` for an unstamped view, `UngovernedClassificationAttribute` for an uncovered map. Views produced by the shipped operators carry the input view's authority forward.
- Why: path 3 of the `D-IMPL-372` amendment; coordinator ruling (2).
- Migration: tests and harnesses that apply a `PolicyFilter` over hand-built views stamp them (`tests/properties/strategies.py::AUTHORITY` is the worked case).

## ccf.deployment.operators.build_operator_registry

- Surface: ccf.deployment.operators.build_operator_registry
- Public surface: true
- Change type: behavior
- Before: built a `PolicyFilter` from any policy artifact, and registered any `deployment_operators`, without consulting authority.
- After: before registering, checks every Policy operator it builds and every deployment operator whose read intent carries a classification map against the authority `view` was read under. Signature unchanged — the six frozen specimens' four-argument calls keep working.
- Why: paths 2 and 4 of the `D-IMPL-372` amendment.
- Migration: none when `view` comes from `FabricHandle.reader`.

## ccf.assembly.worker.AssemblyWorker

- Surface: ccf.assembly.worker.AssemblyWorker
- Public surface: true
- Change type: behavior
- Before: an entity claim from a source not authorized for a governed attribute that OMITTED the attribute was written and blanked the label with no record (`SEC-023-C-01`).
- After: still written (admitted), and each omitted governed attribute is appended as one `governed_attribute_omitted` event (`resolved=True`, `refused_value_present=False`).
- Why: coordinator ruling (3): audit AND admit. The refusal event's schema has no reason field, so a new member names the omission instead of recording an admission as a refusal.
- Migration: none.

## ccf.controlplane.audit.AuditAction

- Surface: ccf.controlplane.audit.AuditAction
- Public surface: true
- Change type: reshaped
- Before: 23 members ending in `attribute_assertion_refused`.
- After: adds `governed_attribute_omitted`, always `resolved=True`.
- Why: SEC-023-C-01, coordinator ruling (3).
- Migration: a consumer that matches exhaustively on the action vocabulary adds the member.

## ccf.controlplane.audit.AuditEvent

- Surface: ccf.controlplane.audit.AuditEvent
- Public surface: true
- Change type: reshaped
- Before: `action` typed over 23 members.
- After: `action` typed over 24 (adds `governed_attribute_omitted`). No field added; canonical bytes of every existing event unchanged.
- Why: the `AuditAction` member above.
- Migration: none.

## ccf.controlplane.registry.AuditEvent

- Surface: ccf.controlplane.registry.AuditEvent
- Public surface: true
- Change type: reshaped
- Before: the re-export of `ccf.controlplane.audit.AuditEvent` over 23 actions.
- After: the same re-export over 24.
- Why: the `AuditAction` member above.
- Migration: none.

## ccf.controlplane.audit.AuthzDecisionAuditEvent

- Surface: ccf.controlplane.audit.AuthzDecisionAuditEvent
- Public surface: true
- Change type: reshaped
- Before: inherited `action` over 23 members.
- After: inherited `action` over 24.
- Why: the `AuditAction` member above.
- Migration: none.

## ccf.controlplane.audit.WorkflowVerdictIntegrityAuditEvent

- Surface: ccf.controlplane.audit.WorkflowVerdictIntegrityAuditEvent
- Public surface: true
- Change type: reshaped
- Before: inherited `action` over 23 members.
- After: inherited `action` over 24.
- Why: the `AuditAction` member above.
- Migration: none.

## ccf.controlplane.audit.AttributeAssertionRefusedAuditEvent

- Surface: ccf.controlplane.audit.AttributeAssertionRefusedAuditEvent
- Public surface: true
- Change type: reshaped
- Before: inherited `action` over 23 members; carried only `attribute_assertion_refused`.
- After: inherited `action` over 24; also carries `governed_attribute_omitted` (`resolved=True`, `refused_value_present=False`). The `action` member, not the field names, says which happened.
- Why: SEC-023-C-01 reuses the five `refused_*` fields rather than adding a parallel keyword family to `AuditLog.append`.
- Migration: a reader of `refused_*` fields filters on `action`.

## examples/cp-04-corporate-family-tree/ccf_config.yaml

- Surface: examples/cp-04-corporate-family-tree/ccf_config.yaml
- Public surface: false
- Change type: behavior
- Before: the frozen specimen's resolution spec wrote its classification attribute with no `attribute_authorities`, so it refused to boot under SEC-023.
- After: the authority declaration is added (executor ruling (b) at `D-IMPL-374`), with a dated README note. Nothing else in the specimen changed beyond that note.
- Why: `D-IMPL-261` permits a specimen change when the SDK surface it consumes was deliberately changed.
- Migration: none.

## examples/cp-05-credit-exposure-rollup/ccf_config.yaml

- Surface: examples/cp-05-credit-exposure-rollup/ccf_config.yaml
- Public surface: false
- Change type: behavior
- Before: the frozen specimen's resolution spec wrote `family_id` on `exposure_anchor` with no `attribute_authorities`, so it refused to boot; three `tests/products/test_cp05_canonical_path.py` tests errored at setup and three `tests/signal_layer/test_cp05_acquisition_boundary.py` tests failed.
- After: the authority declaration is added (executor ruling (b) at `D-IMPL-374`), with a dated README note. Nothing else in the specimen changed beyond that note.
- Why: `D-IMPL-261` permits a specimen change when the SDK surface it consumes was deliberately changed.
- Migration: none.
