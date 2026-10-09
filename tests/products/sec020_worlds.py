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
import functools
import hashlib
import json
import math
import pathlib
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from ccf.artifacts.protocol import parse_artifact_uri
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


def never_withholds() -> str:
    """The class affirmation Dave's Q12 reads (``ccf.products.contract.SUBJECT_WITHHOLDING_NEVER``).

    Read where it is used, so this module still imports on a tree without Q12;
    it is only reached when the owner-read allowlist exists
    (:func:`evidence_allowlist_exists`).
    """
    from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER  # noqa: PLC0415

    return SUBJECT_WITHHOLDING_NEVER


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

    def withholds_no_subject(self) -> bool:
        """The positive declaration Dave's E2 (ii) (d) requires under ``never`` — true exactly when the policy is off.

        :class:`PolicyProjection` sets the withheld signal only when ``active``
        (read off its ``invoke``; and measured, lane ``378f-e2d``: every withheld
        signal a projection of this family raised under a ``never`` class came
        from a policy-on factory). So the policy-off deployments a ``never``
        class is built as here — every instrument, every twin, every readable
        world — declare it, and a policy-on factory states that it may withhold.
        Classes at the default never read it.
        """
        return not self.active


# --- early withholding (Dave, Q8) ------------------------------------------------

#: Early withholding's public name (``D-IMPL-378`` Q8, integrated at
#: ``b2393d2d``): the plan factory's optional companion Protocol
#: ``ccf.products.resolver.SubjectDisclosingPlanFactoryProtocol``, whose
#: ``subject_disclosure()`` returns a declared
#: ``ccf.products.subject_disclosure.SubjectDisclosurePolicy``.
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
    """A plan factory that declares its withholding EARLY, as data (``SubjectDisclosingPlanFactoryProtocol``).

    The declared :class:`~ccf.products.subject_disclosure.SubjectDisclosurePolicy`:
    the asker is not told about :data:`SUBJECT`, and every subject-dependent
    step is asked about :data:`STAND_IN` in its place. The policy-off
    deployment (the instrument) declares a policy that withholds nothing. The
    projection withholds exactly what the policy does not disclose.
    """

    def subject_disclosure(self) -> Any:
        from ccf.products.subject_disclosure import SubjectDisclosurePolicy  # noqa: PLC0415

        return SubjectDisclosurePolicy(
            undisclosed_subject=STAND_IN,
            by_principal={self.asker: frozenset({SUBJECT})} if self.active else {},
            by_role={},
        )

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

#: The position of a side's one question (the reused shapes ask two: ``first``, ``second``).
#: A raise inside a record read is keyed ``<position>/record:<read>``.
ONLY = "only"


@dataclass
class Observation:
    """Everything one question showed, channel by channel.

    ``channels`` maps a channel name to a JSON-shaped value; a channel this
    door cannot carry is absent rather than empty. ``raw`` keeps the outcome
    for the failure message and for reading references back. ``raised`` names,
    per question position, an exception the question ended in instead of an
    answer (in process: the exception; HTTP: a 5xx; MCP: an error result that
    is no door outcome) — so a comparison can tell "both sides answered alike"
    from "both sides broke alike".
    """

    channels: dict[str, Any] = field(default_factory=dict)
    raw: Any = None
    raised: dict[str, str] = field(default_factory=dict)
    #: Per reference this question was handed, what the deployment's own store
    #: says it names: the URI's name and version, the address the store resolves
    #: it to, and the SHA-256 of the bytes stored there (Dave's Q11 properties,
    #: :func:`reference_properties`). An entry ``{"error": ...}`` is a reference
    #: that does not resolve.
    reference_facts: dict[str, dict[str, str]] = field(default_factory=dict)
    #: Per question position, what the record reads were presented with and what
    #: the owner's reads by that reference answered
    #: (:func:`test_sec020_combined_proof.test_the_caller_visible_reference_resolves_through_the_governed_reads`).
    read_check: dict[str, dict[str, Any]] = field(default_factory=dict)


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


def _kind(value: Any) -> str:
    """What a leaf IS, as against what it says: absent, a reference, other text, a number, a container."""
    if value is None:
        return "none"
    if isinstance(value, str):
        return "reference" if value.startswith("ccf-artifact://") else "text"
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, list | tuple):
        return "sequence"
    return type(value).__name__


def kind_diff_paths(left: Any, right: Any, prefix: str = "") -> set[str]:
    """Every dotted path where both sides hold a leaf and the two leaves differ in KIND (:func:`_kind`).

    The noise floor excuses a difference in VALUE where two copies of the
    nonexistent side also differ in value; it never excuses a difference in
    kind. Under Dave's Q11 every reference is unique per answer, so two
    nonexistent copies differ at every reference path, and a value-only floor
    would also excuse one side being handed NO reference where the other was
    handed one. Missing keys and list lengths stay the floor's to judge
    (:func:`diff_paths` reports them); only leaves present on both sides are
    compared here.
    """
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        found: set[str] = set()
        for key in set(left) & set(right):
            found |= kind_diff_paths(left[key], right[key], f"{prefix}.{key}" if prefix else str(key))
        return found
    if isinstance(left, list | tuple) and isinstance(right, list | tuple):
        if len(left) != len(right):
            return set()
        found = set()
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            found |= kind_diff_paths(a, b, f"{prefix}[{index}]")
        return found
    return set() if _kind(left) == _kind(right) else {prefix or "<root>"}


# --- Dave's E1 (a): references are judged by DISTRIBUTION, not equality --------
#
# ``D-IMPL-378``, Dave, 2026-10-08 12:29 MST, verbatim: *"Approve random
# per-answer issuance and the named conformance amendments. Preserve record
# content-address integrity. Random references must have indistinguishable
# distributions; equality is no longer the criterion."* Every product answer's
# record carries a fresh 256-bit issuance and is named by its own content
# address, so no two answers share a reference, and the withheld side's
# reference can never EQUAL the nonexistent side's. What the proof holds instead
# (``test_sec020_combined_proof._compare`` and
# ``test_sec020_combined_proof.test_withheld_and_nonexistent_references_are_drawn_from_one_distribution``):
# every reference has the same FORM on both sides, a reference the nonexistent
# side's two copies agree on is not a draw from any distribution, and the two
# sides' references, pooled over every cell of a comparison, pass a two-sample
# test. A difference in KIND (:func:`kind_diff_paths`) stays a failure.

#: A reference's random token: 64 lowercase hexadecimal characters (a content address).
REFERENCE_TOKEN = re.compile(r"\A[0-9a-f]{64}\Z")

#: The pooled two-sample test's significance level: the probability that the
#: gate goes red when both sides' references ARE drawn from one distribution.
#: Chosen small because the references are fresh randomness on every run, so a
#: false alarm cannot be reproduced on demand: about one run in 10,000.
REFERENCE_DISTRIBUTION_ALPHA = 1e-4

#: The fewest distinct references per side the pooled test accepts as evidence.
REFERENCE_DISTRIBUTION_MIN_SAMPLES = 50

#: The fewest distinct per-answer issuances per side the pooled test accepts:
#: one per answered question, so fewer than the references (an answer's
#: reference also reaches the record reads' own refusals).
ISSUANCE_DISTRIBUTION_MIN_SAMPLES = 30


def reference_leaves(value: Any, *, channel: str, prefix: str = "") -> dict[str, str]:
    """Every leaf of ``value`` that is a replay reference, by dotted path.

    A ``ccf-artifact://`` URI anywhere — the answer's reference, and the
    reference a governed read's own refusal is recorded under. In the
    :data:`REFERENCE` channel also a bare 64-hexadecimal record name: the
    same-deployment comparison reduces every reference to its name
    (:func:`_name_only`). Every other 64-hexadecimal value a channel carries — a
    product's content address, a pinned Control Plane version, a child's
    address — is deterministic, and stays compared by equality.
    """
    if isinstance(value, Mapping):
        found: dict[str, str] = {}
        for key, item in value.items():
            found |= reference_leaves(item, channel=channel, prefix=f"{prefix}.{key}" if prefix else str(key))
        return found
    if isinstance(value, list | tuple):
        found = {}
        for index, item in enumerate(value):
            found |= reference_leaves(item, channel=channel, prefix=f"{prefix}[{index}]")
        return found
    if isinstance(value, str) and (
        value.startswith("ccf-artifact://") or (channel == REFERENCE and REFERENCE_TOKEN.match(value))
    ):
        return {prefix or "<root>": value}
    return {}


def _token_form(token: str) -> tuple[int, str]:
    """A token's length and alphabet: lowercase hexadecimal, or the characters it uses."""
    return len(token), "hex" if REFERENCE_TOKEN.match(token) else "".join(sorted(set(token)))


def reference_form(leaf: str) -> tuple[Any, ...]:
    """What a reference IS, as against WHICH one it is (E1 (a)).

    A URI: its scheme, tenant and class, each identifying segment's length and
    alphabet, and whether its name and version are one identity (Q11). A bare
    record name: its length and alphabet. Two references of one form differ
    only in their random token.
    """
    if leaf.startswith("ccf-artifact://"):
        parts = _reference_parts(leaf)
        return (
            "ccf-artifact", parts["tenant"], parts["artifact_class"],
            _token_form(parts["name"]), _token_form(parts["version"]), parts["name"] == parts["version"],
        )
    return ("name", _token_form(leaf))


def reference_token(leaf: str) -> str:
    """A reference's random token: a URI's version segment (its record's content address), or the bare name."""
    return _reference_parts(leaf)["version"] if leaf.startswith("ccf-artifact://") else leaf


def token_position(token: str) -> float:
    """Where a 64-hexadecimal token sits in [0, 1): its leading 52 bits, read as a fraction."""
    return int(token[:13], 16) / 16**13


def ks_two_sample(left: Iterable[float], right: Iterable[float]) -> float:
    """The two-sample Kolmogorov-Smirnov statistic: the largest gap between the two empirical CDFs."""
    xs, ys = sorted(left), sorted(right)
    if not xs or not ys:
        raise ValueError("the two-sample test needs a sample on each side")
    gap, i, j = 0.0, 0, 0
    while i < len(xs) and j < len(ys):
        point = min(xs[i], ys[j])
        while i < len(xs) and xs[i] == point:
            i += 1
        while j < len(ys) and ys[j] == point:
            j += 1
        gap = max(gap, abs(i / len(xs) - j / len(ys)))
    return gap


def ks_critical(n: int, m: int, alpha: float) -> float:
    """The asymptotic two-sample critical value: reject when the statistic exceeds it.

    ``c(alpha) * sqrt((n + m) / (n * m))`` with ``c(alpha) = sqrt(-ln(alpha / 2) / 2)``
    (Smirnov's limit; conservative at the sample sizes used here).
    """
    return math.sqrt(-math.log(alpha / 2) / 2) * math.sqrt((n + m) / (n * m))


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


#: Where :func:`door_resolver` files what a deployment's resolver raised behind a door.
DOOR_RAISED = "door_raised"


def door_resolver(deployment: Deployment) -> Callable[..., Any]:
    """``deployment.resolve`` as a door is handed it, noting every exception it raises.

    A door turns a resolver's exception into its own opaque failure (a 500 at
    HTTP, ``ccf-runtime-failure:<id>`` at MCP), which names no type; the proof
    needs the type to tell the one refusal a cell may be green on (Q9's) from
    any other break. Behavior is unchanged: the exception is re-raised as is,
    and the signature is the wrapped one (``functools.wraps``).
    """
    raised: list[str] = deployment.notes.setdefault(DOOR_RAISED, [])

    @functools.wraps(deployment.resolve)
    def resolve(*args: Any, **kwargs: Any) -> Any:
        try:
            return deployment.resolve(*args, **kwargs)
        except Exception as exc:
            raised.append(f"{type(exc).__name__}: {exc}")
            raise

    return resolve


def _raised_behind_the_door(deployment: Deployment, since: int, fallback: str) -> str:
    """What the resolver raised during one door call (``since``: the note count before it)."""
    noted = deployment.notes.get(DOOR_RAISED, [])[since:]
    return " | ".join(noted) if noted else fallback


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


def paved_document(anchor: str, *, never: bool = False) -> dict[str, Any]:
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
    if never:
        # Dave's Q12: the class affirms its answers never withhold their subject.
        document["product_class"]["subject_withholding"] = never_withholds()
    return document


def open_paved(
    base: pathlib.Path,
    *,
    anchor: str,
    acquire: Any,
    project: Any,
    document: dict[str, Any] | None = None,
    evidence_readable: bool = False,
    never: bool = False,
    **overrides: Any,
) -> Deployment:
    """Open the paved fixture product under ``base``: one store, one recorder, one Control Plane."""
    from tests.deployment.test_replay_binding import PRODUCT_CLASS, PRODUCT_VERSION, ROLE, TENANT  # noqa: PLC0415
    from tests.products.paved_fixture import granted_control_plane  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT, _open, _write_tree  # noqa: PLC0415
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER  # noqa: PLC0415

    base.mkdir(parents=True, exist_ok=True)
    root = _write_tree(base, config=document if document is not None else paved_document(anchor, never=never))
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
        return Observation(
            channels={RESPONSE: shape, REFUSAL: shape, REFERENCE: shape},
            raw=raised,
            raised={ONLY: f"{type(raised).__name__}: {raised}"},
        )
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
            product_resolver=door_resolver(deployment),
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
        # An exception the app does not handle becomes the 500 a caller would
        # receive, rather than an exception raised into this test.
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://fabric.invalid",
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
    since = len(deployment.notes.get(DOOR_RAISED, []))
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
        raised=(
            {ONLY: _raised_behind_the_door(deployment, since, f"HTTP {response.status_code}: {response.text[:300]}")}
            if response.status_code >= 500
            else {}
        ),
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
        resolver=door_resolver(deployment),
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

    since = len(deployment.notes.get(DOOR_RAISED, []))
    called = mcp_drive(mcp_product_server(deployment), operation)
    if "unreachable" in called:
        shape = {"outcome": "unreachable", "detail": called["unreachable"]}
        return Observation(
            channels={RESPONSE: shape, REFUSAL: shape, REFERENCE: shape},
            raw=called,
            raised={ONLY: f"MCP unreachable: {called['unreachable'][:300]}"},
        )
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
        raised=(
            {ONLY: _raised_behind_the_door(deployment, since, f"MCP error: {str(outcome)[:300]}")}
            if called["is_error"] and not isinstance(outcome, dict)
            else {}
        ),
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


def http_record_reads(
    deployment: Deployment, reference: str | None, *, app: Any, raw: dict[str, Any] | None = None
) -> dict[str, Any]:
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
            if raw is not None:
                raw[f"{who}:{route}"] = {
                    "status": response.status_code,
                    "sha256": hashlib.sha256(response.content).hexdigest(),
                }
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
    never: bool = False,
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
            if never:
                # Dave's Q12: the class affirms its answers never withhold their subject.
                document["subject_withholding"] = never_withholds()
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
        """A fresh fabric for ONE question, from the deployment's documents, holding ``envelopes``.

        Booted ``for_question=True`` onto a path that does not exist yet (SEC-020
        Q9): the fabric an acquisition phase may write into for its one
        question. What it holds before the question (``envelopes``) is the
        source as it stood before anything was asked.
        """
        from ccf.deployment import load_and_boot  # noqa: PLC0415

        self.counter += 1
        fabric = load_and_boot(
            self.manifest,
            registry=self.control_plane,
            connection={"database_path": str(self.root / f"graph-{self.counter}.sqlite3")},
            for_question=True,
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
        # SEC-020 Q7: stated, never defaulted — no shape on this road declares
        # a separate population phase.
        population_acquisition=None,
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

#: Shapes that need a public knob absent from ``e9e5e2cd`` and present from
#: ``b2393d2d`` (D-IMPL-378, Q7–Q8); each maps to the documented name its cells
#: skip under (``pending API: <name>``) on any tree where it is absent.
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

# Dave's ruling D1 = (a), 2026-10-07 21:15 MST, on the question as put to him
# (relayed by the coordinator, verbatim, the elisions the coordinator's own). It
# is kept as a comment, not a string literal: prose addressed to a reader is
# what the No-Hardcoding lint (CINV-01a) refuses in code, tests included.
#
#   "Products that read the whole population. Your two-deployment test ...
#   cannot pass when a product reads everyone's data, such as a pre-loaded
#   fabric or a fetch-everyone source ... (a) For those products only, use your
#   D-IMPL-371 comparison: the withheld subject against an id nothing holds, in
#   the same deployment."
#
#: The citation every retired cell and the governing comparison carry.
D1A_RULING = "Dave D1 = (a), 2026-10-07 21:15 MST; D-IMPL-371"

#: The population-reading shapes D1 = (a) governs: the fabric loaded before the
#: question and walked by class, and the source that returns everyone — with or
#: without the early-withholding declaration, and in the explicit
#: population-fetch mode. For these the same-deployment comparison (``D-IMPL-371``)
#: is the governing check for every observable, and the two-deployment cells are
#: retired from the closure gate. Measured, the reason: an identifier that exists
#: in NEITHER deployment is answered differently by the two (the account's data
#: is in every answer), so no withholding mechanism is what those cells measure.
POPULATION_READING_SHAPES = (NO_ACQUISITION, POPULATION, EARLY_POPULATION, POPULATION_DECLARED)


def build_subject_keyed(
    base: pathlib.Path,
    *,
    anchor: str,
    holds: bool,
    active: bool,
    readable: bool = False,
    early: bool = False,
    never: bool = False,
) -> Deployment:
    """The paved road: one fabric per question, ``acquire`` keyed on the subject."""
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    holdings = {SUBJECT: subject_holding()} if holds else {}
    return open_paved(
        base, anchor=anchor, acquire=SubjectKeyedSource(holdings),
        project=plan_factory(early=early, plan_id=PRODUCT_CLASS, asker=ASKER, active=active),
        evidence_readable=readable,
        never=never,
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
    never: bool = False,
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
            evidence_readable=readable, population=PopulationHalf(holdings), never=never,
        )
    return open_paved(
        base, anchor=anchor, acquire=PopulationSource(holdings), project=project, evidence_readable=readable,
        never=never,
    )


# --- ruling P6 (a)'s retained counterexample: a source that recognizes the probe ------------
#
# Dave, 2026-10-08 16:40 MST (D-IMPL-378), item 2, verbatim (kept as a comment, CINV-01a):
#   "Do not declare closure based on this probe alone: prove it runs before
#   real-subject acquisition, and retain the counterexample where a source treats
#   the probe identifier differently."
#
#: How a source recognizes the identifier the P6 probe asks about: EXACTLY, or by
#: its SHAPE — it is no ``account://`` URI, the form this fixture's entity
#: resolution mints for every account (:func:`entity_uri`).
PROBE_RECOGNIZED_BY_IDENTIFIER = "by_identifier"
PROBE_RECOGNIZED_BY_SHAPE = "by_shape"
PROBE_RECOGNITIONS = (PROBE_RECOGNIZED_BY_IDENTIFIER, PROBE_RECOGNIZED_BY_SHAPE)
#: The label a probe-recognizing run carries. Deliberately outside :data:`SHAPES`
#: and :data:`PENDING_SHAPES`: it is never a cell of the closure gate.
PROBE_RECOGNIZING = "population_probe_recognized"


def probe_identifier() -> str | None:
    """The identifier ruling P6 (a)'s probe asks about, read where it is used (``None`` on a tree without it)."""
    import ccf.products.resolver as resolver  # noqa: PLC0415

    return getattr(resolver, "UNHELD_SUBJECT_PROBE", None)


class ProbeRecognizingPopulationSource(PopulationSource):
    """``acquire`` that answers NOTHING for the probe identifier and the whole population for any other.

    The counterexample ruling P6 (a) keeps: the probe sees a phase that acquires
    nothing for an identifier it does not hold, and admits the product, while
    every real question — the withheld subject's and an identifier nothing
    holds alike — reads the whole population.
    """

    def __init__(self, holdings: Mapping[str, Holding], *, recognition: str) -> None:
        super().__init__(holdings)
        self._recognition = recognition
        #: Every identifier this source recognized as the probe, and answered nothing for.
        self.answered_nothing_for: list[str] = []

    def recognizes(self, subject: str) -> bool:
        if self._recognition == PROBE_RECOGNIZED_BY_IDENTIFIER:
            return subject == probe_identifier()
        return not subject.startswith("account://")

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        subject = context.request.subject
        if not self.recognizes(subject):
            return super().__call__(context)
        self.asked.append(subject)
        self.answered_nothing_for.append(subject)
        return ()


def build_probe_recognizing(
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, recognition: str
) -> Deployment:
    """:func:`build_population`'s deployment with a source that recognizes the probe (ruling P6 (a)'s counterexample)."""
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    holdings = {SIBLING: sibling_holding(), **({SUBJECT: subject_holding()} if holds else {})}
    return open_paved(
        base, anchor=anchor, acquire=ProbeRecognizingPopulationSource(holdings, recognition=recognition),
        project=plan_factory(early=False, plan_id=PRODUCT_CLASS, asker=ASKER, active=active),
    )


def _required_policy_traversal() -> list[str]:
    from tests.products.test_withheld_is_indistinguishable_from_absent import REQUIRED_OPERATORS  # noqa: PLC0415

    return list(REQUIRED_OPERATORS)


def build_no_acquisition(
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False, never: bool = False
) -> Deployment:
    """The low road with no acquisition seam: the fabric holds the source before any question."""
    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

    manifest = low_road_documents(
        base / "deployment", anchor=anchor, required=_required_policy_traversal(), never=never
    )
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
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False, never: bool = False
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
        never=never,
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
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False, never: bool = False
) -> Deployment:
    """ONE fabric handle, booted for a question, with a subject-keyed seam, asked every question (M-6).

    Expected: refused (Dave, Q9: *"Enforce a fresh fabric per question whenever
    acquisition exists, including concurrent use"*). The handle is booted
    ``for_question=True``, so its FIRST question is answered; the second, on
    the fabric the first one's acquisition wrote into, must be refused. The
    paved road never builds this; a hand-composed low-road deployment can. The
    handle lives on one worker thread, as a long-lived deployment's would, so
    every door reaches it the same way (the SQLite reference backend binds a
    connection to the thread that opened it).
    """
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import ASKED_AT, PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

    manifest = low_road_documents(
        base / "deployment", anchor=anchor, required=_required_policy_traversal(), never=never
    )
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
    base: pathlib.Path, *, anchor: str, holds: bool, active: bool, readable: bool = False, never: bool = False
) -> Deployment:
    """ONE persisted graph store, reopened by an ordinary boot for every question (M-6, the production shape).

    Expected: refused, as for :func:`build_reused_fabric` (Dave, Q9). A
    deployment whose graph store outlives the process — several workers over
    one Postgres schema, say — boots a new handle per question over the same
    store, with an ordinary boot (a question fabric is fresh by construction,
    and this store is not). Every question that would acquire into it must be
    refused, the first included. Here the SQLite reference backend stands in
    for the persisted store.
    """
    from ccf.deployment import load_and_boot  # noqa: PLC0415

    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import ASKED_AT, PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

    manifest = low_road_documents(
        base / "deployment", anchor=anchor, required=_required_policy_traversal(), never=never
    )
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

    def child_arguments(self, requirement: Any, request: ProductRequest) -> Mapping[str, str]:
        subject = self._fixed or self._subject
        assert subject is not None, "a child was asked before the composite's request reached it"
        return {"subject": subject, "asked_at": request.asked_at.isoformat(), "threshold": str(THRESHOLD_VALUE)}

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
    never: bool = False,
    project: Any = None,
) -> Deployment:
    """A composite whose child is asked about its own subject, or about a fixed one (channel 4).

    Parent and child are each asked on their own fabric per question, each
    behind a subject-keyed acquisition seam. In a deployment whose source holds
    the subject, both the parent's source and the child's do; the fixed child's
    source holds the fixed subject in every deployment. The parent's Π withholds
    by content (the parent's own view); the child's Π never withholds.
    ``project`` replaces the parent's plan factory (E2 (ii)'s configurations
    only; every shape of the matrix builds the policy's own).
    """
    from ccf.products.composite import CHILD_QUESTION_CLASS  # noqa: PLC0415
    from ccf.products.door import door_answer  # noqa: PLC0415
    from tests.deployment.conftest import POLICY_PARAMS_KEY, TENANT, TRAVERSAL_KEY  # noqa: PLC0415
    from tests.products import composite_fixture as cf  # noqa: PLC0415
    from tests.products.provider_boot import CHILD_CLASS, CHILD_CLASS_KEY, CHILD_REQUEST_CONTRACT_KEY  # noqa: PLC0415
    from tests.products.test_resolver_seam import ASKED_AT, PERSPECTIVE, PRODUCT_CLASS, THRESHOLD_PARAMETER, _Booted  # noqa: PLC0415

    manifest = low_road_documents(
        base / "deployment", anchor=anchor, required=_required_policy_traversal(),
        composite=True, child_anchor=anchor, never=never,
    )
    site = low_road_site(base, manifest, extra_classes=(CHILD_QUESTION_CLASS,), evidence_readable=readable)
    parent_holdings = {SUBJECT: subject_holding()} if holds else {}
    child_holdings = {FIXED: fixed_holding()} if fixed_child else ({SUBJECT: subject_holding()} if holds else {})
    parent_factory = (
        project if project is not None
        else plan_factory(early=early, plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=active)
    )
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
        children.inner = cf.build_child_resolver(
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


def mcp_record_reads(
    deployment: Deployment, reference: str | None, *, raw: dict[str, Any] | None = None
) -> dict[str, Any]:
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
                        decoded = base64.b64decode(contents.blob)
                        parts.append({
                            "blob": _maybe_json(decoded.decode("utf-8", "replace")),
                            "blob_sha256": hashlib.sha256(decoded).hexdigest(),
                        })
                return {"contents": parts}

            read = mcp_drive(mcp_artifact_server(deployment), operation, token=token)
            if raw is not None:
                raw[f"{who}:{name}"] = jsonable(read)
            if isinstance(read, dict):
                for part in read.get("contents", []):
                    # The digest is the read's own measurement, not something it
                    # served: it stays in ``raw`` and out of the compared channel.
                    part.pop("blob_sha256", None)
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
#: Dave's Q12, as built (lane ``378b-s020record`` PROPOSAL section 7, item 1):
#: the record-instrument worlds LIST the class and the class AFFIRMS
#: ``subject_withholding: never``, with the policy OFF — served and nonexistent
#: sides only, plus a second, independent nonexistent copy as their noise
#: floor (the unlisted floor's reads are refused, so it cannot be the floor of
#: a readable pair). The withheld side under ``never`` (WITHHELD_READABLE) is
#: the listed-class cell's, and it is refused by design.
NONEXISTENT_READABLE_FLOOR = "nonexistent-readable-again"
#: For the population-reading shapes (D1 = (a)): the readable serving
#: deployment asked about identifiers nothing holds — the same-deployment record
#: instrument's other side and its noise floor.
SERVED_READABLE_NEVER_HELD = "served-readable-never-held"
SERVED_READABLE_NEVER_HELD_2 = "served-readable-never-held-again"
#: The listed-class cell's other configuration: a class that does NOT affirm
#: ``never``, listed — refused where the resolver is built, in both deployments.
WITHHELD_LISTED_MAY = "withheld-listed-may-withhold"
NONEXISTENT_LISTED_MAY = "nonexistent-listed-may-withhold"
#: The same-deployment instruments (population-reading shapes): the deployment
#: that SERVES the subject (policy off) asked about an identifier nothing holds,
#: and the same question carrying a parameter its class does not declare.
SERVED_NEVER_HELD = "served-deployment-never-held"
REFUSED_NEVER_HELD = "served-deployment-refused-question"

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
    if run.shape == REUSED_STORE:
        # Q9 refuses every question to a store reopened by an ordinary boot, the
        # served subject's included, so no side of this shape SERVES and the
        # served-against-nonexistent pair is equal by the ruling. What the cells
        # must be able to see here is a question the composition answers
        # differently from the refused one: a question the request contract
        # refuses never reaches the claim (``AcquisitionNeedsAQuestionFabric``
        # is raised immediately before the first acquisition phase), so it is
        # set against the nonexistent side's refused composition on every channel.
        return REFUSED_QUESTION, CF_NONEXISTENT
    if channel == RECORD and SERVED_READABLE in run.sides:
        return SERVED_READABLE, NONEXISTENT_READABLE
    if DECLARED_TWIN in run.sides:
        # P2 (c): no side of an undeclared composite answers; the refusal every
        # side observes is set against the same composite declaring a stance.
        return DECLARED_TWIN, CF_NONEXISTENT
    if p6_refused(run):
        # CT-A extended to ruling P6 (a): no probed side answers; the refusal
        # every one observes is set against the declared-population twin answering.
        return POPULATION_TWIN, CF_NONEXISTENT
    return INSTRUMENT_PAIRS[channel]


def instrument_floor(channel: str, run: Run) -> str:
    """The noise-floor side for :func:`instrument_pair`'s right-hand side.

    The readable record pair (Q12) is floored by its own second nonexistent
    copy; every other pair by the counterfactual floor.
    """
    if channel == RECORD and SERVED_READABLE in run.sides and run.shape != REUSED_STORE:
        return NONEXISTENT_READABLE_FLOOR
    return CF_FLOOR


def same_instrument_sides(channel: str, run: Run) -> tuple[str, str, str, str]:
    """``(left, right, floor_a, floor_b)`` of the same-deployment instrument for ``channel``.

    The record channel is instrumented in the readable serving deployment
    (Q12: default-deny refuses every read of the unlisted one alike): the
    subject served against an identifier nothing holds, floored by two such
    identifiers. Every other channel as before.
    """
    if channel == RECORD and SERVED_READABLE_NEVER_HELD in run.sides:
        return SERVED_READABLE, SERVED_READABLE_NEVER_HELD, SERVED_READABLE_NEVER_HELD, SERVED_READABLE_NEVER_HELD_2
    if p6_refused(run):
        # CT-A extended to ruling P6 (a): every question of the deployment is
        # the one refusal, so the comparison is shown it can see the twin's
        # answer (its never-held question) against that refusal.
        return POPULATION_TWIN_NEVER_HELD, SAME_NONEXISTENT, SAME_NONEXISTENT, SAME_FLOOR
    left, right = SAME_INSTRUMENT_PAIRS[channel]
    return left, right, SAME_NONEXISTENT, SAME_FLOOR


#: The same-deployment instrument for each channel (population-reading shapes,
#: D1 = (a)): two questions to ONE deployment that must be seen to differ. The
#: subject SERVED against an identifier nothing holds; for refusal codes and the
#: reference, a question the request contract refuses (it reads nothing, so its
#: record is named for an empty read) against the identifier nothing holds —
#: because in a population-reading deployment every question that reads, reads
#: the same population, and a served subject's record name equals a never-held
#: identifier's (measured: ``same`` reference cells of these shapes).
SAME_INSTRUMENT_PAIRS: dict[str, tuple[str, str]] = {
    RESPONSE: (SERVED, SERVED_NEVER_HELD),
    REFUSAL: (REFUSED_NEVER_HELD, SERVED_NEVER_HELD),
    REFERENCE: (REFUSED_NEVER_HELD, SERVED_NEVER_HELD),
    RECORD: (SERVED, SERVED_NEVER_HELD),
}


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
    if door in (HTTP, MCP) and (comparison == COUNTERFACTUAL or shape in POPULATION_READING_SHAPES):
        # D1 = (a): for a population-reading shape the same-deployment comparison
        # governs every observable, the record read back included. Both records
        # hold their own request, so what differs only because the identifiers
        # differ is in the noise floor (two identifiers nothing holds), and every
        # other path is compared.
        channels.append(RECORD)
    return tuple(channels)


#: The one refusal each reused shape's cells may be green on, and at which positions (Dave, Q9).
REUSE_REFUSALS: dict[str, tuple[str, tuple[str, ...]]] = {
    # One handle booted for a question: the first question claims it, the second is refused.
    REUSED_FABRIC: ("AcquiredFabricReused", ("second",)),
    # A persisted store reopened by an ordinary boot: never a question fabric, every question refused.
    REUSED_STORE: ("AcquisitionNeedsAQuestionFabric", ("first", "second")),
}


#: ``D-IMPL-378`` P2, option (c), ruled by Dave on 2026-10-08 at 12:29 MST: a
#: composite that declares no withholding stance (no early policy, no
#: ``subject_withholding: never``) is refused where its resolver is built,
#: before any question, by this name. The late-composite shapes declare none, so
#: under (c) every question of theirs is that refusal — the same whatever subject
#: is asked — and, as Q9's reuse refusals are for the reused shapes, the refusal
#: IS the property their cells hold. Read only where the refusal exists.
CONSTRUCTION_REFUSALS: dict[str, str] = {
    COMPOSITE_SUBJECT_CHILD: "CompositeNeedsAWithholdingStance",
    COMPOSITE_FIXED_CHILD: "CompositeNeedsAWithholdingStance",
}

#: The instrument side of a shape refused at construction: the same composite
#: with an early policy declared that withholds nothing — a stance, so it is
#: built, and its question is answered — asked what the nonexistent side asks.
DECLARED_TWIN = "declared-twin"


def stance_refusal_exists() -> bool:
    """Whether P2 (c)'s construction refusal exists under its name."""
    import ccf.products.resolver as resolver  # noqa: PLC0415

    return hasattr(resolver, "CompositeNeedsAWithholdingStance")


def refused_at_construction(shape: str) -> bool:
    """Whether every question of ``shape`` is P2 (c)'s construction refusal on this tree."""
    return shape in CONSTRUCTION_REFUSALS and stance_refusal_exists()


# --- CT-A extended to ruling P6 (a) ---------------------------------------------------------
#
# Dave, 2026-10-08 16:40 MST (D-IMPL-378), item 2, verbatim (kept as a comment, CINV-01a):
#   "P6: (a), conditional implementation GO. Amend Q10 to permit the probe.
#   Extend CT-A with the working declared-population twin. Do not declare
#   closure based on this probe alone: ..."
# CT-A (a), Dave, 2026-10-08 12:29 MST: "Construction refusal counts, paired
# with a declared twin that successfully answers."

#: Ruling P6 (a)'s refusal (``ccf.products.resolver.PopulationReadInSubjectKeyedPhase``),
#: raised for every question of a class that may withhold, declares no early
#: policy and reads its population inside the subject-keyed phase — decided by
#: the probe, never by the subject. Every deployment of the ``population`` shape
#: reads that way.
P6_REFUSAL = "PopulationReadInSubjectKeyedPhase"
P6_REFUSED_SHAPES = (POPULATION,)
#: The sides of such a run whose deployment the probe reads: every side but the
#: questions their request contract refuses before acquisition
#: (:data:`REFUSED_QUESTION`, :data:`REFUSED_NEVER_HELD`) and the readable
#: worlds, whose class affirms ``never``.
P6_PROBED_SIDES = (CF_WITHHELD, SAME_NONEXISTENT, SAME_FLOOR, CF_NONEXISTENT, CF_FLOOR, SERVED, SERVED_NEVER_HELD)
#: The declared-population twin: the same source, its whole-population read
#: declared as the population phase through ``open_product(population=...)`` —
#: the ``population_declared`` world (:data:`BUILDERS`) — holding the subject and
#: withholding it from the asker exactly as the shape's withholding deployment
#: does, asked about the subject and about an identifier nothing holds.
POPULATION_TWIN = "declared-population-twin"
POPULATION_TWIN_NEVER_HELD = "declared-population-twin-never-held"


def probe_refusal_exists() -> bool:
    """Whether ruling P6 (a)'s refusal exists under its name."""
    import ccf.products.resolver as resolver  # noqa: PLC0415

    return hasattr(resolver, P6_REFUSAL)


def p6_refused(run: Run) -> bool:
    """CT-A extended to ruling P6 (a): whether this run's P6 refusal is the property its cells hold.

    True only when ALL of these hold: the run is of a shape in
    :data:`P6_REFUSED_SHAPES` on a tree that has the refusal; every probed side
    (:data:`P6_PROBED_SIDES`) ended its one question in that refusal, by type
    name, with ONE message among them all (so the refusal is the same whatever
    subject was asked, and whether or not the source holds it); and the
    declared-population twin ANSWERED both its questions — served, or refused
    as data — raising nothing. Anything less and every raise in the run stays
    "not evidence", as everywhere in this proof.
    """
    if run.shape not in P6_REFUSED_SHAPES or not probe_refusal_exists():
        return False
    if POPULATION_TWIN not in run.sides or POPULATION_TWIN_NEVER_HELD not in run.sides:
        return False
    refusals = {run.raised(side).get(ONLY, "") for side in P6_PROBED_SIDES}
    if len(refusals) != 1 or not next(iter(refusals)).startswith(f"{P6_REFUSAL}:"):
        return False
    return not run.raised(POPULATION_TWIN) and not run.raised(POPULATION_TWIN_NEVER_HELD)


def p6_refusal_is_the_property(run: Run, position: str, raised: str) -> bool:
    """Whether a side raising ``raised`` at ``position`` is ruling P6 (a)'s refusal, held as the property.

    Only at the question's own position (a raise inside a record read never
    is), only that refusal by type name, and only where :func:`p6_refused`
    holds for the whole run.
    """
    return position == ONLY and raised.startswith(f"{P6_REFUSAL}:") and p6_refused(run)


def raising_is_the_property(shape: str, position: str, raised: str) -> bool:
    """Whether a side raising ``raised`` at ``position`` is what the cell is meant to show.

    Only where a refusal of the composition IS the property under test (Dave,
    Q9), and only THAT refusal, named by type: the second question to one
    question fabric (``AcquiredFabricReused``), and every question to a
    persisted store an acquisition phase would write into
    (``AcquisitionNeedsAQuestionFabric``). Anything else — another position,
    another exception (a broken builder raising ``TypeError`` would otherwise
    pass as "refused") — proves nothing about indistinguishability, and a cell
    that sees it is not green. A raise inside a record read (key
    ``<position>/record:<read>``) is never the property.
    """
    if "/" in position:
        return False
    if refused_at_construction(shape):
        return position == ONLY and raised.startswith(f"{CONSTRUCTION_REFUSALS[shape]}:")
    if shape not in REUSE_REFUSALS:
        return False
    refusal, positions = REUSE_REFUSALS[shape]
    return position in positions and raised.startswith(f"{refusal}:")


def comparisons_for(shape: str) -> tuple[str, ...]:
    """The comparisons that GOVERN a shape in the closure gate.

    A fabric or store that outlives the question is compared as a counterfactual
    only: its point is the sequence. A population-reading shape is compared in
    the same deployment only (Dave's D1 = (a), :data:`D1A_RULING`): its
    two-deployment cells are retired from the gate, and the test module lists
    them by id. Every other shape keeps both.
    """
    if shape in REUSED_SHAPES:
        return (COUNTERFACTUAL,)
    if shape in POPULATION_READING_SHAPES:
        return (SAME_DEPLOYMENT,)
    return COMPARISONS


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
    for position, observation in zip(("first", "second"), observations, strict=True):
        for key, message in observation.raised.items():
            merged.raised[position + key[len(ONLY):]] = message
        merged.reference_facts.update(observation.reference_facts)
        for key, check in observation.read_check.items():
            merged.read_check[position + key[len(ONLY):]] = check
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
        observation.reference_facts = _reference_facts(deployment, observation)
        if reads and door == HTTP:
            raw_reads: dict[str, Any] = {}
            observation.channels[RECORD] = http_record_reads(deployment, reference, app=app, raw=raw_reads)
            observation.read_check[ONLY] = {"handed_out": reference, "presented": reference, "reads": raw_reads}
            for read, answered in observation.channels[RECORD].items():
                status = answered.get("status") if isinstance(answered, dict) else None
                if isinstance(status, int) and status >= 500:
                    observation.raised[f"{ONLY}/record:{read}"] = f"HTTP {status}: {str(answered.get('body'))[:300]}"
        if reads and door == MCP:
            raw_reads = {}
            observation.channels[RECORD] = mcp_record_reads(deployment, reference, raw=raw_reads)
            observation.read_check[ONLY] = {"handed_out": reference, "presented": reference, "reads": raw_reads}
            for read, answered in observation.channels[RECORD].items():
                if _mcp_read_failed(answered):
                    observation.raised[f"{ONLY}/record:{read}"] = f"MCP read failed: {render(answered, limit=300)}"
        observed.append(observation)
    return _merge(observed)


def references_in(value: Any) -> set[str]:
    """Every replay reference (a ``ccf-artifact://`` URI) anywhere in a channel value."""
    if isinstance(value, str):
        return {value} if value.startswith("ccf-artifact://") else set()
    found: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            found |= references_in(item)
    elif isinstance(value, list | tuple):
        for item in value:
            found |= references_in(item)
    return found


def _reference_facts(deployment: Deployment, observation: Observation) -> dict[str, dict[str, str]]:
    """What the deployment's own store says each reference this question was handed names."""
    facts: dict[str, dict[str, str]] = {}
    for reference in sorted(references_in(jsonable(observation.channels.get(REFERENCE)))):
        try:
            parsed = parse_artifact_uri(reference)
            address = deployment.store.resolve_uri(uri=reference)
            stored = deployment.store.get(content_address=address)
        except Exception as unresolved:  # noqa: BLE001 — a reference that does not resolve is a finding
            facts[reference] = {"error": f"{type(unresolved).__name__}: {unresolved}"}
            continue
        facts[reference] = {
            "name": parsed.name,
            "version": parsed.artifact_version,
            "resolved": address,
            "sha256": hashlib.sha256(stored).hexdigest(),
            # E1 (a): the per-answer issuance the record carries, read as an
            # auditor would, so the pooled test can hold the two sides' issuances
            # to one distribution as well as their references.
            "issuance": DecisionReplayRecord.model_validate_json(stored).content_generation_path.issuance,
        }
    return facts


def _references_by_position(run: Run, side: str) -> dict[str, set[str]]:
    value = jsonable(run.sides[side].channels.get(REFERENCE))
    if run.shape in REUSED_SHAPES:
        positions = value if isinstance(value, dict) else {}
        return {position: references_in(positions.get(position)) for position in ("first", "second")}
    return {ONLY: references_in(value)}


def reference_properties(run: Run) -> list[str]:
    """Dave's Q11 properties of the references this run handed out; every violation, named.

    Dave, Q11: *"Equal public references must not identify different immutable
    record contents."* The lane ``378b-s020record`` design (PROPOSAL section 7,
    item 2) makes each reference unique per answer, so a difference-based
    instrument cannot see past the noise floor on this channel by design; these
    checks replace it.

    1. **Issued per answer.** Two copies of one deployment asked the same
       question at the same instant (:data:`CF_NONEXISTENT`, :data:`CF_FLOOR`)
       are handed different references at every position both answered.
    2. **One reference, one record.** Every reference any side was handed names
       one record: equal references never name different bytes.
    3. **Name = version = the record's content address**: the URI's two
       identifying segments, the address the store resolves it to, and the
       SHA-256 of the bytes stored there are one identity.

    Not evidence, as everywhere in this proof: a position where either copy
    raised (other than a refusal that is the property, :func:`raising_is_the_property`)
    is reported, and a run in which property 1 was measured at no position fails.
    """
    problems: list[str] = []
    left = _references_by_position(run, CF_NONEXISTENT)
    right = _references_by_position(run, CF_FLOOR)
    measured = 0
    for position in sorted(left):
        raised = {side: run.raised(side).get(position) for side in (CF_NONEXISTENT, CF_FLOOR)}
        if any(raised.values()):
            if all(message and raising_is_the_property(run.shape, position, message) for message in raised.values()):
                continue
            problems.append(f"property 1 not evidence at {position}: a copy raised: {raised}")
            continue
        if not left[position] or not right[position]:
            problems.append(
                f"property 1 not measurable at {position}: an answer carried no reference"
                f" ({sorted(left[position])} / {sorted(right[position])})"
            )
            continue
        measured += 1
        shared = left[position] & right[position]
        if shared:
            problems.append(
                f"property 1 at {position}: the same question, asked of two copies of one deployment at one"
                f" instant, was handed the same reference twice: {sorted(shared)}"
            )
    if not measured:
        problems.append("property 1 was measured at no position")
    digests: dict[str, set[str]] = {}
    for side, observation in sorted(run.sides.items()):
        for reference, facts in sorted(observation.reference_facts.items()):
            if "error" in facts:
                problems.append(f"{side}: {reference} does not resolve in its own deployment's store: {facts['error']}")
                continue
            digests.setdefault(reference, set()).add(facts["sha256"])
            if not facts["name"] == facts["version"] == facts["resolved"] == facts["sha256"]:
                problems.append(
                    f"property 3, {side}: name {facts['name']}, version {facts['version']}, resolved"
                    f" {facts['resolved']}, SHA-256 of the stored record {facts['sha256']} are not one identity"
                )
    for reference, found in sorted(digests.items()):
        if len(found) > 1:
            problems.append(f"property 2: {reference} names {len(found)} different records")
    if not digests:
        problems.append("no side was handed a reference that resolves")
    return problems


def _mcp_read_failed(answered: Any) -> bool:
    """Whether one MCP record read ended in a failure rather than an answer.

    A governed answer on these reads — the record, or a refusal of it — comes
    back as resource contents or as a tool result; a protocol error, an
    unreachable server, or the opaque ``ccf-runtime-failure:<id>`` is a
    failure, and two equal failures are not evidence (none is observed on
    ``b2393d2d``; the check keeps a future one from passing as an answer).
    """
    if not isinstance(answered, dict):
        return False
    if "error" in answered or "unreachable" in answered:
        return True
    texts = answered.get("text") if answered.get("is_error") else None
    return isinstance(texts, list) and any(
        isinstance(text, str) and text.startswith("ccf-runtime-failure") for text in texts
    )


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

    def raised(self, side: str) -> dict[str, str]:
        """Per question position, the exception ``side``'s question ended in, if any."""
        return dict(self.sides[side].raised)

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

    def listed(name: str, *, holds: bool, active: bool, never: bool) -> Deployment | Exception:
        """A deployment whose tenant LISTS the class for owner read-back (Q12).

        A composition the SDK refuses while it is being built is an observation,
        not a broken run: it is returned, and every question to it observes it.
        """
        try:
            built = build(base / name, anchor=anchor, holds=holds, active=active, readable=True, never=never)
        except Exception as refused:  # noqa: BLE001 — a refused composition is an observation
            return refused
        opened.append(built)
        return built

    def listed_side(built: Deployment | Exception, subject: str) -> Observation:
        if isinstance(built, Exception):
            return refused_at_build(shape, built, subject)
        return observe_side(shape, door, built, subject, reads=True)

    try:
        withholding = deployment("withholding", holds=True, active=True)
        sides[CF_WITHHELD] = observe_side(shape, door, withholding, SUBJECT, reads=True)
        if SAME_DEPLOYMENT in comparisons_for(shape):
            same_reads = shape in POPULATION_READING_SHAPES
            sides[SAME_NONEXISTENT] = observe_side(shape, door, withholding, NEVER, reads=same_reads)
            sides[SAME_FLOOR] = observe_side(shape, door, withholding, NEVER_2, reads=same_reads)
        sides[CF_NONEXISTENT] = observe_side(
            shape, door, deployment("not-holding", holds=False, active=True), SUBJECT, reads=True
        )
        sides[CF_FLOOR] = observe_side(
            shape, door, deployment("not-holding-again", holds=False, active=True), SUBJECT, reads=True
        )
        serving = deployment("serving", holds=True, active=False)
        sides[SERVED] = observe_side(shape, door, serving, SUBJECT, reads=True)
        if shape in POPULATION_READING_SHAPES:
            sides[SERVED_NEVER_HELD] = observe_side(shape, door, serving, NEVER, reads=True)
            sides[REFUSED_NEVER_HELD] = observe_side(
                shape, door, serving, NEVER, parameters=violating_parameters()
            )
        sides[REFUSED_QUESTION] = observe_side(
            shape, door, deployment("refusing", holds=False, active=True), SUBJECT,
            parameters=violating_parameters(),
        )
        if refused_at_construction(shape):
            twin = build(base / "declared-twin", anchor=anchor, holds=False, active=False, early=True)
            opened.append(twin)
            sides[DECLARED_TWIN] = observe_side(shape, door, twin, SUBJECT, reads=True)
        if shape in P6_REFUSED_SHAPES and probe_refusal_exists():
            # CT-A extended to ruling P6 (a): the declared-population twin, the
            # same source and the same withholding, its read declared.
            population_twin = BUILDERS[POPULATION_DECLARED](
                base / "declared-population-twin", anchor=anchor, holds=True, active=True
            )
            opened.append(population_twin)
            sides[POPULATION_TWIN] = observe_side(shape, door, population_twin, SUBJECT, reads=True)
            sides[POPULATION_TWIN_NEVER_HELD] = observe_side(shape, door, population_twin, NEVER, reads=True)
        if door in (HTTP, MCP) and evidence_allowlist_exists():
            # Dave's Q12 as built: the record instrument's worlds list the class
            # AND the class affirms ``never``, policy off — served and nonexistent
            # sides only, with their own nonexistent floor.
            serving_readable = listed("serving-readable", holds=True, active=False, never=True)
            sides[SERVED_READABLE] = listed_side(serving_readable, SUBJECT)
            for side, name in (
                (NONEXISTENT_READABLE, "not-holding-readable"),
                (NONEXISTENT_READABLE_FLOOR, "not-holding-readable-again"),
            ):
                sides[side] = listed_side(listed(name, holds=False, active=False, never=True), SUBJECT)
            if shape in POPULATION_READING_SHAPES:
                sides[SERVED_READABLE_NEVER_HELD] = listed_side(serving_readable, NEVER)
                sides[SERVED_READABLE_NEVER_HELD_2] = listed_side(serving_readable, NEVER_2)
            if shape in LISTED_SHAPES:
                # The listed-class cell: the withheld subject under ``never`` (refused
                # by design), and a class that does not affirm it, listed, in both
                # deployments (refused where the resolver is built).
                sides[WITHHELD_READABLE] = listed_side(
                    listed("withholding-readable", holds=True, active=True, never=True), SUBJECT
                )
                sides[WITHHELD_LISTED_MAY] = listed_side(
                    listed("withholding-listed", holds=True, active=True, never=False), SUBJECT
                )
                sides[NONEXISTENT_LISTED_MAY] = listed_side(
                    listed("not-holding-listed", holds=False, active=True, never=False), SUBJECT
                )
    finally:
        for built in opened:
            built.close()
    return Run(shape=shape, anchor=anchor, door=door, sides=sides)


def probe_recognizing_run(base: pathlib.Path, *, recognition: str, anchor: str, door: str) -> Run:
    """Ruling P6 (a)'s counterexample deployment, asked what the same-deployment comparison asks.

    One deployment holding the subject and withholding it from the asker, its
    source recognizing the probe (:class:`ProbeRecognizingPopulationSource`):
    the withheld subject, an identifier nothing holds, and a second one (the
    noise floor), through ``door``, records read back where that door reads
    them — the sides :data:`PAIRS` names for the same-deployment comparison.
    ``notes`` keeps what the source was asked and what it answered nothing
    for: the evidence the case was constructed. Labeled
    :data:`PROBE_RECOGNIZING`, outside every gate shape.
    """
    built = build_probe_recognizing(
        base / "withholding", anchor=anchor, holds=True, active=True, recognition=recognition
    )
    try:
        sides = {
            CF_WITHHELD: observe_side(POPULATION, door, built, SUBJECT, reads=True),
            SAME_NONEXISTENT: observe_side(POPULATION, door, built, NEVER, reads=True),
            SAME_FLOOR: observe_side(POPULATION, door, built, NEVER_2, reads=True),
        }
        source = built.notes["opened"]._acquire
        notes = {"asked": list(source.asked), "answered_nothing_for": list(source.answered_nothing_for)}
    finally:
        built.close()
    return Run(shape=PROBE_RECOGNIZING, anchor=anchor, door=door, sides=sides, notes=notes)


def refused_at_build(shape: str, refused: Exception, subject: str) -> Observation:
    """What every question to a deployment the SDK refused to build observes: that refusal, by type."""
    shape_of = {"outcome": "raised", "type": type(refused).__name__, "message": str(refused)}
    per_question = [
        Observation(
            channels={RESPONSE: shape_of, REFUSAL: shape_of, REFERENCE: shape_of, RECORD: {"reference": None}},
            raw=refused,
            raised={ONLY: f"{type(refused).__name__}: {refused}"},
        )
        for _asked in _questions(shape, subject)
    ]
    return _merge(per_question)


#: The shapes the listed-class cell is held on (Dave's Q12: *"Reject withholding
#: classes—including affected composites"*): the paved road and a composite.
LISTED_SHAPES = (SUBJECT_KEYED, COMPOSITE_SUBJECT_CHILD)


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


# =============================================================================
# E2 (ii): a class that affirms ``never`` whose projection withholds anyway
# =============================================================================
#
# Dave, 2026-10-08 12:29 MST (``D-IMPL-378``), on the owed ruling E2 (ii),
# verbatim: "E2 (ii) REJECTED as disclosure-only: The proposed hidden-subject
# exception versus nonexistent-subject 200 is a measured oracle. Validate
# withholding capability against the class declaration at construction; retain
# the runtime check as defense. Keep the violation probe visible until the
# treatment satisfies the closure criterion." And CT-D (a): "for diagnostic
# precedence; this does not resolve E2(ii)'s oracle." Kept as a comment, not a
# string literal, for D1A_RULING's reason.
#
# One configuration per way a class affirming ``subject_withholding: never``
# can meet a projection that withholds. Every deployment of a configuration
# LISTS its class for owner read-back (Q12) — the reason a class affirms
# ``never`` — so the record channel is observed as well; an unlisted ``never``
# class shows a subset of these observables (its records are sealed alike).

#: The plan factory declares nothing — no early policy, no late withholding, no
#: positive declaration (:class:`SilentPolicyPlanFactory`); its projection
#: withholds late, by content. Under Dave's E2 (ii) (d) silence is refused.
NEVER_LATE = "never_late"
#: The plan factory declares an early policy that does not disclose the subject (Q8).
NEVER_EARLY = "never_early"
#: The plan factory declares that its projection withholds late (``subject_disclosure()`` returns ``None``).
NEVER_DECLARED_LATE = "never_declared_late"
#: A composite: the plan factory declares nothing (:class:`SilentPolicyPlanFactory`);
#: its projection withholds late.
NEVER_COMPOSITE_LATE = "never_composite_late"
#: A composite: the plan factory declares an early policy that does not disclose the subject.
NEVER_COMPOSITE_EARLY = "never_composite_early"

#: Each configuration and the matrix shape whose doors, channels and observations it follows.
NEVER_CONFIGURATIONS: dict[str, str] = {
    NEVER_LATE: SUBJECT_KEYED,
    NEVER_EARLY: EARLY_SUBJECT_KEYED,
    NEVER_DECLARED_LATE: SUBJECT_KEYED,
    NEVER_COMPOSITE_LATE: COMPOSITE_SUBJECT_CHILD,
    NEVER_COMPOSITE_EARLY: EARLY_COMPOSITE_SUBJECT_CHILD,
}

# Dave's E2 (ii), option (d), 2026-10-08 16:40 MST (``D-IMPL-378``), verbatim:
# "Require a positive declaration, default silence to refusal, and explicitly
# limit the trusted-code assumption to deployment code callers cannot
# influence. Keep the false-declaration counterexample visible." The positive
# declaration is trusted deployment code, so a FALSE one is the residual: the
# class is built, and its withheld subject meets the serve-time defense. These
# configurations are that residual. They are NOT in NEVER_CONFIGURATIONS and
# generate no gate cell: the closing test measures them on every run and
# reports them in their own block, never as passing evidence.

#: The plan factory positively declares that its projection never withholds,
#: and the projection withholds late, by content (:class:`FalselyDeclaringPolicyPlanFactory`).
NEVER_FALSE_DECLARATION = "never_false_declaration"
#: A composite over the same false declaration.
NEVER_COMPOSITE_FALSE_DECLARATION = "never_composite_false_declaration"

#: E2 (ii) (d)'s residual configurations and the matrix shape each follows — reported, never gated.
NEVER_FALSE_DECLARATION_CONFIGURATIONS: dict[str, str] = {
    NEVER_FALSE_DECLARATION: SUBJECT_KEYED,
    NEVER_COMPOSITE_FALSE_DECLARATION: COMPOSITE_SUBJECT_CHILD,
}


def never_shape(configuration: str) -> str:
    """The matrix shape an E2 (ii) configuration follows, gated or reported."""
    if configuration in NEVER_FALSE_DECLARATION_CONFIGURATIONS:
        return NEVER_FALSE_DECLARATION_CONFIGURATIONS[configuration]
    return NEVER_CONFIGURATIONS[configuration]

#: The refusal, by name, of a class affirming ``never`` whose projection the SDK
#: knows can withhold, raised where its resolver is built (E2 (ii)). Read by
#: NAME so this module imports on a tree without it. Where every side of a
#: comparison observes exactly this refusal, the cell holds it as the property
#: under test, paired with :data:`NEVER_TWIN` answering — Dave's CT-A (a),
#: 2026-10-08 12:29 MST: "Construction refusal counts, paired with a declared
#: twin that successfully answers."
NEVER_CAPABILITY_REFUSAL = "NeverWithholdingProjectionCanWithhold"

#: The refusal, by name, of a class affirming ``never`` whose plan factory does
#: NOT positively declare that it never withholds — silence included (Dave's
#: E2 (ii), option (d), 2026-10-08 16:40 MST) — raised where its resolver is
#: built, after the refusal above. A subclass of it, read by NAME for the same
#: reason.
NEVER_DECLARATION_REFUSAL = "NeverWithholdingNeedsAPositiveDeclaration"

#: The construction refusals an E2 (ii) cell may hold as the property under
#: test — under CT-A (a), and only when EVERY compared side observed the SAME
#: one (:func:`never_refused_at_construction`) and :data:`NEVER_TWIN` answers.
NEVER_CONSTRUCTION_REFUSALS = (NEVER_CAPABILITY_REFUSAL, NEVER_DECLARATION_REFUSAL)

#: The configuration with its withholding capability removed — the policy off,
#: positively declaring that it never withholds (Dave's E2 (ii) (d),
#: :meth:`PolicyPlanFactory.withholds_no_subject`), and for the early
#: configurations an early policy that withholds nobody — in a deployment whose
#: source holds the subject: it must SERVE the subject. The declared twin a
#: construction refusal is paired with (CT-A (a)), and every channel's instrument.
NEVER_TWIN = "never-twin"


class SilentPolicyPlanFactory:
    """:class:`PolicyPlanFactory`'s projection, behind a factory that declares NOTHING.

    No early policy, no late withholding, and no positive declaration that it
    never withholds: the silence Dave's E2 (ii) (d) counts as able to withhold.
    It composes the policy's factory rather than inheriting it, so it carries
    none of that factory's declarations.
    """

    def __init__(self, *, plan_id: str, asker: str, active: bool) -> None:
        self._policy = PolicyPlanFactory(plan_id=plan_id, asker=asker, active=active)

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> PolicyProjection:
        return self._policy(required=required, request=request)


class FalselyDeclaringPolicyPlanFactory(PolicyPlanFactory):
    """The policy's factory declaring that it never withholds WHATEVER ``active`` says: FALSE with the policy on.

    A broken deployment, on purpose — the residual of the trusted-code
    assumption Dave's E2 (ii) (d) makes explicit, kept visible.
    """

    def withholds_no_subject(self) -> bool:
        return True


class LateDeclaringPlanFactory(PolicyPlanFactory):
    """A plan factory DECLARING that its projection withholds late (``SubjectDisclosingPlanFactoryProtocol``).

    ``subject_disclosure()`` returns ``None``: the statement that the
    projection withholds only inside itself, after its plan has run. Its
    projection is :class:`PolicyProjection`, which withholds by content.
    """

    def subject_disclosure(self) -> Any:
        return None


def build_never(
    base: pathlib.Path, *, configuration: str, anchor: str, holds: bool, capable: bool
) -> Deployment:
    """One deployment of ``configuration``: its class affirms ``never`` and its tenant lists the class.

    ``capable`` builds the configuration as named (the policy on); otherwise
    its :data:`NEVER_TWIN`: the policy off, positively declaring that it never
    withholds, and, for the early configurations, an early policy that
    withholds nobody. The two late configurations are built over
    :class:`SilentPolicyPlanFactory` — silence, not a declaration — and the two
    false-declaration configurations over :class:`FalselyDeclaringPolicyPlanFactory`.
    """
    shape = never_shape(configuration)
    silent = capable and configuration in (NEVER_LATE, NEVER_COMPOSITE_LATE)
    false = capable and configuration in NEVER_FALSE_DECLARATION_CONFIGURATIONS
    if shape in COMPOSITE_SHAPES:
        from tests.products.test_resolver_seam import PERSPECTIVE, PRODUCT_CLASS  # noqa: PLC0415

        project: Any = None
        if silent:
            project = SilentPolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=capable)
        elif false:
            project = FalselyDeclaringPolicyPlanFactory(
                plan_id=PRODUCT_CLASS, asker=PERSPECTIVE.principal_id, active=capable
            )
        return BUILDERS[shape](
            base, anchor=anchor, holds=holds, active=capable, readable=True, never=True, project=project
        )
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    kind: type[PolicyPlanFactory] | type[SilentPolicyPlanFactory] = PolicyPlanFactory
    if configuration == NEVER_EARLY:
        kind = EarlyWithholdingPlanFactory
    elif configuration == NEVER_DECLARED_LATE and capable:
        kind = LateDeclaringPlanFactory
    elif silent:
        kind = SilentPolicyPlanFactory
    elif false:
        kind = FalselyDeclaringPolicyPlanFactory
    holdings = {SUBJECT: subject_holding()} if holds else {}
    return open_paved(
        base, anchor=anchor, acquire=SubjectKeyedSource(holdings),
        project=kind(plan_id=PRODUCT_CLASS, asker=ASKER, active=capable),
        evidence_readable=True, never=True,
    )


def never_run(base: pathlib.Path, *, configuration: str, anchor: str, door: str) -> Run:
    """Every side one (configuration, anchor, door) of E2 (ii) needs, asked once, then closed.

    The sides keep :data:`PAIRS`' names, so the closing test compares them with
    its own rules: the withheld subject (a deployment holding it, the policy
    on), the same question to a deployment that does not hold it and to a
    second copy (the noise floor), the withholding deployment asked about two
    identifiers nothing holds, :data:`NEVER_TWIN`, and the question its class
    refuses by contract (the refusal channel's instrument). A deployment the
    SDK refuses while it is being built is an observation, as in :func:`run_sides`.
    """
    shape = never_shape(configuration)
    sides: dict[str, Observation] = {}
    opened: list[Deployment] = []

    def deployment(name: str, *, holds: bool, capable: bool) -> Deployment | Exception:
        try:
            built = build_never(base / name, configuration=configuration, anchor=anchor, holds=holds, capable=capable)
        except Exception as refused:  # noqa: BLE001 — a refused composition is an observation
            return refused
        opened.append(built)
        return built

    def side(
        built: Deployment | Exception, subject: str, *, reads: bool = True,
        parameters: Mapping[str, Any] | None = None,
    ) -> Observation:
        if isinstance(built, Exception):
            return refused_at_build(shape, built, subject)
        return observe_side(shape, door, built, subject, reads=reads, parameters=parameters)

    try:
        withholding = deployment("withholding", holds=True, capable=True)
        sides[CF_WITHHELD] = side(withholding, SUBJECT)
        sides[SAME_NONEXISTENT] = side(withholding, NEVER, reads=False)
        sides[SAME_FLOOR] = side(withholding, NEVER_2, reads=False)
        sides[CF_NONEXISTENT] = side(deployment("not-holding", holds=False, capable=True), SUBJECT)
        sides[CF_FLOOR] = side(deployment("not-holding-again", holds=False, capable=True), SUBJECT)
        sides[NEVER_TWIN] = side(deployment("twin", holds=True, capable=False), SUBJECT)
        # The refusal channel's instrument, as in :func:`run_sides`: the question
        # carrying a parameter its class does not declare, refused by contract.
        sides[REFUSED_QUESTION] = side(
            deployment("refusing", holds=False, capable=True), SUBJECT, parameters=violating_parameters()
        )
    finally:
        for built in opened:
            built.close()
    return Run(shape=shape, anchor=anchor, door=door, sides=sides, notes={"configuration": configuration})


def never_refused_at_construction(run: Run, sides: tuple[str, ...]) -> bool:
    """Whether every one of ``sides`` observed the SAME one of :data:`NEVER_CONSTRUCTION_REFUSALS`, by name.

    The same one: two sides refused by two different construction refusals
    would be told apart by the refusal's name.
    """
    return any(
        all(run.raised(side).get(ONLY, "").startswith(f"{name}:") for side in sides)
        for name in NEVER_CONSTRUCTION_REFUSALS
    )


class NeverRunCache:
    """One E2 (ii) run per (configuration, anchor, door) for the whole session."""

    def __init__(self, factory: Callable[[str], pathlib.Path]) -> None:
        self._factory = factory
        self._runs: dict[tuple[str, str, str], Run] = {}

    def get(self, *, configuration: str, anchor: str, door: str) -> Run:
        key = (configuration, anchor, door)
        if key not in self._runs:
            self._runs[key] = never_run(
                self._factory("-".join(key)), configuration=configuration, anchor=anchor, door=door
            )
        return self._runs[key]


# =============================================================================
# X17 (a): the pin channel, every pin filed in only ONE of the two deployments
# =============================================================================
#
# Dave, 2026-10-09 06:06 MST (D-IMPL-378), item 1, confirmed at 06:21 MST ("X17(a)"), verbatim (kept as a comment,
# CINV-01a): "A; fix F1-1b and F1-1c now; X17(a). Approve the names behavior amendments explicitly. Cover versioned
# resolution and write-then-read in the closure gate. Keep attacker address derivation labeled unproven until
# demonstrated; it does not excuse the inconsistent authorization." Option (a) is lane 378h-names's P-2, verbatim:
# "Add the channel with every read. The gate goes red on the resolution resource until that is addressed."
#
# A record names the executed-query pins its walk issued (``content_generation_path.graph_query_sequence``). A pin is
# the content hash of its query and is filed in the deployment's store; a record can also name a pin that was never
# filed (at this tree a refused answer's: the closing test's census reports, every run, the pins a run's records name
# that are filed in neither deployment). Two deployments asked the same question can therefore file different pins,
# and a surface that answers a present address differently from an absent one tells the two deployments apart. The
# closing test reads every pin filed in exactly one of the counterfactual's two deployments,
# as the asker, in both and in the noise floor's copy, and compares the readings with the gate's own rules
# (``test_sec020_combined_proof.test_a_pin_filed_in_one_deployment_reads_alike_in_both``).

#: The pin channel's name in the per-pin runs the closing test compares.
PIN = "pin"

#: The surfaces a pin is read at through the record channel's own reads (:func:`mcp_record_reads`,
#: :func:`http_record_reads`: as the asker, keyed ``owner`` there, and as another principal of the tenant), each with
#: the read key it is. The resolution reads are by versioned URI; every other read is by content address.
PIN_READ_SURFACES: dict[str, str] = {
    "mcp-names": "names",
    "mcp-blob": "blob",
    "mcp-presence": "meta",
    "mcp-resolution": "resolution",
    "http-artifact": "artifact",
    "http-replay-decisions": "replay.decisions",
    "http-replay-resolutions": "replay.resolutions",
}

#: Write-then-read, as the asker: its ``put_artifact`` of the pin's canonical bytes on its own client lane, then its
#: three reads at the pin's address.
PIN_WRITE_THEN_READ_SURFACES: dict[str, str] = {
    "write-then-read-put": "put",
    "write-then-read-blob": "blob",
    "write-then-read-presence": "meta",
    "write-then-read-names": "names",
}

#: Every surface of the pin channel, one closing-test cell each per shape and anchor.
PIN_SURFACES: tuple[str, ...] = (*PIN_READ_SURFACES, *PIN_WRITE_THEN_READ_SURFACES)

#: The asker's own client lane: a class no deployment here declares, and the name it files a pin's bytes under.
PIN_CLIENT_CLASS = "fixture.pin-client-lane"
PIN_CLIENT_NAME = "pin-candidate"

#: The counterfactual's three deployments, as :func:`run_sides` builds them: (side, directory, holds the subject).
PIN_DEPLOYMENTS: tuple[tuple[str, str, bool], ...] = (
    (CF_WITHHELD, "withholding", True),
    (CF_NONEXISTENT, "not-holding", False),
    (CF_FLOOR, "not-holding-again", False),
)


def pins_named(deployment: Deployment, observation: Observation) -> tuple[str, ...]:
    """Every executed-query pin named by the records behind ``observation``'s references, in order, once each.

    Read from the deployment's own store, as an auditor reads a record: every record a reference the question was
    handed names (both questions', on a reused shape). A composite's children answer through their own records,
    which the parent's record does not name in these worlds (its ``child_replay_ref`` is empty), so their pins are
    not reached here.
    """
    pins: list[str] = []
    for reference in sorted(references_in(jsonable(observation.channels.get(REFERENCE)))):
        pins.extend(_record_at(deployment.store, reference).content_generation_path.graph_query_sequence)
    return tuple(dict.fromkeys(pins))


def filed_names(deployment: Deployment, address: str) -> tuple[Any, ...]:
    """Every name ``deployment``'s own tenant filed ``address`` under in its store (an auditor's read of its naming)."""
    return tuple(
        named
        for named in deployment.store.names_at(content_address=address)
        if named.tenant_id == deployment.tenant
    )


def _mcp_resource_read(deployment: Deployment, uri: str, *, token: str) -> Any:
    """One MCP artifact-server resource read, as ``token``, decoded exactly as :func:`mcp_record_reads` decodes it."""
    from mcp.types import BlobResourceContents, TextResourceContents  # noqa: PLC0415
    from pydantic import AnyUrl  # noqa: PLC0415

    async def operation(session: Any) -> Any:
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

    return mcp_drive(mcp_artifact_server(deployment), operation, token=token)


def _mcp_put(deployment: Deployment, canonical: bytes, *, name: str = PIN_CLIENT_NAME) -> Any:
    """The asker's ``put_artifact`` of ``canonical`` on its own client lane, through the MCP artifact server."""
    from mcp.types import TextContent  # noqa: PLC0415

    from ccf_runtime.mcp.artifact_server import PUT_ARTIFACT_TOOL  # noqa: PLC0415

    arguments = {
        "artifact_class": PIN_CLIENT_CLASS,
        "name": name,
        "canonical_b64": base64.b64encode(canonical).decode("ascii"),
    }

    async def operation(session: Any) -> Any:
        try:
            result = await session.call_tool(PUT_ARTIFACT_TOOL, arguments)
        except Exception as refused:  # noqa: BLE001 — a protocol error is an observation
            return {"error": type(refused).__name__, "message": str(refused)}
        return {
            "is_error": bool(result.isError),
            "structured": result.structuredContent,
            "text": [_maybe_json(c.text) for c in result.content if isinstance(c, TextContent)],
        }

    return mcp_drive(mcp_artifact_server(deployment), operation, token=ASKER_TOKEN)


def _put_failed(answered: Any) -> bool:
    """Whether a put filed nothing: a protocol error, an unreachable server, or the tool's own error result."""
    return isinstance(answered, dict) and (
        "error" in answered or "unreachable" in answered or bool(answered.get("is_error"))
    )


def _pin_read_failed(surface: str, answered: Any) -> bool:
    """Whether one read ended in a failure rather than an answer: an HTTP 5xx, or a failed MCP read (:func:`_mcp_read_failed`)."""
    if surface.startswith("http-"):
        status = answered.get("status") if isinstance(answered, dict) else None
        return isinstance(status, int) and status >= 500
    return _mcp_read_failed(answered)


def read_pin(
    deployment: Deployment, address: str, uris: tuple[str, ...], readings: dict[str, Any], failures: dict[str, str]
) -> None:
    """Every :data:`PIN_READ_SURFACES` read of one address, into ``readings``; every read that failed, into ``failures``.

    The record channel's own reads (:func:`mcp_record_reads`, :func:`http_record_reads`), once per versioned URI the
    address was filed under: a resolution reading is one per URI, every other reading the one at the address. Each
    read's own presented reference and address are normalized there, as the record channel normalizes them.
    """
    if not uris or any(_reference_parts(uri)["version"] != address for uri in uris):
        raise AssertionError(f"read_pin: {address} is not the version of every URI it was handed: {uris}")
    app = http_app(deployment)
    by_uri = [mcp_record_reads(deployment, uri) | http_record_reads(deployment, uri, app=app) for uri in uris]
    for surface, read in PIN_READ_SURFACES.items():
        keys = (f"owner:{read}", f"other-principal:{read}")
        if read in ("resolution", "replay.resolutions"):
            readings[surface] = {key: [reads[key] for reads in by_uri] for key in keys}
        else:
            readings[surface] = {key: by_uri[0][key] for key in keys}
        failed = sorted({key for reads in by_uri for key in keys if _pin_read_failed(surface, reads[key])})
        if failed:
            failures[surface] = f"{surface} read failed: {failed}: {render(readings[surface], limit=300)}"


def write_then_read_pin(
    deployment: Deployment,
    address: str,
    canonical: bytes,
    presented: tuple[str, ...],
    readings: dict[str, Any],
    failures: dict[str, str],
) -> None:
    """The asker files ``canonical`` on its client lane, then reads blob, presence and names at ``address``.

    ``presented`` is what the asker itself handed the server (the pin's URIs and address), normalized as
    :func:`mcp_record_reads` normalizes it. A put that filed nothing is a failure of every reading after it too: a
    read with no write before it is not a write-then-read.
    """
    from ccf_runtime.mcp.artifact_server import (  # noqa: PLC0415
        artifact_blob_uri,
        artifact_meta_uri,
        artifact_names_uri,
    )

    put = _normalize_presented(jsonable(_mcp_put(deployment, canonical)), presented)
    readings["write-then-read-put"] = put
    put_failure = f"put_artifact filed nothing: {render(put, limit=300)}" if _put_failed(put) else None
    if put_failure:
        failures["write-then-read-put"] = put_failure
    resources = {"blob": artifact_blob_uri, "meta": artifact_meta_uri, "names": artifact_names_uri}
    for surface, read in PIN_WRITE_THEN_READ_SURFACES.items():
        if read == "put":
            continue
        answered = _normalize_presented(
            jsonable(_mcp_resource_read(deployment, resources[read](content_address=address), token=ASKER_TOKEN)),
            presented,
        )
        readings[surface] = answered
        if _mcp_read_failed(answered):
            failures[surface] = f"{surface} read failed: {render(answered, limit=300)}"
        elif put_failure:
            failures[surface] = put_failure


@dataclass
class PinRun:
    """One (shape, anchor)'s pin channel: the three deployments' questions, their pins, and every one-sided pin's readings."""

    shape: str
    anchor: str
    #: What each deployment's question(s) observed, in process (:func:`observe_side`), by side.
    questions: dict[str, Observation]
    #: Every pin each deployment's records name, by side.
    pins: dict[str, tuple[str, ...]]
    #: Whether each deployment's store filed each pin either compared side's records name, read before any write.
    filed: dict[str, dict[str, bool]]
    #: The pins filed in exactly one of the withholding and the not-holding deployment.
    one_sided: tuple[str, ...]
    #: Per one-sided pin, the versioned URIs the deployment that filed it filed it under.
    uris: dict[str, tuple[str, ...]]
    #: Per one-sided pin and side, every surface's reading.
    readings: dict[str, dict[str, dict[str, Any]]]
    #: Per one-sided pin and side, every surface whose read failed, and how.
    failures: dict[str, dict[str, dict[str, str]]]

    def surface_run(self, pin: str, surface: str) -> Run:
        """One pin at one surface as a :class:`Run` of the counterfactual's three sides, for the gate's own comparison."""
        sides = {}
        for side, _directory, _holds in PIN_DEPLOYMENTS:
            failure = self.failures[pin][side].get(surface)
            sides[side] = Observation(
                channels={PIN: self.readings[pin][side][surface]},
                raw=self.readings[pin][side][surface],
                raised={f"{PIN}/{surface}": failure} if failure else {},
            )
        return Run(shape=self.shape, anchor=self.anchor, door=PIN, sides=sides)


def pin_run(base: pathlib.Path, *, shape: str, anchor: str) -> PinRun:
    """Build the counterfactual's three deployments, ask each its question in process, read every one-sided pin.

    Filing is read off each deployment's own store before anything is written, because write-then-read files the
    pin's bytes itself. Every plain read of every pin happens before the first write. The canonical bytes the asker
    writes are read from the deployment that filed the pin, as an auditor would: the stand-in for an outsider
    recomputing them, which is unreproduced (the closing test's pin channel says so).
    """
    from ccf.artifacts.protocol import artifact_uri  # noqa: PLC0415

    deployments: dict[str, Deployment] = {}
    try:
        for side, directory, holds in PIN_DEPLOYMENTS:
            deployments[side] = BUILDERS[shape](base / directory, anchor=anchor, holds=holds, active=True)
        questions = {side: observe_side(shape, IN_PROCESS, built, SUBJECT) for side, built in deployments.items()}
        pins = {side: pins_named(built, questions[side]) for side, built in deployments.items()}
        candidates = tuple(dict.fromkeys((*pins[CF_WITHHELD], *pins[CF_NONEXISTENT])))
        filed = {
            side: {pin: bool(filed_names(built, pin)) for pin in candidates} for side, built in deployments.items()
        }
        one_sided = tuple(pin for pin in candidates if filed[CF_WITHHELD][pin] != filed[CF_NONEXISTENT][pin])
        uris: dict[str, tuple[str, ...]] = {}
        canonical: dict[str, bytes] = {}
        for pin in one_sided:
            filer = deployments[CF_WITHHELD if filed[CF_WITHHELD][pin] else CF_NONEXISTENT]
            uris[pin] = tuple(
                artifact_uri(
                    tenant_id=named.tenant_id, artifact_class=named.artifact_class, name=named.name,
                    artifact_version=pin,
                )
                for named in filed_names(filer, pin)
            )
            canonical[pin] = filer.store.get(content_address=pin)
            if hashlib.sha256(canonical[pin]).hexdigest() != pin:
                raise AssertionError(f"the bytes filed at pin {pin} do not hash to it: not the pin's canonical bytes")
        readings: dict[str, dict[str, dict[str, Any]]] = {pin: {side: {} for side in deployments} for pin in one_sided}
        failures: dict[str, dict[str, dict[str, str]]] = {
            pin: {side: {} for side in deployments} for pin in one_sided
        }
        for pin in one_sided:
            for side, built in deployments.items():
                read_pin(built, pin, uris[pin], readings[pin][side], failures[pin][side])
        for pin in one_sided:
            for side, built in deployments.items():
                write_then_read_pin(
                    built, pin, canonical[pin], (*uris[pin], pin), readings[pin][side], failures[pin][side]
                )
    finally:
        for built in deployments.values():
            built.close()
    return PinRun(
        shape=shape, anchor=anchor, questions=questions, pins=pins, filed=filed, one_sided=one_sided, uris=uris,
        readings=readings, failures=failures,
    )


class PinRunCache:
    """One :class:`PinRun` per (shape, anchor) for the whole session."""

    def __init__(self, factory: Callable[[str], pathlib.Path]) -> None:
        self._factory = factory
        self._runs: dict[tuple[str, str], PinRun] = {}

    def get(self, *, shape: str, anchor: str) -> PinRun:
        key = (shape, anchor)
        if key not in self._runs:
            self._runs[key] = pin_run(self._factory("-".join(("pin", *key))), shape=shape, anchor=anchor)
        return self._runs[key]


# --- the pin channel's instrument -----------------------------------------------------------------------------
#
# Every surface read where it must answer differently, in one deployment: the asker's own readable record (minted by
# a refused read of an address nobody filed; the governed read reads it back to the principal it names, D-IMPL-345
# C20) and the asker's own client-lane filing, against an address nobody filed, floored by a second such address.

#: Addresses nobody files in any deployment here: one whose refused read mints the asker's own record, and two read as
#: the absent side and its floor.
PIN_INSTRUMENT_MINT = hashlib.sha256(b"sec020 pin instrument: minted").hexdigest()
PIN_INSTRUMENT_NOBODY = hashlib.sha256(b"sec020 pin instrument: nobody").hexdigest()
PIN_INSTRUMENT_NOBODY_2 = hashlib.sha256(b"sec020 pin instrument: nobody again").hexdigest()


@dataclass
class PinInstrument:
    """Per surface and side, the instrument's readings: :data:`SERVED` (present), :data:`CF_NONEXISTENT` (absent), :data:`CF_FLOOR`."""

    readings: dict[str, dict[str, Any]]
    failures: dict[str, dict[str, str]]

    def surface_run(self, surface: str) -> Run:
        sides = {
            side: Observation(
                channels={PIN: self.readings[surface][side]},
                raw=self.readings[surface][side],
                raised={f"{PIN}/{surface}": self.failures[surface][side]} if side in self.failures[surface] else {},
            )
            for side in (SERVED, CF_NONEXISTENT, CF_FLOOR)
        }
        return Run(shape=SUBJECT_KEYED, anchor=FROM_DECISION, door=PIN, sides=sides)


def pin_instrument(base: pathlib.Path) -> PinInstrument:
    """Read every pin surface on the asker's own artifacts and on two addresses nobody filed, in one deployment.

    The plain reads: the asker's own read-refusal record, by its versioned URI, against two addresses nobody filed in
    that record's class. Write-then-read: the asker's own client-lane filing, read after its put, against the same
    reads at the two addresses nobody filed; and the put itself, against a put of other bytes (and that put again,
    its floor). Nothing presented is normalized in the put's pair: the instrument asks whether the comparison sees
    the put's answer at all.
    """
    from ccf.artifacts.protocol import artifact_uri  # noqa: PLC0415
    from ccf_runtime.mcp.artifact_server import (  # noqa: PLC0415
        artifact_blob_uri,
        artifact_meta_uri,
        artifact_names_uri,
    )

    deployment = BUILDERS[SUBJECT_KEYED](base / "instrument", anchor=FROM_DECISION, holds=True, active=True)
    readings: dict[str, dict[str, Any]] = {surface: {} for surface in PIN_SURFACES}
    failures: dict[str, dict[str, str]] = {surface: {} for surface in PIN_SURFACES}
    try:
        minted = _mcp_resource_read(
            deployment, artifact_meta_uri(content_address=PIN_INSTRUMENT_MINT), token=ASKER_TOKEN
        )
        own_record = minted["contents"][0]["text"]["replay_reference"]
        record_class = _reference_parts(own_record)["artifact_class"]

        def uri_of(address: str) -> str:
            return artifact_uri(
                tenant_id=deployment.tenant, artifact_class=record_class, name=address, artifact_version=address
            )

        sides = (
            (SERVED, own_record),
            (CF_NONEXISTENT, uri_of(PIN_INSTRUMENT_NOBODY)),
            (CF_FLOOR, uri_of(PIN_INSTRUMENT_NOBODY_2)),
        )
        for side, uri in sides:
            plain: dict[str, Any] = {}
            failed: dict[str, str] = {}
            read_pin(deployment, _reference_parts(uri)["version"], (uri,), plain, failed)
            for surface in PIN_READ_SURFACES:
                readings[surface][side] = plain[surface]
                if surface in failed:
                    failures[surface][side] = failed[surface]
        own_bytes = canonical_bytes({"sec020": "pin instrument", "filing": "own"})
        other_bytes = canonical_bytes({"sec020": "pin instrument", "filing": "other"})
        own_address = hashlib.sha256(own_bytes).hexdigest()
        for side, canonical in ((SERVED, own_bytes), (CF_NONEXISTENT, other_bytes), (CF_FLOOR, other_bytes)):
            put = jsonable(_mcp_put(deployment, canonical))
            readings["write-then-read-put"][side] = put
            if _put_failed(put):
                failures["write-then-read-put"][side] = f"put_artifact filed nothing: {render(put, limit=300)}"
        resources = {"blob": artifact_blob_uri, "meta": artifact_meta_uri, "names": artifact_names_uri}
        for side, address in (
            (SERVED, own_address),
            (CF_NONEXISTENT, PIN_INSTRUMENT_NOBODY),
            (CF_FLOOR, PIN_INSTRUMENT_NOBODY_2),
        ):
            for surface, read in PIN_WRITE_THEN_READ_SURFACES.items():
                if read == "put":
                    continue
                answered = _normalize_presented(
                    jsonable(
                        _mcp_resource_read(deployment, resources[read](content_address=address), token=ASKER_TOKEN)
                    ),
                    (address,),
                )
                readings[surface][side] = answered
                if _mcp_read_failed(answered):
                    failures[surface][side] = f"{surface} read failed: {render(answered, limit=300)}"
    finally:
        deployment.close()
    return PinInstrument(readings=readings, failures=failures)


# =============================================================================
# OWED-RULINGS-3 item 4 (b): a source that answers an unheld identifier with a held refusal
# =============================================================================
#
# Dave, 2026-10-09 06:21 MST (D-IMPL-378), verbatim (kept as a comment, CINV-01a):
#   "4(b), plus the closing-test case and a supported working twin"
# The option ruled (OWED-RULINGS-3, dl-378-record @ 3533cc89), item 4 (b), verbatim:
#   "Refuse when the probe call itself returns a held refusal (refuses every
#   question to a source that refuses unknown identifiers)."
#
#: The label a held-refusal run carries. Deliberately outside :data:`SHAPES` and
#: :data:`PENDING_SHAPES`: its cells are generated by their own test beside the
#: matrix, and its twin is the matrix's own ``subject_keyed`` world.
HELD_REFUSAL = "held_refusal_for_unheld"
#: Item 4 (b)'s refusal (``ccf.products.resolver.UnheldSubjectProbeRefused``):
#: raised for every question of a class the P6 probe reads whose subject-keyed
#: phase answers the probe identifier with a held refusal — decided by the
#: probe, never by the subject.
HELD_REFUSAL_REFUSAL = "UnheldSubjectProbeRefused"
#: The supported working twin: the same deployment with its source answering an
#: identifier it does not hold with NOTHING (:class:`SubjectKeyedSource`) — the
#: shape the SDK supports, which is exactly the :data:`SUBJECT_KEYED` world.
HELD_REFUSAL_TWIN = SUBJECT_KEYED
#: Every side a held-refusal run asks: the two comparisons' sides (:data:`PAIRS`)
#: and an ordinarily served subject (:data:`SERVED`, the policy off). Every one is
#: a question the P6 probe reads, so every one is refused alike.
HELD_REFUSAL_SIDES = (CF_WITHHELD, SAME_NONEXISTENT, SAME_FLOOR, CF_NONEXISTENT, CF_FLOOR, SERVED)


class HeldRefusalSource(SubjectKeyedSource):
    """``acquire`` keyed on the subject, answering an identifier it does not hold with a HELD refusal.

    For a subject it holds, the claim, exactly as :class:`SubjectKeyedSource`;
    for any other identifier, the typed handoff ``GovernedRefusalRaised`` with a
    ``subject-unavailable`` refusal. Under a class the P6 probe reads (it may
    withhold, and declares no early policy), the probe identifier is one such
    identifier: the source shape item 4 (b) refuses every question to.
    """

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        if context.request.subject in self._holdings:
            return super().__call__(context)
        from ccf.products.refusal import (  # noqa: PLC0415
            RESOLVED_BY_THE_RESOLVER,
            GovernedRefusalRaised,
            SubjectUnavailableRefusal,
        )

        self.asked.append(context.request.subject)
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent", detail="the source holds no such subject", error_code=None
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )


def build_held_refusal(base: pathlib.Path, *, anchor: str, holds: bool, active: bool) -> Deployment:
    """:func:`build_subject_keyed`'s deployment with its source swapped for :class:`HeldRefusalSource`."""
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    holdings = {SUBJECT: subject_holding()} if holds else {}
    return open_paved(
        base, anchor=anchor, acquire=HeldRefusalSource(holdings),
        project=plan_factory(early=False, plan_id=PRODUCT_CLASS, asker=ASKER, active=active),
    )


#: Where a run of a constant-refusal world keeps its declared working twin: a :class:`Run` of the same questions,
#: through the same door, asked of the supported deployment the world declares (``Run.notes``). Kept ON the run, so
#: whatever judges the run reads the twin from the run itself, never from a caller's word that one answered
#: (``D-IMPL-378``, Dave, 2026-10-09 10:54 MST, 2.1 (b): *"plus a working declared twin. Enforce these conditions
#: inside the acceptance helper."*).
DECLARED_WORKING_TWIN = "declared_working_twin"


def held_refusal_run(base: pathlib.Path, *, anchor: str, door: str, twin: Run) -> Run:
    """Every side of :data:`HELD_REFUSAL_SIDES`, asked of :func:`build_held_refusal`'s deployments through ``door``.

    The deployment that holds the subject and withholds it from the asker is
    asked about the subject, an identifier nothing holds and a second one (the
    same-deployment comparison); two copies that do not hold it are asked about
    the subject (the counterfactual and its noise floor); and the deployment
    with the policy off is asked about the subject (an ordinarily served
    subject). Records are read back where the door reads them, as
    :func:`run_sides` reads them for a subject-keyed shape. ``notes["asked"]``
    keeps, per deployment, every identifier its source was handed: the evidence
    the case was constructed, and of what the phase saw.
    ``notes[DECLARED_WORKING_TWIN]`` is ``twin``: the gate's own run of
    :data:`HELD_REFUSAL_TWIN` at the same anchor and door, the supported working
    twin the run is judged against (:data:`DECLARED_WORKING_TWIN`).
    """
    opened: list[tuple[str, Deployment]] = []

    def deployment(name: str, *, holds: bool, active: bool) -> Deployment:
        built = build_held_refusal(base / name, anchor=anchor, holds=holds, active=active)
        opened.append((name, built))
        return built

    try:
        withholding = deployment("withholding", holds=True, active=True)
        sides = {
            CF_WITHHELD: observe_side(HELD_REFUSAL, door, withholding, SUBJECT, reads=True),
            SAME_NONEXISTENT: observe_side(HELD_REFUSAL, door, withholding, NEVER),
            SAME_FLOOR: observe_side(HELD_REFUSAL, door, withholding, NEVER_2),
            CF_NONEXISTENT: observe_side(
                HELD_REFUSAL, door, deployment("not-holding", holds=False, active=True), SUBJECT, reads=True
            ),
            CF_FLOOR: observe_side(
                HELD_REFUSAL, door, deployment("not-holding-again", holds=False, active=True), SUBJECT, reads=True
            ),
            SERVED: observe_side(
                HELD_REFUSAL, door, deployment("serving", holds=True, active=False), SUBJECT, reads=True
            ),
        }
        asked = {name: list(built.notes["opened"]._acquire.asked) for name, built in opened}
    finally:
        for _name, built in opened:
            built.close()
    return Run(
        shape=HELD_REFUSAL, anchor=anchor, door=door, sides=sides,
        notes={"asked": asked, DECLARED_WORKING_TWIN: twin},
    )


class HeldRefusalRunCache:
    """One held-refusal run per (anchor, door) for the whole session, each carrying the gate's own twin run."""

    def __init__(self, factory: Callable[[str], pathlib.Path], *, twins: RunCache) -> None:
        self._factory = factory
        self._twins = twins
        self._runs: dict[tuple[str, str], Run] = {}

    def get(self, *, anchor: str, door: str) -> Run:
        key = (anchor, door)
        if key not in self._runs:
            self._runs[key] = held_refusal_run(
                self._factory(f"{HELD_REFUSAL}-{anchor}-{door}"), anchor=anchor, door=door,
                twin=self._twins.get(shape=HELD_REFUSAL_TWIN, anchor=anchor, door=door),
            )
        return self._runs[key]


# =============================================================================
# Decision 4 (a): the stand-in world — a declared early policy whose stand-in names something here
# =============================================================================
#
# Dave, 2026-10-09 06:06 MST, confirmed at 06:21 MST (D-IMPL-378), item 4, verbatim (kept as a comment, CINV-01a):
#   "(a). Verify the stand-in is absent before and after acquisition. A failed
#   check refuses without exposing subject-dependent differences."
# Built by lane 378i-probe in tests/products/test_sec020_stand_in_is_verified_absent.py, which judges it with this
# proof's own rules; moved here, unchanged, so the world and its declared working twin are built where every other
# world of the proof is (D-IMPL-378, Dave, 2026-10-09 10:54 MST, 2.1 (b): "Limit the closing-test exception to the
# held-refusal and stand-in worlds.").

#: The label a stand-in run carries: every question of a deployment whose declared early policy's stand-in names
#: something here is refused by :data:`STAND_IN_REFUSAL`, whatever subject was asked.
STAND_IN_HELD = "stand_in_held"
#: Its declared working twin: the same deployments with the stand-in held nowhere, asked the same questions.
STAND_IN_TWIN = "stand_in_held_nowhere"
#: Decision 4 (a)'s refusal (``ccf.products.resolver.UndisclosedSubjectSubstituteIsHeld``).
STAND_IN_REFUSAL = "UndisclosedSubjectSubstituteIsHeld"
#: How a deployment's source holds the declared stand-in. ``itself``: a record whose resolution the fabric names by
#: the stand-in. ``another-uri``: a record for the stand-in that the fabric names otherwise (an account whose identity
#: mints another URI), which only a comparison of what the phase acquired can see. ``population-phase``: the declared
#: population phase writes the stand-in's own record before the subject-keyed phase runs.
STAND_IN_ITSELF = "itself"
STAND_IN_ANOTHER_URI = "another-uri"
STAND_IN_POPULATION_PHASE = "population-phase"
STAND_IN_HELD_AS = (STAND_IN_ITSELF, STAND_IN_ANOTHER_URI, STAND_IN_POPULATION_PHASE)
#: The account a source returns for the stand-in under ``another-uri``. Fixture vocabulary.
STAND_IN_SHADOW_REF = "acct-stand-in-shadow"
#: Every side a stand-in run asks: the same-deployment comparison's three sides (the withheld subject, an identifier
#: nothing holds and a second one) and an ordinarily served subject (the policy off). Every one is refused alike.
STAND_IN_SIDES = (CF_WITHHELD, SAME_NONEXISTENT, SAME_FLOOR, SERVED)


def stand_in_holding(account_ref: str) -> Holding:
    """The stand-in's own record, in an open book, observed shortly before the question."""
    return Holding(
        account_ref=account_ref, book=OPEN_BOOK, label="stand-in label", observed_at=asked_at() - timedelta(minutes=5)
    )


def build_stand_in(
    base: pathlib.Path, *, anchor: str, held_as: str | None, active: bool
) -> tuple[Deployment, SubjectKeyedSource]:
    """The early-withholding paved deployment holding the subject; ``held_as`` says where the stand-in is held.

    ``held_as=None`` is the twin: the stand-in held nowhere. Returns the deployment and its source (whose ``asked``
    keeps every identifier the subject-keyed phase was handed).
    """
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    holdings = {SUBJECT: subject_holding()}
    overrides: dict[str, Any] = {}
    if held_as == STAND_IN_ITSELF:
        holdings[STAND_IN] = stand_in_holding(STAND_IN_REF)
    elif held_as == STAND_IN_ANOTHER_URI:
        holdings[STAND_IN] = stand_in_holding(STAND_IN_SHADOW_REF)
    elif held_as == STAND_IN_POPULATION_PHASE:
        overrides["population"] = PopulationHalf({STAND_IN: stand_in_holding(STAND_IN_REF)})
    source = SubjectKeyedSource(holdings)
    built = open_paved(
        base, anchor=anchor, acquire=source,
        project=plan_factory(early=True, plan_id=PRODUCT_CLASS, asker=ASKER, active=active),
        **overrides,
    )
    return built, source


def _stand_in_sides(base: pathlib.Path, *, anchor: str, door: str, held_as: str | None) -> dict[str, Observation]:
    """:data:`STAND_IN_SIDES`, asked through ``door`` of :func:`build_stand_in`'s deployments, policy on and off."""
    withholding, _ = build_stand_in(base / "withholding", anchor=anchor, held_as=held_as, active=True)
    serving, _ = build_stand_in(base / "serving", anchor=anchor, held_as=held_as, active=False)
    try:
        return {
            CF_WITHHELD: observe_side(SUBJECT_KEYED, door, withholding, SUBJECT),
            SAME_NONEXISTENT: observe_side(SUBJECT_KEYED, door, withholding, NEVER),
            SAME_FLOOR: observe_side(SUBJECT_KEYED, door, withholding, NEVER_2),
            SERVED: observe_side(SUBJECT_KEYED, door, serving, SUBJECT),
        }
    finally:
        withholding.close()
        serving.close()


def stand_in_run(base: pathlib.Path, *, anchor: str, door: str, held_as: str) -> Run:
    """Every side of :data:`STAND_IN_SIDES` with the stand-in held as ``held_as``, carrying its declared working twin.

    The twin (``notes[DECLARED_WORKING_TWIN]``, labeled :data:`STAND_IN_TWIN`) is the same two deployments with the
    stand-in held nowhere, asked the same questions through the same door.
    """
    sides = _stand_in_sides(base / "held", anchor=anchor, door=door, held_as=held_as)
    twin = Run(
        shape=STAND_IN_TWIN, anchor=anchor, door=door,
        sides=_stand_in_sides(base / "twin", anchor=anchor, door=door, held_as=None),
    )
    return Run(
        shape=STAND_IN_HELD, anchor=anchor, door=door, sides=sides,
        notes={"held_as": held_as, DECLARED_WORKING_TWIN: twin},
    )


# =============================================================================
# 2.1 (b): the acceptance helper — a raised floor copy is a floor only in the two constant-refusal worlds
# =============================================================================
#
# Dave, 2026-10-09 10:54 MST (D-IMPL-378), 2.1 (b), verbatim (kept as a comment, CINV-01a): "Limit the closing-test
# exception to the held-refusal and stand-in worlds. Require identical refusal type, code and constant message across
# all sides, plus a working declared twin. Enforce these conditions inside the acceptance helper." The option ruled
# (the "i" panel's findings brief, dl-378-record @ 15e79163, section 2.1 (b)), verbatim: "accept with the shape
# restriction restored, so it applies only in the held-refusal and stand-in worlds". It restricts the coordinator's
# judging change 09d5c2ba (J5), which admitted any run whose every side raised one of the two refusals.


@dataclass(frozen=True)
class ConstantRefusalWorld:
    """One of the two worlds whose every question is refused alike by one refusal, and the twin it declares.

    ``refusal`` is the refusal's type name; ``constant`` names the ``GovernedResolver`` static method that returns
    the SDK's one message for it; ``sides`` is every side the world asks (its census: each must be refused alike);
    ``twin`` labels the declared working twin's run, which is asked the same ``sides`` and must serve :data:`SERVED`.
    """

    refusal: str
    constant: str
    sides: tuple[str, ...]
    twin: str


#: The two worlds, by the label their runs carry (Dave, 2026-10-09 06:21 MST, D-IMPL-378): item 4 (b)'s held refusal
#: at the P6 probe ("4(b), plus the closing-test case and a supported working twin"), whose twin is the gate's own
#: ``subject_keyed`` world; and decision 4 (a)'s refused stand-in ("A failed check refuses without exposing
#: subject-dependent differences."), whose twin holds the stand-in nowhere.
CONSTANT_REFUSAL_WORLDS: dict[str, ConstantRefusalWorld] = {
    HELD_REFUSAL: ConstantRefusalWorld(
        refusal=HELD_REFUSAL_REFUSAL, constant="_probe_was_refused", sides=HELD_REFUSAL_SIDES, twin=HELD_REFUSAL_TWIN
    ),
    STAND_IN_HELD: ConstantRefusalWorld(
        refusal=STAND_IN_REFUSAL, constant="_stand_in_is_held", sides=STAND_IN_SIDES, twin=STAND_IN_TWIN
    ),
}
#: The two refusals the worlds hold, by type name.
CONSTANT_REFUSALS: tuple[str, ...] = tuple(world.refusal for world in CONSTANT_REFUSAL_WORLDS.values())

#: Why the acceptance helper admitted no floor, one name per condition of 2.1 (b) (:func:`why_no_constant_refusal`).
NOT_ONE_OF_THE_TWO_WORLDS = "the run is not of the held-refusal world or the stand-in world"
REFUSAL_NOT_ON_THIS_TREE = "the world's refusal or its SDK constant is not on this tree"
NOT_THE_WORLDS_SIDES = "the run does not hold exactly the sides its world asks"
NOT_THE_WORLDS_REFUSAL = "a side did not raise its world's refusal type, and only that, at its one question"
NOT_THE_SDKS_CONSTANT = "a side's message is not the SDK's constant message for that refusal"
REFUSAL_CODES_DIFFER = "the sides were answered with different refusal codes"
NO_DECLARED_TWIN = "the run carries no declared working twin"
NOT_THE_DECLARED_TWIN = "the twin is not its world's declared twin: another world, anchor or door, or a question unasked"
TWIN_RAISED = "the declared twin raised instead of answering"
TWIN_SERVED_NOTHING = "the declared twin served no product"


def constant_refusal_message(world: ConstantRefusalWorld) -> str | None:
    """The SDK's own constant message for ``world``'s refusal (``GovernedResolver.<constant>()``), or ``None`` if absent."""
    import ccf.products.resolver as resolver  # noqa: PLC0415

    if not hasattr(resolver, world.refusal):
        return None
    message = getattr(resolver.GovernedResolver, world.constant, None)
    return message() if callable(message) else None


def refusal_code(run: Run, side: str) -> str:
    """The refusal code ``side`` was answered with: its refusal-code channel (:data:`REFUSAL`), rendered canonically.

    In process, the raise itself (outcome, type, message); behind HTTP, the status, the outcome, the body and the
    recorded cause; behind MCP, the error flag, the outcome, the text and the recorded cause. One part is replaced:
    the MCP door's ``ccf-runtime-failure:<id>``, whose id is a fresh ``uuid4().hex`` per call that names an
    occurrence, not a decision (``ccf_runtime.mcp.egress``), so two calls answered alike carry one code.
    """
    from ccf_runtime.mcp.egress import CCF_FAILURE_PREFIX  # noqa: PLC0415

    occurrence = re.compile(rf"{re.escape(CCF_FAILURE_PREFIX)}:[0-9a-f]{{32}}")

    def normalized(value: Any) -> Any:
        if isinstance(value, str):
            return occurrence.sub(f"{CCF_FAILURE_PREFIX}:<occurrence>", value)
        if isinstance(value, dict):
            return {key: normalized(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalized(item) for item in value]
        return value

    return json.dumps(normalized(jsonable(run.sides[side].channels.get(REFUSAL))), sort_keys=True, default=str)


def _constant_refusal_world(run: Run) -> ConstantRefusalWorld | None:
    """The world ``run`` is a run of, read off its own label: the held-refusal world, the stand-in world, or neither."""
    return CONSTANT_REFUSAL_WORLDS.get(run.shape)


def why_no_constant_refusal(run: Run) -> str | None:
    """``None`` when ``run``'s refusal is held as the property; otherwise the first condition it fails, by name.

    Every condition of 2.1 (b), read from the run itself and never from a caller: the run is of one of the two worlds
    (:data:`CONSTANT_REFUSAL_WORLDS`); it holds exactly the sides its world asks; every one of them raised the
    world's refusal type, only at its one question, with the SDK's constant message (:func:`constant_refusal_message`)
    — so the same type and message on every side — and with one refusal code (:func:`refusal_code`); and the run
    carries its world's declared working twin (:data:`DECLARED_WORKING_TWIN`): the world's twin label, at the same
    anchor and door, asked every one of the same questions, raising nothing at any of them, and SERVING its served
    subject (:data:`SERVED`).
    """
    world = _constant_refusal_world(run)
    if world is None:
        return NOT_ONE_OF_THE_TWO_WORLDS
    constant = constant_refusal_message(world)
    if constant is None:
        return REFUSAL_NOT_ON_THIS_TREE
    if set(run.sides) != set(world.sides):
        return NOT_THE_WORLDS_SIDES
    raised = {side: run.raised(side) for side in world.sides}
    if any(set(found) != {ONLY} or not found[ONLY].startswith(f"{world.refusal}: ") for found in raised.values()):
        return NOT_THE_WORLDS_REFUSAL
    if any(found[ONLY] != f"{world.refusal}: {constant}" for found in raised.values()):
        return NOT_THE_SDKS_CONSTANT
    if len({refusal_code(run, side) for side in world.sides}) != 1:
        return REFUSAL_CODES_DIFFER
    twin = run.notes.get(DECLARED_WORKING_TWIN)
    if not isinstance(twin, Run):
        return NO_DECLARED_TWIN
    if (twin.shape, twin.anchor, twin.door) != (world.twin, run.anchor, run.door) or any(
        side not in twin.sides for side in world.sides
    ):
        return NOT_THE_DECLARED_TWIN
    if any(twin.raised(side) for side in world.sides):
        return TWIN_RAISED
    served = jsonable(twin.sides[SERVED].channels.get(REFUSAL))
    if not isinstance(served, dict) or served.get("outcome") != "served":
        return TWIN_SERVED_NOTHING
    return None


def a_constant_refusal_is_the_property(run: Run, position: str, raised: str) -> bool:
    """The acceptance helper: whether a side raising ``raised`` at ``position`` raised the refusal ``run`` holds as the property.

    ``D-IMPL-378``, Dave, 2026-10-09 10:54 MST, 2.1 (b) (verbatim above). Read where every noise floor is read
    (``test_sec020_combined_proof._floor_copy_did_not_answer``): a floor copy that RAISED is a floor only where its
    raise is the property the cell holds. True only at the question's own position (a raise inside a record read never
    is), only where :func:`why_no_constant_refusal` finds every condition met for the whole run, and only for exactly
    the raise every side of its world raised: the world's refusal type with the SDK's constant message. Anything else
    is False, and the cell is judged as it would be without this exception: its floor copy excuses nothing.
    """
    world = _constant_refusal_world(run)
    if position != ONLY or world is None or why_no_constant_refusal(run) is not None:
        return False
    return raised == f"{world.refusal}: {constant_refusal_message(world)}"
