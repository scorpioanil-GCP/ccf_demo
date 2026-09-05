"""The fail-closed guard, proven once per guarded field — never by sampling.

``D-08``. Accessing a post-assembly field on a refused
:class:`~ccf.client.result.Result` raises; it never returns ``None``. The
inversion is the design's sharpest idea and is easy to half-implement: a single
``pytest.raises`` on ``result.payload`` licenses five unguarded fields, which is
verbatim the Phase 16 defect *"a property asserted in four places and controlled
in none."*

So every assertion here is parameterized over
:data:`~ccf.client.result.GUARDED_FIELDS` — the tuple the guard itself reads —
and the sabotage controls at the bottom pass a **divergent subject** into the
same shipped assertion function the real tests call. A control that
re-implements the check proves only that the copy fires.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Final

import pytest

from ccf.client.errors import BindingError, RefusedResultError, TransportError
from ccf.client.result import (
    GUARDED_FIELDS,
    PRE_ASSEMBLY_FIELDS,
    Refusal,
    Result,
)
from ccf.halflife.assessment import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.products.gates import TTLRefusal
from ccf.products.refusal import RefusalEnvelope, RequestIdentity, envelope_for
from ccf.products.request import ProductRequestViolation

_INSTANT: Final = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
_PARAMETERS: Final[Mapping[str, Any]] = {"revenue_threshold": 1000000}
_ADDRESS: Final = "a" * 64


# --------------------------------------------------------------------------
# Subjects
# --------------------------------------------------------------------------


def a_vessel() -> ContextProductContract:
    """A served product, in the shape every door already emits.

    Carries a real :class:`~ccf.halflife.assessment.DebtAssessment` rather than
    the field's ``None`` default, so the served leg can assert every guarded
    name returns *something* rather than merely declining to raise.
    """
    return ContextProductContract(
        schema_name="ccf.test-product",
        schema_version="1.0.0",
        plan_id="plan-1",
        tenant_id="acme-bank",
        temporal_boundary=_INSTANT,
        expires_at=datetime(2026, 9, 1, tzinfo=UTC),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"traversal.neighbors"}),
            policy_bundle_versions=frozenset({"v1"}),
            graph_snapshot_at=_INSTANT,
        ),
        payload={"companies": ["acme", "globex"], "threshold": 1000000},
        debt=DebtAssessment(
            debt=Decimal("0.28"),
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal("0.90"),
                completeness=Decimal("0.80"),
                semantic_consistency=Decimal("1.0"),
            ),
        ),
    )


def a_request_identity() -> RequestIdentity:
    return RequestIdentity(
        product_id="ccf.test-product",
        product_version="1.0.0",
        parameters=_PARAMETERS,
        temporal_boundary=_INSTANT,
    )


def a_request_refusal() -> RefusalEnvelope:
    """A governed "no" reached before the graph was touched."""
    return envelope_for(
        ProductRequestViolation(
            reason="missing-required-parameter",
            key="revenue_threshold",
            declared_type="int",
            presented_type=None,
            declared_keys=frozenset({"revenue_threshold"}),
            presented_keys=frozenset(),
            detail="the class declares `revenue_threshold` and none was supplied",
        ),
        request=a_request_identity(),
    )


def a_gate_refusal() -> RefusalEnvelope:
    """A second kind, from a different family, so ``kind`` is proven carried."""
    return envelope_for(
        TTLRefusal(
            gate="ttl-bounds",
            detail="the candidate outlives the ceiling its class was registered with",
            expires_at=datetime(2026, 9, 1, tzinfo=UTC),
            now=_INSTANT,
            max_ttl_seconds=600,
        ),
        request=a_request_identity(),
    )


def a_served_result() -> Result:
    """A result the fabric answered."""
    return Result(
        product_id="ccf.test-product",
        parameters=_PARAMETERS,
        temporal_boundary=_INSTANT,
        vessel=a_vessel(),
        content_address=_ADDRESS,
        replay_ref="replay-1",
        refusal=None,
    )


def a_refused_result(
    *, refusal: RefusalEnvelope | None = None, replay_ref: str | None = "replay-2"
) -> Result:
    """A result the fabric refused — the fabric working, not failing.

    It carries a replay reference by default as of ``24.6-07``, because that is
    now the ordinary case: a refusal is a recorded decision (``D-IMPL-253``
    Q13). ``replay_ref=None`` is still constructible and is the honest report
    that the producing deployment published none.
    """
    return Result(
        product_id="ccf.test-product",
        parameters=_PARAMETERS,
        temporal_boundary=_INSTANT,
        vessel=None,
        content_address=None,
        replay_ref=replay_ref,
        refusal=refusal if refusal is not None else a_request_refusal(),
    )


# --------------------------------------------------------------------------
# The shipped assertions — one definition, used by the tests AND the controls
# --------------------------------------------------------------------------


def assert_guard_holds(result: Result, field: str) -> None:
    """Assert reading ``field`` off ``result`` refuses rather than returning.

    Takes its subject as a parameter so a control can pass a deliberately leaky
    ``Result`` into *this* function rather than into a copy of it.

    Three things are checked together, because a guard satisfying only the
    first is the guard this project would ship by accident:

    1. Reading raises at all.
    2. It raises :class:`~ccf.client.errors.RefusedResultError` and **not**
       ``AttributeError`` — an ``AttributeError`` is silently swallowed by
       ``getattr(result, field, None)`` and by ``hasattr``, which reintroduces
       the silent ``None`` the guard exists to prevent.
    3. The message names the field and says the result was refused, so a reader
       of the traceback learns which field and why without opening the SDK.
    """
    raised: BaseException | None = None
    try:
        getattr(result, field)
    except BaseException as failure:  # the subject under test may raise anything
        raised = failure
    if raised is None:
        raise AssertionError(
            f"reading `{field}` off a refused result returned instead of"
            " raising — a silent value is how a refusal becomes an empty answer"
            " downstream"
        )
    if not isinstance(raised, RefusedResultError):
        raise AssertionError(
            f"reading `{field}` off a refused result raised"
            f" {type(raised).__name__}, not RefusedResultError. An"
            " AttributeError in particular is swallowed by the three-argument"
            " getattr and by hasattr"
        )
    message = str(raised)
    if field not in message:
        raise AssertionError(
            f"the guard fired for `{field}` but its message does not name the"
            f" field: {message!r}"
        )
    if "refus" not in message.lower():
        raise AssertionError(
            f"the guard fired for `{field}` but its message does not say the"
            f" result was refused: {message!r}"
        )


def assert_served_field_reads(result: Result, field: str) -> None:
    """Assert reading ``field`` off a served result does not raise.

    The other half of the guard, and not a formality: a guard keyed on the
    wrong condition raises on *every* result, which would make the six raising
    assertions pass for entirely the wrong reason.
    """
    getattr(result, field)


def observe_failure(assertion: Any, *args: Any) -> BaseException:
    """Run a shipped assertion over a broken subject and return its failure.

    The controls call this rather than ``pytest.raises`` because the shipped
    assertion fails in more than one way depending on how the subject is
    broken — an ``AssertionError`` when the guard returns, and whatever the
    subject raised when the guard raises the wrong type. Naming the "it did not
    pass" observation once keeps every control comparing against the same
    thing, and makes a control that *passes* a hard failure rather than a
    quiet one.
    """
    try:
        assertion(*args)
    except BaseException as failure:  # catching everything IS the observation
        return failure
    raise AssertionError(
        "the shipped assertion passed on a deliberately broken subject, so it"
        " is not the check it claims to be"
    )


# --------------------------------------------------------------------------
# D-07 — refusal is a value, and `refused` is the branch
# --------------------------------------------------------------------------


def test_refused_is_false_on_a_served_result() -> None:
    assert a_served_result().refused is False


def test_refused_is_true_on_a_refused_result() -> None:
    assert a_refused_result().refused is True


def test_refusal_is_none_on_a_served_result() -> None:
    """The branch reads cleanly in both directions without a raise."""
    assert a_served_result().refusal is None


# --------------------------------------------------------------------------
# D-08 — the six guarded fields, one assertion each in each direction
# --------------------------------------------------------------------------


def test_the_guarded_fields_are_the_ruled_roster() -> None:
    """``D-08`` named six; ``24.6-07`` makes it five, under a ruling.

    A tuple that grew or shrank is a ruling and not a diff, so the change is
    named here rather than left to be noticed. ``replay_ref`` left the group
    because its membership rested on a premise the project removed, verbatim
    from the constant's own docstring: *"``replay_ref`` exists only after the
    replay record was written, which is strictly after all three gates
    passed."* ``D-IMPL-253`` Q13 — *"Refusal is itself a decision and deserves
    the same five-dimensional replay model. Do not create second-class
    replay."* — makes the second clause false. The identical inversion is
    applied at ``DoorOutcome``'s rule 5 in the same row.

    The other five are untouched, and that is the load-bearing half: this row
    reclassified exactly one name and weakened no guard.
    """
    assert GUARDED_FIELDS == (
        "payload",
        "debt",
        "content_address",
        "lineage",
        "expires_at",
    )
    assert "replay_ref" in PRE_ASSEMBLY_FIELDS
    assert "replay_ref" not in GUARDED_FIELDS


def test_a_refused_result_reads_its_replay_reference_rather_than_raising() -> None:
    """The inversion's behavioral half (``24.6-07``).

    The roster assertion above would pass on a `Result` that still raised — a
    tuple is not the guard. This reads the accessor on both halves.
    """
    refused = a_refused_result()
    assert refused.refused
    assert refused.replay_ref == "replay-2"
    # And the absence still reads as an absence rather than a raise: `None` is
    # *the producer published none*, on either half.
    assert a_refused_result(replay_ref=None).replay_ref is None
    assert a_served_result().replay_ref == "replay-1"


@pytest.mark.parametrize("field", GUARDED_FIELDS)
def test_a_refused_result_refuses_every_post_assembly_field(field: str) -> None:
    """Six raising assertions — one per name, never one standing for six."""
    assert_guard_holds(a_refused_result(), field)


@pytest.mark.parametrize("field", GUARDED_FIELDS)
def test_a_served_result_returns_every_post_assembly_field(field: str) -> None:
    """Six non-raising assertions, so the guard is proven keyed on refusal."""
    assert_served_field_reads(a_served_result(), field)


@pytest.mark.parametrize("field", GUARDED_FIELDS)
def test_a_served_result_returns_a_value_and_not_none(field: str) -> None:
    """Every guarded name has something real behind it on a served result."""
    assert getattr(a_served_result(), field) is not None


@pytest.mark.parametrize("field", GUARDED_FIELDS)
def test_the_guard_survives_the_three_argument_getattr(field: str) -> None:
    """``getattr(result, field, None)`` must not be able to swallow the guard.

    ``AttributeError`` would be the idiomatic choice for attribute access and
    is exactly wrong here: the three-argument ``getattr`` and ``hasattr`` both
    convert it back into the silent ``None`` that ``D-08`` exists to prevent.
    """
    sentinel = object()
    with pytest.raises(RefusedResultError):
        getattr(a_refused_result(), field, sentinel)


def test_the_guard_message_enumerates_every_guarded_name() -> None:
    """The guard reads the tuple, so its message cannot list a stale five."""
    raised = observe_failure(getattr, a_refused_result(), "payload")
    message = str(raised)
    for field in GUARDED_FIELDS:
        assert field in message, f"`{field}` is missing from the guard's message"


# --------------------------------------------------------------------------
# D-09 — the refusal stays auditable
# --------------------------------------------------------------------------


def test_a_refused_result_carries_the_refusal_reason_key_and_kind() -> None:
    result = a_refused_result()
    assert result.refusal is not None
    assert result.refusal.reason == "missing-required-parameter"
    assert result.refusal.key == "revenue_threshold"
    assert result.refusal.kind == "product-request-violation"


def test_a_refused_gate_result_keeps_its_own_kind_unflattened() -> None:
    """A second kind from a second family, so ``kind`` is carried not constant."""
    result = a_refused_result(refusal=a_gate_refusal())
    assert result.refusal is not None
    assert result.refusal.kind == "ttl-refusal"
    assert result.refusal.reason == "ttl-bounds"
    assert result.refusal.key is None


def test_a_refused_result_carries_the_refused_request_identity() -> None:
    result = a_refused_result()
    assert result.product_id == "ccf.test-product"
    assert result.parameters == _PARAMETERS
    assert result.temporal_boundary == _INSTANT


def test_a_served_result_carries_the_same_request_identity() -> None:
    result = a_served_result()
    assert result.product_id == "ccf.test-product"
    assert result.parameters == _PARAMETERS
    assert result.temporal_boundary == _INSTANT


def test_the_pre_assembly_lineage_rides_on_the_refusal() -> None:
    """``D-09``'s *"any pre-assembly lineage"*, carried rather than flattened.

    A request-conformity verdict is reached before the graph is touched and has
    none; ``None`` here is the positive assertion *there was none*, which is the
    distinction :mod:`ccf.products.refusal` refuses to lose.
    """
    result = a_refused_result()
    assert result.refusal is not None
    assert result.refusal.pre_assembly_lineage is None


def test_refusal_names_the_one_canonical_envelope_and_not_a_copy() -> None:
    """``Refusal`` *is* the shipped envelope; a copy is how two vocabularies start."""
    assert Refusal is RefusalEnvelope


# --------------------------------------------------------------------------
# The field partition — a seventh property cannot appear unclassified
# --------------------------------------------------------------------------


def public_properties(subject: type) -> set[str]:
    """Every public property ``subject`` itself declares.

    A function over a subject, so the control below can hand it a divergent
    class rather than re-implementing the walk.
    """
    return {
        name
        for name, member in vars(subject).items()
        if isinstance(member, property) and not name.startswith("_")
    }


def assert_properties_are_classified(subject: type) -> None:
    """Assert every public property is declared pre- or post-assembly.

    Without this, a seventh property added next year is neither guarded nor
    declared pre-assembly, and the six-field parameterization keeps passing
    while an ungoverned post-assembly value leaks off a refused result.
    """
    declared = set(GUARDED_FIELDS) | set(PRE_ASSEMBLY_FIELDS)
    unclassified = public_properties(subject) - declared
    if unclassified:
        raise AssertionError(
            f"{sorted(unclassified)} are properties of {subject.__name__} that"
            " are neither guarded nor declared pre-assembly — the assembly"
            " boundary is the rule and nothing may sit outside it"
        )


def test_every_public_property_is_declared_pre_or_post_assembly() -> None:
    assert_properties_are_classified(Result)


def test_the_declared_groups_cover_the_class_exactly() -> None:
    """Both directions: nothing unclassified, and nothing declared but absent."""
    assert public_properties(Result) == set(GUARDED_FIELDS) | set(
        PRE_ASSEMBLY_FIELDS
    )


def test_the_two_declared_groups_do_not_overlap() -> None:
    assert not set(GUARDED_FIELDS) & set(PRE_ASSEMBLY_FIELDS)


# --------------------------------------------------------------------------
# D-10 — one catch-all for "the wire never spoke"
# --------------------------------------------------------------------------


def test_binding_error_is_a_transport_error() -> None:
    """``except TransportError`` catches everything that means nothing was asked."""
    assert issubclass(BindingError, TransportError)


def test_a_binding_error_is_caught_by_the_transport_clause() -> None:
    """Asserted behaviourally too — a subclass relation nobody exercises."""
    with pytest.raises(TransportError):
        raise BindingError("no binding")


def test_the_negligence_error_is_not_a_transport_error() -> None:
    """The wire spoke perfectly; the caller ignored what it said.

    Folding negligence into :class:`~ccf.client.errors.TransportError` would
    make a caller's own bug look like an outage, and a retry loop around
    ``except TransportError`` would retry it forever.
    """
    assert not issubclass(RefusedResultError, TransportError)


# --------------------------------------------------------------------------
# Construction — the two halves are exclusive at construction, not by habit
# --------------------------------------------------------------------------


def test_a_result_carrying_both_halves_is_refused() -> None:
    with pytest.raises(ValueError, match="never both"):
        Result(
            product_id="ccf.test-product",
            parameters=_PARAMETERS,
            temporal_boundary=_INSTANT,
            vessel=a_vessel(),
            content_address=_ADDRESS,
            replay_ref=None,
            refusal=a_request_refusal(),
        )


def test_a_result_carrying_neither_half_is_refused() -> None:
    with pytest.raises(ValueError, match="carries neither"):
        Result(
            product_id="ccf.test-product",
            parameters=_PARAMETERS,
            temporal_boundary=_INSTANT,
            vessel=None,
            content_address=None,
            replay_ref=None,
            refusal=None,
        )


def test_a_served_result_without_a_content_address_is_refused() -> None:
    with pytest.raises(ValueError, match="content address"):
        Result(
            product_id="ccf.test-product",
            parameters=_PARAMETERS,
            temporal_boundary=_INSTANT,
            vessel=a_vessel(),
            content_address=None,
            replay_ref=None,
            refusal=None,
        )


def test_a_refused_result_carrying_a_content_address_is_refused() -> None:
    """A refusal is a governed answer, not a content-addressed artifact."""
    with pytest.raises(ValueError, match="content address"):
        Result(
            product_id="ccf.test-product",
            parameters=_PARAMETERS,
            temporal_boundary=_INSTANT,
            vessel=None,
            content_address=_ADDRESS,
            replay_ref=None,
            refusal=a_request_refusal(),
        )


# --------------------------------------------------------------------------
# Sabotage controls (D-22) — each passes a divergent subject into the shipped
# assertion, and each is observed failing
# --------------------------------------------------------------------------


def _refused(subject_type: type[Result]) -> Result:
    """Build a refused result of a divergent ``Result`` subclass."""
    return subject_type(
        product_id="ccf.test-product",
        parameters=_PARAMETERS,
        temporal_boundary=_INSTANT,
        vessel=None,
        content_address=None,
        replay_ref=None,
        refusal=a_request_refusal(),
    )


class _LeakyResult(Result):
    """A ``Result`` whose ``payload`` guard was replaced by a silent value.

    The exact defect ``17-RESEARCH.md`` §7 names for the ``D-08`` row —
    *"replace one guard with ``return None``; the test must fail for that field
    specifically."* Expressed as a subclass rather than as an edit under
    ``src/``, so the control leaves the shipped tree untouched while still
    handing the shipped assertion a real, broken subject.
    """

    @property
    def payload(self) -> Mapping[str, Any]:
        return {}


def test_control_the_guard_assertion_fires_on_a_leaked_field() -> None:
    """CONTROL 1 — a guard that returns instead of raising is caught."""
    failure = observe_failure(assert_guard_holds, _refused(_LeakyResult), "payload")
    assert isinstance(failure, AssertionError)
    assert "returned instead of raising" in str(failure)


def test_control_the_leak_is_detected_for_that_field_specifically() -> None:
    """CONTROL 2 — the other five still pass on the very same subject.

    A control proving only "something failed" would be satisfied by an
    assertion that fails for every field, which is the shape that makes a
    per-field parameterization decorative.
    """
    leaky = _refused(_LeakyResult)
    for field in GUARDED_FIELDS:
        if field == "payload":
            continue
        assert_guard_holds(leaky, field)


class _AttributeErrorResult(Result):
    """A guard raising ``AttributeError`` — the idiomatic, swallowable bug."""

    @property
    def debt(self) -> DebtAssessment | None:
        raise AttributeError("debt")


def test_control_an_attribute_error_guard_is_caught() -> None:
    """CONTROL 3 — the swallowable exception type is rejected by name.

    Without this control, a guard raising ``AttributeError`` satisfies a naive
    ``pytest.raises(Exception)`` while ``getattr(result, "debt", None)``
    silently hands the caller ``None``.
    """
    failure = observe_failure(
        assert_guard_holds, _refused(_AttributeErrorResult), "debt"
    )
    assert isinstance(failure, AssertionError)
    assert "not RefusedResultError" in str(failure)


class _UnnamedGuardResult(Result):
    """A guard raising the right type with a message naming no field."""

    @property
    def lineage(self) -> ProductLineage:
        raise RefusedResultError("refused")


def test_control_a_guard_whose_message_names_no_field_is_caught() -> None:
    """CONTROL 4 — the traceback obligation is asserted, not assumed."""
    failure = observe_failure(
        assert_guard_holds, _refused(_UnnamedGuardResult), "lineage"
    )
    assert isinstance(failure, AssertionError)
    assert "does not name the field" in str(failure)


class _AlwaysRaisingResult(Result):
    """A guard keyed on nothing, so it refuses a *served* result too."""

    @property
    def expires_at(self) -> datetime:
        raise RefusedResultError("expires_at was refused")


def test_control_a_guard_that_fires_on_a_served_result_is_caught() -> None:
    """CONTROL 5 — the six raising assertions must not pass vacuously.

    A guard keyed on the wrong condition raises for every result. All six
    ``pytest.raises`` assertions would then pass while the client refused every
    answer it ever received, so the served half needs its own control.
    """
    subject = _AlwaysRaisingResult(
        product_id="ccf.test-product",
        parameters=_PARAMETERS,
        temporal_boundary=_INSTANT,
        vessel=a_vessel(),
        content_address=_ADDRESS,
        replay_ref="replay-1",
        refusal=None,
    )
    failure = observe_failure(assert_served_field_reads, subject, "expires_at")
    assert isinstance(failure, RefusedResultError)


class _SeventhPropertyResult(Result):
    """A seventh public property, declared in neither group."""

    @property
    def graph_snapshot_at(self) -> datetime:
        return _INSTANT


def test_control_the_partition_assertion_fires_on_an_unclassified_property() -> None:
    """CONTROL 6 — an unclassified property is caught by the shipped assertion."""
    failure = observe_failure(
        assert_properties_are_classified, _SeventhPropertyResult
    )
    assert isinstance(failure, AssertionError)
    assert "graph_snapshot_at" in str(failure)
