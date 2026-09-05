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

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
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
from ccf.products.refusal import (
    REFUSAL_KINDS,
    RefusalEnvelope,
    RequestIdentity,
    envelope_for,
)
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api import app as app_module
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import CONTENT_ADDRESS_HEADER, canonical_response
from ccf_runtime.http_api.routes import product as product_route
from ccf_runtime.mcp.auth import FileTokenSource
from ccf_runtime.mcp.egress import ProductNotServable
from http_api.conftest import Fabric, call

TOKEN = "declared-obligation-token"
PRINCIPAL = "declared-obligation-caller"
ROLE = "declared-obligation-role"
AUDIT_INSTANT = datetime(2026, 9, 2, tzinfo=UTC)

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

#: The one line in the shipped route that decides the ``409``. The live
#: sabotage asserts it occurs exactly once before mutating a scratch copy.
DECISION_LINE = "and envelope.kind == REFUSAL_KINDS[DeclaredObligationRefusal]"

ROUTE_SOURCE = Path(product_route.__file__)


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
            return fabric.product_servable
        raise ProductNotServable(
            f"no gate-admitted product at {tenant}/{product_class}/{version}"
        )

    return resolve


def _perspective(*, grant: Any, tenant: str, requested_role: str | None) -> Perspective:
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


def _governed_app(
    fabric: Fabric, root: Path, *, resolver: Callable[..., object]
) -> Any:
    """A product door that serves, over the supplied resolver.

    The same shape ``tests/http_api/test_routes.py::_governed_app`` builds,
    with the resolver injectable — the module fixture's app is ungoverned and
    refuses ``503`` before any resolver is reached.
    """
    token_file = root / "declared-obligation-tokens.json"
    token_file.write_text(
        json.dumps({TOKEN: {"client_id": PRINCIPAL, "scopes": ["product"]}}),
        encoding="utf-8",
    )
    address = fabric.product_address
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version="1.0.0",
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
    return create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=resolver,  # type: ignore[arg-type]
        ),
        auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
        product_entitlement=ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: AUDIT_INSTANT
        ),
        perspective_resolver=_perspective,
    )


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
    envelope = _envelope(fabric)
    answer = _ask(
        _governed_app(fabric, tmp_path, resolver=_answering(envelope)),
        fabric,
        query=_question(),
    )

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


def test_a_bare_declared_obligation_refusal_is_enveloped_at_the_door(
    fabric: Fabric, tmp_path: Path
) -> None:
    """A deployment resolver returning what ``run_gates`` gave it gets the same 409.

    The door translates the bare value through
    :func:`~ccf.products.door.door_refusal`, supplying the question from
    the request it carried — so the request identity is the caller's own
    parameters and instant, and the lineage is honestly ``None`` (the door
    never held the candidate). What would fail here: a door that mapped
    only pre-built envelopes and let a bare refusal fall through.
    """
    answer = _ask(
        _governed_app(fabric, tmp_path, resolver=_answering(_refusal())),
        fabric,
        query=_question(),
    )

    assert_declared_obligation_answered_409(
        answer.status, answer.body, escaped=answer.escaped
    )
    refusal = answer.body["refusal"]
    assert refusal["request"] == json.loads(canonical_bytes(_identity(fabric)))
    assert refusal["pre_assembly_lineage"] is None


def test_a_bare_refusal_on_a_call_that_posed_no_question_is_the_documented_value_error(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The route docstring's last sentence, measured rather than trusted.

    With no question on the call there is no request identity for the door
    to name, and :func:`~ccf.products.door.door_refusal` raises the
    ``ValueError`` it documents rather than inventing one. That is the same
    opaque outcome the pre-plan ``TypeError`` produced — no response — now
    naming why. Not a ``409``, and deliberately not: a 409 whose request
    identity was manufactured would report a question nobody asked.
    """
    answer = _ask(
        _governed_app(fabric, tmp_path, resolver=_answering(_refusal())),
        fabric,
        query="",
    )

    assert answer.status is None
    assert isinstance(answer.escaped, ValueError)
    assert "carried no request" in str(answer.escaped)


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


def test_any_other_refusal_kind_still_reaches_served_answer(
    fabric: Fabric, tmp_path: Path
) -> None:
    """DIV-4, preserved and scoped: one kind is mapped, the rest are not.

    A ``ttl-refusal`` envelope is the pre-plan behavior exactly — it reaches
    :func:`~ccf.products.door.served_answer`, which raises ``TypeError``
    naming the shape, and no response is produced. Asserted explicitly so
    the unruled remainder is a measurement in the tree rather than a
    sentence in a docstring. What would fail here: a door that had quietly
    widened the mapping to every kind, which is the ruling nobody has made.
    """
    answer = _ask(
        _governed_app(fabric, tmp_path, resolver=_answering(_ttl_envelope(fabric))),
        fabric,
        query=_question(),
    )

    assert answer.status is None, answer.body
    assert isinstance(answer.escaped, TypeError)
    assert "RefusalEnvelope" in str(answer.escaped)
    assert "neither `ServableProduct` nor `ServedProduct`" in str(answer.escaped)


def test_the_existing_refusal_statuses_are_unchanged(
    fabric: Fabric, app: Any, tmp_path: Path
) -> None:
    """``400``, ``403``, ``404`` and ``503`` answer exactly as before the 409 arrived.

    Each leg is taken through a door whose resolver WOULD answer a
    declared-obligation refusal, so the four refusals are shown to be decided
    before the new branch is reached — the branch adds a status and moves
    none.
    """
    governed = _governed_app(fabric, tmp_path, resolver=_answering(_envelope(fabric)))

    # 400 — a partial §6.3 address; the door fills nothing in (D-IMPL-98).
    partial = _ask(governed, fabric, query="?" + urlencode({"subject": SUBJECT}))
    assert partial.status == 400
    assert partial.body["detail"]["error_code"] == "product-request-incomplete"

    # 403 — a class the grant does not permit; decided before the resolver.
    unentitled = _ask(
        governed, fabric, query=_question(), product_class=UNENTITLED_CLASS
    )
    assert unentitled.status == 403

    # 404 — an entitled class the resolver has nothing for. A second door
    # over the same root: the token file it rewrites is byte-identical.
    absent = _ask(
        _governed_app(fabric, tmp_path, resolver=_serving_or_absent(fabric)),
        fabric,
        query=_question(),
        product_class=ABSENT_CLASS,
    )
    assert absent.status == 404

    # 503 — the module fixture's ungoverned door refuses before any resolver.
    address = fabric.product_address
    ungoverned = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}",
    )
    assert ungoverned.status_code == 503
    assert ungoverned.json()["detail"]["error_code"] == "product-door-ungoverned"


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

    With ``mutate`` the one decision line is replaced by ``False`` — the
    ``409`` branch made dead, which is what "removed" means for a branch
    whose test is the whole of it. The replacement is asserted to occur
    exactly once so a drifted anchor is a red test, not a silently unmutated
    copy.
    """
    source = ROUTE_SOURCE.read_text(encoding="utf-8")
    assert source.count(DECISION_LINE) == 1, (
        "the shipped route no longer holds the one decision line this"
        f" sabotage mutates ({DECISION_LINE!r}); fix the anchor"
    )
    if mutate:
        source = source.replace(DECISION_LINE, "and False  # sabotaged (24.5-L-14)")
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
def test_a_door_with_the_409_branch_removed_is_red_by_name(
    fabric: Fabric, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutate: bool
) -> None:
    """The live sabotage, and its own control, over a scratch copy of the route.

    ``create_app`` reaches the product router through the name ``product``
    bound in :mod:`ccf_runtime.http_api.app`; that name is pointed at the
    scratch module for the duration of one app build, so the door under test
    IS the scratch route and every other route is the shipped one. The
    control leg (no mutation) answers ``409`` — proving the scratch path
    exercises the route, so the sabotaged leg's red is the mutation's. The
    shipped module is byte-compared before and after.
    """
    before = ROUTE_SOURCE.read_bytes()
    scratch = _scratch_route(tmp_path, mutate=mutate)
    monkeypatch.setattr(app_module, "product", scratch)
    answer = _ask(
        _governed_app(fabric, tmp_path, resolver=_answering(_envelope(fabric))),
        fabric,
        query=_question(),
    )
    if mutate:
        # The branch is dead, so the envelope falls through to served_answer.
        assert isinstance(answer.escaped, TypeError)
        with pytest.raises(AssertionError, match=KIND):
            assert_declared_obligation_answered_409(
                answer.status, answer.body, escaped=answer.escaped
            )
    else:
        assert_declared_obligation_answered_409(
            answer.status, answer.body, escaped=answer.escaped
        )
    assert ROUTE_SOURCE.read_bytes() == before
    assert product_route.__file__ == str(ROUTE_SOURCE)
