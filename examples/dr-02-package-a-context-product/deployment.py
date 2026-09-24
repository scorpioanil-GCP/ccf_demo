"""The three verbs, and the gate that keeps the packaging honest.

[ADAPT] the vocabulary. [MECHANISM] the context types imported from the SDK.

The gate at the bottom is what `dr-02` exists for. Everything above it is
arrangement.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

import acquisition
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import (
    DebtAssessment,
    FreshnessScorer,
    Observation,
    assess_debt,
)
from ccf.products.contract import ContextProductContract
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.replay.record import NO_PACKAGING, PackagingTrace
from ccf.signal.envelope import SignalEnvelope

from memo_packaging import AnthropicPackager, DeterministicPackager, PackagingModel

HERE = Path(__file__).parent

FACILITY = "facility_id"
BORROWER_SCOPE = "borrower_scope"
AUDIENCE = "audience"

#: The upstream product class this rung packages (`DR-SPEC-002` R1).
UPSTREAM_CLASS = "credit-risk.collateral-coverage"
UPSTREAM_VERSION = "1.0.0"
UPSTREAM_TENANT = "cp-06-canonical-demo"
UPSTREAM_INTENT = "lgd-assessment"
UPSTREAM_FRESHNESS = "as-filed"

#: The prompt artifact — versioned, hashed, and pinned on every record.
PROMPT_ARTIFACT = HERE / "artifacts" / "memo-prompt.yaml"
PROMPT_URI = "ccf-artifact://dr-02/packaging-prompt/1.0.0"

#: Any run of digits, optionally with a decimal part or separators. The
#: smoothing gate's "is this a figure" test, deliberately BROAD: a narrow
#: pattern would let a moved decimal point through, and the cost of breadth
#: is only that a declared figure has to match.
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def prompt() -> Mapping[str, Any]:
    """The prompt artifact's declaration, read once."""
    return dict(
        yaml.safe_load(PROMPT_ARTIFACT.read_text(encoding="utf-8"))["declaration"]
    )


def prompt_hash() -> str:
    """The identity of the bytes the packaging actually used (`D-IMPL-26`)."""
    return content_hash(PROMPT_ARTIFACT.read_text(encoding="utf-8"))


def packager(declaration: Mapping[str, Any]) -> PackagingModel:
    """The deterministic packager, unless the deployment named a real model.

    `DR-SPEC-002` R4: the stub suffices and CI never reaches a provider. The
    real model is selected only by an explicit `model` setting, so a green
    build cannot acquire a network dependency by accident.
    """
    model = str(declaration.get("model", "")).strip()
    temperature = str(declaration.get("temperature", "0.0"))
    if not model:
        return DeterministicPackager(temperature=temperature)
    return AnthropicPackager(
        model=model,
        temperature=temperature,
        instruction=str(declaration["instruction"]),
    )


def packaging_trace(*, product: ContextProductContract) -> PackagingTrace:
    """§7.10.4's five pins for replay dimension 3 (`PKG-F-08`).

    **Conforms to** :class:`~ccf.products.resolver.PackagingTraceProtocol`.
    The SDK cannot compute any of this — which model ran, at what temperature,
    against which prompt, and what bytes came back are facts of THIS
    deployment's packaging stage — so the deployment says, and the resolver
    records it verbatim.

    **`output_hash` is RECOMPUTED here, from the payload actually being
    served**, rather than copied out of `packaged_by`. Copying would make the
    record agree with the payload by construction, and §7.10.4 wants the two
    readings independent: the payload carries what the packager DECLARED it
    produced, dimension 3 carries what was actually served, and `PKG-G09`
    compares them. A prose edit between packaging and serve moves one and not
    the other.

    The other four are read off the payload because they are the packager's
    own identity, carried on every section — there is no second place to read
    them from, and nothing downstream can alter them without altering the
    sections they ride on.
    """
    payload = dict(product.payload)
    pins = dict(payload.get("packaged_by") or {})
    return PackagingTrace(
        model_version=str(pins.get("model") or NO_PACKAGING),
        temperature=str(pins.get("temperature") or NO_PACKAGING),
        prompt_artifact_uri=str(pins.get("prompt_artifact_uri") or NO_PACKAGING),
        prompt_artifact_hash=str(pins.get("prompt_artifact_hash") or NO_PACKAGING),
        output_hash=acquisition.output_hash(payload.get("sections") or ()),
    )


def plan_id(facility_id: str) -> str:
    return f"dr-02.packaged-memo/{facility_id}"


# ---------------------------------------------------------------------------
# acquire — ask, package, emit. The Mode 2 seam.
# ---------------------------------------------------------------------------


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Ask the upstream product, package it, and hand back dated claims.

    Raises:
        GovernedRefusalRaised: the upstream refused or fell silent, or the
            packager would not render. Each is this product's refusal, raised
            here because the acquisition seam is where a deployment's governed
            refusal becomes data.
    """
    effective = context.request.parameters
    declaration = prompt()
    answer = acquisition.ask_upstream(
        settings=context.sources[acquisition.SOURCE_UPSTREAM],
        tenant=UPSTREAM_TENANT,
        product_class=UPSTREAM_CLASS,
        version=UPSTREAM_VERSION,
        subject=str(effective[FACILITY]),
        # The upstream's own intent, not this product's. `dr-02` asks a
        # coverage question and packages the answer; asking under
        # `credit-memo-drafting` would be asking the upstream a question its
        # discovery set does not declare.
        intent=UPSTREAM_INTENT,
        freshness=UPSTREAM_FRESHNESS,
        parameters={
            FACILITY: str(effective[FACILITY]),
            # Carried VERBATIM. The packaging cannot widen an entitlement the
            # substrate narrowed, so the upstream walk is bounded by exactly
            # what this caller was already entitled to.
            BORROWER_SCOPE: list(effective.get(BORROWER_SCOPE) or ()),
        },
        at=context.instant,
    )
    model = packager(declaration)
    sections = acquisition.package(
        answer=answer, model=model, headings=declaration["headings"]
    )
    return acquisition.envelopes(
        answer=answer,
        sections=sections,
        model=model,
        prompt_uri=PROMPT_URI,
        prompt_hash=prompt_hash(),
        facility_id=str(effective[FACILITY]),
        tenant_id=context.tenant_id,
        at=context.instant,
    )


# ---------------------------------------------------------------------------
# assess — the packaging adds no debt of its own
# ---------------------------------------------------------------------------


def assess(context: AssessmentContext) -> DebtAssessment:
    """Debt over the packaged sections.

    **The packaging contributes no freshness of its own.** Prose written this
    second over a product from last quarter is last quarter's information, and
    a debt reading that said otherwise would be the clearest possible way for
    a rendering to look fresher than what it renders.
    """
    assert context.half_life is not None and context.profile is not None
    return debt(
        context.view,
        now=context.decided_at,
        half_life=context.half_life,
        profile=context.profile,
    )


def debt(
    view: GraphView,
    *,
    now: datetime,
    half_life: HalfLifeTable,
    profile: DebtProfile,
) -> DebtAssessment:
    """Freshness over the sections; completeness over the ones that rendered.

    **Every section carries the same instant**, because the packaging read one
    product at one moment — so `F` here measures the age of the SUBSTRATE's
    reading, which is the only clock this rung has and the correct one.

    **Completeness is the share of declared sections that carry prose.** A
    section that came back blank is not a section with nothing to report; it
    is a section the packaging did not produce, and pricing it as complete
    would hide exactly the failure the smoothing gate refuses.
    """
    sections = [
        record
        for record in view.entities
        if record.claim.attributes.get("heading") is not None
    ]
    observations = [
        Observation(
            observation_type=record.claim.entity_class,
            observed_at=record.claim.observed_at,
            valid_from=record.claim.valid_from,
            subject=record.claim.entity_uri,
        )
        for record in sections
        if record.claim.valid_from is not None
    ]
    rendered = [
        record for record in sections if record.claim.attributes.get("prose")
    ]
    scorer = FreshnessScorer(
        table=half_life, risk_sensitivity=profile.risk_sensitivity
    )
    return assess_debt(
        DebtFactors(
            freshness=scorer.score(observations, now=now) if observations else Decimal(1),
            completeness=(
                Decimal(len(rendered)) / Decimal(len(sections))
                if sections
                else Decimal(0)
            ),
            semantic_consistency=Decimal(1),
        ),
        profile=profile,
    )


# ---------------------------------------------------------------------------
# THE SMOOTHING GATE — `packaging.did-not-move-the-conclusion` 1.0.0
# ---------------------------------------------------------------------------


def packaging_gate(*, candidate: Any, evidence: object = None) -> str | None:
    """Refuse a memo whose prose says something its substrate does not.

    Whitepaper §7.10.4's own watchpoint, as this product's fourth validation
    gate, and `DR-SPEC-002` R3's ruling that it **refuses** rather than serving
    with a finding: an unsupported figure in a credit memo is the failure this
    rung exists to prevent, and a product that serves it with a caveat has
    served it.

    Four refusals, and the first is the one that matters:

    1. **a figure in the prose that the substrate does not carry** — the
       packaging invented a number;
    2. a section whose `derived_from` is not the product actually packaged —
       the prose is about something else;
    3. the packaging identity missing — prose with no provenance;
    4. no sections at all where the substrate served a product — a memo that
       renders nothing reads as "nothing to report", which is a claim.

    **Returns a detail string to refuse, `None` to serve** — the SDK stamps
    the declared gate identity on the refusal, so the record can say which
    gate produced it rather than taking the failing code's word.

    The accepted cost, stated rather than discovered (`DR-SPEC-002` R3): a
    merely verbose model makes this product refuse. That is the correct trade
    for a credit memo.
    """
    payload = getattr(candidate, "payload", None)
    if not isinstance(payload, Mapping):
        return "the candidate carries no payload to check"

    packaged_from = payload.get("packaged_from")
    address = (
        packaged_from.get("content_address")
        if isinstance(packaged_from, Mapping)
        else None
    )
    if not address:
        return "the packaged memo names no substrate content address"

    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        return (
            "the substrate served a product and the packaging rendered no"
            " sections; an empty memo reads as 'nothing to report', which is a"
            " claim this product did not make"
        )

    for section in sections:
        if not isinstance(section, Mapping):
            return "a section is not a mapping"
        heading = str(section.get("heading"))
        if section.get("derived_from") != address:
            return (
                f"section {heading!r} derives from"
                f" {section.get('derived_from')!r}, not from the substrate this"
                f" memo packaged ({address!r})"
            )
        supported = {_canonical(value) for value in section.get("figures_cited") or ()}
        for written in _NUMBER.findall(str(section.get("prose") or "")):
            if _canonical(written) not in supported:
                return (
                    f"section {heading!r} states the figure {written!r}, which"
                    " the substrate does not carry. The packaging moved the"
                    " conclusion (whitepaper §7.10.4)"
                )
    return None


def _canonical(value: object) -> str:
    """Compare figures by VALUE, never by spelling.

    `1,250.00`, `1250.0` and `1250` are one figure written three ways, and a
    gate that compared strings would refuse an honest memo for reformatting a
    number it was given. A value that will not parse compares as its own text,
    so a non-numeric citation is still checkable.
    """
    text = str(value).replace(",", "").strip()
    try:
        return str(Decimal(text).normalize())
    except (InvalidOperation, ValueError):
        return text
