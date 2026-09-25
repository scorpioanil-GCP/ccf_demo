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

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime

from typing import Any

from ccf.artifacts.protocol import ArtifactStoreProtocol, DerivedWrite
from ccf.authz.capability import Authorized, ReplayMint, verify
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.peering.admission import AdmittedProduct, PeeringAdmissionGate
from ccf.products.composite import (
    CHILD_QUESTION_CLASS,
    GATE_CHILD_ADMISSION,
    ChildRefusalReason,
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
    verify_mcp_product_failure,
    verify_mcp_product_invocation,
    PeeringInvocation,
    PeeringSkillRegistry,
    SkillInvocation,
    dispatch_skill,
)
from ccf.skills.grants import GrantLedger

__all__ = [
    "MalformedDoorAnswer",
    "ChildArguments",
    "ChildQuestion",
    "ChildQuestions",
    "ChildRecordMismatch",
    "GrantBoundChildResolver",
    "QuestionBoundChildResolver",
    "QuestionRetentionUnauthorized",
]


class QuestionRetentionUnauthorized(PermissionError):
    """The child-question capability does not cover the gate's tenant (D-IMPL-353 §1.3).

    A :class:`QuestionBoundChildResolver` files each question's identity bytes
    under its ``Authorized[ReplayMint]``'s tenant; the gate admits children for
    its own tenant. The two are one deployment's one consumer tenant, compared
    once at construction, so a question can never be retained under a tenant
    other than the one whose composite asked it. Raised, never returned —
    broken composition, not a governance outcome.
    """


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
            here only for a locally dispatched child, to take its touched
            entities from its persisted execution record; WRITTEN by the
            question-bound subclass, which files each question's identity
            bytes on it before dispatch (`D-IMPL-342` / `CP14-F-35`). Never
            used to reach a remote provider's store — Dave's ruling forbids
            requiring that.
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
        question_ref: str | None = None,
    ) -> object:
        """Turn one dispatch result into an admitted child or a refusal.

        ``question_ref`` (`D-IMPL-342`) is the URI the parent's store returned
        when the question-bound resolver retained the question's identity
        bytes before dispatch; it rides onto every outcome minted for that
        dispatch so the row can reference the retained artifact. The legacy
        argument-bound path mints no question and passes ``None``.
        """
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
            # which is what an UNREGISTERED producer still gets. The mint is
            # verified first: the members are about to be written into a
            # governed row.
            dispatched = verify_mcp_product_failure(dispatched)
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
                question_ref=question_ref,
            )
        elif isinstance(dispatched, McpProductInvocation):
            dispatched = verify_mcp_product_invocation(dispatched)
            asked_invocation = invocation_from_dispatch(
                producer, dispatched, question_ref=question_ref
            )

            def refuse_naming_producer(
                reason: ChildRefusalReason,
                detail: str,
                **producer_refusal: str | None,
            ) -> ChildAdmissionRefusal:
                return ChildAdmissionRefusal(
                    gate=GATE_CHILD_ADMISSION,
                    detail=detail,
                    product_class=requirement.product_class,
                    reason=reason,
                    producer_id=dispatched.producer_id,
                    producer_tenant=dispatched.producer_tenant,
                    producer_registration_address=(
                        dispatched.producer_registration_address
                    ),
                    producer_server=dispatched.server,
                    question_address=dispatched.question_address,
                    question_ref=question_ref,
                    **producer_refusal,
                )

            try:
                asked = _door_answer({"outcome": dispatched.contents})
            except MalformedDoorAnswer as malformed:
                # A completed call whose text is not a door outcome at all —
                # a gateway page, a truncated body. The producer was reached
                # and gave no governed answer: `producer-unavailable`, with
                # the failure's class and never its bytes (review finding).
                return refuse_naming_producer(
                    "producer-unavailable",
                    f"registered producer {dispatched.server!r} answered with"
                    f" something that is not a door outcome ({malformed});"
                    " the producer was reached and gave no governed answer"
                    " (D-IMPL-340)",
                )
            if asked.product_json is None or asked.content_address is None:
                # The producer's own door refused — a governed answer. Its
                # claims about itself and the question are still held to the
                # registration first: an impostor's refusal is a misrouting,
                # not an `ineligible` row under the registered producer's name.
                held = self._gate.hold_producer_claims(
                    invocation=asked_invocation,
                    assertion=asked.producer,
                    replay_ref=asked.replay_ref,
                    echo=asked.request,
                    answered=asked.answered,
                    refuse=refuse_naming_producer,
                )
                if held is not None:
                    return held
                # `D-IMPL-343` R-13: the producer's own reason travels with
                # the refusal — a served lane below the floor asked names both
                # lanes here rather than arriving as a bare `ineligible`.
                # Structured recovery of that evidence onto the row is
                # `D-IMPL-342`; what is retained here is the reason as the
                # producer's door disclosed it.
                if asked.refusal is None:
                    described = "no product"
                else:
                    named = asked.refusal.reason
                    if asked.refusal.key is not None:
                        named = f"{named} at {asked.refusal.key!r}"
                    described = f"{asked.refusal.kind} ({named}: {asked.refusal.detail})"
                # `D-IMPL-342`: the producer's own refusal — kind, reason,
                # key and its replay reference — is carried as EVIDENCE beside
                # the admission verdict, which stays ``ineligible``. Until now
                # the four were collapsed into the prose above and the
                # reference was dropped, while a served-then-rejected child
                # kept its reference (`CP03C-F-05`). Its ``detail`` stays in
                # the prose: it is the producer's disclosure-level text, not
                # an identity token.
                return refuse_naming_producer(
                    "ineligible",
                    f"the child's own door refused: {described}",
                    producer_refusal_kind=(
                        asked.refusal.kind if asked.refusal is not None else None
                    ),
                    producer_refusal_reason=(
                        asked.refusal.reason if asked.refusal is not None else None
                    ),
                    producer_refusal_key=(
                        asked.refusal.key if asked.refusal is not None else None
                    ),
                    producer_replay_ref=asked.replay_ref,
                )
            contract = ContextProductContract.model_validate_json(asked.product_json)
            address = asked.content_address
            # No store read, as for `mcp`: eligibility is the producer's
            # (`provider-controls`). What the door CLAIMED about itself, its
            # echo and its replay reference travel as claims for the gate's
            # producer leg to hold to the registration.
            return self._gate.admit(
                candidate=ChildCandidate(
                    requirement=requirement,
                    contract=contract,
                    content_address=address,
                    invocation=asked_invocation,
                    producer_assertion=asked.producer,
                    question_echo=asked.request,
                    answered_question=asked.answered,
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


class MalformedDoorAnswer(ValueError):
    """A completed producer call whose text is not a `DoorOutcome` (`D-IMPL-340`)."""


def _door_answer(output: Mapping[str, str]) -> DoorOutcome:
    """Decode a door answer in full, or raise :class:`MalformedDoorAnswer`.

    The producer leg needs more than the vessel: the door's producer
    assertion, its echo of the question, the axes it answered and its replay
    reference are the claims admission holds to the registration, so the
    whole outcome is returned rather than the three-tuple
    :func:`_door_outcome` gives the legacy legs. A text that does not parse
    as a door outcome is reported by exception CLASS only — never its bytes,
    which could be anything a gateway returned.
    """
    raw = output.get("outcome")
    if raw is None:
        raise MalformedDoorAnswer("no 'outcome' member")
    try:
        return DoorOutcome.model_validate_json(raw)
    except ValueError as invalid:
        raise MalformedDoorAnswer(type(invalid).__name__) from None


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
        authorized: The composition-minted ``Authorized[ReplayMint]`` for
            :data:`~ccf.products.composite.CHILD_QUESTION_CLASS` (D-IMPL-353
            §1.2, §2 P3; D-IMPL-354) — the capability under which this
            resolver files each question's identity bytes. **This resolver is
            not a composition root**: the deployment that composes it
            (:func:`~ccf.products.product.open_product`, or a test or example
            composing by hand) mints it and hands it in. Verified here, at
            construction, against exactly the child-question class, and its
            tenant is held equal to the gate's — one consumer tenant, compared
            once (§1.3).
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
        authorized: Authorized[ReplayMint],
        child_questions: ChildQuestions,
        callable_registry: CallableRegistry,
        artifact_store: ArtifactStoreProtocol,
        mcp_skills: McpSkillRegistry | None = None,
        peering_skills: PeeringSkillRegistry | None = None,
        peering_gate: PeeringAdmissionGate | None = None,
        child_arguments: ChildArguments | None = None,
    ) -> None:
        # The capability first: kind, mint and resource by identity, before
        # anything about this resolver exists (D-IMPL-353 §1.5).
        verify(authorized, kind=ReplayMint, resource=CHILD_QUESTION_CLASS)
        if authorized.tenant != gate.tenant_id:
            raise QuestionRetentionUnauthorized(
                f"the child-question capability is for tenant"
                f" {authorized.tenant!r} and the admission gate admits for"
                f" {gate.tenant_id!r}; a composite retains its questions under"
                " the one consumer tenant it admits for (D-IMPL-353 §1.3)"
            )
        self._authorized = authorized
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
        requirements: Sequence[ChildRequirement],
        request: ProductRequest,
        asked_at: datetime,
        admitted_at: datetime,
        composition_invocation: str,
        consumer_lineage: ProductLineage,
    ) -> dict[str, object]:
        """Resolve every requirement, asking each producer the mapped question.

        ``requirements`` is typed as the
        :class:`~ccf.products.composite.RequestAwareChildResolverProtocol`
        declares it, so this class conforms to the Protocol the resolver
        checks NOMINALLY as well as at runtime (`D-IMPL-343`: the paved road
        hands one to the builder under the Protocol's type).
        """
        legacy = self._legacy
        view = legacy._ledger.bound_view(legacy._agent)
        outcomes: dict[str, object] = {}
        for requirement in requirements:
            producer = resolve_producing_grant(requirement, view)
            if producer is None:
                outcomes[requirement.product_class] = None
                continue
            binding = producer.entry.binding
            question_ref: str | None = None
            if isinstance(binding, McpProductBinding):
                question = self._questions(requirement, request)
                wire = WireRequest(
                    product_id=binding.product_class,
                    parameters=dict(question.parameters),
                    temporal_boundary=asked_at,
                )
                sent = ProductQuestion(
                    subject=question.subject,
                    intent=question.intent,
                    freshness=question.freshness,
                    asked_at=asked_at,
                    parameters=dict(question.parameters),
                    request_json=canonical_bytes(wire).decode("utf-8"),
                )
                # `D-IMPL-342` / `CP14-F-35`: the question's identity bytes go
                # on the parent's store BEFORE the producer is called, so an
                # admitted, refused or unreachable producer alike leaves the
                # exact historical question behind. No artifact, no dispatch.
                question_ref = self._retain_question(sent)
                dispatched = dispatch_skill(
                    producer.entry,
                    arguments={},
                    callable_registry=legacy._callables,
                    mcp_skills=legacy._mcp,
                    peering_skills=legacy._peering,
                    question=sent,
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
                question_ref=question_ref,
            )
        return outcomes

    def _retain_question(self, sent: ProductQuestion) -> str:
        """File the question's identity bytes on the parent's store; return the store's URI.

        `D-IMPL-342` / `CP14-F-35`. The artifact is
        :meth:`~ccf.skills.dispatch.ProductQuestion.identity_artifact` — the
        five-member preimage whose canonical bytes
        :func:`~ccf.skills.dispatch.question_identity` hashes — filed under
        :data:`~ccf.products.composite.CHILD_QUESTION_CLASS`, named by the
        address, under the capability's tenant — the consumer tenant the gate
        admits for, held equal at construction. Idempotent by
        the store's construction: the same question asked twice files once.

        The store's address for the bytes must equal the question's address —
        the identity the row records — or replay could not resolve the row to
        the bytes; a store that hashed differently is refused here, loudly,
        as the admitted-contract retention refuses it (`D-IMPL-339`). A store
        that cannot file raises: the producer is then never asked, and no row
        can claim a retained question the store does not hold (the
        `D-IMPL-344` R-3 posture).

        Raises:
            RuntimeError: the store filed the bytes at another address.
            OSError, ccf.contracts.canonical.CanonicalizationError: as the
                store raises them — propagated, never converted into a
                governed refusal.
        """
        legacy = self._legacy
        address = sent.address
        # A derived write under the composition-minted capability (D-IMPL-353
        # §1.2): the class is the SDK's, the name is the question's own
        # address, and the tenant is the capability's — held equal to the
        # gate's at construction.
        filed = legacy._store.put(
            self._authorized,
            DerivedWrite(
                artifact_class=CHILD_QUESTION_CLASS,
                name=address,
                artifact=sent.identity_artifact(),
            ),
        )
        if filed.content_address != address:
            raise RuntimeError(
                "the artifact store filed a child question's identity bytes at"
                f" {filed.content_address!r} but the question's address is"
                f" {address!r}; replay holds the retained bytes to the row's"
                " child_question_address and this store would break that"
                " (D-IMPL-342 / CP14-F-35)"
            )
        return filed.uri


def _no_child_arguments(
    requirement: ChildRequirement, asked_at: datetime
) -> Mapping[str, str]:
    raise TypeError(
        f"no child_arguments mapping was supplied for {requirement.product_class!r}"
    )
