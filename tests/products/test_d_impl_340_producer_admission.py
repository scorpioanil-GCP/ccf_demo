"""`D-IMPL-340` — the producer admission leg, held to the registration.

In-process proofs over REAL machinery with a stand-in producer door: a stub
client that answers `call_tool_text` the way a producer's door would — from a
genuinely served child vessel — but whose *claims* (its tenant, its producer
assertion, its echo of the question, its replay reference) the test chooses.
Every dispatch runs through :func:`~ccf.skills.dispatch.dispatch_skill`, every
invocation is minted by `_invoke_mcp_product`, and every verdict is
:class:`~ccf.products.composite.CompositeAdmissionGate`'s. Nothing here
constructs a `ChildInvocation` or a `ChildCandidate` by hand.

| Proof | Test |
| --- | --- |
| 3 producer identity is governed, not caller-authored | `test_the_invocation_carries_the_registration_and_cannot_be_forged` |
| 4 producer tenant is governed, not payload-authored | `test_the_same_bytes_admit_under_one_registration_and_refuse_under_another` |
| 5 wrong producer refuses | `test_a_door_asserting_another_producer_refuses` |
| 6 wrong producer tenant refuses independently | `test_each_of_the_three_tenant_claims_is_held_to_the_registration` |
| 7 self-claim cannot authorize | `test_a_payload_claiming_the_expected_producer_cannot_authorize_itself` |
| 9 question echo mismatch refuses | `test_an_echo_of_a_different_question_refuses` |
| 10/11 provider-controls; local register silence is not authority | `test_the_local_register_is_not_consulted_on_the_producer_leg_and_is_on_the_local_one` |
| ruling 1 | `test_a_producer_that_cannot_answer_is_a_governed_row_and_a_mis_wired_one_is_an_error` |
| ruling 10 | `test_a_literal_address_or_secret_is_refused_at_parse_and_no_question_member_reaches_an_address` |
| 14 existing legs unchanged | `test_the_legacy_resolver_takes_the_legacy_call` |

`ledger_for_product_ask` is shared with the cross-process proofs.
"""

from __future__ import annotations

import hashlib
import inspect
import pathlib
from datetime import datetime
from collections.abc import Callable, Iterator, Mapping
from typing import Any

import pytest

import ccf.products.composite as composite_module
from ccf.agents.definitions import AgentDefinition
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import MCP_PRODUCER, ArtifactLoadError, parse_artifact
from ccf.controlplane.artifacts import declared_artifact_class
from ccf.mcp.client import SyncMcpBridge
from ccf.mcp.errors import McpServerUnreachable, McpTimeout, McpToolFailed
from ccf.products import child_resolver as child_resolver_module
from ccf.products.child_resolver import (
    ChildQuestion,
    GrantBoundChildResolver,
    QuestionBoundChildResolver,
)
from ccf.products.composite import (
    CompositeAdmissionGate,
    RequestAwareChildResolverProtocol,
    invocation_from_dispatch,
)
from ccf.products.contract import ChildRequirement, ContextProductContract
from ccf.products.door import AnsweredQuestion, DoorOutcome, ProducerAssertion, WireRequest
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills import dispatch as dispatch_module
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    McpProductBinding,
    SkillArgumentSchema,
    SkillCatalog,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.skills.dispatch import (
    McpProductInvocation,
    McpProductProvenanceError,
    McpSkillRegistry,
    McpSkillUnregistered,
    ProducerDoesNotOffer,
    ProductQuestion,
    dispatch_skill,
    verify_mcp_product_invocation,
)
from ccf.skills.grants import GrantLedger, SkillGrant
from ccf.skills.producers import (
    ProducerEnvironmentMissing,
    producer_registration_from_artifact,
    register_declared_producer,
)

from tests.crossproc.servers.product_producer_identity import (
    PRODUCER_ID,
    PRODUCER_TENANT,
    SERVER_NAME,
)
from tests.products.composite_fixture import ask_composite, boot_composite, build_composite
from tests.products.provider_boot import CHILD_CLASS, serve_atomic_child
from tests.products.test_resolver_seam import (
    ADMITTED_AT,
    ASKED_AT,
    PERSPECTIVE,
    PRODUCT_CLASS as PARENT_CLASS,
    PRODUCT_VERSION as PARENT_VERSION,
    TENANT,
    THRESHOLD_PARAMETER,
    _Booted,
    _arguments,
)

SKILL = "child-product-ask"
REGIME_KEY = f"{TENANT}/policy-bundle/d-impl-340"
#: One ledger and one effective grant per fabric: a grant artifact is single-use
#: on its Control Plane (WR-05) and two effective grants for one agent and one
#: skill collide, so every wiring over one fabric shares the ledger built first
#: — the `D-IMPL-339` lesson, kept.
_LEDGERS: dict[int, tuple[GrantLedger, str]] = {}
ENDPOINT_VAR = "CCF_TEST_CHILD_PRODUCER_URL"
CREDENTIAL_VAR = "CCF_TEST_CHILD_PRODUCER_TOKEN"


# --- shared wiring -----------------------------------------------------------


def ledger_for_product_ask(
    booted: _Booted, *, grant: bool = True, product_version: str = "1.0.0"
) -> tuple[GrantLedger, str]:
    """A real ledger over the deployment's Control Plane with one `mcp_product` grant."""
    registry = booted.control_plane
    if grant and id(registry) in _LEDGERS:
        return _LEDGERS[id(registry)]
    regime_class = declared_artifact_class("policy-bundle")
    registry.register_typed(
        REGIME_KEY,
        parse_artifact(
            {
                "class_id": "policy-bundle",
                "semver": "1.0.0",
                "declaration": {
                    "regime": "d-impl-340",
                    "skill_governance": {
                        "grant_requires_approval": False,
                        "permitted_scopes": [],
                    },
                },
            },
            regime_class,
        ),
        regime_class,
    )
    definition = AgentDefinition(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="d-impl-340-assembler",
        tenant=TENANT,
        archetypes=("context_assembly",),
        context_contract={
            "consumes": [{"product_class": CHILD_CLASS, "schema_version": "1.0.0"}]
        },
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
            description="asks the registered child-product producer a question",
            argument_schema=SkillArgumentSchema(properties={}, required=()),
            binding=McpProductBinding(
                server=SERVER_NAME, product_class=CHILD_CLASS, product_version=product_version
            ),
            requirements=SkillRequirements(
                required_scopes=frozenset(), required_context_products=frozenset()
            ),
            produces=CHILD_CLASS,
        )
    )
    ledger = GrantLedger(
        control_plane=registry, catalog=catalog, sink=None, clock=lambda: ADMITTED_AT
    )
    if grant:
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
            actor="d-impl-340",
        )
        assert isinstance(outcome, str), outcome
        _LEDGERS[id(registry)] = (ledger, content_hash(definition))
    return ledger, content_hash(definition)


def producer_document(
    *,
    producer_id: str = PRODUCER_ID,
    producer_tenant: str = PRODUCER_TENANT,
    versions_from: str = "1.0.0",
    server: str = SERVER_NAME,
) -> dict[str, Any]:
    return {
        "semver": "1.0.0",
        "server": server,
        "producer_id": producer_id,
        "producer_tenant": producer_tenant,
        "endpoint_from_env": ENDPOINT_VAR,
        "credential_from_env": CREDENTIAL_VAR,
        "offers": [{"product_class": CHILD_CLASS, "versions_from": versions_from}],
    }


def questions(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
    return ChildQuestion(
        subject=request.subject,
        intent="fixture-intent",
        freshness="fixture-freshness",
        parameters={THRESHOLD_PARAMETER: request.parameters[THRESHOLD_PARAMETER]},
    )


class DoorStub:
    """A producer's door, answering from a REAL served vessel with claims the test picks.

    Only the claims move: the governed contract inside is the fixture child
    product as its own resolver served it. ``fail`` makes the door a producer
    that cannot answer.
    """

    def __init__(
        self,
        vessel: str,
        *,
        tenant: str = PRODUCER_TENANT,
        assertion: ProducerAssertion | None = None,
        replay_tenant: str | None = None,
        echo_rewrite: Callable[[WireRequest], WireRequest] | None = None,
        answered_rewrite: Callable[[AnsweredQuestion], AnsweredQuestion] | None = None,
        fail: Exception | None = None,
        refuse: bool = False,
        text: str | None = None,
        schema_name: str | None = None,
    ) -> None:
        self._schema_name = schema_name
        self._vessel = vessel
        self._tenant = tenant
        self._assertion = assertion
        self._replay_tenant = replay_tenant
        self._echo_rewrite = echo_rewrite
        self._answered_rewrite = answered_rewrite
        self._fail = fail
        self._refuse = refuse
        self._text = text
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call_tool_text(self, name: str, arguments: Mapping[str, Any]) -> str:
        self.calls.append((name, dict(arguments)))
        if self._fail is not None:
            raise self._fail
        if self._text is not None:
            return self._text
        wire = WireRequest.model_validate_json(arguments["request"])
        echo = self._echo_rewrite(wire) if self._echo_rewrite else wire
        answered = AnsweredQuestion(
            subject=arguments["subject"],
            intent=arguments["intent"],
            freshness=arguments["freshness"],
            asked_at=datetime.fromisoformat(arguments["asked_at"]),
        )
        if self._answered_rewrite is not None:
            answered = self._answered_rewrite(answered)
        if self._refuse:
            # A governed refusal from this door: the shape `door_answer` emits
            # for a recorded, disclosed envelope, with the same claims.
            return canonical_bytes(
                DoorOutcome(
                    request=echo,
                    product_json=None,
                    content_address=None,
                    replay_ref=_REFUSAL_REPLAY_REF.format(tenant=self._replay_tenant or self._tenant),
                    refusal=_a_refusal(self._replay_tenant or self._tenant),
                    producer=self._assertion,
                    answered=answered,
                )
            ).decode("utf-8")
        contract = ContextProductContract.model_validate_json(self._vessel).model_copy(
            update={
                "tenant_id": self._tenant,
                **({"schema_name": self._schema_name} if self._schema_name else {}),
            }
        )
        vessel = canonical_bytes(contract)
        address = hashlib.sha256(vessel).hexdigest()
        replay_tenant = self._replay_tenant or self._tenant
        return canonical_bytes(
            DoorOutcome(
                request=echo,
                product_json=vessel.decode("utf-8"),
                content_address=address,
                replay_ref=f"ccf-artifact://{replay_tenant}/fixture.replay-record/x@{address}",
                refusal=None,
                producer=self._assertion,
                answered=answered,
            )
        ).decode("utf-8")


_REFUSAL_REPLAY_REF = "ccf-artifact://{tenant}/fixture.replay-record/refused@" + "b" * 64


def _a_refusal(tenant: str) -> RefusalEnvelope:
    """A recorded, disclosed refusal envelope, as a producer's door would emit.

    Built from the envelope machinery the doors use (`envelope_for` over a
    subject-unavailable refusal, then disclosed and given its replay
    reference), so `door_refusal` accepts it exactly as it accepts a
    producer's own — nothing here is a hand-typed envelope.
    """
    from ccf.products.refusal import (  # noqa: PLC0415
        RequestIdentity,
        SubjectUnavailableRefusal,
        envelope_for,
    )

    envelope = envelope_for(
        SubjectUnavailableRefusal(
            cause="unauthorized", detail="the producer's own door refused", error_code="E"
        ),
        request=RequestIdentity(
            product_id=CHILD_CLASS,
            product_version="1.0.0",
            parameters={THRESHOLD_PARAMETER: 1000},
            temporal_boundary=ASKED_AT,
        ),
    )
    return envelope.model_copy(
        update={
            "disclosure": "minimal",
            "replay_reference": _REFUSAL_REPLAY_REF.format(tenant=tenant),
        }
    )


def honest_assertion() -> ProducerAssertion:
    return ProducerAssertion(producer_id=PRODUCER_ID, tenant_id=PRODUCER_TENANT)


@pytest.fixture
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    deployment = boot_composite(tmp_path)
    yield next(deployment)
    deployment.close()


@pytest.fixture
def vessel(tmp_path: pathlib.Path) -> str:
    """The fixture child product, genuinely served once, as door bytes."""
    answer = DoorOutcome.model_validate_json(serve_atomic_child(tmp_path / "producer"))
    assert answer.product_json is not None
    return answer.product_json


def wired(
    booted: _Booted,
    door: DoorStub,
    *,
    document: Mapping[str, Any] | None = None,
) -> tuple[GovernedResolver, McpSkillRegistry, QuestionBoundChildResolver]:
    registry = McpSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    registry.register_producer(
        client=door,  # type: ignore[arg-type]  # duck-typed: only call_tool_text is used
        registration=producer_registration_from_artifact(
            parse_artifact(document or producer_document(), MCP_PRODUCER)
        ),
    )
    ledger, agent_hash = ledger_for_product_ask(booted)
    children = QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=CompositeAdmissionGate(
            tenant_id=TENANT, consumer_scope="consumer://d-impl-340", registry=booted.control_plane
        ),
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=booted.store,
        mcp_skills=registry,
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=children)
    return GovernedResolver(**arguments), registry, children


def ask(resolver: GovernedResolver, *, threshold: int = 1000) -> Any:
    return resolver(
        tenant=TENANT,
        product_class=PARENT_CLASS,
        version=PARENT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PARENT_CLASS,
            schema_version=PARENT_VERSION,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: threshold},
        ),
    )


def row_of(booted: _Booted, outcome: Any) -> Any:
    store = booted.store
    if isinstance(outcome, ServedProduct):
        raw = store.get(content_address=outcome.replay_ref.content_address)
    else:
        raw = store.get(content_address=store.resolve_uri(uri=outcome.replay_reference))
    rows = DecisionReplayRecord.model_validate_json(raw).content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    return rows[0]


def refused_as(booted: _Booted, outcome: Any, reason: str) -> Any:
    assert not isinstance(outcome, ServedProduct), "admitted where a refusal was expected"
    row = row_of(booted, outcome)
    assert row.refusal_ref == reason, (row.refusal_ref, row.outcome_status)
    return row


# --- proof 3 -----------------------------------------------------------------


def test_the_invocation_carries_the_registration_and_cannot_be_forged(
    booted: _Booted, vessel: str
) -> None:
    resolver, _registry, _children = wired(booted, DoorStub(vessel, assertion=honest_assertion()))
    served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    row = row_of(booted, served)
    expected = parse_artifact(producer_document(), MCP_PRODUCER)
    assert row.producer_id == expected.producer_id
    assert row.producer_tenant == expected.producer_tenant
    assert row.producer_registration_address == content_hash(expected)
    assert row.producer_server == SERVER_NAME
    # The public constructor refuses a caller-chosen producer.
    with pytest.raises(McpProductProvenanceError):
        McpProductInvocation(
            skill_name=SKILL,
            skill_type="mcp_product",
            server=SERVER_NAME,
            producer_id="anyone",
            producer_tenant=PRODUCER_TENANT,
            producer_registration_address="x",
            product_class=CHILD_CLASS,
            product_version="1.0.0",
            question_address="q",
            request_json="{}",
            contents="",
            arguments={},
            token=object(),
        )
    # A nominal instance that skipped the mint is refused at the boundary.
    forged = object.__new__(McpProductInvocation)
    with pytest.raises(McpProductProvenanceError):
        verify_mcp_product_invocation(forged)


# --- proof 4 -----------------------------------------------------------------


def test_the_same_bytes_admit_under_one_registration_and_refuse_under_another(
    booted: _Booted, vessel: str
) -> None:
    door = DoorStub(vessel, assertion=honest_assertion())
    honest, _r, _c = wired(booted, door)
    assert isinstance(ask(honest), ServedProduct)
    moved, _r, _c = wired(booted, door, document=producer_document(producer_tenant="other-tenant"))
    row = refused_as(booted, ask(moved), "producer-tenant-mismatch")
    assert row.outcome_status == "unauthorized"
    assert row.producer_tenant == "other-tenant"


# --- proof 5 -----------------------------------------------------------------


def test_a_door_asserting_another_producer_refuses(booted: _Booted, vessel: str) -> None:
    door = DoorStub(
        vessel, assertion=ProducerAssertion(producer_id="impostor", tenant_id=PRODUCER_TENANT)
    )
    resolver, _r, _c = wired(booted, door)
    row = refused_as(booted, ask(resolver), "producer-mismatch")
    assert row.producer_id == PRODUCER_ID  # the expectation, never the claim


# --- proof 6 -----------------------------------------------------------------


def test_each_of_the_three_tenant_claims_is_held_to_the_registration(
    booted: _Booted, vessel: str
) -> None:
    """The contract's tenant, the replay reference's tenant, and the
    assertion's tenant — each alone refuses, and always as the tenant reason
    while the producer identity stays equal.

    **Each case moves exactly ONE claim** and keeps the other two honest, so
    each of the three checks is the only one that can refuse its case. The
    first version of this proof let the replay reference follow the contract's
    tenant, and sabotage S3 (delete the contract-tenant check) stayed green
    because the replay-reference check refused in its place — a proof with two
    checks behind one assertion measures neither.
    """
    contract_claims = DoorStub(
        vessel, tenant="other-tenant", replay_tenant=PRODUCER_TENANT, assertion=honest_assertion()
    )
    refused_as(booted, ask(wired(booted, contract_claims)[0]), "producer-tenant-mismatch")
    replay_claims = DoorStub(vessel, replay_tenant="other-tenant", assertion=honest_assertion())
    refused_as(booted, ask(wired(booted, replay_claims)[0]), "producer-tenant-mismatch")
    assertion_claims = DoorStub(
        vessel, assertion=ProducerAssertion(producer_id=PRODUCER_ID, tenant_id="other-tenant")
    )
    row = refused_as(booted, ask(wired(booted, assertion_claims)[0]), "producer-tenant-mismatch")
    assert row.producer_id == PRODUCER_ID


def test_a_door_that_asserts_nothing_is_refused(booted: _Booted, vessel: str) -> None:
    """No assertion, nothing to hold to the registration — refused, never admitted
    on the contract's tenant alone."""
    row = refused_as(booted, ask(wired(booted, DoorStub(vessel))[0]), "producer-unasserted")
    assert row.outcome_status == "unauthorized"
    assert row.producer_id == PRODUCER_ID


def test_a_refusing_door_is_held_to_the_registration_before_it_is_ineligible(
    booted: _Booted, vessel: str
) -> None:
    """Review finding on the first cut: an impostor's REFUSAL was filed as
    `ineligible` under the registered producer's name. Now a refusing door's
    claims are held first; only an honest refusal is `ineligible`."""
    impostor = DoorStub(
        vessel, refuse=True, assertion=ProducerAssertion(producer_id="impostor", tenant_id=PRODUCER_TENANT)
    )
    refused_as(booted, ask(wired(booted, impostor)[0]), "producer-mismatch")
    silent = DoorStub(vessel, refuse=True)
    refused_as(booted, ask(wired(booted, silent)[0]), "producer-unasserted")
    honest = DoorStub(vessel, refuse=True, assertion=honest_assertion())
    row = refused_as(booted, ask(wired(booted, honest)[0]), "ineligible")
    assert row.producer_id == PRODUCER_ID and row.producer_server == SERVER_NAME


def test_a_completed_call_that_is_not_a_door_outcome_is_producer_unavailable(
    booted: _Booted, vessel: str
) -> None:
    """A gateway page with HTTP 200 is a producer that was reached and gave no
    governed answer — a row, never an exception out of the composition, and
    never the page's bytes."""
    door = DoorStub(vessel, text="<html>maintenance</html>")
    resolver, _r, children = wired(booted, door)
    row = refused_as(booted, ask(resolver), "producer-unavailable")
    assert row.outcome_status == "producer-unavailable"
    assert row.producer_id == PRODUCER_ID


# --- proof 8 (the class half) -----------------------------------------------


def test_a_child_of_another_class_is_refused_on_the_producer_leg(
    booted: _Booted, vessel: str
) -> None:
    """Check 2 still runs on the producer leg: an honest producer, honest
    tenant, honest echo — but a contract declaring another class."""
    door = DoorStub(vessel, assertion=honest_assertion(), schema_name="fixture.other-product")
    row = refused_as(booted, ask(wired(booted, door)[0]), "class-mismatch")
    assert row.child_schema_name is None or row.child_schema_name == "fixture.other-product"
    assert row.producer_id == PRODUCER_ID


def test_a_naive_answered_instant_is_a_malformed_answer_not_a_host_zone_question(
    booted: _Booted, vessel: str
) -> None:
    """Review finding: an `answered.asked_at` without an offset would let the
    question identity depend on the consumer host's zone. The door refuses
    one at decode, so the consumer sees `producer-unavailable`, and the
    identity it computed for its own question is untouched."""
    honest = DoorStub(vessel, assertion=honest_assertion())
    served_text = honest.call_tool_text(
        "request_context_product",
        {
            "request": canonical_bytes(
                WireRequest(
                    product_id=CHILD_CLASS,
                    parameters={THRESHOLD_PARAMETER: 1000},
                    temporal_boundary=ASKED_AT,
                )
            ).decode("utf-8"),
            "subject": "acct-1",
            "intent": "fixture-intent",
            "freshness": "fixture-freshness",
            "asked_at": ASKED_AT.isoformat(),
        },
    )
    import json  # noqa: PLC0415

    outcome = json.loads(served_text)
    outcome["answered"]["asked_at"] = "2026-03-02T12:00:00"  # naive
    naive = DoorStub(vessel, text=json.dumps(outcome, sort_keys=True, separators=(",", ":")))
    row = refused_as(booted, ask(wired(booted, naive)[0]), "producer-unavailable")
    assert row.producer_id == PRODUCER_ID


# --- proof 7 -----------------------------------------------------------------


def test_a_payload_claiming_the_expected_producer_cannot_authorize_itself(
    booted: _Booted, vessel: str
) -> None:
    """The door asserts exactly what a registration for `PRODUCER_ID` would
    expect — but the registration the consumer resolved expects someone else.
    The claim is held to the registration, never the other way round."""
    door = DoorStub(vessel, assertion=honest_assertion())
    resolver, _r, _c = wired(booted, door, document=producer_document(producer_id="the-real-one"))
    refused_as(booted, ask(resolver), "producer-mismatch")
    # And a server the deployment never registered is a wiring error, before
    # any door is reached at all.
    registry = McpSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    # A producer IS registered — under another name — so a resolver that fell
    # back to "any registered producer" would have one to reach; the binding's
    # name is what must resolve, or nothing does.
    registry.register_producer(
        client=door,  # type: ignore[arg-type]
        registration=producer_registration_from_artifact(
            parse_artifact(producer_document(server="someone-else"), MCP_PRODUCER)
        ),
    )
    ledger, agent_hash = ledger_for_product_ask(booted)
    children = QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=CompositeAdmissionGate(
            tenant_id=TENANT, consumer_scope="consumer://d-impl-340", registry=booted.control_plane
        ),
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=booted.store,
        mcp_skills=registry,
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=children)
    contacted_before = len(door.calls)
    with pytest.raises(McpSkillUnregistered):
        ask(GovernedResolver(**arguments))
    assert len(door.calls) == contacted_before, "an unregistered producer must never be contacted"


# --- proof 9 -----------------------------------------------------------------


def test_an_echo_of_a_different_question_refuses(booted: _Booted, vessel: str) -> None:
    def other_parameters(wire: WireRequest) -> WireRequest:
        return wire.model_copy(update={"parameters": {THRESHOLD_PARAMETER: 999999}})

    door = DoorStub(vessel, assertion=honest_assertion(), echo_rewrite=other_parameters)
    row = refused_as(booted, ask(wired(booted, door)[0]), "question-mismatch")
    assert row.outcome_status == "rejected-at-admission"
    assert row.child_question_address is not None

    # The review's blocking finding: an answer to another SUBJECT must be a
    # different question, though the wire request is byte-identical.
    def other_subject(answered: AnsweredQuestion) -> AnsweredQuestion:
        return answered.model_copy(update={"subject": "victim-2"})

    door = DoorStub(vessel, assertion=honest_assertion(), answered_rewrite=other_subject)
    refused_as(booted, ask(wired(booted, door)[0]), "question-mismatch")

    def other_intent(answered: AnsweredQuestion) -> AnsweredQuestion:
        return answered.model_copy(update={"intent": "another-intent"})

    door = DoorStub(vessel, assertion=honest_assertion(), answered_rewrite=other_intent)
    refused_as(booted, ask(wired(booted, door)[0]), "question-mismatch")


# --- proofs 10 and 11 --------------------------------------------------------


def test_the_local_register_is_not_consulted_on_the_producer_leg_and_is_on_the_local_one(
    booted: _Booted, vessel: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A divergence population: the same gate, two acquisition kinds. The
    producer leg records `provider-controls` and never asks this fabric's
    invalidation register; the local leg asks it. Its silence is therefore
    never the producer child's authority."""
    consulted: list[str] = []
    original = composite_module.refuse_dependency_invalidation

    def spy(candidate: Any, **kwargs: Any) -> Any:
        consulted.append(candidate.schema_name)
        return original(candidate, **kwargs)

    monkeypatch.setattr(composite_module, "refuse_dependency_invalidation", spy)
    resolver, _r, _c = wired(booted, DoorStub(vessel, assertion=honest_assertion()))
    served = ask(resolver)
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    row = row_of(booted, served)
    assert row.eligibility_basis == "provider-controls"
    assert row.producing_fabric == PRODUCER_ID
    assert consulted == [], "the producer leg consulted the local register"
    # The local leg, same fabric, same gate class: consulted.
    local, _children = build_composite(booted)
    assert isinstance(ask_composite(local), ServedProduct)
    assert consulted == [CHILD_CLASS], consulted


# --- ruling 1 ----------------------------------------------------------------


@pytest.mark.parametrize(
    "failure, fragment",
    [
        (McpTimeout("deadline"), "timeout"),
        (McpServerUnreachable("down"), "unreachable"),
        (McpToolFailed("request_context_product", "ccf-runtime-failure:deadbeef"), "deadbeef"),
    ],
    ids=["timeout", "unreachable", "tool-error"],
)
def test_a_producer_that_cannot_answer_is_a_governed_row_and_a_mis_wired_one_is_an_error(
    booted: _Booted, vessel: str, failure: Exception, fragment: str
) -> None:
    resolver, _r, children = wired(booted, DoorStub(vessel, fail=failure))
    refused = ask(resolver)
    row = refused_as(booted, refused, "producer-unavailable")
    assert row.outcome_status == "producer-unavailable"
    assert row.producer_id == PRODUCER_ID and row.producer_server == SERVER_NAME
    # The child's own refusal names the failure — the opaque id, never a
    # traceback and never an address.
    from ccf.products.contract import ProductLineage  # noqa: PLC0415

    outcome = children.resolve_for(
        requirements=(ChildRequirement(product_class=CHILD_CLASS, required=True, compatible_from="1.0.0"),),
        request=ProductRequest(
            schema_name=PARENT_CLASS, schema_version=PARENT_VERSION, subject="acct-1",
            intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
        asked_at=ASKED_AT,
        admitted_at=ADMITTED_AT,
        composition_invocation="probe",
        consumer_lineage=ProductLineage(
            operators_invoked=frozenset(), policy_bundle_versions=frozenset(), graph_snapshot_at=ASKED_AT
        ),
    )[CHILD_CLASS]
    assert outcome.reason == "producer-unavailable"
    assert fragment in outcome.detail
    assert "Traceback" not in outcome.detail and "://" not in outcome.detail
    # Mis-wiring stays an error: an offer that does not cover the lane.
    narrow, _r, _c = wired(
        booted, DoorStub(vessel, assertion=honest_assertion()),
        document=producer_document(versions_from="3.0.0"),
    )
    with pytest.raises(ProducerDoesNotOffer):
        ask(narrow)
    # And a second registration under one logical name is refused.
    registry = McpSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    registration = producer_registration_from_artifact(
        parse_artifact(producer_document(), MCP_PRODUCER)
    )
    registry.register_producer(client=DoorStub(vessel), registration=registration)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="already registered"):
        registry.register_producer(client=DoorStub(vessel), registration=registration)  # type: ignore[arg-type]


# --- ruling 10 ---------------------------------------------------------------


def test_a_literal_address_or_secret_is_refused_at_parse_and_no_question_member_reaches_an_address(
    tmp_path: pathlib.Path,
) -> None:
    for member, literal in (
        ("endpoint_from_env", "http://127.0.0.1:8080/mcp"),
        ("endpoint_from_env", "producer.internal:443"),
        ("credential_from_env", "dev-token-value"),
    ):
        document = producer_document()
        document[member] = literal
        with pytest.raises(ArtifactLoadError):
            parse_artifact(document, MCP_PRODUCER)
    # A named variable that is absent is a configuration error, not a refusal.
    with SyncMcpBridge(call_timeout_seconds=1.0) as bridge:
        registry = McpSkillRegistry(
            audit_log=__import__("ccf.controlplane.audit", fromlist=["AuditLog"]).AuditLog(),
            clock=lambda: ADMITTED_AT,
        )
        with pytest.raises(ProducerEnvironmentMissing):
            register_declared_producer(
                registry,
                artifact=parse_artifact(producer_document(), MCP_PRODUCER),
                environ={},
                bridge=bridge,
            )
    # Static: nothing between a question and the tool call builds an address.
    for source in (
        inspect.getsource(child_resolver_module.QuestionBoundChildResolver.resolve_for),
        inspect.getsource(dispatch_module._invoke_mcp_product),
    ):
        assert "://" not in source
        assert ".url" not in source and "urljoin" not in source
        assert "f\"http" not in source and "f'http" not in source
        assert "McpResourceClient(" not in source and "url=" not in source
    # The question type has the four members and no address-shaped one.
    assert set(ChildQuestion.model_fields) == {"subject", "intent", "freshness", "parameters"}
    assert "url" not in ProductQuestion.model_fields and "endpoint" not in ProductQuestion.model_fields


# --- proof 14 ----------------------------------------------------------------


def test_the_legacy_resolver_takes_the_legacy_call(booted: _Booted) -> None:
    """`GrantBoundChildResolver` does not declare the capability and is served by
    the byte-identical legacy call; `QuestionBoundChildResolver` declares it
    and implements no legacy call at all."""
    legacy, children = build_composite(booted)
    assert not isinstance(children, RequestAwareChildResolverProtocol)
    assert isinstance(children, GrantBoundChildResolver)
    assert isinstance(ask_composite(legacy), ServedProduct)
    ledger, agent_hash = ledger_for_product_ask(booted, grant=False)
    asking = QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=CompositeAdmissionGate(
            tenant_id=TENANT, consumer_scope="consumer://d-impl-340", registry=booted.control_plane
        ),
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=booted.store,
    )
    assert isinstance(asking, RequestAwareChildResolverProtocol)
    assert not callable(asking)
    # Dispatching an `mcp_product` entry without a question is refused by name.
    entry = SkillCatalogEntry(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="ask-without-question",
        tenant=TENANT,
        skill_type="mcp_product",
        description="x",
        argument_schema=SkillArgumentSchema(properties={}, required=()),
        binding=McpProductBinding(server=SERVER_NAME, product_class=CHILD_CLASS, product_version="1.0.0"),
        requirements=SkillRequirements(required_scopes=frozenset(), required_context_products=frozenset()),
        produces=CHILD_CLASS,
    )
    registry = McpSkillRegistry(audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT)
    with pytest.raises(TypeError, match="ProductQuestion"):
        dispatch_skill(entry, arguments={}, callable_registry=CallableRegistry(), mcp_skills=registry)



def test_every_new_refusal_reason_is_emitted_exactly_where_declared() -> None:
    """A census over the source: the five reasons `D-IMPL-340` added, and the
    number of emission sites each has. One reason per path, except the tenant
    reason, which the ruling asked to be ONE reason over three claims (the
    contract's tenant, the replay reference's, the assertion's) — each claim
    with its own sabotage."""
    import re  # noqa: PLC0415

    composite_source = inspect.getsource(composite_module)
    resolver_source = inspect.getsource(child_resolver_module)

    def emissions(source: str, reason: str) -> int:
        # An emission is a refusal CALL carrying the reason — never the
        # vocabulary's own listing of it, and never a status-map key.
        calls = re.findall(r'(?:refuse|refuse_naming_producer)\(\s*"' + re.escape(reason) + r'"', source)
        fields = source.count(f'reason="{reason}"')
        return len(calls) + fields

    emitted = {
        "producer-tenant-mismatch": emissions(composite_source, "producer-tenant-mismatch"),
        "producer-mismatch": emissions(composite_source, "producer-mismatch"),
        "producer-unasserted": emissions(composite_source, "producer-unasserted"),
        "question-mismatch": emissions(composite_source, "question-mismatch"),
        "producer-unavailable": emissions(resolver_source, "producer-unavailable"),
    }
    assert emitted == {
        "producer-tenant-mismatch": 3,
        "producer-mismatch": 1,
        "producer-unasserted": 1,
        "question-mismatch": 3,  # no wire echo; no answered axes; an echo of another question
        "producer-unavailable": 2,  # could not answer; answered with no door outcome
    }, emitted
