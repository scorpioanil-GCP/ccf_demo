"""The paved road's CONSUMER half, proven through its public surface (`D-IMPL-343`).

CLAUDE.md §6.2, §7.1, §9, §11; the ruling of record is `D-IMPL-343`'s
IMPLEMENTATION GO (R-2, R-6, R-7, R-13) and its consumer instruction. Every
test here drives :func:`ccf.products.product.open_product` from the outside
over a consumer deployment written as four declarations — ``requires`` on the
class, ``producers:``, ``skills:``, ``agent:`` — plus ONE keyword,
``questions=``, against a REAL producer in ANOTHER process: the paved fixture
product served through the standard door
(``tests/crossproc/servers/paved_fixture_door.py``). No test constructs a
registry, a catalog, a ledger, a grant, a resolver, an MCP client or an
admission gate; the ones that need the low road build it beside the paved
surface and hand it in through ``children=``, which is the hatch under test.

What is held, exactly:

1. A composite is served with the child ADMITTED under `provider-controls`,
   the row naming the registered producer, its tenant, its registration and
   the question's identity; the retained child is the producer's product for
   the subject asked, at the instant asked, on the lane the requirement admits.
2. The adopter constructed none of the SDK's consumer machinery, and each
   piece exists exactly once: one registry the declared producer is on, one
   agent derived from the section, one grant in force for it.
3. Opening twice over one Control Plane serves twice (idempotent grants).
4. `R-13`: a floor the served lane satisfies serves; a floor it does not is
   refused at the producer's door with BOTH lanes retained, and the composite
   refuses with that reason — never `no-producing-skill`, never silently.
5. Thirteen negative controls, each through the public surface, each the
   expected governed refusal or an explicitly classified deployment error.
6. The `children=` hatch still works over the registrations the SDK declared.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.child_resolver import ChildQuestion, QuestionBoundChildResolver
from ccf.products.composite import CompositeAdmissionGate
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.door import WireRequest
from ccf.products.product import OpenedProduct, open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalog
from ccf.skills.dispatch import question_identity
from ccf.skills.grants import GrantLedger
from ccf.skills.producers import ProducerEnvironmentMissing
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import (
    ADMITTED_AT,
    AGENT_NAME,
    ASKED_AT,
    CHILD_CLASS,
    CHILD_VERSION,
    CONSUMER_TENANT,
    CREDENTIAL_VAR,
    ENDPOINT_VAR,
    PARENT_CLASS,
    PARENT_DSN_VAR,
    PRODUCER_ID,
    PRODUCER_TENANT,
    SERVER_NAME,
    SKILL,
    THRESHOLD_PARAMETER,
)

pytestmark = [pytest.mark.crossproc]

DOOR = pathlib.Path(__file__).resolve().parents[1] / "crossproc" / "servers" / "paved_fixture_door.py"
DEV_TOKEN = "dev-token-paved-child-door"


# --- the producer, in another process ------------------------------------------------


@contextmanager
def _producer(**environment: str) -> Iterator[str]:
    """The producer process: the fixture door, spawned; readiness is a handshake."""
    env = {**os.environ, CREDENTIAL_VAR: DEV_TOKEN, **environment}
    process = subprocess.Popen(
        [sys.executable, str(DOOR)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=10)
            raise AssertionError(f"the door did not announce readiness ({announcement!r}); stderr:\n{stderr[-2000:]}")
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.fixture(scope="module")
def producer_url() -> Iterator[str]:
    with _producer() as url:
        yield url


# --- the consumer, on the paved road ------------------------------------------------


def _tree(tmp_path: pathlib.Path, *, config: Mapping[str, Any] | None = None, environment: str | None = None) -> pathlib.Path:
    return fixture.write_tree(
        tmp_path / "consumer",
        config=config if config is not None else fixture.consumer_config(),
        environment=environment if environment is not None else fixture.consumer_environment_text(),
    )


def _environ(url: str, **overrides: str) -> dict[str, str]:
    return {PARENT_DSN_VAR: "postgresql://fixture", ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN, **overrides}


def _open(root: pathlib.Path, scratch: pathlib.Path, url: str, **overrides: Any) -> OpenedProduct:
    arguments: dict[str, Any] = {
        "config_root": root,
        "scratch": scratch,
        "acquire": fixture.Acquire(),
        "project": fixture.plan_factory,
        "assess": fixture.assess,
        "questions": fixture.questions,
        "environ": _environ(url),
        "clock": lambda: ADMITTED_AT,
    }
    arguments.update(overrides)
    return open_product(**arguments)


def _question(opened: OpenedProduct, *, subject: str = "acct-1") -> ProductRequest:
    return opened.question(
        subject=subject, asked_at=ASKED_AT, intent="fixture-intent", freshness="fixture-freshness",
        parameters={THRESHOLD_PARAMETER: 1000},
    )


def _the_row(opened: OpenedProduct, outcome: Any) -> Any:
    rows = opened.record_of(outcome).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def _retained_child(opened: OpenedProduct, address: str) -> ContextProductContract:
    fresh = FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)
    return ContextProductContract.model_validate_json(fresh.get(content_address=address))


# --- 1. served, admitted, from four declarations and one keyword ----------------------


def test_a_composite_is_served_with_its_child_admitted_from_declarations_alone(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = _the_row(opened, served)
        child = _retained_child(opened, row.child_content_address)
    assert row.outcome_status == "admitted"
    assert row.eligibility_basis == "provider-controls"
    assert (row.producer_id, row.producer_tenant, row.producer_server) == (PRODUCER_ID, PRODUCER_TENANT, SERVER_NAME)
    assert row.producing_skill_name == SKILL
    assert row.producer_registration_address is not None and row.child_question_address is not None
    assert row.child_schema_name == CHILD_CLASS and row.child_schema_version == CHILD_VERSION
    assert row.child_replay_ref is not None and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")
    assert (child.schema_name, child.schema_version, child.tenant_id) == (CHILD_CLASS, CHILD_VERSION, PRODUCER_TENANT)
    assert child.temporal_boundary == ASKED_AT
    assert served.product.schema_name == PARENT_CLASS


def test_the_adopter_constructed_none_of_the_consumer_machinery_and_each_exists_once(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        assert opened.mcp_skills is not None
        assert opened.agent is not None and opened.agent.name == AGENT_NAME and opened.agent.tenant == CONSUMER_TENANT
        # The derived agent reads its axes from the deployment's own sections.
        assert [(c.product_class, c.schema_version) for c in opened.agent.context_contract.consumes] == [(CHILD_CLASS, CHILD_VERSION)]
        assert opened.agent.perspective.role == opened.default_perspective.role
        assert opened.agent.policy_regime.ref == f"ccf-artifact://{opened.keys.policy_bundle}@1.0.0"
        assert opened.agent.halflife_debt_profile.ref == f"ccf-artifact://{opened.keys.debt_profile}@1.0.0"
        # ONE grant in force for the agent, resolvable by any ledger over the plane.
        ledger = GrantLedger(control_plane=opened.control_plane, catalog=SkillCatalog(opened.control_plane), sink=None, clock=lambda: ADMITTED_AT)  # type: ignore[arg-type]
        bound = ledger.bound_view(content_hash(opened.agent))
        assert list(bound) == [SKILL]
        entry = bound[SKILL]
        assert (entry.skill_type, entry.produces, entry.binding.server) == ("mcp_product", CHILD_CLASS, SERVER_NAME)  # type: ignore[union-attr]
        assert entry.binding.product_version == CHILD_VERSION  # type: ignore[union-attr]
        assert dict(entry.argument_schema.properties) == {} and entry.argument_schema.required == ()
        # The skills entry registered under the key its grant resolves it through.
        assert opened.keys.skills == (f"{CONSUMER_TENANT}/ccf.skill-catalog-entry/{SKILL}",)


def test_opening_twice_over_one_control_plane_serves_twice(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path)
    registry = ControlPlaneRegistry()
    with _open(root, tmp_path / "s1", producer_url, control_plane=registry) as first:
        assert isinstance(first.answer(_question(first)), ServedProduct)
    with _open(root, tmp_path / "s2", producer_url, control_plane=registry) as second:
        served = second.answer(_question(second))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        assert _the_row(second, served).outcome_status == "admitted"


def test_the_bridge_is_released_on_close_and_open_boots_nothing(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path)
    opened = _open(root, tmp_path / "scratch", producer_url)
    assert sorted((tmp_path / "scratch").glob("paved_consumer_*.sqlite3")) == []
    assert opened._bridge is not None and opened._bridge._thread.is_alive()
    opened.close()
    assert not opened._bridge._thread.is_alive()
    opened.close()  # idempotent


# --- 2. R-13: the floor, everywhere ---------------------------------------------------------


def test_a_floor_below_the_served_lane_serves_and_the_served_lane_is_what_admission_holds(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    """The producer serves `1.0.0`; the consumer declares floor `1.0.0-rc.1` at both
    boundaries. A floor is satisfied by a lane in the same major at or above it."""
    config = fixture.consumer_config(
        compatible_from="1.0.0-rc.1", producers={"child": fixture.producer_section(versions_from="1.0.0-rc.1")}
    )
    root = _tree(tmp_path, config=config)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = _the_row(opened, served)
    assert row.outcome_status == "admitted" and row.child_schema_version == CHILD_VERSION


def test_a_floor_above_the_served_lane_is_refused_at_the_door_with_both_lanes_retained(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    """The producer serves `1.0.0`; the consumer's floor is `1.5.0` at both boundaries
    (consistent with each other, so it opens). The door refuses `class-mismatch`
    naming the served lane and the floor; the composite refuses with the child's
    reason retained — not `no-producing-skill`, not a silent downgrade."""
    config = fixture.consumer_config(compatible_from="1.5.0", producers={"child": fixture.producer_section(versions_from="1.5.0")})
    root = _tree(tmp_path, config=config)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
        record = opened.record_of(refused)
    assert row.refusal_ref == "ineligible" and row.outcome_status != "admitted"
    assert row.producer_id == PRODUCER_ID and row.child_question_address is not None
    # The reason travels: the consumer's RECORD retains the producer's refusal
    # by kind, reason and key as the producer's door disclosed it; the
    # producer's own record (named by the row) holds the two lanes. The
    # disclosed envelope stays minimal — the disclosure boundary is unchanged.
    retained = json.loads(record.content_generation_path.assembly_refusal)["detail"]
    assert "class-mismatch" in retained and "schema_version" in retained, retained
    assert "no-producing-skill" not in retained
    assert "1.5.0" not in refused.detail, "the disclosed envelope stays minimal"
    # NOT retained on a refused child's row: the producer's replay reference
    # (`child_replay_ref` is None here). That is `D-IMPL-342` — refused-child
    # evidence beyond R-13's retained reason — and is excluded by ruling.
    assert row.child_replay_ref is None


def test_the_door_refuses_a_floor_its_lane_does_not_satisfy_with_both_lanes_in_its_record(
    tmp_path: pathlib.Path,
) -> None:
    """The producer side of `R-13`, in-process: the standard door's own refusal
    names the served lane and the floor asked, and is recorded through the ONE
    recorder; a floor the lane satisfies is answered at the served lane."""
    from ccf.projection.plan import Perspective  # noqa: PLC0415

    root = fixture.write_tree(tmp_path / "producer", config=fixture.producer_config(), environment=fixture.producer_environment_text())
    with open_product(
        config_root=root, scratch=tmp_path / "scratch", acquire=fixture.Acquire(), project=fixture.plan_factory,
        assess=fixture.assess, environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"}, clock=lambda: ADMITTED_AT,
    ) as producer:
        perspective = Perspective(principal_id=producer.default_perspective.principal_id, role=producer.default_perspective.role)

        def addressed(floor: str) -> Any:
            request = ProductRequest(
                schema_name=CHILD_CLASS, schema_version=floor, subject="acct-1", intent="fixture-intent",
                freshness="fixture-freshness", asked_at=ASKED_AT, parameters={THRESHOLD_PARAMETER: 1000},
            )
            return producer.resolve(tenant=PRODUCER_TENANT, product_class=CHILD_CLASS, version=floor, perspective=perspective, request=request)

        refused = addressed("1.5.0")
        assert isinstance(refused, RefusalEnvelope) and refused.reason == "class-mismatch"
        recorded = json.loads(producer.record_of(refused).content_generation_path.assembly_refusal)["detail"]
        assert "1.0.0" in recorded and "1.5.0" in recorded and "R-13" in recorded, recorded
        assert isinstance(addressed("2.0.0"), RefusalEnvelope), "another major is outside the lane"
        served = addressed("1.0.0-rc.1")
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        assert served.product.schema_version == CHILD_VERSION
        answered = producer.record_of(served).content_generation_path.request
        assert answered is not None and answered.schema_version == CHILD_VERSION, "answered at the served lane"


def test_an_offer_floor_outside_the_requirements_lane_is_refused_at_open_by_name(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    config = fixture.consumer_config(compatible_from="1.0.0", producers={"child": fixture.producer_section(versions_from="2.0.0")})
    root = _tree(tmp_path, config=config)
    with pytest.raises(ValueError, match="R-13") as refused:
        _open(root, tmp_path / "scratch", producer_url)
    assert "2.0.0" in str(refused.value) and "1.0.0" in str(refused.value)


def test_a_question_cannot_carry_an_instant_and_the_child_answers_the_composites(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    """The mapping has no `asked_at` to change: the child's instant is the
    composite's, by construction and by the retained child."""
    with pytest.raises(ValidationError):
        ChildQuestion(subject="s", intent="i", freshness="f", parameters={}, asked_at=ASKED_AT)  # type: ignore[call-arg]
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct)
        row = _the_row(opened, served)
        assert row.child_asked_at == ASKED_AT
        assert _retained_child(opened, row.child_content_address).temporal_boundary == ASKED_AT


def test_the_mapping_is_the_authority_on_the_subject_and_the_row_records_what_was_asked(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    """A mapping that sends another subject asks another question — recorded by
    identity, held to the producer's echo, and admitted as what it is."""

    def other_subject(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
        return ChildQuestion(subject="acct-2", intent="fixture-intent", freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000})

    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url, questions=other_subject) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = _the_row(opened, served)
    wire = WireRequest(product_id=CHILD_CLASS, parameters={THRESHOLD_PARAMETER: 1000}, temporal_boundary=ASKED_AT)
    expected = question_identity(
        request_json=canonical_bytes(wire).decode("utf-8"), subject="acct-2",
        intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT,
    )
    assert row.child_question_address == expected
    assert row.child_question_address != question_identity(
        request_json=canonical_bytes(wire).decode("utf-8"), subject="acct-1",
        intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT,
    )


# --- 3. negative controls, through the public surface ----------------------------------


def test_each_missing_declaration_is_refused_at_open_naming_the_section(tmp_path: pathlib.Path, producer_url: str) -> None:
    for omitted, match in (
        ({"producers": None}, "producers"),
        ({"skills": None}, "skills"),
        ({"agent": None}, "agent"),
    ):
        root = _tree(tmp_path / match, config=fixture.consumer_config(**omitted))
        with pytest.raises(ValueError, match=match):
            _open(root, tmp_path / match / "scratch", producer_url)


def test_a_missing_question_mapping_is_refused_at_open(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path)
    with pytest.raises(ValueError, match="questions="):
        _open(root, tmp_path / "scratch", producer_url, questions=None)


def test_a_declaration_offering_the_wrong_class_is_refused_at_open(tmp_path: pathlib.Path, producer_url: str) -> None:
    config = fixture.consumer_config(producers={"child": fixture.producer_section(offered_class="fixture.other")})
    root = _tree(tmp_path, config=config)
    with pytest.raises(ValueError, match="no entry under `producers:` offers"):
        _open(root, tmp_path / "scratch", producer_url)


def test_a_skill_naming_the_wrong_producer_or_class_is_refused_at_open(tmp_path: pathlib.Path, producer_url: str) -> None:
    wrong_server = fixture.consumer_config(skills={SKILL: fixture.skill_section(binding={"server": "someone-else"})})
    with pytest.raises(ValueError, match="binding.server"):
        _open(_tree(tmp_path / "a", config=wrong_server), tmp_path / "a" / "scratch", producer_url)
    wrong_class = fixture.consumer_config(skills={SKILL: fixture.skill_section(produces="fixture.other")})
    with pytest.raises(ValueError, match="does not require"):
        _open(_tree(tmp_path / "b", config=wrong_class), tmp_path / "b" / "scratch", producer_url)


def test_a_revoked_grant_refuses_no_producing_skill_as_a_governed_row(tmp_path: pathlib.Path, producer_url: str) -> None:
    """Grant absent at QUESTION time: revoked on the shared plane after open, the
    slot has no producing skill and the composite refuses, with the row."""
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        assert opened.agent is not None
        ledger = GrantLedger(control_plane=opened.control_plane, catalog=SkillCatalog(opened.control_plane), sink=None, clock=lambda: ADMITTED_AT)  # type: ignore[arg-type]
        agent_hash = content_hash(opened.agent)
        ledger.revoke(ledger.bound_view(agent_hash).grant_hash_for(SKILL), actor="test")
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        assert _the_row(opened, refused).outcome_status == "no-producing-skill"


def test_a_grant_the_regime_does_not_permit_is_refused_at_open_with_the_ledgers_reason(
    tmp_path: pathlib.Path, producer_url: str
) -> None:
    config = fixture.consumer_config(skills={SKILL: fixture.skill_section(requirements={"required_scopes": ["scope:x"], "required_context_products": []})})
    root = _tree(tmp_path, config=config)
    with pytest.raises(ValueError, match="RequirementsExceedRegime"):
        _open(root, tmp_path / "scratch", producer_url)


def test_a_regime_requiring_approval_with_no_sink_is_refused_at_open_by_name(tmp_path: pathlib.Path, producer_url: str) -> None:
    config = fixture.consumer_config(governance={"grant_requires_approval": True, "permitted_scopes": []})
    root = _tree(tmp_path, config=config)
    with pytest.raises(ValueError, match="approval_sink="):
        _open(root, tmp_path / "scratch", producer_url)


def test_an_unreachable_producer_is_a_governed_producer_unavailable_row(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", "http://127.0.0.1:1/mcp") as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
    assert row.refusal_ref == "producer-unavailable" and row.producer_server == SERVER_NAME


def test_a_producer_asserting_another_identity_or_tenant_refuses_by_name(tmp_path: pathlib.Path, producer_url: str) -> None:
    for label, section, reason in (
        ("id", fixture.producer_section(producer_id="someone-else"), "producer-mismatch"),
        ("tenant", fixture.producer_section(producer_tenant="another-tenant"), "producer-tenant-mismatch"),
    ):
        root = _tree(tmp_path / label, config=fixture.consumer_config(producers={"child": section}))
        with _open(root, tmp_path / label / "scratch", producer_url) as opened:
            refused = opened.answer(_question(opened))
            assert isinstance(refused, RefusalEnvelope), refused
            assert _the_row(opened, refused).refusal_ref == reason


def test_a_missing_endpoint_variable_or_remote_block_is_a_named_deployment_error(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path / "a")
    with pytest.raises(ProducerEnvironmentMissing, match=ENDPOINT_VAR):
        open_product(
            config_root=root, scratch=tmp_path / "a" / "scratch", acquire=fixture.Acquire(), project=fixture.plan_factory,
            assess=fixture.assess, questions=fixture.questions, environ={PARENT_DSN_VAR: "x", CREDENTIAL_VAR: DEV_TOKEN},
        )
    root = _tree(tmp_path / "b", environment=fixture.consumer_environment_text(remote=False))
    with pytest.raises(ValueError, match="remote"):
        _open(root, tmp_path / "b" / "scratch", producer_url)


def test_no_address_and_no_credential_appears_in_either_document(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    for name in ("ccf_config.yaml", "ccf_environment.yaml"):
        text = (root / name).read_text(encoding="utf-8")
        assert "http" not in text and DEV_TOKEN not in text and "127.0.0.1" not in text, name


# --- 4. the hatch, and bypass attempts ------------------------------------------------


def _low_road_children(opened_registry: ControlPlaneRegistry, url: str) -> QuestionBoundChildResolver:
    """The low road, built by hand beside the paved surface: registry → catalog → grant → resolver."""
    from ccf.agents.definitions import AgentDefinition  # noqa: PLC0415
    from ccf.controlplane.artifacts import MCP_PRODUCER, declared_artifact_class, parse_artifact  # noqa: PLC0415
    from ccf.mcp.client import SyncMcpBridge  # noqa: PLC0415
    from ccf.skills.catalog import McpProductBinding, SkillArgumentSchema, SkillCatalogEntry, SkillRequirements  # noqa: PLC0415
    from ccf.skills.dispatch import McpSkillRegistry  # noqa: PLC0415
    from ccf.skills.grants import SkillGrant  # noqa: PLC0415
    from ccf.skills.producers import register_declared_producer  # noqa: PLC0415

    regime_key = f"{CONSUMER_TENANT}/policy-bundle/low-road"
    regime_class = declared_artifact_class("policy-bundle")
    opened_registry.register_typed(
        regime_key,
        parse_artifact({"class_id": "policy-bundle", "semver": "1.0.0", "declaration": {"regime": "low-road", "skill_governance": {"grant_requires_approval": False, "permitted_scopes": []}}}, regime_class),
        regime_class,
    )
    definition = AgentDefinition(
        schema_version="1.0.0", artifact_version="1.0.0", name="low-road-consumer", tenant=CONSUMER_TENANT,
        archetypes=("context_assembly",),
        context_contract={"consumes": [{"product_class": CHILD_CLASS, "schema_version": CHILD_VERSION}]},  # type: ignore[arg-type]
        perspective={"role": "role-fixture", "selection_params": {}},  # type: ignore[arg-type]
        policy_regime={"ref": f"ccf-artifact://{regime_key}@1.0.0"},  # type: ignore[arg-type]
        halflife_debt_profile={"ref": f"ccf-artifact://{CONSUMER_TENANT}/debt-profile/x@1.0.0"},  # type: ignore[arg-type]
        instruction_bindings=(),
    )
    catalog = SkillCatalog(opened_registry)
    catalog.register(SkillCatalogEntry(
        schema_version="1.0.0", artifact_version="1.0.0", name="low-road-ask", tenant=CONSUMER_TENANT, skill_type="mcp_product",
        description="asks the paved child producer on the low road", argument_schema=SkillArgumentSchema(properties={}, required=()),
        binding=McpProductBinding(server=SERVER_NAME, product_class=CHILD_CLASS, product_version=CHILD_VERSION),
        requirements=SkillRequirements(required_scopes=frozenset(), required_context_products=frozenset()), produces=CHILD_CLASS,
    ))
    ledger = GrantLedger(control_plane=opened_registry, catalog=catalog, sink=None, clock=lambda: ADMITTED_AT)  # type: ignore[arg-type]
    outcome = ledger.request(
        SkillGrant(schema_version="1.0.0", artifact_version="1.0.0", name="grant-low-road-ask", tenant=CONSUMER_TENANT,
                   agent_definition_hash=content_hash(definition), skill_name="low-road-ask", skill_version="1.0.0"),
        definition=definition, actor="low-road-consumer",
    )
    assert isinstance(outcome, str), outcome
    mcp = McpSkillRegistry(audit_log=opened_registry.audit_log, clock=lambda: ADMITTED_AT)
    register_declared_producer(
        mcp, artifact=parse_artifact({"semver": "1.0.0", **fixture.producer_section()}, MCP_PRODUCER),  # type: ignore[arg-type]
        environ={ENDPOINT_VAR: url, CREDENTIAL_VAR: DEV_TOKEN}, bridge=SyncMcpBridge(call_timeout_seconds=60),
        credential_factory=lambda token: lambda: httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=60),
    )
    return QuestionBoundChildResolver(
        ledger=ledger, agent_definition_hash=content_hash(definition),
        gate=CompositeAdmissionGate(tenant_id=CONSUMER_TENANT, consumer_scope="consumer://low-road", registry=opened_registry),
        child_questions=fixture.questions, callable_registry=CallableRegistry(),
        artifact_store=FileArtifactStore(root=tmp_store_root), mcp_skills=mcp,
    )


tmp_store_root = pathlib.Path()


def test_the_children_hatch_still_works_beside_the_declared_producers(tmp_path: pathlib.Path, producer_url: str) -> None:
    """`children=` with `producers:` declared and no `skills:`/`agent:`: the low
    road composes on the paved surface, and the SDK's own registration of the
    declared producer is still there on `opened.mcp_skills`."""
    global tmp_store_root
    tmp_store_root = tmp_path / "scratch" / "artifact-store"
    tmp_store_root.mkdir(parents=True)
    registry = ControlPlaneRegistry()
    config = fixture.consumer_config(skills=None, agent=None)
    root = _tree(tmp_path, config=config)
    children = _low_road_children(registry, producer_url)
    with _open(root, tmp_path / "scratch", producer_url, questions=None, children=children, control_plane=registry) as opened:
        assert opened.mcp_skills is not None and opened.agent is None
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = _the_row(opened, served)
    assert row.outcome_status == "admitted" and row.producing_skill_name == "low-road-ask"


def test_a_hatch_beside_a_declared_chain_or_a_mapping_is_refused_at_open(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path)
    resolver = object()
    with pytest.raises(ValueError, match="never both"):
        _open(root, tmp_path / "scratch", producer_url, children=resolver)  # skills + agent declared
    with pytest.raises(ValueError, match="never both"):
        _open(_tree(tmp_path / "b", config=fixture.consumer_config(skills=None, agent=None)), tmp_path / "b" / "scratch", producer_url, children=resolver)  # questions= too


def test_a_hatch_that_hands_back_an_unadmitted_product_cannot_be_composed(tmp_path: pathlib.Path, producer_url: str) -> None:
    """Bypass attempt: a resolver returning a bare contract — no admission, no
    mint — is refused by the composition's own provenance check, by name."""
    vessel = ContextProductContract.model_validate_json(
        (pathlib.Path(__file__).parent / "fixtures" / "paved_child_vessel.json").read_text()
    ) if (pathlib.Path(__file__).parent / "fixtures" / "paved_child_vessel.json").exists() else None

    def bypass(*, requirements: Any, asked_at: Any, admitted_at: Any, composition_invocation: Any, consumer_lineage: Any) -> dict[str, object]:
        return {CHILD_CLASS: vessel if vessel is not None else object()}

    root = _tree(tmp_path, config=fixture.consumer_config(skills=None, agent=None))
    with _open(root, tmp_path / "scratch", producer_url, questions=None, children=bypass) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        assert _the_row(opened, refused).refusal_ref in {"unsupported-outcome", "undeclared-outcome", "provenance-unverified"}
