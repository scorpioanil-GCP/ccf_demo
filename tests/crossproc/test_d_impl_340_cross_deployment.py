"""`D-IMPL-340` — a composite asks a producer in ANOTHER PROCESS a question.

The producer is `tests/crossproc/servers/mcp_product_producer.py`: the fixture
child product, booted under its **own** tenant (`producer-fixture`, not the
consumer's `tenant-fixture`), served through the SDK's authenticated egress
door with the `request_context_product` tool exposed and a
:class:`~ccf.products.door.ProducerAssertion` stamped on every answer. The
consumer here holds a `ccf.mcp-producer` registration, an `mcp_product` grant,
a :class:`~ccf.products.child_resolver.QuestionBoundChildResolver` and the
admission gate — and nothing of the producer's.

| Proof | Test |
| --- | --- |
| 1 two questions → two governed products | `test_two_questions_to_one_producer_return_two_corresponding_products` |
| 2 no producer assembler in this process | `test_the_consumer_process_runs_no_producer_assembler` |
| 4 producer tenant is governed by the registration | `test_moving_only_the_registration_flips_the_same_bytes_to_a_tenant_refusal` |
| 5 wrong producer refuses | `test_a_door_asserting_another_producer_is_refused` |
| 6 wrong producer tenant refuses independently | `test_a_door_asserting_another_tenant_is_refused_with_the_producer_still_equal` |
| 8 class / version still required | `test_a_lane_the_producer_does_not_serve_is_refused_and_an_unoffered_class_is_an_error` |
| 10 provider-controls recorded | `test_the_row_records_provider_controls_and_names_the_registered_producer` |
| 12 replay: exact producer, exact child, no second call | `test_replay_names_the_producer_relationship_and_calls_no_producer` |
| 13 no argument becomes an address | `test_question_arguments_cannot_move_the_endpoint` |
| — a registered producer that cannot answer | `test_a_registered_producer_that_cannot_answer_is_a_governed_refusal` |
| — an unregistered producer is an error, not a refusal | `test_an_unregistered_producer_is_a_wiring_error_before_any_socket` |
| — a door without an assertion | `test_a_door_that_asserts_nothing_is_refused` |

Every proof is a real acquisition over loopback HTTP with a bearer token; no
network path other than the shared MCP client exists in this process.
"""

from __future__ import annotations

import json
import pathlib
import socket
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import httpx
import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import MCP_PRODUCER, parse_artifact
from ccf.deployment.operators import build_operator_registry
from ccf.mcp.client import SyncMcpBridge
from ccf.products.child_resolver import ChildQuestion, QuestionBoundChildResolver
from ccf.products.composite import CHILD_QUESTION_CLASS, CompositeAdmissionGate
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver
from ccf.replay.engine import replay
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.callables import CallableRegistry
from ccf.skills.dispatch import McpSkillRegistry, McpSkillUnregistered, ProducerDoesNotOffer
from ccf.skills.producers import register_declared_producer

from tests.composition import composition_replay_mint
from tests.crossproc.conftest import spawn_child_server
from tests.crossproc.servers.product_producer_identity import (
    DEV_TOKEN,
    PRODUCER_ID,
    PRODUCER_TENANT,
    PRODUCT_CLASS,
    SERVER_NAME,
)
from tests.products.composite_fixture import boot_composite
from tests.products.test_d_impl_339_child_contract_view import (
    CHILD_VALUE_KEY,
    _ChildReadingFactory,
    _FreshEnvironment,
)
from tests.products.test_resolver_seam import (
    ADMITTED_AT,
    ASKED_AT,
    PERSPECTIVE,
    POLICY_BUNDLE_KEY,
    PRODUCT_CLASS as PARENT_CLASS,
    PRODUCT_VERSION as PARENT_VERSION,
    TENANT,
    THRESHOLD_PARAMETER,
    _Booted,
    _arguments,
)
from tests.products.test_d_impl_340_producer_admission import ledger_for_product_ask

PRODUCER_MODULE = pathlib.Path(__file__).resolve().parent / "servers" / "mcp_product_producer.py"
CALL_TIMEOUT_SECONDS = 30.0
ENDPOINT_VAR = "CCF_TEST_CHILD_PRODUCER_URL"
CREDENTIAL_VAR = "CCF_TEST_CHILD_PRODUCER_TOKEN"


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield bridge


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    deployment = boot_composite(tmp_path)
    yield next(deployment)
    deployment.close()


@contextmanager
def producer(monkeypatch: pytest.MonkeyPatch, **knobs: str) -> Iterator[str]:
    """The producer process, spawned with the given environment knobs; yields its URL."""
    for name, value in knobs.items():
        monkeypatch.setenv(name, value)
    with spawn_child_server(PRODUCER_MODULE) as port:
        yield f"http://127.0.0.1:{port}/mcp"


class _Recording:
    """An `httpx` client factory that records every URL this process requests."""

    def __init__(self, token: str) -> None:
        self.urls: list[str] = []
        self.sessions = 0
        self._token = token

    def __call__(self) -> httpx.AsyncClient:
        self.sessions += 1

        async def note(request: httpx.Request) -> None:
            self.urls.append(str(request.url))

        return httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._token}"},
            event_hooks={"request": [note]},
        )


def producer_document(
    *,
    producer_id: str = PRODUCER_ID,
    producer_tenant: str = PRODUCER_TENANT,
    offered_class: str = PRODUCT_CLASS,
    versions_from: str = "1.0.0",
) -> dict[str, Any]:
    """A `ccf.mcp-producer` document — names only, never an address."""
    return {
        "semver": "1.0.0",
        "server": SERVER_NAME,
        "producer_id": producer_id,
        "producer_tenant": producer_tenant,
        "endpoint_from_env": ENDPOINT_VAR,
        "credential_from_env": CREDENTIAL_VAR,
        "offers": [{"product_class": offered_class, "versions_from": versions_from}],
    }


def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
    """The deployment's mapping: the composite's subject and threshold reach the child."""
    return ChildQuestion(
        subject=request.subject,
        intent="fixture-intent",
        freshness="fixture-freshness",
        parameters={THRESHOLD_PARAMETER: request.parameters[THRESHOLD_PARAMETER]},
    )


def consumer(
    booted: _Booted,
    *,
    url: str,
    bridge: SyncMcpBridge,
    recording: _Recording | None = None,
    document: Mapping[str, Any] | None = None,
    grant: bool = True,
    plan_factory: Any = None,
) -> tuple[GovernedResolver, McpSkillRegistry, _Recording]:
    """The consuming deployment: registration → grant → question-bound resolver → resolver."""
    registry = McpSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    factory = recording or _Recording(DEV_TOKEN)
    register_declared_producer(
        registry,
        artifact=parse_artifact(document or producer_document(), MCP_PRODUCER),
        environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN},
        bridge=bridge,
        credential_factory=lambda _token: factory,
    )
    ledger, agent_hash = ledger_for_product_ask(booted, grant=grant)
    children = QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        # D-IMPL-354: this test is the composition root; it mints for the child
        # questions the resolver files, under the consumer tenant.
        authorized=composition_replay_mint(booted.control_plane, tenant=TENANT, artifact_class=CHILD_QUESTION_CLASS),
        gate=CompositeAdmissionGate(
            tenant_id=TENANT,
            consumer_scope="consumer://d-impl-340",
            registry=booted.control_plane,
        ),
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=booted.store,
        mcp_skills=registry,
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=children)
    if plan_factory is not None:
        arguments.update(plan_factory=plan_factory)
    return GovernedResolver(**arguments), registry, factory


def ask(resolver: GovernedResolver, *, threshold: int = 1000, subject: str = "acct-1") -> Any:
    return resolver(
        tenant=TENANT,
        product_class=PARENT_CLASS,
        version=PARENT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PARENT_CLASS,
            schema_version=PARENT_VERSION,
            subject=subject,
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: threshold},
        ),
    )


def record_of(booted: _Booted, outcome: Any) -> DecisionReplayRecord:
    fresh = FileArtifactStore(root=booted.store.root, write_kinds=booted.store.write_kinds)
    if isinstance(outcome, ServedProduct):
        return DecisionReplayRecord.model_validate_json(
            fresh.get(content_address=outcome.replay_ref.content_address)
        )
    return DecisionReplayRecord.model_validate_json(
        fresh.get(content_address=fresh.resolve_uri(uri=outcome.replay_reference))
    )


def the_row(booted: _Booted, outcome: Any) -> Any:
    rows = record_of(booted, outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def retained_child(booted: _Booted, address: str) -> ContextProductContract:
    fresh = FileArtifactStore(root=booted.store.root, write_kinds=booted.store.write_kinds)
    return ContextProductContract.model_validate_json(fresh.get(content_address=address))


# --- proof 1 -----------------------------------------------------------------


def test_two_questions_to_one_producer_return_two_corresponding_products(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two thresholds, one registered producer, two admitted children that
    each answer their own question — distinct addresses, distinct question
    addresses, and each retained child carries the threshold it was asked."""
    with producer(monkeypatch) as url:
        resolver, _registry, recording = consumer(booted, url=url, bridge=bridge)
        first = ask(resolver, threshold=1000)
        second = ask(resolver, threshold=2000)
    assert isinstance(first, ServedProduct), getattr(first, "detail", first)
    assert isinstance(second, ServedProduct), getattr(second, "detail", second)
    row_1, row_2 = the_row(booted, first), the_row(booted, second)
    assert row_1.outcome_status == "admitted" and row_2.outcome_status == "admitted"
    assert row_1.child_content_address != row_2.child_content_address
    assert row_1.child_question_address != row_2.child_question_address
    child_1 = retained_child(booted, row_1.child_content_address)
    child_2 = retained_child(booted, row_2.child_content_address)
    assert child_1.payload["threshold"] == "1000"
    assert child_2.payload["threshold"] == "2000"
    assert child_1.tenant_id == child_2.tenant_id == PRODUCER_TENANT
    assert content_hash(first.product) != content_hash(second.product)
    assert recording.sessions == 2


def test_two_subjects_are_two_questions_even_when_the_product_does_not_read_the_subject(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The design's proof 1 as written — two requests differing only in
    `subject`. The review found the first cut's question identity bound only
    the wire request, so these two carried ONE identity; now the identity
    covers every axis and the door echoes what it answered, so the two rows
    carry two question addresses and each names its own subject — whether or
    not the fixture product's payload happens to read the subject."""
    with producer(monkeypatch) as url:
        resolver, _registry, _f = consumer(booted, url=url, bridge=bridge)
        first = ask(resolver, subject="acct-1")
        second = ask(resolver, subject="acct-2")
    assert isinstance(first, ServedProduct), getattr(first, "detail", first)
    assert isinstance(second, ServedProduct), getattr(second, "detail", second)
    row_1, row_2 = the_row(booted, first), the_row(booted, second)
    assert row_1.outcome_status == row_2.outcome_status == "admitted"
    assert row_1.child_question_address != row_2.child_question_address


# --- proof 2 -----------------------------------------------------------------


def test_the_consumer_process_runs_no_producer_assembler(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a real acquisition: the producer's module is not imported here, the
    producer's replay record is not in this store, and no producer database
    exists under this deployment's root."""
    with producer(monkeypatch) as url:
        resolver, _registry, _recording = consumer(booted, url=url, bridge=bridge)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    assert not any(
        name.endswith("mcp_product_producer") for name in sys.modules
    ), "the producer's assembler module was imported into the consumer process"
    index = json.loads((booted.store.root / ".artifact-names.json").read_text())
    producer_records = [
        key for key in index if key.startswith(f"{PRODUCER_TENANT}/") and "replay" in key
    ]
    assert producer_records == [], producer_records
    assert not list(booted.root.parent.rglob("producer.sqlite3"))
    row = the_row(booted, served)
    assert row.child_replay_ref is not None
    assert row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")
    with pytest.raises(Exception):  # the producer's record is its own, unresolvable here
        FileArtifactStore(root=booted.store.root, write_kinds=booted.store.write_kinds).resolve_uri(uri=row.child_replay_ref)


# --- proof 4 -----------------------------------------------------------------


def test_moving_only_the_registration_flips_the_same_bytes_to_a_tenant_refusal(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the consumer's registration changes. Expected tenant = the
    producer's → admitted. Expected tenant = another → `producer-tenant-mismatch`.

    Over a real door the tenant the producer is asked for is the
    registration's `producer_tenant` (ruling 6 — never the mapping's), so the
    producer refuses the question it does not govern; its refusal still
    asserts the tenant it DOES govern, and that assertion is held to the
    registration before the refusal could be filed as `ineligible` — the
    review's point that a refusing door's claims are claims too. Either way
    the registration decided, and no bytes governed under the wrong tenant
    were ever admitted.
    """
    with producer(monkeypatch) as url:
        honest, _r, _f = consumer(booted, url=url, bridge=bridge)
        assert isinstance(ask(honest), ServedProduct)
    with producer(monkeypatch) as url:
        moved, _r, _f = consumer(
            booted,
            url=url,
            bridge=bridge,
            document=producer_document(producer_tenant="some-other-tenant"),
        )
        refused = ask(moved)
    assert not isinstance(refused, ServedProduct)
    row = the_row(booted, refused)
    assert row.refusal_ref == "producer-tenant-mismatch", row.refusal_ref
    assert row.outcome_status == "unauthorized"
    assert row.producer_tenant == "some-other-tenant"  # what was asked and expected
    assert row.producer_id == PRODUCER_ID
    assert row.child_content_address is None


# --- proof 5 -----------------------------------------------------------------


def test_a_door_asserting_another_producer_is_refused(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    with producer(monkeypatch, CCF_TEST_PRODUCER_ASSERT_ID="impostor-egress") as url:
        resolver, _r, _f = consumer(booted, url=url, bridge=bridge)
        refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    row = the_row(booted, refused)
    assert row.refusal_ref == "producer-mismatch"
    assert row.producer_id == PRODUCER_ID  # what was EXPECTED, from the registration


# --- proof 6 -----------------------------------------------------------------


def test_a_door_asserting_another_tenant_is_refused_with_the_producer_still_equal(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Producer identity equal, asserted tenant not — the tenant reason, not the
    producer reason: the two are distinct by ruling."""
    with producer(monkeypatch, CCF_TEST_PRODUCER_ASSERT_TENANT="other-tenant") as url:
        resolver, _r, _f = consumer(booted, url=url, bridge=bridge)
        refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    row = the_row(booted, refused)
    assert row.refusal_ref == "producer-tenant-mismatch"
    assert row.producer_id == PRODUCER_ID


def test_a_door_that_asserts_nothing_is_refused(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    with producer(monkeypatch, CCF_TEST_PRODUCER_NO_ASSERTION="1") as url:
        resolver, _r, _f = consumer(booted, url=url, bridge=bridge)
        refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    assert the_row(booted, refused).refusal_ref == "producer-unasserted"


# --- proof 8 -----------------------------------------------------------------


def test_a_lane_the_producer_does_not_serve_is_refused_and_an_unoffered_class_is_an_error(
    tmp_path: pathlib.Path, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Checks 2–3 still run on the producer leg; an offer that does not cover
    the binding's lane is a deployment error before any socket."""
    deployment = boot_composite(
        tmp_path,
        product_class_overrides={
            "requires": [
                {"product_class": PRODUCT_CLASS, "required": True, "compatible_from": "2.0.0"}
            ]
        },
    )
    booted = next(deployment)
    try:
        with producer(monkeypatch) as url:
            resolver, _r, _f = consumer(booted, url=url, bridge=bridge)
            refused = ask(resolver)
            assert not isinstance(refused, ServedProduct)
            assert the_row(booted, refused).refusal_ref == "version-incompatible"
            narrow, _r, _f = consumer(
                booted,
                url=url,
                bridge=bridge,
                document=producer_document(versions_from="3.0.0"),
            )
            with pytest.raises(ProducerDoesNotOffer):
                ask(narrow)
    finally:
        deployment.close()


# --- proof 10 ----------------------------------------------------------------


def test_the_row_records_provider_controls_and_names_the_registered_producer(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    with producer(monkeypatch) as url:
        resolver, _registry, _f = consumer(booted, url=url, bridge=bridge)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    row = the_row(booted, served)
    assert row.eligibility_basis == "provider-controls"
    assert row.producing_fabric == PRODUCER_ID
    assert row.producer_id == PRODUCER_ID
    assert row.producer_tenant == PRODUCER_TENANT
    assert row.producer_server == SERVER_NAME
    assert row.producer_registration_address == content_hash(
        parse_artifact(producer_document(), MCP_PRODUCER)
    )
    assert row.child_question_address is not None
    assert row.child_schema_name == PRODUCT_CLASS


# --- proof 12 ----------------------------------------------------------------


def test_replay_names_the_producer_relationship_and_calls_no_producer(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Serve with the producer alive; replay after the process is gone, in a
    fresh environment, off a fresh store — the same content address, the row
    naming the exact producer and child, and not one more request."""
    recording = _Recording(DEV_TOKEN)
    with producer(monkeypatch) as url:
        resolver, _registry, recording = consumer(
            booted,
            url=url,
            bridge=bridge,
            recording=recording,
            plan_factory=_ChildReadingFactory(),
        )
        served = ask(resolver)
    # The producer process has been terminated by the context exit.
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    assert served.product.payload[CHILD_VALUE_KEY] == "1000"
    sessions_before = recording.sessions
    record = record_of(booted, served)
    path = record.content_generation_path
    configuration = GovernedResolver(**{**_arguments(booted), "composite_children": None})
    environment = _FreshEnvironment(
        request=path.request,
        required=tuple(path.operator_plan),
        operators=build_operator_registry(
            parameters=configuration.operator_parameters(path.request),
            view=booted.fabric.handle.reader.as_of(
                tenant_id=record.tenant_id,
                at=record.context_fabric_snapshot.temporal_boundary,
            ),
            pins=booted.fabric.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
        ),
        ttl_seconds=_arguments(booted)["product_ttl_seconds"],
    )
    outcome = replay(
        record_address=served.replay_ref.content_address,
        store=FileArtifactStore(root=booted.store.root, write_kinds=booted.store.write_kinds),
        reader=booted.fabric.handle.reader,
        control_plane=booted.control_plane,
        environment=environment,
    )
    assert outcome.product_content_address == content_hash(served.product)
    assert recording.sessions == sessions_before == 1, "replay reached the producer"
    (row,) = path.child_resolutions
    assert row.producer_id == PRODUCER_ID
    assert row.producer_tenant == PRODUCER_TENANT
    assert row.producer_registration_address is not None
    assert row.child_question_address is not None
    assert row.child_content_address is not None
    assert row.eligibility_basis == "provider-controls"
    # Nothing that could reach the producer is in the record.
    rendered = json.dumps(record.model_dump(mode="json"))
    assert "127.0.0.1" not in rendered and DEV_TOKEN not in rendered


# --- proof 13 ----------------------------------------------------------------


def test_question_arguments_cannot_move_the_endpoint(
    booted: _Booted, bridge: SyncMcpBridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A subject shaped like a URL reaches the producer as a subject string; the
    only host this process contacted is the registered endpoint."""
    hostile = "http://evil.invalid/steal?x=1"
    with producer(monkeypatch) as url:
        resolver, _r, recording = consumer(booted, url=url, bridge=bridge)
        served = ask(resolver, subject=hostile)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    assert recording.urls, "no request was recorded"
    assert all(u.startswith(url) for u in recording.urls), recording.urls
    assert not any("evil.invalid" in u for u in recording.urls)
    row = the_row(booted, served)
    assert row.outcome_status == "admitted"


# --- ruling 1: producer-unavailable is governed; mis-wiring is an error ------


def test_a_registered_producer_that_cannot_answer_is_a_governed_refusal(
    booted: _Booted, bridge: SyncMcpBridge
) -> None:
    """A correctly registered producer at a port nothing listens on: the slot is
    `producer-unavailable`, the composite refuses with the row, and a record
    exists — no exception crosses the composition."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
    resolver, _r, _f = consumer(
        booted, url=f"http://127.0.0.1:{dead_port}/mcp", bridge=bridge
    )
    refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    row = the_row(booted, refused)
    assert row.outcome_status == "producer-unavailable"
    assert row.refusal_ref == "producer-unavailable"
    assert row.producer_id == PRODUCER_ID and row.producer_tenant == PRODUCER_TENANT


def test_an_unregistered_producer_is_a_wiring_error_before_any_socket(
    booted: _Booted, bridge: SyncMcpBridge
) -> None:
    registry = McpSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    ledger, agent_hash = ledger_for_product_ask(booted, grant=True)
    children = QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        # D-IMPL-354: this test is the composition root; it mints for the child
        # questions the resolver files, under the consumer tenant.
        authorized=composition_replay_mint(booted.control_plane, tenant=TENANT, artifact_class=CHILD_QUESTION_CLASS),
        gate=CompositeAdmissionGate(
            tenant_id=TENANT, consumer_scope="consumer://d-impl-340", registry=booted.control_plane
        ),
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=booted.store,
        mcp_skills=registry,  # registered NOTHING
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=children)
    with pytest.raises(McpSkillUnregistered):
        ask(GovernedResolver(**arguments))
