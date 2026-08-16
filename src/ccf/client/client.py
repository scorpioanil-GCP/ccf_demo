"""The whole of what a client developer learns — two calls and one branch.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§2 and §5 (``D-01``…``D-04``, ``D-12``, ``D-24``).

The entire API::

    from ccf.client import ProductClient

    client = ProductClient.for_product("hw1.companies-over-revenue")
    result = client.ask(parameters={"revenue_threshold": 1_000_000})

    if result.refused:
        log(result.refusal.reason, result.refusal.key)
    else:
        use(result.payload)

Nothing about a manifest, a boot sequence, a Control Plane artifact or an
artifact key appears anywhere in that (``D-02``). The producer side is
invisible to the client, and the scheme prefix inside ``CCF_BINDING`` is the
only place a transport is named.

Why ``Result`` is built here and nowhere else
----------------------------------------------
``D-12``. A Context Product is valuable because of the contract it returns —
typed payload, measured debt, content address, lineage, replay reference, and
an explicit refusal when the governed answer is "no". If every transport
re-implemented that contract in its own shape, the value would evaporate. So
adapters return a :class:`~ccf.client.wire.WireOutcome` and exactly one
decoder, :meth:`ProductClient._result_from`, turns it into a
:class:`~ccf.client.result.Result`. Shape identity across transports is
therefore a code path an adapter cannot avoid rather than a convention it is
asked to follow, and ``tests/client/test_surface.py`` asserts the one-site
property with an AST scan over ``src/``, ``runtime/`` and ``examples/``.

The same reasoning is why this module re-checks what it was handed. ``D-11``
types the adapter seam as returning a ``WireOutcome`` object rather than bytes,
so an adapter that never went near :mod:`ccf.client.codec` can still hand over
a well-formed one. Running :func:`~ccf.client.codec.check_outcome` here — the
*same* function :func:`~ccf.client.codec.decode_outcome` runs — makes the echo
cross-check, the address recomputation and the vessel's validity hold for every
transport whether or not its author remembered them.

Sync only, deliberately
-----------------------
``D-24``. One :meth:`ProductClient.ask`. Async would double the exported
surface, and the first audience for this package is a reader. The concrete
revisit trigger is the MCP adapter — MCP client libraries are async-native and
the adapter bridges internally — and the ``Result`` contract is unaffected
either way.

This module is algorithmic (CINV-03): it moves typed values across a seam and
never acquires an LLM dependency.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ccf.client.binding import adapter_for_binding
from ccf.client.codec import check_outcome
from ccf.client.result import Result
from ccf.client.wire import TransportAdapter, WireOutcome, WireRequest

__ccf_mode__ = "algorithmic"

__all__ = ["ProductClient"]


class ProductClient:
    """One product class, one transport, one question at a time.

    ``D-03``, ``D-04``. Bound to a single product class at construction, so a
    caller asks a question rather than naming a class on every call and the
    identity that ends up in the refusal is the one the client was built for.

    Args:
        product_id: The product class this client asks.
        adapter: The transport that carries the question. Supplied directly by
            an adapter author or a test; the ordinary path is
            :meth:`for_product`, which resolves it from the binding.
    """

    __slots__ = ("_adapter", "_product_id")

    def __init__(self, *, product_id: str, adapter: TransportAdapter) -> None:
        self._product_id = product_id
        self._adapter = adapter

    @classmethod
    def for_product(
        cls, product_id: str, binding: str | None = None
    ) -> ProductClient:
        """Build a client for ``product_id`` over the transport ``binding`` names.

        ``D-04``, ``D-05``. Resolution is three steps and no fourth: an explicit
        ``binding`` wins, else the ``CCF_BINDING`` environment variable, else a
        :class:`~ccf.client.errors.BindingError` naming exactly what to set. The
        scheme prefix inside the address is the only place a transport is named
        in the client's world, and it lives in the environment rather than in
        code — so switching transports is an ops action, and *"same*
        ``consume.py``\\ *, different* ``CCF_BINDING``\\ *, identical*
        ``Result``" is a property rather than a claim.

        Args:
            product_id: The product class to ask.
            binding: A scheme-prefixed address such as ``inprocess:./deployment``
                or ``mcp+stdio:./server.py``. ``None`` defers to
                ``CCF_BINDING``.

        Returns:
            A client bound to the class and to the transport its scheme names.

        Raises:
            ccf.client.errors.BindingError: no address resolved, the address
                carries no scheme prefix, or no adapter is registered for its
                scheme. A :class:`~ccf.client.errors.TransportError` by
                inheritance, so one ``except`` clause covers every way the wire
                never spoke.
        """
        return cls(product_id=product_id, adapter=adapter_for_binding(binding))

    @property
    def product_id(self) -> str:
        """The product class this client asks."""
        return self._product_id

    def ask(
        self, parameters: Mapping[str, Any], as_of: datetime | None = None
    ) -> Result:
        """Ask the question, and get back the answer or the governed "no".

        ``D-04``, ``D-07``. A refusal is **not** an exception: it is the fabric
        working, so the returned :class:`~ccf.client.result.Result` carries
        either half and a caller branches on ``result.refused``.

        **The** ``as_of=None`` **rule.** ``None`` means *use the server's
        decision instant* — the producing deployment answers against its own
        clock, and the instant it used comes back on the served vessel. Passing
        an explicit instant asks the question against that moment instead, which
        is what makes an answer reproducible: the first example's documented
        command passes a fixed ``--as-of`` precisely so its printed debt and
        content address reproduce exactly. The two are not in tension. The API
        default stays ``None`` because the ordinary question is *what is true
        now*, and a client that had to name an instant would be a client
        maintaining a copy of the server's clock.

        Args:
            parameters: The class-declared remainder of the question. Required
                rather than defaulted: an empty mapping is a question that
                needed nothing beyond its axes, which is a positive statement
                and not the same fact as one nobody thought about.
            as_of: The instant to answer against, or ``None`` for the server's
                decision instant.

        Returns:
            The one result shape, identical across every transport.

        Raises:
            ccf.client.errors.TransportError: the wire never spoke — the
                connection failed, the transport answered a different question
                than the one asked, or what came back does not hash to the
                address claimed for it. Never raised for a governed refusal.
        """
        request = WireRequest(
            product_id=self._product_id,
            parameters=parameters,
            temporal_boundary=as_of,
        )
        return self._result_from(self._adapter.ask(request), sent=request)

    def _result_from(self, outcome: WireOutcome, *, sent: WireRequest) -> Result:
        """The one place a :class:`~ccf.client.result.Result` is constructed.

        ``D-12``. Every transport's answer becomes a client-visible one here, so
        a property proven of this function holds for every adapter that ever
        ships — and a property not proven here is one each adapter gets to break
        in its own way.

        The request identity on the result is taken from the outcome's **echo**
        rather than from ``sent``, which is only safe because
        :func:`~ccf.client.codec.check_outcome` has just proven the two equal.
        Reading it from the echo is what makes that check load-bearing instead
        of advisory: if the comparison were ever removed, the identity a caller
        sees would immediately be the one the transport supplied.

        Args:
            outcome: What the adapter returned.
            sent: The request that was actually sent, for the echo cross-check.

        Returns:
            The result, carrying the served vessel or the refusal.

        Raises:
            ccf.client.errors.TransportError: the outcome does not answer the
                question that was asked, the vessel does not hash to its claimed
                address, or the vessel is not a valid contract.
        """
        vessel = check_outcome(outcome, sent=sent)
        return Result(
            product_id=outcome.request.product_id,
            parameters=outcome.request.parameters,
            temporal_boundary=outcome.request.temporal_boundary,
            vessel=vessel,
            content_address=outcome.content_address,
            replay_ref=outcome.replay_ref,
            refusal=outcome.refusal,
        )
