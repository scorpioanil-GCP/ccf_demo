"""The co-lender's own vocabulary and its three verbs: acquire, project's plan id, assess.

[ADAPT] everything here — every name is this product's. [MECHANISM] the two
context types imported from the SDK; nothing else is SDK code.

**Thin edges first, attributed nodes last.** :func:`envelopes` yields the
``positionOf`` edge before either endpoint's attributed claim, because the last
claim at a URI wins and does not merge (`D-IMPL-316`): a thin edge claim
arriving after an attributed one would strip the node it just resolved.

**The attestation control is TWO independent mechanisms, and neither satisfies
the other.**

1. :func:`acquire` raises :class:`~ccf.products.refusal.GovernedRefusalRaised`
   when no attestation record stands behind the declaration. That is the
   control that fires: it produces a governed refusal, as data, with a replay
   reference and the typed ``error_code`` an examiner reads — the cp-21
   pattern (`LEX`'s ``UnknownBasis`` / ``UnknownRegime``).
2. The policy operator declared in ``ccf_config.yaml`` removes an
   ``unattested`` entity from the view if one ever reaches assembly.

The second is a STRUCTURAL BACKSTOP, not decoration, and `CLD-G06`'s sabotage
proves it: with the raise in (1) deleted, the product still cannot serve the
unattested position — the policy operator empties the view and the product
serves a computed-empty answer instead. **A policy-emptied view is SERVED, not
refused** (`D-IMPL-242` amendment 1, and cp-17's `Q8`), which is exactly why
(1) exists and why (2) alone would be insufficient. Measured 2026-09-22: the
first candidate had only (2) and served an empty product where Dave's `Q3.2`
requires a refusal.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

import acquisition
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, assess_debt
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    SubjectUnavailableRefusal,
)
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

#: The typed code the attestation refusal carries. Retained in the record so an
#: examiner can tell an unattested position from an absent one — §D of
#: `docs/EXAMPLE-EVALUATION-CRITERIA.md` requires the *why*, not only the that.
UNATTESTED_CODE = "unattested-position"

#: The request-contract argument names — the contract's, restated nowhere.
FACILITY = "facility_id"
COUNTERPARTY = "counterparty"

#: The environment document's names for the two source legs.
SOURCE_POSITIONS = "peer_positions"
SOURCE_COUNTERPARTIES = "peer_counterparties"

#: Attribute keys the projection reads back off the view. Spelled once.
CLASSIFICATION = "classification"
PRECISION = "precision"
SHARE = "share_usd"
BAND_LOW = "band_low"
BAND_HIGH = "band_high"
DECLARED_TTL = "declared_ttl_seconds"
DECLARED_LATENCY = "declared_latency_ms"
POSITION_AS_OF = "position_as_of"


def plan_id(facility_id: str, counterparty_lei: str) -> str:
    return f"cp-20-peer.co-lender-position/{facility_id}/{counterparty_lei}"


def classification(answer: acquisition.PeerAnswer) -> str:
    """``attested`` or ``unattested`` — the one value the policy operator filters on.

    Read from the vocabulary document rather than spelled here, so the two
    literals have one home (the policy operator's `permitted_classifications`
    names the same strings, and `CLD-G06`'s sabotage is what catches a drift).
    """
    names = acquisition.vocabulary()["classifications"]
    return str(names["attested"] if answer.position.attested else names["unattested"])


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Read both peer stores at the EFFECTIVE request; hand back dated claims.

    Raises:
        GovernedRefusalRaised: no attestation record stands behind this
            position's declaration. The peer will not assert a claim it cannot
            stand behind, so the answer is a governed refusal rather than a
            served position carrying a caveat — and **never** a served position
            discounted by Context Debt (`Q3.2`, Dave, 2026-09-22).
    """
    effective = context.request.parameters
    answer = acquisition.acquire(
        facility_id=str(effective[FACILITY]),
        counterparty_lei=str(effective[COUNTERPARTY]),
        positions=context.sources[SOURCE_POSITIONS],
        counterparties=context.sources[SOURCE_COUNTERPARTIES],
    )
    if not answer.position.attested:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="unauthorized",
                detail=(
                    f"the co-lender publishes no attestation record behind its"
                    f" position {answer.position.position_id!r} in facility"
                    f" {answer.position.facility_id!r}; an unverifiable remote"
                    " claim is not disclosed under this envelope"
                ),
                error_code=UNATTESTED_CODE,
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )
    return envelopes(answer, tenant_id=context.tenant_id, at=context.instant)


def envelopes(
    answer: acquisition.PeerAnswer, *, tenant_id: str, at: datetime
) -> tuple[SignalEnvelope, ...]:
    """The peer's answer as dated claims — EDGE FIRST, NODES LAST."""
    vocab = acquisition.vocabulary()
    templates = vocab["uri_templates"]
    position_uri = str(templates["position"]).format(
        position_id=answer.position.position_id
    )
    counterparty_uri = str(templates["counterparty"]).format(
        lei=answer.counterparty.lei
    )
    mark = classification(answer)
    return (
        _edge_envelope(
            position_uri,
            counterparty_uri,
            predicate=str(vocab["predicates"]["position_of"]),
            tenant_id=tenant_id,
            at=at,
        ),
        _position_envelope(
            answer, uri=position_uri, mark=mark, tenant_id=tenant_id, at=at
        ),
        _counterparty_envelope(
            answer, uri=counterparty_uri, mark=mark, tenant_id=tenant_id, at=at
        ),
    )


def _text(value: object) -> str:
    """A source value as a claim attribute. ``None`` becomes the empty string.

    An absent figure is served as absent — never as ``0``, and never as a
    bound standing in for a number the peer did not disclose.
    """
    return "" if value is None else str(value)


def _position_envelope(
    answer: acquisition.PeerAnswer, *, uri: str, mark: str, tenant_id: str, at: datetime
) -> SignalEnvelope:
    position = answer.position
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"position/{position.position_id}",
        source=SourceIdentity(system_id=SOURCE_POSITIONS),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "position_ref": uri,
            "entity_uri": uri,
            COUNTERPARTY: position.counterparty_lei,
            FACILITY: position.facility_id,
            # The precision travels with the POSITION as well as the member,
            # so a reader of either entity can tell what the figure beside it
            # is allowed to be.
            PRECISION: answer.counterparty.precision,
            SHARE: _text(position.share_usd),
            BAND_LOW: _text(position.band_low),
            BAND_HIGH: _text(position.band_high),
            "internal_rating": _text(position.internal_rating),
            "workout_posture": _text(position.workout_posture),
            DECLARED_TTL: _text(position.declared_ttl_seconds),
            DECLARED_LATENCY: _text(position.declared_latency_ms),
            CLASSIFICATION: mark,
            POSITION_AS_OF: position.as_of,
            "provenance": _text(position.provenance),
        },
    )


def _counterparty_envelope(
    answer: acquisition.PeerAnswer, *, uri: str, mark: str, tenant_id: str, at: datetime
) -> SignalEnvelope:
    member = answer.counterparty
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"counterparty/{member.lei}",
        source=SourceIdentity(system_id=SOURCE_COUNTERPARTIES),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "counterparty_ref": uri,
            "entity_uri": uri,
            "lei": member.lei,
            "label": _text(member.label),
            PRECISION: member.precision,
            # INHERITED from the position, deliberately — see the module
            # docstring and `ccf_config.yaml`'s policy operator.
            CLASSIFICATION: mark,
            "provenance": _text(member.provenance),
        },
    )


def _edge_envelope(
    subject_uri: str, object_uri: str, *, predicate: str, tenant_id: str, at: datetime
) -> SignalEnvelope:
    """The join between the two peer legs, carrying NO attributes."""
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{predicate}",
        source=SourceIdentity(system_id=SOURCE_POSITIONS),
        ingestion_timestamp=at,
        observed_time=at,
        raw_payload={
            "subject_ref": subject_uri,
            "subject_uri": subject_uri,
            "object_ref": object_uri,
            "object_uri": object_uri,
            "predicate": predicate,
        },
    )


def assess(context: AssessmentContext) -> DebtAssessment:
    """`D_c` over the view the OPERATORS produced.

    Completeness is the share of admitted positions carrying a published
    declaration — a position the peer never published terms for is genuinely
    less complete. **Attestation is NOT a factor here** (`Q3.2`): an unattested
    position never reaches this scorer, because the policy operator removed it
    and the product refused.
    """
    assert context.profile is not None
    positions = [
        record
        for record in context.view.entities
        if FACILITY in record.claim.attributes
    ]
    declared = sum(
        1 for record in positions if record.claim.attributes.get(DECLARED_TTL)
    )
    completeness = (
        Decimal(declared) / Decimal(len(positions)) if positions else Decimal(0)
    )
    return assess_debt(
        DebtFactors(
            freshness=Decimal(1),
            completeness=completeness,
            semantic_consistency=Decimal(1),
        ),
        profile=context.profile,
    )


def sources_declared() -> Mapping[str, str]:
    """The two legs' declared names, for a reader of this module alone."""
    return {"relational": SOURCE_POSITIONS, "graph": SOURCE_COUNTERPARTIES}
