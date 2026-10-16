# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Durable, addressable replay evidence (`D-IMPL-383`), proven through the paved road.

The bank's question (Dave, 2026-10-15 18:09): how does decision replay work if
the per-question SQLite is destroyed after each question? The ruling (Dave,
20:27, adopting the reviewer's six instructions) asks for three outcomes, and
each test below holds one of them against the estate-free paved fixture:

1. **Evidence survives a restart.** Decisions answered under one opening replay
   under a SECOND opening of the same scratch, with acquisition sabotaged so a
   re-derivation from sources would fail loudly rather than pass silently.
2. **A decision reliably finds its evidence.** The decision's record address is
   the index key — no scan, no "last file in the folder" — and two questions
   map to two different graphs. Deleting one graph affects only its decision.
3. **Incomplete or altered evidence cannot be presented as successful replay.**
   An interruption between the record and its mapping leaves an explicit
   incomplete state; a graph whose bytes changed raises the existing divergence
   error, never "missing".

Plus the bank front-end's enumeration: decisions listed by time window and by
the subject or a parameter identifier, each entry stating served or refused and
the refusal's reason.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from ccf.contracts.canonical import content_hash
from ccf.products.product import AcquisitionContext, OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.engine import RefusalReplayOutcome, ReplayDivergence, ReplayOutcome
from ccf.replay.evidence import (
    ReplayEvidenceAltered,
    ReplayEvidenceIndex,
    ReplayEvidenceUnavailable,
)
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope

from tests.products.test_paved_road import ASKED_AT, _open, _question, _write_tree

# --- helpers ---------------------------------------------------------------------------


class _SourcesUnavailable:
    """An acquisition that fails the test if replay ever re-derives from sources."""

    def __call__(self, context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        raise AssertionError(
            f"replay reached the sources for {context.request.subject!r}; replay"
            " must read the retained evidence, never re-derive (D-IMPL-218)"
        )


def _address(opened: OpenedProduct, outcome: ServedProduct | RefusalEnvelope) -> str:
    if isinstance(outcome, ServedProduct):
        return outcome.replay_ref.content_address
    return opened.artifact_store.resolve_uri(uri=outcome.replay_reference)


def _early_refusal(opened: OpenedProduct) -> RefusalEnvelope:
    """A refusal recorded before any graph is minted: an address this product does not serve."""
    outcome = opened.resolve(
        tenant=opened.tenant_id,
        product_class="no.such-class",
        version="1.0.0",
        perspective=opened.default_perspective,
        request=_question(opened),
    )
    assert isinstance(outcome, RefusalEnvelope), outcome
    return outcome


@pytest.fixture()
def tree(tmp_path: pathlib.Path) -> Iterator[tuple[pathlib.Path, pathlib.Path]]:
    yield _write_tree(tmp_path), tmp_path / "evidence-root"


# --- 1. evidence survives restart ---------------------------------------------------------


def test_every_decision_replays_after_a_restart_with_the_sources_unavailable(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened))
        refused_after_boot = opened.answer(_question(opened, no_such_parameter=1))
        refused_before_boot = _early_refusal(opened)
        assert isinstance(served, ServedProduct), served
        assert isinstance(refused_after_boot, RefusalEnvelope), refused_after_boot
        addresses = {
            "served": _address(opened, served),
            "after": _address(opened, refused_after_boot),
            "before": _address(opened, refused_before_boot),
        }

    # A second opening of the SAME scratch is the restarted service.
    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        reproduced = restarted.replay_decision(addresses["served"])
        assert isinstance(reproduced, ReplayOutcome), reproduced
        assert reproduced.product_content_address == content_hash(served.product)

        after = restarted.replay_decision(addresses["after"])
        assert isinstance(after, RefusalReplayOutcome), after

        before = restarted.replay_decision(addresses["before"])
        assert isinstance(before, RefusalReplayOutcome), before

        entry = restarted.evidence.entry(addresses["before"])
        assert entry is not None and entry.graph is None, "a pre-graph refusal maps to no graph"
        assert entry.graph_required is False


# --- 2. a decision finds its own evidence ----------------------------------------------------


def test_two_questions_map_to_two_graphs_and_deleting_one_affects_only_its_decision(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        first = opened.answer(_question(opened))
        second = opened.answer(_question(opened))
        assert isinstance(first, ServedProduct) and isinstance(second, ServedProduct)
        first_entry = opened.evidence.entry(_address(opened, first))
        second_entry = opened.evidence.entry(_address(opened, second))

    assert first_entry is not None and second_entry is not None
    assert first_entry.graph is not None and second_entry.graph is not None
    assert first_entry.graph != second_entry.graph, "one graph per question, mapped per decision"
    # Relative to the evidence root, never an absolute path.
    assert not pathlib.PurePath(first_entry.graph).is_absolute()

    (scratch / first_entry.graph).unlink()

    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        with pytest.raises(ReplayEvidenceUnavailable) as missing:
            restarted.replay_decision(_address(restarted, first))
        assert first_entry.graph in str(missing.value)
        assert missing.value.record_address == _address(restarted, first)
        # The other decision is untouched.
        assert isinstance(restarted.replay_decision(_address(restarted, second)), ReplayOutcome)


# --- 3. incomplete or altered evidence is never a successful replay -------------------------


def test_a_graph_whose_bytes_changed_raises_divergence_never_missing(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct)
        address = _address(opened, served)
        entry = opened.evidence.entry(address)
    assert entry is not None and entry.graph is not None
    with (scratch / entry.graph).open("ab") as graph:
        graph.write(b"\x00")

    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        with pytest.raises(ReplayEvidenceAltered) as altered:
            restarted.replay_decision(address)
    assert isinstance(altered.value, ReplayDivergence), "corruption keeps the divergence error"
    assert not isinstance(altered.value, ReplayEvidenceUnavailable), "corruption is not 'missing'"


def test_an_interruption_between_the_record_and_its_mapping_is_reported_as_incomplete(
    tree: tuple[pathlib.Path, pathlib.Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, scratch = tree
    interrupted: list[str] = []

    def crash(self: ReplayEvidenceIndex, entry: object) -> None:
        interrupted.append(entry.record_address)  # type: ignore[attr-defined]
        raise KeyboardInterrupt("simulated stop between the record and its mapping")

    with _open(root, scratch) as opened:
        completed = opened.answer(_question(opened))
        assert isinstance(completed, ServedProduct)
        with monkeypatch.context() as patch:
            patch.setattr(ReplayEvidenceIndex, "publish", crash)
            with pytest.raises(KeyboardInterrupt):
                opened.answer(_question(opened))
    assert len(interrupted) == 1
    (orphan,) = interrupted

    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        # The record exists in the store; its mapping was never published.
        assert restarted.artifact_store.get(content_address=orphan)
        with pytest.raises(ReplayEvidenceUnavailable, match="incomplete") as incomplete:
            restarted.replay_decision(orphan)
        assert incomplete.value.record_address == orphan
        pending = restarted.evidence.incomplete()
        assert len(pending) == 1 and pending[0].subject == "acct-1"
        # The decision that completed before the interruption still replays.
        assert isinstance(restarted.replay_decision(_address(restarted, completed)), ReplayOutcome)
        assert [e.record_address for e in restarted.evidence.decisions()] == [_address(restarted, completed)]


def test_an_unknown_or_malformed_address_is_unavailable_and_never_reaches_the_filesystem(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        with pytest.raises(ReplayEvidenceUnavailable):
            opened.replay_decision("0" * 64)
        with pytest.raises(ValueError, match="content address"):
            opened.replay_decision("../../etc/passwd")


# --- 4. the front-end's questions -------------------------------------------------------------


def test_decisions_are_enumerable_by_time_window_and_by_subject_or_identifier(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened, limit=7))
        refused = opened.answer(_question(opened, no_such_parameter=1))
        early = _early_refusal(opened)
        assert isinstance(served, ServedProduct) and isinstance(refused, RefusalEnvelope)
        everything = opened.evidence.decisions()
        assert [e.record_address for e in everything] == [
            _address(opened, served),
            _address(opened, refused),
            _address(opened, early),
        ], "listed in decision order"

        served_entry, refused_entry, early_entry = everything
        # Wall-clock instants, not the deployment's (fixed, March) clock: evidence
        # never reads the clock the decision itself reads.
        assert served_entry.decided_at > ASKED_AT + timedelta(days=30)
        assert abs(datetime.now(UTC) - early_entry.decided_at) < timedelta(minutes=5)
        assert served_entry.outcome == "served" and served_entry.refusal_reason is None
        assert refused_entry.outcome == "refused" and refused_entry.refusal_reason == refused.reason
        assert early_entry.refusal_reason == "class-mismatch"

        window = opened.evidence.decisions(since=served_entry.decided_at, until=refused_entry.decided_at)
        assert [e.record_address for e in window] == [served_entry.record_address, refused_entry.record_address]

        assert {e.record_address for e in opened.evidence.decisions(involving="acct-1")} == {
            e.record_address for e in everything
        }
        assert opened.evidence.decisions(involving="acct-nobody") == []
        # A parameter value identifies a decision too (a facility, a company id).
        assert [e.record_address for e in opened.evidence.decisions(involving="7")] == [served_entry.record_address]

        # "Which policies and data supported this answer?" — dimensions 2 and 1 of the record.
        record = opened.record_of(served)
        assert record.policy_bindings.bindings, "the policy-bindings snapshot"
        assert record.context_fabric_snapshot.store_watermark, "the touched-substate fingerprint"


# --- 5. an erased record is disclosed, never reported as "missing" ---------------------------


def test_an_erased_decision_record_is_disclosed_by_the_engine_not_reported_unavailable(
    tree: tuple[pathlib.Path, pathlib.Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-009 (`D-IMPL-374` (4)): an erasure is a recorded decision, not an absence.

    A store that consults the erasure index refuses the erased record's bytes;
    the engine turns that into an ErasedReplayOutcome. The lookup helper must
    hand the decision to the engine rather than calling it unavailable.
    """
    from ccf.erasure.errors import ErasedContentRefused  # noqa: PLC0415
    from ccf.replay.engine import ErasedReplayOutcome  # noqa: PLC0415

    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct)
        address = _address(opened, served)

    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        store = restarted.artifact_store
        original_get = store.get

        def erased_get(*, content_address: str) -> bytes:
            if content_address == address:
                raise ErasedContentRefused(
                    content_address=address, erasure_record_address=None, reason=None, erased_at=None
                )
            return original_get(content_address=content_address)

        monkeypatch.setattr(store, "get", erased_get)
        outcome = restarted.replay_decision(address)
    assert isinstance(outcome, ErasedReplayOutcome), outcome
    assert outcome.record_content_address == address


# --- close-panel fixes (Dave, 2026-10-15 22:53: "fix 1-5") ------------------------------------


def test_a_lookup_never_returns_another_tenants_mapping(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Instruction 2: the index is scoped to the instance AND the tenant — lookups too, not only listings."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct)
        address = _address(opened, served)
        own = opened.evidence
        assert own.entry(address) is not None
        foreign = ReplayEvidenceIndex(
            evidence_root=own.evidence_root, index_root=own.index_root, tenant_id=f"not-{own.tenant_id}"
        )
        assert foreign.entry(address) is None, "another tenant's lookup resolved this tenant's mapping"


def test_a_refusal_a_door_records_directly_is_mapped_and_replays(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """A door's own denial (its entitlement step) records through ``refusal_recorder``, not ``answer``.

    It must publish a no-graph mapping like every other refusal before a graph,
    so replay finds it — never reporting a completed decision as interrupted.
    """
    from ccf.products.refusal import RequestIdentity, envelope_for  # noqa: PLC0415
    from ccf.products.request import ProductRequestViolation  # noqa: PLC0415
    from ccf.replay.record import ResolutionNotApplicable  # noqa: PLC0415

    root, scratch = tree
    with _open(root, scratch) as opened:
        request = _question(opened)
        violation = ProductRequestViolation(
            reason="class-mismatch", key="schema_version",
            declared_type="declared@1.0.0", presented_type="presented@9.0.0",
            declared_keys=frozenset(), presented_keys=frozenset(), detail="a door's own denial",
        )
        identity = RequestIdentity(
            product_id=request.schema_name, product_version=request.schema_version,
            parameters=request.parameters, temporal_boundary=request.asked_at,
        )
        recorded = opened.refusal_recorder.record(
            envelope_for(violation, request=identity),
            perspective=opened.default_perspective,
            recorded_at=request.asked_at,
            served_at=request.asked_at,
            request=request,
            resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
        )
        address = _address(opened, recorded)
        entry = opened.evidence.entry(address)
        assert entry is not None, "a door-recorded refusal published no evidence mapping"
        assert entry.graph is None and entry.graph_required is False and entry.outcome == "refused"

    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        assert isinstance(restarted.replay_decision(address), RefusalReplayOutcome)


def test_a_mapping_that_disagrees_with_its_record_is_divergence_never_missing(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """Instruction 4: an altered index is corruption — reported as divergence, not as "unavailable"."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened))
        refused = _early_refusal(opened)
        assert isinstance(served, ServedProduct)
        served_address, refused_address = _address(opened, served), _address(opened, refused)
        index = opened.evidence

    # A served decision's mapping cannot claim it needed no graph.
    entry = index.entry(served_address)
    assert entry is not None
    with pytest.raises(ValueError, match="served"):
        type(entry).model_validate({**entry.model_dump(mode="json"), "graph": None,
                                    "graph_sha256": None, "graph_required": False})

    # A refusal's mapping rewritten as "served" with the served decision's graph.
    refused_entry = index.entry(refused_address)
    served_entry = index.entry(served_address)
    assert refused_entry is not None and served_entry is not None
    forged = refused_entry.model_copy(update={
        "outcome": "served", "refusal_reason": None, "graph": served_entry.graph,
        "graph_sha256": served_entry.graph_sha256, "graph_required": True,
    })
    (index.index_root / "decisions" / f"{refused_address}.json").write_text(forged.model_dump_json())
    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        with pytest.raises(ReplayDivergence) as raised:
            restarted.replay_decision(refused_address)
        assert not isinstance(raised.value, ReplayEvidenceUnavailable)


def test_a_retained_graph_replaced_by_a_symlink_is_refused(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Evidence must live under the evidence root: a symlink is not retained evidence, even to identical bytes."""
    root, scratch = tree
    with _open(root, scratch) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct)
        address = _address(opened, served)
        entry = opened.evidence.entry(address)
        assert entry is not None
        graph = opened.evidence.graph_path(entry)
    elsewhere = scratch.parent / "elsewhere.sqlite3"
    elsewhere.write_bytes(graph.read_bytes())
    graph.unlink()
    graph.symlink_to(elsewhere)
    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        with pytest.raises(ReplayDivergence, match="symlink"):
            restarted.replay_decision(address)


def test_decided_at_is_documented_as_the_wall_clock() -> None:
    from ccf.replay.evidence import EvidenceEntry  # noqa: PLC0415

    doc = EvidenceEntry.__doc__ or ""
    assert "deployment clock" not in doc, "decided_at is the wall clock, never the deployment's"


def test_a_refusal_before_any_graph_replays_first_after_a_restart(tree: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The restarted service's FIRST replay is a pre-graph refusal: nothing else has registered the Control Plane.

    Found by the close-panel fixes (2026-10-15): every earlier proof replayed a
    served decision first, whose boot registered the deployment, and so hid that
    a pre-graph refusal alone was `ReplayUnresolvable`.
    """
    root, scratch = tree
    with _open(root, scratch) as opened:
        address = _address(opened, _early_refusal(opened))
    with _open(root, scratch, acquire=_SourcesUnavailable()) as restarted:
        assert isinstance(restarted.replay_decision(address), RefusalReplayOutcome)
        assert not list(scratch.glob("*.sqlite3")), "replaying a pre-graph refusal minted no graph in the evidence root"
