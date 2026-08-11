"""``ContextProductContract`` — the typed delivery contract (whitepaper §6.3).

Whitepaper §6.3 (the specification elements) and §7.6 (delivery); DESIGN.md
§2B.3, which maps the specification *elements* onto the Fig-CH07-13 typed base
*fields* and records the eight-versus-nine element drift under D-IMPL-30.

Nine elements, per D-IMPL-30 reading (a) — Assembly Mode included. They are
borne across two types, and which type bears which is itself ruled rather than
convenient. The mapping, stated once and asserted by
``tests/products/test_contract_elements.py`` so this table cannot drift from
the code that realizes it:

On :class:`ContextProductContract`, the delivered instance:

===========================================  ================================
Field                                        Specification element
===========================================  ================================
``schema_name``                              Schema
``schema_version``                           Semantic Versioning
``expires_at`` + ``ttl_anchor``              TTL
``lineage``                                  Lineage
``plan_id``                                  Π identity (binds product to plan)
``payload``                                  the class's declared payload
``debt``                                     D_c in force (§7.7, D-IMPL-100)
===========================================  ================================

On :class:`RegisteredProductClass`, the class-level governance a product is
assembled *under* rather than carries a copy of:

===========================================  ================================
Field                                        Specification element
===========================================  ================================
``assembly_mode``                            Assembly Mode (INV-CH7-55)
``accepted_policy_binding_modes``            Policy Binding
``freshness_sla``                            Freshness SLA
``discovery``                                Discovery
``addressability``                           Addressability
===========================================  ================================

**What the previous version of this table got wrong, named rather than quietly
fixed.** It asserted that Freshness SLA, Discovery and Addressability *lived*
on :class:`RegisteredProductClass` when only ``assembly_mode`` of the four
did; a repo-wide grep for ``freshness_sla`` in ``src/`` returned zero. Plan
``15.5-07`` landed the three fields, and
``tests/products/test_contract_elements.py`` now asserts this table against
``model_fields`` so the prose cannot drift from the types again.

The second correction concerns Policy Binding, which the previous table routed
through ``lineage.policy_bundle_versions``. **Both routes exist and they carry
different things.** That one carries the bundle versions actually bound into
the state a *given product* was assembled from — a per-product fact, and the
one that reaches the replay record. The element's **contract surface** — what
the class accepts, which is what governance means and what
:func:`ccf.products.gates.run_gates` compares against — is
``accepted_policy_binding_modes``. The element is keyed to the second above
because a nested field is not reachable from a top-level ``model_fields``
union, and because keying two elements to one field would collapse them.

**Freshness SLA is class-level by ruling, not by convenience** (D-IMPL-106,
option (b), Dave 2026-08-11). The whitepaper's two enumerations of "the same
seven fields" differ by exactly one element — the Fig-CH07-13 sidebar at
``docs/CCF_Whitepaper_1-2.md:2381`` names freshness SLA where the prose at
``:2381-2405`` names ``plan_id`` — and reading 2 was ruled: the sidebar names a
class-level **promise the product was assembled under**, so both enumerations
are consistent, nothing is missing, and ``plan_id`` keeps its place on the
vessel. It is also the only placement that moves no recorded content address.
Its *shape* is per-signal rather than scalar, following §6.3 at ``:1453``
(*"Freshness SLA varies by signal and by decision"*); D-IMPL-106 ruled the
placement and left the shape to this plan, stating that no scalar is ruled in
by silence.

**Discovery and Addressability land for real, not declaration-only.**
D-IMPL-98 ruled that the request surface is a typed request contract per
product class and that addressability and the request contract are the same
commitment — which makes ``15.5-CONTEXT.md``'s declaration-only permission
moot. What is here is the *class-level* half: the registry facts a product is
located by, and the address it answers at. The **argument** half — subject and
instant as typed request arguments rather than artifact literals — is that
ruling's own surface and is deliberately not modelled here.

**The payload is a declared schema, not an open dict** (D-IMPL-97 ruling 1).
A class pins its payload schema by ``(key, version)``, resolved at
registration, and :mod:`ccf.products.payload` holds the one comparison that
reads it. Under D-IMPL-102 that is limb 1 — *schema validity at registration*
— and **no fourth gate joins** :func:`ccf.products.gates.run_gates`; the
three shipped validation gates stay at three.

**Semver lanes are per product class** (INV-CH7-49): ``schema_version`` is a
field on the instance and is never compared across classes, so a bump on one
product never touches another.

**Context Debt rides the vessel, and that is what makes it reach a consumer**
(D-IMPL-100). D_c was computed by :mod:`ccf.halflife.debt` and then discarded:
it appeared on neither the product nor the replay record, so five of the six
axes of ``G(E, R, T, P, Π, L)`` reached the wire and the sixth — the one that
says how much to trust the other five — did not. §7.7 and
``docs/CCF_Whitepaper_1-2.md:2696`` are unambiguous that debt is *"a runtime
signal the agent must consume as a first-class decision input, not a log-line
to be read after the fact"*, so it is carried **here**, inside the delivered
bytes, rather than beside them.

**The three doors, and what a consumer at each receives.** Every shipped
delivery path serializes ``servable.product`` and **none** reads
``ServedProduct.replay_ref``, so a placement beside the vessel would have
reached an in-process caller and no wire consumer at all. Because debt is on
the vessel, all three carry it with **no code change at any door**:

=================================================  ==============  ===========
Door                                               Serializes      Carries D_c
=================================================  ==============  ===========
``ccf_runtime/mcp/egress.py:270``                  the vessel      yes
``ccf_runtime/http_api/routes/product.py:112``     the vessel      yes
``ccf_runtime/mcp/experience.py:632``              the vessel      yes
=================================================  ==============  ===========

No door is structurally unable to carry it, so nothing is carried forward as a
residual on that account. ``tests/invariants/test_replay_by_construction.py``
registers the claim as a CINV-04 check ranging over
``tests/invariants/test_mcp_role_separation.py``'s exhaustive door enumeration —
one enumeration, because this phase began by discovering that nobody had counted
the doors.

**The content address moves, and it moves reconstructibly.** ``debt`` is inside
the hashed body — :func:`~ccf.contracts.canonical.canonical_bytes` walks a model
field-by-field over ``type(value).model_fields`` — so every address recorded
before this field existed differs from the one the same product produces now.
That is authorized by D-IMPL-100 on one condition, which is structural rather
than procedural: the *record* carries the same assessment on dimension 5, and
:meth:`~ccf.replay.engine.ReplayEnvironment.rehydrate_product` reads it back, so
the engine's check at ``src/ccf/replay/engine.py:449-455`` passes on identical
bytes rather than on a re-measurement. Debt is **never** re-derived at replay:
it is computed from observations and a ``now`` neither the record nor the
projection re-derives, so a rehydrator that re-measured it would produce a
different decision wearing this one's identifier.

**One figure per product, not one per principal** (D-IMPL-105). Different
principals legitimately receive different products, assembled from what each may
consult — but debt is not one of the things that differs. A refused consultation
is simply not part of ``C_required`` for that principal, so its absence is not a
shortfall. Under the per-principal reading the completeness number would move
when a source was withheld, and a caller could then infer *what they are not
allowed to see* from the debt they were shown — an oracle over the entitlement
configuration, quieter than a refusal because nothing in the response says a
consultation was declined. There is no per-principal figure here to difference.

**MAX_TTL has no SDK default** (D-IMPL-39). It is required Control Plane
configuration per product class, and the absence of a registered value is a
failure at *class registration* — before any product of that class can exist —
rather than a surprise on the first serve. This module therefore holds no TTL
number, no freshness figure, and no threshold of any kind (CLAUDE.md §11,
CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from ccf.contracts.base import CCFContract
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.graph.protocols import LineageMode, PolicyBindingMode
from ccf.halflife.assessment import DebtAssessment

__ccf_mode__ = "algorithmic"

__all__ = [
    "NOT_ADDRESSABLE",
    "NOT_DISCOVERABLE",
    "NO_PAYLOAD_SCHEMA",
    "NO_VALIDITY_FLOORS",
    "UNMEASURED_FRESHNESS_SLA",
    "AssemblyMode",
    "ConstituentValidityFloors",
    "ContextProductContract",
    "FreshnessSLA",
    "MaxTTL",
    "ProductAddress",
    "ProductClassRegistrationError",
    "ProductDiscovery",
    "ProductLineage",
    "RegisteredProductClass",
    "TTLAnchor",
    "register_product_class",
]

#: Whitepaper §7.6 TTL granularity (D-IMPL-31): a product's expiry is anchored
#: either to the decision that requested it or to the freshness of the entities
#: it was assembled from. Which one is a per-class declaration.
TTLAnchor = Literal["from_decision", "from_entity_freshness"]

#: Whitepaper §7.6 assembly modes (INV-CH7-55, the ninth contract element per
#: D-IMPL-30). I.1 is Mode 1 throughout — no LLM participates anywhere in the
#: fabric core.
AssemblyMode = Literal["algorithmic", "llm_packaged", "swarm_assembled"]


class ProductClassRegistrationError(ValueError):
    """A product class cannot be registered as configured.

    Raised — never returned, never warned — because a class whose governance
    configuration is absent or malformed must not become servable. D-IMPL-39.
    """


class MaxTTL(CCFContract):
    """The per-class TTL ceiling, as a Control Plane artifact.

    A typed artifact rather than a bare integer so that registering the wrong
    thing under the MAX_TTL key is a detectable error rather than a plausible
    one, and so the ceiling gets its own content-addressed version — which is
    what lands in the policy-bindings replay dimension.

    ``seconds`` is declared with no default: a missing ceiling is a deployment
    error, not a number the SDK is entitled to choose (D-IMPL-38).
    """

    seconds: int


class FreshnessSLA(CCFContract):
    """§6.3 **Freshness SLA** — the per-signal currency expectation (D-IMPL-106).

    *"Freshness SLA specifies how current the underlying signals must be for
    the product to be valid at decision time. It is the expectation of
    currency; TTL is the bounded validity after currency is no longer
    guaranteed — sibling primitives, not duplicates"* is §6.3's own
    distinction (``docs/CCF_Whitepaper_1-2.md:1453``), and it is why this is
    not a second spelling of :class:`MaxTTL`.

    **Per signal, not a scalar.** The same passage: *"Freshness SLA varies by
    signal and by decision"*, and immediately before it: *"a product that
    mixed the two without surfacing the asymmetry would produce an unreliable
    agent input"*. A single number for a product assembled from an end-of-day
    filing and an intraday blotter entry is precisely the asymmetry §6.3 says
    a product must not hide. D-IMPL-106 ruled the *placement* and left the
    shape here, recording that no scalar was ruled in by silence.

    The mapping is keyed by the deployment's own signal-type identifiers and
    the SDK never interprets one — the opaque-identifier discipline
    :class:`~ccf.skills.catalog.SkillRequirements` already holds. This class
    therefore ships no signal name and no number (CLAUDE.md §11, CINV-01).

    Attributes:
        max_age_seconds_by_signal: Per signal type, the greatest age at which
            an observation of it still satisfies this class's currency
            expectation. An empty mapping is the positive statement
            :data:`UNMEASURED_FRESHNESS_SLA` documents, not a silence.
    """

    max_age_seconds_by_signal: Mapping[str, int]

    def __hash__(self) -> int:
        # The generated frozen-model hash cannot hash a mapping field; hash
        # the same values equality compares (the SkillArgumentSchema
        # precedent, and for the same reason — the value is carried inside
        # types that are compared as members of sets).
        return hash(
            (type(self), tuple(sorted(self.max_age_seconds_by_signal.items())))
        )


class ConstituentValidityFloors(CCFContract):
    """D-IMPL-31's declarable floors, whose breach refuses assembly.

    Ruled 2026-07-25 as part of the two-granularity TTL reading: *"Product
    classes may declare constituent-validity floors whose breach refuses
    assembly rather than emitting a product fresher-labeled than its stalest
    load-bearing constituent (the mixing-refusal rule, formally footed)."*
    The declaration is here; **the refusal that reads it is plan ``15.5-12``**,
    and nothing in the registration path consumes a floor, because a
    mixing-refusal enforced at wiring time would be a rule applied at the
    wrong moment — the mix does not exist until assembly.

    Distinct from :class:`FreshnessSLA` and not a restatement of it: the SLA
    is the currency the class *expects* of a signal, the floor is the
    remaining validity a constituent must still have for the product to be
    assemblable at all. One is an expectation, the other a refusal condition.

    Attributes:
        min_validity_seconds_by_signal: Per signal type, the least remaining
            validity a load-bearing constituent of that type must have.
            Deployment-declared identifiers, never interpreted here.
    """

    min_validity_seconds_by_signal: Mapping[str, int]

    def __hash__(self) -> int:
        return hash(
            (
                type(self),
                tuple(sorted(self.min_validity_seconds_by_signal.items())),
            )
        )


class ProductDiscovery(CCFContract):
    """§6.3 **Discovery** — the registry facts a class is located by.

    *"A registry exposes available products by intent, domain, and
    capability; agents resolve names to endpoints at runtime"*
    (``docs/CCF_Whitepaper_1-2.md:1463``). The three fields are that sentence,
    and the worked example is a registry entry *"with a capability manifest"*
    — a manifest of declared capability tokens, which is what
    ``capabilities`` is.

    Every value is a deployment-declared opaque identifier. The SDK matches
    them structurally and interprets none, so no intent vocabulary, domain
    taxonomy or capability list exists in this module (CLAUDE.md §11).

    Attributes:
        domain: The domain the class belongs to.
        intents: The decision intents the class is registered as serving.
        capabilities: The class's declared capability manifest.
    """

    domain: str
    intents: frozenset[str]
    capabilities: frozenset[str]


class ProductAddress(CCFContract):
    """§6.3 **Addressability** — the address a class answers at.

    *"Addressability gives every product a well-defined interface the agent
    queries with intent, role, and freshness parameters"*
    (``docs/CCF_Whitepaper_1-2.md:1465``), worked there as
    ``/context-products/credit-risk/counterparty/{counterparty-id}?intent=…&freshness=…``.

    **The path half only, deliberately.** D-IMPL-98 ruled that the request
    surface is a *typed request contract per product class* and that
    addressability and that contract are the same commitment; the query half
    of the worked pattern — subject and instant as typed **arguments** rather
    than artifact literals — is that ruling's own surface. Modelling query
    parameters here would foreclose its shape, so this class declares where a
    class is reached and says nothing about what it is called with.

    Attributes:
        address_template: The address pattern the class answers at. A
            template rather than a resolved address, because the subject is
            an argument of the request and not a property of the class.
    """

    address_template: str


#: A class that states no per-signal currency expectation.
#:
#: The positive assertion, in the ``NO_HITL_ACTIONS`` / ``NO_ADAPTER`` voice:
#: *this class's freshness is bounded by its TTL alone and it measures no
#: signal separately*. It is not "freshness unknown" — §6.3 makes SLA and TTL
#: siblings, and a class that declares only the TTL has made a smaller promise
#: rather than no promise. Every class registered before D-IMPL-106 was in
#: exactly this posture, which is why this is the default: the 29
#: :func:`register_product_class` call sites the ruling priced keep saying
#: what they always said.
UNMEASURED_FRESHNESS_SLA = FreshnessSLA(max_age_seconds_by_signal={})

#: A class that declares no constituent-validity floors (D-IMPL-31).
#:
#: The positive assertion *no constituent of this class is load-bearing enough
#: to refuse assembly on its staleness alone* — which is a governance
#: statement, not an omission, and is what every class shipped before the
#: floors existed was in fact asserting.
NO_VALIDITY_FLOORS = ConstituentValidityFloors(min_validity_seconds_by_signal={})

#: A class not published to the discovery registry.
#:
#: The positive assertion *this class is reached by direct reference and is
#: not offered for intent-, domain- or capability-based lookup*. A class with
#: no registry entry is a real and legitimate deployment choice — it is the
#: choice every class in this tree has made until now — and it is a different
#: statement from an entry nobody filled in.
NOT_DISCOVERABLE = ProductDiscovery(
    domain="not-discoverable",
    intents=frozenset(),
    capabilities=frozenset(),
)

#: A class with no declared external address.
#:
#: The positive assertion *this class is served in process and publishes no
#: address pattern*, which is exactly what the in-process delivery path this
#: tree ships has always done.
NOT_ADDRESSABLE = ProductAddress(address_template="not-addressable")

#: A class that declares no payload schema (D-IMPL-97 ruling 1).
#:
#: Carried on **both** halves of the pin so that "no schema" is one visible
#: state rather than a key and a version disagreeing. The positive assertion
#: *this class has not yet declared what its payload must look like*, which is
#: honest about a gap rather than papering over it: until a class declares a
#: schema, its payload is the unchecked ``Mapping[str, Any]`` D-IMPL-97 named
#: as the substantive defect, and that is visible in the registration rather
#: than inferred from a missing field.
NO_PAYLOAD_SCHEMA = "no-payload-schema"


class RegisteredProductClass(CCFContract):
    """Class-level governance of one product class, resolved at registration.

    Attributes:
        schema_name: Class identity.
        schema_version: The class's own semver lane (INV-CH7-49).
        ttl_anchor: Declared TTL derivation anchor (D-IMPL-31).
        assembly_mode: Declared mode (INV-CH7-55).
        max_ttl_key: Control Plane key of the class's MAX_TTL artifact.
        max_ttl_version: The pinned version of it. Pinned rather than
            "latest" so that the ceiling a decision was gated against is
            re-resolvable years later (whitepaper §7.10, D-IMPL-26).
        accepted_policy_binding_modes: The **accepted modes** of the
            ``policy_binding`` attestation dimension — SDK-defined per
            CLAUDE.md §11, realizing D-09 (see
            :class:`~ccf.controlplane.artifacts.ProductClassDeclaration`
            for the authored side). An unordered set, never an ordered
            minimum: no strength ordering between modes is invented. The
            default is the tier-1 ``{"assembly-stamped"}`` posture every
            pre-attestation class already lived under, so tier-2
            consumption is deny-by-default until a class opts in. Carried
            here because this is the value ``run_gates`` receives — the
            gate derives the class side of the attestation comparison from
            what it already holds.
        accepted_lineage_modes: The accepted modes of the ``lineage``
            attestation dimension, under exactly the same discipline;
            tier-1 default ``{"graph-supplied"}``.
        freshness_sla: The §6.3 **Freshness SLA** element, per signal
            (D-IMPL-106 option (b)). Defaults to
            :data:`UNMEASURED_FRESHNESS_SLA`.
        discovery: The §6.3 **Discovery** element. Defaults to
            :data:`NOT_DISCOVERABLE`.
        addressability: The §6.3 **Addressability** element, path half only;
            the argument half is D-IMPL-98's typed request contract. Defaults
            to :data:`NOT_ADDRESSABLE`.
        constituent_validity_floors: D-IMPL-31's declarable floors. Declared
            here, refused on at assembly by plan ``15.5-12``. Defaults to
            :data:`NO_VALIDITY_FLOORS`.
        payload_schema_key: Control Plane key of the class's declared payload
            schema, or :data:`NO_PAYLOAD_SCHEMA`.
        payload_schema_version: The pinned version of it, on the same
            (key, version) discipline as ``max_ttl_version`` and for the same
            reason — the schema a payload was held to must be re-resolvable
            years later — or :data:`NO_PAYLOAD_SCHEMA`. The pair moves
            together; half a pin is refused at registration.
    """

    schema_name: str
    schema_version: str
    ttl_anchor: TTLAnchor
    assembly_mode: AssemblyMode
    max_ttl_key: str
    max_ttl_version: str
    accepted_policy_binding_modes: frozenset[PolicyBindingMode] = frozenset(
        {"assembly-stamped"}
    )
    accepted_lineage_modes: frozenset[LineageMode] = frozenset(
        {"graph-supplied"}
    )
    freshness_sla: FreshnessSLA = UNMEASURED_FRESHNESS_SLA
    discovery: ProductDiscovery = NOT_DISCOVERABLE
    addressability: ProductAddress = NOT_ADDRESSABLE
    constituent_validity_floors: ConstituentValidityFloors = NO_VALIDITY_FLOORS
    payload_schema_key: str = NO_PAYLOAD_SCHEMA
    payload_schema_version: str = NO_PAYLOAD_SCHEMA


class ProductLineage(CCFContract):
    """The L axis as it appears on a delivered product (INV-CH7-47).

    Attributes:
        operators_invoked: The operator set the *producer declares* it ran.
            Declared, not observed — the L6 lineage gate compares it against
            the engine's independent record, and a field the engine filled in
            would make that comparison vacuous.
        policy_bundle_versions: Every Control Plane policy-bundle version bound
            into the state this product was assembled from. A set, because
            state assembled under two bundle versions has two bindings and
            collapsing them would lose the one that mattered.
        graph_snapshot_at: The temporal anchor of the graph state read.
    """

    operators_invoked: frozenset[str]
    policy_bundle_versions: frozenset[str]
    graph_snapshot_at: datetime


class ContextProductContract(CCFContract):
    """The typed unit L6 delivers — and the only thing an agent may consume.

    Whitepaper §6.3, §7.6; DESIGN.md §2B.3. ``extra=forbid`` and frozen by
    inheritance from :class:`~ccf.contracts.base.CCFContract`: an unvalidated
    or forged product is a validation failure, never a served product.

    Constructing an instance of this class is *not* the same as having
    something servable. This type is the candidate; :class:`
    ~ccf.products.gates.ServableProduct` is the gated result, and only
    :mod:`ccf.products.gates` can mint one.

    Attributes:
        debt: The :class:`~ccf.halflife.assessment.DebtAssessment` in force
            when this product was assembled (§7.7, D-IMPL-99/100) — per factor,
            so a consumer can see *which* of freshness, completeness or
            semantic consistency collapsed rather than only how far. ``None``
            is the positive assertion *this product was assembled with no debt
            assessment*, in the :data:`~ccf.replay.record.NO_HITL_ACTIONS`
            voice: it is what every product shipped before this field existed
            was in fact asserting, and an unassessed product and one whose
            assessment somebody dropped would otherwise be the same artifact.
            The default is what keeps all 42 existing construction sites saying
            exactly what they always said.
    """

    schema_name: str
    schema_version: str
    plan_id: str
    tenant_id: str
    temporal_boundary: datetime
    expires_at: datetime
    ttl_anchor: TTLAnchor
    lineage: ProductLineage
    payload: Mapping[str, Any]
    debt: DebtAssessment | None = None


def register_product_class(
    *,
    registry: ControlPlaneProtocol,
    schema_name: str,
    schema_version: str,
    ttl_anchor: TTLAnchor,
    assembly_mode: AssemblyMode,
    max_ttl_key: str,
    max_ttl_version: str,
    accepted_policy_binding_modes: frozenset[PolicyBindingMode] = frozenset(
        {"assembly-stamped"}
    ),
    accepted_lineage_modes: frozenset[LineageMode] = frozenset(
        {"graph-supplied"}
    ),
    freshness_sla: FreshnessSLA = UNMEASURED_FRESHNESS_SLA,
    discovery: ProductDiscovery = NOT_DISCOVERABLE,
    addressability: ProductAddress = NOT_ADDRESSABLE,
    constituent_validity_floors: ConstituentValidityFloors = NO_VALIDITY_FLOORS,
    payload_schema_key: str = NO_PAYLOAD_SCHEMA,
    payload_schema_version: str = NO_PAYLOAD_SCHEMA,
) -> RegisteredProductClass:
    """Register a product class, requiring its MAX_TTL to already exist.

    Whitepaper §7.6; D-IMPL-39. The MAX_TTL is resolved *here*, at
    registration, so a deployment that forgot to configure a ceiling finds out
    while wiring the fabric rather than when a product is about to be served —
    at which point the only remaining options are a silent default (forbidden)
    or a failure in front of a caller.

    ``accepted_policy_binding_modes`` / ``accepted_lineage_modes`` carry the
    class's D-09 accepted attestation modes onto the registered value (from
    :class:`~ccf.controlplane.artifacts.ProductClassDeclaration`'s fields of
    the same names). Their defaults are the tier-1 posture, so a caller that
    registered before attestation existed registers exactly what it always
    implicitly demanded.

    The three §6.3 elements landed by plan ``15.5-07`` — ``freshness_sla``
    (D-IMPL-106), ``discovery`` and ``addressability`` (D-IMPL-98) — and
    D-IMPL-31's ``constituent_validity_floors`` all default to named positive
    sentinels rather than to required arguments, so every registration written
    before they existed keeps asserting exactly what it always asserted. See
    each sentinel for what it asserts.

    **The payload-schema pin, and why it is resolved here** (D-IMPL-102 limb
    1, *schema validity at registration*). A class that declares a payload
    schema names it by ``(key, version)`` and the schema must already be
    registered, on exactly the MAX_TTL reasoning: a deployment that pinned a
    schema that is not there finds out while wiring the fabric, not when a
    request is about to be bound to it. The well-formedness half of limb 1 is
    structural rather than a check that could be forgotten — a malformed
    :data:`~ccf.products.payload.ProductPayloadSchema` cannot be constructed
    at all (D-IMPL-56's required-names validator and D-IMPL-103's nesting
    ceiling both refuse at construction), so what remains for registration is
    that the pinned artifact **is** one, which is checked by type exactly as
    MAX_TTL's is.

    **No fourth gate follows from any of this** (D-IMPL-102, limb 3). The
    conformity comparison the pin makes possible runs at bind — request time
    — on the surface D-IMPL-98 creates. :func:`ccf.products.gates.run_gates`
    is untouched and the three shipped validation gates stay at three.

    Raises:
        ProductClassRegistrationError: no MAX_TTL is registered at
            ``(max_ttl_key, max_ttl_version)``, or the artifact there is not a
            :class:`MaxTTL`; or the payload-schema pin is half-declared, names
            nothing registered, or names an artifact that is not a payload
            schema.
    """
    try:
        artifact = registry.resolve(max_ttl_key, max_ttl_version)
    except ControlPlaneMissing as missing:
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares MAX_TTL at "
            f"({max_ttl_key!r}, {max_ttl_version!r}), which is not registered; "
            "MAX_TTL is required Control Plane configuration per product class "
            "and the SDK ships no default (D-IMPL-39)"
        ) from missing
    if not isinstance(artifact, MaxTTL):
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares MAX_TTL at "
            f"({max_ttl_key!r}, {max_ttl_version!r}), which holds "
            f"{type(artifact).__name__}, not MaxTTL"
        )
    _refuse_payload_schema_pin(
        registry=registry,
        schema_name=schema_name,
        payload_schema_key=payload_schema_key,
        payload_schema_version=payload_schema_version,
    )
    return RegisteredProductClass(
        schema_name=schema_name,
        schema_version=schema_version,
        ttl_anchor=ttl_anchor,
        assembly_mode=assembly_mode,
        max_ttl_key=max_ttl_key,
        max_ttl_version=max_ttl_version,
        accepted_policy_binding_modes=accepted_policy_binding_modes,
        accepted_lineage_modes=accepted_lineage_modes,
        freshness_sla=freshness_sla,
        discovery=discovery,
        addressability=addressability,
        constituent_validity_floors=constituent_validity_floors,
        payload_schema_key=payload_schema_key,
        payload_schema_version=payload_schema_version,
    )


def _refuse_payload_schema_pin(
    *,
    registry: ControlPlaneProtocol,
    schema_name: str,
    payload_schema_key: str,
    payload_schema_version: str,
) -> None:
    """Raise unless the class's payload-schema pin resolves to a schema.

    Split out of :func:`register_product_class` rather than inlined so the
    MAX_TTL resolution above stays readable as one thing; the refusal
    discipline is identical to it — raised, never returned or warned, naming
    both sides, because a class whose governance configuration is absent or
    malformed must not become servable (D-IMPL-39's reasoning, applied to
    D-IMPL-102 limb 1).

    The import of the payload module is function-local, and deliberately.
    :mod:`ccf.products.payload` reaches
    :class:`~ccf.skills.catalog.SkillArgumentSchema`, and
    :mod:`ccf.skills.catalog` completes its own definitions by importing
    :mod:`ccf.agents.definitions`, which imports this module — so a top-level
    import here would close a cycle at load time. The deferral is the same
    device :mod:`ccf.skills.catalog` already uses at its own foot, for the
    same reason, and it costs nothing: the resolution happens once per class
    registration, at wiring time.
    """
    from ccf.products.payload import ProductPayloadSchema

    declared_key = payload_schema_key != NO_PAYLOAD_SCHEMA
    declared_version = payload_schema_version != NO_PAYLOAD_SCHEMA
    if declared_key != declared_version:
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares half a payload-schema "
            f"pin: key={payload_schema_key!r}, version="
            f"{payload_schema_version!r}. A schema is pinned by (key, "
            "version) so that the schema a payload was held to is "
            f"re-resolvable years later; either both are {NO_PAYLOAD_SCHEMA!r} "
            "or neither is (D-IMPL-102, D-IMPL-26)"
        )
    if not declared_key:
        return
    try:
        artifact = registry.resolve(payload_schema_key, payload_schema_version)
    except ControlPlaneMissing as missing:
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares its payload schema at "
            f"({payload_schema_key!r}, {payload_schema_version!r}), which is "
            "not registered; a declared schema is resolved at registration so "
            "that a deployment which pinned a schema that is not there finds "
            "out while wiring the fabric rather than at bind (D-IMPL-102 "
            "limb 1)"
        ) from missing
    if not isinstance(artifact, ProductPayloadSchema):
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares its payload schema at "
            f"({payload_schema_key!r}, {payload_schema_version!r}), which "
            f"holds {type(artifact).__name__}, not a payload schema "
            f"({ProductPayloadSchema.__name__})"
        )
