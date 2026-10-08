"""SEC-020's combined proof: the deployments, the doors, and what a caller can observe.

Dave's closure condition for SEC-020 (2026-10-07), verbatim: *"prove withheld
and nonexistent subjects are indistinguishable across responses, refusal codes,
public references, composite paths and authorized record reads. Keep SEC-020
open until that combined proof passes."* This module builds the deployments
and the doors; ``tests/products/test_sec020_combined_proof.py`` compares what
comes out of them. Nothing here closes SEC-020: the suite is the closure gate,
and it is red where the measurements below say it is.

**Public behavior only.** Every observation is something a caller, the owner of
a decision record, or another principal can receive: the outcome of a question
through the in-process paved road (:meth:`ccf.products.product.OpenedProduct.answer`)
or a low-road :class:`~ccf.products.resolver.GovernedResolver`, the HTTP door
(:func:`ccf_runtime.http_api.app.create_app`), the MCP product door
(:func:`ccf_runtime.mcp.egress.build_egress_server`), and every read of the
record behind the references those doors hand out: the HTTP replay and artifact
routes, the MCP artifact server, and the MCP Experience server's
``get_replay_record`` tool. The internal reads are the recorded refusal cause
and a composite's child rows, which Dave named as observables; both are read
from the deployment's own store, as an auditor would.

The two comparisons
-------------------
* **Counterfactual** (``cf``) — the brief's matrix: two deployments identical in
  every byte except whether the data source holds the subject, both asked the
  SAME question about the SAME identifier by the SAME principal, under the same
  policy. The policy withholds the subject from the asking principal by its
  content (its ``book`` attribute), so in the deployment whose source does not
  hold it nothing is withheld and the question takes the plain nonexistent
  path. Because the request is byte-identical, every reference and every record
  can be compared path for path, version segment included.
* **Same deployment** (``same``) — the ruled formulation (``D-IMPL-371``): in
  ONE deployment whose source holds the subject, the withheld subject against an
  identifier no source has ever held. The two requests differ in their subject,
  so the reference is compared by its name segment only and records are not
  compared byte for byte (the request is inside them).

Every comparison carries its own noise floor — a second, independent copy of the
nonexistent side — and every channel its own instrument: a side that must differ
from the nonexistent one on that channel (the subject SERVED, by the same
deployment with the policy switched off; for refusal codes, a question the
request contract refuses), or the comparison cannot see what it claims to compare.

Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import asyncio
import base64
import copy
import json
import pathlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.graph.protocols import GraphView
from ccf.products.disclosure import DISCLOSURE_FULL, DISCLOSURE_MINIMAL
from ccf.products.door import WireRequest
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope

from tests.composition import register_typed_at_composition

# =============================================================================
# Fixture vocabulary
# =============================================================================

#: The two anchors a product class may declare (``ccf.products.expiry``).
FROM_DECISION = "from_decision"
FROM_ENTITY_FRESHNESS = "from_entity_freshness"
ANCHORS = (FROM_DECISION, FROM_ENTITY_FRESHNESS)

#: The asking principal (the fixtures' own default perspective), and a second
#: principal of the same tenant, granted the same class at the same level.
ASKER = "principal-fixture"
OTHER = "principal-other"
ASKER_TOKEN = "sec020-proof-asker-token"
OTHER_TOKEN = "sec020-proof-other-token"

#: The subject the policy withholds from the asker, by its content.
SUBJECT_REF = "acct-subject"
#: An identifier no source holds in any deployment of this module.
NEVER_REF = "acct-never-held"
#: A second such identifier: the noise floor of the same-deployment comparison.
NEVER_2_REF = "acct-never-held-2"
#: A sibling every population source holds, in every deployment.
SIBLING_REF = "acct-sibling"
#: The subject a FIXED composite child is asked about, held everywhere.
FIXED_REF = "acct-fixed"

#: The ``book`` attribute the policy reads. Fixture vocabulary.
BOOK_ATTRIBUTE = "book"
RESTRICTED_BOOK = "restricted-book"
OPEN_BOOK = "open-book"

#: The question's four axes and its one declared parameter value.
INTENT = "fixture-intent"
FRESHNESS = "fixture-freshness"
THRESHOLD_VALUE = 1000


def entity_uri(account_ref: str) -> str:
    """The entity URI the fixtures' resolution rule mints for ``account_ref``."""
    return f"account://{content_hash({'account_ref': account_ref})}"


SUBJECT = entity_uri(SUBJECT_REF)
NEVER = entity_uri(NEVER_REF)
NEVER_2 = entity_uri(NEVER_2_REF)
SIBLING = entity_uri(SIBLING_REF)
FIXED = entity_uri(FIXED_REF)


@dataclass(frozen=True)
class Holding:
    """One account a source holds: what it says and when it observed it."""

    account_ref: str
    book: str
    label: str
    observed_at: datetime


# =============================================================================
# The policy: Π withholds a restricted-book subject from the asking principal
# =============================================================================


class PolicyProjection:
    """A Π that answers about the request's subject only, and withholds by content.

    The policy: the asking principal may not be told about a subject whose
    record says it sits in :data:`RESTRICTED_BOOK`. Π finds the subject's own
    record in its view; a subject it cannot find gets the empty payload; a
    subject it withholds gets EXACTLY that payload plus the typed withheld
    signal (``ccf.projection.plan.ProjectionOutput``) — so the payload never
    differs and only what the SDK renders around it can. ``active=False`` is
    the instrument deployment: the same Π with the policy switched off, whose
    restricted subject is SERVED.
    """

    def __init__(
        self,
        *,
        required: tuple[str, ...],
        request: ProductRequest,
        plan_id: str,
        asker: str,
        active: bool,
    ) -> None:
        self._required = required
        self._request = request
        self._plan_id = plan_id
        self._asker = asker
        self._active = active

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        subject = self._request.subject
        records = sorted(
            (record for record in view.entities if record.claim.entity_uri == subject),
            key=lambda record: record.claim_id,
        )
        if not records:
            return ProjectionOutput(plan_id=self._plan_id, payload={})
        attributes = dict(records[-1].claim.attributes)
        if (
            self._active
            and attributes.get(BOOK_ATTRIBUTE) == RESTRICTED_BOOK
            and perspective.principal_id == self._asker
        ):
            return ProjectionOutput(plan_id=self._plan_id, payload={}, withheld=True)
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={"account": subject, "label": attributes.get("label", "")},
        )


class PolicyPlanFactory:
    """A NAMED plan factory (``D-IMPL-137``) building :class:`PolicyProjection`."""

    def __init__(self, *, plan_id: str, asker: str, active: bool) -> None:
        self.plan_id = plan_id
        self.asker = asker
        self.active = active

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> PolicyProjection:
        return PolicyProjection(
            required=required,
            request=request,
            plan_id=self.plan_id,
            asker=self.asker,
            active=self.active,
        )


# --- early withholding (PENDING API) -------------------------------------------

#: Early withholding's documented public name (Dave, Q8; lane ``378-s020design``
#: PROPOSAL, Part 2, channel 4): an optional companion Protocol on the plan
#: factory, ``discloses(*, request, perspective)`` and ``undisclosed_subject()``.
EARLY_WITHHOLDING_PROTOCOL = "SubjectDisclosingPlanFactoryProtocol"


def early_withholding_exists() -> bool:
    """Whether early withholding exists under its documented name."""
    import ccf.products.resolver as resolver  # noqa: PLC0415

    return hasattr(resolver, EARLY_WITHHOLDING_PROTOCOL)


#: The identifier an early-withholding deployment declares in place of a subject
#: it does not disclose: one no source of this module holds.
STAND_IN_REF = "acct-undisclosed-stand-in"
STAND_IN = entity_uri(STAND_IN_REF)


class EarlyPolicyProjection(PolicyProjection):
    """Π under early withholding: an undisclosed subject is withheld by its identifier.

    The decision was made before anything was fetched and cannot depend on
    whether the subject exists (Dave, Q8), so Π withholds the subject the
    factory declared undisclosed to the asking principal whatever its view holds.
    """

    def __init__(self, *, undisclosed: bool, **arguments: Any) -> None:
        super().__init__(**arguments)
        self._undisclosed = undisclosed

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        if self._undisclosed and perspective.principal_id == self._asker:
            return ProjectionOutput(plan_id=self.plan_id, payload={}, withheld=True)
        return super().invoke(
            view=view, operator_outputs=operator_outputs, perspective=perspective,
            temporal_boundary=temporal_boundary,
        )


class EarlyWithholdingPlanFactory(PolicyPlanFactory):
    """A plan factory that decides disclosure BEFORE any fetch (the documented companion Protocol).

    The asker is not told about :data:`SUBJECT`; everything else is disclosed.
    The decision reads the request and the perspective only.
    """

    def discloses(self, *, request: ProductRequest, perspective: Perspective) -> bool:
        return not (self.active and perspective.principal_id == self.asker and request.subject == SUBJECT)

    def undisclosed_subject(self) -> str:
        return STAND_IN

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> PolicyProjection:
        return EarlyPolicyProjection(
            undisclosed=self.active and request.subject == SUBJECT,
            required=required,
            request=request,
            plan_id=self.plan_id,
            asker=self.asker,
            active=self.active,
        )


def plan_factory(*, early: bool, plan_id: str, asker: str, active: bool) -> PolicyPlanFactory:
    """The late (inside-Π) policy, or the same policy declared early."""
    kind = EarlyWithholdingPlanFactory if early else PolicyPlanFactory
    return kind(plan_id=plan_id, asker=asker, active=active)


def envelope_for(
    holding: Holding, *, tenant: str, ingested_at: datetime, envelope_id: str | None = None
) -> SignalEnvelope:
    """One admitted claim about ``holding``, stamped for ``tenant`` at ``ingested_at``."""
    return SignalEnvelope.model_validate(
        {
            "tenant_id": tenant,
            "envelope_id": envelope_id or f"envelope-{holding.account_ref}",
            "source": {"system_id": "fixture-system"},
            "ingestion_timestamp": ingested_at,
            "observed_time": holding.observed_at,
            "raw_payload": {
                "account_ref": holding.account_ref,
                "classification": "fixture-open",
                "label": holding.label,
                BOOK_ATTRIBUTE: holding.book,
            },
        }
    )


# =============================================================================
# What a caller observes, as data
# =============================================================================

#: The five observables Dave named, as this module spells them.
RESPONSE = "response"
REFUSAL = "refusal"
REFERENCE = "reference"
COMPOSITE = "composite"
RECORD = "record"
CHANNELS = (RESPONSE, REFUSAL, REFERENCE, COMPOSITE, RECORD)


@dataclass
class Observation:
    """Everything one question showed, channel by channel.

    ``channels`` maps a channel name to a JSON-shaped value; a channel this
    door cannot carry is absent rather than empty. ``raw`` keeps the outcome
    for the failure message and for reading references back.
    """

    channels: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


def diff_paths(left: Any, right: Any, prefix: str = "") -> set[str]:
    """Every dotted path at which two JSON-shaped values differ (a length change is ``[len]``)."""
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        found: set[str] = set()
        for key in set(left) | set(right):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                found.add(path)
            else:
                found |= diff_paths(left[key], right[key], path)
        return found
    if isinstance(left, list | tuple) and isinstance(right, list | tuple):
        if len(left) != len(right):
            return {f"{prefix}[len]"}
        found = set()
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            found |= diff_paths(a, b, f"{prefix}[{index}]")
        return found
    return set() if left == right else {prefix or "<root>"}


def jsonable(value: Any) -> Any:
    """A JSON round trip, so pydantic and plain values compare alike."""
    return json.loads(json.dumps(value, default=str))


def _record_at(store: Any, reference: str) -> DecisionReplayRecord:
    """The record behind ``reference`` (a URI or a content address), read as an auditor would."""
    address = store.resolve_uri(uri=reference) if reference.startswith("ccf-artifact://") else reference
    return DecisionReplayRecord.model_validate_json(store.get(content_address=address))


def _reference_parts(uri: str) -> dict[str, str]:
    """``ccf-artifact://{tenant}/{class}/{name}@{version}`` split into its segments."""
    head, _, version = uri.partition("@")
    tenant, artifact_class, name = head.removeprefix("ccf-artifact://").split("/", 2)
    return {"tenant": tenant, "artifact_class": artifact_class, "name": name, "version": version}


# =============================================================================
# Deployments — the common surface every shape builds
# =============================================================================


@dataclass
class Deployment:
    """One deployment a question is asked of, whatever shape built it.

    ``resolve`` is the door seam (:class:`~ccf_runtime.mcp.egress.ProductResolverProtocol`);
    ``ask`` is the in-process call a deployment's own code makes. ``store`` is
    the ONE artifact store its records land in, ``recorder`` its ONE refusal
    recorder; the doors are composed over exactly these.
    """

    tenant: str
    product_class: str
    version: str
    role: str
    control_plane: Any
    store: Any
    erasure_index: Any
    erasure_trust: Any
    recorder: Any
    resolve: Callable[..., Any]
    ask: Callable[[str, Mapping[str, Any] | None], Any]
    close: Callable[[], None]
    notes: dict[str, Any] = field(default_factory=dict)


#: The owner-read allowlist's documented public name (Dave, Q12; lane
#: ``378-s020record`` PROPOSAL §4.2): a field of the tenant's entitlement policy
#: listing the classes whose records cross an evidence door to their owners.
EVIDENCE_ALLOWLIST_FIELD = "evidence_readable_classes"


def evidence_allowlist_exists() -> bool:
    """Whether the owner-read allowlist exists under its documented name."""
    return EVIDENCE_ALLOWLIST_FIELD in ProductEntitlementPolicy.model_fields


def entitlement_policy(
    *, tenant: str, product_class: str, role: str, evidence_readable: bool = False
) -> ProductEntitlementPolicy:
    """The asker and one other principal, both granted the class at ``full``.

    ``full`` is the strictest level to compare at: every refusal discloses its
    cause, and ``D-IMPL-345`` lets the owner read its own record back.
    ``evidence_readable`` lists the class on the owner-read allowlist, and is
    honored only where that knob exists (``evidence_allowlist_exists``).
    """
    grant = ProductEntitlementGrant(
        permitted_schema_names=frozenset({product_class}),
        permitted_roles=frozenset({role}),
        disclosure_level=DISCLOSURE_FULL,
    )
    extra: dict[str, Any] = {}
    if evidence_readable and evidence_allowlist_exists():
        extra[EVIDENCE_ALLOWLIST_FIELD] = frozenset({product_class})
    return ProductEntitlementPolicy(
        tenant_id=tenant,
        policy_version="1.0.0",
        principals={ASKER: grant, OTHER: grant},
        disclosure_level=DISCLOSURE_MINIMAL,
        **extra,
    )


def register_entitlement(
    registry: Any, *, tenant: str, product_class: str, role: str, evidence_readable: bool = False
) -> None:
    register_typed_at_composition(
        registry,
        product_entitlement_key(tenant_id=tenant),
        entitlement_policy(
            tenant=tenant, product_class=product_class, role=role, evidence_readable=evidence_readable
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )


# =============================================================================
# The paved road: subject-keyed and population-shaped acquisition
# =============================================================================


class SubjectKeyedSource:
    """The paved road's ``acquire``: claims for the asked subject only (``D-IMPL-371``'s shape)."""

    def __init__(self, holdings: Mapping[str, Holding]) -> None:
        self._holdings = dict(holdings)
        self.asked: list[str] = []

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        self.asked.append(context.request.subject)
        holding = self._holdings.get(context.request.subject)
        if holding is None:
            return ()
        return (envelope_for(holding, tenant=context.tenant_id, ingested_at=context.instant),)


class PopulationSource:
    """The paved road's ``acquire``: the source's whole population, whatever is asked."""

    def __init__(self, holdings: Mapping[str, Holding]) -> None:
        self._holdings = dict(holdings)
        self.asked: list[str] = []

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        self.asked.append(context.request.subject)
        return tuple(
            envelope_for(holding, tenant=context.tenant_id, ingested_at=context.instant)
            for _uri, holding in sorted(self._holdings.items())
        )


#: The explicit population-fetch mode's documented public name (Dave, Q7; lane
#: ``378-s020design`` PROPOSAL, channel 1): ``PopulationAcquireProtocol`` on the
#: paved road, handed to ``open_product(population=...)``.
POPULATION_PROTOCOL = "PopulationAcquireProtocol"


def population_mode_exists() -> bool:
    """Whether the explicit population-fetch mode exists under its documented name."""
    import ccf.products.product as product  # noqa: PLC0415

    return hasattr(product, POPULATION_PROTOCOL)


class PopulationHalf:
    """The declared population half: the source's whole population, handed no subject.

    It reads only the tenant and the instant off the context it is handed —
    the documented context carries no request — so nothing about the question
    can reach it.
    """

    def __init__(self, holdings: Mapping[str, Holding]) -> None:
        self._holdings = dict(holdings)

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        return tuple(
            envelope_for(holding, tenant=context.tenant_id, ingested_at=context.instant)
            for _uri, holding in sorted(self._holdings.items())
        )


class ReferenceAssess:
    """The paved road's ``assess``, scored by the SDK's reference scorer over the view it is handed.

    The paved fixture's own ``assess`` returns one constant assessment, so on
    that road debt could never differ and a leak carried by debt would be
    invisible. Here decay is measured over the actual view against the booted
    λ_c table and D_c profile, exactly as the low road's reference scorer
    measures it; completeness and consistency are the declared fixture factors.
    """

    def __call__(self, context: Any) -> Any:
        from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor  # noqa: PLC0415
        from tests.products.test_evidence_derived_debt import DECLARED  # noqa: PLC0415

        return AssemblyDebtScorer(
            table=context.half_life,
            profile=context.profile,
            completeness=DeclaredFactor(value=DECLARED),
            semantic_consistency=DeclaredFactor(value=DECLARED),
        ).score_at(
            view=context.view,
            evidence=context.evidence,
            decided_at=context.decided_at,
            children=context.children,
        )


def paved_document(anchor: str) -> dict[str, Any]:
    """The paved fixture's config under ``anchor``, with the ``book`` attribute admitted.

    The λ_c row decays from ``valid-from`` under both anchors, as the low road's
    table does: an evidence-anchored class requires it (``D-IMPL-341`` R-3),
    and under ``from_decision`` it is what makes an observation's age count —
    the paved road stamps ingestion at the question's own instant, so decay from
    ingestion would read every claim as brand new. Test-side variant only.
    """
    from tests.products.test_paved_road import _config  # noqa: PLC0415

    document = copy.deepcopy(_config())
    document["product_class"]["ttl_anchor"] = anchor
    for row in document["half_life"].values():
        row["decay_basis"] = "valid-from"
    for rule in document["resolution"]["entity_rules"]:
        rule["attribute_keys"] = [*rule["attribute_keys"], BOOK_ATTRIBUTE]
    return document


def open_paved(
    base: pathlib.Path,
    *,
    anchor: str,
    acquire: Any,
    project: Any,
    document: dict[str, Any] | None = None,
    evidence_readable: bool = False,
    **overrides: Any,
) -> Deployment:
    """Open the paved fixture product under ``base``: one store, one recorder, one Control Plane."""
    from tests.deployment.test_replay_binding import PRODUCT_CLASS, PRODUCT_VERSION, ROLE, TENANT  # noqa: PLC0415
    from tests.products.paved_fixture import granted_control_plane  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT, _open, _write_tree  # noqa: PLC0415
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER  # noqa: PLC0415

    base.mkdir(parents=True, exist_ok=True)
    root = _write_tree(base, config=document if document is not None else paved_document(anchor))
    registry = granted_control_plane(root)
    register_entitlement(
        registry, tenant=TENANT, product_class=PRODUCT_CLASS, role=ROLE, evidence_readable=evidence_readable
    )
    opened = _open(
        root, base / "scratch", acquire=acquire, project=project, control_plane=registry,
        assess=ReferenceAssess(), **overrides,
    )

    def ask(subject: str, parameters: Mapping[str, Any] | None = None) -> Any:
        return opened.answer(
            opened.question(
                subject=subject, asked_at=ASKED_AT, intent=INTENT, freshness=FRESHNESS,
                parameters=dict(parameters) if parameters is not None else {THRESHOLD_PARAMETER: THRESHOLD_VALUE},
            )
        )

    return Deployment(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        role=ROLE,
        control_plane=opened.control_plane,
        store=opened.artifact_store,
        erasure_index=opened.erasure_index,
        erasure_trust=opened.erasure_trust,
        recorder=opened.refusal_recorder,
        resolve=opened.resolve,
        ask=ask,
        close=opened.close,
        notes={"opened": opened},
    )


# =============================================================================
# The doors
# =============================================================================

#: Where every question is asked as of, and what each door's clock reads.
#: The paved road's own fixture instants, so a record's ``served_at`` is pinned.
def asked_at() -> datetime:
    from tests.products.test_paved_road import ASKED_AT  # noqa: PLC0415

    return ASKED_AT


def door_clock() -> datetime:
    return asked_at() + timedelta(minutes=7)


def threshold_parameter() -> str:
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER  # noqa: PLC0415

    return THRESHOLD_PARAMETER


def default_parameters() -> dict[str, Any]:
    """The one declared parameter every question carries."""
    return {threshold_parameter(): THRESHOLD_VALUE}


#: A parameter no class in this module declares: the question that carries it
#: is REFUSED by the resolver's request contract (``undeclared-parameter``),
#: before anything is acquired. The refusal-code instrument.
UNDECLARED_PARAMETER = "sec020_proof_undeclared"


def violating_parameters() -> dict[str, Any]:
    return {**default_parameters(), UNDECLARED_PARAMETER: 1}


IN_PROCESS = "in_process"
HTTP = "http"
MCP = "mcp"
DOORS = (IN_PROCESS, HTTP, MCP)

#: Volatile headers a transport adds that carry nothing about the answer.
_VOLATILE_HEADERS = frozenset({"date", "server"})


def _recorded_cause(deployment: Deployment, reference: str | None) -> Any:
    """The refusal the fabric RECORDED (dimension 5's internal envelope), or ``None`` if served.

    Dave named the recorded cause among the refusal-code observables. It is
    read from the deployment's own store, as an auditor reads it.
    """
    if reference is None:
        return None
    record = _record_at(deployment.store, reference)
    internal = record.content_generation_path.assembly_refusal
    try:
        dumped = json.loads(internal)
    except ValueError:
        # The positive sentinel a served decision records
        # (``ccf.replay.record.NO_ASSEMBLY_REFUSAL``), compared as itself.
        return internal
    if isinstance(dumped, dict):
        dumped.pop("replay_reference", None)
    return dumped


def observe_in_process(
    deployment: Deployment, subject: str, *, parameters: Mapping[str, Any] | None = None
) -> Observation:
    """Ask ``subject`` in process, as the deployment's own code does."""
    try:
        outcome = deployment.ask(subject, parameters)
    except Exception as raised:  # noqa: BLE001 — an exception is an observation too
        shape = {"outcome": "raised", "type": type(raised).__name__, "message": str(raised)}
        return Observation(channels={RESPONSE: shape, REFUSAL: shape, REFERENCE: shape}, raw=raised)
    if isinstance(outcome, ServedProduct):
        reference = outcome.replay_ref.uri
        served = outcome.model_dump(mode="json")
        vessel = served.pop("product")
        return Observation(
            channels={
                RESPONSE: {"outcome": "served", "vessel": vessel},
                REFUSAL: {"outcome": "served", "recorded_cause": _recorded_cause(deployment, reference)},
                # Every member of the in-memory answer but the vessel: the
                # replay reference today, and any reference added beside it.
                REFERENCE: served,
            },
            raw=outcome,
        )
    assert isinstance(outcome, RefusalEnvelope), f"neither served nor refused: {outcome!r}"
    envelope = outcome.model_dump(mode="json")
    reference = envelope.pop("replay_reference", None)
    return Observation(
        channels={
            RESPONSE: {"outcome": "refused", "envelope": envelope},
            REFUSAL: {
                "outcome": "refused",
                "kind": outcome.kind,
                "reason": outcome.reason,
                "key": outcome.key,
                "recorded_cause": _recorded_cause(deployment, reference),
            },
            REFERENCE: {"replay_reference": reference},
        },
        raw=outcome,
    )


# --- HTTP --------------------------------------------------------------------


def _token_source(deployment: Deployment) -> Any:
    from tests.http_api.gate_fixtures import SCOPE_EVERYTHING, tenanted_source  # noqa: PLC0415

    return tenanted_source(
        {ASKER_TOKEN: (ASKER, (SCOPE_EVERYTHING,)), OTHER_TOKEN: (OTHER, (SCOPE_EVERYTHING,))},
        tenant=deployment.tenant,
    )


def _entitlement_source(deployment: Deployment) -> Any:
    from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource  # noqa: PLC0415

    return ControlPlaneProductEntitlementSource(
        control_plane=deployment.control_plane, clock=door_clock
    )


def http_app(deployment: Deployment) -> Any:
    """The shipped HTTP API over the deployment's ONE store, recorder and Control Plane."""
    from ccf_runtime.http_api.app import create_app  # noqa: PLC0415
    from ccf_runtime.http_api.auth import BearerTokenAuth  # noqa: PLC0415
    from ccf_runtime.http_api.dependencies import ApiDependencies  # noqa: PLC0415
    from tests.http_api.gate_fixtures import wide_authorizer  # noqa: PLC0415

    role = deployment.role
    return create_app(
        ApiDependencies(
            control_plane=deployment.control_plane,
            artifact_store=deployment.store,
            erasure_index=deployment.erasure_index,
            erasure_trust=deployment.erasure_trust,
            product_resolver=deployment.resolve,
        ),
        auth=BearerTokenAuth(token_source=_token_source(deployment)),
        authorizer=wide_authorizer(tenant=deployment.tenant, key=f"{deployment.tenant}/sec020-proof-scope-mapping"),
        product_entitlement=_entitlement_source(deployment),
        perspective_resolver=lambda *, grant, tenant, requested_role: Perspective(
            principal_id=grant.client_id, role=role
        ),
        refusal_recorder=deployment.recorder,
        replay_record_product_class=None,
    )


def http_call(app: Any, method: str, url: str, *, token: str, **kwargs: Any) -> httpx.Response:
    """One in-process ASGI request, never hosted."""

    async def go() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://fabric.invalid"
        ) as client:
            return await client.request(method, url, headers={"Authorization": f"Bearer {token}"}, **kwargs)

    return asyncio.run(go())


def _http_shape(response: httpx.Response, *, drop: tuple[str, ...] = ()) -> dict[str, Any]:
    """Status, every header but the volatile ones (and ``drop``), and the decoded body."""
    headers = {
        name.lower(): value
        for name, value in response.headers.items()
        if name.lower() not in _VOLATILE_HEADERS and name.lower() not in drop
    }
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    return {"status": response.status_code, "headers": headers, "body": body}


def _decoded_echo(headers: Mapping[str, str]) -> Any:
    raw = headers.get("x-ccf-request-echo")
    if raw is None:
        return None
    return json.loads(base64.urlsafe_b64decode(raw.encode("ascii")))


def observe_http(
    deployment: Deployment,
    subject: str,
    *,
    app: Any | None = None,
    parameters: Mapping[str, Any] | None = None,
) -> Observation:
    """Ask ``subject`` through the HTTP product route, as the asker."""
    app = app if app is not None else http_app(deployment)
    response = http_call(
        app,
        "GET",
        f"/product/{deployment.tenant}/{deployment.product_class}/{deployment.version}",
        token=ASKER_TOKEN,
        params={
            "subject": subject,
            "intent": INTENT,
            "freshness": FRESHNESS,
            "asked_at": asked_at().isoformat(),
            "parameters": json.dumps(dict(parameters) if parameters is not None else default_parameters()),
        },
    )
    shape = _http_shape(response, drop=("x-ccf-replay-ref",))
    header_ref = response.headers.get("x-ccf-replay-ref")
    body = shape["body"]
    body_ref = None
    if isinstance(body, dict) and isinstance(body.get("refusal"), dict):
        body_ref = body["refusal"].pop("replay_reference", None)
    reference = header_ref or body_ref
    refusal: dict[str, Any] = {"status": response.status_code}
    if isinstance(body, dict) and isinstance(body.get("refusal"), dict):
        refusal.update(
            outcome="refused",
            kind=body["refusal"].get("kind"),
            reason=body["refusal"].get("reason"),
            key=body["refusal"].get("key"),
            refusal_type=body.get("refusal_type"),
        )
    elif response.status_code == 200:
        refusal["outcome"] = "served"
    else:
        refusal.update(outcome="error", body=body)
    refusal["recorded_cause"] = _recorded_cause(deployment, reference) if reference else None
    shape["echo"] = _decoded_echo(response.headers)
    return Observation(
        channels={
            RESPONSE: shape,
            REFUSAL: refusal,
            REFERENCE: {"x-ccf-replay-ref": header_ref, "refusal.replay_reference": body_ref},
        },
        raw={"response": response, "reference": reference, "app": app},
    )


# --- MCP ---------------------------------------------------------------------

MCP_SCOPE = "ccf:sec020-proof"
MCP_BASE_URL = "http://127.0.0.1:8131"


def mcp_product_server(deployment: Deployment) -> Any:
    """The shipped MCP product door over the deployment's resolver and recorder."""
    from mcp.server.auth.settings import AuthSettings  # noqa: PLC0415
    from pydantic import AnyHttpUrl  # noqa: PLC0415

    from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant  # noqa: PLC0415
    from ccf_runtime.mcp.egress import build_egress_server  # noqa: PLC0415
    from tests.mcp.guarded_servers import wide_authorizer  # noqa: PLC0415

    role = deployment.role
    return build_egress_server(
        server_name=f"{deployment.tenant}-sec020-proof",
        resolver=deployment.resolve,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(
                grants={
                    ASKER_TOKEN: TokenGrant(
                        client_id=ASKER, scopes=(MCP_SCOPE,), tenants=frozenset({deployment.tenant})
                    )
                }
            )
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{MCP_BASE_URL}/mcp"),
            required_scopes=[MCP_SCOPE],
        ),
        authorizer=wide_authorizer(scopes=(MCP_SCOPE,)),
        entitlement_source=_entitlement_source(deployment),
        perspective_resolver=lambda *, grant, tenant, requested_role: Perspective(
            principal_id=grant.client_id, role=role
        ),
        refusal_recorder=deployment.recorder,
        expose_product_tool=True,
        product_tool_description="Ask the SEC-020 proof deployment a question.",
    )


def mcp_drive(server: Any, operation: Callable[[Any], Any], *, token: str = ASKER_TOKEN) -> Any:
    """Run one MCP client operation against ``server`` over an in-process ASGI transport."""
    from ccf.mcp.client import run_with_session  # noqa: PLC0415
    from ccf.mcp.errors import McpServerUnreachable  # noqa: PLC0415

    app = server.streamable_http_app()

    async def go() -> Any:
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=MCP_BASE_URL,
                    headers={"Authorization": f"Bearer {token}"},
                )

            try:
                return await run_with_session(
                    url=f"{MCP_BASE_URL}/mcp", operation=operation, http_client_factory=factory
                )
            except McpServerUnreachable as refused:
                return {"unreachable": str(refused)}

    return asyncio.run(go())


def observe_mcp(
    deployment: Deployment, subject: str, *, parameters: Mapping[str, Any] | None = None
) -> Observation:
    """Ask ``subject`` through the MCP product tool, as the asker."""
    from mcp.types import TextContent  # noqa: PLC0415

    from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL  # noqa: PLC0415

    parameters = dict(parameters) if parameters is not None else default_parameters()
    arguments = {
        "tenant": deployment.tenant,
        "product_class": deployment.product_class,
        "version": deployment.version,
        "request": canonical_bytes(
            WireRequest(
                product_id=deployment.product_class,
                parameters=parameters,
                temporal_boundary=asked_at(),
            )
        ).decode("utf-8"),
        "subject": subject,
        "intent": INTENT,
        "freshness": FRESHNESS,
        "asked_at": asked_at().isoformat(),
        "parameters": parameters,
    }

    async def operation(session: Any) -> Any:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
        return {
            "is_error": bool(result.isError),
            "text": " | ".join(c.text for c in result.content if isinstance(c, TextContent)),
        }

    called = mcp_drive(mcp_product_server(deployment), operation)
    if "unreachable" in called:
        shape = {"outcome": "unreachable", "detail": called["unreachable"]}
        return Observation(channels={RESPONSE: shape, REFUSAL: shape, REFERENCE: shape}, raw=called)
    try:
        outcome: Any = json.loads(called["text"])
    except ValueError:
        outcome = called["text"]
    reference = None
    envelope_reference = None
    refusal: dict[str, Any] = {"is_error": called["is_error"]}
    if isinstance(outcome, dict):
        reference = outcome.pop("replay_ref", None)
        envelope = outcome.get("refusal")
        if isinstance(envelope, dict):
            envelope_reference = envelope.pop("replay_reference", None)
            refusal.update(
                outcome="refused",
                kind=envelope.get("kind"),
                reason=envelope.get("reason"),
                key=envelope.get("key"),
            )
        else:
            refusal["outcome"] = "served"
    else:
        refusal.update(outcome="error", text=outcome)
    refusal["recorded_cause"] = _recorded_cause(deployment, reference) if reference else None
    return Observation(
        channels={
            RESPONSE: {"is_error": called["is_error"], "outcome": outcome},
            REFUSAL: refusal,
            REFERENCE: {"door_outcome.replay_ref": reference, "refusal.replay_reference": envelope_reference},
        },
        raw={"called": called, "reference": reference},
    )


# =============================================================================
# Authorized record reads
# =============================================================================


def _normalize_presented(value: Any, presented: tuple[str, ...]) -> Any:
    """Replace every string the caller itself presented with a placeholder.

    A refusal of a dereference echoes the reference it was asked for in its
    request identity; that echo is the caller's own input, not something the
    fabric revealed, so it is normalized before two refusals are compared.
    """
    if isinstance(value, str):
        for index, text in enumerate(presented):
            if text and text in value:
                value = value.replace(text, f"<presented-{index}>")
        return value
    if isinstance(value, dict):
        return {key: _normalize_presented(item, presented) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_presented(item, presented) for item in value]
    return value


def http_record_reads(deployment: Deployment, reference: str | None, *, app: Any) -> dict[str, Any]:
    """Every governed HTTP read of the record behind ``reference``, as the owner and as another principal.

    The three routes ``D-IMPL-345`` governs: ``/replay/resolutions`` by URI,
    ``/replay/decisions`` by content address, ``/artifact/{address}`` for the
    bytes. The address is the URI's version segment — what a caller holding
    only the reference has.
    """
    if reference is None:
        return {"reference": None}
    address = _reference_parts(reference)["version"] if reference.startswith("ccf-artifact://") else reference
    presented = (reference, address)
    reads: dict[str, Any] = {}
    for who, token in (("owner", ASKER_TOKEN), ("other-principal", OTHER_TOKEN)):
        for route, url, params in (
            ("replay.resolutions", "/replay/resolutions", {"uri": reference}),
            ("replay.decisions", "/replay/decisions", {"content_address": address}),
            ("artifact", f"/artifact/{address}", None),
        ):
            response = http_call(app, "GET", url, token=token, params=params)
            reads[f"{who}:{route}"] = _normalize_presented(_http_shape(response), presented)
    return reads


def composite_rows(deployment: Deployment, reference: str | None) -> Any:
    """A composite decision's child rows as RECORDED (dimension 5), read as an auditor would.

    Dave named composite paths among the observables: what a composite answered
    is on the response channel at every door; which children it asked, what
    they answered and how admission judged them is on the record.
    """
    if reference is None:
        return None
    record = _record_at(deployment.store, reference)
    return [row.model_dump(mode="json") for row in record.content_generation_path.child_resolutions]


# =============================================================================
# The low road: a fabric booted per question from the deployment's documents
# =============================================================================


def low_road_documents(
    root: pathlib.Path,
    *,
    anchor: str,
    required: list[str],
    similarity_query: str | None = None,
    composite: bool = False,
    child_anchor: str = FROM_DECISION,
) -> pathlib.Path:
    """Write the ``tests/deployment`` fixture deployment under ``root``; return the manifest.

    The class's anchor and operators are stated; the λ_c row is ``valid-from``
    so both anchors resolve; the resolution rule admits the ``book``
    attribute; with ``similarity_query`` the similarity operator ranks the
    account class's ``label`` against it; with ``composite`` the class requires
    the composite fixture's child class, which is declared beside it.
    Test-side document variants only (CINV-01).
    """
    from tests.deployment.conftest import (  # noqa: PLC0415
        ARTIFACT_SET,
        HALF_LIFE_KEY,
        PRODUCT_CLASS_KEY,
        RESOLUTION_SPEC_KEY,
        SIMILARITY_KEY,
        manifest_document,
        write_artifact,
    )
    from tests.products.test_resolver_seam import (  # noqa: PLC0415
        DEBT_PROFILE_KEY,
        OBLIGATION_ON_OK,
        REQUEST_CONTRACT_CLASS_ID,
        REQUEST_CONTRACT_DOCUMENT,
        REQUEST_CONTRACT_KEY,
    )
    from tests.products.test_withheld_is_indistinguishable_from_absent import (  # noqa: PLC0415
        _table_document,
    )

    root.mkdir(parents=True)
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        document = copy.deepcopy(document)
        if key == PRODUCT_CLASS_KEY:
            document = {**document, "required_operator_keys": required, "ttl_anchor": anchor}
            if composite:
                from tests.products.composite_fixture import _parent_requires  # noqa: PLC0415

                document["requires"] = _parent_requires()
        if key == HALF_LIFE_KEY:
            document = _table_document()
        if key == RESOLUTION_SPEC_KEY:
            for rule in document["entity_rules"]:
                if rule.get("entity_class") == "account":
                    rule["attribute_keys"] = [*rule["attribute_keys"], BOOK_ATTRIBUTE]
        if key == SIMILARITY_KEY and similarity_query is not None:
            document = {
                **document,
                "query": similarity_query,
                "minimum_score_percent": 50,
                "ranked_entity_classes": ["account"],
                "similarity_corpus_attribute_by_class": {"account": "label"},
            }
        write_artifact(root, filename, document)
    write_artifact(root, "request-contract.yaml", copy.deepcopy(REQUEST_CONTRACT_DOCUMENT))
    extra = [("request-contract.yaml", REQUEST_CONTRACT_KEY, REQUEST_CONTRACT_CLASS_ID, "load")]
    if composite:
        from tests.products.provider_boot import (  # noqa: PLC0415
            CHILD_CLASS_KEY,
            CHILD_REQUEST_CONTRACT_KEY,
            child_product_class,
            child_request_contract,
        )

        child = child_product_class()
        child["required_operator_keys"] = ["traversal.typed-neighborhood"]
        child["ttl_anchor"] = child_anchor
        write_artifact(root, "product-class-child.yaml", child)
        write_artifact(root, "request-contract-child.yaml", child_request_contract())
        write_artifact(
            root,
            "debt-profile.yaml",
            {
                "semver": "1.0.0",
                "risk_sensitivity": "1",
                "forced_llm_threshold": "0.30",
                "fail_closed_threshold": "0.70",
                "signal_obligations": [{"signal": "ok", "obligation_ref": OBLIGATION_ON_OK}],
            },
        )
        extra += [
            ("product-class-child.yaml", CHILD_CLASS_KEY, "ccf.product-class", "register"),
            ("request-contract-child.yaml", CHILD_REQUEST_CONTRACT_KEY, REQUEST_CONTRACT_CLASS_ID, "load"),
            ("debt-profile.yaml", DEBT_PROFILE_KEY, "ccf.debt-profile", "register"),
        ]
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        *(
            {"path": path, "key": key, "class_id": class_id, "role": role, "registration": "typed"}
            for path, key, class_id, role in extra
        ),
    ]
    return write_artifact(root, "manifest.yaml", body)


@dataclass
class LowRoadSite:
    """What a low-road deployment holds across questions: one store, one recorder, one plane.

    A fabric is booted per question from ``manifest`` (the paved road's own
    rule, ``CP03C-F-02``), unless the shape is the one that reuses a fabric.
    """

    root: pathlib.Path
    manifest: pathlib.Path
    control_plane: Any
    store: Any
    recorder: Any
    erasure_index: Any
    erasure_trust: Any
    counter: int = 0

    def boot(self, envelopes: tuple[SignalEnvelope, ...]) -> Any:
        """A fresh fabric from the deployment's documents, holding ``envelopes``."""
        from ccf.deployment import load_and_boot  # noqa: PLC0415

        self.counter += 1
        fabric = load_and_boot(
            self.manifest,
            registry=self.control_plane,
            connection={"database_path": str(self.root / f"graph-{self.counter}.sqlite3")},
        )
        for envelope in envelopes:
            fabric.handle.worker.ingest(envelope)
        return fabric


def low_road_site(
    root: pathlib.Path,
    manifest: pathlib.Path,
    *,
    extra_classes: tuple[str, ...] = (),
    evidence_readable: bool = False,
) -> LowRoadSite:
    """The deployment-scoped pieces: the store, the recorder disclosing at the policy's level."""
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415
    from ccf.erasure import erasure_index_at  # noqa: PLC0415
    from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS  # noqa: PLC0415
    from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource  # noqa: PLC0415
    from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust, declaring_store  # noqa: PLC0415
    from tests.deployment.conftest import TENANT  # noqa: PLC0415
    from tests.http_api.composition_authority import refusal_recorder  # noqa: PLC0415
    from tests.products.test_resolver_seam import PERSPECTIVE, PRODUCT_CLASS, QUERY_PIN_CLASS, REPLAY_RECORD_CLASS  # noqa: PLC0415

    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=TENANT)
    register_entitlement(
        control_plane, tenant=TENANT, product_class=PRODUCT_CLASS, role=PERSPECTIVE.role,
        evidence_readable=evidence_readable,
    )
    store = declaring_store(
        root / "artifacts", REPLAY_RECORD_CLASS, QUERY_PIN_CLASS, ADMITTED_CHILD_CONTRACT_CLASS, *extra_classes
    )
    source = ControlPlaneProductEntitlementSource(control_plane=control_plane, clock=door_clock)
    recorder = refusal_recorder(
        control_plane,
        store=store,
        tenant=TENANT,
        replay_record_class=REPLAY_RECORD_CLASS,
        disclosure_level_for=source.disclosure_level_for,
    )
    return LowRoadSite(
        root=root,
        manifest=manifest,
        control_plane=control_plane,
        store=store,
        recorder=recorder,
        erasure_index=erasure_index_at(root / "erasure"),
        erasure_trust=declared_erasure_trust(TENANT),
    )


def low_road_resolver(
    site: LowRoadSite,
    fabric: Any,
    *,
    plan_factory: Any,
    acquisition: Any,
    operator_parameter_keys: tuple[str, ...],
    composite_children: Any = None,
    product_class_key: str | None = None,
    request_contract_key: str | None = None,
) -> Any:
    """The shipped :class:`~ccf.products.resolver.GovernedResolver` over one fabric."""
    from ccf.halflife.assessment import NO_SOURCE_REFRESH_RECENCY  # noqa: PLC0415
    from ccf.products.constraints import ReferencePolicyConstraintResolver  # noqa: PLC0415
    from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor  # noqa: PLC0415
    from ccf.products.resolver import GovernedResolver  # noqa: PLC0415
    from tests.deployment.conftest import HALF_LIFE_KEY, POLICY_BUNDLE_KEY, PRODUCT_CLASS_KEY, TENANT  # noqa: PLC0415
    from tests.products.test_evidence_derived_debt import DECLARED, profile  # noqa: PLC0415
    from tests.products.test_resolver_seam import (  # noqa: PLC0415
        MAX_TTL_SECONDS,
        QUERY_PIN_CLASS,
        REPLAY_RECORD_CLASS,
        REQUEST_CONTRACT_KEY,
    )
    from tests.products.test_withheld_is_indistinguishable_from_absent import (  # noqa: PLC0415
        SERVED_AT,
        WINDOW_SECONDS,
        _table,
    )

    return GovernedResolver(
        composite_children=composite_children,
        acquisition=acquisition,
        packaging_trace=None,
        half_life_key=HALF_LIFE_KEY,
        admission_clock=lambda: SERVED_AT,
        decision_instant_parameter=None,
        source_refresh_recency=NO_SOURCE_REFRESH_RECENCY,
        fabric=fabric,
        control_plane=site.control_plane,
        product_class_key=product_class_key or PRODUCT_CLASS_KEY,
        request_contract_key=request_contract_key or REQUEST_CONTRACT_KEY,
        operator_parameter_keys=operator_parameter_keys,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        debt_profile_key=None,
        plan_factory=plan_factory,
        debt_scorer=AssemblyDebtScorer(
            table=_table(),
            profile=profile(),
            completeness=DeclaredFactor(value=DECLARED),
            semantic_consistency=DeclaredFactor(value=DECLARED),
        ),
        product_gate=None,
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=site.control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
        capabilities=(),
        refusal_recorder=site.recorder,
        artifact_store=site.store,
        replay_record_class=REPLAY_RECORD_CLASS,
        query_pin_class=QUERY_PIN_CLASS,
        max_ttl_seconds=MAX_TTL_SECONDS,
        product_ttl_seconds=WINDOW_SECONDS,
    )


def low_road_request(subject: str, parameters: Mapping[str, Any] | None = None) -> ProductRequest:
    from tests.products.test_resolver_seam import ASKED_AT, PRODUCT_CLASS, PRODUCT_VERSION, THRESHOLD_PARAMETER  # noqa: PLC0415

    return ProductRequest(
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        subject=subject,
        intent=INTENT,
        freshness=FRESHNESS,
        asked_at=ASKED_AT,
        parameters=dict(parameters) if parameters is not None else {THRESHOLD_PARAMETER: THRESHOLD_VALUE},
    )


def low_road_deployment(
    site: LowRoadSite,
    *,
    answer: Callable[..., Any],
    close: Callable[[], None] = lambda: None,
) -> Deployment:
    """A :class:`Deployment` over ``answer(perspective=, request=)``, which boots what it needs."""
    from tests.deployment.conftest import TENANT  # noqa: PLC0415
    from tests.products.test_resolver_seam import PERSPECTIVE, PRODUCT_CLASS, PRODUCT_VERSION  # noqa: PLC0415

    def resolve(*, tenant: str, product_class: str, version: str, perspective: Perspective, request: ProductRequest | None) -> Any:
        assert request is not None, "the doors in this module always carry a request"
        return answer(perspective=perspective, request=request)

    return Deployment(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        role=PERSPECTIVE.role,
        control_plane=site.control_plane,
        store=site.store,
        erasure_index=site.erasure_index,
        erasure_trust=site.erasure_trust,
        recorder=site.recorder,
        resolve=resolve,
        ask=lambda subject, parameters=None: answer(
            perspective=PERSPECTIVE, request=low_road_request(subject, parameters)
        ),
        close=close,
    )


class SubjectKeyedSeam:
    """A low-road acquisition seam keyed on the subject: ingests what the source holds for it."""

    def __init__(self, fabric: Any, holdings: Mapping[str, Holding], *, tenant: str, ingested_at: datetime) -> None:
        self._fabric = fabric
        self._holdings = dict(holdings)
        self._tenant = tenant
        self._ingested_at = ingested_at
        self.asked: list[str] = []

    def __call__(self, *, request: ProductRequest, perspective: Any) -> None:
        self.asked.append(request.subject)
        holding = self._holdings.get(request.subject)
        if holding is not None:
            self._fabric.handle.worker.ingest(
                envelope_for(
                    holding, tenant=self._tenant, ingested_at=self._ingested_at,
                    envelope_id=f"acquired-{holding.account_ref}",
                )
            )


# =============================================================================
# The source shapes
# =============================================================================

#: When each source observed what it holds. The subject was observed one minute
#: before the question, so a SERVED subject is inside an evidence-anchored window
#: on both roads; the sibling and the fixed child subject half an hour earlier,
#: so a walk that reaches the subject and one that does not score differently.
def subject_holding() -> Holding:
    return Holding(
        account_ref=SUBJECT_REF, book=RESTRICTED_BOOK, label="subject label",
        observed_at=asked_at() - timedelta(minutes=1),
    )


def sibling_holding(*, label: str = "sibling label") -> Holding:
    return Holding(
        account_ref=SIBLING_REF, book=OPEN_BOOK, label=label,
        observed_at=asked_at() - timedelta(minutes=30),
    )


def fixed_holding() -> Holding:
    return Holding(
        account_ref=FIXED_REF, book=OPEN_BOOK, label="fixed label",
        observed_at=asked_at() - timedelta(minutes=30),
    )


#: The pre-load instant on the low road (the SEC-020 controls' own).
LOW_ROAD_INGESTED_AT = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)

SUBJECT_KEYED = "subject_keyed"
NO_ACQUISITION = "no_acquisition"
POPULATION = "population"
SIMILARITY = "similarity_refreshed"
COMPOSITE_SUBJECT_CHILD = "composite_subject_child"
COMPOSITE_FIXED_CHILD = "composite_fixed_child"
REUSED_FABRIC = "reused_fabric"
REUSED_STORE = "reused_store"
SHAPES = (
    SUBJECT_KEYED,
    NO_ACQUISITION,
    POPULATION,
    SIMILARITY,
    COMPOSITE_SUBJECT_CHILD,
    COMPOSITE_FIXED_CHILD,
    REUSED_FABRIC,
    REUSED_STORE,
)
#: The two shapes whose point is the SEQUENCE: a question about the subject, then one about an unheld identifier.
REUSED_SHAPES = (REUSED_FABRIC, REUSED_STORE)

#: Shapes that need a public knob that does not exist yet on ``e9e5e2cd``; each
#: maps to the documented name its cells skip under until it exists.
EARLY_SUBJECT_KEYED = "early_subject_keyed"
EARLY_POPULATION = "early_population"
EARLY_COMPOSITE_SUBJECT_CHILD = "early_composite_subject_child"
EARLY_COMPOSITE_FIXED_CHILD = "early_composite_fixed_child"
POPULATION_DECLARED = "population_declared"
PENDING_SHAPES: dict[str, tuple[str, Callable[[], bool]]] = {
    EARLY_SUBJECT_KEYED: (EARLY_WITHHOLDING_PROTOCOL, early_withholding_exists),
    EARLY_POPULATION: (EARLY_WITHHOLDING_PROTOCOL, early_withholding_exists),
    EARLY_COMPOSITE_SUBJECT_CHILD: (EARLY_WITHHOLDING_PROTOCOL, early_withholding_exists),
    EARLY_COMPOSITE_FIXED_CHILD: (EARLY_WITHHOLDING_PROTOCOL, early_withholding_exists),
    POPULATION_DECLARED: (f"{POPULATION_PROTOCOL} (open_product(population=...))", population_mode_exists),
}
COMPOSITE_SHAPES = (
    COMPOSITE_SUBJECT_CHILD,
    COMPOSITE_FIXED_CHILD,
    EARLY_COMPOSITE_SUBJECT_CHILD,
    EARLY_COMPOSITE_FIXED_CHILD,
)
#: The composites whose child is asked about a FIXED subject.
FIXED_CHILD_SHAPES = (COMPOSITE_FIXED_CHILD, EARLY_COMPOSITE_FIXED_CHILD)


def build_subject_keyed(
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False, early: bool = False
) -> Deployment:
    """The paved road: one fabric per question, ``acquire`` keyed on the subject."""
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    holdings = {SUBJECT: subject_holding()} if holds else {}
    return open_paved(
        base, anchor=anchor, acquire=SubjectKeyedSource(holdings),
        project=plan_factory(early=early, plan_id=PRODUCT_CLASS, asker=ASKER, active=active),
        evidence_readable=readable,
    )


def build_population(
    base: pathlib.Path,
    *,
    anchor: str,
    holds: bool,
    active: bool,
    readable: bool = False,
    early: bool = False,
    declared: bool = False,
) -> Deployment:
    """The paved road with an acquisition that reads the whole population, whatever is asked.

    ``declared`` is the explicit population-fetch mode (Dave, Q7; documented
    public name ``PopulationAcquireProtocol``, ``open_product(population=...)``,
    lane ``378-s020design`` PROPOSAL): the population read moves into the
    declared population half, which is handed no subject, and ``acquire`` keeps
    only what is keyed on the subject (nothing, for this source).
    """
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    holdings = {SIBLING: sibling_holding(), **({SUBJECT: subject_holding()} if holds else {})}
    project = plan_factory(early=early, plan_id=PRODUCT_CLASS, asker=ASKER, active=active)
    if declared:
        return open_paved(
            base, anchor=anchor, acquire=SubjectKeyedSource({}), project=project,
            evidence_readable=readable, population=PopulationHalf(holdings),
        )
    return open_paved(
        base, anchor=anchor, acquire=PopulationSource(holdings), project=project, evidence_readable=readable,
    )


def _required_policy_traversal() -> list[str]:
    from tests.products.test_withheld_is_indistinguishable_from_absent import REQUIRED_OPERATORS  # noqa: PLC0415

    return list(REQUIRED_OPERATORS)


def build_no_acquisition(
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False
) -> Deployment:
    """The low road with no acquisition seam: the fabric holds the source before any question."""
    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

    manifest = low_road_documents(base / "deployment", anchor=anchor, required=_required_policy_traversal())
    site = low_road_site(base, manifest, evidence_readable=readable)
    held = (sibling_holding(), *((subject_holding(),) if holds else ()))
    envelopes = tuple(envelope_for(h, tenant=TENANT, ingested_at=LOW_ROAD_INGESTED_AT) for h in held)
    factory = PolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=active)

    def answer(*, perspective: Perspective, request: ProductRequest) -> Any:
        fabric = site.boot(envelopes)
        try:
            return low_road_resolver(
                site, fabric, plan_factory=factory, acquisition=None,
                operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY),
            )(tenant=TENANT, product_class=PRODUCT_CLASS, version=request.schema_version,
              perspective=perspective, request=request)
        finally:
            fabric.handle.close()

    return low_road_deployment(site, answer=answer)


#: The similarity query, the subject's corpus text before any question (no
#: match), the text its acquisition writes (the query), and the sibling's.
SIMILARITY_QUERY = "beta"
SIMILARITY_BEFORE = "alpha"
SIMILARITY_SIBLING = "gamma"


def build_similarity(
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False
) -> Deployment:
    """A similarity operator over an entity the subject-keyed acquisition REFRESHES (channel 5).

    The fabric holds the subject (corpus text ``alpha``) and a sibling before any
    question; the source refreshes the subject to the query text ``beta``.
    """
    from tests.deployment.conftest import POLICY_PARAMS_KEY, SIMILARITY_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from ccf.operators.categories import SimilaritySelect  # noqa: PLC0415
    from tests.products.test_resolver_seam import ASKED_AT, PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

    manifest = low_road_documents(
        base / "deployment", anchor=anchor,
        required=[*_required_policy_traversal(), SimilaritySelect.key],
        similarity_query=SIMILARITY_QUERY,
    )
    site = low_road_site(base, manifest, evidence_readable=readable)
    before = Holding(account_ref=SUBJECT_REF, book=RESTRICTED_BOOK, label=SIMILARITY_BEFORE,
                     observed_at=asked_at() - timedelta(minutes=30))
    refreshed = Holding(account_ref=SUBJECT_REF, book=RESTRICTED_BOOK, label=SIMILARITY_QUERY,
                        observed_at=asked_at() - timedelta(minutes=1))
    held = (sibling_holding(label=SIMILARITY_SIBLING), *((before,) if holds else ()))
    envelopes = tuple(envelope_for(h, tenant=TENANT, ingested_at=LOW_ROAD_INGESTED_AT) for h in held)
    factory = PolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=active)

    def answer(*, perspective: Perspective, request: ProductRequest) -> Any:
        fabric = site.boot(envelopes)
        try:
            seam = SubjectKeyedSeam(fabric, {SUBJECT: refreshed} if holds else {}, tenant=TENANT, ingested_at=ASKED_AT)
            return low_road_resolver(
                site, fabric, plan_factory=factory, acquisition=seam,
                operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY, SIMILARITY_KEY),
            )(tenant=TENANT, product_class=PRODUCT_CLASS, version=request.schema_version,
              perspective=perspective, request=request)
        finally:
            fabric.handle.close()

    return low_road_deployment(site, answer=answer)


def build_reused_fabric(
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False
) -> Deployment:
    """ONE long-lived fabric handle with a subject-keyed acquisition seam, answering every question (M-6).

    Expected: refused (Dave, Q9: *"Enforce a fresh fabric per question whenever
    acquisition exists, including concurrent use"*). The paved road never builds
    this; a hand-composed low-road deployment can. The handle lives on one
    worker thread, as a long-lived deployment's would, so every door reaches it
    the same way (the SQLite reference backend binds a connection to the thread
    that opened it).
    """
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import ASKED_AT, PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

    manifest = low_road_documents(base / "deployment", anchor=anchor, required=_required_policy_traversal())
    site = low_road_site(base, manifest, evidence_readable=readable)
    worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sec020-long-lived-fabric")
    factory = PolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=active)
    state: dict[str, Any] = {}

    def boot() -> None:
        state["fabric"] = site.boot(
            (envelope_for(sibling_holding(), tenant=TENANT, ingested_at=LOW_ROAD_INGESTED_AT),)
        )
        state["seam"] = SubjectKeyedSeam(
            state["fabric"], {SUBJECT: subject_holding()} if holds else {}, tenant=TENANT, ingested_at=ASKED_AT
        )

    worker.submit(boot).result()

    def on_the_worker(*, perspective: Perspective, request: ProductRequest) -> Any:
        # Composed ONCE over the one fabric, the way a hand-built long-lived
        # deployment is; a composition the SDK refuses is refused here, once,
        # and re-raised on every question.
        if "resolver" not in state:
            try:
                state["resolver"] = low_road_resolver(
                    site, state["fabric"], plan_factory=factory, acquisition=state["seam"],
                    operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY),
                )
            except Exception as refused:  # noqa: BLE001 — a refused composition is an observation
                state["resolver"] = refused
        resolver = state["resolver"]
        if isinstance(resolver, Exception):
            raise resolver
        return resolver(tenant=TENANT, product_class=PRODUCT_CLASS, version=request.schema_version,
                        perspective=perspective, request=request)

    def answer(*, perspective: Perspective, request: ProductRequest) -> Any:
        return worker.submit(lambda: on_the_worker(perspective=perspective, request=request)).result()

    def close() -> None:
        worker.submit(lambda: state["fabric"].handle.close()).result()
        worker.shutdown(wait=True)

    return low_road_deployment(site, answer=answer, close=close)


def build_reused_store(
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False
) -> Deployment:
    """ONE persisted graph store, reopened by a fresh handle for every question (M-6, the production shape).

    Expected: refused, as for :func:`build_reused_fabric` (Dave, Q9). A
    deployment whose graph store outlives the process — several workers over
    one Postgres schema, say — boots a new handle per question over the same
    store; a guard that holds a handle in memory does not see the second one.
    Here the SQLite reference backend stands in for the persisted store.
    """
    from ccf.deployment import load_and_boot  # noqa: PLC0415

    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import ASKED_AT, PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

    manifest = low_road_documents(base / "deployment", anchor=anchor, required=_required_policy_traversal())
    site = low_road_site(base, manifest, evidence_readable=readable)
    database = site.root / "persisted-graph.sqlite3"
    seeded = load_and_boot(manifest, registry=site.control_plane, connection={"database_path": str(database)})
    seeded.handle.worker.ingest(envelope_for(sibling_holding(), tenant=TENANT, ingested_at=LOW_ROAD_INGESTED_AT))
    seeded.handle.close()
    factory = PolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=active)
    holdings = {SUBJECT: subject_holding()} if holds else {}

    def answer(*, perspective: Perspective, request: ProductRequest) -> Any:
        fabric = load_and_boot(manifest, registry=site.control_plane, connection={"database_path": str(database)})
        try:
            seam = SubjectKeyedSeam(fabric, holdings, tenant=TENANT, ingested_at=ASKED_AT)
            return low_road_resolver(
                site, fabric, plan_factory=factory, acquisition=seam,
                operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY),
            )(tenant=TENANT, product_class=PRODUCT_CLASS, version=request.schema_version,
              perspective=perspective, request=request)
        finally:
            fabric.handle.close()

    return low_road_deployment(site, answer=answer)


class RequestKeyedChildren:
    """A composite child resolver asking each child about the subject of the request it is handed.

    It wraps the SDK's :class:`~ccf.products.child_resolver.GrantBoundChildResolver`
    and conforms to :class:`~ccf.products.composite.RequestAwareChildResolverProtocol`:
    the governed resolver hands it the composite's effective request, and the
    child's arguments are derived from THAT request, never captured beside the
    governed path. ``fixed`` asks every child about one fixed subject instead.
    """

    def __init__(self, *, fixed: str | None) -> None:
        self._fixed = fixed
        self._subject: str | None = None
        self.inner: Any = None

    def child_arguments(self, requirement: Any, asked_at: datetime) -> Mapping[str, str]:
        subject = self._fixed or self._subject
        assert subject is not None, "a child was asked before the composite's request reached it"
        return {"subject": subject, "asked_at": asked_at.isoformat(), "threshold": str(THRESHOLD_VALUE)}

    def resolve_for(self, *, requirements: Any, request: ProductRequest, asked_at: datetime,
                    admitted_at: datetime, composition_invocation: str, consumer_lineage: Any) -> Any:
        self._subject = request.subject
        return self.inner.resolve_for(
            requirements=requirements, request=request, asked_at=asked_at, admitted_at=admitted_at,
            composition_invocation=composition_invocation, consumer_lineage=consumer_lineage,
        )

    def __call__(self, **arguments: Any) -> Any:
        raise AssertionError("the governed resolver asks a request-aware child resolver through resolve_for")


def asks_the_fixed_subject(requirement: Any, request: ProductRequest) -> Any:
    """The fixed child's question: always about :data:`FIXED` (a population-level child)."""
    from ccf.products.child_resolver import ChildQuestion  # noqa: PLC0415

    return ChildQuestion(subject=FIXED, intent=request.intent, freshness=request.freshness, parameters={})


def build_composite(
    base: pathlib.Path,
    *,
    anchor: str,
    holds: bool,
    active: bool,
    fixed_child: bool,
    readable: bool = False,
    early: bool = False,
) -> Deployment:
    """A composite whose child is asked about its own subject, or about a fixed one (channel 4).

    Parent and child are each asked on their own fabric per question, each
    behind a subject-keyed acquisition seam. In a deployment whose source holds
    the subject, both the parent's source and the child's do; the fixed child's
    source holds the fixed subject in every deployment. The parent's Π withholds
    by content (the parent's own view); the child's Π never withholds.
    """
    from ccf.products.composite import CHILD_QUESTION_CLASS  # noqa: PLC0415
    from ccf.products.door import door_answer  # noqa: PLC0415
    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products import composite_fixture as cf  # noqa: PLC0415
    from tests.products.provider_boot import CHILD_CLASS, CHILD_CLASS_KEY, CHILD_REQUEST_CONTRACT_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import ASKED_AT, PERSPECTIVE, PRODUCT_CLASS, THRESHOLD_PARAMETER, _Booted  # noqa: PLC0415

    manifest = low_road_documents(
        base / "deployment", anchor=anchor, required=_required_policy_traversal(),
        composite=True, child_anchor=anchor,
    )
    site = low_road_site(base, manifest, extra_classes=(CHILD_QUESTION_CLASS,), evidence_readable=readable)
    parent_holdings = {SUBJECT: subject_holding()} if holds else {}
    child_holdings = {FIXED: fixed_holding()} if fixed_child else ({SUBJECT: subject_holding()} if holds else {})
    parent_factory = plan_factory(early=early, plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=active)
    child_factory = PolicyPlanFactory(plan_id=CHILD_CLASS, asker=PERSPECTIVE.principal_id, active=False)

    def child_door(arguments: Mapping[str, str]) -> Mapping[str, str]:
        request = ProductRequest(
            schema_name=CHILD_CLASS, schema_version="1.0.0", subject=arguments["subject"],
            intent=INTENT, freshness=FRESHNESS, asked_at=datetime.fromisoformat(arguments["asked_at"]),
            parameters={THRESHOLD_PARAMETER: int(arguments["threshold"])},
        )
        fabric = site.boot(())
        try:
            seam = SubjectKeyedSeam(fabric, child_holdings, tenant=TENANT, ingested_at=ASKED_AT)
            resolved = low_road_resolver(
                site, fabric, plan_factory=child_factory, acquisition=seam,
                operator_parameter_keys=(TRAVERSAL_KEY,), product_class_key=CHILD_CLASS_KEY,
                request_contract_key=CHILD_REQUEST_CONTRACT_KEY,
            )(tenant=TENANT, product_class=CHILD_CLASS, version="1.0.0", perspective=PERSPECTIVE, request=request)
        finally:
            fabric.handle.close()
        return {
            "outcome": door_answer(
                resolved,
                echo=WireRequest(product_id=CHILD_CLASS, parameters={"subject": request.subject},
                                 temporal_boundary=request.asked_at),
                resolved_request=request,
            ).decode()
        }

    children = RequestKeyedChildren(fixed=FIXED if fixed_child else None)
    bootstrap = site.boot(())
    try:
        _resolver, children.inner = cf.build_composite(
            _Booted(fabric=bootstrap, control_plane=site.control_plane, store=site.store, root=site.root),
            child_door=child_door,
            child_arguments=children.child_arguments,
            child_questions=asks_the_fixed_subject if fixed_child else cf.asks_its_own_subject,
        )
    finally:
        bootstrap.handle.close()

    def answer(*, perspective: Perspective, request: ProductRequest) -> Any:
        fabric = site.boot(())
        try:
            seam = SubjectKeyedSeam(fabric, parent_holdings, tenant=TENANT, ingested_at=ASKED_AT)
            return low_road_resolver(
                site, fabric, plan_factory=parent_factory, acquisition=seam,
                operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY), composite_children=children,
            )(tenant=TENANT, product_class=PRODUCT_CLASS, version=request.schema_version,
              perspective=perspective, request=request)
        finally:
            fabric.handle.close()

    return low_road_deployment(site, answer=answer)


BUILDERS: dict[str, Callable[..., Deployment]] = {
    SUBJECT_KEYED: build_subject_keyed,
    NO_ACQUISITION: build_no_acquisition,
    POPULATION: build_population,
    SIMILARITY: build_similarity,
    COMPOSITE_SUBJECT_CHILD: lambda base, **kw: build_composite(base, fixed_child=False, **kw),
    COMPOSITE_FIXED_CHILD: lambda base, **kw: build_composite(base, fixed_child=True, **kw),
    REUSED_FABRIC: build_reused_fabric,
    REUSED_STORE: build_reused_store,
    EARLY_SUBJECT_KEYED: lambda base, **kw: build_subject_keyed(base, early=True, **kw),
    EARLY_POPULATION: lambda base, **kw: build_population(base, early=True, **kw),
    EARLY_COMPOSITE_SUBJECT_CHILD: lambda base, **kw: build_composite(base, fixed_child=False, early=True, **kw),
    EARLY_COMPOSITE_FIXED_CHILD: lambda base, **kw: build_composite(base, fixed_child=True, early=True, **kw),
    POPULATION_DECLARED: lambda base, **kw: build_population(base, declared=True, **kw),
}


# =============================================================================
# Authorized record reads at the MCP door
# =============================================================================


def mcp_artifact_server(deployment: Deployment) -> Any:
    """The shipped MCP artifact server over the deployment's ONE store, recorder and plane."""
    from mcp.server.auth.settings import AuthSettings  # noqa: PLC0415
    from pydantic import AnyHttpUrl  # noqa: PLC0415

    from ccf_runtime.mcp.artifact_server import build_artifact_server  # noqa: PLC0415
    from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant  # noqa: PLC0415
    from tests.mcp.guarded_servers import wide_authorizer  # noqa: PLC0415

    tenants = frozenset({deployment.tenant})
    return build_artifact_server(
        server_name=f"{deployment.tenant}-sec020-proof-artifacts",
        store=deployment.store,
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(
                grants={
                    ASKER_TOKEN: TokenGrant(client_id=ASKER, scopes=(MCP_SCOPE,), tenants=tenants),
                    OTHER_TOKEN: TokenGrant(client_id=OTHER, scopes=(MCP_SCOPE,), tenants=tenants),
                }
            )
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{MCP_BASE_URL}/mcp"),
            required_scopes=[MCP_SCOPE],
        ),
        authorizer=wide_authorizer(scopes=(MCP_SCOPE,)),
        entitlement_source=_entitlement_source(deployment),
        refusal_recorder=deployment.recorder,
        audit_log=deployment.control_plane.audit_log,
        erasure_index=deployment.erasure_index,
        control_plane=deployment.control_plane,
        erasure_trust=deployment.erasure_trust,
    )


def mcp_record_reads(deployment: Deployment, reference: str | None) -> dict[str, Any]:
    """Every MCP read of the record behind ``reference``, as the owner and another principal.

    The artifact server's blob (the record's bytes), presence answer, the names
    the address was filed under, and the resolution of the versioned URI; and
    the Experience server's ``get_replay_record`` tool.
    """
    from mcp.types import BlobResourceContents, TextResourceContents  # noqa: PLC0415
    from pydantic import AnyUrl  # noqa: PLC0415

    from ccf_runtime.mcp.artifact_server import (  # noqa: PLC0415
        artifact_blob_uri,
        artifact_meta_uri,
        artifact_names_uri,
    )

    if reference is None:
        return {"reference": None}
    address = _reference_parts(reference)["version"] if reference.startswith("ccf-artifact://") else reference
    presented = (reference, address)
    resources = {
        "blob": artifact_blob_uri(content_address=address),
        "meta": artifact_meta_uri(content_address=address),
        "names": artifact_names_uri(content_address=address),
        "resolution": reference,
    }
    reads: dict[str, Any] = {}
    for who, token in (("owner", ASKER_TOKEN), ("other-principal", OTHER_TOKEN)):
        for name, uri in resources.items():

            async def operation(session: Any, uri: str = uri) -> Any:
                try:
                    result = await session.read_resource(AnyUrl(uri))
                except Exception as refused:  # noqa: BLE001 — a protocol error is an observation
                    return {"error": type(refused).__name__, "message": str(refused)}
                parts = []
                for contents in result.contents:
                    if isinstance(contents, TextResourceContents):
                        parts.append({"text": _maybe_json(contents.text)})
                    elif isinstance(contents, BlobResourceContents):
                        parts.append({"blob": _maybe_json(base64.b64decode(contents.blob).decode("utf-8", "replace"))})
                return {"contents": parts}

            read = mcp_drive(mcp_artifact_server(deployment), operation, token=token)
            reads[f"{who}:{name}"] = _normalize_presented(jsonable(read), presented)
        reads[f"{who}:experience.get_replay_record"] = _normalize_presented(
            jsonable(experience_replay_read(deployment, address, token=token)), presented
        )
    return reads


def experience_replay_read(deployment: Deployment, address: str, *, token: str) -> Any:
    """The Experience server's ``get_replay_record`` tool, as a principal of the tenant calls it.

    Its seam (:class:`~ccf_runtime.mcp.experience.ReplayRecordReaderProtocol`)
    serves "the most-recent Decision Replay record"; the deployment here wires it
    the way that Protocol describes — the most recent record, which is the one
    behind the answer just given.
    """
    from mcp.types import TextContent  # noqa: PLC0415
    from mcp.server.auth.settings import AuthSettings  # noqa: PLC0415
    from pydantic import AnyHttpUrl  # noqa: PLC0415

    from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant  # noqa: PLC0415
    from ccf_runtime.mcp.experience import (  # noqa: PLC0415
        GET_REPLAY_RECORD_TOOL,
        ExperienceProductNotServable,
        build_experience_server,
    )
    from tests.mcp.guarded_servers import wide_authorizer  # noqa: PLC0415

    def most_recent_record() -> str:
        return deployment.store.get(content_address=address).decode("utf-8")

    def no_standing_product(**_: Any) -> Any:
        raise ExperienceProductNotServable("this proof deployment serves no standing product")

    role = deployment.role
    tenants = frozenset({deployment.tenant})
    server = build_experience_server(
        server_name=f"{deployment.tenant}-sec020-proof-experience",
        product_resolver=no_standing_product,
        replay_record_reader=most_recent_record,
        get_replay_record_description="The most recent decision record of this proof deployment.",
        replay_record_tenant=deployment.tenant,
        replay_record_product_class=None,
        tool_allowlist=frozenset({GET_REPLAY_RECORD_TOOL}),
        token_verifier=SourceBackedTokenVerifier(
            source=StaticTokenSource(
                grants={
                    ASKER_TOKEN: TokenGrant(client_id=ASKER, scopes=(MCP_SCOPE,), tenants=tenants),
                    OTHER_TOKEN: TokenGrant(client_id=OTHER, scopes=(MCP_SCOPE,), tenants=tenants),
                }
            )
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{MCP_BASE_URL}/mcp"),
            required_scopes=[MCP_SCOPE],
        ),
        authorizer=wide_authorizer(scopes=(MCP_SCOPE,)),
        entitlement_source=_entitlement_source(deployment),
        perspective_resolver=lambda *, grant, tenant, requested_role: Perspective(
            principal_id=grant.client_id, role=role
        ),
        refusal_recorder=deployment.recorder,
    )

    async def operation(session: Any) -> Any:
        try:
            result = await session.call_tool(GET_REPLAY_RECORD_TOOL, {})
        except Exception as refused:  # noqa: BLE001 — a protocol error is an observation
            return {"error": type(refused).__name__, "message": str(refused)}
        return {
            "is_error": bool(result.isError),
            "text": [_maybe_json(c.text) for c in result.content if isinstance(c, TextContent)],
        }

    return mcp_drive(server, operation, token=token)


def _maybe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return text


# =============================================================================
# The sides one cell observes
# =============================================================================

COUNTERFACTUAL = "cf"
SAME_DEPLOYMENT = "same"
COMPARISONS = (COUNTERFACTUAL, SAME_DEPLOYMENT)

#: The deployment holds the subject, the policy withholds it from the asker; it is asked about it.
CF_WITHHELD = "withheld"
#: A deployment identical but for its source, which does not hold the subject; asked the same.
CF_NONEXISTENT = "nonexistent"
#: A second, independent copy of that deployment: the counterfactual's noise floor.
CF_FLOOR = "nonexistent-again"
#: The withholding deployment asked about an identifier no source has ever held.
SAME_NONEXISTENT = "never-held"
#: The same, for a second such identifier: the same-deployment noise floor.
SAME_FLOOR = "never-held-again"
#: The instrument: the deployment that holds the subject with the policy OFF; its subject is SERVED.
SERVED = "served"
#: The refusal-code instrument: the nonexistent deployment asked the same question
#: with a parameter its class does not declare, so it is REFUSED by contract.
REFUSED_QUESTION = "refused-question"
#: Built only where the owner-read allowlist exists: the same three deployments
#: with the class LISTED evidence-readable. The served and nonexistent pair is
#: the record channel's instrument there (default-deny would otherwise refuse
#: both alike); the withheld and nonexistent pair is the PENDING cell that a
#: listed withholding class must not reopen the record channel.
SERVED_READABLE = "served-readable"
WITHHELD_READABLE = "withheld-readable"
NONEXISTENT_READABLE = "nonexistent-readable"

#: (withheld side, nonexistent side, noise-floor side) per comparison.
PAIRS: dict[str, tuple[str, str, str]] = {
    COUNTERFACTUAL: (CF_WITHHELD, CF_NONEXISTENT, CF_FLOOR),
    SAME_DEPLOYMENT: (CF_WITHHELD, SAME_NONEXISTENT, SAME_FLOOR),
}

def instrument_pair(channel: str, run: Run) -> tuple[str, str]:
    """The pair one channel's instrument compares: a side that MUST differ from the nonexistent one.

    Where the owner-read allowlist exists, the record channel is instrumented
    on deployments that LIST the class, so default-deny cannot blind it.
    """
    if channel == RECORD and SERVED_READABLE in run.sides:
        return SERVED_READABLE, NONEXISTENT_READABLE
    return INSTRUMENT_PAIRS[channel]


#: The pair each channel's instrument compares: a side that MUST differ from the nonexistent one.
INSTRUMENT_PAIRS: dict[str, tuple[str, str]] = {
    RESPONSE: (SERVED, CF_NONEXISTENT),
    REFUSAL: (REFUSED_QUESTION, CF_NONEXISTENT),
    REFERENCE: (SERVED, CF_NONEXISTENT),
    COMPOSITE: (SERVED, CF_NONEXISTENT),
    RECORD: (SERVED, CF_NONEXISTENT),
}


def channels_for(*, comparison: str, shape: str, door: str) -> tuple[str, ...]:
    """The channels one (comparison, shape, door) cell compares.

    Composite child rows are read once (in process; they are the record's, not
    the door's). Record reads exist only at the two doors a principal reads
    through, and only in the counterfactual, where the two records can be
    compared byte for byte (in the same deployment the requests differ).
    """
    channels = [RESPONSE, REFUSAL, REFERENCE]
    if comparison == COUNTERFACTUAL and shape in COMPOSITE_SHAPES and door == IN_PROCESS:
        channels.append(COMPOSITE)
    if comparison == COUNTERFACTUAL and door in (HTTP, MCP):
        channels.append(RECORD)
    return tuple(channels)


def comparisons_for(shape: str) -> tuple[str, ...]:
    """A fabric or store that outlives the question is compared as a counterfactual only: its point is the sequence."""
    return (COUNTERFACTUAL,) if shape in REUSED_SHAPES else COMPARISONS


def _questions(shape: str, subject: str) -> tuple[str, ...]:
    """What one side asks: one question, or, on the reused fabric, the subject then an unheld identifier."""
    return (subject, NEVER) if shape in REUSED_SHAPES else (subject,)


def _merge(observations: list[Observation]) -> Observation:
    """One side's observation; on the reused fabric, its two questions keyed by position."""
    if len(observations) == 1:
        return observations[0]
    merged = Observation(raw=[o.raw for o in observations])
    for channel in CHANNELS:
        present = [o.channels.get(channel) for o in observations]
        if any(value is not None for value in present):
            merged.channels[channel] = dict(zip(("first", "second"), present, strict=True))
    return merged


def _reference_of(door: str, observation: Observation) -> str | None:
    if door in (HTTP, MCP):
        return observation.raw["reference"]
    raw = observation.raw
    if isinstance(raw, ServedProduct):
        return raw.replay_ref.uri
    if isinstance(raw, RefusalEnvelope):
        return raw.replay_reference
    return None


def observe_side(
    shape: str,
    door: str,
    deployment: Deployment,
    subject: str,
    *,
    parameters: Mapping[str, Any] | None = None,
    reads: bool = False,
) -> Observation:
    """Ask one side's question(s) through ``door``; with ``reads``, read back what a principal can."""
    app = http_app(deployment) if door == HTTP else None
    observed: list[Observation] = []
    for asked in _questions(shape, subject):
        if door == HTTP:
            observation = observe_http(deployment, asked, app=app, parameters=parameters)
        elif door == MCP:
            observation = observe_mcp(deployment, asked, parameters=parameters)
        else:
            observation = observe_in_process(deployment, asked, parameters=parameters)
        reference = _reference_of(door, observation)
        if reads and shape in COMPOSITE_SHAPES and door == IN_PROCESS:
            observation.channels[COMPOSITE] = {
                "child_rows": composite_rows(deployment, reference),
            }
        if reads and door == HTTP:
            observation.channels[RECORD] = http_record_reads(deployment, reference, app=app)
        if reads and door == MCP:
            observation.channels[RECORD] = mcp_record_reads(deployment, reference)
        observed.append(observation)
    return _merge(observed)


def _subject_neutral(value: Any) -> Any:
    """Replace the asked identifiers with one placeholder (the same-deployment comparison).

    Two different identifiers are asked there, and a door that echoes the
    question it was asked (the MCP door's ``answered``) echoes the caller's own
    input; that echo is not what the comparison is about.
    """
    if isinstance(value, str):
        for asked in (SUBJECT, NEVER, NEVER_2):
            value = value.replace(asked, "<asked-subject>")
        return value
    if isinstance(value, dict):
        return {key: _subject_neutral(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_subject_neutral(item) for item in value]
    return value


def _name_only(value: Any) -> Any:
    """Every reference reduced to its record NAME (the same-deployment reference comparison).

    The version segment is the record's content address, and the record holds
    the request, whose subject differs between the two sides by construction.
    The name is dimension 1's snapshot identity
    (``src/ccf/replay/serve.py::ReplayWriter``): two identifiers that name
    nothing share it (the C-1 test's instrument).
    """
    if isinstance(value, str) and value.startswith("ccf-artifact://"):
        return _reference_parts(value)["name"]
    if isinstance(value, dict):
        if {"content_address", "uri", "name"} <= set(value):
            return {"name": value["name"]}
        return {key: _name_only(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_name_only(item) for item in value]
    return value


@dataclass
class Run:
    """Every side of one (shape, anchor, door), observed once, read by every channel's test."""

    shape: str
    anchor: str
    door: str
    sides: dict[str, Observation]
    notes: dict[str, Any] = field(default_factory=dict)

    def channel(self, side: str, channel: str, *, comparison: str = COUNTERFACTUAL, names_only: bool = False) -> Any:
        """``side``'s ``channel`` as ``comparison`` compares it."""
        value = jsonable(self.sides[side].channels.get(channel))
        if comparison == SAME_DEPLOYMENT:
            value = _subject_neutral(value)
        if names_only or (comparison == SAME_DEPLOYMENT and channel == REFERENCE):
            value = _name_only(value)
        return value


def run_sides(base: pathlib.Path, *, shape: str, anchor: str, door: str) -> Run:
    """Build the deployments one (shape, anchor, door) needs, ask every side, close them."""
    build = BUILDERS[shape]
    sides: dict[str, Observation] = {}
    opened: list[Deployment] = []

    def deployment(name: str, *, holds: bool, active: bool) -> Deployment:
        built = build(base / name, anchor=anchor, holds=holds, active=active)
        opened.append(built)
        return built

    try:
        withholding = deployment("withholding", holds=True, active=True)
        sides[CF_WITHHELD] = observe_side(shape, door, withholding, SUBJECT, reads=True)
        if SAME_DEPLOYMENT in comparisons_for(shape):
            sides[SAME_NONEXISTENT] = observe_side(shape, door, withholding, NEVER)
            sides[SAME_FLOOR] = observe_side(shape, door, withholding, NEVER_2)
        sides[CF_NONEXISTENT] = observe_side(
            shape, door, deployment("not-holding", holds=False, active=True), SUBJECT, reads=True
        )
        sides[CF_FLOOR] = observe_side(
            shape, door, deployment("not-holding-again", holds=False, active=True), SUBJECT, reads=True
        )
        sides[SERVED] = observe_side(
            shape, door, deployment("serving", holds=True, active=False), SUBJECT, reads=True
        )
        sides[REFUSED_QUESTION] = observe_side(
            shape, door, deployment("refusing", holds=False, active=True), SUBJECT,
            parameters=violating_parameters(),
        )
        if door in (HTTP, MCP) and evidence_allowlist_exists():
            for side, name, holds, active in (
                (SERVED_READABLE, "serving-readable", True, False),
                (WITHHELD_READABLE, "withholding-readable", True, True),
                (NONEXISTENT_READABLE, "not-holding-readable", False, True),
            ):
                built = build(base / name, anchor=anchor, holds=holds, active=active, readable=True)
                opened.append(built)
                sides[side] = observe_side(shape, door, built, SUBJECT, reads=True)
    finally:
        for built in opened:
            built.close()
    return Run(shape=shape, anchor=anchor, door=door, sides=sides)


class RunCache:
    """One run per (shape, anchor, door) for the whole session."""

    def __init__(self, factory: Callable[[str], pathlib.Path]) -> None:
        self._factory = factory
        self._runs: dict[tuple[str, str, str], Run] = {}

    def get(self, *, shape: str, anchor: str, door: str) -> Run:
        key = (shape, anchor, door)
        if key not in self._runs:
            self._runs[key] = run_sides(self._factory("-".join(key)), shape=shape, anchor=anchor, door=door)
        return self._runs[key]


def render(value: Any, *, limit: int = 700) -> str:
    """A short rendering for a failure message."""
    text = json.dumps(value, default=str, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "…"
