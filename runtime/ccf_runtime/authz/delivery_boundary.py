"""The governed delivery-boundary step — determination, replay and disclosure in one call.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11, §8.3). The rulings of
record are ``D-IMPL-256`` and ``D-IMPL-254``.

The invariant, in Dave's own words (``D-IMPL-256``, criterion 36):

    *"Every governed determination that crosses a CCF delivery boundary —
    fulfilled or refused, tool or resource, authorized or denied — must reach
    the replay writer before the response is released. A delivery boundary
    unable to satisfy that invariant is unavailable, not partially governed."*

And the sequence principle it turns on, verbatim:

    *"The sequence should conceptually remain: request → identity/policy →
    determination → replay → disclosure shaping → transport encoding — not:
    request → determination → HTTP/MCP → transport notices refusal → writes
    replay. Replay belongs to the governed determination, not to HTTP or MCP.
    That matters because otherwise the standing-resource/tool asymmetry simply
    reappears somewhere else."*

**This module is the delivery-boundary DETERMINATION step of ``D-IMPL-254``'s
Authority layer, and replay belongs here.** A transport calls
:func:`govern_entitlement` and **encodes what it returns**. It does not catch
:class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementRefused`, does
not build a shell, does not read a clock and does not mint a record. The one
``except`` clause for that refusal anywhere under this package is the one in
:func:`govern_entitlement` below, and its uniqueness is what makes the sequence
structural rather than conventional — a second one at a transport would put the
transport back in charge of minting replay, which is the shape the ruling names
and rejects.

What this module imports, and what it deliberately does not
-----------------------------------------------------------
It imports the fabric's own product package and this package's entitlement
seam, and **no transport**: nothing here names the HTTP tree or the MCP tree
directly. A determination module that imported a transport would be the
inversion criterion 36 forbids, in the same spirit as
``tests/invariants/test_mcp_role_separation.py``'s rule that the MCP roles are
separate modules importing none of their siblings.

**That statement is about this module's own imports, and it is deliberately
not transitive.** The entitlement seam module beside this one already reaches
the shared HTTP error vocabulary and the MCP verified-token type, because a
single definition of *entitled* has to be renderable in both protocols and has
to name the type a verified caller arrives as. That is unchanged and correct,
and nobody should "fix" it: the discipline is that the *determination* does not
reach for a transport's machinery, not that a vocabulary two doors share must
be duplicated per door. It is also why the verified-token type is read from
that seam module here rather than from where it is defined — it is part of the
seam this module composes, and taking it from the seam keeps this module's own
import list to two packages.

Algorithmic module (CINV-03): no LLM client, and no wall-clock read of any
kind — the only instant this module knows is the one the deployment declared on
its own entitlement source.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

from ccf.products.refusal import (
    RefusalEnvelope,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.resolver import RefusalRecorderProtocol
from ccf.projection.plan import Perspective
from ccf.replay.record import NO_ROLE_RESOLVED, PolicyBinding
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementRefused,
    ProductEntitlementSourceProtocol,
    TokenGrant,
    entitled_perspective,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "SURFACE_HTTP_ROUTE",
    "SURFACE_MCP_RESOURCE",
    "SURFACE_MCP_TOOL",
    "UnrecordableDeliveryBoundaryError",
    "govern_entitlement",
    "recorded_boundary",
]


#: The three delivery surfaces, as the mechanism tokens
#: :attr:`~ccf.products.refusal.ResourceRequestIdentity.surface` carries.
#:
#: Defined **once**, here, beside the governed step that mints them, and never
#: as a literal at a door. Three doors spelling one surface three ways is three
#: vocabularies in the audit record, and an examiner filtering on a surface
#: would silently miss two of them.
SURFACE_HTTP_ROUTE: Final[str] = "http-route"
SURFACE_MCP_TOOL: Final[str] = "mcp-tool"
SURFACE_MCP_RESOURCE: Final[str] = "mcp-resource"


class UnrecordableDeliveryBoundaryError(ValueError):
    """A delivery boundary that entitles without a recorder is not built.

    ``D-IMPL-256`` (2), Dave, verbatim and stated **once** so the three
    builders that raise this write no prose of their own:

        *"a door configured to make governed determinations without the ability
        to record them is not a valid governed door."*

    His posture on the alternative, in the same ruling: a door that served
    authorized requests normally *"but fail[ed] closed only when denial
    happens"* would *"make auditability contingent on outcome"* — and it would
    reopen the observational leak the checker measured, because unauthorized
    and nonexistent requests would then diverge merely because the door was
    misconfigured.

    A :class:`ValueError` rather than a new base, on this codebase's own
    construction-refusal posture: a boot that cannot satisfy an invariant stops
    at construction rather than at the first request
    (*"Prefer fail-at-construction/boot where practical"*).
    """


def recorded_boundary(
    *, refusal_recorder: object | None, builder: str
) -> RefusalRecorderProtocol:
    """Return the recorder, or refuse to build an entitling delivery boundary.

    The ONE construction-time check ``D-IMPL-256`` (2) asks for. The three
    builders — the HTTP app, the egress MCP server and the experience MCP
    server — call it and add nothing: the posture is stated in
    :class:`UnrecordableDeliveryBoundaryError` and nowhere else, so three doors
    cannot drift into three explanations of one rule.

    **Structural conformance, and no I/O probe.**
    :class:`~ccf.products.resolver.RefusalRecorderProtocol` is
    ``@runtime_checkable``, so the check is real without calling anything. A
    probe that appended a record to prove the store works would write a record
    nobody asked for — an artifact in the audit trail describing no decision,
    which is the opposite of what an audit trail is for. A store that is
    reachable at construction and broken at the first determination is the case
    the seam's own *"a failure to record is a failure to decide"* posture
    covers.

    Args:
        refusal_recorder: What the builder was handed. ``None`` is the
            commonest failure — a deployment that bound an entitlement source
            and forgot the recorder.
        builder: The builder's own name, so the message names where to fix it
            rather than where it was noticed.

    Returns:
        ``refusal_recorder``, unchanged, typed as the Protocol.

    Raises:
        UnrecordableDeliveryBoundaryError: it is absent or does not conform.
    """
    if refusal_recorder is None:
        raise UnrecordableDeliveryBoundaryError(
            f"{builder} was asked to build an entitling delivery boundary with"
            " no `refusal_recorder=`; a door configured to make governed"
            " determinations without the ability to record them is not a valid"
            " governed door (D-IMPL-256 (2)). Pass a"
            " `ccf.products.resolver.RefusalRecorderProtocol` — the SDK ships"
            " `ReplayRefusalRecorder` over the same artifact store the resolver"
            " already holds — or build a boundary that does not entitle"
        )
    if not isinstance(refusal_recorder, RefusalRecorderProtocol):
        raise UnrecordableDeliveryBoundaryError(
            f"{builder} was passed a `refusal_recorder=` of type"
            f" {type(refusal_recorder).__name__}, which does not conform to"
            " `ccf.products.resolver.RefusalRecorderProtocol`; a door"
            " configured to make governed determinations without the ability"
            " to record them is not a valid governed door (D-IMPL-256 (2))."
            " The conformance check is structural — the recorder needs a"
            " `record` method — and it runs at construction rather than at the"
            " first denial, so a misconfigured door never answers at all"
        )
    return refusal_recorder


def govern_entitlement(
    *,
    grant: TokenGrant,
    tenant: str,
    product_class: str,
    product_version: str | None,
    requested_role: str | None,
    parameters: Mapping[str, Any],
    asked_at: datetime | None,
    surface: str,
    address: str,
    entitlement_source: ProductEntitlementSourceProtocol,
    perspective_resolver: PerspectiveResolverProtocol,
    refusal_recorder: RefusalRecorderProtocol,
) -> Perspective | RefusalEnvelope:
    """Decide entitlement, and on a denial mint and disclose before returning.

    The ONE governed step every entitling delivery boundary calls, in
    ``D-IMPL-256``'s ruled sequence: **request → identity/policy →
    determination → replay → disclosure shaping → transport encoding**. The
    first five happen here; only the sixth is the transport's, and by the time
    it runs there is nothing left to decide — a caller receives either the
    entitled :class:`~ccf.projection.plan.Perspective` or an **already-recorded,
    already-disclosed** shell.

    The order, and the order is the property:

    1. ``determined_at = entitlement_source.clock()`` — read **once**, before
       the determination, because it is the instant *of* the determination. No
       other clock is read in this module and no wall-clock call appears in it
       at all, so the audit event the source appends and the replay record
       minted below carry the same instant by construction rather than by two
       reads that happen to agree.
    2. :func:`~ccf_runtime.authz.product_entitlement.entitled_perspective` runs
       the one resolution order every door runs. An entitled request returns
       the perspective and **writes nothing**: a fulfilled decision is the
       resolver's to record, and a second record here would make one decision
       two.
    3. A denial becomes
       :class:`~ccf.products.refusal.SubjectUnavailableRefusal` with
       ``cause="unauthorized"`` — the one canonical outcome an unauthorized
       principal shares with a nonexistent subject (``D-IMPL-253`` Q27) —
       enveloped with the request identity **and** a
       :class:`~ccf.products.refusal.ResourceRequestIdentity`, and handed to
       :meth:`~ccf.products.resolver.RefusalRecorderProtocol.record`, which
       appends the internal truth and returns the disclosed shell.

    **A failed append propagates.** Nothing here catches the store's error: *a
    failure to record is a failure to decide*, which is the resolver's own
    posture and is what makes criterion 36 hold at the boundary rather than
    only in the fabric.

    Args:
        grant: The verified caller identity. Never a caller's claim.
        tenant: The tenant the request was addressed under — established by the
            calling surface, never read from a caller's body.
        product_class: The Context Product class requested.
        product_version: The class's own lane, or ``None`` when the surface
            named none.
        requested_role: The role the caller asked for, or ``None`` on a surface
            with no way to ask. A denial reached before any role is resolved
            records :data:`~ccf.replay.record.NO_ROLE_RESOLVED`, which is the
            door's own positive claim rather than a ``None`` the recorder would
            have to interpret.
        parameters: What the caller supplied, for the request identity.
        asked_at: The instant the caller asked as-of, or ``None`` — the
            positive *the caller deferred to the server's decision instant*.
            Refused when it carries no UTC offset, on
            the egress door's own posture: an ambiguous boundary
            replays differently on every host (``D-IMPL-38``).
        surface: One of :data:`SURFACE_HTTP_ROUTE`, :data:`SURFACE_MCP_TOOL`,
            :data:`SURFACE_MCP_RESOURCE`.
        address: What the caller addressed — the product URI a standing
            resource names, or the route path an HTTP caller asked for. What
            was asked for, never what the fabric resolved it to.
        entitlement_source: The deployment's entitlement decision seam, and the
            holder of the determination clock.
        perspective_resolver: The deployment's role-derivation seam.
        refusal_recorder: The ONE minting seam. Checked at construction by
            :func:`recorded_boundary`, so by the time this runs it conforms.

    Returns:
        The entitled perspective, or the disclosed refusal shell carrying the
        address of its own record.

    Raises:
        ValueError: ``asked_at`` carries no UTC offset, or the source's clock
            returned a naive instant. Both are deployment defects that would
            make a determination replay differently on a different host.
        Exception: whatever the artifact store raises on append, deliberately
            uncaught.
    """
    if asked_at is not None and (
        asked_at.tzinfo is None or asked_at.tzinfo.utcoffset(asked_at) is None
    ):
        raise ValueError(
            f"asked_at {asked_at.isoformat()!r} carries no UTC offset; the"
            " instant a question was asked as-of is the boundary a replay"
            " resolves against and cannot be ambiguous (D-IMPL-38)"
        )

    # (1) The determination instant, read ONCE and first.
    determined_at = entitlement_source.clock()
    if determined_at.tzinfo is None or determined_at.utcoffset() is None:
        raise ValueError(
            f"the entitlement source's clock returned {determined_at.isoformat()!r},"
            " which carries no UTC offset; the instant a governed determination"
            " was reached is what its replay record and its audit event are"
            " both stamped from, and an instant whose offset is the deciding"
            " host's local configuration replays differently on every host"
            " (D-IMPL-38). Declare the source's clock so that it returns a"
            " timezone-aware instant"
        )

    try:
        # (2) The one resolution order. Entitled: return it, write nothing.
        return entitled_perspective(
            grant=grant,
            tenant=tenant,
            product_class=product_class,
            requested_role=requested_role,
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
        )
    except ProductEntitlementRefused as refused:
        # (3) The governed determination. `cause="unauthorized"` is internal
        # truth; what a consumer sees is the Disclosure layer's decision, taken
        # inside `record` below and nowhere else.
        envelope = envelope_for(
            SubjectUnavailableRefusal(
                cause="unauthorized",
                detail=refused.message,
                error_code=refused.error_code,
            ),
            request=RequestIdentity(
                product_id=product_class,
                product_version=product_version,
                parameters=parameters,
                temporal_boundary=asked_at,
            ),
            resource=ResourceRequestIdentity(
                surface=surface,
                address=address,
                tenant_id=tenant,
                determined_at=determined_at,
            ),
            # The policy that DECIDED, carried on the refusal from the source's
            # own single resolution (D-34, `24.6-08`). The empty tuple is the
            # positive "no policy was consulted", which is the honest answer
            # for the subject-conflict path and for a tenant that registered
            # none.
            policy_bindings=(
                (refused.policy,) if refused.policy is not None else ()
            ),
        )
        # The mint AND the disclosure, both inside the seam and in that order.
        # Nothing is disclosed before it is recorded, and a failed append
        # propagates rather than releasing an unrecorded response.
        return refusal_recorder.record(
            envelope,
            perspective=Perspective(
                principal_id=grant.client_id,
                role=requested_role if requested_role is not None else NO_ROLE_RESOLVED,
            ),
            recorded_at=determined_at,
            policy_bindings=(
                (
                    PolicyBinding(
                        key=refused.policy.identity,
                        version=refused.policy.version,
                    ),
                )
                if refused.policy is not None
                and refused.policy.version is not None
                else ()
            ),
        )
