# 372-23 — SEC-023: a governed attribute is asserted only by a source authorized for it

`D-IMPL-372` (and `D-IMPL-368..371`), row SEC-023, ruling Q15 (a) of
`docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md`. Measured
before this entry: a policy classification is an ordinary attribute, and the
claim with the latest ingestion stamp supersedes the whole attribute dict
(`src/ccf/graph/_writer.py::BaseGraphWriter._restitch_chain`). So any source
relabeled an entity another source had classified `restricted` as `public`
just by speaking later, and `PolicyFilter` for a `public`-only principal then
served it. The exploit test is `tests/assembly/test_classification_authority.py`.

**Ruled placement, `D-IMPL-372`:** the authority is declared per attribute on
the `ccf.resolution-spec` rule. The policy bundle is an opaque
`DeclaredArtifact`, and the SDK does not invent its schema. **Ruled
disposition:** a claim that asserts a governed attribute from a source that is
not authorized for it is refused whole. The attribute is never stripped and
never merged. The refusal is recorded on the audit log and is never raised.
**Ruled posture:** the field is optional, and it fails closed wherever it is
declared. **Dave's correction (2026-10-06):** completion requires fail-closed
enforcement wherever classification controls access. So a paved-road
deployment whose `PolicyFilter` admits on an attribute that a resolution rule
writes without an authority declaration now **refuses to boot** with
`UngovernedClassificationAttribute`. The read path does not change.

## ccf.assembly.worker.EntityResolutionRule

- Surface: ccf.assembly.worker.EntityResolutionRule
- Public surface: true
- Change type: reshaped
- Before: no way to say which source may assert an attribute. Every attribute in `attribute_keys` was source-asserted.
- After: adds `attribute_authorities: Mapping[str, frozenset[str]]`, which maps a governed attribute to the `SourceIdentity.system_id` values allowed to assert it. It defaults to empty and is hash-transparent when empty (`D-IMPL-243`), so every existing rule keeps its content hash. An empty source set is fail-closed: no source may assert that attribute. A key that is not one of `attribute_keys` is refused at construction (`ValueError` naming `attribute_authorities`).
- Why: SEC-023. This is the only SDK-typed Control Plane artifact the L2 worker holds when it writes a claim.
- Migration: none for existing artifacts. To govern an attribute, declare `attribute_authorities: {<attribute>: [<system id>, ...]}` on every rule that carries it.

## ccf.assembly.worker.EntityResolutionSpec

- Surface: ccf.assembly.worker.EntityResolutionSpec
- Public surface: true
- Change type: behavior
- Before: no cross-rule check.
- After: if any rule of an entity class governs an attribute, every rule of that class that carries the attribute must declare the identical source set. Otherwise the spec is refused at construction. Adds `governed_attributes()`, which returns class -> attribute -> authorized sources.
- Why: the source's payload decides which rule fires. Without this check, a source could present the match key of a second rule that does not govern the attribute and assert it there.
- Migration: none unless a spec already governs an attribute.

## ccf.assembly.worker.RefusedAssertion

- Surface: ccf.assembly.worker.RefusedAssertion
- Public surface: true
- Change type: added
- Before: absent.
- After: a contract `(entity_uri, entity_class, attribute, source_system_id, envelope_id)`. It carries no value.
- Why: lets the caller see a refusal. The record of truth is the audit event.
- Migration: none.

## ccf.assembly.worker.IngestResult

- Surface: ccf.assembly.worker.IngestResult
- Public surface: true
- Change type: reshaped
- Before: `entities` and `relationships` only.
- After: adds `refused_assertions: tuple[RefusedAssertion, ...]`, which defaults to `()` and is hash-transparent when empty.
- Why: SEC-023. A refusal is an outcome that `ingest` returns. It is never an exception.
- Migration: none.

## ccf.assembly.worker.AssemblyWorker

- Surface: ccf.assembly.worker.AssemblyWorker
- Public surface: true
- Change type: behavior
- Before: `ingest` wrote every resolved entity's claim, whatever its source.
- After: `ingest` writes no claim for an entity whose source is outside the declared set for a governed attribute it asserts. It derives no relationship from that entity in the same envelope. For each refused attribute it appends one `attribute_assertion_refused` event to the Control Plane audit log, with `occurred_at` set to the envelope's ingestion timestamp. It returns normally.
- Why: if the refusal were raised, a non-authoritative source could refuse every serve whose acquisition touched it, through `src/ccf/products/resolver.py::SDK_SEAM_REFUSALS`.
- Migration: none for ungoverned attributes.

## ccf.controlplane.audit.AuditAction

- Surface: ccf.controlplane.audit.AuditAction
- Public surface: true
- Change type: reshaped
- Before: 22 members ending in `composition`.
- After: adds `attribute_assertion_refused`, which is always `resolved=False`.
- Why: none of the existing members can describe a refused L2 write without making the log say something untrue.
- Migration: a consumer that matches exhaustively on the action vocabulary adds the member.

## ccf.controlplane.audit.AttributeAssertionRefusedAuditEvent

- Surface: ccf.controlplane.audit.AttributeAssertionRefusedAuditEvent
- Public surface: true
- Change type: added
- Before: absent.
- After: a derived `AuditEvent` with `refused_entity_class`, `refused_attribute`, `refused_source_system_id`, `refused_envelope_id` and `refused_value_present`. Each field is hash-transparent at `None`. `AuditLog.append` builds this event when it receives `refused_attribute`. The refused value is never recorded (SEC-024 discipline).
- Why: an examiner can ask which source tried to relabel which entity, without the audit plane holding a copy of the data the label protects.
- Migration: none.

## ccf.controlplane.audit.AuditLog

- Surface: ccf.controlplane.audit.AuditLog
- Public surface: true
- Change type: reshaped
- Before: `append` accepted the authz and verdict-integrity keywords.
- After: `append` also accepts the five `refused_*` keywords. Each defaults to `None`, so every existing call shape appends exactly what it appended before.
- Why: SEC-023.
- Migration: none.

## ccf.deployment.manifest.UngovernedClassificationAttribute

- Surface: ccf.deployment.manifest.UngovernedClassificationAttribute
- Public surface: true
- Change type: added
- Before: absent. A deployment could admit on an attribute that any source could relabel.
- After: a `ValueError` subclass carrying `operator_key`, `entity_class` and `attribute`. `_register_and_boot` raises it before anything is registered, which covers both `load_and_boot` and `load_config_and_boot`. It is raised when a `PolicyFilterParametersArtifact` names `classification_attribute_by_class: {class: attribute}` and the resolution spec in force has a rule of that class that writes the attribute without `attribute_authorities` for it. A class that no rule writes the attribute for is not refused. Nothing source-asserts that attribute, and `PolicyFilter` admits such an entity to nobody.
- Why: SEC-023, Dave's correction of 2026-10-06. The L2 refusal governs only what a deployment declares. This check makes the declaration mandatory wherever classification controls access.
- Migration: a deployment whose `PolicyFilter` names a classification attribute declares `attribute_authorities` for it on every rule that writes it. Every shipped example config and the banking fixtures were updated. A fabric composed by hand through `ccf.boot.boot` never sees operator parameters, so this check does not cover it (the low road, `D-IMPL-364`).
