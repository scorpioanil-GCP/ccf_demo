"""The one canonical refusal envelope — how a "no" crosses a delivery seam.

**SDK-defined, not whitepaper-derived.** The whitepaper specifies the Context
Product Contract (§6.3) and the three validation gates that refuse a candidate
(§7.6); it does not specify a transport shape for the refusals themselves,
because it does not specify a client. This module is the CCF SDK's extension,
ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` Amendment 1
§A and framed by CLAUDE.md §7.3 (the neutral seams — the typed contract, MCP,
A2A — are the stable layer). It inherits the whitepaper's contract discipline
by deriving from :class:`~ccf.contracts.base.CCFContract`: frozen,
``extra=forbid``, canonically serializable.

Why it exists
-------------
A served product has one shape every door already emits. A **refused** one had
none: the resolver seam is typed to return a servable product and admits no
refusal in its union, so every refusal type the fabric declares reached no
wire at all. There was nothing for a door to emit until this shape existed,
which is why the envelope is defined here — in ``src/``, beside the types it
carries — before any door is changed.

The two ruled constraints
-------------------------
**(a) Every refusal kind crosses without flattening.** The fabric declares
twenty-three of them: the ``GateRefusal`` hierarchy
(:mod:`ccf.products.gates`, including the declared-obligations refusal of
``24.5-L-14`` / ``24.5-L-26`` and the empty-operator gate's returned-empty
half of ``24.5-L-24``), the peering-admission refusals that derive from it
(:mod:`ccf.peering.admission`), the product-mount refusal that derives from it
(:mod:`ccf.graph.product_source`), the two request/payload conformity verdicts
(:mod:`ccf.products.request`, :mod:`ccf.products.payload`), the pre-assembly
anchor-ambiguity refusal beside them (:mod:`ccf.products.request`,
``24.5-L-16``), the two constraint-layer determinations
(:mod:`ccf.products.constraints`, ``24.6-L-07``), the assembly mixing refusal
(:mod:`ccf.products.composition`),
the assembly-time refusal returned as a value
(:mod:`ccf.agents.errors`, ``24.5-L-11``, narrowed by ``24.6-L-02``),
and the one canonical outcome a nonexistent subject and an unauthorized
principal share (:class:`SubjectUnavailableRefusal`, ``24.6-L-21``). If the
envelope lost *which
kind* a refusal was, a client's ``refusal.reason`` would become mush and the
auditable-refusal guarantee would die at the seam. So ``kind`` is a required
member sourced from :data:`REFUSAL_KINDS`, and every field a refusal type
declares of its own survives the crossing in :attr:`RefusalEnvelope.fields`.

**(b) It carries the pre-assembly request identity** — product id, parameters,
temporal boundary — as :class:`RequestIdentity`. The refusal types carry none
of this: they are values about *what was wrong*, not about *what was asked*.
The caller holding the request supplies it.

The peering and mount families are in scope deliberately
--------------------------------------------------------
:class:`~ccf.peering.admission.AdmissionRefusal` and
:class:`~ccf.graph.product_source.ProductMountRefusal` both derive from
:class:`~ccf.products.gates.GateRefusal` rather than paralleling it, and both
say why in their own docstrings: a caller inspecting ``gate`` and ``detail``
reads a peering refusal exactly as it reads a TTL refusal. An envelope that
carried the TTL refusal and dropped the admission refusal would break the very
property those modules were written to preserve. Whether either is reachable
from a particular door today is a fact about *reachability*; constraint (a) is
worded over the vocabulary.

What is deliberately **not** here
---------------------------------
* **Entitlement verdicts, as exceptions.**
  :class:`~ccf.products.entitlement.ProductEntitlementViolation` and its
  sibling are ``LookupError`` subclasses — *exceptions raised inside the authz
  module*, not values returned by the fabric — so they are out of this
  envelope's vocabulary and are recorded in :data:`NON_VALUE_VIOLATIONS`. The
  governed determination a delivery boundary makes from one **is** in the
  vocabulary, as :class:`SubjectUnavailableRefusal` (``24.6-L-21``).
* **Control Plane, harness and composition verdicts.** Four further
  contracts in the walked name families exist under ``src/`` — a registration
  verdict, a harness effect-capture verdict, a skilling-governance verdict, and
  an agent-composition default conflict. None crosses a product seam. They are
  recorded in :data:`NON_PRODUCT_REFUSALS`.

Both exclusions are **named asserted allowlists**, not omissions: the
exhaustiveness gate in ``tests/products/test_refusal_envelope.py`` closes each
by set equality against a structural walk of ``src/``. A new refusal type that
is neither translated nor allowlisted fails the build and demands a ruling
rather than shipping untranslated.

**Determination → Authority → Disclosure → Delivery** — the architectural
invariant of ``D-IMPL-254``, SDK-defined under CLAUDE.md §11 and not
whitepaper-derived (the whitepaper is deliberately not edited, ``D-IMPL-253``
Q28). Dave's text: *"Internal truth, governing authority, and permitted
disclosure are distinct concerns. The fabric preserves the governed truth of
why a determination was reached; Policy determines what of that truth may cross
the consumer boundary; the response shell expresses only the permitted
disclosure. Decision Replay preserves sufficient governed evidence to
reconstruct both the determination and the disclosure decision."*

**This module is the Determination layer's value, and it is the shape the
other three read.** It states what the fabric determined, whole; it applies no
disclosure filter of its own, because a filter here would be a second place
disclosure is decided. What of it may cross a consumer boundary is
:func:`~ccf.products.disclosure.disclose`'s decision.

This module is algorithmic (CINV-03): pure functions over typed values, no
I/O, no clock, no LLM dependency ever.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final, Literal

from pydantic import Field, field_validator

from ccf.agents.errors import AssemblyRefusal
from ccf.contracts.base import CCFContract
from ccf.controlplane.temporal_boundary import (
    PinnedTemporalBoundary,
    TemporalBoundaryUndeclared,
)
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY, canonical_bytes
from ccf.graph.product_source import ProductMountRefusal
from ccf.halflife.assessment import DebtAssessment
from ccf.peering.admission import (
    AdmissionRefusal,
    ContractRefusal,
    IssuanceRefusal,
    LineageContinuityRefusal,
    PayloadTooLargeRefusal,
    PolicyBindingRefusal,
    SignatureRefusal,
)
from ccf.products.composite import ChildAdmissionRefusal
from ccf.products.composition import MixingRefusal
from ccf.products.constraints import ConstraintRefusal, PolicyResolutionConflict
from ccf.products.contract import (
    ComputedEmptyFinding,
    ProductLineage,
    RefusalCause,
)
from ccf.products.gates import (
    AttestationRefusal,
    DeclaredObligationRefusal,
    EmptyOperatorRefusal,
    GateRefusal,
    LineageAttributionRefusal,
    LineageMismatchRefusal,
    ProductInvariantRefusal,
    ToleranceExceededRefusal,
    DependencyInvalidationRefusal,
    TTLAnchorRefusal,
    TTLRefusal,
)
from ccf.products.payload import PayloadSchemaViolation
from ccf.products.provenance import EffectiveRequest, ProvenanceSource
from ccf.products.request import AnchorAmbiguityRefusal, ProductRequestViolation

__ccf_mode__ = "algorithmic"

__all__ = [
    "NON_PRODUCT_REFUSALS",
    "NON_VALUE_VIOLATIONS",
    "NO_REPLAY_REFERENCE",
    "REFUSAL_KINDS",
    "TemporalBoundRefusal",
    "refuse_temporal_bound",
    "RefusalEnvelope",
    "RefusalEvidence",
    "RequestIdentity",
    "ResourceRequestIdentity",
    "SubjectUnavailableRefusal",
    "ErasedContentRefusal",
    "GovernedRefusalRaised",
    "RESOLVED_BY_THE_RESOLVER",
    "ResolvedByTheResolver",
    "envelope_for",
]


#: :attr:`RefusalEnvelope.replay_reference`'s value when the shell was produced
#: by a seam that minted no Decision Replay record (``24.6-07``; ``D-IMPL-253``
#: Q13, ``D-IMPL-256``). A positive claim in the voice
#: :data:`~ccf.replay.record.NO_HITL_ACTIONS` uses: *"the seam that produced
#: this shell recorded no decision"* is asserted, never inferred from silence —
#: a refusal minted before this seam existed and a refusal whose reference was
#: dropped in transit would otherwise be the same artifact, which is the
#: repudiation failure mode the sentinel discipline exists to close.
#:
#: It is also what the **recorded** shell carries, always: the record's
#: dimension 5 holds the envelope as it stood *before* it learned its own
#: address, because a record whose content address covered a reference to
#: itself could not be content-addressed at all.
NO_REPLAY_REFERENCE: Final[str] = "no-replay-reference"


class RequestIdentity(CCFContract):
    """What was asked, as it stood *before* assembly began.

    Constraint (b) of Amendment 1 §A. None of the refusal types carries any of
    this: a refusal is a value about what was wrong, and the question it was
    wrong about is held by the caller that asked it.

    Attributes:
        product_id: The product class the question addressed — the
            ``schema_name`` of the request.
        product_version: The class's own semver lane, or ``None`` when the
            question named none. Lanes are per class and never compared across
            classes.
        parameters: What the caller supplied. An empty mapping is a question
            that needed nothing beyond its axes — a statement, and not the same
            fact as *unknown*, which this type cannot express and does not need
            to.
        temporal_boundary: The instant the question was asked against. ``None``
            is the positive assertion *the caller deferred to the server's
            decision instant* rather than a missing value.
    """

    product_id: str
    product_version: str | None
    parameters: Mapping[str, Any]
    temporal_boundary: datetime | None


class SubjectUnavailableRefusal(CCFContract):
    """The ONE outcome a nonexistent subject and an unauthorized one share.

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §11); the rulings of
    record are ``D-IMPL-253`` Q27 and its amendment 2 (4), with
    ``D-IMPL-254``'s four layers. Dave, Q27, verbatim:

        *"No special suppression-silent kind. However, this requires a
        canonical externally observable refusal outcome that both nonexistent
        and unauthorized anchors can share. Disclosure policy controls
        permitted detail. Internally/replay, the governed cause may be retained
        if policy permits, while the consumer-visible shell remains
        indistinguishable. Don't destroy audit truth merely to achieve external
        suppression silence."*

    And amendment 2 (4), which is why indistinguishability is a property of the
    **disclosure step** rather than of this type:

        *"Unauthorized and nonexistent subjects must be consumer-observationally
        equivalent at the same disclosure level: same transport status, kind,
        external reason, body schema/field presence and permitted disclosure
        behavior. Internal truth/replay may differ according to policy."*

    So this type is the **internal** value and states the whole truth. What of
    it crosses a consumer boundary is :func:`~ccf.products.disclosure.disclose`'s
    decision and nobody else's; at the safe default that function replaces
    :attr:`cause` with ``"undisclosed"`` while the record keeps what the fabric
    actually determined.

    **There is deliberately no ``subject`` field.** Naming the subject on the
    shell is itself a leak channel — telling a caller *which* entity it may not
    see is telling it the entity exists — and a field that a disclosure step
    had to remember to blank is a field that will one day cross. It cannot be
    set, so it cannot leak. The question that was asked is on
    :attr:`RefusalEnvelope.request`, which is what the caller supplied and
    already knows.

    Attributes:
        cause: What the fabric actually determined. ``"nonexistent"`` — no such
            subject resolved; ``"unauthorized"`` — a subject the principal may
            not receive; ``"undisclosed"`` — the disclosure step withheld which
            of the two it was. The third is not a determination the fabric ever
            reaches; it is the value a **disclosed** shell carries, so that the
            withheld case has a positive spelling rather than an absence a
            reader must interpret.
        detail: The human-readable statement. Internally this is the fabric's
            own sentence; at ``minimal`` the disclosure step replaces it with
            the one external sentence
            :data:`~ccf.products.disclosure.EXTERNAL_STATEMENTS` holds for this
            kind — the *same* sentence for both causes.
        error_code: The typed code the determination carried, when one did —
            a door's own vocabulary
            (:mod:`ccf_runtime.http_api.errors`), retained internally so an
            operator reading an audit record can tell an absent policy from a
            refused role. ``None`` is the positive *no code was carried*, and
            it is also what a disclosed shell carries at every level below
            ``full``: a code is as fine-grained a leak as prose.
    """

    cause: RefusalCause
    detail: str
    error_code: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class ErasedContentRefusal(CCFContract):
    """The requested artifact was erased by a recorded decision and is not served (SEC-009; `D-IMPL-374` (4)).

    **SDK-defined**, built to design ``D-IMPL-367`` §5: the reading of an erased
    address is disclosure-governed. A door renders this kind only at
    ``reasoned`` and ``full``; at ``minimal`` the door answers with its own
    not-found rendering instead, so the erasure is not disclosed (U11). Below
    ``full`` the erasure record's address is withheld
    (:data:`~ccf.products.disclosure.INDISTINGUISHABLE_BELOW_FULL`), so a
    ``reasoned`` reader learns the reason and the instant and an entitled
    ``full`` examiner learns where the authority record is.

    **There is no subject field**, on the ``subject-unavailable`` reasoning:
    naming the subject is the leak.

    Attributes:
        detail: The fabric's statement.
        erasure_reason: The admitted erasure reason (the policy's closed set).
            Not ``reason``, deliberately: ``reason`` is promoted and crosses at
            every level, and this crosses only above ``minimal``.
        erased_at: The erasure record's instant.
        erasure_record_address: The authority record, crossing only at ``full``.
    """

    detail: str
    erasure_reason: str
    erased_at: datetime
    erasure_record_address: str


class TemporalBoundRefusal(CCFContract):
    """The question reaches outside the window this tenant answers for.

    SDK-defined (CLAUDE.md §11); `D-IMPL-358` step 5, enforcing the
    `ccf.controlplane.temporal_boundary.TemporalBoundaryPolicy` step 3 declared.
    **A returned value, never an exception** — the posture `D-IMPL-253` Q13
    requires of every governed determination.

    **Judged before acquisition and before the graph is read**, so an
    out-of-window question costs nothing: no source is invoked, nothing is
    ingested, and there is no candidate to have a lineage. It joins
    `_PRE_ASSEMBLY_REFUSALS` for that reason.

    **Defined here rather than beside the policy it enforces**, which is the one
    place this module departs from the `ccf/products/constraints.py::ConstraintRefusal`
    precedent. Two reasons: this module already hosts a concrete governed refusal
    (`SubjectUnavailableRefusal`), so nothing new is introduced; and a refusal
    kind is overwhelmingly a *delivery-vocabulary* item — it must be registered
    in `REFUSAL_KINDS`, in the disclosure statement and minimal tables, and in
    the door's status map — where the policy itself is a Control Plane artifact
    three subsystems resolve. Putting the vocabulary item here keeps
    `ccf.controlplane` free of a dependency on the products refusal surface.

    **Three reasons, closed, and they are three different facts.** Collapsing
    them would lose exactly what an operator needs to act:

    ``temporal-boundary-undeclared``
        No `TemporalBoundaryPolicy` is registered for this tenant, so how far
        into the past it answers for is unknown. `D-IMPL-358` ruling 11: the
        fabric refuses and records the key and class that were required and the
        absence reason, and **mints no binding** — there is no version to pin
        for a policy that does not exist. The remedy is the operator's, not the
        caller's.
    ``asked-at-outside-temporal-bound``
        The question's own ``asked_at`` falls outside the declared window,
        measured against the trusted ``served_at``.
    ``decision-instant-outside-temporal-bound``
        The instant the class DERIVES the decision from — which a declared
        parameter may supply and policy may narrow — falls outside it. Checked
        separately from ``asked_at`` because the two can differ and a class that
        derives its decision instant from a parameter would otherwise reach
        outside the window through a value nobody judged.

    Attributes:
        reason: Which of the three, above.
        detail: The statement an operator reads. The typed members are the
            machine-readable version.
        policy_key: The canonical Control Plane key that was required or
            resolved. Present on all three reasons, because "which key" is the
            first thing an operator needs in every case.
        served_at: The trusted instant the judgment was made at — read once at
            `ccf.products.resolver.GovernedResolver.__call__` entry, never here.
        presented_at: The instant that fell outside, for the two window reasons.
            ``None`` for ``temporal-boundary-undeclared``, which is the positive
            statement that no window existed to fall outside of.
        max_past_seconds: The declared bound, when one resolved. ``None`` for
            the undeclared reason — **not zero**, which is a legal and strict
            declared bound and would read as one.
        permitted_clock_skew_seconds: The declared forward tolerance, when one
            resolved. ``None`` on the same reasoning.
    """

    reason: Literal[
        "temporal-boundary-undeclared",
        "asked-at-outside-temporal-bound",
        "decision-instant-outside-temporal-bound",
    ]
    detail: str
    policy_key: str
    served_at: datetime
    # `D-IMPL-243` amendments 1 and 2, and the mark is `False` rather than
    # `True` for a reason this type makes easy: **nothing predates it.** A
    # transparent mark buys silence at the sentinel so that records written
    # BEFORE a member existed keep their address — and no refusal of this kind
    # has ever been written, so there is no yesterday for silence to equal.
    # Meanwhile all three are governed evidence about why a determination was
    # refused, and the accepted design's rule is that security defaults are
    # generation boundaries except where a stated reason makes silence safe. No
    # such reason exists here, so they are declared boundaries by name.
    presented_at: datetime | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    max_past_seconds: int | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    permitted_clock_skew_seconds: int | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )


def refuse_temporal_bound(
    *,
    pinned: PinnedTemporalBoundary | TemporalBoundaryUndeclared,
    served_at: datetime,
    asked_at: datetime,
    decision_instant: datetime,
) -> TemporalBoundRefusal | None:
    """Hold a question's instants to the tenant's declared window, or return ``None``.

    `D-IMPL-358` step 5. **Pure**: it reads no clock and no registry. `served_at`
    is the trusted instant the caller read once at
    `ccf.products.resolver.GovernedResolver.__call__` entry, and `pinned` is what
    `ccf.controlplane.temporal_boundary.resolve_temporal_boundary` already
    returned — so this function judges and decides nothing about where either
    came from.

    **Both instants are checked, and they are two different facts.** ``asked_at``
    is what the question asks as of; ``decision_instant`` is what the class
    DERIVES its decision from, which a declared parameter may supply and policy
    may narrow. A class that derives its decision instant from a parameter would
    otherwise reach outside the window through a value nobody judged. ``asked_at``
    is judged first, so a question outside both is reported by the axis a caller
    controls most directly, deterministically.

    **The comparison is the sibling artifact's, exactly.**
    `ccf/peering/eligibility.py::_evidence_too_old` measures ``age`` forward from
    the instant to the trusted time and refuses ``age > max`` in the past
    direction and ``-age > skew`` in the future direction. Reusing that arithmetic
    rather than inventing a second one is what keeps two declared durations in
    this fabric meaning the same thing. It also fixes the reading of zero: a
    declared ``0`` admits only an age of zero or less, which is the strictest
    bound and not "unbounded".

    Returns:
        The refusal, or ``None`` when the question is inside the window. A
        ``None`` from an UNDECLARED policy is impossible: absence always refuses,
        because the SDK holds no window and inventing one is the defect
        `D-IMPL-38` forbids.
    """
    if isinstance(pinned, TemporalBoundaryUndeclared):
        return TemporalBoundRefusal(
            reason="temporal-boundary-undeclared",
            detail=pinned.detail,
            policy_key=pinned.key,
            served_at=served_at,
        )
    policy = pinned.policy
    for instant, reason in (
        (asked_at, "asked-at-outside-temporal-bound"),
        (decision_instant, "decision-instant-outside-temporal-bound"),
    ):
        age = (served_at - instant).total_seconds()
        if age > policy.max_past_seconds:
            return TemporalBoundRefusal(
                reason=reason,  # type: ignore[arg-type]
                detail=(
                    f"the instant {instant.isoformat()} is {int(age)}s before the"
                    f" trusted serve instant {served_at.isoformat()}; this tenant"
                    f" declares a maximum of {policy.max_past_seconds}s of past"
                    " reach. Refused rather than narrowed: the fabric answers the"
                    " question asked or says why it cannot"
                ),
                policy_key=pinned.key,
                served_at=served_at,
                presented_at=instant,
                max_past_seconds=policy.max_past_seconds,
                permitted_clock_skew_seconds=policy.permitted_clock_skew_seconds,
            )
        if -age > policy.permitted_clock_skew_seconds:
            return TemporalBoundRefusal(
                reason=reason,  # type: ignore[arg-type]
                detail=(
                    f"the instant {instant.isoformat()} is {int(-age)}s AFTER the"
                    f" trusted serve instant {served_at.isoformat()}; this tenant"
                    f" permits {policy.permitted_clock_skew_seconds}s of forward"
                    " clock skew. An instant from the future is refused rather"
                    " than treated as maximally current"
                ),
                policy_key=pinned.key,
                served_at=served_at,
                presented_at=instant,
                max_past_seconds=policy.max_past_seconds,
                permitted_clock_skew_seconds=policy.permitted_clock_skew_seconds,
            )
    return None


class RefusalEvidence(CCFContract):
    """What the fabric is PERMITTED to show of the search behind a refusal.

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §11); the ruling of
    record is ``D-IMPL-253`` Q13 (Dave: *"Refusal is itself a decision and
    deserves the same five-dimensional replay model. Do not create
    second-class replay."*) with ``D-IMPL-254``'s four layers —
    Determination → Authority → Disclosure → Delivery.

    It is the **internal** form. What of it crosses a consumer boundary is the
    Disclosure layer's decision and nobody else's: the fabric preserves the
    governed truth, Policy decides what may cross, and the shell expresses only
    the permitted statement. This type therefore states the search and applies
    no filter of its own — a filter here would be a second place disclosure is
    decided, and two places deciding one thing is how audit truth gets
    destroyed to achieve suppression silence.

    Attributes:
        operators_invoked: The operator set the execution behind this refusal
            resolved. Empty is a real answer only for a refusal reached before
            any plan ran, and such a refusal carries no evidence at all — the
            envelope's ``None`` says that, not an empty set here.
        plan_id: The plan the execution ran.
        debt: The Context Debt measured over what the question assembled
            (whitepaper §7.7), when one was measured. ``None`` is the positive
            *no assessment was made* — a gate refusal reached before scoring,
            or a candidate the deployment's scorer declined to assess.
        computed_empty: The search behind an empty answer
            (``24.6-05``, ``D-IMPL-255`` (2)), when the execution recorded one.
            ``None`` is *no operator returned empty*, the claim every product
            assembled before that field existed was already making.
    """

    operators_invoked: frozenset[str]
    plan_id: str
    # Two optional members on a brand-new model, so there is no earlier
    # generation for either to be a boundary against and ``True`` is the only
    # coherent declaration (``D-IMPL-243`` amendment 1; the
    # `ccf.products.provenance` precedent, 24.6-01). A refusal reached with no
    # assessment and one reached with no empty operator each render without
    # the key they have nothing to say under.
    debt: DebtAssessment | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    computed_empty: ComputedEmptyFinding | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


class ResourceRequestIdentity(CCFContract):
    """The identity a DELIVERY-BOUNDARY denial is recorded under.

    **SDK-defined, not whitepaper-derived** (CLAUDE.md §11, §8.3); the ruling
    of record is ``D-IMPL-256`` (1) — ``24.6-CONTEXT.md`` D-34 — in Dave's own
    words: *"No fulfilled Context Product does not mean no Decision Replay."*
    A standing resource, a tool call and an HTTP route are three transport
    shapes of one governed act, and a denial at any of them is a determination
    the fabric reached. Recording only the shapes that happen to carry a
    :class:`~ccf.products.request.ProductRequest` would be *"a replay hole
    based on transport shape"*.

    **Five questions a delivery-boundary denial must answer, and where each is
    answered.** This type carries two of them and names the other three so a
    reader is not left to hunt:

    ==================================== ====================================
    Question                             Answered by
    ==================================== ====================================
    what resource was requested          :attr:`surface` and :attr:`address`
    at what instant                      :attr:`determined_at`
    by whom / under which perspective    replay dimension 4
    under which policy                   replay dimension 2
    why fulfillment was refused          replay dimension 5, and this shell's
                                         own ``kind``/``reason``/``detail``
    ==================================== ====================================

    It **names no subject and no principal**, deliberately. Every value here is
    something the caller itself supplied or the deployment itself declared, so
    the identity is retained on the recorded internal shell and on a disclosed
    shell alike: telling a caller the address it just asked for reveals nothing
    it did not already know. Who asked is dimension 4's, and dimension 4 is not
    a consumer-facing surface.

    Attributes:
        surface: Which delivery boundary decided — the door's own mechanism
            token, defined **once** beside the governed step that mints these
            (``runtime/ccf_runtime/authz/delivery_boundary.py``) and never as a
            literal at a door. Three doors spelling one surface three ways is
            three vocabularies in the audit record.
        address: What was requested — the product URI a standing resource
            names, or the route path an HTTP caller asked for. What the caller
            addressed, never what the fabric resolved it to.
        tenant_id: The tenant the determination was made under, established by
            the calling surface and never claimed by the caller's body.
        determined_at: The instant the entitlement determination was reached,
            read from the deployment's own declared clock — the **same**
            instant the replay record's ``recorded_at`` carries, so the shell
            and its record cannot disagree about when the fabric decided.

    Raises:
        ValueError: ``determined_at`` carries no UTC offset. ``D-IMPL-38``
            admits no implicit UTC anywhere in the fabric: the canonical
            serializer refuses a naive instant rather than guessing an offset,
            and a determination instant whose offset is the deciding host's
            local configuration is an instant that replays differently on a
            different host.
    """

    surface: str
    address: str
    tenant_id: str
    determined_at: datetime

    @field_validator("determined_at")
    @classmethod
    def _instant_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"determined_at {value.isoformat()!r} carries no UTC offset,"
                " and a naive instant cannot cross this seam — the canonical"
                " serializer refuses it rather than guessing an offset, so the"
                " same denial would be recorded at a different instant on"
                " every host (D-IMPL-38). Attach an explicit timezone:"
                " `datetime(..., tzinfo=UTC)`, or `value.replace(tzinfo=UTC)`"
                " if the instant is already UTC"
            )
        return value


class RefusalEnvelope(CCFContract):
    """One shape carrying any shipped refusal, with nothing flattened out.

    Constraint (a) of Amendment 1 §A. The envelope is a *transport* shape: it
    restates no refusal's meaning and computes nothing. It promotes the four
    members every consumer needs to branch on, preserves everything else the
    refusal type declared in :attr:`fields`, and attaches the question and the
    lineage the refusal itself does not carry.

    **Promotion rules, applied by reflection over the refusal's declared
    fields** — never by a per-type table, so a field added to a refusal type
    next year appears here without an edit:

    ``reason``
        A :class:`~ccf.products.gates.GateRefusal` reports its ``gate``,
        because that is the token its whole family was designed to be read by.
        A refusal outside that family that declares a field named ``reason``
        reports it — the closed request and payload reason vocabularies. A
        refusal that declares neither reports its own :attr:`kind`.
    ``key``
        The value of a declared field named ``key``, or ``None``. A TTL refusal
        names no parameter, and saying so is not a loss.
    ``detail``
        The prose the refusal already carries, unchanged.
    ``fields``
        Every remaining declared field, including inherited ones — the whole
        MRO, so a three-level refusal keeps its leaf, middle and base fields
        alike. A member promoted above is not repeated here; a member that
        merely shares a *name* with a promotion that did not take it — a
        gate-family refusal's own ``reason`` field, say — is kept, because
        dropping it would be exactly the flattening this type exists to
        prevent.

    Attributes:
        kind: Which refusal type this was, from :data:`REFUSAL_KINDS`. The
            whole substance of constraint (a): a consumer that cannot name the
            kind cannot audit the refusal.
        reason: The refusal's own reason or gate token, per the rules above.
        key: What the refusal names, when it names one.
        detail: The refusal's human-readable statement, for an operator
            reading a log. The typed members are the machine-readable version;
            nothing should parse this string.
        fields: The refusal type's own declared fields, each rendered in the
            SDK's one canonical form (:func:`~ccf.contracts.canonical.canonical_bytes`),
            so a set arrives sorted, an instant arrives as RFC3339 UTC, and a
            string arrives quoted — which is what keeps a presented ``"3"``
            distinguishable from a presented ``3`` after the crossing.
        request: The question, as it stood before assembly.
        pre_assembly_lineage: The partial lineage that existed at the point of
            refusal, or ``None`` when the refusal preceded assembly entirely.
            The distinction is load-bearing and is carried rather than
            flattened: a request-conformity verdict is reached before the graph
            is touched and *has* no lineage, while a payload verdict or any
            gate refusal has a candidate contract behind it and therefore a
            real, non-empty answer. ``None`` here is the positive assertion
            *there was none*, not *it was dropped*.

    **Six members joined additively in** ``24.6-07`` (``24.6-L-08``;
    ``D-IMPL-253`` Q13/Q14 — Dave: *"Extend* :class:`RefusalEnvelope`
    *additively. We already decided it is effectively the shell form of the
    governed response; another wrapper buys little."*). Each is
    sentinel-defaulted and **hash-transparent at its sentinel**
    (``D-IMPL-243``), so a shell minted before ``24.6-07`` renders
    byte-identically and no envelope's content address moves:

    ``policy_bindings``
        The identity and version of every Control Plane artifact that governed
        this refusal — the policy bundle, the constraints in force at the
        question's instant, and the entitlement policy when one decided
        anything. :class:`~ccf.products.provenance.ProvenanceSource` rather
        than a pin pair, because a source with no version lane (a request's own
        identity, a backend capability) is a real governing input and minting
        an artifact lane for it would be the fake artifact ``D-IMPL-253``
        amendment 2 (1) forbids. The empty tuple is *nothing governed
        version-bearingly*, which is what every shell said before the field
        existed.
    ``replay_reference``
        The decision record's address —
        :attr:`~ccf.artifacts.protocol.ArtifactRef.uri`.
        :data:`NO_REPLAY_REFERENCE` is the positive claim that the seam which
        produced this shell minted none. The **recorded** shell always carries
        the sentinel; only the returned one learns its own address.
    ``evidence``
        What the fabric is permitted to show of the search behind the refusal.
        The Disclosure layer (``D-IMPL-254``) is the only thing that fills or
        empties it for a consumer; a refusal reached before any plan ran
        carries ``None``, which is *there was no search*.
    ``provenance``
        The Authority layer's own record — which authority set each
        parameter's value, which constraint bounded it, and whether an override
        was entitled (``D-IMPL-253`` Q1/Q6). Carried whole rather than
        collapsed, for Q1's reason: *"do not collapse authority after
        resolution."*
    ``disclosure``
        Which disclosure level was applied to produce this shell. ``None`` is
        the **internal, undisclosed** form — the shell as the fabric recorded
        it, before Policy decided what may cross a consumer boundary.
    ``resource``
        The :class:`ResourceRequestIdentity` of a **delivery-boundary** denial
        (``D-IMPL-256`` (1)). ``None`` on a refusal that answered a question:
        a resolver's own refusals carry their question in :attr:`request`, and
        a second identity for the same fact would be two spellings of one
        claim. Retained on the recorded internal shell at every level; on a
        DISCLOSED shell it is governed by the Disclosure layer like any other
        member — for ``subject-unavailable`` it is normalized to ``None`` below
        ``full`` (:data:`~ccf.products.disclosure.INDISTINGUISHABLE_BELOW_FULL`,
        ``D-IMPL-260`` P-J), because a boundary denial carrying one and an
        assembler's nonexistent-subject determination carrying none would tell
        the two apart by key presence alone.
    """

    kind: str
    reason: str
    key: str | None
    detail: str
    fields: Mapping[str, str]
    request: RequestIdentity
    pre_assembly_lineage: ProductLineage | None
    policy_bindings: tuple[ProvenanceSource, ...] = Field(
        default=(), json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    replay_reference: str = Field(
        default=NO_REPLAY_REFERENCE, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    evidence: RefusalEvidence | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    provenance: EffectiveRequest | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    disclosure: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    resource: ResourceRequestIdentity | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


#: Every refusal type the fabric ships, mapped to the token that names it on
#: the wire. Mechanism, not values: it maps SDK types to SDK tokens and holds
#: no deployment's vocabulary (CINV-01).
#:
#: **Closed, and closed by equality.** The exhaustiveness gate in
#: ``tests/products/test_refusal_envelope.py`` walks ``src/`` structurally and
#: asserts this mapping's key set equals what the tree declares, minus the two
#: allowlists below. A type added to the tree and not added here fails the
#: build; a token declared here whose type no longer ships fails it too.
REFUSAL_KINDS: Final[Mapping[type[CCFContract], str]] = {
    # The three-gate family (whitepaper §7.6), the additive attestation
    # gate beside it, and the ONE structural declared-obligations gate
    # D-IMPL-237 licenses — the kind the HTTP door maps to 409. As of
    # 24.6-04 that gate carries ONE obligation (`lineage-inputs`, 24.5-L-26):
    # the debt half and the 409 DEBT route it served are retired, because a
    # class's debt figure is a default tolerance rather than an obligation
    # (`D-IMPL-251` C1=A). The kind and its 409 mapping stand for the lineage
    # obligation. The empty-operator gate briefly had two kinds (24.5-L-24) —
    # a product that DECLARED no operators, and an operator that RETURNED an
    # empty set. As of 24.6-05 it has ONE: `D-IMPL-242` amendment 1 with
    # `D-IMPL-253` Q11/Q12 rules that an operator which ran and found nothing
    # COMPUTED, so it is served with its search recorded on the product
    # (`ccf.products.contract.ComputedEmptyFinding`) and there is no kind to
    # name. `empty-operator-refusal` keeps the one meaning it always had:
    # a product computed by nothing (INV-CH7-46).
    GateRefusal: "gate-refusal",
    EmptyOperatorRefusal: "empty-operator-refusal",
    LineageMismatchRefusal: "lineage-mismatch-refusal",
    LineageAttributionRefusal: "lineage-attribution-refusal",
    TTLRefusal: "ttl-refusal",
    # `D-IMPL-341` R-3: gate 3's second reason — no evidence instant to anchor
    # on — is its own kind, so a caller can tell "the window has passed" from
    # "there was nothing to run a window from".
    TTLAnchorRefusal: "ttl-anchor-refusal",
    AttestationRefusal: "attestation-refusal",
    # `D-IMPL-334`. Serve-time dependency invalidation: an entity this product
    # touched moved after the snapshot it was built at, so it is no longer
    # eligible to serve. Its own kind rather than a reuse of `ttl-refusal`,
    # because the two say different things — a TTL refusal is about elapsed
    # time, and this one is about the world having changed. A consumer that
    # could not tell them apart would retry the wrong one.
    DependencyInvalidationRefusal: "dependency-invalidation-refusal",
    DeclaredObligationRefusal: "declared-obligation-refusal",
    # `D-IMPL-336`. Child admission for a composite Context Product. Its own
    # kind rather than a reuse of `dependency-invalidation-refusal`, because
    # the two answer different questions and a consumer that could not tell
    # them apart would retry the wrong thing: a dependency-invalidation refusal
    # says *the world moved under a product this fabric holds*, and this one
    # says *a CHILD offered to a composition did not pass admission* — which
    # may be a class mismatch, an incompatible version, another `as_of`, an
    # address that did not recompute, unassessable debt, or eligibility this
    # fabric could not establish. The machine-readable cause is the refusal's
    # own `reason`, so the kind stays one token while the vocabulary of causes
    # stays closed at `ccf.replay.record.CHILD_OUTCOME_STATUSES`.
    #
    # The token is `composite-child-` and NOT `child-admission-` because
    # `admission-refusal` (the peering kind) is a substring of the latter, and
    # this vocabulary forbids one token containing another — a consumer
    # prefix-matching `admission-refusal` would silently swallow every
    # composite refusal. Caught by
    # `test_every_kind_has_its_own_test_function`, which is exactly the guard
    # that should catch it.
    ChildAdmissionRefusal: "composite-child-refusal",
    # `24.10-02` / `R-11` (`D-IMPL-282` option 1a with `D-IMPL-224`): the
    # seventh `GateRefusal` sibling, and the token names a **declared** product
    # invariant whose IMPLEMENTATION the deployment supplied. That is exactly
    # what distinguishes it in an audit from the SDK's own universal gates: the
    # six tokens above are mechanism this SDK ships and can be reasoned about
    # from `src/` alone, while this one refuses on a predicate that lives in
    # the deployment's tree — so an examiner reading a decision record must
    # resolve the class declaration to learn what was checked. The gate's
    # identity and lane are stamped by the resolver from that declaration and
    # never by the callable. It is NOT a member of `run_gates`' sequence and
    # adds nothing to `GATE_DECLARED_OBLIGATIONS` (`D-11`); it is post-assembly
    # (a candidate existed, so NOT in `_PRE_ASSEMBLY_REFUSALS`), and no shipped
    # token is a substring of it or it of them.
    ProductInvariantRefusal: "product-invariant-refusal",
    # `D-IMPL-358` step 5. The question reaches outside the window this tenant
    # answers for — judged BEFORE acquisition, so unlike every gate token above
    # it there is no candidate and no lineage. Its own kind rather than a reuse
    # of `constraint-refusal`: a constraint refusal is about a declared
    # PARAMETER's value, and this is about the question's INSTANT, which is an
    # address axis rather than a parameter and is judged against a Control Plane
    # policy the caller cannot see. A consumer that could not tell them apart
    # would retry by changing a parameter. No shipped token is a substring of
    # this one or it of them (checked: 27 tokens, no collision).
    TemporalBoundRefusal: "temporal-bound-refusal",
    # Beside it and deliberately NOT of it (24.6-L-05, `D-IMPL-251` C2=B):
    # `tolerance-exceeded` is not a gate token and `ToleranceExceededRefusal`
    # is not a `GateRefusal`. The gates admitted the product; an applicable
    # declared tolerance — the class's default, the caller's own value or a
    # policy constraint — then withheld its fulfillment, and the shell carries
    # which authority set it. The token is post-assembly (a candidate existed,
    # so it is NOT in `_PRE_ASSEMBLY_REFUSALS`), and no shipped token is a
    # substring of it or it of them. Which door class it maps to is plan 09's
    # question; the DEBT half of the 409 route retired with the gate half.
    ToleranceExceededRefusal: "tolerance-exceeded",
    # The peering-admission family, which derives from the gate family rather
    # than paralleling it (CLAUDE.md §7.2).
    AdmissionRefusal: "admission-refusal",
    PayloadTooLargeRefusal: "payload-too-large-refusal",
    SignatureRefusal: "signature-refusal",
    # `SEC-022`: the issuance check and the replay consult.
    IssuanceRefusal: "issuance-refusal",
    ContractRefusal: "contract-refusal",
    PolicyBindingRefusal: "policy-binding-refusal",
    LineageContinuityRefusal: "lineage-continuity-refusal",
    # The mount refusal, on the same derivation argument.
    ProductMountRefusal: "product-mount-refusal",
    # The two conformity verdicts — named for what they are rather than for
    # the gate family they deliberately do not join — and, beside them, the
    # pre-assembly refusal for an anchor that resolves to more than one
    # entity (24.5-L-16). The SDK names the kind; who is ambiguous, and what a
    # product does about it, stays the product's.
    ProductRequestViolation: "product-request-violation",
    PayloadSchemaViolation: "payload-schema-violation",
    AnchorAmbiguityRefusal: "anchor-ambiguity-refusal",
    # The two constraint-layer determinations (24.6-L-07, D-IMPL-253 Q4/Q7),
    # reached while the effective request is being resolved and therefore
    # before the graph is touched. `constraint-refusal` is a value the fabric
    # may not act on — the caller's or the class's, held to a policy or a
    # technical bound; `policy-resolution-conflict` is the deployment's own
    # policy set disagreeing with itself, which is the shell that exists so
    # priority never has to erase an applicable hard constraint. Neither token
    # is a substring of `contract-refusal` or `policy-binding-refusal`, the two
    # shipped tokens they read closest to, and the closure gate checks that
    # rather than leaving it to the eye.
    ConstraintRefusal: "constraint-refusal",
    PolicyResolutionConflict: "policy-resolution-conflict",
    # The assembly-time mixing rule, which is not a fourth gate.
    MixingRefusal: "mixing-refusal",
    # The assembly-time refusal returned as a value. `24.6-L-02` narrowed the
    # exception of the same name to invariant/configuration/runtime failures
    # (`D-IMPL-253` amendment 2 (3)), so the SDK's own assembler now RETURNS
    # this for the two identity determinations it makes. Still a second channel
    # beside `AssemblyRefused` and never a translation of it: no door catches
    # the raise, because a raise now means the fabric could not determine
    # anything at all.
    AssemblyRefusal: "assembly-refusal",
    # The one canonical outcome a nonexistent subject and an unauthorized
    # principal SHARE (24.6-L-21, `D-IMPL-253` Q27 + amendment 2 (4)). There is
    # deliberately no second, suppression-silent kind: two kinds would be the
    # distinction Q27 forbids, visible on the wire. `subject-unavailable` is
    # not a substring of any shipped token and none is a substring of it, which
    # the closure gate checks rather than the eye.
    SubjectUnavailableRefusal: "subject-unavailable",
    # SEC-009 (`D-IMPL-374` (4); design `D-IMPL-367` §5.1): an erased address,
    # read at `reasoned` or `full`. Its own kind rather than a reuse of
    # `subject-unavailable`: an erasure is a recorded decision, not an absence,
    # and above `minimal` the reader is told so. No shipped token is a
    # substring of `erased-content` or it of them.
    ErasedContentRefusal: "erased-content",
}

#: ``…Refusal``-named contracts under ``src/`` that are **not** product
#: refusals. Each is a verdict on a path that never reaches a product seam, so
#: none belongs in the envelope's vocabulary:
#:
#: * ``RegistrationRefusal`` — a Control Plane registration verdict.
#: * ``EffectRefusal`` — a harness effect-capture verdict (CLAUDE.md §7.3,
#:   seam 3).
#: * ``GrantRefusal`` — a skilling-governance verdict (CLAUDE.md §6.2).
#: * ``DefaultConflict`` — an agent-composition verdict: two archetypes
#:   contributing the same default. It joined this allowlist in ``24.6-L-07``,
#:   when the structural walk widened to the ``…Conflict`` name family so that
#:   :class:`~ccf.products.constraints.PolicyResolutionConflict` could not
#:   enter the vocabulary by exemption. It has been in ``src/`` since the agent
#:   framework shipped and reaches no product seam.
#:
#: An allowlist rather than an omission: the gate asserts this set equals
#: exactly what the structural walk found and could not place, so a fifth
#: such class demands a ruling instead of passing unseen.
NON_PRODUCT_REFUSALS: Final[frozenset[str]] = frozenset(
    {"RegistrationRefusal", "EffectRefusal", "GrantRefusal", "DefaultConflict"}
)

#: ``…Violation``- and ``…Conflict``-named classes under ``src/`` that are
#: **exceptions rather than values**, and therefore outside an envelope that
#: carries returned refusals:
#:
#: * ``TrustPolicyViolation`` — raised on a peering-trust lookup.
#: * ``SnapshotScopeViolation`` — raised on a replay-snapshot scope miss.
#: * ``ProductEntitlementViolation`` — raised inside
#:   :mod:`ccf_runtime.authz.product_entitlement`, and it stays a raise there:
#:   an entitlement source must not be able to hand a delivery path a verdict
#:   it can treat as "not sure". What crosses a consumer boundary is not this
#:   exception but the governed determination the delivery boundary makes from
#:   it — :class:`SubjectUnavailableRefusal` with ``cause="unauthorized"``,
#:   minted and disclosed by ``runtime/ccf_runtime/authz/delivery_boundary.py``
#:   (``24.6-L-21``, ``D-IMPL-256``). So it is outside this envelope's
#:   vocabulary because it is an exception, not because entitlement is
#:   deferred: it no longer is.
#: * ``SingleWriterViolation`` — the single-writer invariant firing
#:   (CLAUDE.md §10).
#: * ``WebhookEndpointConflict`` — raised when two HITL webhook registrations
#:   claim one endpoint.
#: * ``FragmentFamilyConflict`` — raised when two projection fragments claim
#:   one family.
#: * ``ConstraintEffectivityConflict`` — raised when the Control Plane holds
#:   two authoritative statements in force at one instant and they disagree.
#:   **Deliberately an exception and not a governed shell** (``D-IMPL-253``
#:   Q15, Dave: *"retain exceptions for actual configuration/invariant
#:   contradictions"*): a governed "no" is a determination the fabric reached,
#:   while two contradicting authoritative inputs are a state in which it
#:   cannot determine what is true.
#:
#: The last two joined in ``24.6-L-07`` for the reason ``DefaultConflict``
#: joined the allowlist above: the structural walk widened to the ``…Conflict``
#: name family so that
#: :class:`~ccf.products.constraints.PolicyResolutionConflict` could not enter
#: the vocabulary by exemption, and widening a walk means placing everything it
#: then finds. Both are pre-existing ``ValueError`` subclasses and neither
#: changed.
#:
#: This is the second allowlist, and it exists so the exception half of the
#: name vocabulary closes by equality too. Two ``…Violation``-named classes
#: *are* in :data:`REFUSAL_KINDS`; they get there because their base resolves
#: to :class:`~ccf.contracts.base.CCFContract`, never because a constant names
#: them. Without this set the half a ``…Refusal``-only walk cannot reach would
#: stay enumerated by hand, and a new contract-based ``…Violation`` would ship
#: untranslated with the gate green.
NON_VALUE_VIOLATIONS: Final[frozenset[str]] = frozenset(
    {
        "TrustPolicyViolation",
        "SnapshotScopeViolation",
        "ProductEntitlementViolation",
        "SingleWriterViolation",
        "WebhookEndpointConflict",
        "FragmentFamilyConflict",
        "ConstraintEffectivityConflict",
    }
)


#: Refusal types reached **before** the graph is touched, and which therefore
#: cannot have a pre-assembly lineage. Offering one alongside such a refusal is
#: a category error rather than extra information, so :func:`envelope_for`
#: refuses it — which is what makes D-09's assembly-boundary split structural
#: instead of conventional. A payload verdict and every gate refusal have a
#: candidate contract behind them and are deliberately absent from this set.
#:
#: Private: it is a statement about *when* the fabric reaches a refusal, not a
#: second vocabulary, and it is not part of this module's exported surface.
#:
#: :class:`~ccf.products.request.AnchorAmbiguityRefusal` joined in ``24.5-L-16``:
#: an anchor resolves before the graph is touched, so offering it a lineage is
#: the same false claim.
#:
#: :class:`~ccf.products.constraints.ConstraintRefusal` and
#: :class:`~ccf.products.constraints.PolicyResolutionConflict` joined in
#: ``24.6-L-07`` on the same argument: both are reached while the *effective
#: request* is being resolved, which is strictly before an operator plan is
#: built, so a lineage offered with either would claim evidence that could not
#: exist yet.
#:
#: :class:`SubjectUnavailableRefusal` joined in ``24.6-L-21``. A subject that
#: does not resolve is settled before the graph is walked, and an unauthorized
#: one is settled at the delivery boundary before any plan exists — and the two
#: must be **observationally equivalent** (``D-IMPL-253`` amendment 2 (4)), so
#: admitting a lineage on one of the two causes would be a leak channel rather
#: than extra information.
_PRE_ASSEMBLY_REFUSALS: Final[frozenset[type[CCFContract]]] = frozenset(
    {
        ProductRequestViolation,
        AnchorAmbiguityRefusal,
        ConstraintRefusal,
        PolicyResolutionConflict,
        SubjectUnavailableRefusal,
        # SEC-009: decided at the read, before any plan exists.
        ErasedContentRefusal,
        # `D-IMPL-358` step 5: judged before acquisition and before the graph
        # read, so no candidate exists and no lineage is invented for it.
        TemporalBoundRefusal,
    }
)


def _render(value: object) -> str:
    """One field value in the SDK's one canonical form.

    Not ``str()``: a ``frozenset`` has no stable ``repr`` ordering and a
    ``datetime`` has no single textual form, and both reach an audit record
    through this envelope. :func:`~ccf.contracts.canonical.canonical_bytes` is
    the SDK's single answer to both, so this module defines no second one.
    """
    return canonical_bytes(value).decode("utf-8")


def envelope_for(
    refusal: object,
    *,
    request: RequestIdentity,
    pre_assembly_lineage: ProductLineage | None = None,
    policy_bindings: tuple[ProvenanceSource, ...] = (),
    evidence: RefusalEvidence | None = None,
    provenance: EffectiveRequest | None = None,
    resource: ResourceRequestIdentity | None = None,
) -> RefusalEnvelope:
    """Translate any shipped refusal into the one envelope, losing nothing.

    Total over :data:`REFUSAL_KINDS` and defined nowhere else: a type this
    mapping does not name raises rather than receiving a best-effort envelope.

    **Dispatch is on the exact type, never ``isinstance``.** An ``isinstance``
    chain would translate an unknown subclass as its nearest known ancestor and
    report that ancestor's kind — a flattening that produces a perfectly
    well-formed envelope carrying the wrong answer, which is the failure mode
    hardest to notice and exactly the one constraint (a) forbids.

    **The promoted members are found by reflection over the refusal's declared
    fields**, so a field added to a refusal type appears in the envelope with no
    edit here, and the exhaustiveness gate has live structure to check rather
    than a transcription to agree with. See :class:`RefusalEnvelope` for the
    three promotion rules.

    Args:
        refusal: A value of any type named in :data:`REFUSAL_KINDS`.
        request: The question this refusal answers, which the refusal itself
            does not carry — the caller holding the request supplies it.
        pre_assembly_lineage: The partial lineage that existed at the point of
            refusal, when one did. Must be ``None`` for a refusal the fabric
            reaches before touching the graph.
        policy_bindings: Every Control Plane source that governed this refusal,
            by identity and version (``24.6-07``). The empty tuple is the
            positive *nothing version-bearing governed it*.
        evidence: What the fabric is permitted to show of the search behind the
            refusal, when there was one.
        provenance: The Authority layer's resolution record, when the question
            reached that layer.
        resource: The resource-request identity of a delivery-boundary denial
            (``D-IMPL-256`` (1)); ``None`` on a refusal that answered a
            question.

    Returns:
        The envelope, carrying the kind, the promoted members, every remaining
        declared field canonically rendered, the request, the lineage or its
        explicit absence, and the four governance members above. The replay
        reference is **not** among this function's arguments: a shell learns
        its own address only from the seam that appended its record
        (:class:`~ccf.products.resolver.ReplayRefusalRecorder`), so an envelope
        this function returns always carries :data:`NO_REPLAY_REFERENCE`.

    Raises:
        TypeError: ``refusal`` is not an instance of a type this module
            translates. The message names the type, because the two ways to
            resolve it are both deliberate acts — translate it in
            ``src/ccf/products/refusal.py``, or record it in one of the two
            allowlists with its reason.
        ValueError: a lineage was offered alongside a refusal reached before
            assembly began.
    """
    # One guard for both ways of not being a refusal — not a contract at all,
    # or a contract this module does not translate. They are the same defect
    # from the caller's side and get the same message.
    if not isinstance(refusal, CCFContract) or type(refusal) not in REFUSAL_KINDS:
        raise TypeError(
            f"{type(refusal).__name__} is not a refusal type this envelope"
            " translates; add it to REFUSAL_KINDS in"
            " `src/ccf/products/refusal.py`, or to NON_PRODUCT_REFUSALS or"
            " NON_VALUE_VIOLATIONS with its reason"
        )
    kind = REFUSAL_KINDS[type(refusal)]

    if pre_assembly_lineage is not None and type(refusal) in _PRE_ASSEMBLY_REFUSALS:
        raise ValueError(
            f"{type(refusal).__name__} is reached before the graph is touched,"
            " so it has no pre-assembly lineage; pass None"
        )

    declared = tuple(type(refusal).model_fields)
    consumed: set[str] = set()

    if isinstance(refusal, GateRefusal):
        # The gate token is what the whole family was designed to be read by,
        # so it wins even on the one type that also declares a `reason`.
        reason = refusal.gate
        consumed.add("gate")
    elif "reason" in declared:
        reason = str(getattr(refusal, "reason"))
        consumed.add("reason")
    else:
        # A refusal declaring neither is still a refusal; its kind is the most
        # specific true thing that can be said about why.
        reason = kind

    key: str | None = None
    if "key" in declared:
        key = str(getattr(refusal, "key"))
        consumed.add("key")

    detail = ""
    if "detail" in declared:
        detail = str(getattr(refusal, "detail"))
        consumed.add("detail")

    fields = {
        name: _render(getattr(refusal, name))
        for name in declared
        if name not in consumed
    }

    return RefusalEnvelope(
        kind=kind,
        reason=reason,
        key=key,
        detail=detail,
        fields=fields,
        request=request,
        pre_assembly_lineage=pre_assembly_lineage,
        policy_bindings=policy_bindings,
        evidence=evidence,
        provenance=provenance,
        resource=resource,
    )


# ---------------------------------------------------------------------------
# `D-IMPL-304` — the typed handoff for a governed refusal that cannot be RETURNED.
# ---------------------------------------------------------------------------


class ResolvedByTheResolver:
    """The one explicit resolution state a raiser INSIDE a resolver's own seams may state.

    A deployment's acquisition hook, or a composition root's acquisition
    callable, holds the effective question the resolver handed it and not the
    :class:`~ccf.products.provenance.EffectiveRequest` evidence the resolver
    established on the way there. Stating this value says exactly that — *the
    resolver that called me holds the resolution* — and the resolver records
    its own evidence, which is the truth. It is a statement, never a default:
    :class:`GovernedRefusalRaised` refuses construction without one, and a
    delivery boundary (which holds no resolver evidence) refuses this value
    as the programming error it is there.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "RESOLVED_BY_THE_RESOLVER"


#: See :class:`ResolvedByTheResolver`.
RESOLVED_BY_THE_RESOLVER: Final[ResolvedByTheResolver] = ResolvedByTheResolver()


class GovernedRefusalRaised(Exception):
    """A governed determination that could not be RETURNED from where it was made (`D-IMPL-304`).

    **An explicit handoff, never a translation.** Raised only by code that
    already HOLDS a refusal the fabric produced — a value of a type
    :data:`REFUSAL_KINDS` names, or an envelope built from one — together with
    the resolution state that accompanied it. The delivery boundaries and the
    resolver's acquisition seam catch exactly this type, record it through the
    ONE recorder and deliver it through the normal disclosure and emission
    path. Nothing in the SDK raises it on a caller's behalf, nothing parses an
    exception's message to recover a reason, and nothing invents evidence the
    raiser did not hold.

    **Deliberately not a subclass of the fault types.** The doors treat
    ``ValueError``, ``TypeError``, ``LookupError`` and ``OSError`` as *CCF or
    its runtime failed* and answer with an opaque ``ccf-runtime-failure``
    (``D-IMPL-253`` Q20). This type derives from :class:`Exception` directly so
    it can never be mistaken for one of them — and so a raiser cannot smuggle
    a fault through as a determination by subclassing.

    **``resolution`` is required** (``D-IMPL-264`` amendment 1, Dave verbatim:
    *"Any API that constructs or delegates construction of a replay record
    must require an explicit resolution state: effective/partial resolution or
    explicit not-applicable marker. No intermediate layer may manufacture the
    marker from omission."*). Three explicit states, and which is honest
    depends on where the raiser stands:

    * an :class:`~ccf.products.provenance.EffectiveRequest` — the (possibly
      partial) evidence the SDK's own resolution established and the raiser
      holds, as a low-road composition root does after calling
      ``resolve_effective_request`` itself;
    * :class:`~ccf.replay.record.ResolutionNotApplicable` — no resolution ran,
      with its reason;
    * :data:`RESOLVED_BY_THE_RESOLVER` — the raiser is inside a resolver's
      acquisition seam and the resolver holds the evidence. Valid there only.

    Attributes:
        refusal: The governed refusal itself — a :data:`REFUSAL_KINDS` value
            or a :class:`RefusalEnvelope`.
        resolution: One of the three states above.
        request: The pre-assembly request identity, when the raiser holds it;
            a boundary that catches the raise supplies its own otherwise.
    """

    def __init__(
        self,
        refusal: object,
        *,
        resolution: object,
        request: RequestIdentity | None = None,
    ) -> None:
        # Lazy on purpose: `ccf.replay.record` is downstream of this module.
        from ccf.replay.record import ResolutionNotApplicable  # noqa: PLC0415

        named = next((name for cls, name in REFUSAL_KINDS.items() if isinstance(refusal, cls)), None)
        if not isinstance(refusal, RefusalEnvelope) and named is None:
            raise TypeError(
                f"GovernedRefusalRaised carries a governed refusal — a value of a type"
                f" REFUSAL_KINDS names, or a RefusalEnvelope — not {type(refusal).__name__!r};"
                " it is a handoff for a determination the fabric made, never a wrapper"
                " for an arbitrary failure (D-IMPL-304)"
            )
        if not isinstance(resolution, (EffectiveRequest, ResolutionNotApplicable, ResolvedByTheResolver)):
            raise TypeError(
                "GovernedRefusalRaised requires an explicit resolution state — the"
                " EffectiveRequest evidence the raiser holds, an explicit"
                " ResolutionNotApplicable, or RESOLVED_BY_THE_RESOLVER inside a"
                f" resolver's acquisition seam — not {type(resolution).__name__!r}"
                " (D-IMPL-264 amendment 1)"
            )
        kind = refusal.kind if isinstance(refusal, RefusalEnvelope) else named
        super().__init__(f"governed refusal raised: {kind}")
        self.refusal = refusal
        self.resolution = resolution
        self.request = request
