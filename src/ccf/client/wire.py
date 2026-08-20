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

**Amended by ``C-05``/``C-08`` (Phase 19): what comes back across the seam is
the producer's canonical** ``bytes``\\ **, and** :class:`WireOutcome` **is what
the** *codec* **parses out of them.** The sentence above is kept because its
argument is unchanged and was the reason for the change: an adapter that never
builds the outcome cannot build one whose echo it filled from the request it
was handed, so the reach of *"a code path an adapter cannot avoid"* grew from
``Result`` construction to the integrity checks themselves. ``D-11`` is amended
to that extent and to no other; the request stays typed, the outcome shape is
unchanged, and ``__all__`` is what it was.

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

One shape, defined in the products package and re-exported here
---------------------------------------------------------------
``C-06`` (Phase 19, ``19-CONTEXT.md``) collapsed this module's outcome shape
and :class:`~ccf.products.door.DoorOutcome` into **one**, so a door emits
precisely what a client decodes and no transcoding step exists between them — a
transcoding step being exactly where an adapter can re-source the echo from
client state rather than from the wire (``D-IMPL-151`` finding ``B0``).

**The definition lives in :mod:`ccf.products.door`, not here**, because a door
cannot import a client: the shape is emitted from ``runtime/`` and decoded in
``src/ccf/client``, and the placement argument :mod:`ccf.products.door` states
at its own head (*"putting it beside the types it carries is what lets the
emission and the decode agree by construction"*) is what decides the direction.
:class:`WireRequest` moved for the same reason — the door has to name the type
it echoes. Both are re-exported here under their published names, and
``WireOutcome`` is an alias rather than a subclass, so every existing import
path resolves to the same object rather than to a second shape.

This module is algorithmic (CINV-03): typed values and pure validation, no I/O,
no clock, no LLM dependency ever.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.products.door import DoorOutcome, WireRequest

__ccf_mode__ = "algorithmic"

__all__ = ["TransportAdapter", "WireOutcome", "WireRequest"]


#: The one outcome shape, under its published client-side name.
#:
#: An **alias**, not a subclass (``C-06``): ``WireOutcome is DoorOutcome`` is
#: true, so a door's emission and a client's decode cannot drift apart, and an
#: ``isinstance`` check written against either name admits the other.
WireOutcome = DoorOutcome


@runtime_checkable
class TransportAdapter(Protocol):
    """One method: carry the question, bring back the outcome.

    ``D-11``, **as amended by** ``C-05``/``C-08`` (Phase 19): the method returns
    the producer's canonical ``bytes`` rather than an outcome object. The whole
    of what a transport must implement, and deliberately so — an adapter
    surface wide enough to express policy is an adapter surface on which
    transports diverge.

    **A transport failure never has a** :class:`WireOutcome`. The three cases
    are distinct and stay distinct: a refusal is a value the fabric returned, a
    caller's negligence is an exception raised at the caller, and a wire that
    never spoke is a :class:`~ccf.client.errors.TransportError` raised by the
    adapter. An adapter that catches its own connection error and synthesizes a
    refusal has reported "the fabric said no" when nothing was ever asked.

    That paragraph is **unchanged and still exactly right** under the bytes
    seam, and reads more sharply for it: a transport failure now has no *bytes*
    either, and an adapter with nothing to construct has one fewer way to
    manufacture an answer nobody gave. What an adapter author must do
    differently is return what the producer emitted, unexamined — there is no
    deprecation window and no shim accepting either shape, because a shim that
    reconstructed the outcome would restore the permission that admitted
    ``D-IMPL-151`` finding ``B0``.
    """

    def ask(self, request: WireRequest) -> bytes:
        """Carry ``request`` to a producer and return the producer's canonical bytes.

        The answer is **bytes and not an outcome object** (``C-08``, Phase 19).
        The request stays typed because an adapter genuinely needs its fields to
        build a tool call or a URL; only the answer becomes bytes.

        **What the bytes seam does and does not buy, stated exactly** (Phase 19
        close review, ``D-IMPL-162``). It removes the *convenient* path to
        ``D-IMPL-151`` finding ``B0``: an adapter can no longer return a
        well-formed outcome it built, so returning the producer's bytes
        unexamined is the path of least resistance rather than one choice among
        two. Inside this tree it is closed outright — ``C-17``'s gate
        (``tests/client/test_surface.py``) fails if any module under
        ``src/ccf/client/adapters/`` constructs the outcome at all.

        It does **not** make reconstruction impossible. ``WireOutcome`` and
        :func:`~ccf.client.codec.encode_outcome` are both public, by design,
        because this is a ``Protocol`` and out-of-tree adapters are the point of
        one. An adapter outside this tree may parse the producer's bytes, copy
        its own caller's request over the echo, re-encode, and return bytes that
        satisfy this signature — and both
        :func:`~ccf.client.codec.check_outcome` and
        :func:`~ccf.client.codec.verify_content_address` then pass, because the
        adapter supplied both sides of each comparison. That is ``B0``'s failure
        mode, reachable only by an adapter author who goes out of their way.
        Making it *unreachable* would need a producer signature or a private
        encoder; that is deferred, not done (``D-IMPL-162``).

        Raises:
            ccf.client.errors.TransportError: the wire never spoke. Never
                raised for a governed refusal, which is returned as an outcome.
        """
        ...
