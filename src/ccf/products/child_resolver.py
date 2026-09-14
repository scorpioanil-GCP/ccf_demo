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

from ccf.artifacts.protocol import ArtifactStoreProtocol
from ccf.peering.admission import AdmittedProduct, PeeringAdmissionGate
from ccf.products.composite import (
    GATE_CHILD_ADMISSION,
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
from ccf.products.door import DoorOutcome
from ccf.replay.record import DecisionReplayRecord
from ccf.skills.callables import CallableRegistry
from ccf.skills.dispatch import (
    McpInvocation,
    McpSkillRegistry,
    PeeringInvocation,
    PeeringSkillRegistry,
    SkillInvocation,
    dispatch_skill,
)
from ccf.skills.grants import GrantLedger

__all__ = ["GrantBoundChildResolver", "ChildArguments"]

#: How a deployment turns one declared requirement into the typed arguments its
#: producing skill takes. Deployment configuration, not SDK knowledge: what a
#: child needs to be asked is the deployment's to state (`D-IMPL-38`).
ChildArguments = Callable[[ChildRequirement, datetime], Mapping[str, str]]


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
        producer: object,
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
                    producer,  # type: ignore[arg-type]
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
        """
        if replay_ref is None:
            return None
        record = DecisionReplayRecord.model_validate_json(
            self._store.get(content_address=self._store.resolve_uri(uri=replay_ref))
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
