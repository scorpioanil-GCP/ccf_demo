# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Evidence dated after the decision instant is a governed refusal, never a raise (CP08-R3-F-01).

**The finding** (``NEEDS-SDK.md``, r2-mid / r3-fix, cp-08). Asked at the drawdown
day, cp-08 ingests an amendment booked weeks later; the freshness scorer meets an
observation dated after the instant it is evaluated at and raises
:class:`~ccf.halflife.decay.TemporalOrderError` — correctly refusing to score the
future as perfectly fresh — and the resolver let the exception escape.
``docs/EXAMPLE-EVALUATION-CRITERIA.md`` §D: *"refuse correctly — the right reason,
by name, as data, with a replay reference, and never a raise where a governed
refusal is owed"*.

**Ruled** (Dave, 2026-10-11 20:19 MST, ruling 1: *"cp-08's error-versus-refusal
behavior"*). The resolver catches exactly that error at its scoring step and
returns :class:`~ccf.products.gates.EvidenceAfterDecisionRefusal` (kind
``evidence-after-decision-refusal``), recorded like every post-projection refusal:
the execution's operators and plan, no debt (none could be assessed), and a
replay reference. Nothing is clamped: the future-dated evidence is not scored as
fresh, and no other scorer failure is converted.

Every name and number below is this module's own (CINV-01).
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.graph.protocols import GraphView
from ccf.halflife.decay import TemporalOrderError
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    REFUSAL_KINDS,
    RefusalEnvelope,
)

from tests.products.test_resolver_seam import (
    _Booted,
    _ask,
    _internal,
    _request,
    _resolver,
    booted,  # noqa: F401  (fixture import)
)

KIND = "evidence-after-decision-refusal"


def _raising(error: Exception) -> Any:
    """A deployment's debt scorer that meets ``error`` while measuring."""

    def score(*, view: GraphView, evidence: ExecutionEvidence | None = None) -> Any:
        raise error

    return score


def _outcome(booted: _Booted, error: Exception) -> object:
    """The governed outcome, or the exception — so a raise fails an ASSERTION, by name."""
    try:
        return _ask(_resolver(booted, debt_scorer=_raising(error)), _request())
    except TemporalOrderError as raised:
        return raised


def test_evidence_dated_after_the_decision_instant_is_refused_by_name_with_a_record(
    booted: _Booted,  # noqa: F811
) -> None:
    outcome = _outcome(
        booted,
        TemporalOrderError(
            "elapsed time is negative: the source's observation instant is"
            " dated after the instant it is evaluated at"
        ),
    )

    assert isinstance(outcome, RefusalEnvelope), f"a raise where a governed refusal is owed: {outcome!r}"
    from ccf.products.gates import EvidenceAfterDecisionRefusal  # noqa: PLC0415

    assert outcome.kind == KIND == REFUSAL_KINDS[EvidenceAfterDecisionRefusal]
    assert outcome.replay_reference != NO_REPLAY_REFERENCE
    # The record holds the determination, and it is the post-projection shape:
    # the plan ran, and no Context Debt could be assessed — not a fabricated one.
    internal = _internal(booted, outcome)
    assert internal.kind == KIND
    assert internal.evidence is not None
    assert internal.evidence.plan_id
    assert internal.evidence.debt is None
    assert "dated after" in internal.detail


def test_any_other_scorer_failure_is_not_converted(booted: _Booted) -> None:  # noqa: F811
    """The control: only the temporal-order fault is a governed refusal. A scorer
    defect of any other kind still raises — converting every error would hide
    wiring faults behind a refusal."""
    with pytest.raises(ValueError, match="a different scorer fault"):
        _ask(
            _resolver(booted, debt_scorer=_raising(ValueError("a different scorer fault"))),
            _request(),
        )
