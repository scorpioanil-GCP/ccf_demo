"""The three cp-15 gates whose control IS their sabotage — `UBO-G07`,
`UBO-G17`, `UBO-G18`.

Every sabotage here is IN-PROCESS. The tree's `deployment.acquire` or the
acquisition module's own readers are wrapped through `monkeypatch` BEFORE
`produce.product(...)` opens the product, because the paved road binds those
callables at call time. The estate is read and never written.

`UBO-G07` is the floor bound: a request BELOW the estate's declared floor for
`threshold` or `min_confidence` is refused by name rather than silently raised
to the floor, because lowering a floor would report more than the credential
permits.

`UBO-G18` is the entitlement bound: a principal with no jurisdiction grant is
refused by name, as data, rather than served an empty product.

`UBO-G17` is the existence oracle: an entity id that was never issued must be
indistinguishable from one whose claims Policy removed entirely.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
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
EXAMPLE = REPO_ROOT / "examples" / "cp-15-kyc-refresh-beneficial-ownership"

ESTATE_VARIABLES = (
    "CCF_CP_15_SQLITE_PATH", "CCF_CP_15_POSTGRES_DSN", "CCF_CP_15_POSTGRES_SCHEMA",
    "CCF_CP_15_FLUREE_URL", "CCF_CP_15_FLUREE_LEDGER", "CCF_CP_15_MONGO_URI",
    "CCF_CP_15_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "review", "serve", "server")

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
AS_OF: str = QUESTION["instants"]["ASKED_AT"]
NONEXISTENT: tuple[str, ...] = tuple(QUESTION["nonexistent_entities"])

REQUIRED_OPERATORS: frozenset[str] = frozenset(CONFIG["product_class"]["required_operator_keys"])
#: The tolerance at which a computed-empty view is SERVED rather than withheld.
DIAGNOSTIC_TOLERANCE = "1.0"
#: A classification outside the product's declared vocabulary.
FOREIGN_CLASSIFICATION = "sabotage-classified"
PRINCIPAL = "PRIN-KYC-004"
ROLE = "kyc-analyst"


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the cp-15 estate is not configured: {', '.join(missing)} unset"
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
        parameters: dict[str, Any] = {deployment.AS_OF: AS_OF}
        parameters.update({k: v for k, v in params.items() if v is not None})
        asked = opened.question(subject=subject, asked_at=ASKED_AT, intent=INTENT,
                                freshness=FRESHNESS, parameters=parameters)
        outcome = opened.answer(asked, perspective=Perspective(principal_id=PRINCIPAL, role=role))
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
# UBO-G07 — a request below a declared floor is refused, not raised
# =========================================================================


def test_a_request_below_the_declared_floor_is_refused_by_name(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """Lowering a floor would report MORE than the credential permits.

    Declared product gate `UBO-G07` (`CP-SPEC-015` §G.1). The control IS the
    sabotage: the request asks below the estate's declared floor and must be
    refused by name. Silently raising it to the floor would answer a question
    the caller did not ask and hide that the floor exists.

    The positive control is the same request ABOVE the floor, which is served
    — so the refusal is discriminating rather than a blanket rejection of the
    parameter.
    """
    deployment = modules["deployment"]
    raised = _answer(modules, tmp_path / "raised", **{deployment.MIN_CONFIDENCE: "0.95"})
    assert isinstance(raised.outcome, ServedProduct), getattr(raised.outcome, "detail", raised.outcome)
    assert Decimal(raised.product.payload["min_confidence"]) == Decimal("0.95")

    lowered = _answer(modules, tmp_path / "lowered", **{deployment.MIN_CONFIDENCE: "0.10"})
    refusal = lowered.refusal
    assert refusal.kind == "subject-unavailable", refusal.kind
    assert refusal.replay_reference, "the refusal carries no replay reference"
    breach = lowered.record.content_generation_path.assembly_refusal
    assert "floor-breached" in breach, breach
    assert "min_confidence" in breach, breach

    # And the same rule holds for the reporting threshold.
    under = _answer(modules, tmp_path / "under", **{deployment.THRESHOLD: "1"})
    assert "floor-breached" in under.record.content_generation_path.assembly_refusal


# =========================================================================
# UBO-G18 — no jurisdiction grant is a refusal, not an empty product
# =========================================================================


def test_a_principal_with_no_jurisdiction_grant_is_refused_by_name(
    estate: None, monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """No grant, nothing admissible — refused as data.

    Declared product gate `UBO-G18` (`CP-SPEC-015` §G.1). The control IS the
    sabotage, and it has to be: every registered principal in this estate
    holds at least one jurisdiction grant, so the ungranted state is
    unreachable from the data and is produced here by emptying that read.

    An empty product would read as *"this entity has no beneficial owners"*,
    which is a different answer, and a false one.
    """
    acquisition = modules["acquisition"]
    original = acquisition._Relational.rows

    def ungranted(self: Any, sql: str, args: tuple[Any, ...] = ()) -> Any:
        if "principal_jurisdiction" in sql:
            return []
        return original(self, sql, args)

    monkeypatch.setattr(acquisition._Relational, "rows", ungranted)
    answer = _answer(modules, tmp_path / "ungranted")
    monkeypatch.undo()

    refusal = answer.refusal
    assert refusal.kind == "subject-unavailable", refusal.kind
    assert refusal.replay_reference, "the refusal carries no replay reference"
    breach = answer.record.content_generation_path.assembly_refusal
    assert "no-jurisdiction-grant" in breach, breach
    assert answer.record.perspective_conditioning.principal_id == PRINCIPAL


# =========================================================================
# UBO-G17 — a policy-emptied entity is indistinguishable from an absent one
# =========================================================================


def test_a_policy_emptied_entity_reads_as_a_nonexistent_one(
    estate: None, monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """The existence oracle, closed on every path the vessel carries.

    Declared product gate `UBO-G17` (`CP-SPEC-015` §G.1). An entity whose
    every admissible claim Policy removed, and an entity id that was never
    issued, produce vessels that differ at no path at all. Three limbs make
    that a measurement rather than a coincidence:

    1. the emptied entity and the nonexistent id differ nowhere;
    2. two DIFFERENT nonexistent ids hash to the same bytes;
    3. a normally served answer differs from both at the payload.
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
