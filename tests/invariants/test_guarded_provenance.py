"""`D-IMPL-337` — guarded-path provenance at every governed boundary.

The ruled rule, and it is about PROVENANCE rather than nominal type identity:

    A consumer that relies on authority established by a guarded construction
    path must positively verify evidence that the supplied value actually
    passed through that guarded path. Nominal type identity, structural
    compatibility, annotations, Protocol conformance, pattern matching, or
    duck typing alone are insufficient.

**Why `isinstance` is not the check, measured rather than argued.** Before
this work, `isinstance(x, ServableProduct)` returned `True` for a subclass
that skipped `super().__init__` and for `object.__new__(ServableProduct)`, and
the subclass reached a real `ServedProduct` with the three validation gates
never having run. The reference pattern is the tree's own
`ccf.controlplane.state`, whose `_verify` checks the mint and whose test is
already named *"isinstance is not the gate — the mint is verified at the
write."*

**Every governed boundary gets four controls**, per the ruling:
honest value succeeds; structural impostor rejected; subclass that skips
guarded construction rejected; `object.__new__` rejected. Where one is
impossible or meaningless for a type, the reason is recorded rather than a
fake test invented.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ccf.contracts.guarded import GUARDED_TYPES, declaration_for
from ccf.peering.admission import (
    AdmissionBypassError,
    AdmittedProduct,
    verify_admission_provenance,
)
from ccf.products.gates import (
    GateBypassError,
    ServableProduct,
    verify_gate_provenance,
)


# --- the impostor family, built once and used at every boundary -------------


def _structural_impostor(**attrs: object) -> object:
    """An object shaped exactly like the guarded type, minted by nobody."""
    return type("StructuralImpostor", (), attrs)()


def _subclass_skipping_construction(base: type, **attrs: object) -> object:
    """A SUBCLASS that never runs the guarded ``__init__``.

    The specimen that defeats `isinstance`: it is a genuine member of the
    nominal type and inherits its whole attribute surface, and no guarded path
    ever ran.
    """
    namespace: dict[str, object] = {"__init__": lambda self: None, **attrs}
    return type("SubclassSkippingGuard", (base,), namespace)()


def _tolerance_kwargs() -> dict[str, object]:
    """Whatever `refuse_over_tolerance` needs beyond the product.

    Read from the signature rather than restated, so a later parameter change
    moves this helper instead of silently making the test pass on a TypeError
    raised before the provenance check.
    """
    import inspect

    from ccf.products.gates import refuse_over_tolerance

    params = inspect.signature(refuse_over_tolerance).parameters
    return {
        name: None
        for name, p in params.items()
        if p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
    }


def _constructor_bypass(base: type) -> object:
    """``object.__new__`` — the type without any ``__init__`` at all."""
    return object.__new__(base)


# --- ServableProduct: gate provenance ---------------------------------------


class TestGateProvenance:
    """`ServableProduct` — the type at the centre of the measured exploit."""

    def test_the_subclass_that_defeats_isinstance_is_refused(self) -> None:
        """The specimen the ruling exists for.

        Asserted alongside `isinstance` returning True, so the test states the
        exact gap it closes rather than merely passing.
        """
        forged = _subclass_skipping_construction(ServableProduct, product="x")
        assert isinstance(forged, ServableProduct), (
            "the premise has moved: this specimen is supposed to satisfy the"
            " nominal check that D-IMPL-337 rules insufficient"
        )
        with pytest.raises(GateBypassError):
            verify_gate_provenance(forged)

    def test_the_constructor_bypass_is_refused(self) -> None:
        with pytest.raises(GateBypassError):
            verify_gate_provenance(_constructor_bypass(ServableProduct))

    def test_the_structural_impostor_is_refused(self) -> None:
        with pytest.raises(GateBypassError):
            verify_gate_provenance(_structural_impostor(product="x"))

    def test_the_honest_gated_product_succeeds(self, gated: ServableProduct) -> None:
        """The positive control. Without it every refusal above could be a
        verifier that refuses everything."""
        assert verify_gate_provenance(gated) is gated

    def test_serve_refuses_a_forgery_before_recording_anything(
        self, gated: ServableProduct
    ) -> None:
        """The boundary, not the verifier — and the ORDER matters.

        `serve` establishes provenance before it appends the record: a record
        written for a value with no gate provenance would be an audit trail
        for a decision the fabric never made.
        """
        from ccf.replay.serve import serve

        forged = _subclass_skipping_construction(ServableProduct, product="x")
        with pytest.raises(GateBypassError):
            serve(
                product=forged,  # type: ignore[arg-type]
                record=None,  # type: ignore[arg-type]
                replay_writer=None,  # type: ignore[arg-type]
            )

    def test_deliver_refuses_a_forgery_at_its_own_boundary(self) -> None:
        """`DeliveryCapability.deliver` is SEPARATELY reachable from `serve`,
        so it establishes provenance itself. This is the entry the measured
        exploit used."""
        from ccf.artifacts.protocol import ArtifactRef
        from ccf.replay.serve import DeliveryCapability

        forged = _subclass_skipping_construction(ServableProduct, product="x")
        ref = ArtifactRef(
            uri="ccf-artifact://t/c/n@1.0.0",
            content_address="a" * 64,
            artifact_class="c",
            name="n",
            tenant_id="t",
        )
        capability = type(
            "C", (), {"_replay_ref": ref, "deliver": DeliveryCapability.deliver}
        )()
        with pytest.raises(GateBypassError):
            capability.deliver(forged)

    def test_refuse_over_tolerance_refuses_a_forgery(self) -> None:
        from ccf.products.gates import refuse_over_tolerance

        forged = _subclass_skipping_construction(ServableProduct, product="x")
        with pytest.raises(GateBypassError):
            refuse_over_tolerance(
                forged,  # type: ignore[arg-type]
                **_tolerance_kwargs(),
            )


# --- AdmittedProduct: admission provenance ----------------------------------


class TestAdmissionProvenance:
    """`AdmittedProduct` — a bypass here reaches L3 past the single writer."""

    def test_the_subclass_that_defeats_isinstance_is_refused(self) -> None:
        forged = _subclass_skipping_construction(AdmittedProduct)
        assert isinstance(forged, AdmittedProduct)
        with pytest.raises(AdmissionBypassError):
            verify_admission_provenance(forged)

    def test_the_constructor_bypass_is_refused(self) -> None:
        with pytest.raises(AdmissionBypassError):
            verify_admission_provenance(_constructor_bypass(AdmittedProduct))

    def test_the_structural_impostor_is_refused(self) -> None:
        with pytest.raises(AdmissionBypassError):
            verify_admission_provenance(_structural_impostor(product=object()))

    def test_mount_product_source_refuses_a_forgery(self) -> None:
        from ccf.graph.product_source import mount_product_source

        forged = _subclass_skipping_construction(AdmittedProduct)
        with pytest.raises(AdmissionBypassError):
            mount_product_source(admitted=forged)  # type: ignore[arg-type]

    def test_the_exported_constructor_refuses_a_forgery_on_its_own(self) -> None:
        """`ProductSource.__init__` is a boundary in its own right.

        The class is in `__all__` and the constructor is private BY CONVENTION
        only — so an externally supplied value reaches it without passing
        `mount_product_source`. The census filed it as module-private on the
        strength of the leading underscore in `__init__`; that false negative
        is why the registry, not the scan, is the source of truth.
        """
        from ccf.graph.product_source import ProductSource

        forged = _subclass_skipping_construction(AdmittedProduct)
        with pytest.raises(AdmissionBypassError):
            ProductSource(
                admitted=forged,  # type: ignore[arg-type]
                entities=(),
                relationships=(),
            )

    def test_ingest_admitted_refuses_a_forgery(self) -> None:
        from ccf.assembly.worker import AssemblyWorker

        forged = _subclass_skipping_construction(AdmittedProduct)
        with pytest.raises(AdmissionBypassError):
            AssemblyWorker.ingest_admitted(
                object(),  # type: ignore[arg-type]
                forged,  # type: ignore[arg-type]
                spec=None,  # type: ignore[arg-type]
                ingested_at=datetime.now(UTC),
            )


# --- the registry itself -----------------------------------------------------


class TestTheDeclaredRegistry:
    """The registry is the source of truth, so its own shape is pinned."""

    def test_every_declaration_states_what_drift_enforcement_needs(self) -> None:
        for declaration in GUARDED_TYPES:
            assert ":" in declaration.type_path, declaration.type_path
            assert declaration.authority.strip(), declaration.type_path
            assert declaration.mint.strip(), declaration.type_path
            assert declaration.propagation.strip(), declaration.type_path

    def test_a_declared_verifier_actually_refuses_a_nominal_forgery(self) -> None:
        """A declaration naming a verifier that does not refuse would be
        drift the lint cannot see — the registry says what is true, and this
        is what makes that a checkable claim rather than prose."""
        checks = {
            "ccf.products.gates:ServableProduct": (
                verify_gate_provenance,
                ServableProduct,
                GateBypassError,
            ),
            "ccf.peering.admission:AdmittedProduct": (
                verify_admission_provenance,
                AdmittedProduct,
                AdmissionBypassError,
            ),
        }
        for path, (verifier, base, error) in checks.items():
            assert declaration_for(path) is not None, path
            with pytest.raises(error):
                verifier(_subclass_skipping_construction(base))

    def test_the_types_with_no_verifier_declare_why(self) -> None:
        """`D-IMPL-337` conclusion: record the gap rather than hide it.

        Three declared types carry no verifier in this phase. Each states a
        residual or a propagation model explaining why no externally
        substitutable boundary consumes it — which is a declaration, not an
        omission a later reader must infer.
        """
        for declaration in GUARDED_TYPES:
            if declaration.verifier is not None:
                continue
            explained = declaration.residual or not declaration.boundaries
            assert explained, (
                f"{declaration.type_path} has no verifier, names boundaries,"
                " and states no residual — that is an undeclared gap"
            )


@pytest.fixture()
def gated() -> ServableProduct:
    """A genuinely gated product, through the real `run_gates`."""
    from tests.products.test_composite import (
        FAMILY,
        _contract,
        _registered,
        deliver,
        served,
    )
    from ccf.controlplane.registry import ControlPlaneRegistry

    registry = ControlPlaneRegistry()
    outcome = deliver(registry, _contract(schema=FAMILY))
    assert isinstance(outcome, ServableProduct), outcome
    return outcome
