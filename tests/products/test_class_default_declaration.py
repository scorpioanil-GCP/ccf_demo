"""A class default naming an undeclared parameter fails at wiring, not at a door.

``D-IMPL-258`` (5), Dave, verbatim:

    *"Under Q2, a product default is part of the request contract. Therefore a
    default naming a parameter the contract does not expose is a
    malformed/internally inconsistent declaration. That should fail
    registration/configuration/boot validation, not produce a shell to a
    caller. … Default for undeclared parameter → configuration/invariant
    failure. Caller outside a valid declared constraint → governed shell."*

``24.6-04`` put that refusal in
:func:`~ccf.products.constraints.resolve_effective_request`, which reaches it
once per **request**: a self-contradicting Control Plane served every other
class happily and failed the moment somebody asked a question. The ruling moves
it to the two moments a declaration is taken up, and this module is where both
are proved:

=========================================  ===================================
Moment                                     What would fail here
=========================================  ===================================
registration                               a class could be registered against
(``register_product_class``)               a contract that cannot express its
                                           own default, and become servable
boot                                       a resolver could be composed over
(``build_governed_resolver``)              that pair, so the contradiction
                                           reached a caller
the scoping                                the check could widen to a class
                                           that pins NO request contract — a
                                           posture the ruling does not name
                                           and three shipped fixtures hold
the surviving guard                        the resolution-time raise could be
                                           deleted, leaving a public pure
                                           function to fold in a default its
                                           own argument says is undeclared
=========================================  ===================================

Class, lane, parameter and key names are test fixture vocabulary; the SDK ships
none of them (CINV-01). The one name that is **not** fixture vocabulary is
:data:`~ccf.products.gates.DEBT_TOLERANCE_PARAMETER`, which is the SDK's own
mechanism token for the parameter a declared tolerance arrives under.
"""

from __future__ import annotations

import dataclasses
import pathlib
from decimal import Decimal
from typing import Any, Iterator

import pytest

from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    NO_REQUEST_CONTRACT,
    MaxTTL,
    ProductClassRegistrationError,
    ServeObligations,
    register_product_class,
)
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.request import (
    ProductRequestContract,
    refuse_undeclared_class_default,
)
from ccf.products.resolver import build_governed_resolver
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

from tests.deployment.conftest import PRODUCT_CLASS_KEY
from tests.products.test_resolver_defaults import _Booted, _arguments, _boot

#: Test fixture vocabulary.
CLASS_NAME = "fixture.class-default-declaration"
CLASS_VERSION = "1.0.0"
CONTRACT_KEY = "fixture.request-contract"
MAX_TTL_KEY = "fixture.max-ttl"
OTHER_PARAMETER = "fixture_threshold"

#: The number a class declares. Authored here, in a test, never in ``src/``
#: (CINV-01): the SDK ships the machinery for a tolerance and no tolerance.
DECLARED_DEFAULT = Decimal("0.4")


def _arguments_schema(*names: str) -> SkillArgumentSchema:
    return SkillArgumentSchema(
        properties={
            name: SkillArgumentProperty(
                type="number", description=f"a fixture argument named {name}"
            )
            for name in names
        },
        required=(),
    )


def _contract(*names: str) -> ProductRequestContract:
    return ProductRequestContract(
        semver="1.0.0",
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        arguments=_arguments_schema(*names),
    )


def _register(
    *, contract: ProductRequestContract | None, obligations: ServeObligations
) -> Any:
    """Register through the real factory, with a valid MAX_TTL and pin."""
    registry = ControlPlaneRegistry()
    max_ttl_version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=600))
    pin: dict[str, str] = {
        "request_contract_key": NO_REQUEST_CONTRACT,
        "request_contract_version": NO_REQUEST_CONTRACT,
    }
    if contract is not None:
        pin = {
            "request_contract_key": CONTRACT_KEY,
            "request_contract_version": registry.register(CONTRACT_KEY, contract),
        }
    return register_product_class(
        registry=registry,
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=MAX_TTL_KEY,
        max_ttl_version=max_ttl_version,
        serve_obligations=obligations,
        **pin,
    )


# ---------------------------------------------------------------------------
# (1) The pure check, and its control.
# ---------------------------------------------------------------------------


def test_the_check_refuses_a_default_the_contract_does_not_expose() -> None:
    """The malformed pair, refused by name with both remedies stated.

    What would fail here: a check that reported *which* parameter without
    saying what the contract does declare, which is the half an author needs
    to see the contradiction rather than take the message on trust.
    """
    with pytest.raises(ProductClassRegistrationError) as refused:
        refuse_undeclared_class_default(
            schema_name=CLASS_NAME,
            schema_version=CLASS_VERSION,
            serve_obligations=ServeObligations(
                default_debt_tolerance=DECLARED_DEFAULT
            ),
            declared=_contract(OTHER_PARAMETER),
        )

    message = str(refused.value)
    assert DEBT_TOLERANCE_PARAMETER in message
    assert OTHER_PARAMETER in message
    assert "Declare the argument on the request contract" in message
    assert "remove the class default" in message
    assert "D-IMPL-258 (5)" in message


def test_the_check_is_silent_when_the_contract_declares_the_parameter() -> None:
    """The control. Without it the refusal above could be unconditional."""
    refuse_undeclared_class_default(
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        serve_obligations=ServeObligations(default_debt_tolerance=DECLARED_DEFAULT),
        declared=_contract(OTHER_PARAMETER, DEBT_TOLERANCE_PARAMETER),
    )


def test_the_check_is_silent_when_the_class_declares_no_default() -> None:
    """A second control: no default is no contradiction, whatever the contract."""
    refuse_undeclared_class_default(
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        serve_obligations=ServeObligations(),
        declared=_contract(OTHER_PARAMETER),
    )


def test_a_class_pinning_no_contract_is_out_of_scope_and_stays_servable() -> None:
    """The scoping, stated as a measurement rather than left implicit.

    Dave's sentence is *"a default naming a parameter the contract does not
    expose"*, which presupposes a contract. A class pinning none is the
    pre-``D-IMPL-98`` posture: nothing validates a question against a declared
    surface, so nothing can refuse one as ``undeclared-parameter`` and the
    failure this check prevents does not arise. Three fixtures in
    ``tests/products/test_structural_gates.py`` hold exactly that pair.

    Whether the wider rule should also refuse it is put to Dave in
    ``24.6-D-IMPL-258-FIXES.md``; it is not decided here, and this test is what
    turns red the day somebody decides it silently.
    """
    refuse_undeclared_class_default(
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        serve_obligations=ServeObligations(default_debt_tolerance=DECLARED_DEFAULT),
        declared=None,
    )


# ---------------------------------------------------------------------------
# (2) Registration reaches it.
# ---------------------------------------------------------------------------


def test_registration_refuses_the_malformed_declaration() -> None:
    """The check is REACHED from the factory, not merely defined beside it.

    The distinction ``15.5-15`` had to close for the pin refusal, made again
    here: a check nothing calls and a check that runs look identical in a
    module listing.
    """
    with pytest.raises(ProductClassRegistrationError, match="D-IMPL-258"):
        _register(
            contract=_contract(OTHER_PARAMETER),
            obligations=ServeObligations(default_debt_tolerance=DECLARED_DEFAULT),
        )


def test_registration_accepts_the_declared_pair() -> None:
    """The control for the registration leg, and the class is really built."""
    registered = _register(
        contract=_contract(OTHER_PARAMETER, DEBT_TOLERANCE_PARAMETER),
        obligations=ServeObligations(default_debt_tolerance=DECLARED_DEFAULT),
    )

    assert registered.schema_name == CLASS_NAME
    assert registered.serve_obligations.default_debt_tolerance == DECLARED_DEFAULT
    assert registered.request_contract_key == CONTRACT_KEY


def test_registration_accepts_a_default_with_no_pinned_contract() -> None:
    """The scoped case, through the factory rather than only through the check."""
    registered = _register(
        contract=None,
        obligations=ServeObligations(default_debt_tolerance=DECLARED_DEFAULT),
    )

    assert registered.request_contract_key == NO_REQUEST_CONTRACT
    assert registered.serve_obligations.default_debt_tolerance == DECLARED_DEFAULT


# ---------------------------------------------------------------------------
# (3) Boot reaches it, over a real booted deployment.
# ---------------------------------------------------------------------------


@pytest.fixture()
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The ``tests/products/test_resolver_defaults`` deployment, booted.

    Reused rather than rebuilt: its manifest already carries a product class, a
    request contract that does **not** declare
    :data:`~ccf.products.gates.DEBT_TOLERANCE_PARAMETER`, and everything
    :func:`~ccf.products.resolver.build_governed_resolver` needs — so the only
    thing this module varies is the one declaration under test.
    """
    yield from _boot(tmp_path, "class-default-declaration")


def _declaring(booted: _Booted, obligations: ServeObligations) -> _Booted:
    """The same booted deployment, with the class declaring ``obligations``.

    A ``dataclasses.replace`` over the frozen
    :class:`~ccf.deployment.manifest.BootedFabric` rather than a mutation:
    the fixture stays what it was, and what changed is one artifact in one
    copy — which is also how an adopter's *edit to a declaration document*
    reaches the boot path.
    """
    declaration = booted.fabric.artifacts[PRODUCT_CLASS_KEY]
    assert isinstance(declaration, ProductClassDeclaration)
    fabric = dataclasses.replace(
        booted.fabric,
        artifacts={
            **booted.fabric.artifacts,
            PRODUCT_CLASS_KEY: declaration.model_copy(
                update={"serve_obligations": obligations}
            ),
        },
    )
    return dataclasses.replace(booted, fabric=fabric)


def test_the_fixture_contract_really_does_not_declare_the_parameter(
    booted: _Booted,
) -> None:
    """The premise of the two boot tests, measured rather than assumed.

    A fixture whose contract happened to declare the parameter would make the
    refusal below unreachable and the acceptance below vacuous, and both would
    still be green.
    """
    from ccf.products.resolver import _request_contract_on

    from tests.products.test_resolver_seam import REQUEST_CONTRACT_KEY

    contract = _request_contract_on(booted.fabric, key=REQUEST_CONTRACT_KEY)

    assert DEBT_TOLERANCE_PARAMETER not in contract.arguments.properties


def test_boot_refuses_the_malformed_declaration(booted: _Booted) -> None:
    """``build_governed_resolver`` refuses before it composes anything.

    Dave: *"That should fail registration/configuration/boot validation, not
    produce a shell to a caller."* This is the leg that makes the ruling bite
    for the shipped serving path: ``register_product_class`` runs per *serve*
    inside :class:`~ccf.products.resolver.GovernedResolver`, so registration
    alone would have moved the failure one frame and not one moment.

    What would fail here: the check living only in ``register_product_class``,
    which this deployment reaches for the first time after the caller's request
    has already been resolved.
    """
    declaring = _declaring(
        booted, ServeObligations(default_debt_tolerance=DECLARED_DEFAULT)
    )

    with pytest.raises(ProductClassRegistrationError, match="D-IMPL-258"):
        build_governed_resolver(**_arguments(declaring))


def test_boot_composes_a_resolver_when_the_class_declares_nothing(
    booted: _Booted,
) -> None:
    """The control for the boot leg: the untouched fixture still builds."""
    assert build_governed_resolver(**_arguments(booted)) is not None


def test_the_boot_check_runs_before_the_scorer_shape_refusals(
    booted: _Booted,
) -> None:
    """A malformed declaration is reported ahead of a mis-wired scorer.

    Two defects in one call, and the one the deployment must fix first is the
    one that makes every answer wrong. Asserted because the ordering is a
    choice — the scorer refusals were there first — and a later edit could
    reorder it without any other test noticing.
    """
    declaring = _declaring(
        booted, ServeObligations(default_debt_tolerance=DECLARED_DEFAULT)
    )
    arguments = _arguments(declaring)
    arguments.pop("half_life_key")

    with pytest.raises(ProductClassRegistrationError, match="D-IMPL-258"):
        build_governed_resolver(**arguments)
