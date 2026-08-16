"""The adapter seam — one request shape, one outcome shape, one method.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§5 (``D-11``) and Amendment 1 §A (``D-28``). Framed by CLAUDE.md §7.3: the typed
contract is the stable layer and the wire is replaceable, so the wire types name
a *shape*, never a transport.

What crosses here
-----------------
:class:`WireRequest` goes out, :class:`WireOutcome` comes back, and
:class:`TransportAdapter` is the whole of what a transport must implement. An
adapter carries the request; it never interprets it, and it never builds a
``Result`` — a single decoder does that in exactly one place (``D-12``), which
is what makes "every transport returns the same shape" a code path an adapter
cannot avoid rather than a convention it is asked to follow.

The vessel rides as text, and that is a ruling rather than a detail
-------------------------------------------------------------------
:attr:`WireOutcome.product_json` is the UTF-8 **text** of
:func:`~ccf.contracts.canonical.canonical_bytes` applied to the served
``ContextProductContract`` — which is exactly, character for character, what
every shipped door already emits (``ccf_runtime.mcp.egress``,
``ccf_runtime.mcp.experience``, and ``ccf_runtime.http_api.routes.product`` via
``canonical_response``). Freezing the served half is a transcription of what
exists, not a design.

It is **text and never a byte string**, and a later reader should not "fix"
that. The canonical serializer's normalizer admits no byte string in any branch:
its sequence branch explicitly excludes ``(str, bytes)`` and the function falls
through to ``CanonicalizationError``, so a contract carrying a byte-string field
cannot be canonically serialized *at all* — it raises on the first
:func:`~ccf.contracts.canonical.canonical_bytes` call. See
``ccf.contracts.canonical::_normalize``. A :class:`WireOutcome` spelled that way
would be simultaneously required to encode deterministically, forbidden from
inventing a second serialization, and unable to be serialized by the only one
that exists.

Carrying the text costs nothing and settles all three at once:

* **It is not a second serialization.** The string *is* the canonical
  rendering. Decoding those bytes to text and re-encoding them is the identity,
  byte for byte; nothing is re-ordered or re-formatted anywhere in the codec.
* **The outcome itself stays canonically serializable**, because text is a
  rendering the normalizer admits. So the outcome has a content address of its
  own, ``extra=forbid`` applies to it, and encoding is deterministic.
* **The address recomputation is exact**, because
  ``sha256(product_json.encode("utf-8"))`` is by construction the same digest as
  :func:`~ccf.contracts.canonical.content_hash` of the product.

A base64 or nested-JSON envelope was the alternative and is **rejected**: it
would put a second rendering of the vessel on the wire — the one thing freezing
the served half exists to prevent — and would make the recomputed address a
function of the envelope rather than of the product.

This module is algorithmic (CINV-03): typed values and pure validation, no I/O,
no clock, no LLM dependency ever.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import field_validator, model_validator

from ccf.contracts.base import CCFContract
from ccf.products.refusal import RefusalEnvelope

__ccf_mode__ = "algorithmic"

__all__ = ["TransportAdapter", "WireOutcome", "WireRequest"]


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
        temporal_boundary: The instant to answer against. ``None`` is the
            positive assertion *defer to the server's decision instant*, which
            is the rule ``D-04`` documents on ``ask()``; it is not an unset
            field.
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


class WireOutcome(CCFContract):
    """What came back — a served product or a refusal, and exactly one of them.

    ``D-11``: the canonical serialized form of either half. **A transport
    failure has no outcome at all** — see :class:`TransportAdapter`.

    **Two states, enforced at construction rather than documented.** A model
    validator refuses an outcome carrying both halves or neither, so the
    "exactly one" in ``D-11`` is a shape a caller cannot construct their way
    around. Three states would mean every consumer writes its own answer to
    "what does neither mean", and they would not all write the same one.

    **The content address is an outcome-level sibling of the vessel, never a
    member of it.** The reason is recorded at
    ``ccf_runtime.http_api.routes::canonical_response`` and holds here
    unchanged: the vessel's bytes *are* the product, so carrying the address
    inside them would change the bytes and therefore change the address they
    claim. This envelope is a wrapper *around* the vessel, so the sibling always
    has room — which is why the address is required on a served outcome rather
    than optional. Every adapter can compute it in one stdlib line from the text
    it already holds, so "the transport had no channel for it" is not a
    reachable case here, and admitting it as one would leave the decoder's
    recomputation with nothing to compare against exactly when it matters.

    Attributes:
        request: The question, echoed back. The decoder cross-checks it against
            the request that was actually sent — see
            :func:`ccf.client.codec.decode_outcome` for why an echo rather than
            a reconstruction.
        product_json: The UTF-8 text of the served vessel's canonical bytes, or
            ``None`` on a refusal. Text and never a byte string; the module
            docstring records why at length.
        content_address: The vessel's content address on a served outcome, and
            ``None`` on a refusal — a refusal is not a content-addressed
            artifact. Always recomputed by the decoder and never trusted from
            the wire.
        replay_ref: The replay record's artifact reference in string form, when
            one exists. No shipped door emits this today, which is a defect the
            client seam exists to fix rather than a feature request.
        refusal: The governed "no", carrying its kind unflattened, or ``None``
            on a served outcome.
    """

    request: WireRequest
    product_json: str | None
    content_address: str | None
    replay_ref: str | None
    refusal: RefusalEnvelope | None

    @model_validator(mode="after")
    def _exactly_one_half(self) -> WireOutcome:
        """Refuse an outcome that is neither served nor refused, or both."""
        served = self.product_json is not None
        refused = self.refusal is not None
        if served and refused:
            raise ValueError(
                "a `WireOutcome` carries a served product or a refusal, never"
                " both — one wire answer cannot be two governed answers"
            )
        if not served and not refused:
            raise ValueError(
                "a `WireOutcome` carries a served product or a refusal, and"
                " this one carries neither — a transport that produced no"
                " answer raises `TransportError` instead of returning an empty"
                " outcome"
            )
        if served and self.content_address is None:
            raise ValueError(
                "a served `WireOutcome` carries the vessel's content address;"
                " it is computable from `product_json` in one stdlib line, so"
                " omitting it leaves the decoder's recomputation nothing to"
                " check against"
            )
        if refused and self.content_address is not None:
            raise ValueError(
                "a refused `WireOutcome` carries no content address — a refusal"
                " is a governed answer, not a content-addressed artifact"
            )
        return self


@runtime_checkable
class TransportAdapter(Protocol):
    """One method: carry the question, bring back the outcome.

    ``D-11``. The whole of what a transport must implement, and deliberately so
    — an adapter surface wide enough to express policy is an adapter surface on
    which transports diverge.

    **A transport failure never has a** :class:`WireOutcome`. The three cases
    are distinct and stay distinct: a refusal is a value the fabric returned, a
    caller's negligence is an exception raised at the caller, and a wire that
    never spoke is a :class:`~ccf.client.errors.TransportError` raised by the
    adapter. An adapter that catches its own connection error and synthesizes a
    refusal has reported "the fabric said no" when nothing was ever asked.
    """

    def ask(self, request: WireRequest) -> WireOutcome:
        """Carry ``request`` to a producer and return its outcome.

        Raises:
            ccf.client.errors.TransportError: the wire never spoke. Never
                raised for a governed refusal, which is returned as an outcome.
        """
        ...
