"""SEC-020, P2 (c) — a CANDIDATE: every composite declares its withholding stance at construction.

``D-IMPL-378`` owed ruling P2 (``records/2026-10-08-d-impl-378-ci-lane/OWED-RULINGS.md``
on ``dl-378-record``): composites that decide to withhold late. Dave has NOT
ruled it; option (c), which the coordinator recommends, is built here so its
effect can be measured. SEC-020 is OPEN.

Dave, Q8 (2026-10-07): *"Require early withholding for affected composites.
Make it an enforced policy decision before subject-dependent fetches, child
resolution or scoring. It cannot depend on learning whether the subject
exists."* The SDK cannot see at construction whether a projection will
withhold, and a refusal decided when a projection withholds is decided for
the withheld subject only — the closing test measured that error as itself
telling the hidden subject apart (a crash for it, an answer for an unknown
one). Under (c) a composite — a class that declares ``requires`` — states its
stance when its resolver is built: an early policy
(``SubjectDisclosingPlanFactoryProtocol.subject_disclosure()`` returning a
``SubjectDisclosurePolicy``) or its class's affirmation that its answers never
withhold their subject (``subject_withholding: never``, Dave's Q12, enforced
at serve). A composite declaring neither is refused by name at construction,
before any question, so the refusal is the same whatever subject is asked.

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any

import pytest

from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, UnsupportedComposition
from tests.products.composite_fixture import _Booted, boot_composite, build_child_resolver
from tests.products.test_resolver_seam import _arguments, _plan_factory
from tests.products.test_withheld_subject_population_composite_and_fabric import _policy

#: The refusal P2 (c) names, read by NAME so this module states the mechanism it
#: holds without importing a symbol the tree before the change does not have.
STANCE_REFUSAL = "CompositeNeedsAWithholdingStance"


class _DeclaresNothing:
    """A NAMED plan factory (``D-IMPL-137``) that declares no withholding stance."""

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        return _plan_factory(required=required, request=request)


class _DeclaresAnEarlyPolicy(_DeclaresNothing):
    """The same factory, declaring an early policy (Q8) that withholds nothing."""

    def subject_disclosure(self) -> Any:
        return _policy(frozenset())


@pytest.fixture()
def composite(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """A deployment whose class composes a child, its class declaring no affirmation."""
    yield from boot_composite(tmp_path)


@pytest.fixture()
def composite_affirming_never(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, its class affirming ``subject_withholding: never`` (Dave's Q12)."""
    yield from boot_composite(tmp_path, product_class_overrides={"subject_withholding": "never"})


def _construct(booted: _Booted, *, plan_factory: Any) -> GovernedResolver:
    """Construct the composite's resolver — and nothing else: no question is asked."""
    arguments = _arguments(booted)
    arguments.update(composite_children=build_child_resolver(booted), plan_factory=plan_factory)
    return GovernedResolver(**arguments)


def test_p2c_a_composite_declaring_no_withholding_stance_is_refused_at_construction(composite: _Booted) -> None:
    """RED before P2 (c): such a composite constructs, and decides any withhold late.

    The refusal is raised by the resolver's construction — no question has been
    asked, so it cannot depend on any subject — and it is P2 (c)'s own,
    by name, an ``UnsupportedComposition`` like Q7-Q9's construction refusals.
    """
    with pytest.raises(UnsupportedComposition) as refused:
        _construct(composite, plan_factory=_DeclaresNothing())
    assert type(refused.value).__name__ == STANCE_REFUSAL, (
        f"the composition was refused, but not by P2 (c)'s stance check: {type(refused.value).__name__}: {refused.value}"
    )


def test_p2c_a_composite_declaring_an_early_policy_constructs(composite: _Booted) -> None:
    """Control: the early-policy stance (Q8) is a declaration; the composite constructs."""
    assert isinstance(_construct(composite, plan_factory=_DeclaresAnEarlyPolicy()), GovernedResolver)


def test_p2c_a_composite_whose_class_affirms_never_constructs(composite_affirming_never: _Booted) -> None:
    """Control: the never-withholds stance (Q12) is a declaration; the composite constructs."""
    assert isinstance(_construct(composite_affirming_never, plan_factory=_DeclaresNothing()), GovernedResolver)
