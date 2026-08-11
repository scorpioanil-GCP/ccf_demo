"""The request surface a product class declares and a door validates.

SDK-defined. The ruling of record is ``docs/DECISIONS.md`` **D-IMPL-98** (Dave,
2026-08-11, option (a)): *the request surface is a typed request contract per
product class, declared as a Control Plane artifact, in the*
:class:`~ccf.skills.catalog.SkillArgumentSchema` *shape*. CLAUDE.md §11
requires an SDK extension to cite this project's own record; what the
whitepaper does commit to is §6.3 **Addressability**
(``docs/CCF_Whitepaper_1-2.md:1465``): *"Addressability gives every product a
well-defined interface the agent queries with intent, role, and freshness
parameters. Structured queries enable decision-time assembly rather than
pre-aggregated retrieval."* Its worked address pattern —
``/context-products/credit-risk/counterparty/{counterparty-id}?intent=…&freshness=…``
— *"encodes exactly what the agent needs: which entity, for what decision,
under what temporal requirement."*

**What was wrong, stated precisely, because half of it was right.** A Context
Product was *configurable* rather than *callable*: its subject and its instant
were literals authored in an artifact, so one product class answered one
question about one company as of one frozen moment. That is the thing Chapter 1
names CCF as replacing — the difference between the verb *aggregate* and the
verb *assemble*. But the mechanism underneath it is correct and must not be
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
from typing import Any, Literal

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass, VersionedArtifact
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.products.contract import (
    NO_REQUEST_CONTRACT,
    ProductClassRegistrationError,
)

# `ccf.products.payload` and `ccf.skills.catalog` are imported at the BOTTOM of
# this module, on the D-IMPL-56 pattern `ccf.skills.catalog` itself documents.
# The reason is D-IMPL-111 limb (b): `ccf.replay.record` now names
# :class:`ProductRequest` in dimension 5, and `ccf.skills.catalog` reaches
# `ccf.agents.agent`, which reads two names out of `ccf.replay.record` — so
# with those two imports at the top, first-import order would decide whether
# the SDK imports at all. Deferring them makes :class:`ProductRequest` exist
# before anything here can reach the replay plane, which closes the cycle in
# both directions; the deferred annotations are resolved explicitly at the
# bottom.

__ccf_mode__ = "algorithmic"

__all__ = [
    "NO_REQUEST_CONTRACT",
    "PRODUCT_REQUEST_CONTRACT",
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
#: Three of the four are the three ways a closed, typed, partially-required
#: declaration can be missed, spelled in the request's own vocabulary
#: (*parameter*, not *key*) so a caller reading a refusal is not asked to
#: translate. The fourth has no payload analogue: a payload belongs to whatever
#: product carried it, while a request is **addressed**, and a request handed
#: to the wrong class's contract is a mis-delivery rather than a bad argument.
ProductRequestViolationReason = Literal[
    "undeclared-parameter",
    "missing-required-parameter",
    "type-mismatch",
    "class-mismatch",
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
    """

    schema_name: str
    schema_version: str
    subject: str
    intent: str
    freshness: str
    asked_at: datetime
    parameters: Mapping[str, Any]


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
    """

    schema_name: str
    schema_version: str
    arguments: SkillArgumentSchema


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
        reason: Which of the four ways the request missed.
        key: Where. A parameter reads by name, a nested member reads
            ``parent.member`` and an element of a declared list reads
            ``parent[].member``; a class mismatch reads the field that
            disagreed.
        declared_type: The JSON Schema type declared at ``key`` — or, for a
            class mismatch, the value the **contract** declares. ``None`` when
            neither applies.
        presented_type: The Python type name the request presented at ``key``
            — or, for a class mismatch, the value the **request** presented.
        declared_keys: Every parameter the contract declares at the level the
            violation occurred, so an undeclared parameter is readable against
            the set it was not in. Empty for a class mismatch, which is not
            about a level.
        presented_keys: Every parameter the request presented at that level.
        detail: The human-readable statement, for the operator reading a log.
            The typed fields above are the machine-readable version.
    """

    reason: ProductRequestViolationReason
    key: str
    declared_type: str | None
    presented_type: str | None
    declared_keys: frozenset[str]
    presented_keys: frozenset[str]
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


def refuse_request(
    *, request: ProductRequest, declared: ProductRequestContract
) -> ProductRequestViolation | None:
    """The one request-conformity comparison — address first, then parameters.

    Called by the door, once the seam that can carry a typed request exists
    (D-IMPL-108, plan ``15.5-15``), and by any registration-time capability
    check that needs to know what a class accepts. One function, so the two
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
        ``None`` when the request is addressed to this contract and matches its
        declared parameters at every level, otherwise the
        :class:`ProductRequestViolation` naming the first failure — address
        first, then the fixed undeclared-then-missing-then-mistyped order
        :func:`~ccf.products.payload.refuse_payload` imposes over sorted names
        — carrying both sides of the comparison that failed.
    """
    address = _refuse_address(request=request, declared=declared)
    if address is not None:
        return address
    parameters = refuse_payload(
        payload=request.parameters, declared=declared.arguments
    )
    if parameters is None:
        return None
    return _translate(parameters)


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
# deferred annotations above are then resolved explicitly.
from ccf.products.payload import (  # noqa: E402
    PayloadSchemaViolation,
    refuse_payload,
)
from ccf.skills.catalog import SkillArgumentSchema  # noqa: E402

ProductRequestContract.model_rebuild()
