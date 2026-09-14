"""Verifying a producer's child-eligibility assertion — the consumer's side.

`D-IMPL-336` **Amendment 5**. These tests were `tests/products/test_composite.py`'s
`F7` group. They moved with the code they exercise: Dave's ruling was *"Remove
duplicated verification machinery from `composite.py`, not the verification
itself… Peering/A2A: retain signature, trust, policy, and eligibility
verification in the peering layer."*

**This is a RELOCATION, not a deletion.** Every control the composite-side
group asserted is asserted here, against
:func:`ccf.peering.eligibility.verify_child_eligibility`, which is the one call
composition now makes. What is gone is composition's *copy* of the five
equality bindings and the age bound.

The load-bearing case is the third one: a producer legitimately checks
eligibility **today** for a reconstruction request about **the past**, so
`checked_at` is far later than `asked_at` and an ordering check between them
would refuse every honest peered answer about history.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.peering.admission import PRODUCER_ASSERTION_HEADER
from ccf.peering.eligibility import (
    ELIGIBILITY_ASSERTION_HEADER,
    ELIGIBILITY_EVIDENCE_POLICY,
    EligibilityEvidence,
    EligibilityEvidencePolicy,
    EligibilityRefused,
    eligibility_evidence_policy_key,
    encode_eligibility_assertion,
    mint_eligibility_assertion,
    verify_child_eligibility,
)

TENANT = "tenant-composite"
CONSUMER_SCOPE = "consumer://memo-desk"
INVOCATION = "composition://inv-0001"
PRODUCER = "producer-hash"

ASKED_AT = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
SERVED_AT = datetime(2026, 3, 1, 12, 30, tzinfo=UTC)
ADDRESS = "child-content-address"


@pytest.fixture()
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


def declare_bound(
    registry: ControlPlaneRegistry, *, max_age: int = 3600, skew: int = 60
) -> None:
    registry.register_typed(
        eligibility_evidence_policy_key(tenant_id=TENANT),
        EligibilityEvidencePolicy(
            max_evidence_age_seconds=max_age, permitted_clock_skew_seconds=skew
        ),
        ELIGIBILITY_EVIDENCE_POLICY,
    )


def header(
    *,
    checked_at: datetime,
    address: str = ADDRESS,
    as_of: datetime = ASKED_AT,
    producer: str = PRODUCER,
    consumer: str = CONSUMER_SCOPE,
    invocation: str = INVOCATION,
    eligible: bool = True,
) -> dict[str, object]:
    """An AUTHENTICATED protected header, as a peering admission carries it out.

    A test standing in for the peering gate is the one caller that legitimately
    holds that position; deployment code never assembles this mapping, which is
    the property `F16` exists to keep.
    """
    assertion = mint_eligibility_assertion(
        child_content_address=address,
        requested_as_of=as_of,
        producer=producer,
        consumer_scope=consumer,
        checked_at=checked_at,
        composition_invocation=invocation,
        eligible=eligible,
    )
    return {
        PRODUCER_ASSERTION_HEADER: producer,
        ELIGIBILITY_ASSERTION_HEADER: encode_eligibility_assertion(assertion),
    }


def verify(
    registry: ControlPlaneRegistry,
    head: dict[str, object],
    *,
    admitted_at: datetime = SERVED_AT,
    as_of: datetime = ASKED_AT,
    address: str = ADDRESS,
    consumer: str = CONSUMER_SCOPE,
    invocation: str = INVOCATION,
    producer: str = PRODUCER,
) -> EligibilityEvidence | EligibilityRefused:
    return verify_child_eligibility(
        header=head,
        child_content_address=address,
        requested_as_of=as_of,
        verified_producer=producer,
        consumer_scope=consumer,
        composition_invocation=invocation,
        admitted_at=admitted_at,
        registry=registry,
        tenant_id=TENANT,
    )


def test_f7_a_stale_producer_check_is_refused_against_a_declared_bound(
    registry: ControlPlaneRegistry,
) -> None:
    """`F7`: 1970 and 2999 both admitted before. Both refuse now.

    Measured against **admission time**, not against `asked_at` — the
    distinction the ruling turns on.
    """
    declare_bound(registry)
    fresh = verify(registry, header(checked_at=SERVED_AT))
    assert isinstance(fresh, EligibilityEvidence)
    assert fresh.checked_at == SERVED_AT

    for label, when in [
        ("56y stale", datetime(1970, 1, 1, tzinfo=UTC)),
        ("973y future", datetime(2999, 12, 31, tzinfo=UTC)),
    ]:
        out = verify(registry, header(checked_at=when))
        assert isinstance(out, EligibilityRefused), label
        assert out.reason == "eligibility-evidence-stale", label


def test_f7_a_historical_asked_at_does_NOT_make_honest_evidence_stale(
    registry: ControlPlaneRegistry,
) -> None:
    """The ruling's load-bearing half, and the one an ordering check breaks.

    A producer checks eligibility TODAY for a reconstruction request about the
    past. `checked_at` is legitimately far later than `asked_at`, and comparing
    the two would refuse every honest peered answer about history.
    """
    declare_bound(registry)
    historical = datetime(2020, 1, 1, tzinfo=UTC)
    out = verify(
        registry,
        header(checked_at=SERVED_AT, as_of=historical),
        as_of=historical,
    )
    assert isinstance(out, EligibilityEvidence)
    assert out.checked_at == SERVED_AT


def test_f7_an_undeclared_bound_refuses_rather_than_defaulting(
    registry: ControlPlaneRegistry,
) -> None:
    """No hardcoded duration, no numeric default: missing config fails loudly."""
    out = verify(registry, header(checked_at=SERVED_AT))
    assert isinstance(out, EligibilityRefused)
    # Its OWN reason, not "stale" (found by the repair's own review panel): a
    # tenant that declared no bound has a CONFIGURATION error, and telling the
    # operator their peer's evidence is stale would name the wrong party.
    assert out.reason == "eligibility-bound-undeclared"
    assert "declared no eligibility-evidence bound" in out.detail


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        ("a different child", {"address": "another-address"}),
        ("a different instant", {"as_of": datetime(2025, 1, 1, tzinfo=UTC)}),
        ("a different producer", {"producer": "someone-else"}),
        ("a different consumer", {"consumer": "consumer://other-desk"}),
        ("a different composition", {"invocation": "composition://other"}),
    ],
)
def test_every_binding_is_checked_by_EQUALITY(
    registry: ControlPlaneRegistry, label: str, kwargs: dict[str, object]
) -> None:
    """All five, each moved alone, each refusing.

    An assertion is not bearer currency: it authorizes one child, for one
    instant, from one producer, to one consumer, in one composition. A table
    that moved two facts at once could pass while only one binding worked.
    """
    declare_bound(registry)
    minted = header(checked_at=SERVED_AT, **kwargs)  # type: ignore[arg-type]
    out = verify(registry, minted)
    assert isinstance(out, EligibilityRefused), label
    assert out.reason == "eligibility-evidence-mismatch", label


def test_a_signed_NEGATIVE_is_honored_rather_than_ignored(
    registry: ControlPlaneRegistry,
) -> None:
    """The producer saying "not eligible" is a governed answer, not noise."""
    declare_bound(registry)
    out = verify(registry, header(checked_at=SERVED_AT, eligible=False))
    assert isinstance(out, EligibilityRefused)
    assert out.reason == "ineligible"


def test_a_header_carrying_no_assertion_is_refused_not_passed(
    registry: ControlPlaneRegistry,
) -> None:
    """Absence is not eligibility. A verified envelope with no assertion
    establishes nothing, and *don't know* must never read as *pass*."""
    declare_bound(registry)
    out = verify(registry, {PRODUCER_ASSERTION_HEADER: PRODUCER})
    assert isinstance(out, EligibilityRefused)
    assert out.reason == "eligibility-evidence-missing"
