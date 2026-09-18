"""`D-IMPL-304` — a governed refusal that could not be RETURNED reaches the recorder, not the fault clause.

The typed handoff `GovernedRefusalRaised` is caught at exactly two kinds of
boundary — the delivery boundary of each door, and the governed resolver's
acquisition seam — recorded through the ONE recorder those boundaries already
hold, and delivered through the normal disclosure and emission path. These
controls drive the actual boundaries (a real `open_product` fixture tree, the
SDK's standard door over it in-process, the MCP tool and resource surfaces),
never merely the exception's construction, and they hold the four fault
families — programming, configuration, persistence, transport — to their
EXISTING opaque behavior: none acquires a fabricated governed record merely
because the new catch exists.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from ccf.deployment.environment import EnvironmentMissing
from ccf.products.provenance import EffectiveRequest
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.replay.record import NO_PRODUCT_ADDRESS, DecisionReplayRecord, ResolutionNotApplicable
from ccf.replay.serve import ServedProduct
from ccf_runtime.mcp.egress import ProductNotServable
from ccf_runtime.mcp.product_door import open_door
from tests.examples.test_cp_04_two_callers import _refusal_of, drive, tool_arguments, tool_call
from tests.products.test_paved_road import (  # noqa: F401 — `tree` is a fixture
    PRODUCT_CLASS,
    TENANT,
    _Acquire,
    _open,
    _question,
    tree,
)

TOKEN = {"PAVED_FIXTURE_TOKEN": "fixture-token"}
ISSUER = {"issuer_url": "https://issuer.example", "resource_server_url": "https://door.example/mcp"}


def _refusal() -> SubjectUnavailableRefusal:
    return SubjectUnavailableRefusal(cause="nonexistent", detail="the fixture holds no subject to read", error_code=None)


def _records(opened: Any) -> list[dict[str, Any]]:
    """Decision records in the opened product's ONE store, by class, never by file count."""
    found: list[dict[str, Any]] = []
    for path in sorted((opened.scratch / opened.replay.store_dirname).rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(document, dict) and "policy_bindings" in document:
            found.append(document)
    return found


def _resolution_of(document: dict[str, Any]) -> Any:
    resolution = document["policy_bindings"]["request_resolution"]
    return json.loads(resolution) if isinstance(resolution, str) else resolution


def _refusal_records(opened: Any) -> list[dict[str, Any]]:
    """The decision records that served no product — the refusals."""
    return [r for r in _records(opened) if r["content_generation_path"]["product_content_address"] == NO_PRODUCT_ADDRESS]


# --- construction ---------------------------------------------------------------------------


def test_the_handoff_requires_a_governed_refusal_and_an_explicit_resolution_state() -> None:
    """A handoff, not a wrapper: an arbitrary exception or value is refused at
    construction, and so is a missing or foreign resolution state — the marker
    is never manufactured from omission. It is not one of the four fault types."""
    with pytest.raises(TypeError, match="handoff for a determination"):
        GovernedRefusalRaised(ValueError("not a refusal"), resolution=RESOLVED_BY_THE_RESOLVER)
    with pytest.raises(TypeError, match="explicit resolution state"):
        GovernedRefusalRaised(_refusal(), resolution=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        GovernedRefusalRaised(_refusal())  # type: ignore[call-arg]
    raised = GovernedRefusalRaised(_refusal(), resolution=ResolutionNotApplicable(reason="refused-before-resolution"))
    assert not isinstance(raised, (ValueError, TypeError, LookupError, OSError))
    assert "subject-unavailable" in str(raised)


# --- the acquisition seam ---------------------------------------------------------------------


class _RaisingAcquire:
    def __init__(self, exception: Any) -> None:
        self._exception = exception
        self.calls = 0

    def __call__(self, context: Any) -> tuple[Any, ...]:
        self.calls += 1
        raise self._exception


def test_a_refusal_raised_at_the_acquisition_seam_is_recorded_with_the_resolvers_own_evidence(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """The seam stated RESOLVED_BY_THE_RESOLVER; the resolver records its own
    completed resolution as dimension 2 — never a marker — through its one
    minting seam, and returns the refusal AS DATA with a replay reference.
    No product, no fabric read, no second call to the seam."""
    root, scratch = tree
    acquire = _RaisingAcquire(GovernedRefusalRaised(_refusal(), resolution=RESOLVED_BY_THE_RESOLVER))
    with _open(root, scratch, acquire=acquire) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert outcome.kind == "subject-unavailable" and outcome.replay_reference != NO_REPLAY_REFERENCE
        record = opened.record_of(outcome)
        records = _records(opened)
    assert acquire.calls == 1 and len(records) == 1
    resolution = record.policy_bindings.request_resolution
    effective = EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution
    assert isinstance(effective, EffectiveRequest), "dimension 2 is the resolver's evidence, not a marker"
    assert effective.values(), "the completed resolution, with its effective values"
    assert record.content_generation_path.product_content_address == NO_PRODUCT_ADDRESS
    assert not record.context_fabric_snapshot.touched_entities


def test_the_seam_refuses_a_not_applicable_marker_as_the_contradiction_it_is(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Resolution DID run before the seam; a raiser stating otherwise is a
    programming error, surfaced loudly rather than recorded as a false statement."""
    root, scratch = tree
    acquire = _RaisingAcquire(GovernedRefusalRaised(_refusal(), resolution=ResolutionNotApplicable(reason="refused-before-resolution")))
    with _open(root, scratch, acquire=acquire) as opened, pytest.raises(TypeError, match="resolved the effective request before"):
        opened.answer(_question(opened))
    assert acquire.calls == 1


@pytest.mark.parametrize("fault", [ValueError("a programming fault"), TypeError("a programming fault"), EnvironmentMissing("a configuration fault"), OSError("a persistence fault")])
def test_a_fault_raised_at_the_acquisition_seam_still_propagates_untouched(tree: tuple[pathlib.Path, pathlib.Path], fault: Exception) -> None:
    """Only the typed handoff is caught; every other exception the seam raises
    reaches the caller exactly as before, and nothing is recorded for it."""
    root, scratch = tree
    acquire = _RaisingAcquire(fault)
    with _open(root, scratch, acquire=acquire) as opened, pytest.raises(type(fault)):
        opened.answer(_question(opened))
    assert acquire.calls == 1


def test_the_successful_path_through_the_seam_is_unchanged(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """A seam that raises nothing serves exactly as before: one product, one record."""
    root, scratch = tree
    with _open(root, scratch, acquire=_Acquire()) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct)
        assert len(_records(opened)) == 1


# --- the standard door -------------------------------------------------------------------------


def _conformer(opened: Any, *, resolve: Any, recorder: Any = None) -> SimpleNamespace:
    """A structural `ServesProducts` over the opened product, with `resolve` (and optionally the recorder) replaced."""
    return SimpleNamespace(
        tenant_id=opened.tenant_id, declaration=opened.declaration, default_perspective=opened.default_perspective,
        control_plane=opened.control_plane, refusal_recorder=recorder if recorder is not None else opened.refusal_recorder,
        door=opened.door, environment=opened.environment, resolve=resolve,
    )


def _drive_tool(opened: Any, conformer: SimpleNamespace, *, question: Any) -> tuple[bool, str]:
    door = open_door(conformer, environ=TOKEN)
    shim = SimpleNamespace(server=door.server(**ISSUER), credential=door.credential)
    return drive(shim, {"q": tool_call(tool_arguments(tenant=TENANT, typed=question))})["q"]


def _raising(exception_for: Any) -> Any:
    def resolve(*, tenant: str, product_class: str, version: str, perspective: Any, request: Any) -> Any:
        raise exception_for(request)

    return resolve


def _effective_evidence(opened: Any) -> EffectiveRequest:
    """A real, completed EffectiveRequest — read off a served decision's record."""
    served = opened.answer(_question(opened))
    assert isinstance(served, ServedProduct)
    resolution = opened.record_of(served).policy_bindings.request_resolution
    return EffectiveRequest.model_validate_json(resolution) if isinstance(resolution, str) else resolution


def test_a_refusal_raised_to_the_door_is_recorded_at_the_questions_instant_and_delivered_as_a_governed_refusal(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """T1: the tool answers a governed refusal (kind, replay reference, no
    product); exactly one record is appended through the door's own recorder,
    stamped at the question's instant, with dimension 2 = the raised evidence."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        evidence = _effective_evidence(opened)
        before = len(_records(opened))
        question = _question(opened)
        is_error, text = _drive_tool(opened, _conformer(opened, resolve=_raising(lambda request: GovernedRefusalRaised(_refusal(), resolution=evidence))), question=question)
        records = _records(opened)
    assert not is_error, text
    body = json.loads(text)
    assert body["product_json"] is None and body["replay_ref"]
    assert _refusal_of(text)["kind"] == "subject-unavailable"
    assert len(records) == before + 1
    refused = [r for r in records if r["content_generation_path"]["product_content_address"] == NO_PRODUCT_ADDRESS]
    assert len(refused) == 1
    assert EffectiveRequest.model_validate(_resolution_of(refused[0])) == evidence, "dimension 2 carries the raised evidence, not a marker"
    assert datetime.fromisoformat(refused[0]["recorded_at"].replace("Z", "+00:00")) == question.asked_at, "stamped at the question's instant"


def test_a_refusal_raised_to_the_door_with_an_explicit_marker_is_recorded_with_that_marker(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """T2: the explicit not-applicable state is recorded as stated."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        before = len(_records(opened))
        is_error, text = _drive_tool(
            opened, _conformer(opened, resolve=_raising(lambda request: GovernedRefusalRaised(_refusal(), resolution=ResolutionNotApplicable(reason="refused-before-resolution")))),
            question=_question(opened),
        )
        records = _records(opened)
    assert not is_error and _refusal_of(text)["kind"] == "subject-unavailable"
    assert len(records) == before + 1
    refused = [r for r in records if r["content_generation_path"]["product_content_address"] == NO_PRODUCT_ADDRESS]
    assert len(refused) == 1 and _resolution_of(refused[0])["reason"] == "refused-before-resolution"


def test_an_already_recorded_envelope_raised_to_the_door_passes_through_without_a_second_record(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """T3: a recorded envelope (it carries a replay reference) is delivered as is; one record, not two."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        recorded = opened.resolve(tenant=TENANT, product_class=PRODUCT_CLASS, version="9.9.9", perspective=opened.default_perspective, request=_question(opened))
        assert isinstance(recorded, RefusalEnvelope) and recorded.replay_reference != NO_REPLAY_REFERENCE
        before = len(_records(opened))
        is_error, text = _drive_tool(opened, _conformer(opened, resolve=_raising(lambda request: GovernedRefusalRaised(recorded, resolution=ResolutionNotApplicable(reason="refused-before-resolution")))), question=_question(opened))
        after = len(_records(opened))
    assert not is_error and json.loads(text)["replay_ref"] == recorded.replay_reference
    assert after == before


@pytest.mark.parametrize(
    "fault,family",
    [(TypeError("a programming fault"), "programming"), (ValueError("a programming fault"), "programming"), (EnvironmentMissing("a configuration fault"), "configuration"), (OSError("a persistence fault"), "persistence")],
)
def test_a_fault_raised_to_the_door_stays_an_opaque_runtime_failure_with_no_record(tree: tuple[pathlib.Path, pathlib.Path], fault: Exception, family: str) -> None:
    """T4–T6: the four fault families keep their existing opaque behavior and
    acquire no fabricated governed record because the typed catch exists."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        before = len(_records(opened))
        is_error, text = _drive_tool(opened, _conformer(opened, resolve=_raising(lambda request: fault)), question=_question(opened))
        after = len(_records(opened))
    assert is_error and "ccf-runtime-failure" in text, (family, text)
    assert after == before


def test_a_handoff_whose_recording_fails_is_a_failure_and_no_refusal_escapes(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """T6, the persistence half: the recorder's store raises while recording the
    handoff — the door reports a runtime failure; nothing governed crosses."""
    root, scratch = tree

    class _Broken:
        def record(self, *args: Any, **kwargs: Any) -> Any:
            raise OSError("the store is unavailable")

    with _open(root, scratch) as opened:
        before = len(_records(opened))
        is_error, text = _drive_tool(
            opened, _conformer(opened, resolve=_raising(lambda request: GovernedRefusalRaised(_refusal(), resolution=ResolutionNotApplicable(reason="refused-before-resolution"))), recorder=_Broken()),
            question=_question(opened),
        )
        after = len(_records(opened))
    assert is_error and "ccf-runtime-failure" in text
    assert after == before


def test_a_handoff_stating_resolved_by_the_resolver_at_a_door_is_a_programming_error(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """A door holds no resolver evidence and manufactures none: the seam-only
    state reaching a door is a fault, reported opaquely, recording nothing."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        before = len(_records(opened))
        is_error, text = _drive_tool(opened, _conformer(opened, resolve=_raising(lambda request: GovernedRefusalRaised(_refusal(), resolution=RESOLVED_BY_THE_RESOLVER))), question=_question(opened))
        after = len(_records(opened))
    assert is_error and "ccf-runtime-failure" in text
    assert after == before


def test_the_typed_absence_still_governs_as_before(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """T8: `ProductNotServable` keeps its own recorded determination; the new catch changes nothing there."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        before = len(_records(opened))
        is_error, text = _drive_tool(opened, _conformer(opened, resolve=_raising(lambda request: ProductNotServable("nothing servable here"))), question=_question(opened))
        after = len(_records(opened))
    assert not is_error and _refusal_of(text)["kind"] == "subject-unavailable" and json.loads(text)["replay_ref"]
    assert after == before + 1
