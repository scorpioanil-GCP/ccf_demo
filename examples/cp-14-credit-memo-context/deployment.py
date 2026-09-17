"""The deployment's own vocabulary and its four verbs: acquire, assess, question, name.

[ADAPT] everything here — every name is this product's. [MECHANISM] the four
context and contract types imported from the SDK; nothing else is SDK code.

**The whole consumer, in one sentence.** The parent declares what it requires
(`ccf_config.yaml`); this module says what each requirement is ASKED —
:func:`questions` — and reads the one leg the parent owns in this slice. The
SDK does the rest: it registers the five producers, derives the five skills and
their grants, asks each producer the mapped question, holds every answer to its
registration, admits or refuses each child, composes, and records five child
rows on every exit after acquisition (`D-IMPL-338`).

**The tolerance is mapped, never defaulted or raised.** The memo's own
`debt_tolerance` — the effective request's value, 0.25 under the v2 policy at
the CP-14 instant — reaches every child question that takes one, as decimal
text. A child that withholds at that tolerance is the honest answer and refuses
the composite on its required slot (spec §D.3 scenario 8); the 1.0 case is a
diagnostic that the producer CAN serve, never the production question.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import acquisition
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

# --- names ------------------------------------------------------------------------

#: The parent's request parameters — the request contract's, restated nowhere.
MEMO_TYPE = "memo_type"
AS_OF = "as_of"
DEBT_TOLERANCE = "debt_tolerance"
FACILITY_ID = "facility_id"

#: The environment document's source name for the roster store.
SOURCE = "roster"
SOURCE_SYSTEM = "ccf_v2.legal_entity"

#: The obligor node's class and vocabulary in the fabric.
CLASS_OBLIGOR = "obligor"
MATCH_KEY = "obligor_ref"

#: The five child classes, as `requires` declares them — named here so the
#: mapping branches on the class the SDK hands it and never on a position.
SPREAD = "credit-risk.spread"
FAMILY = "reference.corporate-family"
EXPOSURE = "credit-risk.exposure-rollup"
COLLATERAL = "credit-risk.collateral-coverage"
COVENANT = "credit-risk.covenant-cross-reference"

#: What each child is asked FOR — the intent each producer's class serves, and
#: the freshness the question is asked at, in the producer's own vocabulary.
#: Read off each producer's tree; the four unreachable producers' values are
#: their demonstration intents (see FINDINGS.md, CP14-F-27).
CHILD_INTENT = {
    SPREAD: "annual-review",
    FAMILY: "credit-concentration",
    EXPOSURE: "internal-appetite",
    COLLATERAL: "lgd-assessment",
    COVENANT: "compliance-test",
}
CHILD_FRESHNESS = {
    SPREAD: "filing-cadence",
    FAMILY: "as-filed",
    EXPOSURE: "as-booked",
    COLLATERAL: "as-filed",
    COVENANT: "as-filed",
}

NOT_EVALUABLE = "NOT_EVALUABLE"


def plan_id(subject: str) -> str:
    return f"cp-14/credit-memo-context/{subject}"


# --- the parent's own leg -------------------------------------------------------


def _instant(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Resolve the obligor on the memo roster; hand back its identity as one dated claim.

    Handed the EFFECTIVE request by the resolver's seam (`D-IMPL-343` R-4). A
    subject not on the roster hands back nothing: nothing is written, and the
    governed path refuses on the parent's own empty view, with a record.
    """
    resolved = acquisition.resolve(context.request.subject, settings=context.sources[SOURCE])
    if resolved is None:
        return ()
    ref = f"obligor:{resolved.lei}"
    return (
        SignalEnvelope(
            tenant_id=context.tenant_id,
            envelope_id=ref,
            source=SourceIdentity(system_id=SOURCE_SYSTEM),
            ingestion_timestamp=context.instant,
            # When the identity record was last taken from GLEIF — never a wall clock.
            observed_time=_instant(resolved.retrieved_at) if resolved.retrieved_at else context.instant,
            raw_payload={
                MATCH_KEY: ref,
                "entity_ref": ref,
                "lei": resolved.lei,
                "legal_name": resolved.legal_name,
                "legal_jurisdiction": resolved.legal_jurisdiction,
                "sic": resolved.sic or NOT_EVALUABLE,
                "sic_description": resolved.sic_description or NOT_EVALUABLE,
                "roster_member": "true",
            },
        ),
    )


def assess(context: AssessmentContext) -> DebtAssessment:
    """The parent's OWN F, C and S over its own leg, at the DECISION instant.

    Freshness decays the identity record's age against the declared λ_c;
    completeness is whether the roster resolved the obligor at all; consistency
    is 1 — one store, nothing to disagree. The memo's inherited debt from its
    five children is the SDK's per-factor minimum (`D-IMPL-31`), applied by
    composition and never here; the spec's own F/C/S (§E.2) land with the parent
    logic in later slices.
    """
    assert context.half_life is not None and context.profile is not None
    obligors = [r for r in context.view.entities if r.claim.entity_class == CLASS_OBLIGOR]
    if not obligors:
        return assess_debt(
            DebtFactors(freshness=Decimal(0), completeness=Decimal(0), semantic_consistency=Decimal(1)),
            profile=context.profile,
        )
    observations = tuple(
        Observation(
            observation_type=CLASS_OBLIGOR,
            observed_at=record.claim.observed_at,
            subject=record.claim.entity_uri,
        )
        for record in obligors
    )
    freshness = FreshnessScorer(
        table=context.half_life, risk_sensitivity=context.profile.risk_sensitivity
    ).score(observations, now=context.decided_at)
    return assess_debt(
        DebtFactors(freshness=freshness, completeness=Decimal(1), semantic_consistency=Decimal(1)),
        profile=context.profile,
    )


# --- the developer's ONE mapping ---------------------------------------------------


def _tolerance_text(value: Any) -> str:
    """The memo's tolerance as decimal TEXT — bit-stable in a content address."""
    return str(Decimal(str(value)))


#: The environment document's source name for the ledger leg the covenant
#: question is determined from (`CP14-F-28`).
SOURCE_GRAPH = "covenant_graph"


class MemoQuestions:
    """*Given this memo's EFFECTIVE request, what should requirement X be asked?*

    The one thing the SDK cannot know. The subject, intent, freshness and
    parameters of each child's question come from the memo's own resolved
    request; the tenant, class, lane, instant and endpoint come from elsewhere
    (the registration, the derived binding, the composite's `asked_at`) and
    are not reachable from here.

    **Bound late to the deployment's own sources.** The road hands this
    mapping the requirement and the effective request and nothing else; the
    covenant question is determined from the obligor's facility documents,
    which is a read of the roster and the ledger (`acquisition.covenant_sources`).
    `produce.product` constructs ONE instance PER OPENED PRODUCT and binds the
    resolved source settings the road already holds (`opened.sources`) before
    the first question is answered, so the settings are resolved ONCE, by the
    SDK, from the environment document — never a second time here, and never
    shared between two opened products (`CP14-F-34` records the seam).
    """

    def __init__(self) -> None:
        self._sources: Mapping[str, Mapping[str, str]] | None = None

    def bind(self, sources: Mapping[str, Mapping[str, str]]) -> None:
        self._sources = sources

    def __call__(self, requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        effective = request.parameters
        lei = request.subject
        tolerance = _tolerance_text(effective[DEBT_TOLERANCE])
        product_class = requirement.product_class
        intent = CHILD_INTENT[product_class]
        freshness = CHILD_FRESHNESS[product_class]
        if product_class == SPREAD:
            # The obligor's spread: the memo's subject IS the child's subject; the
            # memo's tolerance is the child's, unchanged.
            return ChildQuestion(subject=lei, intent=intent, freshness=freshness, parameters={DEBT_TOLERANCE: tolerance})
        if product_class == FAMILY:
            # The family walked from the obligor, entitled to its own family.
            return ChildQuestion(
                subject=lei, intent=intent, freshness=freshness,
                parameters={"lei": lei, "families": [lei], DEBT_TOLERANCE: tolerance},
            )
        if product_class == EXPOSURE:
            # Exposure rolled up across the obligor's family, at the memo's tolerance.
            return ChildQuestion(
                subject=lei, intent=intent, freshness=freshness,
                parameters={"families": [lei], DEBT_TOLERANCE: tolerance},
            )
        if product_class == COLLATERAL:
            # ONE FACILITY, named by the memo's request (`CP14-F-20`, ruled): the
            # facility is the child's subject, the obligor is its borrower scope.
            # The collateral contract takes no tolerance; none is invented.
            facility = str(effective[FACILITY_ID])
            return ChildQuestion(
                subject=facility, intent=intent, freshness=freshness,
                parameters={"facility_id": facility, "borrower_scope": [lei]},
            )
        if product_class == COVENANT:
            # THE OBLIGOR'S OWN EVIDENCE NODES (`CP14-F-28`): the anchors its
            # facility documents carry, determined from the roster and the
            # ledger and never walked here. The obligor is the child's scope;
            # the memo's tolerance is the child's, unchanged. An obligor whose
            # documents carry no anchor asks with none — and the child refuses
            # that honestly (`CXRC-G23`) rather than this mapping inventing one.
            if self._sources is None:
                raise RuntimeError("the memo's question mapping was asked before its sources were bound")
            sources = acquisition.covenant_sources(
                lei, roster=self._sources[SOURCE], graph=self._sources[SOURCE_GRAPH]
            )
            return ChildQuestion(
                subject=lei, intent=intent, freshness=freshness,
                parameters={"covenant_sources": sources, DEBT_TOLERANCE: tolerance},
            )
        raise ValueError(f"no question mapping for required class {product_class!r}")


