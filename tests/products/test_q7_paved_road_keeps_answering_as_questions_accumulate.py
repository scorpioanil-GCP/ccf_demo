"""SEC-020 Q7: one opened product keeps answering while each question's shared-owner walk grows past the reference bound.

SEC-020 is OPEN: this test measures the paved road; it closes nothing. Lane
``378j-q7``. A control for ``D-IMPL-378`` repair 2.4 (b) (Dave, 2026-10-09
10:54 MST: *"Refuse when the shared-owner walk reaches a limit before
completing."*), committed before any change to how the walk treats its bounds.

What it measures. ``src/ccf/products/product.py::OpenedProduct.answer`` builds
a ``GovernedResolver`` for every question, and its construction runs the
shared-owner walk (``src/ccf/products/resolver.py::_refuse_shared_owner``) over
the two phases it is handed: on the paved road, the SDK's own per-question seam
closures (``src/ccf/products/product.py::OpenedProduct._acquisition_seam``).
Those closures hold the fabric's L2 worker, which holds the Control Plane
registry, whose audit log gains events at every question. So the walk from
either seam reads more references at every question: measured by lane
``378j-q7`` on ``fe25536c`` for this fixture, 971 at the first question and 840
more at each after, past
:data:`~ccf.products.resolver.SHARED_OWNER_WALK_OBJECTS` at the sixth.

Asserted: one opened product answers every one of :data:`QUESTIONS` questions
with a governed outcome (a served product or a refusal value), and never raises
out of construction. Positive control, so the test cannot pass without
exercising the bound: the walk from the population seam, measured with the
walk's own reads and its bounds lifted, grows at every question and, by the
last, would read more than ``SHARED_OWNER_WALK_OBJECTS`` references.

Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

from ccf.products import resolver
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.serve import ServedProduct
from tests.products import test_withheld_is_indistinguishable_from_absent as sec020
from tests.products.test_withheld_subject_population_composite_and_fabric import (
    CLASS_SEEDED,
    FROM_DECISION,
    _ConstantWithholding,
    _paved_ask,
    _SubjectPhase,
    _Withholding,
)

#: Questions asked of one opened product: two past the sixth, where the walk
#: measured past the reference bound on ``fe25536c``.
QUESTIONS = 8


def _references_to_exhaustion(phase: object, owners: frozenset[int]) -> int:
    """The references the walk would read from ``phase`` with no bound: its own reads, run until nothing is left."""
    seen = {id(phase)}
    kept = [phase]
    frontier = [phase]
    read = 0
    while frontier:
        following = []
        for holder in frontier:
            for held in resolver._references(holder, sys.maxsize):
                read += 1
                if id(type(held)) not in resolver._NO_REFERENCES and id(held) not in seen:
                    seen.add(id(held))
                    kept.append(held)
                    following.append(held)
        frontier = following
    return read


def test_q7_one_opened_product_keeps_answering_while_the_walk_grows_past_the_reference_bound(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every question of one opened product is answered; the per-question walk grows past the bound meanwhile."""
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    sizes: list[int] = []
    guard = resolver._refuse_shared_owner

    def measured(population: object, subject_keyed: object) -> None:
        sizes.append(_references_to_exhaustion(population, resolver._owners(subject_keyed)))
        guard(population, subject_keyed)

    # The GovernedResolver site reads this module global; open_product keeps its own import, unmeasured.
    monkeypatch.setattr(resolver, "_refuse_shared_owner", measured)

    def population(context: Any) -> tuple[Any, ...]:
        return ()

    subject_phase = _SubjectPhase(hybrid=True)
    project = _Withholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=_ConstantWithholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED))
    outcomes: list[object] = []
    with _open(root, tmp_path / "scratch", acquire=subject_phase, population=population, project=project) as opened:
        for index in range(QUESTIONS):
            subject = sec020.PAVED_WITHHELD if index % 2 == 0 else sec020._uri(f"acct-accumulate-{index}")
            outcomes.append(_paved_ask(opened, subject))
    assert len(outcomes) == QUESTIONS
    assert all(isinstance(outcome, ServedProduct | RefusalEnvelope) for outcome in outcomes), outcomes
    assert len(sizes) == QUESTIONS, f"the walk ran {len(sizes)} times for {QUESTIONS} questions"
    assert all(later > earlier for earlier, later in zip(sizes, sizes[1:], strict=False)), sizes
    assert sizes[-1] > resolver.SHARED_OWNER_WALK_OBJECTS, sizes
