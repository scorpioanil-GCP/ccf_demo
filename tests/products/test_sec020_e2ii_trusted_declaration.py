"""E2 (ii) (d)'s trusted-code assumption: the false-declaration counterexample, kept visible.

``D-IMPL-378``, Dave, 2026-10-08 16:40 MST, E2 (ii), option (d), verbatim:
*"Require a positive declaration, default silence to refusal, and explicitly
limit the trusted-code assumption to deployment code callers cannot influence.
Keep the false-declaration counterexample visible."*

A class affirming ``subject_withholding: never`` is built only over a plan
factory that positively declares, in its own code, that its projection never
withholds (``ccf.products.resolver.NonWithholdingPlanFactoryProtocol``). The SDK
cannot see inside a projection before running it, so the declaration is trusted
deployment code. **The counterexample test here PASSING means the
counterexample STILL HOLDS**: a factory whose declaration is false is built, and
its withheld subject's question is refused by the serve-time defense alone — an
exception (an HTTP 500 at the door) where a nonexistent subject's is answered.
It is the measured residual of a trusted-code assumption, not a control that
SEC-020 is closed. If the SDK ever closes it, this test goes red and the
counterexample is gone. The closing test also measures every cell of it on every
run, outside the gate
(``tests/products/test_sec020_combined_proof.py::test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated``).

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from tests.products import sec020_worlds as w

#: The serve-time defense Dave retained (E2 (ii), 2026-10-08 12:29 MST), by name.
SERVE_TIME_DEFENSE = "NeverWithholdingContradicted"


def _answered(door: str, observation: w.Observation) -> bool:
    """Whether the side's one question was answered: served in process, HTTP 200 at the door, and nothing raised."""
    if observation.raised.get(w.ONLY):
        return False
    response = observation.channels.get(w.RESPONSE)
    if not isinstance(response, dict):
        return False
    if door == w.HTTP:
        return response.get("status") == 200
    return response.get("outcome") == "served"


@pytest.mark.parametrize("door", [w.IN_PROCESS, w.HTTP])
@pytest.mark.parametrize("configuration", sorted(w.NEVER_FALSE_DECLARATION_CONFIGURATIONS))
def test_e2ii_d_counterexample_a_false_positive_declaration_still_tells_the_withheld_subject_apart(
    tmp_path: pathlib.Path, configuration: str, door: str
) -> None:
    """The counterexample Dave asked to keep visible, measured in process and at the HTTP door, plain and composite.

    A class affirming ``never`` over ``sec020_worlds.FalselyDeclaringPolicyPlanFactory``
    — it positively declares that it never withholds, and its projection
    withholds the restricted subject from the asker. Construction passes, because
    the declaration is trusted. Then the withheld subject's question raises
    ``NeverWithholdingContradicted`` by name (behind HTTP, a 500), while the same
    question to a deployment that does not hold the subject, and an identifier
    nothing holds asked of the withholding deployment, are answered. The control:
    the same deployment with the policy off — whose declaration is true — serves
    the subject, so the defense is the false declaration's, not a broken build.
    """
    observed: dict[str, w.Observation] = {}
    for name, holds, subject, capable in (
        ("withheld", True, w.SUBJECT, True),
        ("nonexistent", False, w.SUBJECT, True),
        ("never-held", True, w.NEVER, True),
        ("twin", True, w.SUBJECT, False),
    ):
        deployment = w.build_never(
            tmp_path / name, configuration=configuration, anchor=w.FROM_DECISION, holds=holds, capable=capable
        )
        try:
            observed[name] = w.observe_side(w.never_shape(configuration), door, deployment, subject)
        finally:
            deployment.close()
    summary: dict[str, Any] = {
        name: observation.raised.get(w.ONLY) or observation.channels.get(w.RESPONSE)
        for name, observation in observed.items()
    }
    assert _answered(door, observed["twin"]), f"control: the truly declaring twin did not serve the subject: {summary}"
    # The counterexample: the withheld subject meets the defense alone...
    assert observed["withheld"].raised.get(w.ONLY, "").startswith(f"{SERVE_TIME_DEFENSE}:"), (
        f"the counterexample no longer holds: the withheld subject was not refused by the serve-time defense: {summary}"
    )
    if door == w.HTTP:
        withheld_response = observed["withheld"].channels.get(w.RESPONSE)
        assert isinstance(withheld_response, dict) and withheld_response.get("status") == 500, summary
    # ...while a subject nothing holds is answered, in another deployment and in the same one.
    assert _answered(door, observed["nonexistent"]) and _answered(door, observed["never-held"]), (
        f"the counterexample no longer holds: a nonexistent subject was not answered: {summary}"
    )
