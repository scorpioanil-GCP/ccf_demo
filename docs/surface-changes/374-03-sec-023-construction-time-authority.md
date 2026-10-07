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

**The fifth path (coordinator ruling (1), same day).** A reader no boot composed
— a store opened directly, or a mounted peer product — answered a classification
`GraphQuery` with no authority anywhere. Every `GraphQuery`-answering reader entry
now refuses a classification query that carries no authority stamp, fail closed:
`BaseGraphReader.query` (SQLite, Postgres, MongoDB, Neo4j, Fluree),
`MemoryGraphReader.query`, `FlureeGraphReader.query_pinned` and
`ProductSource.query`. The booted reader stamps a query after checking it, so the
paved road is unchanged (`tests/graph/test_raw_reader_classification_authority.py`).

**Fix round 1 (review I-1, ruled): the stamp is minted, not declared.** A
`ClassificationAuthority` is minted only by `ccf.boot.boot`, from the resolution
spec its L2 enforces, through a module-private mint key (the `BootToken` /
`_MINT_KEY` pattern), and carries that spec's content address. The stamping
methods are private. A consumer refuses a hand-built authority by name
(`ClassificationAuthorityNotMinted`), and `require` refuses an attribute the
authority knows nothing about, so an empty authority covers nothing. Tests obtain
their authority through boot (`tests/classification_authority.py`).

**Disclosed boundaries, ruled rather than fixed.**
- **An out-of-tree reader** that implements `GraphReader` without subclassing
  `BaseGraphReader` is unguarded on a direct classification query unless it calls
  `require_query_classification_authority` itself; nothing enforces that it does.
  Inside the engine, `PolicyFilter.apply` still refuses its unstamped views.
- **Replay of a record minted under an ungoverned spec** now raises
  `UngovernedClassificationAttribute` / `ClassificationAuthorityMissing` out of
  `replay()`, outside the typed `ReplayUnresolvable` taxonomy, and
  `SnapshotPinUnresolvable`'s message can name the wrapper class. Carried.
- **The declared-read boundary** (ruling (2)): the registry builder checks a
  deployment operator through its declared `read_intent`. An operator that filters
  on a classification attribute WITHOUT declaring it there is not checked when it
  is registered; its own `apply` must call `require_classification_authority`. This
  is a residual, carried by name.
- **A mounted peer product refuses** (ruling (3)): a `ProductSource`'s labels were
  governed by no local L2, so a `PolicyFilter` over its views, or a classification
  query against it, refuses. Accepted as fail-closed.
- **An authorized source may blank the label** (ruling (4)): the omission audit
  covers a source that is NOT authorized for the attribute, and records the
  omission whether or not a label was present (it fires on a first observation
  too, so its volume scales with non-authoritative ingest). A source that IS
  authorized may set the label in either direction, including by omitting it,
  without an event — by design, because the authority carries that responsibility.

## ccf.graph.protocols.require_query_classification_authority

- Surface: ccf.graph.protocols.require_query_classification_authority
- Public surface: true
- Change type: added
- Before: absent. A store reader answered any classification query.
- After: `require_query_classification_authority(q)` — passes a query with no classification map; otherwise refuses a query carrying no authority (`ClassificationAuthorityMissing`) and one whose authority does not cover the map (`UngovernedClassificationAttribute`). Called first by every `GraphQuery`-answering reader entry.
- Why: coordinator ruling (1): the fifth path fails closed.
- Migration: a classification query goes through `FabricHandle.reader`; a store or mounted product queried directly refuses it.

## ccf.graph.protocols.GraphQuery

- Surface: ccf.graph.protocols.GraphQuery
- Public surface: true
- Change type: behavior
- Before: no authority.
- After: carries an optional classification authority as a PRIVATE attribute (`classification_authority`; the stamping method is private), outside the canonical form and outside equality, so `content_hash(q)` — the replay pin — and the engine's recorded query sequence are unchanged. The booted reader stamps a query after checking it.
- Why: the store reader can tell a checked query from one that came another way.
- Migration: none on the paved road.

## ccf.graph.reader.BaseGraphReader

- Surface: ccf.graph.reader.BaseGraphReader
- Public surface: true
- Change type: behavior
- Before: `query` answered any classification query.
- After: `query` runs `require_query_classification_authority` before any substrate I/O. SQLite, Postgres, MongoDB, Neo4j and Fluree inherit it.
- Why: the fifth path.
- Migration: send classification queries through `FabricHandle.reader`.

## ccf.graph.backends.memory.MemoryGraphReader

- Surface: ccf.graph.backends.memory.MemoryGraphReader
- Public surface: true
- Change type: behavior
- Before: `query` answered any classification query.
- After: `query` refuses an unstamped classification query.
- Why: the fifth path.
- Migration: as for `BaseGraphReader`.

## ccf.graph.backends.fluree.FlureeGraphReader

- Surface: ccf.graph.backends.fluree.FlureeGraphReader
- Public surface: true
- Change type: behavior
- Before: `query_pinned` answered any classification query.
- After: `query_pinned` refuses an unstamped classification query before any I/O (its `query` is `BaseGraphReader.query`).
- Why: the fifth path; the one `SnapshotPinnable` store entry.
- Migration: as for `BaseGraphReader`.

## ccf.graph.product_source.ProductSource

- Surface: ccf.graph.product_source.ProductSource
- Public surface: true
- Change type: behavior
- Before: `query` answered any classification query over the mounted product.
- After: `query` refuses an unstamped classification query (ruling (3), fail closed).
- Why: a peer product's labels were governed by no local L2.
- Migration: none supported; a classification answer over a peer product is refused (ruling (3)).

## ccf.graph.protocols.ClassificationAuthority

- Surface: ccf.graph.protocols.ClassificationAuthority
- Public surface: true
- Change type: added
- Before: absent. No classification consumer could see which sources the resolution spec in force authorizes.
- After: a contract `(spec_address, governed: class -> attribute -> frozenset[system_id], written: class -> frozenset[attribute])`, both mappings read-only, with `minted` and `require(by_class, *, consumer)`. `require` raises `UngovernedClassificationAttribute` for any attribute it does not govern — one the spec writes ungoverned, or one it knows nothing about. Minted only by `ccf.boot.boot`; a hand-built instance is refused by every consumer.
- Why: SEC-023, `D-IMPL-374` ruling (3) (a) and fix round 1 (I-1): the value threaded from the composition root to every classification consumer must attest what L2 enforces, not declare it.
- Migration: none. Read through `FabricHandle.reader`; there is no supported way to build one.

## ccf.graph.protocols.ClassificationAuthorityNotMinted

- Surface: ccf.graph.protocols.ClassificationAuthorityNotMinted
- Public surface: true
- Change type: added
- Before: absent.
- After: a `ValueError` subclass carrying `consumer`, raised when a classification consumer (or `governed_reader`) meets an authority `ccf.boot.boot` did not mint.
- Why: fix round 1, I-1 (b).
- Migration: none.

## ccf.graph.protocols.ClassificationAuthorityMissing

- Surface: ccf.graph.protocols.ClassificationAuthorityMissing
- Public surface: true
- Change type: added
- Before: absent. A `PolicyFilter` applied over a hand-built view admitted on whatever labels it carried.
- After: a `ValueError` subclass carrying `consumer`, raised when a classification consumer meets a `GraphView` with no authority stamp.
- Why: coordinator ruling (2) under `D-IMPL-374`: fail closed, by name. A view that carries a classification map silently is the hole.
- Migration: read views through `FabricHandle.reader`.

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
- After: carries an optional classification authority as a PRIVATE attribute (`classification_authority` property; the stamping method is private, called by the booted reader and the shipped operators). It is outside the canonical form and outside equality, so a view's content hash and every record built from one are the same stamped or not (proven by `test_the_authority_stamp_leaves_every_record_identity_unchanged`).
- Why: coordinator ruling (1): the stamp must be hash-transparent, so no replay record changes.
- Migration: none.

## ccf.boot.boot

- Surface: ccf.boot.boot
- Public surface: true
- Change type: behavior
- Before: `FabricHandle.reader` was the store's reader.
- After: `boot` mints the `ClassificationAuthority` of the resolution spec its L2 enforces (the only mint) and `FabricHandle.reader` is `governed_reader(store.reader, <that authority>)`. A classification `GraphQuery` the authority does not cover is refused; every view and every checked query carries the authority.
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
