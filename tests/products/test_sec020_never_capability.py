"""SEC-020, E2 (ii): a class affirming ``never`` over a projection the SDK knows can withhold is refused at construction.

Dave, 2026-10-08 12:29 MST (``D-IMPL-378``), on the owed ruling E2 (ii),
verbatim: *"E2 (ii) REJECTED as disclosure-only: The proposed hidden-subject
exception versus nonexistent-subject 200 is a measured oracle. Validate
withholding capability against the class declaration at construction; retain
the runtime check as defense. Keep the violation probe visible until the
treatment satisfies the closure criterion."* SEC-020 is OPEN.

What the SDK can know, at construction, about whether a projection withholds
— and nothing more (measured by reading the seam: the withheld signal is a
field the deployment's own ``invoke()`` sets on its output, and no operator or
declared plan step sets it):

* **Verified** — an early policy. A plan factory implementing
  ``SubjectDisclosingPlanFactoryProtocol`` returns a ``SubjectDisclosurePolicy``
  from ``subject_disclosure()``; the resolver reads it ONCE at construction and
  itself withholds every subject it does not disclose (and refuses a projection
  that then answers one). A policy that does not disclose some subject to some
  principal or role is a withholding step the SDK runs.
* **Declared** — ``subject_disclosure()`` returning ``None``: the factory's own
  public statement that its projection withholds late, inside itself.

A class affirming ``subject_withholding: never`` over either is refused by
name where its resolver is built, before any question — the same refusal
whatever subject would have been asked. A factory that declares neither
states nothing the SDK can check: it constructs, and the serve-time check
(``NeverWithholdingContradicted``) remains the defense. That configuration is
measured as still telling a withheld subject from a nonexistent one by the
closing test's E2 (ii) cells.

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any

import pytest

from ccf.graph.protocols import GraphView
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ProductNotResolvable
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.serve import ServedProduct
from tests.deployment.conftest import ARTIFACT_SET, PRODUCT_CLASS_KEY
from tests.products.composite_fixture import ask_composite, boot_composite, build_child_resolver
from tests.products.test_resolver_seam import (
    PERSPECTIVE,
    _arguments,
    _ask,
    _boot,
    _Booted,
    _plan_factory,
    _request,
    _resolver,
)

#: The refusal E2 (ii) names, read by NAME so this module states the mechanism
#: it holds without importing a symbol the tree before the change does not have.
CAPABILITY_REFUSAL = "NeverWithholdingProjectionCanWithhold"
#: The runtime defense Dave retained, by name.
SERVE_TIME_DEFENSE = "NeverWithholdingContradicted"

#: The subject every question here asks about (the fixture's own signal batch holds it).
ASKED = _request().subject
#: The identifier an early policy here asks about in place of a subject it does not disclose.
STAND_IN = "acct-undisclosed-e2ii"


def _policy(withheld: frozenset[str]) -> Any:
    """An early policy: the fixture principal is not told about ``withheld``."""
    from ccf.products.subject_disclosure import SubjectDisclosurePolicy  # noqa: PLC0415

    return SubjectDisclosurePolicy(
        undisclosed_subject=STAND_IN, by_principal={PERSPECTIVE.principal_id: withheld}, by_role={}
    )


class _Withholds:
    """The fixture's projection, withholding the subjects it is handed (the payload of a subject it cannot see)."""

    def __init__(self, inner: Any, *, request: ProductRequest, withheld: frozenset[str]) -> None:
        self._inner = inner
        self._request = request
        self._withheld = withheld

    @property
    def plan_id(self) -> str:
        return str(self._inner.plan_id)

    def required_operators(self) -> tuple[str, ...]:
        return tuple(self._inner.required_operators())

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        if self._request.subject not in self._withheld or perspective.principal_id != PERSPECTIVE.principal_id:
            return self._inner.invoke(
                view=view, operator_outputs=operator_outputs, perspective=perspective,
                temporal_boundary=temporal_boundary,
            )
        unseen = self._inner.invoke(
            view=GraphView(tenant_id=view.tenant_id, as_of=view.as_of), operator_outputs={},
            perspective=perspective, temporal_boundary=temporal_boundary,
        )
        return ProjectionOutput(plan_id=unseen.plan_id, payload=unseen.payload, withheld=True)


class _DeclaresNothingWithholds:
    """A NAMED plan factory (``D-IMPL-137``) that declares nothing, whose projection withholds ``withheld`` late."""

    def __init__(self, withheld: frozenset[str]) -> None:
        self.withheld = withheld

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        return _Withholds(_plan_factory(required=required, request=request), request=request, withheld=self.withheld)


class _DeclaresAnEarlyPolicy(_DeclaresNothingWithholds):
    """Declares an early policy (Q8) over ``withheld``; its projection withholds exactly those subjects."""

    def subject_disclosure(self) -> Any:
        return _policy(self.withheld)


class _DeclaresLateWithholding(_DeclaresNothingWithholds):
    """Declares that its projection withholds late: ``subject_disclosure()`` returns ``None``."""

    def subject_disclosure(self) -> Any:
        return None


class _EarlyPolicyNamingAnotherSubject(_DeclaresNothingWithholds):
    """Declares an early policy over a subject other than the asked one, while its projection withholds ``withheld`` late."""

    def subject_disclosure(self) -> Any:
        return _policy(frozenset({OTHER_SUBJECT}))


#: A subject an early policy here names that no question asks about.
OTHER_SUBJECT = "acct-other-e2ii"


def _never_class() -> dict[str, Any]:
    """The fixture class document, affirming ``subject_withholding: never`` (Dave's Q12)."""
    document = copy.deepcopy(next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY))
    document["subject_withholding"] = "never"
    return document


@pytest.fixture()
def never_class(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The seam's fixture deployment, its class affirming ``never``."""
    yield from _boot(tmp_path, product_class=_never_class())


@pytest.fixture()
def may_withhold_class(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, its class at the default (``may-withhold``)."""
    yield from _boot(tmp_path)


@pytest.fixture()
def never_composite(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """A composite deployment, its class affirming ``never``."""
    yield from boot_composite(tmp_path, product_class_overrides={"subject_withholding": "never"})


@pytest.fixture()
def may_withhold_composite(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """A composite deployment, its class at the default (``may-withhold``)."""
    yield from boot_composite(tmp_path)


def _construct_composite(booted: _Booted, *, plan_factory: Any) -> GovernedResolver:
    """Construct the composite's resolver — and nothing else: no question is asked."""
    arguments = _arguments(booted)
    arguments.update(composite_children=build_child_resolver(booted), plan_factory=plan_factory)
    return GovernedResolver(**arguments)


def _refused_by_name(construct: Any) -> str:
    """Construct, and return the NAME of the refusal construction raised (fails if it raised none)."""
    with pytest.raises(ProductNotResolvable) as refused:
        construct()
    return type(refused.value).__name__


def test_e2ii_a_never_class_whose_early_policy_withholds_a_subject_is_refused_at_construction(
    never_class: _Booted,
) -> None:
    """RED before E2 (ii): such a class constructs, and its undisclosed subject's question raises at serve.

    The trial lane's out-of-scope 3, measured as the same hole: the policy
    withholds the subject, the class says it never withholds, and the question
    about the subject raised ``NeverWithholdingContradicted`` where an
    identifier nothing holds was served (``probe-configs-95a9d20.txt``, C2).
    The refusal is raised by construction — no question has been asked.
    """
    refused = _refused_by_name(lambda: _resolver(never_class, plan_factory=_DeclaresAnEarlyPolicy(frozenset({ASKED}))))
    assert refused == CAPABILITY_REFUSAL, f"refused, but not by E2 (ii)'s capability check: {refused}"


def test_e2ii_a_never_class_whose_plan_factory_declares_late_withholding_is_refused_at_construction(
    never_class: _Booted,
) -> None:
    """RED before E2 (ii): the factory's own declaration that it withholds contradicts the class's affirmation."""
    refused = _refused_by_name(
        lambda: _resolver(never_class, plan_factory=_DeclaresLateWithholding(frozenset({ASKED})))
    )
    assert refused == CAPABILITY_REFUSAL, f"refused, but not by E2 (ii)'s capability check: {refused}"


def test_e2ii_a_never_composite_whose_early_policy_withholds_a_subject_is_refused_at_construction(
    never_composite: _Booted,
) -> None:
    """RED before E2 (ii): composites included — the check reads the declaration, not the shape."""
    refused = _refused_by_name(
        lambda: _construct_composite(never_composite, plan_factory=_DeclaresAnEarlyPolicy(frozenset({ASKED})))
    )
    assert refused == CAPABILITY_REFUSAL, f"refused, but not by E2 (ii)'s capability check: {refused}"


def test_e2ii_a_never_composite_declaring_late_withholding_is_refused_by_the_capability_check_first(
    never_composite: _Booted,
) -> None:
    """RED before E2 (ii): Q8 refuses this composite too (``CompositeNeedsAnEarlyPolicy``); the capability check names it first.

    The construction-time counterpart of CT-D (a)'s diagnostic precedence (Dave,
    2026-10-08 12:29 MST): for a class affirming ``never``, the contradiction
    with its own projection's declaration is named before Q8's composite rule.
    """
    refused = _refused_by_name(
        lambda: _construct_composite(never_composite, plan_factory=_DeclaresLateWithholding(frozenset({ASKED})))
    )
    assert refused == CAPABILITY_REFUSAL, f"refused, but not by E2 (ii)'s capability check first: {refused}"


def test_e2ii_control_a_never_class_whose_factory_declares_nothing_and_never_withholds_constructs_and_answers(
    never_class: _Booted,
) -> None:
    """Control: ``never`` over a projection that cannot withhold constructs, and its question is SERVED."""
    outcome = _ask(_resolver(never_class, plan_factory=_DeclaresNothingWithholds(frozenset())), _request())
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_control_a_never_class_whose_early_policy_withholds_nobody_constructs_and_answers(
    never_class: _Booted,
) -> None:
    """Control: an early policy that does not withhold any subject is no capability; the class constructs and serves."""
    outcome = _ask(_resolver(never_class, plan_factory=_DeclaresAnEarlyPolicy(frozenset())), _request())
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_control_a_may_withhold_class_with_an_early_policy_constructs_and_answers(
    may_withhold_class: _Booted,
) -> None:
    """Control: the capability is refused only against ``never``; a ``may-withhold`` class withholding early is built and answers."""
    outcome = _ask(
        _resolver(may_withhold_class, plan_factory=_DeclaresAnEarlyPolicy(frozenset({ASKED}))), _request()
    )
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_the_serve_time_check_remains_the_defense_for_a_factory_that_declares_nothing(
    never_class: _Booted,
) -> None:
    """Dave: *"retain the runtime check as defense."* A factory that declares nothing passes construction.

    Its projection withholds anyway, so the question about the withheld subject
    is refused by the serve-time check, by name, before anything is recorded or
    served. This is the defense, not indistinguishability: the closing test's
    E2 (ii) cells measure the same configuration as still telling a withheld
    subject from a nonexistent one.
    """
    resolver = _resolver(never_class, plan_factory=_DeclaresNothingWithholds(frozenset({ASKED})))
    with pytest.raises(ProductNotResolvable) as raised:
        _ask(resolver, _request())
    assert type(raised.value).__name__ == SERVE_TIME_DEFENSE, repr(raised.value)


def test_ct_d_a_never_composite_that_withholds_late_is_refused_as_never_withholding_contradicted_first(
    never_composite: _Booted,
) -> None:
    """CT-D (a) (Dave, 2026-10-08 12:29 MST): *"for diagnostic precedence; this does not resolve E2(ii)'s oracle."*

    A composite whose class affirms ``never`` and whose plan factory declares
    nothing — so it constructs — withholds the asked subject inside its
    projection. Q8 refuses that as ``CompositeWithheldLate`` and Q12 as
    ``NeverWithholdingContradicted``, both before anything is recorded; the
    class's own contradiction is named first, as its documentation says. The
    order is all this changes: the subject's question still raises where a
    nonexistent subject's is answered (the closing test's
    ``never_composite_late`` cells).
    """
    resolver = _construct_composite(never_composite, plan_factory=_DeclaresNothingWithholds(frozenset({ASKED})))
    with pytest.raises(ProductNotResolvable) as raised:
        ask_composite(resolver)
    assert type(raised.value).__name__ == SERVE_TIME_DEFENSE, repr(raised.value)


def test_ct_d_control_composite_withheld_late_remains_for_a_composite_whose_early_policy_misses_the_subject(
    may_withhold_composite: _Booted,
) -> None:
    """Control for CT-D (a): the order moved; Q8's refusal did not go away.

    A ``may-withhold`` composite with an early policy (a stance under P2 (c))
    over another subject, whose projection withholds the asked subject late, is
    still refused as ``CompositeWithheldLate`` — the one path left to it.
    """
    resolver = _construct_composite(
        may_withhold_composite, plan_factory=_EarlyPolicyNamingAnotherSubject(frozenset({ASKED}))
    )
    with pytest.raises(ProductNotResolvable) as raised:
        ask_composite(resolver)
    assert type(raised.value).__name__ == "CompositeWithheldLate", repr(raised.value)
