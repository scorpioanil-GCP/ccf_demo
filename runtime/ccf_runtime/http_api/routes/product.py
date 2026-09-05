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

**This door has a refusal channel for exactly ONE kind, and the scope is the
ruling** (ledger row ``24.5-L-14``; ``D-IMPL-237``; ROADMAP Phase 24.5
criterion 21; the Standard §9's *"Debt gate exceeded → 409 with the debt
block"*). The resolver's answer is routed through
:func:`~ccf.products.door.door_refusal` — the same translation the two MCP
doors already run, so the three doors cannot disagree about what a refusal
is — and an envelope whose ``kind`` is
``REFUSAL_KINDS[DeclaredObligationRefusal]`` (``declared-obligation-refusal``,
the one refusal the declared-obligations gate returns) is answered as ``409``
carrying the whole envelope in the ``routes/skill.py`` body shape:
``{"kind", "refusal_type", "refusal"}``. The whole envelope, not the debt block
alone, so the gate's ``declared`` and ``observed`` numbers, the request
identity and the pre-assembly lineage all travel; the kind is compared by the
mapping's value and never by a string literal, so the token has one spelling
in the tree. The door MAPS a refusal it already receives to a status; it
decides nothing, inspects no payload, and adds no second mechanism
(``D-IMPL-237``, ``D-IMPL-238``).

**A second mapped kind, ruled at the Phase 24.5 close (Dave, 2026-09-03,
panel finding R3):** a :class:`~ccf.products.request.ProductRequestViolation`
envelope — the resolver's verdict that the QUESTION does not conform to the
class's declared contract, every reason of the vocabulary including
``24.5-FIX-02``'s ``not-a-proportion`` — answers ``400`` in the same body
shape. *"Request violation is 400-family. A 500 is a door lie."* This door
already answered ``400`` for its own two request-shape refusals (malformed
``parameters``, an unrepresentable ``asked_at``); the resolver's verdict on
the same request is the same family. Mapped by kind, not by reason, so a
seventh reason arrives as ``400`` through the same branch. Not a new gate
type and not a second mechanism: the door maps a value it already receives.

**The unruled remainder is ruled, and the two branches above are now one**
(``D-IMPL-253`` Q18 = D-18, Dave 2026-09-03; the paragraph this replaces said
every other kind *"still reaches"* :func:`~ccf.products.door.served_answer`
because *"the status code and body shape for the remaining kinds is a ruling
nobody has made"*). The ruling arrived: *"class-based statuses, but do not
hard-code all entitlement/fulfillment to 409; disclosure/suppression semantics
govern the external mapping. No known refusal may become 500."* So the two
hand-written branches are deleted and every member of
:data:`~ccf.products.refusal.REFUSAL_KINDS` gets its status from the one class
table in :mod:`ccf_runtime.http_api.refusal_status`, rendered in the body shape
both branches already used. The ``409`` and the ``400`` this door answered
before are two rows of that table and did not move.

**What 500 means here, now that no governed refusal reaches it.** A value
that proves no governed determination (``D-IMPL-260`` P-A): a bare
:class:`~ccf.products.gates.ServableProduct` or a bare refusal value, an
envelope with no replay reference or no disclosure decision, or an envelope
whose ``kind`` is not in the vocabulary — the last falls through to
:func:`~ccf.products.door.served_answer`, the rest are refused by name. Each
raises :class:`~ccf.products.door.UngovernedResolverResult` (a ``TypeError``)
naming the shape. That is an invariant violation — a value this SDK did not
mint, or did not record, claiming to be an answer — and it should look like
one rather than cross as a determination the fabric made.

**The entitlement determination travels the same path** (``D-IMPL-256``,
criterion 36; ``D-IMPL-254``'s four layers). This door used to catch
:class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementRefused` and
render a ``403`` in a *second* body shape — which was a D-27 leak channel three
ways over: a different status, a different schema and a different message from
the one a nonexistent subject received. It no longer catches it at all. The
route calls :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`,
the ONE governed step, and **encodes what it returns**: a
:class:`~ccf.projection.plan.Perspective` continues to the resolver, and a
:class:`~ccf.products.refusal.RefusalEnvelope` is rendered through the same
:func:`_refusal_response` a fabric refusal is. Dave, verbatim: *"Replay belongs
to the governed determination, not to HTTP or MCP."* Nothing on this page mints
a replay record, discloses, or reads a clock.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType
from typing import Any, Final

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from starlette.requests import Request

from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest, door_refusal, served_answer
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import RefusalRecorderProtocol
from ccf.projection.plan import Perspective
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_HTTP_ROUTE,
    govern_absence,
    govern_entitlement,
    recorded_boundary,
)
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementSourceProtocol,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_PRODUCT_DOOR_UNGOVERNED,
    ERROR_PRODUCT_PARAMETERS_MALFORMED,
    ERROR_PRODUCT_REQUEST_INCOMPLETE,
    refusal_detail,
)
from ccf_runtime.http_api.grants import grant_from_request
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND, status_for
from ccf_runtime.http_api.routes import canonical_response
from ccf_runtime.mcp.egress import ProductNotServable

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


#: :data:`~ccf.products.refusal.REFUSAL_KINDS`, read backwards.
#:
#: The body's ``refusal_type`` has been the Python class name since the first
#: mapped kind, and the two deleted branches each spelled one by hand
#: (``DeclaredObligationRefusal.__name__``). Derived here instead, so a body
#: shape that was correct for two kinds is correct for twenty-three without a
#: branch per kind — and so this module names no refusal class at all.
_TYPE_NAME_BY_KIND: Final[Mapping[str, str]] = MappingProxyType(
    {kind: refusal_type.__name__ for refusal_type, kind in REFUSAL_KINDS.items()}
)


def _type_name_for(kind: str) -> str:
    """The refusal class's own name, for the body's ``refusal_type`` member.

    Args:
        kind: :attr:`~ccf.products.refusal.RefusalEnvelope.kind`.

    Returns:
        The Python class name the kind was minted from.

    Raises:
        KeyError: ``kind`` is not in the vocabulary — the same invariant
            violation :func:`~ccf_runtime.http_api.refusal_status.status_for`
            refuses, and reached only by a caller that skipped the membership
            test this route runs first.
    """
    return _TYPE_NAME_BY_KIND[kind]


def _refusal_response(envelope: RefusalEnvelope) -> JSONResponse:
    """One governed refusal, one status class, one body shape.

    The ONE emission path for every refusal this door answers — a gate's, a
    request-conformity verdict's, and the delivery boundary's entitlement
    determination alike. That sameness is the D-27 property (``D-IMPL-253``
    amendment 2 (4)): an unauthorized principal and a nonexistent subject reach
    the consumer through this function, so the status, the schema, the field
    set and the message are the same by construction rather than by two
    branches that happen to agree.

    The status comes from the **disclosed** kind
    (:mod:`ccf_runtime.http_api.refusal_status`) and from nothing else. The
    body is the whole envelope in the ``routes/skill.py`` shape, so the debt
    block's numbers, a violation's reason and key, the request identity and the
    replay reference all travel — whatever of them the Disclosure layer
    permitted to cross (``D-IMPL-254``). This door withholds nothing of its own
    and adds nothing of its own.

    Args:
        envelope: The disclosed shell, as the fabric or the governed delivery
            boundary produced it.

    Returns:
        The response, ready to return.
    """
    return JSONResponse(
        status_code=status_for(envelope.kind),
        content={
            "kind": envelope.kind,
            "refusal_type": _type_name_for(envelope.kind),
            "refusal": json.loads(canonical_bytes(envelope)),
        },
    )


def build_router(
    deps: ApiDependencies,
    *,
    entitlement_source: ProductEntitlementSourceProtocol | None = None,
    perspective_resolver: PerspectiveResolverProtocol | None = None,
    refusal_recorder: RefusalRecorderProtocol | None = None,
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
        refusal_recorder: The deployment's ONE minting seam
            (:class:`~ccf.products.resolver.RefusalRecorderProtocol`, and the
            SDK ships :class:`~ccf.products.resolver.ReplayRefusalRecorder`
            over the store the resolver already holds). Required whenever
            ``entitlement_source`` is: a denial at this door is a governed
            determination, and ``D-IMPL-256`` (2) makes a door that cannot
            record one *not a valid governed door*. Refused at construction by
            :func:`~ccf_runtime.authz.delivery_boundary.recorded_boundary`
            rather than at the first denial, so no request ever meets a
            half-governed door.

    Raises:
        ValueError: exactly one of the two governance seams was supplied.
        UnrecordableDeliveryBoundaryError: an entitlement source was supplied
            with no conforming ``refusal_recorder``.
    """
    if (entitlement_source is None) != (perspective_resolver is None):
        raise ValueError(
            "entitlement_source and perspective_resolver are supplied"
            " together or not at all: an entitlement source with no"
            " perspective to decide about, or a perspective resolver whose"
            " output nothing checks, is a door that looks governed and"
            " enforces half a decision (15.5-06)"
        )
    if entitlement_source is not None:
        # `D-IMPL-256` (2) at this builder too, not only at `create_app`: the
        # posture belongs to *a door that entitles*, and this function is one
        # of the two ways to build one. The message names whichever builder was
        # actually called, which is the one an operator has to fix.
        recorded_boundary(
            refusal_recorder=refusal_recorder, builder="build_router"
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
        # The question is assembled BEFORE the delivery boundary decides,
        # because the governed determination records what was asked: the
        # parameters and the temporal boundary travel on the refusal's request
        # identity (`D-IMPL-256` (1)), and a door that authorized first would
        # have to re-parse them or record a question it had not read. A
        # malformed or partial address is refused here for every subject alike
        # — a request-shape verdict is a fact about the request and never about
        # the subject, so no D-27 channel opens (D-18: the request class).
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
        #
        # Built here, before the delivery boundary, because its guard is a
        # REQUEST-shape refusal and belongs with the other two: a question the
        # wire cannot carry — a `float` in `parameters`, a naive `asked_at` —
        # is refused `400` for every subject alike. It also has to precede the
        # determination, because `govern_entitlement` records the boundary the
        # caller asked as-of and refuses a naive one as a deployment defect
        # (`D-IMPL-38`); a `500` there for a value this door already knows how
        # to refuse `400` would be a door lie.
        echo = _echo(asked) if asked is not None else None
        decided = _authorized_perspective(
            request,
            tenant=tenant,
            product_class=product_class,
            version=version,
            role=role,
            asked=asked,
        )
        if isinstance(decided, JSONResponse):
            # The governed delivery boundary refused, and already recorded and
            # disclosed it. This route encodes; it decided nothing.
            return decided
        perspective = decided
        try:
            resolved = deps.product_resolver(
                tenant=tenant,
                product_class=product_class,
                version=version,
                perspective=perspective,
                request=asked,
            )
        except ProductNotServable as absent:
            # `D-IMPL-260` P-C: the absence of a servable product at an address
            # the caller resolved and was entitled to is a governed
            # determination — the same `subject-unavailable` the assembler
            # reaches for a subject nothing resolves — recorded and disclosed
            # at the boundary and rendered through the ONE refusal path below.
            # The status is the kind's (404); the body is the common shell.
            grant = grant_from_request(request)
            # Both narrowed by `_authorized_perspective` having RETURNED a
            # perspective: it refuses 503 before either could be absent.
            assert grant is not None
            assert entitlement_source is not None
            return _refusal_response(
                govern_absence(
                    grant=grant,
                    tenant=tenant,
                    product_class=product_class,
                    product_version=version,
                    parameters=dict(asked.parameters) if asked is not None else {},
                    asked_at=asked.asked_at if asked is not None else None,
                    surface=SURFACE_HTTP_ROUTE,
                    address=request.url.path,
                    perspective=perspective,
                    absent=absent,
                    entitlement_source=entitlement_source,
                    refusal_recorder=recorded_boundary(
                        refusal_recorder=refusal_recorder, builder="build_router"
                    ),
                )
            )
        # D-18: every kind in the vocabulary, one status by class, one body.
        # The envelope is the door's own translation (the MCP doors run the
        # same function); the membership test is against `REFUSAL_KINDS`
        # through the status table, never a literal (T-24.5-38). A `kind` the
        # table does not hold is not a refusal this SDK minted, so it falls
        # through to `served_answer` and reaches the client as the door fault
        # it is — which is the one thing 500 is now reserved for.
        envelope = door_refusal(resolved)
        if envelope is not None and envelope.kind in STATUS_BY_KIND:
            return _refusal_response(envelope)
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
        request: Request,
        *,
        tenant: str,
        product_class: str,
        version: str,
        role: str | None,
        asked: ProductRequest | None,
    ) -> Perspective | JSONResponse:
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

        **The entitlement decision is not made here** (``D-IMPL-256``;
        criterion 36). It is made by
        :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`, which
        runs the ruled sequence — *identity/policy → determination → replay →
        disclosure shaping* — and hands back either the entitled perspective or
        a shell that is **already recorded and already disclosed**. This
        function encodes that return and does nothing else: it holds no
        ``except`` clause for that refusal, calls no recorder, discloses
        nothing and reads no clock (``D-IMPL-98``). A denial is rendered
        through :func:`_refusal_response` — the *same* function a gate refusal
        goes through — which is what makes an unauthorized principal and a
        nonexistent subject observationally equivalent at this door rather than
        equivalent by two branches agreeing (``D-IMPL-253`` amendment 2 (4)).

        Args:
            request: The live request, for the verified grant and for the path
                the caller addressed.
            tenant: The tenant from the path this door resolved.
            product_class: The class from the path this door resolved.
            version: The class's lane from the same path, recorded on the
                determination's request identity.
            role: The caller's ``?role=`` request, or ``None``.
            asked: The typed question this door already assembled, or ``None``
                when the caller posed none. Its ``parameters`` and ``asked_at``
                are what the determination records as having been asked; with
                no question the boundary is ``None``, the positive *the caller
                deferred to the server's decision instant*.

        Returns:
            The authorized perspective, or the response encoding an
            already-recorded governed denial.

        Raises:
            HTTPException: 503 with
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
        decided = govern_entitlement(
            grant=grant,
            tenant=tenant,
            product_class=product_class,
            product_version=version,
            requested_role=role,
            parameters=dict(asked.parameters) if asked is not None else {},
            asked_at=asked.asked_at if asked is not None else None,
            surface=SURFACE_HTTP_ROUTE,
            # What the caller addressed, never what the fabric resolved it to.
            address=request.url.path,
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
            # The recorder this router was BUILT with. `recorded_boundary`
            # already refused to build an entitling door without one, so this
            # read cannot fail; it is spelled as the same function rather than
            # as an assertion so the posture has exactly one name in the tree
            # (`D-IMPL-256` (2)). It is a narrowing, not a per-request check:
            # there is no configuration in which it answers differently for two
            # requests to the same door.
            refusal_recorder=recorded_boundary(
                refusal_recorder=refusal_recorder, builder="build_router"
            ),
        )
        if isinstance(decided, RefusalEnvelope):
            return _refusal_response(decided)
        return decided

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
