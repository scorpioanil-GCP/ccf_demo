"""`D-IMPL-346` — the supported replay environment, and what it refuses.

The environment itself is proven END-TO-END by
`examples/dr-01-replay-a-governed-determination/replay.py`, which reconstructs a
served determination against the curated estate and reaches the **same content
address** as the serve. That is the real proof and it needs an estate; these
tests hold the parts that do not.

**What is deliberately NOT here.** The five example test suites that each wrote
their own environment (`CP06C-F-01`, `CP13C-F-02`, `CP17-F-06`, `ATM-F-12`,
`IBO-F-11`, `UBO-F-12`) are not converted to this class in the same change.
They are not pure duplication: cp-19's carries an ``as_of_override`` sabotage
seam and a rehydration counter its gates assert, and deleting a sabotage seam
to reduce a line count is the move this repository refuses everywhere else. The
duplication they record is real and this class is what retires it; converting
them is its own pass, each keeping its seam.
"""

from __future__ import annotations

import pytest

from ccf.replay.engine import ReplayEnvironment
from ccf.replay.environment import RecordedEnvironment, RecordedEnvironmentUnbuildable


def test_the_class_satisfies_the_engine_s_environment_protocol() -> None:
    """The three methods are the whole Protocol, and the engine's is the authority.

    Asserted structurally rather than by ``isinstance``: the Protocol is not
    runtime-checkable, and a class that merely claimed membership would prove
    nothing about the signatures the engine actually calls.
    """
    required = {
        name
        for name in dir(ReplayEnvironment)
        if not name.startswith("_") and callable(getattr(ReplayEnvironment, name, None))
    }
    assert required, "the Protocol declared no methods; this control is vacuous"
    missing = [name for name in required if not hasattr(RecordedEnvironment, name)]
    assert not missing, f"RecordedEnvironment does not satisfy the Protocol: {missing}"


def test_a_record_with_no_request_identity_is_refused_by_name() -> None:
    """Dimension 5 carries the request, and Π cannot be rebuilt without it.

    Refused rather than defaulted: a substituted request would rebuild Π
    against parameters this decision never ran under, and the reconstruction
    would carry the decision's identifier while answering a different question.
    """

    class _NoRequest:
        class content_generation_path:  # noqa: N801 — a stand-in, not a contract
            request = None

    with pytest.raises(RecordedEnvironmentUnbuildable) as refusal:
        RecordedEnvironment(
            record=_NoRequest(),  # type: ignore[arg-type]
            opened=object(),  # type: ignore[arg-type]
            fabric=object(),  # type: ignore[arg-type]
        )
    assert "no request identity" in str(refusal.value)


def test_the_refusal_is_raised_before_any_fabric_is_touched() -> None:
    """THE POSITIVE CONTROL for the test above, and without it that test is weak.

    A refusal that happened to fire because ``object()`` has no ``build_arguments``
    would pass the assertion above for the wrong reason. Handing a fabric whose
    every attribute access raises proves the request check runs FIRST: the
    sentinel's error is never reached.
    """

    class _Exploding:
        def __getattr__(self, name: str) -> object:
            raise AssertionError(f"the fabric was touched: {name!r}")

    class _NoRequest:
        class content_generation_path:  # noqa: N801
            request = None

    with pytest.raises(RecordedEnvironmentUnbuildable):
        RecordedEnvironment(
            record=_NoRequest(),  # type: ignore[arg-type]
            opened=_Exploding(),  # type: ignore[arg-type]
            fabric=_Exploding(),  # type: ignore[arg-type]
        )


def test_the_unbuildable_refusal_is_a_value_error_not_a_bare_exception() -> None:
    """Callers catch it as a typed refusal, on the module's stated discipline."""
    assert issubclass(RecordedEnvironmentUnbuildable, ValueError)
