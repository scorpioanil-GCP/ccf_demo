"""SEC-020 Q7: a member the shared-owner walk cannot read, and the holders it does not read (``D-IMPL-378`` repair 1.8).

SEC-020 is OPEN: these tests measure the mechanism Dave ruled; they close
nothing. Lane ``378j-q7``.

The ruling, verbatim (Dave, 2026-10-09 10:54 MST, items 1.6 to 1.8):
*"Implement the specified documentation, citation-checker and shared-owner
fixes."* Repair 1.8 as the panel's findings brief specified it: *"Handle a
foreign member descriptor's ``TypeError`` as the walk handles an unread slot
(or refuse, per 2.4); name MappingProxyType, cell objects, generator frames and
``methodcaller`` among what the walk does not read."* Dave ruled 2.4 (b) in
the same text (*"Refuse when the shared-owner walk reaches a limit before
completing."*), so a member the walk cannot read is read as a walk that cannot
complete, and refused by name.

The hole (the "i" panel's Fable G1 finding F-G1-5, probe
``fable-G1/probes/p3_q7_walk.py``, case (g), on ``dl-378-record``): a slotted
class whose namespace holds ANOTHER class's member descriptor made
``src/ccf/products/resolver.py::_refuse_shared_owner`` raise a bare
``TypeError`` ("descriptor ... doesn't apply to ... object") out of resolver
construction and ``open_product``: fail-closed, but under no refusal the
guard names.

Asserted, at both places the guard runs (a ``GovernedResolver`` built by hand,
and ``open_product`` on the paved road): such a population phase is refused by
name, ``SharedOwnerWalkIncomplete``, a ``PopulationPhaseSharesAnOwner``, whose
message names the cause and the walk's counts, whether or not the slot behind
the unreadable member holds the subject-keyed phase's object. Two controls: a
declared slot never assigned still reads as holding nothing, and is admitted;
so does an empty closure cell, while the same cell holding the subject-keyed
phase's object is refused (lane ``378j-fixup`` item H, the panel's
J-SP-WALK-READS).

And, as documented behavior (never as an expected failure), each holder repair
1.8 names, plus the two the walk's docstring already named, is shown NOT read:
the holding is real (dug back out through the holder's own accessor), the two
phases are admitted, and the same holding in a plain container or a function's
closure is refused, so each case discriminates.

Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import collections
import functools
import operator
import pathlib
import types
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from ccf.products import resolver as resolver_module
from ccf.products.resolver import PopulationPhaseSharesAnOwner, _refuse_shared_owner
from ccf.signal.envelope import SignalEnvelope
from tests.products.test_q7_shared_owner_bounded_walk import SITES, _closure_over, _compose, _SubjectKeyed

#: The refusal repair 1.8 names. Looked up on the module, not imported, so this
#: module collects (and each case fails for its own reason) on a tree that does
#: not define it yet.
REFUSAL = "SharedOwnerWalkIncomplete"


class _ForeignSlots:
    """A class with one declared slot, whose member descriptor another class borrows."""

    __slots__ = ("borrowed",)


class _PopulationWithAForeignDescriptor:
    """A population phase whose slotted class namespace holds ANOTHER class's member descriptor.

    ``borrowed`` is ``_ForeignSlots``'s slot descriptor: reading it for this
    object raises ``TypeError``, so the walk cannot read it. ``held`` is this
    class's own slot.
    """

    __slots__ = ("held",)
    borrowed = _ForeignSlots.__dict__["borrowed"]

    def __init__(self, held: object) -> None:
        self.held = held

    def __call__(self, *_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return ()


class _PopulationWithAnUnassignedSlot:
    """A population phase with a declared slot that is never assigned: it holds nothing there."""

    __slots__ = ("held", "never")

    def __init__(self, held: object) -> None:
        self.held = held

    def __call__(self, *_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return ()


def _the_foreign_descriptor_raises(population: _PopulationWithAForeignDescriptor) -> bool:
    """Whether reading the borrowed descriptor for ``population`` raises ``TypeError``, as the fixture says."""
    descriptor = type(population).__dict__["borrowed"]
    try:
        descriptor.__get__(population, type(population))
    except TypeError:
        return True
    return False


#: Each population phase holding a foreign member descriptor: (build it from
#: the subject-keyed phase's object ``peer``, whether its own slot holds ``peer``).
_UNREADABLE: dict[str, tuple[Callable[[_SubjectKeyed], _PopulationWithAForeignDescriptor], bool]] = {
    "holding-nothing-of-the-other": (lambda peer: _PopulationWithAForeignDescriptor(object()), False),
    "holding-the-subject-keyed-object-in-its-own-slot": (_PopulationWithAForeignDescriptor, True),
}


@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize("case", sorted(_UNREADABLE))
def test_q7_a_member_the_walk_cannot_read_is_refused_by_name(tmp_path: pathlib.Path, case: str, site: str) -> None:
    """A foreign member descriptor's ``TypeError`` is refused as a walk that cannot complete, never raised raw."""
    build, holds_the_peer = _UNREADABLE[case]
    peer = _SubjectKeyed()
    population = build(peer)
    assert _the_foreign_descriptor_raises(population), "the fixture's borrowed descriptor must raise TypeError"
    assert (population.held is peer) is holds_the_peer, f"the {case} fixture does not hold what its name says"
    with pytest.raises(PopulationPhaseSharesAnOwner) as refused:
        _compose(site, tmp_path, population=population, peer=peer)
    assert type(refused.value).__name__ == REFUSAL, repr(refused.value)
    assert type(refused.value) is getattr(resolver_module, REFUSAL)
    message = str(refused.value)
    assert "population phase" in message, message
    assert "could not read" in message and "TypeError" in message, message
    assert "references" in message and "step" in message, message


@pytest.mark.parametrize("site", SITES)
def test_q7_control_a_slot_never_assigned_still_reads_as_holding_nothing(tmp_path: pathlib.Path, site: str) -> None:
    """An unassigned slot raises ``AttributeError`` when read; it holds nothing, so the pair is admitted."""
    peer = _SubjectKeyed()
    population = _PopulationWithAnUnassignedSlot(object())
    with pytest.raises(AttributeError):
        _PopulationWithAnUnassignedSlot.__dict__["never"].__get__(population, _PopulationWithAnUnassignedSlot)
    composed = _compose(site, tmp_path, population=population, peer=peer)
    assert type(composed).__name__ == ("GovernedResolver" if site == "resolver" else "OpenedProduct"), repr(composed)


def _a_population_phase_whose_closure_cell_is_empty() -> Callable[..., tuple[SignalEnvelope, ...]]:
    """``_closure_over``'s population phase with its one closure cell empty: the name it closes over bound, then deleted."""
    held: object = object()

    def population(*_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return () if held is not None else ()

    del held
    return population


@pytest.mark.parametrize("site", SITES)
def test_q7_control_an_empty_closure_cell_still_reads_as_holding_nothing(tmp_path: pathlib.Path, site: str) -> None:
    """An empty closure cell raises ``ValueError`` when read; it holds nothing, so the pair is admitted. Filled, refused.

    The panel's J-SP-WALK-READS (measured on ``6cd6023e``): the walk reads an
    empty cell, as it reads a slot never assigned, as holding nothing, and only
    another error raised while reading what an object holds refuses the pair
    (``SharedOwnerWalkIncomplete``). The twin is the same function shape with
    its cell holding the subject-keyed phase's object, which the walk reads and
    refuses, so the admission is the cell being empty, not the cell going
    unread.
    """
    peer = _SubjectKeyed()
    population = _a_population_phase_whose_closure_cell_is_empty()
    (cell,) = population.__closure__ or ()
    with pytest.raises(ValueError):
        cell.cell_contents  # noqa: B018 — an empty cell raises when read
    (tmp_path / "empty").mkdir()
    composed = _compose(site, tmp_path / "empty", population=population, peer=peer)
    assert type(composed).__name__ == ("GovernedResolver" if site == "resolver" else "OpenedProduct"), repr(composed)
    filled = _closure_over(peer)
    (filled_cell,) = filled.__closure__ or ()
    assert filled_cell.cell_contents is peer, "the twin does not hold the subject-keyed object in its cell"
    (tmp_path / "filled").mkdir()
    with pytest.raises(PopulationPhaseSharesAnOwner) as refused:
        _compose(site, tmp_path / "filled", population=filled, peer=peer)
    assert type(refused.value) is PopulationPhaseSharesAnOwner, repr(refused.value)


# --- the holders the walk does not read, each asserted as documented behavior ------------------------------


class _Holds:
    """A population phase holding one object as an instance attribute."""

    def __init__(self, held: object) -> None:
        self.held = held

    def __call__(self, *_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return ()


def _a_cell_holding(held: object) -> Any:
    """A closure cell holding ``held``, taken out of the function that closed over it."""

    def closing() -> object:
        return held

    (cell,) = closing.__closure__ or ()
    return cell


def _a_function_closing_over(held: object) -> Callable[[], object]:
    """A function whose closure holds ``held``."""

    def closing() -> object:
        return held

    return closing


def _a_generator_holding(held: object) -> Iterator[object]:
    """A generator, not yet started, holding ``held`` in its frame."""
    yield held


#: Each holder repair 1.8 names, and the two the walk's docstring already
#: named: (wrap ``peer`` in the holder, dig ``peer`` back out through the
#: holder's own accessor, the same holding in something the walk does read).
_UNREAD_HOLDERS: dict[str, tuple[Callable[[object], object], Callable[[Any], object], Callable[[object], object]]] = {
    "mappingproxy": (
        lambda peer: types.MappingProxyType({"held": peer}),
        lambda holder: holder["held"],
        lambda peer: {"held": peer},
    ),
    "cell-object-outside-a-closure": (
        lambda peer: [_a_cell_holding(peer)],
        lambda holder: holder[0].cell_contents,
        lambda peer: [_a_function_closing_over(peer)],
    ),
    "generator-frame": (
        _a_generator_holding,
        lambda holder: holder.gi_frame.f_locals["held"],
        lambda peer: [peer],
    ),
    "operator-methodcaller": (
        lambda peer: operator.methodcaller("low_road", peer),
        lambda holder: holder.__reduce__()[1][1],
        lambda peer: ("low_road", peer),
    ),
    "functools-partial-arguments": (
        lambda peer: functools.partial(print, peer),
        lambda holder: holder.args[0],
        lambda peer: (print, peer),
    ),
    "collections-deque-members": (
        lambda peer: collections.deque([peer]),
        lambda holder: holder[0],
        lambda peer: [peer],
    ),
}


@pytest.mark.parametrize("holder", sorted(_UNREAD_HOLDERS))
def test_q7_limit_a_holder_the_walk_does_not_read_is_not_seen(holder: str) -> None:
    """The holding is real and admitted inside the named holder; in a container the walk reads, it is refused."""
    wrap, dig, read_alike = _UNREAD_HOLDERS[holder]
    peer = _SubjectKeyed()
    unread = wrap(peer)
    assert dig(unread) is peer, f"the {holder} fixture does not hold the subject-keyed object where it says"
    assert _refuse_shared_owner(_Holds(unread), peer.low_road) is None
    with pytest.raises(PopulationPhaseSharesAnOwner) as refused:
        _refuse_shared_owner(_Holds(read_alike(peer)), peer.low_road)
    assert type(refused.value) is PopulationPhaseSharesAnOwner, repr(refused.value)
