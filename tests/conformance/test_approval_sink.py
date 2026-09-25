"""The ``ApprovalSink`` conformance suite — the acceptance bar for every sink.

D-09 fixes the shape: tier-2 grant governance runs the full state machine
behind a typed ``ApprovalSink`` Protocol, decided in I.2 by a test double and
in I.4 by the real ApprovalGate — **which joins the parametrization below
unchanged** (the D-16 discipline of ``tests/conformance/test_artifactstore.py``:
the suite exists before the implementation it will accept).

Assertions here are about Protocol behavior only: a conforming sink is
runtime-checkable, decides a grant value, and returns a *typed* outcome
carrying a verdict and an approver id string. Nothing here inspects how the
sink reached its verdict — that is precisely what varies between a scripted
double and a suspended human approval. Approver *identity binding* is
deliberately out of scope (D-IMPL-21, I.4; T-05-19 accepted).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.hitl.approval_gate import ApprovalGate, ApprovalSinkAdapter, GateResolution
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
from ccf.skills.grants import ApprovalOutcome, ApprovalSink, SkillGrant
from skills.sinks import ScriptedApprovalSink
from tests.hitl.capabilities import submit_capability

pytestmark = pytest.mark.conformance

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "skills"


def _fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / "grants.yaml").read_text())
    return loaded


def _grant() -> SkillGrant:
    fixture = _fixture()
    definition = parse_artifact(fixture["agents"]["auto"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    return SkillGrant(
        agent_definition_hash=content_hash(definition),
        **fixture["grants"]["metrics_tool"],
    )


SinkFactory = Callable[[bool], ApprovalSink]


def _hitl_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES.parent / "hitl.yaml").read_text()
    )
    return loaded


@pytest.fixture(params=["scripted-double", "approval-gate-adapter"])
def sink_factory(request: pytest.FixtureRequest) -> Iterator[SinkFactory]:
    """A factory for the sink under test, one param per implementation.

    Takes the verdict the produced sink must return, because a conformance
    suite that could only observe approvals would never assert the rejection
    path. I.4's ApprovalGate joins here (D-09) via *composition*: the gate
    owns the async transport/suspend/binding face; the thin
    :class:`~ccf.hitl.approval_gate.ApprovalSinkAdapter` wraps the
    already-completed bound decision the gate produced and satisfies the
    sync grant face — supplied here with a bound in-memory completed
    decision, so the test bodies below stay byte-unchanged and approver
    identity binding stays out of suite scope as reserved (D-IMPL-21).
    """
    if request.param == "scripted-double":
        approver_id = _fixture()["approval"]["approver_id"]

        def factory(approve: bool) -> ApprovalSink:
            return ScriptedApprovalSink(approve=approve, approver_id=approver_id)

        yield factory
        return
    if request.param == "approval-gate-adapter":
        hitl = _hitl_fixture()

        def factory(approve: bool) -> ApprovalSink:
            transport = InMemoryHitlTransport()
            gate = ApprovalGate(
                transport=transport,
                audit=AuditLog(),
                clock=lambda: datetime.fromisoformat(
                    hitl["approvers"]["credit_officer"]["action_time"]
                ),
            )
            event_document = dict(hitl["event"])
            event = PendingHitlEvent(
                **event_document,
                product_content_hash=content_hash(event_document),
            )
            transport.enqueue(event=event)
            approver = hitl["approvers"]["credit_officer"]
            resolution = gate.resolve(
                submit_capability(
                    tenant=event.tenant,
                    principal=approver["identity"]["subject_id"],
                    event_key=event.event_key,
                ),
                event_key=event.event_key,
                action="approve" if approve else "reject",
                principal=HumanPrincipalBinding(
                    approver=ApproverIdentity(**approver["identity"]),
                    authentication=AuthenticationContext(
                        **approver["authentication"]
                    ),
                    action_time=datetime.fromisoformat(
                        approver["action_time"]
                    ),
                    product_content_hash=event.product_content_hash,
                ),
            )
            assert isinstance(resolution, GateResolution)
            return ApprovalSinkAdapter(resolution=resolution)

        yield factory
        return
    raise NotImplementedError(request.param)


def test_the_sink_conforms_to_the_protocol_structurally(
    sink_factory: SinkFactory,
) -> None:
    assert isinstance(sink_factory(True), ApprovalSink)


def test_an_approval_is_a_typed_outcome_naming_its_approver(
    sink_factory: SinkFactory,
) -> None:
    outcome = sink_factory(True).decide(_grant())
    assert isinstance(outcome, ApprovalOutcome)
    assert isinstance(outcome, CCFContract)
    assert outcome.approved is True
    assert outcome.approver_id
    assert isinstance(outcome.approver_id, str)


def test_a_rejection_is_the_same_typed_outcome_not_an_exception(
    sink_factory: SinkFactory,
) -> None:
    """A rejection is an expected governance verdict, never control flow."""
    outcome = sink_factory(False).decide(_grant())
    assert isinstance(outcome, ApprovalOutcome)
    assert outcome.approved is False
    assert outcome.approver_id


def test_the_outcome_is_a_value_the_ledger_can_audit(
    sink_factory: SinkFactory,
) -> None:
    """The outcome is canonically serializable — it must land in audit/replay."""
    outcome = sink_factory(True).decide(_grant())
    assert content_hash(outcome)
