"""The SDK's reference composite child resolver — acquisition by granted skill.

`D-IMPL-336` **Amendment 5**. Dave, after challenging the design: *"The skill
that the composite agent has knows how to acquire the atomic context product
and roll it in."* This is that skill-driven acquisition, shipped so a
deployment **binds** a resolver instead of assembling a chain of evidence
objects by hand.

**Why this is in `src/` and does not violate harness neutrality.** CLAUDE.md
§7.3 and §8.1 keep the *agent loop* out of the SDK — planning, tool-calling,
sub-agent spawning. §11 commits the opposite way for pluggable substrates:
*"Reference implementations ship alongside Protocols."* Resolving a grant and
dispatching one skill is neither a loop nor a scheduler: it runs the
requirements a class declared, in declaration order, exactly once, and returns.
Dave's Amendment 5 settles it explicitly — *"Ship `GrantBoundChildResolver` in
`src/`"* — and the boundary that stays is the one that matters: **no scheduler,
no swarm loop, no new identity axis.**

The path, and it is the whole design:

    effective grant  →  actual skill dispatch  →  the child's governed
    delivery  →  fit checks  →  compose

**What this module does NOT do**, because the ruling is explicit that it must
not:

* It does not assemble atomic products. An atomic Context Product *may already
  be registered elsewhere and serve other consumers*; its provider decides
  whether to return an existing valid instance or assemble one on demand.
* It therefore never needs the provider's **assembler, source credentials,
  database handles or boot context**. It holds a grant ledger, a dispatch
  surface and an admission gate — nothing that reaches into another product's
  production.
* It does not verify signatures, peer trust or policy bindings. Those are
  :mod:`ccf.peering.admission`'s, and this module consumes the verdict.
* It does not re-ask whether the invocation was authorized. **The grant
  authorizes invoking the skill; the provider's own authorization governs what
  the invocation may return.** Composition duplicates neither decision.

**Transport is behind the skill, and is not the trust axis.** A `local_callable`
entry, an `mcp` entry and a `peering` entry all satisfy the same requirement.
What differs is which controls already applied — and that is read off the
**dispatch result's type** in
:func:`~ccf.products.composite.invocation_from_dispatch`, never declared.
`D-IMPL-59` separates MCP from Peering and so does this: an MCP read keeps its
own authenticated, authorized access and is **not** reclassified as peering.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

from typing import Any

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.peering.admission import AdmittedProduct, PeeringAdmissionGate
from ccf.products.composite import (
    GATE_CHILD_ADMISSION,
    ResolvedProducer,
    ChildAdmissionRefusal,
    ChildCandidate,
    CompositeAdmissionGate,
    invocation_from_dispatch,
    resolve_producing_grant,
)
from ccf.products.contract import (
    ChildRequirement,
    ContextProductContract,
    ProductLineage,
)
from ccf.products.door import DoorOutcome, ProducerAssertion, WireRequest
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import McpProductBinding
from ccf.skills.dispatch import (
    McpInvocation,
    McpProductFailure,
    McpProductInvocation,
    McpSkillRegistry,
    ProductQuestion,
    PeeringInvocation,
    PeeringSkillRegistry,
    SkillInvocation,
    dispatch_skill,
)
from ccf.skills.grants import GrantLedger

__all__ = [
    "ChildArguments",
    "ChildQuestion",
    "ChildQuestions",
    "ChildRecordMismatch",
    "GrantBoundChildResolver",
    "QuestionBoundChildResolver",
]


class ChildRecordMismatch(ValueError):
    """A child named a replay record that describes a different product.

    Raised rather than refused, deliberately. A governed refusal says *this
    child may not be composed*; this says *the evidence offered is not about
    this child at all*, which is a producer defect or an attempt to substitute
    evidence — neither is a fact about the child's eligibility, and reporting
    it as one would let a misattribution be read as a governed answer.

    **A `ValueError`, and the base class is load-bearing rather than
    incidental.** The focused review of this repair measured that the MCP
    egress door wraps only ``(ValueError, TypeError, LookupError, OSError)``
    into an opaque ``ccf-runtime-failure`` id — the ruled `D-IMPL-253` Q20
    posture: *no message, no type name, no traceback*. As a `RuntimeError`
    this class escaped that wrap and delivered a replay-reference URI and two
    content addresses straight to the client.

    The precedent settles the choice rather than leaving it to taste:
    :class:`~ccf.replay.serve.ProductRecordMismatch` is the **same defect class
    one layer up** — a record that does not describe the product it is filed
    against (`D-IMPL-279`) — and it is a `ValueError` for exactly this reason.

    **The wider hole is NOT closed here and is not this repair's.**
    :class:`~ccf.products.composite.AmbiguousProducerError` is also a
    `RuntimeError` reaching the same door from the same resolver, so the gap
    predates this work; widening the door's except tuple would change a runtime
    door's posture for a pre-existing condition and belongs to whoever owns
    that door, not to `D-IMPL-336`.
    """

#: How a deployment turns one declared requirement into the typed arguments its
#: producing skill takes. Deployment configuration, not SDK knowledge: what a
#: child needs to be asked is the deployment's to state (`D-IMPL-38`).
ChildArguments = Callable[[ChildRequirement, datetime], Mapping[str, str]]


class ChildQuestion(CCFContract):
    """What one child is asked, derived from the composite's request (`D-IMPL-340`).

    Four members, and only four, because these are the four the producer's
    ``request_context_product`` operation takes from the *question*; the
    producer's tenant, the class and lane, the reconstruction instant and the
    endpoint all come from elsewhere (the registration, the binding, the
    composite's own ``asked_at``) and are not reachable from here. There is no
    code path from a ``ChildQuestion`` to an address.
    """

    subject: str
    intent: str
    freshness: str
    parameters: Mapping[str, Any]


#: How a deployment turns one requirement and the composite's EFFECTIVE
#: request into the question its producer is asked. Deployment configuration,
#: never SDK knowledge (`D-IMPL-38`); what differs from :data:`ChildArguments`
#: is that the composite's own request — its subject, its resolved parameters
#: — is in scope, so a per-request anchor reaches the child through the
#: declared mapping rather than through state closed over beside it.
ChildQuestions = Callable[[ChildRequirement, ProductRequest], ChildQuestion]


class GrantBoundChildResolver:
    """Acquire each declared child through the grant that authorizes it.

    Conforms to
    :class:`~ccf.products.composite.CompositeChildResolverProtocol`
    structurally; a deployment substituting its own loses no capability.

    Args:
        ledger: The grant ledger this deployment's Control Plane holds.
        agent_definition_hash: Whose skill-set is in force. Grants are
            per-agent (`D-07`), so this names the composing agent — it is not
            a fabric identity and no new identity axis is introduced.
        gate: The composite admission gate, which performs the fit checks.
        child_arguments: Turns a requirement into its skill's arguments.
        callable_registry: For ``local_callable`` entries.
        mcp_skills: For ``mcp`` entries. ``None`` means this deployment binds
            none, and an MCP-bound grant then fails loudly rather than being
            skipped — a wiring fact, not a governed absence.
        peering_skills: For ``peering`` entries, on the same terms.
        peering_gate: Verifies an inbound peered product. Required only if a
            peering-bound skill may produce a child; ``None`` refuses one with
            ``provenance-unverified`` rather than admitting it unverified.
        artifact_store: Where this fabric's own decision records live. Read
            **only** for a locally dispatched child, to take its touched
            entities from its persisted execution record. Never used to reach
            a remote provider's store — Dave's ruling forbids requiring that.
    """

    def __init__(
        self,
        *,
        ledger: GrantLedger,
        agent_definition_hash: str,
        gate: CompositeAdmissionGate,
        child_arguments: ChildArguments,
        callable_registry: CallableRegistry,
        artifact_store: ArtifactStoreProtocol,
        mcp_skills: McpSkillRegistry | None = None,
        peering_skills: PeeringSkillRegistry | None = None,
        peering_gate: PeeringAdmissionGate | None = None,
    ) -> None:
        self._ledger = ledger
        self._agent = agent_definition_hash
        self._gate = gate
        self._child_arguments = child_arguments
        self._callables = callable_registry
        self._store = artifact_store
        self._mcp = mcp_skills
        self._peering = peering_skills
        self._peering_gate = peering_gate

    def __call__(
        self,
        *,
        requirements: tuple[ChildRequirement, ...],
        asked_at: datetime,
        admitted_at: datetime,
        composition_invocation: str,
        consumer_lineage: ProductLineage,
    ) -> dict[str, object]:
        """Resolve every declared requirement, in declaration order.

        Returns one outcome per requirement, keyed by product class:
        an :class:`~ccf.products.composite.AdmittedChild`, a
        :class:`~ccf.products.composite.ChildAdmissionRefusal`, or ``None`` for
        the honest absence *no granted skill produces this class*.

        **This method decides nothing about admissibility.** ``None`` is not a
        decision that the composite may proceed — `F1` is the composition's:
        a required slot refuses, an optional one takes its declared treatment.
        """
        view = self._ledger.bound_view(self._agent)
        outcomes: dict[str, object] = {}
        for requirement in requirements:
            producer = resolve_producing_grant(requirement, view)
            if producer is None:
                # The honest absence, and the ONLY one. Anything invoked and
                # refused is a refusal, never an omission (`F1`).
                outcomes[requirement.product_class] = None
                continue
            dispatched = dispatch_skill(
                producer.entry,
                arguments=self._child_arguments(requirement, asked_at),
                callable_registry=self._callables,
                mcp_skills=self._mcp,
                peering_skills=self._peering,
            )
            outcomes[requirement.product_class] = self._admit(
                requirement,
                producer=producer,
                dispatched=dispatched,
                asked_at=asked_at,
                admitted_at=admitted_at,
                composition_invocation=composition_invocation,
                consumer_lineage=consumer_lineage,
            )
        return outcomes

    def _admit(
        self,
        requirement: ChildRequirement,
        *,
        producer: ResolvedProducer,
        dispatched: object,
        asked_at: datetime,
        admitted_at: datetime,
        composition_invocation: str,
        consumer_lineage: ProductLineage,
    ) -> object:
        """Turn one dispatch result into an admitted child or a refusal."""
        refuse = _refusal_for(requirement)
        admission: AdmittedProduct | None = None
        touched: tuple[str, ...] | None = None

        if isinstance(dispatched, SkillInvocation):
            answer = _door_outcome(dispatched.output)
            if isinstance(answer, str):
                return refuse("ineligible", answer)
            contract, address, replay_ref = answer
            # The ONE store read, and only for a child this fabric produced.
            touched = self._touched_entities(replay_ref, contract)
        elif isinstance(dispatched, McpInvocation):
            answer = _door_outcome({"outcome": dispatched.contents})
            if isinstance(answer, str):
                return refuse("ineligible", answer)
            contract, address, _replay_ref = answer
            # Deliberately no store read: this fabric does not hold the
            # provider's execution record and the ruling forbids requiring it.
        elif isinstance(dispatched, McpProductFailure):
            # `D-IMPL-340` ruling 1: a registered, governed producer that
            # could not answer. A governed outcome carrying the registration
            # members, so the row names the producer; never an exception,
            # which is what an UNREGISTERED producer still gets.
            return ChildAdmissionRefusal(
                gate=GATE_CHILD_ADMISSION,
                detail=(
                    f"registered producer {dispatched.server!r} could not"
                    f" answer ({dispatched.failure}: {dispatched.detail}); the"
                    " producer was reached through its registration and gave"
                    " no governed answer, so this slot has no child"
                    " (D-IMPL-340)"
                ),
                product_class=requirement.product_class,
                reason="producer-unavailable",
                producer_id=dispatched.producer_id,
                producer_tenant=dispatched.producer_tenant,
                producer_registration_address=(
                    dispatched.producer_registration_address
                ),
                producer_server=dispatched.server,
                question_address=dispatched.question_address,
            )
        elif isinstance(dispatched, McpProductInvocation):
            asked = _door_answer({"outcome": dispatched.contents})
            if isinstance(asked, str):
                # The producer's own door refused — a governed answer, so an
                # `ineligible` row as on every other leg, and (ruling 9) one
                # that still names the exact producer it was refused by.
                return ChildAdmissionRefusal(
                    gate=GATE_CHILD_ADMISSION,
                    detail=asked,
                    product_class=requirement.product_class,
                    reason="ineligible",
                    producer_id=dispatched.producer_id,
                    producer_tenant=dispatched.producer_tenant,
                    producer_registration_address=(
                        dispatched.producer_registration_address
                    ),
                    producer_server=dispatched.server,
                    question_address=dispatched.question_address,
                )
            contract = ContextProductContract.model_validate_json(
                asked.product_json or ""
            )
            address = asked.content_address or ""
            # No store read, as for `mcp`: eligibility is the producer's
            # (`provider-controls`). What the door CLAIMED about itself, its
            # echo and its replay reference travel as claims for the gate's
            # producer leg to hold to the registration.
            return self._gate.admit(
                candidate=ChildCandidate(
                    requirement=requirement,
                    contract=contract,
                    content_address=address,
                    invocation=invocation_from_dispatch(producer, dispatched),
                    producer_assertion=asked.producer,
                    question_echo=asked.request,
                    child_replay_ref=asked.replay_ref,
                ),
                asked_at=asked_at,
                admitted_at=admitted_at,
                composition_invocation=composition_invocation,
            )
        elif isinstance(dispatched, PeeringInvocation):
            verified = self._admit_peered(
                dispatched,
                requirement,
                consumer_lineage=consumer_lineage,
                now=admitted_at,
            )
            if isinstance(verified, str):
                return refuse("provenance-unverified", verified)
            admission, contract, address = verified
        else:
            return refuse(
                "unsupported-outcome",
                f"a {type(dispatched).__name__} dispatch produces no Context"
                " Product, so this requirement cannot be satisfied by it",
            )

        return self._gate.admit(
            candidate=ChildCandidate(
                requirement=requirement,
                contract=contract,
                content_address=address,
                invocation=invocation_from_dispatch(
                    producer,
                    dispatched,
                    touched_entities=touched,
                ),
                admission=admission,
            ),
            asked_at=asked_at,
            admitted_at=admitted_at,
            composition_invocation=composition_invocation,
        )

    def _touched_entities(
        self, replay_ref: str | None, contract: ContextProductContract
    ) -> tuple[str, ...] | None:
        """What the locally dispatched child's own record says it read.

        ``None`` when the child reported no replay reference — a positive
        statement that its execution record is not resolvable here, which the
        admission gate must not read as *"nothing was touched"*.

        **The binding, stated because it is the whole guarantee.** The
        referenced record's own ``product_content_address`` is held against the
        child's **recomputed** address — ``content_hash(contract)``, never the
        address the producer reported — and that comparison happens **before**
        any dependency evidence is read out of the record.

        Raises:
            ChildRecordMismatch: the referenced record describes a different
                product. Raised rather than refused: evidence about another
                product is not a fact about this child's eligibility.
        """
        if replay_ref is None:
            return None
        record = DecisionReplayRecord.model_validate_json(
            self._store.get(content_address=self._store.resolve_uri(uri=replay_ref))
        )
        # **The record must be THIS product's.** Found by the final review and
        # reproduced: `contract` was a declared parameter this method never
        # read, so the entities came from whatever record the producing skill
        # NAMED rather than from the record that describes the product being
        # admitted. A producer serving an honest contract and address while
        # pointing `replay_ref` at an unrelated record had the eligibility
        # check ask the register about the wrong reads — and the row still
        # recorded `local-register` as the authority that cleared it.
        #
        # The asymmetry was the tell: the gate already refuses to trust the
        # producer on the CONTENT ADDRESS, recomputing `content_hash(contract)`
        # itself, and `DoorOutcome` already binds `replay_ref` on the REFUSED
        # path. Only the served path left it free. The evidence needed was
        # already required — `product_content_address` — and simply unused.
        #
        # `F3` closed the ABSENT-evidence case on this leg; this is the
        # MISATTRIBUTED-evidence case, which reads as present and passes.
        # Refused rather than admitted: the ruled contract (`D-IMPL-336`
        # Amendment 5 §3) is *"obtain touched entities from THE CHILD'S
        # persisted execution/replay record"*, and a record about another
        # product is not that.
        address = content_hash(contract)
        if record.content_generation_path.product_content_address != address:
            raise ChildRecordMismatch(
                f"the child reported replay reference {replay_ref!r}, whose"
                " record describes product"
                f" {record.content_generation_path.product_content_address!r},"
                f" while the product being admitted hashes to {address!r}."
                " Eligibility is established from the record of THIS product or"
                " not at all (D-IMPL-336 Amendment 5 §3)"
            )
        return tuple(record.context_fabric_snapshot.touched_entities)

    def _admit_peered(
        self,
        dispatched: PeeringInvocation,
        requirement: ChildRequirement,
        *,
        consumer_lineage: ProductLineage,
        now: datetime,
    ) -> tuple[AdmittedProduct, ContextProductContract, str] | str:
        """Run the peering gate over what the transport handed back.

        The transport's `products` are **unadmitted** by construction
        (`D-12`): the peer a channel observed is a channel-level claim. What
        binds a product to a principal is its signature, and
        :class:`~ccf.peering.admission.PeeringAdmissionGate` is what checks it.
        """
        if self._peering_gate is None:
            return (
                "this deployment binds no PeeringAdmissionGate, so a peered"
                " child cannot be verified and is not admitted on the"
                " transport's word"
            )
        for inbound in dispatched.products:
            outcome = self._peering_gate.admit(
                inbound=inbound, consumer_lineage=consumer_lineage, now=now
            )
            if not isinstance(outcome, AdmittedProduct):
                continue
            if outcome.product.schema_name != requirement.product_class:
                continue
            return (outcome, outcome.product, outcome.content_address or "")
        return (
            "the peering endpoint returned no product that passed admission"
            f" for {requirement.product_class!r}"
        )


def _refusal_for(
    requirement: ChildRequirement,
) -> Callable[[str, str], ChildAdmissionRefusal]:
    def refuse(reason: str, detail: str) -> ChildAdmissionRefusal:
        return ChildAdmissionRefusal(
            gate=GATE_CHILD_ADMISSION,
            detail=detail,
            product_class=requirement.product_class,
            reason=reason,  # type: ignore[arg-type]
        )

    return refuse


def _door_answer(output: Mapping[str, str]) -> DoorOutcome | str:
    """Decode a door answer in full, or say why it is not one (`D-IMPL-340`).

    The producer leg needs more than the vessel: the door's producer
    assertion, its echo of the question and its replay reference are the
    claims admission holds to the registration, so the whole outcome is
    returned rather than the three-tuple :func:`_door_outcome` gives the
    legacy legs.
    """
    raw = output.get("outcome")
    if raw is None:
        return (
            "the producing skill returned no 'outcome' member, so it did not"
            " answer with a Context Product on the wire"
        )
    answer = DoorOutcome.model_validate_json(raw)
    if answer.product_json is None or answer.content_address is None:
        kind = answer.refusal.kind if answer.refusal is not None else "no product"
        return f"the child's own door refused: {kind}"
    return answer


def _door_outcome(
    output: Mapping[str, str],
) -> tuple[ContextProductContract, str, str | None] | str:
    """Decode a door answer, or say why it is not one.

    **The wire boundary is the point.** A skill returns the product class by
    emitting :func:`~ccf.products.door.door_answer` bytes, so an in-process
    child crosses exactly the seam an MCP or A2A child crosses and its content
    address is the producer's own — not one the consumer recomputed from an
    object it was handed.
    """
    raw = output.get("outcome")
    if raw is None:
        return (
            "the producing skill returned no 'outcome' member, so it did not"
            " answer with a Context Product on the wire"
        )
    answer = DoorOutcome.model_validate_json(raw)
    if answer.product_json is None or answer.content_address is None:
        kind = answer.refusal.kind if answer.refusal is not None else "no product"
        return f"the child's own door refused: {kind}"
    return (
        ContextProductContract.model_validate_json(answer.product_json),
        answer.content_address,
        answer.replay_ref,
    )


class QuestionBoundChildResolver:
    """Acquire each declared child by asking its producer a governed question.

    `D-IMPL-340`. Conforms to
    :class:`~ccf.products.composite.RequestAwareChildResolverProtocol`
    structurally — it declares :meth:`resolve_for` and deliberately does
    **not** implement the legacy call, so a
    :class:`~ccf.products.resolver.GovernedResolver` reaches it with the
    composite's effective request or not at all. The grant resolution, the
    dispatch surface and the admission gate are the same objects
    :class:`GrantBoundChildResolver` holds; what differs is how a requirement
    becomes what its skill is asked.

    For an ``mcp_product`` entry the question is the deployment's
    ``child_questions`` mapping over the effective request; the tenant, class
    and lane come from the registration and the binding, the instant from the
    composite. For any other entry type the resolver falls back to
    ``child_arguments`` when one was supplied, so a composite may mix a
    remote producer with a same-fabric child; without one, such an entry is
    refused as ``unsupported-outcome`` rather than silently asked nothing.

    Args:
        child_questions: The deployment's mapping from a requirement and the
            composite's effective request to the child's question.
        child_arguments: Optional. The legacy mapping, for non-``mcp_product``
            entries granted to the same agent.
        (every other argument): exactly as :class:`GrantBoundChildResolver`.
    """

    def __init__(
        self,
        *,
        ledger: GrantLedger,
        agent_definition_hash: str,
        gate: CompositeAdmissionGate,
        child_questions: ChildQuestions,
        callable_registry: CallableRegistry,
        artifact_store: ArtifactStoreProtocol,
        mcp_skills: McpSkillRegistry | None = None,
        peering_skills: PeeringSkillRegistry | None = None,
        peering_gate: PeeringAdmissionGate | None = None,
        child_arguments: ChildArguments | None = None,
    ) -> None:
        self._questions = child_questions
        self._legacy = GrantBoundChildResolver(
            ledger=ledger,
            agent_definition_hash=agent_definition_hash,
            gate=gate,
            child_arguments=child_arguments or _no_child_arguments,
            callable_registry=callable_registry,
            artifact_store=artifact_store,
            mcp_skills=mcp_skills,
            peering_skills=peering_skills,
            peering_gate=peering_gate,
        )
        self._has_arguments = child_arguments is not None

    def resolve_for(
        self,
        *,
        requirements: tuple[ChildRequirement, ...],
        request: ProductRequest,
        asked_at: datetime,
        admitted_at: datetime,
        composition_invocation: str,
        consumer_lineage: ProductLineage,
    ) -> dict[str, object]:
        """Resolve every requirement, asking each producer the mapped question."""
        legacy = self._legacy
        view = legacy._ledger.bound_view(legacy._agent)
        outcomes: dict[str, object] = {}
        for requirement in requirements:
            producer = resolve_producing_grant(requirement, view)
            if producer is None:
                outcomes[requirement.product_class] = None
                continue
            binding = producer.entry.binding
            if isinstance(binding, McpProductBinding):
                question = self._questions(requirement, request)
                wire = WireRequest(
                    product_id=binding.product_class,
                    parameters=dict(question.parameters),
                    temporal_boundary=asked_at,
                )
                dispatched = dispatch_skill(
                    producer.entry,
                    arguments={},
                    callable_registry=legacy._callables,
                    mcp_skills=legacy._mcp,
                    peering_skills=legacy._peering,
                    question=ProductQuestion(
                        subject=question.subject,
                        intent=question.intent,
                        freshness=question.freshness,
                        asked_at=asked_at,
                        parameters=dict(question.parameters),
                        request_json=canonical_bytes(wire).decode("utf-8"),
                    ),
                )
            elif self._has_arguments:
                dispatched = dispatch_skill(
                    producer.entry,
                    arguments=legacy._child_arguments(requirement, asked_at),
                    callable_registry=legacy._callables,
                    mcp_skills=legacy._mcp,
                    peering_skills=legacy._peering,
                )
            else:
                outcomes[requirement.product_class] = _refusal_for(requirement)(
                    "unsupported-outcome",
                    f"the grant for {requirement.product_class!r} resolves to"
                    f" a {producer.entry.skill_type!r} skill and this resolver"
                    " was given no child_arguments mapping for it; a"
                    " question-bound resolver asks mcp_product producers a"
                    " question and cannot invent arguments for any other"
                    " skill type (D-IMPL-340)",
                )
                continue
            outcomes[requirement.product_class] = legacy._admit(
                requirement,
                producer=producer,
                dispatched=dispatched,
                asked_at=asked_at,
                admitted_at=admitted_at,
                composition_invocation=composition_invocation,
                consumer_lineage=consumer_lineage,
            )
        return outcomes


def _no_child_arguments(
    requirement: ChildRequirement, asked_at: datetime
) -> Mapping[str, str]:
    raise TypeError(
        f"no child_arguments mapping was supplied for {requirement.product_class!r}"
    )
