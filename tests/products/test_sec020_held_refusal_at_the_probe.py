"""SEC-020, OWED-RULINGS-3 item 4 (b): a held refusal at ruling P6 (a)'s probe refuses the question. SEC-020 is OPEN.

``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). The configuration: a class that
may withhold its subject and declares no early policy, so ruling P6 (a) asks
its subject-keyed acquisition phase about
``ccf.products.resolver.UNHELD_SUBJECT_PROBE`` before the question's subject;
and a source keyed on the subject that answers an identifier it does not hold
with a HELD refusal — a ``GovernedRefusalRaised`` (``subject-unavailable``), or
a record whose identity L2 refuses (``ccf.assembly.worker.IdentityRefused``,
one of the SDK's own declared seam refusals). As built under P6 (a), a held
refusal from the probe counted as "acquired nothing", so the question went on:
the withheld subject was answered (withheld inside the projection) while an
identifier nothing holds was refused ``subject-unavailable`` — told apart, on
both roads and both anchors (lane ``378f-p6a`` section 6 finding 1, measured
again on this branch's base).

Dave's ruling, 2026-10-09 06:21 MST, on OWED-RULINGS-3 item 4, is kept verbatim
as a comment below; option (b) as the sheet worded it, too.

What these tests hold the SDK to, by mechanism:

* **The refusal.** Every question to such a deployment is refused by name,
  ``UnheldSubjectProbeRefused``, a withheld subject's, an identifier nothing
  holds and an ordinarily served subject's alike, with one message, when the
  probe call itself ends in a held refusal; the subject-keyed phase is handed
  the probe identifier and never the asked subject; and nothing is recorded.
  On the paved road (``open_product``) and the low road (``GovernedResolver``
  composed by hand).

The controls are green before and after: the same deployment with a source
that answers an identifier it does not hold with "acquired nothing" (the
supported working twin, SEC-020's ``subject_keyed`` world) answers every
question; a class affirming ``subject_withholding: never`` over the refusing
source is not probed, and its unheld identifier is refused as data; a class
declaring an early policy over the refusing source is not probed by P6 either,
and its withheld and nonexistent questions are both refused as data.
"""

# Dave, 2026-10-09 06:21 MST, verbatim (D-IMPL-378 dated amendment on main @ d429dcfa),
# OWED-RULINGS-3 items 1-7:
#   "4(b), plus the closing-test case and a supported working twin"
# OWED-RULINGS-3 (dl-378-record @ 3533cc89), item 4, option (b), verbatim:
#   "Refuse when the probe call itself returns a held refusal (refuses every
#   question to a source that refuses unknown identifiers)."
# Dave, 2026-10-08 12:29 MST, CT-A (a), verbatim: "Construction refusal counts,
# paired with a declared twin that successfully answers."

from __future__ import annotations

import pathlib
import re
from typing import Any

import pytest

import ccf.products.resolver as resolver_module
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.products.resolver import UnsupportedComposition
from tests.deployment.test_replay_binding import PRODUCT_CLASS
from tests.products import sec020_worlds as w
from tests.products import test_withheld_similarity_registry as low

#: The refusal item 4 (b) raises, named as data so this module collects on a
#: tree that does not have it yet (the red commit) and fails there by
#: ``DID NOT RAISE`` rather than by an import error.
REFUSAL = "UnheldSubjectProbeRefused"
#: The two held refusals a source can answer an unheld identifier with: the
#: typed handoff, and the SDK-declared seam refusal L2 raises for a record whose
#: identity value names no entity.
GOVERNED = "governed-refusal-raised"
IDENTITY = "identity-refused"
HOW = (GOVERNED, IDENTITY)


def _probe() -> Any:
    return getattr(resolver_module, "UNHELD_SUBJECT_PROBE", None)


def _held_refusal() -> GovernedRefusalRaised:
    """The typed handoff a source raises for an identifier it does not hold."""
    return GovernedRefusalRaised(
        SubjectUnavailableRefusal(
            cause="nonexistent", detail="the source holds no such subject", error_code=None
        ),
        resolution=RESOLVED_BY_THE_RESOLVER,
    )


def _records(store: Any) -> frozenset[str]:
    """The content-addressed artifacts a deployment's store holds (its records and pins)."""
    root = getattr(store, "inner", store).root
    return frozenset(path.name for path in root.iterdir() if re.fullmatch(r"[0-9a-f]{64}", path.name))


class HeldRefusalSource(w.SubjectKeyedSource):
    """The paved road's ``acquire``: claims for a subject it holds, a HELD refusal for any other identifier."""

    def __init__(self, holdings: Any, *, how: str) -> None:
        super().__init__(holdings)
        self._how = how

    def __call__(self, context: Any) -> Any:
        subject = context.request.subject
        if subject in self._holdings:
            return super().__call__(context)
        self.asked.append(subject)
        if self._how == GOVERNED:
            raise _held_refusal()
        # A record whose declared identity value is empty: L2 refuses it,
        # ``IdentityRefused``, which the SDK declares at this seam.
        blank = w.Holding(account_ref="", book=w.OPEN_BOOK, label="no identity", observed_at=w.asked_at())
        return (w.envelope_for(blank, tenant=context.tenant_id, ingested_at=context.instant),)


def _paved(base: pathlib.Path, anchor: str, *, how: str | None, active: bool, never: bool = False,
           early: bool = False) -> tuple[w.Deployment, Any]:
    """SEC-020's subject-keyed paved deployment holding the subject, its source refusing what it does not hold.

    ``how=None`` is the supported working twin: the same deployment with the
    source answering an identifier it does not hold with nothing.
    """
    holdings = {w.SUBJECT: w.subject_holding()}
    source = w.SubjectKeyedSource(holdings) if how is None else HeldRefusalSource(holdings, how=how)
    built = w.open_paved(
        base, anchor=anchor, acquire=source,
        project=w.plan_factory(early=early, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=active),
        never=never,
    )
    return built, source


def _refused_by_name(asks: dict[str, Any]) -> dict[str, UnsupportedComposition]:
    """Ask each side; every question must raise item 4 (b)'s refusal, by type name, worded once."""
    refused: dict[str, UnsupportedComposition] = {}
    for side, (ask, store) in asks.items():
        before = _records(store)
        with pytest.raises(UnsupportedComposition) as raised:
            ask()
        refused[side] = raised.value
        assert _records(store) == before, f"[{side}] a refused question recorded something"
    names = {side: type(error).__name__ for side, error in refused.items()}
    assert set(names.values()) == {REFUSAL}, names
    messages = {str(error) for error in refused.values()}
    assert len(messages) == 1, f"one refusal for every subject, worded once: {sorted(messages)}"
    return refused


# --- the paved road: SEC-020's own subject-keyed deployment ----------------------------


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_a_held_refusal_at_the_probe_refuses_every_question_on_the_paved_road(
    tmp_path: pathlib.Path, anchor: str, how: str
) -> None:
    """A withheld subject, an identifier nothing holds and a served subject: each refused, by name, at the probe."""
    withholding, withholding_source = _paved(tmp_path / "withholding", anchor, how=how, active=True)
    serving, serving_source = _paved(tmp_path / "serving", anchor, how=how, active=False)
    try:
        _refused_by_name({
            "withheld": (lambda: withholding.ask(w.SUBJECT, None), withholding.store),
            "nonexistent": (lambda: withholding.ask(w.NEVER, None), withholding.store),
            "served": (lambda: serving.ask(w.SUBJECT, None), serving.store),
        })
    finally:
        withholding.close()
        serving.close()
    for name, source in (("withholding", withholding_source), ("serving", serving_source)):
        assert source.asked and set(source.asked) == {_probe()}, (
            f"[{name}] the subject-keyed phase is handed the probe identifier and never the asked"
            f" subject: {source.asked}"
        )


# --- the low road: a hand-composed resolver, its seam refusing what it does not hold --------


class _HeldRefusalSeam(low._SubjectKeyedRefresh):
    """A low-road seam keyed on the subject: the withheld account's fresher claim, a HELD refusal for any other."""

    def __init__(self, fabric: Any, *, text: str, how: str) -> None:
        super().__init__(fabric, text=text)
        self._how = how
        self.asked: list[str] = []

    def __call__(self, *, request: Any, perspective: Any) -> None:
        self.asked.append(request.subject)
        if request.subject == low.WITHHELD:
            super().__call__(request=request, perspective=perspective)
            return
        if self._how == GOVERNED:
            raise _held_refusal()
        self._fabric.handle.worker.ingest(
            low._claim("", "no identity", envelope_id="claim-blank-identity", observed=low.OBSERVED)
        )


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_a_held_refusal_at_the_probe_refuses_every_question_on_the_low_road(
    tmp_path: pathlib.Path, anchor: str, how: str
) -> None:
    """``GovernedResolver(acquisition=...)`` whose seam refuses an identifier it does not hold: refused alike."""
    seams: dict[str, _HeldRefusalSeam] = {}

    def ask(side: str, subject: str, withhold: frozenset[str]) -> tuple[Any, Any]:
        booted = low._boot(tmp_path / side, with_similarity=False, anchor=anchor)
        seams[side] = _HeldRefusalSeam(booted[0], text=low.QUERY, how=how)

        def question() -> Any:
            try:
                return low._serve(
                    booted, subject, with_similarity=False, acquisition=seams[side], withhold=withhold,
                )
            finally:
                booted[0].handle.close()

        return question, booted[2]

    _refused_by_name({
        "withheld": ask("withheld", low.WITHHELD, frozenset({low.WITHHELD})),
        "nonexistent": ask("nonexistent", low.MISSING, frozenset({low.WITHHELD})),
        "served": ask("served", low.WITHHELD, frozenset()),
    })
    for side, seam in seams.items():
        assert seam.asked == [_probe()], (
            f"[{side}] the seam is handed the probe identifier, once, and never the asked subject: {seam.asked}"
        )


# --- controls: green before and after --------------------------------------------------


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_control_the_supported_twin_answers_every_question(tmp_path: pathlib.Path, anchor: str) -> None:
    """The same deployment, its source answering an identifier it does not hold with nothing: every question answered."""
    withholding, _ = _paved(tmp_path / "withholding", anchor, how=None, active=True)
    serving, _ = _paved(tmp_path / "serving", anchor, how=None, active=False)
    try:
        outcomes = {
            "withheld": withholding.ask(w.SUBJECT, None),
            "nonexistent": withholding.ask(w.NEVER, None),
            "served": serving.ask(w.SUBJECT, None),
        }
    finally:
        withholding.close()
        serving.close()
    assert all(type(outcome).__name__ in ("ServedProduct", "RefusalEnvelope") for outcome in outcomes.values()), outcomes


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_control_a_class_that_never_withholds_is_not_probed_and_refuses_an_unheld_identifier_as_data(
    tmp_path: pathlib.Path, anchor: str, how: str
) -> None:
    """Q12: a class affirming ``never`` is outside P6 (a); its source's held refusal reaches the caller as data."""
    built, source = _paved(tmp_path / "never", anchor, how=how, active=False, never=True)
    try:
        served = built.ask(w.SUBJECT, None)
        unheld = built.ask(w.NEVER, None)
    finally:
        built.close()
    assert type(served).__name__ == "ServedProduct", served
    assert isinstance(unheld, RefusalEnvelope) and unheld.kind == "subject-unavailable", unheld
    assert source.asked == [w.SUBJECT, w.NEVER], f"not probed: {source.asked}"


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_control_an_early_policy_over_the_refusing_source_refuses_withheld_and_unheld_as_data(
    tmp_path: pathlib.Path, anchor: str, how: str
) -> None:
    """Q8: under a declared early policy the withheld subject is asked as the stand-in, which the source refuses as it refuses any unheld identifier."""
    built, source = _paved(tmp_path / "early", anchor, how=how, active=True, early=True)
    try:
        withheld = built.ask(w.SUBJECT, None)
        unheld = built.ask(w.NEVER, None)
    finally:
        built.close()
    for name, outcome in (("withheld", withheld), ("nonexistent", unheld)):
        assert isinstance(outcome, RefusalEnvelope) and outcome.kind == "subject-unavailable", (name, outcome)
    assert w.SUBJECT not in source.asked, f"the withheld subject is never handed to the source: {source.asked}"
