"""SEC-020 Q7: the shared-owner walk also reads the SDK's own state, which grows as a service runs, so it is cut off sooner.

SEC-020 is OPEN: these tests measure the walk as built; they close nothing. Lane
``378j-q7``. A control for ``D-IMPL-378`` repair 2.4 (b) (Dave, 2026-10-09
10:54 MST: *"Refuse when the shared-owner walk reaches a limit before
completing."*), committed before any change to how the walk treats its bounds,
and the measurement behind the security how-to's disclosure of how the walk
behaves until repair 2.4 is ruled (section 4.12, the Q7 bullet).

What it measures. ``src/ccf/products/product.py::OpenedProduct.answer`` builds
a ``GovernedResolver`` for every question, and its construction runs the
shared-owner walk (``src/ccf/products/resolver.py::_refuse_shared_owner``) over
the two phases it is handed: on the paved road, the SDK's own per-question seam
closures (``src/ccf/products/product.py::OpenedProduct._acquisition_seam``).
The walk from them reads the SDK's own L2 worker, Control Plane registry and
audit log, and the audit log gains events at every question, so the walk reads
more references at every question: measured by lane ``378j-q7`` on
``fe25536c`` for this fixture, 971 at the first question and 840 more at each
after, past :data:`~ccf.products.resolver.SHARED_OWNER_WALK_OBJECTS` at the
sixth. A walk that needs more than that bound is cut off and, as built under
``D-IMPL-378`` decision 3 (a), admits the two phases: what lies past the
cut-off is not checked.

Asserted, on the paved road: one opened product answers every one of
:data:`QUESTIONS` questions with a governed outcome (a served product or a
refusal value) and never raises out of construction; the walk from the
population seam reads an ``AssemblyWorker``, a ``ControlPlaneRegistry`` and an
``AuditLog``; the registry's audit log is longer after every question; and the
walk, measured with its own reads and its bounds lifted, grows at every
question, stays within the bound at the first and needs more than it from some
question on, every later question included. So from that question on the
bounded walk is cut off, and every one of those questions is still answered.

Asserted, by hand (a population phase holding its booted fabric, as one that
ingests must): the same population phase, holding the subject-keyed phase's
object behind a chain of holders, is refused on a fresh registry, where the
walk reaches the holding within the bound; once resolvers built against the
same registry have grown its audit log until the walk would reach the holding
only after more than ``SHARED_OWNER_WALK_OBJECTS`` references, the same
composition is admitted. The guard's coverage shrinks as a service runs.

Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any, NamedTuple

import pytest

from ccf.products import resolver
from ccf.products.refusal import RefusalEnvelope
from ccf.products.resolver import GovernedResolver, PopulationPhaseSharesAnOwner
from ccf.replay.serve import ServedProduct
from tests.products import test_withheld_is_indistinguishable_from_absent as sec020
from tests.products.test_q7_shared_owner_bounded_walk import _dig, _nested
from tests.products.test_withheld_subject_population_composite_and_fabric import (
    CLASS_SEEDED,
    FROM_DECISION,
    _base_accounts,
    _boot,
    _ConstantWithholding,
    _governed,
    _late,
    _paved_ask,
    _RefreshWhenAsked,
    _SubjectPhase,
    _Withholding,
)

#: Questions asked of one opened product: two past the sixth, where the walk
#: measured past the reference bound on ``fe25536c``.
QUESTIONS = 8

#: The SDK's own objects the paved road's per-question walk is measured reading.
SDK_STATE = frozenset({"AssemblyWorker", "ControlPlaneRegistry", "AuditLog"})

#: Holders between the hand-built population phase and the subject-keyed
#: phase's object: deep enough that the walk reaches the object only after the
#: audit log's events, and within ``SHARED_OWNER_WALK_DEPTH``.
HOLDERS = 9

#: The most resolvers the hand-built test builds to grow the audit log.
CONSTRUCTIONS_CAP = 400


class _Unbounded(NamedTuple):
    """One walk with its bounds lifted, run with the walk's own reads."""

    references: int
    """The references read until nothing is left."""
    kinds: frozenset[str]
    """The type names of the objects read."""
    owner_at: int | None
    """How many references had been read when an owner was first among them; ``None`` if never."""


def _unbounded_walk(phase: object, owners: frozenset[int]) -> _Unbounded:
    """The walk from ``phase`` with no bound: its own reads, in its own order, run until nothing is left."""
    seen = {id(phase)}
    kept = [phase]
    frontier = [phase]
    read = 0
    kinds: set[str] = set()
    owner_at: int | None = None
    while frontier:
        following = []
        for holder in frontier:
            kinds.add(type(holder).__name__)
            for held in resolver._references(holder, sys.maxsize):
                read += 1
                if owner_at is None and id(held) in owners:
                    owner_at = read
                if id(type(held)) not in resolver._NO_REFERENCES and id(held) not in seen:
                    seen.add(id(held))
                    kept.append(held)
                    following.append(held)
        frontier = following
    return _Unbounded(references=read, kinds=frozenset(kinds), owner_at=owner_at)


def test_q7_one_opened_product_keeps_answering_while_the_walk_grows_past_the_reference_bound(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every question is answered; the walk reads the SDK's growing state and is cut off from some question on."""
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    walks: list[_Unbounded] = []
    guard = resolver._refuse_shared_owner

    def measured(population: object, subject_keyed: object) -> None:
        walks.append(_unbounded_walk(population, resolver._owners(subject_keyed)))
        guard(population, subject_keyed)

    # The GovernedResolver site reads this module global; open_product keeps its own import, unmeasured.
    monkeypatch.setattr(resolver, "_refuse_shared_owner", measured)

    def population(context: Any) -> tuple[Any, ...]:
        return ()

    subject_phase = _SubjectPhase(hybrid=True)
    project = _Withholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=_ConstantWithholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED))
    outcomes: list[object] = []
    audit_lengths: list[int] = []
    with _open(root, tmp_path / "scratch", acquire=subject_phase, population=population, project=project) as opened:
        for index in range(QUESTIONS):
            subject = sec020.PAVED_WITHHELD if index % 2 == 0 else sec020._uri(f"acct-accumulate-{index}")
            outcomes.append(_paved_ask(opened, subject))
            audit_lengths.append(len(opened.control_plane.audit_log))
    sizes = [walk.references for walk in walks]
    assert len(outcomes) == QUESTIONS
    assert all(isinstance(outcome, ServedProduct | RefusalEnvelope) for outcome in outcomes), outcomes
    assert len(walks) == QUESTIONS, f"the walk ran {len(walks)} times for {QUESTIONS} questions"
    # The walk reads the SDK's own state, and that state grows at every question.
    assert all(SDK_STATE <= walk.kinds for walk in walks), [sorted(SDK_STATE - walk.kinds) for walk in walks]
    assert all(later > earlier for earlier, later in zip(audit_lengths, audit_lengths[1:], strict=False)), audit_lengths
    assert all(later > earlier for earlier, later in zip(sizes, sizes[1:], strict=False)), sizes
    # Cut off from some question on: within the bound at the first, past it from that question on.
    past_the_bound = [size > resolver.SHARED_OWNER_WALK_OBJECTS for size in sizes]
    assert past_the_bound[-1], sizes
    first = past_the_bound.index(True)
    assert first >= 1 and all(past_the_bound[first:]), sizes


class _HoldsItsFabricThen:
    """A hand-built population phase holding its booted fabric, as one that ingests must, and then ``held``."""

    def __init__(self, booted: Any, held: object) -> None:
        self._booted = booted
        self.held = held

    def __call__(self, *, question: Any, perspective: Any) -> None:
        return None


def test_q7_coverage_shrinks_a_holding_refused_on_a_fresh_registry_is_admitted_once_its_audit_log_has_grown(
    tmp_path: pathlib.Path,
) -> None:
    """The same composition: refused while the walk reaches the holding within the bound, admitted once it cannot."""
    booted = _boot(tmp_path, "coverage", anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=True)
    registry = booted[1]
    try:
        subject_keyed = _RefreshWhenAsked(booted[0], held=False)
        holding = _HoldsItsFabricThen(booted, _nested(subject_keyed, HOLDERS))
        assert _dig(holding.held, HOLDERS) is subject_keyed, "the fixture does not hold the object where it says"
        benign = _HoldsItsFabricThen(booted, _nested(object(), HOLDERS))
        owners = resolver._owners(subject_keyed)

        fresh = _unbounded_walk(holding, owners)
        assert fresh.owner_at is not None and fresh.owner_at <= resolver.SHARED_OWNER_WALK_OBJECTS, fresh
        assert SDK_STATE <= fresh.kinds, sorted(SDK_STATE - fresh.kinds)
        with pytest.raises(PopulationPhaseSharesAnOwner) as refused:
            _governed(booted, plan_factory=_late(), acquisition=subject_keyed, population_acquisition=holding)
        assert type(refused.value) is PopulationPhaseSharesAnOwner, repr(refused.value)

        # A service runs: resolvers built against the same registry, each auditing on its log.
        logged = len(registry.audit_log)
        constructions = 0
        while True:
            position = _unbounded_walk(holding, owners).owner_at
            assert position is not None, "the walk no longer reaches the holding at all"
            if position > resolver.SHARED_OWNER_WALK_OBJECTS:
                break
            assert constructions < CONSTRUCTIONS_CAP, "the audit log never pushed the holding past the bound"
            built = _governed(booted, plan_factory=_late(), acquisition=subject_keyed, population_acquisition=benign)
            assert isinstance(built, GovernedResolver)
            constructions += 1
        grown = _unbounded_walk(holding, owners)
        assert len(registry.audit_log) > logged
        assert grown.owner_at is not None and grown.owner_at > resolver.SHARED_OWNER_WALK_OBJECTS, grown
        assert _dig(holding.held, HOLDERS) is subject_keyed

        admitted = _governed(booted, plan_factory=_late(), acquisition=subject_keyed, population_acquisition=holding)
        assert isinstance(admitted, GovernedResolver)
    finally:
        booted[0].handle.close()
