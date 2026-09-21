"""The three cp-18 gates whose control IS their sabotage — `IBO-G14`,
`IBO-G15`, `IBO-G16`.

Every sabotage here is IN-PROCESS. The tree's `deployment.acquire` or the
acquisition module's own readers are wrapped through `monkeypatch` BEFORE
`produce.product(...)` opens the product, because the paved road binds those
callables at call time. The estate is read and never written.

`IBO-G14` is the request bound: a signal type outside the perspective's plan
is refused BY NAME rather than silently dropped, because asking for a type the
plan does not carry is asking for more than the credential permits.

`IBO-G15` is the empty candidate universe: a banker who covers nothing is
refused by name, not served an empty ranking — an empty list would read as
*"nothing worth working on this week"*, which is a different and false answer.

`IBO-G16` is the existence oracle: a banker id that was never issued must be
indistinguishable from one whose candidates Policy removed entirely.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest
import yaml
from ccf.contracts.canonical import canonical_bytes
from ccf.products.product import AcquisitionContext, OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.products.test_policy_emptied_view_disclosure import _diff_paths

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-18-ib-opportunity-synthesis"

ESTATE_VARIABLES = (
    "CCF_CP_18_SQLITE_PATH", "CCF_CP_18_POSTGRES_DSN", "CCF_CP_18_POSTGRES_SCHEMA",
    "CCF_CP_18_FLUREE_URL", "CCF_CP_18_FLUREE_LEDGER", "CCF_CP_18_MONGO_URI",
    "CCF_CP_18_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
SINCE: str = QUESTION["instants"]["SINCE"]
NONEXISTENT: tuple[str, ...] = tuple(QUESTION["nonexistent_bankers"])

REQUIRED_OPERATORS: frozenset[str] = frozenset(CONFIG["product_class"]["required_operator_keys"])
#: The tolerance at which a computed-empty view is SERVED rather than withheld.
DIAGNOSTIC_TOLERANCE = "1.0"
#: A classification outside the product's declared vocabulary.
FOREIGN_CLASSIFICATION = "sabotage-classified"
ROLE = "ma"


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-18 estate is not configured: {', '.join(missing)} unset"
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    saved = {name: sys.modules.pop(name, None) for name in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment,
               "produce": produce, "projection": projection}
    finally:
        sys.path.remove(str(tree))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


@pytest.fixture(scope="module")
def modules() -> Iterator[dict[str, Any]]:
    with _tree_modules(EXAMPLE) as loaded:
        yield loaded


@dataclass(frozen=True)
class _Answer:
    outcome: Any
    record: DecisionReplayRecord

    @property
    def product(self) -> Any:
        assert isinstance(self.outcome, ServedProduct), getattr(self.outcome, "detail", self.outcome)
        return self.outcome.product

    @property
    def refusal(self) -> RefusalEnvelope:
        assert isinstance(self.outcome, RefusalEnvelope), f"served `{type(self.outcome).__name__}`"
        return self.outcome


def _answer(
    modules: dict[str, Any], scratch: pathlib.Path, *, subject: str = SUBJECT,
    role: str = ROLE, **params: Any,
) -> _Answer:
    deployment = modules["deployment"]
    with modules["produce"].product(scratch) as opened:
        parameters: dict[str, Any] = {deployment.AS_OF: AS_OF, deployment.SINCE: SINCE}
        parameters.update({k: v for k, v in params.items() if v is not None})
        asked = opened.question(subject=subject, asked_at=ASKED_AT, intent=INTENT,
                                freshness=FRESHNESS, parameters=parameters)
        outcome = opened.answer(asked, perspective=Perspective(principal_id=subject, role=role))
        return _Answer(outcome=outcome, record=opened.record_of(outcome))


def _vessel(answer: _Answer) -> dict[str, Any]:
    return answer.product.model_dump(mode="json")


Wrapper = Callable[
    [Callable[[AcquisitionContext], tuple[SignalEnvelope, ...]], AcquisitionContext],
    tuple[SignalEnvelope, ...],
]


def _sabotage_acquire(monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], wrapper: Wrapper) -> None:
    """Wrap the tree's `acquire` BEFORE the product opens, so the road binds it."""
    deployment = modules["deployment"]
    original = deployment.acquire
    monkeypatch.setattr(deployment, "acquire", lambda context: wrapper(original, context))


def _declassified(
    original: Callable[..., tuple[SignalEnvelope, ...]], context: AcquisitionContext
) -> tuple[SignalEnvelope, ...]:
    """Every classified claim re-labelled OUTSIDE the product's vocabulary."""
    return tuple(
        envelope.model_copy(
            update={"raw_payload": {**envelope.raw_payload, "classification": FOREIGN_CLASSIFICATION}}
        )
        if "classification" in envelope.raw_payload
        else envelope
        for envelope in original(context)
    )


# =========================================================================
# IBO-G14 — a signal type outside the plan is refused, not dropped
# =========================================================================


def test_a_signal_type_outside_the_plan_is_refused_by_name(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """Asking for more than the plan carries is refused, never narrowed.

    Declared product gate `IBO-G14` (`CP-SPEC-018` §G.1). The control IS the
    sabotage: the request names a signal type the perspective's plan does not
    carry. Silently dropping it would answer a question the caller did not ask
    and hide that the type exists at all.

    The positive control is the same request naming a type the plan DOES
    carry, which is served — so the refusal is discriminating rather than a
    blanket rejection of the parameter.
    """
    deployment = modules["deployment"]
    # A LIST, because the request contract declares `signal_types` as an
    # array: a comma-joined string is refused by the SDK as a type mismatch
    # before the plan bound is ever consulted, which would make this gate
    # measure the wire shape rather than the entitlement.
    inside = _answer(modules, tmp_path / "inside", **{deployment.SIGNAL_TYPES: ["ma_event_8k"]})
    assert isinstance(inside.outcome, ServedProduct), getattr(inside.outcome, "detail", inside.outcome)
    assert inside.product.payload["ranked_opportunities"], "the narrowed request served nothing"

    outside = _answer(modules, tmp_path / "outside",
                      **{deployment.SIGNAL_TYPES: ["ma_event_8k", "sabotage_not_a_signal_type"]})
    refusal = outside.refusal
    assert refusal.kind == "subject-unavailable", refusal.kind
    breach = outside.record.content_generation_path.assembly_refusal
    assert "signal-type-outside-plan" in breach, breach
    assert "sabotage_not_a_signal_type" in breach, breach
    assert refusal.replay_reference, "the refusal carries no replay reference"


# =========================================================================
# IBO-G15 — an empty candidate universe is a refusal, not an empty list
# =========================================================================


def test_a_banker_with_no_coverage_portfolio_is_refused_by_name(
    estate: None, monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """No portfolio, no candidate universe — refused as data.

    Declared product gate `IBO-G15` (`CP-SPEC-018` §G.1). The control IS the
    sabotage, and it has to be: every one of the estate's forty bankers covers
    exactly twenty-five prospects, so the empty-portfolio state is unreachable
    from the data and is produced here by emptying the coverage read.

    An empty ranking would read as *"nothing worth working on this week"*.
    That is a different answer, and a false one.
    """
    acquisition = modules["acquisition"]
    original = acquisition._Relational.rows

    def uncovered(self: Any, sql: str, args: tuple[Any, ...] = ()) -> Any:
        if "coverage_assignment" in sql:
            return []
        return original(self, sql, args)

    monkeypatch.setattr(acquisition._Relational, "rows", uncovered)
    answer = _answer(modules, tmp_path / "uncovered")
    monkeypatch.undo()

    refusal = answer.refusal
    assert refusal.kind == "subject-unavailable", refusal.kind
    assert refusal.replay_reference, "the refusal carries no replay reference"
    breach = answer.record.content_generation_path.assembly_refusal
    assert "no-coverage-portfolio" in breach, breach
    assert answer.record.perspective_conditioning.principal_id == SUBJECT


# =========================================================================
# IBO-G16 — a policy-emptied banker is indistinguishable from an absent one
# =========================================================================


def test_a_policy_emptied_banker_reads_as_a_nonexistent_one(
    estate: None, monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The existence oracle, closed on every path the vessel carries.

    Declared product gate `IBO-G16` (`CP-SPEC-018` §G.1). A banker whose every
    admissible claim Policy removed, and a banker id that was never issued,
    produce vessels that differ at no path at all. Three limbs make that a
    measurement rather than a coincidence:

    1. the emptied banker and the nonexistent id differ nowhere;
    2. two DIFFERENT nonexistent ids hash to the same bytes, so the comparator
       is stable rather than accidentally equal on one subject;
    3. a normally served answer differs from both at the payload, so the
       comparison is not between two vessels that are trivially alike.
    """
    absent = _answer(modules, tmp_path / "absent", subject=NONEXISTENT[0],
                     debt_tolerance=DIAGNOSTIC_TOLERANCE)
    empty = absent.product
    assert empty.computed_empty is not None, "a view with nothing in it did not declare itself empty"
    assert set(empty.computed_empty.operators_returned_empty) == REQUIRED_OPERATORS

    _sabotage_acquire(monkeypatch, modules, _declassified)
    emptied = _answer(modules, tmp_path / "emptied", debt_tolerance=DIAGNOSTIC_TOLERANCE)
    monkeypatch.undo()

    leaked = _diff_paths(_vessel(emptied), _vessel(absent))
    assert not leaked, f"the vessels differ at `{sorted(leaked)}`"

    other = _answer(modules, tmp_path / "other", subject=NONEXISTENT[1],
                    debt_tolerance=DIAGNOSTIC_TOLERANCE)
    assert canonical_bytes(other.product) == canonical_bytes(empty)

    served = _answer(modules, tmp_path / "served", debt_tolerance=DIAGNOSTIC_TOLERANCE)
    distinguished = _diff_paths(_vessel(served), _vessel(absent))
    assert any(path.startswith("payload") for path in distinguished), sorted(distinguished)
    assert any(path.startswith("computed_empty") for path in distinguished), sorted(distinguished)
