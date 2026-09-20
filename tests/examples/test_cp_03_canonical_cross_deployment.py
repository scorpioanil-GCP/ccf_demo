"""`CP14-F-22` §6 — the canonical spread acquired across a deployment boundary.

A composite in THIS process requires `credit-risk.spread`; the canonical
producer (`examples/cp-03-canonical-obligor-financial-spread/server/serve.py`,
booted by `run.py --door`) runs in ANOTHER process, booted under its own tenant and reached only through
the SDK's authenticated egress door with the `request_context_product` tool
exposed. The consumer holds a `ccf.mcp-producer` registration, an
`mcp_product` grant, a `QuestionBoundChildResolver` and the admission gate —
and nothing of the producer's.

The question is the one `CP-SPEC-014` will ask: `subject` = one of its roster
LEIs, `asked_at` = the instant it is held to (`CP14-F-19`), `intent` and
`freshness` the spread class serves, and the spread's own parameters.

**This is not CP-14 Gate 2.** The parent here is the SDK's fixture composite,
not a credit-memo product; what is proved is that a real, governed
`credit-risk.spread` child can be acquired through `D-IMPL-340` and admitted.

**Reads the estate, seeds nothing.** The producer process reads the same live
estate the in-process example reads; this module reads none of it directly.
"""

from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import yaml

from ccf.agents.definitions import AgentDefinition
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import MCP_PRODUCER, declared_artifact_class, parse_artifact
from ccf.mcp.client import SyncMcpBridge
from ccf.products.child_resolver import ChildQuestion, QuestionBoundChildResolver
from ccf.products.composite import CompositeAdmissionGate
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    McpProductBinding,
    SkillArgumentSchema,
    SkillCatalog,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.skills.dispatch import McpSkillRegistry, ProducerDoesNotOffer
from ccf.skills.grants import GrantLedger, SkillGrant
from ccf.skills.producers import register_declared_producer

from tests.products.composite_fixture import boot_composite
from tests.products.test_resolver_seam import (
    PERSPECTIVE,
    PRODUCT_CLASS as PARENT_CLASS,
    PRODUCT_VERSION as PARENT_VERSION,
    TENANT,
    THRESHOLD_PARAMETER,
    _Booted,
    _arguments,
)

pytestmark = [pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-03-canonical-obligor-financial-spread"
RUN = EXAMPLE / "run.py"

#: The producer's OWN declarations, read from its tree rather than restated:
#: the identity its door asserts and the tenant its fabric runs as — both from
#: the ONE document the paved road declares them in (`D-IMPL-343`). A consumer
#: registers what the producer declares; equality is a binding, never an
#: authorization.
CONFIG = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
PRODUCER_ID = str(CONFIG["door"]["producer_id"])
PRODUCER_TENANT = str(CONFIG["tenant_id"])
PRODUCT_CLASS = str(CONFIG["product_class"]["schema_name"])
PRODUCT_VERSION = str(CONFIG["product_class"]["schema_version"])
INTENT = sorted(CONFIG["product_class"]["discovery"]["intents"])[0]
FRESHNESS = "filing-cadence"

#: The consumer's logical name for the producer — what its `McpProductBinding`
#: selects by. The consumer's vocabulary, not the producer's.
SERVER_NAME = "canonical-spread-producer"
SKILL = "spread-ask"
REGIME_KEY = f"{TENANT}/policy-bundle/cp-03-canonical"
ENDPOINT_VAR = "CCF_TEST_CP03C_PRODUCER_URL"
CREDENTIAL_VAR = "CCF_TEST_CP03C_PRODUCER_TOKEN"
DEV_TOKEN = "dev-token-cp-03-canonical-door"
CALL_TIMEOUT_SECONDS = 120.0

#: The instant CP-14 asks at (`CP14-F-19`), and the clock a child admission is
#: judged against — seven minutes on, as the SDK's own fixture pins it.
CP14_INSTANT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
ADMITTED_AT = CP14_INSTANT + timedelta(minutes=7)

#: A `CP-SPEC-014` §C.1 roster obligor whose latest filing lies inside the
#: spread's declared window at the CP-14 instant (BGC Group), and one that does
#: not (Digital Turbine — not on the roster; the specimen's own anchor).
ROSTER_OBLIGOR = "2549001IGRCG4F0RLD36"
STALE_OBLIGOR = "549300D0WZR1VI2QGB24"

ESTATE_VARIABLES = ("CCF_CP_03C_POSTGRES_DSN", "CCF_CP_03C_POSTGRES_SCHEMA")

_LEDGERS: dict[int, tuple[GrantLedger, str]] = {}


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield bridge


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The consumer: the SDK's fixture composite, REQUIRING `credit-risk.spread`."""
    deployment = boot_composite(
        tmp_path,
        product_class_overrides={
            "requires": [{"product_class": PRODUCT_CLASS, "required": True, "compatible_from": "1.0.0"}]
        },
    )
    yield next(deployment)
    deployment.close()


@contextmanager
def producer(estate: None, **environment: str) -> Iterator[str]:
    """The producer process — the example's own door, spawned via `run.py --door`.

    Readiness is a handshake: the child prints `READY {port}` once the server
    is up. The parent learns the bearer credential by SETTING it, through the
    one variable the door names; no side channel.
    """
    env = {**os.environ, "CCF_CP_03C_DOOR_TOKEN": DEV_TOKEN, **environment}
    process = subprocess.Popen(
        [sys.executable, str(RUN), "--door"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"the door did not announce readiness (got {announcement!r}); stderr:\n{stderr[-2000:]}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


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
            timeout=CALL_TIMEOUT_SECONDS,
        )


def producer_document(
    *, producer_id: str = PRODUCER_ID, producer_tenant: str = PRODUCER_TENANT,
    offered_class: str = PRODUCT_CLASS, versions_from: str = PRODUCT_VERSION,
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


def ledger_for_spread(booted: _Booted, *, product_version: str = PRODUCT_VERSION) -> tuple[GrantLedger, str]:
    """A real ledger over the consumer's Control Plane with one `mcp_product` grant."""
    registry = booted.control_plane
    if id(registry) in _LEDGERS:
        return _LEDGERS[id(registry)]
    regime_class = declared_artifact_class("policy-bundle")
    registry.register_typed(
        REGIME_KEY,
        parse_artifact(
            {
                "class_id": "policy-bundle",
                "semver": "1.0.0",
                "declaration": {
                    "regime": "cp-03-canonical-consumer",
                    "skill_governance": {"grant_requires_approval": False, "permitted_scopes": []},
                },
            },
            regime_class,
        ),
        regime_class,
    )
    definition = AgentDefinition(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="cp-03-canonical-consumer",
        tenant=TENANT,
        archetypes=("context_assembly",),
        context_contract={"consumes": [{"product_class": PRODUCT_CLASS, "schema_version": product_version}]},
        perspective={"role": PERSPECTIVE.role, "selection_params": {}},
        policy_regime={"ref": f"ccf-artifact://{REGIME_KEY}@1.0.0"},
        halflife_debt_profile={"ref": f"ccf-artifact://{TENANT}/debt-profile/x@1.0.0"},
        instruction_bindings=(),
    )
    catalog = SkillCatalog(registry)
    catalog.register(
        SkillCatalogEntry(
            schema_version="1.0.0",
            artifact_version="1.0.0",
            name=SKILL,
            tenant=TENANT,
            skill_type="mcp_product",
            description="asks the registered canonical spread producer a question",
            argument_schema=SkillArgumentSchema(properties={}, required=()),
            binding=McpProductBinding(server=SERVER_NAME, product_class=PRODUCT_CLASS, product_version=product_version),
            requirements=SkillRequirements(required_scopes=frozenset(), required_context_products=frozenset()),
            produces=PRODUCT_CLASS,
        )
    )
    ledger = GrantLedger(control_plane=registry, catalog=catalog, sink=None, clock=lambda: ADMITTED_AT)
    outcome = ledger.request(
        SkillGrant(
            schema_version="1.0.0",
            artifact_version="1.0.0",
            name=f"grant-{SKILL}",
            tenant=TENANT,
            agent_definition_hash=content_hash(definition),
            skill_name=SKILL,
            skill_version="1.0.0",
        ),
        definition=definition,
        actor="cp-03-canonical-consumer",
    )
    assert isinstance(outcome, str), outcome
    _LEDGERS[id(registry)] = (ledger, content_hash(definition))
    return _LEDGERS[id(registry)]


def questions_at(tolerance: str) -> Callable[[ChildRequirement, ProductRequest], ChildQuestion]:
    """The consumer's mapping — the CP-14-shaped question for the spread slot.

    The composite's subject (an obligor LEI) reaches the child as ITS subject;
    the intent and freshness are the ones the spread class serves; the
    parameters are the spread's own, with numbers as decimal TEXT. `asked_at`
    is not here: it is the composite's instant, supplied by dispatch.
    """

    def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        return ChildQuestion(
            subject=request.subject,
            intent=INTENT,
            freshness=FRESHNESS,
            parameters={"debt_tolerance": tolerance},
        )

    return questions


def consumer(
    booted: _Booted, *, url: str, bridge: SyncMcpBridge, recording: _Recording | None = None,
    document: Mapping[str, Any] | None = None, tolerance: str = "1.0",
) -> tuple[GovernedResolver, _Recording]:
    """The consuming deployment: registration → grant → question-bound resolver → resolver."""
    registry = McpSkillRegistry(audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT)
    factory = recording or _Recording(DEV_TOKEN)
    register_declared_producer(
        registry,
        artifact=parse_artifact(document or producer_document(), MCP_PRODUCER),
        environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN},
        bridge=bridge,
        credential_factory=lambda _token: factory,
    )
    ledger, agent_hash = ledger_for_spread(booted)
    children = QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=CompositeAdmissionGate(tenant_id=TENANT, consumer_scope="consumer://cp-03-canonical", registry=booted.control_plane),
        child_questions=questions_at(tolerance),
        callable_registry=CallableRegistry(),
        artifact_store=booted.store,
        mcp_skills=registry,
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=children, admission_clock=lambda: ADMITTED_AT)
    return GovernedResolver(**arguments), factory


def ask(resolver: GovernedResolver, *, subject: str = ROSTER_OBLIGOR) -> Any:
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
            asked_at=CP14_INSTANT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )


def record_of(booted: _Booted, outcome: Any) -> DecisionReplayRecord:
    fresh = FileArtifactStore(root=booted.store.root)
    if isinstance(outcome, ServedProduct):
        return DecisionReplayRecord.model_validate_json(fresh.get(content_address=outcome.replay_ref.content_address))
    return DecisionReplayRecord.model_validate_json(
        fresh.get(content_address=fresh.resolve_uri(uri=outcome.replay_reference))
    )


def the_row(booted: _Booted, outcome: Any) -> Any:
    rows = record_of(booted, outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def retained_child(booted: _Booted, address: str) -> ContextProductContract:
    return ContextProductContract.model_validate_json(
        FileArtifactStore(root=booted.store.root).get(content_address=address)
    )


# --- the proof ------------------------------------------------------------------


def test_the_cp14_question_is_answered_by_the_producer_in_another_process_and_admitted(
    booted: _Booted, bridge: SyncMcpBridge, estate: None
) -> None:
    """A CP-14-shaped question → `mcp_product` → the canonical producer, in
    another process → a governed `credit-risk.spread` child → admission. The
    row records `provider-controls`, the registered producer, the producer's
    tenant, the child's class, and the question's address; the retained child
    is the spread for the subject asked, at the instant asked, on the lane the
    requirement admits.

    Declared product gate `OFC-G16` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        resolver, recording = consumer(booted, url=url, bridge=bridge)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    row = the_row(booted, served)
    assert row.outcome_status == "admitted"
    assert row.eligibility_basis == "provider-controls"
    assert row.producing_fabric == PRODUCER_ID
    assert row.producer_id == PRODUCER_ID
    assert row.producer_tenant == PRODUCER_TENANT
    assert row.producer_server == SERVER_NAME
    assert row.producer_registration_address == content_hash(parse_artifact(producer_document(), MCP_PRODUCER))
    assert row.child_schema_name == PRODUCT_CLASS
    assert row.child_question_address is not None
    child = retained_child(booted, row.child_content_address)
    assert child.schema_name == PRODUCT_CLASS
    assert child.schema_version == PRODUCT_VERSION
    assert child.tenant_id == PRODUCER_TENANT
    assert child.temporal_boundary == CP14_INSTANT
    assert child.payload["obligor"]["lei"] == ROSTER_OBLIGOR
    assert child.ttl_anchor == "from_entity_freshness"
    assert recording.sessions == 1
    assert all(u.startswith(url) for u in recording.urls), recording.urls


def test_the_consumer_process_runs_no_producer_assembler(
    booted: _Booted, bridge: SyncMcpBridge, estate: None
) -> None:
    """After a real acquisition: the producer's modules are not imported here,
    no spread fabric exists under this deployment's root, the producer's replay
    record is not in this store, and the child's replay reference is the
    producer's own — unresolvable here.

    Declared product gate `OFC-G17` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        resolver, _ = consumer(booted, url=url, bridge=bridge)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    for module in sys.modules.values():
        origin = getattr(module, "__file__", None) or ""
        assert not origin.startswith(str(EXAMPLE)), f"the producer's {origin} was imported into the consumer"
    assert not list(booted.root.parent.rglob("cp_03_canonical*.sqlite3"))
    index = json.loads((booted.store.root / ".artifact-names.json").read_text())
    assert [key for key in index if key.startswith(f"{PRODUCER_TENANT}/")] == []
    row = the_row(booted, served)
    assert row.child_replay_ref is not None
    assert row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")
    with pytest.raises(Exception):
        FileArtifactStore(root=booted.store.root).resolve_uri(uri=row.child_replay_ref)


def test_the_expected_producer_identity_and_tenant_come_from_the_registration(
    booted: _Booted, bridge: SyncMcpBridge, estate: None
) -> None:
    """The same door, the same bytes: only the consumer's registration changes.
    Expecting another producer id refuses `producer-mismatch`; expecting another
    tenant refuses `producer-tenant-mismatch`. Neither is authorized by the
    door's own claim about itself.

    Declared product gate `OFC-G18` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        impostor, _ = consumer(booted, url=url, bridge=bridge, document=producer_document(producer_id="somebody-else-egress"))
        refused_id = ask(impostor)
        moved, _ = consumer(booted, url=url, bridge=bridge, document=producer_document(producer_tenant="some-other-tenant"))
        refused_tenant = ask(moved)
    assert not isinstance(refused_id, ServedProduct)
    row = the_row(booted, refused_id)
    assert row.refusal_ref == "producer-mismatch"
    assert row.producer_id == "somebody-else-egress"  # what was EXPECTED
    assert not isinstance(refused_tenant, ServedProduct)
    row = the_row(booted, refused_tenant)
    assert row.refusal_ref == "producer-tenant-mismatch"
    assert row.producer_tenant == "some-other-tenant"
    assert row.child_content_address is None


def test_a_lane_the_requirement_does_not_admit_is_refused_and_an_unoffered_class_is_an_error(
    tmp_path: pathlib.Path, bridge: SyncMcpBridge, estate: None
) -> None:
    """Class and version are still established on the producer leg: a parent
    requiring the next major refuses the served `1.1.0` child
    `version-incompatible`; a registration offering another class never opens
    a socket — a wiring error, not a governed refusal.

    Declared product gate `OFC-G19` (`CP-SPEC-003C` §G.1).
    """
    deployment = boot_composite(
        tmp_path,
        product_class_overrides={
            "requires": [{"product_class": PRODUCT_CLASS, "required": True, "compatible_from": "2.0.0"}]
        },
    )
    booted = next(deployment)
    try:
        with producer(estate) as url:
            resolver, _ = consumer(booted, url=url, bridge=bridge)
            refused = ask(resolver)
            assert not isinstance(refused, ServedProduct)
            assert the_row(booted, refused).refusal_ref == "version-incompatible"
            narrow, _ = consumer(booted, url=url, bridge=bridge, document=producer_document(versions_from="3.0.0"))
            with pytest.raises(ProducerDoesNotOffer):
                ask(narrow)
    finally:
        deployment.close()


def test_no_question_argument_becomes_an_address_and_the_childs_own_gate_governs(
    booted: _Booted, bridge: SyncMcpBridge, estate: None
) -> None:
    """A subject shaped like a URL reaches the producer as a subject string and
    the only host this process contacted is the registered endpoint. The
    producer resolves no such obligor and refuses on its OWN declared gate; the
    consumer records the child refusal and refuses the composite on its
    required slot — no fake spread child.

    Declared product gate `OFC-G20` (`CP-SPEC-003C` §G.1).
    """
    hostile = "http://evil.invalid/steal?x=1"
    with producer(estate) as url:
        resolver, recording = consumer(booted, url=url, bridge=bridge)
        refused = ask(resolver, subject=hostile)
    assert recording.urls and all(u.startswith(url) for u in recording.urls), recording.urls
    assert not any("evil.invalid" in u for u in recording.urls)
    assert not isinstance(refused, ServedProduct)
    assert refused.reason == "child_admission"
    row = the_row(booted, refused)
    assert row.outcome_status == "ineligible" and row.refusal_ref == "ineligible"
    assert row.child_content_address is None
    assert row.child_question_address is not None
    assert row.producer_id == PRODUCER_ID


def test_at_cp14s_own_tolerance_the_spread_slot_is_withheld_and_the_composite_refuses(
    booted: _Booted, bridge: SyncMcpBridge, estate: None
) -> None:
    """Estate truth, preserved across the boundary. At `CP-SPEC-014`'s own
    tolerance the producer withholds the spread with the debt block; the
    consumer records that child outcome and refuses the composite on its
    required slot. The number was not moved to fit the ceiling.

    Declared product gate `OFC-G21` (`CP-SPEC-003C` §G.1).
    """
    with producer(estate) as url:
        resolver, _ = consumer(booted, url=url, bridge=bridge, tolerance="0.25")
        refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    assert refused.reason == "child_admission"
    row = the_row(booted, refused)
    # The producer's refusal reaches the consumer as an `ineligible` row whose
    # producer claims were held first; the producer's own reason and record
    # stay on the producer's side (`CP03C-F-05`).
    assert row.outcome_status == "ineligible" and row.refusal_ref == "ineligible"
    assert row.child_content_address is None
    assert row.producer_id == PRODUCER_ID and row.producer_tenant == PRODUCER_TENANT


def test_a_severed_producer_is_a_governed_refusal_not_a_fake_child(
    booted: _Booted, bridge: SyncMcpBridge, estate: None
) -> None:
    """A correctly registered producer at a port nothing listens on: the slot is
    `producer-unavailable`, the composite refuses with the row, a record
    exists, and no exception crosses the composition.

    Declared product gate `OFC-G22` (`CP-SPEC-003C` §G.1).
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
    resolver, _ = consumer(booted, url=f"http://127.0.0.1:{dead_port}/mcp", bridge=bridge)
    refused = ask(resolver)
    assert not isinstance(refused, ServedProduct)
    row = the_row(booted, refused)
    assert row.outcome_status == "producer-unavailable"
    assert row.refusal_ref == "producer-unavailable"
    assert row.child_content_address is None


def test_the_door_and_the_in_process_run_serve_one_content_address(
    booted: _Booted, bridge: SyncMcpBridge, estate: None
) -> None:
    """The product is the constant; the transport is the variable. The child
    retained through the door hashes to the address the same question hashes
    to when the example is run in this process — same bytes, two doors.

    Declared product gate `OFC-G23` (`CP-SPEC-003C` §G.1).
    """
    import tempfile  # noqa: PLC0415

    with producer(estate) as url:
        resolver, _ = consumer(booted, url=url, bridge=bridge)
        served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    through_the_door = the_row(booted, served).child_content_address

    saved = {name: sys.modules.pop(name, None) for name in ("acquisition", "assembler", "deployment", "produce", "projection")}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as scratch, produce.product(pathlib.Path(scratch)) as opened:
            asked = opened.question(
                subject=ROSTER_OBLIGOR, asked_at=CP14_INSTANT, intent=INTENT, freshness=FRESHNESS,
                parameters={deployment.DEBT_TOLERANCE: "1.0"},
            )
            local = opened.answer(asked)
        assert isinstance(local, ServedProduct), getattr(local, "detail", local)
        assert content_hash(local.product) == through_the_door
    finally:
        sys.path.remove(str(EXAMPLE))
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module
