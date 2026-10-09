"""P6 (a)'s counterexample, kept visible: a source that treats the probe identifier differently.

``D-IMPL-378``, Dave, 2026-10-08 16:40 MST, ruling P6 (a) — kept verbatim as a
comment below — retains this counterexample and says not to declare closure on
the probe alone; the reviewer's framing he relayed: *"P6 is still the main
risk: a source can recognize the probe and behave differently."*

The P6 probe asks the subject-keyed acquisition phase about
``ccf.products.resolver.UNHELD_SUBJECT_PROBE`` before it asks about the
question's subject, and refuses the question when that call changes the fabric
(``tests/products/test_sec020_p6_population_read_in_subject_keyed_phase.py``).
The SDK cannot see inside the phase. **This test PASSING means the
counterexample STILL HOLDS**: a source that answers NOTHING for the probe
identifier — recognizing it exactly, or by its shape (it is no ``account://``
URI, the form this fixture's entity resolution mints) — and reads the whole
population for every other identifier passes the probe, so no question is
refused; the withheld subject is then rendered over the fabric as it stood
before the phase (route A) while an identifier nothing holds is rendered over
the population, and what the caller receives tells the two apart. It is a
measured limitation of the probe, not a control: SEC-020 is OPEN. If the SDK
ever detects this source, this test goes red and the counterexample is gone.

The same configuration is reported, every run and at every door, in its own
block of SEC-020's closing test output (``SEC-020 P6 PROBE LIMITATION``,
``tests/products/test_sec020_combined_proof.py::test_p6_limitation_a_source_that_recognizes_the_probe_is_measured_not_gated``),
never counted as evidence for the gate.

Fixture vocabulary only (CINV-01).
"""

# Dave, 2026-10-08 16:40 MST, verbatim (D-IMPL-378 dated amendment on main @ 35315abf), item 2:
#   "P6: (a), conditional implementation GO. Amend Q10 to permit the probe.
#   Extend CT-A with the working declared-population twin. Do not declare
#   closure based on this probe alone: prove it runs before real-subject
#   acquisition, and retain the counterexample where a source treats the probe
#   identifier differently. Verify that the fixed identifier is actually absent;
#   do not assume it."

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from tests.products import sec020_worlds as w


def _response(observation: w.Observation) -> Any:
    """The response channel as SEC-020's same-deployment comparison reads it: the asked identifiers neutralized."""
    return w._subject_neutral(w.jsonable(observation.channels.get(w.RESPONSE)))


@pytest.mark.parametrize("recognition", w.PROBE_RECOGNITIONS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_counterexample_a_source_that_recognizes_the_probe_still_tells_the_withheld_subject_apart(
    tmp_path: pathlib.Path, anchor: str, recognition: str
) -> None:
    """The counterexample Dave asked to retain, measured on both anchors and both ways of recognizing the probe.

    One deployment that holds the subject and withholds it from the asker
    (SEC-020's ``population`` world, its source swapped for one that recognizes
    the probe), asked about the withheld subject and about two identifiers
    nothing holds — the second is the noise floor, as in the closing test.
    """
    built = w.build_probe_recognizing(
        tmp_path / "withholding", anchor=anchor, holds=True, active=True, recognition=recognition
    )
    try:
        observed = {
            side: w.observe_in_process(built, subject)
            for side, subject in (("withheld", w.SUBJECT), ("never-held", w.NEVER), ("never-held-again", w.NEVER_2))
        }
        source = built.notes["opened"]._acquire
    finally:
        built.close()
    probe = w.probe_identifier()
    # The case is what it claims: the phase was handed the probe before every
    # question's subject, and the source answered nothing for it.
    assert source.asked == [probe, w.SUBJECT, probe, w.NEVER, probe, w.NEVER_2], source.asked
    assert source.answered_nothing_for == [probe, probe, probe], source.answered_nothing_for
    raised = {side: observation.raised for side, observation in observed.items() if observation.raised}
    assert not raised, f"the probe admitted this configuration, so no question raised: {raised}"
    # The counterexample: the withheld subject is told apart from an identifier nothing holds.
    floor = w.diff_paths(_response(observed["never-held"]), _response(observed["never-held-again"]))
    differing = w.diff_paths(_response(observed["withheld"]), _response(observed["never-held"])) - floor
    assert differing, (
        f"[{anchor}, {recognition}] the counterexample no longer holds: under a source that recognizes the probe,"
        " the withheld subject's response equals a never-held identifier's beyond the noise floor"
        f" ({sorted(floor)})\n  withheld:   {w.render(_response(observed['withheld']))}"
        f"\n  never-held: {w.render(_response(observed['never-held']))}"
    )
