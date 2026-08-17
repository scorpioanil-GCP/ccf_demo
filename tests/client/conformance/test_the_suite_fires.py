"""Every conformance assertion, observed failing when its property is broken.

``D-22``. ``.planning/HANDOFF-2026-08-15.md`` states the phase's own record
plainly: *"Every defect found was in the verification or in the plans, never in
the mechanism."* A parity suite whose assertions have never been observed
failing is not a parity gate; it is a parity claim — and this phase has now
shipped four gates that stopped checking without going red.

So each control below constructs a deliberately divergent **second** subject,
runs the **real** suite function over the pair, and asserts that function
fails. Nothing here re-implements an assertion: a control that tested a copy of
the assertion would prove the copy fires.

The control the other controls depend on
-----------------------------------------
:func:`test_two_honest_subjects_agree` is first in this module for a reason.
Every control below asserts a *failure*, and an expectation of failure is
satisfied by any difference at all — including two fixture copies simply not
being comparable. The honest pair rules that out: two separate roots, two
separate boots, identical answers down to the content address. Without it, a
green run of this module would be evidence of nothing.

How a subject is made divergent
--------------------------------
:class:`_Divergent` wraps a healthy transport and edits its answer on the way
back, which is precisely what a re-implemented contract looks like from the
client's side. Where the edit touches the vessel, :func:`_remint`
re-canonicalizes it and recomputes the address from the **new** bytes — so the
divergence survives the codec's own checks and reaches the parity comparison,
which is the layer under test. A control whose divergence was caught by
:func:`~ccf.client.codec.check_outcome` would be testing the codec.
"""

from __future__ import annotations

import ast
import hashlib
import tomllib
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.client.binding import SCHEME_REGISTRY
from ccf.client.errors import RefusedResultError, TransportError
from ccf.client.result import GUARDED_FIELDS
from ccf.client.wire import TransportAdapter, WireOutcome, WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.products.contract import ContextProductContract

from tests.client.conformance import suite
from tests.client.conformance.suite import AdapterSubject, Provision, Question
from tests.client.conformance.test_inprocess_conformance import (
    OTHER_PARAMETERS,
    QUESTION,
    REFUSING_QUESTION,
    UNPINNED_QUESTION,
    SUBJECTS,
    break_in_process,
    connect_in_process,
)

pytestmark = pytest.mark.conformance

#: This repository's root, derived from this file rather than from a working
#: directory — the same reason the citation sweep's absolute-path filter was a
#: defect: a path that depends on where a command was run measures that.
REPO_ROOT = Path(__file__).resolve().parents[3]

#: The suite module whose neutrality and reachability are asserted below.
SUITE_PATH = Path(suite.__file__).resolve()

#: The directory ``make conformance`` names and ``testpaths`` must already reach.
CONFORMANCE_DIR = SUITE_PATH.parent


# ---------------------------------------------------------------------------
# Divergence machinery — a second transport that gets one thing wrong.
# ---------------------------------------------------------------------------

Mutation = Callable[[WireOutcome], WireOutcome]


class _Divergent:
    """A transport that answers correctly and then changes one thing.

    Wraps a healthy adapter rather than reimplementing one, so the only
    difference between this subject and the honest one is the edit — which is
    what makes an observed failure attributable to the property under test.
    """

    def __init__(self, inner: TransportAdapter, mutate: Mutation) -> None:
        self._inner = inner
        self._mutate = mutate

    def ask(self, request: WireRequest) -> WireOutcome:
        return self._mutate(self._inner.ask(request))


def _vessel(outcome: WireOutcome) -> ContextProductContract:
    """The served vessel an outcome carries, parsed."""
    if outcome.product_json is None:
        raise AssertionError(
            "this control was handed a refusal, which carries no vessel to edit"
        )
    return ContextProductContract.model_validate_json(outcome.product_json)


def _remint(outcome: WireOutcome, **updates: Any) -> WireOutcome:
    """Edit the served vessel, re-canonicalize it, and re-address the result.

    The address is recomputed from the new bytes deliberately. A divergence
    that left a stale address would be caught by
    :func:`~ccf.client.codec.verify_content_address`, and the control would then
    be measuring the codec rather than the parity comparison.
    """
    raw = canonical_bytes(_vessel(outcome).model_copy(update=updates))
    return outcome.model_copy(
        update={
            "product_json": raw.decode("utf-8"),
            "content_address": hashlib.sha256(raw).hexdigest(),
        }
    )


def _divergent_subject(name: str, mutate: Mutation) -> AdapterSubject:
    """A second subject identical to the in-process one but for ``mutate``."""
    return AdapterSubject(
        name=name,
        connect=lambda root: _Divergent(connect_in_process(root), mutate),
        break_transport=lambda root: _Divergent(break_in_process(root), mutate),
    )


def _pair(name: str, mutate: Mutation) -> tuple[AdapterSubject, ...]:
    """The honest subject and a divergent twin, as the suite would see them."""
    return (*SUBJECTS, _divergent_subject(name, mutate))


def _fails(reason: str) -> Any:
    """Expect the real suite function to raise, and hand back its message."""
    return pytest.raises(AssertionError, match=reason)


# ---------------------------------------------------------------------------
# The control every other control depends on.
# ---------------------------------------------------------------------------


def test_two_honest_subjects_agree(provision: Provision) -> None:
    """Two separate deployments, one transport, identical answers.

    The baseline, and the client-seam form of
    ``tests/examples/test_s1_00_output.py::test_the_same_question_is_stable``.
    """
    honest = (
        *SUBJECTS,
        AdapterSubject(
            name=f"{SUBJECTS[0].name}-twin",
            connect=connect_in_process,
            break_transport=break_in_process,
        ),
    )

    suite.assert_served_parity(honest, provision=provision, question=QUESTION)
    suite.assert_refusal_parity(
        honest, provision=provision, refusing_question=REFUSING_QUESTION
    )


# ---------------------------------------------------------------------------
# Control 1 — served parity fires on a moved field.
# ---------------------------------------------------------------------------


def _move_the_expiry(outcome: WireOutcome) -> WireOutcome:
    """Bump the vessel's expiry by one second, and re-address it honestly."""
    return _remint(outcome, expires_at=_vessel(outcome).expires_at + timedelta(seconds=1))


def test_served_parity_fires_on_a_moved_field(provision: Provision) -> None:
    """One vessel field bumped by a second: the address moves and parity fails."""
    subjects = _pair("moved-expiry", _move_the_expiry)

    with _fails("served parity") as observed:
        suite.assert_served_parity(subjects, provision=provision, question=QUESTION)

    assert "expires_at" in str(observed.value)
    assert "content_address" in str(observed.value)


# ---------------------------------------------------------------------------
# Control 2 — the payload-only trap is absent.
# ---------------------------------------------------------------------------


def _move_only_the_address(outcome: WireOutcome) -> WireOutcome:
    """Edit a vessel member that is not a ``Result`` field, so only the address moves."""
    return _remint(outcome, plan_id="a-plan-nobody-planned")


def test_served_parity_fires_when_only_the_content_address_differs(
    provision: Provision,
) -> None:
    """The named trap: agree on ``payload``, disagree on the address.

    ``plan_id`` is edited because it is a member of the vessel and **not** a
    field of :class:`~ccf.client.result.Result`. So every field a parity test
    might plausibly have been written to compare — payload, debt, lineage,
    ``expires_at``, ``replay_ref``, the request identity — is identical across
    the pair, and the content address is the only thing that moved.

    A suite comparing ``payload`` alone would pass this control. That is the
    whole point of it, and research named it as the one most likely to be
    skipped.
    """
    subjects = _pair("payload-agrees", _move_only_the_address)

    with _fails("served parity") as observed:
        suite.assert_served_parity(subjects, provision=provision, question=QUESTION)

    message = str(observed.value)
    assert "content_address" in message
    assert "`payload`" not in message, (
        "the payload moved too, so this control is no longer isolating the"
        " content address and proves nothing about the trap"
    )


# ---------------------------------------------------------------------------
# Control 3 — refusal parity fires on a dropped key.
# ---------------------------------------------------------------------------


def _drop_the_refusal_key(outcome: WireOutcome) -> WireOutcome:
    """Lose what the refusal names, and keep everything else it said."""
    if outcome.refusal is None:
        return outcome
    return outcome.model_copy(
        update={"refusal": outcome.refusal.model_copy(update={"key": None})}
    )


def test_refusal_parity_fires_on_a_dropped_key(provision: Provision) -> None:
    """``reason`` intact, ``key`` gone — reported as a difference, not tolerated.

    A governed "no" whose key has been dropped still reads as a refusal and no
    longer says what it was about, which is how an audited refusal becomes
    unattributable.
    """
    subjects = _pair("dropped-key", _drop_the_refusal_key)

    with _fails("refusal parity") as observed:
        suite.assert_refusal_parity(
            subjects, provision=provision, refusing_question=REFUSING_QUESTION
        )

    assert "refusal.key" in str(observed.value)


# ---------------------------------------------------------------------------
# Control 4 — the guard fires per field, six times, not once.
# ---------------------------------------------------------------------------


class _RecordingResult:
    """A stand-in that logs every attribute the guard leg reaches for.

    The only way to establish *which* names
    :func:`~tests.client.conformance.suite.assert_guard_holds` actually
    exercises. A ``grep`` for ``payload`` in ``suite.py`` counts docstring
    mentions and the tuple's own definition alike and cannot tell an exercised
    field from a named one; a recorded access set can.

    Args:
        unguarded: The one field this stand-in hands back instead of raising.
            ``None`` makes it a faithful refused result.
    """

    def __init__(self, unguarded: str | None = None) -> None:
        self.accessed: list[str] = []
        self._unguarded = unguarded

    def __getattr__(self, name: str) -> Any:
        self.accessed.append(name)
        if name == self._unguarded:
            return None
        raise RefusedResultError(f"`{name}` is a post-assembly field")


def test_the_guard_leg_touches_every_guarded_name() -> None:
    """Observed, not grepped: the set of names the guard leg actually read."""
    recorder = _RecordingResult()

    suite.assert_guard_holds(recorder, subject="recorder")

    assert tuple(recorder.accessed) == GUARDED_FIELDS
    assert len(recorder.accessed) == len(set(recorder.accessed))


@pytest.mark.parametrize("field", GUARDED_FIELDS)
def test_the_guard_leg_fires_on_each_field_in_turn(field: str) -> None:
    """Six controls, one per guarded name — not one ``raises`` on ``payload``.

    Parameterized over the tuple ``result.py`` publishes, so a seventh guarded
    field gets its own control the day it is declared rather than the day
    somebody remembers to add one.
    """
    recorder = _RecordingResult(unguarded=field)

    with _fails("refused result") as observed:
        suite.assert_guard_holds(recorder, subject="recorder")

    assert field in str(observed.value)


def test_the_guard_leg_refuses_an_empty_guarded_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty tuple would make the guard leg iterate over nothing and pass."""
    monkeypatch.setattr(suite, "GUARDED_FIELDS", ())

    with _fails("is empty"):
        suite.assert_guard_holds(_RecordingResult(), subject="recorder")


def test_guard_parity_reaches_the_guard_through_a_real_subject(
    provision: Provision,
) -> None:
    """The per-adapter form: ``assert_guard_parity`` needs a refusal to read.

    The parameterized controls above hold ``assert_guard_holds`` to its
    contract; this one holds ``assert_guard_parity`` to noticing when there is
    no refusal to apply it to, which no amount of testing the inner function
    establishes.
    """
    with _fails("answered the refusing question"):
        suite.assert_guard_parity(
            SUBJECTS, provision=provision, refusing_question=QUESTION
        )


# ---------------------------------------------------------------------------
# Control 5 — wire failure fires on a swallowing adapter.
# ---------------------------------------------------------------------------


class _Swallowing:
    """A transport that catches its own failure and calls it a refusal.

    The precise inversion ``D-10`` exists to prevent, written out so the leg
    that forbids it has something to catch. A caller branching correctly on
    ``result.refused`` would record an audited refusal the fabric never made,
    for a question nothing was ever asked.
    """

    def __init__(self, inner: TransportAdapter, template: WireOutcome) -> None:
        self._inner = inner
        self._template = template

    def ask(self, request: WireRequest) -> WireOutcome:
        try:
            return self._inner.ask(request)
        except TransportError:
            return WireOutcome(
                request=request,
                product_json=None,
                content_address=None,
                replay_ref=None,
                refusal=self._template.refusal,
            )


@pytest.fixture()
def refusal_template(provision: Provision) -> WireOutcome:
    """A genuine refusal, captured so the control can misuse a real one.

    Captured from the deployment rather than invented: a synthesized ``kind``
    would name a refusal vocabulary the fabric does not speak, and the control
    would then be exercising an outcome no producer could emit.
    """
    outcome = connect_in_process(provision("template")).ask(
        WireRequest(
            product_id=REFUSING_QUESTION.product_id,
            parameters=REFUSING_QUESTION.parameters,
            temporal_boundary=REFUSING_QUESTION.as_of,
        )
    )
    assert outcome.refusal is not None
    return outcome


def test_wire_failure_fires_on_a_swallowing_adapter(
    provision: Provision, refusal_template: WireOutcome
) -> None:
    """``except Exception: return refusal`` is caught, not passed over.

    Without this control the leg would pass silently on exactly the adapter it
    exists to reject: a swallowing adapter produces a well-formed refusal, and
    every other assertion in the suite is satisfied by one.
    """
    swallowing = AdapterSubject(
        name="swallows",
        connect=lambda root: _Swallowing(connect_in_process(root), refusal_template),
        break_transport=lambda root: _Swallowing(
            break_in_process(root), refusal_template
        ),
    )

    with _fails("instead of raising") as observed:
        suite.assert_wire_failure_parity(
            (swallowing,),
            provision=provision,
            question=QUESTION,
            refusing_question=REFUSING_QUESTION,
        )

    assert "a refusal" in str(observed.value)


def test_wire_failure_fires_on_a_hook_that_substitutes_the_adapter(
    provision: Provision,
) -> None:
    """The non-circularity check: a break hook may damage, never substitute.

    A hook returning some other object that raises would let the leg pass while
    proving only that the substitute raises — the same-shaped defect as a gate
    comparing something to itself.
    """

    class _AlwaysDead:
        def ask(self, request: WireRequest) -> WireOutcome:
            raise TransportError("dead by construction")

    substituting = AdapterSubject(
        name="substitutes",
        connect=connect_in_process,
        break_transport=lambda root: _AlwaysDead(),
    )

    with _fails("substituting"):
        suite.assert_wire_failure_parity(
            (substituting,),
            provision=provision,
            question=QUESTION,
            refusing_question=REFUSING_QUESTION,
        )


def test_wire_failure_fires_on_a_transport_that_raises_on_a_refusal(
    provision: Provision,
) -> None:
    """A refusal must not raise, and the leg is held to checking that.

    Without the healthy-refusal half, a transport that raised
    ``TransportError`` on *everything* would satisfy the broken-wire assertion
    and pass — which would have the leg agree that a governed "no" is a wire
    failure, the inversion in the other direction.
    """

    class _RaisesOnRefusal:
        def __init__(self, inner: TransportAdapter) -> None:
            self._inner = inner

        def ask(self, request: WireRequest) -> WireOutcome:
            outcome = self._inner.ask(request)
            if outcome.refusal is not None:
                raise TransportError("this transport calls a refusal a failure")
            return outcome

    raising = AdapterSubject(
        name="raises-on-refusal",
        connect=lambda root: _RaisesOnRefusal(connect_in_process(root)),
        break_transport=lambda root: _RaisesOnRefusal(break_in_process(root)),
    )

    with pytest.raises(TransportError):
        suite.assert_wire_failure_parity(
            (raising,),
            provision=provision,
            question=QUESTION,
            refusing_question=REFUSING_QUESTION,
        )


# ---------------------------------------------------------------------------
# Control 6 — D-23 fires when the caller's number stops reaching the product.
# ---------------------------------------------------------------------------


#: The line the fixture deployment's projection applies the caller's number on,
#: and the line the sabotage replaces.
_THRESHOLD_LINE = "threshold = Decimal(str(self._request.parameters[parameter]))"

#: What replaces it: a projection that resolves the declared parameter name and
#: then ignores whatever the caller put in it.
_IGNORING_LINE = "threshold = Decimal(0) * len(parameter)"


def _ignore_the_threshold(root: Path) -> Path:
    """Rewrite a deployment copy's projection to ignore the caller's number.

    The edit is asserted to have applied exactly once. An edit that matched
    nothing would leave an unmodified deployment behind, and the control below
    would then be asserting that the *honest* suite fails — the loudest possible
    way for a sabotage control to be lying.

    Idempotent, because a leg asks the same subject twice against one root and
    the second call must not mistake its own earlier edit for a moved fixture.

    **The module is resolved through the deployment's own ``binding.yaml``**,
    not spelled here. ``D-IMPL-141`` made ``plan:`` the one thing that names a
    deployment's Python, so a control naming a filename instead would silently
    stop matching the day a deployment renamed its projection — and would fail
    by editing nothing, which is the failure mode the count assertion below
    exists to catch.
    """
    from ccf.client.adapters.binding_document import load_binding_document

    module = root / load_binding_document(root).plan.partition(":")[0].strip()
    source = module.read_text(encoding="utf-8")
    if source.count(_IGNORING_LINE) == 1:
        return root
    if source.count(_THRESHOLD_LINE) != 1:
        raise AssertionError(
            "the fixture deployment's projection no longer applies the caller's"
            f" number on the line this control rewrites — `{module}` has moved"
            " and the sabotage would have edited nothing"
        )
    module.write_text(
        source.replace(_THRESHOLD_LINE, _IGNORING_LINE), encoding="utf-8"
    )
    return root


def test_two_parameters_fires_when_the_projection_ignores_the_threshold(
    provision: Provision,
) -> None:
    """``D-23``'s control: a precalculated object, and the leg says so.

    A projection that ignores the caller's number answers both questions with
    one product, so two content addresses become one — which is exactly *"a
    Context Product is a precalculated static object"*, the claim the property
    exists to refute.
    """
    ignoring = AdapterSubject(
        name="ignores-the-threshold",
        connect=lambda root: connect_in_process(_ignore_the_threshold(root)),
        break_transport=break_in_process,
    )

    with _fails("one content address"):
        suite.assert_two_parameters_are_two_addresses(
            (ignoring,),
            provision=provision,
            question=QUESTION,
            other_parameters=OTHER_PARAMETERS,
        )


def test_two_parameters_refuses_one_parameter_mapping_handed_over_twice(
    provision: Provision,
) -> None:
    """Handed one mapping twice, the leg refuses rather than comparing self to self."""
    with _fails("one parameter mapping twice"):
        suite.assert_two_parameters_are_two_addresses(
            SUBJECTS,
            provision=provision,
            question=QUESTION,
            other_parameters=QUESTION.parameters,
        )


def test_one_address_fires_when_two_transports_disagree(
    provision: Provision,
) -> None:
    """``D-23``'s cross-adapter half, held to reporting a moved address."""
    subjects = _pair("re-addressed", _move_only_the_address)

    with _fails("one address"):
        suite.assert_one_question_is_one_address(
            subjects, provision=provision, question=QUESTION
        )


# ---------------------------------------------------------------------------
# Control 7 — DEF-17-07's leg fires on a misreported decision instant.
# ---------------------------------------------------------------------------


def _misreport_the_anchor(outcome: WireOutcome) -> WireOutcome:
    """Report a graph anchor one second away from the one that answered."""
    lineage = _vessel(outcome).lineage
    return _remint(
        outcome,
        lineage=lineage.model_copy(
            update={
                "graph_snapshot_at": lineage.graph_snapshot_at + timedelta(seconds=1)
            }
        ),
    )


def test_the_decision_instant_leg_fires_on_a_misreported_instant(
    provision: Provision,
) -> None:
    """A transport reporting an instant it did not answer at is caught.

    This is why the leg **verifies** the recovered instant instead of merely
    reading it: a well-formed, timezone-aware datetime in the right field
    proves nothing, and pinning the same question to it is what turns a claim
    about the decision instant into a checkable one.
    """
    misreporting = AdapterSubject(
        name="misreports-its-instant",
        connect=lambda root: _Divergent(connect_in_process(root), _misreport_the_anchor),
        break_transport=break_in_process,
    )

    with _fails("not the instant that answered"):
        suite.assert_decision_instant_is_auditable(
            (misreporting,),
            provision=provision,
            # UNPINNED, because this leg refuses a question that names its own
            # instant. `QUESTION` gained a pinned `as_of` when `BL-02` made
            # `as_of=None` mean *now*, so handing it here would trip the
            # "on purpose" refusal and this control would pass for the wrong
            # reason — proving the leg rejects pinned questions rather than
            # that it catches a misreported instant.
            question=UNPINNED_QUESTION,
            refusing_question=REFUSING_QUESTION,
        )


def test_the_decision_instant_leg_refuses_a_question_that_pins_its_own_instant(
    provision: Provision,
) -> None:
    """Handed a pinned question the leg refuses rather than recovering a gift."""
    pinned = Question(
        product_id=QUESTION.product_id,
        parameters=QUESTION.parameters,
        as_of=datetime(2026, 3, 2, 12, 0, tzinfo=UTC),
    )

    with _fails("on purpose"):
        suite.assert_decision_instant_is_auditable(
            SUBJECTS,
            provision=provision,
            question=pinned,
            refusing_question=REFUSING_QUESTION,
        )


# ---------------------------------------------------------------------------
# Control 8 — the empty and the unresolvable cases go red, never quiet.
# ---------------------------------------------------------------------------


#: Every leg, with the arguments it takes. A mapping rather than a bare list so
#: the empty-collection control can call each one correctly, and so the
#: completeness check below has something to hold ``suite.__all__`` to.
LEG_CALLS: Mapping[str, Mapping[str, Any]] = {
    "assert_served_parity": {"question": QUESTION},
    "assert_one_question_is_one_address": {"question": QUESTION},
    "assert_refusal_parity": {"refusing_question": REFUSING_QUESTION},
    "assert_guard_parity": {"refusing_question": REFUSING_QUESTION},
    "assert_wire_failure_parity": {
        "question": QUESTION,
        "refusing_question": REFUSING_QUESTION,
    },
    "assert_two_parameters_are_two_addresses": {
        "question": QUESTION,
        "other_parameters": OTHER_PARAMETERS,
    },
    "assert_decision_instant_is_auditable": {
        "question": QUESTION,
        "refusing_question": REFUSING_QUESTION,
    },
}


def test_every_exported_leg_has_a_control_here() -> None:
    """A leg added to the suite without a control is a leg nobody has watched fail.

    Held against ``suite.__all__`` rather than a list written beside it, so the
    day somebody adds an eighth property this control goes red rather than
    quietly covering seven.
    """
    #: `assert_guard_holds` is excluded because it is not a leg: it takes one
    #: result rather than a collection of subjects, and its controls are the
    #: six parameterized ones above.
    exported = {
        name
        for name in suite.__all__
        if name.startswith("assert_") and name != "assert_guard_holds"
    }

    assert exported == set(LEG_CALLS), (
        "the suite's exported assertions and the controls in this module have"
        f" come apart — exported {sorted(exported)}, covered"
        f" {sorted(LEG_CALLS)}"
    )


@pytest.mark.parametrize("leg", sorted(LEG_CALLS))
def test_every_leg_refuses_an_empty_collection_of_adapters(
    leg: str, provision: Provision
) -> None:
    """``for subject in ():`` is a silent success, and every leg refuses it.

    The cheapest way for a parity gate to report green while checking nothing,
    and Python's own defaults will not report it.
    """
    with _fails("no adapters"):
        getattr(suite, leg)((), provision=provision, **LEG_CALLS[leg])


def test_served_parity_fires_on_an_unresolvable_deployment(
    provision: Provision,
) -> None:
    """A subject that cannot answer goes red rather than dropping out.

    The lenient reading — skip what cannot be reached — is exactly how a walk
    reports a smaller surface and a sweep checks fewer citations. A transport
    whose deployment is gone is a failed parity run, not a shorter one.
    """
    unresolvable = AdapterSubject(
        name="unresolvable",
        connect=break_in_process,
        break_transport=break_in_process,
    )

    with pytest.raises(TransportError):
        suite.assert_served_parity(
            (*SUBJECTS, unresolvable), provision=provision, question=QUESTION
        )


def test_served_parity_fires_when_a_subject_refuses(provision: Provision) -> None:
    """A refusal where a served answer belongs is a failed comparison."""
    with _fails("refused the served-parity question"):
        suite.assert_served_parity(
            SUBJECTS, provision=provision, question=REFUSING_QUESTION
        )


def test_no_two_subjects_can_be_handed_one_deployment(
    provision: Provision,
) -> None:
    """Sharing a graph is impossible by construction, not refused by assertion.

    Two subjects reading one deployment would make parity a claim about one
    graph read twice. The provisioner hands out a distinct directory per call,
    so there is no arrangement of subjects that produces the shared case.
    """
    first = provision("same-name")
    second = provision("same-name")

    assert first != second
    assert first.is_dir() and second.is_dir()


def test_the_suite_refuses_two_subjects_answering_to_one_name(
    provision: Provision,
) -> None:
    """A duplicate subject name would report one transport under another's."""
    twice = (SUBJECTS[0], SUBJECTS[0])

    with _fails("answer to the name"):
        suite.assert_served_parity(twice, provision=provision, question=QUESTION)


# ---------------------------------------------------------------------------
# Control 9 — the field derivation cannot silently shrink.
# ---------------------------------------------------------------------------


def test_the_derived_field_list_is_the_published_partition() -> None:
    """The derivation is held to ``result.py``'s own two tuples, and to size."""
    fields = suite.result_fields()

    assert suite.CONTENT_ADDRESS in fields
    assert set(fields) == set(suite.PRE_ASSEMBLY_FIELDS) | set(GUARDED_FIELDS)
    assert len(fields) == len(set(fields))


def test_the_field_derivation_refuses_a_result_that_declares_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A derivation that found no fields is refused, not returned empty.

    The phase's recurring defect in its purest form: ``vars()`` over a class
    that stopped declaring properties the way this reads them returns an empty
    tuple, and an empty field list makes every comparison in the suite pass
    while comparing nothing.
    """

    class _Bare:
        """A stand-in that declares no properties at all."""

    monkeypatch.setattr(suite, "Result", _Bare)

    with _fails("compare nothing"):
        suite.result_fields()


def test_the_field_derivation_refuses_a_list_without_the_content_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Losing ``content_address`` from the published partition is refused."""
    trimmed = tuple(name for name in GUARDED_FIELDS if name != suite.CONTENT_ADDRESS)
    monkeypatch.setattr(suite, "GUARDED_FIELDS", trimmed)

    with _fails("not the partition"):
        suite.result_fields()


# ---------------------------------------------------------------------------
# Control 10 — the suite names no transport, and CI actually collects it.
# ---------------------------------------------------------------------------


def _suite_tree() -> ast.Module:
    return ast.parse(SUITE_PATH.read_text(encoding="utf-8"))


def test_the_suite_imports_no_adapter() -> None:
    """``suite.py`` reaches every transport through a subject, never an import.

    Asserted over the parsed module rather than grepped, because that module's
    own docstring explains at length that it names no adapter — a ``grep``
    would be counting the explanation.
    """
    imported: list[str] = []
    for node in ast.walk(_suite_tree()):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)

    assert imported, "the suite imports nothing, so this scan read the wrong file"
    offending = [name for name in imported if "ccf.client.adapters" in name]
    assert not offending, (
        f"`suite.py` imports {offending} — a suite that reaches a transport"
        " directly is a suite the next transport cannot join without editing"
    )


def test_the_suite_names_no_registered_scheme() -> None:
    """No literal in ``suite.py`` is the name of a transport the client knows.

    Held against :data:`~ccf.client.binding.SCHEME_REGISTRY` rather than one
    hard-coded name, so a scheme registered later is covered without an edit.
    """
    schemes = set(SCHEME_REGISTRY)
    assert schemes, "no scheme is registered, so this compares against nothing"

    named = [
        node.value
        for node in ast.walk(_suite_tree())
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in schemes
    ]

    assert not named, (
        f"`suite.py` carries the transport name(s) {named} as a literal — the"
        " suite is meant to be handed transports, not to know any"
    )


def _conftests_on_the_path() -> Iterator[Path]:
    """Every ``conftest.py`` pytest reads on its way down to this suite."""
    directory = CONFORMANCE_DIR
    while True:
        candidate = directory / "conftest.py"
        if candidate.is_file():
            yield candidate
        if directory == REPO_ROOT:
            return
        directory = directory.parent


def test_the_conformance_suite_is_inside_the_default_collection() -> None:
    """``make ci`` reaches this gate without ``make conformance`` being a step.

    ``make conformance`` is a **name**, not a second collection path: adding it
    as a prerequisite of ``ci`` would run the whole suite twice. That leaves the
    reachability an assumption unless something asserts it, so this does —
    across the four ways it could quietly stop being true.
    """
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text("utf-8"))
    pytest_config = config["tool"]["pytest"]["ini_options"]

    testpaths = pytest_config["testpaths"]
    assert testpaths, "`testpaths` is empty, so nothing is collected by default"
    assert any(
        CONFORMANCE_DIR.is_relative_to((REPO_ROOT / path).resolve())
        for path in testpaths
    ), f"{CONFORMANCE_DIR} is under none of the configured testpaths {testpaths}"

    assert "addopts" not in pytest_config
    assert "norecursedirs" not in pytest_config

    modules = sorted(path.name for path in CONFORMANCE_DIR.glob("test_*.py"))
    assert modules, "the conformance directory holds no module pytest would collect"

    for conftest in _conftests_on_the_path():
        source = conftest.read_text(encoding="utf-8")
        assert "collect_ignore" not in source, (
            f"{conftest} sets a collection ignore, which is how a suite stops"
            " being collected while every target that names it still exits 0"
        )


def test_the_makefile_target_names_this_directory() -> None:
    """The named gate and the default collection point at the same directory."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    relative = CONFORMANCE_DIR.relative_to(REPO_ROOT).as_posix()

    assert "\nconformance:" in makefile, "the `conformance` target is gone"
    assert f"pytest {relative}" in makefile, (
        f"the `conformance` target no longer runs {relative}, so the gate its"
        " name promises and the gate CI collects have come apart"
    )
