"""`R1` — an honest signed envelope carrying a child-eligibility assertion.

`D-IMPL-336` **R1**, raised by the second review panel and kept **blocking**
by Dave through Amendment 5: *"Fix the reported header-cap failure in peering
using the already-authorized bounded configuration. Prove an honest signed
envelope reaches… composition; retain oversized-envelope and
signature-tampering controls. **Moving the code does not close the finding.**"*

**The defect, measured.** ``joserfc``'s :class:`~joserfc.jws.JWSRegistry`
defaults ``max_header_length`` to **512 bytes** and
``ccf.peering.identity._registry_declaring`` never set it. An encoded
eligibility assertion is **448 bytes** and a complete protected header
carrying one is **621**. So the peered composite path was not merely untested
— it was **unreachable**: every honest envelope raised inside the library
before a single CCF check ran. Zero tests exercised it, which is why nothing
caught it.

This module is the proof it is reachable, and the two controls that keep the
bound a bound rather than a removal.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ccf.peering.admission import PRODUCER_ASSERTION_HEADER, AdmittedProduct
from ccf.peering.eligibility import (
    ELIGIBILITY_ASSERTION_HEADER,
    ELIGIBILITY_EVIDENCE_POLICY,
    EligibilityEvidencePolicy,
    eligibility_evidence_policy_key,
    encode_eligibility_assertion,
    mint_eligibility_assertion,
)
from ccf.peering.identity import (
    MAX_PROTECTED_HEADER_BYTES,
    DetachedJwsIdentityProvider,
    SignedContextProduct,
)
from ccf.peering.protocol import InboundProduct, PeerRef
from ccf.products.composite import (
    AdmittedChild,
    ChildAdmissionRefusal,
    ChildCandidate,
    CompositeAdmissionGate,
    ELIGIBILITY_PRODUCER_ATTESTED,
    invocation_from_dispatch,
    resolve_producing_grant,
)
from ccf.skills.dispatch import PeeringInvocation

from tests.peering.test_admission_attributability import (  # noqa: F401
    PEER,
    PEER_KID,
    PEER_PRODUCER,
    TENANT,
    artifact_store,
    banking_product,
    consumer_lineage,
    gate,
    key_dir,
    product_class,
    provider,
    _now,
    public_key,
    registry,
)

CONSUMER_SCOPE = "consumer://peered-composite"

#: The fixture peered product, WITH a debt assessment — the composite gate
#: refuses an unassessable child (*"unknown debt is not zero"*), which the
#: peering fixtures never needed to carry.
def peered_child() -> object:
    from decimal import Decimal

    from ccf.halflife.assessment import DebtAssessment, DebtFactors
    from ccf.halflife.debt import DebtSignal

    return banking_product().model_copy(
        update={
            "debt": DebtAssessment(
                debt=Decimal(0),
                signal=DebtSignal.OK,
                factors=DebtFactors(
                    freshness=Decimal(1),
                    completeness=Decimal(1),
                    semantic_consistency=Decimal(1),
                ),
                scorers=(),
            )
        }
    )

INVOCATION = "composition://peered-inv-0001"


def _assertion_header(
    product: object, *, checked_at: datetime, invocation: str = INVOCATION
) -> dict[str, str]:
    """The producer's own assertions, as the emitter attaches them."""
    from ccf.contracts.canonical import content_hash

    assertion = mint_eligibility_assertion(
        child_content_address=content_hash(product),
        requested_as_of=product.temporal_boundary,  # type: ignore[attr-defined]
        producer=PEER_PRODUCER,
        consumer_scope=CONSUMER_SCOPE,
        checked_at=checked_at,
        composition_invocation=invocation,
        eligible=True,
    )
    return {
        PRODUCER_ASSERTION_HEADER: PEER_PRODUCER,
        ELIGIBILITY_ASSERTION_HEADER: encode_eligibility_assertion(assertion),
    }


def test_r1_the_honest_header_EXCEEDS_the_library_default(
    provider: DetachedJwsIdentityProvider,
) -> None:
    """The measurement the finding rests on, asserted rather than recited.

    If this ever stops being true the bound below is no longer load-bearing
    and someone should be told, rather than the constant quietly outliving its
    reason.
    """
    product = peered_child()
    signed = provider.sign(
        product=product,
        key_id=PEER_KID,
        assertions=_assertion_header(product, checked_at=_now()),
    )
    assert isinstance(signed, SignedContextProduct)
    header_bytes = len(signed.protected.encode())
    assert header_bytes > 512, (
        "the honest header now fits joserfc's default, so R1's premise has"
        f" moved: measured {header_bytes} bytes"
    )
    assert header_bytes <= MAX_PROTECTED_HEADER_BYTES


def test_r1_an_honest_signed_envelope_reaches_COMPOSITION(
    provider: DetachedJwsIdentityProvider,
    gate: object,
    registry: object,
) -> None:
    """The finding's actual close: sign -> admit -> compose, end to end.

    Before the bound was declared this raised inside ``joserfc``. It now runs
    the real :class:`~ccf.peering.admission.PeeringAdmissionGate` — signature,
    peer trust, policy bindings — and the real
    :class:`~ccf.products.composite.CompositeAdmissionGate`, which consumes
    that verdict and verifies the eligibility assertion through
    :func:`~ccf.peering.eligibility.verify_child_eligibility`.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.contract import ChildRequirement

    assert isinstance(registry, ControlPlaneRegistry)
    now = _now()
    product = peered_child()
    signed = provider.sign(
        product=product,
        key_id=PEER_KID,
        assertions=_assertion_header(product, checked_at=now),
    )
    admitted = gate.admit(  # type: ignore[attr-defined]
        inbound=InboundProduct(
            observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER), signed=signed
        ),
        consumer_lineage=consumer_lineage(),
        now=now,
    )
    assert isinstance(admitted, AdmittedProduct), admitted

    # The consumer declares how old a producer's check may be (`F7`).
    registry.register_typed(
        eligibility_evidence_policy_key(tenant_id=TENANT),
        EligibilityEvidencePolicy(
            max_evidence_age_seconds=3600, permitted_clock_skew_seconds=60
        ),
        ELIGIBILITY_EVIDENCE_POLICY,
    )
    requirement = ChildRequirement(
        product_class=admitted.product.schema_name,
        required=True,
        compatible_from=admitted.product.schema_version,
    )
    producer = _granted_producer(registry, requirement)
    outcome = CompositeAdmissionGate(
        tenant_id=TENANT, consumer_scope=CONSUMER_SCOPE, registry=registry
    ).admit(
        candidate=ChildCandidate(
            requirement=requirement,
            contract=admitted.product,
            content_address=admitted.content_address or "",
            invocation=invocation_from_dispatch(
                producer,
                PeeringInvocation(
                    skill_name=producer.entry.name,
                    skill_type="peering",
                    endpoint="fixture-endpoint",
                    products=(),
                    arguments={},
                ),
            ),
            admission=admitted,
        ),
        asked_at=admitted.product.temporal_boundary,
        admitted_at=now,
        composition_invocation=INVOCATION,
    )
    assert isinstance(outcome, AdmittedChild), outcome
    # The PRODUCER's attestation is what authorized it — not this fabric's
    # register, which never saw the child's execution.
    assert outcome.eligibility_basis == ELIGIBILITY_PRODUCER_ATTESTED
    assert outcome.eligibility_evidence is not None
    assert outcome.eligibility_evidence.producer == PEER_PRODUCER


def test_r1_the_declared_bound_is_ENFORCED_not_merely_raised(
    provider: DetachedJwsIdentityProvider, gate: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound is a BOUND, and this is what proves it was not just removed.

    An unbounded header would let a peer force arbitrary allocation before its
    signature is checked, so raising the cap to fit an honest envelope must
    not become having no cap.

    Asserted by moving the DECLARED bound below the honest header and watching
    the same envelope refuse. That is stronger than signing an oversized one:
    it proves the constant is read at verification rather than merely present
    in the module.
    """
    import ccf.peering.identity as identity

    now = _now()
    product = peered_child()
    signed = provider.sign(
        product=product,
        key_id=PEER_KID,
        assertions=_assertion_header(product, checked_at=now),
    )
    honest = len(signed.protected.encode())
    monkeypatch.setattr(identity, "MAX_PROTECTED_HEADER_BYTES", honest - 1)
    outcome = gate.admit(  # type: ignore[attr-defined]
        inbound=InboundProduct(
            observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER), signed=signed
        ),
        consumer_lineage=consumer_lineage(),
        now=now,
    )
    # Refused, not raised. `joserfc`'s `ExceededSizeError` is a `JoseError`, so
    # the identity provider maps it to `SignatureInvalid` and the gate reports
    # a governed refusal. Worth naming: an over-bound header is reported as a
    # signature failure rather than as a size failure, which is the SAFE
    # direction — nothing is admitted — but it does mean an operator debugging
    # an oversized envelope is told the wrong thing. Recorded as a limitation
    # rather than repaired here, because changing that mapping widens what the
    # verify path distinguishes and is not R1's subject.
    assert not isinstance(outcome, AdmittedProduct), (
        "an over-bound protected header was admitted; the declared bound is"
        " not being read at verification"
    )


def test_r1_a_TAMPERED_signature_is_still_refused(
    provider: DetachedJwsIdentityProvider, gate: object
) -> None:
    """The other retained control: the bound changed sizes, not verification.

    The envelope is honest and within the bound; one byte of the signature is
    altered. Admission must refuse — otherwise the wider header would have
    bought reachability at the cost of the thing the envelope is for.
    """
    now = _now()
    product = peered_child()
    signed = provider.sign(
        product=product,
        key_id=PEER_KID,
        assertions=_assertion_header(product, checked_at=now),
    )
    flipped = "A" if signed.signature[0] != "A" else "B"
    tampered = signed.model_copy(update={"signature": flipped + signed.signature[1:]})
    outcome = gate.admit(  # type: ignore[attr-defined]
        inbound=InboundProduct(
            observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER), signed=tampered
        ),
        consumer_lineage=consumer_lineage(),
        now=now,
    )
    assert not isinstance(outcome, AdmittedProduct), (
        "a tampered signature was admitted"
    )


def test_r1_a_stale_producer_check_still_refuses_on_the_real_envelope(
    provider: DetachedJwsIdentityProvider, gate: object, registry: object
) -> None:
    """`F7` on the genuine path rather than on a hand-built header.

    The assertion is really signed, really verified, and really too old.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.products.contract import ChildRequirement

    assert isinstance(registry, ControlPlaneRegistry)
    now = _now()
    product = peered_child()
    signed = provider.sign(
        product=product,
        key_id=PEER_KID,
        assertions=_assertion_header(product, checked_at=now - timedelta(days=365)),
    )
    admitted = gate.admit(  # type: ignore[attr-defined]
        inbound=InboundProduct(
            observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER), signed=signed
        ),
        consumer_lineage=consumer_lineage(),
        now=now,
    )
    assert isinstance(admitted, AdmittedProduct), admitted
    registry.register_typed(
        eligibility_evidence_policy_key(tenant_id=TENANT),
        EligibilityEvidencePolicy(
            max_evidence_age_seconds=3600, permitted_clock_skew_seconds=60
        ),
        ELIGIBILITY_EVIDENCE_POLICY,
    )
    requirement = ChildRequirement(
        product_class=admitted.product.schema_name,
        required=True,
        compatible_from=admitted.product.schema_version,
    )
    producer = _granted_producer(registry, requirement)
    outcome = CompositeAdmissionGate(
        tenant_id=TENANT, consumer_scope=CONSUMER_SCOPE, registry=registry
    ).admit(
        candidate=ChildCandidate(
            requirement=requirement,
            contract=admitted.product,
            content_address=admitted.content_address or "",
            invocation=invocation_from_dispatch(
                producer,
                PeeringInvocation(
                    skill_name=producer.entry.name,
                    skill_type="peering",
                    endpoint="fixture-endpoint",
                    products=(),
                    arguments={},
                ),
            ),
            admission=admitted,
        ),
        asked_at=admitted.product.temporal_boundary,
        admitted_at=now,
        composition_invocation=INVOCATION,
    )
    assert isinstance(outcome, ChildAdmissionRefusal), outcome
    assert outcome.reason == "eligibility-evidence-stale"


def _granted_producer(registry: object, requirement: object) -> object:
    """One in-force grant for a peering-bound skill producing the child class.

    Real ledger, real grant — `O2` holds on this path too: a peered child is
    still acquired through a skill the composing agent was granted.
    """
    from ccf.agents.definitions import AgentDefinition
    from ccf.contracts.canonical import content_hash
    from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
    from ccf.skills.catalog import (
        PeeringBinding,
        SkillArgumentSchema,
        SkillCatalog,
        SkillCatalogEntry,
        SkillRequirements,
    )
    from ccf.skills.grants import GrantLedger, SkillGrant

    regime_key = f"{TENANT}/policy-bundle/peered-composite"
    regime_class = declared_artifact_class("policy-bundle")
    registry.register_typed(  # type: ignore[attr-defined]
        regime_key,
        parse_artifact(
            {
                "class_id": "policy-bundle",
                "semver": "1.0.0",
                "declaration": {
                    "regime": "peered-composite",
                    "skill_governance": {
                        "grant_requires_approval": False,
                        "permitted_scopes": [],
                    },
                },
            },
            regime_class,
        ),
        regime_class,
    )
    definition = AgentDefinition(
        schema_version="1.0.0",
        artifact_version="1.0.0",
        name="peered-composite-assembler",
        tenant=TENANT,
        archetypes=("context_assembly",),
        context_contract={
            "consumes": [
                {
                    "product_class": requirement.product_class,  # type: ignore[attr-defined]
                    "schema_version": "1.0.0",
                }
            ]
        },
        perspective={"role": "assembler", "selection_params": {}},
        policy_regime={"ref": f"ccf-artifact://{regime_key}@1.0.0"},
        halflife_debt_profile={"ref": f"ccf-artifact://{TENANT}/debt-profile/x@1.0.0"},
        instruction_bindings=(),
    )
    catalog = SkillCatalog(registry)
    catalog.register(
        SkillCatalogEntry(
            schema_version="1.0.0",
            artifact_version="1.0.0",
            name="peered-child-skill",
            tenant=TENANT,
            skill_type="peering",
            description="reads the child product class from a peer",
            argument_schema=SkillArgumentSchema(properties={}, required=frozenset()),
            binding=PeeringBinding(endpoint="fixture-endpoint"),
            requirements=SkillRequirements(
                required_scopes=frozenset(), required_context_products=frozenset()
            ),
            produces=requirement.product_class,  # type: ignore[attr-defined]
        )
    )
    ledger = GrantLedger(
        control_plane=registry, catalog=catalog, sink=None, clock=_now
    )
    assert isinstance(
        ledger.request(
            SkillGrant(
                schema_version="1.0.0",
                artifact_version="1.0.0",
                name="grant-peered-child-skill",
                tenant=TENANT,
                agent_definition_hash=content_hash(definition),
                skill_name="peered-child-skill",
                skill_version="1.0.0",
            ),
            definition=definition,
            actor="peered-operator",
        ),
        str,
    )
    resolved = resolve_producing_grant(
        requirement,  # type: ignore[arg-type]
        ledger.bound_view(content_hash(definition)),
    )
    assert resolved is not None
    return resolved
