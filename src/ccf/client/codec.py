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

…and the shipped adapters reconstruct, so both checks are inert today
----------------------------------------------------------------------
**Every word of the argument above stands. What follows is the measured state
of the code beside it**, recorded rather than implied, per ``D-IMPL-151``
(Dave, 2026-08-17) finding ``B0``. The correction is deliberately an addition:
the design this seam is meant to have is not wrong, and deleting the reasoning
would lose why the follow-on is worth doing.

:class:`~ccf.products.door.DoorOutcome` carries **no request identity**, so an
adapter has nothing from the wire to echo. Both shipped adapters therefore set
:attr:`~ccf.client.wire.WireOutcome.request` from the request object they were
*handed*, and :class:`~ccf.client.client.ProductClient` passes that same object
as ``sent`` — so :func:`check_outcome`'s ``outcome.request != sent`` is an
object compared with itself and **cannot fail**. For the same reason the
"claimed" address an adapter supplies is computed by that adapter from the
identical ``product_json`` it emits, so :func:`verify_content_address` is
``sha256(x) != sha256(x)`` and **cannot fail either**. *(That was the measured
state through Phase 18. It is no longer the state of this tree — see* **The
follow-on landed** *below, which is the correction and not a second opinion.)*

Consequently, **until the follow-on phase lands, this SDK must not be described
as detecting a transport that answered a different question, or as detecting a
vessel altered in transit.** Both are open blocking defects against the
client-seam integrity claim rather than accepted risk. Making the checks able to
fail requires ``DoorOutcome`` — or the wire form — to carry request identity, a
wire-shape change across both doors, the adapter and this module; that is the
follow-on's sole job, and ``D-IMPL-151`` deferred it rather than expanding a
phase already declared execution-complete. *(The follow-on is Phase 19 and it
landed. This constraint is* **replaced by the narrower true sentence below,
not lifted** *— the replacement is deliberately smaller than the claim the
constraint was protecting readers from.)*

:func:`decode_outcome` is the path on which these checks *would* be
load-bearing, because it parses ``request`` and ``content_address`` out of bytes
the sender produced rather than taking them from the receiver's own state. **No
shipped adapter calls it.** Both build a :class:`~ccf.client.wire.WireOutcome`
object directly, which ``D-11`` permits — the adapter seam is typed as returning
the object, not bytes — and it is exactly that permission that lets the
reconstruction in. So the function is reached today only by this package's own
tests. That is the measurement, and it is recorded here because "the codec
checks it" reads as a live guarantee and is not one. *(Corrected below:*
``C-05`` *removed that permission by retyping the seam, and* :func:`decode_outcome`
*now has a* **shipped** *call site —* :meth:`~ccf.client.client.ProductClient.ask`
*calls it on the bytes the adapter returned.)*

The **third** check in this module is unaffected and is not part of the defect:
the vessel's contract validation runs over text the *producer* serialized, so a
producer and a consumer that disagree about the contract fail on every
transport.

The follow-on landed, and this is what the checks detect — and do not
----------------------------------------------------------------------
**Phase 19** (``C-01``…``C-18``, Dave, 2026-08-17 / 2026-08-19, in
``.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-CONTEXT.md``).
Everything above is kept and none of it is deleted: it is the record of what
was measured and of why the follow-on was worth doing, and a deleted false
claim leaves no trace that it was ever believed. **The argument two sections
up —** *the echo is cross-checked, not reconstructed* **— was right and is
unchanged**; what was wrong was never that argument but the code beside it.

**What changed.** The adapter seam is typed ``ask(WireRequest) -> bytes``
(``C-05``, ``C-08``), so an adapter has nothing to construct and no way to fill
the echo from the request it was handed. The producer mints the echo from the
question **it** parsed off its own wire (:func:`~ccf.products.door.door_question`,
``C-01``) and computes the content address from the *same* single serialization
of the vessel it emits (:func:`~ccf.products.door.door_answer`). The in-process
transport encodes the question too, so it is a degenerate wire in **both**
directions (``C-07``) and the check is live on the transport every quickstart,
fixture and dev path uses. :func:`decode_outcome` is on the shipped path.

**What the checks now detect**, in the words ``C-10`` fixes them in — the client
detects *an answer to a different question*, and *a vessel that does not match
the address its producer computed* — against five named conditions:

* **corruption** of ``product_json`` in transit;
* **truncation** of it;
* **mis-routing** that swaps a vessel for another producer's, or crosses two
  in-flight questions that are not identical;
* **a re-serializing intermediary**, because any re-render changes the bytes
  and not the claim travelling beside them;
* **producer/consumer canonicalization drift**, because the consumer hashes the
  text it received rather than re-canonicalizing it, so a producer that renders
  differently from what it claims is caught on its own bytes.

**What they do not detect.** Four cases, named because a claim that does not
state its limits is the claim this phase exists to replace:

1. **An adversary who can rewrite the envelope.** The claim rides *in* the
   envelope, so an actor with write access to it rewrites the echo and the
   address to match whatever they substituted. This is non-adversarial
   integrity and nothing more.
2. **A producer that mis-canonicalizes** *consistently*, which states a
   matching address for its own wrong bytes. That case is caught by the third
   check (the vessel's contract validation) and by cross-adapter parity, never
   by this comparison.
3. **Two** *identical* **in-flight questions crossing.** Knowingly accepted:
   the echo is the question, so two callers asking the same thing are not
   distinguishable by it, and every field a correlation token would add is a
   field no check reads (``C-03``).
4. **On a question asked with** ``as_of=None`` **only, a transport that alters
   the instant the door answered against.** The client resolves that instant
   (``C-15``), so it crosses the wire exactly once and there is no second copy
   to compare it against; the echo faithfully carries ``None`` as asked
   (``C-02``) and matches perfectly. **The other half of that axis is held**:
   a **concrete** ``as_of`` crosses twice — inside the encoded question and as
   the door's own ``asked_at`` — and the MCP door cross-checks the two and
   **refuses a disagreement by name** (``C-18``). The residual is the ``None``
   path and only the ``None`` path; a sentence declaring the temporal axis
   unprotected would be as false as the one this phase replaces, in the other
   direction.

**Signing is out of scope and no signature member is reserved on the wire**
(``C-10``). Reserving one would put a member on the wire that nothing sets and
nothing reads, which is precisely the shape this phase exists to close — the
same shape that made both checks inert in the first place.

**``D-GATE-18``'s standing prose constraint is replaced by the paragraphs
above, not lifted.** A reader arriving here from that gate entry should land on
a narrower true statement rather than on silence: the SDK detects a crossed
question and an altered vessel against the five conditions named above; it
**does not detect** an adversary who can rewrite the envelope, and it **does
not detect** a transport that alters only the instant a question asked with
``as_of=None`` was answered at.

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
from dataclasses import dataclass

from pydantic import ValidationError

from ccf.client.errors import TransportError
from ccf.client.wire import WireOutcome, WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.products.contract import ContextProductContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "DecodedOutcome",
    "check_outcome",
    "decode_outcome",
    "encode_outcome",
    "verify_content_address",
]


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

    **On every shipped adapter, ``claimed`` is not a claim that travelled.** It
    is computed by the adapter from the identical ``product_json`` it passes
    here, so this comparison is ``sha256(x) != sha256(x)`` and cannot fail —
    ``D-IMPL-151`` finding ``B0``, an open blocking defect deferred to its own
    phase. The reasoning above is why the function takes the claim as a
    parameter and is unchanged; what is corrected is the impression that the
    claim is currently checkable end to end. See this module's docstring.

    **Corrected in Phase 19, and the paragraph above is kept as the record of
    what was measured.** ``claimed`` is now a claim that travelled: the
    producer computes it in :func:`~ccf.products.door.door_answer` from the
    *same* single serialization of the vessel it emits, and the consumer
    recomputes it from the text it received. The two operands have independent
    origins, so this comparison can fail and is watched failing — see the
    module docstring for the five conditions it detects and the four it does
    not.

    Args:
        product_json: The UTF-8 text of the served vessel's canonical bytes.
        claimed: The address the wire carried alongside it.

    Returns:
        The recomputed address, which equals ``claimed`` when it returns at all.

    Raises:
        TransportError: the bytes do not hash to the address claimed for them,
            so the vessel was altered in transit or the producer and the
            consumer disagree about the canonical form. **Not reachable from any
            shipped adapter today**, for the reason recorded above; a caller who
            handed this function an independently-obtained address — which is
            what a client verifying the HTTP door's header does — gets the
            failure the paragraph describes. **That caveat is superseded as of
            Phase 19**: it *is* reachable from both shipped adapters, because
            the address is the producer's and the recomputation is the
            consumer's, and it is raised through a real ``ProductClient`` on
            each transport in
            ``tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py``.
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


def check_outcome(
    outcome: WireOutcome, *, sent: WireRequest
) -> ContextProductContract | None:
    """Check an outcome against the question it answers, and parse its vessel.

    The three checks a *client* needs on anything an adapter hands it: the
    outcome answers the question that was asked, the vessel hashes to the
    address claimed for it, and the vessel is a valid contract.

    Named and separated from :func:`decode_outcome` so the two paths that must
    perform it can share one definition. :func:`decode_outcome` calls it after
    parsing bytes, and :class:`~ccf.client.client.ProductClient` calls it on
    whatever an adapter returned — because ``D-11`` types the adapter seam as
    returning a :class:`~ccf.client.wire.WireOutcome` rather than bytes, so an
    adapter that never went near this module can still produce a well-formed
    outcome object. Making the client run these checks itself is what turns
    ``D-12``'s *"a code path adapters cannot avoid"* into a property of the
    checks as well as of ``Result`` construction. The cost is one SHA-256 over
    text the client already holds; the alternative is trusting every adapter
    author to have remembered.

    **``D-11`` was amended in Phase 19 and the paragraph above is kept as the
    reasoning that survived the amendment.** ``C-05``/``C-08`` retyped the seam
    to ``ask(WireRequest) -> bytes``, so there is no longer an adapter-built
    outcome for the client to re-check and this function runs **exactly once**
    per ask, inside :func:`decode_outcome`, over bytes the producer serialized.
    What the paragraph was defending — that the checks are a code path an
    adapter cannot avoid — is now enforced by the seam's type rather than by a
    second call, which is strictly stronger. The amending decision entry is the
    one Phase 19 mints for ``C-05``.

    The served vessel is **returned rather than discarded** so the caller that
    needs it does not parse the same text a second time.

    **Two of the three checks are inert on every shipped adapter, and the third
    is not.** Both adapters set ``outcome.request`` from the request object they
    were handed — the one the client also passes as ``sent`` — so
    ``outcome.request != sent`` compares an object with itself, and the address
    they claim is computed from the text they pass, so the recomputation
    compares a digest with itself. That is ``D-IMPL-151`` finding ``B0``, an
    open blocking defect deferred to its own phase and **not** an accepted risk;
    the module docstring records why, and what the follow-on has to change.
    **The contract-validity check is unaffected** and does real work on both
    transports: the vessel is text the *producer* serialized, so a producer and
    a consumer that disagree about the contract fail here today.

    **All three are live as of Phase 19, and the paragraph above is kept
    because it records what was measured rather than what was hoped.** The echo
    is minted by the producer from the question it parsed, and the address is
    computed by the producer from the bytes it emits, so neither comparison has
    an operand the consumer supplied. Both are watched failing through a real
    :class:`~ccf.client.client.ProductClient` on each shipped transport
    separately, never by a diff between two of them. What the client seam does
    **not** detect is enumerated in the module docstring and includes
    ``C-18``'s ``as_of=None`` temporal residual.

    Args:
        outcome: What an adapter produced, or what was just parsed from bytes.
        sent: The request that was actually sent. Required rather than optional
            so the echo cross-check cannot be forgotten — see the module
            docstring for why an echo rather than a reconstruction.

    Returns:
        The parsed vessel on a served outcome, and ``None`` on a refusal. A
        refusal is a governed answer with no vessel, not a failure.

    Raises:
        TransportError: the echoed request names a different question than the
            one sent, the vessel does not hash to its claimed address, or the
            vessel is not a valid contract. Never raised for a governed refusal.
            **Only the last of the three is reachable from a shipped adapter**;
            the first two are reachable from an outcome whose ``request`` and
            ``content_address`` came from the wire rather than from the
            receiver, which today means :func:`decode_outcome` and this
            package's own tests. **Superseded in Phase 19: all three are
            reachable from both shipped adapters**, because ``request`` and
            ``content_address`` now always come from the wire — this function
            is only ever called from :func:`decode_outcome`, which parses them
            out of the producer's bytes.
    """
    if outcome.request != sent:
        raise TransportError(
            "the outcome echoes a different question than the one that was"
            f" asked — sent `{sent.product_id}` and received"
            f" `{outcome.request.product_id}`, or their parameters or temporal"
            " boundaries differ. A transport that crosses two in-flight"
            " questions produces a well-formed answer to the wrong one"
        )

    if outcome.product_json is None:
        return None

    if outcome.content_address is None:  # pragma: no cover - validator forbids
        raise TransportError(
            "a served outcome arrived with no content address, which the"
            " outcome's own validator forbids"
        )
    verify_content_address(outcome.product_json, outcome.content_address)
    try:
        return ContextProductContract.model_validate_json(outcome.product_json)
    except ValidationError as invalid:
        raise TransportError(
            "the received vessel is not a valid product contract — the"
            " producer and this client disagree about the contract, which"
            " is the one condition replay cannot survive silently"
        ) from invalid


@dataclass(frozen=True)
class DecodedOutcome:
    """The decoded outcome and the vessel the checks already parsed out of it.

    **SDK-defined** (``C-05``, Phase 19). It exists for one reason, and the
    reason is a prohibition rather than a convenience: :func:`check_outcome`
    **already parsed** the served vessel in order to validate it, and a caller
    that re-parsed :attr:`~ccf.products.door.DoorOutcome.product_json` to get
    its own copy would be running a second contract validation on a second
    decode path — which is the defect ``D-12`` exists to prevent, one field
    over. Carrying the parsed vessel out beside the outcome is what lets
    :meth:`~ccf.client.client.ProductClient._result_from` build the one
    ``Result`` without parsing anything at all.

    A frozen dataclass rather than a bare tuple, on the precedent
    :class:`~ccf.products.door.ServedAnswer` already sets in this codebase for
    *a value and the thing that authorized it*: a positional pair at a
    published surface reads as an accident at the first call site that unpacks
    it wrong.

    Attributes:
        outcome: The outcome parsed from the producer's bytes.
        vessel: The parsed contract on a served outcome, and ``None`` on a
            refusal — exactly what :func:`check_outcome` returned, never a
            second parse of the same text.
    """

    outcome: WireOutcome
    vessel: ContextProductContract | None


def decode_outcome(raw: bytes, *, sent: WireRequest) -> DecodedOutcome:
    """Turn received bytes into the one outcome shape, or refuse to.

    The single decode path ``D-12`` requires. Four things are checked, in the
    order in which failing early is most informative: the bytes are a
    well-formed outcome, the outcome answers the question that was asked, the
    vessel hashes to the address claimed for it, and the vessel is a valid
    contract. The last three are :func:`check_outcome`, which the client runs
    again on whatever an adapter returns.

    Args:
        raw: The bytes an adapter received.
        sent: The request that was actually sent. Required rather than optional
            so the echo cross-check cannot be forgotten — see the module
            docstring for why an echo rather than a reconstruction.

    Returns:
        The decoded outcome, carrying either a served vessel or a refusal.
        Returned as a :class:`DecodedOutcome` — the outcome **and** the vessel
        :func:`check_outcome` just parsed — because ``C-05`` put this function
        on the shipped path, and the caller there constructs the one ``Result``
        (``D-12``); handing back only the outcome would force that caller to
        re-parse ``product_json``, which is a second contract validation on a
        second decode path.

    Raises:
        TransportError: the bytes are not a well-formed outcome, the echoed
            request names a different question than the one sent, the vessel
            does not hash to its claimed address, or the vessel is not a valid
            contract. Never raised for a governed refusal, which is a value and
            is returned. **All four are reachable here**, because ``request``
            and ``content_address`` are parsed out of ``raw`` rather than taken
            from the receiver — which is exactly what makes this the path the
            follow-on phase for ``D-IMPL-151`` finding ``B0`` has to bring the
            shipped adapters onto, or bring the identity onto their wire.
            **That follow-on is Phase 19 and it did the first of the two**:
            ``C-05`` retyped the seam to bytes and
            :meth:`~ccf.client.client.ProductClient.ask` calls this function on
            what the adapter returned, so both shipped adapters are on this
            path and all four raises are reachable through a real client.
    """
    try:
        outcome = WireOutcome.model_validate_json(raw)
    except ValidationError as malformed:
        raise TransportError(
            "the received bytes are not a well-formed outcome, so the wire"
            " carried no governed answer at all — a malformed wire is a broken"
            " wire and never a refusal"
        ) from malformed

    vessel = check_outcome(outcome, sent=sent)
    return DecodedOutcome(outcome=outcome, vessel=vessel)
