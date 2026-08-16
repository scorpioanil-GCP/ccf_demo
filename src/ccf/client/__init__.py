"""The CCF client — one way to ask a Context Product a question.

**SDK-defined, not whitepaper-derived.** The whitepaper specifies the Context
Product Contract (§6.3) and its delivery envelope (§7.6); it does not specify a
*client*, because it does not commit to a transport. This package is the CCF
SDK's extension, ruled in
``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` and framed by
CLAUDE.md §7.3: the neutral seams — the typed contract, MCP, A2A — are the
stable layer, and a client that speaks the contract speaks every transport.

Why the package exists
----------------------
A Context Product is valuable because of the contract it returns: a typed
payload, measured debt, a content address, lineage, a replay reference, and an
explicit refusal when the governed answer is "no". If every transport
re-implements that contract in its own shape, the value evaporates — so ``D-01``
puts the client abstraction and the result contract in the SDK and makes
transports adapters *behind* it.

What lives here
---------------
* :mod:`ccf.client.errors` — the exception taxonomy. ``D-10``: exceptions are
  reserved for the wire failing and for caller negligence, never for a governed
  refusal.
* :mod:`ccf.client.wire` — the adapter seam. ``WireRequest``, ``WireOutcome``
  and the ``TransportAdapter`` Protocol (``D-11``).
* :mod:`ccf.client.codec` — the one encode and the one decode every transport
  shares (``D-12``, ``D-13``, ``D-20``).

The exported surface, and why it is empty here today
----------------------------------------------------
``D-03`` fixes this package's public surface at **exactly four names** —
``ProductClient``, ``Result`` (carrying its ``Refusal``), ``TransportError`` and
``BindingError``. No manifest type, no Control Plane type and no deployment type
crosses this boundary (``D-02``).

The wire types are deliberately **not** among them. ``WireRequest``,
``WireOutcome`` and ``TransportAdapter`` are the *adapter author's* surface, not
the client developer's: someone asking a product a question never names a
transport type, and someone writing an adapter imports :mod:`ccf.client.wire`
directly. ``__all__`` is therefore empty until the four names exist, at which
point it holds those four and nothing else.

This package is algorithmic (CINV-03): it moves typed values across a seam and
never acquires an LLM dependency.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"

__all__: list[str] = []
