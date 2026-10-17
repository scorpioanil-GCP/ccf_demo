# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The deployment's own verbs: acquire, assess, and the ONE question mapping.

[ADAPT] everything here. [MECHANISM] the context and contract types imported
from the SDK; nothing else is SDK code.

**The whole consumer, in one sentence.** ``ccf_config.yaml`` declares what the
brief requires, who may provide it, the skill that asks, the agent that holds
the grant and the regime that judges it; this module reads the one leg the brief
owns and says what the one requirement is ASKED (:func:`questions`). The SDK
does the rest — registers the producer, derives the skill, requests the grant
through the ledger at open, asks, holds the answer to the registration, admits
or refuses, composes, and records.

Read from ``artifacts/``: the obligor class, the child class, the parameter
names, and the child's intent and freshness. **Restated here, not read:** the
match key (:data:`MATCH_KEY`, which ``ccf_config.yaml``'s ``resolution`` section
also declares), the identity payload keys in :func:`acquire` (the same attribute
names ``resolution.entity_rules[].attribute_keys`` declares), the ``plan_id``
prefix (the product name ``product_class.schema_name`` also declares) and
:data:`SOURCE` (the environment document's label). The SDK hands ``acquire`` no
resolution spec, so each repeats a value another document holds; FINDINGS.md
records the duplication and how it fails when the copies drift (§E).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import acquisition
import yaml
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.products.child_resolver import ChildQuestion
from ccf.products.contract import ChildRequirement
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent


def _declaration(name: str) -> Mapping[str, Any]:
    document: Mapping[str, Any] = yaml.safe_load((HERE / "artifacts" / name).read_text(encoding="utf-8"))
    return document["declaration"]


#: The questions this example asks — the brief's, the demonstration's and the child's.
QUESTION = _declaration("question.yaml")

#: The environment document's label for the identity store (``ccf_environment.yaml``).
SOURCE = "identity"

#: The obligor's class in the fabric.
CLASS_OBLIGOR = str(_declaration("projection.yaml")["obligor_class"])

#: The one class the brief requires, as ``requires`` declares it.
CHILD_CLASS = str(_declaration("projection.yaml")["child_class"])

#: RESTATED from ``ccf_config.yaml``'s ``resolution.entity_rules[].match_key``. A
#: drift between the two resolves no entity, raises nothing, and surfaces only as
#: the brief's own-view refusal (FINDINGS.md §E).
MATCH_KEY = "obligor_ref"


def plan_id(subject: str) -> str:
    return f"sk-01/facility-collateral-brief/{subject}"


# --- the parent's own leg -------------------------------------------------------


def _instant(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Read the obligor's identity row; hand it back as one dated claim.

    A subject the estate holds no identity for hands back nothing: nothing is
    written, and the governed path refuses on the parent's own empty view, with
    a record.
    """
    terms = acquisition.vocabulary()
    resolved = acquisition.resolve(context.request.subject, settings=context.sources[SOURCE])
    if resolved is None:
        return ()
    ref = f"{CLASS_OBLIGOR}:{resolved.lei}"
    return (
        SignalEnvelope(
            tenant_id=context.tenant_id,
            envelope_id=ref,
            source=SourceIdentity(system_id=str(terms["table"])),
            ingestion_timestamp=context.instant,
            # When the identity record was last taken — never a wall clock.
            observed_time=_instant(resolved.retrieved_at) if resolved.retrieved_at else context.instant,
            raw_payload={
                MATCH_KEY: ref,
                "entity_ref": ref,
                "lei": resolved.lei,
                "legal_name": resolved.legal_name,
                "legal_jurisdiction": resolved.legal_jurisdiction,
            },
        ),
    )


def assess(context: AssessmentContext) -> DebtAssessment:
    """The parent's OWN F, C and S over its own leg, at the decision instant.

    Freshness decays the identity record's age against the declared λ_c;
    completeness is whether the obligor resolved at all; consistency is 1 — one
    store, nothing to disagree. The child's debt reaches the brief by the SDK's
    composition (`D-IMPL-31`), never here.
    """
    assert context.half_life is not None and context.profile is not None
    obligors = [r for r in context.view.entities if r.claim.entity_class == CLASS_OBLIGOR]
    if not obligors:
        return assess_debt(
            DebtFactors(freshness=Decimal(0), completeness=Decimal(0), semantic_consistency=Decimal(1)),
            profile=context.profile,
        )
    observations = tuple(
        Observation(observation_type=CLASS_OBLIGOR, observed_at=record.claim.observed_at, subject=record.claim.entity_uri)
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


def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
    """*Given this brief's EFFECTIVE request, what is the one requirement asked?*

    The facility the brief names is the child's subject and its facility
    parameter; the obligor (the brief's subject) is the child's one-element
    borrower scope. The intent, freshness and parameter names are the child's
    own vocabulary, read from ``artifacts/question.yaml``. The tenant, class,
    lane, instant and endpoint come from the registration and the composite,
    never from here.
    """
    if requirement.product_class != CHILD_CLASS:
        raise ValueError(f"no question mapping for required class {requirement.product_class!r}")
    child = QUESTION["child"]
    facility = str(request.parameters[QUESTION["brief"]["facility_parameter"]])
    return ChildQuestion(
        subject=facility,
        intent=str(child["intent"]),
        freshness=str(child["freshness"]),
        parameters={
            str(child["facility_parameter"]): facility,
            str(child["borrower_scope_parameter"]): [request.subject],
        },
    )
