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
Its *shape* is per-signal rather than scalar, following §6.3 at ``:1453``,
which makes the expectation vary with the signal and with the decision;
D-IMPL-106 ruled the placement and left the shape to this plan, stating that
no scalar is ruled in by silence.

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
``docs/CCF_Whitepaper_1-2.md:2696`` are unambiguous that debt is something the
agent has to consume while deciding — a first-class input, not an audit trace
read afterwards — so it is carried **here**, inside the delivered bytes,
rather than beside them.

**The three doors, and what a consumer at each receives.** Every shipped
delivery path serializes ``servable.product`` and **none** reads
``ServedProduct.replay_ref``, so a placement beside the vessel would have
reached an in-process caller and no wire consumer at all. Because debt is on
the vessel, all three carry it with **no code change at any door**:

==================================================================  ==============  ===========
Door                                                                Serializes      Carries D_c
==================================================================  ==============  ===========
``runtime/ccf_runtime/mcp/egress.py::build_egress_server``          the vessel      yes
``runtime/ccf_runtime/http_api/routes/product.py::build_router``    the vessel      yes
``runtime/ccf_runtime/mcp/experience.py::build_experience_server``  the vessel      yes
==================================================================  ==============  ===========

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
the engine's check inside ``src/ccf/replay/engine.py::replay`` passes on
identical
bytes rather than on a re-measurement. Debt is **never** re-derived at replay:
it is computed from observations and a ``now`` neither the record nor the
projection re-derives, so a rehydrator that re-measured it would produce a
different decision wearing this one's identifier.

**What debt points at rides beside it, and the address moves a second time**
(D-IMPL-118). ``debt_evidence`` is a *top-level* field, a sibling of ``debt``
rather than a member of the assessment. The nested placement was the cheaper
measured option — it would have ridden ``ContentGenerationPath.debt`` and
reconstructed for nothing — and was declined, so the sibling pays for its own
identity: dimension 5 carries a matching member, and every implementation of
:meth:`~ccf.replay.engine.ReplayEnvironment.rehydrate_product` reads it back.
Without both halves every replay of every product would raise
``ReplayDivergence``, because
:func:`~ccf.contracts.canonical.canonical_bytes` walks a model field-by-field
over ``type(value).model_fields`` and the new field is therefore in the
address. D-IMPL-117 authorized that move in advance — *"surface impact is
accepted"* — so it is a ruled cost rather than a defect.

**When the sources last published rides beside both, and the address moves a
third time** (D-IMPL-112 gap 2, D-IMPL-117, D-IMPL-118).
``source_refresh_recency`` is the second sibling of ``debt`` and takes the same
ruled placement, which D-IMPL-118 says *"price[s] all three Track B
vessel-carried members identically"* — so it pays the same price: a matching
member on dimension 5 and the same read-back in every ``rehydrate_product``.
It is here rather than folded into ``debt.factors.freshness`` because the two
are different facts. F is a *derived* figure — how much of a decay budget the
fabric's own curve has eaten — while this is an *observed* one about the world
outside the fabric. A consumer shown only F cannot tell a source that publishes
daily and is two days late from one that publishes annually and is current.
The SDK stores the instants and draws no conclusion from them; comparing a
refresh against a cadence or a threshold would be salience, which D-IMPL-101
deferred.

**And it names no source** (D-IMPL-124, revising what 15.6-07 shipped). The
member carried a per-source map whose entries named the source each instant
belonged to, and both delivery paths serialise this vessel verbatim to every
principal who can reach the product — so a reader entitled to the product could
learn that a given upstream system exists and when it last published, with no
check that they were entitled to that system's contents. The member now carries
a :class:`~ccf.halflife.assessment.SourceRefreshWindow`: the oldest and the
newest of the deployment's declared refresh instants, with no source identity
and no count. The placement is unchanged — D-IMPL-118's ruling is not amended,
only the member's contents are — so dimension 5 and the read-backs stay exactly
as they were.

**What the signal obliged rides beside all three, and the address moves a
fourth time** (D-IMPL-112 gap 3, D-IMPL-117, D-IMPL-118).
``obligation_in_force`` is the third sibling of ``debt`` and takes the same
ruled placement, so it pays the same price: a matching member on dimension 5
and the same read-back in every ``rehydrate_product``. It carries the
obligation the deployment's :class:`~ccf.controlplane.artifacts.DebtProfile`
bound to the routing state *this* decision landed in — the resolved value, not
the mapping. A consumer handed the mapping would be holding the calibration
rather than the decision, and a consumer handed nothing would have to resolve
the profile again at read time, which is the substitution D-IMPL-26's
exact-version rule forbids. **The SDK carries it and acts on it nowhere**:
what an obligation requires is user configuration (CLAUDE.md §11), and a
module that branched on the value would have chosen the vocabulary.

**What may be put in it is constrained, and the constraint is standing**
(D-IMPL-119). Evidence pointers are entitlement-sensitive, and the shipped
assembly path is not principal-scoped: :class:`ccf.halflife.assessment
.DebtEvidencePointer` documents what that refuses until the gap is closed.
Nothing carried here varies by principal, which is what keeps a field inside
the content address compatible with D-IMPL-105's one-figure-per-product
reading.

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
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.graph.protocols import (
    NO_STORE_SNAPSHOT_PIN,
    LineageMode,
    PolicyBindingMode,
    StoreSnapshotPin,
)
from ccf.halflife.assessment import (
    NO_DEBT_EVIDENCE,
    NO_OBLIGATION_IN_FORCE,
    NO_SOURCE_REFRESH_RECENCY,
    DebtAssessment,
    DebtEvidence,
    ObligationInForce,
    SourceRefreshRecency,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "NOT_ADDRESSABLE",
    "NOT_DISCOVERABLE",
    "NO_PAYLOAD_SCHEMA",
    "NO_REQUEST_CONTRACT",
    "NO_SERVE_OBLIGATIONS",
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
    "ServeObligations",
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

    §6.3 (``docs/CCF_Whitepaper_1-2.md:1453``) separates two primitives that
    are easy to conflate. This one is an *expectation* — how recent a signal
    has to be before the product may rest on it. :class:`MaxTTL` is a
    *bound* — how long the assembled product stays usable once that recency
    can no longer be guaranteed. §6.3 calls them siblings rather than
    duplicates, which is why both exist here and neither is a respelling of
    the other.

    **Per signal, not a scalar.** §6.3 makes the expectation vary by signal
    and by decision, and warns that collapsing signals of different currency
    into one undeclared figure yields an input an agent cannot rely on. A
    single number for a product assembled from an end-of-day filing *and* an
    intraday blotter entry hides exactly that difference. D-IMPL-106 ruled
    the *placement* and left the shape here, recording that no scalar was
    ruled in by silence.

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

    §6.3 (``docs/CCF_Whitepaper_1-2.md:1463``) puts a registry in front of the
    fabric: products are located by the intent they serve, the domain they
    belong to, and the capability they offer, and an agent turns a name into
    an endpoint at run time rather than at wiring time. The three fields below
    are those three axes. ``capabilities`` is the declared manifest §6.3's
    worked registry entry carries. ``audiences`` is a fourth, SDK-defined axis
    per ``docs/DECISIONS.md`` D-IMPL-135 — see that field's own docstring.

    Every value is a deployment-declared opaque identifier. The SDK matches
    them structurally and interprets none, so no intent vocabulary, domain
    taxonomy, capability list or audience vocabulary exists in this module
    (CLAUDE.md §11).

    Attributes:
        domain: The domain the class belongs to.
        intents: The decision intents the class is registered as serving.
        capabilities: The class's declared capability manifest.
        audiences: The audiences the class is declared for — e.g.
            ``{"analyst", "investment_banker"}``. **Not**
            :class:`~ccf.projection.plan.Perspective`: ``Perspective``
            conditions Π's view of the graph under a caller's grant at run
            time; ``audiences`` advertises an intended readership to a
            registry and conditions nothing. D-IMPL-135 (Dave, 2026-08-14)
            ruled the axis on exactly this distinction — a role maps onto
            none of ``domain``, ``intents`` or ``capabilities``, and the two
            come apart the moment one role serves several intents.

            Defaults to the empty frozenset, the honest reading of an absent
            ``audiences:`` block — *this class declares no audience* — on
            the same footing as :data:`NOT_DISCOVERABLE`'s reading of an
            absent registry entry. The rejected alternative was a required
            field with every one of the tree's ``ProductDiscovery``
            construction sites moved to supply it, which D-IMPL-136 §10's
            compatibility posture forbids by analogy for a shipped §6.3
            element with no migration path.
    """

    domain: str
    intents: frozenset[str]
    capabilities: frozenset[str]
    audiences: frozenset[str] = frozenset()


class ProductAddress(CCFContract):
    """§6.3 **Addressability** — the address a class answers at.

    §6.3 (``docs/CCF_Whitepaper_1-2.md:1465``) commits every product to an
    interface an agent can query by name, parameterised by the intent, the
    role and the freshness it needs. The section works that commitment as a
    path plus a query string, of the shape
    ``/context-products/{domain}/{entity-kind}/{id}?intent=…&freshness=…``.

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
    audiences=frozenset(),
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

#: A class that declares no request contract (D-IMPL-98).
#:
#: Defined **here**, beside the field it defaults, on
#: :data:`NO_PAYLOAD_SCHEMA`'s own placement and for a hard reason as well as a
#: tidy one: :mod:`ccf.products.request` — where the request surface itself
#: lives — imports :class:`ProductClassRegistrationError` from this module, so
#: the sentinel cannot live there and still be readable from
#: :class:`RegisteredProductClass`'s default. It is re-exported from
#: :mod:`ccf.products.request`, which is where an adopter authoring a contract
#: will look for it, exactly as :mod:`ccf.products.bind` reads
#: :data:`NO_PAYLOAD_SCHEMA` from here.
#:
#: Carried on **both** halves of the pin so that "no contract" is one visible
#: state rather than a key and a version disagreeing. The positive assertion is
#: *this class has not yet declared the questions it answers* — until it does,
#: its subject and its instant are whatever an artifact happened to author, and
#: that gap is visible in the declaration rather than inferred from a missing
#: field.
NO_REQUEST_CONTRACT = "no-request-contract"


class ServeObligations(CCFContract):
    """What a product class obliges the serve path to enforce — declared as data.

    SDK-defined per CLAUDE.md §11; whitepaper §7.6 (the delivery contract and
    its validation gates) and §7.7.4–§7.7.8 (Context Debt gating Forced LLM
    and Fail-Closed behavior). Ledger rows ``24.5-L-14`` (the debt ceiling)
    and ``24.5-L-26`` (the per-attribute lineage obligation), licensed by
    ``D-IMPL-237`` — the ONE structural serve-time gate mechanism the SDK
    ships — and shaped by ``D-IMPL-240`` (3). In one sentence: **the class
    declares the ceiling, a request may tighten it, and serve refuses
    over-ceiling by name** (:data:`~ccf.products.gates.GATE_DECLARED_OBLIGATIONS`).

    Both members are *obligations*, never gate types: a product class does
    not declare a new kind of gate (``D-IMPL-224`` stands), it declares what
    the one shipped gate holds it to. And both are read as **structure** —
    a number against a number, the presence of a named member — never as a
    payload shape (``D-IMPL-238`` reads ``D-IMPL-102`` limb 3 as *no payload
    gate*).

    Attributes:
        debt_ceiling: The class's ``D_c`` ceiling, a proportion in ``[0, 1]``
            (the interval :class:`~ccf.halflife.assessment.DebtAssessment`
            already holds ``debt`` to). ``None`` is the positive sentinel
            *this class declares no ceiling* — the only value under which the
            debt half of the gate is silent, and what every class registered
            before this field existed was asserting. The NUMBER is the
            deployment's to author in its product-class artifact; the SDK
            ships no default and no threshold (CINV-01, CLAUDE.md §11). A
            request's ``debt_tolerance`` may only *lower* the effective
            ceiling (:func:`~ccf.products.gates.effective_debt_ceiling`); it
            can neither create one nor raise one.
        lineage_inputs_at: The TOP-LEVEL payload members that must be present
            and non-empty at serve — the class's per-attribute lineage
            obligation (``24.5-L-26``; the SDK's declared form of what cp-03
            carries as a product gate). The empty set is the positive sentinel
            *no obligation declared*. Names only: which members a class
            obliges is the class's to say, and what those members contain is
            never read here.
    """

    debt_ceiling: Decimal | None = None
    lineage_inputs_at: frozenset[str] = frozenset()

    @field_validator("debt_ceiling")
    @classmethod
    def _ceiling_is_a_proportion(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not (Decimal(0) <= value <= Decimal(1)):
            raise ValueError(
                "debt_ceiling must lie in [0, 1]: D_c is a proportion "
                "(whitepaper §7.7.4), so a ceiling outside that interval "
                "either refuses everything or nothing (24.5-L-14)"
            )
        return value


#: A class that declares no serve obligation — no debt ceiling, no lineage
#: member. The positive assertion every product class registered before
#: ``24.5-L-14`` / ``24.5-L-26`` existed was already making, so every
#: pre-phase registration and every pre-phase ``run_gates`` call site says
#: exactly what it always said (``D-10``, additive; ``D-IMPL-240`` (3): "a
#: class declaring no ceiling is unaffected").
NO_SERVE_OBLIGATIONS = ServeObligations()


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
        request_contract_key: Control Plane key of the class's declared
            request contract (D-IMPL-98's typed request surface — *which
            questions this class answers*), or
            :data:`~ccf.products.request.NO_REQUEST_CONTRACT`. The mirror of
            :attr:`~ccf.controlplane.artifacts.ProductClassDeclaration
            .request_contract_key`, resolved at registration rather than
            trusted from the declaration.
        request_contract_version: The pinned version of it, on the same
            (key, version) discipline as the payload-schema pin and for the
            same reason — the surface a *question* was validated against has
            to be re-resolvable years later for a decision to replay — or
            the same sentinel. The pair moves together; half a pin is refused
            at registration.
        serve_obligations: The class's declared :class:`ServeObligations`
            (``24.5-L-14``, ``24.5-L-26``; ``D-IMPL-237``) — the debt ceiling
            and the lineage members the ONE structural declared-obligations
            gate in :func:`~ccf.products.gates.run_gates` holds a served
            product to. Carried here because this is the value the gate
            receives, on the ``accepted_lineage_modes`` reasoning. Defaults to
            :data:`NO_SERVE_OBLIGATIONS`, under which the gate is silent.
            Hash-transparent at that sentinel (``D-IMPL-243``): a class
            obliging nothing is every pre-phase class, so the field is
            omitted from the canonical form at that value and rendered at
            any declared obligation.
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
    request_contract_key: str = NO_REQUEST_CONTRACT
    request_contract_version: str = NO_REQUEST_CONTRACT
    serve_obligations: ServeObligations = Field(
        default=NO_SERVE_OBLIGATIONS, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


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
        store_snapshot_pin: The substrate's transaction-time head at the read
            that assembled this product — the
            :class:`~ccf.graph.protocols.StoreSnapshotPin` the reader minted
            once, before its first query — recorded **beside**
            ``graph_snapshot_at`` and never inside it (D-IMPL-88: a store
            transaction counter is not an as-of instant and never implements
            one; ledger row 24.5-L-02; D-IMPL-240). The default,
            :data:`~ccf.graph.protocols.NO_STORE_SNAPSHOT_PIN`, is the positive
            assertion *this product's substrate exposes no native pin* — what
            a SQLite or Postgres deployment is in fact asserting today — and
            it is asserted, never inferred from silence: a product assembled
            before this field existed, and one assembled over a reader that
            cannot pin, both say exactly that. This field is inside
            :func:`~ccf.contracts.canonical.canonical_bytes` by construction
            (every ``model_fields`` member is), so two products differing only
            in pin have different content addresses — which is what makes
            "served at pin N is not reproducible from pin N+1" a property of
            the contract rather than a hope about the replay path.
            Hash-transparent at the sentinel (``D-IMPL-243``): "no pin
            recorded" is what a product assembled before this field
            existed says, so the field is omitted from the canonical form
            at that value; a real pin is rendered and is a new identity.
    """

    operators_invoked: frozenset[str]
    policy_bundle_versions: frozenset[str]
    graph_snapshot_at: datetime
    store_snapshot_pin: StoreSnapshotPin = Field(
        default=NO_STORE_SNAPSHOT_PIN, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


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
        debt_evidence: What that assessment points at (D-IMPL-118) — the
            handles for the things whose decay it summarises. A **sibling of**
            ``debt`` rather than a member of it, which is the ruled placement
            and not a convenience: see the note below for what the sibling
            costs and why the cost was authorized. Defaults to
            :data:`~ccf.halflife.assessment.NO_DEBT_EVIDENCE`, the positive
            assertion *this product was assembled with no evidence pointers*,
            so every construction site written before this field existed says
            exactly what it always said.
        source_refresh_recency: When the oldest and the newest of the
            assembling deployment's sources last refreshed, as that deployment
            declares it (D-IMPL-112 gap 2, D-IMPL-117, D-IMPL-124). A **second
            sibling of** ``debt`` under the same ruled placement, and a fact
            distinct from the ``debt.factors.freshness`` beside it: F says how
            much of a decay budget has been spent, and says nothing about when
            the upstream registry last published. It is a
            :class:`~ccf.halflife.assessment.SourceRefreshWindow` and **not** a
            per-source map: D-IMPL-124 ruled that the field's purpose is
            freshness rather than source enumeration, so no source identity and
            no count crosses onto the vessel. Reducing a deployment's declared
            per-source instants to this window is the deployment's work — it is
            the only party that knows its own set is complete. Defaults to
            :data:`~ccf.halflife.assessment.NO_SOURCE_REFRESH_RECENCY`, the
            positive assertion *this product records nothing about when its
            sources last refreshed*.
        obligation_in_force: What the deployment's debt profile bound to the
            routing state this decision landed in (D-IMPL-112 gap 3,
            D-IMPL-117). A **third sibling of** ``debt`` under the same ruled
            placement. The *resolved* reference for this decision's signal, not
            the profile's whole mapping — the vessel records what this decision
            was obliged to do, and the calibration stays on the artifact that
            owns it. Opaque: the SDK never parses it and never acts on it.
            Defaults to
            :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE`, the
            positive assertion *no obligation was bound to the state this
            decision landed in*. Carried as
            :data:`~ccf.halflife.assessment.ObligationInForce`, which admits
            that sentinel or a declared reference and refuses a blank — the
            third state that asserts neither and would reproduce inside this
            product's content address as if it did.
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
    debt_evidence: DebtEvidence = NO_DEBT_EVIDENCE
    source_refresh_recency: SourceRefreshRecency = NO_SOURCE_REFRESH_RECENCY
    obligation_in_force: ObligationInForce = NO_OBLIGATION_IN_FORCE


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
    request_contract_key: str = NO_REQUEST_CONTRACT,
    request_contract_version: str = NO_REQUEST_CONTRACT,
    serve_obligations: ServeObligations = NO_SERVE_OBLIGATIONS,
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

    ``serve_obligations`` (``24.5-L-14``, ``24.5-L-26``) is passed straight
    through onto the registered value: it is a declared obligation the ONE
    structural gate ``D-IMPL-237`` licenses reads at serve, not a payload
    gate, and its default — :data:`NO_SERVE_OBLIGATIONS` — keeps every
    registration written before it existed asserting exactly what it always
    asserted.

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
    # The import is function-local for exactly the reason the payload one
    # below is, and one reason more: `ccf.products.request` imports
    # `ProductClassRegistrationError` from THIS module, so a top-level import
    # here would close the cycle directly rather than through the skills
    # catalog. The resolution happens once per class registration, at wiring
    # time, so the deferral costs nothing.
    from ccf.products.request import refuse_request_contract_pin

    refuse_request_contract_pin(
        registry=registry,
        schema_name=schema_name,
        schema_version=schema_version,
        request_contract_key=request_contract_key,
        request_contract_version=request_contract_version,
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
        request_contract_key=request_contract_key,
        request_contract_version=request_contract_version,
        serve_obligations=serve_obligations,
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
