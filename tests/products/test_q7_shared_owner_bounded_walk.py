"""SEC-020 Q7: what the shared-owner guard refuses, under Dave's decision 3 (a) (``D-IMPL-378``, 2026-10-09).

SEC-020 is OPEN: these tests measure the mechanism Dave ruled; they close
nothing. Lane ``378i-q7owner``.

The ruling, verbatim (the 06:06 MST list, confirmed as "3a" at 06:21 MST):
*"(a). Extend the shared-state guard, with a bounded walk and an explicit
statement of what it cannot detect."* The option that letter names (the final
panel's brief, section 2.C): *"extend the guard to a bounded reachability walk
(attributes of held objects, containers in closure cells) and disclose what
remains undetectable."*

The hole (the panel's G-Q7-OWNER, probe ``panel/probes/p_b01_q7_owner.py`` on
``dl-378-record``): ``src/ccf/products/resolver.py::_refuse_shared_owner`` read
the two phases, the objects they are bound to and one level of their closure
cells. A population phase holding the subject-keyed phase's object as an
ATTRIBUTE (shape A), or whose closure holds a CONTAINER holding it (shape C),
was admitted, while the security how-to, section 4.12, says a phase holding
the other is refused. State on that object carries the subject the
subject-keyed phase was handed into a later question's population phase
(Q7: *"Subject-independent acquisition must not receive the requested subject
indirectly through context or closures. Unsupported combinations must refuse
construction."*).

Asserted at both places the guard runs — a ``GovernedResolver`` built by hand,
and ``open_product`` on the paved road:

* every way of holding the subject-keyed phase's object listed in
  :data:`_HOLDING_SHAPES` is refused by name,
  :class:`~ccf.products.resolver.PopulationPhaseSharesAnOwner`; each shape is
  first shown to hold the object where its name says, so no case passes
  without the holding it names;
* so is the reverse: the subject-keyed phase's object holding the population
  phase;
* the probe's two controls (both phases on one object; a closure holding the
  subject-keyed phase itself) are still refused, and so is a method whose
  function's closure holds the subject-keyed phase's object, which the guard
  already read;
* two phases that share nothing are still admitted.

Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import collections
import pathlib
import types
from collections.abc import Callable
from typing import Any, NamedTuple

import pytest

from ccf.products.product import AcquisitionContext, OpenedProduct
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, PopulationPhaseSharesAnOwner
from ccf.projection.plan import Perspective
from ccf.signal.envelope import SignalEnvelope
from tests.products import test_withheld_is_indistinguishable_from_absent as sec020
from tests.products.test_withheld_subject_population_composite_and_fabric import (
    _base_accounts,
    _boot,
    _governed,
    _late,
)

#: The two places the guard runs: a resolver built by hand, and the paved road at open.
SITES = ("resolver", "open_product")


class _SubjectKeyed:
    """The subject-keyed phase's object. It keeps the subject it was last asked about: the state Q7 guards."""

    def __init__(self) -> None:
        self.last: str | None = None

    def low_road(self, *, request: ProductRequest, perspective: Perspective) -> None:
        self.last = request.subject

    def paved(self, context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
        self.last = context.request.subject
        return ()

    def population(self, *_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        """A population phase bound to this same object: the probe's first control."""
        return ()


class _SubjectKeyedHolding(_SubjectKeyed):
    """A subject-keyed phase's object that holds the population phase as an attribute (the reverse direction)."""

    def __init__(self, held: object) -> None:
        super().__init__()
        self.held = held


class _Population:
    """A population phase on an object of its own, keeping only its own state."""

    def __init__(self) -> None:
        self.read: list[str] = []

    def __call__(self, *_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return ()


class _HoldsAsAttribute(_Population):
    """A population phase holding ``peer`` as an attribute (shape A)."""

    def __init__(self, peer: object) -> None:
        super().__init__()
        self.peer = peer


class _HoldsInASlot:
    """A population phase holding ``peer`` in a declared slot."""

    __slots__ = ("peer",)

    def __init__(self, peer: object) -> None:
        self.peer = peer

    def __call__(self, *_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return ()


class _Holder:
    """An object between the population phase and ``peer``."""

    def __init__(self, held: object) -> None:
        self.held = held


class _Pair(NamedTuple):
    """A ``tuple`` subclass."""

    first: object
    second: object


def _closure_over(held: object) -> Callable[..., tuple[SignalEnvelope, ...]]:
    """A population phase whose closure holds ``held``."""

    def population(*_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return () if held is not None else ()

    return population


def _positional_default(held: object) -> Callable[..., tuple[SignalEnvelope, ...]]:
    """A population phase holding ``held`` as a positional default argument."""

    def population(
        question: object = None, perspective: object = None, held: object = held
    ) -> tuple[SignalEnvelope, ...]:
        return ()

    return population


def _keyword_default(held: object) -> Callable[..., tuple[SignalEnvelope, ...]]:
    """A population phase holding ``held`` as a keyword-only default argument."""

    def population(*_: object, held: object = held, **__: object) -> tuple[SignalEnvelope, ...]:
        return ()

    return population


def _function_attribute(held: object) -> Callable[..., tuple[SignalEnvelope, ...]]:
    """A population phase, a plain function, holding ``held`` as one of its own attributes."""

    def population(*_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return ()

    population.held = held  # type: ignore[attr-defined]
    return population


def _a_cycle_before(held: object) -> list[object]:
    """A list holding itself, and then a holder of ``held``."""
    cycle: list[object] = []
    cycle.append(cycle)
    cycle.append(_Holder(held))
    return cycle


def _method_closing_over(held: object) -> Callable[..., tuple[SignalEnvelope, ...]]:
    """A population phase that is a bound method whose function's closure holds ``held``."""

    def population(self: object, *_: object, **__: object) -> tuple[SignalEnvelope, ...]:
        return () if held is not None else ()

    return types.MethodType(population, _Population())


def _cell(phase: Any) -> Any:
    """The one closure cell's contents of ``phase``."""
    (cell,) = phase.__closure__
    return cell.cell_contents


#: Each way a population phase can hold the subject-keyed phase's object
#: ``peer``: (build the population phase from ``peer``, dig ``peer`` back out of
#: it along the path the name states). Shapes A and C are the panel probe's.
_HOLDING_SHAPES: dict[str, tuple[Callable[[_SubjectKeyed], Any], Callable[[Any], Any]]] = {
    "A-attribute": (_HoldsAsAttribute, lambda phase: phase.peer),
    "C-closure-tuple": (lambda peer: _closure_over((peer,)), lambda phase: _cell(phase)[0]),
    "closure-list": (lambda peer: _closure_over([peer]), lambda phase: _cell(phase)[0]),
    "closure-set": (lambda peer: _closure_over({peer}), lambda phase: next(iter(_cell(phase)))),
    "closure-frozenset": (lambda peer: _closure_over(frozenset({peer})), lambda phase: next(iter(_cell(phase)))),
    "closure-dict-value": (lambda peer: _closure_over({"held": peer}), lambda phase: _cell(phase)["held"]),
    "closure-dict-key": (lambda peer: _closure_over({peer: "held"}), lambda phase: next(iter(_cell(phase)))),
    "slot": (_HoldsInASlot, lambda phase: phase.peer),
    "attribute-of-a-held-object": (lambda peer: _HoldsAsAttribute(_Holder(peer)), lambda phase: phase.peer.held),
    "positional-default": (_positional_default, lambda phase: phase.__defaults__[2]),
    "keyword-only-default": (_keyword_default, lambda phase: phase.__kwdefaults__["held"]),
    # Another bound method of ``peer`` in a container: ``peer`` is that method's ``__self__``.
    "closure-list-of-a-bound-method": (
        lambda peer: _closure_over([peer.low_road]),
        lambda phase: _cell(phase)[0].__self__,
    ),
    "function-attribute": (_function_attribute, lambda phase: phase.held),
    # A builtin type whose instances keep their attributes in an instance dictionary.
    "closure-simple-namespace": (
        lambda peer: _closure_over(types.SimpleNamespace(held=peer)),
        lambda phase: _cell(phase).held,
    ),
    "closure-dict-subclass-value": (
        lambda peer: _closure_over(collections.defaultdict(list, {"held": peer})),
        lambda phase: _cell(phase)["held"],
    ),
    "closure-tuple-subclass": (lambda peer: _closure_over(_Pair(peer, None)), lambda phase: _cell(phase).first),
    "closure-cycle-then-holder": (lambda peer: _closure_over(_a_cycle_before(peer)), lambda phase: _cell(phase)[1].held),
}


def _compose(site: str, tmp_path: pathlib.Path, *, population: Any, peer: _SubjectKeyed) -> object:
    """Compose the two phases at ``site``: ``peer``'s subject-keyed phase, and ``population``."""
    if site == "resolver":
        booted = _boot(tmp_path, "q7", anchor=sec020.FROM_DECISION, envelopes=_base_accounts(), for_question=True)
        try:
            return _governed(booted, plan_factory=_late(), acquisition=peer.low_road, population_acquisition=population)
        finally:
            booted[0].handle.close()
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=sec020.FROM_DECISION, seeding=sec020.CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=peer.paved, population=population) as opened:
        return opened


def _admitted(site: str, composed: object) -> bool:
    """What the site returns when the two phases are admitted."""
    return isinstance(composed, GovernedResolver if site == "resolver" else OpenedProduct)


@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize("shape", sorted(_HOLDING_SHAPES))
def test_q7_a_population_phase_holding_the_subject_keyed_object_is_refused(
    tmp_path: pathlib.Path, shape: str, site: str
) -> None:
    """Each holding shape is refused by name, ``PopulationPhaseSharesAnOwner``, at construction and at open."""
    build, dig = _HOLDING_SHAPES[shape]
    peer = _SubjectKeyed()
    population = build(peer)
    assert dig(population) is peer, f"the {shape} fixture does not hold the subject-keyed object where it says"
    with pytest.raises(PopulationPhaseSharesAnOwner):
        _compose(site, tmp_path, population=population, peer=peer)


@pytest.mark.parametrize("site", SITES)
def test_q7_a_subject_keyed_phase_holding_the_population_phase_is_refused(tmp_path: pathlib.Path, site: str) -> None:
    """The reverse direction: the subject-keyed phase's object holds the population phase as an attribute."""
    population = _Population()
    peer = _SubjectKeyedHolding(population)
    assert peer.held is population
    with pytest.raises(PopulationPhaseSharesAnOwner):
        _compose(site, tmp_path, population=population, peer=peer)


@pytest.mark.parametrize("site", SITES)
def test_q7_control_both_phases_bound_to_one_object_is_refused(tmp_path: pathlib.Path, site: str) -> None:
    """The probe's first control, refused before the change and after."""
    peer = _SubjectKeyed()
    with pytest.raises(PopulationPhaseSharesAnOwner):
        _compose(site, tmp_path, population=peer.population, peer=peer)


@pytest.mark.parametrize("site", SITES)
def test_q7_control_a_closure_holding_the_subject_keyed_phase_is_refused(tmp_path: pathlib.Path, site: str) -> None:
    """The probe's second control: the closure holds the subject-keyed bound method itself."""
    peer = _SubjectKeyed()
    held = peer.low_road if site == "resolver" else peer.paved
    population = _closure_over(held)
    assert _cell(population).__self__ is peer
    with pytest.raises(PopulationPhaseSharesAnOwner):
        _compose(site, tmp_path, population=population, peer=peer)


@pytest.mark.parametrize("site", SITES)
def test_q7_control_a_method_whose_function_closes_over_the_subject_keyed_object_is_refused(
    tmp_path: pathlib.Path, site: str
) -> None:
    """A bound method's function closure, which the guard read before the walk, is still read."""
    peer = _SubjectKeyed()
    population = _method_closing_over(peer)
    assert _cell(population.__func__) is peer
    with pytest.raises(PopulationPhaseSharesAnOwner):
        _compose(site, tmp_path, population=population, peer=peer)


@pytest.mark.parametrize("site", SITES)
def test_q7_twin_two_phases_that_share_nothing_are_admitted(tmp_path: pathlib.Path, site: str) -> None:
    """No false positive: a population phase and a subject-keyed phase on unrelated objects are composed."""
    composed = _compose(site, tmp_path, population=_Population(), peer=_SubjectKeyed())
    assert _admitted(site, composed), repr(composed)
