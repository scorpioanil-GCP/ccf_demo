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

import numbers
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Final, Protocol, runtime_checkable

from pydantic import Field, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, content_hash
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.controlplane.artifact_base import VersionedArtifact
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.graph.protocols import GraphWriter, UpsertResult
from ccf.peering.admission import AdmittedProduct, verify_admission_provenance
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

__ccf_mode__ = "algorithmic"

__all__ = [
    "AssemblyWorker",
    "EntityResolutionRule",
    "EntityResolutionSpec",
    "EntityResolutionStrategy",
    "FederatedIngestSpec",
    "IdentityRefused",
    "IngestResult",
    "NO_RESOLVING_RULE",
    "RelationshipResolutionRule",
    "ResolvedEntity",
    "SpecDrivenEntityResolution",
]

#: The ``resolved_by`` a :class:`ResolvedEntity` carries when no entity rule
#: claims it — the value a custom :class:`EntityResolutionStrategy` leaves in
#: place when it does not say which rule produced an entity. An entity under
#: this sentinel is not selectable by ``subject_rule`` / ``object_rule``: an
#: endpoint no rule claims cannot be chosen by rule (``24.5-L-21``).
NO_RESOLVING_RULE = "no-resolving-rule"


class EntityResolutionRule(CCFContract):
    """One user-declared correlation rule from source vocabulary to an E node.

    Attributes:
        match_key: Payload key whose presence selects this rule. Presence, not
            value: a rule that switched on a *value* would be the SDK holding
            a domain vocabulary.
        entity_class: Class within the user's ontology; also the URI scheme.
        identity_keys: The entity's DECLARED identity keys. Their canonical
            hash becomes the URI's identity component, so the URI is stable
            across source-system change (INV-CH7-18). Each is read from the
            payload field of the same name unless ``identity_sources`` names a
            different field to read it from.
        attribute_keys: Payload keys carried onto the claim as attributes.
        identity_sources: Declared identity key -> the PAYLOAD FIELD that
            supplies its value, for rules whose source names the value
            positionally (``CP04C-F-01``, `D-IMPL-316`). A position is not an
            identity: ``parent_uri`` and ``child_uri`` both carry *an entity's
            uri*, and a rule that reads either into the declared key
            ``entity_uri`` mints the same URI for the same value.

            **This field changes WHERE an identity value is READ FROM; it does
            not change WHAT CONSTITUTES IDENTITY** (`D-IMPL-316`, Dave). That
            sentence is the whole boundary of the repair, and it is why
            existing URI and hash behavior is stable: identity is still the
            declared key beside its value, hashed by the one global model, so
            a rule that names no source reads the field it always read and
            mints the URI it always minted. Only keys
            listed in ``identity_keys`` may be remapped, and **what is hashed
            is still the declared key beside its value** — the global identity
            model is untouched, and only where the value is read from moves.
            Hash-transparent when empty (``D-IMPL-243``): every rule written
            before this field keeps the canonical form and the URIs it
            already had.

    A ``*_ref: True`` presence-flag ``match_key`` (the SDK's own acquisition
    idiom) cannot also be an identity key: a boolean identity value is refused
    at the mint (D-IMPL-357 B1).
    """

    match_key: str
    entity_class: str
    identity_keys: tuple[str, ...]
    attribute_keys: tuple[str, ...] = ()
    identity_sources: Mapping[str, str] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @model_validator(mode="after")
    def _sources_remap_declared_identity_keys(self) -> "EntityResolutionRule":
        """A remapped key nobody declared as identity would name nothing.

        Refused rather than ignored: a typo in this mapping would otherwise
        leave the rule reading the payload field of the same name as the
        declared key, mint a different URI, and report nothing at all — the
        silent wrong-identity failure this field exists to remove.
        """
        undeclared = sorted(set(self.identity_sources) - set(self.identity_keys))
        if undeclared:
            raise ValueError(
                f"identity_sources remaps {undeclared}, which"
                f" {self.entity_class!r} does not declare as identity keys"
                f" ({sorted(self.identity_keys)}). A source field can only"
                " supply a key the rule identifies the entity by"
            )
        return self


class RelationshipResolutionRule(CCFContract):
    """One user-declared rule producing a typed edge between resolved entities.

    Relationship types are first-class and user-declared (INV-CH7-20). A rule
    mints in one of three modes, and the envelope decides which rules fire
    (``24.5-L-21``, closing ``24.4-D-35``):

    **Co-occurrence** (no selector fields — every rule declared before Phase
    24.5, kept unchanged for every existing deployment). The rule fires when a
    single envelope resolves an entity of ``subject_entity_class`` and one of
    ``object_entity_class``: co-occurrence in one source event is the evidence,
    and every subject × object pair across the two classes is minted.

    **Predicate selection** (``predicate_key``). The rule fires only when the
    envelope's payload carries ``predicate_key`` and its value equals this
    rule's own ``relationship_type``. A payload therefore selects among the
    rules a deployment declared; it cannot name a type no rule declares,
    because the comparison is against the rule, never a free value. Endpoints
    are still chosen by class unless the endpoint selectors below are set.

    **Endpoint selection** (``subject_rule`` and ``object_rule``, together).
    Each names the ``match_key`` of the *entity* rule that resolved the
    endpoint, so the subject is the entity one declared rule produced and the
    object the entity another produced — chosen by the rule that made them,
    not by their class. This is what lets one envelope carrying
    ``{parent, child, predicate}`` mint a single edge between two entities of
    the same class, which co-occurrence by class could never express. The two
    fields travel together or not at all; ``predicate_key`` may stand alone or
    beside them.

    In **every** mode a pair whose subject and object are the same URI is never
    minted: a self-loop from one envelope is co-occurrence noise, never
    evidence (the cp-04 one-envelope case minted six of them). The entity
    classes remain required in every mode — under endpoint selection they
    describe the endpoints the named entity rules produce.

    Attributes:
        relationship_type: The edge type minted. Under predicate selection it
            is also the value the payload must carry to select this rule.
        subject_entity_class: Class of the subject endpoint (URI scheme).
        object_entity_class: Class of the object endpoint (URI scheme).
        predicate_key: Payload key whose value must equal
            ``relationship_type`` for this rule to fire. ``None`` keeps
            co-occurrence semantics. Hash-transparent at ``None``
            (``D-IMPL-243``): a co-occurrence rule is every pre-phase rule,
            so the field is omitted from the canonical form at that value.
        subject_rule: ``match_key`` of the entity rule that resolved the
            subject. ``None`` chooses subjects by ``subject_entity_class``.
            Hash-transparent at ``None`` (``D-IMPL-243``), as ``predicate_key``.
        object_rule: ``match_key`` of the entity rule that resolved the
            object. ``None`` chooses objects by ``object_entity_class``.
            Hash-transparent at ``None`` (``D-IMPL-243``), as ``predicate_key``.
    """

    relationship_type: str
    subject_entity_class: str
    object_entity_class: str
    predicate_key: str | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})
    subject_rule: str | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})
    object_rule: str | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})

    @model_validator(mode="after")
    def _endpoint_selectors_are_whole(self) -> RelationshipResolutionRule:
        if (self.subject_rule is None) != (self.object_rule is None):
            raise ValueError(
                "endpoint selectors carry both of their fields or neither;"
                " a rule naming the rule for one endpoint and the class for"
                " the other is not a legal value (`24.5-L-21`)"
            )
        return self


class EntityResolutionSpec(VersionedArtifact):
    """The full resolution vocabulary for a deployment.

    A Control Plane artifact, versioned like any other: changing how sources
    map onto the ontology changes what the graph means, so it needs the same
    audit lineage as a policy bundle. That sentence is now literally true —
    the class inherits
    :class:`~ccf.controlplane.artifact_base.VersionedArtifact` and is reachable
    through :func:`~ccf.controlplane.artifacts.parse_artifact` as the
    ``ccf.resolution-spec`` class (D-IMPL-77).

    Inherited from the base rather than wrapped beside it, because a wrapper
    would hand :func:`ccf.boot.boot` a wrapper where it expects a spec, and
    ``boot()``'s signature is the one contract D-05 preserves. The consequence
    is accepted deliberately: ``semver`` changes the spec's content hash, so
    every ``resolution_spec_version`` pin minted after this change differs from
    one minted before it.

    ``semver`` has no default (see the base). A spec that never states its lane
    cannot be registered — and a default lane would be a version nobody chose,
    which is exactly the value the registry's bump check would then compare
    against.
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
    """An entity a strategy recognized in one envelope, before persistence.

    Attributes:
        entity_uri: The canonical, tenant-scoped URI (INV-CH7-18).
        entity_class: Class within the user's ontology; also the URI scheme.
        attributes: Payload values carried onto the claim.
        resolved_by: ``match_key`` of the entity rule that produced this
            entity, filled by :class:`SpecDrivenEntityResolution`. A custom
            :class:`EntityResolutionStrategy` that does not fill it leaves
            :data:`NO_RESOLVING_RULE`, and a relationship rule selecting its
            endpoints by rule then never chooses this entity — an endpoint no
            rule claims is not selectable (``24.5-L-21``). Hash-transparent
            at :data:`NO_RESOLVING_RULE` under ``D-IMPL-243`` amendment 2:
            a resolved entity is never content-hashed, so the mark is inert
            today and reads the sentinel as absent if the model is ever
            hashed.
    """

    entity_uri: str
    entity_class: str
    attributes: dict[str, str]
    resolved_by: str = Field(
        default=NO_RESOLVING_RULE, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


@runtime_checkable
class EntityResolutionStrategy(Protocol):
    """The pluggable correlation seam (D-IMPL-35).

    The SDK ships :class:`SpecDrivenEntityResolution`; probabilistic matching,
    precedence rules, and survivorship policies are deployment plugins.
    """

    def resolve(self, *, envelope: SignalEnvelope) -> tuple[ResolvedEntity, ...]:
        """Return the entities this envelope asserts, in declaration order."""
        ...


class IdentityRefused(ValueError):
    """An identity component's value cannot name an entity (D-IMPL-357 B1; SEC-007).

    Raised, never swallowed, at the ONE mint site: a null, blank, boolean,
    float or non-scalar value would render through ``str()`` into a string
    every such record shares, minting one phantom node and, through the
    relationship rules, false edges onto it. The reason is named so an
    operator can tell which it was. Presence is checked before this
    (partial identity), admissibility here.
    """

    def __init__(self, *, envelope_id: str, entity_class: str, key: str, field: str, reason: str) -> None:
        self.envelope_id, self.entity_class, self.key, self.field, self.reason = (
            envelope_id, entity_class, key, field, reason
        )
        super().__init__(
            f"envelope {envelope_id!r} presents an inadmissible identity value"
            f" ({reason}) for {entity_class!r} key {key!r} read from payload"
            f" field {field!r}; the fabric refuses to mint a URI from a value"
            " that names no entity (D-IMPL-357 B1)"
        )


#: Unicode general categories that carry no visible identity (D-IMPL-357 item 1,
#: Dave's ruling of 2026-09-27, amending B1 for IDENTITY VALUES ONLY).
#:
#: ``str.strip`` removes Python's whitespace set, which does NOT contain U+200B
#: (zero-width space), U+FEFF (BOM) or NUL. An identity holding only those
#: passed the blank check and minted a node; three distinct entities carrying
#: three different invisible-only identities were measured collapsing onto
#: shared nodes with two real relationships between them.
#:
#: ``Cc`` control, ``Cf`` format, ``Zs``/``Zl``/``Zp`` separators. Deliberately
#: NOT ``Cn`` (unassigned) or ``Co`` (private use): an unassigned or
#: private-use codepoint is an identity a deployment may legitimately mint,
#: and refusing it would be a widening Dave did not rule.
_INVISIBLE_IDENTITY_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"Cc", "Cf", "Zs", "Zl", "Zp"}
)


def _is_invisible_identity(value: str) -> bool:
    """Is every character of ``value`` one that carries no visible identity?

    Answers True for the empty string, for Python-whitespace-only values (the
    B1 set this amends), and for values built only from format, control or
    Unicode separator characters. Answers False as soon as one visible
    character is present, so ``"a\u200bb"`` is a real identity that happens to
    carry an invisible character — refusing THAT would be a widening into
    ordinary attribute semantics, which Dave's ruling excludes.
    """
    return all(
        unicodedata.category(character) in _INVISIBLE_IDENTITY_CATEGORIES
        for character in value
    )


def _identity_text(value: object) -> tuple[str | None, str]:
    """The text bare ``str()`` produced for an admissible identity value, or the refusal reason.

    ``numbers.Integral`` and a finite ``Decimal`` render exactly as ``str()``
    rendered them before D-IMPL-357, so every URI minted from a numeric
    identifier is byte-identical (D-IMPL-316: the global hashing model is
    untouched); a ``str`` is taken as is — untrimmed, unfolded. This is
    byte-identity with the historic coercion, not literally "positional": a
    ``Decimal``'s exponent form is not repositioned, e.g. ``Decimal('1E+2')``
    still renders ``'1E+2'`` and ``Decimal('0.0000001')`` still renders
    ``'1E-7'`` — what B2 requires is that the rendering does not move, not
    that it takes one particular shape.

    ``bool`` is checked before ``numbers.Integral`` because ``bool`` is
    registered under it. ``numbers.Integral`` — not the narrower ``int`` — is
    the check: a pandas-backed L1 adapter (``DataFrame.itertuples``) yields
    ``numpy.int64``, which is ``Integral`` without subclassing ``int``, and
    ruling B2 exists so a numeric identity keeps minting the URI it always
    minted, not so it stops minting because a numeric library boxed it
    differently. The value is coerced through ``int()`` rather than rendered
    by its own ``__str__``, so the canonical decimal form is what is hashed
    regardless of the ``Integral`` subtype's own string form. ``float`` is
    refused here because ``str()`` ran before the canonical form's own float
    refusal and would have minted ``"1.5"``. A non-finite ``Decimal`` (NaN,
    ±Infinity) gets its own reason, ``non-finite``, rather than being folded
    into ``non-scalar`` — it IS a scalar, just not one that names an entity.

    The ``str`` blank check is :func:`_is_invisible_identity` (D-IMPL-357 item
    1, Dave's ruling of 2026-09-27, amending B1 for IDENTITY VALUES ONLY) —
    not the original ``str.strip`` check it replaces, which only catches
    Python's whitespace set and missed U+200B (zero-width space), U+FEFF
    (BOM) and NUL.

    **It is called on ``str.__str__(value)``, and that spelling is the whole
    of the hardening** (R1 fix round 1, both review seats). The original
    called ``str.strip`` on the TYPE rather than ``value.strip()`` on the
    instance precisely because a type-bound call cannot be shadowed; a
    ``str`` subclass overriding ``strip`` could not pass a blank value
    through it. Plain ``str(value)`` does NOT carry that property across:
    it is instance-dispatched and invokes ``type(value).__str__``, so a
    ``str`` subclass returning a visible string from ``__str__`` was
    measured minting a node for an EMPTY identity — three distinct classes
    collapsing onto one URI — while the empty ``str`` itself was correctly
    refused. The carrier is ordinary code, not an attack: a ``str``-mixin
    ``Enum`` whose "unknown" member is the empty string renders as
    ``"Tag.UNKNOWN"`` under ``str()`` and as ``""`` under
    ``str.__str__``. ``str.__str__`` is the type-bound analogue of the
    ``str.strip`` idiom and resists ``__str__``, ``__iter__`` and both
    together.

    **The text RETURNED is that same plain-``str`` reading, never the
    subclass instance**, so no later rendering can re-dispatch ``__str__``
    on a value this function already judged, and the declared ``str | None``
    return type is honored at runtime for a ``str``-mixin ``Enum`` member
    (which is not a plain ``str``). This is byte-identical for the hash —
    ``content_hash`` canonicalizes a ``str`` subclass by its content already,
    measured equal for every subclass shape tried — so D-IMPL-316/B2's
    minted-URI identity is untouched.

    **The reason stays ``"empty"``**: the value IS empty
    once invisible-only characters are discounted, and Dave's item-3 ruling
    is not to change the reason vocabulary. An identity carrying an invisible
    character BESIDE a visible one (``"a\u200bb"``) is still a real identity —
    refusing that would be a widening into ordinary attribute semantics that
    Dave's ruling excludes.
    """
    if value is None:
        return None, "null"
    if isinstance(value, bool):
        return None, "bool"
    if isinstance(value, numbers.Integral):
        return str(int(value)), ""
    if isinstance(value, float):
        return None, "float"
    if isinstance(value, str):
        # `str.__str__`, never `str(value)`: type-bound, so a subclass's own
        # `__str__` cannot decide this. Both the CHECK and the RETURNED text
        # read the content (R1 fix round 1).
        text = str.__str__(value)
        return (None, "empty") if _is_invisible_identity(text) else (text, "")
    if isinstance(value, Decimal):
        return (str(value), "") if value.is_finite() else (None, "non-finite")
    return None, "non-scalar"


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
            # Where each declared identity key is READ FROM. The default is
            # the field of the same name, which is every rule written before
            # `identity_sources` existed.
            source_of = {key: rule.identity_sources.get(key, key) for key in rule.identity_keys}
            missing = [
                key for key, field in source_of.items() if field not in payload
            ]
            if missing:
                raise ValueError(
                    f"envelope {envelope.envelope_id!r} matched rule for "
                    f"{rule.entity_class!r} but lacks identity keys {missing}"
                    f" (read from payload fields "
                    f"{sorted(source_of[key] for key in missing)}); "
                    "the fabric refuses to mint a URI from partial identity"
                )
            # THE DECLARED KEY IS WHAT IS HASHED, beside the value the source
            # field supplied. The payload field's name never enters the
            # identity, so one entity named `parent_uri` here and `child_uri`
            # there is ONE entity (`CP04C-F-01`).
            #
            # Presence was checked above; admissibility is checked here
            # (D-IMPL-357 B1, SEC-007) — a null, blank, boolean, float or
            # non-scalar value would otherwise render through bare `str()`
            # into a string every such record shares, minting one phantom
            # node and, through the relationship rules, false edges onto it.
            identity: dict[str, str] = {}
            for key, field in source_of.items():
                text, reason = _identity_text(payload[field])
                if text is None:
                    raise IdentityRefused(
                        envelope_id=envelope.envelope_id, entity_class=rule.entity_class,
                        key=key, field=field, reason=reason,
                    )
                identity[key] = text
            resolved.append(
                ResolvedEntity(
                    entity_uri=f"{rule.entity_class}://{content_hash(identity)}",
                    entity_class=rule.entity_class,
                    # A null attribute is OMITTED, not stringified: bare
                    # `str(None)` would store the literal text "None" on an
                    # otherwise correctly identified node, and PolicyFilter
                    # (and any other attribute-keyed consumer) reads a stored
                    # string as an answered value, not as "unknown"
                    # (D-IMPL-357 B4).
                    #
                    # NO COUNT LIVES HERE. B4 conditioned this change on a
                    # measurement of the population it moves, and that
                    # population belongs where it can go stale visibly:
                    # tools/measure_null_attributes.py prints it with its
                    # per-source denominators, and the decision entry dates the
                    # run. An earlier revision of this comment asserted a
                    # tree-wide count in this spot; no gate checked it, and it
                    # was wrong on the day it was written — committed SQL seed
                    # rows carry nulls under declared attribute keys, in a
                    # fixture format that count's scan never opened.
                    attributes={
                        key: str(payload[key])
                        for key in rule.attribute_keys
                        if key in payload and payload[key] is not None
                    },
                    resolved_by=rule.match_key,
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
    def _stitch(envelope: SignalEnvelope) -> tuple[datetime, datetime | None]:
        """Reconcile observed-time against valid-time (INV-CH7-03, INV-CH7-14).

        Returns ``(observed_at, valid_from)``. ``observed_at`` is always
        ingestion: it records when *the fabric* learned the claim, which is a
        fact the fabric always knows.

        **``valid_from`` is the source's ``observed_time``, and stays ABSENT
        when the source cannot say** (``D-IMPL-332``). It used to fall back to
        ingestion, and that fallback is the defect this ruling removes:

            ``observed_at`` means *when the fabric learned the claim*.
            ``valid_from`` means *when the claim was true in the world*.

        Substituting the first for the second turns *"we learned it at 2 PM"*
        into *"it became true at 2 PM"* — a claim about the world that no
        source made, minted by an ingestion run. It also defeated
        ``D-IMPL-331`` from below: a λ_c row declaring
        ``decay_basis: valid-from`` would read that manufactured instant and
        report a perfectly fresh figure for an observation whose real age is
        unknown, which is exactly what declaring the basis was meant to stop.

        **Unknown stays unknown.** What an absent ``valid_from`` means to a
        validity-window read is defined at ``GQ-09``, not defaulted here.
        """
        observed_at = envelope.ingestion_timestamp
        valid_from = envelope.observed_time
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
        by_rule: dict[str, list[ResolvedEntity]] = {}
        for item in resolved:
            by_class.setdefault(item.entity_class, []).append(item)
            # An entity under the sentinel is claimed by no rule, so no rule
            # can select it; it is reachable by class only (24.5-L-21).
            if item.resolved_by != NO_RESOLVING_RULE:
                by_rule.setdefault(item.resolved_by, []).append(item)

        relationship_results: list[UpsertResult] = []
        for rule in self._relationship_rules():
            # Predicate selection: the envelope must name this rule's own
            # type under the declared key, or the rule does not fire. The
            # comparison is against the rule, so a payload cannot select a
            # type no rule declares (24.5-L-21).
            if (
                rule.predicate_key is not None
                and envelope.raw_payload.get(rule.predicate_key)
                != rule.relationship_type
            ):
                continue
            subjects: Sequence[ResolvedEntity]
            objects: Sequence[ResolvedEntity]
            if rule.subject_rule is not None and rule.object_rule is not None:
                # Endpoint selection: by the entity rule that produced each
                # endpoint, not by its class.
                subjects = by_rule.get(rule.subject_rule, ())
                objects = by_rule.get(rule.object_rule, ())
            else:
                subjects = by_class.get(rule.subject_entity_class, ())
                objects = by_class.get(rule.object_entity_class, ())
            for subject in subjects:
                for obj in objects:
                    if subject.entity_uri == obj.entity_uri:
                        # A self-loop from one envelope is co-occurrence
                        # noise, never evidence — skipped under every mode
                        # (24.5-L-21, 24.4-D-35).
                        continue
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
        not typecheck and does not run.

        **The sentence above used to end "…carried by the type system rather
        than by caller discipline", and that was measured false**
        (`D-IMPL-337`). The type system carries the STATIC half: a conforming
        caller cannot pass the wrong thing. It carries nothing at runtime — a
        subclass of `AdmittedProduct` that skips the guarded `__init__`
        satisfies both mypy and `isinstance` while no admission ran. What makes
        this boundary "architectural, not advisory" (§10) is the provenance
        check below, which the type annotation alone never provided.

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
        # `D-IMPL-337`. A governed boundary: L2's federated entry point, where
        # a bypass would put an unverified peered product into the graph
        # through the one writer (CLAUDE.md §10, D-IMPL-16).
        admitted = verify_admission_provenance(admitted)

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
