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


class _RecordingMapping:
    """A deployment's mapping that records every call; with ``reads_parameter``, it puts a caller's value in the child's subject."""

    def __init__(self, *, reads_parameter: str | None = None) -> None:
        self.handed: list[Any] = []
        self.reads_parameter = reads_parameter

    def __call__(self, requirement: Any, request: Any) -> Mapping[str, str]:
        self.handed.append(request)
        subject = request.subject
        if self.reads_parameter is not None:
            subject = f"from-caller-{request.parameters[self.reads_parameter]}"
        return {"subject": subject, "asked_at": request.asked_at.isoformat(), "threshold": "1000"}


def test_p3_condition_iii_no_caller_input_supplies_or_selects_the_child_arguments_mapping(
    tmp_path: pathlib.Path,
) -> None:
    """Dave's P3 (a): *"caller-controlled mappings cannot use this exception"* — and no caller input makes one.

    A mapping is bound, as deployment code, where its child resolver is built;
    lane ``378e-s020`` scanned ``src/``, ``runtime/`` and ``examples/`` and found
    no other way in (no document key, no dynamic import, no door or adapter
    path names one). Measured here, on the composite the P3 tests ask:

    * a valid question reaches exactly the deployment's mapping object, handed
      the request;
    * a question carrying an undeclared parameter named and shaped like a
      mapping is refused ``undeclared-parameter`` by the request contract, and
      no mapping is called and no child asked;
    * a door's wire request naming a mapping is refused by the wire model.

    The control: a deployment mapping that READS a declared parameter into the
    child's subject puts the caller's value in front of the child — the measure
    sees a caller's influence where deployment code creates it, which is exactly
    what the trusted-code assumption does not cover.
    """
    from pydantic import ValidationError  # noqa: PLC0415

    from ccf.products.door import WireRequest  # noqa: PLC0415

    honest = _RecordingMapping()
    outcome, asked = p3._ask_composite(tmp_path / "honest", m.COMPOSITE_MISSING, child_anchor=m.FROM_DECISION,
                                       mapping=honest)
    assert type(outcome).__name__ == "ServedProduct", outcome
    assert len(honest.handed) == 1 and type(honest.handed[0]).__name__ == "ProductRequest"
    assert asked == [m.COMPOSITE_MISSING]

    injected = _RecordingMapping()
    refused, asked = _ask_with(tmp_path / "injected", injected, {
        m.THRESHOLD_PARAMETER: 1000, "child_arguments": {"subject": m.COMPOSITE_WITHHELD},
    })
    assert type(refused).__name__ == "RefusalEnvelope", refused
    assert (refused.reason, refused.key) == ("undeclared-parameter", "child_arguments"), (refused.reason, refused.key)
    assert injected.handed == [] and asked == []

    with pytest.raises(ValidationError, match="child_arguments"):
        WireRequest.model_validate({
            "product_id": m.PRODUCT_CLASS, "parameters": {}, "temporal_boundary": None,
            "child_arguments": "module:attribute",
        })

    control = _RecordingMapping(reads_parameter=m.THRESHOLD_PARAMETER)
    _outcome, asked = _ask_with(tmp_path / "control", control, {m.THRESHOLD_PARAMETER: 1000})
    assert asked == ["from-caller-1000"], (
        f"control: a mapping reading a caller's parameter did not put it before the child ({asked}),"
        " so this measure could not see a caller's influence at all"
    )


def _ask_with(tmp_path: pathlib.Path, mapping: Any, parameters: dict[str, Any]) -> tuple[Any, list[str]]:
    """The P3 module's early-policy composite, asked about a nonexistent subject with ``parameters``."""
    from ccf.products.request import ProductRequest  # noqa: PLC0415
    from ccf.products.resolver import GovernedResolver  # noqa: PLC0415

    from tests.products import composite_fixture as cf  # noqa: PLC0415

    parent = m._composite_boot(tmp_path / "parent", child_anchor=m.FROM_DECISION)
    child_own = m._composite_boot(tmp_path / "child", child_anchor=m.FROM_DECISION, ingest_batch=False,
                                  for_question=True)
    child = m._Booted(fabric=child_own.fabric, control_plane=child_own.control_plane, store=parent.store,
                      root=child_own.root)
    asked: list[str] = []
    try:
        children = cf.build_child_resolver(
            parent, child_door=m._child_door(child, asked=asked, observed=m.CHILD_OBSERVED[m.FROM_DECISION]),
            child_arguments=mapping,
        )
        arguments = cf._arguments(parent)
        arguments.update(composite_children=children, plan_factory=m._early())
        outcome = GovernedResolver(**arguments)(
            tenant=m.TENANT, product_class=m.PRODUCT_CLASS, version=m.PRODUCT_VERSION, perspective=m.PERSPECTIVE,
            request=ProductRequest(
                schema_name=m.PRODUCT_CLASS, schema_version=m.PRODUCT_VERSION, subject=m.COMPOSITE_MISSING,
                intent="fixture-intent", freshness="fixture-freshness", asked_at=m.ASKED_AT, parameters=parameters,
            ),
        )
    finally:
        parent.fabric.handle.close()
        child.fabric.handle.close()
    return outcome, asked
