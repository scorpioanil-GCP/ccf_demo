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

import yaml

import acquisition
from ccf.agents.definitions import AgentDefinition
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DEPLOYMENT_CONFIG, load_artifact, parse_artifact
from ccf.deployment import (
    derive_deployment,
    register_manifest_entries,
    resolve_artifact_class,
)
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, assess_debt
from ccf.products.child_resolver import ChildQuestion, QuestionBoundChildResolver
from ccf.products.composite import CompositeAdmissionGate
from ccf.products.contract import ChildRequirement
from ccf.products.product import AcquisitionContext, AssessmentContext, ConsumerContext
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    SubjectUnavailableRefusal,
)
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalog, SkillCatalogEntry
from ccf.skills.grants import ApprovalOutcome, GrantLedger, SkillGrant

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
    # ENVELOPE CONTAINMENT, AND IT RUNS HERE FOR A MEASURED REASON.
    #
    # The acquisition seam is the ONLY place a deployment's governed refusal
    # becomes data: `GovernedResolver` catches `GovernedRefusalRaised` around
    # `acquisition(...)` and nowhere else, and child resolution happens
    # strictly after. Raising the same refusal from the `build_children=`
    # seam escapes as an exception instead of a `RefusalEnvelope` — measured
    # 2026-09-22 and recorded as `CLD-F-06`.
    #
    # It also belongs here: the envelope is a fact this deployment reads from
    # its OWN stores, in this read, and checking it here avoids a second read
    # of the same two legs. No peer has been called at this point and none
    # will be if this refuses (`CLD-G10`).
    refuse_outside_envelope(syndicate, request=context.request)
    return envelopes(syndicate, tenant_id=context.tenant_id, at=context.instant)


def refuse_outside_envelope(
    syndicate: acquisition.Syndicate, *, request: ProductRequest
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
        for row in syndicate.envelopes
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
# BEGIN build_children GLUE — `CLD-F-04`
#
# Everything from here to END is the consumer chain `open_product` derives for
# itself when a composite declares `agent:`, `skills:` and `questions=`. This
# composite may declare none of them: `include_federated` is a request
# parameter, the child-resolution seam is the only place it can be honored,
# and `build_children=` is refused beside a declared chain. So the chain is
# rebuilt here from `artifacts/consumer-chain.yaml`.
#
# The artifacts stay artifacts (CLAUDE.md §6.4). What is hand-written is the
# WIRING, not the values.
# ===========================================================================


def _registered_chain(registry: Any) -> tuple[str, AgentDefinition, str, SkillCatalogEntry]:
    """Register what the derived chain registers, then build the agent and skill.

    `open_product` does NOT register the manifest's artifacts before it calls
    a `build_children=` factory — that registration lives inside the derived
    chain this deployment may not declare. Measured 2026-09-22: the Control
    Plane has ZERO audit events at this point. So the policy bundle and the
    debt profile the agent PINS are registered here, through the SDK's own
    one register loop (`register_manifest_entries`) over the SDK's own
    derivation (`derive_deployment`) — never a second parse of the config and
    never a hand-written hash.
    """
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "artifacts" / "consumer-chain.yaml").read_text(encoding="utf-8")
    )
    declaration = document["declaration"]
    pins, keys = declaration["pins"], declaration["keys"]

    config = load_artifact(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8"), DEPLOYMENT_CONFIG
    )
    derived = derive_deployment(config)  # type: ignore[arg-type]
    wanted = frozenset({str(pins["policy_regime_key"]), str(pins["debt_profile_key"])})
    parsed = {
        entry.key: parse_artifact(
            derived.documents[entry.key], resolve_artifact_class(entry.class_id)
        )
        for entry in derived.manifest.artifacts
        if entry.key in wanted
    }
    register_manifest_entries(derived.manifest, parsed, registry=registry, only=wanted)

    agent_document = {
        **declaration["agent"],
        "policy_regime": {"ref": _pinned_ref(registry, str(pins["policy_regime_key"]))},
        "halflife_debt_profile": {
            "ref": _pinned_ref(registry, str(pins["debt_profile_key"]))
        },
    }
    agent = parse_artifact(agent_document, resolve_artifact_class("ccf.agent-definition"))
    skill = parse_artifact(declaration["skill"], resolve_artifact_class("ccf.skill-catalog-entry"))
    assert isinstance(agent, AgentDefinition)
    assert isinstance(skill, SkillCatalogEntry)
    return str(keys["agent"]), agent, str(keys["skill"]), skill


class _NoApprovalSink:
    """The tier-2 surface this deployment supplies: it refuses, never decides.

    A copy of the SDK's own private `_NoApprovalSink`, because a chain handed
    in through `build_children=` must supply one and the SDK's is not
    exported. The regime in force declares `grant_requires_approval: false`,
    so this is never consulted — and if a later regime required approval, an
    open over it would fail here by name rather than the SDK approving
    anything on this deployment's behalf (`D-IMPL-29`).
    """

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise ValueError(
            f"the policy regime requires approval for grant {grant.name!r} and"
            " this deployment supplied no approval sink"
        )


def _pinned_ref(registry: Any, key: str) -> str:
    """The `ccf-artifact://` ref for the version of ``key`` in force.

    The version component is a CONTENT ADDRESS, so it is read off the Control
    Plane rather than authored — a hash written by hand into an artifact is a
    second statement of a value that moves.
    """
    tenant, artifact_class, name = key.split("/", 2)
    version, _artifact = registry.resolve_latest(key)
    return artifact_uri(
        tenant_id=tenant, artifact_class=artifact_class, name=name,
        artifact_version=version,
    )


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
        """Build the derived chain over the facade's own registrations."""
        registry = context.control_plane
        agent_key, agent, skill_key, skill = _registered_chain(registry)
        registry.register(skill_key, skill)
        registry.register(agent_key, agent)
        agent_hash = content_hash(agent)
        ledger = GrantLedger(
            control_plane=registry, catalog=SkillCatalog(registry),
            sink=_NoApprovalSink(), clock=context.clock
        )
        if skill.name not in ledger.bound_view(agent_hash):
            outcome = ledger.request(
                SkillGrant(
                    schema_version=skill.schema_version,
                    artifact_version=skill.artifact_version,
                    name=skill.name,
                    tenant=skill.tenant,
                    agent_definition_hash=agent_hash,
                    skill_name=skill.name,
                    skill_version=skill.artifact_version,
                ),
                definition=agent,
                actor=agent.name,
            )
            if not isinstance(outcome, str):
                raise ValueError(
                    f"the grant for {skill.name!r} was refused by the Control"
                    f" Plane ({type(outcome).__name__}); a composite whose agent"
                    " may not bind the skill that produces its child class"
                    " cannot compose it"
                )
        self._resolver = QuestionBoundChildResolver(
            ledger=ledger,
            agent_definition_hash=agent_hash,
            gate=CompositeAdmissionGate(
                tenant_id=agent.tenant,
                consumer_scope=f"consumer://{agent.tenant}/{agent.name}",
                registry=registry,
            ),
            child_questions=self._question,
            callable_registry=CallableRegistry(),
            artifact_store=context.artifact_store,
            mcp_skills=context.mcp_skills,
        )
        return self

    def bind(self, sources: Mapping[str, Mapping[str, str]]) -> None:
        """Bind the source settings the road resolved, once, at open.

        Retained deliberately though this class no longer reads a store: the
        envelope check moved to the acquisition seam (`CLD-F-06`), and keeping
        the binding here would be keeping a handle nothing uses. It is the
        opened product's `sources` and nothing else, so a later seam that
        needs them has one place to find them.
        """
        self._sources = sources

    # -- the question this deployment asks the peer ------------------------
    def _question(
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
        assert self._resolver is not None  # `factory` ran at open
        self._dispatches += 1
        return self._resolver.resolve_for(
            requirements=requirements, request=request, asked_at=asked_at,
            admitted_at=admitted_at, composition_invocation=composition_invocation,
            consumer_lineage=consumer_lineage,
        )


# ===========================================================================
# END build_children GLUE — `CLD-F-04`
# ===========================================================================
