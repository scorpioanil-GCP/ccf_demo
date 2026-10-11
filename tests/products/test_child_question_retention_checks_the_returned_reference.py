# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A composite records only the reference of the child question it filed (``D-IMPL-378`` decision 5 (a)).

Dave, 2026-10-09 16:38 MST, adopting Grok's recommendation on the "j" batch's decision 5, verbatim: *"(a) Fix
the four writers in one small lane."* Decision 5 (a) itself (06:06 MST, confirmed at 06:21 MST), verbatim:
*"Verify the returned record address against the record actually written."* It was built for
``src/ccf/replay/serve.py::ReplayWriter.write_replay_record``; this module holds its neighbor
``src/ccf/products/child_resolver.py::QuestionBoundChildResolver`` to the same rule.

Before a question-bound composite asks a producer anything, it files the question's identity bytes on the
parent's own store (``D-IMPL-342`` / ``CP14-F-35``) and records the reference the store answers in the parent's
replay record, as ``ChildResolution.child_question_ref``. The resolver held the store's answer's content address
to the question's address, with ``!=``, and recorded its URI unchecked; the record's validator
(``src/ccf/replay/record.py::ChildResolution``) checks only that an address comes with it. The small lane found it
by reading the code; this module measures it on ``dl-378-integ`` @ ``6cd6023e``: a parent store answering the
question's write with the right address and another question's URI had that URI recorded. Replay's audit read of
that row (``src/ccf/replay/engine.py::retained_child_question``) then raised ``ReplayDivergence`` (a lane probe),
and a filed record is immutable, so it keeps that divergence.

What the resolver knows before the store answers (``D-IMPL-26``): the question's address is the content hash of
its identity bytes, the name is that address, the tenant is its capability's (held equal to the gate's), the
class is ``ccf.child-question``, and the URI is ``ccf-artifact://{tenant}/{class}/{address}@{address}``.

What is asserted, by mechanism:

1. **The hole as evidenced.** A parent store that answers the question's write with the question's own address
   and another (genuinely filed) question's URI is refused by name (``ChildQuestionReferenceMismatch``); the
   producer is never asked and no replay record is appended.
2. **Every field of the reference.** One field of the question's reference answered as another question's (the
   address, the URI, the name) or as another tenant's or class's is refused by name; so is a changed field carried
   in a ``str`` subclass that claims to equal the question's own.
3. **Control.** An honest parent store's reference is recorded, and it is the question's own.

The refusal is asserted by its class NAME as a string, so a tree without the check fails each test on its
behavior (the reference recorded, or the refusal raised under another name), never on an import. Fixture
vocabulary only (CINV-01).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreProtocol, artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import MCP_PRODUCER, parse_artifact
from ccf.products.child_resolver import QuestionBoundChildResolver
from ccf.products.composite import CHILD_QUESTION_CLASS, CompositeAdmissionGate
from ccf.products.resolver import GovernedResolver
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.callables import CallableRegistry
from ccf.skills.dispatch import ChildQuestionIdentity, McpSkillRegistry
from ccf.skills.producers import producer_registration_from_artifact
from tests.composition import composition_replay_mint
from tests.products.test_d_impl_340_producer_admission import (  # noqa: F401 — pytest fixtures, used by name
    DoorStub,
    ask,
    booted,
    honest_assertion,
    ledger_for_product_ask,
    producer_document,
    questions,
    row_of,
    vessel,
)
from tests.products.test_resolver_seam import ADMITTED_AT, ASKED_AT, TENANT, _arguments, _Booted

#: The refusal this check raises, by name (absent on a tree without the check).
REFUSAL = "ChildQuestionReferenceMismatch"

#: The one field each lying store changes, and the foreign value it answers with.
#: ``None`` means "the other question's value for that field".
FIELDS: dict[str, str | None] = {
    "content_address": None,
    "uri": None,
    "name": None,
    "tenant_id": "another-tenant",
    "artifact_class": "another-question-class",
}


def _question_ref(address: str) -> ArtifactRef:
    """The reference of the question at ``address`` filed under this fixture's tenant, per D-IMPL-26."""
    return ArtifactRef(
        content_address=address,
        uri=artifact_uri(tenant_id=TENANT, artifact_class=CHILD_QUESTION_CLASS, name=address, artifact_version=address),
        tenant_id=TENANT,
        artifact_class=CHILD_QUESTION_CLASS,
        name=address,
    )


def _another_questions_ref() -> ArtifactRef:
    """The reference another question would have: its own identity bytes, under the same tenant and class."""
    identity = ChildQuestionIdentity(
        asked_at=ASKED_AT,
        freshness="another-freshness",
        intent="another-intent",
        request="{}",
        subject="another-subject",
    )
    return _question_ref(content_hash(identity))


class _AnswersWith:
    """A parent store that files every write faithfully through ``inner`` and answers with ``answer(the honest ref)``.

    A buggy or hostile artifact server whose bytes are right and whose reference is not. Reads delegate unchanged.
    The question-bound resolver's one write to this store is the child question's retention.
    """

    def __init__(self, inner: ArtifactStoreProtocol, answer: Callable[[ArtifactRef], ArtifactRef]) -> None:
        self._inner = inner
        self._answer = answer
        self.filed: list[ArtifactRef] = []

    def put(self, authorized: Any, artifact: Any) -> ArtifactRef:
        honest = self._inner.put(authorized, artifact)
        self.filed.append(honest)
        return self._answer(honest)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _ClaimsEquality(str):
    """A ``str`` whose equality answers for itself: equal to anything, unequal to nothing."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    __hash__ = str.__hash__


def _wired(booted: _Booted, door: DoorStub, *, parent_store: ArtifactStoreProtocol) -> GovernedResolver:
    """``tests/products/test_d_impl_340_producer_admission.py::wired``, with the child resolver's store chosen here.

    The governed resolver records its replay records on ``booted.store`` directly; only the question-bound
    resolver, which files each child question before asking its producer, is handed ``parent_store``.
    """
    registry = McpSkillRegistry(audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT)
    registry.register_producer(
        client=door,  # type: ignore[arg-type]  # duck-typed: only call_tool_text is used
        registration=producer_registration_from_artifact(parse_artifact(producer_document(), MCP_PRODUCER)),
    )
    ledger, agent_hash = ledger_for_product_ask(booted)
    children = QuestionBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=CompositeAdmissionGate(
            tenant_id=TENANT, consumer_scope="consumer://d-impl-340", registry=booted.control_plane
        ),
        authorized=composition_replay_mint(booted.control_plane, tenant=TENANT, artifact_class=CHILD_QUESTION_CLASS),
        child_questions=questions,
        callable_registry=CallableRegistry(),
        artifact_store=parent_store,
        mcp_skills=registry,
    )
    arguments = _arguments(booted)
    arguments.update(composite_children=children)
    return GovernedResolver(**arguments)


def _outcome(call: Callable[[], Any]) -> Any:
    """What the call returned, or the exception it raised instead."""
    try:
        return call()
    except Exception as raised:  # noqa: BLE001 — judged by its type's name below, never by its text
        return raised


def _artifacts(booted: _Booted) -> set[str]:
    """Every content address the deployment's store holds."""
    return {path.name for path in booted.store.root.iterdir() if len(path.name) == 64}


def _records_among(booted: _Booted, addresses: set[str]) -> list[str]:
    """The addresses among ``addresses`` whose bytes are a decision replay record."""
    found = []
    for address in sorted(addresses):
        try:
            DecisionReplayRecord.model_validate_json(booted.store.get(content_address=address))
        except ValueError:
            continue
        found.append(address)
    return found


def _assert_refused_by_name(
    outcome: Any, *, booted: _Booted, door: DoorStub, before: set[str], case: str
) -> None:
    """Nothing was recorded and the producer was never asked; the refusal is the check's own, by its type's name."""
    if not isinstance(outcome, Exception):
        row = row_of(booted, outcome)
        own = _question_ref(row.child_question_address)
        pytest.fail(
            f"[{case}] the composite answered ({type(outcome).__name__}) and its replay record holds"
            f" child_question_ref={row.child_question_ref} for the question at {row.child_question_address};"
            f" the question's own reference is {own.uri}; the recorded reference is the question's own:"
            f" {row.child_question_ref == own.uri}"
        )
    assert any(klass.__name__ == REFUSAL for klass in type(outcome).__mro__), (
        f"[{case}] refused, but not by the returned-reference check ({REFUSAL}): {type(outcome).__name__}: {outcome}"
    )
    assert door.calls == [], f"[{case}] the producer was asked after the parent store's answer was refused"
    appended = _records_among(booted, _artifacts(booted) - before)
    assert appended == [], f"[{case}] a replay record was appended after the refusal: {appended}"


# --- 1. the hole as evidenced: right address, another question's URI ---------------------------


def test_a_parent_store_answering_another_questions_uri_is_refused_by_name(booted: _Booted, vessel: str) -> None:
    """The small lane's repro: the right address, and the URI of a question the store genuinely holds.

    The first question is asked through an honest parent store, so its reference is one the store really answered.
    The second, different question is then asked through a store that files it faithfully and answers its own
    address with the first question's URI. Measured on ``6cd6023e``: the second answer's record carried the first
    question's URI.
    """
    first_door = DoorStub(vessel, assertion=honest_assertion())
    first = ask(_wired(booted, first_door, parent_store=booted.store), threshold=1000)
    assert isinstance(first, ServedProduct), f"the case was not constructed: the honest ask must answer: {first}"
    first_row = row_of(booted, first)
    assert first_row.child_question_ref == _question_ref(first_row.child_question_address).uri

    lying = _AnswersWith(booted.store, lambda honest: honest.model_copy(update={"uri": first_row.child_question_ref}))
    door = DoorStub(vessel, assertion=honest_assertion())
    before = _artifacts(booted)
    outcome = _outcome(lambda: ask(_wired(booted, door, parent_store=lying), threshold=2000))

    assert len(lying.filed) == 1 and lying.filed[0].content_address != first_row.child_question_address, (
        "the case was not constructed: the lying store must have filed a second, different question"
    )
    _assert_refused_by_name(outcome, booted=booted, door=door, before=before, case="another question's URI")


# --- 2. every field of the returned reference ------------------------------------------------


def _one_field_changed(field: str, *, foreign: ArtifactRef) -> Callable[[ArtifactRef], ArtifactRef]:
    value = FIELDS[field]
    replacement = getattr(foreign, field) if value is None else value
    return lambda honest: honest.model_copy(update={field: replacement})


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_with_any_field_not_the_questions_own_is_refused_by_name(
    booted: _Booted, vessel: str, field: str
) -> None:
    """One field of the question's reference answered as another question's (or another tenant's, or class's)."""
    lying = _AnswersWith(booted.store, _one_field_changed(field, foreign=_another_questions_ref()))
    door = DoorStub(vessel, assertion=honest_assertion())
    before = _artifacts(booted)

    outcome = _outcome(lambda: ask(_wired(booted, door, parent_store=lying)))

    assert len(lying.filed) == 1, "the case was not constructed: the store must have filed the question"
    assert lying.filed[0] == _question_ref(lying.filed[0].content_address), (
        "the case was not constructed: the store must have filed the question under its own reference"
    )
    _assert_refused_by_name(outcome, booted=booted, door=door, before=before, case=f"one field, {field}")


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_a_reference_field_that_only_claims_equality_is_refused_by_name(
    booted: _Booted, vessel: str, field: str
) -> None:
    """Another question's value in one field, carried in a ``str`` subclass that says it equals the question's own.

    The comparison reads the type first, so the claim is not taken: the field differs, and the resolver refuses by
    name rather than recording anything.
    """
    value = FIELDS[field]
    disguised = _ClaimsEquality(getattr(_another_questions_ref(), field) if value is None else value)
    lying = _AnswersWith(booted.store, lambda honest: honest.model_construct(**{**dict(honest), field: disguised}))
    door = DoorStub(vessel, assertion=honest_assertion())
    before = _artifacts(booted)

    outcome = _outcome(lambda: ask(_wired(booted, door, parent_store=lying)))

    assert disguised == getattr(lying.filed[0], field), "the case was not constructed: the value must claim equality"
    _assert_refused_by_name(outcome, booted=booted, door=door, before=before, case=f"claimed equality, {field}")


# --- 3. control -------------------------------------------------------------------------------


def test_control_an_honest_parent_stores_reference_is_recorded_and_is_the_questions_own(
    booted: _Booted, vessel: str
) -> None:
    """The deployment's file store answers exactly the question's own reference, and the record holds it."""
    door = DoorStub(vessel, assertion=honest_assertion())
    outcome = ask(_wired(booted, door, parent_store=booted.store))
    assert isinstance(outcome, ServedProduct), outcome
    row = row_of(booted, outcome)
    assert row.child_question_ref == _question_ref(row.child_question_address).uri, row.child_question_ref
    assert booted.store.resolve_uri(uri=row.child_question_ref) == row.child_question_address
    assert len(door.calls) == 1
