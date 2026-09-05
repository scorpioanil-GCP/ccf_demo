"""The request surface a product class declares and a door validates.

SDK-defined. The ruling of record is ``docs/DECISIONS.md`` **D-IMPL-98** (Dave,
2026-08-11, option (a)): *the request surface is a typed request contract per
product class, declared as a Control Plane artifact, in the*
:class:`~ccf.skills.catalog.SkillArgumentSchema` *shape*. CLAUDE.md §11
requires an SDK extension to cite this project's own record; what the
whitepaper does commit to is §6.3 **Addressability**
(``docs/CCF_Whitepaper_1-2.md:1465``), which gives each product an interface an
agent queries by name, parameterised by intent, role and freshness — the point
being that a structured query lets the product be assembled at decision time
instead of retrieved pre-aggregated. §6.3 works the address as a path plus a
query string, of the shape
``/context-products/{domain}/{entity-kind}/{id}?intent=…&freshness=…``,
carrying the three things the agent has to name: which entity, for which
decision, and under what temporal requirement.

**What was wrong, stated precisely, because half of it was right.** A Context
Product was *configurable* rather than *callable*: its subject and its instant
were literals authored in an artifact, so one product class answered one
question about one company as of one frozen moment. That is the thing Chapter 1
names CCF as replacing — the distinction it draws between *aggregating* and
*assembling*. But the mechanism underneath it is correct and must not be
"fixed": **the caller supplying the instant is the design; the instant being a
literal in a YAML file is the defect.**
:meth:`~ccf.projection.engine.ProjectionEngine.execute` reads no clock
deliberately, so that at serve time the caller passes *now* and at replay time
the caller passes the *recorded* boundary, and the same code path yields the
same answer. A plan that put a clock in the engine — or in this module — would
make replay impossible. Nothing here reads one, and
``tests/products/test_request_contract.py`` scans this file's AST to keep that
true rather than trusting the sentence.

**Where the four axes come from.** :class:`ProductRequest` models the
whitepaper's own address pattern rather than a convenience shape: an **entity
anchor** (``subject``), an **intent**, a **freshness expectation**, and the
**instant** the caller is asking as of (``asked_at``). None has a default,
because a defaulted axis is a question nobody asked, answered anyway. The
class-declared remainder travels in ``parameters``, whose shape the class
declares and :func:`refuse_request` compares against.

**Role is deliberately not a request field**, and its absence is asserted by
field enumeration rather than described here. The role a product is shaped
under is resolved *at the door* from the caller's verified
:class:`~ccf.products.entitlement.ProductEntitlementGrant` before a
:class:`~ccf.projection.plan.Perspective` is constructed (plan ``15.5-06``). A
role the caller could put in the request body would reintroduce exactly the
unverified claim that work closed — the caller would be asserting who they are
in the same breath as asking the question. The same reasoning excludes the
tenant: both are things the door *establishes*, never things the request
*claims*.

**Where the parameters go.** ``D-IMPL-49`` already reserved the slot: the
deterministic plan-selection signature is
``(perspective, context_product_class, selection_params)``, and a request's
parameters are what reaches selection through ``selection_params``. This module
supplies the block's shape; it does not alter that signature.

**Where the validation runs, and where it does not run yet.** ``D-IMPL-108``
(Dave, 2026-08-11) ruled that the door wiring is **plan 15.5-15's**, not this
module's: :class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` and
:class:`~ccf_runtime.mcp.experience.ExperienceProductResolverProtocol` are
three-string seams through which neither a typed request nor an authorized
:class:`~ccf.projection.plan.Perspective` can pass, and that seam is widened
**exactly once**, carrying both, rather than twice. This module is therefore
built so a widened seam can pass a :class:`ProductRequest` through without
reshaping it: the request is self-describing — it names the class and the lane
it is addressed to — so a door can cross-check it against what it resolved
rather than re-deriving it.

**One reading of "conforms", not two.** :func:`refuse_request` does not
re-implement the comparison :func:`~ccf.products.payload.refuse_payload`
already makes; it *calls* it and translates the verdict. That is the strongest
available form of the discipline
:func:`~ccf.products.gates.refuse_attestation` states — the door's check and
any registration-time capability check must not drift into two readings of
"well-formed" — and it is why D-IMPL-103's widening reaches the request surface
for free. The verdict **type** stays distinct
(:class:`ProductRequestViolation`, not
:class:`~ccf.products.payload.PayloadSchemaViolation`) for the same reason
:class:`~ccf.products.payload.PayloadSchemaViolation` is not a
:class:`~ccf.products.gates.GateRefusal`: a request verdict must not be able to
travel as a payload verdict merely because the comparison beneath them is
shared.

This module declares **shape only**. There is no intent name, no parameter
name, no entity URI and no freshness figure in it — every one of those is the
deployment's own statement (CINV-01), the posture
``ccf.peering.trust_policy:31-35`` and ``ccf.products.contract:32-35`` both
state for their own modules.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.artifact_base import ArtifactClass, VersionedArtifact
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.products.contract import (
    NO_REQUEST_CONTRACT,
    ProductClassRegistrationError,
)

# `ccf.skills.catalog` is imported at the BOTTOM of this module, on the
# D-IMPL-56 pattern `ccf.skills.catalog` itself documents. The reason is
# D-IMPL-111 limb (b): `ccf.replay.record` now names :class:`ProductRequest` in
# dimension 5, and `ccf.skills.catalog` reaches `ccf.agents.agent`, which reads
# two names out of `ccf.replay.record` — so with that import at the top,
# first-import order would decide whether the SDK imports at all. Deferring it
# makes :class:`ProductRequest` exist before anything here can reach the replay
# plane; the deferred annotation is resolved explicitly at the bottom.
#
# `ccf.products.payload` is **not** imported at module scope at all — see the
# TYPE_CHECKING block and :func:`refuse_request` below. That module reaches
# `ccf.skills.catalog` at *its* top, so a module-scope edge from here back to
# it closed a five-module cycle whose only safe entry point was this module:
# `import ccf.products.payload` as the first import into the tree raised
# ``ImportError`` (DEF-17-02). The edge is genuinely gone rather than reordered,
# and `tests/invariants/test_cold_import.py` walks every `ccf.*` module in its
# own cold subprocess to keep it gone.

if TYPE_CHECKING:  # pragma: no cover - typing-only, and deliberately so
    # *** THE IMPORT EDGE ALREADY RUNS THE OTHER WAY. ***
    # `ccf.controlplane.artifacts:100` imports `NO_REQUEST_CONTRACT` from this
    # module, so a module-level `from ccf.controlplane.artifacts import
    # DeclaredArtifact` here fails at import time — not sometimes, always. This
    # module carries `from __future__ import annotations`, so the annotation on
    # `ProductRequestContract.from_declared` is a string at runtime and this
    # import never executes. `tests/products/test_request_contract.py` imports
    # the two modules in both orders to keep that true.
    from ccf.controlplane.artifacts import DeclaredArtifact

    # Typing-only for the same structural reason, and this one closed a cycle.
    # :func:`_translate` names :class:`
    # ~ccf.products.payload.PayloadSchemaViolation` in a parameter annotation
    # and nowhere else; the module's `from __future__ import annotations` makes
    # that a string, and `_translate` is a plain function rather than a
    # contract, so nothing ever resolves it at runtime. The comparison itself
    # is a *value*, so :func:`refuse_request` imports it at call time instead.
    from ccf.products.payload import PayloadSchemaViolation

__ccf_mode__ = "algorithmic"

__all__ = [
    "NO_REQUEST_CONTRACT",
    "PRODUCT_REQUEST_CONTRACT",
    "AnchorAmbiguityRefusal",
    "ProductRequest",
    "ProductRequestContract",
    "ProductRequestViolation",
    "ProductRequestViolationReason",
    "refuse_request",
    "refuse_request_contract_pin",
    "request_seeds",
]

#: Re-exported from :mod:`ccf.products.contract`, where it is defined.
#:
#: It lives beside the :class:`~ccf.products.contract.RegisteredProductClass`
#: field it defaults — the placement :data:`
#: ~ccf.products.contract.NO_PAYLOAD_SCHEMA` already holds — because this
#: module imports that one and the dependency cannot run the other way. Named
#: here as well because this is where an adopter authoring a request contract
#: looks for it, on the terms :mod:`ccf.products.bind` reads its own sentinel.
#: See the defining module for what the sentinel asserts.

#: Why a request did not conform.
#:
#: Three of the five are the three ways a closed, typed, partially-required
#: declaration can be missed, spelled in the request's own vocabulary
#: (*parameter*, not *key*) so a caller reading a refusal is not asked to
#: translate. The fourth has no payload analogue: a payload belongs to whatever
#: product carried it, while a request is **addressed**, and a request handed
#: to the wrong class's contract is a mis-delivery rather than a bad argument.
#:
#: The fifth, ``not-supported-at-tier``, is the Context Product Specification
#: Standard's ``400 not_supported_at_tier`` (``references/Context_Product_Specification_Standard_v0-3.md``
#: §9) rendered in this vocabulary's own hyphenated spelling: the parameter is
#: part of the class's declared surface and the class refuses it **by
#: declaration**, every time, rather than honoring it (Standard §2.4,
#: *declared-but-inert*). It arrives through
#: :attr:`ProductRequestContract.unsupported_arguments`, never through the
#: payload comparison. Ledger row ``24.5-L-12``.
#:
#: The sixth, ``not-a-proportion``, is the one verdict that reads a presented
#: VALUE rather than a name or a type: the Standard's universal
#: :data:`~ccf.products.gates.DEBT_TOLERANCE_PARAMETER` states a ``D_c``
#: tolerance and ``D_c`` is a proportion (whitepaper §7.7.4), so a declared,
#: honored, well-typed number outside ``[0, 1]`` — or not finite — is not a
#: tolerance at all. It is refused here, in the contract-refusal family, so it
#: can never reach a resolution and stand as the number an admitted product is
#: withheld against (``24.5-REVIEW.md`` WR-02, Dave, 2026-09-02). The interval
#: is the one :class:`~ccf.products.contract.ServeObligations` holds the
#: CLASS's declared default to (``24.5-L-14``, ``24.6-L-04``): the request
#: boundary and the class boundary read the same interval.
ProductRequestViolationReason = Literal[
    "undeclared-parameter",
    "missing-required-parameter",
    "type-mismatch",
    "class-mismatch",
    "not-supported-at-tier",
    "not-a-proportion",
]

#: How :func:`~ccf.products.payload.refuse_payload`'s reasons read on the
#: request surface. A translation table rather than a second vocabulary: the
#: comparison is shared, so its verdicts must arrive intact and merely be
#: spoken in the surface's own words.
_REASONS: dict[str, ProductRequestViolationReason] = {
    "undeclared-key": "undeclared-parameter",
    "missing-required-key": "missing-required-parameter",
    "type-mismatch": "type-mismatch",
}


class ProductRequest(CCFContract):
    """One question asked of one product class — the whitepaper's address, typed.

    Whitepaper §6.3 **Addressability** (``docs/CCF_Whitepaper_1-2.md:1465``);
    D-IMPL-98 for the contract this is validated against.

    Frozen and ``extra=forbid`` by inheritance from
    :class:`~ccf.contracts.base.CCFContract`, so a request is a value: it is
    content-addressable, two callers asking the same question pin identically,
    and two callers asking different questions cannot pin the same — which is
    what makes *which question a decision answered* answerable from the replay
    record rather than reconstructed from context (plan ``15.5-13``).

    **Nothing on this type asserts who is asking.** Role and tenant are
    established by the door from the caller's verified grant, never claimed in
    the body; see the module docstring. The absence is enforced by field
    enumeration in ``tests/products/test_request_contract.py``.

    Attributes:
        schema_name: The product class being asked. Carried on the request
            rather than only alongside it, so a widened door seam can pass one
            self-describing value and cross-check it against what it resolved
            (D-IMPL-108, plan ``15.5-15``).
        schema_version: The class's own semver lane being asked for
            (INV-CH7-49). Lanes are per class and never compared across
            classes.
        subject: The entity anchor — *which entity*. The
            ``{counterparty-id}`` slot of the worked address pattern. An
            opaque deployment identifier; the SDK matches it structurally and
            interprets none of it, and validates its **shape** only. Whether
            this caller may receive a product about this subject is the door's
            entitlement check plus Π conditioning, both upstream of here.
        intent: The decision the product is being assembled for — *for what
            decision*. A deployment-declared token, drawn from the same
            vocabulary :class:`~ccf.products.contract.ProductDiscovery`
            publishes and the SDK enumerates none of.
        freshness: The currency the caller requires — *under what temporal
            requirement*. A declared expectation, compared against the class's
            :class:`~ccf.products.contract.FreshnessSLA` by the delivery path,
            never a number this module knows.
        asked_at: The instant the caller is asking **as of**. Supplied by the
            caller at serve time and by replay at replay time, through the same
            code path — which is the entire reason nothing downstream of here
            reads a clock.
        parameters: The class-declared remainder of the question, compared
            against the class's declared surface by :func:`refuse_request` and
            reaching plan selection through D-IMPL-49's ``selection_params``
            slot. Required with no default: an empty mapping is expressible and
            says *this question needs nothing beyond its four axes*, which is a
            statement rather than an omission.
        policy_overrides: The policy identifiers this question asks to be
            resolved *without* — an explicit, recorded exception rather than a
            silent one (``D-IMPL-253`` Q7). **Naming a policy is not authority
            to override it**: the resolver additionally establishes that the
            principal is entitled to exercise the override, against the
            declared grant
            (:attr:`~ccf.products.entitlement.ProductEntitlementGrant.overridable_policies`)
            — *"otherwise anyone who knows a policy ID could bypass it"*. Both
            facts, entitled and honored, land in the replay record whichever
            way they came out.

            It belongs on the request because **a request carrying an override
            is a different question**: it is content-addressed with the rest of
            the question, so two callers asking the same thing with and without
            an override do not pin identically. Hash-transparent at the empty
            tuple (``D-IMPL-243``): asking for no exception is what every
            request written before this field asked, so the field is omitted
            from the canonical form at that value and no committed request's
            content address moves.

            The SDK names no policy here — the identifiers are the
            deployment's own (CINV-01). This field asserts nothing about *who*
            is asking; the principal is resolved at the door from a verified
            grant, exactly as before.
    """

    schema_name: str
    schema_version: str
    subject: str
    intent: str
    freshness: str
    asked_at: datetime
    parameters: Mapping[str, Any]
    policy_overrides: tuple[str, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class ProductRequestContract(VersionedArtifact):
    """The questions one product class answers, as a Control Plane artifact.

    D-IMPL-98's *"typed request contract per product class ... in the*
    :class:`~ccf.skills.catalog.SkillArgumentSchema` *shape"*, realized. The
    artifact is what an adopter authors; :func:`refuse_request` is what reads
    it.

    **It reuses the declaration machinery rather than inventing a second one.**
    ``arguments`` is a :class:`~ccf.skills.catalog.SkillArgumentSchema` — the
    same type a skill declares its arguments in and a product class declares
    its payload in — which is D-IMPL-103's ruling applied where it was written
    to apply: *"the change is a widening, not a replacement"*. A request
    surface therefore gets one level of nested objects and lists-of-objects for
    free, and gets them with the ceiling expressed structurally rather than
    validated.

    **It names the class it serves**, which the payload schema cannot: a
    :class:`~ccf.skills.catalog.SkillArgumentSchema` is a shape and knows
    nothing about what declared it. Naming the class here makes the binding
    intrinsic to the artifact, so the registration-time refusal
    (:func:`refuse_request_contract_pin`) can catch a contract pinned onto the
    wrong class — a mis-wiring no shape comparison could ever see.

    Attributes:
        schema_name: The product class this is the request surface of.
        schema_version: The class lane it is the request surface of. Not this
            artifact's ``semver`` lane — two lanes, because they version
            different things: how the product's schema evolved, and how this
            declaration document evolved.
        arguments: The parameters the class accepts beyond the four address
            axes, declared as data. The declared world is **closed**: a
            parameter the class did not declare is refused rather than
            forwarded, because a parameter that reaches plan selection without
            having been declared is an argument nobody governed.
        unsupported_arguments: The parameters this class declares **and always
            refuses** — the Standard's *declared-but-inert* parameter
            (``references/Context_Product_Specification_Standard_v0-3.md``
            §2.4): part of the uniform surface, unsupported at this product's
            tier, and therefore refused explicitly rather than allowed to
            appear to work. Parameter name → the declared reason, as Control
            Plane prose the deployment authors and that lands verbatim in the
            verdict's ``detail``. The empty mapping is the positive assertion
            that this class declares no inert parameter, which is what every
            declaration written before this field said and still says. The set
            lives here, in the artifact, so that no spine code carries it
            (CLAUDE.md §6.4; ledger row ``24.5-L-13``). Hash-transparent at
            the empty mapping (``D-IMPL-243``): nothing declared-refused is
            every pre-phase contract, so the field is omitted from the
            canonical form at that value and a non-empty mapping is rendered.
        defaults: The value each parameter takes **when the caller omits it**.
            A default is not a competitor to a value the caller supplied; it is
            what omission *means* for this product (``D-IMPL-253`` Q2, Dave:
            *"Product defaults belong on the request contract. They define what
            omission means for that product."*). The empty mapping is the
            positive assertion that this class declares no default, which is
            what every declaration written before this field said and still
            says. The values live here, in the artifact, so that no spine code
            carries them (CLAUDE.md §6.4; ledger row ``24.6-L-07``): a number
            in code is a number no examiner can trace to a decision anyone made
            (CINV-01). Hash-transparent at the empty mapping (``D-IMPL-243``):
            declaring nothing is every pre-phase contract, so the field is
            omitted from the canonical form at that value and a non-empty
            mapping is rendered.

            **The SDK applies a default BEFORE validation, not after** — plan
            ``24.6-03``'s resolver step, which is what makes an omitted
            parameter reach the closed-world comparison as the value the class
            declared. The resolved value is recorded with authority
            ``default`` and this artifact's own pin as its source
            (:class:`~ccf.products.provenance.EffectiveParameter`), which is
            the whole reason omission has to mean something *declared*: a
            default applied from code could not be pinned, and a decision made
            under it could not be replayed.

            A default is refused at declaration when its name is not a declared
            argument, when it names a parameter this class always refuses, or
            when its value does not satisfy the declared argument's own type —
            all three named together in one message, because a default for a
            parameter the class does not honor would widen the closed request
            world by omission, which is the one thing this artifact exists to
            keep shut.
        capability_bindings: Which declared parameter each **technical**
            capability bounds — parameter name to the SDK's own capability
            token (``D-IMPL-253`` Q21, Dave: *"100 is the genuine technical
            capability boundary"*). The binding is the declaration's statement
            that *this* parameter is the one a substrate limit applies to; the
            limit itself is never here and never anywhere in an artifact — it
            is read off the backend at resolution time as a
            :class:`~ccf.products.constraints.TechnicalCapability`, because a
            number the deployment authored would be a technical bound nobody
            measured (CINV-01).

            Refused at declaration when a binding names a parameter this class
            does not declare, or a token the SDK does not define — both named
            together, on the ``defaults`` message's discipline. The empty
            mapping is the positive assertion that no parameter of this class
            is bounded by a capability, and it is hash-transparent at that
            value (``D-IMPL-243``), which is what every contract written before
            this field said and still says.
    """

    schema_name: str
    schema_version: str
    arguments: SkillArgumentSchema
    unsupported_arguments: Mapping[str, str] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    defaults: Mapping[str, Any] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    capability_bindings: Mapping[str, str] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @model_validator(mode="after")
    def _every_capability_binding_names_a_parameter_and_a_token(
        self,
    ) -> "ProductRequestContract":
        """Refuse a binding onto an undeclared parameter or an unknown token.

        Two ways a binding is not one (``24.6-L-07``; ``D-IMPL-253`` Q21),
        named together for the reason the defaults message names three
        together. The token vocabulary is read from
        :mod:`ccf.products.constraints` through a function-local import — the
        :func:`~ccf.products.payload.refuse_payload` precedent above — because
        that module imports this one, and one reading of *what a capability
        token is* is what keeps a declaration and a resolution from disagreeing
        about it.
        """
        if not self.capability_bindings:
            return self

        from ccf.products.constraints import _CAPABILITY_TOKENS

        undeclared = sorted(
            name
            for name in self.capability_bindings
            if name not in self.arguments.properties
        )
        unknown = sorted(
            {
                token
                for token in self.capability_bindings.values()
                if token not in _CAPABILITY_TOKENS
            }
        )
        if not (undeclared or unknown):
            return self
        raise ValueError(
            f"the request contract for {self.schema_name!r} at class lane "
            f"{self.schema_version!r} declares capability bindings it cannot "
            f"honor: {undeclared} are not declared arguments and {unknown} are "
            f"not capability tokens this SDK defines "
            f"({sorted(_CAPABILITY_TOKENS)}); a binding onto a parameter the "
            "class does not declare bounds nothing, and a binding onto a token "
            "no backend can supply is a wiring failure the resolver would meet "
            "at request time instead (24.6-L-07, D-IMPL-253 Q21)"
        )

    @model_validator(mode="after")
    def _every_default_is_a_parameter_this_class_honors(
        self,
    ) -> "ProductRequestContract":
        """Refuse a default the class cannot honor, naming every offender at once.

        Three ways a declared default is not one, checked together
        (``24.6-L-07``): a name the class never declared, a name the class
        declares and **always refuses**, and a value the declared argument's
        own type would reject. An author fixing a declaration one exception at
        a time is the papercut :meth:`from_declared` already exists to close,
        so the exhaustive message is the behavior here too and not a nicety.

        The type check is :func:`~ccf.products.payload.refuse_payload` over
        ``arguments`` narrowed to the one name, never a second reading of
        "conforms": one function decides what a declared parameter accepts, so
        a default and a caller's value cannot be judged by two rules. The name
        is bound at call time for the same ``DEF-17-02`` reason
        :func:`refuse_request` binds it there.
        """
        if not self.defaults:
            return self

        from ccf.products.payload import refuse_payload

        undeclared = sorted(
            name for name in self.defaults if name not in self.arguments.properties
        )
        inert = sorted(
            name for name in self.defaults if name in self.unsupported_arguments
        )
        mistyped = sorted(
            name
            for name in self.defaults
            if name not in undeclared
            and name not in inert
            and refuse_payload(
                payload={name: self.defaults[name]},
                declared=SkillArgumentSchema(
                    properties={name: self.arguments.properties[name]},
                    required=(),
                ),
            )
            is not None
        )
        if not (undeclared or inert or mistyped):
            return self
        raise ValueError(
            f"the request contract for {self.schema_name!r} at class lane "
            f"{self.schema_version!r} declares defaults it cannot honor: "
            f"{undeclared} are not declared arguments, {inert} are declared "
            f"and always refused, and {mistyped} do not satisfy the declared "
            "argument's own type; every offender is named here rather than one "
            "per exception, so the document is fixed in one pass — a default "
            "for a parameter the class does not honor would widen the closed "
            "request world by omission (24.6-L-07, D-IMPL-98, D-IMPL-253 Q2)"
        )

    @classmethod
    def from_declared(cls, artifact: DeclaredArtifact) -> ProductRequestContract:
        """Read a request contract out of the envelope a manifest returns.

        SDK-defined per CLAUDE.md §11: ``D-IMPL-126`` item (1) (Dave,
        2026-08-13). A deployment's request contract is authored in an adopter
        namespace — ``fibo-kyc.request-contract``, not ``ccf.`` — so a manifest
        resolves it to a
        :class:`~ccf.controlplane.artifacts.DeclaredArtifact` and every adopter
        was left hand-building the four fields out of ``.declaration``. One
        named call replaces the transcription; the transcription is not wrong,
        it is just something nobody should have to copy.

        **This is a constructor, not a validator.** It performs no pin check
        and claims none: :func:`refuse_request_contract_pin` and
        :func:`~ccf.products.contract.register_product_class` remain the
        comparisons that catch a contract pinned onto the wrong class or the
        wrong lane, exactly as they were for the hand-build this replaces. A
        reader must not mistake reaching a typed model for having governed it.

        **Two other shapes were offered and neither was taken. Recorded here so
        a later reader does not re-propose them as oversights.**

        *Not taken: teaching the manifest loader to parse* ``class_id:
        *.request-contract`` *into this type.* Three reasons, in order of
        weight. A suffix pattern over ``class_id`` would have the SDK claim
        ``*.request-contract`` across **every adopter namespace**, where
        ``D-IMPL-84`` draws the SDK's ownership line at exactly one prefix,
        ``ccf.``, and :mod:`ccf.deployment.classes`'s module docstring records
        that the earlier wider reading *"was too wide"*. It is a silent
        behavioural break with no version lane: a committed manifest naming
        ``acme.request-contract`` resolves to a ``DeclaredArtifact`` today and
        would resolve to this class tomorrow, changing what registers, what
        pins, and what enters replay dimension 2. And
        :func:`~ccf.deployment.classes.resolve_artifact_class` is a total
        function with three exhaustive branches and no pattern matching; a
        fourth branch keyed on adopter namespace *text* is the shape CINV-01
        exists to keep out of ``src/``.

        *Not taken: registering* :data:`PRODUCT_REQUEST_CONTRACT` *in*
        :data:`~ccf.deployment.classes.SDK_VERSIONED_ARTIFACT_CLASSES` *so a
        manifest could name* ``class_id: ccf.product-request-contract``. The
        reasons are already committed at that constant's own definition below —
        the first mapping is the set ``GET /schema`` and ``ccf schema export``
        enumerate, and the second is closed to a contract declaring no
        ``artifact_version``. It remains **available to a later ruling**; it is
        not an oversight.

        **Why a plain ``ValueError`` and not**
        :class:`~ccf.controlplane.artifacts.ArtifactLoadError`. That name lives
        in the module this one cannot import (see the ``TYPE_CHECKING`` block
        at the head of this file), so reusing it would cost a function-local
        import for nothing but a name — and a malformed declaration is a bad
        *argument to this call*, which is what ``ValueError`` already says.

        Args:
            artifact: The envelope a manifest resolved. Its ``semver`` is the
                **document's own lane** — how this declaration evolved — which
                is not the product class's lane carried in
                ``declaration["schema_version"]``. Two lanes, two things
                versioned (D-IMPL-98).

        Returns:
            The typed contract, equal field-for-field to the hand-build it
            replaces. ``tests/products/test_request_contract.py`` asserts that
            equality against the committed
            ``examples/s1-01-hello-context-product/artifacts/request-contract.yaml``
            rather than against an inline copy of it.

        **The optional fourth key** (``24.5-L-13``). ``unsupported_arguments``
        is read when present and defaults to the empty mapping when absent, so
        a declaration written before the key existed parses exactly as it did.
        The four ladder configs already carried the key as an uninterpreted
        sibling — the SDK reading it is the change, not the artifacts.

        **The optional fifth key** (``24.6-L-07``). ``defaults`` is read on
        exactly the same terms, and for the same reason: a declaration written
        before it existed parses unchanged, and the empty mapping it lands at
        is the positive assertion that the class declares no default rather
        than a value nobody chose.

        **The optional sixth key** (``24.6-L-07``, ``D-IMPL-253`` Q21).
        ``capability_bindings`` is read on the same terms again: absent means
        no parameter of this class is bounded by a technical capability, which
        is what every declaration written before the key said.

        Raises:
            ValueError: the declaration is missing one or more of the three
                required keys, **named together in one message**. An adopter
                fixing a declaration one ``KeyError`` at a time is the papercut
                this method exists to close, so the exhaustive message is the
                behaviour and not a nicety. Also raised, in the same one-error
                    shape, when ``unsupported_arguments`` is present but is not a
                mapping of parameter name to reason prose, and when
                ``defaults`` is present but is not a mapping keyed by parameter
                name, and when ``capability_bindings`` is present but is not a
                mapping of parameter name to capability token. A default naming
                a parameter the class does not honor, and a binding naming a
                parameter or a token the class cannot honor, are refused by the
                contract's own validators rather than here — each in one
                message naming every offender.
        """
        declaration = artifact.declaration
        missing = tuple(
            key for key in _DECLARATION_KEYS if key not in declaration
        )
        if missing:
            raise ValueError(
                f"the declared artifact {artifact.class_id!r} at lane "
                f"{artifact.semver!r} is missing "
                f"{list(missing)} and cannot be read as a request contract; a "
                f"request contract declares {list(_DECLARATION_KEYS)} — every "
                "missing key is named here rather than one per exception, so "
                "the document is fixed in one pass (D-IMPL-98, D-IMPL-126)"
            )
        unsupported = declaration.get(_KEY_UNSUPPORTED_ARGUMENTS, {})
        if not isinstance(unsupported, Mapping) or not all(
            isinstance(name, str) and isinstance(reason, str)
            for name, reason in unsupported.items()
        ):
            raise ValueError(
                f"the declared artifact {artifact.class_id!r} at lane "
                f"{artifact.semver!r} carries {_KEY_UNSUPPORTED_ARGUMENTS!r} "
                f"as {type(unsupported).__name__}, and it must be a mapping "
                "of parameter name to the declared reason prose — the shape "
                "the four ladder configs already author (Standard §2.4, "
                "24.5-L-13)"
            )
        defaults = declaration.get(_KEY_DEFAULTS, {})
        if not isinstance(defaults, Mapping) or not all(
            isinstance(name, str) for name in defaults
        ):
            raise ValueError(
                f"the declared artifact {artifact.class_id!r} at lane "
                f"{artifact.semver!r} carries {_KEY_DEFAULTS!r} as "
                f"{type(defaults).__name__}, and it must be a mapping of "
                "parameter name to the value the class takes when the caller "
                "omits that parameter (24.6-L-07, D-IMPL-253 Q2)"
            )
        bindings = declaration.get(_KEY_CAPABILITY_BINDINGS, {})
        if not isinstance(bindings, Mapping) or not all(
            isinstance(name, str) and isinstance(token, str)
            for name, token in bindings.items()
        ):
            raise ValueError(
                f"the declared artifact {artifact.class_id!r} at lane "
                f"{artifact.semver!r} carries {_KEY_CAPABILITY_BINDINGS!r} as "
                f"{type(bindings).__name__}, and it must be a mapping of "
                "parameter name to the capability token that bounds it — the "
                "token names WHICH capability applies and never its value "
                "(24.6-L-07, D-IMPL-253 Q21)"
            )
        return cls(
            semver=artifact.semver,
            schema_name=declaration[_KEY_SCHEMA_NAME],
            schema_version=declaration[_KEY_SCHEMA_VERSION],
            arguments=SkillArgumentSchema.model_validate(
                declaration[_KEY_ARGUMENTS]
            ),
            unsupported_arguments=dict(unsupported),
            defaults=dict(defaults),
            capability_bindings=dict(bindings),
        )


_KEY_SCHEMA_NAME = "schema_name"
_KEY_SCHEMA_VERSION = "schema_version"
_KEY_ARGUMENTS = "arguments"
#: The optional fourth declaration key (``24.5-L-13``). A key NAME of the
#: artifact, like the three above — not a parameter set. Nothing in this module
#: names a parameter; the parameters a class refuses are read from the artifact
#: at :meth:`ProductRequestContract.from_declared` and nowhere else.
_KEY_UNSUPPORTED_ARGUMENTS = "unsupported_arguments"

#: The optional fifth declaration key (``24.6-L-07``, ``D-IMPL-253`` Q2). A key
#: NAME of the artifact, like the four above — not a parameter and not a value.
#: Nothing in this module names a parameter or carries a default; what a class
#: takes when a caller omits something is read from the artifact at
#: :meth:`ProductRequestContract.from_declared` and nowhere else (CINV-01).
_KEY_DEFAULTS = "defaults"

#: The optional sixth declaration key (``24.6-L-07``, ``D-IMPL-253`` Q21). A
#: key NAME again, and the value under it is a *capability token* — which
#: capability bounds a parameter — never the bound. The number a backend can
#: technically do is the backend's, read off it at resolution time; a ceiling
#: authored in an artifact would be a technical bound nobody measured
#: (CINV-01).
_KEY_CAPABILITY_BINDINGS = "capability_bindings"

#: The three keys a request-contract declaration carries, in the order
#: :meth:`ProductRequestContract.from_declared` reports them missing. They are
#: this class's own field names rather than a second vocabulary — the envelope
#: is open, so the mapping from declaration key to field is the one thing that
#: could drift, and naming it once is what keeps it from drifting silently.
_DECLARATION_KEYS = (_KEY_SCHEMA_NAME, _KEY_SCHEMA_VERSION, _KEY_ARGUMENTS)


#: The artifact class the registry validates request contracts against.
#:
#: In **neither** :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` nor
#: :data:`~ccf.deployment.classes.SDK_VERSIONED_ARTIFACT_CLASSES`, deliberately
#: and on the placement plan ``15.5-03`` established for
#: ``ccf.product-entitlement-policy``. The first mapping *is* the set the HTTP
#: ``GET /schema`` route and the ``ccf schema export`` verb enumerate, and
#: widening it here would be an unruled runtime surface change made
#: incidentally; the second is closed to a contract that declares no
#: ``artifact_version``, which this one does not. The class still gets a
#: committed ``docs/schemas/`` document, because ``tools/dump_schemas.py``
#: *discovers* :class:`~ccf.controlplane.artifact_base.ArtifactClass` instances
#: in neither mapping rather than reading a list. Registration is adopter code:
#: a deployment registers its contracts against this constant at wiring time,
#: exactly as it registers its entitlement policy.
PRODUCT_REQUEST_CONTRACT = ArtifactClass(
    class_id="ccf.product-request-contract", contract=ProductRequestContract
)


class ProductRequestViolation(CCFContract):
    """A request does not match the contract its product class declared.

    Deliberately **not** a
    :class:`~ccf.products.payload.PayloadSchemaViolation`, and for the reason
    that type is not a :class:`~ccf.products.gates.GateRefusal`: the comparison
    beneath the two is shared on purpose, and if the verdict type were shared
    with it a request refusal could be returned from the payload path by a
    later caller who assumed the type meant it belonged there. One reading of
    "conforms", two verdicts that cannot be confused.

    **The refusal is a returned value, not an exception** — the posture
    :mod:`ccf.products.gates` states at its own head: a refusal returned as
    data cannot be swallowed by a bare ``except``. A malformed request is a bad
    **question**, not a broken deployment, and this tree reports those
    differently. The pin refusal below is the other case and does raise.

    Both sides travel, in the
    :class:`~ccf.products.gates.AttestationRefusal` voice, so a caller never
    re-derives either to learn what the gap was.

    Attributes:
        reason: Which of the six ways the request missed.
        key: Where. A parameter reads by name, a nested member reads
            ``parent.member`` and an element of a declared list reads
            ``parent[].member``; a class mismatch reads the field that
            disagreed; a tier refusal reads the inert parameter's name; a
            proportion refusal reads the tolerance parameter's name.
        declared_type: The JSON Schema type declared at ``key`` — or, for a
            class mismatch, the value the **contract** declares. ``None`` when
            neither applies, which includes a tier refusal: an inert parameter
            is refused whatever its type, so no type is what the declaration
            says about it. A proportion refusal carries the declared type
            (the value was well-typed; it was its magnitude that missed).
        presented_type: The Python type name the request presented at ``key``
            — or, for a class mismatch, the value the **request** presented.
        declared_keys: Every parameter the contract declares at the level the
            violation occurred, so an undeclared parameter is readable against
            the set it was not in. Empty for a class mismatch, which is not
            about a level.
        presented_keys: Every parameter the request presented at that level.
        detail: The human-readable statement, for the operator reading a log.
            The typed fields above are the machine-readable version. For a
            tier refusal it carries the Standard's status token, the parameter
            name and the declared reason prose, all three, so a reader of the
            sentence sees what the declaration said. For a proportion refusal
            it carries the parameter name, the presented value and the
            interval, so a caller reads which number missed and what it had
            to be.
    """

    reason: ProductRequestViolationReason
    key: str
    declared_type: str | None
    presented_type: str | None
    declared_keys: frozenset[str]
    presented_keys: frozenset[str]
    detail: str


class AnchorAmbiguityRefusal(CCFContract):
    """The request's anchor resolves to more than one entity (``24.5-L-16``).

    SDK-defined (CLAUDE.md §11: *refusal is data*). Whitepaper §6.3
    **Addressability** (``docs/CCF_Whitepaper_1-2.md:1465``) makes the entity
    anchor the ``{id}`` slot of the address — *which entity* the question is
    about — and a slot that answers with two entities has not addressed one.
    The ladder met the case at cp-04 (``24.4`` deferred item 14, ``D-IMPL-234``
    (d)): a shared LEI made the anchor row-order dependent, and there was no
    kind to say so, so a product could only serve the wrong one silently.

    **The SDK ships the kind and no resolver.** Which anchor is ambiguous is a
    fact about the deployment's identifiers and its resolution rules, and
    what a product does about it — answer ``404`` (Standard §9, *anchor
    unresolvable*), refuse with this value, or serve one candidate with a
    finding — is the product's ruling. Nothing here decides it; this type
    only lets the decision be a typed, auditable value rather than an
    exception's prose.

    **Pre-assembly.** An anchor resolves before the graph is touched, so this
    kind is in :data:`~ccf.products.refusal._PRE_ASSEMBLY_REFUSALS` beside
    :class:`ProductRequestViolation`, and
    :func:`~ccf.products.refusal.envelope_for` refuses a lineage offered
    with it for the same reason.

    Attributes:
        anchor: What was asked — the request's ``subject``, as presented.
        candidates: The entity URIs that answered to it. More than one, which
            is the whole of what makes this a refusal; carried so a consumer
            can see the collision rather than be told of it.
        detail: The human-readable statement, for an operator reading a log.
    """

    anchor: str
    candidates: frozenset[str]
    detail: str


def _translate(violation: PayloadSchemaViolation) -> ProductRequestViolation:
    """Speak one shared verdict in the request surface's own words.

    A translation and nothing more: every field travels across unchanged except
    ``reason``, which is renamed through :data:`_REASONS`, and ``detail``,
    which is re-voiced because a caller who sent a request should not be told
    about a payload. Nothing is recomputed here — recomputing would be the
    second reading of "conforms" this whole arrangement exists to prevent.
    """
    reason = _REASONS[violation.reason]
    return ProductRequestViolation(
        reason=reason,
        key=violation.key,
        declared_type=violation.declared_type,
        presented_type=violation.presented_type,
        declared_keys=violation.declared_keys,
        presented_keys=violation.presented_keys,
        detail=(
            f"request parameter {violation.key!r}: {reason} — the product"
            " class's declared request contract declares"
            f" {sorted(violation.declared_keys)} at this level and the request"
            f" presents {sorted(violation.presented_keys)}"
            f" (declared {violation.declared_type!r}, presented"
            f" {violation.presented_type!r}); the declared world is closed"
            " (D-IMPL-98, D-IMPL-103)"
        ),
    )


def _refuse_address(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """Is this request even addressed to this contract?

    Checked **before** the parameters, because comparing a request's arguments
    against another class's declaration produces a confident verdict about the
    wrong question — the most misleading answer this function could give.
    """
    for field, presented, expected in (
        ("schema_name", request.schema_name, declared.schema_name),
        ("schema_version", request.schema_version, declared.schema_version),
    ):
        if presented == expected:
            continue
        return ProductRequestViolation(
            reason="class-mismatch",
            key=field,
            declared_type=expected,
            presented_type=presented,
            declared_keys=frozenset(),
            presented_keys=frozenset(),
            detail=(
                f"this request is addressed to {field} {presented!r} and the"
                f" contract it was compared against declares {expected!r}; a"
                " request contract is the request surface of one product class"
                " at one lane (D-IMPL-98, INV-CH7-49)"
            ),
        )
    return None


def _refuse_tier(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """Does this request present a parameter the class declared and always refuses?

    The tier step (``24.5-L-13``): the first presented parameter, in sorted
    order, that the declaration names in
    :attr:`ProductRequestContract.unsupported_arguments` is refused by
    ``not-supported-at-tier``, carrying the declaration's own reason prose.
    The verdict comes **from the declaration**: this function holds no
    parameter name and no reason text of its own.
    """
    for key in sorted(request.parameters):
        if key not in declared.unsupported_arguments:
            continue
        return ProductRequestViolation(
            reason="not-supported-at-tier",
            key=key,
            declared_type=None,
            presented_type=type(request.parameters[key]).__name__,
            declared_keys=frozenset(declared.arguments.properties),
            presented_keys=frozenset(request.parameters),
            detail=(
                f"{key}: 400 not_supported_at_tier — "
                f"{declared.unsupported_arguments[key]}"
            ),
        )
    return None


def _refuse_tolerance(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """Is the presented ``debt_tolerance`` a proportion?

    The interval step (WR-02). Runs LAST, after the payload comparison has
    said the parameter is declared, honored and well-typed, so this function
    only ever judges a number's magnitude: ``bool`` (an ``int`` to Python,
    not to the contract) and non-numbers are the payload comparison's to
    name, and a parameter the declaration does not carry never reaches here.
    The interval ``[0, 1]`` is the one the class's own declared default is
    held to (:class:`~ccf.products.contract.ServeObligations`, ``24.5-L-14``,
    ``24.6-L-04``); the parameter NAME is the SDK's mechanism vocabulary
    (:data:`~ccf.products.gates.DEBT_TOLERANCE_PARAMETER`); the number is the
    caller's. Nothing the class declared is read here, and this step needs
    nothing from it: a value that is not a proportion is not a tolerance under
    any class.
    """
    # Imported at call time for the same DEF-17-02 reason `refuse_payload` is:
    # `ccf.products.gates` reaches `ccf.products.contract`, which is on the
    # path back to this module through the replay record. One name, needed
    # once the comparison runs and never before.
    from ccf.products.gates import DEBT_TOLERANCE_PARAMETER

    key = DEBT_TOLERANCE_PARAMETER
    if key not in request.parameters:
        return None
    presented = request.parameters[key]
    if isinstance(presented, bool) or not isinstance(presented, (int, Decimal)):
        return None
    value = Decimal(presented)
    if value.is_finite() and Decimal(0) <= value <= Decimal(1):
        return None
    property_ = declared.arguments.properties.get(key)
    return ProductRequestViolation(
        reason="not-a-proportion",
        key=key,
        declared_type=None if property_ is None else property_.type,
        presented_type=type(presented).__name__,
        declared_keys=frozenset(declared.arguments.properties),
        presented_keys=frozenset(request.parameters),
        detail=(
            f"{key}: {presented} is not a proportion — D_c is a proportion "
            "(whitepaper §7.7.4), so a tolerance must lie in [0, 1]; the "
            "class's declared default is held to the same interval at "
            "declaration (24.5-L-14, 24.6-L-04), and a caller states a "
            "tolerance or none, never a number that is not a tolerance at all"
        ),
    )


def refuse_request(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """The one request-conformity comparison — address, then tier, then parameters, then the tolerance interval.

    **The order is fixed and load-bearing** (``24.5-L-13``): address first,
    the tier step second, the payload comparison third, the interval step
    last. A declared-and-inert
    parameter is refused whatever its type, and it is typically *not* in
    ``arguments.properties`` — so the payload comparison, run first, would
    call it ``undeclared-parameter`` and hide the reason the declaration
    authored. The tier step runs before that comparison so the declared reason
    is what a caller reads. The address check stays first for the reason
    :func:`_refuse_address` gives: a request to another class never reaches
    the tier step, so a tier verdict is always about this class's declaration.
    The interval step (:func:`_refuse_tolerance`, WR-02) runs after the
    payload comparison for the converse reason: it judges a number's
    magnitude, and only a declared, honored, well-typed number has one.

    **Called by the deployment's own resolver, not by any door**
    (``D-IMPL-121``, Dave, 2026-08-12, extending ``D-IMPL-113``). This
    docstring previously claimed it was *called by the door*; the seam that
    can carry a typed request has existed since plan ``15.5-15``
    (``D-IMPL-108``) and no shipped door calls this function, so the claim was
    false as written and is corrected here rather than left to rot. The join
    point is the resolver behind
    :class:`~ccf_runtime.mcp.egress.ProductResolverProtocol` and
    :class:`~ccf_runtime.mcp.experience.ExperienceProductResolverProtocol`,
    whose docstrings state what a resolver omitting this call serves and why
    the door cannot make it: the door never holds the
    :class:`~ccf.products.contract.RegisteredProductClass` this comparison
    needs. ``examples/s1-01-hello-context-product/spine.py::assemble_and_serve``
    is the shipped worked example.

    Also called by any registration-time capability check that needs to know
    what a class accepts. One function, so the two
    cannot drift into two readings of "well-formed" — the reason
    :func:`~ccf.products.gates.refuse_attestation` is one function and the
    reason this one delegates its parameter comparison to
    :func:`~ccf.products.payload.refuse_payload` rather than restating it.

    Pure over its arguments: no clock, no registry lookup, no I/O. A verdict
    that moved with the time of day or with what was registered elsewhere would
    not be reproducible at replay, which is the property every comparison in
    this package is required to have — and the instant is a *field of the
    request* precisely so that this stays true (see the module docstring).

    Returns:
        ``None`` when the request is addressed to this contract, presents no
        parameter the contract declares inert, matches its declared
        parameters at every level, and presents no tolerance outside the unit
        interval; otherwise the
        :class:`ProductRequestViolation` naming the first failure — address
        first, then the tier step over sorted presented names, then the fixed
        undeclared-then-missing-then-mistyped order
        :func:`~ccf.products.payload.refuse_payload` imposes over sorted names,
        then the interval step — carrying both sides of the comparison that
        failed.
    """
    # Imported at call time, not at module scope (DEF-17-02). `ccf.products.
    # payload` reaches `ccf.skills.catalog` at its own top, and that reaches
    # `ccf.agents.agent` → `ccf.replay.record` → *this* module: a module-scope
    # edge from here back to `payload` therefore closed a cycle that made
    # `import ccf.products.payload` fail whenever it was the first import into
    # the tree. The comparison is needed once this function runs and never
    # before, so binding the name here removes the edge outright rather than
    # ordering around it. The annotation-only half lives under TYPE_CHECKING at
    # the head of this module.
    from ccf.products.payload import refuse_payload

    address = _refuse_address(request=request, declared=declared)
    if address is not None:
        return address
    tier = _refuse_tier(request=request, declared=declared)
    if tier is not None:
        return tier
    parameters = refuse_payload(
        payload=request.parameters, declared=declared.arguments
    )
    if parameters is not None:
        return _translate(parameters)
    return _refuse_tolerance(request=request, declared=declared)


def request_seeds(request: ProductRequest | None) -> frozenset[str] | None:
    """The walk starting points a question implies — its subject, and nothing else.

    D-IMPL-111 limb (a) (Dave, 2026-08-11): *the request seeds the traversal*.
    The entity anchor of the whitepaper's address pattern
    (``/context-products/…/{counterparty-id}?intent=…&freshness=…``,
    ``docs/CCF_Whitepaper_1-2.md:1465``) is *which entity the question is
    about*, so it is where a walk asked to answer that question begins. Before
    this function existed the anchor entered only at Π, and two questions about
    two different companies compiled to the **same** graph query and pinned
    identically in replay dimension 5 — measured, reported and ruled on as
    ``DI-15.5-07``.

    **One reading, used on both paths, and that is the whole reason this is a
    function rather than a set literal at two call sites.** The serving path
    derives the seeds from the request it was handed; the replay path derives
    them from the request the record carries
    (:attr:`~ccf.replay.record.ContentGenerationPath.request`). Two derivations
    could drift, and a drift here would replay a *different question* under the
    original decision's identifier — the failure
    :func:`~ccf.products.request.refuse_request` avoids on the door's side by
    delegating rather than restating.

    A deployment is free to pass
    :meth:`~ccf.projection.engine.ProjectionEngine.execute` some other seed set,
    or none: the parameter is optional and the SDK imposes no walk. What it does
    not get is silence — the seeds are inside every issued
    :class:`~ccf.graph.protocols.GraphQuery` and therefore inside the pins
    dimension 5 records, so a serve path that seeded by another rule diverges
    **loudly** at replay (``ReplayDivergence``) instead of quietly reproducing a
    question the decision never asked.

    Pure over its argument: no clock, no registry, no I/O, exactly as
    :func:`refuse_request` is and for the same replay reason.

    Returns:
        The single-element set naming the request's subject, or ``None`` when
        there is no request — the positive "this decision named no anchor"
        value, which is also what every pre-D-IMPL-111 record replays under.
    """
    if request is None:
        return None
    return frozenset({request.subject})


def refuse_request_contract_pin(
    *,
    registry: ControlPlaneProtocol,
    schema_name: str,
    schema_version: str,
    request_contract_key: str,
    request_contract_version: str,
) -> None:
    """Raise unless a class's request-contract pin resolves to its own contract.

    The registration-time half, in the ``MAX_TTL`` voice and for the ``MAX_TTL``
    reason (D-IMPL-39, applied here to D-IMPL-98): a deployment that pinned a
    contract that is not there — or pinned another class's — finds out **while
    wiring the fabric**, rather than in front of a caller whose question it can
    no longer answer. Raised, never returned or warned, naming both sides,
    exactly as ``ccf.products.contract``'s payload-schema pin refusal is.

    Four refusals, and the last has no payload-schema analogue: a
    :class:`~ccf.skills.catalog.SkillArgumentSchema` names no class, so a
    payload schema pinned onto the wrong product class is undetectable. A
    :class:`ProductRequestContract` names the class and the lane it serves, so
    that mis-wiring is caught here.

    Raises:
        ProductClassRegistrationError: the pin is half-declared; or it names
            nothing registered; or it names an artifact that is not a request
            contract; or it names a contract declared for another product class
            or another lane. The shipped registration error type is reused
            rather than a new one added, because a class whose governance
            configuration is absent or malformed fails for one reason from the
            adopter's point of view.
    """
    declared_key = request_contract_key != NO_REQUEST_CONTRACT
    declared_version = request_contract_version != NO_REQUEST_CONTRACT
    if declared_key != declared_version:
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares half a request-contract "
            f"pin: key={request_contract_key!r}, version="
            f"{request_contract_version!r}. A contract is pinned by (key, "
            "version) so that the surface a question was validated against is "
            f"re-resolvable years later; either both are "
            f"{NO_REQUEST_CONTRACT!r} or neither is (D-IMPL-98, D-IMPL-26)"
        )
    if not declared_key:
        return
    try:
        artifact = registry.resolve(
            request_contract_key, request_contract_version
        )
    except ControlPlaneMissing as missing:
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares its request contract at "
            f"({request_contract_key!r}, {request_contract_version!r}), which "
            "is not registered; a declared contract is resolved at "
            "registration so that a deployment which pinned a contract that is "
            "not there finds out while wiring the fabric rather than when a "
            "caller asks (D-IMPL-98)"
        ) from missing
    if not isinstance(artifact, ProductRequestContract):
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} declares its request contract at "
            f"({request_contract_key!r}, {request_contract_version!r}), which "
            f"holds {type(artifact).__name__}, not a request contract "
            f"({ProductRequestContract.__name__})"
        )
    if (artifact.schema_name, artifact.schema_version) != (
        schema_name,
        schema_version,
    ):
        raise ProductClassRegistrationError(
            f"product class {schema_name!r} at lane {schema_version!r} declares "
            f"its request contract at ({request_contract_key!r}, "
            f"{request_contract_version!r}), which is the request surface of "
            f"{artifact.schema_name!r} at lane {artifact.schema_version!r}; a "
            "request contract names the class it serves so that a pin onto the "
            "wrong class is refused at wiring time rather than validating one "
            "class's questions against another's declaration (D-IMPL-98)"
        )


# Imported at the bottom, deliberately (D-IMPL-56, as applied by
# `ccf.skills.catalog` for the same class of cycle). `ccf.skills.catalog`
# reaches `ccf.agents.agent`, which reads `NO_GRANTS_SET_HASH` and
# `PerspectiveConditioning` out of `ccf.replay.record` — and since D-IMPL-111
# limb (b) that module names :class:`ProductRequest` in dimension 5. By the
# time this line runs every name the replay plane needs from *this* module
# already exists, so the cycle closes safely in both import orders; the
# deferred annotation above is then resolved explicitly.
#
# :class:`SkillArgumentSchema` is a *field type* of
# :class:`ProductRequestContract`, so the rebuild below needs the class itself
# — TYPE_CHECKING cannot serve it and the deferral has to stay.
from ccf.skills.catalog import SkillArgumentSchema  # noqa: E402

ProductRequestContract.model_rebuild()
