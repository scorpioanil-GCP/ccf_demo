"""The Assembly worker — the one component that holds a graph write handle.

Whitepaper §7.1 (L2), §7.3 (graph state), §7.8 (Control Plane binding);
DESIGN.md §2A.3 and §2A.5.4 (the write path, end to end).

Assembly is where the four concerns converge (INV-CH7-03), and this module runs
three of them for the vertical slice — the fourth, operator invocation, is L4's
read side and lands with the operator plan:

**1. Entity resolution.** Fragmented native identifiers from disparate source
systems converge onto one canonical, tenant-scoped URI (INV-CH7-18, D-IMPL-35).
The strategy is a Protocol seam, not a subclass hook, and the reference
implementation is driven entirely by a *user-declared* spec resolved from the
Control Plane. Which payload keys identify a counterparty, and what a
counterparty even is, are deployment vocabulary; the SDK ships the correlation
mechanism and none of the values (CLAUDE.md §11).

**2. Temporal stitching.** Observed-time is reconciled against valid-time on
the bitemporal T axis. Where a source cannot say when an event occurred,
valid-time opens at ingestion — the earliest instant the fabric can honestly
assert — rather than at an invented earlier one. That is a stated reconciliation
rule, not a silent default (D-IMPL-38): the fabric never claims to have known
something before it did, because a historical read that leaked future
information would poison replay.

**3. Policy binding.** The in-force Control Plane policy-bundle version is
stamped onto every claim *as it is written*. The fabric does not resolve
entities first and ask who can see them afterwards (INV-CH7-03) — P travels
with the subgraph.

The worker types its write handle as the :class:`ccf.graph.protocols.GraphWriter`
Protocol, never as a concrete backend class: L2 is substrate-neutral, and the
one place a concrete writer is named is the composition root (:mod:`ccf.boot`).

Algorithmic module (CINV-03) — every stage here is algorithmic; the semantic
extraction stages that may reach an ``LLMClientProtocol`` (D-IMPL-09) arrive
with the Pattern 5 pipeline and will live in their own, untagged modules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph.protocols import GraphWriter, UpsertResult
from ccf.peering.admission import AdmittedProduct
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

__ccf_mode__ = "algorithmic"

__all__ = [
    "AssemblyWorker",
    "EntityResolutionRule",
    "EntityResolutionSpec",
    "EntityResolutionStrategy",
    "FederatedIngestSpec",
    "IngestResult",
    "RelationshipResolutionRule",
    "ResolvedEntity",
    "SpecDrivenEntityResolution",
]


class EntityResolutionRule(CCFContract):
    """One user-declared correlation rule from source vocabulary to an E node.

    Attributes:
        match_key: Payload key whose presence selects this rule. Presence, not
            value: a rule that switched on a *value* would be the SDK holding
            a domain vocabulary.
        entity_class: Class within the user's ontology; also the URI scheme.
        identity_keys: Payload keys whose values identify the entity. Their
            canonical hash becomes the URI's identity component, so the URI is
            stable across source-system change (INV-CH7-18).
        attribute_keys: Payload keys carried onto the claim as attributes.
    """

    match_key: str
    entity_class: str
    identity_keys: tuple[str, ...]
    attribute_keys: tuple[str, ...] = ()


class RelationshipResolutionRule(CCFContract):
    """One user-declared rule producing a typed edge between resolved entities.

    Emits an edge whenever a single envelope resolves an entity of
    ``subject_entity_class`` and one of ``object_entity_class`` — co-occurrence
    in one source event is the evidence. Relationship types are first-class and
    user-declared (INV-CH7-20).
    """

    relationship_type: str
    subject_entity_class: str
    object_entity_class: str


class EntityResolutionSpec(CCFContract):
    """The full resolution vocabulary for a deployment.

    A Control Plane artifact, versioned like any other: changing how sources
    map onto the ontology changes what the graph means, so it needs the same
    audit lineage as a policy bundle.
    """

    entity_rules: tuple[EntityResolutionRule, ...]
    relationship_rules: tuple[RelationshipResolutionRule, ...] = ()


class FederatedIngestSpec(CCFContract):
    """How one deployment reads an admitted federated product into L1 envelopes.

    A user-declared Control Plane artifact, on the
    :class:`EntityResolutionSpec` precedent and for the same reason: which
    member of a product's payload carries the records a peer is asserting, and
    what logical source the federation edge is known by, are the deployment's
    vocabulary. The SDK ships the derivation mechanism and none of the values
    (CLAUDE.md §11, CINV-01) — there is no default key name here, because a
    default would be the SDK guessing at a peer's payload shape.

    Attributes:
        source_system_id: Logical identity of the federation edge, recorded on
            every derived envelope's lineage. Identity, never location
            (INV-CH8-01).
        payload_records_key: The payload member holding the sequence of records
            the peer asserts. Each record becomes one envelope's opaque
            ``raw_payload``, unread by this module — L1's non-interpretation
            survives the federated route exactly as it does the CDC one.
        record_key_aliases: Peer record key → this deployment's key, for the
            keys the deployment chooses to rename. A peer's payload speaks the
            peer's vocabulary and a consumer's resolution spec speaks the
            consumer's; where they differ, the consumer says so here rather
            than the SDK guessing a correspondence. Keys not named are carried
            through unchanged, and renaming is a relabel only — no value is
            read.
    """

    source_system_id: str
    payload_records_key: str
    record_key_aliases: Mapping[str, str] = Field(default_factory=dict)


class ResolvedEntity(CCFContract):
    """An entity a strategy recognized in one envelope, before persistence."""

    entity_uri: str
    entity_class: str
    attributes: dict[str, str]


@runtime_checkable
class EntityResolutionStrategy(Protocol):
    """The pluggable correlation seam (D-IMPL-35).

    The SDK ships :class:`SpecDrivenEntityResolution`; probabilistic matching,
    precedence rules, and survivorship policies are deployment plugins.
    """

    def resolve(self, *, envelope: SignalEnvelope) -> tuple[ResolvedEntity, ...]:
        """Return the entities this envelope asserts, in declaration order."""
        ...


class SpecDrivenEntityResolution:
    """Deterministic attribute-correlation strategy over a declared spec.

    URIs take the INV-CH7-18 form ``<entity-class>://<identity-hash>``, where
    the hash is over the canonical rendering of the rule's identity values. Two
    source systems naming the same counterparty by the same identifier
    therefore converge on one node without either system knowing about the
    other — and the URI survives a source migration, because it was never
    derived from where the record lived (INV-CH8-01).
    """

    def __init__(self, *, spec: EntityResolutionSpec) -> None:
        self._spec = spec

    @property
    def spec(self) -> EntityResolutionSpec:
        return self._spec

    def resolve(self, *, envelope: SignalEnvelope) -> tuple[ResolvedEntity, ...]:
        """Return the entities this envelope asserts, in declaration order."""
        resolved: list[ResolvedEntity] = []
        payload = envelope.raw_payload
        for rule in self._spec.entity_rules:
            if rule.match_key not in payload:
                continue
            missing = [key for key in rule.identity_keys if key not in payload]
            if missing:
                raise ValueError(
                    f"envelope {envelope.envelope_id!r} matched rule for "
                    f"{rule.entity_class!r} but lacks identity keys {missing}; "
                    "the fabric refuses to mint a URI from partial identity"
                )
            identity = {key: str(payload[key]) for key in rule.identity_keys}
            resolved.append(
                ResolvedEntity(
                    entity_uri=f"{rule.entity_class}://{content_hash(identity)}",
                    entity_class=rule.entity_class,
                    attributes={
                        key: str(payload[key])
                        for key in rule.attribute_keys
                        if key in payload
                    },
                )
            )
        return tuple(resolved)


class IngestResult(CCFContract):
    """What one envelope became.

    Reported rather than swallowed so callers, tests, and the eventual replay
    record can see that an envelope produced exactly this much graph state.
    """

    envelope_id: str
    tenant_id: str
    policy_bundle_version: str
    entities: tuple[UpsertResult, ...] = ()
    relationships: tuple[UpsertResult, ...] = ()


class AssemblyWorker:
    """L2 — the sole holder of a ``GraphWriter`` in a running fabric.

    Whitepaper §7.1/§7.3; DESIGN.md §2A.3, §2A.5.4. Constructed only by the
    composition root (:mod:`ccf.boot`); constructing one anywhere else requires
    a writer, and a writer requires a boot token nothing else can mint.

    Args:
        writer: The single graph write handle.
        resolution: Entity-resolution strategy (D-IMPL-35 seam).
        registry: Control Plane the policy bundle is resolved from.
        policy_bundle_key: Control Plane key of the bundle in force.
        policy_bundle_version: Pinned version. Pinned, never "latest": a fabric
            whose policy binding could drift between two writes would produce
            claims nobody can replay.

    Raises:
        ccf.controlplane.registry.ControlPlaneMissing: the pinned bundle is not
            registered. Surfaced at construction — that is, at boot — because a
            fabric that cannot bind policy should not start rather than fail on
            its first write.
    """

    def __init__(
        self,
        *,
        writer: GraphWriter,
        resolution: EntityResolutionStrategy,
        registry: ControlPlaneProtocol,
        policy_bundle_key: str,
        policy_bundle_version: str,
    ) -> None:
        self._writer = writer
        self._resolution = resolution
        self._registry = registry
        self._policy_bundle_key = policy_bundle_key
        # Resolving here both validates the pin and writes the binding to the
        # Control Plane audit log once per fabric, rather than once per write.
        registry.resolve(policy_bundle_key, policy_bundle_version)
        self._policy_bundle_version = policy_bundle_version

    @property
    def policy_bundle_version(self) -> str:
        """The Control Plane policy-bundle version stamped onto every claim."""
        return self._policy_bundle_version

    @property
    def policy_bundle_key(self) -> str:
        return self._policy_bundle_key

    def admit_entity_claim(
        self, *, tenant_id: str, claim: EntityClaim
    ) -> UpsertResult:
        """Write an already-resolved entity claim through L2 (the admission path).

        DESIGN.md §2A.5.4 step 5: a claim that did not originate in this
        fabric's own L1 — a Peering admission, a replayed snapshot — still enters
        L3 *through L2*, never by a direct write. Policy is bound here, on the
        way in, exactly as it is for locally-assembled state.
        """
        return self._writer.upsert_entity(
            tenant_id=tenant_id,
            claim=claim,
            policy_bundle_version=self._policy_bundle_version,
        )

    def admit_relationship_claim(
        self, *, tenant_id: str, claim: RelationshipClaim
    ) -> UpsertResult:
        """Write an already-resolved relationship claim through L2."""
        return self._writer.upsert_relationship(
            tenant_id=tenant_id,
            claim=claim,
            policy_bundle_version=self._policy_bundle_version,
        )

    @staticmethod
    def _stitch(envelope: SignalEnvelope) -> tuple[datetime, datetime]:
        """Reconcile observed-time against valid-time (INV-CH7-03, INV-CH7-14).

        Returns ``(observed_at, valid_from)``. ``observed_at`` is always
        ingestion: it records when *the fabric* learned the claim, which is a
        fact the fabric always knows. ``valid_from`` is the source's
        ``observed_time`` when the source can say, and ingestion when it
        cannot — see the module docstring for why that is a rule rather than a
        default.
        """
        observed_at = envelope.ingestion_timestamp
        valid_from = envelope.observed_time or envelope.ingestion_timestamp
        return observed_at, valid_from

    def ingest(self, envelope: SignalEnvelope) -> IngestResult:
        """Run the full L1→L3 write path for one signal envelope.

        DESIGN.md §2A.5.4 steps 3–4: resolve, stitch, bind policy, persist. The
        envelope's payload is interpreted here and nowhere earlier — L1's
        non-interpretation is what makes this the single point where source
        vocabulary becomes graph state.
        """
        observed_at, valid_from = self._stitch(envelope)
        provenance = frozenset(
            {
                LineageEntry(
                    source=envelope.source,
                    envelope_id=envelope.envelope_id,
                    observed_at=observed_at,
                )
            }
        )
        resolved = self._resolution.resolve(envelope=envelope)

        entity_results = tuple(
            self.admit_entity_claim(
                tenant_id=envelope.tenant_id,
                claim=EntityClaim(
                    tenant_id=envelope.tenant_id,
                    entity_uri=item.entity_uri,
                    entity_class=item.entity_class,
                    attributes=item.attributes,
                    observed_at=observed_at,
                    valid_from=valid_from,
                    lineage=provenance,
                ),
            )
            for item in resolved
        )

        by_class: dict[str, list[ResolvedEntity]] = {}
        for item in resolved:
            by_class.setdefault(item.entity_class, []).append(item)

        relationship_results: list[UpsertResult] = []
        for rule in self._relationship_rules():
            for subject in by_class.get(rule.subject_entity_class, ()):
                for obj in by_class.get(rule.object_entity_class, ()):
                    relationship_results.append(
                        self.admit_relationship_claim(
                            tenant_id=envelope.tenant_id,
                            claim=RelationshipClaim(
                                tenant_id=envelope.tenant_id,
                                relationship_type=rule.relationship_type,
                                subject_uri=subject.entity_uri,
                                object_uri=obj.entity_uri,
                                attributes={},
                                observed_at=observed_at,
                                valid_from=valid_from,
                                lineage=provenance,
                            ),
                        )
                    )

        return IngestResult(
            envelope_id=envelope.envelope_id,
            tenant_id=envelope.tenant_id,
            policy_bundle_version=self._policy_bundle_version,
            entities=entity_results,
            relationships=tuple(relationship_results),
        )

    def ingest_admitted(
        self,
        admitted: AdmittedProduct,
        *,
        spec: FederatedIngestSpec,
        ingested_at: datetime,
    ) -> tuple[IngestResult, ...]:
        """Run the federated write path for one **admitted** Peering product.

        L2's second declared entry point (Dave, 2026-07-27), added so that the
        admission commitment of CLAUDE.md §7.2 — *an inbound Context Product
        is not admissible to L3 until the consuming Control Plane validates its
        Policy bindings* — is carried by the type system rather than by caller
        discipline. The parameter's type is
        :class:`~ccf.peering.admission.AdmittedProduct`, which is constructible
        only inside
        :meth:`~ccf.peering.admission.PeeringAdmissionGate.admit`, so offering
        an unadmitted :class:`~ccf.peering.protocol.InboundProduct` here does
        not typecheck and does not run. That is what §10's "architectural, not
        advisory" asks of this boundary.

        L2 reaches the **category** here, not its first instance
        (``D-IMPL-59``): the import is ``ccf.peering``, so a second Peering
        transport needs no change to this method, and a Peering that tried to
        conclude its own admission would have nothing to hand in (part 4).

        :meth:`ingest` is deliberately left alone. It takes a
        :class:`~ccf.signal.envelope.SignalEnvelope` and serves *every* L1
        source — CDC capture and MCP ingress included — so binding
        ``AdmittedProduct`` onto it would have broken two ingress paths to
        constrain a third. The federated path gets its own door instead.

        Admission is still not a write, and this method does not shorten the
        path: it derives envelopes from the declared spec and drives them
        through :meth:`ingest`, so the federated product meets the same entity
        resolution, temporal stitching and policy binding as locally captured
        signal. Nothing here reads the records — they are carried onto
        ``raw_payload`` verbatim.

        Args:
            admitted: The gate's success value. Holding one is the evidence
                that all six admission checks ran.
            spec: The deployment's federation-ingest vocabulary.
            ingested_at: When this fabric received the product. Supplied by the
                caller for the same reason the gate takes ``now``: a write path
                that read a clock would not replay.

        Returns:
            One :class:`IngestResult` per derived envelope, in payload order.

        Raises:
            TypeError: the payload member named by
                ``spec.payload_records_key`` is absent, is not a sequence of
                records, or holds a non-mapping record. Raised rather than
                refused: an admitted product whose shape the deployment's own
                spec cannot read is a misconfiguration on this side of the
                boundary, not a badly behaved peer, and the two must not be
                reported the same way.
        """
        product = admitted.product
        records = product.payload.get(spec.payload_records_key)
        if isinstance(records, (str, bytes)) or not isinstance(
            records, Sequence
        ):
            raise TypeError(
                f"admitted product {product.schema_name!r} carries no record"
                f" sequence at payload key {spec.payload_records_key!r}; the"
                " deployment's FederatedIngestSpec does not describe this"
                " product's shape"
            )
        address = content_hash(product)
        source = SourceIdentity(system_id=spec.source_system_id)
        results: list[IngestResult] = []
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                raise TypeError(
                    f"record {index} at payload key"
                    f" {spec.payload_records_key!r} is"
                    f" {type(record).__name__}, not a mapping; L1 carries"
                    " source records opaquely and has nothing else to carry"
                )
            relabelled: dict[str, object] = {}
            for key, value in record.items():
                local = spec.record_key_aliases.get(key, key)
                if local in relabelled:
                    raise TypeError(
                        f"record {index} maps two keys onto {local!r} under"
                        " this deployment's record_key_aliases; a relabelling"
                        " that collides would silently drop one of the peer's"
                        " assertions"
                    )
                relabelled[local] = value
            results.append(
                self.ingest(
                    SignalEnvelope(
                        tenant_id=product.tenant_id,
                        envelope_id=f"{address}/{index}",
                        source=source,
                        ingestion_timestamp=ingested_at,
                        observed_time=product.temporal_boundary,
                        raw_payload=relabelled,
                    )
                )
            )
        return tuple(results)

    def _relationship_rules(self) -> tuple[RelationshipResolutionRule, ...]:
        """Edge rules from the strategy, when it exposes a spec.

        A strategy is free not to be spec-driven — a probabilistic matcher
        would not be — in which case it emits entities only and edge derivation
        is that plugin's concern.
        """
        spec = getattr(self._resolution, "spec", None)
        if isinstance(spec, EntityResolutionSpec):
            return spec.relationship_rules
        return ()
