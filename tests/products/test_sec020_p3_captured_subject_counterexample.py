"""P3 (a)'s counterexample, kept visible: a mapping that ignores the request it is handed.

``D-IMPL-378``, Dave, 2026-10-08 12:29 MST, P3 (a), verbatim: *"as the API
improvement, but not as enforcement proof. Keep the captured-subject
counterexample in the review. Trusted deployment code is an explicit assumption;
caller-controlled mappings cannot use this exception."*

P3 (a) hands a composite's child-arguments mapping the request its children are
asked about (``src/ccf/products/child_resolver.py::ChildArguments``): under the
early policy that request names the declared stand-in in place of a withheld
subject, so a mapping that reads the subject off what it is handed asks the
child exactly what a nonexistent subject's composite asks
(``tests/products/test_withheld_subject_child_arguments_and_question_stores.py``).
The SDK cannot see where a mapping's values come from. **This test PASSING
means the counterexample STILL HOLDS**: a mapping that ignores what it is handed
and uses a subject it captured itself asks the child about the WITHHELD subject,
and the withheld composite is answered differently from a nonexistent one. It is
a measured limitation of a trusted-deployment-code assumption, not a control
that SEC-020 is closed. If the SDK ever enforces the child's subject (P3 (b),
not ruled), this test goes red and the counterexample is gone.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import Any

import pytest

from tests.products import test_withheld_subject_child_arguments_and_question_stores as p3
from tests.products import test_withheld_subject_population_composite_and_fabric as m


class _IgnoresWhatItIsHanded:
    """A deployment's mapping that takes the child's subject from state it captured, never from the request."""

    def __init__(self, *, captured: str) -> None:
        self.captured = captured
        self.handed: list[Any] = []

    def __call__(self, requirement: Any, handed: Any) -> Mapping[str, str]:
        self.handed.append(handed)
        return {"subject": self.captured, "asked_at": handed.asked_at.isoformat(), "threshold": "1000"}


@pytest.mark.parametrize("child_anchor", [m.FROM_DECISION, m.FROM_ENTITY_FRESHNESS])
def test_p3_counterexample_a_mapping_that_ignores_the_request_still_asks_the_child_about_the_withheld_subject(
    tmp_path: pathlib.Path, child_anchor: str
) -> None:
    """The counterexample Dave asked to keep in the review, measured on both child anchors.

    Each mapping is handed the request with the stand-in in place of the
    withheld subject — P3 (a) holds, and it is asserted — and ignores it. On
    BOTH anchors the withheld composite's child is then asked about the withheld
    subject itself: the subject crosses to the child's door. What the caller
    then sees depends on the anchor, as measured: under ``from_decision`` the
    withheld composite is refused (``composite-child-refusal``: the child
    answered a question other than the one the composite asked) where the
    nonexistent one is served; under ``from_entity_freshness`` both are refused
    alike, because a nonexistent subject's child has no evidence instant either.
    """
    outcomes: dict[str, Any] = {}
    asks: dict[str, list[str]] = {}
    mappings: dict[str, _IgnoresWhatItIsHanded] = {}
    for name, subject in (("withheld", m.COMPOSITE_WITHHELD), ("nonexistent", m.COMPOSITE_MISSING)):
        mappings[name] = _IgnoresWhatItIsHanded(captured=subject)
        outcomes[name], asks[name] = p3._ask_composite(
            tmp_path / name, subject, child_anchor=child_anchor, mapping=mappings[name]
        )
    # P3 (a) itself: the mapping WAS handed the request with the stand-in.
    assert [request.subject for request in mappings["withheld"].handed] == [m.UNDISCLOSED]
    assert asks["nonexistent"] == [m.COMPOSITE_MISSING], "the case was not constructed"
    # The counterexample: the child is asked about the withheld subject.
    assert asks["withheld"] == [m.COMPOSITE_WITHHELD], (
        f"the counterexample no longer holds: the withheld composite's child was asked {asks['withheld']}"
    )
    # ...and what the caller sees, per anchor, as measured.
    assert type(outcomes["withheld"]).__name__ == "RefusalEnvelope", outcomes["withheld"]
    assert outcomes["withheld"].kind == "composite-child-refusal", outcomes["withheld"].kind
    if child_anchor == m.FROM_DECISION:
        assert type(outcomes["nonexistent"]).__name__ == "ServedProduct", (
            "under from_decision the nonexistent composite was not served, so the counterexample's"
            f" refused-against-served difference was not measured: {outcomes['nonexistent']}"
        )
    else:
        m._assert_indistinguishable(
            outcomes["withheld"], outcomes["nonexistent"],
            case=f"captured-subject counterexample, child anchor {child_anchor}",
        )
