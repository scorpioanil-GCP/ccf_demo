"""The consuming bank's vocabulary, its three verbs, and its federation seam.

[ADAPT] the vocabulary and the verbs. [MECHANISM] the context types imported
from the SDK — and, in the one clearly fenced block below, the consumer chain
this deployment has to hand-build.

**The fenced block is the rung's measured friction and nothing else.** Between
``BEGIN build_children GLUE`` and ``END build_children GLUE`` is the agent,
catalog, grant, gate and resolver chain that `open_product` DERIVES for any
composite declaring ``agent:``/``skills:``/``questions=``. This deployment
cannot declare them, because ``include_federated`` is a REQUEST parameter and
`open_product` refuses ``build_children=`` beside a declared chain. Every line
in the fence is a line an adopter with a request-scoped optional child has to
write, and `CLD-F-04` is its measurement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any



import acquisition
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, assess_debt
from ccf.products.child_resolver import ChildQuestion, QuestionBoundChildResolver
from ccf.products.contract import ChildRequirement
from ccf.products.product import AcquisitionContext, AssessmentContext, ConsumerContext
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    SubjectUnavailableRefusal,
)
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

#: The request-contract argument names — the contract's, restated nowhere.
#: `intent` is deliberately absent: it is a top-level `ProductRequest` field,
#: and a contract argument shadowing it is refused by the SDK.
FACILITY = "facility_id"
INCLUDE_FEDERATED = "include_federated"
COUNTERPARTIES = "counterparties"
AS_OF = "as_of"

#: The environment document's names for the two source legs.
SOURCE_RELATIONAL = "syndicate_relational"
SOURCE_GRAPH = "syndicate_graph"

#: The child class this composite may acquire across the boundary.
CHILD_CLASS = "cb.co-lender-position"

#: Attribute keys the projection reads back off the view.
CLASSIFICATION = "classification"
MEMBER_LEI = "member_lei"
COMMITMENT = "commitment_usd"
IS_OWN = "is_own_position"
CONSENT_PERCENT = "consent_percent"
REQUEST_SCOPE = "request_scope"
DISCLOSE_SCOPE = "disclose_scope"
COUNTERPARTY_LEI = "counterparty_lei"

#: The separator a multi-valued scope is carried under in a claim attribute.
#: Claim attributes are flat strings; the two scopes stay two SETS by being
#: parsed back apart, never by being merged (`CLD-G11`).
SCOPE_SEPARATOR = "|"

#: The typed codes this deployment's governed refusals carry.
OUT_OF_ENVELOPE_CODE = "envelope-scope-exceeded"
NO_ENVELOPE_CODE = "no-envelope-in-force"


def plan_id(facility_id: str) -> str:
    return f"cp-20.syndicate-co-lender/{facility_id}"


def _as_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _text(value: object) -> str:
    return "" if value is None else str(value)


# ---------------------------------------------------------------------------
# From the effective request to a read; from a read to fabric state.
# ---------------------------------------------------------------------------


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Read OUR two stores at the effective request; hand back dated claims.

    Raises:
        GovernedRefusalRaised: the anchor resolves to no facility we hold.
    """
    effective = context.request.parameters
    try:
        syndicate = acquisition.acquire(
            facility_id=str(effective[FACILITY]),
            relational=context.sources[SOURCE_RELATIONAL],
            graph=context.sources[SOURCE_GRAPH],
        )
    except acquisition.UnknownFacility as unknown:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent", detail=str(unknown), error_code="unknown-facility"
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unknown
    # ENVELOPE CONTAINMENT USED TO RUN HERE, AND NO LONGER DOES (`CLD-F-06`).
    #
    # It was here because the acquisition seam was the ONLY place a
    # deployment's governed refusal became data. `D-IMPL-347` A2 wrapped the
    # other three seams, so the check now runs where the decision belongs —
    # at the child-resolution seam, immediately before dispatch — and this
    # acquisition is back to doing one thing.
    return envelopes(syndicate, tenant_id=context.tenant_id, at=context.instant)


def refuse_outside_envelope(
    in_force_rows: Sequence[acquisition.Envelope], *, request: ProductRequest
) -> None:
    """Hold every named counterparty to its bilateral envelope. Before any dispatch.

    `Q1`(b), Dave 2026-09-22: `requestScope` names PRODUCT CLASSES. A
    counterparty whose envelope does not contain this composite's requested
    class is not askable, and **the refusal is the demonstration** — the
    estate is never retuned to make an out-of-scope member admissible.

    A no-op when the caller did not ask across the boundary: there is nothing
    to contain when nothing is requested.
    """
    effective = request.parameters
    if not _as_bool(effective.get(INCLUDE_FEDERATED), default=False):
        return
    named = tuple(str(entry) for entry in (effective.get(COUNTERPARTIES) or ()))
    if not named:
        return
    requested = str(acquisition.federation_policy()["requested_class"])
    in_force = {
        row.counterparty_lei: row
        for row in in_force_rows
        if row.counterparty_lei is not None
    }
    for counterparty in named:
        envelope = in_force.get(counterparty)
        if envelope is None:
            raise GovernedRefusalRaised(
                SubjectUnavailableRefusal(
                    cause="unauthorized",
                    detail=(
                        f"no bilateral disclosure envelope is in force with"
                        f" {counterparty!r}; a federated ask outside a"
                        " negotiated envelope is not made"
                    ),
                    error_code=NO_ENVELOPE_CODE,
                ),
                resolution=RESOLVED_BY_THE_RESOLVER,
            )
        if requested not in envelope.request_scope:
            raise GovernedRefusalRaised(
                SubjectUnavailableRefusal(
                    cause="unauthorized",
                    detail=(
                        f"the envelope in force with {counterparty!r} admits"
                        f" {list(envelope.request_scope)!r} and this composite"
                        f" asks for {requested!r}; the ask exceeds the"
                        " negotiated request scope and no peer is called"
                    ),
                    error_code=OUT_OF_ENVELOPE_CODE,
                ),
                resolution=RESOLVED_BY_THE_RESOLVER,
            )


def envelopes(
    syndicate: acquisition.Syndicate, *, tenant_id: str, at: datetime
) -> tuple[SignalEnvelope, ...]:
    """The syndicate as dated claims — EDGES FIRST, ATTRIBUTED NODES LAST."""
    vocab = acquisition.vocabulary()
    templates = vocab["uri_templates"]
    edges = vocab["edges"]
    marks = vocab["classifications"]
    facility_uri = str(templates["facility"]).format(
        facility_id=syndicate.facility.facility_id
    )

    def participation_uri(row: acquisition.Participation) -> str:
        key = "own_participation" if row.is_own_position else "participation"
        return (
            row.participation_id
            if row.is_own_position
            else str(templates[key]).format(participation_id=row.participation_id)
        )

    edge_envelopes = [
        _edge(facility_uri, participation_uri(row), predicate=str(edges["participation"]),
              tenant_id=tenant_id, at=at, ordinal=ordinal)
        for ordinal, row in enumerate(syndicate.participations)
    ]
    edge_envelopes += [
        _edge(facility_uri, str(templates["threshold"]).format(threshold_id=row.threshold_id),
              predicate=str(edges["threshold"]), tenant_id=tenant_id, at=at,
              ordinal=len(edge_envelopes) + ordinal)
        for ordinal, row in enumerate(syndicate.thresholds)
    ]
    edge_envelopes += [
        _edge(facility_uri, str(templates["envelope"]).format(envelope_id=row.envelope_id),
              predicate=str(edges["envelope"]), tenant_id=tenant_id, at=at,
              ordinal=len(edge_envelopes) + ordinal)
        for ordinal, row in enumerate(syndicate.envelopes)
    ]

    return (
        *edge_envelopes,
        _facility(syndicate.facility, uri=facility_uri, mark=str(marks["public"]),
                  tenant_id=tenant_id, at=at),
        *(
            _participation(row, uri=participation_uri(row), marks=marks,
                           tenant_id=tenant_id, at=at)
            for row in syndicate.participations
        ),
        *(
            _threshold(row, uri=str(templates["threshold"]).format(threshold_id=row.threshold_id),
                       mark=str(marks["public"]), tenant_id=tenant_id, at=at)
            for row in syndicate.thresholds
        ),
        *(
            _envelope(row, uri=str(templates["envelope"]).format(envelope_id=row.envelope_id),
                      mark=str(marks["internal"]), tenant_id=tenant_id, at=at)
            for row in syndicate.envelopes
        ),
    )


def _edge(subject_uri: str, object_uri: str, *, predicate: str, tenant_id: str,
          at: datetime, ordinal: int) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id=SOURCE_GRAPH),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "subject_ref": subject_uri, "subject_uri": subject_uri,
            "participation_object_ref": object_uri,
            "threshold_object_ref": object_uri,
            "envelope_object_ref": object_uri,
            "object_uri": object_uri,
            "predicate": predicate,
        },
    )


def _facility(row: acquisition.Facility, *, uri: str, mark: str, tenant_id: str,
              at: datetime) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"facility/{row.facility_id}",
        source=SourceIdentity(system_id=SOURCE_RELATIONAL),
        ingestion_timestamp=at, observed_time=at,
        raw_payload={
            "facility_ref": uri, "entity_uri": uri,
            FACILITY: row.facility_id,
            "borrower_lei": _text(row.borrower_lei),
            "commitment_amount": _text(row.commitment_amount),
            "syndicated": str(row.syndicated).lower(),
            CLASSIFICATION: mark,
        },
    )


def _participation(row: acquisition.Participation, *, uri: str,
                   marks: Mapping[str, Any], tenant_id: str, at: datetime) -> SignalEnvelope:
    # OUR OWN position is `internal`; a filed commitment schedule is `public`.
    mark = str(marks["internal"] if row.is_own_position else marks["public"])
    system = SOURCE_RELATIONAL if row.is_own_position else SOURCE_GRAPH
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"participation/{row.participation_id}",
        source=SourceIdentity(system_id=system),
        ingestion_timestamp=at, observed_time=at,
        raw_payload={
            "participation_ref": uri, "entity_uri": uri,
            MEMBER_LEI: _text(row.member_lei),
            "member_label": _text(row.member_label),
            COMMITMENT: _text(row.commitment_usd),
            IS_OWN: str(row.is_own_position).lower(),
            "internal_rating": _text(row.internal_rating),
            "workout_posture": _text(row.workout_posture),
            "source_passage": _text(row.source_passage),
            CLASSIFICATION: mark,
        },
    )


def _threshold(row: acquisition.ConsentThreshold, *, uri: str, mark: str,
               tenant_id: str, at: datetime) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"threshold/{row.threshold_id}",
        source=SourceIdentity(system_id=SOURCE_GRAPH),
        ingestion_timestamp=at, observed_time=at,
        raw_payload={
            "threshold_ref": uri, "entity_uri": uri,
            "consent_standard": _text(row.consent_standard),
            CONSENT_PERCENT: _text(row.consent_percent),
            "amendment_type": _text(row.amendment_type),
            "source_passage": _text(row.source_passage),
            CLASSIFICATION: mark,
        },
    )


def _envelope(row: acquisition.Envelope, *, uri: str, mark: str, tenant_id: str,
              at: datetime) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"envelope/{row.envelope_id}",
        source=SourceIdentity(system_id=SOURCE_GRAPH),
        ingestion_timestamp=at, observed_time=at,
        raw_payload={
            "envelope_ref": uri, "entity_uri": uri,
            COUNTERPARTY_LEI: _text(row.counterparty_lei),
            # TWO SETS, carried separately and never merged.
            REQUEST_SCOPE: SCOPE_SEPARATOR.join(row.request_scope),
            DISCLOSE_SCOPE: SCOPE_SEPARATOR.join(row.disclose_scope),
            "envelope_version": _text(row.envelope_version),
            "valid_from": _text(row.valid_from),
            CLASSIFICATION: mark,
        },
    )


def assess(context: AssessmentContext) -> DebtAssessment:
    """`D_c` over the view the OPERATORS produced.

    Completeness is the share of admitted participations carrying a commitment
    figure. **The federated child's presence or absence does NOT enter here**:
    an omitted optional child is priced by its declared `absence_treatment`
    (`ccf_config.yaml`), and a REFUSED one refuses the composite outright
    (`Q3.2`, `CLD-G07`) — neither is a debt factor this scorer invents.
    """
    assert context.profile is not None
    participations = [
        record for record in context.view.entities
        if MEMBER_LEI in record.claim.attributes
    ]
    priced = sum(
        1 for record in participations if record.claim.attributes.get(COMMITMENT)
    )
    completeness = (
        Decimal(priced) / Decimal(len(participations)) if participations else Decimal(0)
    )
    return assess_debt(
        DebtFactors(
            freshness=Decimal(1),
            completeness=completeness,
            semantic_consistency=Decimal(1),
        ),
        profile=context.profile,
    )


# ===========================================================================
# BEGIN build_children SEAM — `CLD-F-04`, AMENDED 2026-10-11 (SDK round 2, G4-F-08)
#
# Until 2026-10-11 this block rebuilt the whole consumer chain by hand — parsed
# an agent and a skill from `artifacts/consumer-chain.yaml`, registered them and
# the two pins, and requested the grant through the ledger — because
# `build_children=` was refused beside a declared chain. D-IMPL-353 then refused
# those hand registrations (`CapabilityBypassError`), so the composite could not
# open at all, even with federation off.
#
# Now the chain is DECLARED in `ccf_config.yaml` (`skills:`, `agent:`,
# `grants:`), derived, registered and granted BY THE SDK's composition, and
# handed to the factory as `ConsumerContext.derived_children`. What remains here
# is only what is this deployment's own: whether THIS request asks the optional
# child (`include_federated`) and the envelope containment check before any
# dispatch. Nothing below writes the Control Plane.
# ===========================================================================


class FederatedChildren:
    """Resolve the federated child — or honestly resolve none of it.

    Conforms to
    :class:`~ccf.products.composite.RequestAwareChildResolverProtocol` by
    declaring :meth:`resolve_for`, so the composite hands it the EFFECTIVE
    request: defaults applied, policy narrowed. That matters here, because
    `include_federated`'s declared default (`false`) has to be the value this
    seam reads, not the caller's silence.

    Two decisions, both before any producer is called:

    1. **`include_federated` is false** — no child is asked for. Returning no
       outcome for the requirement is the honest "nothing was ever invoked",
       and the composite takes the requirement's declared `absence_treatment`
       (`optional-absent`). It is NOT a refusal: nothing was refused.
    2. **A named counterparty's envelope does not admit this class** — the ask
       is REFUSED BY NAME, and the refusal happens here, before dispatch, so
       no peer is called at all (`Q1`(b), `CLD-G10`).
    """

    def __init__(self) -> None:
        self._sources: Mapping[str, Mapping[str, str]] | None = None
        self._resolver: QuestionBoundChildResolver | None = None
        self._dispatches = 0

    # -- the factory `open_product(build_children=)` calls at open ----------
    def factory(self, context: ConsumerContext) -> "FederatedChildren":
        """Compose over the chain the SDK derived from this deployment's declarations.

        The agent, the skill, the regime pins and the grant are the SDK's
        composition-time registrations (G4-F-08; ruling 4, Dave 2026-10-11);
        this seam only wraps the derived resolver.
        """
        if context.derived_children is None:
            raise ValueError(
                "the SDK handed no derived chain: declare `skills:`, `agent:` and"
                " `grants:` in ccf_config.yaml and open with `questions=`"
            )
        self._resolver = context.derived_children
        return self

    def bind(self, sources: Mapping[str, Mapping[str, str]]) -> None:
        """Bind the source settings the road resolved, once, at open.

        **The "later seam" this anticipated is now here** (`CLD-F-06`, Option
        1, 2026-09-23). The binding was retained when the envelope check moved
        OUT to the acquisition seam, on the reasoning that a seam needing the
        sources would want one place to find them. `D-IMPL-347` A2 let the
        check move back, and it reads them from here — so the second read
        costs no environment resolution at all, only the queries themselves.

        It is the opened product's `sources` and nothing else: the settings the
        road resolved once at open, never re-resolved per question.
        """
        self._sources = sources

    # -- the question this deployment asks the peer ------------------------
    def question(
        self, requirement: ChildRequirement, request: ProductRequest
    ) -> ChildQuestion:
        effective = request.parameters
        return ChildQuestion(
            subject=str(effective[FACILITY]),
            # The composite's OWN intent, carried through to the child — a
            # top-level request field, not an argument (`D-IMPL-264` D-01).
            intent=request.intent,
            freshness="standard",
            parameters={
                FACILITY: str(effective[FACILITY]),
                "counterparty": self._counterparties(effective)[0],
            },
        )

    @staticmethod
    def _counterparties(effective: Mapping[str, Any]) -> tuple[str, ...]:
        named = effective.get(COUNTERPARTIES) or ()
        return tuple(str(entry) for entry in named)

    @property
    def dispatches(self) -> int:
        """How many times a producer was actually called. `CLD-G10` reads this."""
        return self._dispatches

    # -- the seam itself ---------------------------------------------------
    def resolve_for(
        self, *, requirements: Sequence[ChildRequirement], request: ProductRequest,
        asked_at: datetime, admitted_at: datetime, composition_invocation: str,
        consumer_lineage: Any,
    ) -> Mapping[str, object]:
        effective = request.parameters
        if not _as_bool(effective.get(INCLUDE_FEDERATED), default=False):
            # Nothing was ever invoked. The declared absence treatment prices
            # it; no refusal is minted, because nothing refused.
            return {}
        # ENVELOPE CONTAINMENT, AT THE SEAM THAT OWNS THE DISPATCH DECISION
        # (`CLD-F-06`, Option 1). Before `D-IMPL-347` A2 a refusal raised here
        # escaped as an exception, so the check lived in `acquire`. It runs
        # here now, and it runs BEFORE `self._dispatches` moves — `CLD-G10`'s
        # evidence is that no peer is called when this refuses.
        #
        # THE SECOND READ, and why it is narrow. The seam receives no source
        # handles, so it resolves its own from the deployment's environment
        # document and reads the ENVELOPE ROWS ONLY — not the facility, the
        # participations, the thresholds or the watermark. Four source calls,
        # never a second acquisition: two answers to one question is what this
        # must not become. The friction is `CLD-F-11`.
        assert self._sources is not None  # `bind` ran at open
        refuse_outside_envelope(
            acquisition.envelopes_in_force(
                relational=self._sources[SOURCE_RELATIONAL],
                graph=self._sources[SOURCE_GRAPH],
            ),
            request=request,
        )
        assert self._resolver is not None  # `factory` ran at open
        self._dispatches += 1
        return self._resolver.resolve_for(
            requirements=requirements, request=request, asked_at=asked_at,
            admitted_at=admitted_at, composition_invocation=composition_invocation,
            consumer_lineage=consumer_lineage,
        )


# ===========================================================================
# END build_children SEAM — `CLD-F-04` (amended 2026-10-11)
# ===========================================================================
