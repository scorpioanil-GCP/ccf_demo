"""SEC-020, E2 (ii): a class affirming ``never`` is built only over a plan factory that positively declares it never withholds.

Dave, 2026-10-08 12:29 MST (``D-IMPL-378``), on the owed ruling E2 (ii),
verbatim: *"E2 (ii) REJECTED as disclosure-only: The proposed hidden-subject
exception versus nonexistent-subject 200 is a measured oracle. Validate
withholding capability against the class declaration at construction; retain
the runtime check as defense. Keep the violation probe visible until the
treatment satisfies the closure criterion."* And at 16:40 MST, option (d),
verbatim: *"Require a positive declaration, default silence to refusal, and
explicitly limit the trusted-code assumption to deployment code callers cannot
influence. Keep the false-declaration counterexample visible."* SEC-020 is OPEN.

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

* **Positively declared** — Dave's (d): ``withholds_no_subject()`` returning
  exactly ``True`` (``NonWithholdingPlanFactoryProtocol``), the factory's own
  statement that no projection it builds withholds. The SDK cannot check it: it
  is trusted deployment code, an assumption limited to code no caller can
  influence.

A class affirming ``subject_withholding: never`` over a factory declaring that
it withholds is refused by name where its resolver is built
(``NeverWithholdingProjectionCanWithhold``); over a factory that does not
positively declare that it never withholds — silence, or any value but
``True`` — likewise, after it (``NeverWithholdingNeedsAPositiveDeclaration``):
silence counts as able to withhold. Each is the same refusal whatever subject
would have been asked; the tests here build the resolver with no question
asked, and one asks the paved road (a resolver per question) about three
subjects and finds the one refusal, with nothing fetched. A factory whose
positive declaration is FALSE constructs, and the serve-time check
(``NeverWithholdingContradicted``) remains the defense; that configuration still
tells a withheld subject from a nonexistent one, and it is kept visible as the
residual of the trusted-code assumption.

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Callable, Iterator, Mapping
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
#: The refusal E2 (ii) (d) names for a factory that does not positively declare
#: that it never withholds, read by NAME for the same reason.
DECLARATION_REFUSAL = "NeverWithholdingNeedsAPositiveDeclaration"
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


class _DeclaresNeverWithholding(_DeclaresNothingWithholds):
    """Positively declares that its projection never withholds (``withholds_no_subject()`` returns ``True``).

    The declaration is TRUE with an empty ``withheld``; with a subject in it,
    it is FALSE — the configuration Dave's (d) leaves to trusted deployment code.
    """

    def withholds_no_subject(self) -> bool:
        return True


class _DeclaresWith(_DeclaresNothingWithholds):
    """``withholds_no_subject()`` returns ``value``; only exactly ``True`` is a positive declaration."""

    def __init__(self, withheld: frozenset[str], *, value: Any) -> None:
        super().__init__(withheld)
        self.value = value

    def withholds_no_subject(self) -> Any:
        return self.value


class _DeclaresAnEarlyPolicyAndNeverWithholding(_DeclaresAnEarlyPolicy):
    """An early policy over ``withheld``, and the positive declaration that the projection never withholds."""

    def withholds_no_subject(self) -> bool:
        return True


class _DeclaresLateWithholdingAndNeverWithholding(_DeclaresLateWithholding):
    """Contradicts itself: ``subject_disclosure()`` says it withholds late, ``withholds_no_subject()`` says never."""

    def withholds_no_subject(self) -> bool:
        return True


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


def test_e2ii_d_a_never_class_whose_plan_factory_declares_nothing_is_refused_at_construction(
    never_class: _Booted,
) -> None:
    """RED before E2 (ii) (d): silence counts as able to withhold — even over a projection that does not withhold.

    Dave, 2026-10-08 16:40 MST, option (d): *"Require a positive declaration,
    default silence to refusal"*. This replaces the control that held the
    opposite (a factory declaring nothing constructed under ``never``): the
    factory here never withholds and says nothing, and the class is refused
    where its resolver is built, by name — no question has been asked.
    """
    refused = _refused_by_name(lambda: _resolver(never_class, plan_factory=_DeclaresNothingWithholds(frozenset())))
    assert refused == DECLARATION_REFUSAL, f"refused, but not for want of a positive declaration: {refused}"


def test_e2ii_d_a_never_class_whose_silent_plan_factory_withholds_is_refused_at_construction(
    never_class: _Booted,
) -> None:
    """RED before E2 (ii) (d): the configuration the closing test's ``never_late`` cells measure, refused before any question.

    Before (d) it constructed, and the withheld subject's question alone met the
    serve-time defense — the oracle Dave ruled.
    """
    refused = _refused_by_name(
        lambda: _resolver(never_class, plan_factory=_DeclaresNothingWithholds(frozenset({ASKED})))
    )
    assert refused == DECLARATION_REFUSAL, f"refused, but not for want of a positive declaration: {refused}"


def test_e2ii_d_a_never_composite_whose_silent_plan_factory_withholds_is_refused_at_construction(
    never_composite: _Booted,
) -> None:
    """RED before E2 (ii) (d): composites too (``never_composite_late``); ``never`` alone no longer states a composite's stance."""
    refused = _refused_by_name(
        lambda: _construct_composite(never_composite, plan_factory=_DeclaresNothingWithholds(frozenset({ASKED})))
    )
    assert refused == DECLARATION_REFUSAL, f"refused, but not for want of a positive declaration: {refused}"


@pytest.mark.parametrize("value", [False, None, 1, "True"], ids=["false", "none", "one", "the-string-True"])
def test_e2ii_d_a_declaration_other_than_exactly_true_is_refused_at_construction(
    never_class: _Booted, value: Any
) -> None:
    """RED before E2 (ii) (d): only ``True`` itself is a positive declaration; ``False`` and look-alikes are refused."""
    refused = _refused_by_name(lambda: _resolver(never_class, plan_factory=_DeclaresWith(frozenset(), value=value)))
    assert refused == DECLARATION_REFUSAL, f"refused, but not for want of a positive declaration: {refused}"


class _SilentPolicyFactory:
    """The closing test's late policy (``sec020_worlds.PolicyPlanFactory``) with NO declaration of any kind."""

    def __init__(self, *, active: bool) -> None:
        from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415
        from tests.products import sec020_worlds as w  # noqa: PLC0415

        self._inner = w.PolicyPlanFactory(plan_id=PRODUCT_CLASS, asker=w.ASKER, active=active)

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        return self._inner(required=required, request=request)


class _DeclaringPolicyFactory(_SilentPolicyFactory):
    """The same policy, positively declaring that it never withholds (TRUE with the policy off)."""

    def withholds_no_subject(self) -> bool:
        return True


def _paved_outcomes(base: pathlib.Path, *, project: Callable[[], Any]) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Ask a ``never`` class on the paved road about three subjects; each outcome as (type, text), and what was fetched.

    The class's tenant does not list it, so nothing here reaches the record
    channel. A deployment whose source holds the subject is asked about it and
    about an identifier nothing holds; one whose source does not hold it is
    asked about the subject.
    """
    from tests.products import sec020_worlds as w  # noqa: PLC0415

    holding_source = w.SubjectKeyedSource({w.SUBJECT: w.subject_holding()})
    empty_source = w.SubjectKeyedSource({})
    outcomes: dict[str, tuple[str, str]] = {}
    for name, source, subject in (
        ("withheld", holding_source, w.SUBJECT),
        ("never-held", holding_source, w.NEVER),
        ("nonexistent", empty_source, w.SUBJECT),
    ):
        try:
            deployment = w.open_paved(base / name, anchor=w.FROM_DECISION, acquire=source, project=project(), never=True)
        except Exception as refused:  # noqa: BLE001 — a refusal at open is an outcome
            outcomes[name] = (type(refused).__name__, str(refused))
            continue
        try:
            answered = deployment.ask(subject, None)
            outcomes[name] = (type(answered).__name__, "")
        except Exception as refused:  # noqa: BLE001 — the observation
            outcomes[name] = (type(refused).__name__, str(refused))
        finally:
            deployment.close()
    return outcomes, [*holding_source.asked, *empty_source.asked]


def test_e2ii_d_the_paved_road_refuses_every_subject_alike_before_anything_is_fetched(tmp_path: pathlib.Path) -> None:
    """RED before E2 (ii) (d): the one refusal for every subject, decided before acquisition.

    The paved road builds a resolver per question, so the construction refusal
    surfaces when a question arrives. A ``never`` class over a silent factory
    whose projection withholds the held subject: the question about that
    subject, about an identifier nothing holds, and about the subject in a
    deployment that does not hold it each raise the same refusal, by name, with
    the same text; and no source was asked anything. Before (d) the withheld
    subject's question raised the serve-time defense while the others were
    answered.
    """
    outcomes, fetched = _paved_outcomes(tmp_path, project=lambda: _SilentPolicyFactory(active=True))
    assert {kind for kind, _text in outcomes.values()} == {DECLARATION_REFUSAL}, outcomes
    assert len({text for _kind, text in outcomes.values()}) == 1, f"one refusal, but its text differs by subject: {outcomes}"
    assert fetched == [], f"a source was asked before the refusal: {fetched}"


def test_e2ii_d_control_the_paved_road_answers_and_fetches_for_a_positively_declaring_factory(
    tmp_path: pathlib.Path,
) -> None:
    """Control: the same deployments over the policy-off factory that positively declares it — every question answered, the source asked."""
    outcomes, fetched = _paved_outcomes(tmp_path, project=lambda: _DeclaringPolicyFactory(active=False))
    assert {kind for kind, _text in outcomes.values()} == {"ServedProduct"}, outcomes
    assert fetched, "control: no source was asked, so the refusal's 'nothing fetched' could not have been seen"


def test_e2ii_d_control_a_positively_declaring_never_class_constructs_and_answers(never_class: _Booted) -> None:
    """Control: ``never`` over a factory that positively declares it, whose projection never withholds, is SERVED."""
    outcome = _ask(_resolver(never_class, plan_factory=_DeclaresNeverWithholding(frozenset())), _request())
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_d_control_a_positively_declaring_never_composite_constructs_and_answers(
    never_composite: _Booted,
) -> None:
    """Control: the composite counterpart — ``never`` with the positive declaration is a stance, and it is SERVED."""
    outcome = ask_composite(_construct_composite(never_composite, plan_factory=_DeclaresNeverWithholding(frozenset())))
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_d_control_a_may_withhold_class_over_a_silent_factory_is_not_refused(
    may_withhold_class: _Booted,
) -> None:
    """Control: the positive declaration is required only under ``never``; a ``may-withhold`` class over a silent, withholding factory is built and answers."""
    outcome = _ask(
        _resolver(may_withhold_class, plan_factory=_DeclaresNothingWithholds(frozenset({ASKED}))), _request()
    )
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_d_control_a_declared_capability_is_named_before_a_contradicting_positive_declaration(
    never_class: _Booted,
) -> None:
    """Control: a factory declaring late withholding AND that it never withholds is named by the declared capability, exactly."""
    refused = _refused_by_name(
        lambda: _resolver(never_class, plan_factory=_DeclaresLateWithholdingAndNeverWithholding(frozenset({ASKED})))
    )
    assert refused == CAPABILITY_REFUSAL, f"refused, but not by the declared capability first: {refused}"


def test_e2ii_control_a_never_class_whose_early_policy_withholds_nobody_constructs_and_answers(
    never_class: _Booted,
) -> None:
    """Control: an early policy that withholds nobody is no capability; with the positive declaration, the class constructs and serves."""
    outcome = _ask(
        _resolver(never_class, plan_factory=_DeclaresAnEarlyPolicyAndNeverWithholding(frozenset())), _request()
    )
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_control_a_may_withhold_class_with_an_early_policy_constructs_and_answers(
    may_withhold_class: _Booted,
) -> None:
    """Control: the capability is refused only against ``never``; a ``may-withhold`` class withholding early is built and answers."""
    outcome = _ask(
        _resolver(may_withhold_class, plan_factory=_DeclaresAnEarlyPolicy(frozenset({ASKED}))), _request()
    )
    assert isinstance(outcome, ServedProduct), outcome


def test_e2ii_the_serve_time_check_remains_the_defense_for_a_false_positive_declaration(
    never_class: _Booted,
) -> None:
    """Dave: *"retain the runtime check as defense."* A factory whose positive declaration is FALSE passes construction.

    Under (d) only a positive declaration passes construction, so the defense is
    reached only through a false one — trusted deployment code. Its projection
    withholds anyway, so the question about the withheld subject is refused by
    the serve-time check, by name, before anything is recorded or served. This
    is the defense, not indistinguishability: the withheld subject's question
    still raises where a nonexistent subject's is answered, the residual (d)
    keeps visible.
    """
    resolver = _resolver(never_class, plan_factory=_DeclaresNeverWithholding(frozenset({ASKED})))
    with pytest.raises(ProductNotResolvable) as raised:
        _ask(resolver, _request())
    assert type(raised.value).__name__ == SERVE_TIME_DEFENSE, repr(raised.value)


def test_ct_d_a_never_composite_that_withholds_late_is_refused_as_never_withholding_contradicted_first(
    never_composite: _Booted,
) -> None:
    """CT-D (a) (Dave, 2026-10-08 12:29 MST): *"for diagnostic precedence; this does not resolve E2(ii)'s oracle."*

    A composite whose class affirms ``never`` and whose plan factory positively
    declares that it never withholds — so it constructs; under E2 (ii) (d) only
    such a factory does, and here the declaration is FALSE — withholds the asked
    subject inside its projection. Q8 refuses that as ``CompositeWithheldLate``
    and Q12 as ``NeverWithholdingContradicted``, both before anything is
    recorded; the class's own contradiction is named first, as its
    documentation says. The order is all this changes: the subject's question
    still raises where a nonexistent subject's is answered.
    """
    resolver = _construct_composite(never_composite, plan_factory=_DeclaresNeverWithholding(frozenset({ASKED})))
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
