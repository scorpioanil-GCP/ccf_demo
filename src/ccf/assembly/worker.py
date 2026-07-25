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

from datetime import datetime
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph.protocols import GraphWriter, UpsertResult
from ccf.signal.envelope import SignalEnvelope

__ccf_mode__ = "algorithmic"

__all__ = [
    "AssemblyWorker",
    "EntityResolutionRule",
    "EntityResolutionSpec",
    "EntityResolutionStrategy",
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
        fabric's own L1 — an A2A admission, a replayed snapshot — still enters
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
