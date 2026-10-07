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
Authority layer, and replay belongs here** — SDK-defined under CLAUDE.md §11
and ``D-IMPL-256``, not whitepaper-derived. A transport calls
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
It imports the fabric's own product package, this package's entitlement seam,
and — since ``D-IMPL-345`` — the shared door error vocabulary for the four
``evidence-*`` codes a dereference determination records. It imports **no
transport machinery**: nothing here builds a response, reads a request object
or reaches a router. A determination module that imported a transport would be
the inversion criterion 36 forbids, in the same spirit as
``tests/invariants/test_mcp_role_separation.py``'s rule that the MCP roles are
separate modules importing none of their siblings. Knowing a door's error
*vocabulary* is not that inversion, and is the permission the entitlement seam
beside this one already has, in
``tests/invariants/test_delivery_boundary_replay.py``'s own words: *"The
determination layer is allowed to know a door's error vocabulary; a door is
not allowed to make the determination."*

**That statement is about this module's own imports, and it is deliberately
not transitive.** The entitlement seam module beside this one already reaches
the shared HTTP error vocabulary and the MCP verified-token type, because a
single definition of *entitled* has to be renderable in both protocols and has
to name the type a verified caller arrives as. That is unchanged and correct,
and nobody should "fix" it: the discipline is that the *determination* does not
reach for a transport's machinery, not that a vocabulary two doors share must
be duplicated per door. It is also why the verified-token type is read from
that seam module here rather than from where it is defined — it is part of the
seam this module composes, and taking it from the seam keeps this module's
import list to the packages it genuinely composes.

Algorithmic module (CINV-03): no LLM client, and no wall-clock read of any
kind — the only instant this module knows is the one the deployment declared on
its own entitlement source.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Protocol, runtime_checkable

from pydantic import ValidationError

from ccf.artifacts.protocol import (
    ArtifactNotFound,
    ArtifactStoreError,
    ArtifactStoreProtocol,
    MovingTargetRefused,
    held_content_address,
    parse_artifact_uri,
)
from ccf.authz.capability import ArtifactRead, Authorized, ReplayRead, verify_any
from ccf.controlplane.audit import AuditLog
from ccf.contracts.base import CCFContract
from ccf.erasure.store import ErasedContentRefused, ErasureConsultingStore
from ccf.products.disclosure import DISCLOSURE_FULL, DISCLOSURE_MINIMAL, DisclosureLevel
from ccf.products.provenance import EffectiveRequest, ProvenanceSource
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    GovernedRefusalRaised,
    ResolvedByTheResolver,
    RefusalEnvelope,
    ErasedContentRefusal,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.resolver import RefusalRecorderProtocol
from ccf.projection.plan import Perspective
from ccf.replay.engine import (
    ReplayDivergence,
    ReplayUnresolvable,
    resolve_artifact,
)
from ccf.replay.record import (
    NO_ASSEMBLY_REFUSAL,
    NO_ROLE_RESOLVED,
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
)
from ccf_runtime.http_api.errors import (
    ERROR_EVIDENCE_ABSENT,
    ERROR_EVIDENCE_CLASS_UNRECOVERABLE,
    ERROR_EVIDENCE_DISCLOSURE_WITHHELD,
    ERROR_EVIDENCE_PRINCIPAL_MISMATCH,
)
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementRefused,
    ProductEntitlementSourceProtocol,
    TokenGrant,
    entitled_perspective,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "DEREFERENCE_PRODUCT_ID",
    "EVIDENCE_READ_KINDS",
    "EVIDENCE_SURFACES",
    "EvidenceReadAuthority",
    "SURFACE_HTTP_ARTIFACT_READ",
    "SURFACE_HTTP_REPLAY_READ",
    "SURFACE_HTTP_ROUTE",
    "SURFACE_MCP_RESOURCE",
    "SURFACE_MCP_TOOL",
    "DereferenceRequest",
    "DereferencedEvidence",
    "DisclosingRecorderProtocol",
    "UnconsultedDeliveryBoundaryError",
    "UnrecordableDeliveryBoundaryError",
    "disclosing_boundary",
    "govern_absence",
    "govern_dereference",
    "govern_entitlement",
    "govern_erasure",
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

#: The two evidence-read surfaces ``D-IMPL-345`` adds. Separate tokens from
#: :data:`SURFACE_HTTP_ROUTE` because a dereference is a different question
#: from a serve, and an examiner reading a record must be able to tell which
#: was asked without inferring it from the address.
SURFACE_HTTP_REPLAY_READ: Final[str] = "http-replay-read"
SURFACE_HTTP_ARTIFACT_READ: Final[str] = "http-artifact-read"

#: The surfaces a read-refusal record can have been minted at. One of the two
#: constants that together identify such a record (:data:`DEREFERENCE_PRODUCT_ID`
#: is the other) — both, never either, so a record forged through the open
#: write path cannot present one and borrow the other's meaning.
#:
#: :data:`SURFACE_MCP_RESOURCE` is a member since the D-IMPL-353 join: the MCP
#: artifact server's blob and presence resources dereference through
#: :func:`govern_dereference` under that surface identity (§2 P5), so the
#: read-refusal records they mint must be recognized as read refusals — Lane
#: MCP measured that without this member an MCP-minted read refusal was
#: withheld from its own principal at hold 2 as a record with no recoverable
#: class.
EVIDENCE_SURFACES: Final[frozenset[str]] = frozenset(
    {SURFACE_HTTP_REPLAY_READ, SURFACE_HTTP_ARTIFACT_READ, SURFACE_MCP_RESOURCE}
)

#: The two kinds under which governed evidence is dereferenced (D-IMPL-353
#: §1.2): the artifact door's ``artifact.read`` and the replay doors'
#: ``replay.read``. :func:`govern_dereference` verifies the capability against
#: whichever it was minted for, by identity, before its first real statement.
EVIDENCE_READ_KINDS: Final[tuple[type[ArtifactRead] | type[ReplayRead], ...]] = (
    ArtifactRead,
    ReplayRead,
)

#: The static type of :func:`govern_dereference`'s first parameter. A handler
#: holding any other kind — a write capability, a product-retrieve capability —
#: is a ``mypy --strict`` error at the call (§1.5b), and a forced call dies at
#: ``verify_any`` (§1.5c).
EvidenceReadAuthority = Authorized[ArtifactRead] | Authorized[ReplayRead]

#: The ``product_id`` every dereference refusal carries in its request
#: identity, for every outcome (``D-IMPL-345`` R-4). A mechanism constant, not
#: a recovered class: :func:`~ccf.products.disclosure.disclose` leaves
#: ``request`` untouched at every level because on a serve it is what the
#: caller itself asked, and a dereference caller asks only for an address — so
#: anything recovered from the target and placed here would cross the boundary
#: below ``full`` and tell the caller that the target exists and what class it
#: was decided on.
DEREFERENCE_PRODUCT_ID: Final[str] = "ccf.evidence-dereference"


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


class UnconsultedDeliveryBoundaryError(TypeError):
    """A governed evidence read was handed a store that does not consult the erasure index (SEC-009; PM5, panel C5; `D-IMPL-374`).

    U12: the erasure consult is composed ALWAYS, at every store construction
    site (:func:`~ccf.erasure.compose_erasure_consult`).
    :func:`govern_dereference` is public, and it read the consult only when its
    store happened to be an :class:`~ccf.erasure.ErasureConsultingStore` — so a
    door built outside the SDK over a store it never composed served erased
    bytes with no refusal at all. Raised after the capability check and before
    anything is read, recorded or clocked: a wiring defect, refused where an
    operator sees it, never a determination about a caller.
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


def _determined_at(entitlement_source: ProductEntitlementSourceProtocol) -> datetime:
    """The one instant a governed determination is stamped from.

    Read ONCE per determination, off the entitlement source's own declared
    clock, and refused when it carries no UTC offset: the instant is what the
    replay record and the audit event are both stamped from, and an instant
    whose offset is the deciding host's local configuration replays
    differently on every host (``D-IMPL-38``).
    """
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
    return determined_at


def govern_absence(
    *,
    grant: TokenGrant,
    tenant: str,
    product_class: str,
    product_version: str | None,
    parameters: Mapping[str, Any],
    asked_at: datetime | None,
    surface: str,
    address: str,
    perspective: Perspective,
    absent: LookupError,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: RefusalRecorderProtocol,
) -> RefusalEnvelope:
    """The governed determination for a product class the deployment does not serve.

    ``D-IMPL-260`` P-C (Dave, verbatim): *"an unregistered product class must
    reach the caller as the common shell; the status may stay 404."* Before
    this step, a deployment resolver's ``ProductNotServable`` — the absence of
    a gate-admitted product at the address the caller resolved and was
    entitled to — left each door in that door's own vocabulary: an
    ``HTTPException(404, str(absent))`` on HTTP, an opaque runtime failure on
    the MCP tool, a transport error on the resources. A caller could tell
    *there is no such class* from *there is no such subject* by the shape of
    the non-answer, and none of the three was a recorded decision.

    It is the same determination the assembler reaches for a subject nothing
    resolves — :class:`~ccf.products.refusal.SubjectUnavailableRefusal` with
    ``cause="nonexistent"`` — minted here at the boundary because the
    resolver that would have minted it is the one that has nothing to serve.
    Recorded THEN disclosed, through the same
    :class:`~ccf.products.resolver.ReplayRefusalRecorder` an entitlement denial
    goes through, under the same
    :class:`~ccf.products.refusal.ResourceRequestIdentity`, and rendered by
    each door through the same function its other refusals go through — so
    the three doors say one thing, and a consumer reads *subject unavailable*
    with a replay reference behind it.

    **What it is not.** Not a catch-all: only the typed absence — a
    ``LookupError`` the deployment's resolver raised to say *nothing is
    servable there* — reaches this step, and a transport that catches more
    than that here would be converting a runtime fault into a governed "no"
    the fabric never made (``D-IMPL-253`` Q20). Dimension 2 pins nothing: no
    policy decided the absence. Dimension 4 carries the perspective the
    caller was already entitled under — the role that participated
    (``D-IMPL-260`` P-D).

    Args:
        grant: The verified caller.
        tenant: The tenant the caller addressed.
        product_class: The class the caller addressed and was entitled to.
        product_version: The class's lane, or ``None`` when the surface named
            none.
        parameters: What the caller supplied, for the request identity.
        asked_at: The instant asked as-of, or ``None`` (the caller deferred to
            the server's decision instant).
        surface: One of the three surface tokens.
        address: What the caller addressed, verbatim.
        perspective: The perspective the delivery boundary already authorized
            for this call — the entitlement step returned it.
        absent: The resolver's own statement of the absence. Its text is the
            internal ``detail``; what a consumer sees of it is the Disclosure
            layer's decision.
        entitlement_source: The source whose declared clock stamps the
            determination.
        refusal_recorder: The seam that mints the record and discloses.

    Returns:
        The disclosed shell, carrying the replay reference of the record this
        determination produced.
    """
    determined_at = _determined_at(entitlement_source)
    envelope = envelope_for(
        SubjectUnavailableRefusal(
            cause="nonexistent",
            detail=str(absent),
            error_code=None,
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
        policy_bindings=(),
    )
    return refusal_recorder.record(
        envelope,
        perspective=Perspective(
            principal_id=grant.client_id, role=perspective.role
        ),
        # `D-IMPL-358` step 5 section F: THE QUESTION'S INSTANT bounds the
        # record. This read `determined_at`, while the comment below already
        # claimed the boundary stayed the question's — the code did not do what
        # the comment said. No control caught it because every one in
        # `tests/authz/test_delivery_boundary.py` passed `asked_at=DETERMINED_AT`,
        # so the two readings were the same assertion and neither could fail.
        recorded_at=asked_at if asked_at is not None else determined_at,
        # `D-IMPL-358` step 5: the LIVE determination instant, carried beside
        # the record's own boundary rather than collapsed into it. Where an
        # `asked_at` exists the boundary stays the QUESTION's instant; where a
        # governed surface genuinely has none, the ruled resource-form boundary
        # (`D-IMPL-256` (1)) is retained and this says so separately.
        served_at=determined_at,
        policy_bindings=(),
        # Dimension 2: the absence is decided at the door, before any
        # resolver could run, and the record SAYS so with its reason — a
        # positive absence stated by the door, never inferred by the seam
        # from a keyword the door left out (`D-IMPL-264` D-09/D-10 am.1).
        resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
    )


def govern_raised_refusal(
    *,
    raised: GovernedRefusalRaised,
    tenant: str,
    product_class: str,
    product_version: str | None,
    parameters: Mapping[str, Any],
    asked_at: datetime | None,
    surface: str,
    address: str,
    perspective: Perspective,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: RefusalRecorderProtocol,
) -> RefusalEnvelope:
    """The governed determination a resolver RAISED rather than returned (`D-IMPL-304`).

    The mirror of :func:`govern_absence` for the typed handoff
    :class:`~ccf.products.refusal.GovernedRefusalRaised`: a producer or adapter
    that held a refusal the fabric made — the frozen cp-05 low road's
    pre-resolution refusal is the reproduction — and could not return it as a
    value. Before this step that raise reached each door's generic fault
    clause and left as an opaque ``ccf-runtime-failure``: no envelope, no
    record, and a consumer reading ``producer-unavailable`` for a
    determination that was in fact made.

    **What it does, in the ruled order.** Builds the envelope from the raised
    refusal with the request identity the raiser supplied or this boundary's
    own, carrying the raised :class:`~ccf.products.provenance.EffectiveRequest`
    as provenance where that is what the raiser held; records it through the
    ONE recorder the door already holds, stamped with the QUESTION's instant
    (the resolver's own pre-resolution refusals are stamped the same way) and
    with ``resolution=`` exactly the state the raiser stated; returns what the
    recorder returned, for the door's normal disclosure and emission path. An
    envelope the raiser had ALREADY recorded — one carrying a replay reference
    — passes through untouched, as :func:`~ccf.products.door.door_refusal`
    would take it from a returning resolver.

    **What it is not.** Not a catch-all: only the typed handoff reaches it,
    and the boundary that calls it must keep its generic fault clause exactly
    as it was. **A recording failure remains a failure**: whatever the store
    raises propagates, so no governed response escapes without its record. And
    a handoff stating :data:`~ccf.products.refusal.RESOLVED_BY_THE_RESOLVER`
    is refused here as a ``TypeError`` — a door holds no resolver evidence and
    will not manufacture a resolution state — which the door then reports as
    the programming error it is.
    """
    resolution = raised.resolution
    if isinstance(resolution, ResolvedByTheResolver):
        raise TypeError(
            "a GovernedRefusalRaised reached a delivery boundary stating"
            " RESOLVED_BY_THE_RESOLVER; that state is valid only inside a"
            " resolver's acquisition seam, and a door holds no resolver evidence"
            " to record — state the EffectiveRequest evidence or an explicit"
            " ResolutionNotApplicable (D-IMPL-304, D-IMPL-264 amendment 1)"
        )
    determined_at = _determined_at(entitlement_source)
    if isinstance(raised.refusal, RefusalEnvelope):
        if raised.refusal.replay_reference != NO_REPLAY_REFERENCE:
            return raised.refusal
        envelope = raised.refusal
    else:
        provenance = resolution if isinstance(resolution, EffectiveRequest) else None
        envelope = envelope_for(
            raised.refusal,
            request=raised.request
            if raised.request is not None
            else RequestIdentity(
                product_id=product_class,
                product_version=product_version,
                parameters=dict(parameters),
                temporal_boundary=asked_at,
            ),
            policy_bindings=provenance.applied if provenance is not None else (),
            provenance=provenance,
            resource=ResourceRequestIdentity(
                surface=surface,
                address=address,
                tenant_id=tenant,
                determined_at=determined_at,
            ),
        )
    return refusal_recorder.record(
        envelope,
        perspective=perspective,
        recorded_at=asked_at if asked_at is not None else determined_at,
        # `D-IMPL-358` step 5: the LIVE determination instant, carried beside
        # the record's own boundary rather than collapsed into it. Where an
        # `asked_at` exists the boundary stays the QUESTION's instant; where a
        # governed surface genuinely has none, the ruled resource-form boundary
        # (`D-IMPL-256` (1)) is retained and this says so separately.
        served_at=determined_at,
        policy_bindings=(),
        resolution=resolution,
    )


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
       at all. The replay record minted below is stamped from this read; the
       ``authz_decision`` audit event the source appends inside its own
       ``authorize`` is stamped from a SECOND read of the same clock, so the
       two agree exactly under a pinned clock and to within one read under a
       wall clock. Carrying this instant INTO ``authorize`` is a Protocol
       change recorded as a carried finding at the Phase 24.6 close, not a
       claim this docstring makes. (Its earlier text claimed *"the same
       instant by construction"*, which was false.)
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
            with no way to ask. Handed to the perspective resolver and used for
            nothing else here: the role a denial RECORDS is the one the
            determination was made under —
            :attr:`~ccf_runtime.authz.product_entitlement.ProductEntitlementRefused.role`,
            the resolved perspective's role the source decided against — and
            a denial reached before any role of the caller's was established
            records :data:`~ccf.replay.record.NO_ROLE_RESOLVED`, the door's
            own positive claim rather than a ``None`` the recorder would have
            to interpret (``D-IMPL-260`` P-D: *"the role that actually
            participated, explicit absence if none was established, never a
            substituted default"*).
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
    determined_at = _determined_at(entitlement_source)

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
                # Dimension 4: the role the source DECIDED under, off the
                # determination itself — not the role the caller asked for,
                # which the resolver may have replaced or defaulted — and the
                # positive absence when none was established (D-IMPL-260 P-D).
                role=refused.role if refused.role is not None else NO_ROLE_RESOLVED,
            ),
            # `D-IMPL-358` step 5 section F: THE QUESTION'S INSTANT bounds the
            # record — see the sibling in `govern_absence` for why this was wrong
            # and why no control caught it. `govern_dereference` below keeps
            # `determined_at` and is NOT a third instance: a resource
            # dereference takes no `asked_at`, so the ruled resource-form
            # boundary (`D-IMPL-256` (1)) is the only instant it has.
            recorded_at=asked_at if asked_at is not None else determined_at,
            # `D-IMPL-358` step 5: the LIVE determination instant, carried beside
            # the record's own boundary rather than collapsed into it. Where an
            # `asked_at` exists the boundary stays the QUESTION's instant; where a
            # governed surface genuinely has none, the ruled resource-form boundary
            # (`D-IMPL-256` (1)) is retained and this says so separately.
            served_at=determined_at,
            # Dimension 2: entitlement is refused before resolution begins —
            # the resolver never ran, so there is no resolution to record and
            # the record says WHY there is none, in the `NO_ROLE_RESOLVED`
            # voice: a positive absence the door states, never one the seam
            # infers from silence (`D-IMPL-264` D-09/D-10 am.1).
            resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
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


# =========================================================================
# D-IMPL-345 — a dereference is a governed determination
# =========================================================================


@runtime_checkable
class DisclosingRecorderProtocol(RefusalRecorderProtocol, Protocol):
    """A recorder that can also state the level it would disclose at.

    ``D-IMPL-345`` R-2, Dave, verbatim: *"Read disclosure authority through
    the recorder, not the entitlement source. The entitlement source answers
    whether the caller is entitled; it is not the authority for what the serve
    disclosed."*

    The two extra members are the two
    :class:`~ccf.products.resolver.ReplayRefusalRecorder` already carries as
    fields, so the reference recorder conforms without changing. They are
    declared here rather than on
    :class:`~ccf.products.resolver.RefusalRecorderProtocol` because a door
    that only records refusals needs neither, and the MCP builders must keep
    accepting exactly what they accept today (``D-IMPL-345`` §6.3).

    ``disclosure_level_for`` is typed as the ``Callable`` attribute the
    recorder holds rather than as a method: the recorder takes it by
    injection, and a Protocol that declared a method would refuse the shipped
    object.

    **``record`` is INHERITED rather than restated**, which is what "the two
    extra members on top" means when it is said in code instead of in prose.
    It was restated once, and the copy drifted: it narrowed ``resolution`` to
    ``object`` and dropped the six optional keywords the seam actually
    carries. Two protocols declaring one method incompatibly is a pair no
    class can satisfy, so mypy read the conformance check in
    :func:`disclosing_boundary` as narrowing to ``Never`` and reported its
    refusal branch unreachable — the guard was typed out of existence while
    still running. Inheritance makes the relationship the docstring always
    claimed, and leaves the runtime member set exactly as it was:
    ``record`` — the base Protocol's only member — plus the two below.
    """

    @property
    def tenant_id(self) -> str:
        """The tenant this recorder writes under (read-only: the SDK's recorder
        derives it from its composition-minted capability, D-IMPL-353 §1.3)."""
        ...

    disclosure_level_for: Callable[
        ..., tuple[DisclosureLevel, ProvenanceSource | None]
    ]


def disclosing_boundary(
    *, refusal_recorder: object | None, builder: str
) -> DisclosingRecorderProtocol:
    """Return the recorder, or refuse to build an evidence-dereferencing door.

    :func:`recorded_boundary`'s check FIRST — so a door that cannot record is
    refused in exactly the words it is refused in everywhere else — and then
    the two members ``D-IMPL-345`` needs on top.

    **A sibling rather than a widening**, deliberately.
    :func:`recorded_boundary` is one function shared with the egress and
    experience MCP builders, which ``D-IMPL-345`` leaves byte-for-byte
    unchanged; tightening it there would change the construction posture of
    two doors this ruling does not touch.
    """
    recorder = recorded_boundary(refusal_recorder=refusal_recorder, builder=builder)
    if not isinstance(recorder, DisclosingRecorderProtocol):
        raise UnrecordableDeliveryBoundaryError(
            f"{builder} was asked to build a door that dereferences governed"
            f" evidence, but its `refusal_recorder=` of type"
            f" {type(recorder).__name__} cannot state a disclosure level: a"
            " dereference is disclosed at the level that disclosed the serve,"
            " read through the recorder rather than the entitlement source"
            " (D-IMPL-345 R-2), so the recorder must carry `tenant_id` and"
            " `disclosure_level_for`. The SDK's `ReplayRefusalRecorder` does."
            " A door that cannot decide what it may disclose is not a valid"
            " governed door (D-IMPL-256 (2))"
        )
    return recorder


@dataclass(frozen=True, kw_only=True)
class DereferenceRequest:
    """What a caller asked for, and nothing recovered from what it names.

    Attributes:
        reference: The address or versioned URI, exactly as the caller wrote
            it. This string is the only caller-supplied member a refusal
            echoes (``D-IMPL-345`` R-4).
        by_uri: Whether ``reference`` is a versioned URI rather than a bare
            content address.
        wants_bytes: Whether the caller asked for stored bytes (the artifact
            route) rather than the typed record (the replay routes). Both are
            decided identically; only what is delivered differs.
    """

    reference: str
    by_uri: bool
    wants_bytes: bool


@dataclass(frozen=True, kw_only=True)
class DereferencedEvidence:
    """One authorized read: the record, its address, and the exact bytes.

    ``payload`` is populated only for a ``wants_bytes`` ask, and it is what
    the store returned rather than a re-serialization — the caller asked for
    the bytes at an address and gets those bytes, so the address it verifies
    them against is the one it asked for.
    """

    content_address: str
    record: DecisionReplayRecord
    payload: bytes | None = None


def _internal_refusal(record: DecisionReplayRecord) -> RefusalEnvelope | None:
    """The record's own internal refusal envelope, or ``None`` if it served.

    Dimension 5 holds the envelope as canonical JSON. A block that does not
    validate — the legacy pre-``24.6-07`` shape included — is *no recoverable
    identity*, which the caller's own hold 2 turns into a withheld read rather
    than a guess.
    """
    block = record.content_generation_path.assembly_refusal
    if block == NO_ASSEMBLY_REFUSAL:
        return None
    try:
        return RefusalEnvelope.model_validate_json(block)
    except ValidationError:
        return None


def _is_read_refusal(internal: RefusalEnvelope | None) -> bool:
    """Whether this record is one a dereference itself produced.

    Recognized by **both** constants together — the mechanism
    :data:`DEREFERENCE_PRODUCT_ID` and one of :data:`EVIDENCE_SURFACES` — and
    never by either alone. A record filed through the still-open write path
    (``D-IMPL-73``) could carry one and borrow the other's meaning; requiring
    both makes that forgery a record with no recoverable identity instead.
    It is safe rather than merely careful because hold 1 binds every record to
    its author: a forged record is readable by its forger and by nobody else.
    """
    return (
        internal is not None
        and internal.request.product_id == DEREFERENCE_PRODUCT_ID
        and internal.resource is not None
        and internal.resource.surface in EVIDENCE_SURFACES
    )


def _decided_identity(
    record: DecisionReplayRecord, internal: RefusalEnvelope | None
) -> tuple[str, str, str | None] | None:
    """``(tenant, product_class, lane)`` the serve was decided under, or ``None``.

    The tenant is the one the determination was **keyed on**, which differs
    from the record's own tenant exactly where it matters: a delivery-boundary
    denial is decided under the tenant the caller addressed, retained at
    ``assembly_refusal.resource.tenant_id``, while ``record.tenant_id`` is the
    tenant of the recorder that wrote it. Re-deciding a cross-tenant denial
    under the recorder's tenant would answer a different question from the one
    the serve asked.

    The class comes from the served request when there was one, and from the
    internal envelope's request identity otherwise. ``None`` — no recoverable
    class — is returned rather than a default: ``D-IMPL-345`` §9.1 withholds
    those records rather than inventing ownership for them.
    """
    served = record.content_generation_path.request
    if served is not None:
        return (record.tenant_id, served.schema_name, served.schema_version)
    if internal is None:
        return None
    product_id = internal.request.product_id
    if not product_id:
        return None
    tenant = (
        internal.resource.tenant_id
        if internal.resource is not None
        else record.tenant_id
    )
    return (tenant, product_id, internal.request.product_version)


def govern_dereference(
    authorized: EvidenceReadAuthority,
    *,
    reference: DereferenceRequest,
    store: ArtifactStoreProtocol,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: DisclosingRecorderProtocol,
    audit_log: AuditLog,
    surface: str,
    address: str,
    erased_client_read: ErasedContentRefused | None = None,
) -> DereferencedEvidence | RefusalEnvelope:
    """Decide one dereference of governed evidence (``D-IMPL-345``).

    The ONE governed step both evidence routes call, in ``D-IMPL-256``'s ruled
    sequence — request → identity/policy → determination → replay →
    disclosure shaping → transport encoding — with the transport holding only
    the sixth. A caller receives either the evidence it asked for or an
    already-recorded, already-disclosed shell.

    **The holds, in order, and the order is the property** (``D-IMPL-345``
    R-2):

    0. **Tenant.** The tenant the record was decided under
       (:func:`_decided_identity`; the record's own ``tenant_id`` when no
       identity is recoverable) equals the capability's ``authorized.tenant``.
       On a mismatch the read is answered exactly as a missing address is —
       ``nonexistent``, the one outcome at every disclosure level — so a caller
       learns nothing about another tenant's records, not even that one exists
       at an address it computed (C-2, the ``D-IMPL-376`` close-out). First,
       because hold 1's ``unauthorized`` at ``full`` would otherwise be that
       signal, and so that hold 2 only ever re-decides a grant under the
       capability's own tenant.
    1. **Principal.** The verified ``client_id`` equals the record's own
       ``perspective_conditioning.principal_id``. On a mismatch the boundary
       stops reading the record: ``authorize`` is never called, no policy pin
       is obtained, and nothing about the target — its principal, class, role
       or tenant — reaches the read-refusal record or the shell. That is
       structural, not careful: the ordering is what makes it true.
    2. **Product grant, re-decided now.** The identical ``authorize`` call the
       serve's entitlement made, under the tenant the determination was keyed
       on, for the class the record retains and the role it resolved
       (:func:`_decided_identity`). Resolved per call, so a revoked grant
       stops the read immediately; audited by the source as every entitlement
       decision is. The deployment's perspective resolver is **not** re-run —
       the record already carries the role it resolved, and the D-IMPL-67
       subject-conflict check is hold 1. A record this boundary itself wrote
       carries no product determination and skips this hold; a record with no
       recoverable class is withheld.
    3. **Disclosure, through the recorder.** The level in force for this
       principal, read from the recorder that disclosed the serve and under
       the recorder's own tenant, must be
       :data:`~ccf.products.disclosure.DISCLOSURE_FULL`. Below it the record
       does not cross — a dereference never upgrades a caller to the cause its
       own shell withheld.

    Only after all three pass is a versioned URI's naming checked, and the
    ordering is again the property: :meth:`resolve_uri` answers only under the
    exact ``(tenant, class, name)`` triple a version was registered under, so
    a caller allowed to consult it before the holds could confirm those three
    facts about a record it may not read by varying the segments.

    **An erased address** (SEC-009; ``D-IMPL-374`` (4), U11, ruling 1) is
    decided AFTER holds 1 and 2 — authorization first: the holds read the
    record through the unconsulted inner store — bytes read INTERNALLY for the
    rights check only, which never leave the door — so a caller not entitled
    to the record receives exactly the rendering it received before the
    erasure.
    An entitled caller then meets the consult: at ``minimal`` the same absence
    as below; at ``reasoned`` and ``full`` an ``erased-content`` shell (410)
    carrying the erasure's reason and instant, and its record address only at
    ``full``. The consult reads through the view for the caller's verified tenant, so
    an erasure withholds only within its tenant (fix round 1, I6). On the
    by-URI path the erased reading is decided BEFORE the URI's naming check
    (M7): an entitled caller naming an erased address under a wrong
    ``(tenant, class, name)`` triple receives the erased reading where a
    non-erased record would answer not-found — it learns nothing its
    entitlement to the record did not already admit. The naming check itself
    reads the SAME tenant view (FW-7, whole-branch review M-3;
    ``D-IMPL-374``): another tenant's entry naming the address cannot make it
    refuse what the view served, and an erasure it meets is the erased
    reading at the caller's level, never recorded as ``nonexistent``.

    **Every refusal and every absence is one outcome**: a
    :class:`~ccf.products.refusal.SubjectUnavailableRefusal` recorded through
    the door's recorder and returned disclosed. ``cause="unauthorized"``
    distinguishes a failure of holds 1 to 3 on a genuine record of the
    caller's own tenant from ``"nonexistent"`` for everything else — another
    tenant's record included (hold 0) — as internal truth; below ``full`` the
    two are one shell, and the request identity every shell carries is the
    mechanism constant plus the caller's own reference, never anything
    recovered from the target.

    **The capability first** (D-IMPL-353 §1.2, §1.5). ``authorized`` is the
    ``Authorized[ArtifactRead]`` or ``Authorized[ReplayRead]`` the HTTP gate or
    the MCP wrapper minted for THIS ask, and ``verify_any`` against it is the
    first statement of this function: the mint by identity, every field against
    the minted tuple, the kind by identity, and the resource bound to
    ``reference.reference`` — the string the door's declaration named as the
    resource the authorizer decided on (the path or query parameter on HTTP,
    the wire argument on MCP). After that line the principal is
    ``authorized.principal`` and the tenant is ``authorized.tenant``; there is
    no grant parameter and no tenant parameter, and nothing here is the
    caller's. The one seam below that still takes a
    :class:`~ccf_runtime.authz.product_entitlement.TokenGrant` — the
    entitlement source's ``authorize``, hold 2 — is handed a grant carrying
    the capability's principal and tenant and nothing else; the seam reads the
    principal (``client_id``) and nothing more.

    Args:
        authorized: The capability for this read. Verified first.
        reference: What was asked for, verbatim — and the resource the
            capability is bound to.
        store: The artifact store the door was built over — composed with
            the erasure consult (:func:`~ccf.erasure.compose_erasure_consult`;
            U12), or refused (PM5).
        entitlement_source: The deployment's entitlement seam and the holder
            of the determination clock.
        refusal_recorder: The ONE minting seam, which also states the level.
            Checked at construction by :func:`disclosing_boundary`.
        audit_log: The Control Plane's own append-only log. Every dereference
            appends exactly one ``authz_decision`` event naming the reference
            asked and the address delivered — the trail of a read, which the
            entitlement decision's own event is not (``D-IMPL-345`` R-5).
        surface: :data:`SURFACE_HTTP_REPLAY_READ` or
            :data:`SURFACE_HTTP_ARTIFACT_READ`.
        address: The route path the caller asked, for the resource identity.
        erased_client_read: SEC-009 (``D-IMPL-374`` (4), MCP ruling): the
            erasure refusal a door met reading a CLIENT-LANE artifact it had
            already decided the caller owns (the MCP artifact server's tenant
            split). When given, no record is resolved and no record hold runs —
            there is no record — and the caller receives the erased reading at
            its disclosure level: the not-found shell at ``minimal``,
            ``erased-content`` above it. It can only ever produce a refusal,
            never bytes.

    Returns:
        The evidence, or the disclosed shell carrying its own record's address.

    Raises:
        ccf.authz.capability.CapabilityBypassError: ``authorized`` is
            fabricated, retargeted, of a kind other than the two evidence-read
            kinds, or bound to a resource other than ``reference.reference``.
            Raised before the clock is read and before anything is recorded.
        UnconsultedDeliveryBoundaryError: ``store`` is not an
            :class:`~ccf.erasure.ErasureConsultingStore` (PM5, panel C5;
            U12). Raised right after the capability check, before anything
            is read, recorded or clocked.
        ccf.artifacts.protocol.MovingTargetRefused: the URI asks for
            ``@latest``. A request-shape refusal raised by the shared parser
            before any lookup, which reveals nothing and which the route
            renders as the ``409`` it renders today.
        Exception: whatever the artifact store raises on append, deliberately
            uncaught — a failure to record is a failure to decide.
    """
    kind = verify_any(
        authorized, kinds=EVIDENCE_READ_KINDS, resource=reference.reference
    )
    if not isinstance(store, ErasureConsultingStore):
        # PM5 (panel C5; `D-IMPL-374`): U12 composes the consult ALWAYS; a
        # store that does not consult would serve erased bytes unrefused.
        raise UnconsultedDeliveryBoundaryError(
            f"govern_dereference was handed a {type(store).__name__}, which does not"
            " consult the erasure index; compose it with"
            " ccf.erasure.compose_erasure_consult first — a governed evidence read"
            " over an unconsulted store would serve erased content (SEC-009; U12;"
            " D-IMPL-374)"
        )
    principal = authorized.principal
    # The one seam that still takes a grant: handed the capability's principal
    # and tenant, nothing the caller supplied.
    grant = TokenGrant(
        client_id=principal, scopes=(), tenants=frozenset({authorized.tenant})
    )
    determined_at = _determined_at(entitlement_source)
    action_id = kind.action_id

    def audited(*, delivered: str, allowed: bool) -> None:
        audit_log.append(
            action="authz_decision",
            key=reference.reference,
            version=delivered,
            resolved=allowed,
            occurred_at=determined_at,
            actor=principal,
            artifact_class=DEREFERENCE_PRODUCT_ID,
            authz_action_id=action_id,
            authz_matched_pattern=None,
        )

    def refuse(
        *,
        cause: str,
        error_code: str,
        detail: str,
        policy: ProvenanceSource | None = None,
        refusal: CCFContract | None = None,
    ) -> RefusalEnvelope:
        envelope = envelope_for(
            refusal
            if refusal is not None
            else SubjectUnavailableRefusal(
                cause=cause,  # type: ignore[arg-type]
                detail=detail,
                error_code=error_code,
            ),
            # The caller asked for an address. That is the whole of what its
            # request identity may say (`D-IMPL-260` (2)): authorization state
            # must never change an identity member's presence OR its value,
            # and `disclose` leaves `request` untouched at every level.
            request=RequestIdentity(
                product_id=DEREFERENCE_PRODUCT_ID,
                product_version=None,
                parameters={"reference": reference.reference},
                temporal_boundary=None,
            ),
            resource=ResourceRequestIdentity(
                surface=surface,
                address=address,
                # The door's own tenant: an address ask carries none, and an
                # absent target has none to carry. Normalized below `full`.
                tenant_id=refusal_recorder.tenant_id,
                determined_at=determined_at,
            ),
            policy_bindings=(policy,) if policy is not None else (),
        )
        audited(delivered="", allowed=False)
        return refusal_recorder.record(
            envelope,
            perspective=Perspective(
                principal_id=principal,
                # No perspective is resolved on a read: the positive absence,
                # never a role borrowed from the record being asked for.
                role=NO_ROLE_RESOLVED,
            ),
            recorded_at=determined_at,
            # `D-IMPL-358` step 5: the LIVE determination instant, carried beside
            # the record's own boundary rather than collapsed into it. Where an
            # `asked_at` exists the boundary stays the QUESTION's instant; where a
            # governed surface genuinely has none, the ruled resource-form boundary
            # (`D-IMPL-256` (1)) is retained and this says so separately.
            served_at=determined_at,
            # Dimension 2: there is no resolution step on this path at all —
            # the door states it rather than the seam inferring it from
            # silence (`D-IMPL-264` D-09/D-10).
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            policy_bindings=(
                (PolicyBinding(key=policy.identity, version=policy.version),)
                if policy is not None and policy.version is not None
                else ()
            ),
        )

    absent = "the requested evidence is not available to this principal"

    def erased_reading(erased: ErasedContentRefused) -> RefusalEnvelope:
        # SEC-009 (`D-IMPL-374` (4); design `D-IMPL-367` §5.3, U11): the level
        # in force for THIS principal decides what CROSSES — `minimal` is the
        # not-found rendering, `reasoned`/`full` the `erased-content` shell
        # (410 at HTTP) — and the disclosure step decides it.
        # At every level the RECORDED determination is `erased-content` (I5);
        # at `minimal` the disclosure step renders it as the not-found shell
        # (`ccf.products.disclosure.TRANSLATED_AT_MINIMAL`), so the wire says
        # nothing and the audit trail stays honest.
        return refuse(
            cause="nonexistent",
            error_code=ERROR_EVIDENCE_ABSENT,
            detail=absent,
            refusal=ErasedContentRefusal(
                detail="the requested content was erased by a recorded decision and is not served",
                erasure_reason=erased.reason,
                erased_at=erased.erased_at,
                erasure_record_address=erased.erasure_record_address,
            ),
        )

    if erased_client_read is not None:
        return erased_reading(erased_client_read)

    # --- resolution: every failure below is the SAME absence -----------------
    if reference.by_uri:
        # `@latest` raises MovingTargetRefused here, before any lookup.
        parsed = parse_artifact_uri(reference.reference)
        candidate = parsed.artifact_version
    else:
        candidate = reference.reference
    # SEC-009 ruling 1 (`D-IMPL-374` (4)): AUTHORIZATION FIRST. The record the
    # holds judge is read through the UNCONSULTED inner store, so an erased
    # address is authorized exactly as it was before its erasure. Those bytes
    # are read INTERNALLY for the rights check only and NEVER leave the door
    # (accepted as recorded by the coordinator): what crosses comes from the
    # consulted read below, after the holds.
    authorization_store = store.inner
    try:
        content_address = held_content_address(candidate)
        record = resolve_artifact(
            store=authorization_store,
            content_address=content_address,
            contract=DecisionReplayRecord,
        )
    except (
        ArtifactNotFound,
        ArtifactStoreError,
        ReplayUnresolvable,
        ReplayDivergence,
        ValidationError,
    ):
        # A malformed address, nothing stored, bytes that are not a record,
        # bytes that do not hash to their address: ONE outcome at every level.
        # The non-record classes are addressed by the hash of their own
        # inputs, so a caller able to tell them apart from nothing could
        # confirm that a particular traversal or question happened.
        return refuse(
            cause="nonexistent", error_code=ERROR_EVIDENCE_ABSENT, detail=absent
        )

    internal = _internal_refusal(record)
    decided = _decided_identity(record, internal)

    # --- hold 0: the tenant the record was decided under --------------------
    # C-2 (`D-IMPL-345` R-2: the caller is held to the record's retained
    # principal/TENANT/product identity). A record decided under any tenant but
    # the capability's answers exactly as a missing address does — the one
    # `nonexistent` outcome, at every level — and FIRST: hold 1's
    # `unauthorized` would otherwise tell a `full` caller that another tenant
    # holds a record at an address it computed, and hold 2 would re-decide a
    # grant under a tenant the capability does not name.
    deciding_tenant = decided[0] if decided is not None else record.tenant_id
    if deciding_tenant != authorized.tenant:
        return refuse(
            cause="nonexistent", error_code=ERROR_EVIDENCE_ABSENT, detail=absent
        )

    # --- hold 1: the record's own principal ---------------------------------
    if principal != record.perspective_conditioning.principal_id:
        return refuse(
            cause="unauthorized",
            error_code=ERROR_EVIDENCE_PRINCIPAL_MISMATCH,
            detail=(
                "the record at the requested reference was determined for"
                " another principal"
            ),
        )

    # --- hold 2: the product grant that governed the serve ------------------
    if not _is_read_refusal(internal):
        if decided is None:
            return refuse(
                cause="unauthorized",
                error_code=ERROR_EVIDENCE_CLASS_UNRECOVERABLE,
                detail=(
                    "the record retains no product class, so the grant that"
                    " governed its serve cannot be re-decided"
                ),
            )
        decided_tenant, product_class, _lane = decided
        try:
            entitlement_source.authorize(
                grant=grant,
                tenant=decided_tenant,
                product_class=product_class,
                role=record.perspective_conditioning.role,
            )
        except ProductEntitlementRefused as refused:
            return refuse(
                cause="unauthorized",
                error_code=refused.error_code,
                detail=refused.message,
                policy=refused.policy,
            )

    # --- the erasure consult: after the holds, before disclosure -------------
    # SEC-009 (`D-IMPL-374` (4), ruling 1; design `D-IMPL-367` §5.3): only a
    # caller entitled to this record reaches here. At `minimal` an erased
    # address is the route's not-found rendering; at `reasoned` and `full` it
    # is the `erased-content` shell the door renders 410.
    try:
        # I6 (fix round 1, ruling (i)): the view for the caller's VERIFIED
        # tenant — an erasure withholds within its tenant, and another
        # tenant's reason or record address never reaches this caller.
        tenant_view = store.scoped(authorized.tenant)
        consulted = tenant_view.get(content_address=content_address)
    except ErasedContentRefused as erased:
        return erased_reading(erased)

    # --- hold 3: the level that disclosed the serve -------------------------
    level, _policy = refusal_recorder.disclosure_level_for(
        tenant=refusal_recorder.tenant_id, principal_id=principal
    )
    if level != DISCLOSURE_FULL:
        return refuse(
            cause="unauthorized",
            error_code=ERROR_EVIDENCE_DISCLOSURE_WITHHELD,
            detail=(
                f"the disclosure level in force for this principal is {level!r};"
                " a governed record crosses a door only at full disclosure"
            ),
        )

    # --- the URI's naming, checked LAST -------------------------------------
    if reference.by_uri:
        # FW-7 (whole-branch review M-3; `D-IMPL-374`): through the SAME view
        # the consult above read — the caller's verified tenant's — so another
        # tenant's entry naming this address cannot make the naming check
        # refuse what the tenant view served; and an erasure met here is the
        # erased reading at the caller's level, never recorded as an absence.
        try:
            registered = tenant_view.resolve_uri(uri=reference.reference)
        except ErasedContentRefused as erased:
            return erased_reading(erased)
        except (ArtifactStoreError, LookupError):
            return refuse(
                cause="nonexistent",
                error_code=ERROR_EVIDENCE_ABSENT,
                detail=absent,
            )
        if registered != content_address:
            return refuse(
                cause="nonexistent",
                error_code=ERROR_EVIDENCE_ABSENT,
                detail=absent,
            )

    payload = consulted if reference.wants_bytes else None
    audited(delivered=content_address, allowed=True)
    return DereferencedEvidence(
        content_address=content_address, record=record, payload=payload
    )


def govern_erasure(
    *,
    grant: TokenGrant,
    tenant: str,
    product_class: str,
    product_version: str | None,
    parameters: Mapping[str, Any],
    asked_at: datetime | None,
    surface: str,
    address: str,
    perspective: Perspective,
    erased: ErasedContentRefused,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: RefusalRecorderProtocol,
) -> RefusalEnvelope:
    """The governed determination for an erasure a door met while answering (FW-3, whole-branch review I-2; ``D-IMPL-374``).

    SEC-009's U11 (``ccf.products.refusal.ErasedContentRefusal``): an erased
    address's reading is disclosure-governed — a door renders the erasure only
    at ``reasoned`` and ``full``, and at ``minimal`` answers with its own
    not-found rendering. The HTTP doors and the MCP artifact server did that
    through :func:`govern_dereference`; the whole-branch review measured the
    MCP egress tool and resources and the Experience seams passing
    :class:`~ccf.erasure.ErasedContentRefused` to the wire as exception prose
    naming the erased address, at every level. This is the mapping they call.

    The mirror of :func:`govern_absence`: the ``erased-content`` determination
    is enveloped under this surface's request and resource identity, RECORDED
    through the one recorder the door holds — at every level, so the audit
    trail is honest (the design's I5) — and returned DISCLOSED. The disclosure
    step decides what crosses: at ``minimal`` it renders the not-found shell
    (``ccf.products.disclosure.TRANSLATED_AT_MINIMAL``, the shell
    :func:`govern_absence` answers), at ``reasoned`` the reason and instant, at
    ``full`` the record address too. The erased address is never in the
    envelope: an :class:`~ccf.products.refusal.ErasedContentRefusal` has no
    address field.

    **Dimension 2 states** ``ResolutionNotApplicable("no-resolution-step")``:
    the ``erased-content`` determination is the store consult's, made at a
    read, and a door holds no resolver evidence to record — it states that no
    resolution step belongs to this determination rather than manufacturing
    one (the :func:`govern_absence` precedent).

    A door whose surface has NO not-found rendering (the Experience
    ``get_context``, ``get_lineage`` and ``get_replay_record`` seams) calls
    this only above ``minimal``, and answers ``minimal`` with its opaque
    runtime failure instead.

    Args:
        grant: The verified caller.
        tenant: The tenant the caller addressed.
        product_class: The class the surface answers for.
        product_version: The class's lane, or ``None``.
        parameters: What the caller supplied, for the request identity.
        asked_at: The instant asked as-of, or ``None``.
        surface: One of the surface tokens.
        address: What the caller addressed, verbatim.
        perspective: The perspective the door already authorized, or the
            positive no-role perspective where the surface resolves none.
        erased: The consult's refusal. Its facts are what the store's view
            disclosed to the door — ``None`` where the read was tenantless.
        entitlement_source: The source whose declared clock stamps the
            determination.
        refusal_recorder: The seam that mints the record and discloses.

    Returns:
        The disclosed shell, carrying the replay reference of its own record.

    Raises:
        Exception: whatever the recorder's store raises on append,
            deliberately uncaught — a failure to record is a failure to decide.
    """
    determined_at = _determined_at(entitlement_source)
    envelope = envelope_for(
        ErasedContentRefusal(
            detail="the requested content was erased by a recorded decision and is not served",
            erasure_reason=erased.reason,
            erased_at=erased.erased_at,
            erasure_record_address=erased.erasure_record_address,
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
        policy_bindings=(),
    )
    return refusal_recorder.record(
        envelope,
        perspective=Perspective(principal_id=grant.client_id, role=perspective.role),
        recorded_at=asked_at if asked_at is not None else determined_at,
        served_at=determined_at,
        policy_bindings=(),
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
