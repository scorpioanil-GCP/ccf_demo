"""`ccf.policy-constraint` — the artifact a governed parameter boundary IS.

``24.6-01`` Task 2; ledger row ``24.6-L-07``; ``D-IMPL-253`` Q3 (*"Separate
Control Plane artifact. A policy constraint has independent identity, version,
effectivity and authority and should not disappear inside another bundle."*)
and Q5 (the five-member v0 vocabulary); ``D-IMPL-251`` (policy limits are not
placed in product-class registration); whitepaper §7.8.

**Nothing here resolves anything.** No resolver reads a constraint yet — plan
``24.6-02`` is the algorithm. What is asserted is that the *artifact* exists
with the identity, the vocabulary, the effectivity window and the independence
the ruling requires, and that each is refused by name when a document gets it
wrong.

The values below are fixture vocabulary, chosen to satisfy shape. They are not
calibrations and carry no meaning outside this module (CINV-01).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    CONSTRAINT_OPERATORS,
    POLICY_CONSTRAINT,
    ArtifactLoadError,
    ConstraintApplicability,
    PolicyConstraint,
    ProductClassDeclaration,
    load_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry

_FROM = datetime(2026, 1, 1, tzinfo=UTC)
_UNTIL = datetime(2027, 1, 1, tzinfo=UTC)


def _constraint(**overrides: object) -> PolicyConstraint:
    """A constraint that validates, with one field swapped per call."""
    fields: dict[str, object] = {
        "semver": "1.0.0",
        "policy_id": "fixture-regime",
        "applies_to": ConstraintApplicability(product_class="fixture-product"),
        "parameter": "fixture_parameter",
        "operator": "maximum",
        "value": Decimal("0.2"),
        "source_authority": "fixture-authority",
        "effective_from": _FROM,
        "reason": "fixture reason",
    }
    fields.update(overrides)
    return PolicyConstraint(**fields)  # type: ignore[arg-type]


# --- C-04's vocabulary half: closed by equality ------------------------------


def test_the_constraint_vocabulary_is_closed_by_set_equality() -> None:
    """``D-IMPL-253`` Q5's five members and no sixth. Equality, never a count:
    a right count with a wrong member audits clean forever.

    The never-refuses property of ``preferred`` is NOT asserted here — it is a
    property of a *resolution* and belongs to plan ``24.6-02``. What this
    module owns is that the member exists and that a `preferred` document
    validates.
    """
    assert CONSTRAINT_OPERATORS == frozenset(
        {"maximum", "minimum", "allowed_set", "required", "preferred"}
    )


# --- each operator's value type, admitted and refused ------------------------


@pytest.mark.parametrize(
    ("operator", "value"),
    [
        ("maximum", Decimal("0.2")),
        ("minimum", Decimal("0.1")),
        ("allowed_set", ("fixture-a", "fixture-b")),
        ("required", None),
        ("preferred", Decimal("0.5")),
        ("preferred", "fixture-name"),
    ],
)
def test_each_operator_admits_the_value_type_it_bounds(
    operator: str, value: object
) -> None:
    constraint = _constraint(operator=operator, value=value)
    assert constraint.operator == operator
    assert constraint.value == value


@pytest.mark.parametrize(
    ("operator", "value", "named"),
    [
        ("maximum", "fixture-name", "maximum"),
        ("minimum", ("fixture-a",), "minimum"),
        ("allowed_set", Decimal("0.2"), "allowed_set"),
        ("allowed_set", (), "allowed_set"),
        ("required", Decimal("0.2"), "required"),
        ("preferred", ("fixture-a",), "preferred"),
    ],
)
def test_a_value_that_does_not_match_its_operator_is_refused_by_name(
    operator: str, value: object, named: str
) -> None:
    with pytest.raises(ValueError) as raised:
        _constraint(operator=operator, value=value)
    assert named in str(raised.value)


def test_an_operator_outside_the_vocabulary_is_refused() -> None:
    with pytest.raises(ValueError):
        _constraint(operator="fixture-operator", value=Decimal("0.2"))


def test_a_quoted_number_under_a_numeric_operator_reads_as_a_decimal() -> None:
    """A Control Plane document quotes its numbers — a YAML float is refused
    outright — so the operator is what makes the decimal reading unambiguous.
    Without this the correct document would be refused by the operator check.
    """
    constraint = _constraint(operator="maximum", value="0.2")
    assert constraint.value == Decimal("0.2")
    assert isinstance(constraint.value, Decimal)


def test_a_quoted_name_under_preferred_stays_a_name() -> None:
    """The positive control for the coercion above: it fires only where the
    numeric reading cannot mean anything else. `preferred` admits both, so
    guessing between them would be the silent repair this module refuses."""
    constraint = _constraint(operator="preferred", value="fixture-name")
    assert constraint.value == "fixture-name"
    assert not isinstance(constraint.value, Decimal)


# --- effectivity ------------------------------------------------------------


def test_an_effectivity_window_that_closes_before_it_opens_is_refused() -> None:
    with pytest.raises(ValueError) as raised:
        _constraint(effective_from=_UNTIL, effective_until=_FROM)
    assert "effective_until" in str(raised.value)


def test_an_open_ended_window_is_admitted_and_hash_transparent() -> None:
    """``None`` is *no stated end*, and the field renders as absent at that
    sentinel (``D-IMPL-243``) — a constraint with no end hashes as though the
    key were not there."""
    from ccf.contracts.canonical import canonical_bytes

    assert _constraint().effective_until is None
    assert b"effective_until" not in canonical_bytes(_constraint())
    assert b"effective_until" in canonical_bytes(_constraint(effective_until=_UNTIL))


_NAIVE_DOCUMENT = """
semver: "1.0.0"
policy_id: fixture-regime
applies_to:
  product_class: fixture-product
parameter: fixture_parameter
operator: maximum
value: "0.2"
source_authority: fixture-authority
effective_from: 2026-01-01T00:00:00
reason: fixture reason
"""

_ZONED_DOCUMENT = _NAIVE_DOCUMENT.replace(
    "2026-01-01T00:00:00", "2026-01-01T00:00:00Z"
)


def test_a_zone_less_effective_from_is_refused_by_the_loader() -> None:
    """Not re-implemented on the contract: :func:`load_artifact` already
    refuses a zone-less timestamp in any Control Plane document (``D-IMPL-38``,
    no implicit UTC). Asserted here because D-06's effectivity comparison at
    ``asked_at`` is aware-versus-aware, and this is what makes it so."""
    with pytest.raises(ArtifactLoadError) as raised:
        load_artifact(_NAIVE_DOCUMENT, POLICY_CONSTRAINT)
    assert "effective_from" in str(raised.value)


def test_the_same_document_with_a_zone_loads(
) -> None:
    """The positive control: the refusal above is about the missing zone and
    not about the document being unloadable."""
    constraint = load_artifact(_ZONED_DOCUMENT, POLICY_CONSTRAINT)
    assert isinstance(constraint, PolicyConstraint)
    assert constraint.effective_from == _FROM
    assert constraint.value == Decimal("0.2")


# --- independent identity: the whole reason it is its own class --------------


def test_registering_a_constraint_mints_a_content_hash_version() -> None:
    registry = ControlPlaneRegistry()
    constraint = _constraint()
    version = registry.register_typed(
        "policy_constraints.fixture", constraint, POLICY_CONSTRAINT
    )
    assert version == content_hash(constraint)
    assert registry.keys_of_class("ccf.policy-constraint") == (
        "policy_constraints.fixture",
    )
    assert registry.resolve("policy_constraints.fixture", version) == constraint


def test_two_constraints_of_one_policy_id_are_two_artifacts() -> None:
    """``D-IMPL-253`` Q3's *"should not disappear inside another bundle"*, as a
    measurement: one regime, two parameters, two keys, two content-hash
    versions, and each resolvable on its own."""
    registry = ControlPlaneRegistry()
    ceiling = _constraint(parameter="fixture_parameter_a")
    floor = _constraint(
        parameter="fixture_parameter_b", operator="minimum", value=Decimal("0.1")
    )
    assert ceiling.policy_id == floor.policy_id

    ceiling_version = registry.register_typed(
        "policy_constraints.ceiling", ceiling, POLICY_CONSTRAINT
    )
    floor_version = registry.register_typed(
        "policy_constraints.floor", floor, POLICY_CONSTRAINT
    )

    assert ceiling_version != floor_version
    assert set(registry.keys_of_class("ccf.policy-constraint")) == {
        "policy_constraints.ceiling",
        "policy_constraints.floor",
    }
    assert registry.resolve("policy_constraints.floor", floor_version) == floor


def test_the_product_class_declaration_names_no_policy_constraint() -> None:
    """``D-IMPL-251``: policy limits are not placed in product-class
    registration, *"because then you lose the ability to answer: is this a
    property of the product, or a rule imposed by a particular policy
    regime?"* Asserted against the field list rather than against one
    document."""
    fields = " ".join(ProductClassDeclaration.model_fields)
    assert "policy_constraint" not in fields
    assert "constraint" not in fields


def test_a_lane_less_constraint_cannot_be_declared() -> None:
    """The `VersionedArtifact` inheritance, asserted rather than assumed: a
    constraint whose author never stated its lane is refused, because a
    default would be a version nobody chose."""
    with pytest.raises(ValueError):
        PolicyConstraint(  # type: ignore[call-arg]
            policy_id="fixture-regime",
            applies_to=ConstraintApplicability(),
            parameter="fixture_parameter",
            operator="required",
            value=None,
            source_authority="fixture-authority",
            effective_from=_FROM,
            reason="fixture reason",
        )


def test_an_applicability_that_narrows_nothing_is_the_empty_statement() -> None:
    """``None`` means *any* on every axis, and the four members are
    hash-transparent at it, so an applicability narrowing nothing renders as
    nothing (``D-IMPL-243``)."""
    from ccf.contracts.canonical import canonical_bytes

    everything = ConstraintApplicability()
    assert everything.product_class is None
    assert everything.tenant is None
    assert everything.perspective_role is None
    assert everything.intent is None
    assert canonical_bytes(everything) == b"{}"


def test_an_undeclared_key_is_refused_rather_than_carried() -> None:
    with pytest.raises(ValueError):
        _constraint(jurisdiction="fixture-jurisdiction")
