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
from datetime import datetime, timedelta
import re
from decimal import Decimal
from typing import Final, TYPE_CHECKING, Any, Literal

from pydantic import Field, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
from ccf.controlplane.artifact_base import ArtifactClass, VersionedArtifact
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.products.provenance import OverrideRecord
from ccf.products.contract import (
    NO_REQUEST_CONTRACT,
    NOT_DISCOVERABLE,
    ProductClassRegistrationError,
    ProductDiscovery,
    ServeObligations,
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
    "ArgumentDomain",
    "NO_REQUEST_CONTRACT",
    "PRODUCT_REQUEST_CONTRACT",
    "AnchorAmbiguityRefusal",
    "ProductRequest",
    "ProductRequestContract",
    "ProductRequestViolation",
    "ProductRequestViolationReason",
    "RelativeDefault",
    "refuse_intent",
    "decode_declared_request",
    "refuse_request",
    "refuse_request_contract_pin",
    "refuse_undeclared_class_default",
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
#: The same token, at ``key="intent"``, is the verdict of :func:`refuse_intent`
#: (``D-IMPL-264`` D-01): §6.3 makes intent an addressing token, and a class
#: not registered to serve the intent is addressed to the wrong class in the
#: same family as a lane mismatch. No tenth token was added for it — the
#: vocabulary is fixed at nine (criterion 7) and ``key`` already reads *the
#: field that disagreed* for this reason.
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
#:
#: The seventh and eighth, ``below-minimum`` and ``above-maximum``, are the
#: two ends of a numeric :class:`ArgumentDomain` (``D-IMPL-259``). The ninth,
#: ``not-in-domain``, is the enumerated shape's one verdict (``D-IMPL-264``
#: D-05, Dave: *"Wrong type and valid type/wrong value are materially
#: different failures. The presented value can be named; disclosure controls
#: whether the allowed set is exposed."*): a well-typed value that is not a
#: member of the class's declared set. A wrong-typed value is still
#: ``type-mismatch`` — the payload comparison runs first and this verdict
#: never reaches it. Appended last, never inserted, so every older record's
#: reason meets the same roster prefix.
ProductRequestViolationReason = Literal[
    "undeclared-parameter",
    "missing-required-parameter",
    "type-mismatch",
    "class-mismatch",
    "not-supported-at-tier",
    "not-a-proportion",
    "below-minimum",
    "above-maximum",
    "not-in-domain",
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
            way the resolution goes: on the recorded
            :class:`~ccf.products.provenance.EffectiveRequest` when the request
            RESOLVES, and on the refusal's own ``overrides`` member — carried
            into the record's internal envelope — when the resolution REFUSES
            (``D-IMPL-260`` P-I, criterion 10: *"the refusal path must preserve
            the attempted override and the entitlement result in replay"*).

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


class ArgumentDomain(CCFContract):
    """The valid domain of one declared parameter — the seventh key.

    **SDK-defined** (CLAUDE.md §11); the rulings of record are ``D-IMPL-259``
    (Dave, 2026-09-05): *"cp-04 ``max_depth`` has a declared request-contract
    minimum of 1 … Requests below 1 … are governed request-validity refusals
    returned as data; values 1–100 are valid and are never clamped."* And the
    scoping sentence that puts the type HERE rather than in the constraint
    layer: *"don't turn ``1`` into a Policy Constraint. It is simply the
    parameter's valid domain."* — and ``D-IMPL-264`` (Dave, 2026-09-05,
    Q3/Q4/Q6), which gives the type its second shape. The whitepaper hook is
    §6.3 **Addressability** (``docs/CCF_Whitepaper_1-2.md:1465``): the
    request contract is the interface a caller queries by name, and a domain
    is part of what that interface declares.

    **What this is and is not.** A domain is part of the *request contract*
    — a statement of which values are meaningful questions of this class —
    in the same register as ``type`` and ``required``. It is not a policy
    constraint (no artifact pin, no priority, no comparability fold, no
    authority — ``ccf.products.constraints`` never reads it) and it is not a
    technical capability (no substrate, no identity — the number a backend
    can walk is read off the backend through ``capability_bindings``). Both of
    those bound a request *after* it is well-formed; a domain says what
    well-formed means for a value, so it is judged where ``type`` is judged,
    by :func:`refuse_request`, and a value outside it is a
    :class:`ProductRequestViolation` — ``below-minimum``, ``above-maximum``
    or ``not-in-domain`` — returned as data, never a substituted value.

    **Two shapes, exactly one of them** (``D-IMPL-264`` D-03, Dave: *"Exactly
    one domain shape: numeric bounds or enumerated values. Non-empty,
    duplicate-free … Neither shape is also invalid if ``ArgumentDomain`` is
    present."*):

    * **Numeric bounds** — ``minimum`` and/or ``maximum``, inclusive on both
      ends, because a boundary a caller may ask for and a boundary a caller
      may not are two different declarations and the shorter one to write is
      the one the ruling used (*"values 1–100 are valid"*). Either end may
      be absent.
    * **An enumerated member set** — ``members``, the closed set of legal
      values, over any supported primitive type (``D-IMPL-264`` D-06, Dave:
      *"Any supported primitive type, with homogeneous members matching the
      declared property type. Don't unnecessarily make this
      string-specific."*). Homogeneity is by CLASS — string, numeric
      (``int`` and :class:`~decimal.Decimal` together), boolean — and
      ``bool`` is its own class, never a number, on :func:`_as_decimal`'s
      reading.

    A domain declaring both shapes, neither shape, an empty set, a duplicated
    member or a heterogeneous set is refused at construction, naming the
    defect: a domain that admits everything, or that no value could satisfy,
    is not a declaration but a key with nothing under it.

    **Membership is exact typed equality** (``D-IMPL-264`` D-04, Dave,
    verbatim: *"Exact canonical match. No trimming, case folding, aliases, or
    silent substitution. Canonicalization, if ever wanted, should be an
    explicit mechanism upstream of domain validation."*). ``"AB"`` is not
    ``"ab"``, ``" ab"`` is not ``"ab"``, ``True`` is not ``1`` and ``"1"`` is
    not ``1``; within the numeric class ``Decimal("2")`` IS ``2``, because the
    contract reads a number by its value and not by its Python type. Nothing
    here trims, folds, aliases or substitutes — ``tests/products/
    test_request_contract.py`` plants each of those in turn and watches the
    membership tests red.

    Attributes:
        minimum: The smallest value a caller may ask for, or ``None`` when the
            numeric domain is unbounded below (or the domain is enumerated).
            Held as a :class:`~decimal.Decimal` for the reason
            :class:`~ccf.products.contract.ServeObligations` holds its
            tolerance as one: a float boundary that is not the number the
            author wrote is a boundary nobody declared.
        maximum: The largest, or ``None``. Declared rarely in practice — a
            ceiling a backend imposes is a capability, not a domain
            (``D-IMPL-253`` Q21) — but the type is symmetric so a genuine
            domain ceiling (*"a percentage"*, *"a calendar month"*) has a
            place to be declared rather than a policy to be faked.
        members: The closed set of legal values, or ``None`` when the domain
            is numeric. Hash-transparent at ``None`` (``D-IMPL-243``): every
            numeric domain written before the member set existed
            canonicalizes byte-for-byte as it did, so no committed request
            contract's content address moves. The schema render derives the
            advertised ``enum`` from this field (``D-IMPL-264`` D-00, P-1:
            *"the request contract is the authority for legal values; schemas
            and discovery advertise that authority but never independently
            define it"*), which is why the declaration is not itself named
            ``enum``.
    """

    minimum: Decimal | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    maximum: Decimal | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    members: tuple[str | int | bool | Decimal, ...] | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @model_validator(mode="after")
    def _at_least_one_end_and_in_order(self) -> "ArgumentDomain":
        """Refuse a domain that is not exactly one well-formed shape, by name.

        The name predates the second shape and is kept: the numeric half is
        still *at least one end, in order*; the enumerated half is *a
        non-empty, duplicate-free, homogeneous set*; and the shapes are
        exclusive (``D-IMPL-264`` D-03/D-06 beside ``D-IMPL-259``).
        """
        numeric = self.minimum is not None or self.maximum is not None
        if numeric and self.members is not None:
            raise ValueError(
                "an argument domain declares exactly one shape — numeric "
                "bounds (minimum and/or maximum) OR an enumerated member set "
                "(members) — and this one declares both; a value cannot be "
                "held to a magnitude and to a closed set at once "
                "(D-IMPL-264 D-03, D-IMPL-259)"
            )
        if not numeric and self.members is None:
            raise ValueError(
                "an argument domain declares a minimum, a maximum or both, or "
                "an enumerated member set; a domain with neither shape admits "
                "every value and is a key with nothing under it "
                "(D-IMPL-264 D-03, D-IMPL-259)"
            )
        if self.members is not None:
            _refuse_a_malformed_member_set(self.members)
            return self
        for name, value in (("minimum", self.minimum), ("maximum", self.maximum)):
            if value is not None and not value.is_finite():
                raise ValueError(
                    f"an argument domain's {name} must be a finite number, "
                    f"not {value} (D-IMPL-259)"
                )
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError(
                f"an argument domain's minimum {self.minimum} exceeds its "
                f"maximum {self.maximum}; no number satisfies it, so no request "
                "could ever be well-formed under it (D-IMPL-259)"
            )
        return self

    def refuses(self, value: object) -> ProductRequestViolationReason | None:
        """Which way ``value`` misses this domain, or ``None`` when it lies inside.

        Numeric shape: the value's magnitude against the declared ends
        (``below-minimum`` / ``above-maximum``); a value with no magnitude is
        not judged here — the payload comparison names it ``type-mismatch``
        first, and this step runs after (``24.5-L-13``). Enumerated shape:
        exact typed equality against the member set (``not-in-domain``), on
        the rule :func:`_is_member` states — the presented value's class must
        be the set's class and the value must equal a member under that
        class's own equality. *"No trimming, case folding, aliases, or silent
        substitution"* (``D-IMPL-264`` D-04).
        """
        if self.members is not None:
            if any(_is_member(value, member) for member in self.members):
                return None
            return "not-in-domain"
        number = _as_decimal(value)
        if number is None:
            return None
        if self.minimum is not None and number < self.minimum:
            return "below-minimum"
        if self.maximum is not None and number > self.maximum:
            return "above-maximum"
        return None


class RelativeDefault(CCFContract):
    """A default declared as an offset from the request's own ``asked_at``.

    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-325``
    (Dave, 2026-09-10), on the gap ``examples/cp-07-client-360-coverage-graph``
    measured as ``CP07-F-03``. The whitepaper hook is §6.3 **Addressability**
    (``docs/CCF_Whitepaper_1-2.md:1465``), the same one
    :class:`ArgumentDomain` attaches to: what a class takes when a caller
    omits a parameter is part of the interface the caller queries by name.

    **The defect it closes is a value that ages silently.**
    ``CP-SPEC-007`` §B.2 declares a ``since`` default of *minus 365 days*.
    :attr:`ProductRequestContract.defaults` holds literal values, so the
    artifact could only carry an absolute date — which on the day it is
    written means one window and a year later means another, with the fan-out
    growing and nothing anywhere saying the default drifted. The alternative
    an adopter reaches for next is worse: computing the date in deployment
    code puts a governance value back in the spine and gives the deployment a
    second authority for one bound, which is the shape ``D-IMPL-315`` exists
    to keep out.

    **What it is NOT.** It is not a rule the fabric carries forward. The
    resolution computes the value once, against the instant of the question,
    and what lands in the Decision Replay record is that **literal** under
    authority ``default`` with this contract's own pin — never the offset.
    Dave, verbatim: *"Replay records the resolved absolute value and
    ``authority=default``, not a rule that gets recomputed later."* A rule
    re-evaluated at replay time would make one decision answer differently on
    two days, which is exactly the determinism the five-dimension record
    exists to hold.

    **Why the offset is seconds and nothing friendlier** (``D-IMPL-325``
    ruling 2, Dave: *"Reuse the SDK's existing duration vocabulary. No
    ``days`` convenience field and no ISO-duration parser."*). A duration in
    an artifact is already spelled one way in this SDK —
    :attr:`~ccf.halflife.decay.HalfLifeEntry.half_life_seconds` — and a second
    spelling would be a second thing to keep in agreement, plus (for the ISO
    form) a parser and the failure mode that comes with one.

    Attributes:
        offset_seconds: How far from ``asked_at`` the default lies, in
            seconds. **Zero or negative**; a positive offset refuses at
            construction, because a default in the future describes no window
            a caller could have observed.

            **``0`` is the identity offset and means the request's own instant,
            unchanged** (``D-IMPL-328``). It is what *today* and *now* mean as
            defaults, and `ProductRequestContract.defaults` cannot express them
            — a literal date written there is a date that ages, which is the
            defect ``CP07-F-03`` measured. Zero resolves through this same
            branch against the same ``asked_at``, records the same authority
            and the same pin, and lands in replay as the same resolved literal.
        render: The form the resolved value takes — ``"date"`` for the
            calendar day, ``"timestamp"`` for the full instant. **Declared,
            never inferred** (``D-IMPL-325`` ruling 3, Dave: *"Do not infer
            semantics from JSON Schema ``type: string``."*). JSON Schema has
            no date type, so both forms arrive as ``string`` and an inferring
            reader would have one declared type meaning two things.
    """

    offset_seconds: int
    render: Literal["date", "timestamp"]

    @model_validator(mode="after")
    def _the_offset_does_not_reach_into_the_future(self) -> "RelativeDefault":
        """Refuse a POSITIVE offset. Zero is admitted, and means the instant itself.

        **``0`` was refused until ``D-IMPL-328`` and is now the identity
        offset.** The original reading was that a zero offset *"is not a
        relative window"* and belonged in :attr:`ProductRequestContract.defaults`
        as a literal. ``CP-SPEC-008`` measured that reading wrong from the other
        side: a bitemporal product's ``as_of`` and ``known_as_of`` default to
        *today* and *now*, which is precisely ``asked_at`` **unchanged** — and
        the literal surface cannot express it, because any date written there is
        a date that ages. The two available moves were to admit ``0`` or to let
        the deployment inject ``asked_at`` in code, and the second puts a
        governance value back in the spine (``D-IMPL-315``).

        **Zero is a relative default in every respect that matters.** It
        resolves through the same branch, against the same ``request.asked_at``,
        at the same point in the resolution; it records the same authority
        ``default`` with the same contract pin; and it lands in replay as the
        same resolved literal. What is recorded is the rendered instant, never
        the offset — so a decision replays against the day it was served, not
        against the day it is replayed. Nothing about it is a special case
        except the arithmetic being an identity.

        A **positive** offset is still refused, and for the reason that always
        applied: a default in the future is not a window over anything that has
        happened.
        """
        if self.offset_seconds <= 0:
            return self
        raise ValueError(
            f"a relative default declares offset_seconds={self.offset_seconds},"
            " and an offset may not be positive: a default reaches into what"
            " has already happened, or — at 0 — names the request's own instant"
            " unchanged. A future default describes no window a caller could"
            " have observed (D-IMPL-325, D-IMPL-328)"
        )

    def resolve(self, asked_at: datetime) -> str:
        """The literal this default means for a question asked at ``asked_at``.

        Pure and total over its argument, and it **reads no clock** — the
        instant is supplied, which is what lets replay feed the recorded
        boundary through this same code path and get the same string back.

        Args:
            asked_at: The decision instant, zone-aware. Supplied by the
                resolution from :attr:`ProductRequest.asked_at`; this method
                never observes one.

        Returns:
            The ISO-8601 rendering declared by :attr:`render` — the calendar
            day, or the full instant including its offset from UTC.
        """
        moment = asked_at + timedelta(seconds=self.offset_seconds)
        if self.render == "date":
            return moment.date().isoformat()
        return moment.isoformat()


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
        relative_defaults: The value each parameter takes when the caller
            omits it, declared **as an offset from the request's own**
            ``asked_at`` rather than as a literal (``D-IMPL-325``, on the gap
            cp-07 measured as ``CP07-F-03``). A window declared here does not
            age: a product whose default is *the last year* says so, and means
            the last year on every day it is asked, instead of meaning an
            absolute date that quietly widens.

            **A separate field rather than a marker object inside**
            ``defaults`` (``D-IMPL-325`` ruling 1, Dave: *"Keep ``defaults``
            literal-only and add ``relative_defaults``. Do not overload
            ``defaults`` with marker objects."*). The two say the same kind of
            thing — what omission means — in two registers, and a literal
            surface that sometimes carries a rule is a surface no reader can
            judge by its declared type.

            **A parameter appears in exactly one of the two.** Both would be
            two documents saying what omission means for one parameter with no
            rule ordering them, which is the shape ``D-IMPL-315`` keeps out;
            it is refused here, where the author can still fix it.

            Refused at declaration for the sibling reasons ``defaults`` is
            refused — a name the class never declared, a name the class
            declares and always refuses, a name already carrying a literal
            default — and for one of its own: a ``render`` the declared
            argument's type cannot hold. Both renders produce a string, so a
            parameter declared ``integer`` cannot take one. Every offender is
            named in one message, on this class's own precedent.

            **The declared domain is deliberately NOT checked here**
            (``D-IMPL-325``, Dave ruling against the option offered: *"Do not
            forbid ``relative_defaults`` when an ``argument_domain``
            exists."*). A relative default's value does not exist until
            ``asked_at`` does, so there is nothing for
            :meth:`ArgumentDomain.refuses` to judge at declaration time. The
            resolved value is judged instead — by the same
            :func:`refuse_request` comparison that judges every effective
            value, at the resolution's conformity step — so a computed date
            outside its governed domain is a request-time refusal and not an
            escape. Dave: *"That is not weaker governance; the value simply
            does not exist until ``asked_at`` exists."*

            Hash-transparent at the empty mapping (``D-IMPL-243``), so every
            contract written before this field keeps its content address; any
            populated mapping renders and therefore **changes the contract
            hash**, because two products with different relative-window rules
            must not share one contract identity.
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
    relative_defaults: Mapping[str, RelativeDefault] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    capability_bindings: Mapping[str, str] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    argument_domains: Mapping[str, ArgumentDomain] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )

    @model_validator(mode="after")
    def _intent_is_not_declared_as_an_argument(self) -> "ProductRequestContract":
        """Refuse an ``intent`` property: a shadow of the top-level field.

        ``D-IMPL-264`` D-01 (Dave, verbatim): *"`intent` is a top-level
        request concept, not an ordinary argument. `ProductDiscovery.intents`
        is the declaration of what the class serves. A duplicate
        `arguments.properties.intent` is a shadow declaration and should fail
        contract construction."* Every request carries
        :attr:`ProductRequest.intent` as one of the four address axes (§6.3),
        and what a class serves is declared once, on
        :class:`~ccf.products.contract.ProductDiscovery`; a parameter of the
        same name would be a second place to say it, judged by a different
        rule (the payload comparison) from the one that judges the field
        (:func:`refuse_intent`). Refused at construction — first, before any
        other validator — so an author is told about the shadow before the
        rest of the document is judged around it.

        The comparison is against the ONE field name and nothing else — no
        collection of reserved names lives in this module (the
        ``_string_collection_constants`` guard in
        ``tests/products/test_request_contract.py``).

        Amendment 1 F-2: the frozen rungs cp-01 through cp-04 declare exactly
        this shadow and fail here; they are evidence, read by the tests and
        never edited (``D-IMPL-261``).
        """
        if "intent" in self.arguments.properties:
            raise ValueError(
                f"the request contract for {self.schema_name!r} at class lane "
                f"{self.schema_version!r} declares 'intent' under "
                "arguments.properties, which is a shadow of the top-level "
                "request field ProductRequest.intent; what a class serves is "
                "declared once, on ProductDiscovery.intents, and judged there "
                "— remove the argument (D-IMPL-264 D-01, amendment 1 F-2)"
            )
        return self

    @model_validator(mode="after")
    def _every_domain_bounds_a_declared_number_the_default_respects(
        self,
    ) -> "ProductRequestContract":
        """Refuse a domain the class cannot hold a caller to, naming every offender.

        Five ways a declared domain is not one (``D-IMPL-259``; ``D-IMPL-264``
        D-03/D-06), checked together on the defaults validator's precedent: a
        name the class never declared; a name declared with a type that has
        no magnitude under a NUMERIC domain (bounds over a string bound
        nothing, and ``bool`` is not a number to this contract); an
        ENUMERATED domain whose members are typed against the declared
        property (a string set over an integer, a number over a boolean —
        *"homogeneous members matching the declared property type"*); a
        name the class declares and **always refuses** (a domain over an
        inert parameter describes questions the tier step never lets
        through); and a declared default that lies outside the domain,
        judged by the same :meth:`ArgumentDomain.refuses` the domain step
        uses — the class contradicting itself, which fails HERE, where the
        author can still fix it, rather than in front of a caller who
        omitted the parameter (``D-IMPL-258`` (5)'s rule, one key over).
        """
        if not self.argument_domains:
            return self

        undeclared = sorted(
            name
            for name in self.argument_domains
            if name not in self.arguments.properties
        )
        inert = sorted(
            name
            for name in self.argument_domains
            if name in self.unsupported_arguments
        )
        unmeasurable = sorted(
            name
            for name, domain in self.argument_domains.items()
            if name in self.arguments.properties
            and domain.members is None
            and not _has_magnitude(self.arguments.properties[name].type)
        )
        mistyped = sorted(
            f"{name} declares {self.arguments.properties[name].type} but "
            f"enumerates {_member_class(domain.members[0])}"
            for name, domain in self.argument_domains.items()
            if name in self.arguments.properties
            and domain.members is not None
            and not _members_match_type(
                domain.members, self.arguments.properties[name].type
            )
        )
        contradicted = sorted(
            f"{name}={self.defaults[name]!r}"
            for name, domain in self.argument_domains.items()
            if name in self.defaults
            and name not in undeclared
            and name not in unmeasurable
            and domain.refuses(self.defaults[name]) is not None
        )
        if not (undeclared or inert or unmeasurable or mistyped or contradicted):
            return self
        raise ValueError(
            f"the request contract for {self.schema_name!r} at class lane "
            f"{self.schema_version!r} declares argument domains it cannot "
            f"hold a caller to: {undeclared} are not declared arguments, "
            f"{unmeasurable} are bounded numerically but declared with a type "
            "that has no magnitude (numeric bounds hold integer and number "
            f"only), {mistyped} are enumerated with members typed against the "
            f"declared property (mistyped), {inert} are declared and always "
            f"refused, and {contradicted} carry a declared default outside "
            "their own domain (the parameter and the offending default, "
            "criterion 2) — a class that would refuse the value it fills "
            "in for an omission contradicts itself, and that fails at "
            "declaration rather than in front of a caller "
            "(D-IMPL-259, D-IMPL-264 D-03/D-06, D-IMPL-258 (5))"
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

    @model_validator(mode="after")
    def _every_relative_default_names_one_parameter_it_can_fill(
        self,
    ) -> "ProductRequestContract":
        """Refuse a relative default the class cannot honor, naming every offender.

        Four ways a declared relative default is not one (``D-IMPL-325``),
        checked together on the ``defaults`` validator's precedent: a name the
        class never declared; a name the class declares and **always refuses**
        (a default for a parameter the tier step never lets through fills
        nothing); a name that **also** carries a literal default (two
        authorities over one bound, ``D-IMPL-315``); and a ``render`` the
        declared argument's type cannot hold — both renders produce a string,
        so a parameter declared with any other type could never take one.

        **The declared domain is not among them, by ruling.** A relative
        default's value does not exist until ``asked_at`` does, so the
        contradiction check the sibling validator runs over ``defaults`` has
        nothing to read here. The resolved value faces
        :func:`refuse_request` at the resolution's conformity step exactly as
        a caller's value does.
        """
        if not self.relative_defaults:
            return self

        undeclared = sorted(
            name
            for name in self.relative_defaults
            if name not in self.arguments.properties
        )
        inert = sorted(
            name
            for name in self.relative_defaults
            if name in self.unsupported_arguments
        )
        doubly_declared = sorted(
            name for name in self.relative_defaults if name in self.defaults
        )
        unrenderable = sorted(
            f"{name} declares {self.arguments.properties[name].type} but a "
            f"{spec.render} render produces a string"
            for name, spec in self.relative_defaults.items()
            if name in self.arguments.properties
            and self.arguments.properties[name].type != "string"
        )
        if not (undeclared or inert or doubly_declared or unrenderable):
            return self
        raise ValueError(
            f"the request contract for {self.schema_name!r} at class lane "
            f"{self.schema_version!r} declares relative defaults it cannot "
            f"honor: {undeclared} are not declared arguments, {inert} are "
            f"declared and always refused, {doubly_declared} already carry a "
            "literal value under `defaults` and a parameter takes its meaning "
            "for omission from exactly one of the two, and {} cannot hold "
            "what the declared render produces; every offender is named here "
            "rather than one per exception, so the document is fixed in one "
            "pass (D-IMPL-325, D-IMPL-315, 24.6-L-07)".format(unrenderable)
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
        relative = declaration.get(_KEY_RELATIVE_DEFAULTS, {})
        if not isinstance(relative, Mapping) or not all(
            isinstance(name, str) and isinstance(spec, Mapping)
            for name, spec in relative.items()
        ):
            raise ValueError(
                f"the declared artifact {artifact.class_id!r} at lane "
                f"{artifact.semver!r} carries {_KEY_RELATIVE_DEFAULTS!r} as "
                f"{type(relative).__name__}, and it must be a mapping of "
                "parameter name to a mapping carrying `offset_seconds` and "
                "`render` — what the class takes when the caller omits that "
                "parameter, expressed as an offset from the request's own "
                "asked_at rather than as a literal that ages (D-IMPL-325)"
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
        domains = declaration.get(_KEY_ARGUMENT_DOMAINS, {})
        if not isinstance(domains, Mapping) or not all(
            isinstance(name, str) and isinstance(domain, Mapping)
            for name, domain in domains.items()
        ):
            raise ValueError(
                f"the declared artifact {artifact.class_id!r} at lane "
                f"{artifact.semver!r} carries {_KEY_ARGUMENT_DOMAINS!r} as "
                f"{type(domains).__name__}, and it must be a mapping of "
                "parameter name to a mapping carrying `minimum` and/or "
                "`maximum` — the parameter's valid domain, which is part of "
                "the request contract and neither a policy constraint nor a "
                "technical capability (D-IMPL-259)"
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
            relative_defaults={
                name: RelativeDefault.model_validate(dict(spec))
                for name, spec in relative.items()
            },
            capability_bindings=dict(bindings),
            argument_domains={
                name: ArgumentDomain.model_validate(dict(domain))
                for name, domain in domains.items()
            },
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

#: The optional EIGHTH declaration key (``D-IMPL-325``). A key NAME again, and
#: the value under it is an *offset and a render* — never a date. The window a
#: class defaults to is read from the artifact at
#: :meth:`ProductRequestContract.from_declared` and nowhere else; a date in
#: this module would be a governance value in the spine, and a date in an
#: adopter's deployment code would be a second authority over one bound
#: (CINV-01, ``D-IMPL-315``).
_KEY_RELATIVE_DEFAULTS = "relative_defaults"

#: The optional sixth declaration key (``24.6-L-07``, ``D-IMPL-253`` Q21). A
#: key NAME again, and the value under it is a *capability token* — which
#: capability bounds a parameter — never the bound. The number a backend can
#: technically do is the backend's, read off it at resolution time; a ceiling
#: authored in an artifact would be a technical bound nobody measured
#: (CINV-01).
_KEY_CAPABILITY_BINDINGS = "capability_bindings"

#: The optional seventh declaration key (``D-IMPL-259``). A key NAME, and the
#: value under it is a parameter's VALID DOMAIN — the numbers that are
#: meaningful questions of this class — which is part of the request
#: contract in the same register as ``type`` and ``required``. Not a policy
#: constraint and not a capability: no artifact pin, no authority, no
#: substrate. Nothing in this module carries a boundary value (CINV-01); what a
#: class admits is read from the artifact at
#: :meth:`ProductRequestContract.from_declared` and nowhere else.
_KEY_ARGUMENT_DOMAINS = "argument_domains"

def _has_magnitude(type_name: str) -> bool:
    """Is ``type_name`` one of the two declared JSON Schema types with a magnitude?

    ``integer`` and ``number``, and not ``boolean`` — ``bool`` is an ``int``
    to Python and not to this contract, the reading :func:`_refuse_tolerance`
    already takes. Spelled inside a function rather than as a module-level
    collection on purpose: this module's own guard
    (``tests/products/test_request_contract.py::_string_collection_constants``)
    reads any module-level set of string literals as a spine-held parameter
    set, which is the CINV-01 shape it exists to refuse. These two are JSON
    Schema's names, the SDK's own vocabulary, and the function keeps them
    where the guard can tell the difference.
    """
    return type_name in {"integer", "number"}


def _as_decimal(value: object) -> Decimal | None:
    """The value as a :class:`~decimal.Decimal`, or ``None`` when it has no magnitude.

    One reading for a caller's value and a declared default, so the domain
    step and the declaration validator cannot judge the same number by two
    rules. ``bool`` is refused on purpose (see :func:`_has_magnitude`), and a
    float is refused because :mod:`ccf.contracts.canonical` refuses it first:
    a boundary compared to a float is a comparison the contract could never
    address.
    """
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return None
    return Decimal(value)


def _member_class(value: object) -> str | None:
    """Which of the three member classes ``value`` belongs to, or ``None``.

    ``boolean`` is read FIRST, because ``bool`` is an ``int`` to Python and
    not to this contract — the discipline :func:`_as_decimal` and
    :func:`_refuse_tolerance` already hold. ``int`` and
    :class:`~decimal.Decimal` are one ``numeric`` class, ``str`` is
    ``string``. Spelled as a function rather than a module-level table for the
    reason :func:`_has_magnitude` gives: this module's own guard refuses any
    module-level collection of string literals (``D-IMPL-264`` D-06).
    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, Decimal)):
        return "numeric"
    if isinstance(value, str):
        return "string"
    return None


def _members_match_type(
    members: tuple[str | int | bool | Decimal, ...], type_name: str
) -> bool:
    """Do these (homogeneous) members match the declared JSON Schema type?

    ``string`` takes the string class; ``boolean`` the boolean class;
    ``number`` the numeric class; ``integer`` the numeric class with every
    member an ``int`` (a ``Decimal("1.5")`` is a number, not an integer).
    ``array`` and ``object`` take no enumerated domain at all — a member set
    is a set of primitives (``D-IMPL-264`` D-06). Spelled as a function, not
    a table, for the reason :func:`_has_magnitude` gives.
    """
    member_class = _member_class(members[0])
    if type_name == "string":
        return member_class == "string"
    if type_name == "boolean":
        return member_class == "boolean"
    if type_name == "number":
        return member_class == "numeric"
    if type_name == "integer":
        return member_class == "numeric" and all(
            isinstance(member, int) for member in members
        )
    return False


def _is_member(value: object, member: object) -> bool:
    """Is ``value`` exactly ``member``, under that member's class equality?

    The ONE membership judgment (``D-IMPL-264`` D-04, Dave: *"Exact canonical
    match. No trimming, case folding, aliases, or silent substitution."*),
    called by :meth:`ArgumentDomain.refuses` and, through it, by the domain
    step and the contract validator, so a default and a caller's value are
    judged by one rule. Class first, then value: a string is compared as the
    untouched ``str``; a boolean by identity; a number by
    :func:`_as_decimal` value, so ``Decimal("2")`` is ``2`` while ``True``
    is never ``1`` and ``"1"`` is never ``1``.
    """
    member_class = _member_class(member)
    if member_class is None or _member_class(value) != member_class:
        return False
    if member_class == "numeric":
        return _as_decimal(value) == _as_decimal(member)
    if member_class == "boolean":
        return value is member
    return value == member


def _refuse_a_malformed_member_set(
    members: tuple[str | int | bool | Decimal, ...],
) -> None:
    """Empty, non-finite, heterogeneous or duplicated — named, in that order.

    The enumerated half of :meth:`ArgumentDomain._at_least_one_end_and_in_order`
    (``D-IMPL-264`` D-03/D-06). Duplication is judged by :func:`_is_member`
    itself, so ``1`` and ``Decimal("1")`` ARE duplicates while ``1`` and
    ``True`` are a heterogeneous pair, refused one check earlier.
    """
    if not members:
        raise ValueError(
            "an enumerated argument domain declares a non-empty member set; "
            "an empty set admits no value and is a key with nothing under it "
            "(D-IMPL-264 D-03, D-IMPL-259)"
        )
    for member in members:
        number = _as_decimal(member)
        if number is not None and not number.is_finite():
            raise ValueError(
                "an enumerated argument domain's members must be finite "
                f"numbers, not {member!r} (D-IMPL-264 D-06, D-IMPL-259)"
            )
    classes = sorted({str(_member_class(member)) for member in members})
    if len(classes) != 1:
        raise ValueError(
            "an enumerated argument domain's members are homogeneous — one "
            "class for the whole set, and bool is its own class — but this "
            f"set mixes {classes} (D-IMPL-264 D-06, D-IMPL-259)"
        )
    duplicated = sorted(
        {
            repr(later)
            for index, later in enumerate(members)
            if any(_is_member(later, earlier) for earlier in members[:index])
        }
    )
    if duplicated:
        raise ValueError(
            "an enumerated argument domain's members are duplicate-free, "
            f"judged by the membership rule itself; {duplicated} appear more "
            "than once (D-IMPL-264 D-03, D-IMPL-259)"
        )


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
        reason: Which of the nine ways the request missed.
        key: Where. A parameter reads by name, a nested member reads
            ``parent.member`` and an element of a declared list reads
            ``parent[].member``; a class mismatch reads the field that
            disagreed; a tier refusal reads the inert parameter's name; a
            proportion refusal reads the tolerance parameter's name; a
            domain refusal reads the domained parameter's name.
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
            to be. For a ``not-in-domain`` refusal it carries the parameter
            name, the presented value and the sorted member set — and the
            allowed set travels ONLY here, never as a typed member, so
            :data:`~ccf.products.disclosure.PERMITTED_AT_MINIMAL` decides its
            exposure without a new row (``D-IMPL-264`` D-05, the disclosure
            channel); advertising the set to a caller BEFORE the request is
            the other channel, the canonical contract render (D-02), and is
            not a refusal's business. For an intent refusal
            (:func:`refuse_intent`, ``class-mismatch`` at ``key="intent"``)
            it carries the presented intent and the sorted declared set on
            exactly the same rule — the set ONLY here, never in
            ``declared_type`` (``D-IMPL-264`` amendment 3 A-8 a).
        overrides: Every override the request attempted, with its entitlement
            result, when this violation was reached by
            :func:`~ccf.products.constraints.resolve_effective_request` —
            the validation pass runs over the EFFECTIVE values after the
            attempts were verified, and a refused request must not lose them
            (``D-IMPL-260`` P-I, criterion 10). Empty on a violation reached
            before any resolution — request-contract conformity at the door —
            and empty when nothing was attempted. Hash-transparent at the
            empty tuple, so no violation written before the member existed
            moves.
    """

    reason: ProductRequestViolationReason
    key: str
    declared_type: str | None
    presented_type: str | None
    declared_keys: frozenset[str]
    presented_keys: frozenset[str]
    detail: str
    overrides: tuple[OverrideRecord, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


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


def _refuse_domain(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """Does every presented value lie inside its declared domain?

    The domain step (``D-IMPL-259``, ``D-IMPL-264`` D-04/D-05). Runs LAST,
    after the payload comparison has said each parameter is declared, honored
    and well-typed and after the interval step has judged the tolerance, so
    this function only ever judges a well-typed value against the class's
    own declaration of what values are meaningful: a number's magnitude
    against a numeric domain, or a value's exact typed membership in an
    enumerated one. Names are read in sorted order so the first verdict is
    the same verdict on every run — the replay property every comparison in
    this package carries.

    The one membership judgment is :meth:`ArgumentDomain.refuses`, which the
    contract validator also calls over a declared default, so a caller's
    value and a default are judged by one rule. A presented value with no
    magnitude under a numeric domain is not judged here (the payload
    comparison named it first); an enumerated domain receives the presented
    value as it is — untrimmed, unfolded, unaliased (D-04).

    Nothing here clamps and nothing here reads a policy or a capability: a
    value below the floor is refused with the floor named, a value outside
    the set is refused with the set named, exactly as a caller's value above
    a technical capability is refused by :mod:`ccf.products.constraints`
    with the capability named — two boundaries, two vocabularies, one
    posture (*"never clamped"*).
    """
    for key in sorted(declared.argument_domains):
        if key not in request.parameters:
            continue
        presented = request.parameters[key]
        domain = declared.argument_domains[key]
        reason = domain.refuses(presented)
        if reason is None:
            continue
        property_ = declared.arguments.properties.get(key)
        if reason == "not-in-domain":
            members = ", ".join(repr(member) for member in sorted(domain.members or ()))
            detail = (
                f"{key}: {presented!r} is not a member of this class's "
                f"declared domain [{members}] — the parameter's legal values, "
                "declared beside its type and judged by exact typed equality, "
                "refused by name rather than substituted (D-IMPL-264 D-04/D-05)"
            )
        else:
            limit = domain.minimum if reason == "below-minimum" else domain.maximum
            edge = (
                "below the declared minimum"
                if reason == "below-minimum"
                else "above the declared maximum"
            )
            detail = (
                f"{key}: {presented} lies {edge} {limit} of this class's "
                "request contract — the parameter's valid domain, declared "
                "beside its type and refused by name rather than substituted "
                "(D-IMPL-259)"
            )
        return ProductRequestViolation(
            reason=reason,
            key=key,
            declared_type=None if property_ is None else property_.type,
            presented_type=type(presented).__name__,
            declared_keys=frozenset(declared.arguments.properties),
            presented_keys=frozenset(request.parameters),
            detail=detail,
        )
    return None


#: The canonical decimal lexical form a ``number`` argument crosses the wire as.
#:
#: `D-IMPL-302`. Deliberately NARROWER than :class:`decimal.Decimal`'s own
#: parser: an optional sign, digits, and an optional fraction. No exponent, no
#: ``NaN``, no ``Infinity``, no leading ``+`` on the fraction, no whitespace.
#: Python would accept every one of those and they are not values a product
#: contract means by *number*; letting `Decimal`'s breadth define the wire
#: contract by accident is the failure this pattern exists to prevent.
CANONICAL_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")

#: The declared type this decoding applies to, and the only one.
DECODED_DECLARED_TYPE: Final[str] = "number"


def decode_declared_request(
    request: ProductRequest, declared: ProductRequestContract
) -> ProductRequest:
    """A NEW request whose declared ``number`` arguments carry exact decimals.

    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-302``
    (Dave, 2026-09-09): *"MCP transport representation must not force Context
    Product authors to misdeclare logical numeric parameters as strings."*

    **The defect this closes.** A product declaring ``materiality: number``
    could not be asked over MCP at all. The contract refused a ``str`` with
    ``type-mismatch``; :class:`~ccf.products.door.WireRequest` refused a
    ``float`` because *"canonical JSON renders it as text, so the decoded echo
    would differ from what was sent"*. Both refusals are correct on their own
    terms, and their composition left a fractional number with **no
    representation**. cp-05 was the first product whose numeric arguments were
    consequential enough to need one.

    **Two representations, two authorities, and keeping them apart is the
    point.** The wire keeps the lexical ``"0.05"`` and the echo cross-check
    still runs against it; the governed request carries exact
    ``Decimal("0.05")``, which is what the contract validates, what resolution
    computes over, and what replay records. *Wire stability does not require
    semantic type erasure.*

    **A VALIDATOR IS NOT A TRANSFORMER.** This is deliberately separate from
    :func:`refuse_request`, which judges and returns a violation or ``None``.
    Dave: *"Turning it into both validator and transformer would blur a useful
    boundary and ripple a new return shape through every caller."* The sequence
    is decode, then judge.

    **The incoming request is never mutated.** A new one is returned, so the
    lexical request stays available to the transport boundary and the
    conversion point is observable rather than implied.

    **NARROW BY RULING, and the list of what it does not do is the contract.**
    Only *declared ``number`` + canonical decimal text -> exact* ``Decimal``.
    No ``"true"`` -> ``bool``, no ``"123"`` -> ``int``, no date parsing, no
    enums, no scalar-to-collection promotion, no expression or transform
    registry. **No** :func:`float` **anywhere**: the decimal is built from the
    text, never through a binary float, so ``0.05`` is exact rather than the
    nearest double.

    A value that is already numeric passes through untouched, and text that is
    not a canonical decimal passes through **unchanged** so that
    :func:`refuse_request` refuses it by name — this function never mints a
    refusal of its own, because the contract comparison is the one place that
    verdict belongs.
    """
    properties = declared.arguments.properties
    decoded: dict[str, Any] = {}
    for name, value in request.parameters.items():
        declaration = properties.get(name)
        if (
            declaration is not None
            and declaration.type == DECODED_DECLARED_TYPE
            and isinstance(value, str)
            and CANONICAL_DECIMAL.match(value)
        ):
            decoded[name] = Decimal(value)
        else:
            decoded[name] = value
    if decoded == dict(request.parameters):
        return request
    return request.model_copy(update={"parameters": decoded})


def refuse_request(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """The one request-conformity comparison — address, then tier, then parameters, then the tolerance interval, then the declared domains.

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
        parameters at every level, presents no tolerance outside the unit
        interval, and presents no number outside its declared domain;
        otherwise the
        :class:`ProductRequestViolation` naming the first failure — address
        first, then the tier step over sorted presented names, then the fixed
        undeclared-then-missing-then-mistyped order
        :func:`~ccf.products.payload.refuse_payload` imposes over sorted names,
        then the interval step, then the domain step (:func:`_refuse_domain`,
        ``D-IMPL-259``) over sorted domained names — carrying both sides of
        the comparison that failed.
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
    tolerance = _refuse_tolerance(request=request, declared=declared)
    if tolerance is not None:
        return tolerance
    return _refuse_domain(request=request, declared=declared)


def refuse_intent(
    *, request: ProductRequest, discovery: ProductDiscovery
) -> ProductRequestViolation | None:
    """Is this request's intent one the class is registered to serve?

    ``D-IMPL-264`` D-01 as amended by amendment 1 (F-1 a). Dave, verbatim:
    *"Absence of a discovery declaration is non-applicability. Presence of a
    discovery declaration makes its intent set authoritative, including an
    explicitly empty set."* The whitepaper hook is §6.3: intent is one of the
    axes a caller addresses a product by, and the registry entry a class
    publishes is what says which intents it answers.

    Three states, and the first is not the third:

    * ``discovery == NOT_DISCOVERABLE`` — **no declaration exists**, and the
      intent is **unjudged**: ``None``, whatever the intent. The sentinel is
      the positive assertion *this class is reached by direct reference*,
      not a statement that it serves zero intents; every class shipped
      before this phase is in that state and serves exactly as it did. The
      comparison is by equality with the sentinel, so a deployment that
      writes the sentinel's exact content has written the not-discoverable
      state and is read as such.
    * declared, and ``request.intent in discovery.intents`` — ``None``.
    * declared, and not a member — a :class:`ProductRequestViolation`
      returned as data (``D-IMPL-251``): ``class-mismatch`` at
      ``key="intent"``, because §6.3 makes intent an addressing token and a
      class not registered to serve it is addressed to the wrong class, in
      the same family as a lane mismatch. A declared **empty** set refuses
      every intent — *"an explicitly declared empty set means 'serves
      none'"* — which is the state the sentinel is NOT.

    Membership is exact (D-04's rule, one field over): ``"A"`` is not
    ``"a"`` and ``" a"`` is not ``"a"``; nothing trims, folds or aliases.

    The declared set rides in ``detail`` ONLY — never in ``declared_type``,
    which :data:`~ccf.products.disclosure.PERMITTED_AT_MINIMAL` lets cross —
    so a refusal shell reveals it according to the disclosure level, exactly
    as the enumerated argument domain's members do (``D-IMPL-264`` amendment
    3 A-8 a, Dave: *"a refusal shell reveals it only according to the
    disclosure level"*). Advertising the set BEFORE the request is the
    canonical discovery representation's business, not a refusal's.

    A sibling of :func:`refuse_request`, not a step inside it: that function
    sees the request and the contract only, and the declaration that carries
    ``discovery`` is in scope where the class is resolved
    (:meth:`ccf.products.resolver.GovernedResolver.resolve`), which hosts
    this judgment beside its address check. Direct validators that never
    hold a declaration never judge intent — consistent with D-09.
    """
    if discovery == NOT_DISCOVERABLE:
        return None
    if request.intent in discovery.intents:
        return None
    return ProductRequestViolation(
        reason="class-mismatch",
        key="intent",
        declared_type=None,
        presented_type=request.intent,
        declared_keys=frozenset(),
        presented_keys=frozenset(),
        detail=(
            f"this request is addressed with intent {request.intent!r} and the"
            f" class it names is registered to serve {sorted(discovery.intents)};"
            " a declared intent set is authoritative and an explicitly empty one"
            " serves none (D-IMPL-264 D-01, amendment 1 F-1 a; whitepaper §6.3)"
        ),
    )


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
) -> ProductRequestContract | None:
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

    Returns:
        The contract this pin resolved to, or ``None`` when the class declares
        none. Returned rather than discarded since ``D-IMPL-258`` (5), so the
        declaration-versus-contract check
        (:func:`refuse_undeclared_class_default`) reads the contract this
        function already resolved. Two reads of one key are two chances to
        disagree about what a class's request surface is.

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
        return None
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
    return artifact


def refuse_undeclared_class_default(
    *,
    schema_name: str,
    schema_version: str,
    serve_obligations: ServeObligations,
    declared: ProductRequestContract | None,
) -> None:
    """Raise unless every class default names a parameter the contract exposes.

    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-258``
    (5), Dave: *"Under Q2, a product default is part of the request contract.
    Therefore a default naming a parameter the contract does not expose is a
    malformed/internally inconsistent declaration. That should fail
    registration/configuration/boot validation, not produce a shell to a
    caller. … Default for undeclared parameter → configuration/invariant
    failure. Caller outside a valid declared constraint → governed shell."*

    **Why a class default is not a ceiling** (``D-IMPL-251`` C1=A, ``24.6-L-04``).
    A default is what *omission* means, so it presupposes a counterfactual: a
    caller who could have stated the parameter and did not. A class
    characteristic the caller has **no way to state** has no counterfactual —
    it is a ceiling wearing a default's name, which is exactly the power C1=A
    took away from a product class. Neither of the two alternatives is
    tenable: folding the value in anyway refuses every request as
    ``undeclared-parameter``, reporting a deployment's mistake as a caller's
    on a path the caller cannot fix; dropping it silently leaves a class
    believing it declared a tolerance it never applies.

    **Why it runs here rather than at resolution.** ``24.6-04`` put this
    refusal in :func:`~ccf.products.constraints.resolve_effective_request`,
    which reaches it once per *request* — so a self-contradicting Control Plane
    served every other class happily and failed the moment somebody asked a
    question. `D-IMPL-258` (5) moves it to the two moments a declaration is
    taken up: registration
    (:func:`~ccf.products.contract.register_product_class`) and boot
    (:func:`~ccf.products.resolver.build_governed_resolver`). The resolution
    -time raise is retained as an unreachable invariant guard for callers of
    the pure function, which cannot assume its caller booted through either.

    Args:
        schema_name: The class whose declaration is being taken up.
        schema_version: Its own semver lane, for the message.
        serve_obligations: What the class declares about serving. Read for its
            defaults only; the lineage obligation is a different kind of thing
            and is not this function's subject.
        declared: The class's request contract, or ``None`` when it pins none.
            ``None`` **returns without refusing**, and the scoping is
            deliberate rather than lenient: Dave's sentence is *"a default
            naming a parameter the contract does not expose"*, which
            presupposes a contract. A class that pins none is the
            pre-``D-IMPL-98`` posture — nothing validates a question against a
            declared surface, so nothing can refuse one as
            ``undeclared-parameter``, and the failure mode this check exists to
            prevent does not arise. Whether that posture should also be refused
            is a wider rule than the one ruled, and it is put to Dave in
            ``24.6-D-IMPL-258-FIXES.md`` rather than decided here.

    Raises:
        ProductClassRegistrationError: the class declares a default for a
            parameter its request contract does not declare as an argument.
            The shipped registration error is reused rather than a new type
            added, for :func:`refuse_request_contract_pin`'s reason: a class
            whose governance configuration is malformed fails for one reason
            from the adopter's point of view.
    """
    # Function-local for `_refuse_tolerance`'s reason, spelled there:
    # `ccf.products.gates` reaches `ccf.products.contract`, which is on the
    # path back to this module through the replay record. One name, needed
    # once per class registration and never in a request path.
    from ccf.products.gates import DEBT_TOLERANCE_PARAMETER

    if declared is None:
        return

    # The class's declared defaults, by the parameter name each reaches the
    # Authority layer under. One entry today; a mapping rather than a check so
    # a second declared default has a place to be listed rather than a branch
    # to be added — the shape `INDISTINGUISHABLE_BELOW_FULL` uses for the same
    # reason.
    class_defaults: Mapping[str, object | None] = {
        DEBT_TOLERANCE_PARAMETER: serve_obligations.default_debt_tolerance,
    }
    exposed = frozenset(declared.arguments.properties)
    undeclared = sorted(
        name
        for name, value in class_defaults.items()
        if value is not None and name not in exposed
    )
    if not undeclared:
        return
    raise ProductClassRegistrationError(
        f"product class {schema_name!r} at lane {schema_version!r} declares a"
        f" default for {undeclared}, and its request contract"
        f" ({declared.schema_name!r} @{declared.schema_version}) declares"
        f" {sorted(exposed)} as its arguments. A caller who cannot state the"
        " parameter cannot accept a product the default would withhold, so the"
        " default would be a class-imposed ceiling (D-IMPL-251 C1=A) rather"
        " than a default. Declare the argument on the request contract, or"
        " remove the class default (D-IMPL-258 (5))"
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
