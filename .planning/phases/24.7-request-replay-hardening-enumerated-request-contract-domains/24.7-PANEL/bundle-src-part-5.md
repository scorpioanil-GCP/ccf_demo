# 24.7 close-time panel — bundle-src-part-5.md

Subject: the SHIPPED tree of `phase-24.7` at `ad8dc5a9` (src/ and runtime/), diff base `6a019322`.
Read `prompt.md` for the instruction and `known-findings.md` for what NOT to re-derive.
Feed this file via STDIN, never as an argv string. Quote the line below verbatim in your review;
a review that does not quote it is recorded as a failed reviewer, not a reviewer.

```
READ-PROOF bundle-src-part-5.md: 365439472dbbc610
```

Subjects in this part (1): `src/ccf/replay/engine.py`


<!-- mid-payload read-proof -->
```
READ-PROOF bundle-src-part-5.md: 365439472dbbc610
```

## src/ccf/replay/engine.py — FULL TEXT at ad8dc5a9

```python
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
from ccf.contracts.canonical import content_hash, generation_mismatch
from ccf.controlplane.artifacts import PolicyConstraint
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
from ccf.graph.protocols import GraphReader
from ccf.products.contract import ContextProductContract
from ccf.products.request import ProductRequestContract, request_seeds
from ccf.projection.engine import OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
from ccf.replay.record import (
    NO_GRAPH_QUERIES,
    NO_REQUEST_RESOLUTION,
    DecisionReplayRecord,
    ResolutionNotApplicable,
)
from ccf.replay.snapshots import SnapshotReader, snapshot_of_execution

__ccf_mode__ = "algorithmic"

__all__ = [
    "ReplayDivergence",
    "ReplayEnvironment",
    "ReplayError",
    "ReplayGenerationMismatch",
    "ReplayOutcome",
    "ReplayResolutionClaimMismatch",
    "ReplayUnresolvable",
    "replay",
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
    record = _resolve_record(store=store, record_address=record_address)
    # D-IMPL-243 amendment 1: the declared-scope generation check, on the
    # record's STORED form, here and never in resolve_artifact. A record that
    # lacks a `False`-marked field is refused by name now; a record that lacks
    # only `True`-marked or unmarked fields continues exactly as it always has.
    _refuse_generation_mismatch(
        contract=DecisionReplayRecord,
        stored=_stored_canonical_object(store=store, content_address=record_address),
        content_address=record_address,
    )
    _resolve_bindings(record=record, control_plane=control_plane)
    # D-IMPL-264 D-11 (24.7-09): with every pin known to resolve, hold the
    # record's not-applicable claim against what those pins ARE at their
    # recorded versions — before any plan or operator is resolved.
    _verify_resolution_claim(
        record=record, control_plane=control_plane, content_address=record_address
    )

    path = record.content_generation_path
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

    product = environment.rehydrate_product(
        record=record, projection=execution.projection
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
```


---
End of bundle-src-part-5.md. Read-proof, again:
```
READ-PROOF bundle-src-part-5.md: 365439472dbbc610
```
