"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. This file names all of it and makes no fabric call the spine does not.
Delete ``ccf_config.yaml`` and nothing here has anything left to interpret,
which is the No-Hardcoding Rule (CLAUDE.md §6.4) being structural rather than
aspirational.

**Its boundaries are ruled** (`D-IMPL-315`, `D-IMPL-343`): vocabulary, source
access and admission. No boot, no effective-request derivation, no binder, no
gates, no replay record, no serve — those are the paved road's, and
``produce.py`` hands it the three verbs this file authors: :func:`acquire`,
:func:`assess` and the product's own gate.

## Per-attribute temporal validity is fabric state here, not a payload

The frozen specimen ingested ONE envelope carrying the whole spread and dated it
from the payload's freshest filing; the per-figure filing dates lived inside an
object the graph never held, so Π and the debt reading both closed over a
scenario carried in from the side. Here :func:`envelopes` emits one envelope per
obligor, per period, per line and per cohort statistic, each dated
``observed_time`` from THE FILING THAT ASSERTED IT. The view the policy
operator produces is therefore the spread itself: Π reads nothing around it
(``projection.py``), the debt reading dates each column from the graph
(:func:`debt`), and a principal who may not see the obligor sees no period, no
line and no cohort either — the suppression is one grant over four classes,
not a filter Π has to remember.

## What is deliberately preserved from the specimen, unmoved

The λ_c values, the D_c bands, the 30-day window, the eight-period default, the
as-reported default and the peer basis are the specimen's demonstration values
(`CP14-F-22` §8). The debt reading is the specimen's method — one observation
per period typed by its signal class, completeness as the evaluable fraction of
declared lines, ``S = 1`` as a structural property of a one-store product — so
that what moved between the two trees is the SDK path and not the answer.

## What moved OUT of this file on the paved road (`D-IMPL-343`), and where to

Deleted, not relocated (`D-IMPL-289`): the config re-parse (the booted
artifacts are the one read), the TTL re-parse (the ``ttl:`` section), the
per-run substrate mint (the facade mints per question from
``ccf_environment.yaml``), the request constructor's schema reads
(``opened.question``), the perspective re-parse (the booted
``default_perspective``), the effective-request re-derivation (the resolver's
own, handed to :func:`acquire` through the declared seam), the ingest loop (the
facade's, with the tenant and instant refused by name), and the scenario object
that restated five section keys (``fabric.keys``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import acquisition
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtAssessment, DebtFactors
from ccf.halflife.debt import FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

#: The request parameters this deployment reads by name — the contract's own.
PERIODS = "periods"
BASIS = "basis"
INCLUDE_PEERS = "include_peers"
PEER_BASIS = "peer_basis"
DEBT_TOLERANCE = "debt_tolerance"
JURISDICTIONS = "jurisdictions"

#: The one source store, by the name ``ccf_environment.yaml`` declares it under.
SOURCE = "financial_spread"

#: The four entity classes `ccf_config.yaml`'s resolution section mints.
CLASS_OBLIGOR = "obligor"
CLASS_PERIOD = "spread_period"
CLASS_LINE = "spread_line"
CLASS_COHORT = "peer_cohort"

#: The attribute the policy envelope is keyed on, carried by every class.
JURISDICTION = "obligor_jurisdiction"

#: The payload member the product's own gate reads its anchor from.
ANCHOR_MEMBER = "latest_filed_in_payload"

#: How a multi-valued `inputs` list is carried through a `Mapping[str, str]`.
#: Declared once here and read back once in `projection.py`.
INPUTS_SEPARATOR = "|"

#: The identifier the fabric records as this product's source system.
SOURCE_SYSTEM = "financial_fact"

#: The plan identity every question's Π is built under, per subject. Inside
#: the served content address, so it is this deployment's vocabulary and not
#: the spine's.
PLAN_ID_PREFIX = "cp-03-canonical.obligor-financial-spread"


def plan_id(subject: str) -> str:
    """The plan identity for one obligor's spread."""
    return f"{PLAN_ID_PREFIX}/{subject}"


def grant_parameters(principal_id: str, *, settings: Mapping[str, str]) -> dict[str, Any]:
    """Ask as another principal: that principal's grant, STATED on the request.

    The principal's jurisdiction grant is expanded against the estate and
    stated as the request's ``jurisdictions``, so the value that reaches the
    policy operator is request state the effective request records — never a
    value written over a resolved artifact. The demonstration's way of asking
    as somebody else; a caller may also pass ``jurisdictions`` directly.
    """
    return {JURISDICTIONS: list(acquisition.grant_for(principal_id, settings=settings))}


# ---------------------------------------------------------------------------
# The three verbs the paved road binds: acquire, assess, gate.
# ---------------------------------------------------------------------------


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Read the source store at the EFFECTIVE parameters; hand back dated claims.

    The parameters are the values governance resolved — the class defaults
    where the caller omitted one, the caller's values where they are in
    bounds — handed here by the resolver through the declared seam
    (`D-IMPL-343` R-4). Debt is scored over the view the OPERATORS produced;
    reading the estate at the resolved values makes L3, the operator view and
    the payload the same set (`CP04C-F-02`). A refused request never reaches
    this function, by the seam's ordering rather than by a check here.

    A read that resolves nothing hands back no envelope: nothing is written,
    and the governed path refuses on the product's own gate, with a record.
    """
    effective = context.request.parameters
    read = acquisition.acquire(
        anchor_lei=context.request.subject,
        periods=int(effective[PERIODS]),
        basis=str(effective[BASIS]),
        include_peers=bool(effective[INCLUDE_PEERS]),
        peer_basis=str(effective[PEER_BASIS]),
        settings=context.sources[SOURCE],
    )
    return envelopes(read, tenant_id=context.tenant_id, at=context.instant)


def assess(context: AssessmentContext) -> DebtAssessment:
    """`D_c` over what this question assembled, as of the DECISION instant.

    The λ_c table and the D_c bands are the BOOTED artifacts the paved road
    hands here — the exact documents the pins record, never a second parse —
    and the instant is the resolver's own decision instant, which for this
    class (declaring none apart) is the asked instant.
    """
    assert context.half_life is not None and context.profile is not None
    return debt(
        context.view,
        now=context.decided_at,
        half_life=context.half_life,
        profile=context.profile,
    )


# ---------------------------------------------------------------------------
# From a read to fabric state — one envelope per dated claim.
# ---------------------------------------------------------------------------


def _instant(value: date) -> datetime:
    """A source DATE as a UTC instant at midnight.

    Widening a date to an instant is a lossless statement about when the fact
    is known to have held BY. Narrowing the other way would invent a time.
    """
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _amount(value: Decimal | None) -> str:
    """One figure as text, or the word — never `0` for absent."""
    return acquisition.NOT_EVALUABLE if value is None else str(value)


def _envelope(
    *, tenant_id: str, match_key: str, ref: str, at: datetime, observed: datetime,
    attributes: Mapping[str, Any],
) -> SignalEnvelope:
    """One dated claim under the fabric's own vocabulary."""
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=ref,
        source=SourceIdentity(system_id=SOURCE_SYSTEM),
        # The request instant, so the as-of boundary the caller asked at is at
        # or after the claim's `observed_at` — and what the paved road's
        # boundary refuses by name if it is anything else (`D-IMPL-343`).
        ingestion_timestamp=at,
        # THE FILING THAT ASSERTED THIS CLAIM — never a wall clock. A figure
        # filed 2026-08-10 is the same age whichever instant it was asked at.
        observed_time=observed,
        raw_payload={
            match_key: ref,
            "entity_ref": ref,
            **{key: "" if value is None else str(value) for key, value in attributes.items()},
        },
    )


def envelopes(
    read: acquisition.SpreadRead, *, tenant_id: str, at: datetime
) -> tuple[SignalEnvelope, ...]:
    """The whole spread as dated claims: obligor, periods, lines, cohort."""
    resolved = read.resolved
    if resolved is None:
        return ()
    fiscal_annual = str(acquisition.vocabulary()["fiscal_annual"])
    anchor = read.latest_filed_in_payload
    common = {"lei": resolved.lei, JURISDICTION: resolved.jurisdiction}
    out: list[SignalEnvelope] = [
        _envelope(
            tenant_id=tenant_id, match_key="obligor_ref", ref=f"obligor:{resolved.lei}", at=at,
            observed=_instant(anchor) if anchor is not None else at,
            attributes={
                **common,
                "cik": resolved.cik,
                "obligor_legal_name": resolved.legal_name,
                "fiscal_year_end_month": resolved.fiscal_year_end_month,
                "latest_filed_date": resolved.latest_filed.isoformat() if resolved.latest_filed else acquisition.NOT_EVALUABLE,
                "formally_restated": str(resolved.has_non_reliance_filing).lower(),
                "basis_applied": read.basis,
                "spread_periods": len(read.periods),
                "peer_cohort_basis": read.cohort_basis,
                "peer_sic": resolved.sic or acquisition.NOT_EVALUABLE,
                "peer_cohort_size": read.cohort_size,
            },
        )
    ]
    for period in read.periods:
        period_observed = _instant(period.latest_filed) if period.latest_filed is not None else at
        key = f"{resolved.lei}:{period.period_end.isoformat()}:{period.fiscal_period}"
        out.append(
            _envelope(
                tenant_id=tenant_id, match_key="period_ref", ref=f"period:{key}", at=at,
                observed=period_observed,
                attributes={
                    **common,
                    "period_end": period.period_end.isoformat(),
                    "fiscal_period": period.fiscal_period,
                    # WHICH λ_c THIS COLUMN DECAYS AGAINST. Two columns of one
                    # payload answer differently here.
                    "signal_class": period.signal_class(fiscal_annual=fiscal_annual),
                    "latest_filed": period.latest_filed.isoformat() if period.latest_filed else acquisition.NOT_EVALUABLE,
                },
            )
        )
        for name, line in sorted(period.lines.items()):
            cell = line.cell
            observed = _instant(cell.filed_date) if cell is not None else period_observed
            attributes: dict[str, Any] = {
                **common,
                "period_end": period.period_end.isoformat(),
                "fiscal_period": period.fiscal_period,
                "line": name,
                "derived": str(line.derived).lower(),
                "value": _amount(line.value),
                "unit": line.unit if line.unit is not None else acquisition.NOT_EVALUABLE,
                "kind": (
                    (acquisition.KIND_INSTANT if cell.is_instant else acquisition.KIND_DURATION)
                    if cell is not None else line.declared_kind
                ),
                "period_start": cell.period_start.isoformat() if cell is not None and cell.period_start else "",
                # WHICH FILING ASSERTED THIS FIGURE — per attribute, not per
                # product. A column stitched from two filings reports two.
                "filed_date": cell.filed_date.isoformat() if cell is not None else "",
                "accession": cell.accession if cell is not None else "",
                "form": cell.form if cell is not None else "",
                "basis_applied": read.basis if cell is not None else "",
                "restated": str(cell.restated).lower() if cell is not None else "",
                "restatement_class": (cell.restatement_class or acquisition.NOT_EVALUABLE) if cell is not None else "",
                "kind_conflict": str(line.kind_conflict).lower(),
                "inputs": INPUTS_SEPARATOR.join(line.inputs),
                "reason": (
                    "no declared tag for this line was filed in this period"
                    if cell is None and not line.derived else ""
                ),
            }
            out.append(
                _envelope(
                    tenant_id=tenant_id, match_key="line_ref", ref=f"line:{key}:{name}", at=at,
                    observed=observed, attributes=attributes,
                )
            )
    for statistic in read.cohort:
        out.append(
            _envelope(
                tenant_id=tenant_id, match_key="peer_ref",
                ref=f"peers:{resolved.lei}:{statistic.period_end.isoformat()}:{statistic.tag}", at=at,
                observed=_instant(statistic.latest_filed) if statistic.latest_filed is not None else at,
                attributes={
                    **common,
                    "sic": resolved.sic or "",
                    "period_end": statistic.period_end.isoformat(),
                    "tag": statistic.tag,
                    "peers_reporting": statistic.peers_reporting,
                    "median": str(statistic.median),
                },
            )
        )
    return tuple(out)


# ---------------------------------------------------------------------------
# D_c over the view the OPERATORS produced — the specimen's method, off the graph.
# ---------------------------------------------------------------------------


def debt(
    view: GraphView, *, now: datetime, half_life: HalfLifeTable, profile: DebtProfile
) -> DebtAssessment:
    """`D_c` over what this question assembled — whitepaper §7.7, spec §E.2.

    **One observation per spread period, TYPED BY THAT PERIOD'S CLASS and dated
    from the graph.** An annual column decays against `annual_facts` and a
    quarterly column against `quarterly_facts`, each from its OWN filing —
    ``valid_from`` on the period entity, the instant the declared
    ``decay_basis: valid-from`` rows age from — so one payload carries two decay
    rates at once and a four-year-old annual is four years stale even beside a
    quarter filed last week.

    **Completeness is the evaluable fraction of declared lines** in the view:
    every `NOT_EVALUABLE` line is a real shortfall and contributes its full
    weight; none is filled with a default.

    **`S` is 1 and it is a MEASURED PROPERTY of this estate, not a magic
    constant.** This product reads ONE store: `financial_fact` is the only
    authority for a figure, and `peer_fact` describes different companies.
    Nothing here could disagree, so the signal cannot fire.

    **An empty view is the maximum, not a score for nothing.** The scorer
    refuses an empty sequence by design; the product's own gate refuses the
    serve before this number could be read as a debt reading.
    """
    periods = [r for r in view.entities if r.claim.entity_class == CLASS_PERIOD]
    lines = [r for r in view.entities if r.claim.entity_class == CLASS_LINE]
    observations = tuple(
        Observation(
            observation_type=record.claim.attributes["signal_class"],
            # When the FABRIC learned the claim — the request instant.
            observed_at=record.claim.observed_at,
            # When the SOURCE asserted it — the filing. The λ_c rows declare
            # `decay_basis: valid-from`, so THIS is the instant a column ages
            # from, and a period carrying none would be refused by name rather
            # than scored fresh (`D-IMPL-331`).
            valid_from=record.claim.valid_from,
            subject=record.claim.entity_uri,
        )
        for record in periods
    )
    if not observations:
        return assess_debt(
            DebtFactors(freshness=Decimal(0), completeness=Decimal(0), semantic_consistency=Decimal(1)),
            profile=profile,
        )
    evaluable = sum(1 for r in lines if r.claim.attributes.get("value") != acquisition.NOT_EVALUABLE)
    completeness = Decimal(evaluable) / Decimal(len(lines)) if lines else Decimal(0)
    freshness = FreshnessScorer(table=half_life, risk_sensitivity=profile.risk_sensitivity).score(
        observations, now=now
    )
    return assess_debt(
        DebtFactors(freshness=freshness, completeness=completeness, semantic_consistency=Decimal(1)),
        profile=profile,
    )


# ---------------------------------------------------------------------------
# The product's OWN invariant — the predicate behind `declared_product_gate`.
# ---------------------------------------------------------------------------

#: One text for an absent obligor and a suppressed one. §B.2's suppression
#: rule: no count, no marker, and NO WAY TO TELL THE TWO APART.
NO_OBLIGOR = (
    "no obligor in the admitted view: the anchor resolved to nothing this"
    " principal may see"
)


def freshness_window_gate(*, candidate: Any, evidence: object = None) -> str | None:
    """The predicate for `cp-03-canonical.spread-freshness-window`.

    Two refusals in one governed verdict, both returned as a detail and stamped
    with the declared gate identity by the resolver:

    * **no obligor** — the admitted view held none. The anchor resolved to no
      entity, to one with no facts, or to one the policy envelope suppressed;
      the text is the same for all three by construction.
    * **outside the window** — the freshest filing the payload rests on plus
      the declared window is not after the asked instant. This is the SERVING
      half of `ttl_anchor: from_entity_freshness`, held here because the
      governed path anchors the contract's `expires_at` at the decision
      instant regardless of the declaration (`CP03C-F-01`). Filers file
      quarterly, so this refusal clears as filings land.

    **The window is read off the served candidate and nowhere else**
    (`D-IMPL-343`): ``expires_at`` is the decision instant plus the declared
    ``product_ttl_seconds`` and, for a class declaring no distinct decision
    instant, the decision instant IS ``temporal_boundary`` — so their
    difference is the one declared window, and this predicate restates no
    number. The gate exists only because `expires_at` is decision-anchored
    (`CP03C-F-01`, `D-IMPL-341`); when the SDK honors the declared anchor,
    this serving half is deleted, not moved.
    """
    payload = candidate.payload
    if payload.get("obligor") is None:
        return NO_OBLIGOR
    anchor = payload.get(ANCHOR_MEMBER)
    if anchor is None or anchor == acquisition.NOT_EVALUABLE:
        return NO_OBLIGOR
    window = candidate.expires_at - candidate.temporal_boundary
    expires = _instant(date.fromisoformat(str(anchor))) + window
    asked_at = candidate.temporal_boundary
    if not asked_at < expires:
        return (
            f"outside the declared window: the freshest filing in the payload"
            f" ({anchor}) plus {window.days} days is {expires.isoformat()}, which"
            f" is not after the asked instant {asked_at.isoformat()}; under its"
            " declared anchor (from_entity_freshness) this spread has expired and"
            " clears when the obligor files again"
        )
    return None


#: Re-exported for `run.py` and the tests, which state a caller's own grant.
Grant = Sequence[str]
