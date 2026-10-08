"""SEC-020 residuals P3 and P4: child arguments, and a question's store booted again (``D-IMPL-378``).

**Candidates, not rulings.** Dave has not ruled P3 or P4; these tests measure
the design lane's recommended option (a) of each, built on lane
``378d-s020next``. SEC-020 stays OPEN: nothing here closes it.

* **P3 (a), child arguments (Q8).** The design lane's residual, measured on
  ``ca1195e6``: *"Child arguments derived from state the deployment captured
  itself still ask the child about the withheld subject. The composite is then
  refused (``question-mismatch``) where a nonexistent subject is served."* The
  option: the child-arguments mapping is handed the request its composite asks
  the children about, so a mapping needs no state of its own to know the
  subject. Under the early policy that request carries the declared
  undisclosed subject in place of a withheld one (Q8: *"before ...
  child resolution"*; Q10: the stand-in replaces the subject and is never
  fetched beside it).
* **P4 (a), a question's store (Q9).** The design lane's residual, measured on
  ``ca1195e6``: *"A question's store reopened plainly and asked through a
  resolver with no acquisition phase still shows what the withheld subject's
  question fetched ... Q9 binds only where acquisition exists."* The option: a
  boot for one question leaves a durable marker beside the store, and any
  later serve from that store is refused by name; Decision Replay, which
  rebuilds the resolver without calling it, reads the store as before. The
  same handle asked again with no acquisition phase is the in-process twin of
  that residual (``probe_q9_same_handle_without_acquisition.py``, this lane):
  a question fabric answers one governed call.

Equality is the controls' standard
(``tests/products/test_withheld_is_indistinguishable_from_absent.py``):
served-or-refused first, then the vessel path for path, or the refusal shell
in every member but its own ``replay_reference``. Every domain value here is
fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.deployment import load_and_boot, load_config_and_boot
from ccf.products.request import ProductRequest
from ccf.products.resolver import ProductNotResolvable, build_governed_resolver
from ccf.replay.engine import replay
from ccf.replay.environment import RecordedEnvironment
from ccf.replay.serve import ServedProduct
from tests.products import composite_fixture as cf
from tests.products import test_withheld_subject_population_composite_and_fabric as m

sec020 = m.sec020

# --- P3: the child-arguments mapping, handed the request ----------------------------


class _ReadsWhatItIsHanded:
    """A deployment's child-arguments mapping: the child is asked about the subject the mapping is handed.

    Handed the asked request, it reads the subject and the instant off it. A
    tree whose mapping is handed only the instant gives it no subject to read,
    so there the subject can only come from what the deployment captured of
    the caller's question itself (``captured``): the shape the residual was
    measured on (``probe_closure_child_args_tip.py``).
    """

    def __init__(self, *, captured: str) -> None:
        self.captured = captured
        self.handed: list[object] = []

    def __call__(self, requirement: Any, handed: Any) -> Mapping[str, str]:
        self.handed.append(handed)
        if isinstance(handed, ProductRequest):
            subject, asked_at = handed.subject, handed.asked_at
        else:
            subject, asked_at = self.captured, handed
        return {"subject": subject, "asked_at": asked_at.isoformat(), "threshold": "1000"}


def _ask_composite(
    tmp_path: pathlib.Path,
    subject: str,
    *,
    child_anchor: str,
    mapping: Callable[..., Mapping[str, str]],
    questions: Callable[..., Any] | None = None,
) -> tuple[Any, list[str]]:
    """The design lane's probe, as a fixture: an early-withholding composite over a local child door.

    The child resolver is the SDK's ``GrantBoundChildResolver`` as
    ``build_composite`` wires it, handed ``mapping`` and nothing that wraps it.
    Returns the composite's outcome and the subjects its child door was asked.
    """
    parent = m._composite_boot(tmp_path / "parent", child_anchor=child_anchor)
    child_own = m._composite_boot(tmp_path / "child", child_anchor=child_anchor, ingest_batch=False, for_question=True)
    child = m._Booted(fabric=child_own.fabric, control_plane=child_own.control_plane, store=parent.store, root=child_own.root)
    asked: list[str] = []
    try:
        built, _granted = cf.build_composite(
            parent,
            child_door=m._child_door(child, asked=asked, observed=m.CHILD_OBSERVED[child_anchor]),
            child_arguments=mapping,
            child_questions=questions,
        )
        composite = dataclasses.replace(built, plan_factory=m._early())
        outcome = composite(
            tenant=m.TENANT, product_class=m.PRODUCT_CLASS, version=m.PRODUCT_VERSION, perspective=m.PERSPECTIVE,
            request=ProductRequest(
                schema_name=m.PRODUCT_CLASS, schema_version=m.PRODUCT_VERSION, subject=subject,
                intent="fixture-intent", freshness="fixture-freshness", asked_at=m.ASKED_AT,
                parameters={m.THRESHOLD_PARAMETER: 1000},
            ),
        )
    finally:
        parent.fabric.handle.close()
        child.fabric.handle.close()
    return outcome, asked


def _tail(subjects: Sequence[str]) -> list[str]:
    return [subject[-8:] for subject in subjects]


@pytest.mark.parametrize("name", ["withheld", "nonexistent"])
def test_p3_the_child_arguments_mapping_is_handed_the_request_its_child_is_asked_about(
    tmp_path: pathlib.Path, name: str
) -> None:
    """The mechanism, by name: the mapping is handed the request the child's question is minted from.

    The same request ``child_questions`` is handed — one request per child, so
    the arguments the child is dispatched with and the question its answer is
    held to come from one place. For a subject the early policy does not
    disclose, that request names the declared undisclosed subject; for any
    other, the caller's own subject.
    """
    subject = m.COMPOSITE_WITHHELD if name == "withheld" else m.COMPOSITE_MISSING
    mapping = _ReadsWhatItIsHanded(captured=subject)
    questioned: list[ProductRequest] = []

    def questions(requirement: Any, request: ProductRequest) -> Any:
        questioned.append(request)
        return cf.asks_its_own_subject(requirement, request)

    _outcome, _asked = _ask_composite(
        tmp_path / name, subject, child_anchor=m.FROM_DECISION, mapping=mapping, questions=questions
    )
    handed = [type(value).__name__ for value in mapping.handed]
    assert handed == ["ProductRequest"], (
        f"[{name}] the child-arguments mapping must be handed the request the composite asks its child"
        f" about; it was handed {handed}"
    )
    assert mapping.handed == questioned, (
        f"[{name}] the mapping and the child's question must be handed one request: {mapping.handed} != {questioned}"
    )
    expected = m.UNDISCLOSED if name == "withheld" else m.COMPOSITE_MISSING
    request = mapping.handed[0]
    assert isinstance(request, ProductRequest)
    assert request.subject == expected and request.asked_at == m.ASKED_AT, (
        f"[{name}] the request handed names {request.subject[-8:]} at {request.asked_at}; expected"
        f" {expected[-8:]} at {m.ASKED_AT}"
    )


@pytest.mark.parametrize("child_anchor", [m.FROM_DECISION, m.FROM_ENTITY_FRESHNESS])
def test_p3_a_withheld_composite_whose_mapping_reads_what_it_is_handed_composes_as_a_nonexistent_one(
    tmp_path: pathlib.Path, child_anchor: str
) -> None:
    """The residual as the design lane worded it, as a test: both child anchors.

    A mapping that takes the child's subject from what it is handed. The
    withheld composite's child must be asked about the declared undisclosed
    subject — never the withheld one — and the two composites must be served
    or refused alike, member for member.
    """
    outcomes: dict[str, Any] = {}
    asks: dict[str, list[str]] = {}
    for name, subject in (("withheld", m.COMPOSITE_WITHHELD), ("nonexistent", m.COMPOSITE_MISSING)):
        outcomes[name], asks[name] = _ask_composite(
            tmp_path / name, subject, child_anchor=child_anchor, mapping=_ReadsWhatItIsHanded(captured=subject)
        )
    case = (
        f"composite, child arguments from the mapping, child anchor {child_anchor}; the child was asked"
        f" {_tail(asks['withheld'])} (withheld) and {_tail(asks['nonexistent'])} (nonexistent)"
    )
    assert asks["nonexistent"] == [m.COMPOSITE_MISSING], f"[{case}] the case was not constructed"
    m._assert_indistinguishable(outcomes["withheld"], outcomes["nonexistent"], case=case)
    assert asks["withheld"] == [m.UNDISCLOSED], (
        f"[{case}] the withheld composite's child must be asked about the declared undisclosed subject,"
        " never the withheld one"
    )


# --- P4: a question's store answers one governed call -------------------------------


def _first_question(booted: Any, subject: str) -> int:
    """The question the store was booted for, asked with its acquisition seam; returns what the seam ingested."""
    first = m._RefreshWhenAsked(booted[0])
    m._ask(m._governed(booted, plan_factory=m._late(), acquisition=first), subject)
    return first.ingested


def _later(booted: Any) -> Any:
    """A later question about an identifier that names nothing, through a resolver with NO acquisition phase."""
    try:
        return m._ask(m._governed(booted, plan_factory=m._late(), acquisition=None), sec020.MISSING)
    except ProductNotResolvable as raised:
        return raised


def _refused_by_name(outcomes: Mapping[str, Any], name: str, *, case: str) -> None:
    """Every later serve refused by ``name``; or, if anything was answered, what that answer revealed.

    ``untouched``'s first question named an identifier the source does not
    hold (nothing was acquired); ``planted``'s named the withheld subject,
    whose source returned a fresher claim. The comparison of the two later
    answers is what a caller could have seen, and it is printed when either
    store answered.
    """
    answered = {key: type(value).__name__ for key, value in outcomes.items() if not isinstance(value, ProductNotResolvable)}
    if answered:
        try:
            m._assert_indistinguishable(outcomes["planted"], outcomes["untouched"], case=case)
            seen = "the two later answers matched"
        except (AssertionError, KeyError) as unequal:
            seen = str(unequal).splitlines()[0]
        pytest.fail(
            f"[{case}] a later serve was answered ({answered}); it must be refused by name ({name})."
            f" Compared with a store whose first question acquired nothing: {seen}"
        )
    for key, value in outcomes.items():
        assert m._named(value, name), f"[{case}] the {key} store's later serve was refused for another reason: {value!r}"
    assert str(outcomes["planted"]) == str(outcomes["untouched"]), (
        f"[{case}] the refusal must read nothing about what the store holds"
    )


@pytest.mark.parametrize("anchor", [m.FROM_DECISION, m.FROM_ENTITY_FRESHNESS])
def test_p4_a_question_store_booted_again_refuses_every_later_serve_by_name(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """The residual as the design lane worded it: the store booted again, plainly, and asked with no acquisition.

    Each store is booted for its one question, asked it through an
    acquisition seam, and closed — as the paved road leaves a question's store
    on disk. Booted again without ``for_question`` (the way the replay road and
    a deployment keeping its graph reopen it), a governed call over it is
    refused by name, before anything is read, whatever its first question
    acquired.
    """
    outcomes: dict[str, Any] = {}
    for name, first_subject in (("untouched", sec020.MISSING), ("planted", sec020.WITHHELD)):
        booted = m._boot(tmp_path, name, anchor=anchor, envelopes=m._base_accounts(), for_question=True)
        try:
            ingested = _first_question(booted, first_subject)
        finally:
            booted[0].handle.close()
        assert ingested == (1 if name == "planted" else 0), f"[{anchor}, {name}] the case was not constructed: {ingested}"
        fabric = load_and_boot(
            tmp_path / name / "manifest.yaml",
            registry=booted[1],
            connection={"database_path": str(tmp_path / name / "graph.sqlite3")},
        )
        try:
            outcomes[name] = _later((fabric, booted[1], booted[2]))
        finally:
            fabric.handle.close()
    _refused_by_name(outcomes, "QuestionStoreReopened", case=f"{anchor}, a question's store booted again")


@pytest.mark.parametrize("anchor", [m.FROM_DECISION, m.FROM_ENTITY_FRESHNESS])
def test_p4_a_question_fabric_refuses_a_later_serve_with_no_acquisition_phase(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """The in-process twin: the SAME handle, asked again through a resolver with no acquisition phase.

    Q9's claim was taken by the first question's acquisition; a later governed
    call that declares no acquisition never reached the claim, so it answered
    from what the first question fetched. A question fabric answers one
    governed call: the later one is refused by name.
    """
    outcomes: dict[str, Any] = {}
    for name, first_subject in (("untouched", sec020.MISSING), ("planted", sec020.WITHHELD)):
        booted = m._boot(tmp_path, name, anchor=anchor, envelopes=m._base_accounts(), for_question=True)
        try:
            ingested = _first_question(booted, first_subject)
            outcomes[name] = _later(booted)
        finally:
            booted[0].handle.close()
        assert ingested == (1 if name == "planted" else 0), f"[{anchor}, {name}] the case was not constructed: {ingested}"
    _refused_by_name(outcomes, "AcquiredFabricReused", case=f"{anchor}, the same question fabric asked again")


@pytest.mark.parametrize("read_only", [False, True], ids=["writer-boot", "read-only-boot"])
@pytest.mark.parametrize("subject", [sec020.PAVED_WITHHELD, sec020.PAVED_ABSENT], ids=["early-withheld", "never-acquired"])
def test_p4_a_question_store_booted_again_replays_its_own_record_and_serves_nothing(
    tmp_path: pathlib.Path, subject: str, read_only: bool
) -> None:
    """Decision Replay over a question's store is unaffected; a serve from the same reopened store is refused.

    The paved road answers on a store it mints and boots for the question,
    then closes it. The replay road reopens that store and rebuilds the
    resolver through ``RecordedEnvironment`` without calling it: the record
    replays to its own address. The same reopened fabric, asked to serve, is
    refused by name.
    """
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    project = m._EarlyWithholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=m._paved_withholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=m.FROM_DECISION, seeding=m.CLASS_SEEDED))
    scratch = tmp_path / "scratch"
    with _open(root, scratch, acquire=sec020._AcquireForSubject(), project=project) as opened:
        served = m._paved_ask(opened, subject)
        assert isinstance(served, ServedProduct), served
        record = opened.record_of(served)
        minted = sorted(scratch.glob("paved_fixture*.sqlite3"))
        assert len(minted) == 1, minted
        fabric = load_config_and_boot(
            opened.config_path, registry=opened.control_plane,
            connection={"database_path": str(minted[0])}, read_only=read_only,
        )
        try:
            outcome = replay(
                record_address=served.replay_ref.content_address, store=opened.artifact_store,
                reader=fabric.handle.reader, control_plane=opened.control_plane,
                environment=RecordedEnvironment(record=record, opened=opened, fabric=fabric),
            )
            arguments = opened.build_arguments(fabric)
            arguments["acquisition"] = None
            try:
                later: Any = build_governed_resolver(**arguments)(
                    tenant=opened.tenant_id, product_class=opened.declaration.schema_name,
                    version=opened.declaration.schema_version, perspective=opened.default_perspective,
                    request=opened.question(
                        subject=sec020.PAVED_ABSENT, asked_at=record.context_fabric_snapshot.temporal_boundary,
                        intent="fixture-intent", freshness="fixture-freshness", parameters={PAVED_THRESHOLD: 1000},
                    ),
                )
            except ProductNotResolvable as raised:
                later = raised
        finally:
            fabric.handle.close()
    path = record.content_generation_path
    assert content_hash(outcome.product) == path.product_content_address == content_hash(served.product), (
        "the record must replay to its own address over its question's store, booted again"
    )
    assert m._named(later, "QuestionStoreReopened"), (
        f"a serve from a question's store booted again must be refused by name; it was answered: {type(later).__name__}"
    )


__all__: Sequence[str] = ()
