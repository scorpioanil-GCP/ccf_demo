"""The one encode and the one decode every transport shares.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§5 (``D-12``, ``D-13``) and §8 (``D-20``).

Why this module is the densest-tested one in the package
---------------------------------------------------------
``D-12`` puts ``Result`` construction in exactly one place, and ``D-13`` sends
even the in-process adapter through this codec rather than past it. Together
they make this the **single point of parity failure**: every transport's output
becomes a client-visible answer here, so a property proven here holds for every
adapter that ever ships, and a property not proven here is one each adapter gets
to break in its own way.

The in-process adapter has live objects in hand and serializes them anyway. That
is deliberate and is not waste: it makes in-process a true degenerate wire rather
than a privileged fast path, it gives a parity bug exactly one place to live, and
it *physically* prevents the adapter from leaking live producer-side objects
across the seam. The cost is a microsecond of serialization.

There is exactly one serialization, and this module does not add a second
--------------------------------------------------------------------------
:func:`encode_outcome` is :func:`~ccf.contracts.canonical.canonical_bytes` of the
outcome and nothing more. The served vessel rides inside it as the UTF-8 text the
doors already emit and is re-parsed on decode with the contract's own validator,
so no rendering in this module is invented, re-ordered or re-formatted. See
:mod:`ccf.client.wire` for the full ruling and for why a byte-string field was
impossible rather than merely undesirable.

The echo is cross-checked, not reconstructed
---------------------------------------------
:func:`decode_outcome` takes the request that was **sent** as a required
argument. The client could instead reconstruct the request identity from what it
holds — cheaper, and one fewer thing on the wire. It is rejected because
reconstruction cannot detect a transport that answered a *different question*
than the one asked: a proxying or multiplexing transport that crosses two
in-flight questions produces a perfectly well-formed outcome for the wrong
request, and a client that reconstructs the identity from its own state would
label that answer with the question it meant to ask. Comparing what came back
against what was asked turns that into a detectable failure. Making it a
parameter of the operation rather than an optional extra is what stops the check
from being forgotten at a call site.

What is a value and what is an exception
-----------------------------------------
A refusal is a value and is returned; a malformed wire is a
:class:`~ccf.client.errors.TransportError` and is raised. Decoding never converts
the second into the first — ``except Exception: return refusal`` would report
"the fabric said no" when nothing was ever asked, and the caller, having branched
correctly, would record an audited refusal that never happened.

This module is algorithmic (CINV-03): pure functions over typed values, no I/O,
no clock, no LLM dependency ever.
"""

from __future__ import annotations

import hashlib

from pydantic import ValidationError

from ccf.client.errors import TransportError
from ccf.client.wire import WireOutcome, WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.products.contract import ContextProductContract

__ccf_mode__ = "algorithmic"

__all__ = ["decode_outcome", "encode_outcome", "verify_content_address"]


def encode_outcome(outcome: WireOutcome) -> bytes:
    """Render ``outcome`` as the canonical bytes a transport puts on the wire.

    Deterministic by construction, because it delegates to the SDK's one
    canonical serializer and defines no second form: two encodes of the same
    outcome are byte-identical, which is what lets a content address computed on
    one side be verified on the other.
    """
    return canonical_bytes(outcome)


def verify_content_address(product_json: str, claimed: str) -> str:
    """Recompute the vessel's address and refuse a wire that disagrees.

    Named, and taking both the received text and the claimed address as
    parameters, so the check is one function the round-trip path and its
    sabotage control can both reach. A control that re-implemented the
    comparison would prove only that the copy fires.

    The recomputed value is authoritative and the claimed one is never trusted:
    an address that travelled beside the bytes it describes is a claim about
    them, and the whole value of a content address is that the claim is
    checkable. This is precisely what the HTTP door's address header exists to
    let a client verify without owning a CCF canonicalizer, and it is why the
    MCP doors publishing no address is harmless.

    Args:
        product_json: The UTF-8 text of the served vessel's canonical bytes.
        claimed: The address the wire carried alongside it.

    Returns:
        The recomputed address, which equals ``claimed`` when it returns at all.

    Raises:
        TransportError: the bytes do not hash to the address claimed for them,
            so the vessel was altered in transit or the producer and the
            consumer disagree about the canonical form.
    """
    recomputed = hashlib.sha256(product_json.encode("utf-8")).hexdigest()
    if recomputed != claimed:
        raise TransportError(
            "the received vessel does not hash to the content address the wire"
            f" claimed for it — claimed `{claimed}`, recomputed `{recomputed}`."
            " The bytes were altered in transit, or the producer and this"
            " client disagree about the canonical form"
        )
    return recomputed


def decode_outcome(raw: bytes, *, sent: WireRequest) -> WireOutcome:
    """Turn received bytes into the one outcome shape, or refuse to.

    The single decode path ``D-12`` requires. Four things are checked, in the
    order in which failing early is most informative: the bytes are a
    well-formed outcome, the outcome answers the question that was asked, the
    vessel hashes to the address claimed for it, and the vessel is a valid
    contract.

    Args:
        raw: The bytes an adapter received.
        sent: The request that was actually sent. Required rather than optional
            so the echo cross-check cannot be forgotten — see the module
            docstring for why an echo rather than a reconstruction.

    Returns:
        The decoded outcome, carrying either a served vessel or a refusal.

    Raises:
        TransportError: the bytes are not a well-formed outcome, the echoed
            request names a different question than the one sent, the vessel
            does not hash to its claimed address, or the vessel is not a valid
            contract. Never raised for a governed refusal, which is a value and
            is returned.
    """
    try:
        outcome = WireOutcome.model_validate_json(raw)
    except ValidationError as malformed:
        raise TransportError(
            "the received bytes are not a well-formed outcome, so the wire"
            " carried no governed answer at all — a malformed wire is a broken"
            " wire and never a refusal"
        ) from malformed

    if outcome.request != sent:
        raise TransportError(
            "the outcome echoes a different question than the one that was"
            f" asked — sent `{sent.product_id}` and received"
            f" `{outcome.request.product_id}`, or their parameters or temporal"
            " boundaries differ. A transport that crosses two in-flight"
            " questions produces a well-formed answer to the wrong one"
        )

    if outcome.product_json is not None:
        if outcome.content_address is None:  # pragma: no cover - validator forbids
            raise TransportError(
                "a served outcome arrived with no content address, which the"
                " outcome's own validator forbids"
            )
        verify_content_address(outcome.product_json, outcome.content_address)
        try:
            ContextProductContract.model_validate_json(outcome.product_json)
        except ValidationError as invalid:
            raise TransportError(
                "the received vessel is not a valid product contract — the"
                " producer and this client disagree about the contract, which"
                " is the one condition replay cannot survive silently"
            ) from invalid

    return outcome
