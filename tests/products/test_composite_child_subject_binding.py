"""`SEC-025`: a composite child is admitted only for the subject the composite asked.

The row (`docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md`,
``### SEC-025``), ruled at Q16 (a) of
`docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md` under
`D-IMPL-368` / `D-IMPL-370`: *every child leg returns the subject it answered;
the composite refuses by name on any mismatch, on every leg kind, and the
refusal names the leg, not the subject.*

**The defect, reproduced before the repair.** A parent asked about ``acct-1``
whose local child's own door answered ``acct-OTHER`` composed silently: the
child's ``DoorOutcome.answered.subject`` was on the wire and
``child_resolver.py::_door_outcome`` discarded it. Only the ``mcp-product``
leg (`D-IMPL-340`) bound the question at all.

**Four leg kinds** (``ccf.products.composite::ChildAcquisition``), one
mismatch subcase each:

* ``local-dispatch`` and ``mcp`` — red before the repair, the row's targets;
* ``mcp-product`` — already refusing before the repair; it is the
  SHARED-CHECK control. The repair routes every leg through one comparison, so
  severing that comparison must redden this subcase AND
  ``tests/products/test_d_impl_340_producer_admission.py::test_an_echo_of_a_different_question_refuses``;
* ``peered`` — ``xfail(strict=True)`` as **SEC-025-U1**: the A2A envelope
  (``ccf.peering.protocol::InboundProduct``) carries no question, so a peered
  child cannot echo one until SEC-022's signed claim set adds it. Strict, so
  the day it is fixed this goes red and the marker must be removed.

And the positive control: every child answers the asked subject, and the
composite serves.

The refusal name is the EXISTING ``question-mismatch``
(``ccf.products.composite::ChildRefusalReason``); no new name is introduced.
"""

from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any

import pytest

from ccf.products.composite import ChildAdmissionRefusal, CompositeAdmissionGate
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.dispatch import McpSkillRegistry

from tests.products.composite_fixture import (
    SERVER_NAME,
    _child_door,
    ask_composite,
    boot_composite,
    build_composite,
)
from tests.products.test_resolver_seam import ADMITTED_AT, _Booted

#: The subject the parent asks about, and the one a misrouted child answers.
ASKED = "acct-1"
OTHER = "acct-OTHER"

MCP_RESOURCE = "child-product"
MCP_URI = "ccf://fixture/child-product"


@contextlib.contextmanager
def _deployment(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    generator = boot_composite(tmp_path)
    booted = next(generator)
    try:
        yield booted
    finally:
        generator.close()


def _answering(subject: str) -> Any:
    """What the deployment's skill is handed: a child asked about ``subject``."""

    def arguments(requirement: Any, asked_at: datetime) -> Mapping[str, str]:
        return {"subject": subject, "asked_at": asked_at.isoformat(), "threshold": "1000"}

    return arguments


class _AdmissionSpy:
    """Records every verdict the shipped gate returns; changes none of them."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.verdicts: list[object] = []
        original = CompositeAdmissionGate.admit
        spy = self

        def admit(self_gate: CompositeAdmissionGate, **kwargs: Any) -> object:
            verdict = original(self_gate, **kwargs)
            spy.verdicts.append(verdict)
            return verdict

        monkeypatch.setattr(CompositeAdmissionGate, "admit", admit)


def _assert_refused_by_name(
    booted: _Booted, outcome: Any, spy: _AdmissionSpy, *, leg: str
) -> None:
    """The composite refused ``question-mismatch``, served nothing, named the leg and not B."""
    assert not isinstance(outcome, ServedProduct), (
        f"SEC-025: the parent asked {ASKED!r} and a {leg} child answering another"
        " subject was composed into a served product"
    )
    # No composite product: the replay record names no served product.
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(content_address=booted.store.resolve_uri(uri=outcome.replay_reference))
    )
    rows = record.content_generation_path.child_resolutions
    assert len(rows) == 1, rows
    assert rows[0].refusal_ref == "question-mismatch", (rows[0].refusal_ref, rows[0].outcome_status)
    assert rows[0].outcome_status == "rejected-at-admission"
    # The refusal object itself: by name, naming the leg, never the answered subject.
    refusals = [v for v in spy.verdicts if isinstance(v, ChildAdmissionRefusal)]
    assert len(refusals) == 1, spy.verdicts
    refusal = refusals[0]
    assert refusal.reason == "question-mismatch", refusal
    assert leg in refusal.detail, refusal.detail
    assert OTHER not in refusal.detail, refusal.detail
    # And nothing the caller receives carries the other subject either.
    assert OTHER not in outcome.model_dump_json()


def test_a_local_child_answering_another_subject_is_refused_by_name(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _deployment(tmp_path) as booted:
        spy = _AdmissionSpy(monkeypatch)
        resolver, _children = build_composite(booted, child_arguments=_answering(OTHER))
        _assert_refused_by_name(booted, ask_composite(resolver), spy, leg="local-dispatch")


class _OneResourceClient:
    """An MCP client whose one resource is the child door's answer for ``subject``."""

    def __init__(self, booted: _Booted, subject: str) -> None:
        self._answer = _child_door(booted)(_answering(subject)(None, _asked_at()))["outcome"]
        self.reads: list[str] = []

    def read_text(self, uri: str) -> str:
        self.reads.append(uri)
        return self._answer


def _asked_at() -> datetime:
    from tests.products.composite_fixture import ASKED_AT

    return ASKED_AT


def _mcp_composite(booted: _Booted, subject: str) -> tuple[Any, _OneResourceClient]:
    client = _OneResourceClient(booted, subject)
    mcp_skills = McpSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    mcp_skills.register(
        server=SERVER_NAME,
        client=client,  # type: ignore[arg-type]  # duck-typed: only read_text is used
        resources={MCP_RESOURCE: MCP_URI},
    )
    resolver, _children = build_composite(
        booted, binding="mcp", mcp_skills=mcp_skills, resource=MCP_RESOURCE
    )
    return resolver, client


def test_an_mcp_child_answering_another_subject_is_refused_by_name(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _deployment(tmp_path) as booted:
        spy = _AdmissionSpy(monkeypatch)
        resolver, client = _mcp_composite(booted, OTHER)
        outcome = ask_composite(resolver)
        assert client.reads == [MCP_URI], "the mcp leg did not execute"
        _assert_refused_by_name(booted, outcome, spy, leg="mcp")


def test_an_mcp_product_child_answering_another_subject_is_refused_by_name(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The shared-check control: refused before the repair, by the check every leg now shares."""
    from tests.products.test_d_impl_340_producer_admission import (
        DoorStub,
        ask,
        honest_assertion,
        wired,
    )
    from tests.products.provider_boot import serve_atomic_child
    from ccf.products.door import AnsweredQuestion, DoorOutcome

    answer = DoorOutcome.model_validate_json(serve_atomic_child(tmp_path / "producer"))
    assert answer.product_json is not None

    def other_subject(answered: AnsweredQuestion) -> AnsweredQuestion:
        return answered.model_copy(update={"subject": OTHER})

    with _deployment(tmp_path / "consumer") as booted:
        spy = _AdmissionSpy(monkeypatch)
        door = DoorStub(
            answer.product_json, assertion=honest_assertion(), answered_rewrite=other_subject
        )
        resolver = wired(booted, door)[0]
        _assert_refused_by_name(booted, ask(resolver), spy, leg="mcp-product")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "SEC-025-U1: a peered child is admitted without subject binding until"
        " SEC-022's envelope carries the question — the A2A envelope"
        " (ccf.peering.protocol::InboundProduct) carries no question to echo"
    ),
)
def test_a_peered_child_answering_another_subject_is_refused_by_name(
    tmp_path: pathlib.Path,
    provider: Any,
    public_key: Mapping[str, str],
) -> None:
    from tests.products import test_d364_peered_child_served_at as peered

    with _deployment(tmp_path) as booted:
        gate = peered._peering_gate(booted, provider, public_key, tmp_path)
        transport = peered._OnePeerTransport(
            peered._inbound(provider, peered._peered_product(expires_after=peered._VALID_FOR))
        )
        resolver = peered._resolver_over_two_legs(
            booted, peering_gate=gate, transport=transport
        )
        requirement = peered._requirements()[1]
        assert requirement.product_class == peered.PEERED_CLASS
        outcomes = resolver.resolve_for(
            requirements=(requirement,),
            request=ProductRequest(
                schema_name="fixture.manifest-product",
                schema_version="1.0.0",
                subject=ASKED,
                intent="fixture-intent",
                freshness="fixture-freshness",
                asked_at=peered.ASKED_AT,
                parameters={},
            ),
            asked_at=peered.ASKED_AT,
            admitted_at=peered.ADMITTED_AT,
            composition_invocation=peered.INVOCATION,
            consumer_lineage=peered.consumer_lineage(),
        )
        assert transport.receives == 1, "the peered leg did not execute"
        verdict = outcomes[peered.PEERED_CLASS]
        # The peered product names no subject at all, so it cannot be shown to
        # have answered the one asked; binding would refuse it by name.
        assert isinstance(verdict, ChildAdmissionRefusal), verdict
        assert verdict.reason == "question-mismatch", verdict


def test_every_child_answering_the_asked_subject_serves(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control: binding refuses the misrouted child, never the honest one."""
    with _deployment(tmp_path) as booted:
        spy = _AdmissionSpy(monkeypatch)
        resolver, _children = build_composite(booted, child_arguments=_answering(ASKED))
        outcome = ask_composite(resolver)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        assert not [v for v in spy.verdicts if isinstance(v, ChildAdmissionRefusal)]
    with _deployment(tmp_path / "mcp") as booted:
        resolver, client = _mcp_composite(booted, ASKED)
        outcome = ask_composite(resolver)
        assert client.reads == [MCP_URI]
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)


# The peering fixtures the xfail subcase reads (banking fixture values, CINV-01).
from tests.peering.test_admission_attributability import (  # noqa: E402,F401
    key_dir,
    provider,
    public_key,
)
