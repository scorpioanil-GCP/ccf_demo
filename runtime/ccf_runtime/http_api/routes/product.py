"""The ``product`` noun — retrieval only (D-IMPL-23; whitepaper §8.3 P3).

Read-only by construction: the router registers GET and nothing else, and
the seam it holds is the egress resolver
(:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`) — the same
already-servable-product seam the MCP front door holds, trading only in
gate-admitted :class:`~ccf.products.gates.ServableProduct`s. No write door
can exist here because no handle here could hold one (T-07-23).

**The 15.5-06 entitlement composition.** This is the third of the three
exposed product doors, and it asks the *same question* the two MCP doors ask,
through the *same code*: the seams and the resolution order come from
:mod:`ccf_runtime.authz.product_entitlement`, imported rather than
re-declared. Three doors that disagreed about what "entitled" means is the
drift ``run_gates``/``run_federated_gates`` share their comparison functions
specifically to prevent.

**Why the seams are optional here and required on the MCP doors.**
Authentication on this surface is ``create_app``'s ``auth=`` hook, which is
itself optional by ruling (D-IMPL-73 — the acknowledged insecure default, with
its own warning). An entitlement seam that were required here would make this
app unbuildable in the very posture the SDK explicitly still supports, so
instead the seams are optional and ``create_app`` warns when they are bound
without ``auth=`` — an entitlement check downstream of no authentication can
never run (WR-05's shape). On the MCP builders there is no such posture: both
are authenticated by construction, so their seams are required and there is no
inert configuration of either.

**The role is a query parameter, not a path segment.** The three path segments
are the product's *address*; a role is the caller's *request about capacity*,
and folding it into the address would change what a product URI means on a
surface whose MCP siblings address the same three facts. It is optional: with
no ``role``, the deployment's resolver derives one from the verified grant,
and whatever it derives is still checked against the grant.

**This is the one door with a query surface, so it is the one door that can
carry a request** (``D-IMPL-108``, closing plan ``15.5-08``'s undeliverable
must-have). Whitepaper §6.3 **Addressability**
(``docs/CCF_Whitepaper_1-2.md:1465``) writes the address as
``/context-products/credit-risk/counterparty/{counterparty-id}?intent=…&freshness=…``
— path for *what*, query for *what is being asked of it* — and that is exactly
the split this route now realizes. The four §6.3 axes arrive as query
parameters and the door assembles them into a
:class:`~ccf.products.request.ProductRequest` before the resolver is reached.

**The request's address is the door's, never the caller's.** ``schema_name``
and ``schema_version`` are filled from the *path segments this door already
resolved*, so a request addressed to a class other than the one being served
is **unrepresentable** rather than merely refused — the strongest available
form of "validated where it crosses the door, not downstream", and the reason
this route needs no address cross-check. The tenant is likewise not on the
request at all: it is a thing the door establishes.

**This door carries the replay reference, and it is one of two that do**
(``D-IMPL-148`` **Addendum A**, Dave, 2026-08-17). The base ruling scoped the
fix to the MCP door and recorded the identical gap here as *deferred, not
fixed*, on the ground that no shared assertion spanned both. Dave superseded
that: *both doors carry the reference*, on the same *"both, not one"* principle
``D-IMPL-133`` applied to ``parameters`` — and for the same reason it turned out
to matter there, namely that a gap left on one door is a gap the next assertion
to span both discovers the hard way.

It travels as a **response header** (:data:`~ccf_runtime.http_api.routes.REPLAY_REF_HEADER`),
never in the body, because the body *is* the vessel and anything carried inside
it changes the address it claims — the argument
:func:`~ccf_runtime.http_api.routes.canonical_response` already records for the
content address, applied unchanged. The MCP tool publishes the same string in an
envelope because it has no header channel; the asymmetry is a property of the
transports rather than a difference in what the doors carry.

**And it now carries a third sibling: the question it was asked** (``C-09``),
under :data:`~ccf_runtime.http_api.routes.REQUEST_ECHO_HEADER`. The paragraph
above is extended rather than rewritten, because nothing in it stops being
true: the echo joins the two siblings on the identical argument, through the
identical channel. What it adds is that this door's published siblings are now
the same *values* the envelope-carrying doors carry — ``D-IMPL-126``'s ruling
(*"each surface publishes the same sibling values through whatever channel it
actually has"*) applied, not amended. ``C-09`` scopes *one shape* to doors that
**have** an envelope; this one has headers, so it is reconciled rather than
converted, and its body stays the vessel.

**A consequence of the echo, and it is a narrowing.** The echo is a
:class:`~ccf.products.door.WireRequest`, whose two field guards refuse a value
that would not survive a wire unchanged. A question this door can parse but
cannot represent on the wire is therefore refused at the door with a ``400``
naming the spelling that works, rather than served with a sibling silently
missing — a sibling that disappears for some questions is exactly the pattern
``C-10`` names. Two classes of value reach that refusal, and both bring this
door into agreement with the MCP tool, which already refuses each of them:
a ``float`` (or ``Decimal``, or ``set``) inside ``parameters``, and a naive
``asked_at``. The second closes a measured divergence: ``WireRequest``'s own
temporal guard states that *"both product doors refuse a naive ``asked_at`` by
name"*, and until this change that sentence was false of this door.

**What is still deferred here, stated so it is found rather than rediscovered:
this door has no refusal channel** (DIV-4). A resolver that answers with a
:class:`~ccf.products.refusal.RefusalEnvelope` reaches
:func:`~ccf.products.door.served_answer`, which raises ``TypeError`` naming the
shape — an opaque 500, exactly as the pre-existing ``AttributeError`` produced,
but now saying what went wrong. Rendering a fabric refusal over HTTP is a
status-code and body-shape decision nobody has ruled, and inventing one here
would put an unruled contract on a shipped door.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from starlette.requests import Request

from pydantic import ValidationError

from ccf.products.door import WireRequest, served_answer
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementRefused,
    ProductEntitlementSourceProtocol,
    entitled_perspective,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_PRODUCT_DOOR_UNGOVERNED,
    ERROR_PRODUCT_PARAMETERS_MALFORMED,
    ERROR_PRODUCT_REQUEST_INCOMPLETE,
    refusal_detail,
)
from ccf_runtime.http_api.grants import grant_from_request
from ccf_runtime.http_api.routes import canonical_response
from ccf_runtime.mcp.egress import ProductNotServable

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


def build_router(
    deps: ApiDependencies,
    *,
    entitlement_source: ProductEntitlementSourceProtocol | None = None,
    perspective_resolver: PerspectiveResolverProtocol | None = None,
) -> APIRouter:
    """The product router over the injected resolver seam.

    Args:
        deps: The named provider bundle carrying the assemble-and-gate path.
        entitlement_source: The deployment's per-principal entitlement
            decision seam. Required *together* with ``perspective_resolver``
            when either is supplied: an entitlement with no perspective to
            decide about, or a perspective nothing checks, is a half-bound
            door that looks governed.
        perspective_resolver: The deployment's role-derivation seam.

    Raises:
        ValueError: exactly one of the two governance seams was supplied.
    """
    if (entitlement_source is None) != (perspective_resolver is None):
        raise ValueError(
            "entitlement_source and perspective_resolver are supplied"
            " together or not at all: an entitlement source with no"
            " perspective to decide about, or a perspective resolver whose"
            " output nothing checks, is a door that looks governed and"
            " enforces half a decision (15.5-06)"
        )
    router = APIRouter()

    @router.get(
        "/{tenant}/{product_class}/{version}",
        summary="Product retrieval (D-IMPL-23)",
    )
    def retrieve(
        tenant: str,
        product_class: str,
        version: str,
        request: Request,
        role: str | None = None,
        subject: str | None = None,
        intent: str | None = None,
        freshness: str | None = None,
        asked_at: datetime | None = None,
        parameters: str | None = None,
    ) -> Response:
        perspective = _authorized_perspective(
            request, tenant=tenant, product_class=product_class, role=role
        )
        asked = _asked(
            product_class=product_class,
            version=version,
            subject=subject,
            intent=intent,
            freshness=freshness,
            asked_at=asked_at,
            parameters=parameters,
        )
        # `C-09`: every field of the echo originates producer-side, from the
        # query string THIS route parsed — `product_class` off the path it
        # already resolved, and the remainder off `_asked`'s own return. That
        # is the property a future HTTP adapter depends on: it decodes the
        # published header and never reconstructs the echo from its own state,
        # so the two are independently-sourced facts rather than one fact
        # compared with itself. `None` here is not a missing value; it is the
        # caller's positive assertion that they posed no question at all, and
        # the header is then absent rather than empty.
        echo = _echo(asked) if asked is not None else None
        try:
            resolved = deps.product_resolver(
                tenant=tenant,
                product_class=product_class,
                version=version,
                perspective=perspective,
                request=asked,
            )
        except ProductNotServable as absent:
            raise HTTPException(status_code=404, detail=str(absent)) from absent
        # `D-IMPL-148` Addendum A: the reference the resolver produced reaches
        # the consumer, on the sibling channel this transport has. `None` is the
        # honest report that this deployment's resolver returned the narrower
        # vessel, which carries none — never a reference dropped at the door.
        answer = served_answer(resolved)
        replay_ref = answer.replay_ref
        return canonical_response(answer.product, replay_ref=replay_ref, asked=echo)

    def _echo(asked: ProductRequest) -> WireRequest:
        """The question this door parsed, in the shape a consumer decodes.

        ``C-09``. Built from ``asked`` and from nothing else, so the echo and
        the answer have **one** source: the resolver is called with the same
        object this reads, and there is no second copy of the question anywhere
        on this door for the two to drift apart between. That is also why
        ``C-18``'s temporal cross-check has no subject here — the boundary is
        taken from the one ``asked_at`` this route parsed, so a cross-check
        would compare a value with itself. Its absence is a measurement, not an
        exemption.

        **The refusal is a narrowing, and it is deliberate.**
        :class:`~ccf.products.door.WireRequest` refuses a value that would not
        survive a wire unchanged — a ``float`` in ``parameters``, or an instant
        with no UTC offset. Before this door published an echo it forwarded
        both verbatim and served; the MCP tool refuses both, so the two doors
        disagreed on a class of value that
        ``tests/mcp/test_egress_parameters.py``'s shared table happens not to
        contain. Refusing here is ``D-08``'s posture — *the fabric never
        silently degrades a caller's value* — and it moves this door into
        agreement rather than widening the other, which is the direction
        ``D-IMPL-151`` finding ``B2`` already chose for this pair.

        The guard's own message is carried into the refusal rather than
        paraphrased, because it is the message that names the spelling that
        works; a caller told only *"malformed"* would have to guess.

        Raises:
            HTTPException: 400 with
                :data:`~ccf_runtime.http_api.errors.ERROR_PRODUCT_PARAMETERS_MALFORMED`
                when a declared parameter value cannot cross a wire, or with
                :data:`~ccf_runtime.http_api.errors.ERROR_PRODUCT_REQUEST_INCOMPLETE`
                when ``asked_at`` carries no UTC offset — an axis supplied
                without the part that makes it unambiguous, which is the same
                *the door fills nothing in* that constant already records
                (``D-IMPL-38``).
        """
        try:
            return WireRequest(
                product_id=asked.schema_name,
                parameters=dict(asked.parameters),
                temporal_boundary=asked.asked_at,
            )
        except ValidationError as unrepresentable:
            temporal = any(
                error["loc"] == ("temporal_boundary",)
                for error in unrepresentable.errors()
            )
            raise HTTPException(
                status_code=400,
                detail=refusal_detail(
                    error_code=(
                        ERROR_PRODUCT_REQUEST_INCOMPLETE
                        if temporal
                        else ERROR_PRODUCT_PARAMETERS_MALFORMED
                    ),
                    message=(
                        "this question cannot be represented on the wire, so"
                        " the door refuses it rather than serving an answer"
                        " whose published request echo would be absent or"
                        " would differ from what was asked (C-09):"
                        f" {unrepresentable}"
                    ),
                ),
            ) from unrepresentable

    def _authorized_perspective(
        request: Request, *, tenant: str, product_class: str, role: str | None
    ) -> Perspective:
        """The conditioning this door authorizes, or no product at all.

        Ask the bound seams before the resolver is reached, and **return what
        they decided** rather than only whether they refused (``DI-15.5-03``,
        closed by ``D-IMPL-108``). Until plan ``15.5-15`` this function was
        called for its exception and its return value was discarded, so the
        route proved that an unentitled caller was refused while leaving
        unproven that the product it served was shaped under the perspective
        it had authorized.

        **It is no longer inert, and that is the substantive change.** The
        previous shape returned quietly when the seams were unbound or when no
        verified grant accompanied the call, and the resolver then ran with no
        perspective at all. That is no longer expressible: the resolver seam
        requires one, deliberately, because a door that manufactured a
        perspective would serve a product conditioned on a role nobody granted
        and nothing on the wire would say so. With no authorized perspective
        this door refuses — the plan's own truth, *"a door that cannot pass a
        perspective refuses rather than silently constructing one"*.

        The refusal is a 503 and not a 403 because the fault is the
        deployment's, not the caller's: ``create_app`` already warns at
        construction and at first request about both configurations that reach
        it (:data:`~ccf_runtime.http_api.app.CcfDeadEntitlementWarning` and the
        D-IMPL-73 insecure-default warning), and the operator reading this code
        is being told which of the two to fix.

        Raises:
            HTTPException: 403 with the typed refusal body when the entitlement
                refused the class or the role; 503 with
                :data:`~ccf_runtime.http_api.errors.ERROR_PRODUCT_DOOR_UNGOVERNED`
                when no authorized perspective can be produced at all.
        """
        if entitlement_source is None or perspective_resolver is None:
            raise HTTPException(
                status_code=503,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_DOOR_UNGOVERNED,
                    message=(
                        "this product door has no entitlement seam and no"
                        " perspective resolver bound, so it cannot name the"
                        " Π conditioning a product would be shaped under;"
                        " it refuses rather than serving one conditioned on"
                        " a role nobody granted (D-IMPL-108, DI-15.5-03)."
                        " Supply product_entitlement= and"
                        " perspective_resolver= to create_app()"
                    ),
                ),
            )
        grant = grant_from_request(request)
        if grant is None:
            raise HTTPException(
                status_code=503,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_DOOR_UNGOVERNED,
                    message=(
                        "this product door's entitlement seams are bound but"
                        " no verified grant accompanies the call, so there is"
                        " no principal to resolve a perspective for; deciding"
                        " about an unverified claim is worse than not"
                        " deciding, and serving without a perspective is"
                        " worse than both (D-IMPL-108). Bind auth= to"
                        " create_app()"
                    ),
                ),
            )
        try:
            return entitled_perspective(
                grant=grant,
                tenant=tenant,
                product_class=product_class,
                requested_role=role,
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
            )
        except ProductEntitlementRefused as refused:
            # The typed constant is the contract and the prose is human
            # context (D-08): the same decision the MCP doors render
            # protocol-natively, rendered here as the one 403 body shape.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=refused.error_code, message=refused.message
                ),
            ) from refused

    def _asked(
        *,
        product_class: str,
        version: str,
        subject: str | None,
        intent: str | None,
        freshness: str | None,
        asked_at: datetime | None,
        parameters: str | None,
    ) -> ProductRequest | None:
        """The caller's typed question, or the honest absence of one.

        Whitepaper §6.3's four address axes arrive as query parameters and are
        assembled here, at the door, before anything is resolved — which is
        where ``D-IMPL-98``'s request surface was always supposed to be
        validated. ``schema_name`` and ``schema_version`` are taken from the
        **path this door already resolved**, never from the caller, so a
        request addressed to another class cannot be expressed on this surface
        at all.

        Three outcomes, and the middle one is the point:

        * none of the four supplied → ``None``, the positive assertion *this
          caller asked for the class's standing answer and posed no question of
          their own*;
        * some but not all → refused, because a defaulted axis is a question
          nobody asked, answered anyway;
        * all four → the typed request, ``parameters`` empty.

        **``parameters`` is carried, and the reason it once was not is kept
        rather than deleted.** This paragraph used to read: *"``parameters`` is
        the empty mapping rather than something read off the query string: the
        class-declared remainder is a typed surface whose declared types
        (``D-IMPL-103``'s one level of nested objects and lists-of-objects) a
        flat string-valued query cannot carry without the door guessing at
        coercions ... a caller needing declared parameters reaches the fabric
        in process or through a deployment's own surface."* ``D-IMPL-133``
        (Dave, 2026-08-14) ruled that consequence a defect rather than a
        boundary: a product class declaring **any** required parameter was
        unreachable through this door, and *"both doors carry ``parameters``.
        Both, not one."*

        **The recorded objection is honoured rather than overridden, because
        what it objects to is a *flat, string-valued* query.** That is exactly
        what is not used here. The mapping arrives as **one JSON object** in a
        single query parameter, and JSON is self-describing: a presented ``3``
        stays an ``int``, a presented ``"3"`` stays a ``str``, and one level of
        declared nesting crosses intact. There is nothing left for the door to
        guess at, so it guesses at nothing. This is the same shape the MCP tool
        carries, where the argument map was already JSON — which is what keeps
        the two doors exactly as wide as each other, the property
        ``D-IMPL-133`` names as the reason for repairing both.

        **The door does not validate what is inside the object**, and that is
        the whole of why this is a two-line repair rather than a seam widening:
        the declared world is closed at the resolver, against the
        :class:`~ccf.products.contract.RegisteredProductClass` this door never
        holds (``D-IMPL-121``). The door refuses only text that is not a JSON
        object at all — a malformed *argument*, on the same line
        :class:`~ccf_runtime.mcp.egress.NaiveAskedAtRefused` sits on — and
        falls back to nothing, because a door that quietly read malformed text
        as the empty mapping would answer a question the caller did not ask
        while reporting success.

        Omitting the parameter is the empty mapping, which says *this question
        needs nothing beyond its four axes*. Supplying it **without** the four
        axes is refused as an incomplete address: the declared remainder
        qualifies a question, and there is no question here to qualify.

        No clock is read here, and that is structural rather than incidental:
        ``asked_at`` is the caller's instant at serve time and the *recorded*
        boundary at replay time, through the same code path, which is the
        entire reason nothing downstream of the request reads one either.

        Raises:
            HTTPException: 400 with
                :data:`~ccf_runtime.http_api.errors.ERROR_PRODUCT_REQUEST_INCOMPLETE`
                when the address is partial, or with
                :data:`~ccf_runtime.http_api.errors.ERROR_PRODUCT_PARAMETERS_MALFORMED`
                when ``parameters`` is not a JSON object.
        """
        supplied = [
            name
            for name, axis in (
                ("subject", subject),
                ("intent", intent),
                ("freshness", freshness),
                ("asked_at", asked_at),
            )
            if axis is not None
        ]
        if not supplied:
            if parameters is None:
                return None
            raise HTTPException(
                status_code=400,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_REQUEST_INCOMPLETE,
                    message=(
                        "`parameters` was supplied with none of the four §6.3"
                        " axes. The class-declared remainder qualifies a"
                        " question; with no subject, intent, freshness or"
                        " asked_at there is no question here for it to"
                        " qualify, and the door fills none of them in"
                        " (D-IMPL-98, D-IMPL-133)"
                    ),
                ),
            )
        if (
            subject is None
            or intent is None
            or freshness is None
            or asked_at is None
        ):
            raise HTTPException(
                status_code=400,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_REQUEST_INCOMPLETE,
                    message=(
                        "a §6.3 request address is the four axes together:"
                        " subject, intent, freshness and asked_at. This call"
                        f" supplied {supplied}; the door fills none of the"
                        " rest, because a defaulted axis is a question nobody"
                        " asked, answered anyway (D-IMPL-98)"
                    ),
                ),
            )
        return ProductRequest(
            schema_name=product_class,
            schema_version=version,
            subject=subject,
            intent=intent,
            freshness=freshness,
            asked_at=asked_at,
            # Verbatim, exactly as the MCP tool forwards its argument map: the
            # door parses the JSON and carries what it found. It coerces
            # nothing and inspects nothing inside the object, because the
            # comparison against the declared surface belongs to the resolver,
            # which holds the class (D-IMPL-121, D-IMPL-133).
            parameters=_parameters(parameters),
        )

    def _parameters(supplied: str | None) -> Mapping[str, Any]:
        """One JSON object, parsed and carried — or refused as malformed.

        Refusal rather than a fallback: reading unparseable text as the empty
        mapping would answer a question the caller did not ask and report
        success, which is ``D-08``'s *the fabric never silently degrades a
        caller's value* on the request side of the same seam.
        """
        if supplied is None:
            return {}
        try:
            decoded = json.loads(supplied)
        except ValueError as malformed:
            raise HTTPException(
                status_code=400,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_PARAMETERS_MALFORMED,
                    message=(
                        "`parameters` is one JSON object carrying the"
                        " class-declared remainder of the question, and this"
                        f" call supplied text that is not JSON: {malformed}."
                        " JSON rather than flattened query keys because it is"
                        " self-describing — a presented 3 and a presented"
                        ' "3" stay distinguishable, so the door never guesses'
                        " at a coercion (D-IMPL-103, D-IMPL-133)"
                    ),
                ),
            ) from malformed
        if not isinstance(decoded, dict):
            raise HTTPException(
                status_code=400,
                detail=refusal_detail(
                    error_code=ERROR_PRODUCT_PARAMETERS_MALFORMED,
                    message=(
                        "`parameters` parsed as a"
                        f" {type(decoded).__name__} rather than a JSON object;"
                        " the class-declared remainder is a mapping of"
                        " parameter names to values, and a door that coerced"
                        " some other shape into one would be inventing a"
                        " question (D-IMPL-133)"
                    ),
                ),
            )
        return decoded

    return router
