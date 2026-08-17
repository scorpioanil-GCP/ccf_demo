"""The precondition without which `served parity`'s `replay_ref` column is empty.

``D-IMPL-151`` finding ``B1``. :func:`~tests.client.conformance.suite
.assert_served_parity` compares **every** declared field of
:class:`~ccf.client.result.Result`, ``replay_ref`` among them. If both subjects
answer ``None`` there they agree perfectly while carrying nothing — the vacuity
class this repository keeps shipping, surviving inside ``D-IMPL-148``'s own fix.

Both ``None`` is a reachable state and not a defect on its own
--------------------------------------------------------------
:func:`~ccf.products.door.served_answer` returns ``replay_ref=None`` when a
deployment's resolver answers with the narrower
:class:`~ccf.products.gates.ServableProduct`, which carries none, and
``door.py`` records that ``None`` there is *"the honest report that this
deployment's resolver returned no reference"*. The MCP adapter propagates it
unchanged. So a deployment with no reference to give is a legitimate shape, and
a conforming transport must be free to say so.

**That is exactly why this assertion cannot live in** ``suite.py``. The suite is
handed subjects and a provisioner and is required to be adapter-agnostic; making
it demand a replay reference would make it reject a legitimate deployment shape
on grounds that have nothing to do with the transport under test. The thing that
must be true is a fact about **this package's fixture** — that it resolves
through a :class:`~ccf.products.resolver.GovernedResolver`, so a reference
exists for the parity leg's column to be about. Plan ``17-10`` Task 2 recorded
that precondition in prose and nothing enforced it. This module is the
enforcement, and it lives at the binding because that is where the deployment is
chosen. ``suite.py`` is untouched, as ``D-IMPL-148`` requires and ``D-IMPL-151``
did not lift.

The precedent, stated so this is a pattern rather than a one-off
-----------------------------------------------------------------
``tests/mcp/test_egress_parameters.py::assert_same_verdicts`` refuses a case
table in which no case is served, *"because a table with no served case cannot
fail for the reason it exists"*. This is the same guard one layer over: a parity
comparison whose column is empty on every subject cannot fail for the reason it
exists either.

The control (``D-22``) passes a divergent subject into the **real** assertion
rather than a copy of it — an adapter that drops the reference on its way back,
which is the single most likely way this column goes quiet without a deployment
changing at all.
"""

from __future__ import annotations

from typing import Final

import pytest

from ccf.client.client import ProductClient
from ccf.client.wire import TransportAdapter, WireOutcome, WireRequest

from tests.client.conformance.suite import AdapterSubject, Provision, Question
from tests.client.conformance.test_inprocess_conformance import QUESTION
from tests.client.conformance.test_mcp_conformance import SUBJECTS

pytestmark = pytest.mark.conformance

#: The field this module exists to keep non-empty. Named rather than spelled at
#: each use so the messages, the assertion and the control say one string.
REPLAY_REF: Final[str] = "replay_ref"


def assert_a_served_delivery_carries_a_replay_reference(
    subjects: tuple[AdapterSubject, ...],
    *,
    provision: Provision,
    question: Question,
) -> None:
    """Every subject's served answer carries a replay reference, not ``None``.

    Non-vacuous with one subject, deliberately: this is a per-subject property
    and never a comparison, so it cannot degenerate the way a cross-adapter leg
    can. A subject that refused is reported as its own failure rather than
    folded in, because "refused" and "served without a reference" are different
    defects and a message that could not tell them apart would send a reader to
    the wrong file.

    Args:
        subjects: The transports to hold to the property, each against its own
            provisioned deployment.
        provision: How a fresh deployment root is obtained, per subject.
        question: A question this deployment **serves**. A refusing question
            would make every subject fail here for a reason belonging to the
            question.

    Raises:
        AssertionError: no subjects were handed in, a subject refused, or a
            subject served an answer carrying no replay reference.
    """
    if not subjects:
        raise AssertionError(
            "the replay-reference precondition was handed no adapters — an"
            " empty collection iterates to a silent success, which is this"
            " guard doing what it exists to catch"
        )
    missing: list[str] = []
    for subject in subjects:
        result = ProductClient(
            product_id=question.product_id,
            adapter=subject.connect(provision(subject.name)),
        ).ask(parameters=question.parameters, as_of=question.as_of)
        if result.refused:
            reason = result.refusal.reason if result.refusal is not None else "?"
            raise AssertionError(
                f"`{subject.name}` refused the question this precondition asks"
                f" with `{reason}` — it must be one the fixture serves, or"
                " nothing here is about a delivery at all"
            )
        if getattr(result, REPLAY_REF) is None:
            missing.append(subject.name)
    if missing:
        raise AssertionError(
            f"{sorted(missing)} served an answer carrying no `{REPLAY_REF}`, so"
            " the `served parity` leg compares that column as `None` against"
            " `None` and agrees while carrying nothing. Either this package's"
            " fixture stopped resolving through a `GovernedResolver` — the"
            " precondition plan `17-10` recorded in prose and nothing enforced"
            " — or a transport is dropping the reference on the way back"
        )


def test_every_conformance_subject_serves_a_replay_reference(
    provision: Provision,
) -> None:
    """`D-IMPL-151` `B1`: the parity leg's `replay_ref` column is about something.

    Run over the **full** subject pair rather than one transport, because the
    reference can be lost in two different places — the deployment may stop
    producing one, and an adapter may stop propagating one — and only the pair
    covers both.
    """
    assert_a_served_delivery_carries_a_replay_reference(
        SUBJECTS, provision=provision, question=QUESTION
    )


class _DropsTheReplayReference:
    """A real adapter with the reference blanked on the way back.

    Wraps rather than replaces, so everything else about the answer — the
    vessel, the address, the echoed question — is whatever the real transport
    produced. The one thing that moved is the one thing under test.
    """

    def __init__(self, inner: TransportAdapter) -> None:
        self._inner = inner

    def ask(self, request: WireRequest) -> WireOutcome:
        outcome = self._inner.ask(request)
        return WireOutcome(
            request=outcome.request,
            product_json=outcome.product_json,
            content_address=outcome.content_address,
            replay_ref=None,
            refusal=outcome.refusal,
        )


def test_control_an_adapter_that_drops_the_reference_is_caught(
    provision: Provision,
) -> None:
    """**The control.** A dropped reference fails the **real** assertion.

    This is the failure the `served parity` leg is blind to when it happens on
    *both* subjects: two adapters dropping the reference the same way agree
    perfectly. Here one subject drops it and the per-subject property — the half
    a comparison cannot supply — fires.
    """
    honest = SUBJECTS[0]
    forgetful = AdapterSubject(
        name=f"{honest.name}-drops-the-reference",
        connect=lambda root: _DropsTheReplayReference(honest.connect(root)),
        break_transport=honest.break_transport,
    )

    with pytest.raises(AssertionError, match=REPLAY_REF):
        assert_a_served_delivery_carries_a_replay_reference(
            (forgetful,), provision=provision, question=QUESTION
        )


def test_control_the_precondition_refuses_an_empty_subject_collection(
    provision: Provision,
) -> None:
    """An empty collection is a silent success in Python, and is refused by name."""
    with pytest.raises(AssertionError, match="no adapters"):
        assert_a_served_delivery_carries_a_replay_reference(
            (), provision=provision, question=QUESTION
        )


def test_control_a_refusing_question_is_reported_as_its_own_failure(
    provision: Provision,
) -> None:
    """A refusal is not silently read as "no reference".

    Without this branch a refusing question would land in the ``missing`` list
    and be reported as a lost replay reference, sending a reader to look for a
    resolver defect that is not there.
    """
    refusing = Question(
        product_id=QUESTION.product_id, parameters={}, as_of=QUESTION.as_of
    )

    with pytest.raises(AssertionError, match="refused the question"):
        assert_a_served_delivery_carries_a_replay_reference(
            SUBJECTS[:1], provision=provision, question=refusing
        )
