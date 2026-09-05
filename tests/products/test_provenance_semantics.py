"""The Authority layer's value, held to Dave's four worked cases.

``24.6-01`` Task 1; ``D-IMPL-253`` Q1/Q6 and Amendment 2 (1); ``D-IMPL-254``.
:mod:`ccf.products.provenance` resolves nothing — plan ``24.6-02`` is the
algorithm and ``24.6-03`` is the resolver seam — so what is asserted here is
the *contract*: the closed authority vocabulary, the refusal of a manufactured
artifact source, and that the four cases are constructible and canonically
renderable in this shape with both authorities intact.

**The numbers live here and not in ``src/``** (CINV-01). They are Dave's
worked cases, quoted from ``24.6-RULINGS.md`` §1, and they are fixtures of a
test rather than calibration the SDK ships.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.products.provenance import (
    AUTHORITIES,
    EffectiveParameter,
    EffectiveRequest,
    OverrideRecord,
    ParameterBound,
    ProvenanceSource,
)

_ASKED_AT = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)

#: The request contract that declares the default of cases 1-3, as a pinned
#: artifact source. A default IS Control Plane data, so this kind has a lane.
_CONTRACT = ProvenanceSource(
    kind="artifact", identity="request_contract", version="c0ffee"
)
#: The caller's own question. No lane, deliberately.
_REQUEST = ProvenanceSource(kind="request", identity="req-1", version=None)
#: Case 3's policy constraint — an artifact, so a lane.
_POLICY = ProvenanceSource(
    kind="artifact", identity="policy_constraints.tolerance", version="beadfeed"
)
#: Case 4's technical maximum. A backend capability, NOT an artifact:
#: ``D-IMPL-253`` amendment 2 (1) refuses a manufactured artifact id here.
_CAPABILITY = ProvenanceSource(
    kind="capability", identity="graph.backend.max_depth", version=None
)


# --- (a) the vocabulary, closed by equality ----------------------------------


def test_the_authority_vocabulary_is_closed_by_set_equality() -> None:
    """Four members and no fifth (``D-IMPL-253`` Q1). Equality, never a count:
    a right count with a wrong member audits clean forever."""
    assert AUTHORITIES == frozenset({"default", "caller", "policy", "technical"})


# --- (b) a manufactured artifact source is refused by construction -----------


def test_an_artifact_source_without_a_version_is_refused() -> None:
    with pytest.raises(ValueError) as raised:
        ProvenanceSource(kind="artifact", identity="request_contract", version=None)
    assert "D-IMPL-26" in str(raised.value)


@pytest.mark.parametrize("kind", ["request", "capability"])
def test_a_request_or_capability_source_carrying_a_version_is_refused(
    kind: str,
) -> None:
    """Amendment 2 (1) made structural: the fake-artifact path is closed at
    construction rather than left to authorial discipline."""
    with pytest.raises(ValueError) as raised:
        ProvenanceSource(kind=kind, identity="x", version="1")  # type: ignore[arg-type]
    assert "D-IMPL-253" in str(raised.value)


def test_the_two_valid_shapes_are_admitted() -> None:
    """The positive control for the pair above: the refusals are about the
    version/kind disagreement and not about the type being unbuildable."""
    assert _CONTRACT.version == "c0ffee"
    assert _REQUEST.version is None
    assert _CAPABILITY.version is None


# --- (c) the four worked cases, constructed by hand --------------------------


#: Case 1 — default .25, caller .30, no policy → effective .30, authority
#: caller. The default did not compete with a value the caller stated.
_CASE_1 = EffectiveParameter(
    name="debt_tolerance",
    value=Decimal(".30"),
    authority="caller",
    source=_REQUEST,
)
#: Case 2 — default .25, caller omitted, no policy → effective .25, authority
#: default, sourced from the contract's own pin.
_CASE_2 = EffectiveParameter(
    name="fallback_tolerance",
    value=Decimal(".25"),
    authority="default",
    source=_CONTRACT,
)
#: Case 3 — default .25, caller .30, policy maximum .20 → effective .20,
#: authority policy. The caller's .30 is NOT here; it lives on
#: ``RequestIdentity.parameters``, which this record never replaces.
_CASE_3 = EffectiveParameter(
    name="bounded_tolerance",
    value=Decimal(".20"),
    authority="policy",
    source=_POLICY,
    bound=ParameterBound(
        operator="maximum",
        value=Decimal(".20"),
        authority="policy",
        source=_POLICY,
        policy_id="tolerance-policy",
    ),
)
#: Case 4 — default 6, caller 8, technical maximum 100 → effective 8, authority
#: caller, BOUND authority technical. Two authorities at once.
_CASE_4 = EffectiveParameter(
    name="max_depth",
    value=8,
    authority="caller",
    source=_REQUEST,
    bound=ParameterBound(
        operator="maximum",
        value=100,
        authority="technical",
        source=_CAPABILITY,
    ),
)

_RESOLVED = EffectiveRequest(
    parameters=(_CASE_1, _CASE_2, _CASE_3, _CASE_4),
    guidance=(),
    overrides=(),
    applied=(_CONTRACT, _REQUEST, _POLICY, _CAPABILITY),
    asked_at=_ASKED_AT,
)


def test_the_four_cases_resolve_to_the_ruled_effective_values() -> None:
    assert _RESOLVED.values() == {
        "debt_tolerance": Decimal(".30"),
        "fallback_tolerance": Decimal(".25"),
        "bounded_tolerance": Decimal(".20"),
        "max_depth": 8,
    }


def test_each_case_keeps_the_authority_that_established_its_value() -> None:
    assert _CASE_1.authority == "caller"
    assert _CASE_2.authority == "default"
    assert _CASE_3.authority == "policy"
    assert _CASE_4.authority == "caller"


def test_case_four_carries_two_authorities_at_once() -> None:
    """The property a scalar cannot express: the value is the caller's and the
    bound that admitted it is the backend's."""
    bound = _CASE_4.bound
    assert bound is not None
    assert _CASE_4.authority == "caller"
    assert bound.authority == "technical"
    assert bound.source.kind == "capability"
    assert bound.source.version is None


def test_case_three_records_the_policy_as_the_authority_of_the_value() -> None:
    bound = _CASE_3.bound
    assert bound is not None
    assert _CASE_3.authority == "policy"
    assert bound.policy_id == "tolerance-policy"
    assert bound.source.version == "beadfeed"


def test_the_resolved_request_renders_canonically() -> None:
    """Every value in the record is canonically encodable, so a resolution can
    reach a content address and therefore replay."""
    rendered = canonical_bytes(_RESOLVED)
    assert b"technical" in rendered
    assert b"0.30" in rendered
    assert canonical_bytes(_RESOLVED) == rendered


def test_a_float_value_is_refused_rather_than_left_to_fail_at_rendering() -> None:
    with pytest.raises(ValueError) as raised:
        EffectiveParameter(
            name="debt_tolerance",
            value=0.30,
            authority="caller",
            source=_REQUEST,
        )
    assert "float" in str(raised.value)


def test_a_float_inside_a_container_is_refused_too() -> None:
    """The container is not an escape: a tuple of floats is the same defect."""
    with pytest.raises(ValueError):
        ParameterBound(
            operator="allowed_set",
            value=(0.1, 0.2),
            authority="policy",
            source=_POLICY,
        )


def test_a_parameter_resolved_twice_is_refused_by_name() -> None:
    with pytest.raises(ValueError) as raised:
        EffectiveRequest(
            parameters=(_CASE_1, _CASE_1),
            guidance=(),
            overrides=(),
            applied=(_REQUEST,),
            asked_at=_ASKED_AT,
        )
    assert "debt_tolerance" in str(raised.value)


def test_an_unresolved_name_answers_none_rather_than_raising() -> None:
    assert _RESOLVED.parameter("max_depth") is _CASE_4
    assert _RESOLVED.parameter("not_a_parameter") is None


# --- the two halves of an override are two facts -----------------------------


def test_an_unentitled_override_attempt_is_recordable() -> None:
    """``D-IMPL-253`` Q7: naming a policy is not authority to override it, and
    the attempt is a thing that happened."""
    attempt = OverrideRecord(
        policy_id="tolerance-policy",
        policy_version="beadfeed",
        principal_id="analyst-1",
        entitled=False,
        honored=False,
    )
    assert attempt.grant_source is None
    assert canonical_bytes(attempt)


def test_the_optional_members_are_hash_transparent_at_their_sentinels() -> None:
    """``D-IMPL-243``: a record with nothing optional stated renders as it
    would have without the optional keys."""
    bare = ParameterBound(
        operator="maximum", value=100, authority="technical", source=_CAPABILITY
    )
    assert b"policy_id" not in canonical_bytes(bare)
    assert b"bound" not in canonical_bytes(
        EffectiveParameter(
            name="max_depth", value=8, authority="caller", source=_REQUEST
        )
    )
