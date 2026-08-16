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

The whole API
-------------
::

    from ccf.client import ProductClient

    client = ProductClient.for_product("hw1.companies-over-revenue")
    result = client.ask(parameters={"revenue_threshold": 1_000_000})

    if result.refused:
        log(result.refusal.reason, result.refusal.key)
    else:
        use(result.payload)   # + .debt, .content_address, .replay_ref, .lineage

What lives here
---------------
* :mod:`ccf.client.client` — :class:`~ccf.client.client.ProductClient` and the
  one decoder that builds every ``Result`` (``D-12``).
* :mod:`ccf.client.result` — the result contract and its fail-closed guard
  (``D-07``…``D-09``).
* :mod:`ccf.client.binding` — three-step resolution of *where*, and the scheme
  registry (``D-05``, ``D-06``).
* :mod:`ccf.client.errors` — the exception taxonomy. ``D-10``: exceptions are
  reserved for the wire failing and for caller negligence, never for a governed
  refusal.
* :mod:`ccf.client.wire` — the adapter seam. ``WireRequest``, ``WireOutcome``
  and the ``TransportAdapter`` Protocol (``D-11``).
* :mod:`ccf.client.codec` — the one encode and the one decode every transport
  shares (``D-12``, ``D-13``, ``D-20``).

The exported surface is exactly four names
-------------------------------------------
``D-03``: :class:`~ccf.client.client.ProductClient`,
:class:`~ccf.client.result.Result` (carrying its ``Refusal``),
:class:`~ccf.client.errors.TransportError` and
:class:`~ccf.client.errors.BindingError`. No manifest type, no Control Plane
type and no deployment type crosses this boundary (``D-02``). The count is not
a style preference — it is the measurable form of *the producer side stays
invisible to the client*, and ``tests/client/test_surface.py`` asserts it by
set equality with a control that watches the assertion fail on a fifth name.

Four names, and each thing deliberately **not** among them:

* ``Refusal`` rides on ``Result`` rather than standing beside it — the spec's
  own words are *"``Result`` (with its ``Refusal``)"* — and a caller reaches it
  through ``result.refusal``.
* ``WireRequest``, ``WireOutcome`` and ``TransportAdapter`` are the *adapter
  author's* surface. Someone asking a product a question never names a transport
  type; someone writing an adapter imports :mod:`ccf.client.wire` directly.
* ``RefusedResultError`` is importable from :mod:`ccf.client.errors` but is not
  offered here, because a caller reaching for it by name is writing ``except``
  around a field read — which is a way of working around the guard rather than
  branching on ``result.refused``.

This package is algorithmic (CINV-03): it moves typed values across a seam and
never acquires an LLM dependency.
"""

from __future__ import annotations

from ccf.client.client import ProductClient
from ccf.client.errors import BindingError, TransportError
from ccf.client.result import Result

__ccf_mode__ = "algorithmic"

__all__ = ["BindingError", "ProductClient", "Result", "TransportError"]
