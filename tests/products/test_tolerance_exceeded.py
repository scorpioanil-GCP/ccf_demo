"""Three authorities, one shell — the tolerance step through the booted resolver (``24.6-L-04``, ``24.6-L-05``).

``D-IMPL-251`` C1=A and C2=B, recorded as ``D-IMPL-240`` amendment 2, and
``D-IMPL-253`` Q9/Q10. The unit-level behavior of
:func:`~ccf.products.gates.refuse_over_tolerance` is proven in
``tests/products/test_structural_gates.py`` against parameters this test suite
builds by hand. **This module proves the other half**: that the Authority layer
actually resolves the three authorities the way the ruling says, end to end,
through a real ``load_and_boot`` deployment and the shipped
:class:`~ccf.products.resolver.GovernedResolver` — so a resolution that folded
them wrongly, or dropped a provenance, or reached the gate instead of the
delivery step, is red here even though every unit test stayed green.

What each test pins:

* **``default``** — the caller omits the tolerance, the product class's
  ``default_debt_tolerance`` fills the omission, and the shell names the
  product-class artifact as the source. This is the ONLY way a class figure can
  withhold anything after C1=A.
* **``caller``** — a value the caller states is enforced **as requested**, in
  both directions. The looser half is the inversion of the shipped
  ``24.5-L-14`` behavior and would have been red before this plan; the tighter
  half proves the caller's number is live rather than ignored.
* **``policy``** — a registered ``ccf.policy-constraint`` bounding the same
  parameter produces the SAME kind with ``authority == "policy"`` and the
  constraint's ``(key, version)`` as the source. Three authorities, one shell:
  what changes is who set the number, not what happened.
* **the shell's voice** — ``fulfillment was withheld``, ``applicable declared
  tolerance``, and the word ``invalid`` absent, asserted by grep on the
  envelope that actually crossed the seam.
* **the disclosable breakdown** — the withheld shell's ``breakdown`` is the
  very :class:`~ccf.halflife.assessment.DebtAssessment` the served twin
  carries, so *"including the debt information that can safely be disclosed"*
  is a measured identity rather than a claim.
* **the two controls that keep the rest from being vacuous** — a class
  declaring no default serves at any Debt, and the request contract's own
  ``defaults`` win over the class characteristic for the same name.
* **the wiring refusal** — a class default naming a parameter its request
  contract does not declare is refused, because a characteristic a caller
  cannot state is a ceiling wearing a default's name.

The deployment, the manifest and the product class are
``tests/products/test_resolver_seam.py``'s, imported rather than restated for
that module's own reason: a second copy of a fixture deployment is a second
thing to keep in step. Every number, key and role below is this module's own
(CINV-01 reaches ``tests/``); none of them lives in ``src/``.

**How the observed Debt is set.** The deployment's debt scorer is a
constructor argument of the resolver — a value the deployment owns, exactly as
its projection and its plan factory are — so this module supplies its own
rather than reaching inside the assembled view to force a factor. That keeps
the subject the *resolution and the delivery decision*; what a deployment
measures Debt over is its own policy and is proven elsewhere. The control
below asserts the two fixtures really do produce the two different ``D_c``
values the tests compare against, so "above" and "below" are measured rather
than assumed.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    POLICY_CONSTRAINT,
    ConstraintApplicability,
    PolicyConstraint,
)
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.constraints import (
    ReferencePolicyConstraintResolver,
    resolve_effective_request,
)
from ccf.products.entitlement import product_entitlement_key
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER, ToleranceExceededRefusal
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope
from ccf.products.provenance import ProvenanceSource
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.projection.plan import Perspective
from ccf.replay.serve import ServedProduct
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

from tests.deployment.conftest import ARTIFACT_SET, PRODUCT_CLASS_KEY, TENANT
from tests.products.test_resolver_seam import (
    ASKED_AT,
    _internal,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    REQUEST_CONTRACT_DOCUMENT,
    THRESHOLD_PARAMETER,
    _Booted,
    _ask,
    _boot,
    _request,
    _resolver,
)
from tests.composition import register_typed_at_composition

# --- this module's own vocabulary -------------------------------------------

#: The observed Context Debt every deployment below measures, and the four
#: tolerances held against it. Fixture proportions: the class's default is
#: BELOW the observation (so it withholds), the caller's loose value is ABOVE
#: it (so it delivers), the caller's tight value is below it, and the policy
#: maximum is below everything (so it wins on comparability and still
#: withholds). The four are deliberately distinct, so a shell reporting the
#: wrong one is visible rather than coincidentally right.
OBSERVED_DEBT = Decimal("0.20")
CLASS_DEFAULT = Decimal("0.10")
CALLER_LOOSE = Decimal("0.30")
CALLER_TIGHT = Decimal("0.05")
POLICY_MAXIMUM = Decimal("0.01")
#: The request contract's own default, authored as an INTEGER proportion. A
#: YAML float is not canonically encodable and
#: :class:`~ccf.products.provenance.EffectiveParameter` refuses one outright,
#: so a document that must round-trip through YAML states a whole proportion or
#: nothing — which also exercises the tolerance step's integer reading.
CONTRACT_DEFAULT = 1

#: A second observation, for the undeclared-class control: nothing bounds it,
#: so it is delivered however large it is.
ANY_DEBT = Decimal("0.99")

#: The Control Plane key the policy constraint is registered under, and the
#: policy id the artifact carries. Two different strings on purpose.
POLICY_KEY = "tenant-fixture/policy_constraints/tolerance"
POLICY_ID = "tolerance-policy"

PERSPECTIVE = Perspective(principal_id="principal-fixture", role="role-fixture")


def _scorer(debt: Decimal) -> Any:
    """A deployment-owned debt scorer measuring exactly ``debt``."""

    def score(
        *, view: GraphView, evidence: ExecutionEvidence | None = None
    ) -> DebtAssessment:
        # `evidence` accepted and unread (24.6-05): this module's subject is
        # the RESOLUTION of a tolerance, so the debt is supplied rather than
        # measured — but the seam the resolver calls through now carries the
        # execution's evidence, and a scorer that refused it would fail here
        # for a reason that has nothing to do with tolerance.
        return DebtAssessment(
            debt=debt,
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal("1"),
                completeness=Decimal("1"),
                semantic_consistency=Decimal("1"),
            ),
            scorers=(),
        )

    return score


def _documents(
    *,
    class_default: Decimal | None,
    declare_parameter: bool = True,
    contract_default: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The two authored documents a deployment varies, and nothing else."""
    product_class = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    if class_default is not None:
        product_class["serve_obligations"] = {
            "default_debt_tolerance": str(class_default)
        }
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    if declare_parameter:
        request_contract["declaration"]["arguments"]["properties"][
            DEBT_TOLERANCE_PARAMETER
        ] = {"type": "number", "description": "Fixture tolerance; a proportion."}
    if contract_default is not None:
        request_contract["declaration"]["defaults"] = {
            DEBT_TOLERANCE_PARAMETER: contract_default
        }
    return product_class, request_contract


@pytest.fixture
def booted_with_default(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """A class declaring a DEFAULT tolerance below the observed Debt."""
    product_class, request_contract = _documents(class_default=CLASS_DEFAULT)
    yield from _boot(
        tmp_path, product_class=product_class, request_contract=request_contract
    )


@pytest.fixture
def booted_without_default(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The control: a class declaring nothing, on the same request surface."""
    product_class, request_contract = _documents(class_default=None)
    yield from _boot(
        tmp_path, product_class=product_class, request_contract=request_contract
    )


@pytest.fixture
def booted_with_contract_default(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """Both documents declare a default for the same name; the contract's wins."""
    product_class, request_contract = _documents(
        class_default=CLASS_DEFAULT, contract_default=CONTRACT_DEFAULT
    )
    yield from _boot(
        tmp_path, product_class=product_class, request_contract=request_contract
    )


def _governed(booted: _Booted, *, debt: Decimal = OBSERVED_DEBT) -> Any:
    """The seam's own wiring, with this module's scorer and the reference resolver."""
    return _resolver(
        booted,
        debt_scorer=_scorer(debt),
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=booted.control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
    )


def _question(**parameters: Any) -> ProductRequest:
    return _request(parameters={THRESHOLD_PARAMETER: 1000, **parameters})


def _assert_withheld(outcome: Any, *, authority: str) -> RefusalEnvelope:
    """The envelope predicate: `tolerance-exceeded`, and by whose authority."""
    assert isinstance(outcome, RefusalEnvelope), (
        f"expected fulfillment to be withheld; got {type(outcome).__name__}"
    )
    assert outcome.kind == REFUSAL_KINDS[ToleranceExceededRefusal]
    assert outcome.kind == "tolerance-exceeded"
    assert outcome.fields["authority"] == f'"{authority}"', outcome.fields
    return outcome


def _register_maximum(booted: _Booted, value: Decimal) -> str:
    """One ``maximum`` on the tolerance, applicable to everything, from ``T0``."""
    return register_typed_at_composition(booted.control_plane, POLICY_KEY,
        PolicyConstraint(
            semver="1.0.0",
            policy_id=POLICY_ID,
            applies_to=ConstraintApplicability(),
            parameter=DEBT_TOLERANCE_PARAMETER,
            operator="maximum",
            value=value,
            overridable=False,
            source_authority="fixture-authority",
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            effective_until=None,
            reason="a fixture reason",
        ),
        POLICY_CONSTRAINT,
    )


# --- the control that keeps every comparison below non-vacuous --------------


def test_the_fixture_deployments_measure_the_debt_the_tests_compare_against(
    booted_with_default: _Booted,
) -> None:
    """The scorer takes: a delivered product carries exactly ``OBSERVED_DEBT``.

    Without this, every "above" and "below" in this module would be an
    assumption about a fixture rather than a measurement of one, and a scorer
    that silently returned zero would make the delivered cases pass for the
    wrong reason.
    """
    outcome = _ask(
        _governed(booted_with_default),
        _question(**{DEBT_TOLERANCE_PARAMETER: CALLER_LOOSE}),
    )

    assert isinstance(outcome, ServedProduct), outcome
    assert outcome.product.debt is not None
    assert outcome.product.debt.debt == OBSERVED_DEBT
    # And the four tolerances really do straddle it in the order the tests use.
    assert POLICY_MAXIMUM < CALLER_TIGHT < CLASS_DEFAULT < OBSERVED_DEBT
    assert OBSERVED_DEBT < CALLER_LOOSE < Decimal(CONTRACT_DEFAULT)


# --- authority `default`: the class fills an omission, and only that ---------


def test_an_omitted_tolerance_takes_the_class_default_and_withholds_by_name(
    booted_with_default: _Booted,
) -> None:
    """Case (a): the caller says nothing, the class's default applies, the shell names the class.

    ``D-IMPL-251`` C1=A leaves the class figure exactly one power: to say what
    OMISSION means. Here the omission is real, so the figure applies — with
    authority ``default`` and the product-class artifact as the source an
    examiner resolves it from.
    """
    outcome = _ask(_governed(booted_with_default), _question())

    envelope = _assert_withheld(outcome, authority="default")
    # The authority and the tolerance are what a caller must act on, so both
    # survive the safe default (`ccf.products.disclosure.PERMITTED_AT_MINIMAL`;
    # `D-IMPL-253` Q10 by name). The source pin and the observed D_c are the
    # fabric's own measurement and are read from the record (`24.6-08`).
    assert Decimal(envelope.fields["tolerance"].strip('"')) == CLASS_DEFAULT

    internal = _internal(booted_with_default, envelope)
    source = ProvenanceSource.model_validate_json(internal.fields["source"])
    assert source.kind == "artifact"
    assert source.identity == PRODUCT_CLASS_KEY
    assert source.version is not None, "an artifact source names its version"
    assert Decimal(internal.fields["tolerance"].strip('"')) == CLASS_DEFAULT
    assert Decimal(internal.fields["observed"].strip('"')) == OBSERVED_DEBT


def test_the_shell_says_fulfillment_was_withheld_and_never_that_debt_is_invalid(
    booted_with_default: _Booted,
) -> None:
    """Case (d): ``D-IMPL-253`` Q10's semantic caution, on the envelope that crossed the seam.

    Dave: *"I would not make the shell itself imply that Debt is invalid; the
    product was constructible, but fulfillment was withheld because an
    applicable declared tolerance was exceeded."* Asserted on the whole
    envelope rather than on the type's ``detail`` alone, because the door and
    the promotion machinery are between the two and either could add prose.

    The lineage assertion is the other half of the same sentence: the shell
    carries the candidate's own lineage, because a candidate existed. A shell
    for a product that was never constructed would have none, and the
    pre-assembly split is what keeps those two claims distinguishable.
    """
    outcome = _ask(_governed(booted_with_default), _question())

    envelope = _assert_withheld(outcome, authority="default")
    # Dave's own sentence, and it is the sentence at BOTH ends: the fabric's
    # internal prose says it, and `EXTERNAL_STATEMENTS["tolerance-exceeded"]`
    # is the same claim in the same words, so the safe default does not turn a
    # withheld fulfillment into an unexplained one.
    internal = _internal(booted_with_default, envelope)
    for detail in (envelope.detail, internal.detail):
        assert "fulfillment was withheld" in detail
        assert "applicable declared tolerance" in detail
        assert "invalid" not in detail
    assert "invalid" not in str(envelope.fields)
    assert "invalid" not in str(internal.fields)
    # The product was constructible: it has a lineage, and it is the
    # candidate's own. Internal, because a lineage is evidence of the search
    # and does not cross at `minimal`.
    assert internal.pre_assembly_lineage is not None
    assert internal.pre_assembly_lineage.operators_invoked


def test_the_withheld_breakdown_is_the_served_twins_own_assessment(
    booted_with_default: _Booted,
) -> None:
    """Case (e): *"including the debt information that can safely be disclosed"*, measured.

    The same deployment answers twice — once with the caller silent (withheld
    under the class default) and once with the caller stating a value above the
    observation (delivered). The ``breakdown`` on the first is byte-identical to
    the ``debt`` on the second, so the shell discloses the assessment the
    consumer would have received rather than a summary of it.
    """
    withheld = _ask(_governed(booted_with_default), _question())
    delivered = _ask(
        _governed(booted_with_default),
        _question(**{DEBT_TOLERANCE_PARAMETER: CALLER_LOOSE}),
    )

    envelope = _assert_withheld(withheld, authority="default")
    assert isinstance(delivered, ServedProduct), delivered
    assert delivered.product.debt is not None

    internal = _internal(booted_with_default, envelope)
    breakdown = DebtAssessment.model_validate_json(internal.fields["breakdown"])
    assert breakdown == delivered.product.debt
    assert breakdown.factors == delivered.product.debt.factors
    # And the breakdown does NOT cross at the safe default: a per-factor
    # measurement of the fabric's own state is not something a refused caller
    # is owed (`ccf.products.disclosure.PERMITTED_AT_MINIMAL`).
    assert envelope.fields["breakdown"] != internal.fields["breakdown"]


# --- authority `caller`: enforced as requested, in both directions -----------


def test_a_caller_tolerance_above_the_observation_is_delivered(
    booted_with_default: _Booted,
) -> None:
    """Case (b), the LOOSER half — the inversion ``D-IMPL-251`` C2=B bought.

    The caller asks for 0.30 against a class default of 0.10 and an observed
    0.20, and is served. Before ``24.6-04`` the class's number was the floor of
    strictness and this was a ``409``. Dave: *"the class shouldn't override me
    merely because its author thought .20 was generally preferable."*
    """
    outcome = _ask(
        _governed(booted_with_default),
        _question(**{DEBT_TOLERANCE_PARAMETER: CALLER_LOOSE}),
    )

    assert isinstance(outcome, ServedProduct), outcome
    assert outcome.product.debt is not None
    assert outcome.product.debt.debt == OBSERVED_DEBT > CLASS_DEFAULT


def test_a_caller_tolerance_below_the_observation_withholds_naming_the_caller(
    booted_with_default: _Booted,
) -> None:
    """Case (b), the TIGHTER half: the caller's own fitness decision, honored.

    The source is the caller's own question and carries **no version** — a
    request is not a versioned document, and
    :class:`~ccf.products.provenance.ProvenanceSource` refuses one that claims
    to be. That is what distinguishes this shell from the class's at audit,
    beyond the authority token.
    """
    outcome = _ask(
        _governed(booted_with_default),
        _question(**{DEBT_TOLERANCE_PARAMETER: CALLER_TIGHT}),
    )

    envelope = _assert_withheld(outcome, authority="caller")
    internal = _internal(booted_with_default, envelope)
    source = ProvenanceSource.model_validate_json(internal.fields["source"])
    assert source.kind == "request"
    assert source.version is None
    assert Decimal(envelope.fields["tolerance"].strip('"')) == CALLER_TIGHT
    # The class's own number is NOT what withheld it, though it would also
    # have: the shell reports the authority that actually set the value.
    assert CALLER_TIGHT != CLASS_DEFAULT


# --- authority `policy`: the same kind, a different authority ----------------


def test_a_policy_maximum_withholds_under_the_same_kind_naming_the_constraint(
    booted_with_default: _Booted,
) -> None:
    """Case (c): governance bounds the caller, and the shell is the SAME shell.

    The caller asks for 0.30; a registered ``ccf.policy-constraint`` maximum of
    0.01 replaces it with authority ``policy`` (worked case 3, the one place
    anything is clamped); the observed 0.20 then exceeds it. A second kind for
    governance would make a consumer branch on the wrong axis — what changed is
    who set the number.
    """
    version = _register_maximum(booted_with_default, POLICY_MAXIMUM)

    outcome = _ask(
        _governed(booted_with_default),
        _question(**{DEBT_TOLERANCE_PARAMETER: CALLER_LOOSE}),
    )

    envelope = _assert_withheld(outcome, authority="policy")
    internal = _internal(booted_with_default, envelope)
    source = ProvenanceSource.model_validate_json(internal.fields["source"])
    assert source.kind == "artifact"
    assert source.identity == POLICY_KEY
    assert source.version == version
    assert Decimal(envelope.fields["tolerance"].strip('"')) == POLICY_MAXIMUM
    # One kind across all three authorities.
    assert envelope.kind == "tolerance-exceeded"


def test_a_policy_maximum_above_the_observation_still_delivers(
    booted_with_default: _Booted,
) -> None:
    """The control for the test above: a live constraint that does not bind delivers.

    Without it, the policy case would pass on a resolver that refused whenever
    any constraint was registered at all.
    """
    _register_maximum(booted_with_default, CALLER_LOOSE)

    outcome = _ask(
        _governed(booted_with_default),
        _question(**{DEBT_TOLERANCE_PARAMETER: CALLER_LOOSE}),
    )

    assert isinstance(outcome, ServedProduct), outcome


# --- the two controls -------------------------------------------------------


def test_a_class_declaring_no_default_delivers_at_any_debt(
    booted_without_default: _Booted,
) -> None:
    """Case (f): no authority stated a tolerance, so none applies — at ``D_c`` 0.99.

    ``None`` is not a permissive default: it is the absence of any declaration
    to enforce. This is also the control that keeps every withheld case above
    from passing on a resolver that withheld unconditionally.
    """
    outcome = _ask(_governed(booted_without_default, debt=ANY_DEBT), _question())

    assert isinstance(outcome, ServedProduct), outcome
    assert outcome.product.debt is not None
    assert outcome.product.debt.debt == ANY_DEBT


def test_the_request_contracts_own_default_wins_over_the_class_characteristic(
    booted_with_contract_default: _Booted,
) -> None:
    """Case (g): two documents declare a default for one name, and the contract's stands.

    A request contract says what omission means **for that parameter of that
    surface**; a class characteristic says it for the class. The more specific
    declaration wins, and the delivered answer proves which one was applied —
    the contract's 0.40 is above the observation and the class's 0.10 is below
    it, so the two readings give opposite outcomes rather than the same one.
    """
    outcome = _ask(_governed(booted_with_contract_default), _question())

    assert isinstance(outcome, ServedProduct), outcome
    assert CLASS_DEFAULT < OBSERVED_DEBT < Decimal(CONTRACT_DEFAULT), (
        "the two defaults must straddle the observation, or this test cannot"
        " tell which one was applied"
    )


# --- the wiring refusal -----------------------------------------------------


def test_a_class_default_the_contract_does_not_declare_is_refused() -> None:
    """The surviving invariant guard: this pure function still refuses the pair.

    A characteristic a caller cannot state is a ceiling wearing a default's
    name. ``D-IMPL-251`` C1=A took from a product class the power to withhold
    context over its own preference, and a default on a parameter the request
    contract does not declare as an argument would hand it straight back: the
    caller has no way to accept a product the default withholds. It is also
    unanswerable — the resolution's closed-world comparison runs over the
    EFFECTIVE values, so folding the name in would refuse the request as
    ``undeclared-parameter`` and report a deployment's mistake as a caller's.

    Raised rather than returned, on the ``capability_bindings`` precedent: the
    fabric cannot reach a valid governed determination
    (``D-IMPL-253`` amendment 2 (3)).

    **Unreachable through the SDK's own wiring since ``D-IMPL-258`` (5)**, and
    kept anyway. Dave moved the refusal to declaration time — registration and
    boot, proved in ``tests/products/test_class_default_declaration.py`` — so a
    class that contradicts its own contract never becomes servable and this
    branch never sees one through the shipped seams. It stays because
    :func:`~ccf.products.constraints.resolve_effective_request` is a **public
    pure function over its arguments**: it cannot assume its caller booted
    through either seam, and silently folding in a default its own argument
    says is undeclared would be the silent repair this codebase refuses
    everywhere. This test is what keeps the last line a line.
    """
    contract = ProductRequestContract(
        semver="1.0.0",
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        arguments=SkillArgumentSchema(
            properties={
                THRESHOLD_PARAMETER: SkillArgumentProperty(
                    type="number", description="a fixture threshold"
                )
            },
            required=(),
        ),
    )
    pin = ProvenanceSource(
        kind="artifact", identity="tenant-fixture/product-class", version="1"
    )
    request = ProductRequest(
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        subject="acct-1",
        intent="fixture-intent",
        freshness="fixture-freshness",
        asked_at=ASKED_AT,
        parameters={THRESHOLD_PARAMETER: 1000},
    )

    with pytest.raises(ValueError, match="C1=A"):
        resolve_effective_request(
            request=request,
            declared=contract,
            declared_source=pin,
            constraints=(),
            capabilities=(),
            capability_bindings={},
            verified_overrides=(),
            perspective=PERSPECTIVE,
            tenant=TENANT,
            class_defaults={DEBT_TOLERANCE_PARAMETER: CLASS_DEFAULT},
            class_source=pin,
        )

    # And the control: the same call with the parameter DECLARED resolves.
    declaring = contract.model_copy(
        update={
            "arguments": SkillArgumentSchema(
                properties={
                    THRESHOLD_PARAMETER: SkillArgumentProperty(
                        type="number", description="a fixture threshold"
                    ),
                    DEBT_TOLERANCE_PARAMETER: SkillArgumentProperty(
                        type="number", description="a fixture tolerance"
                    ),
                },
                required=(),
            )
        }
    )
    resolved = resolve_effective_request(
        request=request,
        declared=declaring,
        declared_source=pin,
        constraints=(),
        capabilities=(),
        capability_bindings={},
        verified_overrides=(),
        perspective=PERSPECTIVE,
        tenant=TENANT,
        class_defaults={DEBT_TOLERANCE_PARAMETER: CLASS_DEFAULT},
        class_source=pin,
    )
    assert resolved.refusal is None, resolved.refusal
    tolerance = resolved.evidence.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None
    assert tolerance.authority == "default"
    assert tolerance.source == pin


def test_a_class_default_with_no_pin_is_refused() -> None:
    """A default the fabric applies must name the artifact that declared it.

    ``D-IMPL-253`` Q1 (*"do not collapse authority after resolution"*) and
    amendment 2 (1) (*"do not create fake artifacts"*) meet here: the fix for a
    default with no provenance is to supply the pin, never to mint one.
    """
    contract = ProductRequestContract(
        semver="1.0.0",
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        arguments=SkillArgumentSchema(
            properties={
                DEBT_TOLERANCE_PARAMETER: SkillArgumentProperty(
                    type="number", description="a fixture tolerance"
                )
            },
            required=(),
        ),
    )
    request = ProductRequest(
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        subject="acct-1",
        intent="fixture-intent",
        freshness="fixture-freshness",
        asked_at=ASKED_AT,
        parameters={},
    )

    with pytest.raises(ValueError, match="class_source"):
        resolve_effective_request(
            request=request,
            declared=contract,
            declared_source=ProvenanceSource(
                kind="artifact", identity="tenant-fixture/request-contract", version="1"
            ),
            constraints=(),
            capabilities=(),
            capability_bindings={},
            verified_overrides=(),
            perspective=PERSPECTIVE,
            tenant=TENANT,
            class_defaults={DEBT_TOLERANCE_PARAMETER: CLASS_DEFAULT},
            class_source=None,
        )
