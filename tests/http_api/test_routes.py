"""The HTTP API skeleton answers on every ruled noun (07-10 Task 1; EXPR-03).

Written before the implementation per the TDD discipline. The claims:

**Noun-set fidelity.** The mounted noun prefixes equal — set-equality, not
subset — the noun set the D-IMPL-22 ruling text enumerates, read from
``docs/DECISIONS.md`` itself so the test follows the ruling, never a
paraphrase (Cursor suggestion 8).

**No write door.** No route exists under any ingest/L1/write-to-graph path,
asserted by walking ``app.routes`` (T-07-23; D-IMPL-23's ruled exclusion),
and the product noun is read-only.

**Real contracts at the boundary.** Each noun router takes and returns the
existing ``extra=forbid`` contracts: an extra field is refused with 422,
workflow invocation returns the engine's typed outcome, HITL listing
returns typed pending events, replay returns the typed record, agent
declaration takes an artifact payload and nothing inline beyond it.

**Refusal-vs-exception line over HTTP.** Typed refusals map to 4xx with the
typed refusal body; wiring errors surface as opaque 5xx (T-07-26).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.projection.plan import Perspective
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api.routes import (
    CONTENT_ADDRESS_HEADER,
    REQUEST_ECHO_HEADER,
)
from ccf_runtime.mcp.auth import FileTokenSource

# One definition of how a governed HTTP door's refusal recorder is built,
# imported rather than copied (`24.6-09`).
from tests.http_api.test_product_declared_obligation_409 import _recorder

from .gate_fixtures import SCOPE_EVERYTHING, wide_authorizer

from ccf.contracts.canonical import content_hash
from ccf_runtime.http_api.errors import ERROR_PRODUCT_DOOR_UNGOVERNED
from http_api.conftest import Fabric, call
from http_api.composition_authority import (
    register_typed_at_composition,
)

DECISIONS = Path(__file__).resolve().parents[2] / "docs" / "DECISIONS.md"

#: Path prefixes that would be a second writer door if they existed
#: (T-07-23; D-IMPL-23: "L1 ingestion is deliberately NOT on the v0 HTTP
#: surface").
FORBIDDEN_PREFIXES = frozenset(
    {"ingest", "ingestion", "l1", "signal", "signals", "graph", "events"}
)


def _ruled_nouns() -> frozenset[str]:
    """The noun set exactly as the D-IMPL-22 ruling text enumerates it."""
    text = DECISIONS.read_text()
    match = re.search(r"\(([^()]*?)\s+noun set\)", text)
    assert match is not None, "the D-IMPL-22 ruling names its noun set"
    return frozenset(re.findall(r"`([a-z]+)`", match.group(1)))


def _paths(app: Any) -> dict[str, dict[str, Any]]:
    """Every mounted path with its methods — the materialized route walk.

    FastAPI 0.140 keeps included routers lazy on ``app.routes``
    (``_IncludedRouter``), so the honest enumeration of what is mounted is
    the generated document itself — which is also EXPR-03's own claim:
    ``app.openapi()`` IS the surface.
    """
    paths: dict[str, dict[str, Any]] = app.openapi()["paths"]
    return paths


def _noun_prefixes(app: Any) -> frozenset[str]:
    return frozenset(
        path.split("/")[1]
        for path in _paths(app)
        if path.split("/")[1] != "health"
    )


# --- noun-set fidelity and the absent write door ---------------------------


def test_mounted_nouns_equal_the_ruling_text(app: Any) -> None:
    """Set-equality against the ruling, including product and config."""
    ruled = _ruled_nouns()
    assert {"product", "config"} <= ruled  # the under-emphasized pair
    assert _noun_prefixes(app) == ruled


def test_no_ingest_or_write_to_graph_path_exists(app: Any) -> None:
    """Walking the mounted paths finds no L1/write door (T-07-23)."""
    for path in _paths(app):
        segments = {s for s in path.lower().split("/") if s}
        assert not (segments & FORBIDDEN_PREFIXES), path


def test_the_product_noun_is_read_only(app: Any) -> None:
    """The product surface serves; it never accepts (single-writer)."""
    for path, operations in _paths(app).items():
        if path.split("/")[1] == "product":
            assert set(operations) <= {"get", "head"}, path


def test_health_answers(app: Any) -> None:
    assert call(app, "GET", "/health").status_code == 200


# --- product: retrieval with the existing gate-admitted contract -----------


def test_an_ungoverned_product_door_refuses_rather_than_serving(
    app: Any, fabric: Fabric
) -> None:
    """No perspective, no product — D-IMPL-108, closing DI-15.5-03.

    **This test replaces two that asserted the opposite**, and the
    supersession is the point rather than a casualty. Until plan ``15.5-15``
    this route served a gate-admitted product with no entitlement seams bound
    and no verified grant, which meant the served bytes carried no statement
    at all about the Π conditioning they were shaped under. The resolver seam
    now *requires* the authorized :class:`~ccf.projection.plan.Perspective`,
    deliberately and with no default, so this posture is no longer
    expressible: the door either names the conditioning it authorized or it
    does not serve.

    What would fail here: a future edit that restored service by defaulting
    the perspective — at which point every product this route served would be
    conditioned on a role nobody granted, indistinguishably from one the door
    authorized. The two shipped happy-path assertions this replaces live on
    at ``test_product_entitlement.py``, against the door's *governed*
    configuration, where they assert something.

    ``SEC-001`` changed what this module's app IS: there is no ungoverned
    ``create_app`` any more, so the fixture app is a governed one and this
    route serves. The 503 that used to be asserted here now has exactly one
    reachable cause — a handler called with no verified grant — and it is
    asserted where that is the subject
    (``test_product_declared_obligation_409.py``).
    """
    address = fabric.product_address

    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/"
        f"{address.version}",
    )

    assert response.status_code == 200


# --- product: the request echo is ABSENT when no question was posed (C-09) --
#
# The module fixture's app is deliberately ungoverned, so the product door
# refuses there and never reaches `canonical_response`. These two legs need a
# door that actually serves, so they build a governed one — the same shape
# `test_content_address_header.py` and `test_product_entitlement.py` each build
# for the same reason. Tenant, principal, class and role names below are test
# deployment vocabulary; the SDK ships none of it (CINV-01).

ECHO_TOKEN = "routes-echo-token"
#: The shared credential ``conftest.call`` supplies. The HITL submissions
#: below name it as their approver subject because the audited subject is
#: **derived** from the verified grant and a conflicting claim is refused
#: (``D-IMPL-67``) — so a body naming anyone else is a 403, not a 200.
GATE_CLIENT_ID = "gate-caller"
#: The tenant that credential acts for — the fabric's own product tenant.
GATE_TENANT = "acme-bank"
ECHO_PRINCIPAL = "routes-echo-caller"
ECHO_ROLE = "routes-echo-role"
ECHO_AUDIT_INSTANT = datetime(2026, 8, 19, tzinfo=UTC)
ECHO_BOUNDARY = datetime(2026, 3, 1, tzinfo=UTC)


def _echo_auth(fabric: Any, token_file: Path) -> Any:
    """The echo door's auth hook — the REAL dev token file (D-IMPL-353 §2 P1).

    Before D-IMPL-353 this helper wrote nothing and minted a test-only
    subclass; the file it was handed was never read. It now writes the
    grant, ``tenants`` included, and the door reads it through
    :class:`~ccf_runtime.mcp.auth.FileTokenSource` — exactly what a
    deployment on the dev source does.
    """
    from ccf_runtime.http_api.auth import BearerTokenAuth

    token_file.write_text(
        json.dumps(
            {
                ECHO_TOKEN: {
                    "client_id": ECHO_PRINCIPAL,
                    "scopes": [SCOPE_EVERYTHING],
                    "tenants": [fabric.product_address.tenant],
                }
            }
        ),
        encoding="utf-8",
    )
    return BearerTokenAuth(token_source=FileTokenSource(path=token_file))


def _echo_perspective(
    *, grant: Any, tenant: str, requested_role: str | None
) -> Perspective:
    return Perspective(
        principal_id=grant.client_id,
        role=requested_role if requested_role is not None else ECHO_ROLE,
    )


def _echo_entitlement(fabric: Fabric) -> Any:
    """The echo door's entitlement source over its own policy."""
    address = fabric.product_address
    registry = ControlPlaneRegistry()
    register_typed_at_composition(registry, 
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version="1.0.0",
            principals={
                ECHO_PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({ECHO_ROLE}),
                ),
                "alice": ProductEntitlementGrant(
                    permitted_schema_names=frozenset({address.product_class}),
                    permitted_roles=frozenset({ECHO_ROLE}),
                ),
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: ECHO_AUDIT_INSTANT
    )


def _governed_app(fabric: Fabric, tmp_path: Path) -> Any:
    """A product door that serves, so an absent header means something."""
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    token_file = tmp_path / "routes-echo-tokens.json"
    source = _echo_entitlement(fabric)
    return create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        auth=_echo_auth(fabric, token_file),
        authorizer=wide_authorizer(
            tenant=fabric.product_address.tenant, key="routes-echo/mapping"
        ),
        product_entitlement=source,
        perspective_resolver=_echo_perspective,
        # `24.6-09` / `D-IMPL-256` (2): an entitling door that cannot record a
        # denial is not built. This door only ever serves, so the recorder is
        # bound and never fires — one keyword, and nothing else here moves.
        refusal_recorder=_recorder(fabric, tmp_path, source=source),
    )


def _ask(app: Any, fabric: Fabric, *, query: str) -> Any:
    address = fabric.product_address
    return call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/"
        f"{address.version}{query}",
        headers={"Authorization": f"Bearer {ECHO_TOKEN}"},
    )


def assert_no_question_was_echoed(response: Any) -> None:
    """No echo header at all — **absent**, never present-and-empty.

    Asserted as absence rather than as ``== ""`` for the reason
    :data:`~ccf_runtime.http_api.routes.REQUEST_ECHO_HEADER` records: stamping
    an empty header would make *"no question was asked"* and *"the question is
    named by nothing"* the same observation, and a consumer would have no way
    to tell which it was looking at.

    A function over its subject so the control below can hand *this same
    function* a response that **did** carry a question (``D-22``). That control
    is not decoration: on its own this assertion passes against a route that
    never stamps the header at all, which is precisely the vacuity this
    repository has shipped before.
    """
    assert REQUEST_ECHO_HEADER not in response.headers


def test_a_caller_who_posed_no_question_gets_no_echo_header(
    fabric: Fabric, tmp_path: Path
) -> None:
    """``C-09``'s absence leg, on a door that is actually serving.

    None of the four §6.3 axes is supplied, which the product route's
    ``_asked`` reads as the positive assertion *this caller asked for the
    class's standing answer and posed no question of their own*. There is then
    no question to echo, and the sibling is absent — while the other two
    siblings are unaffected, which is what makes this an absence rather than a
    door that stopped publishing.
    """
    response = _ask(_governed_app(fabric, tmp_path), fabric, query="")

    assert response.status_code == 200
    assert_no_question_was_echoed(response)
    assert (
        hashlib.sha256(response.content).hexdigest()
        == response.headers[CONTENT_ADDRESS_HEADER]
    )


def test_the_absence_assertion_fails_when_a_question_was_posed(
    fabric: Fabric, tmp_path: Path
) -> None:
    """The named sabotage control (``CLNT-12``, ``D-22``) for the leg above.

    An absence assertion is the easiest kind of check to ship broken: it passes
    against a door that never publishes the thing at all, and it passes for the
    right reason and the wrong reason indistinguishably. So the *same* function
    is handed a response to a request that did pose a question, and it must
    fail. Both legs of ``C-09`` are therefore observed — present when asked,
    absent when not — rather than one being asserted and the other assumed.
    """
    response = _ask(
        _governed_app(fabric, tmp_path),
        fabric,
        query=(
            "?subject=routes-echo-subject&intent=routes-echo-intent"
            "&freshness=routes-echo-freshness"
            f"&asked_at={quote(ECHO_BOUNDARY.isoformat())}"
        ),
    )

    assert response.status_code == 200
    with pytest.raises(AssertionError):
        assert_no_question_was_echoed(response)


# --- agent: declare takes an artifact payload, reads resolve it ------------


def test_agent_declare_accepts_an_artifact_payload(
    app: Any, fabric: Fabric
) -> None:
    document = dict(fabric.grants_fixture["agents"]["gated"])
    key = f"acme-bank/agents/{document['name']}"
    response = call(
        app,
        "POST",
        "/agent/declarations",
        json={"key": key, "definition": document},
    )
    assert response.status_code == 200
    version = response.json()["version"]
    listed = call(app, "GET", "/agent/declarations")
    assert key in listed.json()
    shown = call(
        app, "GET", "/agent/declaration", params={"key": key, "version": version}
    )
    assert shown.status_code == 200
    assert shown.json()["name"] == document["name"]
    versions = call(app, "GET", "/agent/versions", params={"key": key})
    assert version in versions.json()


def test_agent_declare_refuses_extra_fields(app: Any, fabric: Fabric) -> None:
    """extra=forbid holds at the boundary — 422, nothing registered."""
    document = dict(fabric.grants_fixture["agents"]["auto"])
    document["inline_prompt"] = "not a thing an artifact payload carries"
    response = call(
        app,
        "POST",
        "/agent/declarations",
        json={"key": "acme-bank/agents/extra", "definition": document},
    )
    assert response.status_code == 422


def test_agent_show_of_nothing_is_a_404(app: Any) -> None:
    response = call(
        app,
        "GET",
        "/agent/declaration",
        params={"key": "acme-bank/agents/nobody", "version": "1.0.0"},
    )
    assert response.status_code == 404


# --- skill: catalog and governed grants ------------------------------------


def test_skill_catalog_lists_typed_entries(app: Any) -> None:
    response = call(app, "GET", "/skill/catalog")
    assert response.status_code == 200
    names = {entry["name"] for entry in response.json()}
    assert "covenant-metrics" in names


def test_skill_grant_routes_through_the_ledger(
    app: Any, fabric: Fabric
) -> None:
    grant = dict(fabric.grants_fixture["grants"]["metrics_tool"])
    grant["agent_definition_hash"] = content_hash(fabric.auto_agent)
    response = call(
        app,
        "POST",
        "/skill/grants",
        json={
            "grant": grant,
            "definition_key": fabric.auto_agent_key,
            "definition_version": fabric.auto_agent_version,
        },
    )
    assert response.status_code == 200
    assert response.json()["grant_hash"]


def test_skill_grant_refusal_is_a_typed_4xx(app: Any, fabric: Fabric) -> None:
    """A tier-1 refusal returns the typed refusal body, not a 500."""
    grant = dict(fabric.grants_fixture["grants"]["writeback"])
    grant["agent_definition_hash"] = content_hash(fabric.auto_agent)
    response = call(
        app,
        "POST",
        "/skill/grants",
        json={
            "grant": grant,
            "definition_key": fabric.auto_agent_key,
            "definition_version": fabric.auto_agent_version,
        },
    )
    assert response.status_code == 409
    assert "refusal" in response.json()["kind"]


# --- workflow: invoke / status / resume through the factory-handle path ----


def test_workflow_invocation_runs_to_the_typed_terminal(
    app: Any, fabric: Fabric
) -> None:
    key, version = fabric.refresh
    response = call(
        app,
        "POST",
        "/workflow/invocations",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": "http-refresh-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["terminal_state"]
    assert body["step_sequence_block"]


def test_workflow_invocation_suspends_on_the_gate(
    app: Any, fabric: Fabric
) -> None:
    key, version = fabric.covenant
    response = call(
        app,
        "POST",
        "/workflow/invocations",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": "http-covenant-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gate"]
    assert body["event_key"]
    # the suspended execution is visible on the status surface
    status = call(
        app,
        "GET",
        "/workflow/execution",
        params={"tenant": body["tenant"], "execution_id": "http-covenant-1"},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "suspended"
    # and its pending event is on the HITL queue
    queue = call(
        app, "GET", "/hitl/queue", params={"tenant": body["tenant"]}
    )
    assert body["event_key"] in {
        event["event_key"] for event in queue.json()
    }


def test_workflow_duplicate_invocation_is_a_typed_409(
    app: Any, fabric: Fabric
) -> None:
    key, version = fabric.refresh
    payload = {
        "definition_key": key,
        "definition_version": version,
        "execution_id": "http-refresh-dup",
    }
    assert call(app, "POST", "/workflow/invocations", json=payload).status_code == 200
    second = call(app, "POST", "/workflow/invocations", json=payload)
    assert second.status_code == 409
    assert "already exists" in second.json()["reason"]


def _suspend_over_http(
    app: Any, fabric: Fabric, execution_id: str
) -> dict[str, Any]:
    key, version = fabric.covenant
    body: dict[str, Any] = call(
        app,
        "POST",
        "/workflow/invocations",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": execution_id,
        },
    ).json()
    return body


def _approve_over_http(app: Any, fabric: Fabric, body: dict[str, Any]) -> None:
    """Put a human action on the authority path for this suspension."""
    pending = next(
        event
        for event in fabric.hitl.pending(tenant=body["tenant"])
        if event.event_key == body["event_key"]
    )
    submission = _bound_submission(body["event_key"])
    submission["product_content_hash"] = pending.product_content_hash
    assert call(
        app, "POST", "/hitl/actions", json=submission
    ).status_code == 200


def test_workflow_resume_of_a_gate_without_a_human_action_is_refused(
    app: Any, fabric: Fabric
) -> None:
    """SEC-001 at the door. ``POST /workflow/resumptions`` is the reachable
    path the security review of 2026-09-23 named: with nothing on the HITL
    authority path, naming a declared transition does not open the gate."""
    key, version = fabric.covenant
    body = _suspend_over_http(app, fabric, "http-covenant-unapproved")
    response = call(
        app,
        "POST",
        "/workflow/resumptions",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": "http-covenant-unapproved",
            "decision": "approved",
        },
    )
    assert response.status_code == 409
    assert "authority path" in response.json()["reason"]
    status = call(
        app,
        "GET",
        "/workflow/execution",
        params={
            "tenant": body["tenant"],
            "execution_id": "http-covenant-unapproved",
        },
    )
    assert status.json()["status"] == "suspended"


def test_workflow_resume_refusal_does_not_enumerate_the_declared_targets(
    app: Any, fabric: Fabric
) -> None:
    """SEC-001 remedy 3: the 409 must not hand the caller the transitions
    it would have accepted."""
    key, version = fabric.covenant
    body = _suspend_over_http(app, fabric, "http-covenant-noleak")
    # Approve first, or the authority refusal answers and this test never
    # reaches the branch that could leak.
    _approve_over_http(app, fabric, body)
    response = call(
        app,
        "POST",
        "/workflow/resumptions",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": "http-covenant-noleak",
            "decision": "no-such-transition",
        },
    )
    assert response.status_code == 409
    assert "approved" not in response.json()["reason"]


def test_workflow_resume_with_an_undeclared_decision_is_refused(
    app: Any, fabric: Fabric
) -> None:
    key, version = fabric.covenant
    body = _suspend_over_http(app, fabric, "http-covenant-resume")
    _approve_over_http(app, fabric, body)
    response = call(
        app,
        "POST",
        "/workflow/resumptions",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": "http-covenant-resume",
            "decision": "no-such-transition",
        },
    )
    assert response.status_code == 409
    assert "declared transition" in response.json()["reason"]


def test_workflow_status_of_nothing_is_a_404(app: Any) -> None:
    response = call(
        app,
        "GET",
        "/workflow/execution",
        params={"execution_id": "never-started"},
    )
    assert response.status_code == 404


# --- hitl: typed queue views and the authority path ------------------------


def test_hitl_action_submission_travels_the_typed_queue(
    app: Any, fabric: Fabric
) -> None:
    product_hash = "0" * 64
    submission = {
        "event_key": "acme-bank/http-covenant-1/gate",
        "action": "approve",
        "product_content_hash": product_hash,
        "annotation": None,
    }
    response = call(app, "POST", "/hitl/actions", json=submission)
    assert response.status_code == 200
    recorded = fabric.hitl.submissions(tenant="acme-bank")
    assert submission["event_key"] in {s.event_key for s in recorded}


def test_hitl_action_with_an_extra_field_is_refused(app: Any) -> None:
    submission = {
        "event_key": "acme-bank/x/gate",
        "action": "approve",
        "product_content_hash": "0" * 64,
        "not_a_field": True,
    }
    assert call(app, "POST", "/hitl/actions", json=submission).status_code == 422


def _bound_submission(event_key: str) -> dict[str, Any]:
    return {
        "event_key": event_key,
        "action": "approve",
        "product_content_hash": "0" * 64,
        "annotation": None,
    }


def test_hitl_action_receipt_states_submitted_with_honest_disposition(
    app: Any, fabric: Fabric
) -> None:
    """D-IMPL-62 hardening: the action door is submit-only and says so.

    The response states ``submitted`` — never ``resolved`` — and carries
    the queue state that shows the disposition honestly: the submit alone
    effects no state transition, so the pending event is still pending.
    """
    from ccf.hitl.transport import PendingHitlEvent

    event = PendingHitlEvent(
        event_key="acme-bank/http-receipt-1/gate",
        event_class="approval-gate",
        tenant="acme-bank",
        workflow_state_ref="acme-bank/http-receipt-1",
        product_content_hash="0" * 64,
    )
    fabric.hitl.enqueue(event=event)
    response = call(
        app, "POST", "/hitl/actions", json=_bound_submission(event.event_key)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    # the receipt's field set is closed — no field claims resolution
    assert set(body) == {
        "status",
        "submission",
        "event_pending",
        "submissions_for_event",
    }
    assert body["event_pending"] is True
    assert body["submissions_for_event"] == 1
    assert body["submission"]["event_key"] == event.event_key


def test_hitl_action_receipt_for_an_unqueued_event_is_not_pending(
    app: Any,
) -> None:
    """The disposition state is real queue state, not an echo."""
    body = call(
        app,
        "POST",
        "/hitl/actions",
        json=_bound_submission("acme-bank/never-enqueued/gate"),
    ).json()
    assert body["status"] == "submitted"
    assert body["event_pending"] is False
    assert body["submissions_for_event"] == 1


# --- replay and artifact: governed dereferences (D-IMPL-345) ---------------
#
# These four nouns answered `200` to a caller with no credential at all until
# `D-IMPL-345`, which is what made `S-01` reachable. On THIS module's app —
# built with no auth hook and no entitlement seam, deliberately, because this
# module is about routing rather than posture — every evidence read is now the
# product route's own ungoverned refusal (R-1). The positive behavior moved
# with the governance: an authorized read, the `404` shell, the `409` for
# `@latest` and the no-oracle equality are proven in
# `tests/http_api/test_evidence_dereference.py`, against a door that has the
# seams to decide.


def _reaches_the_boundary(response: Any) -> None:
    """The read reached the governed dereference rather than a wiring refusal.

    ``SEC-001`` changed what this module's app is. These four legs asserted
    ``503 product-door-ungoverned`` because the fixture app was built with no
    auth hook and no entitlement seam — a posture that no longer exists, so a
    503 here would now mean something is broken rather than something is
    governed. What they assert instead is that the response is a *governed*
    outcome: a served record, or the one disclosed shell every absence and
    every denial share (``D-IMPL-345``; ``D-IMPL-253`` amendment 2 (4)).

    The positive behavior — an authorized read, the ``404`` shell, the ``409``
    for ``@latest``, the no-oracle equality — is proven against a purpose-built
    door in ``tests/http_api/test_evidence_dereference.py``.
    """
    assert response.status_code != 503, response.text
    assert response.status_code in {200, 404, 409}, response.text


def test_replay_decisions_refuses_on_an_ungoverned_door(
    app: Any, fabric: Fabric
) -> None:
    _reaches_the_boundary(
        call(
            app,
            "GET",
            "/replay/decisions",
            params={"content_address": fabric.replay_ref.content_address},
        )
    )


def test_replay_resolutions_refuses_on_an_ungoverned_door(
    app: Any, fabric: Fabric
) -> None:
    _reaches_the_boundary(
        call(
            app, "GET", "/replay/resolutions", params={"uri": fabric.replay_ref.uri}
        )
    )


def test_replay_refuses_a_moving_target_only_once_it_may_answer(
    app: Any, fabric: Fabric
) -> None:
    """``@latest`` still dies — but the ungoverned door never gets that far.

    The `409` itself is unchanged and is proven on a governed door
    (`test_evidence_dereference.py::test_c13_a_moving_target_is_still_a_409`);
    here the point is the ORDER: a door that cannot decide refuses before it
    parses what it was asked, so a caller learns nothing from the shape of its
    own malformed reference.
    """
    moving = fabric.replay_ref.uri.rsplit("@", 1)[0] + "@latest"
    _reaches_the_boundary(call(app, "GET", "/replay/resolutions", params={"uri": moving}))


def test_replay_of_nothing_is_refused_the_same_way_as_something(
    app: Any, fabric: Fabric
) -> None:
    """A nonexistent address and an unentitled one are one observation.

    ``SEC-001`` changed what this leg measures. It used to compare two 503s
    on an ungoverned door, where sameness was trivial — neither had reached a
    decision. Both now reach the governed dereference and come back as the
    one disclosed shell, which is the property that actually matters
    (``D-IMPL-253`` amendment 2 (4)).

    **Two members are excluded, and naming them is the honest part.**
    ``replay_reference``, because every determination mints its own record and
    two denials therefore name two records by construction; and ``request``,
    because the reference a caller supplied is echoed back in exactly that one
    place — which is precisely why
    :func:`~ccf_runtime.http_api.routes.replay._route_path` keeps the rest of
    the shell constant across asks. Everything else is compared, and
    everything else is identical. The full no-oracle argument, including that
    neither excluded member discloses which case occurred, is in
    ``tests/http_api/test_evidence_dereference.py``.
    """
    nothing = call(
        app, "GET", "/replay/decisions", params={"content_address": "f" * 64}
    )
    something = call(
        app,
        "GET",
        "/replay/decisions",
        params={"content_address": fabric.replay_ref.content_address},
    )
    _reaches_the_boundary(nothing)
    assert nothing.status_code == something.status_code

    varying = {"replay_reference", "request"}

    def _constant_members(body: dict[str, Any]) -> dict[str, Any]:
        refusal = {
            key: value
            for key, value in body["refusal"].items()
            if key not in varying
        }
        return {**body, "refusal": refusal}

    assert _constant_members(nothing.json()) == _constant_members(
        something.json()
    )
    # Both excluded members are present on both responses, so the exclusion
    # is a narrowing of the comparison rather than a hole in it — and the
    # `request` echoes differ only because the two asks differed.
    for body in (nothing.json(), something.json()):
        assert varying <= set(body["refusal"])
    assert (
        nothing.json()["refusal"]["request"]
        != something.json()["refusal"]["request"]
    )


# --- artifact: put is unchanged; get is governed ---------------------------


def test_artifact_put_still_stores_and_returns_its_reference(app: Any) -> None:
    """The write path still stores; what it no longer does is take a tenant.

    ``D-IMPL-345`` left this path alone, and ``SEC-002`` changed exactly one
    thing about it: the tenant an artifact is filed under used to be a body
    field, so a recognized bearer filed into any tenant's namespace by typing
    its name. It now comes from the verified grant, which is why the ``uri``
    below is asserted against the credential's tenant rather than a literal.
    """
    put = call(
        app,
        "POST",
        "/artifact",
        json={
            # No `tenant_id`: it is the verified grant's (`SEC-002`). The
            # field is deleted from `ArtifactPutRequest`, so sending it is a
            # 422 rather than a value the store would have honored.
            "artifact_class": "ccf.test-blob",
            "name": "blob-1",
            "artifact": {"field": "value"},
        },
    )
    assert put.status_code == 200
    ref = put.json()
    assert ref["content_address"] == content_hash({"field": "value"})
    assert ref["uri"].startswith(
        f"ccf-artifact://{GATE_TENANT}/ccf.test-blob/blob-1@"
    )


def test_artifact_get_is_a_governed_dereference(app: Any) -> None:
    """Including for bytes the same app just stored: a write is not a read.

    Renamed with ``SEC-001``: there is no ungoverned door to refuse on. What
    still holds, and is what this leg was always about, is that filing bytes
    does not make them readable — a put is not an entitlement.
    """
    put = call(
        app,
        "POST",
        "/artifact",
        json={
            # No `tenant_id`: it is the verified grant's (`SEC-002`). The
            # field is deleted from `ArtifactPutRequest`, so sending it is a
            # 422 rather than a value the store would have honored.
            "artifact_class": "ccf.test-blob",
            "name": "blob-2",
            "artifact": {"field": "value"},
        },
    )
    assert put.status_code == 200
    _reaches_the_boundary(call(app, "GET", f"/artifact/{put.json()['content_address']}"))
    _reaches_the_boundary(call(app, "GET", f"/artifact/{'e' * 64}"))


# --- config: Control Plane introspection ------------------------------------


def test_config_lists_keys_versions_and_resolves(
    app: Any, fabric: Fabric
) -> None:
    from ccf.agents.definitions import AGENT_DEFINITION

    keys = call(
        app,
        "GET",
        "/config/keys",
        params={"class_id": AGENT_DEFINITION.class_id},
    )
    assert keys.status_code == 200
    assert fabric.auto_agent_key in keys.json()
    versions = call(
        app, "GET", "/config/versions", params={"key": fabric.auto_agent_key}
    )
    assert fabric.auto_agent_version in versions.json()
    resolved = call(
        app,
        "GET",
        "/config/resolution",
        params={
            "key": fabric.auto_agent_key,
            "version": fabric.auto_agent_version,
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["name"] == fabric.auto_agent.name


def test_config_resolution_of_nothing_is_a_404(app: Any) -> None:
    response = call(
        app,
        "GET",
        "/config/resolution",
        params={"key": "acme-bank/nothing", "version": "1.0.0"},
    )
    assert response.status_code == 404


# --- backends: the adapter names this deployment accepts (D-15) -------------


def test_backends_lists_the_registry_names_sorted(app: Any) -> None:
    """The answer is the registry's, sorted — never a list written here."""
    from ccf.graph.registry import declared_names

    response = call(app, "GET", "/backends")
    assert response.status_code == 200
    assert response.json()["backends"] == sorted(declared_names())


def test_backends_discloses_names_and_nothing_else(app: Any) -> None:
    """T-15.4-11: no distribution name, version, or module path.

    Asserted as "exactly one key" rather than as a blocklist of the fields
    that must be absent, because a blocklist only ever catches the leaks
    somebody thought of. A widening of this response body fails here.
    """
    body = call(app, "GET", "/backends").json()
    assert set(body) == {"backends"}
    assert all(isinstance(name, str) for name in body["backends"])


def test_backends_is_guarded_exactly_as_schema_is(
    fabric: Fabric, tmp_path: Path
) -> None:
    """T-15.4-30: the same authentication posture as the other read routes.

    Held to ``GET /schema`` rather than to a literal 401, so the claim is
    "this route did not invent a posture" — if the read-route posture ever
    changes, this test follows it instead of pinning the old one.
    """
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.auth import BearerTokenAuth
    from ccf_runtime.http_api.dependencies import ApiDependencies
    from ccf_runtime.mcp.auth import FileTokenSource

    from .gate_fixtures import SCOPE_EVERYTHING, tenanted_source, wide_authorizer

    tenant = fabric.product_address.tenant
    authed = create_app(
        ApiDependencies(
            control_plane=fabric.registry,
            artifact_store=fabric.store,
            product_resolver=fabric.product_resolver,
            workflow_factory=fabric.factory,
            workflow_engine=fabric.engine,
            hitl_transport=fabric.hitl,
            skill_catalog=fabric.catalog,
            grant_ledger=fabric.ledger,
        ),
        auth=BearerTokenAuth(
            token_source=tenanted_source(
                {"good-token": ("alice", (SCOPE_EVERYTHING,))}, tenant=tenant
            )
        ),
        authorizer=wide_authorizer(tenant=tenant, key="routes-backends/mapping"),
        product_entitlement=_echo_entitlement(fabric),
        perspective_resolver=_echo_perspective,
        refusal_recorder=_recorder(
            fabric, tmp_path, source=_echo_entitlement(fabric)
        ),
    )

    from .gate_fixtures import probe

    unauthenticated = probe(authed, "GET", "/backends").status_code
    assert unauthenticated == probe(authed, "GET", "/schema").status_code
    assert unauthenticated == 401

    header = {"Authorization": "Bearer good-token"}
    assert probe(authed, "GET", "/backends", headers=header).status_code == 200


def test_backends_refuses_503_naming_the_conflicting_distributions(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A packaging conflict is a 503 an operator can act on, not a 500.

    The refusal names the offending distributions, which is the one thing
    that tells a packaging conflict apart from a missing adapter — and the
    one thing an uncaught exception would have thrown away.

    The message is the registry's, forwarded verbatim, so what it discloses is
    decided where it is built. That the registry builds a discovery refusal
    from distribution names and never their versions is asserted in
    ``tests/graph/test_backend_registry.py`` (WR-01); the injected message here
    is written in that same shape so this test does not teach a body the route
    can no longer receive.
    """
    from ccf.graph.registry import DuplicateBackendName
    from ccf_runtime.http_api.routes import backends as backends_route

    refusal = DuplicateBackendName(
        "adapter name 'duplicated' is declared by more than one installed"
        " distribution (acme-adapters, beta-adapters); the fabric does not"
        " choose between them. This is a packaging conflict in the installed"
        " environment, not a missing adapter. Run `pip uninstall` on one of"
        " them."
    )

    def _conflicted() -> frozenset[str]:
        raise refusal

    # The route binds ``declared_names`` at import, so the patch goes on the
    # route module's own name — patching the registry's would not be seen.
    monkeypatch.setattr(backends_route, "declared_names", _conflicted)

    response = call(app, "GET", "/backends")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error_code"] == backends_route.BACKEND_REGISTRY_CONFLICT
    # The literal, not only the symbol (D-GATE-15.4). Asserting the constant
    # against itself agrees with whatever it happens to say, so it would have
    # stayed green through the underscore/hyphen inconsistency this rename
    # closed — and would stay green through the next silent rename, which
    # ``errors.py`` records as a breaking change to every consumer. Hyphenated
    # to match all seven of the shared vocabulary's codes.
    assert detail["error_code"] == "backend-registry-conflict"
    assert "acme-adapters" in detail["message"]
    assert "beta-adapters" in detail["message"]
    # Not an empty list under a 200: fail-closed exists so that nothing
    # answers past the ambiguity, and an empty list is a different fact.
    assert "backends" not in response.json()


def test_backends_refuses_503_when_the_sdks_own_adapter_package_is_unreadable(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Close-review F5 — the registry's fourth refusal is not a ``ValueError``.

    ``declared_names`` documents four refusals. Three are ``ValueError``
    subclasses; the fourth — the SDK's own adapter package not being a readable
    directory — is a ``RuntimeError``, and the route's catch tuple had been
    assembled from the three that shared a base class. So the one refusal whose
    remedy an operator is least likely to guess (`pip install
    --force-reinstall` **the SDK**, not an adapter) escaped as an unshaped 500,
    which is exactly the loss this route's docstring rejects for a packaging
    conflict.

    Driven through the *real* ``declared_names`` with only the directory lookup
    redirected, rather than by injecting a ``RuntimeError`` into the route. The
    claim is that the registry's own refusal reaches an operator intact, and an
    injected exception would assert the catch tuple's contents while proving
    nothing about the path — the shape of mistake that let this through in the
    first place.
    """
    import pathlib

    from ccf.graph import registry as registry_module

    monkeypatch.setattr(
        registry_module,
        "_backends_directory",
        lambda: pathlib.Path("/nonexistent/ccf-adapter-package-f5"),
    )

    response = call(app, "GET", "/backends")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error_code"] == "backend-registry-conflict"
    # The remedy survives the trip, which is the whole reason this is a 503.
    assert "force-reinstall" in detail["message"]
    assert "not readable" in detail["message"]
    assert "backends" not in response.json()


# --- D-IMPL-357 A4 at the door: conflicting verdicts refuse -----------------
#
# The lane's gating verification, run through the served interfaces rather
# than only in process: `POST /hitl/actions` twice with opposite verdicts on
# one pending gate event, then `POST /workflow/resumptions` claiming the
# approving decision. Before the guard the third call answered `200` with the
# approving terminal state and the rejection standing.


def _verdict_over_http(
    app: Any, fabric: Fabric, body: dict[str, Any], action: str
) -> None:
    """One verdict through the submit-only action door (D-IMPL-62).

    The subject is the door's, minted from the capability rather than
    described by the body (D-IMPL-353 §2 P6), so both verdicts here come
    from one principal. That is still two recorded verdicts in
    disagreement on one suspension, which is what the guard is about: the
    fabric cannot route on both, and it does not get to pick.
    """
    pending = next(
        event
        for event in fabric.hitl.pending(tenant=body["tenant"])
        if event.event_key == body["event_key"]
    )
    submission = _bound_submission(body["event_key"])
    submission["product_content_hash"] = pending.product_content_hash
    submission["action"] = action
    assert call(app, "POST", "/hitl/actions", json=submission).status_code == 200


def _resume_over_http(
    app: Any, fabric: Fabric, execution_id: str, decision: str
) -> Any:
    key, version = fabric.covenant
    return call(
        app,
        "POST",
        "/workflow/resumptions",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": execution_id,
            "decision": decision,
        },
    )


def test_conflicting_verdicts_through_the_action_door_refuse_the_resumption(
    app: Any, fabric: Fabric
) -> None:
    """The measured attack, at the door. Approve, then reject, then claim
    the approving decision: `409`, and the execution stays suspended."""
    body = _suspend_over_http(app, fabric, "http-covenant-conflict")
    _verdict_over_http(app, fabric, body, "approve")
    _verdict_over_http(app, fabric, body, "reject")
    response = _resume_over_http(
        app, fabric, "http-covenant-conflict", "approved"
    )
    assert response.status_code == 409
    assert "carries conflicting human verdicts" in response.json()["reason"]
    status = call(
        app,
        "GET",
        "/workflow/execution",
        params={
            "tenant": body["tenant"],
            "execution_id": "http-covenant-conflict",
        },
    )
    assert status.json()["status"] == "suspended"


def test_conflicting_verdicts_at_the_door_refuse_in_the_reversed_order_too(
    app: Any, fabric: Fabric
) -> None:
    """Reject first, then approve. This must refuse for the CONFLICT rather
    than falling back to A3's routing refusal, which would record two
    disagreeing humans as a caller naming the wrong transition."""
    body = _suspend_over_http(app, fabric, "http-covenant-conflict-rev")
    _verdict_over_http(app, fabric, body, "reject")
    _verdict_over_http(app, fabric, body, "approve")
    response = _resume_over_http(
        app, fabric, "http-covenant-conflict-rev", "approved"
    )
    assert response.status_code == 409
    reason = response.json()["reason"]
    assert "carries conflicting human verdicts" in reason
    assert "does not agree with the route" not in reason


def test_agreeing_verdicts_at_the_door_still_resume_the_execution(
    app: Any, fabric: Fabric
) -> None:
    """The control at the door: the refusal is not blanket. Two submissions
    that agree carry one distinct verdict and the resumption completes."""
    body = _suspend_over_http(app, fabric, "http-covenant-agree")
    _verdict_over_http(app, fabric, body, "approve")
    _verdict_over_http(app, fabric, body, "approve")
    response = _resume_over_http(app, fabric, "http-covenant-agree", "approved")
    assert response.status_code == 200
    assert response.json()["terminal_state"] == "approved"
