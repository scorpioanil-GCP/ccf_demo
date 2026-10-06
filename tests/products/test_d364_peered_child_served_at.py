"""`SEC-010` B3: the peered child is judged at the SAME instant as an in-process one.

`D-IMPL-364`, the criterion for `SEC-010`, clause B3, verbatim:

    *B3 (per choice 3).* Gate 3's `now` is `served_at`: a product with
    `expires_at <= served_at` refuses, one with `expires_at > served_at +
    MAX_TTL` refuses, `MAX_TTL` is the Control Plane's, and returning the
    comparand to the decision instant reddens a named control; the composite's
    children and the mixing law are judged at `served_at`; **a peered child is
    judged at the same instant as an in-process child, proven by a BEHAVIORAL
    control that executes the peered-child branch — structural proof alone does
    not discharge it.**

And Dave's own words at choice (3): *"Require a behavioral control for the
peered child at the same `served_at`. Structural proof alone does not discharge
it."*

**What stood before this module, and why it was not enough.** Two controls
covered the peered hop and both read SOURCE rather than behavior —
`tests/peering/test_admission_clock.py::test_the_peering_hop_passes_the_FABRIC_instant_and_not_the_question_s`
and
`tests/products/test_served_at_severings.py::test_severing_Peer_the_verdict_is_judged_at_the_callers_instant`.
Their own docstrings said why: the behavioral control *"does not exist because
no path to it exists"* — `GrantBoundChildResolver._admit` requires a
`ResolvedProducer`, mintable only through `resolve_producing_grant` from a
module-private `BoundSkillView`, and **no deployment in the tree wired a
`PeeringAdmissionGate` into a child resolver**. That is a statement about the
FIXTURES, not about the mechanism, and this module is the fixture that was
missing: a real grant ledger holding two grants, a real `PeeringSkillRegistry`
over a transport that hands back one honestly signed envelope, a real
`PeeringAdmissionGate`, and a real `CompositeAdmissionGate` — driven through
`GrantBoundChildResolver.resolve_for` (the request-aware call `SEC-025` made it
take) with the question's instant and the fabric's instant pinned SEVEN MINUTES
APART.

**Nothing here is a stub that ignores `now`.** The admission gate is the shipped
:class:`~ccf.peering.admission.PeeringAdmissionGate`; the only wrapper is a spy
that RECORDS the instant it was handed and then delegates to that gate
unchanged (:class:`_PeeringNowSpy`). A gate that ignored `now` would make the
second test below — where the verdict itself moves with the instant —
unfalsifiable, which is the reason the counterfactual is run against the real
gate rather than asserted about a double.

Ruling 9 of `D-IMPL-358` is what made the hop's argument exist at all:
`PeeringAdmission.admit(now=)` joined the Gate 3 repair, so the peered child is
judged at the fabric instant. This module is the first execution of that branch.

Every domain-shaped value — peer id, key id, producer hash, product schema,
policy regime — is read from `tests/fixtures/banking/*.yaml` through the peering
fixtures, and every fabric-shaped value from the composite fixture deployment
(CINV-01: nothing domain-shaped is authored here).
"""

from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Iterator, Mapping
from datetime import datetime, timedelta
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.peering.admission import (
    ADMISSION_RECORD,
    INBOUND_PAYLOAD_CEILING,
    AdmittedProduct,
    InboundPayloadCeiling,
    PeeringAdmissionGate,
    payload_ceiling_key,
)
from ccf.peering.eligibility import (
    ELIGIBILITY_EVIDENCE_POLICY,
    EligibilityEvidencePolicy,
    eligibility_evidence_policy_key,
)
from ccf.peering.identity import DetachedJwsIdentityProvider, SignedContextProduct
from ccf.peering.protocol import EmitReceipt, InboundProduct, PeerRef
from ccf.peering.trust_policy import (
    PEERING_TRUST_POLICY,
    PeeringTrustPolicy,
    PeerTrustGrant,
    trust_policy_key,
)
from ccf.products.composite import (
    ELIGIBILITY_LOCAL_REGISTER,
    ELIGIBILITY_PRODUCER_ATTESTED,
    AdmittedChild,
    ChildAdmissionRefusal,
    CompositeAdmissionGate,
)
from ccf.products.child_resolver import GrantBoundChildResolver
from ccf.products.contract import (
    ChildRequirement,
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.request import ProductRequest
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import (
    PeeringBinding,
    SkillArgumentSchema,
    SkillCatalogEntry,
    SkillRequirements,
)
from ccf.skills.dispatch import PeeringSkillRegistry
from ccf.skills.grants import SkillGrant

from tests.composition import (
    composition_replay_mint,
    declaring_store,
    register_at_composition,
    register_skill_entry,
    register_typed_at_composition,
)
from tests.deployment.conftest import TENANT
from tests.products.composite_fixture import (
    CHILD_CALLABLE,
    CHILD_CLASS,
    CHILD_SKILL,
    _child_door,
    _ledger,
    asks_its_own_subject,
    boot_composite,
)
from tests.products.test_resolver_seam import ADMITTED_AT, ASKED_AT, _Booted
from tests.skills.authority import grant_capability

# The peering fixtures' own values and helpers, imported rather than restated.
# `provider` and `key_dir` are pytest fixtures and are re-exported here so this
# module's tests can request them (the same move
# `tests/peering/test_peered_child_envelope.py` makes).
from tests.peering.test_admission_attributability import (  # noqa: F401
    CEILING_BYTES,
    PEER,
    PEER_KID,
    PEER_PRODUCER,
    POLICY_REGIME,
    POLICY_SEMVER,
    PRODUCT_CLASS as PEERED_PRODUCT_CLASS,
    consumer_lineage,
    key_dir,
    provider,
    public_key,
)
from tests.peering.test_peered_child_envelope import (
    CONSUMER_SCOPE,
    _assertion_header,
    peered_child,
)

#: The class the peered leg produces, and the class the in-process leg produces.
#: DIFFERENT classes, because `resolve_producing_grant` refuses two in-force
#: grants that both claim one class — so a single composite acquiring both legs
#: is only expressible with two classes, which is also the shape the clause's
#: comparison needs.
PEERED_CLASS: str = PEERED_PRODUCT_CLASS["schema_name"]
PEERED_VERSION: str = PEERED_PRODUCT_CLASS["schema_version"]

#: The grant that puts the peering-bound producing skill in force, its logical
#: endpoint name, and the key this consumer's MAX_TTL for the peered class is
#: registered under. Deployment vocabulary, authored test-side.
PEERED_SKILL = "peered-child-skill"
PEERED_ENDPOINT = "fixture-peer-endpoint"
PEERED_MAX_TTL_KEY = "tenant-fixture/peered-child/max-ttl"

#: This composition's invocation identity — one value for the whole resolve, as
#: a composition has exactly one.
INVOCATION = "composition://d364-peered-and-local-0001"

#: The MAX_TTL the consumer's Control Plane holds for the peered class. Wide
#: enough that neither test is measuring the ceiling: what is measured here is
#: the INSTANT the ceiling and the expiry are compared against.
PEERED_MAX_TTL_SECONDS = 3600

#: Where the peered product's expiry sits in each test.
#:
#: `_VALID_FOR` is comfortably past BOTH instants, so the first test's verdict
#: cannot turn on expiry at all and its measurement is the recorded argument.
#: `_EXPIRES_BETWEEN` sits strictly between the question's instant and the
#: fabric's, which is what lets the second test turn the same argument into a
#: difference in the VERDICT — admitted at one instant, refused at the other.
_VALID_FOR = timedelta(minutes=30)
_EXPIRES_BETWEEN = timedelta(minutes=3)


class _PeeringNowSpy:
    """The real :class:`PeeringAdmissionGate`, with the instant it is handed recorded.

    A spy and not a double: every call delegates to the gate the deployment
    wired, so a verdict observed through this object is the shipped gate's
    verdict. What it adds is the one fact the structural controls could only
    read off source — WHICH instant the child resolver actually passed down the
    peered hop at run time.
    """

    def __init__(self, inner: PeeringAdmissionGate) -> None:
        self._inner = inner
        self.nows: list[datetime] = []

    def admit(
        self,
        *,
        inbound: InboundProduct,
        consumer_lineage: ProductLineage,
        now: datetime,
    ) -> object:
        self.nows.append(now)
        return self._inner.admit(
            inbound=inbound, consumer_lineage=consumer_lineage, now=now
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _OnePeerTransport:
    """A :class:`~ccf.peering.protocol.PeeringProtocol` holding one received envelope.

    The deployment's composition root is what registers a transport
    (`T-06-57`: a skill artifact never names an address), so a test standing in
    as that root supplies one. It declares trust INPUTS and never a verdict —
    it yields :class:`~ccf.peering.protocol.InboundProduct`, which is unadmitted
    by construction (`D-12`) — so nothing about this class can shortcut the gate
    the clause is about.
    """

    def __init__(self, inbound: InboundProduct) -> None:
        self._inbound = inbound
        self.receives = 0

    def emit(self, *, peer: PeerRef, signed: SignedContextProduct) -> EmitReceipt:
        raise AssertionError("this control reads from a peer and emits nothing")

    def receive(self) -> Iterator[InboundProduct]:
        self.receives += 1
        yield self._inbound


def _child_arguments(requirement: ChildRequirement, asked_at: datetime) -> dict[str, str]:
    """What the deployment states each of its children is asked.

    One mapping for both legs: the peered entry declares the same argument
    schema as the in-process one, so the composite's own statement of what it
    asks does not have to branch on how a child happens to be acquired — which
    is the property `D-IMPL-336` Amendment 5 is for.
    """
    return {
        "subject": "acct-1",
        "asked_at": asked_at.isoformat(),
        "threshold": "1000",
    }


def _peered_product(*, expires_after: timedelta) -> ContextProductContract:
    """The banking fixture's product, re-tenanted onto the consuming fabric.

    Three members are moved and nothing else: the tenant (trust is per tenant,
    and the consuming gate admits for its own), the reconstruction instant (a
    composite has exactly one, and a child from another cannot be composed), and
    the expiry (which is what the second test varies). The product is SIGNED
    after the move, so its attested address is the address of these bytes.
    """
    return peered_child().model_copy(  # type: ignore[no-any-return]
        update={
            "tenant_id": TENANT,
            "temporal_boundary": ASKED_AT,
            "expires_at": ASKED_AT + expires_after,
        }
    )


def _inbound(
    provider: DetachedJwsIdentityProvider, product: ContextProductContract
) -> InboundProduct:
    """One honestly signed envelope, built exactly as the `R1` control builds one."""
    signed = provider.sign(
        product=product,
        key_id=PEER_KID,
        assertions=_assertion_header(
            product, checked_at=ASKED_AT, invocation=INVOCATION
        ),
    )
    assert isinstance(signed, SignedContextProduct)
    return InboundProduct(
        observed_peer=PeerRef(tenant_id=TENANT, peer_id=PEER), signed=signed
    )


def _peering_gate(
    booted: _Booted,
    provider: DetachedJwsIdentityProvider,
    public_key: Mapping[str, str],
    tmp_path: pathlib.Path,
) -> PeeringAdmissionGate:
    """The consuming fabric's peering gate, over the deployment's OWN Control Plane.

    The peered class is registered here as a class this consumer serves,
    because the gate holds an inbound product to the consumer's own pinned
    MAX_TTL — *"this consumer serves no product class X, so it holds no MAX_TTL
    to gate the product against"* is the refusal otherwise, and it would hide
    the instant this module is measuring behind a wiring absence.
    """
    registry = booted.control_plane
    max_ttl_version = register_at_composition(
        registry, PEERED_MAX_TTL_KEY, MaxTTL(seconds=PEERED_MAX_TTL_SECONDS)
    )
    peered_class = register_product_class(
        registry=registry,
        schema_name=PEERED_CLASS,
        schema_version=PEERED_VERSION,
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=PEERED_MAX_TTL_KEY,
        max_ttl_version=max_ttl_version,
    )
    trust_version = register_typed_at_composition(
        registry,
        trust_policy_key(tenant_id=TENANT),
        PeeringTrustPolicy(
            semver=POLICY_SEMVER,
            tenant_id=TENANT,
            peers={
                PEER: PeerTrustGrant(
                    signing_keys={PEER_KID: public_key},
                    permitted_producer_hashes=frozenset({PEER_PRODUCER}),
                    permitted_schema_names=frozenset({PEERED_CLASS}),
                    permitted_policy_regimes=frozenset({POLICY_REGIME}),
                )
            },
        ),
        PEERING_TRUST_POLICY,
    )
    ceiling_version = register_typed_at_composition(
        registry,
        payload_ceiling_key(tenant_id=TENANT),
        InboundPayloadCeiling(semver=POLICY_SEMVER, max_payload_bytes=CEILING_BYTES),
        INBOUND_PAYLOAD_CEILING,
    )
    return PeeringAdmissionGate(
        identity=provider,
        control_plane=registry,
        audit_log=registry.audit_log,
        artifact_store=declaring_store(
            tmp_path / "admission-records", ADMISSION_RECORD.class_id
        ),
        authorized=composition_replay_mint(
            registry, tenant=TENANT, artifact_class=ADMISSION_RECORD.class_id
        ),
        trust_policy_version=trust_version,
        payload_ceiling_version=ceiling_version,
        product_classes={PEERED_CLASS: peered_class},
    )


def _resolver_over_two_legs(
    booted: _Booted,
    *,
    peering_gate: object,
    transport: _OnePeerTransport,
) -> GrantBoundChildResolver:
    """One child resolver, two in-force grants: one `local_callable`, one `peering`.

    The ledger, the catalog, the agent definition and the policy regime are the
    composite fixture's — imported rather than restated, so the in-process leg
    here is the same leg `tests/products/test_composite_integration.py` drives.
    What this adds is the SECOND grant, which is the thing no deployment in the
    tree had.
    """
    ledger, agent_hash, definition, catalog = _ledger(booted)
    for skill in (CHILD_SKILL, PEERED_SKILL):
        if skill == PEERED_SKILL:
            registered = register_skill_entry(
                catalog,
                booted.control_plane,
                SkillCatalogEntry(
                    schema_version="1.0.0",
                    artifact_version="1.0.0",
                    name=PEERED_SKILL,
                    tenant=TENANT,
                    skill_type="peering",
                    description="reads the peered child class from a federation peer",
                    argument_schema=SkillArgumentSchema(
                        properties={
                            "subject": {
                                "type": "string",
                                "description": "The account the child answers about.",
                            },
                            "asked_at": {
                                "type": "string",
                                "description": "The composition's one reconstruction instant.",
                            },
                            "threshold": {
                                "type": "string",
                                "description": "The class-declared threshold parameter.",
                            },
                        },
                        required=frozenset({"subject", "asked_at", "threshold"}),
                    ),
                    binding=PeeringBinding(endpoint=PEERED_ENDPOINT),
                    requirements=SkillRequirements(
                        required_scopes=frozenset(),
                        required_context_products=frozenset(),
                    ),
                    produces=PEERED_CLASS,
                ),
            )
            assert isinstance(registered, str), registered
        granted = ledger.request(
            grant_capability(definition),
            SkillGrant(
                schema_version="1.0.0",
                artifact_version="1.0.0",
                name=f"grant-{skill}",
                tenant=TENANT,
                agent_definition_hash=agent_hash,
                skill_name=skill,
                skill_version="1.0.0",
            ),
            definition=definition,
        )
        assert isinstance(granted, str), granted

    callables = CallableRegistry()
    callables.register(CHILD_CALLABLE, _child_door(booted))

    peering_skills = PeeringSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    peering_skills.register(endpoint=PEERED_ENDPOINT, transport=transport)

    # The consumer declares how old a producer's eligibility check may be (`F7`).
    register_typed_at_composition(
        booted.control_plane,
        eligibility_evidence_policy_key(tenant_id=TENANT),
        EligibilityEvidencePolicy(
            max_evidence_age_seconds=3600, permitted_clock_skew_seconds=60
        ),
        ELIGIBILITY_EVIDENCE_POLICY,
    )
    return GrantBoundChildResolver(
        ledger=ledger,
        agent_definition_hash=agent_hash,
        gate=CompositeAdmissionGate(
            tenant_id=TENANT,
            consumer_scope=CONSUMER_SCOPE,
            registry=booted.control_plane,
        ),
        child_arguments=_child_arguments,
        # `SEC-025`: what the composite asks each child, so the in-process
        # leg's answered subject is bound to it.
        child_questions=asks_its_own_subject,
        callable_registry=callables,
        artifact_store=booted.store,
        peering_skills=peering_skills,
        peering_gate=peering_gate,  # type: ignore[arg-type]
    )


def _request() -> ProductRequest:
    """The composite's request — what each child's question is minted from (`SEC-025`)."""
    return ProductRequest(
        schema_name="fixture.manifest-product",
        schema_version="1.0.0",
        subject="acct-1",
        intent="fixture-intent",
        freshness="fixture-freshness",
        asked_at=ASKED_AT,
        parameters={},
    )


def _requirements() -> tuple[ChildRequirement, ...]:
    """The two declared requirements, both REQUIRED.

    Required rather than optional for the reason the composite fixture gives:
    an optional requirement has a declared absence treatment, so a resolve that
    never reached a leg at all would still look satisfied.
    """
    return (
        ChildRequirement(
            product_class=CHILD_CLASS, required=True, compatible_from="1.0.0"
        ),
        ChildRequirement(
            product_class=PEERED_CLASS, required=True, compatible_from=PEERED_VERSION
        ),
    )


@contextlib.contextmanager
def _deployment(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The composite fixture deployment, driven as a context manager."""
    generator = boot_composite(tmp_path)
    booted = next(generator)
    try:
        yield booted
    finally:
        generator.close()


def test_a_peered_child_and_an_in_process_child_are_judged_at_the_same_served_at(
    tmp_path: pathlib.Path,
    provider: DetachedJwsIdentityProvider,
    public_key: Mapping[str, str],
) -> None:
    """B3, behaviorally: ONE resolve, two legs, one instant — the fabric's.

    `ASKED_AT` and `ADMITTED_AT` are the fixture's two pinned instants, seven
    minutes apart, and the resolve is driven with ``asked_at=ASKED_AT`` and
    ``admitted_at=ADMITTED_AT``. Both legs are then asserted to have been judged
    at `ADMITTED_AT`:

    * the peered leg, by the instant the child resolver actually handed
      :meth:`~ccf.peering.admission.PeeringAdmissionGate.admit` — recorded by
      the spy, which is a fact about the executed call and not about the source;
    * the in-process leg, by :attr:`AdmittedChild.admitted_at`, which the
      composite gate takes from the ``admitted_at`` it was passed.

    And the reconstruction instant is asserted to be the OTHER one on both legs,
    because "the same instant" is only the claim if the two instants are
    genuinely distinct in this run — a fixture whose two instants had collapsed
    would satisfy every assertion below while measuring nothing.

    **Expected GREEN today.** The mechanism already passes ``admitted_at`` down
    the peered hop; what did not exist was any execution of that branch. The
    proof this control carries is therefore its SEVERING, named exactly:
    in `src/ccf/products/child_resolver.py`, the ``now=admitted_at,`` argument of
    the ``self._admit_peered(...)`` call inside
    ``GrantBoundChildResolver._admit`` replaced by ``now=asked_at,`` must redden
    this test — it is the same edit
    `tests/products/test_served_at_severings.py::test_severing_Peer_the_verdict_is_judged_at_the_callers_instant`
    applies, and that control can only read the source slice afterwards, where
    this one watches the argument arrive.

    The IN-PROCESS half of the comparison has its own severing in the same
    method: the ``admitted_at=admitted_at`` keyword of the closing
    ``self._gate.admit(...)`` call replaced by ``admitted_at=asked_at`` reddens
    ``local.admitted_at == ADMITTED_AT`` here. Both severings are the
    orchestrator's to run against the tree; this module does not apply them.
    """
    with _deployment(tmp_path) as booted:
        gate = _peering_gate(booted, provider, public_key, tmp_path)
        spy = _PeeringNowSpy(gate)
        transport = _OnePeerTransport(
            _inbound(provider, _peered_product(expires_after=_VALID_FOR))
        )
        resolver = _resolver_over_two_legs(
            booted, peering_gate=spy, transport=transport
        )

        assert ASKED_AT != ADMITTED_AT, (
            "the fixture's two instants have collapsed, so no assertion below"
            " can distinguish the question's instant from the fabric's"
        )

        outcomes = resolver.resolve_for(
            requirements=_requirements(),
            request=_request(),
            asked_at=ASKED_AT,
            admitted_at=ADMITTED_AT,
            composition_invocation=INVOCATION,
            consumer_lineage=consumer_lineage(),
        )

        # Both legs genuinely ran and both produced an admitted child.
        assert set(outcomes) == {CHILD_CLASS, PEERED_CLASS}, outcomes
        local = outcomes[CHILD_CLASS]
        peered = outcomes[PEERED_CLASS]
        assert isinstance(local, AdmittedChild), local
        assert isinstance(peered, AdmittedChild), peered
        # The two legs were acquired the two different ways, which is what makes
        # the comparison between them a comparison at all.
        assert local.eligibility_basis == ELIGIBILITY_LOCAL_REGISTER
        assert peered.eligibility_basis == ELIGIBILITY_PRODUCER_ATTESTED
        assert transport.receives == 1, (
            "the peered branch did not execute: the transport was read"
            f" {transport.receives} times"
        )

        # THE CLAUSE. The peered hop was handed the FABRIC instant, exactly
        # once, and never the question's.
        assert spy.nows == [ADMITTED_AT], (
            "the peered admission was judged at an instant other than the"
            f" fabric's: {spy.nows}"
        )
        assert ASKED_AT not in spy.nows

        # And the in-process leg was judged at the same instant, from the gate's
        # own record of when it admitted.
        assert peered.admitted_at == ADMITTED_AT
        assert local.admitted_at == ADMITTED_AT
        assert local.admitted_at == peered.admitted_at, (
            "the two legs were admitted at different instants, which is the"
            " asymmetry B3 forbids"
        )

        # Both answered the ONE reconstruction instant, which is the other one.
        assert local.asked_at == ASKED_AT and peered.asked_at == ASKED_AT
        assert local.contract.temporal_boundary == ASKED_AT
        assert peered.contract.temporal_boundary == ASKED_AT


def test_the_peered_verdict_itself_moves_when_the_instant_moves(
    tmp_path: pathlib.Path,
    provider: DetachedJwsIdentityProvider,
    public_key: Mapping[str, str],
) -> None:
    """The instant is MATERIAL on the peered leg, not merely recorded.

    `D-IMPL-364` `SEC-010` B3 again, and the half a recorded argument cannot
    carry on its own: *"a product with `expires_at <= served_at` refuses"*. The
    envelope here expires three minutes after the question and four minutes
    before the serve, so the two instants give OPPOSITE verdicts on the same
    bytes. Driven through the resolver it refuses — `provenance-unverified`,
    because composition does not admit a peered child on the transport's word
    — while the in-process leg beside it still admits. The counterfactual is
    then run against the SAME shipped gate at the question's instant and
    admits, which is what proves the refusal is the instant's doing and not the
    envelope's.

    Without this test, a peering gate that ignored its `now` argument entirely
    would satisfy the control above (the argument would still be recorded) and
    nothing in the tree would notice. With it, the severing named above reddens
    on the VERDICT as well as on the argument.
    """
    with _deployment(tmp_path) as booted:
        gate = _peering_gate(booted, provider, public_key, tmp_path)
        spy = _PeeringNowSpy(gate)
        product = _peered_product(expires_after=_EXPIRES_BETWEEN)
        assert ASKED_AT < product.expires_at < ADMITTED_AT, (
            "the envelope's expiry does not sit between the two instants, so"
            " the two instants cannot disagree about it"
        )
        inbound = _inbound(provider, product)
        resolver = _resolver_over_two_legs(
            booted, peering_gate=spy, transport=_OnePeerTransport(inbound)
        )

        outcomes = resolver.resolve_for(
            requirements=_requirements(),
            request=_request(),
            asked_at=ASKED_AT,
            admitted_at=ADMITTED_AT,
            composition_invocation=INVOCATION,
            consumer_lineage=consumer_lineage(),
        )

        peered = outcomes[PEERED_CLASS]
        assert isinstance(peered, ChildAdmissionRefusal), peered
        assert peered.reason == "provenance-unverified", peered
        assert spy.nows == [ADMITTED_AT], spy.nows

        # The leg that did not cross a trust boundary is unaffected: this is a
        # statement about the instant, not about the resolve having fallen over.
        assert isinstance(outcomes[CHILD_CLASS], AdmittedChild), outcomes[CHILD_CLASS]

        # THE COUNTERFACTUAL, against the same shipped gate: at the question's
        # instant these exact bytes are admitted. So the refusal above is the
        # instant's doing.
        at_the_question = gate.admit(
            inbound=inbound,
            consumer_lineage=consumer_lineage(),
            now=ASKED_AT,
        )
        assert isinstance(at_the_question, AdmittedProduct), (
            "the same envelope is refused at the question's instant too, so the"
            " refusal above proves nothing about which instant governed"
        )
        assert content_hash(at_the_question.product) == content_hash(product)
