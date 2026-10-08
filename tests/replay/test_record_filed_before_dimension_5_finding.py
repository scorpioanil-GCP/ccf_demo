"""A record filed before dimension 5 carried the empty finding replays to its own address.

Channel 7 of SEC-020 in the ``D-IMPL-377`` close-out (review finding M-5),
``D-IMPL-378``. It is a replay limit, not an existence channel: nothing here
tells a withheld subject from a nonexistent one, and SEC-020 stays OPEN for the
reasons the security how-to, section 4.12, lists.

The history, by commit
----------------------
* ``ac4e4573`` (24.6-05, merged to ``main`` in ``8e8374c3`` on 2026-09-05) put
  :attr:`~ccf.products.contract.ContextProductContract.computed_empty` on the
  product: a product carries a finding when an operator ran and returned
  nothing, and the finding is inside the product's content address.
* Until ``7bf069cc`` (2026-10-07), ``main``'s
  ``src/ccf/replay/record.py::build_replay_record`` did not copy that finding
  into dimension 5, and the replay environment had no member to rebuild it
  from. Every record of a product that carried a finding therefore failed
  replay with ``ReplayDivergence``, under the very code that filed it. The
  ``v1.0.0`` and ``v1.0.1`` tags are inside that window.
* ``1a2359e4`` added ``ContentGenerationPath.computed_empty`` (hash-transparent
  at ``None``) on a lane branch. Its integration ``77d5e2a9`` and the revert
  ``91fd7965`` both reached ``main`` in ``29a3c5a4``, with no net change. The
  reapply ``6247cd63`` reached ``main`` in ``7bf069cc``.

How the record filed before the change is constructed here
----------------------------------------------------------
It is the record the current writer files for the same question with dimension
5's ``computed_empty`` removed. That is byte for byte what the writer at
``d9305603`` filed for this question: ``git diff d9305603 7bf069cc --
src/ccf/replay/record.py`` adds that one member and nothing else, the member is
hash-transparent at ``None``, and serving this fixture's question under both
trees (``D-IMPL-378`` lane measurement, 2026-10-07) gave stored record bytes
with one sha256.

The rule under test is ``src/ccf/replay/engine.py::replay``'s, and the record's
own product address arbitrates it: the controls below hold that the record the
current writer files still replays with its finding copied, and that a record
naming a product the re-execution does not produce still diverges.

Every value here is the paved fixture's vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any

import pytest

from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import content_hash
from ccf.deployment import load_config_and_boot
from ccf.products.contract import ComputedEmptyFinding
from ccf.products.product import AcquisitionContext, OpenedProduct
from ccf.replay.engine import ReplayDivergence, ReplayOutcome, replay
from ccf.replay.environment import RecordedEnvironment
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.composition import composition_replay_mint
from tests.products.test_paved_road import _Acquire, _open, _question, _write_tree


class _AcquiresNothing(_Acquire):
    """A source holding nothing for the question, so the plan's operators return empty."""

    def __call__(self, context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        self.contexts.append(context)
        return ()


class _Served:
    """One computed-empty decision on the paved road, with what replaying it needs."""

    def __init__(
        self,
        opened: OpenedProduct,
        scratch: pathlib.Path,
        answer: ServedProduct,
        record: DecisionReplayRecord,
    ) -> None:
        self.opened = opened
        self.scratch = scratch
        self.answer = answer
        self.record = record

    def file(self, record: DecisionReplayRecord, *, name: str) -> str:
        """File ``record`` in the deployment's own store under the record class; its address."""
        artifact_class = self.answer.replay_ref.artifact_class
        reference = self.opened.artifact_store.put(
            composition_replay_mint(
                self.opened.control_plane,
                tenant=record.tenant_id,
                artifact_class=artifact_class,
            ),
            DerivedWrite(artifact_class=artifact_class, name=name, artifact=record),
        )
        return str(reference.content_address)

    def replay(self, *, address: str, record: DecisionReplayRecord) -> Any:
        """Replay ``address`` through the shipped ``RecordedEnvironment`` over the question's fabric."""
        minted = sorted(self.scratch.glob("paved_fixture*.sqlite3"))[-1]
        fabric = load_config_and_boot(
            self.opened.config_path,
            registry=self.opened.control_plane,
            connection={"database_path": str(minted)},
        )
        try:
            return replay(
                record_address=address,
                store=self.opened.artifact_store,
                reader=fabric.handle.reader,
                control_plane=self.opened.control_plane,
                environment=RecordedEnvironment(record=record, opened=self.opened, fabric=fabric),
            )
        finally:
            fabric.handle.close()


@pytest.fixture()
def served(tmp_path: pathlib.Path) -> Iterator[_Served]:
    root = _write_tree(tmp_path)
    scratch = tmp_path / "scratch"
    with _open(root, scratch, acquire=_AcquiresNothing()) as opened:
        answer = opened.answer(_question(opened))
        assert isinstance(answer, ServedProduct), answer
        assert answer.product.computed_empty is not None, (
            "case not constructed: with nothing acquired the plan's operators"
            f" return empty, so the product carries a finding: {answer.product}"
        )
        yield _Served(opened, scratch, answer, opened.record_of(answer))


def _without_the_member(record: DecisionReplayRecord, **path_updates: Any) -> DecisionReplayRecord:
    """``record`` as a writer before dimension 5 carried ``computed_empty`` filed it."""
    path = record.content_generation_path
    return record.model_copy(
        update={
            "content_generation_path": path.model_copy(
                update={"computed_empty": None, **path_updates}
            )
        }
    )


def test_m5_a_record_filed_before_dimension_5_carried_the_finding_replays_to_its_own_address(
    served: _Served,
) -> None:
    """The record the writer at ``d9305603`` filed for this question, replayed now."""
    record = served.record
    assert record.content_generation_path.computed_empty == served.answer.product.computed_empty, (
        "case not constructed: the current writer files the product's finding on dimension 5"
    )
    before = _without_the_member(record)
    address = served.file(before, name="filed-before-dimension-5-carried-the-finding")
    assert address != served.answer.replay_ref.content_address, (
        "case not constructed: the record without the member is a different record"
    )
    assert before.content_generation_path.product_content_address == content_hash(
        served.answer.product
    )

    try:
        outcome = served.replay(address=address, record=before)
    except ReplayDivergence as divergence:
        pytest.fail(
            "channel 7 (M-5): a record filed before dimension 5 carried the empty"
            f" finding does not replay to its own address: ReplayDivergence: {divergence}"
        )

    assert isinstance(outcome, ReplayOutcome), outcome
    assert outcome.record_content_address == address
    assert outcome.product_content_address == before.content_generation_path.product_content_address
    assert content_hash(outcome.product) == content_hash(served.answer.product)
    # THE MECHANISM, BY NAME: the finding the writer of that era attached,
    # re-derived from the re-execution the engine held to the record.
    assert outcome.product.computed_empty == served.answer.product.computed_empty


def test_m5_control_the_record_the_current_writer_files_replays_with_its_finding_copied(
    served: _Served,
) -> None:
    """The record carrying the member replays exactly as before this rule existed."""
    outcome = served.replay(address=served.answer.replay_ref.content_address, record=served.record)
    assert isinstance(outcome, ReplayOutcome), outcome
    assert outcome.product_content_address == content_hash(served.answer.product)
    assert outcome.product.computed_empty == served.answer.product.computed_empty


def test_m5_control_the_record_s_own_product_address_still_arbitrates(served: _Served) -> None:
    """A record without the member that names a product the re-execution does not produce diverges.

    The record names the served product with its finding's ``emptiness``
    flipped: a validly typed finding the re-execution never derives. The rule
    may add only the finding the re-execution yields, and only when the product
    then hashes to the address the record names, so this record must still
    raise ``ReplayDivergence``.
    """
    finding = served.answer.product.computed_empty
    assert finding is not None
    flipped = ComputedEmptyFinding(
        operators_returned_empty=finding.operators_returned_empty,
        operators_invoked=finding.operators_invoked,
        plan_id=finding.plan_id,
        emptiness="unattested" if finding.emptiness == "attested" else "attested",
    )
    claimed = served.answer.product.model_copy(update={"computed_empty": flipped})
    assert content_hash(claimed) != content_hash(served.answer.product)
    misnamed = _without_the_member(served.record, product_content_address=content_hash(claimed))
    address = served.file(misnamed, name="names-a-product-the-re-execution-does-not-produce")

    with pytest.raises(ReplayDivergence):
        served.replay(address=address, record=misnamed)
