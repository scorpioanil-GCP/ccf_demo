"""The replay engine: a recorded decision, reproduced and hash-verified.

Whitepaper §7.10 (every decision forensically reconstructible years later
against the exact fabric state at decision time — INV-CH7-79/86); D-IMPL-06
(logical snapshots); D-IMPL-26 (exact-version artifact resolution); D-IMPL-44
(the re-hydration path); DESIGN.md §2B.5.

The pipeline, in order, with each step's failure mode named:

1. **Resolve the record** at its content address. A missing record is
   :class:`ReplayUnresolvable` — never the nearest one, never the newest under
   the name. The **raw fetched bytes** are re-hashed on arrival, before any
   model validation, so a substrate that returned the wrong artifact is caught
   here rather than believed (T-04-17, D-IMPL-89).

   That read path is :func:`resolve_artifact`, which is **parametrized by
   contract rather than fixed to the decision record**, plus
   :func:`resolve_artifact_at_uri` for the named form. A replay resolves
   whatever a record names, and the discipline — exact version, no fallback,
   re-hash on arrival, ``@latest`` refused — is identical for every class, so it
   is stated once. ``ccf.admission-record`` (D-IMPL-58 reading (d)) resolves
   through it as any other class does; no federation-shaped special case exists
   inside this engine, which is what keeps the seam described in one place
   rather than two.

   Then — for the decision record only, and **before anything is resolved
   or re-executed** — the record's stored canonical form is held against the
   running canonicalizer's **declared generation boundaries** (``D-IMPL-243``
   amendment 1). A field the running record class marks
   ``ccf_hash_transparent: False`` that the stored bytes lack is a field
   whose owner asserted "a record without this is of an earlier generation":
   no hash this engine computes below could be compared with one that
   record carries, so the record is refused as
   :class:`ReplayGenerationMismatch` — reason
   ``canonical_generation_mismatch``, **naming the field** — rather than
   diverging later on a parameter hash for operators that are exactly the
   ones that ran. Fields marked ``True`` (omitted at their sentinel) and
   fields with no key (the pre-243 ``D-IMPL-89`` lineage) are never named;
   the check is declared scope, not "every default the class has grown". It
   lives here and not in :func:`resolve_artifact`, by ruling: byte-first
   resolution is a statement about the record's **own** address and stays
   exactly ``D-IMPL-89``; the generation boundary is a statement about the
   hashes replay **re-computes**, which only this function does.
2. **Resolve every Control Plane binding at its exact recorded version.** A
   control plane that has lost the version a decision was made under cannot say
   what that decision saw; that is :class:`ReplayUnresolvable`, not a fallback.
3. **Resolve the projection plan and operators** through the deployment's
   :class:`ReplayEnvironment`. The SDK cannot know a deployment's Π or its
   operator parameters — they are user code and user configuration — so this is
   a seam. It is a *verified* seam: what the environment supplies is checked
   against the record, never trusted.
4. **Re-execute** against a :class:`~ccf.replay.snapshots.SnapshotReader` pinned
   to the recorded tenant and boundary — under the recorded dimension-2
   ``survivor_cap`` (D-10), so a capped decision re-executes the way it ran —
   then check that the executed step sequence — operator keys, categories, and
   parameter hashes, in order — equals the recorded one, and that the
   re-executed query-pin sequence — one ``content_hash`` per issued
   ``GraphQuery``, in order — equals the recorded dimension-5
   ``graph_query_sequence`` (D-11). Drifted parameters and a drifted question
   sequence both surface as :class:`ReplayDivergence` here rather than as a
   quietly different answer. A record carrying the pre-seam
   :data:`~ccf.replay.record.NO_GRAPH_QUERIES` sentinel asserts it predates
   the query seam, and the pin comparison stands down — that is the
   compatibility promise, not a hole: the snapshot and product checks below
   still hold it to the same answer.
5. **Check the snapshot id** derived from the re-execution against the recorded
   one. Both are content-derived, so agreement is a statement about state.
6. **Re-hydrate the product** and check its content address against the
   recorded one. This is the claim in one line: *the same bytes*.

**Divergence is raised, not returned.** The gates (L6) return refusals as data
because a caller there holds a candidate it might legitimately discard. A
replay has no such option: a decision that does not reproduce is a finding, and
a caller that could receive it as a value could log it and carry on with the
freshly-computed product — which is precisely the substitution this engine
exists to prevent.

Nothing here reads a clock, and nothing here resolves "latest".

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Final, Protocol, TypeVar, runtime_checkable

from ccf.artifacts.protocol import (
    ArtifactStoreError,
    ArtifactStoreProtocol,
    MovingTargetRefused,
)
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash, generation_mismatch
from ccf.controlplane.artifacts import PolicyConstraint
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.graph.protocols import GraphReader
from ccf.products.composite import ChildContractView
from ccf.products.contract import ContextProductContract
from ccf.products.request import (
    ProductRequestContract,
    ProductRequestViolation,
    request_seeds,
)
from ccf.projection.engine import ExecutionResult, OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
from ccf.replay.record import (
    CHILD_ADMITTED,
    ChildResolution,
    ContentGenerationPath,
    ContextFabricSnapshot,
    DecisionReplayRecord,
    NO_ASSEMBLY_REFUSAL,
    NO_FABRIC_READ,
    NO_GRAPH_QUERIES,
    NO_PRODUCT_ADDRESS,
    NO_REQUEST_RESOLUTION,
    ResolutionNotApplicable,
)
from ccf.replay.snapshots import SnapshotReader, snapshot_of_execution
from ccf.products.expiry import (
    FROM_DECISION,
    FROM_ENTITY_FRESHNESS,
    TTLAnchorResolution,
    resolve_ttl_anchor,
)
from ccf.controlplane.artifacts import HalfLifeTable
from ccf.skills.dispatch import ChildQuestionIdentity

__ccf_mode__ = "algorithmic"

__all__ = [
    "ReplayDivergence",
    "CompositeReplayEnvironment",
    "ReplayEnvironment",
    "ReplayError",
    "ReplayGenerationMismatch",
    "ReplayOutcome",
    "ReplayRecordKindMismatch",
    "ReplayResolutionClaimMismatch",
    "ReplayUnresolvable",
    "RefusalReplayOutcome",
    "replay",
    "replay_refusal",
    "retained_child_question",
    "resolve_artifact",
    "resolve_artifact_at_uri",
]

#: Any contract a record can name. Bound to :class:`CCFContract` because the
#: resolution discipline needs exactly two things from an artifact — that it
#: parses closed-world, and that it has a canonical form to re-hash — and both
#: are properties of that base rather than of any particular class.
_ArtifactT = TypeVar("_ArtifactT", bound=CCFContract)


class ReplayError(Exception):
    """Base of the replay engine's failures."""


class ReplayUnresolvable(ReplayError, LookupError):
    """Something the record names cannot be resolved at its exact version.

    The record, a Control Plane binding, a projection plan, an operator. In
    every case the engine stops: a replay that substituted a *different*
    version would produce a confident answer about a decision that never
    happened, which is worse than no answer (CLAUDE.md §7.4, D-IMPL-26).
    """


class ReplayDivergence(ReplayError):
    """The reproduction does not match what was recorded.

    A finding, and therefore raised rather than returned — see the module
    docstring. Carries what disagreed in its message so the operator reading it
    can tell parameter drift from state drift from an envelope mismatch.
    """


class ReplayGenerationMismatch(ReplayError):
    """The record was written under an earlier generation of the canonical form.

    ``D-IMPL-243`` (the CR-01 ruling) and its amendment 1; whitepaper §7.10;
    CLAUDE.md §7.4. Raised by :func:`replay` **before** any binding, plan or
    operator is resolved and before anything is re-executed, when the record's
    stored canonical object lacks a field the running
    :class:`~ccf.replay.record.DecisionReplayRecord` declares as a generation
    boundary (``ccf_hash_transparent: False``). The record resolved — its own
    address verified byte-first under ``D-IMPL-89`` — but every hash this
    engine would go on to compare (``parameter_hash`` per step, the
    ``graph_query_sequence`` pins, ``product_content_address``) is computed by
    a canonicalizer that renders a field the record predates, so a comparison
    would report divergence for operators that are exactly the ones that ran.
    Refusing by name is the ruling: "not a quiet address drift and not a
    silent upgrade".

    Not a :class:`ReplayDivergence` — nothing was reproduced and found to
    differ — and not a :class:`ReplayUnresolvable` — nothing is missing from
    any store. It is its own finding, with its own token, so an operator can
    tell "this record cannot be replayed by this revision of the SDK" from
    either of those.

    Attributes:
        reason: The token, ``canonical_generation_mismatch``, fixed on the
            class so a caller can branch on it without parsing the message.
        fields: The model-qualified names of every boundary field the stored
            object lacks, in the record class's declaration order, dotted
            through nested models (``DecisionReplayRecord.policy_bindings.x``).
        content_address: Where the refused record was resolved from.
    """

    reason: Final[str] = "canonical_generation_mismatch"

    def __init__(self, *, contract: type[CCFContract], fields: tuple[str, ...], content_address: str) -> None:
        self.fields = tuple(f"{contract.__name__}.{name}" for name in fields)
        self.content_address = content_address
        super().__init__(
            f"{self.reason}: the {contract.__name__} at {content_address!r} "
            "was written under an earlier generation of the canonical form — "
            "it lacks "
            + ", ".join(self.fields)
            + ", which the running SDK declares as a generation boundary "
            "(ccf_hash_transparent: False); no hash this revision computes "
            "can be compared with one this record carries, so it is refused "
            "by name rather than replayed into a divergence (D-IMPL-243)"
        )


class ReplayResolutionClaimMismatch(ReplayError):
    """The record claims no resolution applies, and its own pins say one ran.

    ``D-IMPL-264`` D-11 (24.7-09) with amendment 3 B-3 a; whitepaper §7.10
    (the five-dimension record's completeness commitment, applied to
    dimension 2's resolution); CLAUDE.md §11 (replay enforced at write time
    and verified at read time). Raised by :func:`replay` **after** every
    binding has resolved at its pinned version and **before** anything is
    re-executed, when dimension 2's ``request_resolution`` is a
    :class:`~ccf.replay.record.ResolutionNotApplicable` marker while at
    least one of the record's ``policy_bindings.bindings``, resolved at its
    EXACT pinned version through the Control Plane, is a
    :class:`~ccf.products.request.ProductRequestContract` or a
    :class:`~ccf.controlplane.artifacts.PolicyConstraint`. Dave's sentence
    for why those two classes and only those two: *"request-contract pin +
    applicable constraint pins are the evidence that effective-request
    resolution ran."* A record that both pins that evidence and claims the
    resolution never happened has contradicted itself, and the engine
    refuses to replay a contradiction into a confident answer.

    Not a :class:`ReplayDivergence` — nothing was re-executed and found to
    differ; the check reads the record and the Control Plane, never the
    graph. Not a :class:`ReplayUnresolvable` — nothing is missing; the pins
    resolve, which is exactly how the contradiction becomes visible. It is
    its own finding, with its own token, so an operator can tell *"this
    record's dimension 2 is not the truth about this decision"* from either
    of those. Dave, ``D-IMPL-264`` P-2: *"`not applicable` is an explicit
    governed fact with a reason. Missing resolution information is an
    internal integrity failure."* This is the read-side half of that rule.

    Attributes:
        reason: The token, ``resolution_claim_mismatch``, fixed on the class
            so a caller can branch on it without parsing the message.
        claimed_reason: The reason the marker stated — the claim that the
            pins contradict.
        pinned: Every ``(key, version, artifact class name)`` in the
            record's bindings that resolved to a trigger class, in the
            record's binding order. The evidence, named so the operator can
            re-resolve it.
        content_address: Where the refused record was resolved from.
    """

    reason: Final[str] = "resolution_claim_mismatch"

    def __init__(
        self,
        *,
        content_address: str,
        claimed_reason: str,
        pinned: tuple[tuple[str, str, str], ...],
    ) -> None:
        self.content_address = content_address
        self.claimed_reason = claimed_reason
        self.pinned = pinned
        evidence = ", ".join(
            f"({key!r}, {version!r}) → {class_name}"
            for key, version, class_name in pinned
        )
        super().__init__(
            f"{self.reason}: the DecisionReplayRecord at {content_address!r} "
            f"claims no request resolution applies ({claimed_reason!r}) while "
            "its own policy bindings pin, at their recorded versions, "
            f"{evidence} — the evidence that effective-request resolution ran "
            "(D-IMPL-264 D-11, amendment 3). A record that pins the contract "
            "or constraint a resolution consulted and states that none applied "
            "has contradicted itself; it is refused by name rather than "
            "replayed into an answer about a decision whose governance it "
            "misstates"
        )



class ReplayRecordKindMismatch(ReplayError):
    """The record is not the kind of decision this entry point reconstructs.

    `D-IMPL-344`. A :class:`DecisionReplayRecord` is one of two kinds, and the
    record says which on its own dimension 5: a **served** decision names a
    product address and carries :data:`~ccf.replay.record.NO_ASSEMBLY_REFUSAL`;
    a **refused** decision carries the refusal's own block and
    :data:`~ccf.replay.record.NO_PRODUCT_ADDRESS`. :func:`replay` reconstructs
    the first and :func:`replay_refusal` the second, and each refuses the
    other's record **by name**. The order, exactly: the shared prologue
    resolves the record at its address and verifies its generation, its
    bindings and its resolution claim first; this guard runs after that, and
    before any child contract, plan or operator is resolved and before
    anything is re-executed.

    Raised, not returned, for the reason every replay finding is: before this
    guard a refused record handed to :func:`replay` failed at
    ``environment.resolve_plan("no-fabric-read")`` — a *don't know* reported
    as a missing plan — and a served record handed to a refusal reconstruction
    would have had a product read off it as though nothing had been served.
    Also raised for a record that contradicts itself about its kind (a refusal
    block beside a product address, or neither), and for a refused record
    whose dimension 5 contradicts its own no-read claim.
    """

@runtime_checkable
class ReplayEnvironment(Protocol):
    """The deployment side of a replay (SDK-defined seam).

    A record names *what* ran — plan id, operator keys, parameter hashes — but
    the things themselves are deployment code and deployment configuration. The
    environment supplies them; the engine verifies them. Nothing an environment
    returns is taken on trust: a wrong plan produces a step-sequence mismatch, a
    wrong parameter set produces a parameter-hash mismatch, and a wrong product
    envelope produces a content-address mismatch.
    """

    def resolve_plan(self, *, plan_id: str) -> ProjectionPlan:
        """Return the projection registered under ``plan_id``.

        Raises:
            LookupError: no such plan. The engine translates it into
                :class:`ReplayUnresolvable`.
        """
        ...

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> OperatorRegistry:
        """Return a registry holding the recorded operators as they then were.

        ``operator_keys`` is the recorded execution order, passed so an
        environment can resolve historical parameter sets rather than current
        ones.

        Raises:
            LookupError: an operator cannot be reconstituted.
        """
        ...

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        """Rebuild the delivered product from the record and the re-execution.

        The payload comes from the re-executed projection; the envelope
        (schema, TTL anchor, expiry) comes from the deployment's product class.
        The engine checks the result's content address against the record, so
        an envelope reconstructed wrongly is caught rather than accepted.

        **The TTL ANCHOR comes off the record too** (`D-IMPL-341`). Read
        ``record.content_generation_path.ttl_anchor_at`` and carry it verbatim
        onto the rebuilt product, and reconstruct ``expires_at`` FROM it rather
        than from the graph boundary or the decision instant; a pre-341 record
        carries ``None``, which is the decision-anchored shape and reconstructs
        as it always did. The member is hash-transparent, so an environment
        that omits it still passes the address check and fails only the engine's
        anchor hold — measured on three example environments at 341's
        validation pass, each of which had to be told this.

        **The debt in force comes off the record, and must not be re-measured**
        (15.5-11, D-IMPL-100). ``ContextProductContract.debt`` is inside the
        hashed body, so an implementation that omitted it — or recomputed it —
        returns a product the engine's address check rejects. It is
        reconstructible without a signature change because the record is
        already a parameter here: read
        ``record.content_generation_path.debt`` and carry it onto the rebuilt
        product verbatim. Re-deriving it is not an option even in principle:
        D_c is computed from observations and a ``now`` that neither the record
        nor the projection re-derives, so a fresh assessment would be a
        different decision wearing this one's identifier. A record carrying the
        ``None`` sentinel asserts its decision had no assessment, and the
        rebuilt product carries ``None`` in turn.

        **What the debt pointed at comes off the record too, and an
        implementation that omits it diverges** (15.6-06, D-IMPL-118).
        ``ContextProductContract.debt_evidence`` is a *top-level* vessel field
        rather than a member of the assessment, so it does not ride ``debt``
        back: read ``record.content_generation_path.debt_evidence`` and carry
        it onto the rebuilt product verbatim. It is reconstructible without a
        signature change for the same reason ``debt`` is — the record is
        already a parameter here — but only because dimension 5 was given a
        matching member; :class:`~ccf.projection.plan.ProjectionOutput` carries
        exactly ``(plan_id, payload)`` and names no evidence at all. A record
        carrying :data:`~ccf.halflife.assessment.NO_DEBT_EVIDENCE` asserts its
        decision pointed at nothing, and the rebuilt product asserts the same.

        **When the sources last published comes off the record too** (15.6-07,
        D-IMPL-117 gap 2; reshaped by 15.6-13 under D-IMPL-124).
        ``ContextProductContract.source_refresh_recency`` is the second
        top-level vessel field under the same D-IMPL-118 placement, so it does
        not ride ``debt`` back either: read
        ``record.content_generation_path.source_refresh_recency`` and carry it
        onto the rebuilt product verbatim. Re-deriving it is not an option even
        in principle — a refresh instant is a fact the deployment declared
        about its sources at assembly time, and a rehydrator that asked those
        sources again would be recording today's answer against a decision made
        against yesterday's. A record carrying
        :data:`~ccf.halflife.assessment.NO_SOURCE_REFRESH_RECENCY` asserts its
        decision recorded no refresh instants, and the rebuilt product asserts
        the same. **The read-back line is unchanged in spelling** by D-IMPL-124:
        the member now carries a
        :class:`~ccf.halflife.assessment.SourceRefreshWindow` rather than a
        per-source map, and a conforming implementation copies it exactly as it
        copied the map.

        **What the signal obliged comes off the record too — and re-resolving
        it is the failure this one guards** (15.6-08, D-IMPL-117 gap 3).
        ``ContextProductContract.obligation_in_force`` is the third top-level
        vessel field under the same D-IMPL-118 placement: read
        ``record.content_generation_path.obligation_in_force`` and carry it onto
        the rebuilt product verbatim. Unlike the two members above, an
        implementation *can* obtain a plausible value elsewhere — the
        deployment's current :class:`~ccf.controlplane.artifacts.DebtProfile`
        binds an obligation to the very same signal — and that is exactly what
        must not be done. A profile rebound since the decision would reproduce
        the obligation in force **now** against a decision made under the one in
        force **then**, which is the substitution CLAUDE.md §7.4 and D-IMPL-26
        forbid: replay resolves exact versions, never "latest". The engine's
        address check catches it, because the value is inside the hashed body.
        A record carrying
        :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE` asserts its
        decision was under no bound obligation, and the rebuilt product asserts
        the same.
        """
        ...


@runtime_checkable
class CompositeReplayEnvironment(ReplayEnvironment, Protocol):
    """A replay environment that can rebuild a CHILD-DEPENDENT plan (`D-IMPL-339`).

    The companion to :class:`ReplayEnvironment` on the two-seams precedent
    (:class:`~ccf.products.resolver.CompositePlanFactoryProtocol`): an
    environment for a composite whose plan read its children's contracts
    declares so by implementing this method. :func:`replay` reconstructs the
    view from the contracts the deciding fabric RETAINED by content address —
    never from a provider — and hands it here **before** the plan is rebuilt.
    An environment implementing only :meth:`ReplayEnvironment.resolve_plan`
    is used exactly as before for every record that composed no admitted
    child, and is refused, by name, for one that did.
    """

    def resolve_composite_plan(
        self, *, plan_id: str, children: ChildContractView
    ) -> ProjectionPlan:
        """Return the projection registered under ``plan_id``, over ``children``.

        Raises:
            LookupError: no such plan. Translated into :class:`ReplayUnresolvable`.
        """
        ...


class ReplayOutcome(CCFContract):
    """A verified reproduction. Constructed only after every check has passed.

    Holding one of these *is* the evidence — the engine has no path that
    returns an outcome it could not verify, so a caller cannot receive a
    "probably" and read it as a "yes".

    Attributes:
        record: The record that was replayed, resolved at its exact address.
        product: The reproduced product.
        record_content_address: Where the record was resolved from.
        product_content_address: Content address of the reproduced product,
            equal by construction to the one the record carries.
        graph_snapshot_id: Snapshot id derived from the re-execution, equal by
            construction to the recorded one.
    """

    record: DecisionReplayRecord
    product: ContextProductContract
    record_content_address: str
    product_content_address: str
    graph_snapshot_id: str



class RefusalReplayOutcome(CCFContract):
    """A verified reconstruction of a REFUSED decision (`D-IMPL-344`).

    Constructed only after every check :func:`replay_refusal` runs has passed,
    on the same rule as :class:`ReplayOutcome`: holding one *is* the evidence.
    **It has no ``product`` member and cannot acquire one.** A refused decision
    served nothing, and a reconstruction that could hand back something
    product-shaped — the provisional projection a post-projection refusal
    re-derived, say — would let a governed "no" be read as a "yes" one call
    downstream.

    Attributes:
        record: The record that was reconstructed, resolved at its exact
            address.
        record_content_address: Where the record was resolved from.
        assembly_refusal: Dimension 5's refusal block — the refusal envelope's
            canonical bytes — rehydrated and re-canonicalized equal.
        child_contract_addresses: Every admitted child row's content address,
            each resolved from the store and re-hashed to itself. Empty when
            the decision admitted no child, which is a positive statement.
        graph_snapshot_id: :data:`~ccf.replay.record.NO_FABRIC_READ` for a
            refusal reached before any projection ran; otherwise the snapshot
            id the re-execution derived, equal by construction to the
            recorded one.
    """

    record: DecisionReplayRecord
    record_content_address: str
    assembly_refusal: str
    child_contract_addresses: tuple[str, ...]
    graph_snapshot_id: str

def resolve_artifact(
    *,
    store: ArtifactStoreProtocol,
    content_address: str,
    contract: type[_ArtifactT],
) -> _ArtifactT:
    """Resolve one recorded artifact at its **exact** content address.

    The replay plane's single read path, stated once and parametrized by
    contract rather than duplicated per artifact class. Generality is the point:
    a replay resolves whatever a record names — a
    :class:`~ccf.replay.record.DecisionReplayRecord`, a
    ``ccf.admission-record`` (D-IMPL-58 reading (d)), a future class — and the
    resolution *discipline* is identical in every case, so a per-class resolver
    would be the same rule written down N times and a place for the (N+1)th to
    differ. Nothing about federation is special-cased inside the replay engine;
    an admission record resolves by class exactly as any other artifact does.

    Two guarantees, both structural rather than procedural:

    * **Exact version, never a fallback.** A miss is
      :class:`ReplayUnresolvable`. Substituting a nearby or newer artifact would
      produce a confident answer about a decision that never happened, which is
      worse than no answer (CLAUDE.md §7.4, D-IMPL-26).
    * **The raw fetched bytes are re-hashed on arrival, before validation**
      (D-IMPL-89). The put-time address *is* the sha256 of the stored canonical
      bytes, and the store's ``get`` contract promises those exact bytes back —
      so byte fidelity is the whole tamper claim, verified model-class-free. A
      substrate that returned the wrong artifact is *caught* rather than
      believed (T-04-17, T-06-102), and the "exact version" claim rests on
      arithmetic rather than on the store's good behaviour. The check is
      deliberately **not** a re-hash of the re-validated model: canonicalizing
      a rebuilt model serializes every sentinel-defaulted field a *later*
      contract version added, so an honest record written before a record
      extension would re-hash to a different address and trip the tamper check
      — the exact failure D-IMPL-89 rules out. Byte-first verification is what
      makes the sentinel-default extension strategy (D-IMPL-87 lineage) keep
      its compatibility promise.

    Args:
        store: Where the artifact lives (CLAUDE.md §7.4).
        content_address: The address to resolve. An address, not a name: names
            move, addresses do not.
        contract: The contract the bytes must satisfy. Supplied by the caller
            because deciding *which* contract a set of bytes is remains the
            caller's business — the store's contract is byte fidelity.

    Raises:
        ReplayUnresolvable: nothing is stored at that address.
        ReplayDivergence: the stored bytes do not hash to the address asked for.
    """
    try:
        payload = store.get(content_address=content_address)
    except (ArtifactStoreError, KeyError) as missing:
        raise ReplayUnresolvable(
            f"no {contract.__name__} is stored at {content_address!r}; "
            "replay resolves the exact recorded artifact and has no fallback "
            "(CLAUDE.md §7.4, D-IMPL-26)"
        ) from missing
    # Byte fidelity FIRST, validation second (D-IMPL-89): the address is the
    # sha256 of the stored canonical bytes, so the raw payload is the thing to
    # verify. Re-hashing a re-validated model here would serialize every
    # sentinel-defaulted field a later contract version added and reject
    # honest pre-extension records as tampered.
    reproduced = hashlib.sha256(payload).hexdigest()
    if reproduced != content_address:
        raise ReplayDivergence(
            f"the bytes at {content_address!r} hash to {reproduced!r}; the "
            f"store returned bytes that are not the {contract.__name__} that "
            "was asked for"
        )
    return contract.model_validate_json(payload)


def resolve_artifact_at_uri(
    *,
    store: ArtifactStoreProtocol,
    uri: str,
    contract: type[_ArtifactT],
) -> _ArtifactT:
    """Resolve a recorded artifact named by a D-IMPL-26 versioned URI.

    Naming resolution first, then :func:`resolve_artifact`. The two steps stay
    two calls for the reason :meth:`~ccf.artifacts.protocol.
    ArtifactStoreProtocol.resolve_uri` gives: identity is the content address
    and everything else is naming, and a combined call tempts an implementation
    to answer the naming question approximately.

    This is where ``@latest`` dies on the replay path. A URI is a string, and a
    string is where a moving target sneaks back in, so the refusal has to happen
    on the path a caller actually takes rather than only in a parser nobody is
    obliged to reach.

    Raises:
        ccf.artifacts.protocol.MovingTargetRefused: the URI asks for
            ``@latest``. Propagated unchanged, not translated: the caller did
            not fail to find something, the caller asked a question replay must
            never answer.
        ReplayUnresolvable: the URI is malformed, names no stored version, or
            names a version whose bytes are absent.
        ReplayDivergence: the resolved bytes do not hash to the address the name
            pointed at.
    """
    try:
        content_address = store.resolve_uri(uri=uri)
    except MovingTargetRefused:
        raise
    except (ArtifactStoreError, LookupError) as unresolvable:
        raise ReplayUnresolvable(
            f"{uri!r} names no stored {contract.__name__} version; replay "
            "resolves an exact version and has no fallback "
            "(CLAUDE.md §7.4, D-IMPL-26)"
        ) from unresolvable
    return resolve_artifact(
        store=store, content_address=content_address, contract=contract
    )


def _resolve_record(
    *, store: ArtifactStoreProtocol, record_address: str
) -> DecisionReplayRecord:
    """Resolve the decision record — the generic path, at a fixed contract."""
    return resolve_artifact(
        store=store,
        content_address=record_address,
        contract=DecisionReplayRecord,
    )


def _stored_canonical_object(
    *, store: ArtifactStoreProtocol, content_address: str
) -> Mapping[str, object]:
    """The record's stored canonical form, as bytes parsed — not as a model.

    Fetched the way :func:`resolve_artifact` fetches it — the same
    ``store.get`` at the same address — and held to the same arithmetic: the
    bytes must hash to the address, or they are not the record that was just
    resolved. The second read exists because the generation check needs the
    stored **object**, and a validated model cannot supply it: validation
    fills every default, which erases the very absence the check measures.
    The store's ``get`` contract promises the same bytes for the same address,
    and the re-hash makes that a verified property rather than a trusted one.
    """
    payload = store.get(content_address=content_address)
    reproduced = hashlib.sha256(payload).hexdigest()
    if reproduced != content_address:
        raise ReplayDivergence(
            f"the bytes at {content_address!r} hash to {reproduced!r} on the "
            "second read; the store returned different bytes for the same "
            "address between resolution and the generation check"
        )
    stored = json.loads(payload)
    if not isinstance(stored, Mapping):
        raise ReplayDivergence(
            f"the bytes at {content_address!r} are not a canonical object"
        )
    return stored


def _refuse_generation_mismatch(
    *,
    contract: type[CCFContract],
    stored: Mapping[str, object],
    content_address: str,
) -> None:
    """Refuse ``stored`` by name if it crosses a declared generation boundary.

    ``D-IMPL-243`` amendment 1. Parametrized by contract for the same reason
    :func:`resolve_artifact` is: the discipline is one rule, and a test can
    hold it against a scratch contract without a decision record in the
    loop. :func:`generation_mismatch` decides; this raises.
    """
    missing = generation_mismatch(contract, stored)
    if missing:
        raise ReplayGenerationMismatch(
            contract=contract, fields=missing, content_address=content_address
        )


def _resolve_bindings(
    *, record: DecisionReplayRecord, control_plane: ControlPlaneProtocol
) -> None:
    """Resolve every recorded binding at its pinned version, or refuse."""
    for binding in record.policy_bindings.bindings:
        try:
            control_plane.resolve(binding.key, binding.version)
        except ControlPlaneMissing as missing:
            raise ReplayUnresolvable(
                f"policy binding ({binding.key!r}, {binding.version!r}) is not "
                "registered; the configuration this decision was made under is "
                "gone and no other version stands in for it (D-IMPL-38)"
            ) from missing


def _verify_resolution_claim(
    *,
    record: DecisionReplayRecord,
    control_plane: ControlPlaneProtocol,
    content_address: str,
) -> None:
    """Hold dimension 2's not-applicable claim against the record's own pins.

    ``D-IMPL-264`` D-11 (24.7-09), Dave verbatim: *"Replay verification
    protects against a false `not-applicable` claim. The verification must
    use the pinned historical contract/constraint state, not today's
    configuration."* Called by :func:`replay` immediately after
    :func:`_resolve_bindings` — so every pin is already known to resolve —
    and before any plan or operator is resolved, because a record whose
    dimension 2 misstates its own governance should not be re-executed at
    all.

    **The evidence base, and why it is exactly two classes** (amendment 3,
    B-3 a): *"request-contract pin + applicable constraint pins are the
    evidence that effective-request resolution ran. Do not use 'any class
    declaration pin exists' as the proxy, because the intent check can
    legitimately pin the class declaration before parameter resolution
    occurs."* This is true of the tree, not only of the ruling: in ``src/``
    and ``runtime/`` a :class:`~ccf.products.request.ProductRequestContract`
    or a :class:`~ccf.controlplane.artifacts.PolicyConstraint` reaches a
    record's ``policy_bindings.bindings`` only through
    ``GovernedResolver._applied_bindings(effective)``, which exists only
    once a resolution has run. A ``ProductClassDeclaration`` pin is
    deliberately NOT a trigger — the intent refusal pins the deciding
    declaration beside a ``refused-before-resolution`` marker, and that
    record is telling the truth. So a marker beside no contract or
    constraint pin is legitimate non-applicability (D-09) and replays; a
    marker beside either is a contradiction and is refused.

    **Pinned state only.** Each binding is resolved through
    ``control_plane.resolve(key, version)`` at the version the record wrote,
    never through a latest read, never through the deployment's current
    registration under the same key. The classification is by the artifact
    class that comes back, not by the key's name: keys are deployment
    vocabulary and the engine knows none of it.

    **The legacy sentinel is exempt** (D-12; F-4). A record carrying
    :data:`~ccf.replay.record.NO_REQUEST_RESOLUTION` asserts it predates the
    marker and is left exactly as it was — the same compatibility promise
    the :data:`~ccf.replay.record.NO_GRAPH_QUERIES` exemption makes further
    down :func:`replay`. Dave: *"Do not retroactively declare previously
    valid replay artifacts defective because the SDK acquired a stronger
    contract."* A value that is neither the sentinel nor a marker — the
    :class:`~ccf.products.provenance.EffectiveRequest` that ran — makes no
    not-applicable claim, so there is nothing to verify.
    """
    value = record.policy_bindings.request_resolution
    if value == NO_REQUEST_RESOLUTION:
        # D-12 / F-4: a record carrying the pre-marker sentinel asserts it
        # predates the explicit resolution state and is exempt — that is
        # the sentinel's compatibility promise, exactly as NO_GRAPH_QUERIES
        # below exempts a pre-seam record from the query-pin comparison.
        return
    try:
        marker = ResolutionNotApplicable.model_validate_json(value)
    except ValueError:
        # An EffectiveRequest (complete or partial) — a resolution ran and
        # the record says so. Nothing is claimed not to apply.
        return
    pinned: list[tuple[str, str, str]] = []
    for binding in record.policy_bindings.bindings:
        artifact = control_plane.resolve(binding.key, binding.version)
        if isinstance(artifact, (ProductRequestContract, PolicyConstraint)):
            pinned.append((binding.key, binding.version, type(artifact).__name__))
    if pinned:
        raise ReplayResolutionClaimMismatch(
            content_address=content_address,
            claimed_reason=marker.reason,
            pinned=tuple(pinned),
        )


def _reconstruct_child_contracts(
    *, store: ArtifactStoreProtocol, rows: tuple[ChildResolution, ...]
) -> ChildContractView:
    """Rebuild the parent's child-contract view from RETAINED bytes (`D-IMPL-339`).

    Each admitted row names its child by content address; the deciding fabric
    filed the contract under that address at decision time
    (:meth:`~ccf.products.resolver.GovernedResolver._retain_child_contracts`).
    Resolved here by address alone — no provider call, no latest-version
    lookup, no live object — and held to the address it claims, so a store
    answering different bytes is a divergence rather than a quiet substitution.

    Raises:
        ReplayUnresolvable: a row's contract is not in the store.
        ReplayDivergence: the bytes found do not hash to the row's address.
    """
    contracts: dict[str, ContextProductContract] = {}
    for row in rows:
        address = row.child_content_address
        if address is None:
            raise ReplayUnresolvable(
                f"the admitted child row for {row.required_product_class!r}"
                " carries no content address, so its contract cannot be"
                " resolved (D-IMPL-339)"
            )
        try:
            stored = store.get(content_address=address)
        except (LookupError, OSError) as missing:
            raise ReplayUnresolvable(
                f"the child contract {address!r} consumed for"
                f" {row.required_product_class!r} is not retained in the"
                " store; a composite's replay rebuilds its children from what"
                " was consumed, never from a provider (D-IMPL-339)"
            ) from missing
        try:
            contract = ContextProductContract.model_validate_json(stored)
        except ValueError as not_a_contract:
            # `D-IMPL-344` case 5: bytes at the address that are not a contract
            # are an integrity failure by name, never a substitution and never
            # a validation error escaping from inside the store's answer.
            raise ReplayDivergence(
                f"the bytes retained at {address!r} for"
                f" {row.required_product_class!r} do not rehydrate as a"
                " context product contract; the store answered something at"
                f" the address the row names, and it is not the child"
                f" ({not_a_contract})"
            ) from not_a_contract
        if content_hash(contract) != address:
            raise ReplayDivergence(
                f"the bytes retained at {address!r} rehydrate to a contract"
                f" hashing to {content_hash(contract)!r}; the child the"
                " decision consumed is not the child the store now answers"
            )
        contracts[row.required_product_class] = contract
    return ChildContractView(contracts)


def replay(
    *,
    record_address: str,
    store: ArtifactStoreProtocol,
    reader: GraphReader,
    control_plane: ControlPlaneProtocol,
    environment: ReplayEnvironment,
) -> ReplayOutcome:
    """Reproduce the decision recorded at ``record_address``, exactly.

    Args:
        record_address: Content address of the :class:`DecisionReplayRecord`.
            An address, not a name: names move, addresses do not.
        store: Where the record lives (CLAUDE.md §7.4).
        reader: Live read access to the graph. Scoped to the recorded snapshot
            before anything reads through it.
        control_plane: Where the recorded bindings are resolved at their pinned
            versions.
        environment: The deployment's plan, operators, and product envelope.

    Returns:
        A :class:`ReplayOutcome`, which exists only if every check passed.

    Raises:
        ReplayUnresolvable: the record, a binding, the plan, or an operator
            cannot be resolved at its exact recorded version.
        ReplayGenerationMismatch: the record resolved but was written under
            an earlier generation of the canonical form — it lacks a field the
            running record class declares as a generation boundary
            (``D-IMPL-243`` amendment 1). Raised before any binding is
            resolved and before anything is re-executed.
        ReplayResolutionClaimMismatch: dimension 2 claims no request
            resolution applies while a binding, resolved at its pinned
            version, is a request contract or a policy constraint — the
            evidence that a resolution ran (``D-IMPL-264`` D-11, amendment
            3). Raised after every binding has resolved and before anything
            is re-executed. A record carrying the legacy
            :data:`~ccf.replay.record.NO_REQUEST_RESOLUTION` sentinel is
            exempt (D-12).
        ReplayRecordKindMismatch: the record is a REFUSED decision — its
            dimension 5 carries a refusal block and
            :data:`~ccf.replay.record.NO_PRODUCT_ADDRESS` — or contradicts
            itself about its kind (`D-IMPL-344`). Raised after the record's
            bindings and resolution claim have been verified and before any
            child, plan or operator is resolved; :func:`replay_refusal` is the
            entry point for that record.
        ReplayDivergence: something resolved but did not reproduce.
        ~ccf.replay.snapshots.SnapshotPinUnresolvable: dimension 1 carries a
            real store pin and the reader is not
            :class:`~ccf.graph.protocols.SnapshotPinnable`. A ``LookupError``
            that is NOT a :class:`ReplayError`; it propagates from
            re-execution exactly as raised (``24.5-L-02``).
        ~ccf.replay.snapshots.SnapshotScopeViolation: a read during
            re-execution left the recorded snapshot's scope. Likewise a
            ``LookupError`` outside :class:`ReplayError`, propagated as raised.
    """
    record = _prologue(
        record_address=record_address, store=store, control_plane=control_plane
    )
    _hold_kind(
        record,
        content_address=record_address,
        expected=_RECORD_KIND_SERVED,
        entry_point="replay",
    )
    # `D-IMPL-339`: the view is rebuilt BEFORE the child-dependent plan, from
    # the contracts the deciding fabric retained by address.
    children, _addresses = _children_of(store=store, record=record)
    _hold_retained_questions(store=store, record=record)
    execution, reproduced_snapshot = _re_execute(
        record=record, reader=reader, environment=environment, children=children
    )
    path = record.content_generation_path
    product = environment.rehydrate_product(
        record=record, projection=execution.projection
    )
    _hold_ttl_anchor(
        record=record, product=product, execution=execution, control_plane=control_plane
    )
    reproduced_address = content_hash(product)
    if reproduced_address != path.product_content_address:
        raise ReplayDivergence(
            f"the rehydrated product hashes to {reproduced_address!r}; the "
            f"record names {path.product_content_address!r}"
        )

    return ReplayOutcome(
        record=record,
        product=product,
        record_content_address=record_address,
        product_content_address=reproduced_address,
        graph_snapshot_id=reproduced_snapshot.graph_snapshot_id,
    )


def replay_refusal(
    *,
    record_address: str,
    store: ArtifactStoreProtocol,
    reader: GraphReader,
    control_plane: ControlPlaneProtocol,
    environment: ReplayEnvironment,
) -> RefusalReplayOutcome:
    """Reconstruct the REFUSED decision recorded at ``record_address``.

    `D-IMPL-344`, the other half of :func:`replay`: the same prologue (the
    record at its exact address, the generation check, every binding at its
    pinned version, the resolution claim), the same child reconstruction from
    the contracts the deciding fabric retained by content address — and then
    what the record's own dimension 5 says happened, held positively rather
    than skipped past. Nothing here calls a producer, resolves a "latest"
    anything, or reads a live object from the serve.

    **Refusal before projection** (``plan_id`` is
    :data:`~ccf.replay.record.NO_FABRIC_READ`): the record's no-read and
    no-product claims are each asserted — no steps, no operator plan, no query
    pins, dimension 1 saying nothing was read — and the rehydrated refusal is
    held against the child rows: a child-admission refusal must name a
    declared, required requirement whose row carries a blocking disposition
    and the refusal's own reason. **No plan is resolved, no operator runs, and
    no payload is invented**: the environment is not consulted on this path.

    **Refusal after projection** (a real ``plan_id``): the recorded operator
    path is re-derived exactly as :func:`replay` re-derives it — the plan over
    the reconstructed children, the operators, the execution under the recorded
    snapshot, the step, query-pin and snapshot comparisons — and stops there.
    ``environment.rehydrate_product`` is **never called**: the record names no
    product, the re-executed projection is provisional computation, and the
    outcome type has no member that could carry it. The recorded refusal's
    evidence is then held to that re-execution (its ``operators_invoked`` must
    equal the re-executed set) and to the record's own dimension 5 (its
    ``plan_id`` and ``debt``). **The gate or tolerance verdict itself is not
    recomputed** — the record does not carry the provisional candidate's
    address, and the environment exposes no gate or scorer — so what this
    path reproduces is the recorded verdict over a re-derived operator path
    (the `D-IMPL-344` R-2 boundary, ruled).

    Args:
        record_address: Content address of the :class:`DecisionReplayRecord`.
        store: Where the record and the retained child contracts live.
        reader: Live read access to the graph; consulted only on the
            post-projection path, scoped to the recorded snapshot.
        control_plane: Where the recorded bindings are resolved at their
            pinned versions.
        environment: The deployment's plan and operators; consulted only on
            the post-projection path.

    Returns:
        A :class:`RefusalReplayOutcome`, which exists only if every check passed.

    Raises:
        ReplayUnresolvable: the record, a binding, an admitted child's retained
            contract, the plan or an operator cannot be resolved at its exact
            recorded address or version.
        ReplayGenerationMismatch: as for :func:`replay`.
        ReplayResolutionClaimMismatch: as for :func:`replay`.
        ReplayRecordKindMismatch: the record is a SERVED decision (use
            :func:`replay`), contradicts itself about its kind, carries a
            dimension-5 block that is not a governed refusal, or claims no
            fabric read while naming steps, an operator plan or query pins.
        ReplayDivergence: a retained child's bytes do not hash to the row's
            address; the refusal block does not re-canonicalize to itself; the
            re-execution differs from the recorded steps, pins or snapshot;
            the recorded evidence does not match the re-execution.
    """
    record = _prologue(
        record_address=record_address, store=store, control_plane=control_plane
    )
    _hold_kind(
        record,
        content_address=record_address,
        expected=_RECORD_KIND_REFUSED,
        entry_point="replay_refusal",
    )
    path = record.content_generation_path
    refusal = _rehydrate_refusal_block(
        block=path.assembly_refusal, content_address=record_address
    )
    if path.plan_id == NO_FABRIC_READ:
        _hold_no_read_claims(record=record, content_address=record_address)
        children, addresses = _children_of(store=store, record=record)
        _hold_retained_questions(store=store, record=record)
        del children  # reconstructed and verified; no plan reads them here
        _hold_refusal_to_rows(
            refusal=refusal, path=path, content_address=record_address
        )
        return RefusalReplayOutcome(
            record=record,
            record_content_address=record_address,
            assembly_refusal=path.assembly_refusal,
            child_contract_addresses=addresses,
            graph_snapshot_id=NO_FABRIC_READ,
        )
    children, addresses = _children_of(store=store, record=record)
    _hold_retained_questions(store=store, record=record)
    execution, reproduced_snapshot = _re_execute(
        record=record, reader=reader, environment=environment, children=children
    )
    _hold_refusal_to_execution(
        refusal=refusal, path=path, execution=execution, content_address=record_address
    )
    return RefusalReplayOutcome(
        record=record,
        record_content_address=record_address,
        assembly_refusal=path.assembly_refusal,
        child_contract_addresses=addresses,
        graph_snapshot_id=reproduced_snapshot.graph_snapshot_id,
    )


# --- the shared halves ------------------------------------------------------


def _prologue(
    *,
    record_address: str,
    store: ArtifactStoreProtocol,
    control_plane: ControlPlaneProtocol,
) -> DecisionReplayRecord:
    """Everything both entry points verify before anything is re-executed.

    The record at its exact address; the declared-scope generation check on the
    record's STORED form (`D-IMPL-243` amendment 1 — here and never in
    :func:`resolve_artifact`); every recorded binding at its pinned version;
    and, with every pin known to resolve, the record's not-applicable claim
    held against what those pins are (`D-IMPL-264` D-11). Factored out under
    `D-IMPL-344` so a refused decision runs exactly the checks a served one
    does, stated once.
    """
    record = _resolve_record(store=store, record_address=record_address)
    _refuse_generation_mismatch(
        contract=DecisionReplayRecord,
        stored=_stored_canonical_object(store=store, content_address=record_address),
        content_address=record_address,
    )
    _resolve_bindings(record=record, control_plane=control_plane)
    _verify_resolution_claim(
        record=record, control_plane=control_plane, content_address=record_address
    )
    return record


_RECORD_KIND_SERVED: Final = "served"
_RECORD_KIND_REFUSED: Final = "refused"


def _record_kind(record: DecisionReplayRecord, *, content_address: str) -> str:
    """Which kind of decision the record says it is, from its own dimension 5.

    Both claims are read, and they must agree: a served decision names a
    product and carries no refusal block; a refused one carries the block and
    names no product. One without the other is a record contradicting itself,
    refused by name rather than resolved either way.
    """
    path = record.content_generation_path
    has_refusal = path.assembly_refusal != NO_ASSEMBLY_REFUSAL
    has_product = path.product_content_address != NO_PRODUCT_ADDRESS
    if has_refusal and not has_product:
        return _RECORD_KIND_REFUSED
    if has_product and not has_refusal:
        return _RECORD_KIND_SERVED
    raise ReplayRecordKindMismatch(
        f"the record at {content_address!r} contradicts itself about its kind:"
        f" dimension 5 {'carries' if has_refusal else 'carries no'} refusal"
        f" block and {'names' if has_product else 'names no'} product address;"
        " a decision served or it refused, and the record must say which"
        " (D-IMPL-344)"
    )


def _hold_kind(
    record: DecisionReplayRecord,
    *,
    content_address: str,
    expected: str,
    entry_point: str,
) -> None:
    kind = _record_kind(record, content_address=content_address)
    if kind == expected:
        return
    other = "replay_refusal" if entry_point == "replay" else "replay"
    raise ReplayRecordKindMismatch(
        f"{entry_point}() reconstructs a {expected} decision; the record at"
        f" {content_address!r} is a {kind} one. Use {other}() for it"
        " (D-IMPL-344)"
    )


def _children_of(
    *, store: ArtifactStoreProtocol, record: DecisionReplayRecord
) -> tuple[ChildContractView | None, tuple[str, ...]]:
    """The admitted children, reconstructed from RETAINED bytes, or ``None``.

    ``None`` — rather than an empty view — when the decision admitted no
    child, so a non-composite record keeps taking exactly the plan-resolution
    path it always took. The addresses returned are the rows' own; each has
    resolved and re-hashed by the time this returns.
    """
    path = record.content_generation_path
    admitted_rows = tuple(
        row for row in path.child_resolutions if row.outcome_status == CHILD_ADMITTED
    )
    if not admitted_rows:
        return None, ()
    children = _reconstruct_child_contracts(store=store, rows=admitted_rows)
    addresses = tuple(
        row.child_content_address
        for row in admitted_rows
        if row.child_content_address is not None
    )
    return children, addresses


#: What :func:`_hold_ttl_anchor` did, named — so a test can see the pre-341
#: path was taken by name rather than infer it from an absent exception.
TTL_ANCHOR_NOT_RECORDED: Final = "not-recorded"
TTL_ANCHOR_HELD_DECISION: Final = "held-decision"
TTL_ANCHOR_HELD_EVIDENCE: Final = "held-evidence"


def _hold_ttl_anchor(
    *,
    record: DecisionReplayRecord,
    product: ContextProductContract,
    execution: ExecutionResult,
    control_plane: ControlPlaneProtocol,
) -> str:
    """Re-derive the served product's TTL anchor and hold it to the record (`D-IMPL-341` R-5).

    A record whose dimension 5 carries no ``ttl_anchor_at`` was written before
    the member existed and is decision-anchored by definition of the sentinel:
    the hold is **skipped, by name** (:data:`TTL_ANCHOR_NOT_RECORDED`), every
    other replay check having run. That path does not establish that the old
    expiry implemented evidence anchoring.

    For a ``from_decision`` record the recorded decision instant is the
    anchor, and the rehydrated product must agree with the record. For a
    ``from_entity_freshness`` record the anchor is re-derived over the
    re-executed view under the λ_c table the record pinned — the same
    selection and clock the serve used — and must equal the recorded member.
    Nothing is overwritten, no current configuration is substituted, and no
    producer is called.

    Raises:
        ReplayDivergence: the product and the record disagree, or the
            re-derived anchor differs from the recorded one.
        ReplayUnresolvable: an evidence-anchored record pins no λ_c table.
    """
    path = record.content_generation_path
    recorded = path.ttl_anchor_at
    if recorded is None:
        return TTL_ANCHOR_NOT_RECORDED
    if product.ttl_anchor_at != recorded:
        raise ReplayDivergence(
            f"the rehydrated product's ttl_anchor_at is {product.ttl_anchor_at!r};"
            f" the record names {recorded.isoformat()} (D-IMPL-341)"
        )
    if product.ttl_anchor == FROM_DECISION:
        if recorded != record.recorded_at:
            raise ReplayDivergence(
                f"a decision-anchored record names ttl_anchor_at"
                f" {recorded.isoformat()} and was recorded at"
                f" {record.recorded_at.isoformat()}; the two are one instant"
                " (D-IMPL-308, D-IMPL-341)"
            )
        return TTL_ANCHOR_HELD_DECISION
    table: HalfLifeTable | None = None
    for binding in record.policy_bindings.bindings:
        artifact = control_plane.resolve(binding.key, binding.version)
        if isinstance(artifact, HalfLifeTable):
            table = artifact
            break
    if table is None:
        raise ReplayUnresolvable(
            "an evidence-anchored record pins no λ_c table on dimension 2, so"
            " its anchor cannot be re-derived under the declarations it was"
            " made under; today's table is not substituted (D-IMPL-341 R-5)"
        )
    derived = resolve_ttl_anchor(
        ttl_anchor=FROM_ENTITY_FRESHNESS,
        view=execution.view,
        table=table,
        decided_at=record.recorded_at,
        product_class=product.schema_name,
    )
    if not isinstance(derived, TTLAnchorResolution) or derived.anchor_at != recorded:
        raise ReplayDivergence(
            "the TTL anchor re-derived over the re-executed view is"
            f" {derived.anchor_at.isoformat() if isinstance(derived, TTLAnchorResolution) else 'unresolvable'};"
            f" the record names {recorded.isoformat()} (D-IMPL-341 R-5)"
        )
    return TTL_ANCHOR_HELD_EVIDENCE


def retained_child_question(
    *, store: ArtifactStoreProtocol, row: ChildResolution
) -> ChildQuestionIdentity:
    """The exact question a child row records, from the parent's RETAINED bytes.

    `D-IMPL-342` / `CP14-F-35` — the audit read. Resolves the row's
    ``child_question_ref`` on ``store``, requires the address it resolves to
    to be the row's ``child_question_address``, reads the bytes, holds their
    ``sha256`` to that address, rehydrates them as a
    :class:`~ccf.skills.dispatch.ChildQuestionIdentity` and holds the
    rehydrated contract's content hash to the same address. It calls no
    question mapping, no producer, and reads no configuration: what comes
    back is what was sent, or a named failure.

    Raises:
        ReplayUnresolvable: the row carries no reference — the question is
            **not retained** (the row predates `D-IMPL-342` retention, or was
            written by a resolver that retains none) and is not rebuilt from
            anything else; or the reference or the bytes are not in the store.
        ReplayDivergence: the reference resolves to another address; the bytes
            do not hash to the row's address; the bytes do not rehydrate as a
            question identity; or the rehydrated contract does not hash back
            to the address.
    """
    reference = row.child_question_ref
    address = row.child_question_address
    if reference is None:
        raise ReplayUnresolvable(
            f"the child row for {row.required_product_class!r} carries no"
            " retained-question reference: the historical question is not"
            " retained — the row predates D-IMPL-342 retention or was written"
            " by a resolver that retains no question — and it is not rebuilt"
            " from the mapping or the producer (D-IMPL-342 / CP14-F-35)"
        )
    if address is None:  # pragma: no cover - refused at row construction
        raise ReplayDivergence(
            f"the child row for {row.required_product_class!r} references a"
            " retained question but records no question address"
        )
    try:
        resolved = store.resolve_uri(uri=reference)
    except (LookupError, OSError, ValueError) as missing:
        raise ReplayUnresolvable(
            f"the retained-question reference {reference!r} for"
            f" {row.required_product_class!r} does not resolve on this store"
            f" ({missing}); the question is not retained here (D-IMPL-342)"
        ) from missing
    if resolved != address:
        raise ReplayDivergence(
            f"the retained-question reference {reference!r} for"
            f" {row.required_product_class!r} resolves to {resolved!r} but the"
            f" row records question identity {address!r}; the reference names"
            " a different question (D-IMPL-342)"
        )
    try:
        stored = store.get(content_address=address)
    except (LookupError, OSError) as missing:
        raise ReplayUnresolvable(
            f"the question bytes {address!r} sent for"
            f" {row.required_product_class!r} are not retained in the store;"
            " the historical question is resolved from the parent's store and"
            " from nowhere else (D-IMPL-342 / CP14-F-35)"
        ) from missing
    digest = hashlib.sha256(stored).hexdigest()
    if digest != address:
        raise ReplayDivergence(
            f"the bytes retained at {address!r} for"
            f" {row.required_product_class!r} hash to {digest!r}; the store"
            " answered different bytes at the address the row names"
            " (D-IMPL-342)"
        )
    try:
        question = ChildQuestionIdentity.model_validate_json(stored)
    except ValueError as not_a_question:
        raise ReplayDivergence(
            f"the bytes retained at {address!r} for"
            f" {row.required_product_class!r} do not rehydrate as a child"
            f" question identity ({not_a_question})"
        ) from not_a_question
    rehashed = content_hash(question)
    if rehashed != address:
        raise ReplayDivergence(
            f"the question retained at {address!r} for"
            f" {row.required_product_class!r} re-canonicalizes to {rehashed!r};"
            " the retained bytes are not the identity's canonical form"
            " (D-IMPL-342)"
        )
    return question


def _hold_retained_questions(
    *, store: ArtifactStoreProtocol, record: DecisionReplayRecord
) -> None:
    """Hold every row that references a retained question to its bytes.

    `D-IMPL-342` / `CP14-F-35`. Every row carrying a ``child_question_ref`` —
    admitted, refused, rejected or unreachable — resolves and re-hashes
    through :func:`retained_child_question`. A row carrying none is left
    unheld **by name**: a record written before retention existed replays as
    it did, and a resolver that retains no question is not silently credited
    with having done so — the three-state reading (held / diverged / not
    retained), never a don't-know collapsed into a pass.
    """
    for row in record.content_generation_path.child_resolutions:
        if row.child_question_ref is not None:
            retained_child_question(store=store, row=row)


def _re_execute(
    *,
    record: DecisionReplayRecord,
    reader: GraphReader,
    environment: ReplayEnvironment,
    children: ChildContractView | None,
) -> tuple[ExecutionResult, ContextFabricSnapshot]:
    """Re-derive the recorded operator path and hold it to the record.

    The plan (over its children when the decision composed any), the operators
    at their recorded keys, the execution under the recorded snapshot and cap
    and seeds, then the three comparisons — step sequence, query pins, graph
    substate and store pin. Shared by :func:`replay` and the post-projection
    half of :func:`replay_refusal`; **stops before any product is rehydrated**,
    which is what lets the refused path reuse it.
    """
    path = record.content_generation_path
    if children is not None:
        if not isinstance(environment, CompositeReplayEnvironment):
            raise ReplayUnresolvable(
                f"this decision composed {len(children)} admitted child"
                " product(s) and the environment does not implement"
                " `resolve_composite_plan`; a child-dependent plan cannot be"
                " rebuilt without the children it read (D-IMPL-339)"
            )
        try:
            plan = environment.resolve_composite_plan(
                plan_id=path.plan_id, children=children
            )
        except LookupError as missing:
            raise ReplayUnresolvable(
                f"projection plan {path.plan_id!r} cannot be resolved over its"
                " children; the interpretation this decision used is not"
                " available"
            ) from missing
    else:
        try:
            plan = environment.resolve_plan(plan_id=path.plan_id)
        except LookupError as missing:
            raise ReplayUnresolvable(
                f"projection plan {path.plan_id!r} cannot be resolved; the "
                "interpretation this decision used is not available"
            ) from missing
    try:
        operators = environment.resolve_operators(operator_keys=path.operator_plan)
    except LookupError as missing:
        raise ReplayUnresolvable(
            f"the operators recorded for plan {path.plan_id!r} cannot be "
            "resolved as they were at decision time"
        ) from missing

    snapshot = record.context_fabric_snapshot
    execution = ProjectionEngine(
        reader=SnapshotReader(reader=reader, snapshot=snapshot),
        registry=operators,
        # The recorded dimension-2 cap, not the deployment's current one
        # (D-10): the pushed/in-process split depends on this value, so a
        # replay under a different cap would issue a different question
        # sequence — a re-computation wearing the decision's identifier.
        survivor_cap=record.policy_bindings.survivor_cap,
    ).execute(
        plan=plan,
        perspective=Perspective(
            principal_id=record.perspective_conditioning.principal_id,
            role=record.perspective_conditioning.role,
        ),
        tenant_id=snapshot.tenant_id,
        temporal_boundary=snapshot.temporal_boundary,
        # The recorded question's anchor, not the deployment's current one
        # (D-IMPL-111): the walk starting points are compiled into the query,
        # so a replay under different seeds would ask a different question
        # wearing the decision's identifier — the ``survivor_cap`` argument
        # one line up, applied to the other half of what shapes a query. A
        # record carrying no request yields ``None`` and replays exactly as
        # it did before the ruling.
        seeds=request_seeds(path.request),
    )

    if execution.steps != path.steps:
        raise ReplayDivergence(
            "the re-executed step sequence differs from the recorded one "
            f"(recorded {[step.model_dump() for step in path.steps]}, "
            f"replayed {[step.model_dump() for step in execution.steps]}); a "
            "differing parameter hash means the operators are no longer the "
            "ones that ran"
        )

    if path.graph_query_sequence != NO_GRAPH_QUERIES:
        # D-11: recompute the per-round-trip pins from the re-execution and
        # compare, in order. A record carrying the pre-seam sentinel asserts
        # it predates the query seam and is exempt — that is the sentinel's
        # compatibility promise (D-IMPL-89), and the snapshot and product
        # checks below still bind such a record to the same answer.
        replayed_pins = tuple(
            content_hash(query) for query in execution.executed_queries
        )
        if replayed_pins != path.graph_query_sequence:
            raise ReplayDivergence(
                "the re-executed query sequence differs from the recorded "
                f"pins (recorded {list(path.graph_query_sequence)!r}, "
                f"replayed {list(replayed_pins)!r}); the questions asked of "
                "the substrate are no longer the questions the decision "
                "asked (D-11, `GQ-20`)"
            )

    reproduced_snapshot = snapshot_of_execution(
        execution=execution,
        tenant_id=snapshot.tenant_id,
        temporal_boundary=snapshot.temporal_boundary,
    )
    if reproduced_snapshot.graph_snapshot_id != snapshot.graph_snapshot_id:
        raise ReplayDivergence(
            "the re-executed graph substate does not match the recorded "
            f"snapshot {snapshot.graph_snapshot_id!r}; the state the decision "
            "was made against is not the state the graph now re-renders"
        )
    if reproduced_snapshot.store_snapshot_pin != snapshot.store_snapshot_pin:
        # 24.5-L-02 (D-IMPL-240): the pin is outside the id derivation, so
        # it is compared on its own. A re-execution that read under any
        # other store state than the recorded one — the head, or a pin that
        # moved between record and rehydration — is a different decision.
        recorded_pin = snapshot.store_snapshot_pin
        replayed_pin = reproduced_snapshot.store_snapshot_pin
        raise ReplayDivergence(
            "the re-execution read under store pin "
            f"{replayed_pin.substrate}:{replayed_pin.pin!r}; the record pins "
            f"{recorded_pin.substrate}:{recorded_pin.pin!r} — the state the "
            "decision was made against is not the state it was replayed "
            "against (24.5-L-02, CLAUDE.md §7.4)"
        )
    return execution, reproduced_snapshot


# --- the refused half's own checks -------------------------------------------


#: The envelope kind a composite's child-admission refusal crosses in
#: (:data:`ccf.products.refusal.REFUSAL_KINDS`). Quoted here rather than
#: imported so this module's import order stays what it is; pinned by the
#: `D-IMPL-344` controls against the live vocabulary.
_COMPOSITE_CHILD_REFUSAL_KIND: Final = "composite-child-refusal"

#: The one non-blocking absence a child row can carry (`D-IMPL-336` F1).
_OPTIONAL_ABSENT: Final = "optional-absent"

#: The three child-refusal reasons whose scope is not a child row
#: (:data:`ccf.products.composite.CHILD_REFUSAL_REASONS`; pinned by the
#: `D-IMPL-344` controls against the live vocabulary).
_UNDECLARED_OUTCOME: Final = "undeclared-outcome"
_REQUIREMENT_MISMATCH: Final = "requirement-mismatch"
_NO_PRODUCING_SKILL: Final = "no-producing-skill"


def _rehydrate_refusal_block(*, block: str, content_address: str) -> CCFContract:
    """Dimension 5's block as the governed refusal it serializes, re-verified.

    The two shapes :func:`~ccf.replay.record.mint_assembly_refusal` admits —
    a :class:`~ccf.products.refusal.RefusalEnvelope`, or the legacy
    :class:`~ccf.products.request.ProductRequestViolation` D-60 shipped — tried
    in that order, exactly as the builder tries them at write. The value is
    then re-canonicalized and held to the stored bytes, so a block that parses
    but was not minted by the builder's own arithmetic is a divergence rather
    than a refusal read off a record that never carried it.
    """
    # Function-local for the cycle `ccf.replay.record` documents at
    # `_refusal_names`: `ccf.products.refusal` reaches this package first.
    from ccf.products.refusal import RefusalEnvelope

    refusal: CCFContract
    try:
        refusal = RefusalEnvelope.model_validate_json(block)
    except ValueError as not_an_envelope:
        try:
            refusal = ProductRequestViolation.model_validate_json(block)
        except ValueError as invalid:
            raise ReplayRecordKindMismatch(
                f"the record at {content_address!r} carries a dimension-5"
                " refusal block that is neither a `RefusalEnvelope` nor a"
                f" `ProductRequestViolation` (as an envelope: {not_an_envelope};"
                f" as a violation: {invalid}); it is not a governed refusal"
                " this engine can reconstruct (D-IMPL-344)"
            ) from invalid
    if canonical_bytes(refusal).decode("utf-8") != block:
        raise ReplayDivergence(
            f"the refusal block recorded at {content_address!r} does not"
            " re-canonicalize to itself; the bytes on dimension 5 are not the"
            " builder's own minting of the refusal they parse as (D-IMPL-344)"
        )
    return refusal


def _hold_no_read_claims(
    *, record: DecisionReplayRecord, content_address: str
) -> None:
    """A refusal before projection says nothing was read or run; check each claim.

    Asserted positively rather than inferred from ``plan_id`` alone: a record
    naming :data:`~ccf.replay.record.NO_FABRIC_READ` beside a step sequence,
    an operator plan, query pins or a real dimension-1 watermark has
    contradicted itself, and reconstructing "nothing happened" over it would
    be a confident answer about a record that says two things.
    """
    path = record.content_generation_path
    claims = (
        ("steps", path.steps == ()),
        ("operator_plan", path.operator_plan == ()),
        ("graph_query_sequence", path.graph_query_sequence == NO_GRAPH_QUERIES),
        (
            "context_fabric_snapshot.store_watermark",
            record.context_fabric_snapshot.store_watermark == NO_FABRIC_READ,
        ),
    )
    contradicted = [name for name, holds in claims if not holds]
    if contradicted:
        raise ReplayRecordKindMismatch(
            f"the record at {content_address!r} names plan"
            f" {NO_FABRIC_READ!r} — a refusal before any projection — while"
            f" {contradicted!r} say a fabric read or an execution happened;"
            " the record contradicts its own no-read claim (D-IMPL-344)"
        )


def _hold_refusal_to_rows(
    *,
    refusal: CCFContract,
    path: ContentGenerationPath,
    content_address: str,
) -> None:
    """A child-admission refusal must agree with the determination that occurred.

    Held to **the evidence and scope the record carries**, never to the
    assumption that every composite refusal is a required-slot failure. The
    refusal's ``product_class`` and ``reason`` are canonical-bytes strings on
    the envelope's ``fields`` (`D-IMPL-253`). The shapes
    :func:`~ccf.products.composite.resolve_child_outcomes` and the resolver's
    composite branch can record before projection, each with its own check:

    * **``undeclared-outcome``** — the resolver produced an outcome for a class
      the composite does not require. The named class must have **no** row:
      a row for it would say the class was declared after all.
    * **``requirement-mismatch`` with no rows** — one class declared twice. The
      walk returns before producing any row. The same token is also the
      re-binding failure of an admitted child walked under another slot or
      invocation, which DOES write a row; with rows present it is held as a
      child-row refusal below.
    * **A parent-scope refusal** — the deployment wired no child resolver, and
      the resolver records ``no-producing-skill`` against the composite's OWN
      class with no rows (nothing was attempted, so nothing is invented). The
      named class must equal the recorded request's class and the rows must be
      empty; a record carrying no request cannot evidence that scope and is
      refused by name rather than assumed.
    * **A child-row refusal** — every other reason. The named class must have
      a row; that row must carry a blocking disposition, which is anything in
      the closed vocabulary except ``admitted`` and the declared optional
      absence; and the refusal's reason must be the row's, as either its
      ``outcome_status`` (a requirement nothing produced) or its
      ``refusal_ref`` (a child dispatched and then refused at admission).
      **``required`` is not a condition**: an optional child that was invoked
      and refused blocks the composition by the `D-IMPL-336` F1 rule —
      optional means optional *absence*, not optional governance — and its
      row records ``required=False`` exactly as the determination did.

    A refusal of any other kind before projection — a request-conformity
    verdict, a constraint refusal — names no child and is held to nothing
    here; its admitted rows, if any, were verified by :func:`_children_of`.
    """
    kind = getattr(refusal, "kind", None)
    if kind != _COMPOSITE_CHILD_REFUSAL_KIND:
        return
    fields: Mapping[str, str] = refusal.fields  # type: ignore[attr-defined]
    try:
        named = json.loads(fields["product_class"])
        reason = json.loads(fields["reason"])
    except (KeyError, ValueError) as malformed:
        raise ReplayRecordKindMismatch(
            f"the child-admission refusal recorded at {content_address!r}"
            " names no product_class and reason on its fields; the refusal"
            " cannot be held to the determination (D-IMPL-344)"
        ) from malformed
    rows = path.child_resolutions
    by_class = {row.required_product_class: row for row in rows}

    if reason == _UNDECLARED_OUTCOME:
        if named in by_class:
            raise ReplayRecordKindMismatch(
                f"the refusal recorded at {content_address!r} says {named!r}"
                " was produced without being required, while a child row"
                " declares that very class (D-IMPL-344)"
            )
        return
    if reason == _REQUIREMENT_MISMATCH and not rows:
        # A duplicate declaration: the walk returned before any row.
        return

    row = by_class.get(named)
    if row is None:
        own = path.request.schema_name if path.request is not None else None
        if rows == () and reason == _NO_PRODUCING_SKILL and own is not None and named == own:
            # The parent-scope refusal: no child resolver wired, recorded
            # against the composite's own class, nothing attempted.
            return
        raise ReplayRecordKindMismatch(
            f"the refusal recorded at {content_address!r} is about"
            f" {named!r} ({reason!r}), which no child row of the record"
            " declares and which is not the parent-scope refusal the resolver"
            " records against its own class with no rows"
            + (" (the record carries no request to establish that scope)" if own is None else f" (the record's own class is {own!r})")
            + " (D-IMPL-344)"
        )
    if row.outcome_status in (CHILD_ADMITTED, _OPTIONAL_ABSENT):
        raise ReplayRecordKindMismatch(
            f"the refusal recorded at {content_address!r} blocks on"
            f" {named!r}, whose row reads {row.outcome_status!r}; a child the"
            " record says was admitted (or honestly absent) cannot be the one"
            " it refused on (D-IMPL-344)"
        )
    if reason not in (row.outcome_status, row.refusal_ref):
        raise ReplayDivergence(
            f"the refusal recorded at {content_address!r} gives reason"
            f" {reason!r} for {named!r}; its row carries outcome"
            f" {row.outcome_status!r} and refusal_ref {row.refusal_ref!r} —"
            " the refusal and the disposition it records disagree"
            " (D-IMPL-344)"
        )


def _hold_refusal_to_execution(
    *,
    refusal: CCFContract,
    path: ContentGenerationPath,
    execution: ExecutionResult,
    content_address: str,
) -> None:
    """A refusal after projection carries evidence; hold it to the re-execution.

    ``operators_invoked`` is the re-derived check — what the engine just ran
    against what the refusal said ran. ``plan_id`` and ``debt`` are integrity
    checks between the refusal and the record's own dimension 5 (the builder
    writes both from the same values, so they catch an edited record rather
    than a drifted deployment). What is NOT checked here, by ruling
    (`D-IMPL-344` R-2): the gate or tolerance verdict itself.
    """
    evidence = getattr(refusal, "evidence", None)
    if evidence is None:
        raise ReplayRecordKindMismatch(
            f"the record at {content_address!r} names plan {path.plan_id!r}"
            " — a refusal after projection — while its refusal carries no"
            " evidence of that projection; the record contradicts itself"
            " (D-IMPL-344)"
        )
    if evidence.plan_id != path.plan_id:
        raise ReplayDivergence(
            f"the refusal recorded at {content_address!r} evidences plan"
            f" {evidence.plan_id!r}; dimension 5 names {path.plan_id!r}"
            " (D-IMPL-344)"
        )
    if evidence.operators_invoked != execution.operators_invoked:
        raise ReplayDivergence(
            f"the refusal recorded at {content_address!r} evidences operators"
            f" {sorted(evidence.operators_invoked)!r}; the re-execution invoked"
            f" {sorted(execution.operators_invoked)!r} (D-IMPL-344)"
        )
    if evidence.debt != path.debt:
        raise ReplayDivergence(
            f"the refusal recorded at {content_address!r} evidences debt"
            f" {evidence.debt!r}; dimension 5 records {path.debt!r}"
            " (D-IMPL-344)"
        )
