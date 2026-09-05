"""What a door puts on a wire — the served vessel, or the governed "no".

**SDK-defined, not whitepaper-derived** (CLAUDE.md §7.1, §8.3). The whitepaper
specifies the Context Product Contract (§6.3), the three validation gates
(§7.6) and the Decision Replay record (§7.10); it specifies no client, and
therefore no shape in which a door answers one. The ruling of record is
``D-IMPL-148`` **Addendum A** (Dave, 2026-08-17): *both* shipped product doors
carry the replay reference, and the MCP door additionally carries a refusal as
its tool's **return value**.

This module lives in ``src/`` for the reason :mod:`ccf.products.refusal` gives
for its own placement: the shape is emitted by a door in ``runtime/`` and
decoded by a client in ``src/ccf/client``, and ``src/`` cannot import
``runtime/``. Putting it beside the types it carries is what lets the emission
and the decode agree **by construction** rather than by two implementations
being written to the same paragraph.

Why a refusal cannot be raised at the MCP door
----------------------------------------------
Measured against ``mcp==1.28.1``: a FastMCP tool that raises has its exception
wrapped as ``ToolError: Error executing tool <name>: <message>`` and delivered
to the client as ``isError=True`` carrying that **prose prefix**. A client
wanting the governed answer would have to strip a server's wording — string
parsing a sentence for an audited verdict. So the refusal is the tool's
*return*, and :class:`DoorOutcome` is what that return is.

**Served and refused are discriminable structurally, never by sniffing.** The
two halves are separate, exclusive, named members, and a model validator
refuses an outcome carrying both or neither — the shape ``D-11`` already fixed
for :class:`~ccf.client.wire.WireOutcome`, restated here because this is the
producing side of the same seam. Underneath, the backstop holds too:
:class:`~ccf.products.refusal.RefusalEnvelope` and
:class:`~ccf.products.contract.ContextProductContract` are both frozen and
``extra=forbid`` with disjoint required fields, so neither can validate as the
other even if a member were read in isolation.

The vessel rides as **text**, and that is inherited rather than re-decided
-------------------------------------------------------------------------
:attr:`DoorOutcome.product_json` carries the UTF-8 text of
:func:`~ccf.contracts.canonical.canonical_bytes` applied to the served vessel —
character for character what every shipped door already emits.
:class:`~ccf.client.wire.WireOutcome` records the full argument for that
spelling and it holds here unchanged: nesting the vessel as a JSON *object*
would put a second rendering of it on the wire, and a consumer recomputing the
content address would then be hashing this envelope's rendering rather than the
producer's bytes. Carrying the text makes ``sha256(product_json.encode())``
exactly the producer's address, with no re-serialization anywhere on the path.

Why the replay reference is a **sibling** of the vessel and never a member
--------------------------------------------------------------------------
The reason is the one recorded at
``ccf_runtime.http_api.routes::canonical_response`` for the content address:
the vessel's bytes *are* the product, so carrying anything inside them changes
the bytes and therefore changes the address they claim. An envelope *around*
the vessel always has room for a sibling, which is why the reference sits here
and why the HTTP door — which has a header channel and whose body must stay the
vessel — publishes the same string as a response header instead. **The
asymmetry is a property of the transports, not a difference in what the two
doors carry**, and ``tests/mcp/test_egress_refusal_envelope.py`` holds the two
to the identical string for the identical question.

One shape, and it is defined here
---------------------------------
``C-06`` (Phase 19, ``19-CONTEXT.md``) collapsed the door's outcome shape and
the client's wire outcome shape into **one**: a door emits precisely what a
client decodes, so no transcoding step exists between them — and a transcoding
step is exactly where an adapter can re-source the echo from client state
rather than from the wire (``D-IMPL-151`` finding ``B0``). :class:`DoorOutcome`
is that one shape and ``ccf.client.wire.WireOutcome`` is an alias of it.
:class:`WireRequest` moved here for the same placement reason the paragraph
above gives: the door has to name the type it echoes, and a producer-side shape
module cannot import the client package without reversing the established
layering.

This module is algorithmic (CINV-03): pure functions over typed values, no
I/O, no clock, no LLM dependency ever.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import field_validator, model_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.products.contract import ContextProductContract
from ccf.products.gates import ServableProduct
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    REFUSAL_KINDS,
    RefusalEnvelope,
    RequestIdentity,
    envelope_for,
)
from ccf.products.request import ProductRequest
from ccf.replay.serve import ServedProduct

__ccf_mode__ = "algorithmic"

__all__ = [
    "PRODUCT_REQUEST_TOOL",
    "DoorOutcome",
    "ServedAnswer",
    "WireRequest",
    "door_answer",
    "door_question",
    "door_refusal",
    "served_answer",
]


#: The name of the parameterised MCP Tool a deployment may expose over its
#: egress server (``ccf_runtime.mcp.egress::build_egress_server``).
#:
#: **Declared here rather than in the door that registers it, for this
#: module's own stated reason.** The emitting side is
#: ``ccf_runtime.mcp.egress`` and the calling side is
#: :mod:`ccf.client.adapters.mcp_stdio`, and ``src/`` cannot import
#: ``runtime/`` — so a name spelled in both places would be two implementations
#: written to the same paragraph rather than one fact. ``egress.py`` imports it
#: from here and re-exports it, so every existing citation of
#: ``ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL`` resolves unchanged.
#:
#: It is **mechanism, not a deployment value** (CINV-01): a deployment chooses
#: *whether* to expose the tool and what prose it advertises, and the SDK
#: chooses what the tool is called — exactly as it chooses the shape of what
#: the tool returns.
PRODUCT_REQUEST_TOOL = "request_context_product"


def _unstable_parameter(value: object, path: str) -> tuple[str, object] | None:
    """Find the first parameter value that does not survive the wire unchanged.

    Returns the dotted path and the offending value, or ``None`` when every
    value in the tree crosses and comes back equal to itself.

    The admissible set is the JSON-native one — text, whole numbers, booleans,
    absence, and mappings and lists of those. It is deliberately *narrower* than
    what the canonical serializer accepts, and the difference is the whole point
    of this function: the serializer renders a ``Decimal`` as text, an instant
    as an RFC3339 string, and a set as a sorted array, all of which are correct
    canonical renderings and none of which come back as the type that went out
    when the receiving field is annotated ``Any``. A tuple is excluded for the
    same reason and not by oversight — it returns as a list, and a list does not
    equal a tuple.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return None
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                return (path, key)
            found = _unstable_parameter(item, f"{path}.{key}")
            if found is not None:
                return found
        return None
    if isinstance(value, list):
        for index, item in enumerate(value):
            found = _unstable_parameter(item, f"{path}[{index}]")
            if found is not None:
                return found
        return None
    return (path, value)


class WireRequest(CCFContract):
    """The question, in the shape an adapter carries but never interprets.

    ``D-11``: an adapter's whole job is to get this to a producer and get an
    outcome back. It reads no member of this type to decide anything.

    **There is no version member, and the omission is deliberate.** ``D-04``
    fixes the client API at ``for_product(product_id, binding=None)`` with no
    version parameter, because a caller pinning a schema version at the client
    is a caller maintaining a copy of the deployment's registry. The version is
    resolved server-side from the deployment's registered class and reported
    back on the served vessel's ``schema_version`` — so it travels in the
    answer, where the producer is the authority, rather than in the question,
    where the client would be guessing.

    Attributes:
        product_id: The product class the question addresses.
        parameters: The class-declared remainder of the question. An empty
            mapping is a question that needed nothing beyond its axes — a
            positive statement, not a missing value.
        temporal_boundary: The instant to answer against, **timezone-aware or
            absent**. ``None`` is the positive assertion *defer to the server's
            decision instant*, which is the rule ``D-04`` documents on
            ``ask()``; it is not an unset field. A naive instant is refused at
            construction — see
            :meth:`_temporal_boundary_survives_the_wire`.
    """

    product_id: str
    parameters: Mapping[str, Any]
    temporal_boundary: datetime | None

    @field_validator("parameters")
    @classmethod
    def _parameters_survive_the_wire(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Refuse a parameter value that would come back as a different type.

        This guard is what makes the outcome's echo cross-check sound, and
        without it that cross-check produces **false wire failures**. The
        mechanism, stated once so it is not re-derived: ``parameters`` is
        annotated ``Any``, so the canonical serializer's correct rendering of a
        ``Decimal`` (text) or an instant (an RFC3339 string) is parsed back as
        text, and the decoded echo then differs from the request that was sent.
        The decoder compares the two and reports a ``TransportError`` — on a
        wire that worked perfectly.

        So the choice is not between strict and lax. It is between refusing the
        value at construction, where the message can name the wire-stable
        spelling, and reporting a transport failure that never happened at a
        point where nothing can diagnose it. ``D-08``'s posture decides it: the
        fabric never silently degrades a caller's value.
        """
        found = _unstable_parameter(value, "parameters")
        if found is None:
            return value
        path, offending = found
        raise ValueError(
            f"{path} is a `{type(offending).__name__}`, which does not survive"
            " the wire unchanged — canonical JSON renders it as text, so the"
            " decoded echo would differ from what was sent and the"
            " `WireOutcome.request` cross-check would report a transport"
            " failure on a healthy wire. Wire-stable parameter values are"
            " `str`, `int`, `bool`, `None`, and `dict`/`list` of those; render"
            " a `Decimal` with `format(value, 'f')` and an instant with"
            " `ccf.contracts.canonical.canonical_timestamp`"
        )

    @field_validator("temporal_boundary")
    @classmethod
    def _temporal_boundary_survives_the_wire(
        cls, value: datetime | None
    ) -> datetime | None:
        """Refuse a naive instant, at the seam, before any transport sees it.

        ``D-IMPL-151`` finding ``B0b``. The sibling of
        :meth:`_parameters_survive_the_wire`, one field over and for the same
        reason: a value that cannot cross is refused where the message can name
        the spelling that can, rather than surfacing as whatever each transport
        happens to make of it.

        **The defect this repairs, as measured.** With a naive ``--as-of``, the
        two shipped transports answered the same question with two different
        exception classes — ``inprocess:`` raised
        :class:`~ccf.contracts.canonical.CanonicalizationError` out of the graph
        backend, and ``mcp+stdio:`` raised
        :class:`~ccf.client.errors.TransportError` because the far door refused
        an ``asked_at`` with no offset and a raised door refusal reaches a client
        as a wire error. So the same caller mistake was two different failures,
        and on one transport it was reported as *the wire never spoke*. That is
        ``D-10``'s inversion running backwards: an exception reserved for "no
        governed answer arrived" used to report a caller's malformed argument,
        at a point where nothing downstream can tell the two apart.

        **Why a naive instant cannot cross.** ``D-IMPL-38`` admits no implicit
        UTC anywhere in the fabric: the canonical serializer refuses a naive
        datetime outright rather than guessing an offset, and both product doors
        refuse a naive ``asked_at`` by name. The instant a question is asked
        as-of is the boundary a replay resolves against, and a boundary whose
        offset is the producing host's local configuration is a boundary that
        replays differently on a different host.

        ``None`` is admitted unchanged and is not the same fact: it is the
        positive assertion *defer to the server's decision instant* (``D-04``),
        which is a question the fabric can answer.
        """
        if value is None or value.utcoffset() is not None:
            return value
        raise ValueError(
            f"temporal_boundary {value.isoformat()!r} carries no UTC offset,"
            " and a naive instant cannot cross this seam — the canonical"
            " serializer refuses it rather than guessing an offset, and both"
            " product doors refuse a naive `asked_at` by name, so the same"
            " question would fail differently on every transport (D-IMPL-38)."
            " Attach an explicit timezone: `datetime(..., tzinfo=UTC)`, or"
            " `value.replace(tzinfo=UTC)` if the instant is already UTC, or"
            " `datetime.fromisoformat('2026-08-01T00:00:00+00:00')`. Pass"
            " `None` to ask against the server's own decision instant"
        )


def _replay_ref_of(refusal: RefusalEnvelope | None) -> str | None:
    """A refusal's replay reference on the wire, or ``None`` at the sentinel.

    ``24.6-07``; ``D-IMPL-253`` Q13. Two vocabularies meet here and neither is
    wrong in its own place: the envelope says *"no record was minted"* with the
    positive :data:`~ccf.products.refusal.NO_REPLAY_REFERENCE` string, because
    a contract field that went quiet could not distinguish that from a dropped
    value; :attr:`DoorOutcome.replay_ref` says it with ``None``, because that
    field has meant *"this deployment's resolver returned no reference"* since
    it shipped and a served outcome uses ``None`` for exactly that.

    Translating in **one** place is what stops the two from being reconciled
    twice, differently — the rule-5 validator and :func:`door_answer` both read
    this function, so a door cannot emit an outcome its own validator refuses.
    """
    if refusal is None:
        return None
    if refusal.replay_reference == NO_REPLAY_REFERENCE:
        return None
    return refusal.replay_reference


class DoorOutcome(CCFContract):
    """One wire answer from a door: a served vessel, or a refusal.

    The shape a door emits on a transport with **no header channel** — which
    today is the MCP product tool. See the module docstring for why a refusal
    cannot be raised there, and why the vessel rides as text.

    **This is also what a client decodes.** ``C-06`` merged this class with the
    former ``ccf.client.wire.WireOutcome``, which is now an alias of it, so the
    emitted shape and the decoded shape are the same object rather than two
    declarations kept in step by hand.

    **The content address is an outcome-level sibling of the vessel, never a
    member of it.** The reason is recorded at
    ``ccf_runtime.http_api.routes::canonical_response`` and holds here
    unchanged: the vessel's bytes *are* the product, so carrying the address
    inside them would change the bytes and therefore change the address they
    claim. This envelope is a wrapper *around* the vessel, so the sibling always
    has room — which is why the address is required on a served outcome rather
    than optional. Every producer can compute it in one stdlib line from the
    bytes it already holds, so "the transport had no channel for it" is not a
    reachable case here, and admitting it as one would leave the decoder's
    recomputation with nothing to compare against exactly when it matters.

    Attributes:
        request: The question, echoed back. The decoder cross-checks it against
            the request that was actually sent — see
            :func:`ccf.client.codec.decode_outcome` for why an echo rather than
            a reconstruction, **and for the measured fact that both shipped
            adapters fill this member from the request they were handed rather
            than from the wire, which makes that cross-check inert on every
            shipped transport today** (``D-IMPL-151`` finding ``B0``, an open
            blocking defect deferred to its own phase). **Corrected in Phase
            19, with the measurement kept above rather than deleted:** the
            **producer** now mints this member from the question it parsed off
            its own wire (:func:`door_question`, ``C-01``), no adapter can
            construct an outcome at all (``C-05``), and the cross-check
            therefore compares two independently-sourced facts on both shipped
            transports.

        product_json: The UTF-8 text of the served vessel's canonical bytes, or
            ``None`` on a refusal. Text and never a byte string, and never a
            nested JSON object: the string *is* the producer's serialization,
            so a consumer's ``sha256`` of it is the producer's content address.
        content_address: The vessel's content address on a served outcome, and
            ``None`` on a refusal — a refusal is not a content-addressed
            artifact. Always recomputed by the decoder and never trusted from
            the wire — though on both shipped adapters the value recomputed
            against is one the adapter itself derived from the same
            ``product_json``, so the comparison cannot currently disagree. Same
            deferred defect as ``request`` above. **Corrected in Phase 19 in
            the same way:** :func:`door_answer` serializes the vessel **once**
            and claims ``sha256`` of those same bytes, so the value the decoder
            recomputes against is the **producer's** and the recomputation has
            an operand the consumer did not produce.
        replay_ref: The versioned URI of the replay record this outcome's
            decision was written into
            (:attr:`~ccf.artifacts.protocol.ArtifactRef.uri`), or ``None``.
            ``None`` is the honest report that **this deployment's resolver
            returned no reference** — the narrower
            :class:`~ccf.products.gates.ServableProduct` shape carries none —
            rather than a reference that was dropped in transit.

            **On a refusal it is the envelope's own** ``replay_reference``
            (``24.6-07``; ``D-IMPL-253`` Q13, rule 5 below). Until this row a
            refusal carried none, on the reasoning that nothing was delivered
            so no append authorized anything. That reasoning was about
            *delivery*, and the rule it produced quietly asserted the thing
            Dave's ruling denies: *"Refusal is itself a decision and deserves
            the same five-dimensional replay model."* A refusal is now recorded
            before its shell leaves the resolver, and the door reports where.
        refusal: The governed "no", with its kind unflattened, or ``None`` on a
            served outcome.
    """

    request: WireRequest
    product_json: str | None
    content_address: str | None
    replay_ref: str | None
    refusal: RefusalEnvelope | None

    @model_validator(mode="after")
    def _exactly_one_half(self) -> DoorOutcome:
        """Refuse an outcome that is neither served nor refused, or both.

        ``D-11``'s two-state rule, enforced at construction rather than
        documented, so *"discriminable structurally"* is a shape a caller
        cannot construct their way around. Three states would mean every
        consumer writes its own answer to "what does neither mean", and they
        would not all write the same one.

        **Five rules, and the count is the point.** ``C-06`` merged this
        validator with the former ``WireOutcome``'s; two of the seven raises
        across the two originals were the same rule said in different words,
        so the union is five. Each is named in ``19-01-PLAN.md`` Task 1 and
        each carries its own assertion in
        ``tests/products/test_door_answer.py``, because a merge that silently
        dropped one would leave the surviving class weaker than either of the
        two it replaced.
        """
        served = self.product_json is not None
        refused = self.refusal is not None
        if served and refused:
            raise ValueError(
                "a `DoorOutcome` carries a served vessel or a refusal, never"
                " both — one wire answer cannot be two governed answers"
            )
        if not served and not refused:
            raise ValueError(
                "a `DoorOutcome` carries a served vessel or a refusal, and this"
                " one carries neither; a door with nothing to say raises rather"
                " than emitting an empty answer"
            )
        if served and self.content_address is None:
            raise ValueError(
                "a served `DoorOutcome` carries the vessel's content address;"
                " it is computable from `product_json` in one stdlib line, so"
                " omitting it leaves the decoder's recomputation nothing to"
                " check against"
            )
        if refused and self.content_address is not None:
            raise ValueError(
                "a refused `DoorOutcome` carries no content address — a refusal"
                " is a governed answer, not a content-addressed artifact"
            )
        if refused and self.replay_ref != _replay_ref_of(self.refusal):
            raise ValueError(
                "a refused `DoorOutcome` carries the replay reference its own"
                f" envelope carries — {_replay_ref_of(self.refusal)!r} — and"
                f" this one carries {self.replay_ref!r}. A refusal IS a"
                " decision and has a decision record (`D-IMPL-253` Q13), so"
                " the door reports where that record landed rather than"
                " inventing one or dropping it; two references for one"
                " decision would be two answers to `which record authorized"
                " this?`"
            )
        return self


@dataclass(frozen=True)
class ServedAnswer:
    """A served vessel and the replay reference that authorized it.

    A plain frozen value rather than a contract, deliberately: it never crosses
    a wire. It exists so the three shipped doors read the **two** served shapes
    their resolvers actually return through one function instead of each
    growing its own ``isinstance`` ladder — which is how three doors come to
    disagree about what "served" means.

    Attributes:
        product: The gate-admitted vessel, exactly as the resolver produced it.
        replay_ref: The replay record's versioned URI, or ``None`` when the
            resolver answered with the narrower
            :class:`~ccf.products.gates.ServableProduct`, which carries none.
    """

    product: ContextProductContract
    replay_ref: str | None


def served_answer(resolved: object) -> ServedAnswer:
    """Read the vessel and its replay reference off whichever served shape came back.

    **Two shapes reach a door, and the divergence is recorded rather than
    incidental** (:mod:`ccf.products.resolver`, *"a named divergence"*). The two
    ``runtime/`` seams are typed to
    :class:`~ccf.products.gates.ServableProduct`; the ``src/``-resident
    :class:`~ccf.products.resolver.ServedProductResolverProtocol` — which a
    deployment may plug into a door, since the five arguments are copied
    exactly — is typed to :class:`~ccf.replay.serve.ServedProduct`. Only the
    second carries a replay reference, and reporting ``None`` for the first is
    the honest answer rather than a defect: the narrower vessel has none to
    give.

    Args:
        resolved: What a deployment's resolver returned.

    Returns:
        The vessel and the reference, or the reference's honest absence.

    Raises:
        TypeError: ``resolved`` is neither served shape. The message names the
            type, because a resolver answering with something else is a wiring
            defect and never a governed "no" — reporting the two the same way
            would let a mis-wiring read to a caller as a refusal the fabric
            never made.
    """
    if isinstance(resolved, ServedProduct):
        return ServedAnswer(
            product=resolved.product, replay_ref=resolved.replay_ref.uri
        )
    if isinstance(resolved, ServableProduct):
        return ServedAnswer(product=resolved.product, replay_ref=None)
    raise TypeError(
        f"a resolver answered a door with `{type(resolved).__name__}`, which is"
        " neither `ServableProduct` nor `ServedProduct`; a door serves what the"
        " gate sequence admitted and has nothing to serve from any other shape"
    )


def door_refusal(
    resolved: object,
    *,
    asked: ProductRequest | None,
    product_class: str,
    version: str,
) -> RefusalEnvelope | None:
    """The governed "no" a resolver answered with, or ``None`` if it served.

    Two refusal shapes reach a door, and **both** are handled here rather than
    at each door, so the three doors cannot come to disagree about what a
    refusal is:

    * a :class:`~ccf.products.refusal.RefusalEnvelope`, which is what
      :class:`~ccf.products.resolver.GovernedResolver` returns. It already
      carries its own :class:`~ccf.products.refusal.RequestIdentity` and, where
      one existed, the pre-assembly lineage — so it is passed through
      **untouched**. Re-enveloping it here would discard the lineage a gate
      refusal genuinely had, which is the flattening
      :mod:`ccf.products.refusal` exists to prevent.
    * a **bare** refusal value — a :class:`~ccf.products.gates.GateRefusal`, a
      :class:`~ccf.products.request.ProductRequestViolation`, any type
      :data:`~ccf.products.refusal.REFUSAL_KINDS` names — which is what a
      deployment's own resolver returns when it hands back what
      :func:`~ccf.products.gates.run_gates` gave it. The door translates it,
      supplying the question from the request it carried.

    **No third channel exists, and that is a measurement rather than an
    omission.** Every type in :data:`~ccf.products.refusal.REFUSAL_KINDS` is a
    :class:`~ccf.contracts.base.CCFContract` — a *value* — so none of them can
    be raised, and no shipped exception in the tree carries one. A door has
    nothing to catch and translate; a resolver refusing by exception is
    refusing in a vocabulary the envelope does not have.

    **The pre-assembly lineage is ``None`` on the translated path**, and saying
    so is not a loss the caller should have to guess at: a door holds the
    question and the answer, never the candidate contract that was refused, so
    the lineage a gate refusal had is reachable only from the resolver that
    produced it. A deployment wanting it returns a
    :class:`~ccf.products.refusal.RefusalEnvelope` — which is exactly what the
    SDK's reference resolver does.

    Args:
        resolved: What a deployment's resolver returned.
        asked: The question the door carried, or ``None`` when the surface has
            no way to ask one.
        product_class: The class the door already resolved and entitled. Taken
            from the door rather than from ``asked`` for the reason both doors
            fill ``schema_name`` from their own address: a request aimed at
            another class must be unrepresentable, not merely refused.
        version: The class's own semver lane, on the same terms.

    Returns:
        The envelope, or ``None`` when ``resolved`` is not a refusal at all.

    Raises:
        ValueError: a bare refusal value arrived on a surface that carried no
            question. The envelope's second ruled constraint is that it carries
            the pre-assembly request identity, and a door that manufactured one
            would be reporting a question nobody asked as the question that was
            refused.
    """
    if isinstance(resolved, RefusalEnvelope):
        return resolved
    if not isinstance(resolved, CCFContract) or type(resolved) not in REFUSAL_KINDS:
        return None
    if asked is None:
        raise ValueError(
            f"a resolver answered with `{type(resolved).__name__}` on a surface"
            " that carried no request, so there is no question for the refusal"
            " envelope to name; a door that invented one would report a"
            " question nobody asked as the one that was refused. Return a"
            " `RefusalEnvelope`, which carries its own request identity"
        )
    return envelope_for(
        resolved,
        request=RequestIdentity(
            product_id=product_class,
            product_version=version,
            parameters=asked.parameters,
            temporal_boundary=asked.asked_at,
        ),
    )


def door_question(asked_json: str) -> WireRequest:
    """Parse the question a caller encoded, so the door echoes what it *parsed*.

    ``C-01`` (Phase 19): the echo must be filled from what the door decoded off
    its own wire, never from an object it was handed. The parameter is
    **text** for exactly that reason — a door given an already-constructed
    :class:`WireRequest` would be echoing the caller's copy back to the caller,
    which is the reconstruction ``D-IMPL-151`` finding ``B0`` measured and this
    entry exists to make impossible.

    Args:
        asked_json: The canonical bytes of the caller's :class:`WireRequest`,
            decoded to UTF-8 text — what a transport actually carries.

    Returns:
        The question, exactly as it crossed.

    Raises:
        pydantic.ValidationError: ``asked_json`` is not a well-formed
            :class:`WireRequest`. Re-raised as itself rather than wrapped: a
            door handed a malformed request argument has been called
            malformedly, and at the MCP door the raise reaches a client as
            ``isError`` — the boundary ``D-IMPL-148`` Addendum A drew.
    """
    return WireRequest.model_validate_json(asked_json)


def door_answer(
    resolved: object,
    *,
    echo: WireRequest,
    resolved_request: ProductRequest,
    product_class: str,
    version: str,
) -> bytes:
    """The canonical bytes a door puts on an envelope-carrying wire.

    The one emission site for :class:`DoorOutcome`, so a door states what it
    was asked and what its bytes hash to without either fact being assembled
    twice (``C-01``, ``C-04``, ``C-06``).

    **``echo`` and ``resolved_request`` are different facts, which is why they
    do not share a name.** ``echo`` is the question as the caller stated it and
    is echoed **verbatim**: on the temporal axis its ``temporal_boundary`` may
    be ``None``, which is the positive assertion *answer against the decision
    instant* and must come back as ``None`` (``C-02``, ``C-15``).
    ``resolved_request.asked_at`` is the instant the door actually answers at
    and is never ``None``. Deriving either from the other reintroduces the
    vacuity ``C-02`` rejected, one field over.

    **The vessel is serialized exactly once** and the content address is
    ``sha256`` of those same bytes — the discipline
    ``ccf_runtime.http_api.routes::canonical_response`` records, because two
    serializations are two chances to disagree and a claimed address that
    disagreed with the bytes beside it would be a checkable claim that is
    false by construction.

    Args:
        resolved: What the deployment's resolver returned — a served shape or
            a refusal, exactly as :func:`served_answer` and
            :func:`door_refusal` already accept.
        echo: The question the door parsed off its own wire, via
            :func:`door_question`.
        resolved_request: The typed question the door resolved and answered
            against, and the one :func:`door_refusal` names in a refusal's
            request identity.
        product_class: The class the door already resolved and entitled.
        version: The class's own semver lane, on the same terms.

    Returns:
        The outcome's canonical bytes. **Bytes** rather than text, because the
        caller puts them on a wire without a second rendering.
    """
    refusal = door_refusal(
        resolved,
        asked=resolved_request,
        product_class=product_class,
        version=version,
    )
    if refusal is not None:
        return canonical_bytes(
            DoorOutcome(
                request=echo,
                product_json=None,
                content_address=None,
                # 24.6-07: where the refusal's own decision record landed. The
                # door REPORTS it and mints nothing — replay belongs to the
                # governed determination, never to a transport that noticed a
                # refusal (`D-IMPL-256`).
                replay_ref=_replay_ref_of(refusal),
                refusal=refusal,
            )
        )
    answer = served_answer(resolved)
    vessel = canonical_bytes(answer.product)
    return canonical_bytes(
        DoorOutcome(
            request=echo,
            product_json=vessel.decode("utf-8"),
            content_address=hashlib.sha256(vessel).hexdigest(),
            replay_ref=answer.replay_ref,
            refusal=None,
        )
    )
