"""The in-process transport, bound into the conformance suite as its first subject.

``D-15``. This module is short on purpose, and its length is a measurement of
whether ``suite.py`` is genuinely adapter-agnostic: a factory, a break hook, the
question this deployment answers, and one call per property. Plan ``17-10``
adds a second module exactly like this one and changes nothing in ``suite.py``.

**How this transport is broken.** ``break_transport`` removes the binding
document from a root it was handed to destroy, so the address still names a
directory and the directory no longer names a deployment that can carry a
question. The adapter's own path turns that into a
:class:`~ccf.client.errors.BindingError`, which is a
:class:`~ccf.client.errors.TransportError` by inheritance — *"one* ``except``
*clause covers every way the wire never spoke"*. The hook itself raises
nothing, which is what stops the wire-failure leg proving only that the hook
raises. For the MCP transport the same hook will close the pipe.

Every value the questions below carry is read out of the deployment's own
documents or computed from the rows the fixture seeds — the No-Hardcoding Rule
(CLAUDE.md §6.4) scopes to ``tests`` through
``tools/lints/__main__.py::RULE_TREE_SCOPE``, so a product identity or a
parameter name spelled here as a constant would be that rule firing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ccf.client.adapters.binding_document import BINDING_DOCUMENT_NAME
from ccf.client.adapters.inprocess import SCHEME, InProcessAdapter

from tests.client.conformance import suite
from tests.client.conformance.suite import AdapterSubject, Provision, Question
from tests.client.conftest import FIXTURE_DEPLOYMENT, SEEDED_ROWS, config_document

pytestmark = pytest.mark.conformance

#: The deployment's Control Plane document, read once from the committed copy.
_CONFIG = config_document(FIXTURE_DEPLOYMENT)

#: The class every subject is asked for, as the deployment declares it.
PRODUCT_ID = str(_CONFIG["product_class"]["schema_name"])

#: The one parameter this class requires, read off its declared request surface
#: rather than spelled — the document says which, and this reads that.
PARAMETER = str(_CONFIG["request_contract"]["arguments"]["required"][0])

#: The seeded scores, ascending. The two thresholds below are computed from
#: them so the pair is guaranteed to partition the fixture's rows differently —
#: a hand-picked pair could stop doing that the day the rows change, and
#: ``D-23``'s leg would then fail for a reason belonging to the fixture.
_SCORES = sorted(int(score) for _, score in SEEDED_ROWS)


def _in_process(root: Path) -> InProcessAdapter:
    """A healthy in-process adapter pointed at ``root``."""
    return InProcessAdapter(str(root))


def _break_in_process(root: Path) -> InProcessAdapter:
    """Damage ``root`` so it names no deployment, and point an adapter at it.

    The hook owns this root — the healthy leg is handed its own — and it raises
    nothing itself. What comes back is the same class the healthy factory
    returns, so the wire-failure leg measures a damaged substrate rather than a
    substituted object.
    """
    (root / BINDING_DOCUMENT_NAME).unlink()
    return InProcessAdapter(str(root))


#: The collection every leg compares over. One subject today; ``17-10`` appends.
SUBJECTS = (
    AdapterSubject(
        name=SCHEME, connect=_in_process, break_transport=_break_in_process
    ),
)

#: The question, at the deployment's own decision instant (``as_of=None``).
QUESTION = Question(
    product_id=PRODUCT_ID, parameters={PARAMETER: _SCORES[0] + 1}
)

#: The same question with the caller's number moved past the second row, so the
#: two questions have different answers as well as different addresses.
OTHER_PARAMETERS = {PARAMETER: _SCORES[1] + 1}

#: A question this class does not answer: the required parameter is absent, so
#: the request is refused at the door before the graph is touched.
REFUSING_QUESTION = Question(product_id=PRODUCT_ID, parameters={})


def test_served_parity(provision: Provision) -> None:
    """`D-15(a)`: same question, same instant, identical fields and address."""
    suite.assert_served_parity(SUBJECTS, provision=provision, question=QUESTION)


def test_refusal_parity(provision: Provision) -> None:
    """`D-15(b)`: the same governed no, with the same reason, key and kind."""
    suite.assert_refusal_parity(
        SUBJECTS, provision=provision, refusing_question=REFUSING_QUESTION
    )


def test_guard_parity(provision: Provision) -> None:
    """`D-15(c)`: every post-assembly field raises on a refused result."""
    suite.assert_guard_parity(
        SUBJECTS, provision=provision, refusing_question=REFUSING_QUESTION
    )


def test_wire_failure_parity(provision: Provision) -> None:
    """`D-15(d)`: a broken wire raises and a refusal does not."""
    suite.assert_wire_failure_parity(
        SUBJECTS,
        provision=provision,
        question=QUESTION,
        refusing_question=REFUSING_QUESTION,
    )


def test_two_thresholds_are_two_content_addresses(provision: Provision) -> None:
    """`D-23`, on its new path — the caller's number is part of the address."""
    suite.assert_two_parameters_are_two_addresses(
        SUBJECTS,
        provision=provision,
        question=QUESTION,
        other_parameters=OTHER_PARAMETERS,
    )


def test_one_question_is_one_content_address(provision: Provision) -> None:
    """`D-23`'s cross-adapter half — one question, one address, any transport."""
    suite.assert_one_question_is_one_address(
        SUBJECTS, provision=provision, question=QUESTION
    )


def test_the_decision_instant_is_auditable(provision: Provision) -> None:
    """`DEF-17-07`: which instant answered is recoverable *and* verifiable."""
    suite.assert_decision_instant_is_auditable(
        SUBJECTS,
        provision=provision,
        question=QUESTION,
        refusing_question=REFUSING_QUESTION,
    )
