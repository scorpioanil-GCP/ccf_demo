"""The third exposed product door asks the same question as the other two.

15.5-06. ``GET /product/{tenant}/{product_class}/{version}`` is one of three
places this tree serves a Context Product, and the phase's criterion is *every*
exposed door. This file asserts that this one refuses what the MCP doors
refuse, refuses it with the *same typed constants*, and reaches the same
decision through the same imported code rather than a second reading of what
"entitled" means.

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
one definition, three doors                this route would re-declare the
                                           seams or re-implement the order,
                                           and the HTTP door would drift from
                                           the MCP doors one edit at a time
T-15.5-20 (per-class disclosure)           an authenticated caller would
                                           receive a class its grant does not
                                           name
T-15.5-19 (caller-asserted role)           ``?role=`` would be threaded to the
                                           engine without meeting the grant
T-15.5-21 (dead configuration)             entitlement seams could be bound
                                           with no auth hook, enforcing
                                           nothing, with no signal
D-08 (one vocabulary, two renderings)      the refusal would carry free text a
                                           client had to parse
=========================================  ===================================

Tenant, principal, role and class names are test deployment vocabulary.
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope, SubjectUnavailableRefusal
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api.app import (
    CcfDeadEntitlementWarning,
    CcfInsecureDefaultWarning,
    create_app,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
    ERROR_PRODUCT_DOOR_UNGOVERNED,
    ERROR_PRODUCT_REQUEST_INCOMPLETE,
    ERROR_PRODUCT_ROLE_UNGRANTED,
)
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND
from ccf_runtime.mcp.auth import FileTokenSource, TokenGrant

from http_api.conftest import Fabric, call

#: The ONE outcome an unauthorized principal and a nonexistent subject share
#: (``D-IMPL-253`` Q27), read from the mapping and never spelled here.
SUBJECT_UNAVAILABLE = REFUSAL_KINDS[SubjectUnavailableRefusal]

#: Where this module's governed doors file their denials.
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "product-door-token"
STRANGER_TOKEN = "product-door-stranger-token"
PRINCIPAL = "product-door-caller"
STRANGER = "product-door-stranger"
ROLE = "product-door-role"
UNGRANTED_ROLE = "product-door-role-ungranted"
SCOPE = "product"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 11, tzinfo=UTC)


def _deps(fabric: Fabric) -> ApiDependencies:
    return ApiDependencies(
        control_plane=fabric.registry,
        artifact_store=fabric.store,
        product_resolver=fabric.product_resolver,
        workflow_factory=fabric.factory,
        workflow_engine=fabric.engine,
        hitl_transport=fabric.hitl,
        skill_catalog=fabric.catalog,
        grant_ledger=fabric.ledger,
    )


def _resolver(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
    """This deployment's role derivation: the verified subject, declared role."""
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ROLE,
    )


@dataclass(frozen=True)
class Entitled:
    """One booted governed door, with the seams a test has to read back.

    The recorder is exposed because a denial is now a **recorded** decision
    (``D-IMPL-256``): the typed code an assertion used to read off the ``403``
    body is internal truth, and the only honest place to assert it is the
    record it was written to.
    """

    app: Any
    recorder: ReplayRefusalRecorder

    def record_at(self, uri: str) -> DecisionReplayRecord:
        store = self.recorder.artifact_store
        return DecisionReplayRecord.model_validate_json(
            store.get(content_address=store.resolve_uri(uri=uri))
        )

    def internal(self, uri: str) -> RefusalEnvelope:
        """The INTERNAL determination behind a disclosed shell's reference."""
        return RefusalEnvelope.model_validate_json(
            self.record_at(uri).content_generation_path.assembly_refusal
        )


def _entitled(
    fabric: Fabric,
    tmp_path: Path,
    *,
    permitted_classes: frozenset[str] | None = None,
    permitted_roles: frozenset[str] | None = None,
) -> Entitled:
    """An app whose product door is authenticated *and* entitled."""
    from ccf_runtime.http_api.auth import BearerTokenAuth

    token_file = tmp_path / "product-tokens.json"
    token_file.write_text(
        json.dumps(
            {
                TOKEN: {"client_id": PRINCIPAL, "scopes": [SCOPE]},
                STRANGER_TOKEN: {"client_id": STRANGER, "scopes": [SCOPE]},
            }
        ),
        encoding="utf-8",
    )
    address = fabric.product_address
    registry = ControlPlaneRegistry()
    registry.register_typed(
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version=POLICY_VERSION,
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=(
                        frozenset({address.product_class})
                        if permitted_classes is None
                        else permitted_classes
                    ),
                    permitted_roles=(
                        frozenset({ROLE})
                        if permitted_roles is None
                        else permitted_roles
                    ),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    source = ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )
    # `D-IMPL-256` (2): a door that entitles without the ability to record what
    # it decides is not built at all, so every app in this module binds the one
    # minting seam. Built the way `build_governed_resolver` builds its own —
    # one writer, one store, one record form.
    recorder = ReplayRefusalRecorder(
        artifact_store=FileArtifactStore(root=tmp_path / "artifacts"),
        replay_record_class=REPLAY_RECORD_CLASS,
        tenant_id=address.tenant,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )
    return Entitled(
        app=create_app(
            _deps(fabric),
            auth=BearerTokenAuth(token_source=FileTokenSource(path=token_file)),
            product_entitlement=source,
            perspective_resolver=_resolver,
            refusal_recorder=recorder,
        ),
        recorder=recorder,
    )


def _entitled_app(
    fabric: Fabric,
    tmp_path: Path,
    *,
    permitted_classes: frozenset[str] | None = None,
    permitted_roles: frozenset[str] | None = None,
) -> Any:
    """Just the app, for the callers that need nothing else."""
    return _entitled(
        fabric,
        tmp_path,
        permitted_classes=permitted_classes,
        permitted_roles=permitted_roles,
    ).app


def _get(app: Any, fabric: Fabric, *, token: str, role: str | None = None) -> Any:
    address = fabric.product_address
    url = f"/product/{address.tenant}/{address.product_class}/{address.version}"
    if role is not None:
        url = f"{url}?role={role}"
    return call(app, "GET", url, headers={"Authorization": f"Bearer {token}"})


# --- one definition, three doors -------------------------------------------


def test_the_route_imports_the_seams_rather_than_re_declaring_them() -> None:
    """Three doors, one reading of "entitled" — asserted, not reviewed.

    What would fail here: this module growing its own
    ``PerspectiveResolverProtocol`` or its own check order. The two would
    agree on the day they were written and diverge on the first edit, and the
    HTTP door is the one an operator is most likely to reach first.

    **Re-derived at ``24.6-09``.** The shared function this door calls moved
    one layer out: it is
    :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement` — the ONE
    governed step, which runs ``entitled_perspective`` *and* the replay and
    disclosure that ``D-IMPL-256`` puts on the same side of the boundary. The
    claim is unchanged and strictly stronger: the door not only fails to
    re-declare the seams, it no longer holds the ``except`` that used to make
    it the thing that decided what a denial looked like.
    """
    import ccf_runtime.http_api.routes.product as route

    source = inspect.getsource(route)
    assert "from ccf_runtime.authz.delivery_boundary import" in source
    assert "govern_entitlement(" in source
    assert "from ccf_runtime.authz.product_entitlement import" in source
    # Nothing is re-declared here: the Protocols are imported names, never
    # class statements in this module.
    assert "class PerspectiveResolverProtocol" not in source
    assert "class ProductEntitlementSourceProtocol" not in source
    # And the order itself is not re-implemented — the raising checks are
    # reached through the shared step, never called here.
    assert "require_schema" not in source
    assert "require_role" not in source

    # The last two claims are made against the AST, not the text: this
    # module's own prose *names* both of them (it says, in so many words, that
    # it holds no `except ProductEntitlementRefused`), so a substring test
    # measures the docstring rather than the code. Found by writing the
    # substring test first and watching it go red on a comment.
    tree = ast.parse(source)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "govern_entitlement" in called
    assert "entitled_perspective" not in called

    caught = {
        name.id
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler)
        for name in ast.walk(node.type)
        if isinstance(name, ast.Name)
    }
    # The catch moved with the decision: `govern_entitlement` owns it, and a
    # second one here would put the transport back in charge of minting replay
    # (`D-IMPL-256`, criterion 36).
    assert "ProductEntitlementRefused" not in caught


# --- the refusals ----------------------------------------------------------


def test_an_entitled_caller_is_served(fabric: Fabric, tmp_path: Path) -> None:
    """The happy path, so every refusal below refuses something real.

    The canonical-bytes assertion moved here from the ungoverned
    retrieval test in ``test_routes.py`` when D-IMPL-108 made that posture
    refuse: the claim *this route serves the fabric's own product, byte for
    byte* is still worth making, and the governed configuration is now the
    only place it can be made.
    """
    app = _entitled_app(fabric, tmp_path)

    response = _get(app, fabric, token=TOKEN)

    assert response.status_code == 200
    assert response.content == canonical_bytes(
        fabric.product_servable.product
    )


def test_an_absent_product_is_a_404_behind_the_governed_door(
    fabric: Fabric, tmp_path: Path
) -> None:
    """Absence is still absence — moved here with the happy path above.

    What would fail here: a door whose new governance turned every miss into a
    503, which would make an unregistered lane indistinguishable from an
    unconfigured deployment. The perspective refusal and the product refusal
    are different facts and stay different status codes.
    """
    app = _entitled_app(fabric, tmp_path)
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/9.9.9",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 404


def test_the_door_forwards_the_perspective_it_authorized(
    fabric: Fabric, tmp_path: Path
) -> None:
    """DI-15.5-03, closed — asserted on the VALUE, not on the parameter.

    A test that only checked the resolver *has* a ``perspective`` parameter
    would pass against a door that forwarded a freshly-constructed one, which
    is precisely the state this plan exists to end. So this observes what the
    resolver actually received and compares it against what
    ``_resolver`` — this deployment's perspective seam — returned for the same
    grant.

    What would fail here: a door that re-derived the perspective after the
    entitlement decided, or forwarded one belonging to a different principal,
    or served the product before the decision ran.
    """
    app = _entitled_app(fabric, tmp_path)
    before = len(fabric.resolver_calls)

    response = _get(app, fabric, token=TOKEN, role=ROLE)

    assert response.status_code == 200
    forwarded, _request = fabric.resolver_calls[before]
    assert forwarded == Perspective(principal_id=PRINCIPAL, role=ROLE)


def test_a_refused_caller_reaches_no_resolver_at_all(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The refusal leg, stated as an absence of forwarding.

    The companion to the test above: forwarding the authorized perspective is
    only a security property if an *unauthorized* caller never reaches the
    seam. What would fail here: a door that resolved first and decided after.
    """
    app = _entitled_app(fabric, tmp_path)
    before = len(fabric.resolver_calls)

    response = _get(app, fabric, token=STRANGER_TOKEN)

    assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    assert len(fabric.resolver_calls) == before


def test_the_request_axes_are_assembled_at_the_door(
    fabric: Fabric, tmp_path: Path
) -> None:
    """D-IMPL-98's request surface, validated where it crosses the door.

    The four §6.3 axes arrive as query parameters — the whitepaper's own
    ``?intent=…&freshness=…`` shape — and the door assembles them into a typed
    :class:`~ccf.products.request.ProductRequest` whose ``schema_name`` and
    ``schema_version`` come from the **path it resolved**, never from the
    caller. What would fail here: a request reaching the resolver addressed to
    a class other than the one being served, which this arrangement makes
    unrepresentable rather than merely refused.
    """
    app = _entitled_app(fabric, tmp_path)
    address = fabric.product_address
    before = len(fabric.resolver_calls)

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}"
        f"?subject=acme-bank%2Fcounterparty%2Fnorthwind"
        f"&intent=credit-review&freshness=intraday"
        f"&asked_at=2026-03-01T00%3A00%3A00%2B00%3A00",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 200
    _perspective, asked = fabric.resolver_calls[before]
    assert asked is not None
    assert asked.schema_name == address.product_class
    assert asked.schema_version == address.version
    assert asked.subject == "acme-bank/counterparty/northwind"
    assert asked.intent == "credit-review"
    assert asked.freshness == "intraday"
    assert asked.asked_at == datetime(2026, 3, 1, tzinfo=UTC)
    assert asked.parameters == {}


def test_a_partial_request_address_is_refused(
    fabric: Fabric, tmp_path: Path
) -> None:
    """A defaulted axis is a question nobody asked, answered anyway.

    What would fail here: the door filling in the three axes a caller omitted,
    which would put a literal back where D-IMPL-98 removed one.
    """
    app = _entitled_app(fabric, tmp_path)
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}"
        f"?intent=credit-review",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]["error_code"]
        == ERROR_PRODUCT_REQUEST_INCOMPLETE
    )


def test_a_caller_that_asks_nothing_forwards_no_request(
    fabric: Fabric, tmp_path: Path
) -> None:
    """``None`` is the honest absence, never a manufactured question."""
    app = _entitled_app(fabric, tmp_path)
    before = len(fabric.resolver_calls)

    assert _get(app, fabric, token=TOKEN).status_code == 200

    _perspective, asked = fabric.resolver_calls[before]
    assert asked is None


def test_an_undeclared_principal_is_refused_with_a_typed_code(
    fabric: Fabric, tmp_path: Path
) -> None:
    """A real token is not a grant: authentication is not entitlement.

    **Re-derived at ``24.6-09``: the typed code is still the contract, and it
    is now internal truth.** It used to be read off a ``403`` body, which told
    a caller with no grant *which* of five things went wrong — as fine-grained
    a leak as prose (``D-IMPL-253`` Q27). The consumer now sees the one shared
    outcome at its one status, and the code is asserted where it actually
    lives: the replay record this denial minted before the response was
    released. Both halves, because neither implies the other — a door that
    disclosed nothing and recorded nothing would pass the first alone.
    """
    entitled = _entitled(fabric, tmp_path)

    response = _get(entitled.app, fabric, token=STRANGER_TOKEN)

    assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    body = response.json()
    assert body["kind"] == SUBJECT_UNAVAILABLE
    assert ERROR_PRINCIPAL_NOT_ENTITLED not in json.dumps(body)

    internal = entitled.internal(body["refusal"]["replay_reference"])
    assert internal.kind == SUBJECT_UNAVAILABLE
    assert json.loads(internal.fields["cause"]) == "unauthorized"
    assert json.loads(internal.fields["error_code"]) == ERROR_PRINCIPAL_NOT_ENTITLED


def test_an_unentitled_class_is_refused_with_a_typed_code(
    fabric: Fabric, tmp_path: Path
) -> None:
    """T-15.5-20 on the HTTP door, with the same constant the MCP doors carry."""
    entitled = _entitled(
        fabric,
        tmp_path,
        permitted_classes=frozenset(
            {f"{fabric.product_address.product_class}-not-this-one"}
        ),
    )

    response = _get(entitled.app, fabric, token=TOKEN)

    assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    body = response.json()
    assert body["kind"] == SUBJECT_UNAVAILABLE
    # The class name was in the ``403``'s prose. It must not survive into the
    # disclosure-controlled members — the statement and the fields — which is
    # where the fabric's own account of the refusal lives. It DOES stay on
    # `request` and `resource`, and that is correct rather than tolerated:
    # those are what the caller itself supplied and addressed, so they tell it
    # nothing it did not already know (`disclose` records exactly that reason).
    refusal = body["refusal"]
    assert fabric.product_address.product_class not in refusal["detail"]
    assert fabric.product_address.product_class not in json.dumps(refusal["fields"])
    assert refusal["request"]["product_id"] == fabric.product_address.product_class

    internal = entitled.internal(body["refusal"]["replay_reference"])
    assert json.loads(internal.fields["error_code"]) == ERROR_PRODUCT_CLASS_UNENTITLED
    assert fabric.product_address.product_class in internal.detail


def test_an_ungranted_requested_role_is_refused_with_a_typed_code(
    fabric: Fabric, tmp_path: Path
) -> None:
    """T-15.5-19: ``?role=`` is a request, and asking is not receiving."""
    entitled = _entitled(fabric, tmp_path)

    response = _get(entitled.app, fabric, token=TOKEN, role=UNGRANTED_ROLE)

    assert response.status_code == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    body = response.json()
    assert body["kind"] == SUBJECT_UNAVAILABLE

    internal = entitled.internal(body["refusal"]["replay_reference"])
    assert json.loads(internal.fields["error_code"]) == ERROR_PRODUCT_ROLE_UNGRANTED


def test_a_granted_requested_role_is_served(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The mirror case: without it, a door that refused every role would pass.

    A refusal test alone is satisfied by a door that refuses everything, which
    is a different defect wearing the same green tick.
    """
    app = _entitled_app(fabric, tmp_path)

    response = _get(app, fabric, token=TOKEN, role=ROLE)

    assert response.status_code == 200


def test_the_refusal_body_is_the_one_shape_and_never_free_text(
    fabric: Fabric, tmp_path: Path
) -> None:
    """D-08: the code is the contract, the prose is human context.

    **The shape changed at ``24.6-09``, and that is the point.** This door
    rendered entitlement in ``{"error_code", "message"}`` and every fabric
    refusal in ``{"kind", "refusal_type", "refusal"}`` — two schemas at one
    door, which is a D-27 leak by *body schema* before a single value is read
    (``D-IMPL-253`` amendment 2 (4) names it in the list of six). There is one
    shape now, and the old one is asserted **absent** rather than merely not
    asserted: an ``error_code`` key anywhere in the body is the regression.
    """
    entitled = _entitled(fabric, tmp_path)

    response = _get(entitled.app, fabric, token=STRANGER_TOKEN)
    body = response.json()

    assert set(body) == {"kind", "refusal_type", "refusal"}, body
    assert body["kind"] == SUBJECT_UNAVAILABLE
    assert body["refusal_type"] == SubjectUnavailableRefusal.__name__
    assert isinstance(body["refusal"], dict)
    # The retired shape, asserted gone: no `detail`/`error_code` pair at the
    # top level, which is the whole of what `refusal_detail` produced.
    assert "detail" not in body
    assert "error_code" not in body
    assert "message" not in body
    # `error_code` survives as a KEY inside `fields` and that is deliberate,
    # not a leak: the disclosure step replaces the VALUE and keeps the key, so
    # the shell's *shape* cannot differ between two internal causes
    # (`D-IMPL-253` amendment 2 (4) names field presence explicitly). What must
    # not cross at `minimal` is the value, and it does not.
    assert set(body["refusal"]["fields"]) == {"cause", "error_code"}
    assert json.loads(body["refusal"]["fields"]["error_code"]) == "undisclosed"
    assert json.loads(body["refusal"]["fields"]["cause"]) == "undisclosed"


# --- the dead configurations -----------------------------------------------


def test_entitlement_without_an_auth_hook_warns_loudly(
    fabric: Fabric, tmp_path: Path
) -> None:
    """T-15.5-21: intent to gate plus zero enforcement must not be silent.

    What would fail here: the seams accepted with no auth hook and no signal.
    The deployment then serves every class to every caller while believing it
    is gated — the WR-05 failure, on a wider surface.
    """
    source = ControlPlaneProductEntitlementSource(
        control_plane=ControlPlaneRegistry(), clock=lambda: AUDIT_INSTANT
    )
    with pytest.warns(CcfDeadEntitlementWarning):
        with pytest.warns(CcfInsecureDefaultWarning):
            create_app(
                _deps(fabric),
                product_entitlement=source,
                perspective_resolver=_resolver,
                # `24.6-09`: an entitling door binds the recorder or is not
                # built. The dead-entitlement posture is unchanged by that —
                # both warnings still fire — and this keyword is what proves
                # the two rulings compose rather than one having eaten the
                # other.
                refusal_recorder=ReplayRefusalRecorder(
                    artifact_store=FileArtifactStore(root=tmp_path / "dead"),
                    replay_record_class=REPLAY_RECORD_CLASS,
                    tenant_id=fabric.product_address.tenant,
                    assembly_mode="algorithmic",
                    policy_bundle_pin=None,
                    disclosure_level_for=source.disclosure_level_for,
                ),
            )


def test_half_a_governance_pair_is_refused_at_build_time(
    fabric: Fabric,
) -> None:
    """An entitlement with nothing to decide about is not a configuration.

    What would fail here: one seam accepted alone, producing a door that looks
    governed in the composition root and enforces half a decision — or none.
    """
    import ccf_runtime.http_api.routes.product as route

    with pytest.raises(ValueError, match="together"):
        route.build_router(_deps(fabric), perspective_resolver=_resolver)

    with pytest.raises(ValueError, match="together"):
        route.build_router(
            _deps(fabric),
            entitlement_source=ControlPlaneProductEntitlementSource(
                control_plane=ControlPlaneRegistry(),
                clock=lambda: AUDIT_INSTANT,
            ),
        )


def test_the_unbound_posture_no_longer_serves_and_says_which_seam_is_missing(
    fabric: Fabric,
) -> None:
    """The T-07-24 preservation is **superseded by D-IMPL-108**, deliberately.

    This test previously asserted 200: with no seams bound, ``GET /product``
    served a gate-admitted product to anyone who asked, on the reasoning that
    the acknowledged insecure posture (D-IMPL-73) is a supported one and a
    required seam would make it unbuildable. That reasoning still holds for
    ``create_app`` — the app builds, and every other noun answers exactly as
    it did — but it no longer reaches the product door, because the resolver
    seam now requires the authorized
    :class:`~ccf.projection.plan.Perspective`.

    The trade is stated plainly rather than smuggled: the ungoverned posture
    gives up **one route**, and gains the property that no product this fabric
    serves over HTTP was ever shaped under a perspective nobody named. The
    optional-here / required-on-MCP split survives at the level it was about —
    ``create_app`` still accepts no seams and still builds.

    What would fail here: a default sneaking back onto the perspective
    argument, or the route quietly reverting to serving without one.
    """
    app = create_app(_deps(fabric), acknowledge_insecure_default=True)
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/{address.version}",
    )

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["error_code"] == ERROR_PRODUCT_DOOR_UNGOVERNED
    # The prose names the seam to bind — an operator reading a refusal should
    # not have to read the source to learn what to configure (D-08's shape).
    assert "product_entitlement=" in body["message"]
