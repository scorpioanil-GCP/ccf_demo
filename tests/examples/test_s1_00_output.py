"""HW-1's assertions, under a runner that can actually fail.

``examples/s1-00-companies-over-revenue/consume.py`` prints; it asserts nothing.
The assertions live here, because an assertion inside a driver only fails a
build if somebody remembers to run the driver.

**The expected answer is never inlined.** It is computed by issuing the very
``SELECT`` this example argues against — ``select … from companies where revenue
> %s`` — over the same seeded rows. That makes the comparison the example is
built to win into the test's own oracle: CCF must return *exactly* the rows the
query returns, and then it must return four things the query cannot. A count
this module authored would be the test agreeing with itself.

**The two most important tests here are about identity, not content.**
:func:`test_two_thresholds_are_two_products` is what refutes the reading of a
Context Product as a precalculated static object: the caller's number is part of
the question, so it is part of the product's content address. Both it and
:func:`test_a_missing_threshold_is_refused_not_defaulted` were proved
non-vacuous by making them go red — see the plan-16-25 commit body.

Marked ``postgres``: the manifest declares a networked substrate, so every
fixture requests the session-scoped ``postgres_dsn`` fixture. Unset
``CCF_TEST_POSTGRES_DSN`` starts a container; ``CCF_REQUIRE_POSTGRES`` turns a
skip into a failure. ``make leg-postgres`` is what runs this module.

The example is not a package, so its modules are loaded by file path with
``importlib.util`` — the pattern ``test_quickstart_output.py`` established.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import psycopg
import pytest

from ccf.contracts.canonical import content_hash
from ccf.products.request import ProductRequestViolation
from ccf.replay.record import DecisionReplayRecord

pytestmark = pytest.mark.postgres

EXAMPLE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "examples"
    / "s1-00-companies-over-revenue"
)


def _load(relative: str) -> Any:
    """Load one of the example's modules by path."""
    path = EXAMPLE / relative
    name = "s1_00_" + relative.replace("/", "_").removesuffix(".py")
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # A half-executed module left in the cache would make every later
        # failure read as a missing attribute rather than as the import error
        # that actually happened.
        sys.modules.pop(name, None)
        raise
    return module


@pytest.fixture(scope="module")
def seeded(postgres_dsn: str) -> Any:
    """A seeded database, with the DSN exported where `backends.yaml` reads it."""
    provision = _load("scenario/provision.py")
    provision.seed(postgres_dsn)
    previous = os.environ.get(provision.FABRIC_DSN_ENV)
    os.environ[provision.FABRIC_DSN_ENV] = postgres_dsn
    yield postgres_dsn
    if previous is None:
        os.environ.pop(provision.FABRIC_DSN_ENV, None)
    else:
        os.environ[provision.FABRIC_DSN_ENV] = previous


def _expected(dsn: str, threshold: int) -> list[tuple[str, Decimal]]:
    """The plain SELECT this example argues against — the test's oracle."""
    deployment = _load("deployment.py")
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            f"select {deployment.COLUMN_NAME}, {deployment.COLUMN_REVENUE}"  # noqa: S608
            f" from {deployment.TABLE}"
            f" where {deployment.COLUMN_REVENUE} > %s"
            f" order by {deployment.COLUMN_NAME}",
            (threshold,),
        )
        return [(row[0], row[1]) for row in cursor.fetchall()]


def _assemble(
    root: pathlib.Path,
    *,
    parameters: Any,
    asked_at: datetime | None = None,
) -> Any:
    produce = _load("produce.py")
    deployment = _load("deployment.py")
    return produce.assemble_and_serve(
        manifest=deployment.MANIFEST,
        connection=deployment.connection(root=root),
        read=deployment.read,
        plan_class=deployment.plan_class(),
        request=deployment.request(parameters=parameters, asked_at=asked_at),
        root=root,
    )


def _over(root: pathlib.Path, threshold: int, **kwargs: Any) -> Any:
    deployment = _load("deployment.py")
    return _assemble(
        root, parameters={deployment.THRESHOLD_PARAMETER: threshold}, **kwargs
    )


#: Two thresholds the seeded estate separates. Not expected counts — the counts
#: come from the database. These merely have to differ in what they admit.
#:
#: ``int``, not ``Decimal``, and deliberately: a ``Decimal`` request parameter
#: does NOT survive the replay-record round trip (it returns as ``str``, and
#: ``refuse_request`` then refuses the replayed request with ``type-mismatch``
#: against the contract that admitted the original). Measured at plan-16-25
#: execution time and reported as an SDK finding; an ``int`` round-trips
#: exactly, which is what
#: :func:`test_the_record_is_written_before_delivery` asserts below.
LOW = 100_000_000
HIGH = 3_000_000_000


def test_the_threshold_selects(tmp_path: pathlib.Path, seeded: str) -> None:
    """A low threshold admits strictly more companies than a high one."""
    low = _over(tmp_path / "low", LOW)
    high = _over(tmp_path / "high", HIGH)

    assert low.product.payload["count"] == len(_expected(seeded, LOW))
    assert high.product.payload["count"] == len(_expected(seeded, HIGH))
    assert low.product.payload["count"] > high.product.payload["count"]

    names = [entry["name"] for entry in low.product.payload["companies"]]
    assert sorted(names) == [name for name, _ in _expected(seeded, LOW)]


def test_two_thresholds_are_two_products(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """THE test. A Context Product is not a precalculated static object.

    The caller's number is part of the question, so it is part of the product's
    content address. Two thresholds, two addresses.
    """
    low = _over(tmp_path / "low", LOW)
    high = _over(tmp_path / "high", HIGH)
    assert content_hash(low.product) != content_hash(high.product)


def test_the_same_question_is_stable(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """Identical question, identical address — determinism, not coincidence."""
    first = _over(tmp_path / "first", LOW)
    second = _over(tmp_path / "second", LOW)
    assert content_hash(first.product) == content_hash(second.product)


def test_a_missing_threshold_is_refused_not_defaulted(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """Refused at the door, returned as data, and nothing is assembled."""
    outcome = _assemble(tmp_path / "none", parameters={})
    assert isinstance(outcome, ProductRequestViolation)
    assert outcome.reason == "missing-required-parameter"
    deployment = _load("deployment.py")
    assert outcome.key == deployment.THRESHOLD_PARAMETER
    assert not hasattr(outcome, "product")


def test_debt_is_driven_by_last_updated(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """The same rows, asked about later, are measurably less fresh.

    The direction is the assertion, never a literal figure: the figure is a
    function of the declared half-life, and pinning it here would make an
    artifact edit look like a code regression.
    """
    early = _over(tmp_path / "early", LOW)
    late = _over(
        tmp_path / "late",
        LOW,
        asked_at=early.scenario.request.asked_at + timedelta(days=365),
    )
    assert late.product.debt.factors.freshness < early.product.debt.factors.freshness
    assert late.product.debt.debt > early.product.debt.debt


def test_debt_rides_the_product(tmp_path: pathlib.Path, seeded: str) -> None:
    """D_c is delivered WITH the answer and is inside its content address."""
    result = _over(tmp_path / "d", LOW)
    assert result.product.debt is not None
    assert Decimal("0") <= result.product.debt.factors.freshness <= Decimal("1")
    assert result.product.debt.signal is not None


def test_one_operator_and_the_gates_agree(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """Exactly one operator, and it is the key the artifact declares.

    Holding a ``ServableProduct`` is itself the evidence the gates ran
    (INV-CH7-52), so the gate assertion is the assembly having returned at all.
    """
    result = _over(tmp_path / "ops", LOW)
    declared = result.scenario.product_class.required_operator_keys
    assert len(declared) == 1
    assert result.operators_invoked == frozenset(declared)
    assert result.product.lineage.operators_invoked == frozenset(declared)


def test_the_record_is_written_before_delivery(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """The replay record resolves, and it round-trips the caller's threshold."""
    result = _over(tmp_path / "rec", LOW)
    deployment = _load("deployment.py")
    address = result.served.replay_ref.content_address
    assert result.store.exists(content_address=address)
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=address)
    )
    assert restored == result.record
    recorded = restored.content_generation_path.request
    assert recorded.parameters[deployment.THRESHOLD_PARAMETER] == LOW


def test_the_answer_is_the_select_plus_four_things_it_cannot_return(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """The comparison the example exists to win, asserted rather than claimed."""
    result = _over(tmp_path / "cmp", LOW)
    expected = _expected(seeded, LOW)

    # the SELECT's answer
    assert result.product.payload["count"] == len(expected)

    # ... and the four things it does not return
    assert result.product.debt is not None
    assert result.product.lineage.policy_bundle_versions
    assert content_hash(result.product)
    assert result.served.replay_ref.content_address
