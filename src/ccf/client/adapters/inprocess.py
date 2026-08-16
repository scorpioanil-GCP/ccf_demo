"""The degenerate wire — in-process, and deliberately not a fast path.

**SDK-defined**, ruled in ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
§5 (``D-13``), §7 (``D-16``) and Amendment 1 §C (``D-30``, ``D-32``).

What this adapter is for
-------------------------
``inprocess:./deployment`` is the binding a developer types first. The adapter
boots the deployment the address names, asks it one question, and hands back a
:class:`~ccf.client.wire.WireOutcome` — and it does all of that **invisibly**,
on the first :meth:`InProcessAdapter.ask`, so nothing about a manifest, a boot
sequence or an artifact key reaches the client developer (``D-02``, ``D-16``).

It serializes live objects anyway, and that is the point (``D-13``)
--------------------------------------------------------------------
This adapter has the served product in hand as a live Python object and
**encodes it to the canonical wire form regardless**, exactly as an HTTP body
would carry it. There is no fast path and there is not going to be one. Three
things follow, and the third is the one that could not be achieved by
convention:

* in-process becomes a **true degenerate wire** rather than a privileged leg,
  so the conformance suite's *"same* ``consume.py``\\ *, different*
  ``CCF_BINDING``\\ *, identical* ``Result``\\ *"* is a property of a shared code
  path rather than of two implementations that happen to agree;
* a parity bug has **exactly one place to live** —
  :mod:`ccf.client.codec` — because every transport's answer becomes a
  client-visible one through the same decode;
* the adapter is **physically prevented** from leaking a live producer-side
  object across the seam. A :class:`~ccf.replay.serve.ServedProduct`, a
  :class:`~ccf.products.gates.ServableProduct` and a
  :class:`~ccf.deployment.BootedFabric` cannot survive a round trip through
  UTF-8 text, so "the client never gets a handle into the producer's world" is
  a structural fact rather than a rule an adapter author is asked to follow.

The cost is a microsecond of serialization.

The boot cache is required, and not for speed (``D-30``)
----------------------------------------------------------
A second :func:`~ccf.deployment.config.load_config_and_boot` against the same
graph raises :class:`~ccf.graph._writer.SingleWriterViolation` — measured, and
the message names the graph: *"a GraphWriter already exists for graph
'…/graph.sqlite3'; the fabric permits exactly one writer per graph
(INV-CH7-10)"*. So caching is what makes a **second** ``ask()`` legal at all,
and what makes two :class:`~ccf.client.client.ProductClient`\\ s on one binding
legal at all. It is not an optimization and removing it does not make the
client slower; it makes the client raise.

**The cache key is the resolved absolute deployment root**, and that is
load-bearing rather than tidy. The single-writer identity is the *graph*, and
one deployment root composes one graph however its address was spelled — so a
cache keyed on the literal address string would boot twice against one graph
the first time an adopter wrote an absolute path, or a ``./a/../deployment``,
and would fail with a single-writer violation that named nothing the adopter
had done wrong. :func:`~ccf.client.adapters.binding_document.load_binding_document`
resolves the root, and this module keys on what it resolved.

The cache is process-lifetime and there is no ``close()`` on the client
(``D-30``). :func:`~ccf.deployment.manifest.load_and_boot`'s own docstring
warns that *"a loop that never closes leaks one connection per iteration"*; a
process-lifetime cache creates exactly **one** handle per deployment root, so
there is nothing to leak. Teardown is an :mod:`atexit` close.

What this adapter does not do, and will not learn to (``D-16``, ``D-32``)
--------------------------------------------------------------------------
It **boots**. It does not ingest, does not create a store, does not mint a
schema and does not start anything. The deployment an address names is already
populated — that is the deployment's own job, done before a client exists — and
a client call that provisioned would make asking a question a producer-side
act. That is the boundary Phase 16's rejected example got wrong, and
``tests/client/test_no_provisioning.py`` is the gate that keeps it drawn.

This module is algorithmic (CINV-03): it boots, calls a resolver and encodes.
No LLM dependency on this path, ever.
"""

from __future__ import annotations

import atexit
import hashlib
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ccf.client.adapters.binding_document import (
    BindingDocument,
    ResolverCall,
    conforming_resolver,
    load_binding_document,
    load_reference,
)
from ccf.client.binding import SCHEME_REGISTRY
from ccf.client.errors import BindingError, TransportError
from ccf.client.wire import WireOutcome, WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneProtocol, ControlPlaneRegistry
from ccf.deployment import BootedFabric
from ccf.deployment.config import load_config_and_boot
from ccf.products.refusal import RefusalEnvelope
from ccf.products.resolver import ServedProductResolverProtocol
from ccf.replay.serve import ServedProduct

__ccf_mode__ = "algorithmic"

__all__ = ["SCHEME", "InProcessAdapter", "reset_boot_cache"]


#: The scheme this adapter answers to. Written once, so the registry entry, the
#: refusal messages and the tests all say the same string.
SCHEME = "inprocess"


@dataclass(frozen=True)
class _BootedDeployment:
    """One deployment, booted once, with everything a question needs.

    Frozen and handle-carrying for the reason
    :class:`~ccf.deployment.BootedFabric` gives for its own shape: a live
    handle has no canonical serialization and never belongs in a content hash.
    """

    fabric: BootedFabric
    control_plane: ControlPlaneProtocol
    resolver: ServedProductResolverProtocol
    question: Any


#: Resolved absolute deployment root → the fabric booted from it. Process
#: lifetime, module level, and the only mutable state in this package — it
#: exists because "has this graph already got a writer?" is not a question a
#: type system can answer, which is the same reason
#: ``ccf.graph._writer::_LIVE_WRITERS`` exists one layer down.
_BOOT_CACHE: dict[Path, _BootedDeployment] = {}

#: Guards :data:`_BOOT_CACHE`. Two threads asking the same *unbooted* binding
#: would otherwise both miss the cache and both boot, and the second boot is
#: precisely the ``SingleWriterViolation`` the cache exists to prevent. The
#: boot happens **inside** the lock for that reason; it is slow (~74 ms cold),
#: and holding a lock across it is the cost of the invariant.
_BOOT_LOCK = threading.Lock()


def reset_boot_cache() -> None:
    """Close every cached fabric and empty the cache. **For tests only.**

    Not re-exported from :mod:`ccf.client`: ``D-03`` fixes that package's
    surface at four names, and a fifth for a test affordance would put a
    lifecycle control in a client developer's namespace to buy a test
    something the test can reach directly.

    Closing is not optional here and is the whole reason this is a function
    rather than ``_BOOT_CACHE.clear()``. A cleared cache whose handles were
    never closed leaves the writers live, so the next boot against the same
    graph raises :class:`~ccf.graph._writer.SingleWriterViolation` — a test
    helper that made the next test fail for a reason belonging to the previous
    one.
    """
    with _BOOT_LOCK:
        cached = list(_BOOT_CACHE.values())
        _BOOT_CACHE.clear()
    for entry in cached:
        entry.fabric.handle.close()


@atexit.register
def _close_cached_fabrics() -> None:
    """Release every graph handle at process exit.

    Registered rather than left to the interpreter because a handle owns a
    backend connection. There is no ``close()`` on
    :class:`~ccf.client.client.ProductClient` by ruling (``D-30``) — two clients
    on one binding **share** the cached fabric, so a per-client close would
    retire a handle the other client is still using.
    """
    for entry in list(_BOOT_CACHE.values()):
        try:
            entry.fabric.handle.close()
        except Exception:  # pragma: no cover - best effort at interpreter exit
            pass
    _BOOT_CACHE.clear()


def _boot(document: BindingDocument) -> _BootedDeployment:
    """Boot one deployment and wire its resolver. Called at most once per root.

    Every value this needs comes from the deployment: the Control Plane
    document ``binding.yaml`` names, the connection its own factory composes,
    and the resolver and question factories it declares. This function supplies
    no default for any of them, which is why it has nothing domain-specific to
    hold.
    """
    connection: Mapping[str, object] | None = None
    if document.connection is not None:
        composer = load_reference(
            document.connection, root=document.root, key="connection"
        )
        composed = composer(root=document.root)
        if not isinstance(composed, Mapping):
            raise BindingError(
                f"`connection: {document.connection}` in"
                f" {document.root}/binding.yaml names a factory that returned"
                f" `{type(composed).__name__}` — a connection factory returns a"
                " mapping of the declared adapter's own setting names to their"
                " values"
            )
        connection = composed

    control_plane = ControlPlaneRegistry()
    fabric = load_config_and_boot(
        document.config, registry=control_plane, connection=connection
    )
    factory = load_reference(document.resolver, root=document.root, key="resolver")
    resolver = conforming_resolver(
        factory(fabric=fabric, control_plane=control_plane),
        reference=document.resolver,
        root=document.root,
    )
    question = load_reference(document.question, root=document.root, key="question")
    return _BootedDeployment(
        fabric=fabric,
        control_plane=control_plane,
        resolver=resolver,
        question=question,
    )


class InProcessAdapter:
    """Carry a question to a deployment in this process, and encode the answer.

    Conforms to :class:`~ccf.client.wire.TransportAdapter` structurally; it is
    registered for the ``inprocess`` scheme at import of this module, which is
    the whole of how a scheme reaches the registry (``D-05`` — no plugin lookup
    and no discovery chain).

    Args:
        address: The remainder of the binding after its scheme prefix — the
            deployment root. Not resolved here: resolution happens at boot,
            through :func:`~ccf.client.adapters.binding_document.load_binding_document`,
            so a client constructed against a root that does not exist yet
            fails when it asks rather than when it is built.
    """

    #: The deployment's resolver, bound on first :meth:`ask`.
    #:
    #: **The annotation is load-bearing and is not a style choice.**
    #: ``tests/invariants/test_mcp_role_separation.py`` walks for product doors
    #: by matching seam names against
    #: :data:`~tests.invariants.test_mcp_role_separation.PRODUCT_RESOLVER_PROTOCOLS`,
    #: and one of the shapes it matches is an annotated assignment whose
    #: annotation names a resolver Protocol. An adapter holding its resolver in
    #: an un-annotated attribute would be **invisible** to the gate that exists
    #: to see exactly this door — and the gate would pass while checking
    #: nothing, which is the failure mode that suite was built to be immune to.
    _resolver: ServedProductResolverProtocol

    __slots__ = ("_address", "_question", "_resolver", "_tenant")

    def __init__(self, address: str) -> None:
        self._address = address

    def ask(self, request: WireRequest) -> WireOutcome:
        """Boot if needed, ask the deployment, and encode what it answered.

        Raises:
            ccf.client.errors.BindingError: the address names no deployment, or
                its binding document is unusable. A
                :class:`~ccf.client.errors.TransportError` by inheritance, so
                one ``except`` clause still covers every way the wire never
                spoke.
            ccf.client.errors.TransportError: the deployment's question factory
                did not produce a :class:`ResolverCall`.
            ccf.products.resolver.ProductNotResolvable: the deployment is
                wired to serve a different class than the one asked for.
                Deliberately **not** converted into a refusal: a mis-wiring
                reported as a governed "no" would have a caller record an
                audited refusal the fabric never made.
        """
        booted = self._ensure_booted()
        call = self._question(
            product_id=request.product_id,
            parameters=request.parameters,
            temporal_boundary=request.temporal_boundary,
        )
        if not isinstance(call, ResolverCall):
            raise TransportError(
                f"the deployment at {self._address} answered its question"
                f" factory with `{type(call).__name__}` rather than a"
                " `ResolverCall`, so there is no typed question to ask and no"
                " perspective to ask it under"
            )

        outcome = self._resolver(
            tenant=booted.fabric.tenant_id,
            product_class=call.request.schema_name,
            version=call.request.schema_version,
            perspective=call.perspective,
            request=call.request,
        )
        return self._encode(outcome, request=request)

    def _ensure_booted(self) -> _BootedDeployment:
        """Return this address's booted deployment, booting it at most once.

        The resolved root is computed **before** the cache is consulted, which
        is the whole of ``D-30``'s cache-key rule: ``./deployment`` and the
        absolute path it resolves to produce one key, so they share one fabric
        and the second one does not raise.
        """
        document = load_binding_document(self._address)
        with _BOOT_LOCK:
            booted = _BOOT_CACHE.get(document.root)
            if booted is None:
                booted = _boot(document)
                _BOOT_CACHE[document.root] = booted
        self._resolver = booted.resolver
        self._question = booted.question
        self._tenant = booted.fabric.tenant_id
        return booted

    @staticmethod
    def _encode(outcome: object, *, request: WireRequest) -> WireOutcome:
        """Put the answer on the wire — the same bytes an HTTP body would carry.

        ``D-13``. The served vessel is rendered through the SDK's one canonical
        serializer and the address is ``sha256`` of exactly those bytes, so the
        decoder's recomputation is exact by construction rather than by two
        implementations agreeing.

        The replay reference travels as the artifact's **versioned URI**, which
        is the resolvable form: a consumer holding a product can name the
        decision record that authorized it, which is what makes the audit trail
        usable from the consuming side.
        """
        if isinstance(outcome, RefusalEnvelope):
            return WireOutcome(
                request=request,
                product_json=None,
                content_address=None,
                replay_ref=None,
                refusal=outcome,
            )
        if not isinstance(outcome, ServedProduct):  # pragma: no cover - typed seam
            raise TransportError(
                "the deployment's resolver answered with"
                f" `{type(outcome).__name__}`, which is neither a served"
                " product nor a governed refusal — the seam's return type is a"
                " union of exactly those two"
            )
        vessel = canonical_bytes(outcome.product)
        return WireOutcome(
            request=request,
            product_json=vessel.decode("utf-8"),
            content_address=hashlib.sha256(vessel).hexdigest(),
            replay_ref=outcome.replay_ref.uri,
            refusal=None,
        )


SCHEME_REGISTRY[SCHEME] = InProcessAdapter
