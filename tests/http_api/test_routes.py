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

import re
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from ccf.contracts.canonical import canonical_bytes, content_hash

from http_api.conftest import Fabric, call

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


def _api_routes(app: Any) -> tuple[APIRoute, ...]:
    return tuple(r for r in app.routes if isinstance(r, APIRoute))


def _noun_prefixes(app: Any) -> frozenset[str]:
    return frozenset(
        route.path.split("/")[1]
        for route in _api_routes(app)
        if route.path.split("/")[1] != "health"
    )


# --- noun-set fidelity and the absent write door ---------------------------


def test_mounted_nouns_equal_the_ruling_text(app: Any) -> None:
    """Set-equality against the ruling, including product and config."""
    ruled = _ruled_nouns()
    assert {"product", "config"} <= ruled  # the under-emphasized pair
    assert _noun_prefixes(app) == ruled


def test_no_ingest_or_write_to_graph_path_exists(app: Any) -> None:
    """Walking app.routes finds no L1/write door anywhere (T-07-23)."""
    for route in _api_routes(app):
        segments = {s for s in route.path.lower().split("/") if s}
        assert not (segments & FORBIDDEN_PREFIXES), route.path


def test_the_product_noun_is_read_only(app: Any) -> None:
    """The product surface serves; it never accepts (single-writer)."""
    for route in _api_routes(app):
        if route.path.split("/")[1] == "product":
            assert route.methods is not None
            assert route.methods <= {"GET", "HEAD"}, route.path


def test_health_answers(app: Any) -> None:
    assert call(app, "GET", "/health").status_code == 200


# --- product: retrieval with the existing gate-admitted contract -----------


def test_product_retrieval_serves_canonical_bytes(
    app: Any, fabric: Fabric
) -> None:
    address = fabric.product_address
    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/"
        f"{address.version}",
    )
    assert response.status_code == 200
    expected = canonical_bytes(
        fabric.product_resolver(
            tenant=address.tenant,
            product_class=address.product_class,
            version=address.version,
        ).product
    )
    assert response.content == expected


def test_product_absence_is_a_404(app: Any, fabric: Fabric) -> None:
    address = fabric.product_address
    response = call(
        app,
        "GET",
        f"/product/{address.tenant}/{address.product_class}/9.9.9",
    )
    assert response.status_code == 404


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
            "actor": fabric.actor,
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
            "actor": fabric.actor,
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


def test_workflow_resume_with_an_undeclared_decision_is_refused(
    app: Any, fabric: Fabric
) -> None:
    key, version = fabric.covenant
    call(
        app,
        "POST",
        "/workflow/invocations",
        json={
            "definition_key": key,
            "definition_version": version,
            "execution_id": "http-covenant-resume",
        },
    )
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
        params={"tenant": "acme-bank", "execution_id": "never-started"},
    )
    assert response.status_code == 404


# --- hitl: typed queue views and the authority path ------------------------


def test_hitl_action_submission_travels_the_typed_queue(
    app: Any, fabric: Fabric
) -> None:
    product_hash = "0" * 64
    submission = {
        "event_key": "acme-bank/http-covenant-1/gate",
        "tenant": "acme-bank",
        "action": "approve",
        "principal": {
            "approver": {"subject_id": "risk-officer-7"},
            "authentication": {
                "method": "sso",
                "assurance_level": "aal2",
                "session_ref": "session-1",
            },
            "action_time": "2026-07-30T12:00:00+00:00",
            "product_content_hash": product_hash,
        },
        "annotation": None,
    }
    response = call(app, "POST", "/hitl/actions", json=submission)
    assert response.status_code == 200
    recorded = fabric.hitl.submissions(tenant="acme-bank")
    assert submission["event_key"] in {s.event_key for s in recorded}


def test_hitl_action_with_an_extra_field_is_refused(app: Any) -> None:
    submission = {
        "event_key": "acme-bank/x/gate",
        "tenant": "acme-bank",
        "action": "approve",
        "principal": {
            "approver": {"subject_id": "risk-officer-7"},
            "authentication": {
                "method": "sso",
                "assurance_level": "aal2",
                "session_ref": "session-1",
            },
            "action_time": "2026-07-30T12:00:00+00:00",
            "product_content_hash": "0" * 64,
        },
        "not_a_field": True,
    }
    assert call(app, "POST", "/hitl/actions", json=submission).status_code == 422


# --- replay: decisions and exact-version resolution ------------------------


def test_replay_decision_returns_the_typed_record(
    app: Any, fabric: Fabric
) -> None:
    response = call(
        app,
        "GET",
        "/replay/decisions",
        params={"content_address": fabric.replay_ref.content_address},
    )
    assert response.status_code == 200
    assert response.json()["product"]["tenant_id"] == "acme-bank"


def test_replay_resolution_follows_the_versioned_uri(
    app: Any, fabric: Fabric
) -> None:
    response = call(
        app, "GET", "/replay/resolutions", params={"uri": fabric.replay_ref.uri}
    )
    assert response.status_code == 200
    assert response.json()["product"]["tenant_id"] == "acme-bank"


def test_replay_refuses_a_moving_target(app: Any, fabric: Fabric) -> None:
    """``@latest`` dies on the replay path over HTTP exactly as in-process."""
    pinned = fabric.replay_ref.uri
    moving = pinned.rsplit("@", 1)[0] + "@latest"
    response = call(app, "GET", "/replay/resolutions", params={"uri": moving})
    assert response.status_code == 409


def test_replay_of_nothing_is_a_404(app: Any) -> None:
    response = call(
        app,
        "GET",
        "/replay/decisions",
        params={"content_address": "f" * 64},
    )
    assert response.status_code == 404


# --- artifact: get/put against the injected store --------------------------


def test_artifact_put_then_get_round_trips(app: Any) -> None:
    put = call(
        app,
        "POST",
        "/artifact",
        json={
            "tenant_id": "acme-bank",
            "artifact_class": "ccf.test-blob",
            "name": "blob-1",
            "artifact": {"field": "value"},
        },
    )
    assert put.status_code == 200
    ref = put.json()
    got = call(app, "GET", f"/artifact/{ref['content_address']}")
    assert got.status_code == 200
    assert got.json() == {"field": "value"}


def test_artifact_get_of_nothing_is_a_404(app: Any) -> None:
    assert (
        call(app, "GET", f"/artifact/{'e' * 64}").status_code == 404
    )


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
