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

This module is algorithmic (CINV-03): pure functions over typed values, no
I/O, no clock, no LLM dependency ever.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import model_validator

from ccf.contracts.base import CCFContract
from ccf.products.contract import ContextProductContract
from ccf.products.gates import ServableProduct
from ccf.products.refusal import (
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


class DoorOutcome(CCFContract):
    """One wire answer from a door: a served vessel, or a refusal.

    The shape a door emits on a transport with **no header channel** — which
    today is the MCP product tool. See the module docstring for why a refusal
    cannot be raised there, and why the vessel rides as text.

    Attributes:
        product_json: The UTF-8 text of the served vessel's canonical bytes, or
            ``None`` on a refusal. Text and never a byte string, and never a
            nested JSON object: the string *is* the producer's serialization,
            so a consumer's ``sha256`` of it is the producer's content address.
        replay_ref: The versioned URI of the replay record whose successful
            append authorized this delivery
            (:attr:`~ccf.artifacts.protocol.ArtifactRef.uri`), or ``None``.
            ``None`` is the honest report that **this deployment's resolver
            returned no reference** — the narrower
            :class:`~ccf.products.gates.ServableProduct` shape carries none —
            rather than a reference that was dropped in transit. A refusal
            carries none: nothing was delivered, so no append authorized
            anything.
        refusal: The governed "no", with its kind unflattened, or ``None`` on a
            served outcome.
    """

    product_json: str | None
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
        if refused and self.replay_ref is not None:
            raise ValueError(
                "a refused `DoorOutcome` carries no replay reference: nothing"
                " was delivered, so no replay append authorized anything and a"
                " reference here would name a decision record for a decision"
                " that was not made"
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
