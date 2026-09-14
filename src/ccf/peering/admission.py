"""The Control Plane admission gate every inbound Peering product passes.

SDK-defined extension (CLAUDE.md §7.2), attaching to whitepaper §8.3 Pattern 4
and to the Control Plane of §7.8. CLAUDE.md §7.2 states the commitment this
module *is*: **an inbound Context Product is not admissible to L3 until the
consuming Control Plane validates its Policy bindings.** D-IMPL-16 rules that
this happens for *every* inbound product, with no fast path for a high-trust
peer — a trust tier narrows or widens what a peer may assert, never whether it
is checked.

**One gate, uniformly over every Peering (D-12; ``D-IMPL-59`` part 4).** A
*Peering* is a governed, peer-symmetric context exchange between two fabrics
that each have a Control Plane of their own, so what crosses must be merged
under the receiver's policy; A2A is this seam's reference transport (part 2),
not the category. The check therefore does not live inside a
:class:`~ccf.peering.protocol.PeeringProtocol` implementation. Two transports
ship this phase and more may follow; a per-transport check would state the rule
once per wire and let a later wire state it differently, or not at all. So the
rule sits above all of them, and a transport is handed no way to reach past it:
**a Peering declares trust inputs and never the verdict — core runs this gate
uniformly over every Peering and constructs the admitted value L2 accepts.**
That is the same structural device as the harness adapter's inability to
acquire a write handle (CLAUDE.md §7.3), applied at a second boundary, and it is
why single-writer survives federation.

MCP is deliberately outside this seam (part 3): it is asymmetric and originates
lineage rather than merging a peer's, and stays its own surface per
CLAUDE.md §7.1. Nothing in this package imports it.

The six checks, **in this order, and the order is load-bearing**:

1. **Size ceiling — the only check that runs before canonicalization.** The
   payload member is measured as received, so an oversized or
   decompression-bomb payload is refused for the cost of one length rather than
   the cost of decoding it (T-06-41). The ceiling is a Control Plane value with
   no SDK default (D-IMPL-38): see :class:`InboundPayloadCeiling`.
2. **Signature verification.** The protected header's ``kid`` selects a key
   *from the peer's own trust-policy entry*, so the key that proves the
   signature is one that peer was entitled to sign with. A header naming a key
   belonging to a different peer therefore fails here, not later (T-06-37).
3. **Contract validation.** The verified canonical bytes are parsed and
   validated as a :class:`~ccf.products.contract.ContextProductContract` with
   ``extra=forbid``. **CCF's own validation is the typed boundary — never the
   transport's types** (research Pitfall 5): a protobuf or JSON-RPC message has
   no closed-world semantics and preserves unknown fields silently, so trusting
   it would end the fabric's contract discipline at the process edge
   (T-06-42).
4. **Policy-binding verification.** The asserted producer hash (an
   authenticated protected-header claim — see
   :data:`PRODUCER_ASSERTION_HEADER`), the product's ``schema_name``, and its
   ``policy_bundle_versions`` must all lie inside what *this* peer, for *this*
   tenant, is permitted to assert (T-06-39).
5. **The federated contract gates.**
   :func:`ccf.products.gates.run_federated_gates` is wired in rather than
   reimplemented, so a validly signed but stale product is refused by the same
   INV-CH7-48 mechanism a locally assembled one is (T-06-40), and the declared
   operator plan is checked for *attributability* against the bytes whose
   signature verified. See
   :meth:`PeeringAdmissionGate._run_federated_gates` for what that call does and
   does not establish across a trust boundary.
6. **Lineage integrity, and where the union actually lives.** The inbound
   lineage *extends* the consumer's by set-union: producer entries survive,
   consumer entries survive, and the producer's operator plan, graph snapshot
   and policy version are preserved (CLAUDE.md §7.2; D-14).
   :func:`union_lineage` is the law, and ``tests/properties/test_lineage_union.py``
   is what pins the computation (T-06-44).

   Until Dave's ``D-IMPL-58`` ruling of 2026-07-27 that was *all* that held, and
   it was not enough: the union was computed into :attr:`AdmittedProduct.lineage`
   and **nothing read it** — :meth:`~ccf.assembly.worker.AssemblyWorker.
   ingest_admitted` reads ``admitted.product`` and never ``admitted.lineage``,
   and stamps the *consumer's* policy bundle version — so a "lineage continuity"
   claim was a property of a wrapper L2 discards. That was blocking finding B2.
   Under the ruling's **reading (d)** the union is persisted at the crossing as
   an immutable :class:`AdmissionRecord` (:func:`PeeringAdmissionGate.
   _persist_admission_record`), and ``ccf.contracts.claims.LineageEntry`` is
   untouched. Lineage continuity is thereby located where CLAUDE.md §7.2
   actually describes it — as a property of the **Peering** admission boundary
   (``D-IMPL-59``) — rather than forced into an L-axis structure never shaped to
   hold it.

   **What the audit log does and does not carry.** ``AuditLog.append`` takes
   scalars only; there is no payload field and an ``AuditEvent`` cannot hold a
   ``ProductLineage``. So the audit plane answers *was this admitted, by whom,
   when* — a verdict — and the ``AdmissionRecord`` answers *what was admitted*.
   The verdict carries the ``artifact_class`` / ``key`` / ``version`` triple
   naming the record; neither structure pretends to be the other. ``D-IMPL-58``'s
   correction paragraph records that reading (d) was first ruled on the false
   premise that admission "already reaches replay" through the audit log, which
   it never did.

**Single-writer survives this, and the survival is structural.** The gate now
writes, but not to the graph: the ArtifactStore is a persistence substrate
reached through mechanism (CLAUDE.md §7.4), never a second writer to L3
(T-06-101). The gate is handed an :class:`~ccf.artifacts.protocol.
ArtifactStoreProtocol` and nothing that can reach L3 — this module imports
nothing from :mod:`ccf.graph` — and an admitted product still enters the graph
only via :meth:`~ccf.assembly.worker.AssemblyWorker.ingest_admitted`, through
L2, exactly as before. Admission is still not a write to the graph; what it
writes is the record of its own verdict's subject.

**Refusals are returned values, and every one is audited.** The base is
:class:`~ccf.products.gates.GateRefusal` itself — the same discipline, not a
parallel one — and each subclass carries **both sides of its mismatch** so a
caller never re-derives what it was already told. A refusal returned as data
cannot be swallowed by a bare ``except`` and leaves the caller holding no
product to proceed with. Every verdict, admission and refusal alike, is
appended to the Control Plane audit log, refusals with ``resolved=False``
(T-05-16, T-05-04 precedent; T-06-43): the audit plane is only credible if it
records what it turned away.

**The admitted-product type, and why it carries a token.**
:class:`AdmittedProduct` is the gate's success output and is constructible only
here. That is a real choice with a live counter-precedent: Dave's I.2 D-12
ruling *removed* exactly this token from
:class:`~ccf.agents.agent.Agent` in favour of a lint, so a construction token is
not automatic house style and its use has to be argued. The argument here is
that the two cases differ in origin. An ``Agent`` is constructed by an
in-process factory the SDK itself controls, so the question the token answered
was one a lint over the SDK's own code could answer instead. An
``AdmittedProduct`` describes something that arrived from an **untrusted remote
peer**, and its constructibility *is* the trust boundary: the property that
must hold is not "SDK code went through the factory" but "nothing outside this
module can produce the value L2 accepts, however it got here". A lint cannot
make that statement about code the SDK does not ship — a deployment's own
transport, or a third-party wire implementation. So the token stays, and the
claim stays the honest one (D-21): no unforced path exists, and every forced
path fails at construction.

**D-20: this module adds no ``ControlPlaneStateStore`` consumer.** Nothing here
is mutable-until-terminal Control Plane state. The trust policy and the size
ceiling are versioned artifacts resolved by pinned ``(key, version)``, keys are
an :class:`~ccf.peering.identity.IdentityProvider` concern, and peers are resolved
per call. Closing the audit-bearing-write-path gap D-20 names is a prerequisite
this plan deliberately does not incur (T-06-45).

This module holds no ceiling, no peer, no schema name and no regime — every one
of those is the deployment's statement (CLAUDE.md §11, CINV-01). Algorithmic
module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast
from types import MappingProxyType

from pydantic import Field, ValidationError, field_validator

from ccf.artifacts.protocol import (
    ArtifactRef,
    ArtifactStoreError,
    ArtifactStoreProtocol,
)
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass, validate_semver
from ccf.controlplane.audit import AuditAction, AuditLog
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.peering.identity import IdentityError, IdentityProvider
from ccf.peering.protocol import InboundProduct, PeerRef
from ccf.peering.trust_policy import (
    PEERING_TRUST_POLICY,
    PeeringTrustPolicy,
    PeerTrustGrant,
    TrustPolicyViolation,
    trust_policy_key,
)
from ccf.products.contract import (
    ContextProductContract,
    ProductLineage,
    RegisteredProductClass,
)
from ccf.products.gates import GateRefusal, run_federated_gates

__ccf_mode__ = "algorithmic"

__all__ = [
    "ADMISSION_RECORD",
    "GATE_CONTRACT",
    "GATE_LINEAGE_CONTINUITY",
    "GATE_PAYLOAD_CEILING",
    "GATE_POLICY_BINDING",
    "GATE_SIGNATURE",
    "INBOUND_PAYLOAD_CEILING",
    "PRODUCER_ASSERTION_HEADER",
    "PeeringAdmissionGate",
    "AdmissionBypassError",
    "AdmissionNotRecorded",
    "AdmissionRecord",
    "AdmissionRefusal",
    "AdmittedProduct",
    "verify_admission_provenance",
    "ContractRefusal",
    "InboundPayloadCeiling",
    "LineageContinuityRefusal",
    "PayloadTooLargeRefusal",
    "PolicyBindingRefusal",
    "SignatureRefusal",
    "payload_ceiling_key",
    "union_lineage",
]

#: Names of the six checks, in execution order. Strings rather than an enum for
#: the same reason :mod:`ccf.products.gates` uses strings: the value lands in a
#: refusal an operator reads in a log. Named for the *seam* rather than for one
#: of its transports (``D-IMPL-59`` part 4): one gate runs over every Peering, so
#: a refusal an operator reads must not suggest a per-protocol check.
GATE_PAYLOAD_CEILING = "peering-payload-ceiling"
GATE_SIGNATURE = "peering-signature"
GATE_CONTRACT = "peering-contract"
GATE_POLICY_BINDING = "peering-policy-binding"
GATE_LINEAGE_CONTINUITY = "peering-lineage-continuity"

#: The protected-header member an emitter states its producing agent under.
#: In the *protected* header, so it is covered by the signature: a producer
#: claim carried outside the signature could be rewritten in flight, and a
#: governance check against a rewritable claim checks nothing. This is a
#: mechanism constant (like JOSE's own ``typ``), not a deployment value — no
#: producer hash appears anywhere in this module.
PRODUCER_ASSERTION_HEADER = "ccf_producer"


class InboundPayloadCeiling(CCFContract):
    """The largest inbound payload a tenant will decode, as an artifact.

    A typed, versioned Control Plane artifact on the
    :class:`~ccf.products.contract.MaxTTL` precedent, for the same three
    reasons: registering the wrong thing under the ceiling key is a detectable
    error, the ceiling carries its own semver lane, and the *number* stays out
    of code. **The SDK ships no default** (D-IMPL-38) — how large a legitimate
    product is in a given federation is something only that deployment knows,
    and a ceiling nobody chose is either a denial-of-service hole or an outage.

    Attributes:
        semver: This artifact's own lane. No default, so a ceiling whose author
            never stated its lane cannot be constructed.
        max_payload_bytes: The ceiling, measured on the received payload member
            before anything decodes it. Must be positive: a zero ceiling admits
            nothing and is far more likely a mistake than a policy.
    """

    semver: str
    max_payload_bytes: int = Field(gt=0)

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)


#: The artifact class the registry validates inbound ceilings against.
INBOUND_PAYLOAD_CEILING = ArtifactClass(
    class_id="ccf.peering-inbound-payload-ceiling", contract=InboundPayloadCeiling
)


def payload_ceiling_key(*, tenant_id: str) -> str:
    """Return the Control Plane key one tenant's inbound ceiling registers under.

    A derivation rather than a table, on the
    :func:`~ccf.peering.trust_policy.trust_policy_key` precedent: the SDK supplies
    the shape so two components cannot disagree about where the value lives,
    and supplies no tenant, so it holds no deployment's vocabulary (CINV-01).
    """
    return f"{INBOUND_PAYLOAD_CEILING.class_id}/{tenant_id}"


class AdmissionRefusal(GateRefusal):
    """Base of the admission refusals — values, never exceptions.

    Deriving from :class:`~ccf.products.gates.GateRefusal` rather than
    paralleling it is deliberate: an inbound product meets the fabric's gate
    discipline, not a second one that happens to look similar. A caller
    inspecting ``gate`` and ``detail`` reads a Peering refusal exactly as it reads
    a TTL refusal, and :meth:`PeeringAdmissionGate.admit` can return either without
    the caller learning a new shape.

    Attributes:
        tenant_id: The tenant whose Control Plane refused.
        peer_id: The peer whose product was refused, as the transport observed
            it. Carried on the base because every refusal is *about* a peer,
            and an audit reader should never have to correlate to learn which.
    """

    tenant_id: str
    peer_id: str


class PayloadTooLargeRefusal(AdmissionRefusal):
    """Check 1: the payload exceeded the tenant's ceiling (T-06-41).

    Both sides are carried so an operator can see whether the ceiling is too
    low or the peer is misbehaving, without resolving the artifact again.
    """

    observed_bytes: int
    ceiling_bytes: int


class SignatureRefusal(AdmissionRefusal):
    """Check 2: the envelope did not verify under this peer's keys (T-06-37).

    Carries what the header *claimed* and what the peer was *permitted*, which
    is the pair that distinguishes a rotation the trust policy has not caught
    up with from a product signed by somebody else entirely.
    """

    declared_key_id: str | None
    permitted_key_ids: frozenset[str]
    failure: str


class ContractRefusal(AdmissionRefusal):
    """Check 3 (or 5): the bytes are not a product this fabric can accept.

    Covers a payload that is not a valid ``ContextProductContract`` under
    ``extra=forbid``, and a product whose ``schema_name`` names no class this
    consumer has registered — in both cases the consumer cannot say what the
    thing *is*, which is upstream of saying whether the peer may send it.
    """

    schema_name: str | None
    violation: str


class PolicyBindingRefusal(AdmissionRefusal):
    """Check 4: the peer asserted something outside its entitlements (T-06-39).

    Attributes:
        assertion: Which entitlement was exceeded — the producer hash, the
            schema, the policy regimes, or the tenant.
        asserted: What the peer claimed.
        permitted: What its trust-policy entry allows. Both sides, so the
            caller never re-resolves the policy to learn what the gap was.
    """

    assertion: str
    asserted: frozenset[str]
    permitted: frozenset[str]


class LineageContinuityRefusal(AdmissionRefusal):
    """Check 6: the merged lineage lost an entry it must have kept (D-14).

    Unreachable while :func:`union_lineage` unions. It is here precisely for
    the day it does not: an implementation that replaced instead of unioning
    would erase the producer's provenance silently, and this refusal is what
    makes that failure loud at the boundary as well as in the property suite.
    """

    producer: frozenset[str]
    consumer: frozenset[str]
    merged: frozenset[str]


def union_lineage(
    *, producer: ProductLineage, consumer: ProductLineage
) -> ProductLineage:
    """Extend ``consumer``'s lineage with ``producer``'s by set-union (D-14).

    CLAUDE.md §7.2: *"Inbound L extends, not replaces, the consumer's L via
    set-union; producer's operator plan, graph snapshot, and policy version are
    all preserved."* Realized literally:

    * ``operators_invoked`` and ``policy_bundle_versions`` are unions, so the
      producer's operator plan and policy versions survive and so do the
      consumer's. Replacement in either direction loses a provenance claim
      somebody made, and the whole point of L is that nobody's claim is
      dropped on the way through a boundary.
    * ``graph_snapshot_at`` is the **producer's**. It is not a set and cannot
      be unioned, and the value that must be preserved is the anchor the
      product was actually assembled against — the consumer's own anchor
      describes different state and would misdate this product's provenance.
      The consumer's anchor is not lost either: it stays on the consumer's own
      products, which is where it describes something true.

    Because ``graph_snapshot_at`` is single-valued, the order-independence law
    is a law about the two *set* axes; the property suite states it that way
    rather than pretending an instant commutes.
    """
    return ProductLineage(
        operators_invoked=(
            producer.operators_invoked | consumer.operators_invoked
        ),
        policy_bundle_versions=(
            producer.policy_bundle_versions | consumer.policy_bundle_versions
        ),
        graph_snapshot_at=producer.graph_snapshot_at,
    )


class AdmissionRecord(CCFContract):
    """What crossed a Peering, persisted at the boundary (D-IMPL-58 reading (d)).

    SDK-defined extension (CLAUDE.md §7.2, §7.4). Dave's ruling of 2026-07-27
    resolves D-IMPL-58 as **reading (d)**: the merged :class:`
    ~ccf.products.contract.ProductLineage` is persisted *at the admission
    boundary* rather than in graph state, and
    ``ccf.contracts.claims.LineageEntry`` is not extended. The defect being
    closed is that :meth:`PeeringAdmissionGate.admit` computed the union into
    :attr:`AdmittedProduct.lineage` and nothing read it — ``ingest_admitted``
    reads ``admitted.product`` and never ``admitted.lineage`` — so lineage
    continuity was a property of a wrapper L2 discards. Under (d) the property
    becomes true *and* correctly located: continuity is a property of the
    federation boundary, which is what CLAUDE.md §7.2 actually describes.

    **Why this is an ArtifactStore artifact and not Control Plane state
    (D-IMPL-27).** D-IMPL-27 splits substrates by mutability, and this record is
    immutable, versioned and replay-relevant: it describes one crossing that
    already happened, so there is nothing about it to update. Content addressing
    (D-IMPL-26) then makes immutability structural rather than procedural — the
    same bytes yield the same address, so no overwrite path is needed or
    offered, and replay resolves an exact version rather than "latest".

    **What the audit log does and does not carry — stated here so the next
    reader does not repeat the false premise D-IMPL-58's correction paragraph
    records.** :meth:`~ccf.controlplane.audit.AuditLog.append` carries *scalars
    only* (``action, key, version, resolved, occurred_at, actor,
    artifact_class``); there is no payload field, and an
    :class:`~ccf.controlplane.audit.AuditEvent` cannot hold a ``ProductLineage``.
    So the audit plane answers *was this admitted, by whom, when* — a verdict —
    and this artifact answers *what was admitted*. The verdict points at the
    record through the reference triple, and neither structure pretends to be
    the other.

    **Producer and consumer are carried alongside the merge, not only the
    merge.** A union that cannot be decomposed cannot be audited: an examiner
    handed only ``merged_lineage`` cannot say which side contributed which
    operator, and reconstructing it from the peer's product later depends on
    that product still being available. All three are recorded so the crossing
    is legible from this artifact alone.

    Attributes:
        tenant_id: The consuming tenant whose Control Plane admitted (D-IMPL-05).
        peer_id: The peer whose signature and entitlements were verified.
        product_content_address: Address of the admitted product — the bytes
            whose signature verified, which is the same witness the
            attributability gate used. This is what ties the record to a
            specific crossing rather than to a schema.
        producer_lineage: The inbound product's declared lineage.
        consumer_lineage: The consuming fabric's own lineage at admission.
        merged_lineage: The union :func:`union_lineage` computed — what
            CLAUDE.md §7.2's "extends, not replaces" commitment produced.
        admitted_at: The evaluation instant the gate was given. Supplied, never
            read from a clock, so the record is as deterministic as the verdict.

    No value here is a deployment's: no peer id, no schema, no regime is
    authored in this module (CINV-01).
    """

    tenant_id: str
    peer_id: str
    product_content_address: str
    producer_lineage: ProductLineage
    consumer_lineage: ProductLineage
    merged_lineage: ProductLineage
    admitted_at: datetime


#: The artifact class an admission record is filed under. Named for the **seam**
#: it records rather than for the transport that carried the bytes: one gate runs
#: uniformly over every Peering (``D-IMPL-59`` part 4), so one record class serves
#: every Peering and a second transport files nothing new. The ``class_id`` value
#: itself is exactly what D-IMPL-58's amendment ruled and is unchanged here.
#: Dot-namespaced and kebab-cased, matching the established family exactly —
#: ``ccf.half-life-table`` at ``src/ccf/controlplane/artifacts.py::HALF_LIFE_TABLE``
#: and ``ccf.debt-profile`` at ``src/ccf/controlplane/artifacts.py::DEBT_PROFILE``.
#: D-IMPL-58's amendment of 2026-07-27 records why this is asserted in a test
#: rather than left to review: the entry originally carried the non-conforming
#: literal ``admission_record``, and an error in the decision log propagates with
#: that log's authority behind it.
ADMISSION_RECORD = ArtifactClass(
    class_id="ccf.admission-record", contract=AdmissionRecord
)


class AdmissionNotRecorded(RuntimeError):
    """The admission record could not be persisted, so nothing was admitted.

    Raised rather than returned as a refusal, on this module's own established
    discipline (see :meth:`PeeringAdmissionGate._ceiling`): a fabric that cannot
    reach its own substrate is a **broken deployment**, not a badly behaved
    peer, and reporting the two the same way would let an outage read as a
    federation dispute. It is the same reasoning
    :class:`~ccf.replay.serve.ReplayWriter` applies to serving — a failure to
    record is a failure to serve — applied one boundary earlier: a crossing
    whose record was not persisted is not reported as admitted (T-06-100).
    """


class AdmissionBypassError(TypeError):
    """An admitted product was constructed outside the admission gate."""


_ADMISSION_TOKEN = object()


def verify_admission_provenance(admitted: object) -> "AdmittedProduct":
    """Establish that ``admitted`` came through Control Plane peering admission.

    `D-IMPL-337`'s verifier for :class:`AdmittedProduct`. **The check is the
    provenance, not the type.** A bypass here is not a governance failure of a
    federated product — it is an unverified one reaching the path toward L3,
    against the single-writer invariant (CLAUDE.md §10) and `D-IMPL-16`'s
    commitment that an inbound A2A product is inadmissible until the consuming
    Control Plane validates it.

    Returns the value, narrowed, so a caller cannot verify and then forget to
    use the result.

    Raises:
        AdmissionBypassError: the value did not come through
            :meth:`PeeringAdmissionGate.admit`.
    """
    if getattr(admitted, "_admission_provenance", None) is not _ADMISSION_TOKEN:
        raise AdmissionBypassError(
            "this value carries no evidence of Control Plane peering"
            " admission. ccf.peering.admission.PeeringAdmissionGate.admit is"
            " the only path that establishes it, and neither a structurally"
            " compatible object nor a subclass of AdmittedProduct that skipped"
            " its guarded __init__ acquires it (D-IMPL-337; CLAUDE.md §7.2,"
            " D-IMPL-16)"
        )
    return cast("AdmittedProduct", admitted)


class AdmittedProduct:
    """A product the consuming Control Plane has admitted — L2's inbound input.

    Not constructible outside this module (see the module docstring for why the
    token is justified here and was withdrawn from ``Agent``). Holding one *is*
    the evidence that all six checks ran, which is why the assembly path takes
    this type: a :class:`~ccf.peering.protocol.PeeringProtocol`
    implementation can produce
    an :class:`~ccf.peering.protocol.InboundProduct` and nothing more, and an
    ``InboundProduct`` is not what L2 accepts.

    Admission is not a write. What this value confers is the right to be
    *offered* to L2 — L2 remains the only holder of a graph write handle
    (CLAUDE.md §10), and the gate does not shorten the path through it; it
    guards its entrance.

    Since Dave's 2026-07-27 ruling, the offer has a typed door:
    :meth:`ccf.assembly.worker.AssemblyWorker.ingest_admitted` takes *this*
    type, so a federated product that never passed the gate cannot be offered
    to L2 at all. The envelope-based :meth:`~ccf.assembly.worker.AssemblyWorker.
    ingest` is unchanged and continues to serve CDC and MCP ingress, which is
    why the federated path needed its own entry point rather than a constraint
    on the shared one.
    """

    def __init__(
        self,
        product: ContextProductContract,
        lineage: ProductLineage,
        peer: PeerRef,
        token: object,
        protected_header: Mapping[str, object] | None = None,
        content_address: str | None = None,
    ) -> None:
        if token is not _ADMISSION_TOKEN:
            raise AdmissionBypassError(
                "AdmittedProduct is constructed only by "
                "ccf.peering.admission.PeeringAdmissionGate.admit; Control Plane "
                "admission is the only path by which an inbound Peering Context "
                "Product becomes offerable to L2 (CLAUDE.md §7.2, D-IMPL-16)"
            )
        self._product = product
        self._lineage = lineage
        self._peer = peer
        # `D-IMPL-337`. The PROVENANCE, distinct from the type. Set only here,
        # on the only path that verified the signature, the peer's entitlement
        # and the policy bindings. `isinstance` says nothing about whether any
        # of that ran — a subclass skipping this `__init__` passes it.
        self._admission_provenance = _ADMISSION_TOKEN
        # FROZEN, not stored by reference. A caller holding the admitted
        # product could otherwise mutate the mapping after verification and
        # substitute a claim the gate never checked — which would make
        # "authenticated header" mean "a header that was authenticated at some
        # point, and is whatever it is now".
        self._protected_header = (
            MappingProxyType(dict(protected_header))
            if protected_header is not None
            else None
        )
        self._content_address = content_address

    @property
    def product(self) -> ContextProductContract:
        """The validated inbound contract."""
        return self._product

    @property
    def lineage(self) -> ProductLineage:
        """The merged lineage — the producer's extended onto the consumer's."""
        return self._lineage

    @property
    def peer(self) -> PeerRef:
        """The peer whose signature and entitlements were verified."""
        return self._peer

    @property
    def protected_header(self) -> Mapping[str, object] | None:
        """The **authenticated** protected header, or ``None``.

        Carried out of the gate as of ``D-IMPL-336`` Amendment 3 (F16), because
        a consumer that needs a claim from the header must be able to reach one
        this gate verified rather than re-reading an envelope itself. It is
        authenticated in the strong sense: the header was part of the JWS
        signing input, and this value is the very local
        :meth:`PeeringAdmissionGate.admit` ran its policy-binding checks
        against — not a second :meth:`~ccf.peering.protocol.SignedContextProduct.declared_header`
        call, which would re-derive rather than carry.

        ``None`` only on an ``AdmittedProduct`` built before this member
        existed; the shipped gate always fills it.
        """
        return self._protected_header

    @property
    def content_address(self) -> str | None:
        """The address computed over the **verified** canonical bytes.

        Same carrying discipline as :attr:`protected_header`, and for the same
        reason: a consumer recomputing it independently is fine, but a consumer
        comparing against a value the gate already established is comparing
        against something a peer could not choose.
        """
        return self._content_address


class PeeringAdmissionGate:
    """The one gate every inbound Peering product passes before L2 (D-12).

    Run uniformly over every Peering, whichever transport carried the bytes
    (``D-IMPL-59`` part 4): a Peering declares trust inputs — the observed peer
    and the signed bytes — and this gate alone reaches the verdict and
    constructs the :class:`AdmittedProduct` L2 accepts.

    Tenant-scoped at construction (D-IMPL-05): a gate answers for one tenant's
    Control Plane, resolving that tenant's trust policy and that tenant's
    ceiling by pinned version. Two tenants therefore run two gates over two
    artifacts, and one tenant's grant to a peer cannot admit that peer for
    another — there is no shared object for it to leak through.

    Args:
        identity: Signature verification (D-IMPL-15). Takes its candidate keys
            as an argument, so the trust decision stays here rather than
            inside the verifier.
        control_plane: Where the trust policy and the ceiling are resolved
            from, by pinned ``(key, version)``. Never "latest": a decision must
            be re-resolvable against the configuration in force when it was
            made (whitepaper §7.10).
        audit_log: The Control Plane's append-only log. Injected rather than
            constructed so admissions land in the *same* monotonic sequence as
            registrations and grants (WR-07): the Control Plane is the audit
            plane, singular.
        artifact_store: Where each admitted crossing's :class:`AdmissionRecord`
            is persisted (D-IMPL-58 reading (d), CLAUDE.md §7.4). **Injected, and
            never constructed here** — a gate that built its own store would fix
            the substrate the SDK has spent a Protocol avoiding fixing, and would
            put a file path in a module that holds no deployment values. Note
            what this parameter is *not*: it is not a write handle to the graph.
            Single-writer is preserved because the store is a persistence
            substrate reached through mechanism, never a second writer to L3
            (T-06-101).
        tenant_id: The tenant this gate admits for.
        trust_policy_version: Pinned version of that tenant's policy.
        payload_ceiling_version: Pinned version of that tenant's ceiling.
        product_classes: The product classes this consumer serves, by
            ``schema_name``, carrying the pinned MAX_TTL the TTL check runs
            against. Supplied by the deployment; the SDK holds no class list.
    """

    def __init__(
        self,
        *,
        identity: IdentityProvider,
        control_plane: ControlPlaneProtocol,
        audit_log: AuditLog,
        artifact_store: ArtifactStoreProtocol,
        tenant_id: str,
        trust_policy_version: str,
        payload_ceiling_version: str,
        product_classes: Mapping[str, RegisteredProductClass],
    ) -> None:
        self._identity = identity
        self._control_plane = control_plane
        self._audit = audit_log
        self._artifact_store = artifact_store
        self._tenant_id = tenant_id
        self._trust_policy_key = trust_policy_key(tenant_id=tenant_id)
        self._trust_policy_version = trust_policy_version
        self._ceiling_key = payload_ceiling_key(tenant_id=tenant_id)
        self._payload_ceiling_version = payload_ceiling_version
        self._product_classes = dict(product_classes)

    @property
    def tenant_id(self) -> str:
        """The tenant this gate admits for."""
        return self._tenant_id

    # -- audit --------------------------------------------------------------

    def _record(
        self,
        *,
        action: AuditAction,
        resolved: bool,
        peer_id: str,
        content_address: str,
        occurred_at: datetime,
        admission_ref: ArtifactRef | None = None,
    ) -> None:
        """Append one admission verdict to the Control Plane audit log.

        ``content_address`` is empty when the verdict was reached before the
        payload could be decoded — the size ceiling is the one check that runs
        that early, and computing an address to log it would be exactly the
        work the ceiling exists to avoid.

        ``admission_ref``, when present, is the reference to the crossing's
        :class:`AdmissionRecord`, and its ``(artifact_class, name,
        content_address)`` becomes the append's ``artifact_class`` / ``key`` /
        ``version`` triple. **That triple is the only new thing crossing into
        the audit plane** (D-IMPL-58): no ``AuditAction`` member is added and
        ``AuditEvent`` gains no field, because the plane's job is unchanged. It
        keeps answering the verdict question — *was this admitted, by whom,
        when* — and now points at the artifact answering *what was admitted*,
        which it was never shaped to carry itself.
        """
        self._audit.append(
            action=action,
            key=(
                admission_ref.name
                if admission_ref is not None
                else self._trust_policy_key
            ),
            version=(
                admission_ref.content_address
                if admission_ref is not None
                else content_address
            ),
            resolved=resolved,
            occurred_at=occurred_at,
            actor=peer_id,
            artifact_class=(
                ADMISSION_RECORD.class_id
                if admission_ref is not None
                else PEERING_TRUST_POLICY.class_id
            ),
        )

    # -- the record of what crossed -----------------------------------------

    def _persist_admission_record(
        self,
        *,
        peer: PeerRef,
        content_address: str,
        producer: ProductLineage,
        consumer: ProductLineage,
        merged: ProductLineage,
        occurred_at: datetime,
    ) -> ArtifactRef:
        """Persist what crossed, before anything can be reported as admitted.

        Called at the point the union exists and *before* an
        :class:`AdmittedProduct` is constructed, which is the ordering the
        repudiation threat turns on (T-06-100): a record written afterwards could
        be skipped by any path that returned early, and a crossing nobody can
        describe is a crossing the fabric cannot be held to.

        The record is named by the admitted product's content address and
        addressed by its own, so two deliveries of the same crossing converge on
        one artifact rather than accumulating near-duplicates — the store's
        idempotence doing the work rather than a de-duplication rule here.

        Raises:
            AdmissionNotRecorded: the store could not persist the record. Not
                swallowed and not softened into a refusal — see that class.
        """
        record = AdmissionRecord(
            tenant_id=self._tenant_id,
            peer_id=peer.peer_id,
            product_content_address=content_address,
            producer_lineage=producer,
            consumer_lineage=consumer,
            merged_lineage=merged,
            admitted_at=occurred_at,
        )
        try:
            return self._artifact_store.put(
                tenant_id=self._tenant_id,
                artifact_class=ADMISSION_RECORD.class_id,
                name=content_address,
                artifact=record,
            )
        except ArtifactStoreError as unreachable:
            raise AdmissionNotRecorded(
                f"the admission record for peer {peer.peer_id!r}'s product"
                f" {content_address!r} could not be persisted, so the crossing"
                " is not reported as admitted; a record of what crossed is a"
                " precondition of admitting it (D-IMPL-58, T-06-100)"
            ) from unreachable

    def _refuse(
        self,
        refusal: AdmissionRefusal,
        *,
        content_address: str,
        occurred_at: datetime,
    ) -> AdmissionRefusal:
        self._record(
            action="peering_admission_refused",
            resolved=False,
            peer_id=refusal.peer_id,
            content_address=content_address,
            occurred_at=occurred_at,
        )
        return refusal

    # -- Control Plane resolution -------------------------------------------

    def _ceiling(self) -> InboundPayloadCeiling:
        """Resolve the tenant's pinned inbound ceiling.

        Raises:
            ccf.controlplane.registry.ControlPlaneMissing: no ceiling is
                registered at the pinned ``(key, version)``.
            TypeError: something other than an :class:`InboundPayloadCeiling`
                is registered there. Both are raised, not refused: a fabric
                that cannot resolve its own ceiling is a broken deployment, not
                a badly behaved peer, and reporting the two the same way would
                let an outage read as a federation dispute.
        """
        artifact = self._control_plane.resolve(
            self._ceiling_key, self._payload_ceiling_version
        )
        if not isinstance(artifact, InboundPayloadCeiling):
            raise TypeError(
                f"inbound payload ceiling at ({self._ceiling_key!r},"
                f" {self._payload_ceiling_version!r}) holds"
                f" {type(artifact).__name__}, not InboundPayloadCeiling"
            )
        return artifact

    def _trust_policy(self) -> PeeringTrustPolicy:
        """Resolve the tenant's pinned trust policy.

        Raises:
            ccf.controlplane.registry.ControlPlaneMissing: not registered.
            TypeError: something other than an :class:`PeeringTrustPolicy` is
                registered there. Broken deployment, as above.
        """
        artifact = self._control_plane.resolve(
            self._trust_policy_key, self._trust_policy_version
        )
        if not isinstance(artifact, PeeringTrustPolicy):
            raise TypeError(
                f"Peering trust policy at ({self._trust_policy_key!r},"
                f" {self._trust_policy_version!r}) holds"
                f" {type(artifact).__name__}, not PeeringTrustPolicy"
            )
        return artifact

    # -- the gate -----------------------------------------------------------

    def admit(
        self,
        *,
        inbound: InboundProduct,
        consumer_lineage: ProductLineage,
        now: datetime,
    ) -> AdmittedProduct | GateRefusal:
        """Run all six checks over ``inbound``; see the module docstring.

        Args:
            inbound: What a transport received, and who it believes sent it.
            consumer_lineage: The consuming fabric's own lineage, which the
                producer's extends rather than replaces (D-14).
            now: The evaluation instant, supplied by the caller. Nothing here
                reads a clock — a verdict that depended on wall-clock time
                would make replay non-deterministic exactly where determinism
                matters most.

        Returns:
            An :class:`AdmittedProduct` when every check passes, otherwise the
            refusal of the *first* check that did not. Refusals from checks
            1–4 and 6 are :class:`AdmissionRefusal` subclasses; check 5 returns
            the federated contract gates' own refusal types unchanged, because
            it *is* the federated contract gates.

        Raises:
            ccf.controlplane.registry.ControlPlaneMissing: a pinned Control
                Plane artifact this gate needs is not registered.
            TypeError: a pinned artifact holds the wrong contract.
        """
        peer = inbound.observed_peer

        # --- 1. size ceiling, before anything decodes --------------------
        ceiling = self._ceiling()
        observed = inbound.declared_payload_size()
        if observed > ceiling.max_payload_bytes:
            return self._refuse(
                PayloadTooLargeRefusal(
                    gate=GATE_PAYLOAD_CEILING,
                    tenant_id=self._tenant_id,
                    peer_id=peer.peer_id,
                    observed_bytes=observed,
                    ceiling_bytes=ceiling.max_payload_bytes,
                    detail=(
                        f"inbound payload of {observed} bytes exceeds the"
                        f" tenant's ceiling of {ceiling.max_payload_bytes};"
                        " refused before canonicalization"
                    ),
                ),
                content_address="",
                occurred_at=now,
            )

        # --- 2. signature, against this peer's own keys ------------------
        policy = self._trust_policy()
        try:
            grant: PeerTrustGrant = policy.grant_for(peer_id=peer.peer_id)
        except TrustPolicyViolation as violation:
            return self._refuse(
                SignatureRefusal(
                    gate=GATE_SIGNATURE,
                    tenant_id=self._tenant_id,
                    peer_id=peer.peer_id,
                    declared_key_id=None,
                    permitted_key_ids=frozenset(),
                    failure=str(violation),
                    detail=(
                        f"peer {peer.peer_id!r} has no entry in tenant"
                        f" {self._tenant_id!r}'s trust policy; an unconfigured"
                        " peer is refused, never treated as unconstrained"
                    ),
                ),
                content_address="",
                occurred_at=now,
            )

        permitted_key_ids = frozenset(grant.signing_keys)
        try:
            declared_key_id: str | None = inbound.signed.declared_key_id()
        except IdentityError:
            declared_key_id = None
        try:
            verified = self._identity.verify(
                signed=inbound.signed, public_keys=grant.signing_keys
            )
        except IdentityError as failure:
            return self._refuse(
                SignatureRefusal(
                    gate=GATE_SIGNATURE,
                    tenant_id=self._tenant_id,
                    peer_id=peer.peer_id,
                    declared_key_id=declared_key_id,
                    permitted_key_ids=permitted_key_ids,
                    failure=type(failure).__name__,
                    detail=(
                        f"the envelope did not verify as peer {peer.peer_id!r}"
                        f": {failure}"
                    ),
                ),
                content_address="",
                occurred_at=now,
            )

        # Everything after this point is about *verified* bytes, and the
        # protected header is now authenticated: it was part of the JWS signing
        # input, so a claim in it is the peer's claim rather than anyone's.
        content_address = inbound.signed.content_address()
        header = inbound.signed.declared_header()

        # --- 3. contract validation, over the verified canonical bytes ---
        try:
            product = ContextProductContract.model_validate_json(verified)
        except ValidationError as invalid:
            return self._refuse(
                ContractRefusal(
                    gate=GATE_CONTRACT,
                    tenant_id=self._tenant_id,
                    peer_id=peer.peer_id,
                    schema_name=None,
                    violation=str(invalid),
                    detail=(
                        "the verified payload is not a valid"
                        " ContextProductContract under extra=forbid; CCF's own"
                        " validation is the typed boundary, never the"
                        " transport's"
                    ),
                ),
                content_address=content_address,
                occurred_at=now,
            )

        # --- 4. policy bindings ------------------------------------------
        binding = self._check_policy_bindings(
            product=product, header=header, peer=peer, grant=grant
        )
        if binding is not None:
            return self._refuse(
                binding, content_address=content_address, occurred_at=now
            )

        # --- 5. the federated contract gates -----------------------------
        product_class = self._product_classes.get(product.schema_name)
        if product_class is None:
            return self._refuse(
                ContractRefusal(
                    gate=GATE_CONTRACT,
                    tenant_id=self._tenant_id,
                    peer_id=peer.peer_id,
                    schema_name=product.schema_name,
                    violation="unregistered product class",
                    detail=(
                        f"this consumer serves no product class"
                        f" {product.schema_name!r}, so it holds no MAX_TTL to"
                        " gate the product against"
                    ),
                ),
                content_address=content_address,
                occurred_at=now,
            )
        gate_refusal = self._run_federated_gates(
            product=product,
            attested_address=content_address,
            product_class=product_class,
            now=now,
        )
        if gate_refusal is not None:
            self._record(
                action="peering_admission_refused",
                resolved=False,
                peer_id=peer.peer_id,
                content_address=content_address,
                occurred_at=now,
            )
            return gate_refusal

        # --- 6. lineage integrity ----------------------------------------
        merged = union_lineage(
            producer=product.lineage, consumer=consumer_lineage
        )
        for side, original in (
            ("producer", product.lineage),
            ("consumer", consumer_lineage),
        ):
            if not (
                original.operators_invoked <= merged.operators_invoked
                and original.policy_bundle_versions
                <= merged.policy_bundle_versions
            ):
                return self._refuse(
                    LineageContinuityRefusal(
                        gate=GATE_LINEAGE_CONTINUITY,
                        tenant_id=self._tenant_id,
                        peer_id=peer.peer_id,
                        producer=product.lineage.operators_invoked,
                        consumer=consumer_lineage.operators_invoked,
                        merged=merged.operators_invoked,
                        detail=(
                            f"the merged lineage does not contain the {side}'s"
                            " entries; inbound L must extend the consumer's by"
                            " set-union, never replace it (CLAUDE.md §7.2)"
                        ),
                    ),
                    content_address=content_address,
                    occurred_at=now,
                )

        # The crossing is recorded before it is reported. Nothing between this
        # call and the return can produce an admitted product without a record.
        admission_ref = self._persist_admission_record(
            peer=peer,
            content_address=content_address,
            producer=product.lineage,
            consumer=consumer_lineage,
            merged=merged,
            occurred_at=now,
        )
        self._record(
            action="peering_admitted",
            resolved=True,
            peer_id=peer.peer_id,
            content_address=content_address,
            occurred_at=now,
            admission_ref=admission_ref,
        )
        return AdmittedProduct(
            product,
            merged,
            peer,
            _ADMISSION_TOKEN,
            protected_header=header,
            content_address=content_address,
        )

    def _check_policy_bindings(
        self,
        *,
        product: ContextProductContract,
        header: Mapping[str, object],
        peer: PeerRef,
        grant: PeerTrustGrant,
    ) -> PolicyBindingRefusal | None:
        """Hold the peer to what its trust-policy entry permits (T-06-39).

        Four assertions, each checked against the peer's own entry: the tenant
        the product claims, the producing agent it names in the authenticated
        protected header, the product class it sends, and the policy regimes it
        claims. Returns the first refusal, or ``None`` when all four are inside
        the grant.
        """
        if product.tenant_id != self._tenant_id:
            return PolicyBindingRefusal(
                gate=GATE_POLICY_BINDING,
                tenant_id=self._tenant_id,
                peer_id=peer.peer_id,
                assertion="tenant_id",
                asserted=frozenset({product.tenant_id}),
                permitted=frozenset({self._tenant_id}),
                detail=(
                    f"the product claims tenant {product.tenant_id!r} but this"
                    f" gate admits for {self._tenant_id!r}; trust is per tenant"
                ),
            )

        producer = header.get(PRODUCER_ASSERTION_HEADER)
        if not isinstance(producer, str) or not producer:
            return PolicyBindingRefusal(
                gate=GATE_POLICY_BINDING,
                tenant_id=self._tenant_id,
                peer_id=peer.peer_id,
                assertion=PRODUCER_ASSERTION_HEADER,
                asserted=frozenset(),
                permitted=grant.permitted_producer_hashes,
                detail=(
                    "the signed header asserts no producing agent; a peer that"
                    " does not say what produced a product cannot be held to"
                    " what it is permitted to produce"
                ),
            )
        try:
            grant.require_producer(producer_agent_definition_hash=producer)
        except TrustPolicyViolation as violation:
            return PolicyBindingRefusal(
                gate=GATE_POLICY_BINDING,
                tenant_id=self._tenant_id,
                peer_id=peer.peer_id,
                assertion=PRODUCER_ASSERTION_HEADER,
                asserted=frozenset({producer}),
                permitted=grant.permitted_producer_hashes,
                detail=str(violation),
            )

        try:
            grant.require_schema(schema_name=product.schema_name)
        except TrustPolicyViolation as violation:
            return PolicyBindingRefusal(
                gate=GATE_POLICY_BINDING,
                tenant_id=self._tenant_id,
                peer_id=peer.peer_id,
                assertion="schema_name",
                asserted=frozenset({product.schema_name}),
                permitted=grant.permitted_schema_names,
                detail=str(violation),
            )

        claimed = product.lineage.policy_bundle_versions
        outside = claimed - grant.permitted_policy_regimes
        if outside:
            return PolicyBindingRefusal(
                gate=GATE_POLICY_BINDING,
                tenant_id=self._tenant_id,
                peer_id=peer.peer_id,
                assertion="policy_bundle_versions",
                asserted=claimed,
                permitted=grant.permitted_policy_regimes,
                detail=(
                    f"the product claims policy regimes {sorted(outside)} that"
                    f" peer {peer.peer_id!r} is not entitled to claim"
                ),
            )
        return None

    def _run_federated_gates(
        self,
        *,
        product: ContextProductContract,
        attested_address: str,
        product_class: RegisteredProductClass,
        now: datetime,
    ) -> GateRefusal | None:
        """Run the federated contract gates, and be explicit about what they show.

        :func:`~ccf.products.gates.run_federated_gates` is called rather than
        reimplemented, so a stale inbound product is refused by the *same*
        INV-CH7-48 mechanism a locally assembled one is, against the same
        pinned MAX_TTL. What each gate establishes across a trust boundary
        differs per gate, and pretending otherwise would be the more dangerous
        error:

        * **Empty-operator guard (INV-CH7-46) — fully meaningful.** A product
          declaring no operators was computed by nothing, whoever produced it.
        * **Lineage attributability — what INV-CH7-47 becomes here, per Dave's
          ``D-IMPL-57`` ruling of 2026-07-27 (reading (a)).** The declared
          operator plan must be covered by the bytes whose signature verified:
          the address check 2 established is passed in as ``attested_address``,
          and a candidate hashing to anything else is refused. The consumer ran
          no engine, so no independent record of the producer's plan exists on
          this side; what holds is that the peer *signed* the plan it asserted
          and cannot later deny it. Accepted consequence, stated rather than
          softened: **a compromised or buggy peer can assert an operator plan it
          did not run, and the consuming fabric will admit the product.** What
          is guaranteed is attribution and non-repudiation, never truth.
        * **TTL bounds (INV-CH7-48) — fully meaningful.** Expiry is a property
          of the product and the consumer's clock, and needs nothing the
          consumer lacks (T-06-40).

        Returns:
            The gates' refusal, or ``None`` when all three pass.
        """
        outcome = run_federated_gates(
            product,
            attested_address=attested_address,
            now=now,
            registry=self._control_plane,
            product_class=product_class,
        )
        return outcome if isinstance(outcome, GateRefusal) else None
