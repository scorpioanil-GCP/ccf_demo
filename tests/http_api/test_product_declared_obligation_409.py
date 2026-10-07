"""The product door's first typed refusal status — ``409`` for ONE kind.

Ledger rows ``24.5-L-26`` and ``24.6-L-04`` (door half), ``D-IMPL-237``;
CLAUDE.md §8.3 (the HTTP API skeleton).

**Re-derived at ``24.6-04``, and the subject narrowed.** The kind under test
carried two obligations when this module was written, and the one exercised
here was the debt half — a ``D_c`` over a class-declared ceiling, the
Standard §9's *"Debt gate exceeded → 409 with the debt block"*. That half is
retired (``D-IMPL-251`` C1=A: a class figure is a default tolerance, not an
admission boundary), so the kind now carries the LINEAGE obligation alone and
that is what travels through the door below. **The mapping is unchanged**: the
door still answers ``409`` for ``declared-obligation-refusal``, and what a
``tolerance-exceeded`` shell maps to is a later plan's question, not this
module's.

What this module measures, and what it deliberately does not:

* A resolver answering the product door with a
  :class:`~ccf.products.refusal.RefusalEnvelope` of kind
  ``declared-obligation-refusal`` — the ONE refusal the declared-obligations
  gate returns (plan ``24.5-13``) — is answered ``409`` carrying the whole
  envelope in the ``routes/skill.py`` body shape. A *bare*
  :class:`~ccf.products.gates.DeclaredObligationRefusal` on a call that
  posed a question is translated at the door and answered the same way.
* A served product still answers ``200`` with **the same bytes** as before
  this plan — compared against
  :func:`~ccf_runtime.http_api.routes.canonical_response`'s own output for
  the same product (``D-10``, additive over breaking).
* Every OTHER refusal kind keeps the pre-plan behavior, asserted rather
  than implied: a ``ttl-refusal`` envelope still reaches
  :func:`~ccf.products.door.served_answer` and raises ``TypeError`` naming
  the shape (``DIV-4``, scoped — the status and body for the remaining kinds
  is a ruling nobody has made, and this module does not make it).
* The shipped ``400`` / ``403`` / ``404`` / ``503`` refusals are unchanged.

**The status check is a function over its subject** (``D-22``), so the
sabotage control below can hand the *same* function a ``200`` and watch it
go red naming the kind, and the live sabotage can hand it what a door with
the ``409`` branch removed actually answers. The live sabotage runs over a
scratch copy of the route module loaded under another name; the shipped
module is byte-compared before and after and never opened for writing.

Tenant, principal, class and role names here are test deployment vocabulary;
the SDK ships none of it (CINV-01). The two rendered strings are what an
obliged payload member and its observed state look like on the wire.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.disclosure import DISCLOSURE_MINIMAL, DisclosureLevel
from ccf.products.door import WireRequest
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.gates import (
    GATE_DECLARED_OBLIGATIONS,
    DeclaredObligationRefusal,
    TTLRefusal,
)
from ccf.products.door import UngovernedResolverResult
from ccf.products.refusal import NO_REPLAY_REFERENCE
from ccf.products.refusal import (
    REFUSAL_KINDS,
    RefusalEnvelope,
    RequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.request import ProductRequest
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord, ResolutionNotApplicable
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api import app as app_module
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import CONTENT_ADDRESS_HEADER, canonical_response
from ccf_runtime.http_api.routes import product as product_route
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND
from ccf_runtime.mcp.auth import FileTokenSource
from ccf_runtime.mcp.egress import ProductNotServable

# One INTERNAL envelope per kind, driven by each refusal type's own
# annotations rather than by a per-type table — imported rather than restated
# so a kind that grows a field needs no edit here either (`24.6-08`).
from tests.products.test_disclosure import _internal as _internal_envelope

from http_api.conftest import Fabric, call
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

TOKEN = "declared-obligation-token"
PRINCIPAL = "declared-obligation-caller"
ROLE = "declared-obligation-role"
#: The ONE instant every determination behind this module's doors is reached
#: at. Pinned on the entitlement source's own clock (``24.6-08``), so the audit
#: event the source appends and the replay record the recorder writes carry the
#: same instant by construction rather than by two reads that happen to agree.
#: It was ``AUDIT_INSTANT`` while the source was the only thing reading it.
DETERMINED_AT = datetime(2026, 9, 2, tzinfo=UTC)

#: Where a governed door's denials land. Deployment vocabulary.
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"

SUBJECT = "declared-obligation-subject"
INTENT = "declared-obligation-intent"
FRESHNESS = "declared-obligation-freshness"
ASKED_AT = datetime(2026, 9, 2, 9, 30, tzinfo=UTC)
CALLER_PARAMETERS: Mapping[str, Any] = {"minimum_score": 11}

#: A second class the grant permits and the resolver has nothing for — the
#: ``404`` leg needs a class the door lets through to the resolver.
ABSENT_CLASS = "declared-obligation.absent-class"
#: A class the grant does NOT permit — the ``403`` leg.
UNENTITLED_CLASS = "declared-obligation.unentitled-class"

#: What the gate said, rendered as it crosses the wire: the payload member the
#: class obliges, and the state the candidate carried it in. Test vocabulary.
DECLARED = "inputs"
OBSERVED = "absent"

#: The kind this plan maps, read from the mapping and never spelled here as a
#: second literal that could drift from the tree's one spelling.
KIND = REFUSAL_KINDS[DeclaredObligationRefusal]

#: The ONE outcome an unauthorized principal and a nonexistent subject share
#: (``D-IMPL-253`` Q27). Read from the mapping for the same reason.
SUBJECT_UNAVAILABLE = REFUSAL_KINDS[SubjectUnavailableRefusal]

#: The one line in the shipped route that decides EVERY governed refusal's
#: status (``24.6-09``; it decided only the ``409`` before D-18 arrived). The
#: live sabotage asserts it occurs exactly once before mutating a scratch copy.
DECISION_LINE = "if envelope is not None and envelope.kind in STATUS_BY_KIND:"

#: The kind the sabotage below restores DIV-4's fall-through for — read from
#: the mapping, never spelled, so a renamed token moves the sabotage with it.
FALL_THROUGH_KIND = REFUSAL_KINDS[TTLRefusal]

#: The sabotage: one kind excluded from the table lookup, so an envelope of
#: that kind reaches ``served_answer`` again and 500s. Narrower than deleting
#: the branch on purpose — the defect this door is now built against is a
#: *single* governed kind slipping back into the opaque remainder, not the
#: whole mapping vanishing.
SABOTAGED_LINE = (
    "if envelope is not None and envelope.kind in STATUS_BY_KIND"
    f" and envelope.kind != {FALL_THROUGH_KIND!r}:  # sabotaged (24.6-L-03)"
)

ROUTE_SOURCE = Path(product_route.__file__)

#: "Build me the recorder this source discloses under." Distinct from ``None``,
#: which is a caller SAYING *no recorder* — the construction-time refusal's own
#: subject — so the default and the refused value cannot be confused.
_RECORDER_FROM_THE_SOURCE = object()


# ---------------------------------------------------------------------------
# The shipped assertion — a function over its subject (D-22).
# ---------------------------------------------------------------------------


def assert_declared_obligation_answered_409(
    status: int | None, body: Any, *, escaped: BaseException | None = None
) -> None:
    """A declared-obligation refusal reached the door and the door said ``409``.

    The subject is *what the door answered*, not the door, so the control can
    hand this function a ``200`` and the live sabotage can hand it what a
    door with the branch removed actually does (an escaped ``TypeError``).

    Args:
        status: The status the door answered with, or ``None`` when no
            response was produced at all.
        body: The decoded JSON body, when there was one.
        escaped: The exception that escaped the door instead of a response,
            when one did.

    Raises:
        AssertionError: the door did not answer ``409`` carrying the
            ``declared-obligation-refusal`` envelope in the skill route's
            body shape.
    """
    if escaped is not None or status is None:
        raise AssertionError(
            f"a {KIND!r} reached the product door and no response came back;"
            f" {type(escaped).__name__ if escaped else 'nothing'} escaped"
            f" instead ({escaped}). This kind (24.5-L-26) is a typed 409, not"
            " an opaque 500"
        )
    if status != 409:
        raise AssertionError(
            f"a {KIND!r} reached the product door and the door answered"
            f" {status}, not 409 (24.5-L-26; the declared-obligations gate is"
            " the one kind this door maps to a typed status)"
        )
    if not isinstance(body, Mapping) or body.get("kind") != KIND:
        raise AssertionError(
            f"the 409 body does not carry kind {KIND!r} at the top level in"
            f" the routes/skill.py shape; got {body!r}"
        )
    if body.get("refusal_type") != DeclaredObligationRefusal.__name__:
        raise AssertionError(
            "the 409 body's refusal_type is"
            f" {body.get('refusal_type')!r}, not"
            f" {DeclaredObligationRefusal.__name__!r}"
        )
    refusal = body.get("refusal")
    if not isinstance(refusal, Mapping) or refusal.get("kind") != KIND:
        raise AssertionError(
            "the 409 body's `refusal` member is not the whole envelope of"
            f" kind {KIND!r}; got {refusal!r}"
        )


# ---------------------------------------------------------------------------
# The declared world.
# ---------------------------------------------------------------------------


def _refusal() -> DeclaredObligationRefusal:
    """What the declared-obligations gate returns for a dropped lineage member."""
    return DeclaredObligationRefusal(
        gate=GATE_DECLARED_OBLIGATIONS,
        detail=(
            f"product declares a lineage obligation on payload member"
            f" {DECLARED!r}, which is {OBSERVED} — every served line must name"
            " what it was computed from (24.5-L-26)"
        ),
        obligation="lineage-inputs",
        declared=DECLARED,
        observed=OBSERVED,
    )


def _identity(fabric: Fabric) -> RequestIdentity:
    address = fabric.product_address
    return RequestIdentity(
        product_id=address.product_class,
        product_version=address.version,
        parameters=dict(CALLER_PARAMETERS),
        temporal_boundary=ASKED_AT,
    )


def _envelope(fabric: Fabric) -> RefusalEnvelope:
    """The envelope the SDK's reference resolver returns — lineage and all."""
    return envelope_for(
        _refusal(),
        request=_identity(fabric),
        pre_assembly_lineage=fabric.product_servable.product.lineage,
    )


def _ttl_envelope(fabric: Fabric) -> RefusalEnvelope:
    """One OTHER kind, so DIV-4's remainder is asserted and not assumed."""
    return envelope_for(
        TTLRefusal(
            gate="ttl",
            detail="expires_at fell outside (now, now + MAX_TTL]",
            expires_at=datetime(2027, 9, 2, tzinfo=UTC),
            now=ASKED_AT,
            max_ttl_seconds=3600,
        ),
        request=_identity(fabric),
        pre_assembly_lineage=fabric.product_servable.product.lineage,
    )


def _answering(outcome: object) -> Callable[..., object]:
    """A resolver that answers every call with ``outcome``, whatever it is.

    The seam is typed to ``ServableProduct``; this returns a wider set on
    purpose, because the subject is what the door does with the shapes a
    deployment's resolver actually returns.
    """

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        return outcome

    return resolve


def _serving_or_absent(fabric: Fabric) -> Callable[..., object]:
    """The fabric's own served product for its class; ``ProductNotServable`` otherwise."""

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        address = fabric.product_address
        if (tenant, product_class, version) == (
            address.tenant,
            address.product_class,
            address.version,
        ):
            return fabric.product_served
        raise ProductNotServable(
            f"no gate-admitted product at {tenant}/{product_class}/{version}"
        )

    return resolve


def _perspective(*, grant: Any, tenant: str, requested_role: str | None) -> Perspective:
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


def _entitlement_registry(
    fabric: Fabric, *, disclosure_level: DisclosureLevel = DISCLOSURE_MINIMAL
) -> ControlPlaneRegistry:
    """The Control Plane this module's doors decide against.

    One tenant, one principal, two permitted classes and one permitted role —
    so ``ABSENT_CLASS`` reaches the resolver and ``UNENTITLED_CLASS`` does not.
    ``disclosure_level`` is threaded rather than defaulted so the D-27 control
    can register the same policy at each of the three postures without a second
    registry builder (``24.6-08``: the level lives on the tenant's entitlement
    policy).
    """
    address = fabric.product_address
    registry = ControlPlaneRegistry()
    register_typed_at_composition(registry, 
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version="1.0.0",
            disclosure_level=disclosure_level,
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset(
                        {address.product_class, ABSENT_CLASS}
                    ),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return registry


def _recorder(
    fabric: Fabric,
    root: Path,
    *,
    source: ControlPlaneProductEntitlementSource,
) -> ReplayRefusalRecorder:
    """The SDK's own refusal recorder, built the way the resolver's is.

    The keyword list is copied from
    :func:`~ccf.products.resolver.build_governed_resolver`'s own construction
    site, read once — one writer, one store, one record form, which is the
    substance of *"do not create second-class replay"* (``D-IMPL-253`` Q13).
    ``policy_bundle_pin`` is ``None`` because a delivery boundary holds no
    bundle key, which is exactly the posture that field's default documents.

    Args:
        fabric: The module fabric, for the tenant every determination this
            recorder writes was made under.
        root: A per-test temporary root; the store lives under ``artifacts/``.
        source: The entitlement source the door is built with, read for the
            disclosure posture in force — the *same* reader a resolver refusal
            for this principal would disclose under (``24.6-08``).
    """
    return refusal_recorder(
        fabric.registry,
        store=deployment_store(root / "artifacts", REPLAY_RECORD_CLASS),
        tenant=fabric.product_address.tenant,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )


@dataclass(frozen=True)
class Governed:
    """One booted governed door, with the seams a test needs to read back."""

    app: Any
    source: ControlPlaneProductEntitlementSource
    recorder: ReplayRefusalRecorder

    def record_at(self, uri: str) -> DecisionReplayRecord:
        """The replay record one refusal's ``replay_reference`` addresses."""
        store = self.recorder.artifact_store
        return DecisionReplayRecord.model_validate_json(
            store.get(content_address=store.resolve_uri(uri=uri))
        )

    def internal(self, record: DecisionReplayRecord) -> RefusalEnvelope:
        """The INTERNAL determination dimension 5 carries, whole."""
        return RefusalEnvelope.model_validate_json(
            record.content_generation_path.assembly_refusal
        )

    def addresses(self) -> set[str]:
        """Every content address in this door's store — the store's own count.

        Counted from the substrate rather than from anything the door
        reported, so *"the store grew by one"* is a measurement and not the
        response's word for itself.
        """
        root = self.recorder.artifact_store.root
        return (
            {path.name for path in root.iterdir() if len(path.name) == 64}
            if root.exists()
            else set()
        )


def _governed(
    fabric: Fabric,
    root: Path,
    *,
    resolver: Callable[..., object],
    disclosure_level: DisclosureLevel = DISCLOSURE_MINIMAL,
    refusal_recorder: Any = _RECORDER_FROM_THE_SOURCE,
) -> Governed:
    """A governed product door, plus the seams it was built over.

    The same shape ``tests/http_api/test_routes.py::_governed_app`` builds,
    with the resolver injectable — the module fixture's app is ungoverned and
    refuses ``503`` before any resolver is reached.

    ``refusal_recorder`` defaults to a recorder built over ``source``; a caller
    passes its own when a fixture resolver has to mint through the *same*
    instance the door was built with (the D-27 control), and passes ``None``
    explicitly when the subject is the construction-time refusal itself.
    """
    # `SEC-001`/`SEC-002`: every app binds an authorizer, and the tenant is
    # the credential's. This suite's subject is the declared-obligation
    # refusal rather than the gate, so the mapping is registered wide and the
    # token source mints tenanted grants.
    from .gate_fixtures import (
        SCOPE_EVERYTHING,
        tenanted_source,
        wide_authorizer,
    )

    tenant = fabric.product_address.tenant
    token_source = tenanted_source(
        {TOKEN: (PRINCIPAL, (SCOPE_EVERYTHING,))}, tenant=tenant
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(
            fabric, disclosure_level=disclosure_level
        ),
        clock=lambda: DETERMINED_AT,
    )
    recorder = (
        _recorder(fabric, root, source=source)
        if refusal_recorder is _RECORDER_FROM_THE_SOURCE
        else refusal_recorder
    )
    return Governed(
        app=create_app(
            ApiDependencies(
                control_plane=fabric.registry,
                artifact_store=fabric.store,
                product_resolver=resolver,  # type: ignore[arg-type]
            ),
            auth=BearerTokenAuth(token_source=token_source),
            authorizer=wide_authorizer(
                tenant=tenant, key="declared-obligation/scope-mapping"
            ),
            product_entitlement=source,
            perspective_resolver=_perspective,
            refusal_recorder=recorder,
            replay_record_product_class=None,
        ),
        source=source,
        recorder=recorder,
    )


def _governed_app(
    fabric: Fabric, root: Path, *, resolver: Callable[..., object]
) -> Any:
    """Just the app, for the callers that need nothing else."""
    return _governed(fabric, root, resolver=resolver).app


def _minted(
    fabric: Fabric,
    root: Path,
    envelope: RefusalEnvelope,
    *,
    disclosure_level: DisclosureLevel = DISCLOSURE_MINIMAL,
) -> tuple[Governed, RefusalEnvelope]:
    """A governed door whose resolver answers with ``envelope`` RECORDED and DISCLOSED.

    ``D-IMPL-260`` P-A: a door releases only a refusal that proves its record
    and its disclosure — what :class:`~ccf.products.resolver.ReplayRefusalRecorder`
    returns. So a fixture that wants a refusal to cross mints it through the
    same recorder the door is built with, exactly as the SDK's own resolver
    does, and hands the door the shell that came back. Returns the door and
    the shell, so a test can compare the wire against what was minted.
    """
    source = ControlPlaneProductEntitlementSource(
        control_plane=_entitlement_registry(
            fabric, disclosure_level=disclosure_level
        ),
        clock=lambda: DETERMINED_AT,
    )
    recorder = _recorder(fabric, root, source=source)
    shell = recorder.record(
        envelope,
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        recorded_at=DETERMINED_AT,
        served_at=DETERMINED_AT,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    governed = _governed(
        fabric,
        root,
        resolver=_answering(shell),
        disclosure_level=disclosure_level,
        refusal_recorder=recorder,
    )
    return governed, shell


def _question(parameters: Mapping[str, Any] = CALLER_PARAMETERS) -> str:
    """The four §6.3 axes plus the declared remainder, as this door reads them."""
    return "?" + urlencode(
        {
            "subject": SUBJECT,
            "intent": INTENT,
            "freshness": FRESHNESS,
            "asked_at": ASKED_AT.isoformat(),
            "parameters": json.dumps(dict(parameters)),
        }
    )


def _echo(fabric: Fabric) -> WireRequest:
    """The echo the door publishes for :func:`_question` — built the way the door builds it."""
    return WireRequest(
        product_id=fabric.product_address.product_class,
        parameters=dict(CALLER_PARAMETERS),
        temporal_boundary=ASKED_AT,
    )


@dataclass(frozen=True)
class Answer:
    """What one call to the door produced — a response, or an escape."""

    status: int | None
    body: Any
    content: bytes
    headers: Mapping[str, str]
    escaped: BaseException | None


def _ask(
    app: Any,
    fabric: Fabric,
    *,
    query: str,
    product_class: str | None = None,
) -> Answer:
    """One in-process call; an exception that escapes the app is captured, not hidden.

    httpx's ASGI transport re-raises an application exception rather than
    rendering a 500, which is the honest shape for DIV-4's remainder: the
    door produced no response at all.
    """
    address = fabric.product_address
    url = (
        f"/product/{address.tenant}/{product_class or address.product_class}/"
        f"{address.version}{query}"
    )
    try:
        response = call(
            app, "GET", url, headers={"Authorization": f"Bearer {TOKEN}"}
        )
    except Exception as escaped:  # noqa: BLE001 — the escape IS the measurement
        return Answer(
            status=None, body=None, content=b"", headers={}, escaped=escaped
        )
    body: Any
    try:
        body = response.json()
    except ValueError:
        body = None
    return Answer(
        status=response.status_code,
        body=body,
        content=response.content,
        # The httpx `Headers` object itself, not a `dict` of it: header
        # names are case-insensitive on the wire and only the object
        # preserves that on lookup.
        headers=response.headers,
        escaped=None,
    )


# ---------------------------------------------------------------------------
# Criterion 21: the typed 409, for exactly one kind.
# ---------------------------------------------------------------------------


def test_a_declared_obligation_refusal_answers_409_with_the_envelope(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The one mapped kind: ``409``, the whole envelope, the skill route's shape.

    What would fail here: a door that still reached ``served_answer`` for
    this kind (an escaped ``TypeError``), one that answered some other
    status, one that carried the typed fields alone rather than the envelope
    — the ``declared``/``observed`` pair, the request identity and the
    pre-assembly lineage all travel — or one that spelled the kind by a
    literal that had drifted from ``REFUSAL_KINDS``.
    """
    # Minted at `full`, so the wire carries the whole envelope the reference
    # resolver would have produced — lineage included — rather than the
    # `minimal` shell (`D-IMPL-260` P-A: what crosses is what was recorded).
    governed, envelope = _minted(
        fabric, tmp_path, _envelope(fabric), disclosure_level="full"
    )
    answer = _ask(governed.app, fabric, query=_question())

    assert_declared_obligation_answered_409(
        answer.status, answer.body, escaped=answer.escaped
    )
    refusal = answer.body["refusal"]
    # The body is the envelope's own canonical rendering — nothing added,
    # nothing dropped (T-24.5-37).
    assert refusal == json.loads(canonical_bytes(envelope))
    assert refusal["reason"] == GATE_DECLARED_OBLIGATIONS
    # Envelope fields arrive in the SDK's one canonical form: a string is
    # quoted, so a presented "inputs" stays distinguishable from a bare
    # identifier after the crossing.
    assert refusal["fields"]["obligation"] == '"lineage-inputs"'
    assert json.loads(refusal["fields"]["obligation"]) == "lineage-inputs"
    assert json.loads(refusal["fields"]["declared"]) == DECLARED
    assert json.loads(refusal["fields"]["observed"]) == OBSERVED
    assert refusal["request"]["product_id"] == fabric.product_address.product_class
    assert refusal["request"]["parameters"] == dict(CALLER_PARAMETERS)
    assert refusal["pre_assembly_lineage"] is not None


def test_a_bare_declared_obligation_refusal_does_not_cross_the_door(
    fabric: Fabric, tmp_path: Path
) -> None:
    """``D-IMPL-260`` P-A: a bare refusal value is a wiring defect, not a 409.

    Until this ruling the door translated what ``run_gates`` gave a deployment
    resolver into an envelope of its own — undisclosed, unrecorded — and
    answered ``409`` with it. A determination reaching a consumer with no
    replay and no disclosure decision behind it is what criterion 36 forbids,
    so the door now refuses the bare value by name and the transport reports
    a door fault: no response, the typed
    :class:`~ccf.products.door.UngovernedResolverResult` escaping.

    What would fail here: the pre-ruling translation returning, which would
    answer ``409`` from a value nothing recorded.
    """
    answer = _ask(
        _governed_app(fabric, tmp_path, resolver=_answering(_refusal())),
        fabric,
        query=_question(),
    )

    assert answer.status is None, answer.body
    assert isinstance(answer.escaped, UngovernedResolverResult), answer.escaped
    assert "bare `DeclaredObligationRefusal`" in str(answer.escaped)


def test_an_unrecorded_or_undisclosed_envelope_does_not_cross_the_door(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The other two shapes P-A names: the sentinel reference, and ``disclosure=None``.

    Both are the INTERNAL form a recorder is handed, never the shell it
    returns. A door that released either would be releasing a determination
    whose record was never appended, or whose disclosure was never decided.
    """
    internal = _envelope(fabric)
    assert internal.replay_reference == NO_REPLAY_REFERENCE
    assert internal.disclosure is None
    for leg in ("unrecorded", "minted", "undisclosed"):
        (tmp_path / leg).mkdir()

    unrecorded = _ask(
        _governed_app(fabric, tmp_path / "unrecorded", resolver=_answering(internal)),
        fabric,
        query=_question(),
    )
    assert unrecorded.status is None, unrecorded.body
    assert isinstance(unrecorded.escaped, UngovernedResolverResult)
    assert "no replay reference" in str(unrecorded.escaped)

    _governed_at_full, shell = _minted(
        fabric, tmp_path / "minted", internal, disclosure_level="full"
    )
    undisclosed = shell.model_copy(update={"disclosure": None})
    answer = _ask(
        _governed_app(fabric, tmp_path / "undisclosed", resolver=_answering(undisclosed)),
        fabric,
        query=_question(),
    )
    assert answer.status is None, answer.body
    assert isinstance(answer.escaped, UngovernedResolverResult)
    assert "disclosure" in str(answer.escaped)


# ---------------------------------------------------------------------------
# D-10: the served path and every other refusal are unchanged.
# ---------------------------------------------------------------------------


def test_a_served_product_still_answers_200_with_the_same_bytes(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Additive over breaking: the served path is byte-identical to the pre-plan route.

    The pre-plan route's whole served answer was
    ``canonical_response(answer.product, replay_ref=…, asked=echo)``; that
    function is unchanged and is called here directly on the same product,
    so the two bodies are compared as bytes rather than as a status. Both
    legs — no question posed, and the four axes posed — because the
    ``door_refusal`` call now sits on the path in both.
    """
    app = _governed_app(fabric, tmp_path, resolver=_serving_or_absent(fabric))
    product = fabric.product_servable.product

    standing = _ask(app, fabric, query="")
    assert standing.escaped is None
    assert standing.status == 200
    assert standing.content == canonical_response(product).body
    assert standing.content == canonical_bytes(product)
    assert (
        hashlib.sha256(standing.content).hexdigest()
        == standing.headers[CONTENT_ADDRESS_HEADER]
    )

    asked = _ask(app, fabric, query=_question())
    assert asked.escaped is None
    assert asked.status == 200
    assert asked.content == canonical_response(product, asked=_echo(fabric)).body
    assert asked.content == standing.content


@pytest.mark.parametrize("kind", sorted(REFUSAL_KINDS.values()))
def test_no_known_refusal_kind_reaches_served_answer(
    fabric: Fabric, tmp_path: Path, kind: str
) -> None:
    """DIV-4, **inverted** by D-18 — over the roster, not over a count.

    This test used to assert the opposite of its own name: a ``ttl-refusal``
    envelope reached :func:`~ccf.products.door.served_answer`, raised
    ``TypeError`` and produced no response at all, *"because the status code
    and body shape for the remaining kinds is a ruling nobody has made"*. Dave
    made it (``D-IMPL-253`` Q18): **"No known refusal may become 500."** So the
    assertion is negated and widened from one kind to every member of
    :data:`~ccf.products.refusal.REFUSAL_KINDS` — the roster, enumerated, never
    a cardinality.

    What would fail here: a kind added to the vocabulary with no row in the
    status table (its parametrization goes red on its own), a door that let one
    kind fall through (the sabotage below restores exactly that), or a table
    row that answered ``5xx``.
    """
    answer = _ask(
        _minted(fabric, tmp_path, _internal_envelope(kind))[0].app,
        fabric,
        query=_question(),
    )

    assert answer.escaped is None, (
        f"a {kind!r} reached the product door and"
        f" {type(answer.escaped).__name__} escaped instead of a response"
        f" ({answer.escaped}); no known governed refusal may become 500"
    )
    assert answer.status == STATUS_BY_KIND[kind], answer.body
    assert answer.status != 500
    assert set(answer.body) == {"kind", "refusal_type", "refusal"}
    assert answer.body["kind"] == kind


def test_the_existing_refusal_statuses_are_unchanged(
    fabric: Fabric, app: Any, tmp_path: Path
) -> None:
    """``400``, ``404`` and ``503`` answer exactly as before the table arrived.

    Each leg is taken through a door whose resolver WOULD answer a
    declared-obligation refusal, so the refusals are shown to be decided
    before the mapped branch is reached — the table adds statuses and moves
    none of these.

    **One leg did move, by ruling, and it is asserted rather than dropped:**
    the unentitled class answered ``403`` in the ``{"error_code", "message"}``
    shape and now answers the envelope at the ``subject-unavailable`` row of
    the table. It is here rather than deleted because *"the four refusals are
    decided before the new branch is reached"* is still the claim, and a leg
    silently removed is a claim silently narrowed.
    """
    governed = _minted(fabric, tmp_path, _envelope(fabric))[0].app

    # 400 — a partial §6.3 address; the door fills nothing in (D-IMPL-98).
    partial = _ask(governed, fabric, query="?" + urlencode({"subject": SUBJECT}))
    assert partial.status == 400
    assert partial.body["detail"]["error_code"] == "product-request-incomplete"

    # 404 — a class the grant does not permit; decided before the resolver.
    # This leg answered `403` in a second body shape until `24.6-09`: an
    # unauthorized principal and a nonexistent subject now share one kind, one
    # status and one schema, because telling a caller they are *forbidden* is
    # telling them the subject exists (D-27 amendment 2 (4)). The status is
    # read from the table rather than spelled, so the two legs below are
    # asserted equal by construction rather than by two literals agreeing.
    unentitled = _ask(
        governed, fabric, query=_question(), product_class=UNENTITLED_CLASS
    )
    assert unentitled.status == STATUS_BY_KIND[SUBJECT_UNAVAILABLE], unentitled.body
    assert unentitled.body["kind"] == SUBJECT_UNAVAILABLE

    # 404 — an entitled class the resolver has nothing for. A second door
    # over the same root: the token file it rewrites is byte-identical.
    absent = _ask(
        _governed_app(fabric, tmp_path, resolver=_serving_or_absent(fabric)),
        fabric,
        query=_question(),
        product_class=ABSENT_CLASS,
    )
    assert absent.status == 404

    # 503 — **no longer reachable from the front door** (`SEC-001`). This leg
    # used to call the module fixture's app, which was built with no seams and
    # refused `product-door-ungoverned` before any resolver. `create_app` has
    # no such arm now, so the honest subject is the handler reached outside
    # the gate. Under D-IMPL-353 §1.4 the FIRST thing such a handler does is
    # refuse for holding no capability (403 `no-capability`); the 503 branch
    # survives for the one shape that gets past that — a capability stashed
    # with no verified grant beside it — which is why the branch is kept in
    # the route rather than deleted, and why both refusals are asserted here.
    from fastapi import HTTPException
    from starlette.requests import Request

    from ccf.authz.capability import ProductRetrieve, mint
    from ccf.authz.decision import AuthzDecision
    from ccf_runtime.authz.refusals import ACTION_PRODUCT_RETRIEVE
    from ccf_runtime.http_api.errors import ERROR_NO_CAPABILITY
    from ccf_runtime.http_api.gate import mounted_routes

    address = fabric.product_address
    (handler_route,) = [
        route
        for template, route in mounted_routes(governed)
        if template.startswith("/product/")
    ]
    handler = handler_route.endpoint

    def _outside_the_gate(state: dict[str, Any]) -> HTTPException:
        with pytest.raises(HTTPException) as refused:
            handler(
                tenant=address.tenant,
                product_class=address.product_class,
                version=address.version,
                request=Request(
                    {
                        "type": "http",
                        "method": "GET",
                        "path": "/product",
                        "headers": [],
                        "query_string": b"",
                        "endpoint": handler,
                        "state": state,
                    }
                ),
            )
        return refused.value

    no_capability = _outside_the_gate({})
    assert no_capability.status_code == 403
    assert no_capability.detail["error_code"] == ERROR_NO_CAPABILITY

    capability = mint(
        ProductRetrieve,
        decision=AuthzDecision(
            allowed=True,
            matched_scope_pattern=address.tenant,
            matched_resource_pattern=address.product_class,
            artifact_version="1",
            action_id=ACTION_PRODUCT_RETRIEVE,
            tenant=address.tenant,
            resource=address.product_class,
        ),
        principal=PRINCIPAL,
        decision_id="0" * 64,
    )
    ungoverned = _outside_the_gate({"authorized": capability})
    assert ungoverned.status_code == 503
    assert ungoverned.detail["error_code"] == "product-door-ungoverned"


# ---------------------------------------------------------------------------
# Sabotage: the check goes red by name, as a predicate and against a live door.
# ---------------------------------------------------------------------------


def test_the_status_check_refuses_a_200_for_a_declared_obligation(
    fabric: Fabric,
) -> None:
    """The predicate over a fake ``(200, body)`` is RED naming the kind.

    The vacuity control (``D-22``): an assertion that passes against the
    right answer proves nothing until it is shown failing against the wrong
    one. Three wrong answers, each red by name — a served 200, a 409 whose
    body names another kind, and no response at all.
    """
    served_body = json.loads(canonical_bytes(fabric.product_servable.product))
    with pytest.raises(AssertionError, match=KIND):
        assert_declared_obligation_answered_409(200, served_body)

    other = json.loads(canonical_bytes(_ttl_envelope(fabric)))
    with pytest.raises(AssertionError, match=KIND):
        assert_declared_obligation_answered_409(
            409,
            {"kind": other["kind"], "refusal_type": "TTLRefusal", "refusal": other},
        )

    with pytest.raises(AssertionError, match=KIND):
        assert_declared_obligation_answered_409(
            None, None, escaped=TypeError("a resolver answered a door with …")
        )

    # And the right answer, through the same function, is green.
    right = json.loads(canonical_bytes(_envelope(fabric)))
    assert_declared_obligation_answered_409(
        409,
        {"kind": KIND, "refusal_type": DeclaredObligationRefusal.__name__, "refusal": right},
    )


def _scratch_route(root: Path, *, mutate: bool) -> Any:
    """The shipped route module, loaded from a scratch copy under another name.

    With ``mutate`` the one decision line excludes ONE kind from the table
    lookup, which restores DIV-4's fall-through for exactly that kind — what
    "removed" means for a branch whose whole content is a membership test. The
    replacement is asserted to occur exactly once so a drifted anchor is a red
    test, not a silently unmutated copy.
    """
    source = ROUTE_SOURCE.read_text(encoding="utf-8")
    assert source.count(DECISION_LINE) == 1, (
        "the shipped route no longer holds the one decision line this"
        f" sabotage mutates ({DECISION_LINE!r}); fix the anchor"
    )
    if mutate:
        source = source.replace(DECISION_LINE, SABOTAGED_LINE)
    name = "scratch_product_route_" + ("sabotaged" if mutate else "control")
    path = root / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.__file__ != product_route.__file__
    return module


@pytest.mark.parametrize("mutate", [False, True], ids=["control", "sabotaged"])
def test_a_door_that_restores_the_fall_through_for_one_kind_is_red_by_name(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutate: bool
) -> None:
    """The live sabotage, and its own control, over a scratch copy of the route.

    ``create_app`` reaches the product router through the name ``product``
    bound in :mod:`ccf_runtime.http_api.app`; that name is pointed at the
    scratch module for the duration of one app build, so the door under test
    IS the scratch route and every other route is the shipped one. The control
    leg (no mutation) answers the excluded kind's own table status — proving
    the scratch path exercises the route, so the sabotaged leg's red is the
    mutation's. The shipped module is byte-compared before and after.

    The subject is ``ttl-refusal`` because that is the kind whose fall-through
    this plan ENDED: before ``24.6-09`` a ``ttl-refusal`` envelope escaped as a
    ``TypeError`` and the test above asserted it. The sabotage puts exactly
    that back.
    """
    before = ROUTE_SOURCE.read_bytes()
    scratch = _scratch_route(tmp_path, mutate=mutate)
    monkeypatch.setattr(app_module, "product", scratch)
    answer = _ask(
        _minted(fabric, tmp_path, _ttl_envelope(fabric))[0].app,
        fabric,
        query=_question(),
    )
    if mutate:
        # The kind is excluded, so the envelope falls through to served_answer
        # — no response at all, which is the pre-D-18 opaque 500.
        assert answer.status is None, answer.body
        assert isinstance(answer.escaped, TypeError)
        assert "not `ServedProduct`" in str(answer.escaped)
    else:
        assert answer.escaped is None
        assert answer.status == STATUS_BY_KIND[FALL_THROUGH_KIND]
        assert answer.body["kind"] == FALL_THROUGH_KIND
    assert ROUTE_SOURCE.read_bytes() == before
    assert product_route.__file__ == str(ROUTE_SOURCE)
