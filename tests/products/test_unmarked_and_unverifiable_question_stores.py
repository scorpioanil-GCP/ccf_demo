"""SEC-020 P4 (a), made strict: no store is presumed fresh (``D-IMPL-378``).

Dave, 2026-10-08 12:29 MST, ruling P4 (a), verbatim: *"An unmarked existing
store must not be presumed fresh. Require verifiable fresh creation or refuse
acquisition-backed serving. Unsupported network compositions must refuse
before questions run."* SEC-020 stays OPEN: these tests measure what the SDK
refuses, and nothing here closes it.

What P4 (a) left open, measured on lane ``378d-s020next`` @ ``f2ce304c``
(``probe-p4-marker-limits``, ``oldrec-phase-b``): the marker a question boot
leaves beside its store is the only thing a later boot reads, so a store
booted for a question BEFORE the marker existed carries none and still
answered a later question, and so did a copy of a used store taken without its
marker. Both read as stores nobody's question had written into. Those are the
"unmarked existing store" of the ruling, and the first section below asks the
SDK to refuse a governed call over one by name, before the graph is read,
while Decision Replay — which rebuilds a resolver over the store and never
calls it — reads it as before.

Each store here is booted for its question and asked it through an
acquisition seam that, asked about the withheld account, ingests a fresher
claim (``planted``), or asked about an identifier that names nothing, ingests
nothing (``untouched``). A later question about that nothing-identifier,
answered from each, differs exactly when the first question's acquisition
landed — which is what an unmarked store would disclose if it were presumed
fresh. Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
import shutil
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.deployment import load_and_boot, load_config_and_boot
from ccf.products.resolver import ProductNotResolvable, build_governed_resolver
from ccf.replay.engine import replay
from ccf.replay.environment import RecordedEnvironment
from ccf.replay.serve import ServedProduct
from tests.products import test_withheld_subject_population_composite_and_fabric as m
from tests.products.test_withheld_subject_child_arguments_and_question_stores import (
    _first_question,
    _later,
    _refused_by_name,
)

sec020 = m.sec020

#: The store file every fixture fabric here names, beside its manifest.
_STORE = "graph.sqlite3"


def _sdk_markers(store: pathlib.Path) -> list[pathlib.Path]:
    """Every marker the SDK left beside ``store``: ``<resolved store path>.ccf-*-store``."""
    resolved = store.resolve()
    return sorted(resolved.parent.glob(f"{resolved.name}.ccf-*-store"))


def _as_before_the_marker(store: pathlib.Path) -> list[str]:
    """Remove the SDK's markers beside ``store``: the store as a tree from before the marker left it.

    Returns the names removed, so a test can show the case was constructed —
    a question's store carries its marker on this tree, and only its removal
    makes it the unmarked store the ruling names.
    """
    removed = []
    for marker in _sdk_markers(store):
        marker.unlink()
        removed.append(marker.name)
    return removed


def _reopen(directory: pathlib.Path, booted: Any) -> Any:
    """Boot the store under ``directory`` again, plainly — the way the replay road and a kept graph reopen it."""
    return load_and_boot(
        directory / "manifest.yaml",
        registry=booted[1],
        connection={"database_path": str(directory / _STORE)},
    )


def _asked_later(directory: pathlib.Path, booted: Any) -> Any:
    """The later question, through a resolver with no acquisition phase, over the store reopened."""
    fabric = _reopen(directory, booted)
    try:
        return _later((fabric, booted[1], booted[2]))
    finally:
        fabric.handle.close()


# --- 1. an unmarked existing store is not presumed fresh ----------------------------


@pytest.mark.parametrize("anchor", [m.FROM_DECISION, m.FROM_ENTITY_FRESHNESS])
def test_p4_strict_a_question_store_from_before_the_marker_serves_no_later_question(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """A store booted for a question before the marker existed: refused by name, not presumed fresh.

    Measured on ``f2ce304c``: the four stores served on the pre-marker tree
    each answered a later question when reopened (``oldrec-phase-b``). The
    store here is the same thing built on this tree — booted for its question,
    asked it, closed, and stripped of the marker this tree left — so the later
    boot finds an existing store that carries no marker.
    """
    outcomes: dict[str, Any] = {}
    for name, first_subject in (("untouched", sec020.MISSING), ("planted", sec020.WITHHELD)):
        booted = m._boot(tmp_path, name, anchor=anchor, envelopes=m._base_accounts(), for_question=True)
        try:
            ingested = _first_question(booted, first_subject)
        finally:
            booted[0].handle.close()
        assert ingested == (1 if name == "planted" else 0), f"[{anchor}, {name}] the case was not constructed: {ingested}"
        removed = _as_before_the_marker(tmp_path / name / _STORE)
        assert removed, f"[{anchor}, {name}] the question boot left no marker to remove; the case was not constructed"
        outcomes[name] = _asked_later(tmp_path / name, booted)
    _refused_by_name(outcomes, "UnmarkedStoreNotPresumedFresh", case=f"{anchor}, a question's store from before the marker")


@pytest.mark.parametrize("anchor", [m.FROM_DECISION, m.FROM_ENTITY_FRESHNESS])
def test_p4_strict_a_marker_less_copy_of_a_used_store_serves_no_later_question(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """A copy of a used question store taken without its marker: refused by name, not presumed fresh.

    Measured on ``f2ce304c`` (``probe-p4-marker-limits``, measure ``g``): the
    copy answered while the original beside it was refused. The copy here
    carries the store and the deployment's documents and no SDK marker. The
    original, still marked, is the control: it is refused under its own name.
    """
    outcomes: dict[str, Any] = {}
    originals: dict[str, Any] = {}
    for name, first_subject in (("untouched", sec020.MISSING), ("planted", sec020.WITHHELD)):
        booted = m._boot(tmp_path, name, anchor=anchor, envelopes=m._base_accounts(), for_question=True)
        try:
            ingested = _first_question(booted, first_subject)
        finally:
            booted[0].handle.close()
        assert ingested == (1 if name == "planted" else 0), f"[{anchor}, {name}] the case was not constructed: {ingested}"
        copy = tmp_path / f"{name}-copy"
        copy.mkdir()
        for item in (tmp_path / name).iterdir():
            documents = item.suffix == ".yaml"
            store_files = item.name.startswith(_STORE) and ".ccf-" not in item.name
            if item.is_file() and (documents or store_files):
                shutil.copy(item, copy / item.name)
        assert (copy / _STORE).exists() and not _sdk_markers(copy / _STORE), f"[{anchor}, {name}] the copy was not constructed"
        outcomes[name] = _asked_later(copy, booted)
        originals[name] = _asked_later(tmp_path / name, booted)
    for name, refused in originals.items():
        assert m._named(refused, "QuestionStoreReopened"), (
            f"[{anchor}] the marked original ({name}) must still be refused under its own name: {refused!r}"
        )
    _refused_by_name(outcomes, "UnmarkedStoreNotPresumedFresh", case=f"{anchor}, a marker-less copy of a used store")


@pytest.mark.parametrize("read_only", [False, True], ids=["writer-boot", "read-only-boot"])
def test_p4_strict_replay_reads_an_unmarked_question_store_whose_serve_is_refused(
    tmp_path: pathlib.Path, read_only: bool
) -> None:
    """Decision Replay needs no fresh store: an unmarked question store replays its record; a serve from it is refused.

    The paved road answers on a store it mints and boots for the question;
    stripped of its marker, the store is one from before the marker. The
    replay road reopens it and rebuilds the resolver through
    ``RecordedEnvironment`` without calling it: the record replays to its own
    address. The same reopened fabric, asked to serve with no acquisition
    phase, is refused by name.
    """
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    project = m._EarlyWithholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=m._paved_withholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=m.FROM_DECISION, seeding=m.CLASS_SEEDED))
    scratch = tmp_path / "scratch"
    with _open(root, scratch, acquire=sec020._AcquireForSubject(), project=project) as opened:
        served = m._paved_ask(opened, sec020.PAVED_WITHHELD)
        assert isinstance(served, ServedProduct), served
        record = opened.record_of(served)
        minted = sorted(scratch.glob("paved_fixture*.sqlite3"))
        assert len(minted) == 1, minted
        removed = _as_before_the_marker(minted[0])
        assert removed, "the paved road's question boot left no marker to remove; the case was not constructed"
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
        "the record must replay to its own address over its question's store, unmarked and booted again"
    )
    assert m._named(later, "UnmarkedStoreNotPresumedFresh"), (
        f"a serve from an unmarked question store booted again must be refused by name; it was answered: {later!r}"
    )


# --- 1, controls: what the SDK created verifiably still serves -------------------------


def test_p4_strict_control_a_verifiably_fresh_question_store_serves_its_one_question(tmp_path: pathlib.Path) -> None:
    """The control the ruling keeps: a store the SDK created fresh for one question answers that question."""
    booted = m._boot(tmp_path, "fresh", anchor=m.FROM_DECISION, envelopes=m._base_accounts(), for_question=True)
    try:
        seam = m._RefreshWhenAsked(booted[0])
        answered = m._ask(m._governed(booted, plan_factory=m._late(), acquisition=seam), sec020.MISSING)
    finally:
        booted[0].handle.close()
    assert isinstance(answered, ServedProduct), f"a verifiably fresh question store must answer its one question: {answered!r}"
    assert seam.asked == [sec020.MISSING], f"its acquisition phase must run, once, for that question: {seam.asked}"


def test_p4_strict_control_a_store_the_sdk_created_for_a_deployment_serves_again_when_reopened(
    tmp_path: pathlib.Path,
) -> None:
    """The control the strict reading must not break: a deployment's own store, kept and reopened, still answers.

    Booted plainly — never for a question, so no acquisition phase can ever
    have written into it (Q9 refuses one) — filled by the deployment's own
    ingest, closed, and booted again: a governed call with no acquisition
    phase is answered, from the first boot and from the second alike.
    """
    booted = m._boot(tmp_path, "kept", anchor=m.FROM_DECISION, envelopes=m._base_accounts(), for_question=False)
    try:
        first = m._ask(m._governed(booted, plan_factory=m._late(), acquisition=None), sec020.MISSING)
    finally:
        booted[0].handle.close()
    again = _asked_later(tmp_path / "kept", booted)
    assert isinstance(first, ServedProduct), f"a deployment's store must answer: {first!r}"
    assert isinstance(again, ServedProduct), (
        f"a deployment's store the SDK created, booted again, must still answer: {again!r}"
    )
    m._assert_indistinguishable(again, first, case="a deployment's own store, reopened")
