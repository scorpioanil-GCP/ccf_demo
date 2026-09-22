"""The deployment's half of `risk.large-exposure`.

[ADAPT] the vocabulary here to your own product. The three verbs the paved road
binds (`acquire`, `assess`, and the declared gate `large_exposure_gate`) live
here.

FOUR RULINGS ARE LOAD-BEARING IN THIS MODULE (`CP-SPEC-021` §F.4, 2026-09-21):

- **`Q1` — ONE PRODUCT, NO CHILDREN.** CP-21 is a single-class producer. The
  six prerequisites the source specification names are re-acquired here rather
  than composed as child trees, and **composition is a named coverage gap this
  rung does not close**. Nothing below builds a child resolver.
- **`Q2` — NORMALIZE AT THE ACQUISITION BOUNDARY, WITH A DECLARED FACTOR.**
  The FFIEC capital figure is denominated in thousands. `acquisition` scales it
  using the factor declared in `artifacts/source-vocabulary.yaml` — **never a
  literal in code** — the source table is not rewritten, and BOTH figures
  travel with their units. The gate refuses a payload that loses either.
- **The regime is an effective-dated artifact** selected at the determination
  instant, and a limit is a **percentage of capital OR an absolute amount**.
  Regulation O's $500,000 exercises the second shape.
- **The freshness asymmetry is disclosed, never fused.** Four prohibitions,
  enforced by the gate: a ratio without its denominator's date, capital
  presented as intraday, either clock aged into the other, and any single fused
  freshness key.

AND, unchanged from rung 23: population debt is the SDK's own combinator,
`ccf.halflife.debt.compose_debt_factors`, applied to the MEMBERS' factors under
the `D-IMPL-104` worst-factor rule — per-factor minimum strength across the
population. Never `max(member D_c)`, never a second debt law.

A PROPOSAL IS AN ASSUMPTION. It is bound, echoed onto the group claim, and
consumed by the arithmetic — and it never reaches `assess`. Two proposals over
one instant and group therefore produce identical `D_c` (`LEX-G19`).

AND THE BOUNDARY (`PEW-G18`, preserved): rung 23 reads no `limit_definition`,
no `bank_capital` and no connection basis. Those are THIS product's inputs.
Rung 23's concentration view uses its own declared threshold and nothing else;
nothing here reaches back into it.
"""
from __future__ import annotations

import json as _json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import acquisition
import projection
from ccf.halflife.assessment import DebtAssessment
from ccf.halflife.debt import DebtFactors, compose_debt_factors
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.refusal import RESOLVED_BY_THE_RESOLVER, GovernedRefusalRaised, SubjectUnavailableRefusal
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

AS_OF = "as_of"
MEMBERS = "members"
REGIME = "regime"
CONNECTION_BASIS = "connection_basis"
PROPOSAL = "proposal"
APPLY_MITIGATION = "apply_mitigation"

SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_DOCUMENTS = "documents"
SOURCE_CREDENTIALS = "credentials"

# THE DEFAULTS THE SPECIFICATION DECLARES (`CP-SPEC-021` §B.3). `both` is the
# CONSERVATIVE posture: a product exposing only control-based grouping computes
# a compliant-looking number against an incomplete group.
DEFAULT_REGIME = "pra-2022"
DEFAULT_BASIS = "both"

SYSTEM = "cp-21-large-exposure"
PLAN_ID = "cp-21.large-exposure.v1"

NODE_MATCH_KEY = {
    "group": "group_node", "member": "member_node", "exposure": "exposure_node",
    "capital": "capital_node", "regime": "regime_node", "limit": "limit_node",
}
OBJECT_RULE = {
    "member": "member_object", "exposure": "exposure_object",
    "capital": "capital_object", "regime": "regime_object", "limit": "limit_object",
}
GROUP_SUBJECT_RULE = "group_subject"


def plan_id() -> str:
    return PLAN_ID


# =========================================================================
# ACQUIRE
# =========================================================================


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    effective = context.request.parameters
    as_of = _instant(effective[AS_OF])
    try:
        estate = acquisition.acquire(
            anchor_lei=context.request.subject,
            as_of=as_of,
            intent=context.request.intent,
            perspective=context.perspective.role,
            regime=str(effective.get(REGIME) or DEFAULT_REGIME),
            connection_basis=str(effective.get(CONNECTION_BASIS) or DEFAULT_BASIS),
            proposal=acquisition.bind_proposal(_as_mapping(effective.get(PROPOSAL)) or None),
            apply_mitigation=_as_bool(effective.get(APPLY_MITIGATION), default=True),
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
            document_settings=context.sources[SOURCE_DOCUMENTS],
        )
    except acquisition.UnknownBasis as basis:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(basis),
                                      error_code="unknown-connection-basis"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from basis
    except acquisition.UnknownRegime as regime_error:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(regime_error),
                                      error_code="regime-not-in-force"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from regime_error
    except acquisition.NoCapitalBase as no_capital:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(no_capital),
                                      error_code="no-capital-base"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from no_capital
    except acquisition.NoncanonicalMagnitude as noncanonical:
        # REFUSED, NEVER COERCED (`Q1`, `LEX-G04`). Rounding a float here would
        # produce an address nobody could reproduce.
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(noncanonical),
                                      error_code="noncanonical-magnitude"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from noncanonical
    except acquisition.UnknownRole as unknown:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(unknown),
                                      error_code="role-not-declared"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unknown
    except acquisition.UnpricedIntent as unpriced:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(unpriced),
                                      error_code="unpriced-intent"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unpriced
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant,
                     intent=context.request.intent, perspective=context.perspective.role,
                     as_of=str(effective[AS_OF]))


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime, intent: str,
    perspective: str, as_of: str,
) -> tuple[SignalEnvelope, ...]:
    """EDGES FIRST, ATTRIBUTED NODES LAST (`D-IMPL-316`)."""
    if estate.empty:
        return ()
    assert estate.group is not None
    group_uri = f"{acquisition.vocabulary()['entity_uri_prefix']['group']}{estate.anchor_lei}"
    edges = tuple(
        _edge(tenant_id=tenant_id, at=at, ordinal=ordinal, subject=group_uri, record=record)
        for ordinal, record in enumerate(estate.records)
    )
    nodes = tuple(_node(tenant_id=tenant_id, at=at, record=record) for record in estate.records)
    group = _group_claim(tenant_id=tenant_id, at=at, estate=estate, uri=group_uri,
                 intent=intent, perspective=perspective, as_of=as_of)
    return (*edges, *nodes, group)


def _edge(*, tenant_id: str, at: datetime, ordinal: int, subject: str, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"edge/{record.edge_type}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM), ingestion_timestamp=at, observed_time=None,
        raw_payload={
            GROUP_SUBJECT_RULE: subject,
            OBJECT_RULE[record.entity_class]: record.entity_uri,
            "subject_uri": subject, "object_uri": record.entity_uri,
            "predicate": record.edge_type,
        },
    )


def _node(*, tenant_id: str, at: datetime, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"node/{record.entity_uri}",
        source=SourceIdentity(system_id=SYSTEM), ingestion_timestamp=at,
        # TWO OBSERVATION TYPES (`D-IMPL-332`): group membership, an exposure
        # and a limit are STANDING STATE and carry no day; a regime version and
        # the capital base are DATED and carry theirs — which is exactly what
        # makes the freshness asymmetry measurable (`LEX-G14`).
        observed_time=_midnight(record.dated),
        raw_payload={
            NODE_MATCH_KEY[record.entity_class]: record.entity_uri,
            "entity_uri": record.entity_uri, **dict(record.attributes),
        },
    )


def _group_claim(
    *, tenant_id: str, at: datetime, estate: acquisition.Estate, uri: str,
    intent: str, perspective: str, as_of: str,
) -> SignalEnvelope:
    assert estate.group is not None
    terms = acquisition.vocabulary()
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM), ingestion_timestamp=at, observed_time=None,
        raw_payload={
            NODE_MATCH_KEY["group"]: uri, "entity_uri": uri, **estate.group,
            # THE FINDINGS ACQUISITION MEASURED. They are computed from the
            # sources and would otherwise be discarded at this seam; a finding
            # the product measured and did not serve is a finding nobody has.
            "acquisition_findings": _json.dumps(
                [dict(row) for row in estate.findings], sort_keys=True),
            "classification": terms["classification"]["assignment"]["group"],
            "intent": intent, "perspective": perspective, "as_of": as_of,
            "records_materialized": str(estate.records_materialized),
        },
    )


# =========================================================================
# ASSESS — `Q1`: the SDK's combinator, over MEMBERS
# =========================================================================


def assess(context: AssessmentContext) -> DebtAssessment:
    """The book's own factors, then the WORST FACTOR across its members.

    `Q1`, ruled 2026-09-21: use `ccf.halflife.debt.compose_debt_factors` — the
    SDK's `D-IMPL-104` rule, per-factor minimum strength — with the members as
    the composed sequence. Not `max(member D_c)`: collapsing each member to one
    number before composing loses *which* factor each was weak on, so a member
    weak only on freshness beside one weak only on completeness would read as
    one modest problem when in truth both are impaired.
    """
    assert context.half_life is not None and context.profile is not None
    scorer = AssemblyDebtScorer(
        table=context.half_life,
        profile=context.profile,
        completeness=DeclaredFactor(value=projection.view_completeness(context.view)),
        semantic_consistency=DeclaredFactor(value=Decimal("1.0000")),
    )
    assessment = scorer(view=context.view, evidence=context.evidence)
    members = projection.member_factors(context.view)
    if not members:
        return assessment
    composed = compose_debt_factors(assessment.factors, [factors for _, factors in members])
    return assessment.model_copy(update={"factors": composed, "debt": _debt_of(composed)})


def _debt_of(factors: DebtFactors) -> Decimal:
    from ccf.halflife.debt import context_debt  # noqa: PLC0415

    return context_debt(factors)


# =========================================================================
# THE DECLARED GATE — `cp-21.portfolio-holds`
# =========================================================================


def large_exposure_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Derived group · unit provenance · rule form · both authorities · asymmetry."""
    del evidence
    payload = candidate.payload
    role = payload.get("perspective")
    if not isinstance(role, str) or role not in projection.PERSPECTIVE_MEMBERS:
        return f"the payload names perspective {role!r}, which `artifacts/perspectives.yaml` does not declare"
    expected = projection.members_for(role)
    if set(payload) != expected:
        return (
            f"the payload's member set differs from the declared shape for role `{role}`"
            f" ({sorted(set(payload) ^ expected)}); the shape is a function of the perspective"
        )
    if payload.get("group") is None:
        return None

    # THE GROUP IS DERIVED, AND SAYS WHICH BASIS DERIVED IT.
    group = payload["group"]
    if group.get("derived") != "true":
        return (
            "the payload does not declare its group DERIVED; this group is computed from edges at"
            " the ledger point and is never read from a registry (LEX-G02)"
        )
    if group.get("connection_basis") not in acquisition.connection_bases():
        return f"the payload states connection basis {group.get('connection_basis')!r}, outside the declared domain (LEX-G03)"
    population = payload.get("members") or []
    if not population:
        return "the served group has no members; an empty group is refused rather than served (LEX-G02)"
    for member in population:
        if member.get("in_group") != "true":
            return f"member {member.get('legal_name')!r} is served without declaring group membership (LEX-G02)"

    # UNIT PROVENANCE SURVIVES NORMALIZATION (`Q2`, `LEX-G07`).
    capital = payload.get("capital_base")
    if not isinstance(capital, Mapping):
        return "the payload carries no capital base (LEX-G07)"
    for key in ("raw_value", "source_unit", "normalized_value", "normalized_unit",
                "unit_authority", "report_date", "age_days"):
        if capital.get(key) in (None, ""):
            return (
                f"`capital_base` states no {key!r}; the raw source value and the normalized"
                f" value must BOTH be served with their units, and the denominator's own date"
                f" travels with it (LEX-G07, LEX-G14)"
            )
    if capital.get("source_unit") == capital.get("normalized_unit"):
        return (
            "`capital_base` reports the same unit before and after normalization; the FFIEC"
            " source is in thousands and the arithmetic consumes dollars (LEX-G07)"
        )
    # THE DIMENSIONAL NEGATIVE CONTROL: the arithmetic must consume the
    # normalized figure, never the raw one.
    if payload.get("limits"):
        for row in payload["limits"]:
            if row.get("rule_form") == "percentage-of-capital" and row.get("limit_value"):
                if Decimal(str(row["limit_value"])) <= Decimal(str(capital["raw_value"])):
                    return (
                        f"limit {row.get('limit_id')!r} evaluates to {row.get('limit_value')} against a"
                        f" raw capital figure of {capital['raw_value']}; a percentage limit computed on"
                        f" the unnormalized base is dimensionally wrong (LEX-G06)"
                    )

    # THE RULE FORM IS NAMED, AND THE REGIME IS ATTRIBUTED.
    regime = payload.get("regime_in_force")
    if not isinstance(regime, Mapping):
        return "the payload names no regime in force (LEX-G10)"
    for key in ("regime_id", "effective_from", "rule_form", "limit_value", "authority"):
        if regime.get(key) in (None, ""):
            return (
                f"`regime_in_force` states no {key!r}; the determination must name the regime and"
                f" version selected, the effective basis, the rule form, the resulting limit and"
                f" the authority supporting it (LEX-G10)"
            )
    if regime.get("rule_form") not in ("percentage-of-capital", "absolute-amount"):
        return (
            f"`regime_in_force` names rule form {regime.get('rule_form')!r}; a limit is a percentage"
            f" of capital OR an absolute amount, and the product must say which (LEX-G09)"
        )
    for provision in regime.get("provisions") or ():
        if not provision.get("resolved") == "true" or not provision.get("quoted_text"):
            return (
                f"provision {provision.get('passage_id')!r} does not resolve to quoted rulebook text;"
                f" a limit must cite an authority that resolves, and no hash is minted (LEX-G08)"
            )

    # BOTH INTERNAL AUTHORITIES, AND THE CONFLICT VISIBLE.
    authorities = {row.get("authority") for row in payload.get("limits") or ()}
    if len(authorities) < 2:
        return (
            f"the payload serves limits from {sorted(a for a in authorities if a)} only; both the"
            f" relational register and the graph envelope are served, and neither is silently"
            f" dropped (LEX-G11)"
        )
    conflict = payload.get("limit_authority_conflict")
    if conflict is not None and not conflict.get("selected_by_rule"):
        return (
            "a limit-authority conflict is reported without naming the rule that selected one;"
            " the other source is not presented as wrong (LEX-G11)"
        )

    # THE ASYMMETRY IS DISCLOSED, NOT FUSED — AND THE SCAN IS RECURSIVE,
    # BECAUSE AT TOP LEVEL THIS LIMB COULD NOT FIRE.
    #
    # Measured 2026-09-21: the declared-shape check above already refuses any
    # undeclared top-level key, so a top-level `combined_freshness_at` was
    # caught as a shape violation and this limb was dead code. A fused
    # timestamp does not need to be top-level to do the damage — minting it
    # INSIDE `freshness_asymmetry` or `capital_base` is the likelier shape and
    # was unreachable by the original check. Recorded as `LEX-F-05`.
    fused = ("combined_freshness_at", "fused_as_of", "effective_freshness",
             "blended_as_of", "resolved_freshness_at")
    found = _fused_key(payload, fused)
    if found is not None:
        return (
            f"the payload names `{found}`; intraday exposure and a quarterly capital base do not"
            f" share a clock and are not collapsed into one timestamp (LEX-G14)"
        )
    asymmetry = payload.get("freshness_asymmetry")
    if not isinstance(asymmetry, Mapping) or asymmetry.get("resolved") != "false":
        return (
            "`freshness_asymmetry` does not declare the gap unresolved; the two clocks are"
            " disclosed, never reconciled (LEX-G14)"
        )
    if asymmetry.get("capital_report_date") != capital.get("report_date"):
        return (
            "`freshness_asymmetry` reports a capital date other than the capital base's own;"
            " the denominator's date travels WITH the ratio (LEX-G14)"
        )

    # WHICH LIMIT BINDS FIRST, AND THE PROPOSAL BOTH WAYS.
    evaluation = payload.get("evaluation")
    if not isinstance(evaluation, Mapping):
        return "the payload carries no evaluation (LEX-G12)"
    if not evaluation.get("binding_limit_id") or not evaluation.get("binding_limit_value"):
        return (
            "the evaluation says a limit binds without saying WHICH; identifying the binding limit"
            " is the determination, not a pass/fail (LEX-G12)"
        )
    if not evaluation.get("without_proposal"):
        return "the evaluation serves no pre-proposal position (LEX-G16)"
    if group.get("proposal_stated") == "true" and not evaluation.get("with_proposal"):
        return (
            "a proposal was stated and only one position is served; the determination is computed"
            " WITH and WITHOUT it, and both are served (LEX-G16)"
        )
    if evaluation.get("proposal_basis") not in (None, "assumption"):
        return (
            f"the evaluation labels the proposal {evaluation.get('proposal_basis')!r}; a proposal is"
            f" an assumption and never an observation (LEX-G17)"
        )

    # THE COUNTING RULES REACH THE ARITHMETIC.
    for row in payload.get("limits") or ():
        if row.get("authority") == "relational-limit-register":
            for key in ("counts_guarantees", "counts_undrawn", "connection_basis"):
                if row.get(key) in (None, ""):
                    return (
                        f"limit {row.get('limit_id')!r} is served without its {key!r} counting rule;"
                        f" headroom that ignores a counting rule is not the regime's headroom (LEX-G13)"
                    )

    debt = payload.get("population_debt")
    if not isinstance(debt, Mapping) or debt.get("rule") != "per-factor-minimum":
        return "`population_debt` does not name the ruled per-factor-minimum law (LEX-G19)"
    if any(key.startswith("proposal") for key in debt):
        return (
            "`population_debt` names a proposal input; a hypothetical is not evidence and cannot"
            " move Context Debt (LEX-G19)"
        )

    # THE EXAMINER RENDERING CARRIES WHAT THE OTHERS DO NOT (`LEX-G18`).
    # `policy_version` is asserted on the CONTRACT'S LINEAGE, not in the
    # payload: it belongs to lineage, and copying it into the payload would be
    # minting a second, divergeable copy of a governed fact.
    if role == "examiner":
        for member_name in ("methodology", "replay_attribution"):
            if not payload.get(member_name):
                return f"the examiner rendering serves no `{member_name}` (LEX-G18)"
        if not candidate.lineage.policy_bundle_versions:
            return (
                "the examiner rendering carries no policy bundle version in lineage; the"
                " determination cannot be reconstructed without the policy in force (LEX-G18)"
            )
        anchor = payload["replay_attribution"]
        for key in ("plan_id", "regime_id", "connection_basis", "capital_report_date",
                    "determination_instant"):
            if not anchor.get(key):
                return f"`replay_attribution` names no {key!r}; replay re-derives nothing (LEX-G21)"
        # THE LEDGER POINT IS DISCLOSED, NOT ASSERTED. This estate exposes no
        # route returning Fluree's `t` (`LEX-F-04`), so the product must say
        # whether it resolved one rather than presenting a constant as an
        # anchor. Gating on a value that is always `unreported` here would be
        # a vacuous gate; gating on the DISCLOSURE is not.
        if anchor.get("ledger_point_resolvable") not in ("true", "false"):
            return (
                "`replay_attribution` does not state whether the ledger point resolved; an"
                " unresolvable derivation point is disclosed, never minted (LEX-G21)"
            )
        if anchor.get("ledger_point_resolvable") == "false" and anchor.get("ledger_t") != "unreported":
            return (
                f"`replay_attribution` reports ledger point {anchor.get('ledger_t')!r} while"
                f" declaring it unresolvable; a `t` nobody can resolve is not minted (LEX-G21)"
            )

    vocabulary = set(projection.CLASSIFICATION_VOCABULARY)
    rows: list[tuple[str, Any]] = [
        (m, item) for m in projection.LIST_MEMBERS for item in payload.get(m) or ()
    ]
    for member_name, key in projection.NESTED_LIST_MEMBERS.items():
        holder = payload.get(member_name)
        if isinstance(holder, Mapping):
            rows.extend((f"{member_name}.{key}", item) for item in holder.get(key) or ())
    for member_name, item in rows:
        if not isinstance(item, Mapping):
            return f"member `{member_name}` carries a non-record entry {item!r}"
        classification = item.get("classification")
        if classification is not None and classification not in vocabulary:
            return f"member `{member_name}` carries classification {classification!r} outside the vocabulary"
    return None


# --- helpers ------------------------------------------------------------------------


def _fused_key(value: Any, forbidden: tuple[str, ...], *, path: str = "") -> str | None:
    """Any fused-freshness key, at any depth."""
    if isinstance(value, Mapping):
        for key, nested in value.items():
            here = f"{path}.{key}" if path else str(key)
            if key in forbidden:
                return here
            found = _fused_key(nested, forbidden, path=here)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = _fused_key(item, forbidden, path=f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _instant(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"an instant must carry a zone; got {value!r}")
    return parsed.astimezone(UTC)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """`proposal` is declared a CLOSED OBJECT and is passed as a mapping."""
    if value is None or value == "":
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("`proposal` is declared an object; pass a mapping, not a scalar")
    return value


def _as_bool(value: Any, *, default: bool) -> bool:
    """`apply_mitigation` defaults to TRUE, and the default is declared."""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    raise ValueError("`apply_mitigation` is declared a boolean; pass true or false")


def _as_list(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        raise ValueError("this parameter is declared an array; pass a list, not a string")
    return tuple(str(item) for item in value)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _midnight(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def credential_grants(sources: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    return {token: principal_id for principal_id, token in sources[SOURCE_CREDENTIALS].items()}
