"""``WireProtocol`` — the transport seam for A2A Context Product exchange.

SDK-defined extension (CLAUDE.md §7.2 — "A2A federation is first-class in v0"),
attaching to whitepaper §8.3 Pattern 4; D-IMPL-14 rules the v0 default wire and
commits the abstraction itself. The commitment this module realizes is the one
CLAUDE.md §7.2 states outright: **the Context Product Contract is the stable
layer; the wire is replaceable.**

**Only CCF types cross this line.** The Protocol's parameters and returns are
:class:`~ccf.contracts.base.CCFContract` values and
:class:`~ccf.a2a.identity.SignedContextProduct` — never a transport's native
message type. That is not tidiness, it is the C4 typed-boundary requirement:

* The Linux Foundation A2A Python SDK at 1.x is **protobuf**-based rather than
  Pydantic-based. A protobuf message has no ``extra=forbid`` semantics and no
  Pydantic validation; unknown fields are silently *preserved* rather than
  refused. Treating such a message as the typed boundary would mean the
  fabric's closed-world contract stopped at the process edge.
* The other candidate transport speaks JSON-RPC framing, whose envelope shape
  is likewise a transport concern with no CCF meaning.

So the boundary sits **above** both. Each implementation converts its native
representation to and from the CCF types declared here, and CCF's own
validation — run at the admission gate, over the raw canonical bytes — is what
the fabric trusts (:mod:`ccf.a2a.admission`; research Pitfall 5). The words
"protobuf" and "JSON-RPC" appear in this module only in this paragraph, which
explains why they are excluded; **nothing in ``/src`` imports ``a2a`` at all**,
and plan 06-16's gate sweep asserts that absence rather than trusting it.

**What the Protocol omits (D-21).** It declares no L2 surface, no assembly
surface and no graph surface: there is no parameter, return type, or method
here that names one. A received product is a value an implementation hands to
its caller, and the only thing that turns such a value into something L2 will
accept is :class:`~ccf.a2a.admission.AdmittedProduct`, which this module cannot
construct and a transport therefore cannot produce. The honest claim is
structural rather than absolute: the admission gate sits above every transport
(D-12), so a second transport cannot arrive with its own private check, and a
transport that wanted to reach L2 would have to be handed something it has no
way to make.

Placement follows D-04: the Protocol is declared in ``/src`` while every
concrete transport lives in ``/runtime``, so ``/src`` types against the
abstraction and the dependency cannot invert.

Algorithmic module (CINV-03): declarations and value types only — no I/O
happens here, and no LLM dependency may ever be acquired.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from ccf.a2a.identity import SignedContextProduct
from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "EmitReceipt",
    "InboundProduct",
    "PeerRef",
    "WireProtocol",
]


class PeerRef(CCFContract):
    """A federation peer, named the way the Control Plane names it.

    Deliberately not an address. A URL, a host, or a channel handle is the
    transport's business and differs per wire; the identifier here is the one
    the tenant's trust-policy artifact keys on
    (:class:`~ccf.a2a.trust_policy.A2ATrustPolicy`), so the same peer is the
    same peer whichever wire carried it. A reference that embedded an endpoint
    would make trust a property of where a message arrived from, which is the
    property an attacker most easily controls.

    ``tenant_id`` is carried because trust is per tenant (D-IMPL-05): one
    tenant's grant to a peer says nothing about another's.

    Attributes:
        tenant_id: The tenant whose federation this peer belongs to.
        peer_id: The peer's identifier within that tenant's trust policy.
    """

    tenant_id: str
    peer_id: str


class EmitReceipt(CCFContract):
    """What a transport reports after carrying one signed product outward.

    A receipt is an acknowledgement of *transport*, and says nothing about
    admission: whether the far side admitted the product is the far side's
    Control Plane decision, reached after this receipt exists. Modelled as its
    own type so an emitter cannot read "delivered" as "accepted".

    Attributes:
        peer: The peer the product was carried to.
        content_address: The address of the canonical bytes that were sent —
            the same value :meth:`~ccf.a2a.identity.SignedContextProduct.
            content_address` computes, so producer and consumer can name one
            artifact when they disagree about anything else.
        wire_message_id: The transport's own identifier for the carriage, for
            operational correlation. Opaque to CCF by construction: nothing in
            the fabric interprets it.
    """

    peer: PeerRef
    content_address: str
    wire_message_id: str


class InboundProduct(CCFContract):
    """One signed product a transport received, with what the transport saw.

    Attributes:
        observed_peer: Who the *transport* believes sent this — a channel-level
            observation (a connection, a header, a session), and therefore a
            claim. It selects which trust-policy entry the admission gate reads;
            it proves nothing. What binds the product to a principal is the
            signature verifying against a key that peer's entry lists
            (:mod:`ccf.a2a.identity`).
        signed: The detached-JWS envelope carrying the canonical product bytes.
    """

    observed_peer: PeerRef
    signed: SignedContextProduct

    def declared_payload_size(self) -> int:
        """Return the size of the carried payload member, without decoding it.

        Measured on the base64url text as received, so the admission gate's
        size ceiling can refuse an oversized or decompression-bomb payload
        *before* anything decodes, parses, or canonicalizes it. Base64url is a
        fixed 4:3 expansion of the underlying bytes, so this is a faithful
        proxy for the payload's size and costs one length.
        """
        return len(self.signed.payload)


@runtime_checkable
class WireProtocol(Protocol):
    """Carry a signed Context Product across a process boundary (D-IMPL-14).

    CLAUDE.md §7.2; whitepaper §8.3 Pattern 4. Implementations live in
    ``/runtime`` (D-04) and convert between their native wire representation
    and the CCF types above — see the module docstring for why the boundary
    sits above every transport's own types.

    **An implementation is handed no route into the fabric.** There is no
    method here that takes or returns an L2, assembly, or graph type, and the
    value :meth:`receive` yields is an :class:`InboundProduct`, which L2 does
    not accept. The admission gate is what converts one into something L2 will
    take, and it is above every transport rather than inside any of them
    (D-12), so the rule is stated once and a later transport cannot omit it.

    ``runtime_checkable`` supports composition-root wiring checks; it verifies
    method presence only, so static conformance still rests on mypy.
    """

    def emit(
        self, *, peer: PeerRef, signed: SignedContextProduct
    ) -> EmitReceipt:
        """Carry ``signed`` to ``peer`` and return the transport's receipt.

        The envelope is emitted as given. A transport that re-serialized the
        product would change the bytes the signature was made over, so the
        payload member travels verbatim.
        """
        ...

    def receive(self) -> Iterator[InboundProduct]:
        """Yield products this transport has received, oldest first.

        Yielding rather than dispatching is deliberate: an implementation that
        *delivered* products somewhere would need to know where the fabric
        begins, and the whole point of D-12 is that it does not.
        """
        ...
