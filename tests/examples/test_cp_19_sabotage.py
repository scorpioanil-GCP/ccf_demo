"""The two gates of cp-19 whose control IS their sabotage — `ATM-G04`, `ATM-G14`.

Both sabotages are IN-PROCESS. The tree's `deployment.acquire` and the
projection's own member builder are wrapped through `monkeypatch` BEFORE
`produce.product(...)` opens the product, because the paved road binds those
callables at call time. The estate is read and never written.

`ATM-G04` is the refusal branch of the disposition bound: a candidate the
posture forbids must refuse the product BY NAME rather than be quietly
dropped, and the disposition injected is a real one — the set the OTHER
posture permits, measured, never a synthetic string.

`ATM-G14` is the existence oracle: an alert whose admissible content Policy
removes entirely must be indistinguishable from an alert id that was never
issued. Nothing here pins an estate figure.
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
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.products.test_policy_emptied_view_disclosure import _diff_paths

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-19-aml-typology-match"

ESTATE_VARIABLES = (
    "CCF_CP_19_SQLITE_PATH", "CCF_CP_19_POSTGRES_DSN", "CCF_CP_19_POSTGRES_SCHEMA",
    "CCF_CP_19_FLUREE_URL", "CCF_CP_19_FLUREE_LEDGER", "CCF_CP_19_MONGO_URI",
    "CCF_CP_19_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
INSTANTS: dict[str, str] = QUESTION["instants"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
ASKED_AT = datetime.fromisoformat(QUESTION["question"]["asked_at"])
NONEXISTENT: tuple[str, ...] = tuple(QUESTION["nonexistent_alerts"])

GATE_ID: str = CONFIG["product_class"]["declared_product_gate"]["gate_id"]
REQUIRED_OPERATORS: frozenset[str] = frozenset(CONFIG["product_class"]["required_operator_keys"])

#: The tolerance at which a computed-empty view is SERVED rather than withheld.
#: Both limbs of the comparator are asked at it, so the comparison is between
#: two served vessels rather than between a serve and a refusal.
DIAGNOSTIC_TOLERANCE = "1.0"
#: A classification outside the product's declared vocabulary.
FOREIGN_CLASSIFICATION = "sabotage-classified"

L1 = Perspective(principal_id="PRIN-AML-L1", role="l1")


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the cp-19 estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
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


def _question(opened: OpenedProduct, *, subject: str, **params: Any) -> ProductRequest:
    parameters = {name: value for name, value in params.items() if value is not None}
    return opened.question(
        subject=subject, asked_at=ASKED_AT, intent=INTENT, freshness=FRESHNESS, parameters=parameters
    )


def _answer(
    modules: dict[str, Any], scratch: pathlib.Path, *, perspective: Perspective = L1,
    subject: str = SUBJECT, **params: Any,
) -> _Answer:
    with modules["produce"].product(scratch) as opened:
        outcome = opened.answer(_question(opened, subject=subject, **params), perspective=perspective)
        return _Answer(outcome=outcome, record=opened.record_of(outcome))


def _vessel(answer: _Answer) -> dict[str, Any]:
    return answer.product.model_dump(mode="json")


Wrapper = Callable[
    [Callable[[AcquisitionContext], tuple[SignalEnvelope, ...]], AcquisitionContext],
    tuple[SignalEnvelope, ...],
]


def _sabotage_acquire(monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], wrapper: Wrapper) -> None:
    """Wrap the tree's `acquire` BEFORE the product opens, so the road binds the wrapper."""
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
# ATM-G04 — a forbidden disposition refuses the product, by name
# =========================================================================


def test_a_forbidden_disposition_refuses_the_product_by_name(
    estate: None, monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """One candidate outside the permitted set turns the serve into a refusal.

    Declared product gate `ATM-G04` (`CP-SPEC-019` §G.1). The candidate list is
    built FROM the permitted set, so the only way to observe the gate's refusal
    branch is to break that construction — which is what this does. The
    disposition injected is REAL: it is the one the posture at the other
    instant permits and this one does not, measured from two live answers
    rather than invented, so the gate refuses a plausible mistake rather than
    an impossible string.

    The un-sabotaged answer at the same instant is served, or the sabotage
    proves nothing.
    """
    projection = modules["projection"]
    early = _answer(modules, tmp_path / "early", as_of=INSTANTS["AS_OF_EARLY"])
    late = _answer(modules, tmp_path / "late", as_of=INSTANTS["AS_OF_LATE"])
    permitted_early = set(early.product.payload["permitted_dispositions"])
    forbidden = sorted(set(late.product.payload["permitted_dispositions"]) - permitted_early)
    assert forbidden, (
        "the two postures permit the same set, so no REAL forbidden disposition exists;"
        " the gate would have to be sabotaged with an invented string"
    )
    injected = forbidden[0]

    original_member = projection._member

    def propose_forbidden(member: str, by_class: Any, **kwargs: Any) -> Any:
        built = original_member(member, by_class, **kwargs)
        if member == "disposition_candidates":
            return [*built, {"disposition": injected, "basis": "posture-permitted"}]
        return built

    monkeypatch.setattr(projection, "_member", propose_forbidden)
    sabotaged = _answer(modules, tmp_path / "sabotaged", as_of=INSTANTS["AS_OF_EARLY"])

    refusal = sabotaged.refusal
    assert refusal.kind == "product-invariant-refusal", refusal.kind
    assert refusal.reason == GATE_ID, refusal.reason
    breach = sabotaged.record.content_generation_path.assembly_refusal
    assert injected in breach and "ATM-G03" in breach, f"the record's `assembly_refusal` names no breach: {breach}"
    assert sabotaged.record.perspective_conditioning.principal_id == L1.principal_id
    # And the refusal is a DECISION, not an exception: the record exists.
    assert sabotaged.record.content_generation_path.plan_id == early.record.content_generation_path.plan_id


# =========================================================================
# ATM-G14 — a policy-emptied alert is indistinguishable from an absent one
# =========================================================================


def test_a_policy_emptied_alert_reads_as_a_nonexistent_one(
    estate: None, monkeypatch: pytest.MonkeyPatch, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The existence oracle, closed on every path the vessel carries.

    Declared product gate `ATM-G14` (`CP-SPEC-019` §G.1). An alert that EXISTS
    and whose every admissible claim Policy removed, and an alert id that was
    never issued, produce vessels that differ at no path at all. The three
    limbs together are what make that a measurement:

    1. The emptied alert and the nonexistent id differ nowhere.
    2. Two DIFFERENT nonexistent ids hash to the same content address, so the
       comparator is stable rather than accidentally equal on one subject.
    3. A NORMALLY served answer differs from both at the payload, so the
       comparison is not between two vessels that are trivially alike.
    """
    absent = _answer(modules, tmp_path / "absent", subject=NONEXISTENT[0],
                     as_of=INSTANTS["AS_OF_EARLY"], debt_tolerance=DIAGNOSTIC_TOLERANCE)
    empty = absent.product
    assert empty.computed_empty is not None, "a view with nothing in it did not declare itself empty"
    assert set(empty.computed_empty.operators_returned_empty) == REQUIRED_OPERATORS

    _sabotage_acquire(monkeypatch, modules, _declassified)
    emptied = _answer(modules, tmp_path / "emptied", as_of=INSTANTS["AS_OF_EARLY"],
                      debt_tolerance=DIAGNOSTIC_TOLERANCE)
    monkeypatch.undo()

    leaked = _diff_paths(_vessel(emptied), _vessel(absent))
    assert not leaked, f"the vessels differ at `{sorted(leaked)}`"

    other_absent = _answer(modules, tmp_path / "other", subject=NONEXISTENT[1],
                           as_of=INSTANTS["AS_OF_EARLY"], debt_tolerance=DIAGNOSTIC_TOLERANCE)
    assert canonical_bytes(other_absent.product) == canonical_bytes(empty)

    served = _answer(modules, tmp_path / "served", as_of=INSTANTS["AS_OF_EARLY"],
                     debt_tolerance=DIAGNOSTIC_TOLERANCE)
    distinguished = _diff_paths(_vessel(served), _vessel(absent))
    assert any(path.startswith("payload") for path in distinguished), sorted(distinguished)
    assert any(path.startswith("computed_empty") for path in distinguished), sorted(distinguished)
