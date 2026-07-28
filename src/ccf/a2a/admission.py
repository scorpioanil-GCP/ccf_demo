"""The Control Plane admission gate every inbound A2A product passes.

SDK-defined extension (CLAUDE.md §7.2), attaching to whitepaper §8.3 Pattern 4
and to the Control Plane of §7.8. CLAUDE.md §7.2 states the commitment this
module *is*: **an inbound A2A Context Product is not admissible to L3 until the
consuming Control Plane validates its Policy bindings.** D-IMPL-16 rules that
this happens for *every* inbound product, with no fast path for a high-trust
peer — a trust tier narrows or widens what a peer may assert, never whether it
is checked.

**One gate, above every transport (D-12).** The check does not live inside a
:class:`~ccf.a2a.wire.WireProtocol` implementation. Two transports ship this
phase and more may follow; a per-transport check would state the rule once per
wire and let a later wire state it differently, or not at all. So the rule sits
above all of them, and a transport is handed no way to reach past it.

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
   :meth:`A2AAdmissionGate._run_federated_gates` for what that call does and
   does not establish across a trust boundary.
6. **Lineage integrity.** The inbound lineage *extends* the consumer's by
   set-union: producer entries survive, consumer entries survive, and the
   producer's operator plan, graph snapshot and policy version are preserved
   (CLAUDE.md §7.2; D-14). :func:`union_lineage` is the law, and
   ``tests/properties/test_lineage_union.py`` is what pins it (T-06-44).

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
an :class:`~ccf.a2a.identity.IdentityProvider` concern, and peers are resolved
per call. Closing the audit-bearing-write-path gap D-20 names is a prerequisite
this plan deliberately does not incur (T-06-45).

This module holds no ceiling, no peer, no schema name and no regime — every one
of those is the deployment's statement (CLAUDE.md §11, CINV-01). Algorithmic
module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from pydantic import Field, ValidationError, field_validator

from ccf.a2a.identity import IdentityError, IdentityProvider
from ccf.a2a.trust_policy import (
    A2A_TRUST_POLICY,
    A2ATrustPolicy,
    PeerTrustGrant,
    TrustPolicyViolation,
    trust_policy_key,
)
from ccf.a2a.wire import InboundProduct, PeerRef
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import ArtifactClass, validate_semver
from ccf.controlplane.audit import AuditAction, AuditLog
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.products.contract import (
    ContextProductContract,
    ProductLineage,
    RegisteredProductClass,
)
from ccf.products.gates import GateRefusal, run_federated_gates

__ccf_mode__ = "algorithmic"

__all__ = [
    "GATE_CONTRACT",
    "GATE_LINEAGE_CONTINUITY",
    "GATE_PAYLOAD_CEILING",
    "GATE_POLICY_BINDING",
    "GATE_SIGNATURE",
    "INBOUND_PAYLOAD_CEILING",
    "PRODUCER_ASSERTION_HEADER",
    "A2AAdmissionGate",
    "AdmissionBypassError",
    "AdmissionRefusal",
    "AdmittedProduct",
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
#: refusal an operator reads in a log.
GATE_PAYLOAD_CEILING = "a2a-payload-ceiling"
GATE_SIGNATURE = "a2a-signature"
GATE_CONTRACT = "a2a-contract"
GATE_POLICY_BINDING = "a2a-policy-binding"
GATE_LINEAGE_CONTINUITY = "a2a-lineage-continuity"

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
    class_id="ccf.a2a-inbound-payload-ceiling", contract=InboundPayloadCeiling
)


def payload_ceiling_key(*, tenant_id: str) -> str:
    """Return the Control Plane key one tenant's inbound ceiling registers under.

    A derivation rather than a table, on the
    :func:`~ccf.a2a.trust_policy.trust_policy_key` precedent: the SDK supplies
    the shape so two components cannot disagree about where the value lives,
    and supplies no tenant, so it holds no deployment's vocabulary (CINV-01).
    """
    return f"{INBOUND_PAYLOAD_CEILING.class_id}/{tenant_id}"


class AdmissionRefusal(GateRefusal):
    """Base of the admission refusals — values, never exceptions.

    Deriving from :class:`~ccf.products.gates.GateRefusal` rather than
    paralleling it is deliberate: an inbound product meets the fabric's gate
    discipline, not a second one that happens to look similar. A caller
    inspecting ``gate`` and ``detail`` reads an A2A refusal exactly as it reads
    a TTL refusal, and :meth:`A2AAdmissionGate.admit` can return either without
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


class AdmissionBypassError(TypeError):
    """An admitted product was constructed outside the admission gate."""


_ADMISSION_TOKEN = object()


class AdmittedProduct:
    """A product the consuming Control Plane has admitted — L2's inbound input.

    Not constructible outside this module (see the module docstring for why the
    token is justified here and was withdrawn from ``Agent``). Holding one *is*
    the evidence that all six checks ran, which is why the assembly path takes
    this type: a :class:`~ccf.a2a.wire.WireProtocol` implementation can produce
    an :class:`~ccf.a2a.wire.InboundProduct` and nothing more, and an
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
    ) -> None:
        if token is not _ADMISSION_TOKEN:
            raise AdmissionBypassError(
                "AdmittedProduct is constructed only by "
                "ccf.a2a.admission.A2AAdmissionGate.admit; Control Plane "
                "admission is the only path by which an inbound A2A Context "
                "Product becomes offerable to L2 (CLAUDE.md §7.2, D-IMPL-16)"
            )
        self._product = product
        self._lineage = lineage
        self._peer = peer

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


class A2AAdmissionGate:
    """The one gate every inbound A2A product passes before L2 (D-12).

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
        tenant_id: str,
        trust_policy_version: str,
        payload_ceiling_version: str,
        product_classes: Mapping[str, RegisteredProductClass],
    ) -> None:
        self._identity = identity
        self._control_plane = control_plane
        self._audit = audit_log
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
    ) -> None:
        """Append one admission verdict to the Control Plane audit log.

        ``content_address`` is empty when the verdict was reached before the
        payload could be decoded — the size ceiling is the one check that runs
        that early, and computing an address to log it would be exactly the
        work the ceiling exists to avoid.
        """
        self._audit.append(
            action=action,
            key=self._trust_policy_key,
            version=content_address,
            resolved=resolved,
            occurred_at=occurred_at,
            actor=peer_id,
            artifact_class=A2A_TRUST_POLICY.class_id,
        )

    def _refuse(
        self,
        refusal: AdmissionRefusal,
        *,
        content_address: str,
        occurred_at: datetime,
    ) -> AdmissionRefusal:
        self._record(
            action="a2a_admission_refused",
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

    def _trust_policy(self) -> A2ATrustPolicy:
        """Resolve the tenant's pinned trust policy.

        Raises:
            ccf.controlplane.registry.ControlPlaneMissing: not registered.
            TypeError: something other than an :class:`A2ATrustPolicy` is
                registered there. Broken deployment, as above.
        """
        artifact = self._control_plane.resolve(
            self._trust_policy_key, self._trust_policy_version
        )
        if not isinstance(artifact, A2ATrustPolicy):
            raise TypeError(
                f"A2A trust policy at ({self._trust_policy_key!r},"
                f" {self._trust_policy_version!r}) holds"
                f" {type(artifact).__name__}, not A2ATrustPolicy"
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
                action="a2a_admission_refused",
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

        self._record(
            action="a2a_admitted",
            resolved=True,
            peer_id=peer.peer_id,
            content_address=content_address,
            occurred_at=now,
        )
        return AdmittedProduct(product, merged, peer, _ADMISSION_TOKEN)

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
